"""LANE-B / GT-DIAG-MULTI-OBJECT-001: five objects, each one field from D0.

BODY SWAP DONE THIS ROUND (PANYA-DECISION 2026-08-27T20:10+07:00 "M1-P" item
3).  ADDENDUM 20:18 (+07:00, the SAME day, landed on main after this module
was first built and pf-adversary-reviewed) has the owner naming the body
herself: Mountain Deer, MOBS n_ID 27, NOT Jungle Big Tiger (template 60, the
previous pick, kept below as a struck record rather than deleted).  Mountain
Deer is not a member of ANY generated roster -- neither bg0001's
(:data:`field_mobs.HOSTILE_PLACEMENTS`) nor Bg0002's (which this same round
mined for the first time, :data:`field_mob_tables_bg0002.HOSTILE_PLACEMENTS`)
-- so :func:`_control_body`, which used to search a generated roster, now
builds the body directly from a hand-mined row instead (see the
``DIAG_MOUNTAIN_DEER_*`` constants below for the exact figures and their
provenance).  A NEW entry in ``mob_death.WIDENING_RULINGS`` (and its
companion ``WIDENING_RULING_SCENES``) covers template 27 on its own, scoped
to bg0001 (where these diagnostic objects are actually placed) -- see that
dict's own comments in mob_death.py.

~~"Everything below still answers ADDENDUM 19:05's original two-criteria
question (aggro + EXP) correctly for the body it names"~~ -- STRUCK, this
round, by re-checking the SAME table this module already mines from for a
DIFFERENT template.  Mountain Deer's own ``n_AI_WANDER`` is 16
(:data:`field_mob_ai_tables.AI_WANDER_ROWS`\\ [16] = ``n_AGGRO`` 0), the SAME
zero-aggro row "WHY THE BODY IS A REAL FIELD MONSTER" below says most
bg0001 hostiles use and explicitly picked AWAY from; Jungle Big Tiger's
``n_AI_WANDER`` was 11 (``n_AGGRO`` 1200).  So the owner's later, more
specific instruction trades away the FIRST of ADDENDUM 19:05's two original
criteria (aggro AI) -- Mountain Deer is NOT an aggro monster by this
project's own reading of that column.  It keeps the second: Mountain Deer's
``f_RATIO_EXP`` is 1.0, the same "grants EXP" contrast this module's EXP
paragraph below already established (bg0001's hand-placed story NPCs read
0.0).  This module follows the owner's later, more specific, explicitly
provenance-checked instruction rather than re-arguing it -- ADDENDUM 20:18
outranks ADDENDUM 19:05's own criteria where the two disagree, and the
disagreement is recorded here rather than silently absorbed.  Also worth
naming: Mountain Deer's ``n_AI_COMBAT`` is 150, which has no row in
:data:`field_mob_ai_tables.AI_COMBAT_ROWS` (Jungle Big Tiger's 123 did), so
this body carries no mined combat-AI script either -- irrelevant to what
GT-114 actually tests (click/Tab/fall/freeze on a body the server itself
kills, not autonomous monster behaviour), but named here rather than left
for someone else to notice later.

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

WHY THE BODY WAS A REAL FIELD MONSTER, NOT TORNADO EAGLE -- ORIGINAL REASONING,
KEPT FOR THE RECORD, SUPERSEDED BY THE OWNER'S OWN LATER PICK ABOVE.  The
order's first draft used Tornado Eagle; ADDENDUM 19:05 forbids it and asks
for a monster that (a) has aggro AI and (b) grants EXP, "so that it is
unmistakably born as a monster" rather than a re-flagged NPC.
``field_mob_ai_tables.AI_WANDER_ROWS`` already carries a mined, committed
``n_AGGRO`` column.  Checked against every row of
``field_mobs.HOSTILE_PLACEMENTS`` (bg0001's own roster, itself filtered on "a
MOBS row with a rank AND a combat AI" -- the project's own standing test for
"a real monster, not a story NPC wearing the MOBS table"), exactly THREE
have a nonzero ``n_AGGRO`` (all 1200, via ``ai_wander=11``): placement 58
(Jungle Big Tiger, template 60, level 37), placement 63 (Ward Apes, template
65, level 43) and placement 132 (Orc Chief, template 103, level 58).  This
module PICKED Jungle Big Tiger, the lowest-level of the three, over the
order's own example (Mountain Deer, a different scene entirely) to avoid
opening new cross-scene RE for a criterion bg0001 already answered with
mined, committed, digest-pinned data, and to keep the diagnostic body away
from the higher-level pair on no stronger reason than "smaller number" -- a
tie-breaker, not a claim that level matters to the test.

``CONSTDATA_TH__MOBS.tsv`` row 60 reads ``f_RATIO_EXP=1.0`` (a normal,
nonzero EXP ratio); the two hand-placed story NPCs checked for contrast
(rows 1 and 2) both read ``f_RATIO_EXP=0.0``.  That contrast was this
module's only "grants EXP" evidence, and it is re-checked for Mountain Deer
in the module docstring's update above (also 1.0 -- the EXP half of this
reasoning still holds for the NEW body; the aggro half does not, see above).

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

from . import field_mob_tables
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
    "pass DIAG_WIDENED_RULING, mob_death's own dedicated Mountain-Deer "
    "ruling (template 27 is its only covered template, and it is scoped to "
    "scene 'bg0001' in WIDENING_RULING_SCENES, matching this module's own "
    "objects, which are placed here and not at any real Bg0002 placement) "
    "-- D1b does NOT: dead_only_schedule calls mob_death.dead_frames() "
    "directly, which carries no identity/template/scene gate at all (only "
    "kill() does), so no widened= applies there; D3 calls neither, per the "
    "line above."
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

# ~~Jungle Big Tiger: field_mobs.HOSTILE_PLACEMENTS placement 58, template
# 60.~~ SUPERSEDED THIS ROUND by ADDENDUM 20:18's own, later, more specific
# pick.  Kept struck rather than deleted, per this project's own convention.
# DIAG_BODY_TEMPLATE_ID = 60

# MOUNTAIN DEER (MOBS n_ID 27) -- ADDENDUM 20:18's own pick for all five
# GT-114/DIAG-001 objects, superseding the Jungle Big Tiger pick above.  NOT
# a member of ANY generated roster: both field_mob_tables.py (bg0001) and
# field_mob_tables_bg0002.py (Bg0002, mined for the first time this same
# round) exclude it on the SAME ground -- CONSTDATA_TH__MOBS.tsv row 27's
# s_OUTFIT is the two-variant list "M005_000_000_SP1;M005_000_000_SP2",
# which fails tools/pf_mine_scene_mob_roster.py's own "single unambiguous
# basename" selection rule (see that tool's docstring).  So
# :func:`_control_body` cannot find it by searching a mined roster the way
# it used to for template 60; it builds the record from the constants below
# instead, hand-mined from the SAME committed tables at the SAME digests
# field_mob_tables_bg0002.py's own header already records (mobs
# 3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b,
# mobs_tip e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f,
# standard_mob 4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925
# -- CONSTDATA_TH__STANDARD_MOB.tsv, read at level 17, not the placements
# table, since this body has no real placement of its own):
#
#   CONSTDATA_TH__MOBS.tsv row 27: s_ID_MODEL_CLASS M005, n_LEVEL_MIN 17,
#     n_LEVEL_MAX 19, n_RANK 1, n_AI_WANDER 16, n_AI_COMBAT 150,
#     n_SPEED_WALK 100, f_RATIO_EXP 1.0, n_DROPS_NORMAL 2701001,
#     n_DROPS_EQUIPMENT 5400001, n_DROPS_SPECIALLY 2802222.
#   CONSTDATA_TH__STANDARD_MOB.tsv row 17: n_HPMAX 1201.
#   TEXTDATA_TH__MOBS_TIP.tsv row 27: s_NAME "Mountain Deer".
#
# Every one of these was checked against ADDENDUM 20:18's own relayed
# numbers (n_AI_COMBAT 150, n_AI_WANDER 16, f_RATIO_EXP 1.0, drops
# 5400001/2701001/2802222) and AGREES exactly -- the addendum's text is
# correct, but this module cites the primary table, per PANYA-DECISION
# 2026-08-27T20:10+07:00's own instruction to re-derive rather than
# hand-copy a relayed number.
#
# s_OUTFIT carries TWO variants; this diagnostic body deterministically picks
# the FIRST token (M005_000_000_SP1).  This project has no evidence for
# which variant a real spawn would use, so this is a NAMED CHOICE for a
# synthetic diagnostic placement, not a discovery -- it does not need to
# match a real spawn's rule, since Mountain Deer has never had a real
# placement in this project's mined data at all.
DIAG_MOUNTAIN_DEER_TEMPLATE_ID = 27
DIAG_MOUNTAIN_DEER_LEVEL = 17
DIAG_MOUNTAIN_DEER_RANK = 1
DIAG_MOUNTAIN_DEER_AI_WANDER = 16
DIAG_MOUNTAIN_DEER_AI_COMBAT = 150
DIAG_MOUNTAIN_DEER_SPEED_WALK = 100
DIAG_MOUNTAIN_DEER_MAX_HP = 1201
DIAG_MOUNTAIN_DEER_DROPS_NORMAL = 2701001
DIAG_MOUNTAIN_DEER_DROPS_EQUIPMENT = 5400001
DIAG_MOUNTAIN_DEER_DROPS_SPECIALLY = 2802222
DIAG_MOUNTAIN_DEER_VISUAL_PRESET = "M005_000_000_SP1"
DIAG_MOUNTAIN_DEER_DISPLAY_NAME = "Mountain Deer"

DIAG_BODY_TEMPLATE_ID = DIAG_MOUNTAIN_DEER_TEMPLATE_ID

# mob_death.kill() refuses any target that is not the sanctioned first target
# (0x201F, Tornado Eagle) unless the caller names a ruling from
# mob_death.WIDENING_RULINGS, and even then only if mob.template_id is in
# that ruling's covered set AND (this round) mob.scene agrees with whatever
# mob_death.WIDENING_RULING_SCENES ties that ruling to, if anything does.
# Template 27 is deliberately NOT in the bg0001 ruling's covered set (that
# set is the bg0001 roster's own 13 templates) and NOT in the new Bg0002
# roster ruling's covered set either (Bg0002's mining run excludes template
# 27 on the same outfit-ambiguity ground this module's own comment above
# explains) -- so it gets its OWN dedicated ruling, citing the same letter
# and timestamp as the Bg0002 roster ruling (they are two separate sentences
# of the SAME PANYA-DECISION/ADDENDUM), scoped to scene "bg0001" because
# these five objects are placed at DIAG_CENTER_X/Y, a bg0001 point, not at
# any real Bg0002 placement.
DIAG_WIDENED_RULING = (
    "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
    "diag-mountain-deer-template-27"
)

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
    """Mountain Deer's real row, built from the hand-mined constants above.

    Template 27 is not a member of ANY generated roster (bg0001's or
    Bg0002's): both mining runs exclude it on the SAME ground, an ambiguous
    two-variant ``s_OUTFIT`` that fails tools/pf_mine_scene_mob_roster.py's
    own "single unambiguous basename" rule.  So, unlike the earlier
    Jungle-Big-Tiger version of this function, this cannot search a
    generated roster for the row -- the ``DIAG_MOUNTAIN_DEER_*`` constants
    above ARE the row, mined by hand from the same committed tables at the
    same digests, with their own provenance comment.  ``placement_index``
    and ``x``/``y``/``z`` are placeholders here; :func:`_diag_mob`
    overwrites both per slot, and ``scene`` is set to bg0001 (where these
    synthetic objects are actually placed), NOT Bg0002 (where the template's
    stats were mined from) -- see ``DIAG_WIDENED_RULING``'s own comment for
    why that distinction matters to mob_death.kill().
    """
    return FieldMob(
        placement_index=0, template_id=DIAG_MOUNTAIN_DEER_TEMPLATE_ID,
        x=0.0, y=0.0, z=0.0,
        visual_preset=DIAG_MOUNTAIN_DEER_VISUAL_PRESET,
        display_name=DIAG_MOUNTAIN_DEER_DISPLAY_NAME,
        level=DIAG_MOUNTAIN_DEER_LEVEL, rank=DIAG_MOUNTAIN_DEER_RANK,
        ai_wander=DIAG_MOUNTAIN_DEER_AI_WANDER,
        ai_combat=DIAG_MOUNTAIN_DEER_AI_COMBAT,
        speed_walk=DIAG_MOUNTAIN_DEER_SPEED_WALK,
        max_hp=DIAG_MOUNTAIN_DEER_MAX_HP,
        drops_normal=DIAG_MOUNTAIN_DEER_DROPS_NORMAL,
        drops_equipment=DIAG_MOUNTAIN_DEER_DROPS_EQUIPMENT,
        drops_specially=DIAG_MOUNTAIN_DEER_DROPS_SPECIALLY,
        scene=field_mob_tables.SCENE,
    )


def _diag_mob(slot: int) -> FieldMob:
    body = _control_body()
    x, y, z = _diag_position(slot)
    return FieldMob(
        DIAG_PLACEMENT_BASE + slot, body.template_id, x, y, z,
        body.visual_preset, body.display_name, body.level, body.rank,
        body.ai_wander, body.ai_combat, body.speed_walk, body.max_hp,
        body.drops_normal, body.drops_equipment, body.drops_specially,
        scene=body.scene,
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
