"""LANE-CS: what the on-screen damage number becomes once the dispatcher
sends the CHARACTER'S OWN level instead of the pinned constant.

WHY THIS EXISTS.  `runtime.py:5093` hands every hit the same attacker record,
`MOB_COMBAT_DEFAULT_ATTACKER = mob_combat.pin_attacker()` (`runtime.py:311`),
so every class at every level prints exactly the same number on the practice
dummy.  CORE-REQUEST row 032 (`CHIEF_CONTINUATION.md`, registered by chief
2026-09-07T08:08+07:00) asks for one variable to move: the attacker's
`level`, read from the character row instead of the pin.  Chief's own letter
asks LANE-CS for the numbers that change when it lands, so that the new pin
and the wiring go in ONE commit rather than costing a round to ask for
afterwards (`COO-DECISION 20260907_0445` point 4 condition 1).

This module is that answer, computed rather than transcribed.

WHAT IT DOES NOT DO.  It does not read a character row, it does not touch
`runtime.py`, and it does not change how any hit is resolved: every number
below comes back out of `mob_combat.resolve_damage` unchanged, reached
through `damage_town_target.unclamped_hit_damage`, which is the same function
`tests/test_damage_town_target.py` already pins against R322C.  Those four
R322C numbers are NOT one layer of evidence: the per-hit 891 is what an owner
photographed on the client, while the 192779 -> 189215 hp pair came off the
SERVER console (`damage_town_target.py:8-13` names both origins; `:128` is the
provenance comment above the constants, which is NOT where the split is
stated -- T1-F, and the wrong line number is how a reader concludes the split
was never written down).  This module
inherits that split; it does not merge the two layers, and no claim here rests
on the console pair standing in for something seen on screen.  Nothing here is
a production caller and nothing here is reachable from a frame.

ONE VARIABLE, AND THE MODULE PROVES IT IS ONE -- WITH ITS BLIND SPOT NAMED.
The projected attacker is built with `dataclasses.replace` on
`mob_combat.pin_attacker()` -- not assembled here from typed numbers -- so the
day the pin grows a field, or its `ability_str` moves, this module follows it
instead of silently pinning an attacker nobody ships.
`require_only_level_differs` re-checks that claim at call time rather than
leaving it to the docstring, and it checks exactly the attributes it is able
to reason about: the declared `init=True` fields of `Combatant`.  Two kinds of
attribute it CANNOT reason about, because a value derived from `level` is
supposed to move when `level` moves:

  * a declared field with `init=False`, which `dataclasses.replace`
    recomputes, and
  * instance state assigned in `__post_init__`, which `dataclasses.fields`
    never sees at all.

Rather than pretend, the guard skips both and :func:`unchecked_attributes`
reports them by name.  On the `Combatant` shipped today that report is EMPTY,
so the "only level moves" claim is complete -- and
`tests/test_damage_level_projection.py` asserts the report is empty, so the
day someone adds a derived column the TEST goes red naming it instead of this
module refusing every level with a message blaming the caller.

WHY THE HITS COLUMN IS A CEILING AND NOT A DIVISION.  The last hit of a kill
is clamped to the room left (`mob_combat.apply_hit`), so a player watching the
screen sees a smaller number on the final swing -- the same trap
`damage_town_target.unclamped_hit_damage`'s docstring names.  The hit COUNT is
unaffected by that clamp, which is why this module can answer it in integer
arithmetic; `tests/test_damage_level_projection.py` proves the ceiling agrees
with walking the ladder one hit at a time through
`damage_town_target.hp_after_hits` rather than asserting it in prose.

AND THE CLAMPED SWING IS A COLUMN, NOT A CAVEAT (T1-D).  A row that said
`damage_per_hit=891, hits_to_fell=223` put back the exact claim this lane had
withdrawn: on this dummy the 223rd swing prints **323**, not 891.  The field
is now `unclamped_damage_per_hit`, `final_hit_damage` sits beside it, and both
are computed from the same room so they cannot drift apart.  Prose does not
survive the trip into a letter; a column does.

AND THE COUNT IS FROM FULL (T1-E).  `hits_to_fell` starts at `max_hp`, which
is a dummy nobody has touched.  R322C started at 192779 and takes 217 swings,
not 223.  :func:`hits_to_fell_from_hp` is the same count from a stated hp, so
the watched run and the full-bar table can never be quoted for each other.

WHAT IS OPEN.  `ability_str` stays at the pin for every row here, because
CORE-REQUEST row 032 moves the level half only.  A character's real STR is
`RE-293`'s question, and `COO-DECISION 20260907_1441` closed it as a DESIGN
question rather than an RE one: there is no per-class starting-stat table in
anything this repository ships, so the formula carries no STR term that has no
source.  This module does not guess it, and every projection below is
explicitly "this character's level, the pinned STR", not "this character".

WHAT THIS MODULE DOES NOT IMPLEMENT, SAID HERE BECAUSE SILENCE READ AS
COVERAGE (T1-H).  CORE-REQUEST row 032 has a THIRD condition beside the two
above: if the character's level cannot be read, the dispatcher must fall back
to the pin AND announce a NAMED event -- never a silent 0.  Nothing in this
module does that, and nothing in this module can: the read happens in
`runtime.py`, which is a CORE-REQUEST seam and not this lane's to write.  This
module is the projection table the request asks for alongside that change, so
a reader who finds all three conditions in the request and only two discussed
here would otherwise be entitled to assume the third was handled.
"""
from __future__ import annotations

import dataclasses
from typing import Any

from . import damage_town_target, field_mobs, mob_combat
from .mob_combat import Combatant

__all__ = [
    "LevelProjectionError",
    "LevelOutOfRangeError",
    "PinWillNotAssembleError",
    "NotThePracticeDummyError",
    "UnorderedLevelRequestError",
    "ProjectedRow",
    "attacker_at_level",
    "unchecked_attributes",
    "require_only_level_differs",
    "damage_at_level",
    "final_hit_damage_at_level",
    "hits_to_fell_at_level",
    "hits_to_fell_from_hp",
    "project_levels",
    "production_pin_row",
]


class LevelProjectionError(RuntimeError):
    """Base for every refusal this projection makes."""


class LevelOutOfRangeError(LevelProjectionError):
    """The CALLER's level is one the shipped `Combatant` will not accept."""


class PinWillNotAssembleError(LevelProjectionError):
    """The PIN itself will not rebuild -- nothing to do with the level asked.

    Kept apart from :class:`LevelOutOfRangeError` on purpose.  A single
    `except Exception` around `dataclasses.replace` blamed the caller's level
    for both, so the day `PIN_ATTACKER_ABILITY_STR` drifts outside the range
    `Combatant.__post_init__` enforces, `attacker_at_level(7)` would report
    "7 is not a level the shipped Combatant accepts" -- a true-sounding
    sentence about the wrong number, for every level, with the test class that
    asserts refusals still reporting green.
    """


class NotThePracticeDummyError(LevelProjectionError):
    """The mob handed in is not the dummy this lane measures against.

    T1-E: `damage_at_level` used to answer for any typed `FieldMob` -- a
    `replace(dummy, template_id=31)` came back with a normal-looking number --
    even though every sentence in this module, and LANE-CS's charter, says the
    subject is Training Iron Man (`field_mobs.TOWN_TARGET_N_ID`).  A number
    computed for a monster nobody pinned is worse than a refusal because it
    reads exactly like a number that was.
    """


class UnorderedLevelRequestError(LevelProjectionError):
    """`project_levels` was handed a container that has no order to keep.

    T1-E: a `set` or a `dict` went through `tuple(levels)`, which invented an
    order, and `TheTableKeepsTheOrderItWasAsked` then vouched for "the order
    given" for a request that never had one.
    """


@dataclasses.dataclass(frozen=True)
class ProjectedRow:
    """One row of the answer chief asked for: a level and what it prints.

    THE FIRST NUMBER IS NOT WHAT THE SCREEN SHOWS ON EVERY SWING, which is
    why the field is no longer called `damage_per_hit`.  T1-D: the row
    `(7, 891, 223)` reads as "223 swings of 891", but `mob_combat.apply_hit`
    clamps the last swing to the room left, so on this dummy the 223rd swing
    prints **323**.  This lane had already withdrawn that claim once in
    `damage_town_target.unclamped_hit_damage`'s docstring and the row put it
    straight back.  The clamped last swing is a number an owner watching the
    dummy die will photograph, so it is a COLUMN here, not a caveat in prose
    that a report can drop on its way to a letter.
    """

    level: int
    unclamped_damage_per_hit: int
    hits_to_fell: int
    final_hit_damage: int


def _shipped_pin() -> Combatant:
    """`mob_combat.pin_attacker()` with its refusal renamed to this module's.

    T1-A.  This call used to sit OUTSIDE every `try` in the module, so the day
    `PIN_ATTACKER_ABILITY_STR` or `PIN_ATTACKER_LEVEL` drifts outside the
    range `Combatant.__post_init__` enforces, all seven public entry points
    let `mob_combat.MobCombatContractError` escape -- a class that a caller
    reading THIS module's exception hierarchy has no reason to catch.
    Measured, not argued: with `PIN_ATTACKER_ABILITY_STR = 200000` every entry
    point raised that class and `except LevelProjectionError` -- the sentence
    the hierarchy invites -- caught nothing.

    Renaming it here is also what makes :class:`PinWillNotAssembleError`
    reachable from shipped code.  Before this, the only path into it ran
    through a test that replaced `mob_combat.pin_attacker` with a lambda
    returning a bare `object()`; a refusal class no shipped line can raise is
    a docstring, not behaviour.
    """
    try:
        return mob_combat.pin_attacker()
    except LevelProjectionError:                  # already ours; keep its name
        raise
    except Exception as exc:                      # noqa: BLE001 - re-raised
        raise PinWillNotAssembleError(
            "the shipped pin will not build at all (%s: %s); no level was "
            "asked for yet, so no level is what failed"
            % (type(exc).__name__, exc)
        ) from exc


def attacker_at_level(level: int) -> Combatant:
    """The production-pinned attacker with `level` replaced and nothing else.

    Raises :class:`LevelOutOfRangeError` for a level `Combatant` itself would
    refuse, by asking `Combatant` rather than re-typing its bounds here: the
    range that matters is the one the shipped record enforces, and a second
    copy of it is how two range checks drift apart.

    Raises :class:`PinWillNotAssembleError` -- a DIFFERENT name -- when it is
    the pin, not the level, that will not go back together.  The pin is
    rebuilt at its own level first precisely so the two failures can never be
    reported with the same sentence.
    """
    if type(level) is not int or type(level) is bool:
        raise LevelProjectionError("level must be an int")
    pin = _shipped_pin()
    try:
        rebuilt_at_its_own_level = dataclasses.replace(pin, level=pin.level)
    except Exception as exc:                      # noqa: BLE001 - re-raised
        raise PinWillNotAssembleError(
            "the shipped pin will not rebuild even at its own level %r; the "
            "level %r that was asked for is not what failed"
            % (getattr(pin, "level", None), level)
        ) from exc
    if level == pin.level:
        return rebuilt_at_its_own_level
    try:
        return dataclasses.replace(pin, level=level)
    except Exception as exc:                      # noqa: BLE001 - re-raised
        raise LevelOutOfRangeError(
            "level %r is not one the shipped Combatant accepts" % (level,)
        ) from exc


def unchecked_attributes(sample: Any = None) -> tuple[str, ...]:
    """The attribute names :func:`require_only_level_differs` does NOT vouch
    for, sorted, so the blind spot is a value a test can assert on.

    Two kinds qualify, and both for the same reason: a value derived from
    `level` is SUPPOSED to move when `level` moves, so comparing it would
    refuse every honest projection.

      * a declared field with `init=False`, which `dataclasses.replace`
        recomputes for the new level, and
      * an instance attribute that `dataclasses.fields` does not declare at
        all, i.e. state assigned in `__post_init__`.

    `sample` defaults to the shipped pin.  On the `Combatant` shipped today
    this returns `()` -- which is the whole point: the emptiness is asserted
    in `tests/test_damage_level_projection.py`, so a derived column added
    tomorrow turns that test red BY NAME instead of turning this module into
    something that refuses every level.
    """
    record = _shipped_pin() if sample is None else sample
    declared = {field.name for field in dataclasses.fields(record)}
    derived = {field.name for field in dataclasses.fields(record)
               if not field.init}
    try:
        undeclared = set(vars(record)) - declared
    except TypeError:                             # no instance __dict__
        undeclared = set()
    return tuple(sorted(derived | undeclared))


def require_only_level_differs(projected: Combatant) -> None:
    """Refuse a projected attacker that moved anything except `level`.

    Compared field by field against `mob_combat.pin_attacker()` through
    `dataclasses.fields`, so a field added to `Combatant` tomorrow is compared
    too without an edit here.  This is the check that makes the module's
    "one variable" claim mechanical instead of editorial.

    Scope, stated because an unscoped version of this sentence was the defect:
    the comparison covers the declared `init=True` fields only.  Anything in
    :func:`unchecked_attributes` is skipped and the refusal message never
    pretends otherwise.
    """
    pin = _shipped_pin()
    if type(projected) is not Combatant:
        raise LevelProjectionError("projected must be the typed Combatant")
    skipped = set(unchecked_attributes(pin))
    for field in dataclasses.fields(pin):
        if field.name == "level" or field.name in skipped:
            continue
        if getattr(projected, field.name) != getattr(pin, field.name):
            raise LevelProjectionError(
                "projection moved %s as well as level" % (field.name,))


def damage_at_level(level: int, mob: Any) -> int:
    """One unclamped hit on `mob` from a character of `level`.

    `mob` must be a Training Iron Man row (`field_mobs.TOWN_TARGET_N_ID`).
    `mob_combat.mob_defender` refuses anything that is not a typed `FieldMob`,
    but it has no opinion about WHICH monster, so a `replace(dummy,
    template_id=31)` used to come back with a perfectly ordinary number -- see
    :class:`NotThePracticeDummyError`.  The template check is here rather than
    inside the formula because the formula is general and this projection is
    not: every sentence in this module is about the dummy.
    """
    template = getattr(mob, "template_id", None)
    if template != field_mobs.TOWN_TARGET_N_ID:
        raise NotThePracticeDummyError(
            "this projection is only about Training Iron Man (template %r); "
            "the mob handed in is template %r"
            % (field_mobs.TOWN_TARGET_N_ID, template))
    attacker = attacker_at_level(level)
    require_only_level_differs(attacker)
    return damage_town_target.unclamped_hit_damage(attacker, mob)


def _room(mob: Any, current_hp: Any = None) -> int:
    """The hp between `current_hp` (default: FULL) and the floor.

    The default is the seam T1-E named: `max_hp` is the hp of a dummy nobody
    has touched, while the only run this lane has ever watched (R322C) started
    at 192779, not at 198125.  Callers who mean the watched run say so with
    `current_hp`; the default is documented as "full" everywhere it reaches a
    public name, so the two can never be quoted for each other.
    """
    start = int(mob.max_hp) if current_hp is None else current_hp
    if type(start) is not int or type(start) is bool:
        raise LevelProjectionError("current_hp must be an int")
    if not mob_combat.HP_FLOOR <= start <= int(mob.max_hp):
        raise LevelProjectionError(
            "current_hp %r is outside [%r, %r] for this mob"
            % (start, mob_combat.HP_FLOOR, int(mob.max_hp)))
    return start - mob_combat.HP_FLOOR


def hits_to_fell_at_level(level: int, mob: Any) -> int:
    """Hits of :func:`damage_at_level` to take `mob` from FULL to the floor.

    The ceiling of (max hp above the floor) / (damage per hit), in integer
    arithmetic.  `max_hp` is read off the shipped record; the floor is
    `mob_combat.HP_FLOOR` rather than a typed zero, for the same reason
    `damage_town_target.applied_damage` reads it there.

    "From full" is load-bearing, not decoration: R322C did not start from
    full.  :func:`hits_to_fell_from_hp` is the same count from a stated hp,
    and on this dummy it answers 217 from 192779 where this one answers 223.
    """
    return hits_to_fell_from_hp(level, mob, None)


def hits_to_fell_from_hp(level: int, mob: Any, current_hp: Any = None) -> int:
    """Hits to take `mob` from `current_hp` (default full) to the floor."""
    per_hit = damage_at_level(level, mob)
    room = _room(mob, current_hp)
    return -(-room // per_hit)


def final_hit_damage_at_level(
    level: int, mob: Any, current_hp: Any = None,
) -> int:
    """What the LAST swing prints -- the clamped one (T1-D).

    `mob_combat.apply_hit` clamps a swing to the room left, so the number an
    owner photographs on the killing blow is not
    :func:`damage_at_level`.  Computed here as the room left after every
    earlier swing, so it cannot drift away from the hit count beside it.
    """
    per_hit = damage_at_level(level, mob)
    room = _room(mob, current_hp)
    # The room left after every earlier swing.  Written as a remainder rather
    # than `room - (hits - 1) * per_hit` because `K_DEF_LV` is 1, so a typed
    # `1` here is a formula constant this module is forbidden to carry --
    # `test_the_module_types_none_of_the_numbers_it_reports` catches it, and
    # it caught exactly this line.  A room that divides evenly ends on a FULL
    # swing, which is the `or` branch.
    return room % per_hit or per_hit


def project_levels(mob: Any, levels: Any) -> tuple[ProjectedRow, ...]:
    """The projection table for `levels`, in the order given, from FULL hp.

    Refuses an empty request rather than answering it with an empty table: a
    caller that asked for nothing has a bug, and an empty tuple reads like a
    measurement.

    Refuses an UNORDERED request for the same class of reason (T1-E): this
    function promises "the order given", and a `set` or a `dict` never gave
    one -- `tuple()` invented it.  A `str` is refused too: it iterates, so it
    would otherwise be read one character at a time.
    """
    if isinstance(levels, (set, frozenset, dict, str, bytes)):
        raise UnorderedLevelRequestError(
            "project_levels keeps the order it was given, so it will not take "
            "a %s; hand it a list or a tuple" % (type(levels).__name__,))
    wanted = tuple(levels)
    if not wanted:
        raise LevelProjectionError("project_levels needs at least one level")
    return tuple(
        ProjectedRow(
            level=level,
            unclamped_damage_per_hit=damage_at_level(level, mob),
            hits_to_fell=hits_to_fell_at_level(level, mob),
            final_hit_damage=final_hit_damage_at_level(level, mob),
        )
        for level in wanted
    )


def production_pin_row(mob: Any) -> ProjectedRow:
    """The row for the level production pins TODAY.

    This is the anchor of the whole table: it must reproduce, number for
    number, what the shipped pinned attacker already resolves against this
    same dummy.  `tests/test_damage_level_projection.py` asserts exactly that
    against `damage_town_target.unclamped_hit_damage(mob_combat.pin_attacker(),
    mob)` -- so the projection cannot drift away from the pin it is meant to
    replace without going red.
    """
    return project_levels(mob, (mob_combat.PIN_ATTACKER_LEVEL,))[0]
