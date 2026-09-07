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

    def test_levels_outside_the_combatant_range_are_refused(self):
        # RENAMED, round `b2cnxe`: the committed progression table is no
        # longer read (COO-DECISION 20260907_2050 withdrew the import), so the
        # only bound left is the combatant record's own range.  The old name
        # would have gone on claiming a table read that no longer happens.
        below = class_attacker_profile.LEVEL_MIN - 1
        above = class_attacker_profile.LEVEL_MAX + 1
        for level in (below, above, -1, 10 ** 9):
            with self.subTest(level=level):
                self.assertEqual(
                    class_attacker_profile.REFUSE_LEVEL_OFF_TABLE,
                    self._refusal(1, level).reason,
                )

    def test_a_level_the_client_table_does_not_carry_is_ACCEPTED_today(self):
        """The hole the withdrawn import leaves, pinned rather than described.

        Round `hhmvit` asserted the opposite here: a real row read refused a
        level the client's own progression table does not carry even when the
        numeric span still covered it.  `COO-DECISION 20260907_2050` withdrew
        that import (the caller retreats; only LANE-DB retires its own pin),
        so this server will now happily build an attacker at a level no
        client progression row exists for.  That is a REGRESSION in the
        module's answer, and it is pinned here in the direction it actually
        runs so that nobody reads the old test name and believes the check is
        still there.

        DELETE THIS TEST in the same commit that restores the import
        (COO-DECISION 20260907_2050 item 4) -- it is written to go red the
        moment the real check comes back, which is exactly when it should.
        """
        top = persistence_standard_status.STANDARD_STATUS_MAX_LEVEL
        off_the_table = top + 1
        self.assertLessEqual(off_the_table, class_attacker_profile.LEVEL_MAX)
        profile = class_attacker_profile.profile_for_character(
            _row(1, off_the_table)
        )
        self.assertEqual(off_the_table, profile.level)

    def test_the_withdrawn_import_is_actually_absent_from_the_source(self):
        """`grep`, not prose: the module must not import the DB scaffold.

        The pin in `tests/test_persistence_standard_status.py` greps the
        production tree for this module name and is LANE-DB's to retire.
        Round `hhmvit` kept its import and allowlisted itself inside that pin;
        this test is the other half of undoing that, and it fails from THIS
        side too, so the withdrawal cannot be quietly reverted by editing only
        LANE-DB's file.
        """
        source = Path(class_attacker_profile.__file__).read_text(
            encoding="utf-8"
        )
        self.assertNotIn("persistence_standard_status", source)

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


class TheRefusalContractDoesNotLeakTests(unittest.TestCase):
    """pf-adversary D4: an in-type but out-of-range STR used to come back as
    `mob_combat.MobCombatContractError`, a different class than the one this
    module's docstring tells callers to branch on."""

    def test_an_out_of_range_ability_str_refuses_in_this_modules_currency(
        self,
    ):
        for bad in (-1, class_attacker_profile.ABILITY_STR_MAX + 1, 131070):
            with self.subTest(bad=bad):
                with self.assertRaises(
                    class_attacker_profile.ClassAttackerProfileError
                ) as caught:
                    class_attacker_profile.profile_for_character(
                        _row(1, 7), bad
                    )
                self.assertEqual(
                    class_attacker_profile.REFUSE_ABILITY_STR_OUT_OF_RANGE,
                    caught.exception.reason,
                )

    def test_the_two_migration_str_columns_summed_are_refused_by_name(self):
        # `migrations/006` bounds `stat_str` and `bonus_str` at 65535 each,
        # so the obvious "this character's STR" reaches 131070.  That is the
        # caller the module docstring says needs no change here, so it must
        # get a named refusal rather than an uncaught foreign exception.
        with self.assertRaises(
            class_attacker_profile.ClassAttackerProfileError
        ):
            class_attacker_profile.profile_for_character(
                _row(1, 7), 65535 + 65535
            )

    def test_the_restated_bounds_still_agree_with_the_combatant_record(self):
        # The bounds are duplicated from `Combatant`; walk the real record to
        # prove the copy has not drifted, in both directions.
        mob_combat.Combatant(
            level=7,
            ability_str=class_attacker_profile.ABILITY_STR_MAX,
            ability_con=0,
        )
        with self.assertRaises(Exception):
            mob_combat.Combatant(
                level=7,
                ability_str=class_attacker_profile.ABILITY_STR_MAX + 1,
                ability_con=0,
            )

    def test_no_table_read_can_fail_because_there_is_no_table_read(self):
        # Round `hhmvit` (pf-adversary D5) pinned that an unreadable
        # progression table propagated as itself instead of being relabelled
        # "your level is outside the table".  With the import withdrawn there
        # is no read to fail, so the D5 pin is re-aimed at the fact that makes
        # it moot rather than deleted: the symbol is gone from the module.
        self.assertFalse(
            hasattr(class_attacker_profile, "standard_status_row")
        )


class TheRowCannotBeBuiltInTheWrongOrderTests(unittest.TestCase):
    """pf-adversary D6: every selectable class id is also a legal level."""

    def test_positional_construction_is_refused_outright(self):
        with self.assertRaises(TypeError):
            class_attacker_profile.CharacterBattleRow(4, 2)

    def test_every_class_id_is_also_a_legal_level(self):
        # This is WHY the row is keyword-only; if it ever stops being true
        # the reason for that decision has changed and should be re-read.
        for class_id in class_catalog.CLASS_IDS:
            with self.subTest(class_id=class_id):
                self.assertLessEqual(
                    persistence_standard_status.STANDARD_STATUS_MIN_LEVEL,
                    class_id,
                )
                self.assertLessEqual(
                    class_id,
                    persistence_standard_status.STANDARD_STATUS_MAX_LEVEL,
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
        # `rglob`, not `glob` (pf-adversary D2): the package has `gm/`,
        # `lua_api/` and `lane_hooks/` subpackages whose modules import
        # siblings routinely.  The earlier non-recursive scan let a real
        # caller land in `gm/level_command.py` with the token still reading
        # `callers_in_src=0` and every test green -- measured, not supposed.
        found = []
        for path in sorted(SRC.rglob("*.py")):
            if path.name == "class_attacker_profile.py":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "class_attacker_profile" in text:
                found.append(path.relative_to(SRC).as_posix())
        return found

    def test_the_token_count_matches_the_tree(self):
        importers = self._importers()
        summary = class_attacker_profile._headless_summary()[-1]
        # Whole-token match, not `assertIn` (pf-adversary D2): a token
        # reading `callers_in_src=12` contains the substring
        # `callers_in_src=1` and would have passed against one importer.
        self.assertIn(
            " callers_in_src=%d " % len(importers), " %s " % summary
        )

    def test_the_module_still_has_no_caller_in_src(self):
        # When this fails, the wiring the CORE-REQUEST asked for has landed.
        # Do not delete it then -- re-point it, and re-measure the token.
        self.assertEqual([], self._importers())


if __name__ == "__main__":
    unittest.main()
