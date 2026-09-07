"""LANE-CS: the level-half projection for CORE-REQUEST row 032.

Read `src/pirateforce_foundation/damage_level_projection.py`'s docstring
first.  Almost every number this file asserts is DERIVED here from the same
shipped sources the module reads -- the formula constants in `mob_combat`, the
pinned attacker, and the practice-dummy row out of the shipped roster.

THE EXCEPTIONS, NAMED, BECAUSE AN EARLIER VERSION OF THIS PARAGRAPH SAID
"every" AND WAS WRONG.  `TheDummyItselfIsPinnedHere` transcribes the dummy's
`max_hp`, `level` and `template_id`, and `TheColumnThatWentToChiefIsPinned`
transcribes the eleven numbers that were actually sent.  Both are transcribed
ON PURPOSE, and the first one is a fix, not an oversight: the hit-count
assertions have `mob.max_hp` on BOTH sides, so before this pin existed,
moving `max_hp` from 198125 to 99999 left this file reporting green with every
hit count in it silently wrong.  A derivation cannot anchor itself; one end of
it has to be nailed to something that does not move when the source does.
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


# The one number in this file that is TRANSCRIBED rather than derived, and
# the reason the rest of the file means anything.  See the module docstring:
# the hit-count assertions read `mob.max_hp` on both sides, so without an
# anchor that does not move with the roster, every one of them is a tautology.
# Provenance: the shipped roster row for template 916, the same value
# `tests/test_mob_combat.py` pins at `assertEqual(mob.max_hp, 198125)`.
PINNED_DUMMY_MAX_HP = 198125
PINNED_DUMMY_LEVEL = 100
PINNED_DUMMY_TEMPLATE_ID = 916


def _combatant_max_level():
    """The highest level the shipped `Combatant` accepts, MEASURED.

    Probed rather than typed, so the sweeps below follow the record instead
    of a constant in this file drifting away from it.  Doubling probe, then a
    binary search on the boundary: no bound of `Combatant` is copied here.
    """
    def accepted(level):
        try:
            mob_combat.Combatant(level=level, ability_str=0, ability_con=0)
        except Exception:
            return False
        return True

    assert accepted(1), "the shipped Combatant refuses level 1"
    high = 1
    while accepted(high * 2):
        high *= 2
        assert high < 1 << 30, "Combatant appears to accept any level at all"
    low, high = high, high * 2          # low accepted, high refused
    while high - low > 1:
        mid = (low + high) // 2
        if accepted(mid):
            low = mid
        else:
            high = mid
    return low


COMBATANT_MAX_LEVEL = _combatant_max_level()


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

    def test_damage_matches_the_formula_across_every_level_it_answers_for(self):
        """The band swept is the band the module ANSWERS for, not a band
        chosen for looking useful.

        The earlier version stopped at 120 while `attacker_at_level` happily
        answered up to `COMBATANT_MAX_LEVEL`, so levels 121..1000 carried no
        assertion at all and a special case parked in there was invisible.
        """
        mob = town_target_mob()
        for level in range(1, COMBATANT_MAX_LEVEL + 1):
            self.assertEqual(
                projection.damage_at_level(level, mob),
                self.expected_damage(level, mob),
                "level %d" % level,
            )

    def test_hits_match_the_ceiling_of_the_room_over_the_damage(self):
        """Swept over the same full band, for the same reason: the hit count
        used to be checked at five levels out of a thousand."""
        mob = town_target_mob()
        room = PINNED_DUMMY_MAX_HP - mob_combat.HP_FLOOR
        for level in range(1, COMBATANT_MAX_LEVEL + 1):
            self.assertEqual(
                projection.hits_to_fell_at_level(level, mob),
                math.ceil(room / self.expected_damage(level, mob)),
                "level %d" % level,
            )

    def test_the_projection_answers_for_the_whole_band_and_refuses_outside_it(self):
        """The sweeps above are only worth their runtime if the band they
        sweep really is the band the module accepts."""
        mob = town_target_mob()
        self.assertIsInstance(
            projection.damage_at_level(COMBATANT_MAX_LEVEL, mob), int)
        with self.assertRaises(projection.LevelOutOfRangeError):
            projection.attacker_at_level(COMBATANT_MAX_LEVEL + 1)

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


class TheDummyItselfIsPinnedHere(unittest.TestCase):
    """The anchor.  Without this class the hit-count column is a tautology.

    `hits_to_fell_at_level` divides by a damage the file derives, but the
    numerator is `mob.max_hp` -- read from the roster on BOTH sides of every
    hit assertion.  Moving 198125 to 99999 in the roster left this file at 23
    passed with every hit count in it wrong.  These three assertions are the
    end of the derivation that is nailed down.
    """

    def test_the_dummys_ceiling_is_the_number_the_hit_column_divides(self):
        self.assertEqual(int(town_target_mob().max_hp), PINNED_DUMMY_MAX_HP)

    def test_the_dummy_is_the_level_the_defence_half_reads(self):
        self.assertEqual(town_target_mob().level, PINNED_DUMMY_LEVEL)

    def test_the_row_under_test_is_the_training_iron_man(self):
        self.assertEqual(
            town_target_mob().template_id, PINNED_DUMMY_TEMPLATE_ID)
        self.assertEqual(field_mobs.TOWN_TARGET_N_ID, PINNED_DUMMY_TEMPLATE_ID)


class TheColumnThatWentToChiefIsPinned(unittest.TestCase):
    """The eleven numbers that left this lane in a letter.

    Deliberately transcribed: derived numbers cannot catch a letter that
    reported something the code never said.  If the shipped sources move,
    these go red and the letter has to be corrected -- which is the point.
    Rows are (level, damage per hit, hits to fell).
    """

    REPORTED = (
        (1, 873, 227),
        (7, 891, 223),
        (25, 945, 210),
        (40, 990, 201),
        (60, 1050, 189),
        (100, 1170, 170),
    )

    def test_every_row_reported_to_chief_is_what_the_module_answers(self):
        mob = town_target_mob()
        for level, damage, hits in self.REPORTED:
            with self.subTest(level=level):
                row = projection.project_levels(mob, (level,))[0]
                self.assertEqual(row.damage_per_hit, damage)
                self.assertEqual(row.hits_to_fell, hits)


class TheTwoRefusalsHaveDifferentNames(unittest.TestCase):
    """A level `Combatant` refuses is not the same event as a pin that will
    not rebuild, and reporting both with one sentence hid the second one
    behind a true-sounding statement about the first."""

    def test_a_level_outside_the_record_is_a_level_error(self):
        with self.assertRaises(projection.LevelOutOfRangeError):
            projection.attacker_at_level(COMBATANT_MAX_LEVEL + 1)

    def test_a_pin_that_will_not_rebuild_does_not_blame_the_level(self):
        original = mob_combat.pin_attacker
        try:
            mob_combat.pin_attacker = lambda: object()
            with self.assertRaises(projection.PinWillNotAssembleError) as caught:
                projection.attacker_at_level(7)
        finally:
            mob_combat.pin_attacker = original
        self.assertNotIsInstance(
            caught.exception, projection.LevelOutOfRangeError)
        self.assertIn("is not what failed", str(caught.exception))

    def test_both_are_still_catchable_as_the_base_refusal(self):
        for raiser in (
            lambda: projection.attacker_at_level(COMBATANT_MAX_LEVEL + 1),
            lambda: projection.attacker_at_level("7"),
        ):
            with self.assertRaises(projection.LevelProjectionError):
                raiser()


class TheGuardsBlindSpotIsReportedAndEmpty(unittest.TestCase):
    """`require_only_level_differs` cannot vouch for a value derived from
    `level`.  It says so instead of either lying or dying."""

    def test_the_shipped_record_has_nothing_the_guard_cannot_check(self):
        self.assertEqual(projection.unchecked_attributes(), ())

    def test_a_derived_column_is_reported_by_name_not_silently_skipped(self):
        import dataclasses as _dc

        @_dc.dataclass(frozen=True)
        class WithDerived:
            level: int
            ability_str: int
            ability_con: int
            twice_level: int = _dc.field(init=False, default=0)

        sample = WithDerived(level=7, ability_str=132, ability_con=0)
        self.assertEqual(
            projection.unchecked_attributes(sample), ("twice_level",))

    def test_post_init_state_the_fields_api_cannot_see_is_reported_too(self):
        import dataclasses as _dc

        @_dc.dataclass
        class WithHiddenState:
            level: int

            def __post_init__(self):
                self.cached_attack = self.level * 3

        sample = WithHiddenState(level=7)
        self.assertEqual(
            projection.unchecked_attributes(sample), ("cached_attack",))

    def test_the_guard_still_refuses_a_field_it_can_check(self):
        pin = mob_combat.pin_attacker()
        cheat = mob_combat.Combatant(
            level=pin.level,
            ability_str=pin.ability_str,
            ability_con=pin.ability_con + 1,
        )
        with self.assertRaises(projection.LevelProjectionError):
            projection.require_only_level_differs(cheat)


if __name__ == "__main__":
    unittest.main()
