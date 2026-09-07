"""LANE-CS: the level-half projection for CORE-REQUEST row 032.

Read `src/pirateforce_foundation/damage_level_projection.py`'s docstring
first.  Every number this file asserts is DERIVED here from the same shipped
sources the module reads -- the formula constants in `mob_combat`, the pinned
attacker, and the practice-dummy row out of the shipped roster.  Nothing is
transcribed, so moving any of those three makes this file go red instead of
letting a stale projection ship to chief as if it were still true.
"""

import math
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import damage_level_projection as projection
from pirateforce_foundation import damage_town_target
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_combat


def town_target_mob():
    """The first shipped Training Iron Man row, same selection the R322C pin
    test makes -- see `tests/test_damage_town_target.py`."""
    rows = sorted(
        (mob for mob in field_mobs.load_roster()
         if mob.template_id == field_mobs.TOWN_TARGET_N_ID),
        key=lambda mob: mob.placement_index,
    )
    assert rows, "the default roster ships no Training Iron Man"
    return rows[0]


class TheProjectionIsAnchoredToTheShippedPin(unittest.TestCase):
    """The one row that must already be true today."""

    def test_the_pin_level_reproduces_the_shipped_pinned_hit(self):
        mob = town_target_mob()
        self.assertEqual(
            projection.production_pin_row(mob).damage_per_hit,
            damage_town_target.unclamped_hit_damage(
                mob_combat.pin_attacker(), mob),
        )

    def test_the_pin_level_row_reproduces_the_observed_r322c_number(self):
        # Not a second copy of the observation: it is read off the module
        # that owns it, so a corrected observation moves both together.
        mob = town_target_mob()
        self.assertEqual(
            projection.production_pin_row(mob).damage_per_hit,
            damage_town_target.R322C_OBSERVED_DAMAGE_PER_HIT,
        )

    def test_the_pin_row_is_the_pin_level(self):
        mob = town_target_mob()
        self.assertEqual(
            projection.production_pin_row(mob).level,
            mob_combat.PIN_ATTACKER_LEVEL,
        )


class OnlyTheLevelMoves(unittest.TestCase):
    """The module's central claim, checked mechanically."""

    def test_a_projected_attacker_differs_from_the_pin_in_level_alone(self):
        pin = mob_combat.pin_attacker()
        moved = projection.attacker_at_level(pin.level + 1)
        self.assertEqual(moved.level, pin.level + 1)
        self.assertEqual(moved.ability_str, pin.ability_str)
        self.assertEqual(moved.ability_con, pin.ability_con)

    def test_the_guard_refuses_an_attacker_that_moved_strength_too(self):
        pin = mob_combat.pin_attacker()
        cheat = mob_combat.Combatant(
            level=pin.level,
            ability_str=pin.ability_str + 1,
            ability_con=pin.ability_con,
        )
        with self.assertRaises(projection.LevelProjectionError):
            projection.require_only_level_differs(cheat)

    def test_the_guard_accepts_every_level_the_projection_offers(self):
        for level in (1, mob_combat.PIN_ATTACKER_LEVEL, 50, 100):
            projection.require_only_level_differs(
                projection.attacker_at_level(level))

    def test_the_guard_refuses_something_that_is_not_a_combatant(self):
        with self.assertRaises(projection.LevelProjectionError):
            projection.require_only_level_differs(
                {"level": 7, "ability_str": 132, "ability_con": 0})


class TheNumbersAreTheFormulaAndNotATable(unittest.TestCase):
    """Every projected number re-derived from the shipped constants."""

    def expected_damage(self, level, mob):
        attack = (mob_combat.ATK_BASE
                  + mob_combat.K_ATK_STR * mob_combat.PIN_ATTACKER_ABILITY_STR
                  + mob_combat.K_ATK_LV * level)
        defence = (mob_combat.DEF_BASE
                   + mob_combat.K_DEF_CON * mob_combat.MOB_ABILITY_CON
                   + mob_combat.K_DEF_LV * mob.level)
        return max(mob_combat.MIN_HIT, attack - defence)

    def test_damage_matches_the_formula_across_the_useful_band(self):
        mob = town_target_mob()
        for level in range(1, 121):
            self.assertEqual(
                projection.damage_at_level(level, mob),
                self.expected_damage(level, mob),
                "level %d" % level,
            )

    def test_hits_match_the_ceiling_of_the_room_over_the_damage(self):
        mob = town_target_mob()
        room = int(mob.max_hp) - mob_combat.HP_FLOOR
        for level in (1, mob_combat.PIN_ATTACKER_LEVEL, 25, 60, 100):
            self.assertEqual(
                projection.hits_to_fell_at_level(level, mob),
                math.ceil(room / self.expected_damage(level, mob)),
                "level %d" % level,
            )

    def test_the_hit_count_agrees_with_walking_the_ladder_one_hit_at_a_time(self):
        """The ceiling is arithmetic; this is the same answer measured.

        `damage_town_target.hp_after_hits` applies the real per-hit clamp, so
        this also proves the clamp on the final swing does not change the
        COUNT -- the one thing the ceiling could have got wrong.
        """
        mob = town_target_mob()
        for level in (1, mob_combat.PIN_ATTACKER_LEVEL, 100):
            hits = projection.hits_to_fell_at_level(level, mob)
            attacker = projection.attacker_at_level(level)
            self.assertEqual(
                damage_town_target.hp_after_hits(
                    attacker, mob, int(mob.max_hp), hits),
                mob_combat.HP_FLOOR,
                "level %d does not fell it in %d hits" % (level, hits),
            )
            self.assertGreater(
                damage_town_target.hp_after_hits(
                    attacker, mob, int(mob.max_hp), hits - 1),
                mob_combat.HP_FLOOR,
                "level %d fells it in fewer than %d hits" % (level, hits),
            )

    def test_damage_rises_with_level_and_hits_never_rise(self):
        mob = town_target_mob()
        rows = projection.project_levels(mob, range(1, 101))
        for earlier, later in zip(rows, rows[1:]):
            self.assertGreater(later.damage_per_hit, earlier.damage_per_hit)
            self.assertLessEqual(later.hits_to_fell, earlier.hits_to_fell)

    def test_the_module_types_none_of_the_numbers_it_reports(self):
        """The projection may not carry a damage, hit count or ability number
        of its own: every one has to come out of `mob_combat` at call time.

        Measured over the integers the module's own source actually
        evaluates, parsed rather than grepped -- the same lesson round
        `z8o8ma` paid for when a string search could not tell a typed id
        apart from a digit inside a sha.
        """
        import ast

        source = pathlib.Path(projection.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        literals = {
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and type(node.value) is int
        }
        mob = town_target_mob()
        forbidden = {
            mob_combat.ATK_BASE, mob_combat.K_ATK_STR, mob_combat.K_ATK_LV,
            mob_combat.DEF_BASE, mob_combat.K_DEF_CON, mob_combat.K_DEF_LV,
            mob_combat.PIN_ATTACKER_LEVEL,
            mob_combat.PIN_ATTACKER_ABILITY_STR,
            mob_combat.MOB_ABILITY_CON,
            int(mob.max_hp),
            damage_town_target.R322C_OBSERVED_DAMAGE_PER_HIT,
        }
        # 0 and 1 are ordinary program arithmetic (a negation, an index) and
        # are not any of the numbers above unless one of them IS 0 or 1, in
        # which case the module genuinely must not type it.
        self.assertEqual(sorted(literals & forbidden), [],
                         "the projection types a number it must derive")


class TheNumberReallyComesOutOfTheFormula(unittest.TestCase):
    """Monkeypatch pins, not text pins.

    An earlier draft of this file checked the module's AST for typed numbers
    and checked the arithmetic against the same constants the module reads.
    Both are necessary and neither is sufficient: a mutant that keeps the
    imports, keeps consuming `mob`, keeps calling the guard, and then
    returns `870 + level + level + level` types no forbidden literal, agrees
    with the derivation, and passed every test in this file.  That is the
    same defect `pf-adversary` found in round `z8o8ma` (A4) -- "computed,
    not transcribed" is only a real claim if removing the computation goes
    red.  These tests remove it.
    """

    def test_the_damage_is_whatever_the_shipped_formula_says_it_is(self):
        mob = town_target_mob()
        sentinel = 424242
        original = damage_town_target.unclamped_hit_damage
        try:
            damage_town_target.unclamped_hit_damage = (
                lambda attacker, target: sentinel)
            self.assertEqual(projection.damage_at_level(1, mob), sentinel)
        finally:
            damage_town_target.unclamped_hit_damage = original

    def test_the_hit_count_is_computed_from_that_same_damage(self):
        mob = town_target_mob()
        original = damage_town_target.unclamped_hit_damage
        try:
            damage_town_target.unclamped_hit_damage = (
                lambda attacker, target: 1)
            self.assertEqual(
                projection.hits_to_fell_at_level(1, mob),
                int(mob.max_hp) - mob_combat.HP_FLOOR,
            )
        finally:
            damage_town_target.unclamped_hit_damage = original

    def test_the_attacker_handed_to_the_formula_carries_the_asked_level(self):
        mob = town_target_mob()
        seen = []
        original = damage_town_target.unclamped_hit_damage
        try:
            damage_town_target.unclamped_hit_damage = (
                lambda attacker, target: seen.append((attacker, target)) or 1)
            projection.damage_at_level(42, mob)
        finally:
            damage_town_target.unclamped_hit_damage = original
        self.assertEqual(len(seen), 1)
        attacker, target = seen[0]
        self.assertEqual(attacker.level, 42)
        self.assertIs(target, mob)

    def test_the_guard_is_on_the_path_and_not_merely_exported(self):
        """Removing `require_only_level_differs` from `damage_at_level` used
        to change nothing measurable.  Now it does."""
        mob = town_target_mob()
        original = projection.require_only_level_differs
        marker = projection.LevelProjectionError("guard reached")

        def refuse(projected):
            raise marker

        try:
            projection.require_only_level_differs = refuse
            with self.assertRaises(projection.LevelProjectionError) as caught:
                projection.damage_at_level(1, mob)
            self.assertIs(caught.exception, marker)
        finally:
            projection.require_only_level_differs = original


class TheGuardLooksAtEveryFieldAndNotOne(unittest.TestCase):
    """`require_only_level_differs` claims to walk `dataclasses.fields`.  A
    guard that only ever inspected `ability_str` passed every other test
    here, so the claim needs a field it would have to have walked to see."""

    def test_a_moved_ability_con_is_refused_too(self):
        pin = mob_combat.pin_attacker()
        cheat = mob_combat.Combatant(
            level=pin.level,
            ability_str=pin.ability_str,
            ability_con=pin.ability_con + 1,
        )
        with self.assertRaises(projection.LevelProjectionError):
            projection.require_only_level_differs(cheat)

    def test_every_non_level_field_of_the_pin_is_actually_compared(self):
        """One subtest per field, so a guard that skips any one of them goes
        red naming that field rather than passing quietly."""
        import dataclasses as _dc

        pin = mob_combat.pin_attacker()
        for field in _dc.fields(pin):
            if field.name == "level":
                continue
            with self.subTest(field=field.name):
                moved = _dc.replace(
                    pin, **{field.name: getattr(pin, field.name) + 1})
                with self.assertRaises(projection.LevelProjectionError):
                    projection.require_only_level_differs(moved)


class ItRefusesRatherThanGuesses(unittest.TestCase):

    def test_a_level_the_shipped_record_refuses_is_refused_here(self):
        for bad in (0, -1, 100000):
            with self.assertRaises(projection.LevelProjectionError):
                projection.attacker_at_level(bad)

    def test_a_level_that_is_not_an_int_is_refused(self):
        for bad in (7.0, "7", True, None):
            with self.assertRaises(projection.LevelProjectionError):
                projection.attacker_at_level(bad)

    def test_an_empty_level_request_is_refused_not_answered(self):
        with self.assertRaises(projection.LevelProjectionError):
            projection.project_levels(town_target_mob(), ())

    def test_a_mob_that_is_not_the_typed_record_is_refused(self):
        with self.assertRaises(Exception):
            projection.damage_at_level(1, object())


class TheTableKeepsTheOrderItWasAsked(unittest.TestCase):

    def test_rows_come_back_in_the_order_given(self):
        mob = town_target_mob()
        wanted = (100, 1, 7)
        rows = projection.project_levels(mob, wanted)
        self.assertEqual(tuple(row.level for row in rows), wanted)


if __name__ == "__main__":
    unittest.main()
