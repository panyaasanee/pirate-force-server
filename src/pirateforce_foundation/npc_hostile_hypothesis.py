"""NPC-HOSTILE-001: the hostile-presentation actor-entry encoder (GT-032).

WHY THIS MODULE EXISTS -- Door A of the mob-aggro design
--------------------------------------------------------
``drafts/MOB_AGGRO_SERVER_AI_STATIC_AND_DESIGN_R98_20260820.md`` (round 98)
ranked the three doors a fight needs by how proven each one is, and Door A --
HOSTILITY -- is the only one already proven on the wire.  This module is the
honest first checkpoint that draft proposed: make the first Port Royal
placement PRESENT as hostile, using exactly two proven mechanisms and nothing
else, and ask a real client one clean attended question (GT-032).

The two proven mechanisms, and what each one proved:

1. **SCENE-005 semantics** (runtime pass, 2026-08-15,
   ``reports/PF_SCENE005_FACTION1_HOSTILE_RELATION_RUNTIME_PASS_20260815.md``):
   faction is BasicAttr bit ``0x0400``, a u32 at object offset ``+0x68``
   (wire tag ``0x14``).  The client's relation lookup ``0x4A1D50`` compares
   TWO actors' faction fields against a client-side faction table.  With the
   local player's StartGame ActorAttr carrying faction **1** and the scene NPC
   carrying faction **6**, a real client rendered the pink/red name, the red
   outline and the red target panel, and emitted the 31-byte TargetVital
   kind 1.  Both halves of that pairing matter: the arena-v2 run
   (``PF_FOUNDATION_ARENA_V2_FACTION_ONLY_NEGATIVE_20260815.md``) proved that
   an NPC faction of 6 ALONE, against the unmodified player, is neutral --
   the relation-comparator trace pinned the unmodified player's faction at
   the constructor default 0, and the pair (0, 6) was observed neutral over
   1,023 comparator calls.  A lane that set only the NPC's faction would
   re-run a proven negative and answer nothing.
2. **HYP-PF-023 transport** (``runtimeres_death_hypothesis.py``, GT-022/025
   attended PASS): the actor-entry pipe -- ``GSCN_RunTimeProtocolRes`` id
   ``0x6E9D`` version 4, derived change mask bit ``0x02``, one actor entry,
   actor_type 4 (CNetNPC) -- delivers a spawn for placement identity
   ``0x2001`` that a real client renders.  Its SPAWN frame carries a nested
   BasicAttr, so the faction field has a proven truck to ride on.

WHAT THIS MODULE COMPOSES
-------------------------
ONE frame.  ``HOSTILE_SPAWN`` is the HYP-PF-023 SPAWN frame for the same
frozen probe (placement 0, template 1, identity 0x2001, preset
P_MALE_002_000_SP1, full-mask MovementAttr, HP 100/100) with EXACTLY ONE
delta: BasicAttr bit ``0x0400`` set, carrying the u32 faction value **6** --
five bytes inserted in ascending mask-bit order after the 0x0200 scene
sequence, and a mask that differs by exactly that one bit.  The encoder
re-derives the frozen ``legacy.make_npc_attr`` body on every composition and
refuses to return bytes unless the hostile body IS that body plus the
five-byte splice.  Nothing else is new: no name, no attack, no behavior id,
no movement beyond the placement itself.

The OTHER half of the pairing rides the entry, not the sweep: under this
opt-in scenario the runtime recomposes the full-writable StartGame response
through ``player_wire.make_actor_attr_with_name_class_and_faction`` (as of
CORE-REQUEST-022; the guard is byte-identical to the frozen
``make_actor_attr_with_basic_faction`` it replaced -- ONLY faction 1,
scene_seq 0, scene_id 1 or 2, the exact SCENE-005/SCENE-007 probe), and
ONLY when the selected character is the canonical smoke identity
0x10010001/0 the pins were computed for.
Any other identity, and any serializer refusal, falls back to the
byte-identical production StartGame and the sweep then refuses by name:
the tester sees the full proven pairing or nothing.

THE ATTENDED QUESTION (GT-032, queued, not run)
-----------------------------------------------
Does the real client render actor-entry-projected NPC 0x2001 as hostile
(red name board is absent by design -- this spawn carries no name bit -- so
the observables are the red outline and the Tab target panel / arrow) the
way SCENE-005 rendered the scene-load NPC 0x203D?  A negative is valuable:
it would say a spawn-time faction bit on this pipe does not reach the
relation read, which redirects Door A before anything is built on it.

FAIL CLOSED
-----------
* ``production_allowed`` is ``False`` and the scenario file must say so too.
* The scenario JSON is checked against an EXACT allowlist -- one extra or
  missing key anywhere in the tree and the loader refuses.
* BasicAttr bit ``0x0400`` cannot be emitted on this path at all without the
  wire unlock token, and the ONLY way to obtain that token is from the
  allowlisted scenario object, compared by identity everywhere.
* Every composed sweep is re-read by :func:`validate_npc_hostile_sweep`
  before it is returned.  A frame whose BasicAttr mask is not EXACTLY the
  parent spawn mask plus the faction bit -- any missing bit, any extra bit,
  the death lane's timer bit included -- produces NO BYTES AT ALL.
* The faction values are pinned: 6 on the NPC, 1 on the player.  Any other
  value refuses by name.  THE VALUES ARE OUR COMPOSITION (SCENE-005 already
  records this caveat): the original server's faction assignment is unknown
  and unrecoverable, and nothing here claims otherwise.

SCOPE
-----
The NPC-HOSTILE-001 milestone is this module, its scenario file, the
``app.py`` flag, the ``runtime.py`` entry recomposition + dispatch branch,
its verifier, its headless replay, its tests and its report, registered as
``HYP-PF-027`` by the round-99 ledger append.  What is NOT covered: the
client.  No client has ever been shown one byte of this profile, and whether
anything turns red is GT-032, attended, not run.  No aggro, no threat table,
no chase, no attack (Door B stays closed), no persistence (faction has no
write path and this lane opens none).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
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

NPC_HOSTILE_SCENARIO_ID = "npc_hostile_hypothesis_faction_pairing"
# PF-HYPOTHESIS-LEDGER: HYP-PF-027 active
# Registered in docs/HYPOTHESIS_LEDGER.json by the round-99 append (entry 34).
# The annotation above and that entry's source_refs bind each other both ways:
# removing either one turns tools/verify_hypothesis_ledger.py red.
NPC_HOSTILE_HYPOTHESIS_ID = "HYP-PF-027"
NPC_HOSTILE_DISPATCH_KWARG = "npc_hostile_hypothesis_scenario"

# ---------------------------------------------------------------------------
# The envelope.  Byte offsets into the PC that make_runtime_remote_actors
# emits -- the same constants HYP-PF-023 pinned, copied here (drift-tested by
# the verifier and the tests, never imported: an encoder does not import a
# neighbouring lane).
# ---------------------------------------------------------------------------
RUNTIME_PROTOCOL_RES_VERSION = 4
INHERITED_CHANGE_MASK_ABSENT = 0x00
INHERITED_CHANGE_MASK_OFFSET = 11
DERIVED_CHANGE_MASK_ACTOR_ENTRIES = 0x02
DERIVED_CHANGE_MASK_OFFSET = 13
DERIVED_CHANGE_MASK_OBJECT_OFFSET = 0x1C
ACTOR_ENTRY_COUNT_TAG_OFFSET = 14
ACTOR_ENTRY_COUNT_OFFSET = 15
ACTOR_ENTRY_LIST_OFFSET = 17

BASIC_ATTR_MASK_TAG = 0x12
BASIC_BIT_CURRENT_HP = 0x0004      # u32 tag 0x14 @ +0x44
BASIC_BIT_MAX_HP = 0x0008          # u32 tag 0x14 @ +0x48
BASIC_BIT_SCENE_ID = 0x0100        # u16 tag 0x12 @ +0x5C
BASIC_BIT_SCENE_SEQ = 0x0200       # qword tag 0x32 @ +0x60
BASIC_BIT_FACTION = 0x0400         # u32 tag 0x14 @ +0x68  <- Door A
FACTION_OBJECT_OFFSET = 0x68
FACTION_TAG = 0x14
FACTION_WIDTH = 4

NPC_ATTR_MASK_TAG = 0x0B
NPC_BIT_TEMPLATE = 0x01            # u16 tag 0x12 @ +0x78
NPC_BIT_VISUAL_PRESET = 0x04       # wstring tag 0x48 @ +0x7C
DB_ATTRIBUTE_IDENTITY_MASK = 0x01
DB_ATTRIBUTE_MASK_TAG = 0x0B
IDENTITY_TAG = 0x32
FULL_MOVEMENT_MASK = 0xFF

# The parent lane's timerless SPAWN mask (HP pair + scene pair) and this
# lane's one-bit widening of it.  The strict-equality rule below is what
# keeps every OTHER BasicAttr bit -- the death lane's timer bit expressly
# included -- structurally impossible on this lane: a mask is either exactly
# HYP23_SPAWN_BASIC_MASK | BASIC_BIT_FACTION or the sweep refuses.
HYP23_SPAWN_BASIC_MASK = 0x030C
NPC_HOSTILE_BASIC_MASK = HYP23_SPAWN_BASIC_MASK | BASIC_BIT_FACTION  # 0x070C

# ===========================================================================
# THE PAIRING.  Both values are OUR COMPOSITION, chosen because they are the
# one pair a real client has already rendered as hostile (SCENE-005), and
# because the only other observed pairing -- NPC 6 against the unmodified
# player's constructor-default 0 -- was observed NEUTRAL (arena v2 negative +
# the 1,023-call relation-comparator trace).  The original server's faction
# assignment is unknown and unrecoverable.
#
#   relation lookup:            0x4A1D50  (compares two actors' +0x68 fields)
#   player StartGame faction:   1   (entry side, player_wire serializer)
#   NPC spawn faction:          6   (sweep side, this module)
#   proven hostile pair:        (1, 6)   SCENE-005 runtime pass
#   proven neutral pair:        (0, 6)   SCENE-004 / arena v2 negative
# ===========================================================================
RELATION_LOOKUP_VA = 0x4A1D50
NPC_HOSTILE_NPC_FACTION_VALUE = 6
NPC_HOSTILE_PLAYER_PAIR_FACTION = 1
NPC_HOSTILE_PLAYER_IDENTITY_LO = 0x10010001
NPC_HOSTILE_PLAYER_IDENTITY_HI = 0
# The faction-1 StartGame ActorAttr is the production one plus exactly one
# tagged u32: five bytes.  runtime.py measures the recomposed response
# against this delta and falls back to production bytes on any other shape.
NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA = 5

NPC_HOSTILE_HP_ALIVE = 100
NPC_HOSTILE_HP_MAX = 100

CLIENT_SHA256 = (
    "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
)
STATIC_ANCHORS = {
    "runtime_protocol_res_id": RUNTIME_PROTOCOL_RES_ID,          # 0x6E9D
    "runtime_protocol_res_serializer": 0x5E3EE0,
    "runtime_protocol_res_inbound_handler": 0x5E4060,
    "actor_reconcile": 0x446F30,
    "actor_identity_lookup": 0x446170,
    "actor_spawn_not_found": 0x446990,
    "actor_type_jump_table": 0x446B2C,
    "cnetnpc_vtable": 0xF0DF58,
    "cnetnpc_actor_type": NPC_STYLE_ACTOR_TYPE,
    "relation_lookup": RELATION_LOOKUP_VA,
    "faction_object_offset": FACTION_OBJECT_OFFSET,
}

# ---------------------------------------------------------------------------
# The step plan: one frame.
# ---------------------------------------------------------------------------
HOSTILE_SPAWN_STEP_LABEL = "HOSTILE_SPAWN"
NPC_HOSTILE_STEP_ORDER = (HOSTILE_SPAWN_STEP_LABEL,)
NPC_HOSTILE_FIRST_DELAY_SECONDS = 0.0
# 15 s spacing is pinned for consistency with every photographed lane since
# round 84; with one frame it only documents the cadence a widening would use.
NPC_HOSTILE_SPACING_SECONDS = 15.0
NPC_HOSTILE_ACTION_LABEL_PREFIX = "HYP_PF_027_NPC_HOSTILE_"
NPC_HOSTILE_ACTION_LABELS = tuple(
    NPC_HOSTILE_ACTION_LABEL_PREFIX + label
    for label in NPC_HOSTILE_STEP_ORDER
)

# ---------------------------------------------------------------------------
# The probe actor: the SAME frozen placement HYP-PF-023 kills and HYP-PF-024's
# npc profile targets, selected by the SAME rule (nearest placement to the
# frozen V135 player spawn) and pinned so a drift in the frozen source turns
# this lane RED instead of silently making a different NPC hostile.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NpcHostileProbe:
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


NPC_HOSTILE_PROBE_PLACEMENT_INDEX = 0
NPC_HOSTILE_PROBE_TEMPLATE_ID = 1
NPC_HOSTILE_PROBE_ACTOR_IDENTITY = 0x2001
NPC_HOSTILE_PROBE_VISUAL_PRESET = "P_MALE_002_000_SP1"
NPC_HOSTILE_PROBE_SOURCE_NAME = "Navy Transfer"

# The deterministic bytes the sweep produces for that probe.  Three copies of
# these pins must agree on every build: this dict, the scenario file, and the
# composed bytes themselves.
NPC_HOSTILE_PINS: dict[str, dict[str, Any]] = {
    HOSTILE_SPAWN_STEP_LABEL: {
        "basic_mask": NPC_HOSTILE_BASIC_MASK,
        "faction_value": NPC_HOSTILE_NPC_FACTION_VALUE,
        "pc_size": 178,
        "pc_sha256":
            "A85DD9F7C11D5F7B5C7779E0C9B0C5032459458A103B5282D42CDDEB8C7FC21B",
        "frame_size": 190,
        "frame_sha256":
            "BB2B59486989C69B083436AC694A4085594ED4A386C4144AB227C7616C6D5983",
    },
}


def resolve_probe(legacy: Any) -> NpcHostileProbe:
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
        raise ValueError(
            "HYP-PF-027 refuses a probe with no visual preset: an actor whose "
            "model never resolves cannot present anything, hostile or not"
        )
    if (
        placement.placement_index != NPC_HOSTILE_PROBE_PLACEMENT_INDEX
        or placement.template_id != NPC_HOSTILE_PROBE_TEMPLATE_ID
        or placement.actor_identity != NPC_HOSTILE_PROBE_ACTOR_IDENTITY
        or placement.visual_preset != NPC_HOSTILE_PROBE_VISUAL_PRESET
        or placement.source_name != NPC_HOSTILE_PROBE_SOURCE_NAME
    ):
        raise RuntimeError(
            "HYP-PF-027 probe drift: the nearest frozen placement is no "
            "longer the pinned one"
        )
    return NpcHostileProbe(
        placement.placement_index, placement.template_id,
        placement.actor_identity, placement.x, placement.y, placement.z,
        placement.visual_preset, placement.source_name,
        SCENE_ID, SCENE_SEQUENCE,
    )


# ---------------------------------------------------------------------------
# The wire unlock.  Same shape as the neighbouring lanes': derived ONCE from
# the allowlisted scenario object and required by every code path that can
# put the faction bit on the actor-entry wire.  Compared by identity, so a
# value-equal forgery opens nothing.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NpcHostileWireUnlock:
    scenario_id: str
    hypothesis_id: str


@dataclass(frozen=True)
class NpcHostileHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float
    first_delay_seconds: float
    action_label_prefix: str
    npc_faction: int
    player_pair_faction: int


_PROFILE = NpcHostileHypothesisScenario(
    NPC_HOSTILE_SCENARIO_ID,
    NPC_HOSTILE_HYPOTHESIS_ID,
    NPC_HOSTILE_STEP_ORDER,
    NPC_HOSTILE_SPACING_SECONDS,
    NPC_HOSTILE_FIRST_DELAY_SECONDS,
    NPC_HOSTILE_ACTION_LABEL_PREFIX,
    NPC_HOSTILE_NPC_FACTION_VALUE,
    NPC_HOSTILE_PLAYER_PAIR_FACTION,
)
_ALLOWED_PROFILES = (_PROFILE,)

_UNLOCK = NpcHostileWireUnlock(
    NPC_HOSTILE_SCENARIO_ID, NPC_HOSTILE_HYPOTHESIS_ID,
)


def npc_hostile_wire_unlock(value: Any) -> NpcHostileWireUnlock:
    """The only key that lets this process emit the faction bit on this path."""
    require_npc_hostile_hypothesis_scenario(value)
    return _UNLOCK


def require_npc_hostile_wire_unlock(value: Any) -> NpcHostileWireUnlock:
    if value is not _UNLOCK:
        raise ValueError(
            "npc_hostile_missing_or_forged_wire_unlock: HYP-PF-027 refuses "
            "to emit BasicAttr bit 0x0400 on the actor-entry path without "
            "the unlock derived from the opt-in scenario"
        )
    return value


def require_npc_hostile_hypothesis_scenario(
    value: Any,
) -> NpcHostileHypothesisScenario:
    if type(value) is not NpcHostileHypothesisScenario or not any(
        value == allowed for allowed in _ALLOWED_PROFILES
    ):
        raise ValueError(
            "npc hostile hypothesis scenario object exceeds the allowlist"
        )
    return value


# ---------------------------------------------------------------------------
# The encoder.
# ---------------------------------------------------------------------------
# Where the five faction bytes land inside the frozen make_npc_attr body:
# DBAttribute mask (2) + tagged identity qword (9) + BasicAttr mask tag (1)
# put the u16 mask at bytes 12..13; the HP pair (5+5), scene id (3) and scene
# sequence (9) end at byte 36, which is where ascending mask-bit order puts
# bit 0x0400 -- after 0x0200, before the NPCAttr own mask.
_BASELINE_MASK_AT = 12
_BASELINE_FACTION_INSERT_AT = 36


def encode_hostile_npc_attr(
    legacy: Any,
    probe: NpcHostileProbe,
    *,
    current_hp: int = NPC_HOSTILE_HP_ALIVE,
    max_hp: int = NPC_HOSTILE_HP_MAX,
    faction: int = NPC_HOSTILE_NPC_FACTION_VALUE,
    wire: Any = None,
) -> bytes:
    """One NPCAttr body: the frozen baseline plus EXACTLY the faction splice.

    The body is refused unless it equals ``legacy.make_npc_attr(...)`` -- the
    projection this project's actor-entry emitters already ship and a real
    client already rendered -- with the u16 BasicAttr mask widened by exactly
    bit 0x0400 and the five bytes of the tagged u32 faction spliced in at the
    ascending-order position.  Any other delta means the field landed in the
    wrong place, and no bytes are returned.
    """
    if type(probe) is not NpcHostileProbe:
        raise ValueError("HYP-PF-027 probe must be the typed probe object")
    require_npc_hostile_wire_unlock(wire)
    if type(current_hp) is not int or type(current_hp) is bool:
        raise ValueError("current hp must be an int")
    if type(max_hp) is not int or type(max_hp) is bool:
        raise ValueError("max hp must be an int")
    if not 0 <= current_hp <= 0xFFFFFFFF or not 0 <= max_hp <= 0xFFFFFFFF:
        raise ValueError("hp values must fit u32")
    if current_hp == 0:
        raise ValueError(
            "npc_hostile_refuses_zero_hp: a spawn at zero HP walks into the "
            "death lane's predicates and answers a different question"
        )
    if faction != NPC_HOSTILE_NPC_FACTION_VALUE:
        raise ValueError(
            "npc_hostile_faction_value_not_pinned: only the SCENE-005 "
            "diagnostic value 6 is allowed, and it is our composition"
        )
    baseline = legacy.make_npc_attr(
        probe.template_id, probe.actor_identity,
        probe.scene_id, probe.scene_sequence, probe.visual_preset,
        current_hp, max_hp,
    )
    baseline_mask = int.from_bytes(
        baseline[_BASELINE_MASK_AT:_BASELINE_MASK_AT + 2], "little",
    )
    if baseline_mask != HYP23_SPAWN_BASIC_MASK:
        raise RuntimeError(
            "HYP-PF-027 baseline drift: the frozen make_npc_attr mask is no "
            "longer 0x030C, so the splice offsets below are stale"
        )
    expected = (
        baseline[:_BASELINE_MASK_AT]
        + int(NPC_HOSTILE_BASIC_MASK).to_bytes(2, "little")
        + baseline[_BASELINE_MASK_AT + 2:_BASELINE_FACTION_INSERT_AT]
        + bytes(legacy.u32tag(FACTION_TAG, faction))
        + baseline[_BASELINE_FACTION_INSERT_AT:]
    )
    composed = _compose_hostile_npc_attr(
        legacy, probe, current_hp, max_hp, faction,
    )
    if composed != expected:
        raise RuntimeError(
            "npc_hostile_baseline_splice_drift: the hostile body is not the "
            "frozen make_npc_attr body plus exactly the five faction bytes"
        )
    if len(composed) != len(baseline) + 1 + FACTION_WIDTH:
        raise RuntimeError("HYP-PF-027 hostile NPCAttr length drift")
    return composed


def _compose_hostile_npc_attr(
    legacy: Any,
    probe: NpcHostileProbe,
    current_hp: int,
    max_hp: int,
    faction: int,
) -> bytes:
    npc_mask = NPC_BIT_TEMPLATE | (
        NPC_BIT_VISUAL_PRESET if probe.visual_preset else 0
    )
    out = bytearray()
    out += legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK)
    out += legacy.qwordtag(IDENTITY_TAG, probe.actor_identity)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, NPC_HOSTILE_BASIC_MASK)
    # Ascending mask-bit order inside the block, which is the order the
    # BasicAttr serializer 0x4656F0 writes and its reader expects.
    out += legacy.u32tag(0x14, current_hp)                     # 0x0004
    out += legacy.u32tag(0x14, max_hp)                         # 0x0008
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, probe.scene_id)  # 0x0100
    out += legacy.qwordtag(IDENTITY_TAG, probe.scene_sequence)  # 0x0200
    out += legacy.u32tag(FACTION_TAG, faction)                 # 0x0400
    out += legacy.u8tag(NPC_ATTR_MASK_TAG, npc_mask)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, probe.template_id)
    if probe.visual_preset:
        out += legacy.wstr_tag(probe.visual_preset)
    return bytes(out)


def make_npc_hostile_step_response(
    legacy: Any,
    probe: NpcHostileProbe,
    index: int,
    wire: Any,
    profile: Any,
) -> tuple[bytes, bytes]:
    """Compose one step of the hostile-presentation sweep."""
    require_npc_hostile_hypothesis_scenario(profile)
    if type(index) is not int or type(index) is bool:
        raise ValueError("step index must be an int")
    if not 0 <= index < len(profile.step_order):
        raise ValueError("step index is outside the pinned plan")
    require_npc_hostile_wire_unlock(wire)
    npc_attr = encode_hostile_npc_attr(
        legacy, probe,
        current_hp=NPC_HOSTILE_HP_ALIVE, max_hp=NPC_HOSTILE_HP_MAX,
        faction=profile.npc_faction, wire=wire,
    )
    movement = legacy.make_remote_movement_attr(
        probe.actor_identity, probe.x, probe.y, probe.z, 0.0,
        mask=FULL_MOVEMENT_MASK,
    )
    entry = legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE, probe.actor_identity,
        [(NPC_ATTR_ID, npc_attr), (MOVEMENT_ATTR_ID, movement)],
    )
    pc, frame = legacy.make_runtime_remote_actors([entry])
    if frame != legacy.frame_pc(pc):
        raise RuntimeError("HYP-PF-027 frame drift")
    return pc, frame


def build_npc_hostile_sweep(
    legacy: Any,
    probe: NpcHostileProbe,
    wire: Any,
    profile: Any,
) -> list[tuple[str, bytes, bytes, float]]:
    """Compose the whole one-frame sweep and refuse anything off the pins."""
    require_npc_hostile_hypothesis_scenario(profile)
    actions: list[tuple[str, bytes, bytes, float]] = []
    for index, label in enumerate(profile.step_order):
        pc, frame = make_npc_hostile_step_response(
            legacy, probe, index, wire, profile,
        )
        delay = (
            profile.first_delay_seconds if index == 0
            else profile.spacing_seconds
        )
        actions.append((profile.action_label_prefix + label, pc, frame, delay))
    rows = validate_npc_hostile_sweep(actions, profile)
    for index, label in enumerate(profile.step_order):
        pin = NPC_HOSTILE_PINS[label]
        row = rows[index]
        for key in ("basic_mask", "faction_value", "pc_size", "pc_sha256",
                    "frame_size", "frame_sha256"):
            if row[key] != pin[key]:
                raise NpcHostileValidationError(
                    "HYP-PF-027 %s %s drift: %r != %r"
                    % (label, key, row[key], pin[key])
                )
    return actions


# ---------------------------------------------------------------------------
# The validator.  This is the guard the trap tests exist to break.
# ---------------------------------------------------------------------------
class NpcHostileValidationError(RuntimeError):
    """A composed sweep that must never reach a socket."""


# Only the bits this lane's strict mask allows, in ascending order.  The mask
# equality check below runs BEFORE the field walk, so a mask carrying any bit
# outside this table -- the death lane's timer bit included -- never reaches
# the walker at all.
_BASIC_FIELD_ORDER = (
    (BASIC_BIT_CURRENT_HP, 0x14),
    (BASIC_BIT_MAX_HP, 0x14),
    (BASIC_BIT_SCENE_ID, 0x12),
    (BASIC_BIT_SCENE_SEQ, 0x32),
    (BASIC_BIT_FACTION, FACTION_TAG),
)
_SCALAR_WIDTH = {0x12: 2, 0x14: 4, 0x32: 8}


def decode_npc_hostile_actor_entry_frame(pc: bytes) -> dict[str, Any]:
    """Read one composed PC back with a strict, standalone tag walker.

    Deliberately does not reuse the encoder's composition for anything except
    the constants, so a symmetrical bug in the encoder cannot hide here.
    """
    if type(pc) is not bytes:
        raise NpcHostileValidationError("a frame must be bytes")
    if len(pc) < ACTOR_ENTRY_LIST_OFFSET:
        raise NpcHostileValidationError("frame is shorter than the envelope")
    if pc[0] != 0x12 or int.from_bytes(pc[1:3], "little") != RUNTIME_PROTOCOL_RES_ID:
        raise NpcHostileValidationError(
            "frame does not open with GSCN_RunTimeProtocolRes id 0x6E9D"
        )
    if pc[3] != 0x14 or int.from_bytes(pc[4:8], "little") != 0:
        raise NpcHostileValidationError("envelope u32 field drift")
    if pc[8] != 0x08 or pc[9] != RUNTIME_PROTOCOL_RES_VERSION:
        raise NpcHostileValidationError("envelope is not version 4")
    if pc[10] != 0x0B or pc[INHERITED_CHANGE_MASK_OFFSET] != INHERITED_CHANGE_MASK_ABSENT:
        raise NpcHostileValidationError(
            "the inherited VitalData change mask is not absent"
        )
    if pc[12] != 0x0B:
        raise NpcHostileValidationError("the derived change mask tag drifted")
    derived = pc[DERIVED_CHANGE_MASK_OFFSET]
    if not derived & DERIVED_CHANGE_MASK_ACTOR_ENTRIES:
        raise NpcHostileValidationError(
            "the derived change mask is missing bit 0x02, so the client "
            "never reads the +0x1C actor-entry collection"
        )
    if pc[ACTOR_ENTRY_COUNT_TAG_OFFSET] != 0x12:
        raise NpcHostileValidationError("the actor count tag drifted")
    count = int.from_bytes(
        pc[ACTOR_ENTRY_COUNT_OFFSET:ACTOR_ENTRY_COUNT_OFFSET + 2], "little",
    )
    if count != 1:
        raise NpcHostileValidationError(
            "this lane ships exactly one actor entry per frame"
        )
    cursor = ACTOR_ENTRY_LIST_OFFSET
    if pc[cursor] != 0x0B:
        raise NpcHostileValidationError("actor type tag drift")
    actor_type = pc[cursor + 1]
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise NpcHostileValidationError("actor identity tag drift")
    identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != 0x0B:
        raise NpcHostileValidationError("attr count tag drift")
    attr_count = pc[cursor + 1]
    cursor += 2

    attrs: dict[int, dict[str, Any]] = {}
    for _ in range(attr_count):
        if pc[cursor] != 0x12:
            raise NpcHostileValidationError("attr id tag drift")
        attr_id = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
        cursor += 3
        if attr_id == NPC_ATTR_ID:
            parsed, cursor = _walk_npc_attr(pc, cursor)
            attrs[attr_id] = parsed
        elif attr_id == MOVEMENT_ATTR_ID:
            cursor = _skip_movement_attr(pc, cursor)
            attrs[attr_id] = {"present": True}
        else:
            raise NpcHostileValidationError(
                "unexpected attr id 0x%04X on the actor-entry path" % attr_id
            )
    if cursor > len(pc):
        raise NpcHostileValidationError(
            "the frame is truncated: the walker ran %d bytes past its end"
            % (cursor - len(pc))
        )
    if cursor != len(pc):
        raise NpcHostileValidationError(
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
        raise NpcHostileValidationError("DBAttribute mask tag drift")
    if pc[cursor + 1] != DB_ATTRIBUTE_IDENTITY_MASK:
        raise NpcHostileValidationError(
            "DBAttribute mask is not the identity-only 0x01"
        )
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise NpcHostileValidationError("NPCAttr identity tag drift")
    attr_identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != BASIC_ATTR_MASK_TAG:
        raise NpcHostileValidationError("BasicAttr mask tag drift")
    basic_mask = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
    cursor += 3
    # THE STRICT RULE, checked before a single field is read: the mask must
    # be exactly the parent spawn mask plus the faction bit.  Any missing
    # bit and any extra bit -- whatever its meaning on any other lane -- is
    # a refusal with no field walk at all.
    if basic_mask != NPC_HOSTILE_BASIC_MASK:
        raise NpcHostileValidationError(
            "BasicAttr mask 0x%04X is not exactly the HYP-PF-023 spawn mask "
            "0x%04X plus the faction bit 0x%04X"
            % (basic_mask, HYP23_SPAWN_BASIC_MASK, BASIC_BIT_FACTION)
        )
    fields: dict[int, Any] = {}
    for bit, tag in _BASIC_FIELD_ORDER:
        if not basic_mask & bit:
            continue
        if pc[cursor] != tag:
            raise NpcHostileValidationError(
                "BasicAttr bit 0x%04X expected tag 0x%02X, found 0x%02X"
                % (bit, tag, pc[cursor])
            )
        width = _SCALAR_WIDTH[tag]
        fields[bit] = int.from_bytes(pc[cursor + 1:cursor + 1 + width], "little")
        cursor += 1 + width
    if pc[cursor] != NPC_ATTR_MASK_TAG:
        raise NpcHostileValidationError("NPCAttr mask tag drift")
    npc_mask = pc[cursor + 1]
    cursor += 2
    template_id = None
    visual_preset = None
    if npc_mask & NPC_BIT_TEMPLATE:
        if pc[cursor] != 0x12:
            raise NpcHostileValidationError("NPCAttr template tag drift")
        template_id = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
        cursor += 3
    if npc_mask & NPC_BIT_VISUAL_PRESET:
        if pc[cursor] != 0x48:
            raise NpcHostileValidationError("NPCAttr preset tag drift")
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
    (0x01, 15), (0x02, 5), (0x04, 2), (0x08, 5), (0x10, 5), (0x20, 5),
    (0x40, 5),
)


def _skip_movement_attr(pc: bytes, cursor: int) -> int:
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG or pc[cursor + 1] != 0x01:
        raise NpcHostileValidationError("MovementAttr DBAttribute drift")
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise NpcHostileValidationError("MovementAttr identity tag drift")
    cursor += 9
    if pc[cursor] != 0x0B:
        raise NpcHostileValidationError("MovementAttr mask tag drift")
    mask = pc[cursor + 1]
    cursor += 2
    for bit, width in _MOVEMENT_FIELD_WIDTH:
        if mask & bit:
            cursor += width
    return cursor


def validate_npc_hostile_sweep(
    actions: Any,
    profile: Any,
) -> list[dict[str, Any]]:
    """Prove a composed sweep is the one designed frame and nothing else."""
    require_npc_hostile_hypothesis_scenario(profile)
    if type(actions) is not list:
        raise NpcHostileValidationError("the sweep must be a list")
    if len(actions) != len(profile.step_order):
        raise NpcHostileValidationError(
            "the sweep must carry exactly %d frame(s)" % len(profile.step_order)
        )
    rows: list[dict[str, Any]] = []
    for index, action in enumerate(actions):
        if type(action) is not tuple or len(action) != 4:
            raise NpcHostileValidationError(
                "each sweep entry must be (label, pc, frame, delay)"
            )
        label, pc, frame, delay = action
        expected_label = profile.action_label_prefix + profile.step_order[index]
        if label != expected_label:
            raise NpcHostileValidationError(
                "step %d is labelled %r, expected %r"
                % (index, label, expected_label)
            )
        if type(frame) is not bytes or not frame:
            raise NpcHostileValidationError("step %d has no frame" % index)
        read = decode_npc_hostile_actor_entry_frame(pc)
        if read["actor_type"] != NPC_STYLE_ACTOR_TYPE:
            raise NpcHostileValidationError(
                "actor_type %d is not the CNetNPC case 4 this lane pins"
                % read["actor_type"]
            )
        if read["identity"] != NPC_HOSTILE_PROBE_ACTOR_IDENTITY:
            raise NpcHostileValidationError(
                "entry identity 0x%X is not the pinned probe 0x%X"
                % (read["identity"], NPC_HOSTILE_PROBE_ACTOR_IDENTITY)
            )
        npc = read["attrs"].get(NPC_ATTR_ID)
        if npc is None:
            raise NpcHostileValidationError(
                "step %d carries no NPCAttr" % index
            )
        if npc["identity"] != read["identity"]:
            raise NpcHostileValidationError(
                "step %d: the entry identity and the NPCAttr identity differ"
                % index
            )
        if not npc["visual_preset"]:
            raise NpcHostileValidationError(
                "step %d carries no visual preset, so no model resolves and "
                "nothing can present anything" % index
            )
        hp = npc["fields"].get(BASIC_BIT_CURRENT_HP)
        faction = npc["fields"].get(BASIC_BIT_FACTION)
        if hp != NPC_HOSTILE_HP_ALIVE:
            raise NpcHostileValidationError(
                "step %d must spawn alive at the pinned HP %d"
                % (index, NPC_HOSTILE_HP_ALIVE)
            )
        if faction != profile.npc_faction:
            raise NpcHostileValidationError(
                "step %d faction %r is not the pinned %d"
                % (index, faction, profile.npc_faction)
            )
        if MOVEMENT_ATTR_ID not in read["attrs"]:
            raise NpcHostileValidationError(
                "the spawn frame must place the actor (MovementAttr)"
            )
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
            "faction_value": faction,
            "pc_size": len(pc),
            "frame_size": len(frame),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
        })
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


NPC_HOSTILE_CAPABILITIES = (
    "emit_gscn_runtimeprotocolres_0x6e9d_derived_mask_bit_0x02_actor_entries",
    "append_basicattr_faction_bit_0x0400_to_the_proven_hyp_pf_023_spawn_body",
    "reproduce_the_frozen_make_npc_attr_body_byte_for_byte_except_the_five_byte_faction_splice",
    "recompose_the_start_game_actor_attr_with_the_frozen_faction_1_serializer_for_the_pinned_identity_only",
    "refuse_any_basicattr_mask_that_is_not_exactly_the_spawn_mask_plus_the_faction_bit",
)
NPC_HOSTILE_NONCLAIMS = (
    "no_client_has_ever_been_shown_one_byte_of_this_profile",
    "client_rendering_of_a_hostile_presentation_on_an_npc_pending_gt032",
    "faction_values_1_and_6_are_our_composition_not_the_original_servers_which_is_unrecoverable",
    "that_the_relation_pair_1_6_behaves_on_an_actor_entry_projected_npc_as_it_did_in_scene005",
    "no_name_board_this_spawn_carries_no_name_bit_the_observables_are_outline_and_target_panel",
    "no_aggro_no_threat_table_no_chase_no_attack_door_b_stays_closed",
    "no_persistence_faction_has_no_write_path_and_this_lane_opens_none",
    "production_dispatch_wiring_the_wiring_is_opt_in_and_production_allowed_is_false",
    "production_baseline_behavior",
)


def _expected_scenario() -> dict[str, Any]:
    profile = _PROFILE
    return {
        "schema": 1,
        "id": profile.scenario_id,
        "profile": "faction_pairing",
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": NPC_HOSTILE_HYPOTHESIS_ID,
        "hypothesis_id_is_registered_in_the_ledger": True,
        "lethal": False,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_one_hostile_spawn_actor_entry_frame_no_write_no_close"
            ),
            "player_start_game": {
                "basic_faction": NPC_HOSTILE_PLAYER_PAIR_FACTION,
                "serializer": (
                    "player_wire_make_actor_attr_with_name_class_and_"
                    "faction_scene005_probe"
                ),
                "identity_pinned_lo": NPC_HOSTILE_PLAYER_IDENTITY_LO,
                "identity_pinned_hi": NPC_HOSTILE_PLAYER_IDENTITY_HI,
                "wire_delta_bytes": NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA,
                "fallback_when_not_pinned": (
                    "production_start_game_bytes_and_the_sweep_refuses_by_name"
                ),
            },
        },
        "dispatch": {
            "wired": True,
            "wiring_owner": "npc_hostile_dispatch_001_round_99",
            "app_policy_when_lane_disabled": (
                "no_frames_composed_and_the_encoder_raises_if_called_directly"
            ),
            "frames_per_accepted_request": len(profile.step_order),
            "step_order": list(profile.step_order),
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
            "requires_player_faction_start_game": True,
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
            "faction_field": {
                "name": "faction",
                "block": "basic",
                "mask_bit": BASIC_BIT_FACTION,
                "object_offset": FACTION_OBJECT_OFFSET,
                "wire_tag": FACTION_TAG,
                "width": "u32",
            },
            "relation": {
                "lookup": RELATION_LOOKUP_VA,
                "player_side_value": NPC_HOSTILE_PLAYER_PAIR_FACTION,
                "npc_side_value": NPC_HOSTILE_NPC_FACTION_VALUE,
                "proven_hostile_pair": "scene005_player_faction_1_npc_faction_6",
                "proven_neutral_pair": (
                    "arena_v2_npc_faction_6_alone_against_the_constructor_"
                    "default_player_faction_0"
                ),
                "values_are_our_composition": True,
            },
            "chain": {
                "inbound_handler": 0x5E4060,
                "actor_reconcile": 0x446F30,
                "identity_lookup": 0x446170,
                "spawn_when_unknown": 0x446990,
            },
        },
        "probe": {
            "source": "port_royal_unambiguous_placements_frozen_v141",
            "selection_rule": "nearest_placement_to_the_frozen_v135_player_spawn",
            "identity_formula": "0x2000_plus_placement_index_plus_1",
            "placement_index": NPC_HOSTILE_PROBE_PLACEMENT_INDEX,
            "template_id": NPC_HOSTILE_PROBE_TEMPLATE_ID,
            "actor_identity": NPC_HOSTILE_PROBE_ACTOR_IDENTITY,
            "visual_preset": NPC_HOSTILE_PROBE_VISUAL_PRESET,
            "source_name": NPC_HOSTILE_PROBE_SOURCE_NAME,
            "per_step": {
                label: {
                    "basic_mask": NPC_HOSTILE_PINS[label]["basic_mask"],
                    "faction_value": NPC_HOSTILE_PINS[label]["faction_value"],
                    "pc_size": NPC_HOSTILE_PINS[label]["pc_size"],
                    "pc_sha256": NPC_HOSTILE_PINS[label]["pc_sha256"],
                    "frame_size": NPC_HOSTILE_PINS[label]["frame_size"],
                    "frame_sha256": NPC_HOSTILE_PINS[label]["frame_sha256"],
                }
                for label in profile.step_order
            },
            "hp_alive": NPC_HOSTILE_HP_ALIVE,
            "hp_max": NPC_HOSTILE_HP_MAX,
            "scene_id": SCENE_ID,
            "scene_sequence": SCENE_SEQUENCE,
            "baseline_crosscheck": (
                "the_hostile_npc_attr_body_reproduces_legacy_make_npc_attr_"
                "byte_for_byte_except_the_five_byte_faction_splice"
            ),
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": list(NPC_HOSTILE_CAPABILITIES),
        "nonclaims": list(NPC_HOSTILE_NONCLAIMS),
    }


def load_npc_hostile_hypothesis_scenario(
    path: str | Path,
) -> NpcHostileHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid npc hostile hypothesis scenario") from exc
    if type(data) is not dict or not _exact_equal(data, _expected_scenario()):
        raise ValueError(
            "npc hostile hypothesis scenario exceeds the exact allowlist"
        )
    return require_npc_hostile_hypothesis_scenario(_PROFILE)
