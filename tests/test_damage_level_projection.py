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

import array
import ast
import collections.abc
import dataclasses
import inspect
import math
import pathlib
import re
import sys
import textwrap
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


def _declared_level_gate():
    """The `(label, minimum, maximum)` `Combatant.__post_init__` declares.

    Read out of the shipped source with `ast` rather than out of a refusal
    message, because a message is formatted by the same code that would have
    to be wrong for this to matter.  The body is required to be nothing but
    `_require_int` calls so that "this call is the accepted set" is a checked
    statement and not an assumption -- see :func:`_combatant_max_level` step 1.

    S1: THE READER IS JOINED TO THE RUNTIME OBJECT.  Adversary broke the
    previous version with a decoy `class Combatant` inside an uncalled
    function (`ast.walk` is breadth-first and the old loop kept the LAST
    match, so the decoy won) and with a monkeypatched `__post_init__` (which
    the source never sees).  Two lines close both: exactly one `Combatant`
    class node may exist in the file, and the `ast.FunctionDef` picked here
    must be the very code object `mob_combat.Combatant.__post_init__` runs --
    same file, same first line.  A monkeypatch moves `co_filename` into
    whatever module patched it, so it can no longer hide behind the source.

    S6: IT DIAGNOSES INSTEAD OF DYING.  A docstring on `__post_init__` used
    to be reported as "calls something other than `_require_int`", and a
    keyword argument raised a bare `IndexError` with no message at all --
    both at import time, which took the whole file down with a wrong
    explanation.  A leading docstring is now allowed and skipped, and every
    other shape is named, with the file and function in the message.
    """
    source = (ROOT / "src" / "pirateforce_foundation" / "mob_combat.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    post_init = _the_only_post_init(tree)
    _join_source_to_running_gate(post_init, source)
    return _gate_out_of(post_init)


def _the_only_post_init(tree):
    """The one `Combatant.__post_init__` in `tree`, or an AssertionError.

    Split out of :func:`_declared_level_gate` so the decoy case can be
    measured on a parsed decoy rather than described in prose (S1).
    """
    where = "`mob_combat.Combatant.__post_init__`"
    classes = [node for node in ast.walk(tree)
               if isinstance(node, ast.ClassDef) and node.name == "Combatant"]
    assert len(classes) == 1, (
        "`mob_combat.py` defines %d classes named `Combatant`; this file "
        "reads the level gate out of the source and cannot tell which one "
        "the record uses (S1: a decoy class is how the previous reader was "
        "fooled)" % (len(classes),))
    post_inits = [item for item in classes[0].body
                  if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and item.name == "__post_init__"]
    assert len(post_inits) == 1, (
        "%s is defined %d times in the shipped source; this file reads the "
        "level gate out of it" % (where, len(post_inits)))
    return post_inits[0]


def _join_source_to_running_gate(post_init, source):
    """Assert the parsed `post_init` IS the code the record runs (S1)."""
    where = "`mob_combat.Combatant.__post_init__`"
    running = getattr(mob_combat.Combatant, "__post_init__", None)
    code = getattr(running, "__code__", None)
    assert code is not None, (
        "%s is not a plain Python function at run time (%r); the source this "
        "file reads and the gate the record runs cannot be joined"
        % (where, running))
    assert pathlib.Path(code.co_filename) == source, (
        "%s runs from %s, not from the shipped source %s that this file "
        "parses -- the two oracles are not the same gate (S1)"
        % (where, code.co_filename, source))
    assert code.co_firstlineno == post_init.lineno, (
        "%s runs code starting at line %d while the source this file parsed "
        "declares it at line %d; the reader is not looking at the gate the "
        "record runs (S1)" % (where, code.co_firstlineno, post_init.lineno))


def _gate_out_of(post_init):
    """`(label, minimum, maximum)` read off the parsed `post_init` body."""
    where = "`mob_combat.Combatant.__post_init__`"
    body = list(post_init.body)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]          # a docstring is not a gate (S6)
    assert body, (
        "%s has no statements left after its docstring; this file asserts "
        "the level gate is one `_require_int` call" % (where,))
    found = []
    for statement in body:
        assert isinstance(statement, ast.Expr), (
            "%s gained a statement that is not a bare call (%s).  This file "
            "asserts the level gate is one `_require_int` call; a second "
            "gate would make every sweep here cover a subset of what the "
            "record accepts." % (where, type(statement).__name__))
        call = statement.value
        assert (isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "_require_int"), (
            "%s calls something other than `_require_int`; see the assertion "
            "above for why that matters" % (where,))
        assert not call.keywords and len(call.args) == 4, (
            "%s calls `_require_int` with %d positional arguments and %d "
            "keywords; this file reads (value, label, minimum, maximum) by "
            "position and will not guess at any other spelling (S6)"
            % (where, len(call.args), len(call.keywords)))
        target, label = call.args[0], call.args[1]
        if isinstance(target, ast.Attribute) and target.attr == "level":
            assert (isinstance(label, ast.Constant)
                    and isinstance(label.value, str)), (
                "the level gate in %s labels itself with something that is "
                "not a string literal; this file probes `_require_int` with "
                "that exact label" % (where,))
            bounds = call.args[2], call.args[3]
            for bound in bounds:
                assert isinstance(bound, ast.Constant) and isinstance(
                    bound.value, int), (
                    "the level bounds in %s are not plain int literals any "
                    "more; this file cannot read them" % (where,))
            found.append((label.value, bounds[0].value, bounds[1].value))
    assert len(found) == 1, (
        "%s has %d range checks on `level`, not one; the accepted set is no "
        "longer a single interval" % (where, len(found)))
    return found[0]


def _declared_level_bounds():
    """The `[minimum, maximum]` half of :func:`_declared_level_gate`."""
    _, minimum, maximum = _declared_level_gate()
    return minimum, maximum


def _require_int_is_that_interval(label, lo, hi):
    """Measure `mob_combat._require_int` itself against its own contract (S1).

    Step 1 of :func:`_combatant_max_level` checks that `__post_init__` CALLS
    `_require_int`; adversary's second island was five lines added inside
    `_require_int`, which that check never looks at.  So the helper is
    measured here the same way the record is: with the LABEL the gate
    actually passes (a version that special-cases `"level"` cannot hide
    behind a probe using some other label), over the edges of the band, and
    at the same decades sampled above it.  Accepting anything outside
    `[lo, hi]`, or refusing anything inside, is an island wherever it was
    written.
    """
    def accepted(value):
        try:
            mob_combat._require_int(value, label, lo, hi)
        except mob_combat.MobCombatContractError:
            return False
        return True

    inside = (lo, lo + 1, (lo + hi) // 2, hi - 1, hi)
    outside = (lo - 1, hi + 1) + _ABOVE_CEILING_PROBES(hi)
    wrong = [value for value in inside if not accepted(value)]
    assert not wrong, (
        "`mob_combat._require_int(value, %r, %d, %d)` refuses %r, which is "
        "inside the band it was handed" % (label, lo, hi, wrong))
    leaked = [value for value in outside if accepted(value)]
    assert not leaked, (
        "`mob_combat._require_int(value, %r, %d, %d)` accepts %r, which is "
        "outside the band it was handed; the gate the record declares is not "
        "the gate `_require_int` enforces (S1)" % (label, lo, hi, leaked))
    for value in (True, 1.0, "1", None):
        assert not accepted(value), (
            "`mob_combat._require_int` accepts %r as a plain int" % (value,))


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

      4. JOIN THE TWO ORACLES, AND MEASURE THE HELPER THE GATE DELEGATES TO
         (S1).  Steps 1-3 were a reader of the source and a sampler of the
         record with nothing tying them together, and pf-adversary built
         three islands in that gap, all leaving the whole file green:
         `[1500, 1600]` monkeypatched into `__post_init__` (it clears every
         sampled point, and step 1 reads the SOURCE, which a monkeypatch does
         not touch); five lines added to `mob_combat._require_int` itself
         (step 1 checks that `__post_init__` CALLS it, never what it does);
         and a decoy `class Combatant` inside an uncalled function (the old
         reader kept the LAST `ast.walk` match).  All three are closed by
         asking three questions instead of trusting: `_declared_level_gate`
         requires exactly ONE `Combatant` in the file and requires the
         `ast.FunctionDef` it read to be the code object the record RUNS
         (`co_filename` and `co_firstlineno`), and
         :func:`_require_int_is_that_interval` measures `_require_int` under
         the label the gate passes it.

    WHAT IS STILL NOT CLOSED, STATED RATHER THAN IMPLIED.  A `_require_int`
    that answers on something other than its four arguments -- inspecting its
    caller, or a global mode flag -- would pass step 4's probe and could then
    let `__post_init__` accept a level the probe never asks about above the
    span.  Nothing in this repository is written that way and no reader would
    do it by accident, but it is the remaining shape, and it is the reason
    step 2's full scan and step 3's decades stay: they are the half that does
    not care why a level is accepted.
    """
    def accepted(level):
        try:
            mob_combat.Combatant(level=level, ability_str=0, ability_con=0)
        except Exception:
            return False
        return True

    label, lo, hi = _declared_level_gate()
    _require_int_is_that_interval(label, lo, hi)
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
    """The sixteen numbers that left this lane in a letter, plus a column.

    Deliberately transcribed: derived numbers cannot catch a letter that
    reported something the code never said.  If the shipped sources move,
    these go red and the letter has to be corrected -- which is the point.
    Rows are (level, UNCLAMPED damage per hit, hits to fell, what the LAST
    swing prints).

    S7: THESE ARE THE ROWS THAT ACTUALLY WENT, AND SIX OF THEM WERE NOT.
    The letter is `pf_bridge/notes_to_chief/20260907_0910_LANE-CS-TO-CHIEF-
    pin-891-projection-for-core-request-row-032.md`, and its table has EIGHT
    rows: levels 1, 3, 7, 10, 30, 40, 50, 100.  This class pinned six --
    1, 7, 25, 40, 60, 100 -- so levels 25 and 60 were pinned as "reported to
    chief" having never left this lane in any letter, while 3, 10, 30 and 50,
    which did leave, were pinned nowhere.  A class named for a letter was
    guarding a different set of numbers than the letter carried, and the word
    "eleven" in this docstring matched neither.  Sixteen numbers left (eight
    levels, two columns each).

    THE FOURTH COLUMN IS THIS FILE'S, NOT THE LETTER'S, AND THAT IS THE
    POINT.  The letter said "223 hits of 891" where the 223rd hit prints 323;
    the final-swing column is transcribed here for the same drift-catching
    reason as the other three, and is marked as an addition rather than a
    quotation because no letter has carried it yet.

    NO ORACLE, SAID PLAINLY (same shape as D10).  `pf_gate_preflight` runs
    this suite with no `pf_bridge` beside it, so nothing here can open that
    letter and check the levels against it.  The transcription is checked
    against the MODULE; that it is the letter's set is checked by a reader.
    """

    #: Level, unclamped damage per hit, hits to fell -- the eight rows of the
    #: letter -- and the final swing, which the letter did not carry.
    REPORTED = (
        (1, 873, 227, 827),
        (3, 879, 226, 350),
        (7, 891, 223, 323),
        (10, 900, 221, 125),
        (30, 960, 207, 365),
        (40, 990, 201, 125),
        (50, 1020, 195, 245),
        (100, 1170, 170, 395),
    )

    #: The two columns that were in the letter, so a future edit cannot
    #: quietly re-add a level nobody sent by appending a row above.
    LEVELS_IN_THE_LETTER = (1, 3, 7, 10, 30, 40, 50, 100)

    def test_the_pinned_levels_are_the_levels_the_letter_carried(self):
        self.assertEqual(
            tuple(row[0] for row in self.REPORTED),
            self.LEVELS_IN_THE_LETTER)

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

    def _island(self, lo, hi, extra):
        """A `__post_init__` that accepts `[lo, hi]` and `extra` as well."""
        def islanded(self_):
            if lo <= self_.level <= hi or extra[0] <= self_.level <= extra[1]:
                return
            raise ValueError("level")
        return islanded

    def test_every_monkeypatched_island_is_now_caught_by_the_join(self):
        """S1: the three islands adversary built, including the survivor.

        `[5000, 6000]` was caught before by `5 * hi`.  `[1500, 1600]` was
        NOT: it clears every sampled decade, and the source reader could not
        see a monkeypatch at all.  Both are caught in the same place now and
        for the same reason -- the gate the record RUNS is no longer the
        source this file parsed, which is a fact about the patch and not
        about which levels it happens to accept.
        """
        lo, hi = _declared_level_bounds()
        for extra in ((5 * hi, 6 * hi), (1500, 1600), (hi + 1, hi + 2)):
            with self.subTest(island=extra):
                self._with_post_init(self._island(lo, hi, extra))
                with self.assertRaises(AssertionError) as caught:
                    _combatant_max_level()
                self.assertIn("not from the shipped source",
                              str(caught.exception))

    def test_the_reader_and_the_record_are_the_same_gate(self):
        """The join itself, asserted rather than left to the islands."""
        code = mob_combat.Combatant.__post_init__.__code__
        source = ROOT / "src" / "pirateforce_foundation" / "mob_combat.py"
        self.assertEqual(pathlib.Path(code.co_filename), source)
        tree = ast.parse(source.read_text(encoding="utf-8"))
        classes = [node for node in ast.walk(tree)
                   if isinstance(node, ast.ClassDef)
                   and node.name == "Combatant"]
        self.assertEqual(len(classes), 1)
        picked = [item for item in classes[0].body
                  if isinstance(item, ast.FunctionDef)
                  and item.name == "__post_init__"]
        self.assertEqual(len(picked), 1)
        self.assertEqual(code.co_firstlineno, picked[0].lineno)

    def test_a_decoy_combatant_class_is_refused_rather_than_preferred(self):
        """S1's third island: `ast.walk` used to keep the LAST match.

        Measured on a real decoy: the shipped source with adversary's
        uncalled function appended.  The old reader answered `[1, 9999]`
        here without a word; the reader refuses to choose at all, which is
        the only honest answer -- it cannot tell which class the record is.
        """
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "mob_combat.py").read_text(encoding="utf-8")
        decoyed = source + (
            "\n\ndef _never_called():\n"
            "    class Combatant:\n"
            "        def __post_init__(self):\n"
            "            _require_int(self.level, \"level\", 1, 9999)\n")
        tree = ast.parse(decoyed)
        self.assertEqual(
            len([node for node in ast.walk(tree)
                 if isinstance(node, ast.ClassDef)
                 and node.name == "Combatant"]),
            2, "the decoy did not parse as a second Combatant")
        with self.assertRaises(AssertionError) as caught:
            _the_only_post_init(tree)
        self.assertIn("cannot tell which one", str(caught.exception))

    def test_a_docstring_on_the_gate_does_not_take_the_file_down(self):
        """S6: LANE-B adds a docstring and this file used to die at import.

        The old reader called a docstring "something other than
        `_require_int`" -- a wrong diagnosis, delivered at collection time,
        for every test in the file.  The gate reads the same either way now.
        """
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "mob_combat.py").read_text(encoding="utf-8")
        documented = source.replace(
            '        _require_int(self.level, "level", 1, 1000)',
            '        """Ranges, in one place."""\n'
            '        _require_int(self.level, "level", 1, 1000)', 1)
        self.assertNotEqual(documented, source, "the gate line moved")
        self.assertEqual(
            _gate_out_of(_the_only_post_init(ast.parse(documented))),
            ("level", 1, 1000))

    def test_a_keyword_argument_is_diagnosed_and_not_an_index_error(self):
        """S6: `_require_int(value=..., ...)` used to raise a bare IndexError.

        No message, no file name, nothing to act on -- and it took the whole
        file down with it.  It is refused by name now, and the message says
        what this reader will and will not read.
        """
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "mob_combat.py").read_text(encoding="utf-8")
        keyworded = source.replace(
            '_require_int(self.level, "level", 1, 1000)',
            '_require_int(self.level, "level", minimum=1, maximum=1000)', 1)
        self.assertNotEqual(keyworded, source, "the gate line moved")
        with self.assertRaises(AssertionError) as caught:
            _gate_out_of(_the_only_post_init(ast.parse(keyworded)))
        message = str(caught.exception)
        self.assertIn("keywords", message)
        self.assertIn("mob_combat.Combatant.__post_init__", message)

    def test_a_second_gate_in_the_body_is_caught_before_any_probing(self):
        """Step 1: the accepted set is ONE range check, and that is checked.

        S1: THIS WAS A SUBSTRING GREP OVER A 3070-LINE FILE.  `assertIn('_re
        quire_int(self.level, "level", 1, 1000)', source)` passes if that
        text appears ANYWHERE -- in a comment, in a docstring, in a second
        class -- and says nothing about the statement the record runs.  It
        asks the parsed gate now, which is the same object
        `_combatant_max_level` measures.
        """
        label, lo, hi = _declared_level_gate()
        self.assertEqual((label, lo, hi), ("level", 1, 1000))

    def test_an_island_written_into_require_int_itself_is_caught(self):
        """S1's second island: the helper the gate delegates to."""
        original = mob_combat._require_int

        def leaky(value, label, minimum, maximum):
            if label == "level" and 5000 <= value <= 6000:
                return value
            return original(value, label, minimum, maximum)

        mob_combat._require_int = leaky
        self.addCleanup(setattr, mob_combat, "_require_int", original)
        with self.assertRaises(AssertionError) as caught:
            _combatant_max_level()
        self.assertIn("not the gate `_require_int` enforces",
                      str(caught.exception))

    def test_a_hole_inside_the_declared_band_is_still_caught(self):
        """A hole is caught by the JOIN now, one step earlier than before.

        The monkeypatch is what the assertion names, which is more nearly
        true than "the accepted levels are not the interval": a patched
        record is not the shipped record, whatever shape its holes have.
        """
        lo, hi = _declared_level_bounds()

        def holed(self_):
            if lo <= self_.level <= hi and not (100 < self_.level < 200):
                return
            raise ValueError("level")

        self._with_post_init(holed)
        with self.assertRaises(AssertionError) as caught:
            _combatant_max_level()
        self.assertIn("not from the shipped source", str(caught.exception))

    def test_the_full_scan_still_fires_where_the_sampled_probes_miss(self):
        """Step 2 is not dead code now that step 4 exists, and here is why.

        Step 4 probes `_require_int` at five points inside the band (both
        edges, both neighbours of an edge, the midpoint), so a hole at 137 is
        invisible to it.  The full scan of `[lo, hi]` is what notices, on a
        record whose `__post_init__` is still the shipped function at the
        shipped line -- the join passes and the scan has to carry it.
        """
        original = mob_combat._require_int

        def holed(value, label, minimum, maximum):
            answer = original(value, label, minimum, maximum)
            if label == "level" and answer == 137:
                raise mob_combat.MobCombatContractError(
                    mob_combat.REFUSE_VALUE_OUT_OF_RANGE, "hole")
            return answer

        mob_combat._require_int = holed
        self.addCleanup(setattr, mob_combat, "_require_int", original)
        with self.assertRaises(AssertionError) as caught:
            _combatant_max_level()
        message = str(caught.exception)
        self.assertIn("not the interval", message)
        self.assertIn("137", message)


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

    def test_all_three_conditions_of_the_row_are_listed_not_just_one(self):
        """S5(c): naming one of three is the T1-H defect committed again.

        The paragraph exists so that a reader who finds three conditions in
        the request and fewer here does not read the silence as coverage.
        A first version named only the fall-back condition, so condition 2
        -- do not touch mob-to-player damage -- appeared nowhere in the
        module at all.

        This is a completeness check on the module's own text, and that is
        ALL it is: there is no oracle for the wording, because the row lives
        in the bridge repository and this suite runs with no `pf_bridge`
        beside it.  The module says so in its own paragraph rather than
        letting a passing test here look like verification.
        """
        text = ((ROOT / "src" / "pirateforce_foundation"
                 / "damage_level_projection.py")
                .read_text(encoding="utf-8"))
        self.assertIn("THREE conditions", text)
        for condition in ("the 891 pin moves in the SAME commit",
                          "mob-to-player damage is NOT touched",
                          "never a silent 0"):
            with self.subTest(condition=condition):
                self.assertIn(condition, text)
        self.assertIn("is a TRANSLATION, not a quotation", text)



class AnHpThisModuleCannotCountFromIsRefused(unittest.TestCase):
    """S3: `_room` used to coerce the record's hp with `int()`.

    The finding pf-adversary called the worst thing on the branch: with
    `max_hp=1.5` the module ANSWERED -- `ProjectedRow(level=7, ...,
    hits_to_fell=1, final_hit_damage=1)` -- a complete, ordinary-looking row
    for a dummy no measurement could produce.  A truncation is not a check.
    """

    def _entry_points(self, mob):
        return {
            "hits_to_fell_at_level": lambda: (
                projection.hits_to_fell_at_level(7, mob)),
            "hits_to_fell_from_hp": lambda: (
                projection.hits_to_fell_from_hp(7, mob, None)),
            "final_hit_damage_at_level": lambda: (
                projection.final_hit_damage_at_level(7, mob)),
            "project_levels": lambda: projection.project_levels(mob, (7,)),
            "production_pin_row": lambda: projection.production_pin_row(mob),
        }

    def test_a_fractional_max_hp_is_refused_and_not_answered_as_one(self):
        mob = dataclasses.replace(town_target_mob(), max_hp=1.5)
        for name, call in self._entry_points(mob).items():
            with self.subTest(entry=name):
                with self.assertRaises(
                        projection.HpWillNotReadAsAnIntError) as caught:
                    call()
                self.assertIn("max_hp", str(caught.exception))

    def test_the_row_that_used_to_come_back_for_it_does_not(self):
        """The exact answer the old code gave, pinned as no longer given."""
        mob = dataclasses.replace(town_target_mob(), max_hp=1.5)
        with self.assertRaises(projection.LevelProjectionError):
            projection.project_levels(mob, (7,))

    def test_no_entry_point_leaks_a_raw_builtin_refusal(self):
        """D3 closed this on the record side; `int()` reopened it one line
        lower.  A caller under `except LevelProjectionError` catches these."""
        for bad in ("198125", None, [198125], object()):
            mob = dataclasses.replace(town_target_mob(), max_hp=bad)
            for name, call in self._entry_points(mob).items():
                with self.subTest(max_hp=repr(bad), entry=name):
                    with self.assertRaises(projection.LevelProjectionError):
                        call()

    def test_a_boolean_hp_is_refused_on_both_sides(self):
        mob = town_target_mob()
        with self.assertRaises(projection.HpWillNotReadAsAnIntError):
            projection.hits_to_fell_from_hp(7, mob, True)
        with self.assertRaises(projection.HpWillNotReadAsAnIntError):
            projection.hits_to_fell_at_level(
                7, dataclasses.replace(mob, max_hp=True))

    def test_the_shipped_dummy_is_still_answered(self):
        """The refusal is about hp that is not an int, not about hp."""
        mob = town_target_mob()
        self.assertEqual(projection.hits_to_fell_at_level(7, mob), 223)
        self.assertEqual(
            projection.hits_to_fell_from_hp(7, mob, 192779), 217)

    def test_there_is_no_int_coercion_left_in_the_room_helper(self):
        """The mutant M12 adversary ran (delete the `int()`) has nothing to
        delete: no call to `int` survives in `_room`'s executable body.

        The docstring is dropped before looking, because it QUOTES the line
        that was removed -- a text search that counted that quotation would
        pass forever whatever the code did.
        """
        body = ast.parse(
            textwrap.dedent(inspect.getsource(projection._room))).body[0]
        if (isinstance(body.body[0], ast.Expr)
                and isinstance(body.body[0].value, ast.Constant)):
            del body.body[0]
        called = {node.func.id for node in ast.walk(body)
                  if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name)}
        self.assertNotIn("int", called)
        self.assertIn("_require_hp_int", called)


class TheOrderCheckMeasuresOrderInsteadOfTrustingRegistration(
        unittest.TestCase):
    """S4: `isinstance(x, Sequence)` is a registration, not a proof."""

    def test_a_memoryview_is_refused_like_the_bytes_it_views(self):
        """Adversary's counterexample: `memoryview(b'\\x07d')` walked
        through and was read as `[7, 100]` while the identical `bytes`
        object was refused by name."""
        mob = town_target_mob()
        raw = b"\x07d"
        with self.assertRaises(projection.UnorderedLevelRequestError):
            projection.project_levels(mob, raw)
        with self.assertRaises(projection.UnorderedLevelRequestError) as view:
            projection.project_levels(mob, memoryview(raw))
        self.assertIn("buffer", str(view.exception))

    def test_every_buffer_is_refused_and_not_a_list_of_three_names(self):
        mob = town_target_mob()
        for container in (b"\x07", bytearray(b"\x07"),
                          memoryview(bytearray(b"\x07")),
                          array.array("l", [7, 10])):
            with self.subTest(container=type(container).__name__):
                with self.assertRaises(
                        projection.UnorderedLevelRequestError):
                    projection.project_levels(mob, container)

    def test_a_container_registered_as_a_sequence_is_still_measured(self):
        """`Sequence.register(frozenset)` makes `isinstance` say yes to a
        container with no `__getitem__` at all."""
        mob = town_target_mob()

        class _RegisteredButNotIndexed(frozenset):
            pass

        collections.abc.Sequence.register(_RegisteredButNotIndexed)
        self.assertIsInstance(
            _RegisteredButNotIndexed({7}), collections.abc.Sequence)
        with self.assertRaises(
                projection.UnorderedLevelRequestError) as caught:
            projection.project_levels(mob, _RegisteredButNotIndexed({7}))
        self.assertIn("will not be indexed", str(caught.exception))

    def test_a_container_whose_index_order_is_not_its_walk_order(self):
        """The other half of "the order given": one object, two orders."""
        mob = town_target_mob()

        class _TwoOrders(collections.abc.Sequence):
            def __init__(self, values):
                self._values = list(values)

            def __getitem__(self, index):
                return self._values[index]

            def __len__(self):
                return len(self._values)

            def __iter__(self):
                return iter(reversed(self._values))

        with self.assertRaises(
                projection.UnorderedLevelRequestError) as caught:
            projection.project_levels(mob, _TwoOrders([1, 7]))
        self.assertIn("two different orders", str(caught.exception))

    def test_the_containers_a_caller_actually_hands_it_still_work(self):
        mob = town_target_mob()
        for container in ([1, 7], (1, 7), range(1, 8, 6)):
            with self.subTest(container=type(container).__name__):
                rows = projection.project_levels(mob, container)
                self.assertEqual([row.level for row in rows], [1, 7])



if __name__ == "__main__":
    unittest.main()
