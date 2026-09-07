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
`tests/test_damage_town_target.py` already pins against the four numbers an
owner photographed in R322C.  Nothing here is a production caller and nothing
here is reachable from a frame.

ONE VARIABLE, AND THE MODULE PROVES IT IS ONE.  The projected attacker is
built with `dataclasses.replace` on `mob_combat.pin_attacker()` -- not
assembled here from typed numbers -- so the day the pin grows a field, or its
`ability_str` moves, this module follows it instead of silently pinning an
attacker nobody ships.  `require_only_level_differs` re-checks that claim
field by field at call time rather than leaving it to the docstring.

WHY THE HITS COLUMN IS A CEILING AND NOT A DIVISION.  The last hit of a kill
is clamped to the room left (`mob_combat.apply_hit`), so a player watching the
screen sees a smaller number on the final swing -- the same trap
`damage_town_target.unclamped_hit_damage`'s docstring names.  The hit COUNT is
unaffected by that clamp, which is why this module can answer it in integer
arithmetic; `tests/test_damage_level_projection.py` proves the ceiling agrees
with walking the ladder one hit at a time through
`damage_town_target.hp_after_hits` rather than asserting it in prose.

WHAT IS OPEN.  `ability_str` stays at the pin for every row here, because
CORE-REQUEST row 032 moves the level half only.  A character's real STR is
`RE-293`'s question and is not answered anywhere in this repository today;
this module does not guess it, and every projection below is explicitly
"this character's level, the pinned STR", not "this character".
"""
from __future__ import annotations

import dataclasses
from typing import Any

from . import damage_town_target, mob_combat
from .mob_combat import Combatant

__all__ = [
    "LevelProjectionError",
    "ProjectedRow",
    "attacker_at_level",
    "require_only_level_differs",
    "damage_at_level",
    "hits_to_fell_at_level",
    "project_levels",
    "production_pin_row",
]


class LevelProjectionError(RuntimeError):
    """Raised for a level this projection will not answer for."""


@dataclasses.dataclass(frozen=True)
class ProjectedRow:
    """One row of the answer chief asked for: a level and what it prints."""

    level: int
    damage_per_hit: int
    hits_to_fell: int


def attacker_at_level(level: int) -> Combatant:
    """The production-pinned attacker with `level` replaced and nothing else.

    Raises :class:`LevelProjectionError` for a level `Combatant` itself would
    refuse, by asking `Combatant` rather than re-typing its bounds here: the
    range that matters is the one the shipped record enforces, and a second
    copy of it is how two range checks drift apart.
    """
    if type(level) is not int or type(level) is bool:
        raise LevelProjectionError("level must be an int")
    try:
        return dataclasses.replace(mob_combat.pin_attacker(), level=level)
    except Exception as exc:                      # noqa: BLE001 - re-raised
        raise LevelProjectionError(
            "level %r is not one the shipped Combatant accepts" % (level,)
        ) from exc


def require_only_level_differs(projected: Combatant) -> None:
    """Refuse a projected attacker that moved anything except `level`.

    Compared field by field against `mob_combat.pin_attacker()` through
    `dataclasses.fields`, so a field added to `Combatant` tomorrow is compared
    too without an edit here.  This is the check that makes the module's
    "one variable" claim mechanical instead of editorial.
    """
    pin = mob_combat.pin_attacker()
    if type(projected) is not Combatant:
        raise LevelProjectionError("projected must be the typed Combatant")
    for field in dataclasses.fields(pin):
        if field.name == "level":
            continue
        if getattr(projected, field.name) != getattr(pin, field.name):
            raise LevelProjectionError(
                "projection moved %s as well as level" % (field.name,))


def damage_at_level(level: int, mob: Any) -> int:
    """One unclamped hit on `mob` from a character of `level`.

    `mob` is the shipped roster record for the practice dummy; it is handed
    straight to `damage_town_target.unclamped_hit_damage`, which refuses
    anything else by name through `mob_combat.mob_defender`.
    """
    attacker = attacker_at_level(level)
    require_only_level_differs(attacker)
    return damage_town_target.unclamped_hit_damage(attacker, mob)


def hits_to_fell_at_level(level: int, mob: Any) -> int:
    """How many hits of :func:`damage_at_level` take `mob` from full to floor.

    The ceiling of (max hp above the floor) / (damage per hit), in integer
    arithmetic.  `max_hp` is read off the shipped record; the floor is
    `mob_combat.HP_FLOOR` rather than a typed zero, for the same reason
    `damage_town_target.applied_damage` reads it there.
    """
    per_hit = damage_at_level(level, mob)
    room = int(mob.max_hp) - mob_combat.HP_FLOOR
    return -(-room // per_hit)


def project_levels(mob: Any, levels: Any) -> tuple[ProjectedRow, ...]:
    """The projection table for `levels`, in the order given.

    Refuses an empty request rather than answering it with an empty table: a
    caller that asked for nothing has a bug, and an empty tuple reads like a
    measurement.
    """
    wanted = tuple(levels)
    if not wanted:
        raise LevelProjectionError("project_levels needs at least one level")
    return tuple(
        ProjectedRow(
            level=level,
            damage_per_hit=damage_at_level(level, mob),
            hits_to_fell=hits_to_fell_at_level(level, mob),
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
