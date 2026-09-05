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

[UPDATE, round `qni1p5`, per `COO-DECISION 20260904_1246` ("keep going on
skill-99 damage, do not wait for chief")]: `tests/test_damage_by_skill.py`'s
`test_normal_attack_against_916_with_the_production_pin_attacker` now pins
the exact number this function returns against the house's standard test
field (Training Iron Man, template 916) when handed the REAL production
attacker (`mob_combat.pin_attacker()`, the object `runtime.py` binds to
`MOB_COMBAT_DEFAULT_ATTACKER` today) rather than only the arbitrary stand-in
attacker the rest of this test file uses — 891, re-derived from the named
formula constants, matching `mob_combat.py`'s own existing costing comment
for this defender.  This does not change "zero production callers" above:
the pin proves what this gate WOULD return the day a caller exists, it is
not itself a caller.

[UPDATE, round `plg1ne`, per RE-240 RESULT (`pf_bridge/notes_to_chief/
20260904_1714_RE-240-RESULT-HOTBAR-DISPATCH-EXITS-NO-PRODUCER.md`), which
answers the CORE-REQUEST above]: chief's letter `20260904_1405` closed
CORE-REQUEST `1041` by naming none of the five fields and opening `RE-240`
in its place.  RE-240 came back DONE/BOUNDED-NEGATIVE: the hotbar/skillbar
key dispatcher (`0x450B20`) that the ticket walked for every named
`TOOLBAR*`/`SKILLBAR*` hotkey exits at its epilogue `0x4518F3` before any
frame is built at all -- no call, no producer, no
`ActionVital`/`TriggerCastSkillVital` field write on that route.  So the
skill id is not merely unidentified among the five fields named above; the
route that would have produced the frame carrying it was never reached to
begin with.  The result letter's own next step is an attended capture
(press skill 99 from the hotbar, and separately the WIELD `Z` control, in
the same session, then diff the two decoded frames byte for byte) --
cloud-static work on this question is exhausted until that capture exists.
"Zero production callers" above is unchanged.

[UPDATE, round `88ej1z`, per GT-243 RESULT (`pf_bridge/notes_to_chief/
20260906_0155_KA1A-R320-RESULTS-group2-GT266-257-255-230-243-RE235-237-261.md`
section "GT-243"), the attended capture the update above said this question
was waiting on]: GT-243 itself came back BLOCKED-ON-PRECONDITION -- the run
DB's `character_skills` was empty, so the capture could not press skill 99
specifically -- but the operator captured the WIELD-vs-skill diff anyway
against skill 110 ("Strive Jump", already on the hotbar at Ctrl+1) since the
boot was open for another ticket regardless.  Two decoded `ActionVital`
frames, byte for byte, both reproduced twice:
pressing `Z` with no weapon equipped (`action_u32_30=0x0000EA7E`, matching
`V128_WIELD_ACTION_CODE` exactly) versus clicking the skill 110 hotbar icon
(`action_u32_30=0x0000006E`) -- `0x6E` is 110 decimal, the exact id of the
skill in that slot.  This module still refuses to call this a proven skill-
id field: one matching id, for a skill this module does not classify
(110 is "Strive Jump", not one of the `_ATTACK_SKILL_IDS`), from a ticket
whose own precondition failed, is exactly the single-differing-byte
"CANDIDATE, not proof" case `GT-243`'s own body warned against overclaiming
-- the client's producer for this field has never been traced statically
(`RE-271`, opened the same round as this update, asks for that trace).  What
this update DOES change: the CORE-REQUEST above is answered with a strong
candidate rather than left at "cloud-static work is exhausted" -- see
`candidate_skill_id_from_action_fields` below, which reads the field under
that explicit CANDIDATE label and has no caller in this repository, the
same as everything else in this module today.
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
    "candidate_skill_id_from_action_fields",
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


def candidate_skill_id_from_action_fields(action_fields, wield_action_code):
    """Read `action_u32_30` from a parsed `ActionVital` fields dict and
    return a CANDIDATE skill id, or ``None`` for the no-skill-selected
    (WIELD) case.

    This is a candidate, not a confirmed skill-id accessor -- see the module
    docstring's GT-243 update for exactly what is and is not established.
    Callers must not treat a non-None return as "the skill the player used"
    without accounting for that: today's only evidence is one attended
    capture, for skill 110, which this module does not classify as an
    attack, and the client's producer for this field has never been traced
    statically (`RE-271`).  This function has zero callers in this
    repository -- it exists so the day either RE-271 or a skill-99-specific
    capture lands, wiring a real caller is a one-line change rather than a
    new field lookup written under time pressure.

    ``wield_action_code`` is not hardcoded here: `V128_WIELD_ACTION_CODE`
    lives in the frozen `current/pf_login_game_server_v141.py` (0xEA7E), and
    this module -- like `action_ack.py`'s `parse_scene006_ea7d`, which takes
    its `legacy` module the same way -- takes it as a parameter instead of
    importing v141 or re-declaring the constant, so there is never a second
    copy of that number to drift out of sync with the frozen one.

    ``action_fields`` is whatever `legacy.parse_action_vital` returned (the
    same dict shape `action_ack.py` and `mob_combat.py` already read from);
    only the one key this function needs is required.
    """
    value = action_fields["action_u32_30"]
    if value == wield_action_code:
        return None
    return value
