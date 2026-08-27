"""LANE-B / GT-DIAG-MULTI-OBJECT-001: five objects, each one field from D0.

SUPERSEDED BODY PICK -- READ THIS FIRST.  ADDENDUM 20:18 (+07:00, the SAME
day, landed on main after this module was built and pf-adversary-reviewed)
has the owner naming the body herself: Mountain Deer, MOBS n_ID 27, NOT
Jungle Big Tiger (template 60, below).  Mountain Deer is not a member of
bg0001's mined roster (:data:`field_mobs.HOSTILE_PLACEMENTS`), so
:func:`_control_body` -- which only searches that roster -- cannot find it;
swapping to it needs a fresh mine of MOBS/MOBS_TIP/STANDARD_MOB for n_ID 27
(this module's ``_control_body`` docstring below explains why it insists on
a roster row rather than composing one), AND a new entry in
mob_death.WIDENING_RULINGS covering template 27, which the existing
bg0001 ruling's covered set does NOT include.  Both are next round's work,
not done here.  Everything below still answers ADDENDUM 19:05's original
two-criteria question (aggro + EXP) correctly for the body it names; it is
the OWNER'S OWN LATER, MORE SPECIFIC DECISION that supersedes the pick, not
a defect in the reasoning below.

WHAT THIS MODULE IS FOR.  PANYA-ORDER 2026-08-27 18:55 (+07:00, ADDENDUM 19:05)
asks for one boot that answers RE-107, RE-108 and RE-109 at once by placing
five objects near the owner's test point and varying exactly one field per
object against a shared control, D0.  The owner's own rule: "every object must
equal the control byte for byte except the one field meant to differ, and that
difference must be proven by a byte-diff of the real frame, not by intent in
the code."  This module is that composition layer.  It sends nothing, opens no
socket and schedules nothing; :mod:`runtime` (the chief's file) is the only
thing that can put these bytes on a wire, through one CORE-REQUEST call site
this module exists to make small.

WHY THE BODY IS A REAL FIELD MONSTER, NOT TORNADO EAGLE.  The order's first
draft used Tornado Eagle; ADDENDUM 19:05 forbids it and asks for a monster
that (a) has aggro AI and (b) grants EXP, "so that it is unmistakably born as
a monster" rather than a re-flagged NPC.  ``field_mob_ai_tables.AI_WANDER_ROWS``
already carries a mined, committed ``n_AGGRO`` column.  Checked against every
row of ``field_mobs.HOSTILE_PLACEMENTS`` (bg0001's own roster, itself filtered
on "a MOBS row with a rank AND a combat AI" -- the project's own standing test
for "a real monster, not a story NPC wearing the MOBS table"), exactly THREE
have a nonzero ``n_AGGRO`` (all 1200, via ``ai_wander=11``): placement 58
(Jungle Big Tiger, template 60, level 37), placement 63 (Ward Apes, template
65, level 43) and placement 132 (Orc Chief, template 103, level 58).  This
module picks Jungle Big Tiger, the lowest-level of the three, over the
order's own example (Mountain Deer, a different scene entirely) to avoid
opening new cross-scene RE for a criterion bg0001 already answers with mined,
committed, digest-pinned data, and to keep the diagnostic body away from the
higher-level pair on no stronger reason than "smaller number" -- a
tie-breaker, not a claim that level matters to the test.

``CONSTDATA_TH__MOBS.tsv`` row 60 reads ``f_RATIO_EXP=1.0`` (a normal,
nonzero EXP ratio); the two hand-placed story NPCs checked for contrast
(rows 1 and 2) both read ``f_RATIO_EXP=0.0``.  That contrast is this module's
only "grants EXP" evidence.

    [LANE-B ASSUMPTION - PROVISIONAL, awaiting RE/COO confirmation]
    ``f_RATIO_EXP`` is read here as a "grants EXP" signal by contrast with
    the two NPC rows checked above, not because the column's semantics are
    RE-proven.  An earlier draft of this docstring also cited
    ``n_MOB_APPEAR`` and a pair of "per-NPC ids" (8700001/8700002) as a
    second signal; pf-adversary (this round) checked the table directly and
    found both halves wrong -- ``n_MOB_APPEAR=1`` is the value on 2,960 of
    3,210 rows (92%), not a distinguishing mark, and 8700001/8700002 are
    ``n_DROPS_QUEST`` values, not any per-NPC id field.  That second signal
    is retracted rather than kept as decoration; ``f_RATIO_EXP`` alone is
    what this pick stands on.  If RE or the owner reads that differently,
    only ``DIAG_BODY_TEMPLATE_ID`` and this docstring change; nothing
    downstream names the monster.

WHERE THE FIVE OBJECTS GO.  ``DIAG_CENTER_X/Y`` are the owner's own test point
(PANYA-ORDER, unchanged by the addendum).  ``DIAG_CENTER_Z`` is 2231.17 --
NOT a placeholder: it is placement 19's own ``z`` from ``population.py``'s
real bg0001 census, the closest real placement to (X=11865, Y=6147) at
~931 units, and every other real placement within ~3,000 units (indices 4,
59, 46, 9, 47, 14) reads ``z`` in the same 2200-2250 band -- pf-adversary
(this round) pulled these numbers after an earlier draft carried ``0.0``
here, borrowed from a DIFFERENT scene's precedent
(``PANYA-DECISION scene17 provisional arrival xyz 0 0 0``, 2026-08-27 14:45)
without checking bg0001's own already-committed census first.  A boot at
Z=0 in a scene whose ground sits ~2200 units up would have printed all five
``DIAG`` console lines and passed every test in this file while placing
every object far outside anything the owner's camera could see -- exactly
the failure mode the order's own "prove headless before calling the owner"
gate exists to catch, and byte composition alone cannot catch it.  This is
still a nearest-neighbour estimate, not a terrain query at the exact point,
so it is labelled accordingly below.  The four cardinal slots
sit at ``DIAG_RADIUS`` on the clock face the order asks for (12/3/6/9); the
fifth sits further out on the same face, at ``DIAG_FAR_RADIUS``, per "a fifth
a little further out".  Placement indices start at ``DIAG_PLACEMENT_BASE``
(9000), a range no real ``.npc`` placement in this project has ever reached
(bg0001's own roster tops out under 150), so ``FieldMob.actor_identity``
(``0x2000 + placement_index + 1``) cannot collide with a live census member.

WHAT DIFFERS FROM D0, OBJECT BY OBJECT, AND WHY EACH IS ALREADY BUILDABLE.

    D0  (control)   Jungle Big Tiger, spawned and killed exactly the way
                     production does today: :func:`field_mobs.hostile_actor_entry`
                     for the census, :func:`mob_death.kill` at its default
                     ``hold_ms`` for the death pair.  Answers RE-108's "does a
                     click open the target panel, does Tab" baseline and
                     RE-107/RE-109's shared reference point.

    D1a (RE-107)    Same alive entry as D0.  On death, the ONLY difference is
                     the schedule: :func:`mob_death.kill` called with
                     ``hold_ms=int(mob_death.DYING_TIMER_SECONDS * 1000)``
                     (20000) instead of the production default (700).  The
                     dying and dead FRAME BYTES are therefore byte-identical
                     to D0's; only the gap between sending them changes.  That
                     identity is exactly the byte-diff proof this object
                     needs, and :mod:`mob_death` already exposes the keyword
                     that makes it -- no new composer.

    D1b (RE-107)    Same alive entry as D0.  On death, sends ONLY the dead
                     frame (:func:`mob_death.dead_frames`), never the dying
                     frame, and only once the caller attests the client has
                     already been sent a ``TargetVital`` for this identity
                     (the order's "model-loaded bit").  This lane has no
                     session state that could observe that itself --
                     :func:`dead_only_schedule` refuses unless the caller
                     passes ``target_vital_seen=True``, which pushes the
                     actual gate to wherever that observation already lives
                     (chief's dispatch), rather than this lane guessing at it.

    D2  (RE-109)    Byte-identical to D0 in every field except identity and
                     position: a second copy of the SAME proven hostile body
                     (GT-032's own faction pairing, unchanged -- "the dark-red
                     control we already have, not a new guess").  Its purpose
                     is a second on-screen reference point next to D0/D1x/D3
                     in the same capture, not a new production value.

    D3  (RE-109)    Same body fields as D0 (template, preset, name, HP, scene)
                     but composed WITHOUT the hostile faction splice --
                     ``legacy.make_npc_attr(...)`` directly, the exact
                     "named + HP, no faction" case ``field_mobs`` documents as
                     what a plain town NPC entry already looks like on the
                     wire, and what ``hostile_npc_attr`` calls its own
                     ``baseline`` before splicing.  No new field value is
                     invented; this object only withholds one that D0 adds.

NOT IN THIS ROUND.  The order's D2/D3 row also names a second, harder question
(does an alternate value inside FONT_COLOR's ``0x070C`` mask make an
un-aggroed NPC's name a *different* shade) that RE-109 left at method ceiling
for lack of a crosswalk.  Building that would mean guessing a byte this
project has an explicit rule against guessing, so it stays out: D2 here is the
repeat-control reading of the order's table, not the alternate-value reading.
If RE or the owner wants the alternate-value object built, it needs a value
with provenance first; that is RE's decision, not this lane's guess.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from . import field_mobs
from . import mob_death
from .field_mobs import FieldMob

# Convention marker only; nothing in this tree branches on it.
production_allowed = True
test_only = False

# The one line this lane owes the chief, written where a reader of the module
# finds it rather than only in a PR body -- same convention as
# mob_death.MOB_DEATH_WIRING.
GT_DIAG_MULTI_OBJECT_WIRING = (
    "Behind a diagnostic-only boot config (env var, same shape as "
    "PF_GM_ACCOUNTS_CONFIG -- never on by default): (1) census assembly adds "
    "alive_entry(legacy, obj) for each of diagnostic_objects() into the "
    "collection this scene sends, and prints describe_diag_object(obj) for "
    "each one at that point (one console line per object, the format the "
    "owner's order asks for); (2) the roster _dispatch_mob_combat resolves "
    "targets against must also resolve these five identities while the "
    "config is active, so an attack on one reaches mob_combat at all; "
    "(3) on death, dispatch by obj.label: D0/D2 -> kill_schedule(legacy, "
    "obj, outcome, register) (the production hold_ms); D1a -> "
    "dying_timer_hold_schedule(legacy, obj, outcome, register) (same call, "
    "20s hold); D1b -> dead_only_schedule(legacy, obj, "
    "target_vital_seen=<whatever this dispatch already tracks about a prior "
    "TargetVital for that identity, if anything does>) -- if nothing already "
    "tracks that, say so in the reply rather than passing True to get past "
    "the refusal, since that is the one fact this object exists to test; D3 "
    "needs no death handling, it is not expected to reach zero HP in this "
    "round. D0/D2/D1a's calls above (kill_schedule/dying_timer_hold_schedule) "
    "pass DIAG_WIDENED_RULING, mob_death's own already-registered bg0001 "
    "ruling (template 60 is in its covered set), not a new one -- D1b does "
    "NOT: dead_only_schedule calls mob_death.dead_frames() directly, which "
    "carries no identity/template gate at all (only kill() does), so no "
    "widened= applies there; D3 calls neither, per the line above."
)

# The owner's test point (PANYA-ORDER 18:55, unchanged by ADDENDUM 19:05).
DIAG_CENTER_X = 11865.0
DIAG_CENTER_Y = 6147.0
# [LANE-B ASSUMPTION - PROVISIONAL, awaiting COO/attended confirmation] --
# nearest-neighbour estimate from population.py's own bg0001 census
# (placement 19, ~931 units from this point, z=2231.17; every other real
# placement within ~3000 units reads z in the same 2200-2250 band), NOT a
# terrain query at the exact point.  See the module docstring for why 0.0
# (an earlier draft, borrowed from a different scene) was wrong here.
DIAG_CENTER_Z = 2231.17
DIAG_RADIUS = 275.0
DIAG_FAR_RADIUS = 450.0

# Placement-index range reserved for this diagnostic: no real bg0001 .npc
# placement has ever reached four digits (the roster tops out under 150), so
# FieldMob.actor_identity (0x2000 + placement_index + 1) cannot collide with a
# live census member.
DIAG_PLACEMENT_BASE = 9000

# Jungle Big Tiger: field_mobs.HOSTILE_PLACEMENTS placement 58, template 60.
# Picked over the order's own example (Mountain Deer) because this scene's
# already-mined, digest-pinned data answers the addendum's two criteria
# without opening new cross-scene RE -- see the module docstring.
DIAG_BODY_TEMPLATE_ID = 60

# mob_death.kill() refuses any target that is not the sanctioned first target
# (0x201F, Tornado Eagle) unless the caller names a ruling from
# mob_death.WIDENING_RULINGS, and even then only if mob.template_id is in
# that ruling's covered set -- the gate is BY TEMPLATE, not by identity or
# scene (mob_death.py says so of itself, in its own [OPEN RISK] note on this
# exact ruling).  "COO-RULING-20260827-1350 widen-death-scope-bg0001" covers
# template 60 (Jungle Big Tiger, DIAG_BODY_TEMPLATE_ID below), so this
# diagnostic's synthetic placements of that same body pass the gate under
# the ruling's own exact wording -- no paraphrase, no new ruling needed.
# What that [OPEN RISK] note flags, and what this comment is flagging back:
# the ruling's PROSE only ever named bg0001's 13 real placements, and this
# module is the first caller to reach kill() with a template-60 mob that is
# NOT one of them.  mob_death.py's own gate design already decided that is
# authorised; this is not a new assumption on top of it, but the round note
# says so plainly for RE/COO to correct if they read the ruling narrower.
DIAG_WIDENED_RULING = "COO-RULING-20260827-1350 widen-death-scope-bg0001"

DIAG_LABEL_CONTROL = "D0"
DIAG_LABEL_DYING_TIMER_HOLD = "D1a"
DIAG_LABEL_DEAD_ONLY_AFTER_TARGET = "D1b"
DIAG_LABEL_REPEAT_CONTROL = "D2"
DIAG_LABEL_NO_FACTION_SPLICE = "D3"

DIAG_LABELS = (
    DIAG_LABEL_CONTROL,
    DIAG_LABEL_DYING_TIMER_HOLD,
    DIAG_LABEL_DEAD_ONLY_AFTER_TARGET,
    DIAG_LABEL_REPEAT_CONTROL,
    DIAG_LABEL_NO_FACTION_SPLICE,
)

# Clockwise from 12, then the fifth object further out on the same face.
_CLOCK_UNIT_OFFSETS = (
    (0.0, 1.0),    # 12 o'clock
    (1.0, 0.0),    # 3 o'clock
    (0.0, -1.0),   # 6 o'clock
    (-1.0, 0.0),   # 9 o'clock
)
_FAR_UNIT_OFFSET = (0.70710678, 0.70710678)  # northeast, further out


class MobDiagContractError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def _diag_position(slot: int) -> tuple[float, float, float]:
    if slot < 4:
        dx, dy = _CLOCK_UNIT_OFFSETS[slot]
        radius = DIAG_RADIUS
    elif slot == 4:
        dx, dy = _FAR_UNIT_OFFSET
        radius = DIAG_FAR_RADIUS
    else:
        raise MobDiagContractError("only five diagnostic slots are defined")
    return (
        DIAG_CENTER_X + dx * radius,
        DIAG_CENTER_Y + dy * radius,
        DIAG_CENTER_Z,
    )


def _control_body() -> FieldMob:
    """Jungle Big Tiger's real row, every field but placement/xyz untouched."""
    for mob in field_mobs.load_roster():
        if mob.template_id == DIAG_BODY_TEMPLATE_ID:
            return mob
    raise MobDiagContractError(
        "template %d is not in the mined bg0001 roster any more; "
        "regenerate field_mob_tables or pick a different body" %
        DIAG_BODY_TEMPLATE_ID)


def _diag_mob(slot: int) -> FieldMob:
    body = _control_body()
    x, y, z = _diag_position(slot)
    return FieldMob(
        DIAG_PLACEMENT_BASE + slot, body.template_id, x, y, z,
        body.visual_preset, body.display_name, body.level, body.rank,
        body.ai_wander, body.ai_combat, body.speed_walk, body.max_hp,
        body.drops_normal, body.drops_equipment, body.drops_specially,
    )


@dataclass(frozen=True)
class DiagObject:
    """One of the five: its label, the one thing that differs from D0, and
    the ``FieldMob`` record that carries its identity and position."""

    label: str
    differs_from_d0: str
    mob: FieldMob


def diagnostic_objects() -> tuple[DiagObject, ...]:
    """The five objects, D0 first, in the order the owner will walk them."""
    return (
        DiagObject(DIAG_LABEL_CONTROL,
                   "(none -- this is the control)", _diag_mob(0)),
        DiagObject(DIAG_LABEL_DYING_TIMER_HOLD,
                   "death schedule hold_ms: 20000 instead of 700",
                   _diag_mob(1)),
        DiagObject(DIAG_LABEL_DEAD_ONLY_AFTER_TARGET,
                   "death schedule: dead frame only, no dying frame, "
                   "gated on a prior TargetVital for this identity",
                   _diag_mob(2)),
        DiagObject(DIAG_LABEL_REPEAT_CONTROL,
                   "(none but identity/position -- a second D0 for "
                   "on-screen comparison)", _diag_mob(3)),
        DiagObject(DIAG_LABEL_NO_FACTION_SPLICE,
                   "NPCAttr composed without the hostile faction splice "
                   "(legacy.make_npc_attr directly, no BASIC_BIT_FACTION)",
                   _diag_mob(4)),
    )


def alive_entry(legacy: Any, obj: DiagObject) -> bytes:
    """The spawn-census entry for one diagnostic object.

    D0/D1a/D1b/D2 all use the exact production hostile builder.  D3 is the
    one exception: it calls the legacy NPCAttr composer directly, the same
    call :func:`field_mobs.hostile_npc_attr` makes internally as its
    unspliced ``baseline``, wrapped in the same actor-entry/movement shape
    :func:`field_mobs.hostile_actor_entry` uses so the two are diffable.
    """
    if obj.label == DIAG_LABEL_NO_FACTION_SPLICE:
        npc_attr = legacy.make_npc_attr(
            obj.mob.template_id, obj.mob.actor_identity,
            field_mobs.SCENE_ID, field_mobs.SCENE_SEQUENCE,
            obj.mob.visual_preset, obj.mob.max_hp, obj.mob.max_hp,
            basic_name=obj.mob.display_name,
        )
        movement = legacy.make_remote_movement_attr(
            obj.mob.actor_identity, obj.mob.x, obj.mob.y, obj.mob.z,
            field_mobs.HEADINGS[obj.mob.placement_index & 3],
            mask=field_mobs.FULL_MOVEMENT_MASK,
        )
        return legacy.make_remote_actor_entry(
            field_mobs.NPC_STYLE_ACTOR_TYPE, obj.mob.actor_identity,
            [(field_mobs.NPC_ATTR_ID, npc_attr),
             (field_mobs.MOVEMENT_ATTR_ID, movement)],
        )
    return field_mobs.hostile_actor_entry(legacy, obj.mob)


def kill_schedule(
    legacy: Any, obj: DiagObject, outcome: Any, register: Any = None,
    *, hold_ms: int = mob_death.DEATH_TASK_HOLD_MS,
) -> Any:
    """D0's death: the production pair, at whatever ``hold_ms`` the caller

    asks for.  Only ``DIAG_LABEL_CONTROL`` and ``DIAG_LABEL_REPEAT_CONTROL``
    go through here directly; ``dying_timer_hold_schedule`` is D1a's own
    wrapper over the same call.
    """
    if obj.label not in (DIAG_LABEL_CONTROL, DIAG_LABEL_REPEAT_CONTROL):
        raise MobDiagContractError(
            "kill_schedule is only defined for %s/%s, got %s" % (
                DIAG_LABEL_CONTROL, DIAG_LABEL_REPEAT_CONTROL, obj.label))
    return mob_death.kill(
        legacy, obj.mob, outcome, register, hold_ms=hold_ms,
        widened=DIAG_WIDENED_RULING,
    )


def dying_timer_hold_schedule(
    legacy: Any, obj: DiagObject, outcome: Any, register: Any = None,
) -> Any:
    """D1a's death: the production pair, held for 20s instead of 700ms.

    Everything but ``hold_ms`` is the production default, so the dying and
    dead FRAME BYTES this produces are byte-identical to D0's; only the gap
    between sending them differs.  That identity is the byte-diff proof this
    object exists to make, and it falls straight out of reusing
    :func:`mob_death.kill` rather than composing anything new.
    """
    if obj.label != DIAG_LABEL_DYING_TIMER_HOLD:
        raise MobDiagContractError(
            "dying_timer_hold_schedule is only defined for %s, got %s" %
            (DIAG_LABEL_DYING_TIMER_HOLD, obj.label))
    return mob_death.kill(
        legacy, obj.mob, outcome, register,
        hold_ms=int(mob_death.DYING_TIMER_SECONDS * 1000),
        widened=DIAG_WIDENED_RULING,
    )


def dead_only_schedule(
    legacy: Any, obj: DiagObject, *, target_vital_seen: bool,
) -> tuple[bytes, bytes]:
    """D1b's death: the dead frame alone, refused until the caller attests

    the client has already been sent a TargetVital for this identity.  This
    lane tracks no session state, so the attestation is the caller's --
    typically the chief wiring this module names in its CORE-REQUEST.
    """
    if obj.label != DIAG_LABEL_DEAD_ONLY_AFTER_TARGET:
        raise MobDiagContractError(
            "dead_only_schedule is only defined for %s, got %s" %
            (DIAG_LABEL_DEAD_ONLY_AFTER_TARGET, obj.label))
    if target_vital_seen is not True:
        raise MobDiagContractError(
            "dead_only_schedule refuses without target_vital_seen=True: "
            "the order's D1b tests whether a dead-only reply needs the "
            "client to have already been sent a TargetVital for this "
            "identity, so sending it unconditionally would not test that")
    return mob_death.dead_frames(legacy, obj.mob)


def describe_diag_object(obj: DiagObject) -> str:
    """One console line, exactly the format the order asks for."""
    return "DIAG object=%s variant=%s identity=0x%X pos=(%.4f,%.4f,%.4f)" % (
        obj.label, obj.differs_from_d0, obj.mob.actor_identity,
        obj.mob.x, obj.mob.y, obj.mob.z,
    )


def describe_boot(objects: tuple[DiagObject, ...]) -> tuple[str, ...]:
    """One line per object, in the order the owner will read them off."""
    return tuple(describe_diag_object(obj) for obj in objects)
