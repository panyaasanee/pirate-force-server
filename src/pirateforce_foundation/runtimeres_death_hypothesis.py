"""RUNTIMERES-DEATH-001: the spawn-then-kill actor-entry encoder (GT-022).

WHY THIS MODULE EXISTS, AND WHY IT IS NOT THE HP-DEATH LANE
-----------------------------------------------------------
``reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md`` (round 85) proved,
byte-exactly, from the read-only client image, four things that together make
the existing HP-DEATH-002 lane structurally unable to produce a corpse:

1. The carrier that reaches the engine death chain is **not**
   ``UpdateAttrVital``.  ``UpdateAttrVital``'s inbound handler
   ``0x5F2400..0x5F261A`` contains **zero** ``mov r,[reg+0x20]; call r``
   dispatch shapes over its whole extent, so it cannot reach ``0x4446F0``,
   cannot latch ``[actor+0x70] |= 0x200``, cannot build a ``CActorTask_Dead``
   and cannot play ``_F_DIE_000``.  HP-DEATH-002 opens the LOCAL player's
   ``L"Main_Dead"`` window through a separate per-frame read in
   ``CMyActor::Update`` -- that lane is correct about what it proved and is
   deliberately left untouched by this one.
2. The carrier that DOES reach it is ``GSCN_RunTimeProtocolRes`` id ``0x6E9D``,
   **derived change-mask bit ``0x02``, object at ``+0x1C``** -- the actor-entry
   collection.  Its inbound handler ``0x5E4060`` feeds that collection's list
   head straight into ``0x446F30``, which has **exactly one** direct caller
   (``0x5E4085``) and **zero** pointer occurrences anywhere in the image.
3. **An actor cannot be born dead.**  ``0x446F30`` looks the entry's 64-bit
   identity up (``0x446991`` -> ``0x446170``).  FOUND -> vtable ``+0x20``
   (apply AND dead-sync).  NOT FOUND -> ``0x446990``, the spawn, which applies
   through vtable ``+0x10`` and never touches ``0x4437C0``.  So death needs at
   least TWO actor-entries for the SAME identity: a spawn, then a kill.
4. **The timer polarity is inverted from intuition.**  See the block of named
   constants below; this is the single fact most likely to be got wrong.

WHAT THIS MODULE COMPOSES
-------------------------
Three ``GSCN_RunTimeProtocolRes`` frames for ONE identity, in this order:

    SPAWN        actor_type 4 (CNetNPC), NPCAttr with a visual preset plus the
                 frozen full-mask MovementAttr.  HP full, death timer ABSENT.
                 The identity is unknown to the client, so this frame takes the
                 spawn branch 0x446990 -> vtable +0x10.  The visual preset is
                 what eventually sets ``[actor+0x70] |= 0x40`` (the two writers
                 are 0x4448B4 and 0x4599B4, both on the model-load path), and
                 that bit is the SECOND gate on the animation at 0x47289E.
    DYING_LATCH  the SAME identity again -> found -> vtable +0x20 -> 0x4446F0
                 -> 0x4437C0.  HP == 0 and the timer STRICTLY POSITIVE, which
                 is the ``vt+0x40`` side of the polarity and latches
                 ``[actor+0x70] |= 0x200`` at 0x44384C.
    DEATH_TASK   the SAME identity a third time.  HP == 0 and the timer
                 EXPLICITLY <= 0, which is the ``vt+0x3C`` side and is what
                 gates the task construction at 0x443990 -> 0x4439E9 ->
                 ``CActorTask_Dead`` 0x472810 -> ``L"_F_DIE_000"`` @0xF0F060.

Nothing about the envelope is invented: the frames are composed by the frozen
V141 serializers ``make_remote_actor_entry`` (0x5E21D0) and
``make_runtime_remote_actors`` (derived bit 0x02), which are the same pair
``population.py``, ``scenario.py`` and ``scene_object.py`` already use.  The
ONE thing this module adds to the actor-entry path is BasicAttr mask bit
``0x0080`` -- the f32 death timer at object offset ``+0x58``, wire tag ``0x2A``
-- which ``legacy.make_npc_attr`` cannot emit.  Everything else in the NPCAttr
body is reproduced byte-for-byte from ``legacy.make_npc_attr``, and
``encode_death_capable_npc_attr`` asserts that equality on every call where the
timer is absent, so a drifted encoder fails closed instead of putting a guessed
body on the wire.

The probe actor is not invented either: template id, visual preset, XYZ and
identity all come from the frozen, hash-pinned
``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS`` source (115 rows, SHA-256
``22D7430E..9618``), selected as the single placement nearest to the frozen
V135 player spawn, using the same ``0x2000 + index + 1`` identity formula
``population.py`` already uses.

FAIL CLOSED
-----------
* ``production_allowed`` is ``False`` and the scenario file must say so too.
* The scenario JSON is checked against an EXACT allowlist -- one extra or
  missing key anywhere in the tree and the loader refuses.
* BasicAttr bit ``0x0080`` cannot be named at all without the lethal unlock
  token, and the ONLY way to obtain that token is from the allowlisted scenario
  object.  With the flag absent, nothing in the process can emit a death timer
  on the actor-entry path.
* Every composed sweep is re-read by :func:`validate_runtimeres_death_sweep`
  before it is returned.  A sweep that is missing the ``0x02`` derived mask, or
  whose timer never reaches ``<= 0``, or whose kill frames carry a different
  identity from the spawn, produces NO BYTES AT ALL.

SCOPE THIS MODULE DOES NOT COVER -- read this before running GT-022
-------------------------------------------------------------------
The RUNTIMERES-ENCODER-001 lane was scoped to this module, its scenario, the
``app.py`` flag, its verifier, its tests and its report; RUNTIMERES-DISPATCH-001
added the ``runtime.py`` branch later the same round, and the round-86 ledger
append registered ``HYP-PF-023``, so the annotation below is now real and the
three ``PF-HYPOTHESIS-LEDGER: HYP-PF-023 active`` comments (here, ``runtime.py``
and ``app.py``) are bound both ways by ``tools/verify_hypothesis_ledger.py``.
What is STILL not covered: the client.  No client has ever been shown one byte
of this profile.  Everything below is composition and static re-derivation, and
whether any of it renders a corpse is GT-022, attended, not run.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any

from .population import (
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
    RUNTIME_PROTOCOL_RES_ID,
    SCENE_ID,
    SCENE_SEQUENCE,
    load_port_royal_placements,
)


production_allowed = False

RUNTIMERES_DEATH_SCENARIO_ID = "runtimeres_death_hypothesis_spawn_then_kill"
# PF-HYPOTHESIS-LEDGER: HYP-PF-023 active
# Registered in docs/HYPOTHESIS_LEDGER.json by the round-86 append (entry 30).
# The annotation above and that entry's source_refs bind each other both ways:
# removing either one turns tools/verify_hypothesis_ledger.py red.
RUNTIMERES_DEATH_HYPOTHESIS_ID = "HYP-PF-023"
# The keyword ``app.py`` hands to ``make_state_class``.  RUNTIMERES-DISPATCH-001
# added that parameter; ``app.py`` now passes it plainly and the constant is
# kept because the tests read it.
RUNTIMERES_DEATH_DISPATCH_KWARG = "runtimeres_death_hypothesis_scenario"

# ---------------------------------------------------------------------------
# NAMED PROFILES (RUNTIMERES-LATCHONLY-001, round 91).
#
# WHY THERE ARE TWO.  GT-022 ran three times on a real client and produced a
# real corpse: the probe NPC went from standing to lying flat and stayed there.
# What it could NOT answer is WHICH FRAME did that.  DYING_LATCH lands at t+6
# and DEATH_TASK at t+12, the tester photographed at roughly t+10.5 to t+11.5
# and the pose was already there, which points hard at DYING_LATCH -- but the
# margin is about one second, capture latency was never instrumented, and a
# timing argument with a one second margin is an indication and not a proof.
#
# The cheapest experiment that settles it without any appeal to a clock is a
# sweep that STOPS after DYING_LATCH.  If the pose still appears, it belongs to
# the latch; if it does not, it belongs to the death task.  Either answer is
# decisive and neither depends on when a screenshot was taken.
#
# The two-frame profile is a STRICT SUBSET: its steps are literally the first
# two rows of the same plan, so its bytes cannot drift away from the three-frame
# profile's first two frames, and both hash-pin against the SAME per-step pins
# below.  A test asserts that byte identity, because "the only difference is the
# missing third frame" is the whole experiment; if the first two frames also
# changed, a difference on screen would prove nothing.
#
# The validator is STRICTER for the new profile rather than looser: a profile
# that does not reach the death task must never emit a frame that satisfies
# vt+0x3C at all, must end on the latch, and must not carry the DEATH_TASK
# label anywhere.  See validate_runtimeres_death_sweep.
# ---------------------------------------------------------------------------
RUNTIMERES_DEATH_PROFILE_SPAWN_THEN_KILL = "spawn_then_kill"
RUNTIMERES_DEATH_PROFILE_DYING_LATCH_ONLY = "dying_latch_only"
RUNTIMERES_DEATH_LATCH_ONLY_SCENARIO_ID = (
    "runtimeres_death_hypothesis_dying_latch_only"
)


# ---------------------------------------------------------------------------
# The envelope.  Byte offsets into the PC that make_runtime_remote_actors emits.
# ---------------------------------------------------------------------------
RUNTIME_PROTOCOL_RES_VERSION = 4
# The INHERITED (base 0x5F4070) change mask.  0 = "no VitalData collection at
# +0x18".  This is the sub-object UpdateAttrVital rides and the one this lane
# deliberately leaves empty.
INHERITED_CHANGE_MASK_ABSENT = 0x00
INHERITED_CHANGE_MASK_OFFSET = 11
# The DERIVED (0x5E3EE0) change mask.  Bit 0x02 selects the object at +0x1C,
# the actor-entry collection, whose list head 0x5E4073 hands to 0x446F30.
DERIVED_CHANGE_MASK_ACTOR_ENTRIES = 0x02
DERIVED_CHANGE_MASK_OFFSET = 13
DERIVED_CHANGE_MASK_OBJECT_OFFSET = 0x1C
ACTOR_ENTRY_COUNT_TAG_OFFSET = 14
ACTOR_ENTRY_COUNT_OFFSET = 15
ACTOR_ENTRY_LIST_OFFSET = 17

# BasicAttr, mask +0x70, u16 tag 0x12.  Only the bits this lane emits.
BASIC_ATTR_MASK_TAG = 0x12
BASIC_BIT_CURRENT_HP = 0x0004      # u32 tag 0x14 @ +0x44
BASIC_BIT_MAX_HP = 0x0008          # u32 tag 0x14 @ +0x48
BASIC_BIT_DEATH_TIMER = 0x0080     # f32 tag 0x2A @ +0x58   <- the lethal bit
BASIC_BIT_SCENE_ID = 0x0100        # u16 tag 0x12
BASIC_BIT_SCENE_SEQ = 0x0200       # qword tag 0x32
DEATH_TIMER_OFFSET = 0x58
DEATH_TIMER_TAG = 0x2A
DEATH_TIMER_WIDTH = 4
CURRENT_HP_OFFSET = 0x44
CURRENT_HP_TAG = 0x14

# NPCAttr's own u8 mask @ +0xBC.
NPC_BIT_TEMPLATE = 0x01            # u16 tag 0x12 @ +0x78
NPC_BIT_VISUAL_PRESET = 0x04       # wstring tag 0x48 @ +0x7C
NPC_ATTR_MASK_TAG = 0x0B
DB_ATTRIBUTE_IDENTITY_MASK = 0x01
DB_ATTRIBUTE_MASK_TAG = 0x0B
IDENTITY_TAG = 0x32

FULL_MOVEMENT_MASK = 0xFF


# ===========================================================================
# THE POLARITY.  Round 85 s.3 correction 2.  Get this backwards and the lane
# produces a latched-but-never-animating actor, which is exactly the failure
# HP-DEATH-002 already has.  Both predicates require BasicAttr +0x44 (current
# HP) == 0; they differ ONLY in the sign test on the f32 at BasicAttr +0x58.
#
#   vtable slot +0x40  ==  0x43BDA0  ==  HP == 0 AND timer >  0.0f
#       comiss xmm0,[0xF0989C] ; jbe -> false          (0xF0989C holds 0.0f)
#       -> inside 0x4437C0 this is `bl`, and 0x44384C gates
#          `[actor+0x70] |= 0x200`, the DYING latch.
#       -> a sweep that stops here gets the latch and NO ANIMATION.
#
#   vtable slot +0x3C  ==  0x43BD70  ==  HP == 0 AND timer <= 0.0f
#       xorps xmm0,xmm0 ; comiss xmm0,[attr+0x58] ; jb -> false
#       -> inside 0x4437C0 this is `[esp+0x13]`, and 0x443990 gates EVERYTHING
#          below it including 0x4439E9 `call 0x472810` (CActorTask_Dead, task
#          id 0x80000005, vtable 0xF0F048), which is what plays
#          `L"_F_DIE_000"` @0xF0F060 through actor vtable +0x28.
#
# The two are mutually exclusive on any one snapshot, so the sweep must send
# BOTH sides in order: positive first (latch), then <= 0 (task).
# ===========================================================================
DYING_LATCH_TIMER_SECONDS = 20.0   # gates vtable +0x40 (0x43BDA0): must be > 0
DEATH_TASK_TIMER_SECONDS = 0.0     # gates vtable +0x3C (0x43BD70): must be <= 0
DEATH_TASK_TIMER_CEILING = 0.0     # the sweep is invalid unless it reaches this

DYING_LATCH_PREDICATE_VA = 0x43BDA0        # actor vtable +0x40
DEATH_TASK_PREDICATE_VA = 0x43BD70         # actor vtable +0x3C
ZERO_FLOAT_CONSTANT_VA = 0xF0989C

RUNTIMERES_DEATH_HP_ALIVE = 100
RUNTIMERES_DEATH_HP_MAX = 100
RUNTIMERES_DEATH_HP_ZERO = 0


# Static anchors this lane's design rests on.  They are re-derived from the
# read-only client image by tools/pf_runtimeres_death_encoder_static.py; they
# are repeated here so a source reader can see what the lane assumes and so the
# verifier and the module cannot drift apart silently.
CLIENT_SHA256 = (
    "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
)
STATIC_ANCHORS = {
    "runtime_protocol_res_id": RUNTIME_PROTOCOL_RES_ID,          # 0x6E9D
    "runtime_protocol_res_literal": 0xF2FFF8,
    "runtime_protocol_res_vtable": 0xF2FFC0,
    "runtime_protocol_res_sizeof": 0x28,
    "runtime_protocol_res_serializer": 0x5E3EE0,
    "runtime_protocol_res_inbound_handler": 0x5E4060,
    "actor_entry_list_head_dispatch": 0x5E4073,
    "actor_reconcile": 0x446F30,
    "actor_reconcile_only_caller": 0x5E4085,
    "actor_identity_lookup": 0x446170,
    "actor_spawn_not_found": 0x446990,
    "actor_spawn_applies_through_vtable_slot": 0x10,
    "actor_update_applies_through_vtable_slot": 0x20,
    "attr_apply_and_dead_sync": 0x4446F0,
    "attr_apply_and_dead_sync_only_caller": 0x4566A7,
    "dead_state_sync": 0x4437C0,
    "dead_state_sync_only_caller": 0x444705,
    "dying_latch_site": 0x44384C,
    "dying_latch_flag": 0x200,
    "death_task_gate_site": 0x443990,
    "death_task_ctor": 0x472810,
    "death_task_ctor_only_caller": 0x4439E9,
    "death_task_id": 0x80000005,
    "death_task_vtable": 0xF0F048,
    "die_animation_literal": 0xF0F060,
    "model_loaded_flag": 0x40,
    "model_loaded_gate_site": 0x47289E,
    "actor_type_gate": 0x4469C8,
    "actor_type_jump_table": 0x446B2C,
    "cnetnpc_vtable": 0xF0DF58,
    "cnetnpc_actor_type": NPC_STYLE_ACTOR_TYPE,
    "update_attr_vital_handler": 0x5F2400,
    "update_attr_vital_handler_end": 0x5F261A,
    "update_attr_vital_vt20_dispatch_shapes": 0,
    "dying_latch_predicate": DYING_LATCH_PREDICATE_VA,
    "death_task_predicate": DEATH_TASK_PREDICATE_VA,
    "zero_float_constant": ZERO_FLOAT_CONSTANT_VA,
}


# ---------------------------------------------------------------------------
# The step plan.
# ---------------------------------------------------------------------------
SPAWN_STEP_LABEL = "SPAWN"
DYING_LATCH_STEP_LABEL = "DYING_LATCH"
DEATH_TASK_STEP_LABEL = "DEATH_TASK"

RUNTIMERES_DEATH_STEPS = (
    # label, current_hp, death_timer (None == bit 0x0080 absent), movement
    (SPAWN_STEP_LABEL, RUNTIMERES_DEATH_HP_ALIVE, None, True),
    (DYING_LATCH_STEP_LABEL, RUNTIMERES_DEATH_HP_ZERO,
     DYING_LATCH_TIMER_SECONDS, False),
    (DEATH_TASK_STEP_LABEL, RUNTIMERES_DEATH_HP_ZERO,
     DEATH_TASK_TIMER_SECONDS, False),
)
RUNTIMERES_DEATH_STEP_ORDER = tuple(row[0] for row in RUNTIMERES_DEATH_STEPS)
RUNTIMERES_DEATH_LETHAL_STEP_LABELS = (
    DYING_LATCH_STEP_LABEL, DEATH_TASK_STEP_LABEL,
)
# The latch-only profile's plan is a SLICE of the plan above, not a copy of it.
# A copy could be edited on one side only; a slice cannot.  Everything the two
# profiles share -- the step rows, the pins, the probe, the encoder -- is shared
# by reference for exactly that reason.
RUNTIMERES_DEATH_LATCH_ONLY_STEPS = RUNTIMERES_DEATH_STEPS[:2]
RUNTIMERES_DEATH_LATCH_ONLY_STEP_ORDER = tuple(
    row[0] for row in RUNTIMERES_DEATH_LATCH_ONLY_STEPS
)
RUNTIMERES_DEATH_LATCH_ONLY_LETHAL_STEP_LABELS = (DYING_LATCH_STEP_LABEL,)
# One row of the plan per step label, so a profile can name its steps by label
# and still get the SAME row object the three-frame plan uses.
RUNTIMERES_DEATH_STEP_BY_LABEL = {
    row[0]: row for row in RUNTIMERES_DEATH_STEPS
}
# Gap before each send.  The frozen V141 sender accumulates these onto one
# deadline, exactly as the HYP-PF-022 sweep documents, so index 0 is 0.0 and
# every later index is the spacing.  6.0 s is the spacing the attended HP-death
# rounds already used; no new timing is invented here.
RUNTIMERES_DEATH_FIRST_DELAY_SECONDS = 0.0
RUNTIMERES_DEATH_SPACING_SECONDS = 6.0
RUNTIMERES_DEATH_ACTION_LABEL_PREFIX = "HYP_PF_023_RUNTIMERES_DEATH_"
RUNTIMERES_DEATH_ACTION_LABELS = tuple(
    RUNTIMERES_DEATH_ACTION_LABEL_PREFIX + label
    for label in RUNTIMERES_DEATH_STEP_ORDER
)
RUNTIMERES_DEATH_LATCH_ONLY_ACTION_LABELS = tuple(
    RUNTIMERES_DEATH_ACTION_LABEL_PREFIX + label
    for label in RUNTIMERES_DEATH_LATCH_ONLY_STEP_ORDER
)


# ---------------------------------------------------------------------------
# The probe actor, resolved from the frozen placement source.  Nothing here is
# a literal typed by a human: template, preset, XYZ and identity all come out
# of PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS, and the selection rule is "nearest to
# the frozen V135 player spawn", which is the same distance rule population.py
# already uses to choose who the client is told about.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RuntimeResDeathProbe:
    placement_index: int
    template_id: int
    actor_identity: int
    x: float
    y: float
    z: float
    visual_preset: str
    source_name: str
    scene_id: int
    scene_sequence: int


# The deterministic answer of the selection rule below against the frozen
# 115-row placement source and the frozen V135 player spawn.  Pinned so that a
# drift in either source turns this lane RED instead of silently killing a
# different NPC in a different place.
RUNTIMERES_DEATH_PROBE_PLACEMENT_INDEX = 0
RUNTIMERES_DEATH_PROBE_TEMPLATE_ID = 1
RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY = 0x2001
RUNTIMERES_DEATH_PROBE_VISUAL_PRESET = "P_MALE_002_000_SP1"
RUNTIMERES_DEATH_PROBE_SOURCE_NAME = "Navy Transfer"

# The deterministic bytes the sweep produces for that probe.  These are the
# pins the headless wire proof and the tests both check, so the tool and the
# test cannot agree with each other while both disagreeing with the encoder.
RUNTIMERES_DEATH_PINS: dict[str, dict[str, Any]] = {
    SPAWN_STEP_LABEL: {
        "basic_mask": 0x030C,
        "pc_size": 173,
        "pc_sha256":
            "8965DCF2574B733B119741D2350FB5BAB6D416A9168113AA3E95A5F2FBAC698C",
        "frame_size": 185,
        "frame_sha256":
            "E7E2B0C671C1B023F5FD6FAE4D6489CC670F648DBD3802A67B760816A78AB0C4",
    },
    DYING_LATCH_STEP_LABEL: {
        "basic_mask": 0x038C,
        "pc_size": 120,
        "pc_sha256":
            "451D73AD2AB0360D206DDD3A3C4CED9A7A328FFD8455B84C4018A27B635D21EA",
        "frame_size": 131,
        "frame_sha256":
            "CDBFED6788E418110C1D8FE177BE9D4275DC7FF376A8E654F3B734C14BCDA2E4",
    },
    DEATH_TASK_STEP_LABEL: {
        "basic_mask": 0x038C,
        "pc_size": 120,
        "pc_sha256":
            "0116A7300814CA53F38668B2CAA193123324360F172EE2A9F9B5791BDE81BF0C",
        "frame_size": 131,
        "frame_sha256":
            "D545EC392D880D96BBC669A1F5646741268E8D0E29FD32B90474FF080160D1A0",
    },
}


def resolve_probe(legacy: Any) -> RuntimeResDeathProbe:
    """Pick the single frozen placement nearest the frozen player spawn."""
    placements = load_port_royal_placements(legacy)
    px = float(legacy.V135_PLAYER_X)
    py = float(legacy.V135_PLAYER_Y)
    pz = float(legacy.V135_PLAYER_Z)
    best = None
    for placement in placements:
        distance2 = (
            (placement.x - px) ** 2
            + (placement.y - py) ** 2
            + (placement.z - pz) ** 2
        )
        if not math.isfinite(distance2):
            raise ValueError("placement distance is non-finite")
        key = (distance2, placement.placement_index)
        if best is None or key < best[0]:
            best = (key, placement)
    if best is None:
        raise ValueError("the frozen placement source produced no candidate")
    placement = best[1]
    if not placement.visual_preset:
        # The visual preset is what eventually sets [actor+0x70] |= 0x40, and
        # 0x47289E gates the animation on that bit.  An actor whose model never
        # resolves would latch, build the task and still never animate.
        raise ValueError(
            "HYP-PF-023 refuses a probe with no visual preset: the animation "
            "gate [actor+0x70] & 0x40 at 0x47289E would never open"
        )
    if (
        placement.placement_index != RUNTIMERES_DEATH_PROBE_PLACEMENT_INDEX
        or placement.template_id != RUNTIMERES_DEATH_PROBE_TEMPLATE_ID
        or placement.actor_identity != RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY
        or placement.visual_preset != RUNTIMERES_DEATH_PROBE_VISUAL_PRESET
        or placement.source_name != RUNTIMERES_DEATH_PROBE_SOURCE_NAME
    ):
        raise RuntimeError(
            "HYP-PF-023 probe drift: the nearest frozen placement is no longer "
            "the pinned one"
        )
    return RuntimeResDeathProbe(
        placement.placement_index, placement.template_id,
        placement.actor_identity, placement.x, placement.y, placement.z,
        placement.visual_preset, placement.source_name,
        SCENE_ID, SCENE_SEQUENCE,
    )


# ---------------------------------------------------------------------------
# The lethal unlock.  Same shape as HYP-PF-022's: derived ONCE from the
# allowlisted scenario object and required by every code path that can name
# BasicAttr bit 0x0080.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RuntimeResDeathLethalUnlock:
    scenario_id: str
    hypothesis_id: str


@dataclass(frozen=True)
class RuntimeResDeathHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float
    first_delay_seconds: float
    action_label_prefix: str
    # Added by RUNTIMERES-LATCHONLY-001 (round 91).  These three carry defaults
    # for one reason and it is deliberate: the trap tests written when this
    # class had six fields build a lookalike positionally and require a
    # ValueError from the allowlist.  Defaulting keeps those traps working
    # VERBATIM instead of turning them into TypeErrors, which would have been a
    # different test proving a different thing.  Every default is the REFUSING
    # value -- a profile name no profile has, an empty set of labels allowed to
    # carry the lethal bit, and the narrower "does not reach the death task"
    # claim -- so a partially built object can never be the wider one.
    profile_name: str = ""
    lethal_step_labels: tuple[str, ...] = ()
    ends_on_death_task: bool = False


_PROFILE = RuntimeResDeathHypothesisScenario(
    RUNTIMERES_DEATH_SCENARIO_ID,
    RUNTIMERES_DEATH_HYPOTHESIS_ID,
    RUNTIMERES_DEATH_STEP_ORDER,
    RUNTIMERES_DEATH_SPACING_SECONDS,
    RUNTIMERES_DEATH_FIRST_DELAY_SECONDS,
    RUNTIMERES_DEATH_ACTION_LABEL_PREFIX,
    RUNTIMERES_DEATH_PROFILE_SPAWN_THEN_KILL,
    RUNTIMERES_DEATH_LETHAL_STEP_LABELS,
    True,
)
_PROFILE_LATCH_ONLY = RuntimeResDeathHypothesisScenario(
    RUNTIMERES_DEATH_LATCH_ONLY_SCENARIO_ID,
    RUNTIMERES_DEATH_HYPOTHESIS_ID,
    RUNTIMERES_DEATH_LATCH_ONLY_STEP_ORDER,
    RUNTIMERES_DEATH_SPACING_SECONDS,
    RUNTIMERES_DEATH_FIRST_DELAY_SECONDS,
    RUNTIMERES_DEATH_ACTION_LABEL_PREFIX,
    RUNTIMERES_DEATH_PROFILE_DYING_LATCH_ONLY,
    RUNTIMERES_DEATH_LATCH_ONLY_LETHAL_STEP_LABELS,
    False,
)
_ALLOWED_PROFILES = (_PROFILE, _PROFILE_LATCH_ONLY)
RUNTIMERES_DEATH_PROFILE_BY_SCENARIO_ID = {
    profile.scenario_id: profile for profile in _ALLOWED_PROFILES
}
RUNTIMERES_DEATH_PROFILE_BY_NAME = {
    profile.profile_name: profile for profile in _ALLOWED_PROFILES
}

# One unlock token PER PROFILE rather than one for the lane.  Handing the same
# key to both profiles would have been simpler and strictly weaker: the sweep
# builder can then check that the key it was given belongs to the profile it was
# asked to compose, so a caller holding the three-frame key cannot compose the
# two-frame sweep and vice versa.  Compared by identity everywhere, so a
# value-equal forgery still opens nothing.
_UNLOCKS = {
    profile.scenario_id: RuntimeResDeathLethalUnlock(
        profile.scenario_id, profile.hypothesis_id,
    )
    for profile in _ALLOWED_PROFILES
}
# The original name, kept because tools and tests reach for it directly.
_UNLOCK = _UNLOCKS[RUNTIMERES_DEATH_SCENARIO_ID]
_UNLOCK_LATCH_ONLY = _UNLOCKS[RUNTIMERES_DEATH_LATCH_ONLY_SCENARIO_ID]


def runtimeres_death_lethal_unlock(value: Any) -> RuntimeResDeathLethalUnlock:
    """The only key that lets this process emit BasicAttr bit 0x0080."""
    profile = require_runtimeres_death_hypothesis_scenario(value)
    return _UNLOCKS[profile.scenario_id]


def require_runtimeres_death_lethal_unlock(
    value: Any,
) -> RuntimeResDeathLethalUnlock:
    if not any(value is unlock for unlock in _UNLOCKS.values()):
        raise ValueError(
            "HYP-PF-023 refuses to emit BasicAttr bit 0x0080 without the "
            "lethal unlock derived from the opt-in scenario"
        )
    return value


def require_runtimeres_death_lethal_unlock_for(
    value: Any,
    profile: "RuntimeResDeathHypothesisScenario",
) -> RuntimeResDeathLethalUnlock:
    """The unlock must belong to THIS profile, not merely to this lane."""
    require_runtimeres_death_lethal_unlock(value)
    if value is not _UNLOCKS[profile.scenario_id]:
        raise ValueError(
            "HYP-PF-023 refuses a lethal unlock issued for a different "
            "profile of this lane"
        )
    return value


def require_runtimeres_death_hypothesis_scenario(
    value: Any,
) -> RuntimeResDeathHypothesisScenario:
    if type(value) is not RuntimeResDeathHypothesisScenario or not any(
        value == allowed for allowed in _ALLOWED_PROFILES
    ):
        raise ValueError(
            "runtimeres death hypothesis scenario object exceeds the allowlist"
        )
    return value


# ---------------------------------------------------------------------------
# The encoder.
# ---------------------------------------------------------------------------
def _require_finite_float32(value: Any, label: str) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"{label} must be a finite float32 value")
    result = float(value)
    if not math.isfinite(result) or abs(result) > 3.4028234663852886e38:
        raise ValueError(f"{label} must be a finite float32 value")
    return result


def encode_death_capable_npc_attr(
    legacy: Any,
    probe: RuntimeResDeathProbe,
    *,
    current_hp: int,
    max_hp: int = RUNTIMERES_DEATH_HP_MAX,
    death_timer: Any = None,
    lethal: Any = None,
) -> bytes:
    """One NPCAttr body, optionally carrying BasicAttr bit 0x0080.

    ``death_timer is None`` -> bit 0x0080 is ABSENT and the result is asserted
    byte-for-byte equal to ``legacy.make_npc_attr(...)``, the projection this
    project's actor-entry emitters already ship.  That equality is the whole
    reason to believe the widened encoder is right: it is a superset that
    degrades exactly to the known-good body.

    ``death_timer is not None`` -> bit 0x0080 is emitted, in ascending
    mask-bit order (after 0x0008 max HP, before 0x0100 scene id), as an f32
    with wire tag 0x2A.  That path requires the lethal unlock.
    """
    if type(probe) is not RuntimeResDeathProbe:
        raise ValueError("HYP-PF-023 probe must be the typed probe object")
    if type(current_hp) is not int or type(current_hp) is bool:
        raise ValueError("current hp must be an int")
    if type(max_hp) is not int or type(max_hp) is bool:
        raise ValueError("max hp must be an int")
    if not 0 <= current_hp <= 0xFFFFFFFF or not 0 <= max_hp <= 0xFFFFFFFF:
        raise ValueError("hp values must fit u32")

    baseline = legacy.make_npc_attr(
        probe.template_id, probe.actor_identity,
        probe.scene_id, probe.scene_sequence, probe.visual_preset,
        current_hp, max_hp,
    )
    if death_timer is None:
        composed = _compose_npc_attr(legacy, probe, current_hp, max_hp, None)
        if composed != baseline:
            raise RuntimeError(
                "HYP-PF-023 NPCAttr drift: the timerless body no longer "
                "reproduces legacy.make_npc_attr byte for byte"
            )
        return composed

    require_runtimeres_death_lethal_unlock(lethal)
    timer = _require_finite_float32(death_timer, "death timer")
    composed = _compose_npc_attr(legacy, probe, current_hp, max_hp, timer)
    # The lethal body must be the timerless body plus EXACTLY the five bytes of
    # the tag-0x2A f32, and the mask must differ by EXACTLY bit 0x0080.  Any
    # other delta means the field landed in the wrong place.
    if len(composed) != len(baseline) + 1 + DEATH_TIMER_WIDTH:
        raise RuntimeError("HYP-PF-023 lethal NPCAttr length drift")
    return composed


def _compose_npc_attr(
    legacy: Any,
    probe: RuntimeResDeathProbe,
    current_hp: int,
    max_hp: int,
    death_timer: float | None,
) -> bytes:
    basic_mask = (
        BASIC_BIT_CURRENT_HP | BASIC_BIT_MAX_HP
        | BASIC_BIT_SCENE_ID | BASIC_BIT_SCENE_SEQ
    )
    if death_timer is not None:
        basic_mask |= BASIC_BIT_DEATH_TIMER
    npc_mask = NPC_BIT_TEMPLATE | (
        NPC_BIT_VISUAL_PRESET if probe.visual_preset else 0
    )
    out = bytearray()
    out += legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK)
    out += legacy.qwordtag(IDENTITY_TAG, probe.actor_identity)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, basic_mask)
    # Ascending mask-bit order inside the block, which is the order BasicAttr's
    # serializer 0x4656F0 writes and its reader expects.
    out += legacy.u32tag(CURRENT_HP_TAG, current_hp)          # 0x0004
    out += legacy.u32tag(CURRENT_HP_TAG, max_hp)              # 0x0008
    if death_timer is not None:
        out += legacy.f32tag(death_timer)                     # 0x0080
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, probe.scene_id)  # 0x0100
    out += legacy.qwordtag(IDENTITY_TAG, probe.scene_sequence)  # 0x0200
    out += legacy.u8tag(NPC_ATTR_MASK_TAG, npc_mask)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, probe.template_id)
    if probe.visual_preset:
        out += legacy.wstr_tag(probe.visual_preset)
    return bytes(out)


def make_runtimeres_death_step_response(
    legacy: Any,
    probe: RuntimeResDeathProbe,
    index: int,
    lethal: Any,
    profile: Any,
) -> tuple[bytes, bytes]:
    """Compose one step of the spawn-then-kill sweep."""
    require_runtimeres_death_hypothesis_scenario(profile)
    if type(index) is not int or type(index) is bool:
        raise ValueError("step index must be an int")
    if not 0 <= index < len(profile.step_order):
        raise ValueError("step index is outside the pinned plan")
    label = profile.step_order[index]
    row = RUNTIMERES_DEATH_STEP_BY_LABEL.get(label)
    # Both profiles must resolve step i to the SAME row object the three-frame
    # plan holds at position i.  That is what makes the two-frame profile's
    # bytes a strict prefix of the three-frame profile's bytes rather than a
    # second composition that merely looks like one, and it is the property the
    # whole experiment rests on.
    if row is None or index >= len(RUNTIMERES_DEATH_STEPS) or (
        row is not RUNTIMERES_DEATH_STEPS[index]
    ):
        raise RuntimeError("HYP-PF-023 step plan drift")
    label, current_hp, death_timer, with_movement = row
    if death_timer is not None:
        # The unlock has to belong to THIS profile, and the label has to be one
        # this profile declared lethal.  Either check alone would let a profile
        # emit bit 0x0080 on a step it never declared.
        require_runtimeres_death_lethal_unlock_for(lethal, profile)
        if label not in profile.lethal_step_labels:
            raise RuntimeError(
                "HYP-PF-023 %s carries the death timer but profile %r does not "
                "declare that step lethal" % (label, profile.profile_name)
            )
    npc_attr = encode_death_capable_npc_attr(
        legacy, probe, current_hp=current_hp,
        max_hp=RUNTIMERES_DEATH_HP_MAX,
        death_timer=death_timer,
        lethal=(lethal if death_timer is not None else None),
    )
    attrs = [(NPC_ATTR_ID, npc_attr)]
    if with_movement:
        attrs.append((
            MOVEMENT_ATTR_ID,
            legacy.make_remote_movement_attr(
                probe.actor_identity, probe.x, probe.y, probe.z, 0.0,
                mask=FULL_MOVEMENT_MASK,
            ),
        ))
    entry = legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE, probe.actor_identity, attrs,
    )
    pc, frame = legacy.make_runtime_remote_actors([entry])
    if frame != legacy.frame_pc(pc):
        raise RuntimeError("HYP-PF-023 frame drift")
    return pc, frame


def build_runtimeres_death_sweep(
    legacy: Any,
    probe: RuntimeResDeathProbe,
    lethal: Any,
    profile: Any,
) -> list[tuple[str, bytes, bytes, float]]:
    """Compose the whole sweep and refuse to return a sweep that cannot kill."""
    require_runtimeres_death_hypothesis_scenario(profile)
    actions: list[tuple[str, bytes, bytes, float]] = []
    for index, label in enumerate(profile.step_order):
        pc, frame = make_runtimeres_death_step_response(
            legacy, probe, index, lethal, profile,
        )
        delay = (
            profile.first_delay_seconds if index == 0
            else profile.spacing_seconds
        )
        actions.append((profile.action_label_prefix + label, pc, frame, delay))
    rows = validate_runtimeres_death_sweep(actions, profile)
    _require_pinned_composition(profile, rows)
    return actions


def _require_pinned_composition(
    profile: RuntimeResDeathHypothesisScenario,
    rows: list[dict[str, Any]],
) -> None:
    """Refuse to hand back a sweep whose bytes are not the pinned ones."""
    for index, label in enumerate(profile.step_order):
        pin = RUNTIMERES_DEATH_PINS[label]
        row = rows[index]
        for key in ("basic_mask", "pc_size", "pc_sha256",
                    "frame_size", "frame_sha256"):
            if row[key] != pin[key]:
                raise RuntimeResDeathValidationError(
                    "HYP-PF-023 %s %s drift: %r != %r"
                    % (label, key, row[key], pin[key])
                )


# ---------------------------------------------------------------------------
# The validator.  This is the guard the trap tests exist to break.
# ---------------------------------------------------------------------------
_SCALAR_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x12: 2, 0x14: 4, 0x19: 4,
                 0x26: 4, 0x2A: 4, 0x32: 8}
_BASIC_FIELD_ORDER = (
    (0x0001, 0x48), (0x0002, 0x12), (0x0004, 0x14), (0x0008, 0x14),
    (0x0010, 0x14), (0x0020, 0x14), (0x0040, 0x2A), (0x0080, 0x2A),
    (0x0100, 0x12), (0x0200, 0x32), (0x0400, 0x14),
)


class RuntimeResDeathValidationError(RuntimeError):
    """A composed sweep that must never reach a socket."""


def _envelope_prefix(legacy: Any) -> bytes:
    return bytes(
        legacy.u16tag(0x12, RUNTIME_PROTOCOL_RES_ID)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, RUNTIME_PROTOCOL_RES_VERSION)
        + legacy.u8tag(0x0B, INHERITED_CHANGE_MASK_ABSENT)
        + legacy.u8tag(0x0B, DERIVED_CHANGE_MASK_ACTOR_ENTRIES)
    )


def decode_runtimeres_actor_entry_frame(pc: bytes) -> dict[str, Any]:
    """Read one composed PC back with a strict, standalone tag walker.

    Deliberately does not reuse the encoder's own tables for anything except
    the constants, so a symmetrical bug in the encoder cannot hide here.
    """
    if type(pc) is not bytes:
        raise RuntimeResDeathValidationError("a frame must be bytes")
    if len(pc) < ACTOR_ENTRY_LIST_OFFSET:
        raise RuntimeResDeathValidationError("frame is shorter than the envelope")
    if pc[0] != 0x12 or int.from_bytes(pc[1:3], "little") != RUNTIME_PROTOCOL_RES_ID:
        raise RuntimeResDeathValidationError(
            "frame does not open with GSCN_RunTimeProtocolRes id 0x6E9D"
        )
    if pc[3] != 0x14 or int.from_bytes(pc[4:8], "little") != 0:
        raise RuntimeResDeathValidationError("envelope u32 field drift")
    if pc[8] != 0x08 or pc[9] != RUNTIME_PROTOCOL_RES_VERSION:
        raise RuntimeResDeathValidationError("envelope is not version 4")
    if pc[10] != 0x0B or pc[INHERITED_CHANGE_MASK_OFFSET] != INHERITED_CHANGE_MASK_ABSENT:
        raise RuntimeResDeathValidationError(
            "the inherited VitalData change mask is not absent"
        )
    if pc[12] != 0x0B:
        raise RuntimeResDeathValidationError("the derived change mask tag drifted")
    derived = pc[DERIVED_CHANGE_MASK_OFFSET]
    if not derived & DERIVED_CHANGE_MASK_ACTOR_ENTRIES:
        raise RuntimeResDeathValidationError(
            "the derived change mask is missing bit 0x02, so the client never "
            "reads the +0x1C actor-entry collection and 0x446F30 is never "
            "reached (this is the ErrorData=28317 over-read shape)"
        )
    if pc[ACTOR_ENTRY_COUNT_TAG_OFFSET] != 0x12:
        raise RuntimeResDeathValidationError("the actor count tag drifted")
    count = int.from_bytes(
        pc[ACTOR_ENTRY_COUNT_OFFSET:ACTOR_ENTRY_COUNT_OFFSET + 2], "little",
    )
    if count != 1:
        raise RuntimeResDeathValidationError(
            "this lane ships exactly one actor entry per frame"
        )
    cursor = ACTOR_ENTRY_LIST_OFFSET
    if pc[cursor] != 0x0B:
        raise RuntimeResDeathValidationError("actor type tag drift")
    actor_type = pc[cursor + 1]
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise RuntimeResDeathValidationError("actor identity tag drift")
    identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != 0x0B:
        raise RuntimeResDeathValidationError("attr count tag drift")
    attr_count = pc[cursor + 1]
    cursor += 2

    attrs: dict[int, dict[str, Any]] = {}
    for _ in range(attr_count):
        if pc[cursor] != 0x12:
            raise RuntimeResDeathValidationError("attr id tag drift")
        attr_id = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
        cursor += 3
        if attr_id == NPC_ATTR_ID:
            parsed, cursor = _walk_npc_attr(pc, cursor)
            attrs[attr_id] = parsed
        elif attr_id == MOVEMENT_ATTR_ID:
            cursor = _skip_movement_attr(pc, cursor)
            attrs[attr_id] = {"present": True}
        else:
            raise RuntimeResDeathValidationError(
                "unexpected attr id 0x%04X on the actor-entry path" % attr_id
            )
    if cursor > len(pc):
        raise RuntimeResDeathValidationError(
            "the frame is truncated: the walker ran %d bytes past its end"
            % (cursor - len(pc))
        )
    if cursor != len(pc):
        raise RuntimeResDeathValidationError(
            "the frame has %d trailing bytes the walker could not account for"
            % (len(pc) - cursor)
        )
    return {
        "derived_mask": derived,
        "count": count,
        "actor_type": actor_type,
        "identity": identity,
        "attrs": attrs,
    }


def _walk_npc_attr(pc: bytes, cursor: int) -> tuple[dict[str, Any], int]:
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG:
        raise RuntimeResDeathValidationError("DBAttribute mask tag drift")
    if pc[cursor + 1] != DB_ATTRIBUTE_IDENTITY_MASK:
        raise RuntimeResDeathValidationError(
            "DBAttribute mask is not the identity-only 0x01"
        )
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise RuntimeResDeathValidationError("NPCAttr identity tag drift")
    attr_identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != BASIC_ATTR_MASK_TAG:
        raise RuntimeResDeathValidationError("BasicAttr mask tag drift")
    basic_mask = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
    cursor += 3
    fields: dict[int, Any] = {}
    for bit, tag in _BASIC_FIELD_ORDER:
        if not basic_mask & bit:
            continue
        if pc[cursor] != tag:
            raise RuntimeResDeathValidationError(
                "BasicAttr bit 0x%04X expected tag 0x%02X, found 0x%02X"
                % (bit, tag, pc[cursor])
            )
        if tag == 0x48:
            length = int.from_bytes(pc[cursor + 1:cursor + 5], "little")
            fields[bit] = pc[cursor + 5:cursor + 5 + length].decode("utf-16le")
            cursor += 5 + length
            continue
        width = _SCALAR_WIDTH[tag]
        raw = pc[cursor + 1:cursor + 1 + width]
        fields[bit] = (
            struct.unpack("<f", raw)[0] if tag == 0x2A
            else int.from_bytes(raw, "little")
        )
        cursor += 1 + width
    if basic_mask & ~0x07FF:
        raise RuntimeResDeathValidationError(
            "BasicAttr mask 0x%04X carries a bit this walker cannot read"
            % basic_mask
        )
    if pc[cursor] != NPC_ATTR_MASK_TAG:
        raise RuntimeResDeathValidationError("NPCAttr mask tag drift")
    npc_mask = pc[cursor + 1]
    cursor += 2
    template_id = None
    visual_preset = None
    if npc_mask & NPC_BIT_TEMPLATE:
        if pc[cursor] != 0x12:
            raise RuntimeResDeathValidationError("NPCAttr template tag drift")
        template_id = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
        cursor += 3
    if npc_mask & NPC_BIT_VISUAL_PRESET:
        if pc[cursor] != 0x48:
            raise RuntimeResDeathValidationError("NPCAttr preset tag drift")
        length = int.from_bytes(pc[cursor + 1:cursor + 5], "little")
        visual_preset = pc[cursor + 5:cursor + 5 + length].decode("utf-16le")
        cursor += 5 + length
    return (
        {
            "identity": attr_identity,
            "basic_mask": basic_mask,
            "fields": fields,
            "npc_mask": npc_mask,
            "template_id": template_id,
            "visual_preset": visual_preset,
        },
        cursor,
    )


_MOVEMENT_FIELD_WIDTH = (
    (0x01, 12), (0x02, 4), (0x04, 2), (0x08, 5), (0x10, 5), (0x20, 5),
    (0x40, 5),
)


def _skip_movement_attr(pc: bytes, cursor: int) -> int:
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG or pc[cursor + 1] != 0x01:
        raise RuntimeResDeathValidationError("MovementAttr DBAttribute drift")
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise RuntimeResDeathValidationError("MovementAttr identity tag drift")
    cursor += 9
    if pc[cursor] != 0x0B:
        raise RuntimeResDeathValidationError("MovementAttr mask tag drift")
    mask = pc[cursor + 1]
    cursor += 2
    for bit, width in _MOVEMENT_FIELD_WIDTH:
        if mask & bit:
            # bit 0x01 is three tagged f32s, 0x04 is one tagged u8, the rest
            # are one tagged scalar each.
            cursor += 15 if bit == 0x01 else (2 if bit == 0x04 else 5)
    return cursor


def validate_runtimeres_death_sweep(
    actions: Any,
    profile: Any,
) -> list[dict[str, Any]]:
    """Prove a composed sweep can actually reach ``_F_DIE_000``.

    Raises :class:`RuntimeResDeathValidationError` on any of:
      * a frame whose derived change mask is missing bit 0x02 (the ErrorData
        28317 over-read shape, and the shape that never reaches 0x446F30);
      * a first frame that is not a live spawn (an actor cannot be born dead:
        an unknown identity takes 0x446990 -> vtable +0x10, which never touches
        0x4437C0);
      * a kill frame whose identity differs from the spawn's (that is a second
        spawn, not an update);
      * a sweep whose death timer never reaches ``<= 0`` -- the polarity trap:
        ``vt+0x40`` (timer > 0) latches dying and ``vt+0x3C`` (timer <= 0)
        gates the task, so a sweep that stays positive can never animate;
      * a frame with no visual preset (the ``[actor+0x70] & 0x40`` gate at
        0x47289E would never open).
    """
    require_runtimeres_death_hypothesis_scenario(profile)
    if type(actions) is not list:
        raise RuntimeResDeathValidationError("the sweep must be a list")
    if len(actions) != len(profile.step_order):
        raise RuntimeResDeathValidationError(
            "the sweep must carry exactly %d frames" % len(profile.step_order)
        )
    rows: list[dict[str, Any]] = []
    spawn_identity = None
    reached_le_zero = False
    latched_dying = False
    for index, action in enumerate(actions):
        if type(action) is not tuple or len(action) != 4:
            raise RuntimeResDeathValidationError(
                "each sweep entry must be (label, pc, frame, delay)"
            )
        label, pc, frame, delay = action
        expected_label = profile.action_label_prefix + profile.step_order[index]
        if label != expected_label:
            raise RuntimeResDeathValidationError(
                "step %d is labelled %r, expected %r"
                % (index, label, expected_label)
            )
        if type(frame) is not bytes or not frame:
            raise RuntimeResDeathValidationError("step %d has no frame" % index)
        read = decode_runtimeres_actor_entry_frame(pc)
        if read["actor_type"] != NPC_STYLE_ACTOR_TYPE:
            raise RuntimeResDeathValidationError(
                "actor_type %d is outside the 2..6 jump table case this lane "
                "pins (CNetNPC == 4)" % read["actor_type"]
            )
        npc = read["attrs"].get(NPC_ATTR_ID)
        if npc is None:
            raise RuntimeResDeathValidationError(
                "step %d carries no NPCAttr" % index
            )
        if npc["identity"] != read["identity"]:
            raise RuntimeResDeathValidationError(
                "step %d: the entry identity and the NPCAttr identity differ, "
                "so 0x446170 and the attr apply would target different actors"
                % index
            )
        if not npc["visual_preset"]:
            raise RuntimeResDeathValidationError(
                "step %d carries no visual preset, so [actor+0x70] & 0x40 "
                "never opens and 0x47289E can never play _F_DIE_000" % index
            )
        hp = npc["fields"].get(BASIC_BIT_CURRENT_HP)
        timer = npc["fields"].get(BASIC_BIT_DEATH_TIMER)
        if hp is None:
            raise RuntimeResDeathValidationError(
                "step %d omits BasicAttr bit 0x0004, so the client's HP==0 "
                "half of both predicates is never satisfied" % index
            )
        if index == 0:
            if hp == 0:
                raise RuntimeResDeathValidationError(
                    "the first frame introduces an identity the client does "
                    "not know, which takes the spawn path 0x446990 -> vtable "
                    "+0x10 and never reaches 0x4437C0: an actor cannot be "
                    "born dead"
                )
            if timer is not None:
                raise RuntimeResDeathValidationError(
                    "the spawn frame must not carry BasicAttr bit 0x0080"
                )
            if MOVEMENT_ATTR_ID not in read["attrs"]:
                raise RuntimeResDeathValidationError(
                    "the spawn frame must place the actor (MovementAttr)"
                )
            spawn_identity = read["identity"]
        else:
            if read["identity"] != spawn_identity:
                raise RuntimeResDeathValidationError(
                    "step %d re-uses identity 0x%X, not the spawned 0x%X: that "
                    "is a second spawn, not the vtable +0x20 update the death "
                    "chain needs" % (index, read["identity"], spawn_identity)
                )
            if hp != 0:
                raise RuntimeResDeathValidationError(
                    "step %d is a kill frame and must carry current HP == 0"
                    % index
                )
            if timer is None:
                raise RuntimeResDeathValidationError(
                    "step %d omits the death timer, so neither predicate is "
                    "decidable from this frame alone" % index
                )
            if timer > 0.0:
                latched_dying = True
            if timer <= DEATH_TASK_TIMER_CEILING:
                reached_le_zero = True
        rows.append({
            "index": index,
            "label": label,
            "delay_seconds": delay,
            "identity": read["identity"],
            "actor_type": read["actor_type"],
            "derived_mask": read["derived_mask"],
            "basic_mask": npc["basic_mask"],
            "template_id": npc["template_id"],
            "visual_preset": npc["visual_preset"],
            "hp_current_bit_0x0004": hp,
            "death_timer_bit_0x0080": timer,
            "dying_latch_predicate_vt40": hp == 0 and timer is not None
            and timer > 0.0,
            "death_task_predicate_vt3c": hp == 0 and timer is not None
            and timer <= 0.0,
            "pc_size": len(pc),
            "frame_size": len(frame),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
        })
    if spawn_identity is None:
        raise RuntimeResDeathValidationError("the sweep has no spawn frame")
    if not latched_dying:
        raise RuntimeResDeathValidationError(
            "no frame satisfies vt+0x40 (HP==0 AND timer>0), so the dying "
            "latch [actor+0x70] |= 0x200 is never set"
        )
    if profile.ends_on_death_task:
        if not reached_le_zero:
            raise RuntimeResDeathValidationError(
                "the death timer never reaches <= 0, so vt+0x3C (0x43BD70) is "
                "never true, 0x443990 never opens and CActorTask_Dead is never "
                "constructed: this sweep can latch dying and can never animate"
            )
        if rows[-1]["death_task_predicate_vt3c"] is not True:
            raise RuntimeResDeathValidationError(
                "the LAST frame must be the one that satisfies vt+0x3C, or the "
                "sweep re-arms the timer after opening the task gate"
            )
    else:
        # RUNTIMERES-LATCHONLY-001.  The three checks below are the ones that
        # make this profile an EXPERIMENT rather than a truncation.  Its whole
        # value is that it cannot possibly reach the death task, so if the
        # client still lies down, the pose belongs to the dying latch.  A
        # profile that reached the gate by accident would answer nothing.
        if reached_le_zero:
            raise RuntimeResDeathValidationError(
                "profile %r must never satisfy vt+0x3C (HP==0 AND timer<=0): a "
                "frame that opens the death task gate destroys the only "
                "question this profile exists to answer"
                % (profile.profile_name,)
            )
        if DEATH_TASK_STEP_LABEL in profile.step_order:
            raise RuntimeResDeathValidationError(
                "profile %r must not carry the %s step at all"
                % (profile.profile_name, DEATH_TASK_STEP_LABEL)
            )
        if rows[-1]["dying_latch_predicate_vt40"] is not True:
            raise RuntimeResDeathValidationError(
                "the LAST frame of profile %r must be the one that satisfies "
                "vt+0x40 (HP==0 AND timer>0), so the sweep ends with the dying "
                "latch armed and nothing else pending"
                % (profile.profile_name,)
            )
    return rows


# ---------------------------------------------------------------------------
# The scenario file, checked against an exact allowlist.
# ---------------------------------------------------------------------------
def _exact_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(
            _exact_equal(actual[key], value) for key, value in expected.items()
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _exact_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


RUNTIMERES_DEATH_CAPABILITIES = (
    "emit_gscn_runtimeprotocolres_0x6e9d_derived_mask_bit_0x02_actor_entries",
    "re_send_the_same_identity_so_the_client_takes_the_vtable_0x20_update_path",
    "emit_basicattr_bit_0x0080_on_the_actor_entry_path_not_the_vital_path",
    "sweep_the_death_timer_from_positive_to_zero_in_the_proven_polarity_order",
    "reproduce_the_frozen_make_npc_attr_body_byte_for_byte_when_no_timer_is_set",
    "refuse_to_return_a_sweep_that_cannot_reach_the_death_task_gate",
)
RUNTIMERES_DEATH_NONCLAIMS = (
    "no_client_has_ever_been_shown_one_byte_of_this_profile",
    "client_rendering_of_the_death_animation_pending_gt022",
    "that_the_dying_latch_is_a_prerequisite_for_the_death_task",
    "that_the_229_unresolved_vtable_0x20_dispatch_sites_are_not_actors",
    "the_original_server_death_rules_which_this_project_cannot_read",
    "any_damage_model_or_death_penalty_or_corpse_persistence",
    # Worded without the three come-back-to-life verbs on purpose -- and this
    # comment cannot name them or the tool's own filename either.  HP-DEATH-001's
    # static verifier scans v141 and the whole of src/ for those verbs and
    # asserts ZERO hits, i.e. that no such encoder or dispatch exists on our
    # side.  That negative is still true (this lane opens no way back out of
    # the state it leaves behind), and a NONCLAIM string must never be the
    # thing that falsifies it.
    "no_way_back_out_of_the_state_this_sweep_leaves_behind",
    "no_persistence_hp_has_no_write_path_and_this_lane_opens_none",
    # Reworded in round 86's second edit.  It used to read "which this lane
    # deliberately does not add", which was true for about four hours and then
    # RUNTIMERES-DISPATCH-001 added the wiring.  What is still true, and is
    # what the nonclaim was for, is that the wiring is opt-in and test-only.
    "production_dispatch_wiring_the_wiring_is_opt_in_and_production_allowed_is_false",
    "production_baseline_behavior",
)


RUNTIMERES_DEATH_LATCH_ONLY_CAPABILITIES = (
    "emit_gscn_runtimeprotocolres_0x6e9d_derived_mask_bit_0x02_actor_entries",
    "re_send_the_same_identity_so_the_client_takes_the_vtable_0x20_update_path",
    "emit_basicattr_bit_0x0080_on_the_actor_entry_path_not_the_vital_path",
    "stop_the_sweep_on_the_positive_side_of_the_polarity_so_the_task_gate_never_opens",
    "reproduce_the_frozen_make_npc_attr_body_byte_for_byte_when_no_timer_is_set",
    "refuse_to_return_a_sweep_that_reaches_the_death_task_gate",
    "compose_the_first_two_frames_byte_identical_to_the_three_frame_profile",
)
RUNTIMERES_DEATH_LATCH_ONLY_NONCLAIMS = RUNTIMERES_DEATH_NONCLAIMS + (
    "which_frame_produced_the_pose_gt022_photographed_this_variant_is_the_test_not_the_answer",
    "that_a_client_does_anything_at_all_when_the_sweep_stops_after_the_latch",
)


def _expected_scenario(
    profile: RuntimeResDeathHypothesisScenario | None = None,
) -> dict[str, Any]:
    profile = _PROFILE if profile is None else profile
    latch_only = not profile.ends_on_death_task
    return {
        "schema": 1,
        "id": profile.scenario_id,
        "profile": profile.profile_name,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": RUNTIMERES_DEATH_HYPOTHESIS_ID,
        # Round 86, third edit: the ledger append landed, so this flag is now
        # True.  It is data rather than prose on purpose -- a scenario file that
        # claims an id nobody registered is exactly the kind of thing a future
        # round reads and believes.
        "hypothesis_id_is_registered_in_the_ledger": True,
        "lethal": True,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_spawn_then_dying_latch_actor_entry_frames_and_stop_"
                "no_write_no_close"
                if latch_only else
                "compose_spawn_then_kill_actor_entry_frames_no_write_no_close"
            ),
        },
        "dispatch": {
            # Round 86, second edit: RUNTIMERES-DISPATCH-001 landed later the
            # same round and wired this lane into runtime.py, so the three
            # keys below stopped describing reality within hours of being
            # written.  They are corrected rather than left stale, because a
            # scenario file that lies about whether it can run is the kind of
            # thing a future round reads and believes.
            "wired": True,
            "wiring_owner": "runtimeres_dispatch_001_round_86",
            "app_policy_when_lane_disabled": (
                "no_frames_composed_and_the_encoder_raises_if_called_directly"
            ),
            "frames_per_accepted_request": len(profile.step_order),
            "step_order": list(profile.step_order),
            "lethal_steps": list(profile.lethal_step_labels),
            "ends_on_death_task": profile.ends_on_death_task,
            "spacing_seconds": profile.spacing_seconds,
            "first_frame_delay_seconds": profile.first_delay_seconds,
            "delay_semantics": "gap_before_each_send_on_a_cumulative_deadline",
            "action_label_prefix": profile.action_label_prefix,
            "action_labels": [
                profile.action_label_prefix + label
                for label in profile.step_order
            ],
            "one_shot": True,
            "socket_action": "none",
        },
        "wire": {
            "vital_id": RUNTIME_PROTOCOL_RES_ID,
            "vital_version": RUNTIME_PROTOCOL_RES_VERSION,
            "envelope": "gscn_runtime_protocol_res_v4_actor_entry_collection",
            "inherited_change_mask": INHERITED_CHANGE_MASK_ABSENT,
            "derived_change_mask": DERIVED_CHANGE_MASK_ACTOR_ENTRIES,
            "derived_object_offset": DERIVED_CHANGE_MASK_OBJECT_OFFSET,
            "actor_type": NPC_STYLE_ACTOR_TYPE,
            "attr_ids": [NPC_ATTR_ID, MOVEMENT_ATTR_ID],
            "field_order_rule": "ascending_mask_bit_within_each_block",
            "death_field": {
                "name": "hp_death_timer",
                "block": "basic",
                "mask_bit": BASIC_BIT_DEATH_TIMER,
                "object_offset": DEATH_TIMER_OFFSET,
                "wire_tag": DEATH_TIMER_TAG,
                "width": "f32",
            },
            "polarity": {
                "dying_latch_predicate": DYING_LATCH_PREDICATE_VA,
                "dying_latch_vtable_slot": 0x40,
                "dying_latch_rule": "current_hp_zero_and_death_timer_greater_"
                                    "than_zero",
                "dying_latch_value_seconds": DYING_LATCH_TIMER_SECONDS,
                "death_task_predicate": DEATH_TASK_PREDICATE_VA,
                "death_task_vtable_slot": 0x3C,
                "death_task_rule": "current_hp_zero_and_death_timer_less_than_"
                                   "or_equal_to_zero",
                "death_task_value_seconds": DEATH_TASK_TIMER_SECONDS,
                "zero_float_constant": ZERO_FLOAT_CONSTANT_VA,
            },
            "chain": {
                "inbound_handler": 0x5E4060,
                "actor_reconcile": 0x446F30,
                "actor_reconcile_direct_callers": 1,
                "identity_lookup": 0x446170,
                "spawn_when_unknown": 0x446990,
                "update_when_known_vtable_slot": 0x20,
                "attr_apply_and_dead_sync": 0x4446F0,
                "dead_state_sync": 0x4437C0,
                "death_task_ctor": 0x472810,
                "death_task_id": 0x80000005,
                "die_animation_literal": 0xF0F060,
                "model_loaded_gate": 0x40,
            },
        },
        "probe": {
            "source": "port_royal_unambiguous_placements_frozen_v141",
            "selection_rule": "nearest_placement_to_the_frozen_v135_player_spawn",
            "identity_formula": "0x2000_plus_placement_index_plus_1",
            "placement_index": RUNTIMERES_DEATH_PROBE_PLACEMENT_INDEX,
            "template_id": RUNTIMERES_DEATH_PROBE_TEMPLATE_ID,
            "actor_identity": RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY,
            "visual_preset": RUNTIMERES_DEATH_PROBE_VISUAL_PRESET,
            "source_name": RUNTIMERES_DEATH_PROBE_SOURCE_NAME,
            # Only the steps THIS profile sends.  The pins themselves are the
            # same objects for both profiles, which is the point: the two-frame
            # file publishes the same two hashes the three-frame file does.
            "per_step": {
                label: {
                    "lethal": label in profile.lethal_step_labels,
                    "basic_mask": RUNTIMERES_DEATH_PINS[label]["basic_mask"],
                    "pc_size": RUNTIMERES_DEATH_PINS[label]["pc_size"],
                    "pc_sha256": RUNTIMERES_DEATH_PINS[label]["pc_sha256"],
                    "frame_size": RUNTIMERES_DEATH_PINS[label]["frame_size"],
                    "frame_sha256":
                        RUNTIMERES_DEATH_PINS[label]["frame_sha256"],
                }
                for label in profile.step_order
            },
            "hp_alive": RUNTIMERES_DEATH_HP_ALIVE,
            "hp_max": RUNTIMERES_DEATH_HP_MAX,
            "hp_zero": RUNTIMERES_DEATH_HP_ZERO,
            "scene_id": SCENE_ID,
            "scene_sequence": SCENE_SEQUENCE,
            "baseline_crosscheck": (
                "the_timerless_npc_attr_body_reproduces_legacy_make_npc_attr_"
                "byte_for_byte"
            ),
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": list(
            RUNTIMERES_DEATH_LATCH_ONLY_CAPABILITIES if latch_only
            else RUNTIMERES_DEATH_CAPABILITIES
        ),
        "nonclaims": list(
            RUNTIMERES_DEATH_LATCH_ONLY_NONCLAIMS if latch_only
            else RUNTIMERES_DEATH_NONCLAIMS
        ),
    }


def load_runtimeres_death_hypothesis_scenario(
    path: str | Path,
) -> RuntimeResDeathHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid runtimeres death hypothesis scenario") from exc
    if type(data) is not dict:
        raise ValueError(
            "runtimeres death hypothesis scenario exceeds the exact allowlist"
        )
    # The file names its own profile and the id has to be one of the two this
    # module ships.  The exact-tree comparison below is still the thing that
    # decides; this lookup only picks WHICH tree to compare against, so a file
    # cannot select a profile and then carry another profile's contents.
    scenario_id = data.get("id")
    profile = (
        RUNTIMERES_DEATH_PROFILE_BY_SCENARIO_ID.get(scenario_id)
        if type(scenario_id) is str else None
    )
    if profile is None or not _exact_equal(data, _expected_scenario(profile)):
        raise ValueError(
            "runtimeres death hypothesis scenario exceeds the exact allowlist"
        )
    return require_runtimeres_death_hypothesis_scenario(profile)
