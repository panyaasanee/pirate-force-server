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

import ast
import collections.abc
import dataclasses
import math
import pathlib
import re
import sys
import types
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


# How far up this file probes for the accepted band.  This is NOT a copy of
# `Combatant`'s bound: `_combatant_max_level` asserts the top of this span is
# REFUSED, so a record that grows past it turns this file red asking to be
# widened instead of quietly measuring the wrong ceiling.
LEVEL_PROBE_SPAN = 4096



class _ASetSubclass(collections.abc.Set):
    """An unordered container the type blacklist never listed (D6)."""

    def __init__(self, values):
        self._values = frozenset(values)

    def __contains__(self, value):
        return value in self._values

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)


def _ABOVE_CEILING_PROBES(ceiling):
    """Sampled levels above `ceiling`, spread over decades -- see step 3."""
    return (ceiling + 1, 2 * ceiling, 5 * ceiling, 10 * ceiling,
            100 * ceiling, 1000 * ceiling, 2 ** 31 - 1)


def _declared_level_bounds():
    """The `[minimum, maximum]` `Combatant.__post_init__` declares for `level`.

    Read out of the shipped source with `ast` rather than out of a refusal
    message, because a message is formatted by the same code that would have
    to be wrong for this to matter.  The body is required to be nothing but
    `_require_int` calls so that "this call is the accepted set" is a checked
    statement and not an assumption -- see :func:`_combatant_max_level` step 1.
    """
    source = (ROOT / "src" / "pirateforce_foundation" / "mob_combat.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    post_init = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Combatant":
            for item in node.body:
                if (isinstance(item, ast.FunctionDef)
                        and item.name == "__post_init__"):
                    post_init = item
    assert post_init is not None, (
        "`Combatant.__post_init__` is not in the shipped source; this file "
        "reads the level gate out of it")
    found = []
    for statement in post_init.body:
        assert isinstance(statement, ast.Expr), (
            "`Combatant.__post_init__` gained a statement that is not a bare "
            "call (%s).  This file asserts the level gate is one "
            "`_require_int` call; a second gate would make every sweep here "
            "cover a subset of what the record accepts." % (
                type(statement).__name__,))
        call = statement.value
        assert (isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "_require_int"), (
            "`Combatant.__post_init__` calls something other than "
            "`_require_int`; see the assertion above for why that matters")
        target = call.args[0]
        if (isinstance(target, ast.Attribute) and target.attr == "level"):
            bounds = call.args[2], call.args[3]
            for bound in bounds:
                assert isinstance(bound, ast.Constant) and isinstance(
                    bound.value, int), (
                    "the level bounds in `Combatant.__post_init__` are not "
                    "plain int literals any more; this file cannot read them")
            found.append((bounds[0].value, bounds[1].value))
    assert len(found) == 1, (
        "`Combatant.__post_init__` has %d range checks on `level`, not one; "
        "the accepted set is no longer a single interval" % (len(found),))
    return found[0]


def _combatant_max_level():
    """The highest level the shipped `Combatant` accepts, MEASURED.

    T1-B, AND WHY THIS IS A SCAN AND NOT A BINARY SEARCH.  The previous
    version doubled to the first refusal and then bisected, which measures
    "the top of the first contiguous accepted run" -- not the ceiling.
    Measured, not argued: with `Combatant.__post_init__` patched to reject
    `100 < level < 200`, that version returned 100 while the record still
    accepted up to 1000, every sweep below silently stopped at 100, and the
    FULL SUITE STAYED GREEN.  Levels 200..1000 had nothing asserting anything
    about them while a test class named for sweeping them reported success.

    A ceiling can only be measured by a search that does not assume the
    accepted set is an interval -- so this walks every level in the probe span
    and then asserts the shape it was assuming: `[1, N]` with no holes.  Cheap
    at this size (a `Combatant` is three range checks), and the assertion is
    what makes the returned number mean "ceiling" rather than "first gap".

    D5, AND THE SCAN ALONE DID NOT CLOSE IT.  Adversary showed the scan
    version still measuring 1000 and the full suite still green with
    `Combatant.__post_init__` patched to accept `[1, 1000] u [5000, 6000]`:
    the second band sits ABOVE `LEVEL_PROBE_SPAN`, so `max(band)` never sees
    it, the holes check only looks inside `[1, top]`, and `top <
    LEVEL_PROBE_SPAN` reads as "the ceiling is inside the span" when what it
    actually says is "nothing in the span above `top` is accepted".  No
    amount of probing a bounded window can rule out an island outside it, so
    this stops probing for the answer and asks the record where its gate is:

      1. READ THE GATE.  `Combatant.__post_init__` is parsed out of the
         shipped source and its body is required to be nothing but
         `_require_int` calls, exactly one of which is about `level`, with
         both bounds as plain int literals.  That call IS the accepted set --
         `_require_int` refuses everything outside `[minimum, maximum]` --
         so an island can only exist if the body is not that shape, which is
         the assertion that fires.
      2. CONFIRM IT BY MEASUREMENT.  `lo - 1` and `hi + 1` refused, `lo` and
         `hi` accepted, and no holes anywhere in `[lo, hi]`.  A declaration
         nothing checks is a comment; a measurement with no declaration
         cannot see past its own window.  Both, or neither means anything.
      3. SAMPLE ABOVE IT.  Decades above `hi` are asserted refused, which is
         the cheap net for a gate that passes step 1 but is monkeypatched at
         run time -- the exact shape adversary used.  `5 * hi` catches the
         `[5000, 6000]` island on today's bounds.

    NONCLAIM: step 3 is a sample, not a proof.  An island that clears every
    sampled point AND leaves the source shape in step 1 untouched would still
    pass, and there is no way to rule that out from a test.  What the three
    steps together buy is that such an island can no longer be built by
    monkeypatching `__post_init__` (step 1 or 3 fires) or by editing the
    range check in place (step 1 fires).
    """
    def accepted(level):
        try:
            mob_combat.Combatant(level=level, ability_str=0, ability_con=0)
        except Exception:
            return False
        return True

    lo, hi = _declared_level_bounds()
    assert accepted(lo), (
        "`Combatant.__post_init__` declares levels [%d, %d] but refuses its "
        "own lower bound %d" % (lo, hi, lo))
    assert accepted(hi), (
        "`Combatant.__post_init__` declares levels [%d, %d] but refuses its "
        "own upper bound %d" % (lo, hi, hi))
    assert not accepted(lo - 1), (
        "`Combatant` declares [%d, %d] and still accepts %d; the declared "
        "gate is not the gate" % (lo, hi, lo - 1))
    assert not accepted(hi + 1), (
        "`Combatant` declares [%d, %d] and still accepts %d; the declared "
        "gate is not the gate" % (lo, hi, hi + 1))
    assert hi <= LEVEL_PROBE_SPAN, (
        "the shipped Combatant declares a ceiling of %d, above this file's "
        "probe span; widen LEVEL_PROBE_SPAN" % (hi,))
    band = frozenset(l for l in range(lo, hi + 1) if accepted(l))
    holes = sorted(set(range(lo, hi + 1)) - band)
    assert not holes, (
        "the shipped Combatant's accepted levels are not the interval [%d, "
        "%d]: it refuses %r (first %d shown).  Every sweep in this file "
        "assumes an interval; fix the sweeps, do not delete this assertion."
        % (lo, hi, holes[:8], min(len(holes), 8)))
    islands = [probe for probe in _ABOVE_CEILING_PROBES(hi) if accepted(probe)]
    assert not islands, (
        "the shipped Combatant declares a ceiling of %d and still accepts %r;"
        " an accepted level above the declared gate means every sweep in this"
        " file covers a subset of what the record takes" % (hi, islands))
    assert lo == 1, (
        "this file's sweeps start at 1; the shipped Combatant's floor is %d"
        % (lo,))
    return hi


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
            projection.production_pin_row(mob).unclamped_damage_per_hit,
            damage_town_target.unclamped_hit_damage(
                mob_combat.pin_attacker(), mob),
        )

    def test_the_pin_level_row_reproduces_the_observed_r322c_number(self):
        # Not a second copy of the observation: it is read off the module
        # that owns it, so a corrected observation moves both together.
        mob = town_target_mob()
        self.assertEqual(
            projection.production_pin_row(mob).unclamped_damage_per_hit,
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
            self.assertGreater(
                later.unclamped_damage_per_hit,
                earlier.unclamped_damage_per_hit)
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
    Rows are (level, UNCLAMPED damage per hit, hits to fell, what the LAST
    swing prints).  The fourth column is transcribed for the same reason as
    the other three, and it is the column the letter did not have: the letter
    said "223 hits of 891" where the 223rd hit prints 323.
    """

    REPORTED = (
        (1, 873, 227, 827),
        (7, 891, 223, 323),
        (25, 945, 210, 620),
        (40, 990, 201, 125),
        (60, 1050, 189, 725),
        (100, 1170, 170, 395),
    )

    def test_every_row_reported_to_chief_is_what_the_module_answers(self):
        mob = town_target_mob()
        for level, damage, hits, final in self.REPORTED:
            with self.subTest(level=level):
                row = projection.project_levels(mob, (level,))[0]
                self.assertEqual(row.unclamped_damage_per_hit, damage)
                self.assertEqual(row.hits_to_fell, hits)
                self.assertEqual(row.final_hit_damage, final)

    def test_no_reported_row_prints_its_own_damage_on_the_last_swing(self):
        """The defect T1-D named, asserted rather than described: on every row
        that went to chief the final swing is SMALLER than the column beside
        it, so a reader who quotes "N hits of D" is quoting a number the
        screen never shows on the last one.

        ADVERSARY D1: the first version of this test compared two literals
        out of `REPORTED` to each other and never said `projection.` at all.
        Measured: with `final_hit_damage_at_level` returning -12345 it still
        reported `1 passed, 6 subtests`.  It described the defect it was
        named for.  It now asks the module."""
        mob = town_target_mob()
        for level, damage, hits, final in self.REPORTED:
            with self.subTest(level=level):
                answered = projection.final_hit_damage_at_level(level, mob)
                self.assertEqual(answered, final)
                self.assertLess(
                    answered, projection.damage_at_level(level, mob))
                self.assertGreater(answered, 0)


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


class TheRefusalsAreThisModulesOwnAndNotTheFormulasFromDeeper(
        unittest.TestCase):
    """T1-A: `mob_combat.pin_attacker()` sat outside every `try`.

    A caller reading this module's exception hierarchy writes
    `except LevelProjectionError`.  Before this fix, a pin that will not build
    -- which is what `PIN_ATTACKER_ABILITY_STR` drifting out of range does --
    threw `mob_combat.MobCombatContractError` straight through all seven
    public entry points, and that sentence caught nothing.
    """

    ENTRY_POINTS = (
        lambda mob: projection.attacker_at_level(7),
        lambda mob: projection.unchecked_attributes(),
        lambda mob: projection.require_only_level_differs(
            mob_combat.Combatant(level=7, ability_str=132, ability_con=0)),
        lambda mob: projection.damage_at_level(7, mob),
        lambda mob: projection.final_hit_damage_at_level(7, mob),
        lambda mob: projection.hits_to_fell_at_level(7, mob),
        lambda mob: projection.hits_to_fell_from_hp(7, mob),
        lambda mob: projection.project_levels(mob, (7,)),
        lambda mob: projection.production_pin_row(mob),
    )

    def test_a_pin_that_will_not_build_is_this_modules_refusal_everywhere(
            self):
        mob = town_target_mob()
        original = mob_combat.pin_attacker

        def refuses():
            raise mob_combat.MobCombatContractError("ability_str out of range")

        try:
            mob_combat.pin_attacker = refuses
            for index, entry in enumerate(self.ENTRY_POINTS):
                with self.subTest(entry=index):
                    with self.assertRaises(projection.LevelProjectionError):
                        entry(mob)
        finally:
            mob_combat.pin_attacker = original

    def test_that_refusal_is_the_pin_one_and_names_the_deeper_class(self):
        original = mob_combat.pin_attacker
        try:
            mob_combat.pin_attacker = lambda: (_ for _ in ()).throw(
                mob_combat.MobCombatContractError("ability_str out of range"))
            with self.assertRaises(projection.PinWillNotAssembleError) as got:
                projection.attacker_at_level(7)
        finally:
            mob_combat.pin_attacker = original
        self.assertNotIsInstance(
            got.exception, projection.LevelOutOfRangeError)
        self.assertIn("MobCombatContractError", str(got.exception))

    def test_the_shipped_pin_really_does_go_through_that_wrapper(self):
        """Without this, the two tests above would pass over a module that
        called `mob_combat.pin_attacker` directly and happened to have a
        wrapper nobody reaches."""
        original = mob_combat.pin_attacker
        seen = []
        try:
            mob_combat.pin_attacker = lambda: (
                seen.append(None) or original())
            projection.damage_at_level(7, town_target_mob())
        finally:
            mob_combat.pin_attacker = original
        self.assertTrue(seen, "the module never asked mob_combat for the pin")


class TheGuardsSkipBranchIsWalkedAndNotMerelyWritten(unittest.TestCase):
    """T1-C, the "skip" half.  Deleting `field.name in skipped` from
    `require_only_level_differs`, and the `except TypeError` from
    `unchecked_attributes`, left the suite at 35 passed -- so neither branch
    was doing anything a test could see.  These two walk them."""

    def test_a_derived_field_on_the_pin_is_skipped_and_not_looked_up(self):
        import dataclasses as _dc

        @_dc.dataclass(frozen=True)
        class PinWithDerived:
            level: int
            ability_str: int
            ability_con: int
            twice_level: int = _dc.field(init=False, default=0)

        real = mob_combat.pin_attacker()
        original = mob_combat.pin_attacker
        try:
            mob_combat.pin_attacker = lambda: PinWithDerived(
                level=real.level,
                ability_str=real.ability_str,
                ability_con=real.ability_con,
            )
            # `twice_level` is a name the typed Combatant does not carry, so
            # without the skip this is an AttributeError rather than a clean
            # return -- which is what makes this a walk of that branch and
            # not a restatement of the blind-spot report.
            self.assertIsNone(projection.require_only_level_differs(real))
        finally:
            mob_combat.pin_attacker = original

    def test_a_record_with_no_instance_dict_is_reported_as_nothing_unchecked(
            self):
        import dataclasses as _dc

        @_dc.dataclass(frozen=True, slots=True)
        class NoInstanceDict:
            level: int
            ability_str: int
            ability_con: int

        sample = NoInstanceDict(level=7, ability_str=132, ability_con=0)
        with self.assertRaises(TypeError):
            vars(sample)          # the condition the branch exists to survive
        self.assertEqual(projection.unchecked_attributes(sample), ())


class TheClampedSwingAndTheStartingHpAreTheirOwnNumbers(unittest.TestCase):
    """T1-D and T1-E(c): the two places a row was quietly claiming more than
    it measured."""

    def test_the_last_swing_is_the_room_left_and_not_the_column_beside_it(
            self):
        mob = town_target_mob()
        for level in (1, 7, 100, COMBATANT_MAX_LEVEL):
            with self.subTest(level=level):
                per_hit = projection.damage_at_level(level, mob)
                hits = projection.hits_to_fell_at_level(level, mob)
                final = projection.final_hit_damage_at_level(level, mob)
                room = int(mob.max_hp) - mob_combat.HP_FLOOR
                # Every earlier swing at full value, plus the last one, is
                # exactly the room: an identity, so it cannot be satisfied by
                # a final-hit number that was typed.
                self.assertEqual((hits - 1) * per_hit + final, room)
                self.assertTrue(0 < final <= per_hit)

    def test_the_watched_run_started_below_full_and_takes_fewer_hits(self):
        """R322C's dummy was at 192779, not at `max_hp`.  The full-bar table
        answers 223 for the pinned level; the watched run is 217.  Asserting
        they DIFFER is the point -- it is what stops one being quoted for the
        other."""
        mob = town_target_mob()
        level = mob_combat.PIN_ATTACKER_LEVEL
        watched = damage_town_target.R322C_OBSERVED_HP_BEFORE
        from_full = projection.hits_to_fell_at_level(level, mob)
        from_watched = projection.hits_to_fell_from_hp(level, mob, watched)
        self.assertLess(from_watched, from_full)
        per_hit = projection.damage_at_level(level, mob)
        self.assertEqual(
            from_watched,
            -(-(watched - mob_combat.HP_FLOOR) // per_hit))

    def test_the_last_swing_is_what_the_clamp_owner_says_it_is(self):
        """ADVERSARY D2(b): nothing tied `final_hit_damage` to the clamp.

        The ladder is walked hit by hit through `damage_town_target`'s own
        `hp_after_hits`/`applied_damage` -- the pair `tests/
        test_damage_town_target.py` pins against R322C -- so this asserts the
        column against the client-observable path rather than against the
        module's own arithmetic identity."""
        mob = town_target_mob()
        for level in (1, 7, 100):
            with self.subTest(level=level):
                attacker = projection.attacker_at_level(level)
                hits = projection.hits_to_fell_at_level(level, mob)
                before_last = damage_town_target.hp_after_hits(
                    attacker, mob, int(mob.max_hp), hits - 1)
                self.assertEqual(
                    projection.final_hit_damage_at_level(level, mob),
                    damage_town_target.applied_damage(
                        attacker, mob, before_last))
                # and the swing after it really is the one that lands it.
                self.assertEqual(
                    damage_town_target.hp_after_hits(
                        attacker, mob, int(mob.max_hp), hits),
                    mob_combat.HP_FLOOR)

    def test_a_dummy_already_at_the_floor_has_no_last_swing(self):
        """ADVERSARY D2(a): `HP_FLOOR` is a legal `current_hp`, and the
        arithmetic version answered 891 there -- the unclamped number, the
        exact claim T1-D withdrew -- beside a hit count of 0."""
        mob = town_target_mob()
        self.assertEqual(
            projection.hits_to_fell_from_hp(7, mob, mob_combat.HP_FLOOR), 0)
        self.assertEqual(
            projection.final_hit_damage_at_level(
                7, mob, mob_combat.HP_FLOOR),
            0)

    def test_a_starting_hp_the_mob_cannot_be_at_is_refused(self):
        mob = town_target_mob()
        for bad in (-1, int(mob.max_hp) + 1, 7.0, "192779", True):
            with self.subTest(bad=bad):
                with self.assertRaises(projection.LevelProjectionError):
                    projection.hits_to_fell_from_hp(7, mob, bad)
        # `None` is not a bad value -- it is the documented default, and it
        # has to keep meaning FULL or `hits_to_fell_at_level` (which passes
        # it) stops answering the question its own name asks.
        self.assertEqual(
            projection.hits_to_fell_from_hp(7, mob, None),
            projection.hits_to_fell_from_hp(7, mob, int(mob.max_hp)))


class ItAnswersOnlyForTheDummyAndOnlyForAnOrderedRequest(unittest.TestCase):
    """T1-E(a) and T1-E(b)."""

    def test_a_different_monster_is_refused_by_name(self):
        import dataclasses as _dc

        mob = town_target_mob()
        other = _dc.replace(mob, template_id=31)
        with self.assertRaises(projection.NotThePracticeDummyError):
            projection.damage_at_level(7, other)
        with self.assertRaises(projection.NotThePracticeDummyError):
            projection.project_levels(other, (7,))

    def test_the_dummy_itself_is_still_answered(self):
        self.assertIsInstance(
            projection.damage_at_level(7, town_target_mob()), int)

    def test_an_unordered_request_is_refused_rather_than_given_an_order(self):
        mob = town_target_mob()
        for unordered in ({1, 7, 100}, {1: None, 7: None}, "17"):
            with self.subTest(kind=type(unordered).__name__):
                with self.assertRaises(projection.UnorderedLevelRequestError):
                    projection.project_levels(mob, unordered)

    def test_an_ordered_request_of_the_same_levels_is_answered(self):
        rows = projection.project_levels(town_target_mob(), [100, 1, 7])
        self.assertEqual(tuple(row.level for row in rows), (100, 1, 7))


class TheMobArgumentIsThisModulesRefusalToo(unittest.TestCase):
    """D3: the `mob` half of the T1-A leak, and both of its doors.

    T1-A renamed the refusals that come out of the PIN.  The refusals that
    come out of the MOB kept `mob_combat`'s own class name, so a caller who
    wrote the sentence this module's hierarchy invites -- `except
    projection.LevelProjectionError` -- caught nothing for the commonest
    mistake there is: handing in something that is not a roster record.
    """

    def _entry_points(self, mob):
        """Every public name in `__all__` that takes a `mob`, called."""
        return {
            "damage_at_level":
                lambda: projection.damage_at_level(7, mob),
            "hits_to_fell_at_level":
                lambda: projection.hits_to_fell_at_level(7, mob),
            "hits_to_fell_from_hp":
                lambda: projection.hits_to_fell_from_hp(7, mob, 192779),
            "final_hit_damage_at_level":
                lambda: projection.final_hit_damage_at_level(7, mob),
            "project_levels":
                lambda: projection.project_levels(mob, (7,)),
            "production_pin_row":
                lambda: projection.production_pin_row(mob),
        }

    def test_a_duck_typed_stand_in_is_refused_by_this_modules_hierarchy(self):
        """The exact object adversary walked through the template gate."""
        dummy = town_target_mob()
        impostor = types.SimpleNamespace(
            template_id=dummy.template_id,
            max_hp=dummy.max_hp,
            level=dummy.level,
        )
        for name, call in self._entry_points(impostor).items():
            with self.subTest(entry_point=name):
                with self.assertRaises(
                        projection.NotTheTypedMobRecordError) as caught:
                    call()
                # And it is still catchable as the base refusal, which is the
                # sentence that used to catch nothing here.
                self.assertIsInstance(
                    caught.exception, projection.LevelProjectionError)

    def test_the_two_mob_doors_do_not_report_each_others_mistake(self):
        """Not-a-record and wrong-record are different names (D3).

        Collapsing them is how a caller who handed in a `SimpleNamespace`
        goes looking for the wrong template id.
        """
        dummy = town_target_mob()
        wrong_monster = dataclasses.replace(dummy, template_id=31)
        not_a_record = types.SimpleNamespace(
            template_id=dummy.template_id, max_hp=dummy.max_hp,
            level=dummy.level)
        with self.assertRaises(projection.NotThePracticeDummyError):
            projection.damage_at_level(7, wrong_monster)
        with self.assertRaises(projection.NotTheTypedMobRecordError):
            projection.damage_at_level(7, not_a_record)

    def test_the_deeper_type_door_is_on_a_path_something_walks(self):
        """The second half of D3.

        Adding the template gate for T1-E left `mob_combat.mob_defender`'s
        "must be the typed FieldMob record" refusal true of no reachable
        call from this module: the gate read one attribute and refused first.
        This asserts the deeper door is the one that fires, by NAME, for a
        stand-in the template gate would have waved through.
        """
        dummy = town_target_mob()
        impostor = types.SimpleNamespace(
            template_id=dummy.template_id, max_hp=dummy.max_hp,
            level=dummy.level)
        with self.assertRaises(
                projection.NotTheTypedMobRecordError) as caught:
            projection.damage_at_level(7, impostor)
        self.assertIsInstance(
            caught.exception.__cause__, mob_combat.MobCombatContractError)
        self.assertEqual(
            caught.exception.__cause__.reason,
            mob_combat.REFUSE_TYPE_NOT_TYPED_RECORD)


class NothingDeeperKnowsThisModulesRefusals(unittest.TestCase):
    """D4: the deleted branch was dead, and this is what keeps it dead.

    `_shipped_pin` opened with `except LevelProjectionError: raise` and a
    comment saying "already ours; keep its name".  `mob_combat` has never
    heard of `LevelProjectionError`, so the branch was a sentence about a
    path nothing walks -- the same defect T1-C had just been raised about,
    reintroduced two functions away in the commit that fixed it.

    Deleting it is not something a behaviour test can pin (that is the whole
    point of it being dead).  What CAN be pinned is the fact that made it
    dead, so the day someone couples the two modules the other way round,
    this goes red instead of the branch quietly becoming necessary again.
    """

    def test_mob_combat_raises_nothing_from_this_modules_hierarchy(self):
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "mob_combat.py").read_text(encoding="utf-8")
        self.assertNotIn("LevelProjectionError", source)
        self.assertNotIn("damage_level_projection", source)


class TheCeilingIsTheRecordsOwnAndNotTheProbeWindows(unittest.TestCase):
    """D5: an accepted island above the probe span used to be invisible."""

    def test_the_declared_bounds_are_the_ones_the_record_enforces(self):
        lo, hi = _declared_level_bounds()
        self.assertEqual(lo, 1)
        self.assertEqual(hi, COMBATANT_MAX_LEVEL)

    def _with_post_init(self, replacement):
        original = mob_combat.Combatant.__post_init__
        mob_combat.Combatant.__post_init__ = replacement
        self.addCleanup(
            setattr, mob_combat.Combatant, "__post_init__", original)

    def test_an_accepted_island_above_the_ceiling_is_caught(self):
        """Adversary's construction, run against the new helper.

        `[1, 1000] u [5000, 6000]` left the previous helper measuring 1000
        and the whole suite green.  The sampled probes include `5 * hi`, so
        it is now named.
        """
        lo, hi = _declared_level_bounds()

        def islanded(self_):
            if lo <= self_.level <= hi or 5 * hi <= self_.level <= 6 * hi:
                return
            raise ValueError("level")

        self._with_post_init(islanded)
        with self.assertRaises(AssertionError) as caught:
            _combatant_max_level()
        self.assertIn("above the declared gate", str(caught.exception))

    def test_a_second_gate_in_the_body_is_caught_before_any_probing(self):
        """Step 1: the accepted set is ONE range check, and that is checked."""
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "mob_combat.py").read_text(encoding="utf-8")
        self.assertIn('_require_int(self.level, "level", 1, 1000)', source)

    def test_a_hole_inside_the_declared_band_is_still_caught(self):
        lo, hi = _declared_level_bounds()

        def holed(self_):
            if lo <= self_.level <= hi and not (100 < self_.level < 200):
                return
            raise ValueError("level")

        self._with_post_init(holed)
        with self.assertRaises(AssertionError) as caught:
            _combatant_max_level()
        self.assertIn("not the interval", str(caught.exception))


class TheOrderCheckAsksForOrderAndNotForAListOfTypes(unittest.TestCase):
    """D6: the blacklist was three types somebody thought of."""

    def test_the_three_containers_that_walked_through_the_blacklist(self):
        mob = town_target_mob()
        cases = {
            "dict_keys": {1: None, 7: None}.keys(),
            "generator": (level for level in {1, 7, 100}),
            "abc_Set_subclass": _ASetSubclass({1, 7}),
        }
        for kind, unordered in cases.items():
            with self.subTest(kind=kind):
                with self.assertRaises(projection.UnorderedLevelRequestError):
                    projection.project_levels(mob, unordered)

    def test_the_ordered_containers_are_all_still_answered(self):
        mob = town_target_mob()
        for ordered in ([7], (7,), range(7, 8)):
            with self.subTest(kind=type(ordered).__name__):
                rows = projection.project_levels(mob, ordered)
                self.assertEqual(tuple(row.level for row in rows), (7,))

    def test_a_string_says_why_it_is_refused_and_it_is_not_about_order(self):
        with self.assertRaises(projection.UnorderedLevelRequestError) as one:
            projection.project_levels(town_target_mob(), "7")
        self.assertIn("one element at a time", str(one.exception))
        with self.assertRaises(projection.UnorderedLevelRequestError) as two:
            projection.project_levels(town_target_mob(), {1, 7})
        self.assertIn("Sequence", str(two.exception))


class EveryCrossFileCitationIsAPhraseAndTheFileReallySaysIt(
        unittest.TestCase):
    """D9: a line number into another file is a pin that nothing pins.

    `:128` was wrong; T1-F "fixed" it to `:8-13`, a line number for a
    docstring that had already moved once, and nothing could tell.  The
    citations are quoted phrases now and this is the test that makes them
    cost something.
    """

    MODULE = (ROOT / "src" / "pirateforce_foundation"
              / "damage_level_projection.py")

    def test_the_module_cites_no_line_number_in_another_file(self):
        text = self.MODULE.read_text(encoding="utf-8")
        offenders = re.findall(r"[A-Za-z_][A-Za-z0-9_]*\.py:\d+", text)
        self.assertEqual(
            offenders, [],
            "cross-file line-number citations are back: %r.  Cite a quoted "
            "phrase and assert it here instead." % (offenders,))

    def test_the_quoted_phrases_are_in_the_files_they_are_attributed_to(self):
        cited = {
            "damage_town_target.py": [
                "the owner photographed",
                "R322C_OBSERVED_",
                # D8's answer is anchored to the file that owns it, so the
                # day that sentence is edited or deleted, the projection
                # module's claim about WHOSE hp 192779 is goes red with it.
                "ONE connection's combat ledger",
            ],
            "mob_combat.py": [
                "pin_attacker",
                "HP_FLOOR",
                "apply_hit",
            ],
        }
        module_text = self.MODULE.read_text(encoding="utf-8")
        for filename, phrases in cited.items():
            target = (ROOT / "src" / "pirateforce_foundation" / filename)
            body = target.read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(file=filename, phrase=phrase):
                    self.assertIn(phrase, module_text)
                    self.assertIn(phrase, body)


class TheRequestThisModuleAnswersIsAddressedAndNotJustNamed(
        unittest.TestCase):
    """D10: `CORE-REQUEST row 032` is not openable from this repository.

    `grep -rn "CORE-REQUEST row 032"` over this tree finds only this module
    and this file citing each other.  A reader who cannot open the row cannot
    check any sentence that begins "row 032 says".  The row lives in the
    BRIDGE repository, so the module addresses it by path -- and this test
    deliberately does NOT go and read that path: `pf_gate_preflight` runs
    this suite with no `pf_bridge` beside it, and a test that needs the
    sibling repository present is a test that is red on the gate machine.
    """

    def test_the_module_addresses_the_row_by_repository_path(self):
        text = ((ROOT / "src" / "pirateforce_foundation"
                 / "damage_level_projection.py")
                .read_text(encoding="utf-8"))
        self.assertIn("pf_bridge/CHIEF_CONTINUATION.md", text)
        self.assertIn(
            "pf_bridge/notes_to_chief/20260907_0618_LANE-CS-CORE-REQUEST"
            "-attacker-level-from-the-real-character.md", text)

    def test_the_third_condition_is_quoted_and_not_pointed_at(self):
        text = ((ROOT / "src" / "pirateforce_foundation"
                 / "damage_level_projection.py")
                .read_text(encoding="utf-8"))
        self.assertIn(
            "fall back to the pin together\nwith a NAMED event, never a "
            "silent 0", text)



if __name__ == "__main__":
    unittest.main()
