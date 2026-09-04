"""LANE-CS: class-gated damage entry point, on top of `damage_by_skill`'s
skill-id gate.

WHY THIS EXISTS AND WHAT IT ADDS.  `damage_by_skill.resolve_skill_damage`
(round `ltahoi` onward) already refuses every starting-kit skill id except
99 -- but it does that refusal the same way for every caller regardless of
WHICH of the 5 classes is swinging.  That is correct for id 99 (`s_SKILL_3`
for all five classes per `persistence_starting_skills.py`'s own docstring)
but leaves a real gap open once a second attack id is ever classified: 99
aside, the four remaining starting-kit ids that ARE class-specific -- the
40000/41000/42000/43000/44000 "<Class> Basic Training" rows -- are each
granted to exactly one of the five classes (`class_catalog.
CLASS_ID_TO_STARTING_SKILL_IDS`, pinned from `CONSTDATA_TH__CHARCREATE_CLASS
.tsv`), and nothing before this module checked that a caller's `class_id`
actually owns the `skill_id` it is trying to swing before handing the pair
to the formula.  This module is that check, wired to `class_catalog` (the
one committed table that already answers "which skill ids does this class
start with") rather than a second, independently-typed roster of the same
five-class-to-skill mapping -- exactly the drift `class_catalog.
SOURCE_SHA256` and `skill_catalog`'s own sha pins exist to prevent
elsewhere in this lane.

COO-DECISION 20260905_0155's damage-formula direction: "เขียน resolver ที่รับ
(class, skill id, ..., ตาราง SKILL ที่ pin) คืนตัวเลข ... ห้ามคอนสแตนต์" --
this module adds the `class` argument that direction asks for, contributes
no new numeric constant of its own (every id it reads comes from
`class_catalog`/`skill_catalog`, both pinned to committed tables), and, like
`damage_by_skill.py` before it, defers the actual arithmetic to
`mob_combat.resolve_damage` unchanged.

ZERO PRODUCTION CALLERS, SAME AS THE MODULE IT WRAPS.  `damage_by_skill.py`'s
own docstring is unchanged by this file: no field `mob_combat.
attack_from_observed_action` reads today carries a skill id, so nothing
calls `resolve_skill_damage` in production, and by extension nothing calls
`resolve_class_skill_damage` either.  This module only narrows what such a
caller would be allowed to do once one exists -- it does not create the
caller.
"""
from __future__ import annotations

from . import class_catalog, damage_by_skill
from .damage_by_skill import Combatant, DamageBySkillError, resolve_damage

__all__ = [
    "Combatant",
    "resolve_damage",
    "DamageByClassSkillError",
    "is_skill_granted_to_class",
    "resolve_class_skill_damage",
]


class DamageByClassSkillError(RuntimeError):
    """Raised when `class_id` does not carry `skill_id` at all, or does but
    `damage_by_skill.resolve_skill_damage` itself refuses it (unknown id, or
    known-but-unclassified id -- see that module's docstring)."""


def is_skill_granted_to_class(class_id: int, skill_id: int) -> bool:
    """True only when `class_catalog.starting_skill_ids(class_id)` names
    `skill_id` among its four.  Raises `KeyError` for a `class_id`
    `class_catalog` does not carry -- same refusal-not-guess `class_catalog.
    starting_skill_ids` itself makes, propagated rather than swallowed, so a
    caller cannot mistake "unknown class" for "known class, wrong skill."""
    return skill_id in class_catalog.starting_skill_ids(class_id)


def resolve_class_skill_damage(
    class_id: int, skill_id: int, attacker: Combatant, defender: Combatant
) -> int:
    """The formula, gated by class ownership of `skill_id` first, then by
    `damage_by_skill.resolve_skill_damage`'s own skill-id gate.

    Raises :class:`DamageByClassSkillError` for:
      * a `class_id` outside `class_catalog.CLASS_IDS` (unknown class), or
      * a `class_id` that is known but whose starting kit does not name
        `skill_id` at all (e.g. class 1's own 40000 "Gladiator Basic
        Training" tried against `class_id=2`, the Paladin's kit, which does
        not carry it -- `class_catalog.CLASS_ID_TO_STARTING_SKILL_IDS`
        pins the five kits as pairwise distinct on exactly this column).

    A `skill_id` this class DOES carry (99 included) is passed straight to
    `damage_by_skill.resolve_skill_damage`, which may still refuse it for
    its own reasons (not yet classified as an attack) -- that refusal
    surfaces here as the same :class:`DamageByClassSkillError`, wrapping the
    original `DamageBySkillError` as its cause rather than swallowing it.
    """
    try:
        granted = is_skill_granted_to_class(class_id, skill_id)
    except KeyError as exc:
        raise DamageByClassSkillError(
            "class_id %r is not in the class catalog "
            "(class_catalog.CLASS_IDS) -- this module only resolves damage "
            "for the 5 selectable classes" % (class_id,)
        ) from exc
    if not granted:
        raise DamageByClassSkillError(
            "skill_id %r is not in class_id %r's starting kit "
            "(class_catalog.starting_skill_ids(%r) = %r) -- refusing rather "
            "than resolving damage for a skill this class was never granted"
            % (skill_id, class_id, class_id,
               class_catalog.starting_skill_ids(class_id))
        )
    try:
        return damage_by_skill.resolve_skill_damage(skill_id, attacker, defender)
    except DamageBySkillError as exc:
        raise DamageByClassSkillError(str(exc)) from exc
