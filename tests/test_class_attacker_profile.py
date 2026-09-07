"""LANE-CS: tests for `class_attacker_profile`, the module that turns a real
character row into the attacker `Combatant`.

Two things this file deliberately does NOT do.  It does not restate the
damage formula's constants -- every arithmetic expectation is re-derived from
`mob_combat`'s own `Combatant.attack` in the test body, so the day that
formula changes these tests move with it instead of pinning a stale number.
And it does not hand-type the five class ids: they come from
`class_catalog.CLASS_IDS`, so a sixth selectable class changes what this file
expects rather than leaving a row that quietly stops testing anything.

`CallersInSrcTokenIsMeasuredTests` is the one guard here that watches
something outside this module: the headless token says `callers_in_src=0`,
and the day someone wires the module (the CORE-REQUEST this round files) that
token becomes a lie unless it is re-measured.  The test measures the tree.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    class_attacker_profile,
    class_catalog,
    mob_combat,
    persistence_standard_status,
)

SRC = ROOT / "src" / "pirateforce_foundation"


def _row(class_id, level):
    return class_attacker_profile.CharacterBattleRow(
        class_id=class_id, level=level
    )


class EverySelectableClassBuildsAProfileTests(unittest.TestCase):
    def test_every_class_id_at_birth_level_builds_a_combatant(self):
        for class_id in class_catalog.CLASS_IDS:
            with self.subTest(class_id=class_id):
                profile = class_attacker_profile.profile_for_character(
                    _row(class_id, persistence_standard_status.
                         STANDARD_STATUS_MIN_LEVEL)
                )
                self.assertIsInstance(profile, mob_combat.Combatant)
                self.assertEqual(
                    persistence_standard_status.STANDARD_STATUS_MIN_LEVEL,
                    profile.level,
                )
                self.assertEqual(
                    mob_combat.PIN_ATTACKER_ABILITY_STR, profile.ability_str
                )

    def test_the_attacker_record_carries_no_invented_defence(self):
        # `Combatant`'s own docstring: the attacker half reads `level` and
        # `ability_str`.  A defence number on an attacker profile would be a
        # number nobody asked for, so it is 0 and this pins that.
        profile = class_attacker_profile.profile_for_character(_row(2, 1))
        self.assertEqual(0, profile.ability_con)

    def test_the_top_table_level_is_accepted(self):
        top = persistence_standard_status.STANDARD_STATUS_MAX_LEVEL
        profile = class_attacker_profile.profile_for_character(_row(1, top))
        self.assertEqual(top, profile.level)


class LevelActuallyMovesTheAttackNumberTests(unittest.TestCase):
    """The whole point of the module: two characters, two numbers."""

    def test_a_higher_level_character_swings_harder(self):
        low = class_attacker_profile.profile_for_character(_row(1, 5))
        high = class_attacker_profile.profile_for_character(_row(1, 40))
        self.assertLess(low.attack, high.attack)

    def test_the_pin_is_reproduced_exactly_at_the_pinned_level(self):
        # Not a coincidence worth asserting for its own sake: it is the
        # control that proves the difference at other levels comes from the
        # level and from nothing else this module added.
        same = class_attacker_profile.profile_for_character(
            _row(1, class_attacker_profile.PINNED_LEVEL)
        )
        self.assertEqual(class_attacker_profile.pinned_profile().attack,
                         same.attack)

    def test_the_birth_level_delta_is_the_formulas_own_arithmetic(self):
        born = class_attacker_profile.profile_for_character(_row(1, 1))
        pin = class_attacker_profile.pinned_profile()
        expected = mob_combat.K_ATK_LV * (born.level - pin.level)
        self.assertEqual(expected, born.attack - pin.attack)


class RowsThatCannotAnswerAreRefusedByNameTests(unittest.TestCase):
    def _refusal(self, class_id, level):
        with self.assertRaises(
            class_attacker_profile.ClassAttackerProfileError
        ) as caught:
            class_attacker_profile.profile_for_character(_row(class_id, level))
        return caught.exception

    def test_a_class_id_that_is_not_selectable_is_refused(self):
        unknown = 3
        self.assertNotIn(unknown, class_catalog.CLASS_IDS)
        error = self._refusal(unknown, 1)
        self.assertEqual(
            class_attacker_profile.REFUSE_CLASS_ID_UNKNOWN, error.reason
        )

    def test_a_zero_class_id_is_refused_rather_than_defaulted(self):
        self.assertNotIn(0, class_catalog.CLASS_IDS)
        self.assertEqual(
            class_attacker_profile.REFUSE_CLASS_ID_UNKNOWN,
            self._refusal(0, 1).reason,
        )

    def test_levels_off_the_committed_table_are_refused(self):
        below = persistence_standard_status.STANDARD_STATUS_MIN_LEVEL - 1
        above = persistence_standard_status.STANDARD_STATUS_MAX_LEVEL + 1
        for level in (below, above, -1, 10 ** 9):
            with self.subTest(level=level):
                self.assertEqual(
                    class_attacker_profile.REFUSE_LEVEL_OFF_TABLE,
                    self._refusal(1, level).reason,
                )

    def test_a_level_missing_from_the_table_is_refused_even_inside_the_span(
        self,
    ):
        # The check is a real row read, not a range comparison: prove it by
        # removing a row the span still covers.
        rows = dict(persistence_standard_status.STANDARD_STATUS_ROWS)
        victim = 9
        self.assertIn(victim, rows)
        del rows[victim]
        with mock.patch.object(
            persistence_standard_status, "STANDARD_STATUS_ROWS", rows
        ):
            self.assertEqual(
                class_attacker_profile.REFUSE_LEVEL_OFF_TABLE,
                self._refusal(1, victim).reason,
            )

    def test_a_bool_is_not_a_level_and_is_not_a_class_id(self):
        # `True == 1` and 1 IS a selectable class id, so a coercing check
        # would build a Gladiator at level 1 out of two booleans.
        for class_id, level in ((True, 1), (1, True)):
            with self.subTest(class_id=class_id, level=level):
                with self.assertRaises(
                    class_attacker_profile.ClassAttackerProfileError
                ):
                    _row(class_id, level)

    def test_a_float_level_is_refused_rather_than_truncated(self):
        with self.assertRaises(
            class_attacker_profile.ClassAttackerProfileError
        ) as caught:
            _row(1, 7.0)
        self.assertEqual(
            class_attacker_profile.REFUSE_LEVEL_NOT_AN_INT,
            caught.exception.reason,
        )

    def test_a_string_class_id_is_refused_rather_than_parsed(self):
        with self.assertRaises(
            class_attacker_profile.ClassAttackerProfileError
        ) as caught:
            _row("1", 1)
        self.assertEqual(
            class_attacker_profile.REFUSE_CLASS_ID_NOT_AN_INT,
            caught.exception.reason,
        )

    def test_a_non_int_ability_str_is_refused(self):
        for bad in (7.5, "132", True, None):
            with self.subTest(bad=bad):
                with self.assertRaises(
                    class_attacker_profile.ClassAttackerProfileError
                ) as caught:
                    class_attacker_profile.profile_for_character(
                        _row(1, 1), bad
                    )
                self.assertEqual(
                    class_attacker_profile.REFUSE_ABILITY_STR_NOT_AN_INT,
                    caught.exception.reason,
                )

    def test_a_mutated_row_whose_class_id_is_not_an_int_is_refused_by_type(
        self,
    ):
        # `class_catalog.is_known_class_id("1")` answers False rather than
        # raising, so without the type re-check this row would come back
        # under the WRONG reason -- "not selectable" instead of "not an int".
        row = _row(1, 1)
        object.__setattr__(row, "class_id", "1")
        with self.assertRaises(
            class_attacker_profile.ClassAttackerProfileError
        ) as caught:
            class_attacker_profile.profile_for_character(row)
        self.assertEqual(
            class_attacker_profile.REFUSE_CLASS_ID_NOT_AN_INT,
            caught.exception.reason,
        )

    def test_a_mutated_row_whose_level_is_not_an_int_is_refused_by_type(self):
        row = _row(1, 1)
        object.__setattr__(row, "level", "1")
        with self.assertRaises(
            class_attacker_profile.ClassAttackerProfileError
        ) as caught:
            class_attacker_profile.profile_for_character(row)
        self.assertEqual(
            class_attacker_profile.REFUSE_LEVEL_NOT_AN_INT,
            caught.exception.reason,
        )

    def test_a_row_mutated_past_the_frozen_dataclass_still_refuses(self):
        # `__post_init__` validates on construction, but a frozen dataclass
        # is not tamper-proof; `profile_for_character` re-checks rather than
        # trusting the record it was handed.
        row = _row(1, 1)
        object.__setattr__(row, "class_id", 3)
        with self.assertRaises(
            class_attacker_profile.ClassAttackerProfileError
        ) as caught:
            class_attacker_profile.profile_for_character(row)
        self.assertEqual(
            class_attacker_profile.REFUSE_CLASS_ID_UNKNOWN,
            caught.exception.reason,
        )


class TheFormulaIsImportedNotCopiedTests(unittest.TestCase):
    def test_the_pinned_str_is_the_same_object_mob_combat_owns(self):
        self.assertIs(
            mob_combat.PIN_ATTACKER_ABILITY_STR,
            class_attacker_profile.ABILITY_STR_PINNED_UNTIL_RE_229_REOPENS,
        )
        self.assertIs(
            mob_combat.PIN_ATTACKER_LEVEL, class_attacker_profile.PINNED_LEVEL
        )

    def test_the_module_assigns_none_of_the_formula_constants(self):
        source = (SRC / "class_attacker_profile.py").read_text(
            encoding="utf-8"
        )
        for constant in ("ATK_BASE", "K_ATK_STR", "K_ATK_LV", "DEF_BASE",
                         "K_DEF_CON", "K_DEF_LV", "MIN_HIT"):
            with self.subTest(constant=constant):
                self.assertNotIn("%s =" % constant, source)

    def test_the_module_computes_no_damage_number(self):
        source = (SRC / "class_attacker_profile.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("resolve_damage", "damage_to_wire", "apply_hit"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


class ConsoleLinesAreAsciiAndQuotableTests(unittest.TestCase):
    def test_describe_profile_change_reports_both_sides_and_the_delta(self):
        lines = class_attacker_profile.describe_profile_change(_row(2, 1))
        self.assertEqual(3, len(lines))
        mine = class_attacker_profile.profile_for_character(_row(2, 1))
        pin = class_attacker_profile.pinned_profile()
        self.assertIn("class=Paladin", lines[0])
        self.assertIn("attack=%d" % mine.attack, lines[0])
        self.assertIn("attack=%d" % pin.attack, lines[1])
        self.assertIn("attack=%+d" % (mine.attack - pin.attack), lines[2])

    def test_every_console_line_survives_the_bridge_console(self):
        # `prompts/COMMON_LANE_ROUND.md`: anything printed to the console is
        # ASCII English only, because the bridge console is cp874.
        for line in class_attacker_profile._headless_summary():
            with self.subTest(line=line):
                line.encode("ascii")

    def test_the_summary_names_one_line_per_selectable_class(self):
        lines = class_attacker_profile._headless_summary()
        named = [line for line in lines
                 if line.startswith("CLASS_ATTACKER_PROFILE class=")]
        self.assertEqual(class_catalog.CLASS_COUNT, len(named))
        self.assertTrue(lines[-1].endswith("RESULT=ARMED"))


class CallersInSrcTokenIsMeasuredTests(unittest.TestCase):
    """The token says `callers_in_src=0`.  This measures whether that holds."""

    def _importers(self):
        found = []
        for path in sorted(SRC.glob("*.py")):
            if path.name == "class_attacker_profile.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "class_attacker_profile" in text:
                found.append(path.name)
        return found

    def test_the_token_count_matches_the_tree(self):
        importers = self._importers()
        summary = class_attacker_profile._headless_summary()[-1]
        self.assertIn("callers_in_src=%d" % len(importers), summary)

    def test_the_module_still_has_no_caller_in_src(self):
        # When this fails, the wiring the CORE-REQUEST asked for has landed.
        # Do not delete it then -- re-point it, and re-measure the token.
        self.assertEqual([], self._importers())


if __name__ == "__main__":
    unittest.main()
