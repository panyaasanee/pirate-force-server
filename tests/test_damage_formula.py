"""Tests for ``damage_formula`` -- the lane's one damage door.

Two things are pinned here that no other test file pins:

1. THE TREE HAS ONE SET OF FORMULA NUMBERS.  Five modules type a full copy of
   ``ATK_BASE`` and its neighbours today -- ``mob_combat`` plus the four in
   ``COPY_CARRIERS``, measured with the AST scan below, NOT the nine files a
   grep for those names returns (the other four mention them in prose or
   import them).  ``DamageConstantDriftTests`` reads every copy out of the
   source and fails the day one stops agreeing with ``mob_combat``'s.  It
   edits none of them -- all four belong to other lanes -- so this is a
   detector, not a refactor.
2. THE TABLE HALF IS RE-DERIVED, NEVER RESTATED.  Every number this file
   asserts about ``n_POINT_ABILITY`` is summed here, straight out of the
   committed TSV, by code that does not import the module under test.  The day
   the table changes, these go red and say which row moved.

Pure offline pytest: no network, no UI, no artifact this clone does not carry.
"""
from __future__ import annotations

import ast
import csv
import unittest
from pathlib import Path

from pirateforce_foundation import (
    damage_formula,
    mob_combat,
    persistence_standard_status,
)
from pirateforce_foundation.damage_formula import (
    AbilityPointTable,
    AbilityStrVerdict,
    DamageFormulaError,
    REFUSE_ABILITY_STR_ABOVE_CEILING,
    REFUSE_LEVEL_NOT_AN_INT,
    REFUSE_LEVEL_OFF_TABLE,
    REFUSE_STARTING_ABILITY_STR_INVALID,
    REFUSE_TABLE_UNUSABLE,
    ability_points_granted_through_level,
    ability_str_ceiling_at_level,
    attack_of,
    damage_of,
    defence_of,
    describe_pinned_attacker,
    headless_summary,
    refuse_ability_str_above_ceiling,
    verdict_for_ability_str,
)

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
TABLE_PATH = SRC_ROOT / "data" / "standard_status.tsv"
#: The modules that type their own full copy of the formula constants,
#: measured with the AST scan below at the round that wrote this file.  Three
#: of the four are other lanes' hypothesis modules and are not edited here --
#: ``mob_combat`` is LANE-B's production module and is the canonical one.
COPY_CARRIERS = (
    "src/pirateforce_foundation/damage_hp_link_hypothesis.py",
    "src/pirateforce_foundation/damage_model_hypothesis.py",
    "src/pirateforce_foundation/hostile_hp_link_hypothesis.py",
    "src/pirateforce_foundation/npc_hp_link_hypothesis.py",
)
FORMULA_NAMES = (
    "ATK_BASE",
    "K_ATK_STR",
    "K_ATK_LV",
    "DEF_BASE",
    "K_DEF_CON",
    "K_DEF_LV",
    "MIN_HIT",
)


def _points_by_level_from_the_tsv() -> dict[int, int]:
    """The n_POINT_ABILITY column, read out of the committed file itself.

    Deliberately NOT read through the module that owns the file: this test
    should still be able to say what the rows are if that module changes shape.
    ``TableIsTheOwnersTableTests`` below then ties this reading to the owner's
    own accessor, which is the check that keeps the two honest.
    """
    with TABLE_PATH.open(encoding="utf-8", newline="") as handle:
        return {
            int(row["n_ID"]): int(row["n_POINT_ABILITY"])
            for row in csv.DictReader(handle, delimiter="\t")
        }


def _table() -> AbilityPointTable:
    return AbilityPointTable(_points_by_level_from_the_tsv())


def _module_level_int_assignments(path: Path) -> dict[str, int]:
    """Module-level ``NAME = <int literal>`` bindings, read from source.

    Reading the source rather than importing keeps this test away from every
    module's import side effects -- several of the files scanned below are
    scenario-gated hypothesis modules this lane must not wake up.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(
            value.value, int
        ):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in FORMULA_NAMES:
                found[target.id] = value.value
    return found


class DamageConstantDriftTests(unittest.TestCase):
    """One set of numbers, however many files type them."""

    def _canonical(self) -> dict[str, int]:
        canonical = _module_level_int_assignments(SRC_ROOT / "mob_combat.py")
        # If the scan ever stops finding them, every comparison below would
        # pass by measuring nothing.  Assert the scan works first.
        self.assertEqual(
            sorted(canonical), sorted(FORMULA_NAMES), canonical
        )
        return canonical

    def test_every_copy_in_the_tree_agrees_with_mob_combat(self):
        canonical = self._canonical()
        scanned = 0
        carriers = []
        for path in sorted(
            list(SRC_ROOT.glob("*.py")) + list((ROOT / "tools").glob("*.py"))
        ):
            if path.name == "mob_combat.py":
                continue
            copies = _module_level_int_assignments(path)
            if not copies:
                continue
            scanned += 1
            carriers.append(path.relative_to(ROOT).as_posix())
            for name, value in sorted(copies.items()):
                self.assertEqual(
                    value, canonical[name],
                    "%s types %s = %r, mob_combat says %r -- one formula, and "
                    "these two files no longer agree on it"
                    % (path.as_posix(), name, value, canonical[name]),
                )
        # Measured, not guessed: a draft of this test asserted "at least six"
        # off a grep for the NAMES, and the grep counted files that only
        # mention them in prose or import them.  Four modules type a full copy.
        # The set is pinned rather than the count so that a rename cannot turn
        # this into a test that scans nothing and still passes.
        self.assertEqual(
            sorted(carriers), sorted(COPY_CARRIERS),
            "the set of modules typing their own copy of the formula moved; a "
            "new one should import the numbers from damage_formula (or from "
            "mob_combat) instead, and a retired one should be dropped here"
        )
        self.assertEqual(scanned, len(COPY_CARRIERS), scanned)

    def test_this_module_types_none_of_them(self):
        """The door re-exports the numbers; it must not restate them."""
        typed = _module_level_int_assignments(SRC_ROOT / "damage_formula.py")
        self.assertEqual(typed, {}, typed)

    def test_the_re_exports_are_the_same_values(self):
        canonical = self._canonical()
        for name, value in sorted(canonical.items()):
            self.assertEqual(getattr(damage_formula, name), value, name)


class AbilityPointTableTests(unittest.TestCase):
    """Sums re-derived from the committed TSV, not quoted from the module."""

    @classmethod
    def setUpClass(cls):
        cls.point_ability = _points_by_level_from_the_tsv()
        cls.table = _table()

    def _expected_through(self, level: int) -> int:
        return sum(
            points
            for row, points in self.point_ability.items()
            if row <= level
        )

    def test_the_running_sum_matches_the_table_at_every_level(self):
        for level in sorted(self.point_ability):
            with self.subTest(level=level):
                self.assertEqual(
                    ability_points_granted_through_level(self.table, level),
                    self._expected_through(level),
                )

    def test_level_one_is_granted_nothing(self):
        self.assertEqual(self.point_ability[1], 0)
        self.assertEqual(
            ability_points_granted_through_level(self.table, 1), 0
        )

    def test_the_sum_never_goes_down(self):
        previous = 0
        for level in sorted(self.point_ability):
            current = ability_points_granted_through_level(self.table, level)
            self.assertGreaterEqual(current, previous, level)
            previous = current

    def test_the_table_is_the_span_this_module_advertises(self):
        self.assertEqual(min(self.point_ability), 1)
        self.assertEqual(
            sorted(self.point_ability),
            list(range(1, max(self.point_ability) + 1)),
            "the table grew a hole; a range check is no longer a row check",
        )


class TableIsTheOwnersTableTests(unittest.TestCase):
    """The tie this module cannot make from ``src/``.

    ``damage_formula`` takes the ability-point table from its caller instead of
    importing the module that parses it: that module's OWNER pins its caller
    list over ``src/``, ``tools/``, ``current/``, ``migrations/`` and
    ``scenarios/``, and ``COO-ORDER 20260907_2050`` says a caller withdraws
    until the owner retires the pin rather than allowlisting itself into it.
    ``tests/`` is outside that scan on purpose, so the check that the numbers
    really are the committed rows lives here -- and it is a REAL row read
    against the owner's own accessor, not a range comparison.
    """

    def test_every_row_this_test_reads_is_the_row_the_owner_serves(self):
        rows = _points_by_level_from_the_tsv()
        self.assertEqual(
            sorted(rows),
            list(
                range(
                    persistence_standard_status.STANDARD_STATUS_MIN_LEVEL,
                    persistence_standard_status.STANDARD_STATUS_MAX_LEVEL + 1,
                )
            ),
        )
        for level, points in sorted(rows.items()):
            with self.subTest(level=level):
                self.assertEqual(
                    points,
                    persistence_standard_status.standard_status_row(
                        level
                    ).point_ability,
                )

    def test_a_table_built_from_the_owners_accessor_sums_the_same(self):
        owned = AbilityPointTable(
            {
                level: persistence_standard_status.standard_status_row(
                    level
                ).point_ability
                for level in range(
                    persistence_standard_status.STANDARD_STATUS_MIN_LEVEL,
                    persistence_standard_status.STANDARD_STATUS_MAX_LEVEL + 1,
                )
            }
        )
        mine = _table()
        self.assertEqual(owned.last_level, mine.last_level)
        for level in range(1, owned.last_level + 1):
            with self.subTest(level=level):
                self.assertEqual(
                    owned.granted_through(level), mine.granted_through(level)
                )


class UnusableTableTests(unittest.TestCase):
    """A table that cannot be summed is refused at construction.

    The hole case is the one that matters: a missing row silently UNDER-counts
    every ceiling above it, and an under-count refuses a character that was
    fine.  That is the expensive direction, so it fails loudly instead.
    """

    def test_a_hole_is_refused_and_named(self):
        rows = _points_by_level_from_the_tsv()
        del rows[9]
        with self.assertRaises(DamageFormulaError) as raised:
            AbilityPointTable(rows)
        self.assertEqual(raised.exception.args[0], REFUSE_TABLE_UNUSABLE)
        self.assertIn("9", raised.exception.args[1])

    def test_an_empty_table_and_a_table_that_does_not_start_at_one(self):
        for bad in ({}, {2: 0, 3: 1}):
            with self.subTest(table=bad):
                with self.assertRaises(DamageFormulaError) as raised:
                    AbilityPointTable(bad)
                self.assertEqual(
                    raised.exception.args[0], REFUSE_TABLE_UNUSABLE
                )

    def test_a_grant_that_is_not_a_count_is_refused(self):
        for bad in (-1, 1.5, "2", None, True):
            with self.subTest(points=bad):
                with self.assertRaises(DamageFormulaError) as raised:
                    AbilityPointTable({1: 0, 2: bad})
                self.assertEqual(
                    raised.exception.args[0], REFUSE_TABLE_UNUSABLE
                )


class LevelRefusalTests(unittest.TestCase):
    def setUp(self):
        self.table = _table()

    def test_off_table_levels_refuse_by_name(self):
        for bad in (0, -1, 256, 10**6):
            with self.subTest(level=bad):
                with self.assertRaises(DamageFormulaError) as raised:
                    ability_points_granted_through_level(self.table, bad)
                self.assertEqual(raised.exception.args[0], REFUSE_LEVEL_OFF_TABLE)

    def test_a_level_that_is_not_an_int_refuses_by_name(self):
        for bad in (1.0, "7", None, True):
            with self.subTest(level=bad):
                with self.assertRaises(DamageFormulaError) as raised:
                    ability_points_granted_through_level(self.table, bad)
                self.assertEqual(
                    raised.exception.args[0], REFUSE_LEVEL_NOT_AN_INT
                )

    def test_a_starting_score_that_is_not_a_count_refuses_by_name(self):
        for bad in (-1, 2.5, "8", None, False):
            with self.subTest(starting=bad):
                with self.assertRaises(DamageFormulaError) as raised:
                    ability_str_ceiling_at_level(
                        self.table, 7, starting_ability_str=bad
                    )
                self.assertEqual(
                    raised.exception.args[0],
                    REFUSE_STARTING_ABILITY_STR_INVALID,
                )


class CeilingTests(unittest.TestCase):
    def setUp(self):
        self.table = _table()

    def test_the_ceiling_is_the_start_plus_what_the_table_granted(self):
        for level, start in ((1, 0), (7, 20), (25, 0), (100, 5), (255, 99)):
            with self.subTest(level=level, start=start):
                self.assertEqual(
                    ability_str_ceiling_at_level(
                        self.table, level, starting_ability_str=start
                    ),
                    start
                    + ability_points_granted_through_level(self.table, level),
                )

    def test_a_value_inside_the_ceiling_is_accepted_and_reports_no_gap(self):
        verdict = refuse_ability_str_above_ceiling(
            self.table, 7, 20, starting_ability_str=20
        )
        self.assertIsInstance(verdict, AbilityStrVerdict)
        self.assertTrue(verdict.within_the_table)
        self.assertEqual(verdict.unaccounted_for, 0)

    def test_a_value_past_the_ceiling_refuses_and_names_the_gap(self):
        ceiling = ability_str_ceiling_at_level(
            self.table, 7, starting_ability_str=0
        )
        with self.assertRaises(DamageFormulaError) as raised:
            refuse_ability_str_above_ceiling(
                self.table, 7, ceiling + 1, starting_ability_str=0
            )
        self.assertEqual(
            raised.exception.args[0], REFUSE_ABILITY_STR_ABOVE_CEILING
        )
        self.assertIn("1 above the ceiling", raised.exception.args[1])

    def test_the_verdict_form_does_not_raise_on_a_value_past_the_ceiling(self):
        verdict = verdict_for_ability_str(
            self.table, 7, 10_000, starting_ability_str=0
        )
        self.assertFalse(verdict.within_the_table)
        self.assertEqual(
            verdict.unaccounted_for,
            10_000
            - ability_str_ceiling_at_level(
                self.table, 7, starting_ability_str=0
            ),
        )


class PinnedAttackerTests(unittest.TestCase):
    """What the table says about the profile every player swings as today."""

    def setUp(self):
        self.table = _table()

    def test_the_gap_is_measured_from_the_table_and_from_the_pin(self):
        verdict = describe_pinned_attacker(self.table)
        self.assertEqual(verdict.level, mob_combat.PIN_ATTACKER_LEVEL)
        self.assertEqual(
            verdict.ability_str, mob_combat.PIN_ATTACKER_ABILITY_STR
        )
        self.assertEqual(
            verdict.granted_points,
            ability_points_granted_through_level(
                self.table, mob_combat.PIN_ATTACKER_LEVEL
            ),
        )
        # The pin is one of this project's own numbers, so it is NOT a sum of
        # this table's grants and the gap is expected.  Pinned as a
        # measurement: the day either side moves, this says so.
        self.assertFalse(verdict.within_the_table)
        self.assertEqual(
            verdict.unaccounted_for,
            mob_combat.PIN_ATTACKER_ABILITY_STR
            - ability_points_granted_through_level(
                self.table, mob_combat.PIN_ATTACKER_LEVEL
            ),
        )


class OneFormulaManyCallersTests(unittest.TestCase):
    def test_the_door_returns_exactly_what_mob_combat_resolves(self):
        for level in (1, 7, 25, 100):
            for ability_str in (0, 12, 132):
                for ability_con in (0, 22, 300):
                    attacker = mob_combat.Combatant(
                        level=level, ability_str=ability_str, ability_con=0
                    )
                    defender = mob_combat.Combatant(
                        level=level, ability_str=0, ability_con=ability_con
                    )
                    with self.subTest(
                        level=level, s=ability_str, c=ability_con
                    ):
                        self.assertEqual(
                            damage_of(attacker, defender),
                            mob_combat.resolve_damage(attacker, defender),
                        )
                        self.assertEqual(attack_of(attacker), attacker.attack)
                        self.assertEqual(defence_of(defender), defender.defence)

    def test_the_number_an_owner_photographed_comes_back_through_this_door(self):
        """891, the Training Iron Man hit GT-274/R322C watched on a screen.

        Not a new pin -- three test files already guard it -- but the door has
        to reproduce it, or "one formula" is not true of this module.
        """
        attacker = mob_combat.pin_attacker()
        dummy = mob_combat.Combatant(
            level=100, ability_str=0, ability_con=mob_combat.MOB_ABILITY_CON
        )
        self.assertEqual(damage_of(attacker, dummy), 891)

    def test_the_floor_holds(self):
        weak = mob_combat.Combatant(level=1, ability_str=0, ability_con=0)
        wall = mob_combat.Combatant(level=255, ability_str=0, ability_con=99999)
        self.assertEqual(damage_of(weak, wall), mob_combat.MIN_HIT)


class HeadlessTokenTests(unittest.TestCase):
    def setUp(self):
        self.table = _table()

    def test_the_token_survives_the_bridge_console(self):
        line = headless_summary(self.table)
        self.assertEqual(len(line.splitlines()), 1)
        line.encode("ascii")
        line.encode("cp874")
        self.assertTrue(line.startswith("DAMAGE_FORMULA "))

    def test_the_token_carries_the_measured_numbers_not_typed_ones(self):
        verdict = describe_pinned_attacker(self.table)
        line = headless_summary(self.table)
        self.assertIn("granted_points=%d" % verdict.granted_points, line)
        self.assertIn("unaccounted=%d" % verdict.unaccounted_for, line)


class NoProductionCallerYetTests(unittest.TestCase):
    """Says out loud that nothing swings through this door yet.

    The module's docstring claims it: this turns the claim into something that
    goes red the day it stops being true, so the round that wires it cannot
    leave a stale nonclaim behind.
    """

    def test_no_module_in_src_imports_this_one(self):
        importers = []
        for path in sorted(SRC_ROOT.rglob("*.py")):
            if path.name == "damage_formula.py":
                continue
            text = path.read_text(encoding="utf-8")
            if (
                "from .damage_formula import" in text
                or "from . import damage_formula" in text
                or "import damage_formula" in text
            ):
                importers.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(
            importers, [],
            "damage_formula has a caller now -- update the module's nonclaim "
            "and this test together, in the round that wired it",
        )


if __name__ == "__main__":
    unittest.main()
