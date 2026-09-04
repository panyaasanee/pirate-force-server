"""LANE-CS: skill-id-aware damage entry point, the first module in this
lane's own territory (as opposed to the bare-hit path in `mob_combat.py`,
which is LANE-B's and stays untouched by this module).

SCOPE AND WHAT THIS IS NOT.  `COO-DECISION 20260904_0943` drew the line:
"basic attack" for LANE-CS means the 8 named starting-kit skills
(`skill_catalog.STARTING_KIT_SKILL_IDS`) and everything that hangs off a
skill id, while the bare-hit path a player already triggers today by
clicking a monster (`mob_combat.attack_from_observed_action`, which reads no
skill id at all) stays LANE-B's and is not touched here.  This module is the
skill-id side of that split.

THE FORMULA IS IMPORTED, NOT COPIED.  `mob_combat.py` documents why the
formula is copied into it (and into the two hypothesis modules) instead of
importing a scenario-gated probe: a flagless production build cannot depend
on a probe lane.  That reasoning does not apply here — this module ships in
the same flagless build as `mob_combat.py` itself, so there is no excuse for
a FOURTH copy of `ATK_BASE`/`K_ATK_STR`/etc.  `resolve_damage` and
`Combatant` below are the exact objects `mob_combat` defines, re-exported so
a caller of this module never needs to import `mob_combat` directly.
`tests/test_damage_by_skill.py` proves this by identity (``is``), not value
equality, and additionally asserts this file assigns none of the formula
constant names itself.

ONLY SKILL 99 IS CLASSIFIED, AND THAT IS DELIBERATE, NOT A ROUND THAT RAN OUT
OF TIME.  Of the 8 starting-kit ids, only 99 carries a client-given title
that is unambiguous as an attack: `skill_catalog.SKILL_ID_TO_TITLE[99]` is
literally "Normal Attack".  110/111 are "Strive Jump"/"VIP Strive Jump" —
movement, by their own titles, not attacks.  The five 40000-series ids are
"<Class> Basic Training" — `skill_catalog.py`'s own docstring (round 6o11t1)
already proved `n_PASSIVE` cannot be used to tell these apart from real
attack skills, and the one table that could (`s_CAST_CONDITION`/
`s_CAST_BEHAVIOR` token grammar) has now been tried and failed: `RE-232`
came back **BOUNDED-NEGATIVE** (pf_bridge/notes_to_chief/20260904_1055_
RE-232-RESULT-BOUNDED-NEGATIVE-EIGHT-ROWS-DO-NOT-CLASSIFY.md, closed the
same round this docstring was corrected, `tp9rpy`) — the grammar has real
condition/behavior structure, but none of the 8 rows offers an
independently-labeled AOE, self-buff or heal example to check a classifier
against, and the tokens it does show (`GO`, `CHASE`, `SKIP`, `ISVIP_I`) are
control-flow/edge data, not a type enum, so they cannot tell the remaining 7
ids apart either.  The result letter's own `BUILD_IMPACT` line is explicit:
"no classifier change" — the refusal below is not provisional pending an
open ticket, it is what the evidence supports today.  Guessing any of the
other 7 one way or the other here would be exactly the "invented type
column" `skill_catalog.py` already refused to build.  A classifier for them
would need a NEW ticket (the result letter's own suggestion: at least 8 more
rows, independently labeled 2 single-target + 2 AOE + 2 self-buff + 2 heal,
alongside these 8 as controls) — no such ticket exists yet as of this round.
`resolve_skill_damage` therefore REFUSES every id but 99 by name, loudly,
instead of silently treating it as zero damage or silently treating it as an
attack.

ZERO PRODUCTION CALLERS THIS ROUND.  `mob_combat.attack_from_observed_action`
reads only `field_qword_20` (the target identity) from the inbound
`ActionVital` fields — no field it consumes today carries a skill id, so
there is nothing for the real combat-hit path to key `resolve_skill_damage`
off of.  Round `go74te` confirmed this by reading the parser
(`current/pf_login_game_server_v141.py:parse_action_vital`), which decodes
several fields `mob_combat.py`'s combat dispatch never reads
(`action_u32_30`, `field_u32_34`, `field_u8_48`, `field_u16_4a`,
`field_u8_4c`).

    CORRECTION (round `ltahoi`, pf-adversary this round, D2): a DRAFT of this
    docstring and of the CORE-REQUEST letter both said these five fields are
    unread by "`action_ack.py`/`mob_combat.py`" — that is FALSE of
    `action_ack.py`.  `action_ack.parse_scene006_ea7d` and
    `make_scene007_action_ack` read and strictly gate on all five, for a
    DIFFERENT EA7D consumer than combat: the SCENE-006/007 relocation
    acknowledgement wired from `scene_load.py:173`'s
    `SceneActionAck(action=0xEA7D, target_identity=0x203D, scene_id=1)` --
    a frame is refused outright (returns ``None``) unless `action_u32_30 ==
    0xEA7D` and `field_u16_4a == 1` exactly.  Whether that is the SAME wire
    shape the client sends when a player clicks to attack, or a distinct one,
    is not established here -- this module does not touch either consumer
    and does not resolve that question, it only refuses to repeat the wrong
    claim.  See the CORE-REQUEST letter for the collision this raises for
    whoever answers it.

One of the five fields may be the skill id, but which one is not
established, and this module does not guess.  A `CORE-REQUEST` asking chief
to name that field went out the same round this module was added
(`pf_bridge/notes_to_chief/20260904_1041_...md`).  Until that request is
answered and LANE-B or chief writes the call site, this function has no
caller anywhere in this repository — a fact this docstring states directly
per `COO-DECISION 20260904_0943` item (c), rather than leaving a reader to
infer it from an absent grep hit.
"""
from __future__ import annotations

from . import skill_catalog
from .mob_combat import Combatant, resolve_damage

__all__ = [
    "Combatant",
    "resolve_damage",
    "DamageBySkillError",
    "is_classified_attack_skill",
    "resolve_skill_damage",
]

# The one starting-kit skill id with an unambiguous client-given attack
# title.  See the module docstring for why the other 7 are refused rather
# than guessed one way or the other.
_ATTACK_SKILL_IDS = (99,)


class DamageBySkillError(RuntimeError):
    """Raised for a skill id this module cannot yet resolve damage for."""


def is_classified_attack_skill(skill_id: int) -> bool:
    """True only for a starting-kit skill id this module classifies as an
    attack.  False for every other known id (movement, basic-training) and
    for an id outside the starting-kit catalog altogether — callers that need
    to tell those two "false" cases apart should call
    ``skill_catalog.is_known_skill_id`` themselves first."""
    return skill_id in _ATTACK_SKILL_IDS


def resolve_skill_damage(
    skill_id: int, attacker: Combatant, defender: Combatant
) -> int:
    """The formula, gated by skill id.

    Raises :class:`DamageBySkillError` for a skill id outside the 8-skill
    starting-kit catalog (unknown id) or inside it but not yet classified as
    an attack (known id, no verdict yet — see the module docstring).
    Otherwise defers to :func:`resolve_damage` unchanged: this function adds
    a gate, not a second formula.
    """
    if not skill_catalog.is_known_skill_id(skill_id):
        raise DamageBySkillError(
            "skill_id %r is not in the starting-kit catalog "
            "(skill_catalog.STARTING_KIT_SKILL_IDS) -- this module only "
            "resolves damage for the 8 named starting-kit skills" % (skill_id,)
        )
    if not is_classified_attack_skill(skill_id):
        raise DamageBySkillError(
            "skill_id %r (%r) is a known starting-kit skill but is not yet "
            "classified as an attack skill -- RE-232 (s_CAST_CONDITION/"
            "s_CAST_BEHAVIOR token grammar) came back BOUNDED-NEGATIVE and "
            "does not classify it either way; refusing rather than guessing" % (
                skill_id, skill_catalog.skill_title(skill_id))
        )
    return resolve_damage(attacker, defender)
