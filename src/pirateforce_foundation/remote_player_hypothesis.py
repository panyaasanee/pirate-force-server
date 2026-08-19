"""REMOTE-PLAYER-ENCODER-001: the actor_type 2 visibility probe (multiplayer chunk 2).

WHY THIS MODULE EXISTS
----------------------
Every "somebody else is in the world" frame this project has ever shipped
carried ``actor_type 4`` (``CNetNPC``): 19 literal call sites in the frozen
v141 snapshot and all four emitters in ``src/`` (the multiplayer readiness
audit counted them).  The client's actor factory 0x446990 dispatches on that
byte through the jump table at 0x446B2C, and ``2`` selects ``CNetActor`` --
the remote-player branch (MPAUDIT-FOLLOWUP-001; the word "player" appears
nowhere in the image, so "remote player" is an INFERRED reading of the class
hierarchy, not a byte).  No frame with ``actor_type 2`` has ever been
composed, dispatched or shown to a client by this project, and the original
server -- which is closed, was never published, and left no server->client
capture of a remote human player in any corpus -- cannot be consulted.

    THIS IS OUR DESIGN, NOT THE ORIGINAL SERVER'S, WHICH IS UNRECOVERABLE.
    Every value below without a [PROVEN ...] source is a value we chose.

WHAT THIS MODULE COMPOSES
-------------------------
Five ``GSCN_RunTimeProtocolRes`` (0x6E9D v4, derived mask bit 0x02) frames,
one actor entry each, for THREE probe identities, all ``actor_type 2``:

    SPAWN_BARE        identity A: ActorAttr (name, HP 100/100, scene) +
                      MovementAttr mask 0xFF at the frozen placement-0 XYZ.
    SPAWN_AVATAR      identity B: the same ActorAttr shape + MovementAttr at
                      X+150, plus the selected character's OPAQUE AvatarAttr
                      replayed with its identity rebound to B.  Comparing A
                      with B on one screen is the AvatarAttr experiment.
    MOVE_A_1          identity A again -> the client update path (vtable
                      +0x20): ONE MovementAttr, mask 0x01, at X+300.
    MOVE_A_2          identity A a third time: mask 0x03 (position+heading),
                      heading pi/2.
    NEGATIVE_CONTROL  identity C: a deliberately WRONG-CLASS NPCAttr (its
                      bind thunk 0x4697B0 gates on CNetNPC) + MovementAttr at
                      X-150.  Chunk 1's most expensive claim is that a
                      wrong-class attr is parsed and dropped in silence; if
                      this actor shows a NAME, that claim is falsified and
                      the whole lane stops.

WHAT THE CHUNK2 STATIC ROUND (Q1/Q2/Q3, round 90) CHANGED IN THIS DESIGN
------------------------------------------------------------------------
The R90 design named three questions that change the SHAPE of this encoder
and required them closed before it was written.  All three are closed, from
bytes (reports/PF_CHUNK2_Q1/Q2/Q3_*.md), and each one left a mark here:

* Q1: ``ActorAttr`` 64-bit mask == 0 is LEGAL -- the deciding branches
  (0x4667AD, 0x466B5C) are short-circuits over empty mask halves, not error
  paths -- but the actor-entry pipe binds attrs through vtable +0x24 =
  0x464F30, a CopyTo that copies EVERY field and never reads the mask (0 mask
  tests in 143 instructions).  The mask-honouring merge (+0x30 = 0x465E60)
  exists and is NEVER called on this pipe.  So an all-zero ActorAttr would
  put ctor defaults (HP 0, name L"") on the actor, and HP == 0 is the death
  predicate (0x43BD7A / 0x43BDAA).  This encoder therefore always ships the
  BasicAttr probe mask 0x030D (name + HP pair + scene pair), pins the
  ActorAttr 64-bit mask at 0 knowing the 43 gated fields land as ctor
  defaults, keeps the second-stage gate byte +0x1BC (wire tag 0x05) at the
  value 1 v141 always sent, and refuses HP < 1 by name.
* Q2: the mask-gated MovementAttr merge 0x467130 runs BEFORE the actor bind,
  inside handler 0x5E4060, against the PREVIOUS RuntimeRes frame's collection
  copy (singleton [0x01081A90]+0x154) -- not against the actor's state and
  not against history.  MOVE_A_1's unsent fields (heading/mode/flags/f32x3)
  therefore arrive at the actor as ctor zeros, because the previous frame's
  collection holds identity B, not A.  That is recorded as the PREDICTION for
  the attended run, not hidden: mask 0x01 still moves the actor; it does not
  preserve what it does not send.
* Q3: the bind thunk +0x38 never swaps the attr pointer -- it hands the
  already-bound object to the incoming attr's CopyTo -- so re-sending a known
  identity updates values and leaks nothing.  That is why MOVE_A_1/MOVE_A_2
  are safe to send at all.

DELIBERATE DEVIATIONS FROM THE R90 DESIGN DRAFT (both are ours to make; the
draft marked both rows [DESIGN CHOICE]):

* Attr order inside SPAWN_AVATAR is ActorAttr, MovementAttr, AvatarAttr --
  the AVATAR IS LAST, where the draft sketched it second.  The avatar body is
  an opaque replay; an independent tag walker can only find its boundary if
  it is the tail of the frame.  Q3 proved the binds are independent per-attr
  CopyTo calls, and no evidence orders them, so the walkable order wins.
* ``spacing_seconds`` is 15.0, not the draft's 6.0.  Attended rounds 84 and
  #8 both lost evidence to 6-second spacing (photography races capture
  latency); the damage lane's npc_target profile moved to 15 s for the same
  reason and this lane starts there.

THE SPAWN_AVATAR PIN IS A SKELETON PIN
--------------------------------------
``characters.avatar_wire`` is per-character database content (submitted by a
real client at character creation and rebound at rest), so the full bytes of
SPAWN_AVATAR cannot be pinned in code without pinning a database.  The pin
for that one step covers the frame SKELETON: every byte from the envelope
through the AvatarAttr id tag 0x16A0 -- everything this module composes --
and the avatar tail is checked structurally instead (it must satisfy the
proven common-Attr prefix ``0x0B`` / bit 0x01 / ``0x32`` and carry identity B
after the rebind).  The other four steps are pinned in full.

FAIL CLOSED
-----------
* ``production_allowed`` is ``False`` and the scenario file must say so too.
* The scenario JSON is checked against an EXACT allowlist -- one extra or
  missing key anywhere in the tree and the loader refuses.
* ``actor_type 2`` cannot be named on the wire at all without the wire
  unlock token, and the ONLY way to obtain that token is from the
  allowlisted scenario object, compared by identity everywhere (a
  value-equal forgery opens nothing).
* Every composed sweep is re-read by :func:`validate_remote_player_sweep`
  and re-pinned before it is returned.  A sweep missing the negative
  control, or carrying BasicAttr bit 0x0080 (the death lane's field), or
  whose positions did not come from the frozen placement source, produces
  NO BYTES AT ALL.
* This lane deliberately does not touch ``population.py``'s emitters,
  ``scene_object.py``, the HYP-PF-022/023/024 lanes, or any DB write path.

SCOPE THIS MODULE DOES NOT COVER -- read before running the attended test
-------------------------------------------------------------------------
No client has ever been shown one byte of this profile.  Whether anything
renders, what it looks like, whether the name board fills, whether frames
3/4 move it, and whether the negative control stays nameless are ALL the
attended test's questions.  There is NO WAY TO DESPAWN a probe on this lane
(one entry per frame means no next generation to fall out of), and ground Z
at the offset positions is unchecked -- a floating or sunken probe does not
falsify visibility.  See the report and the ledger entry for the full
nonclaim list.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any

from .actor_wire import bind_common_attr_identity
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

REMOTE_PLAYER_SCENARIO_ID = "remote_player_hypothesis_visibility_probe"
# PF-HYPOTHESIS-LEDGER: HYP-PF-025 active
# Registered in docs/HYPOTHESIS_LEDGER.json by the round-96 append (entry 32).
# The annotation above and that entry's source_refs bind each other both ways:
# removing either one turns tools/verify_hypothesis_ledger.py red.
REMOTE_PLAYER_HYPOTHESIS_ID = "HYP-PF-025"
REMOTE_PLAYER_DISPATCH_KWARG = "remote_player_hypothesis_scenario"

# ---------------------------------------------------------------------------
# The envelope.  Byte offsets into the PC that make_runtime_remote_actors
# emits.  Identical to the HYP-PF-023 lane because it is the same carrier.
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

# The actor types this lane can even talk about.  2 is the lane; 4 appears
# ONLY in refusal guards and in the negative control's attr provenance.
REMOTE_PLAYER_ACTOR_TYPE = 2       # CNetActor  [PROVEN VA=0x4469E1, table 0x446B2C]
CLIENT_ACTOR_TYPE_RANGE = (2, 6)   # outside it, 0x446B14 creates nothing
LOCAL_PLAYER_ACTOR_TYPE = 3        # CMyActor singleton, global 0x1032EC4 - NEVER

# Attr ids on this lane.
ACTOR_ATTR_ID = 0x12AD             # [PROVEN VA=0xF0E7A0 vtable; v141:416]
AVATAR_ATTR_ID = 0x16A0            # [PROVEN VA=0xF0E088 vtable; v141:2372]
SKILL_ATTR_ID = 0x1661             # the skill attr, CMyActor-only bind 0x4698B0 - NEVER
# NOTE: the exact class token for 0x1661 is deliberately NOT spelled out in this
# tree.  tools/pf_stats_progression_static.py asserts src/ carries zero tokens
# for any progression verb (that class is one of the five it tracks), and this
# lane must not be the thing that falsifies that standing negative.  We refuse
# the id, not the name.

# BasicAttr, mask +0x70, u16 tag 0x12.  Only the bits this lane emits.
BASIC_ATTR_MASK_TAG = 0x12
BASIC_BIT_NAME = 0x0001            # wstring tag 0x48 @ +0x28 -> LABEL_NAME 0x5BD624
BASIC_BIT_CURRENT_HP = 0x0004      # u32 tag 0x14 @ +0x44
BASIC_BIT_MAX_HP = 0x0008          # u32 tag 0x14 @ +0x48
BASIC_BIT_SCENE_ID = 0x0100        # u16 tag 0x12 @ +0x5C
BASIC_BIT_SCENE_SEQ = 0x0200       # qword tag 0x32 @ +0x60
BASIC_MASK_PROBE = (
    BASIC_BIT_NAME | BASIC_BIT_CURRENT_HP | BASIC_BIT_MAX_HP
    | BASIC_BIT_SCENE_ID | BASIC_BIT_SCENE_SEQ
)                                  # == 0x030D
# The death lane's field.  This lane must never be able to name it.
BASIC_BIT_DEATH_TIMER_FORBIDDEN = 0x0080

# ActorAttr block framing (after the BasicAttr block).
DB_ATTRIBUTE_MASK_TAG = 0x0B
DB_ATTRIBUTE_IDENTITY_MASK = 0x01
IDENTITY_TAG = 0x32
ACTOR_ATTR_MASK_TAG = 0x32
ACTOR_ATTR_MASK_PROBE = 0          # legal per Q1; ctor defaults land via CopyTo
ACTOR_ATTR_MASK_LOW_HALF_LIMIT = 1 << 32
ACTOR_ATTR_EXTRA_GROUP_TAG = 0x05
ACTOR_ATTR_EXTRA_GROUP_VALUE = 1   # the +0x1BC gate byte; 0 skips 25/43 fields (Q1)

# MovementAttr masks this lane may emit.  Anything else is refused by name.
MOVEMENT_MASK_FULL = 0xFF
MOVEMENT_MASK_POSITION = 0x01
MOVEMENT_MASK_POSITION_AND_HEADING = 0x03
MOVEMENT_MASKS_PINNED = (
    MOVEMENT_MASK_FULL, MOVEMENT_MASK_POSITION,
    MOVEMENT_MASK_POSITION_AND_HEADING,
)

# HP policy.  0x4446F0 calls the dead-state sync 0x4437C0 on EVERY update-path
# frame, and both of its predicates require BasicAttr +0x44 == 0, so a probe
# with HP 0 walks into the death chain the moment its identity is re-sent.
REMOTE_PLAYER_HP_ALIVE = 100
REMOTE_PLAYER_HP_MAX = 100
REMOTE_PLAYER_HP_MIN = 1

# The probe identities.  [DESIGN CHOICE] - the band 0x00A0_xxxx has no proven
# meaning; it is chosen to be visibly synthetic and to collide with nothing:
# below the character space (>= 0x10000000, lifecycle.py) and outside the
# frozen NPC band (0x2001 .. 0x2000+len(placements)).
PROBE_IDENTITY_A = 0x00A00001
PROBE_IDENTITY_B = 0x00A00002
PROBE_IDENTITY_C = 0x00A00003
CHARACTER_IDENTITY_FLOOR = 0x10000000
NPC_IDENTITY_BAND_BASE = 0x2000

PROBE_NAME_A = "ProbePlayer01"
PROBE_NAME_B = "ProbePlayer02"
PROBE_NAME_C = "ProbeControl03"

# Position offsets from the frozen placement-0 XYZ.  [DESIGN CHOICE]; ground
# Z at the offset points is UNCHECKED and that is recorded, not hidden.
PROBE_B_X_OFFSET = 150.0
PROBE_C_X_OFFSET = -150.0
MOVE_X_OFFSET = 300.0
MOVE_HEADING = math.pi / 2.0       # the same set population.py's _HEADINGS uses

# ---------------------------------------------------------------------------
# The step plan.
# ---------------------------------------------------------------------------
SPAWN_BARE_STEP_LABEL = "SPAWN_BARE"
SPAWN_AVATAR_STEP_LABEL = "SPAWN_AVATAR"
MOVE_A_1_STEP_LABEL = "MOVE_A_1"
MOVE_A_2_STEP_LABEL = "MOVE_A_2"
NEGATIVE_CONTROL_STEP_LABEL = "NEGATIVE_CONTROL"

# label, probe role, shape
REMOTE_PLAYER_STEPS = (
    (SPAWN_BARE_STEP_LABEL, "A", "actor_attr_and_full_movement"),
    (SPAWN_AVATAR_STEP_LABEL, "B", "actor_attr_movement_then_avatar_tail"),
    (MOVE_A_1_STEP_LABEL, "A", "movement_only_position"),
    (MOVE_A_2_STEP_LABEL, "A", "movement_only_position_and_heading"),
    (NEGATIVE_CONTROL_STEP_LABEL, "C", "wrong_class_npc_attr_and_full_movement"),
)
REMOTE_PLAYER_STEP_ORDER = tuple(row[0] for row in REMOTE_PLAYER_STEPS)
REMOTE_PLAYER_STEP_BY_LABEL = {row[0]: row for row in REMOTE_PLAYER_STEPS}

# 15.0 s, not 6.0: the attended tests on this lane are photography, and the
# standing rule since round 84 is that a tester must never race their camera.
REMOTE_PLAYER_FIRST_DELAY_SECONDS = 0.0
REMOTE_PLAYER_SPACING_SECONDS = 15.0
REMOTE_PLAYER_ACTION_LABEL_PREFIX = "HYP_PF_025_REMOTE_PLAYER_"
REMOTE_PLAYER_ACTION_LABELS = tuple(
    REMOTE_PLAYER_ACTION_LABEL_PREFIX + label
    for label in REMOTE_PLAYER_STEP_ORDER
)

# Static anchors this lane's design rests on, re-derived from the read-only
# client image by tools/verify_remote_player_encoder.py --binary; repeated
# here so a source reader can see what the lane assumes and so the verifier
# and the module cannot drift apart silently.
CLIENT_SHA256 = (
    "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
)
STATIC_ANCHORS = {
    "runtime_protocol_res_id": RUNTIME_PROTOCOL_RES_ID,          # 0x6E9D
    "runtime_protocol_res_inbound_handler": 0x5E4060,
    "actor_entry_list_head_dispatch": 0x5E4073,
    "actor_reconcile": 0x446F30,
    "actor_reconcile_only_caller": 0x5E4085,
    "actor_identity_lookup": 0x446170,
    "actor_spawn_not_found": 0x446990,
    "actor_type_gate": 0x4469C8,
    "actor_type_jump_table": 0x446B2C,
    "cnetactor_actor_type": REMOTE_PLAYER_ACTOR_TYPE,
    "cnetactor_ctor": 0x457340,
    "cnetactor_vtable": 0xF0DD08,
    "cmyactor_singleton_gate_global": 0x1032EC4,
    "bind_thunk_actor_attr": 0x469760,      # gates CNetActor
    "bind_thunk_npc_attr": 0x4697B0,        # gates CNetNPC  -> frame 5 drop
    "bind_thunk_movement_attr": 0x469800,   # gates CActorBaseClient (all types)
    "bind_thunk_avatar_attr": 0x469850,     # gates CNetActor OR CAvatarNPC
    "bind_thunk_skill_attr": 0x4698B0,      # gates CMyActor -> never this lane
    "actor_attr_copy_to_vtable_slot": 0x24,
    "actor_attr_copy_to": 0x464F30,         # copies ALL fields, 0 mask tests (Q1)
    "actor_attr_masked_merge_vtable_slot": 0x30,
    "actor_attr_masked_merge": 0x465E60,    # exists, never called on this pipe
    "actor_attr_serializer": 0x466230,
    "actor_attr_mask_low_empty_short_circuit": 0x4667AD,
    "actor_attr_mask_high_empty_short_circuit": 0x466B5C,
    "actor_attr_extra_group_offset": 0x1BC,
    "basic_attr_serializer": 0x4656F0,
    "name_board_label_name_reader_lo": 0x5BD624,
    "name_board_label_name_reader_hi": 0x5BD633,
    "name_board_null_attr_early_return": 0x5BD8C7,
    "movement_merge_against_previous_frame": 0x467130,           # Q2
    "movement_merge_singleton": 0x01081A90,
    "movement_merge_singleton_offset": 0x154,
    "movement_attr_serializer": 0x4671C0,
    "attr_apply_and_dead_sync": 0x4446F0,
    "dead_state_sync": 0x4437C0,
    "death_predicate_sites": (0x43BD7A, 0x43BDAA),               # HP == 0 (Q1)
    "update_when_known_vtable_slot": 0x20,
    "spawn_applies_through_vtable_slot": 0x10,
}


# ---------------------------------------------------------------------------
# The probes, resolved from the frozen placement source.  The anchor position
# is not typed by a human: it is placement 0 of PORT_ROYAL_UNAMBIGUOUS_
# PLACEMENTS (115 rows, SHA-256 22D7430E..9618), the same nearest-to-spawn
# rule and the same pinned answer the HYP-PF-023 lane uses.  The identities
# and offsets are DESIGN CHOICES and say so above.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RemotePlayerProbe:
    role: str                      # "A" / "B" / "C"
    identity: int
    name: str
    x: float
    y: float
    z: float
    scene_id: int
    scene_sequence: int
    # Only the negative control uses these two, but every probe records the
    # placement it derived from so the oracle cross-check can run for all.
    anchor_placement_index: int
    anchor_template_id: int
    anchor_visual_preset: str


# The pinned answer of the nearest-placement rule (drift in the frozen source
# turns this lane red instead of silently moving the probes).
REMOTE_PLAYER_ANCHOR_PLACEMENT_INDEX = 0
REMOTE_PLAYER_ANCHOR_TEMPLATE_ID = 1
REMOTE_PLAYER_ANCHOR_NPC_IDENTITY = 0x2001
REMOTE_PLAYER_ANCHOR_VISUAL_PRESET = "P_MALE_002_000_SP1"
REMOTE_PLAYER_ANCHOR_SOURCE_NAME = "Navy Transfer"

# The deterministic bytes the sweep produces for those probes.  SPAWN_AVATAR
# is a SKELETON pin (see the module docstring): everything this module
# composes, i.e. the frame up to and including the AvatarAttr id tag; the
# opaque avatar tail is structurally checked instead.  Values are computed by
# the encoder itself, re-derived independently by the verifier, and asserted
# by the headless replay and the tests, so no two readers can agree with each
# other while both disagreeing with the wire.
REMOTE_PLAYER_PINS: dict[str, dict[str, Any]] = {
    SPAWN_BARE_STEP_LABEL: {
        "basic_mask": 0x030D,
        "movement_mask": 0xFF,
        "pc_size": 169,
        "pc_sha256":
            "2D45DB50F86B529CCB22AD31C67BCD232EF289CB72A653360B546923EAB76466",
        "frame_size": 181,
        "frame_sha256":
            "30E80C5C920E094F625196968D30389113B5C6F6160078CB71795B1E43C5A06A",
    },
    SPAWN_AVATAR_STEP_LABEL: {
        "basic_mask": 0x030D,
        "movement_mask": 0xFF,
        "avatar_tail_excluded_from_pin": True,
        "pc_skeleton_size": 172,
        "pc_skeleton_sha256":
            "F4F72429FE91DCAD15D98FA325E02F64821024CD2900C93F6F78EF0EAB815E75",
    },
    MOVE_A_1_STEP_LABEL: {
        "movement_mask": 0x01,
        "pc_size": 61,
        "pc_sha256":
            "F81490F852AD70E7C9101E8E5DC52DA4AC3EE2027D032DCA392A613413F8743F",
        "frame_size": 72,
        "frame_sha256":
            "FFFBFDDF972BFF587A0AAB6F745EC2760D71F36BCE25F34D94275CF9706EB7CF",
    },
    MOVE_A_2_STEP_LABEL: {
        "movement_mask": 0x03,
        "pc_size": 66,
        "pc_sha256":
            "2DED86222CB7D7DCDC0778E88F4F711E5C3692EF791438BF719A995A455239C7",
        "frame_size": 77,
        "frame_sha256":
            "2369FD47F6F58327C32735C3055A1C9BC03F2E2F9A3952FBBED9A67A5CA53AA4",
    },
    NEGATIVE_CONTROL_STEP_LABEL: {
        "basic_mask": 0x030D,
        "movement_mask": 0xFF,
        "pc_size": 206,
        "pc_sha256":
            "9F73EEE1F170347B6345772E2D667D6F035B5801FEE165C441DA073762FF07C9",
        "frame_size": 218,
        "frame_sha256":
            "32825C8E207026758936FBDE4FAE00511D2160FDE13C4AB16B927B3083479688",
    },
}


class RemotePlayerValidationError(RuntimeError):
    """A composed sweep that must never reach a socket."""


def _refuse(reason: str, detail: str = "") -> None:
    message = "HYP-PF-025 refused: " + reason
    if detail:
        message += " (" + detail + ")"
    raise ValueError(message)


def _require_probe_identity(identity: Any, npc_band_top: int) -> int:
    if type(identity) is not int or type(identity) is bool:
        _refuse("probe_identity_outside_qword", repr(identity))
    if not 0 <= identity <= 0xFFFFFFFFFFFFFFFF:
        _refuse("probe_identity_outside_qword", hex(identity))
    if NPC_IDENTITY_BAND_BASE < identity <= npc_band_top:
        _refuse(
            "probe_identity_collides_with_the_frozen_npc_band",
            hex(identity),
        )
    if identity >= CHARACTER_IDENTITY_FLOOR:
        _refuse(
            "probe_identity_collides_with_the_character_identity_space",
            hex(identity),
        )
    return identity


def resolve_probes(legacy: Any) -> tuple[RemotePlayerProbe, ...]:
    """Derive A/B/C from the frozen placement source, refusing on any drift."""
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
            raise RemotePlayerValidationError(
                "frozen_placement_source_drift: non-finite distance"
            )
        key = (distance2, placement.placement_index)
        if best is None or key < best[0]:
            best = (key, placement)
    if best is None:
        raise RemotePlayerValidationError(
            "frozen_placement_source_drift: no candidate"
        )
    anchor = best[1]
    if (
        anchor.placement_index != REMOTE_PLAYER_ANCHOR_PLACEMENT_INDEX
        or anchor.template_id != REMOTE_PLAYER_ANCHOR_TEMPLATE_ID
        or anchor.actor_identity != REMOTE_PLAYER_ANCHOR_NPC_IDENTITY
        or anchor.visual_preset != REMOTE_PLAYER_ANCHOR_VISUAL_PRESET
        or anchor.source_name != REMOTE_PLAYER_ANCHOR_SOURCE_NAME
    ):
        raise RemotePlayerValidationError(
            "frozen_placement_source_drift: the nearest placement is no "
            "longer the pinned one"
        )
    npc_band_top = NPC_IDENTITY_BAND_BASE + len(placements)
    identities = (PROBE_IDENTITY_A, PROBE_IDENTITY_B, PROBE_IDENTITY_C)
    if len(set(identities)) != len(identities):
        _refuse("probe_identity_duplicated_across_steps_that_declare_new_actors")
    for identity in identities:
        _require_probe_identity(identity, npc_band_top)
    common = dict(
        scene_id=SCENE_ID, scene_sequence=SCENE_SEQUENCE,
        anchor_placement_index=anchor.placement_index,
        anchor_template_id=anchor.template_id,
        anchor_visual_preset=anchor.visual_preset,
    )
    return (
        RemotePlayerProbe(
            "A", PROBE_IDENTITY_A, PROBE_NAME_A,
            anchor.x, anchor.y, anchor.z, **common,
        ),
        RemotePlayerProbe(
            "B", PROBE_IDENTITY_B, PROBE_NAME_B,
            anchor.x + PROBE_B_X_OFFSET, anchor.y, anchor.z, **common,
        ),
        RemotePlayerProbe(
            "C", PROBE_IDENTITY_C, PROBE_NAME_C,
            anchor.x + PROBE_C_X_OFFSET, anchor.y, anchor.z, **common,
        ),
    )


# ---------------------------------------------------------------------------
# The wire unlock.  Same shape as HYP-PF-023's lethal unlock: derived ONCE
# from the allowlisted scenario object and required by every code path that
# can put actor_type 2 on the wire.  Compared by identity everywhere.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RemotePlayerWireUnlock:
    scenario_id: str
    hypothesis_id: str


@dataclass(frozen=True)
class RemotePlayerHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float
    first_delay_seconds: float
    action_label_prefix: str


_PROFILE = RemotePlayerHypothesisScenario(
    REMOTE_PLAYER_SCENARIO_ID,
    REMOTE_PLAYER_HYPOTHESIS_ID,
    REMOTE_PLAYER_STEP_ORDER,
    REMOTE_PLAYER_SPACING_SECONDS,
    REMOTE_PLAYER_FIRST_DELAY_SECONDS,
    REMOTE_PLAYER_ACTION_LABEL_PREFIX,
)
_ALLOWED_PROFILES = (_PROFILE,)
_UNLOCK = RemotePlayerWireUnlock(
    REMOTE_PLAYER_SCENARIO_ID, REMOTE_PLAYER_HYPOTHESIS_ID,
)


def require_remote_player_hypothesis_scenario(
    value: Any,
) -> RemotePlayerHypothesisScenario:
    if type(value) is not RemotePlayerHypothesisScenario or not any(
        value == allowed for allowed in _ALLOWED_PROFILES
    ):
        raise ValueError(
            "remote player hypothesis scenario object exceeds the allowlist"
        )
    return value


def remote_player_wire_unlock(value: Any) -> RemotePlayerWireUnlock:
    """The only key that lets this process put actor_type 2 on the wire."""
    require_remote_player_hypothesis_scenario(value)
    return _UNLOCK


def require_remote_player_wire_unlock(value: Any) -> RemotePlayerWireUnlock:
    if value is not _UNLOCK:
        _refuse("missing_or_forged_wire_unlock")
    return value


# ---------------------------------------------------------------------------
# The encoder.
# ---------------------------------------------------------------------------
def _require_finite_float32(value: Any, label: str) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        _refuse("movement_position_not_finite_float32", label)
    result = float(value)
    if not math.isfinite(result) or abs(result) > 3.4028234663852886e38:
        _refuse("movement_position_not_finite_float32", label)
    return result


def _require_probe(probe: Any) -> RemotePlayerProbe:
    if type(probe) is not RemotePlayerProbe:
        _refuse("probe_object_is_not_the_typed_probe", repr(type(probe)))
    return probe


def _require_probe_name(name: Any) -> str:
    if type(name) is not str or not name:
        _refuse("character_name_not_encodable_as_utf16le", repr(name))
    try:
        raw = name.encode("utf-16le")
    except UnicodeEncodeError:
        _refuse("character_name_not_encodable_as_utf16le", repr(name))
    if len(raw) % 2:
        _refuse("character_name_not_encodable_as_utf16le", "odd byte length")
    return name


def _require_hp(current_hp: Any, max_hp: Any) -> tuple[int, int]:
    for value in (current_hp, max_hp):
        if type(value) is not int or type(value) is bool:
            _refuse("hp_zero_would_cross_into_the_death_chain",
                    "hp must be an int")
        if not 0 <= value <= 0xFFFFFFFF:
            _refuse("hp_zero_would_cross_into_the_death_chain",
                    "hp must fit u32")
    if current_hp < REMOTE_PLAYER_HP_MIN:
        _refuse(
            "hp_zero_would_cross_into_the_death_chain",
            "0x4446F0 calls 0x4437C0 on every update frame and both "
            "predicates need BasicAttr +0x44 == 0",
        )
    return current_hp, max_hp


def encode_remote_player_actor_attr(
    legacy: Any,
    probe: RemotePlayerProbe,
    unlock: Any,
    *,
    basic_mask: int = BASIC_MASK_PROBE,
    actor_mask: int = ACTOR_ATTR_MASK_PROBE,
    extra_group_value: int = ACTOR_ATTR_EXTRA_GROUP_VALUE,
    current_hp: int = REMOTE_PLAYER_HP_ALIVE,
    max_hp: int = REMOTE_PLAYER_HP_MAX,
) -> bytes:
    """One ActorAttr body carrying BasicAttr bit 0x0001 (the name) -- the one
    field no encoder in this tree has ever put on the ActorAttr wire.

    The BasicAttr prefix (DBAttribute mask + identity + BasicAttr mask +
    fields through scene_seq) is asserted byte-for-byte equal to the same
    span of ``legacy.make_npc_attr(...)`` with ``basic_name`` set --
    ``BasicAttr`` is the shared base class and its serializer 0x4656F0 runs
    first on both attr classes, so the projection that has been in front of
    a real client since OBJECT-POP-002 is a free oracle for this new body.
    """
    require_remote_player_wire_unlock(unlock)
    probe = _require_probe(probe)
    name = _require_probe_name(probe.name)
    current_hp, max_hp = _require_hp(current_hp, max_hp)
    if type(basic_mask) is not int or type(basic_mask) is bool:
        _refuse("basic_mask_is_not_the_pinned_probe_mask", repr(basic_mask))
    if basic_mask & BASIC_BIT_DEATH_TIMER_FORBIDDEN:
        _refuse(
            "death_timer_bit_is_not_this_lanes_field",
            "BasicAttr bit 0x0080 belongs to HYP-PF-023",
        )
    if basic_mask != BASIC_MASK_PROBE:
        _refuse("basic_mask_is_not_the_pinned_probe_mask", hex(basic_mask))
    if not basic_mask & BASIC_BIT_NAME:
        _refuse("basic_name_bit_set_without_a_name", "the bit is required")
    if type(actor_mask) is not int or type(actor_mask) is bool:
        _refuse("actor_attr_mask_is_not_the_pinned_probe_mask", repr(actor_mask))
    if actor_mask >= ACTOR_ATTR_MASK_LOW_HALF_LIMIT:
        _refuse("actor_attr_mask_high_half_not_implemented", hex(actor_mask))
    if actor_mask != ACTOR_ATTR_MASK_PROBE:
        _refuse("actor_attr_mask_is_not_the_pinned_probe_mask", hex(actor_mask))
    if extra_group_value != ACTOR_ATTR_EXTRA_GROUP_VALUE:
        _refuse("actor_attr_extra_group_flag_not_one", repr(extra_group_value))

    prefix = bytes(
        legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK)
        + legacy.qwordtag(IDENTITY_TAG, probe.identity)
        + legacy.u16tag(BASIC_ATTR_MASK_TAG, basic_mask)
        # Ascending mask-bit order inside the block, which is the order
        # BasicAttr's serializer 0x4656F0 writes and its reader expects.
        + legacy.wstr_tag(name)                                # 0x0001
        + legacy.u32tag(0x14, current_hp)                      # 0x0004
        + legacy.u32tag(0x14, max_hp)                          # 0x0008
        + legacy.u16tag(BASIC_ATTR_MASK_TAG, probe.scene_id)   # 0x0100
        + legacy.qwordtag(IDENTITY_TAG, probe.scene_sequence)  # 0x0200
    )
    _require_basic_prefix_matches_make_npc_attr(
        legacy, prefix, probe, current_hp, max_hp,
    )
    body = (
        prefix
        + legacy.qwordtag(ACTOR_ATTR_MASK_TAG, actor_mask)
        + legacy.u8tag(ACTOR_ATTR_EXTRA_GROUP_TAG, extra_group_value)
    )
    return bytes(body)


def _require_basic_prefix_matches_make_npc_attr(
    legacy: Any,
    prefix: bytes,
    probe: RemotePlayerProbe,
    current_hp: int,
    max_hp: int,
) -> None:
    """The free oracle.  BasicAttr::Serial 0x4656F0 runs first on BOTH attr
    classes, so our ActorAttr prefix must equal the same span of the frozen,
    client-proven ``make_npc_attr`` body.  Anything else means the new name
    field landed in the wrong place, and NO BYTES leave this module."""
    baseline = legacy.make_npc_attr(
        probe.anchor_template_id, probe.identity,
        probe.scene_id, probe.scene_sequence, "",
        current_hp, max_hp, None, probe.name,
    )
    if bytes(baseline[:len(prefix)]) != prefix:
        _refuse(
            "basic_prefix_does_not_reproduce_make_npc_attr",
            "the shared BasicAttr span drifted",
        )


def _make_movement_attr(
    legacy: Any,
    probe: RemotePlayerProbe,
    mask: int,
    x: float,
    y: float,
    z: float,
    heading: float,
) -> bytes:
    if type(mask) is not int or type(mask) is bool or (
        mask not in MOVEMENT_MASKS_PINNED
    ):
        _refuse("movement_mask_outside_the_pinned_set", repr(mask))
    x = _require_finite_float32(x, "x")
    y = _require_finite_float32(y, "y")
    z = _require_finite_float32(z, "z")
    heading = _require_finite_float32(heading, "heading")
    return legacy.make_remote_movement_attr(
        probe.identity, x, y, z, heading, mask=mask,
    )


def _require_avatar_wire(avatar_wire: Any, probe: RemotePlayerProbe) -> bytes:
    """The opaque replay.  We can rebind its identity (the proven common-Attr
    prefix) and nothing else; the rest of the body is preserved bytes."""
    if type(avatar_wire) is not bytes or len(avatar_wire) < 11 or (
        avatar_wire[0] != DB_ATTRIBUTE_MASK_TAG
        or not (avatar_wire[1] & DB_ATTRIBUTE_IDENTITY_MASK)
        or avatar_wire[2] != IDENTITY_TAG
    ):
        _refuse("avatar_wire_absent_or_not_a_common_attr_body")
    rebound = bind_common_attr_identity(
        avatar_wire, probe.identity & 0xFFFFFFFF,
        (probe.identity >> 32) & 0xFFFFFFFF,
    )
    lo, hi = struct.unpack_from("<II", rebound, 3)
    if ((hi << 32) | lo) != probe.identity:
        _refuse("avatar_wire_identity_rebind_failed")
    return rebound


def encode_remote_player_entry(
    legacy: Any,
    step_label: str,
    probe: RemotePlayerProbe,
    unlock: Any,
    *,
    actor_type: int = REMOTE_PLAYER_ACTOR_TYPE,
    avatar_wire: Any = None,
) -> bytes:
    """One actor entry for one step of the plan, fail-closed on every axis."""
    require_remote_player_wire_unlock(unlock)
    probe = _require_probe(probe)
    if step_label not in REMOTE_PLAYER_STEP_BY_LABEL:
        _refuse("unknown_step_label", repr(step_label))
    if type(actor_type) is not int or type(actor_type) is bool:
        _refuse("actor_type_outside_client_jump_table", repr(actor_type))
    if not CLIENT_ACTOR_TYPE_RANGE[0] <= actor_type <= CLIENT_ACTOR_TYPE_RANGE[1]:
        _refuse(
            "actor_type_outside_client_jump_table",
            "0x446B14 creates nothing for %r" % actor_type,
        )
    if actor_type == LOCAL_PLAYER_ACTOR_TYPE:
        _refuse(
            "actor_type_3_would_claim_the_local_player_slot",
            "CMyActor is a singleton gated by global 0x1032EC4",
        )
    shape = REMOTE_PLAYER_STEP_BY_LABEL[step_label][2]
    wants_actor_attr = shape in (
        "actor_attr_and_full_movement", "actor_attr_movement_then_avatar_tail",
    )
    if wants_actor_attr and actor_type == NPC_STYLE_ACTOR_TYPE:
        _refuse(
            "actor_attr_inside_actor_type_4_entry",
            "bind thunk 0x469760 gates on CNetActor; the bytes would be "
            "dropped in silence and the attended reading would be wrong",
        )
    if shape == "wrong_class_npc_attr_and_full_movement":
        pass  # the ONE place NPCAttr may ride an actor_type 2 entry
    elif actor_type == REMOTE_PLAYER_ACTOR_TYPE and shape not in (
        "actor_attr_and_full_movement", "actor_attr_movement_then_avatar_tail",
        "movement_only_position", "movement_only_position_and_heading",
    ):
        _refuse("unknown_step_label", repr(shape))
    if actor_type != REMOTE_PLAYER_ACTOR_TYPE:
        _refuse(
            "actor_type_not_the_remote_player_branch",
            "this lane pins actor_type 2 on every frame",
        )

    attrs: list[tuple[int, bytes]] = []
    avatar_tail = b""
    if shape == "actor_attr_and_full_movement":
        attrs.append((
            ACTOR_ATTR_ID,
            encode_remote_player_actor_attr(legacy, probe, unlock),
        ))
        attrs.append((
            MOVEMENT_ATTR_ID,
            _make_movement_attr(
                legacy, probe, MOVEMENT_MASK_FULL,
                probe.x, probe.y, probe.z, 0.0,
            ),
        ))
    elif shape == "actor_attr_movement_then_avatar_tail":
        attrs.append((
            ACTOR_ATTR_ID,
            encode_remote_player_actor_attr(legacy, probe, unlock),
        ))
        attrs.append((
            MOVEMENT_ATTR_ID,
            _make_movement_attr(
                legacy, probe, MOVEMENT_MASK_FULL,
                probe.x, probe.y, probe.z, 0.0,
            ),
        ))
        avatar_tail = _require_avatar_wire(avatar_wire, probe)
        attrs.append((AVATAR_ATTR_ID, avatar_tail))
    elif shape == "movement_only_position":
        attrs.append((
            MOVEMENT_ATTR_ID,
            _make_movement_attr(
                legacy, probe, MOVEMENT_MASK_POSITION,
                probe.x + MOVE_X_OFFSET, probe.y, probe.z, 0.0,
            ),
        ))
    elif shape == "movement_only_position_and_heading":
        attrs.append((
            MOVEMENT_ATTR_ID,
            _make_movement_attr(
                legacy, probe, MOVEMENT_MASK_POSITION_AND_HEADING,
                probe.x + MOVE_X_OFFSET, probe.y, probe.z, MOVE_HEADING,
            ),
        ))
    elif shape == "wrong_class_npc_attr_and_full_movement":
        # Called STRAIGHT into the frozen serializer, no modification: the
        # control must be the known-good NPC body, or a silent drop would be
        # ambiguous between "gate works" and "we broke the body".
        attrs.append((
            NPC_ATTR_ID,
            legacy.make_npc_attr(
                probe.anchor_template_id, probe.identity,
                probe.scene_id, probe.scene_sequence,
                probe.anchor_visual_preset,
                REMOTE_PLAYER_HP_ALIVE, REMOTE_PLAYER_HP_MAX,
                None, probe.name,
            ),
        ))
        attrs.append((
            MOVEMENT_ATTR_ID,
            _make_movement_attr(
                legacy, probe, MOVEMENT_MASK_FULL,
                probe.x, probe.y, probe.z, 0.0,
            ),
        ))
    else:  # pragma: no cover - unreachable, the shapes are a closed set
        _refuse("unknown_step_label", repr(shape))
    for attr_id, _body in attrs:
        if attr_id == SKILL_ATTR_ID:
            _refuse("skill_attr_is_my_actor_only")
        if attr_id == NPC_ATTR_ID and shape != (
            "wrong_class_npc_attr_and_full_movement"
        ):
            _refuse("npc_attr_inside_actor_type_2_outside_the_negative_control")
    return legacy.make_remote_actor_entry(actor_type, probe.identity, attrs)


def make_remote_player_step_response(
    legacy: Any,
    probes: tuple[RemotePlayerProbe, ...],
    index: Any,
    unlock: Any,
    profile: Any,
    avatar_wire: Any = None,
) -> tuple[bytes, bytes]:
    """Compose one step of the visibility sweep."""
    require_remote_player_hypothesis_scenario(profile)
    require_remote_player_wire_unlock(unlock)
    if type(index) is not int or type(index) is bool:
        _refuse("unknown_step_label", repr(index))
    if not 0 <= index < len(profile.step_order):
        _refuse("unknown_step_label", repr(index))
    label = profile.step_order[index]
    row = REMOTE_PLAYER_STEP_BY_LABEL.get(label)
    if row is None or row is not REMOTE_PLAYER_STEPS[index]:
        raise RemotePlayerValidationError("HYP-PF-025 step plan drift")
    by_role = {probe.role: probe for probe in probes}
    if sorted(by_role) != ["A", "B", "C"] or len(probes) != 3:
        _refuse("probe_object_is_not_the_typed_probe", "need roles A/B/C")
    probe = by_role[row[1]]
    entry = encode_remote_player_entry(
        legacy, label, probe, unlock,
        avatar_wire=(avatar_wire if label == SPAWN_AVATAR_STEP_LABEL else None),
    )
    pc, frame = legacy.make_runtime_remote_actors([entry])
    if frame != legacy.frame_pc(pc):
        raise RemotePlayerValidationError("HYP-PF-025 frame drift")
    return pc, frame


def build_remote_player_sweep(
    legacy: Any,
    probes: tuple[RemotePlayerProbe, ...],
    unlock: Any,
    profile: Any,
    *,
    avatar_wire: Any,
    selected_identity: Any,
) -> list[tuple[str, bytes, bytes, float]]:
    """Compose the whole five-frame sweep and refuse anything off-plan.

    ``selected_identity`` is the qword identity of the character the client
    is playing.  A probe that collides with it would take the LOCAL player's
    own actor down the update path, so the collision is refused by name
    before one byte is composed.
    """
    require_remote_player_hypothesis_scenario(profile)
    require_remote_player_wire_unlock(unlock)
    if type(selected_identity) is not int or type(selected_identity) is bool:
        _refuse(
            "probe_identity_collides_with_the_selected_character",
            "selected identity must be an int",
        )
    for probe in probes:
        _require_probe(probe)
        if probe.identity == selected_identity:
            _refuse(
                "probe_identity_collides_with_the_selected_character",
                hex(probe.identity),
            )
    actions: list[tuple[str, bytes, bytes, float]] = []
    for index, label in enumerate(profile.step_order):
        pc, frame = make_remote_player_step_response(
            legacy, probes, index, unlock, profile,
            avatar_wire=avatar_wire,
        )
        delay = (
            profile.first_delay_seconds if index == 0
            else profile.spacing_seconds
        )
        actions.append((profile.action_label_prefix + label, pc, frame, delay))
    rows = validate_remote_player_sweep(actions, profile, probes)
    _require_pinned_composition(profile, rows)
    return actions


def _require_pinned_composition(
    profile: RemotePlayerHypothesisScenario,
    rows: list[dict[str, Any]],
) -> None:
    """Refuse to hand back a sweep whose bytes are not the pinned ones."""
    for index, label in enumerate(profile.step_order):
        pin = REMOTE_PLAYER_PINS[label]
        row = rows[index]
        for key, expected in pin.items():
            if row.get(key) != expected:
                raise RemotePlayerValidationError(
                    "composed_bytes_do_not_match_the_pin: %s %s: %r != %r"
                    % (label, key, row.get(key), expected)
                )


# ---------------------------------------------------------------------------
# The independent walker.  Deliberately does not reuse the encoder's own
# composition for anything except the constants, so a symmetrical bug in the
# encoder cannot hide here.
# ---------------------------------------------------------------------------
_SCALAR_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x12: 2, 0x14: 4, 0x26: 4,
                 0x2A: 4, 0x32: 8}
_BASIC_FIELD_ORDER = (
    (0x0001, 0x48), (0x0002, 0x12), (0x0004, 0x14), (0x0008, 0x14),
    (0x0010, 0x14), (0x0020, 0x14), (0x0040, 0x2A), (0x0080, 0x2A),
    (0x0100, 0x12), (0x0200, 0x32), (0x0400, 0x14),
)


def _walk_envelope(pc: bytes) -> int:
    if type(pc) is not bytes:
        raise RemotePlayerValidationError("a frame must be bytes")
    if len(pc) < ACTOR_ENTRY_LIST_OFFSET:
        raise RemotePlayerValidationError("frame is shorter than the envelope")
    if pc[0] != 0x12 or int.from_bytes(pc[1:3], "little") != (
        RUNTIME_PROTOCOL_RES_ID
    ):
        raise RemotePlayerValidationError(
            "envelope_id_or_version_not_pinned: not GSCN_RunTimeProtocolRes"
        )
    if pc[3] != 0x14 or int.from_bytes(pc[4:8], "little") != 0:
        raise RemotePlayerValidationError("envelope u32 field drift")
    if pc[8] != 0x08 or pc[9] != RUNTIME_PROTOCOL_RES_VERSION:
        raise RemotePlayerValidationError(
            "envelope_id_or_version_not_pinned: version byte or tag"
        )
    if pc[10] != 0x0B or pc[INHERITED_CHANGE_MASK_OFFSET] != (
        INHERITED_CHANGE_MASK_ABSENT
    ):
        raise RemotePlayerValidationError(
            "inherited_change_mask_not_zero"
        )
    if pc[12] != 0x0B or pc[DERIVED_CHANGE_MASK_OFFSET] != (
        DERIVED_CHANGE_MASK_ACTOR_ENTRIES
    ):
        raise RemotePlayerValidationError(
            "derived_change_mask_not_the_actor_entry_bit"
        )
    if pc[ACTOR_ENTRY_COUNT_TAG_OFFSET] != 0x12:
        raise RemotePlayerValidationError("the actor count tag drifted")
    count = int.from_bytes(
        pc[ACTOR_ENTRY_COUNT_OFFSET:ACTOR_ENTRY_COUNT_OFFSET + 2], "little",
    )
    if count != 1:
        raise RemotePlayerValidationError(
            "actor_entry_count_not_one: V43 met ErrorData=28317 on combined "
            "streams and V42 proved one entry per frame is parse-safe"
        )
    return ACTOR_ENTRY_LIST_OFFSET


def _walk_actor_attr(pc: bytes, cursor: int) -> tuple[dict[str, Any], int]:
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG or pc[cursor + 1] != (
        DB_ATTRIBUTE_IDENTITY_MASK
    ):
        raise RemotePlayerValidationError("ActorAttr DBAttribute drift")
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise RemotePlayerValidationError("ActorAttr identity tag drift")
    identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != BASIC_ATTR_MASK_TAG:
        raise RemotePlayerValidationError("BasicAttr mask tag drift")
    basic_mask = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
    cursor += 3
    if basic_mask & BASIC_BIT_DEATH_TIMER_FORBIDDEN:
        raise RemotePlayerValidationError(
            "death_timer_bit_is_not_this_lanes_field"
        )
    if basic_mask & ~0x07FF:
        raise RemotePlayerValidationError(
            "BasicAttr mask 0x%04X carries a bit this walker cannot read"
            % basic_mask
        )
    fields: dict[int, Any] = {}
    for bit, tag in _BASIC_FIELD_ORDER:
        if not basic_mask & bit:
            continue
        if pc[cursor] != tag:
            raise RemotePlayerValidationError(
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
    if pc[cursor] != ACTOR_ATTR_MASK_TAG:
        raise RemotePlayerValidationError("ActorAttr 64-bit mask tag drift")
    actor_mask = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != ACTOR_ATTR_EXTRA_GROUP_TAG:
        raise RemotePlayerValidationError("ActorAttr extra-group tag drift")
    extra_group = pc[cursor + 1]
    cursor += 2
    if extra_group != ACTOR_ATTR_EXTRA_GROUP_VALUE:
        raise RemotePlayerValidationError("actor_attr_extra_group_flag_not_one")
    if actor_mask != ACTOR_ATTR_MASK_PROBE:
        raise RemotePlayerValidationError(
            "actor_attr_mask_is_not_the_pinned_probe_mask"
        )
    return (
        {
            "identity": identity,
            "basic_mask": basic_mask,
            "fields": fields,
            "actor_mask": actor_mask,
            "extra_group": extra_group,
        },
        cursor,
    )


def _walk_npc_attr(pc: bytes, cursor: int) -> tuple[dict[str, Any], int]:
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG or pc[cursor + 1] != (
        DB_ATTRIBUTE_IDENTITY_MASK
    ):
        raise RemotePlayerValidationError("NPCAttr DBAttribute drift")
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise RemotePlayerValidationError("NPCAttr identity tag drift")
    identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != BASIC_ATTR_MASK_TAG:
        raise RemotePlayerValidationError("NPCAttr BasicAttr mask tag drift")
    basic_mask = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
    cursor += 3
    fields: dict[int, Any] = {}
    for bit, tag in _BASIC_FIELD_ORDER:
        if not basic_mask & bit:
            continue
        if pc[cursor] != tag:
            raise RemotePlayerValidationError("NPCAttr BasicAttr field drift")
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
    if pc[cursor] != 0x0B:
        raise RemotePlayerValidationError("NPCAttr own-mask tag drift")
    npc_mask = pc[cursor + 1]
    cursor += 2
    template_id = None
    visual_preset = None
    if npc_mask & 0x01:
        if pc[cursor] != 0x12:
            raise RemotePlayerValidationError("NPCAttr template tag drift")
        template_id = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
        cursor += 3
    if npc_mask & 0x04:
        if pc[cursor] != 0x48:
            raise RemotePlayerValidationError("NPCAttr preset tag drift")
        length = int.from_bytes(pc[cursor + 1:cursor + 5], "little")
        visual_preset = pc[cursor + 5:cursor + 5 + length].decode("utf-16le")
        cursor += 5 + length
    return (
        {
            "identity": identity,
            "basic_mask": basic_mask,
            "fields": fields,
            "npc_mask": npc_mask,
            "template_id": template_id,
            "visual_preset": visual_preset,
        },
        cursor,
    )


_MOVEMENT_FIELDS = (
    (0x01, "position"), (0x02, "heading"), (0x04, "mode"), (0x08, "flags"),
    (0x10, "p40"), (0x20, "p44"), (0x40, "p48"),
)


def _walk_movement_attr(pc: bytes, cursor: int) -> tuple[dict[str, Any], int]:
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG or pc[cursor + 1] != 0x01:
        raise RemotePlayerValidationError("MovementAttr DBAttribute drift")
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise RemotePlayerValidationError("MovementAttr identity tag drift")
    identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != 0x0B:
        raise RemotePlayerValidationError("MovementAttr mask tag drift")
    mask = pc[cursor + 1]
    cursor += 2
    out: dict[str, Any] = {"identity": identity, "mask": mask}
    for bit, name in _MOVEMENT_FIELDS:
        if not mask & bit:
            continue
        if bit == 0x01:
            values = []
            for _ in range(3):
                if pc[cursor] != 0x2A:
                    raise RemotePlayerValidationError(
                        "MovementAttr position tag drift"
                    )
                values.append(
                    struct.unpack("<f", pc[cursor + 1:cursor + 5])[0]
                )
                cursor += 5
            out["position"] = tuple(values)
        elif bit == 0x04:
            if pc[cursor] != 0x0B:
                raise RemotePlayerValidationError("MovementAttr mode tag drift")
            out[name] = pc[cursor + 1]
            cursor += 2
        elif bit == 0x08:
            if pc[cursor] != 0x26:
                raise RemotePlayerValidationError("MovementAttr flags tag drift")
            out[name] = int.from_bytes(pc[cursor + 1:cursor + 5], "little")
            cursor += 5
        else:
            if pc[cursor] != 0x2A:
                raise RemotePlayerValidationError("MovementAttr f32 tag drift")
            out[name] = struct.unpack("<f", pc[cursor + 1:cursor + 5])[0]
            cursor += 5
    return out, cursor


def decode_remote_player_actor_entry_frame(pc: bytes) -> dict[str, Any]:
    """Read one composed PC back with a strict, standalone tag walker.

    The AvatarAttr body is opaque replay: the walker requires it to be the
    LAST attr, takes everything to the end of the frame as its body, and
    checks the proven common-Attr prefix and the rebound identity -- the two
    things about it that are not opaque.
    """
    cursor = _walk_envelope(pc)
    if pc[cursor] != 0x0B:
        raise RemotePlayerValidationError("actor type tag drift")
    actor_type = pc[cursor + 1]
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise RemotePlayerValidationError("actor identity tag drift")
    identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != 0x0B:
        raise RemotePlayerValidationError("attr count tag drift")
    attr_count = pc[cursor + 1]
    cursor += 2

    attrs: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    for attr_index in range(attr_count):
        if pc[cursor] != 0x12:
            raise RemotePlayerValidationError("attr id tag drift")
        attr_id = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
        cursor += 3
        order.append(attr_id)
        if attr_id == SKILL_ATTR_ID:
            raise RemotePlayerValidationError("skill_attr_is_my_actor_only")
        if attr_id == ACTOR_ATTR_ID:
            parsed, cursor = _walk_actor_attr(pc, cursor)
            attrs[attr_id] = parsed
        elif attr_id == NPC_ATTR_ID:
            parsed, cursor = _walk_npc_attr(pc, cursor)
            attrs[attr_id] = parsed
        elif attr_id == MOVEMENT_ATTR_ID:
            parsed, cursor = _walk_movement_attr(pc, cursor)
            attrs[attr_id] = parsed
        elif attr_id == AVATAR_ATTR_ID:
            if attr_index != attr_count - 1:
                raise RemotePlayerValidationError(
                    "the opaque AvatarAttr must be the LAST attr of the "
                    "entry, or no independent walker can find its boundary"
                )
            body = pc[cursor:]
            if len(body) < 11 or body[0] != DB_ATTRIBUTE_MASK_TAG or not (
                body[1] & DB_ATTRIBUTE_IDENTITY_MASK
            ) or body[2] != IDENTITY_TAG:
                raise RemotePlayerValidationError(
                    "avatar_wire_absent_or_not_a_common_attr_body"
                )
            avatar_identity = int.from_bytes(body[3:11], "little")
            attrs[attr_id] = {
                "identity": avatar_identity,
                "body_size": len(body),
                "body_sha256": hashlib.sha256(body).hexdigest().upper(),
            }
            cursor = len(pc)
        else:
            raise RemotePlayerValidationError(
                "unexpected attr id 0x%04X on the actor-entry path" % attr_id
            )
    if cursor > len(pc):
        raise RemotePlayerValidationError(
            "the frame is truncated: the walker ran %d bytes past its end"
            % (cursor - len(pc))
        )
    if cursor != len(pc):
        raise RemotePlayerValidationError(
            "the frame has %d trailing bytes the walker could not account for"
            % (len(pc) - cursor)
        )
    return {
        "actor_type": actor_type,
        "identity": identity,
        "attr_order": tuple(order),
        "attrs": attrs,
    }


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def validate_remote_player_sweep(
    actions: Any,
    profile: Any,
    probes: tuple[RemotePlayerProbe, ...],
) -> list[dict[str, Any]]:
    """Prove a composed sweep is exactly the planned experiment.

    Raises :class:`RemotePlayerValidationError` on any of: a frame whose
    envelope is off-pin; an actor_type that is not 2; a position that did not
    come from the frozen placement plus the pinned offsets; a duplicated
    probe identity across the steps that declare new actors; a missing
    negative control; the death-timer bit anywhere; an avatar tail that is
    not the last attr or whose identity is not B's.
    """
    require_remote_player_hypothesis_scenario(profile)
    if type(actions) is not list:
        raise RemotePlayerValidationError("the sweep must be a list")
    if len(actions) != len(profile.step_order):
        raise RemotePlayerValidationError(
            "the sweep must carry exactly %d frames" % len(profile.step_order)
        )
    by_role = {probe.role: probe for probe in probes}
    if sorted(by_role) != ["A", "B", "C"]:
        raise RemotePlayerValidationError("the probes must be roles A/B/C")
    if len({probe.identity for probe in probes}) != 3:
        raise RemotePlayerValidationError(
            "probe_identity_duplicated_across_steps_that_declare_new_actors"
        )
    anchor = by_role["A"]
    expected_geometry = {
        SPAWN_BARE_STEP_LABEL: (
            "A", MOVEMENT_MASK_FULL,
            (_f32(anchor.x), _f32(anchor.y), _f32(anchor.z)), _f32(0.0),
        ),
        SPAWN_AVATAR_STEP_LABEL: (
            "B", MOVEMENT_MASK_FULL,
            (_f32(anchor.x + PROBE_B_X_OFFSET), _f32(anchor.y), _f32(anchor.z)),
            _f32(0.0),
        ),
        MOVE_A_1_STEP_LABEL: (
            "A", MOVEMENT_MASK_POSITION,
            (_f32(anchor.x + MOVE_X_OFFSET), _f32(anchor.y), _f32(anchor.z)),
            None,
        ),
        MOVE_A_2_STEP_LABEL: (
            "A", MOVEMENT_MASK_POSITION_AND_HEADING,
            (_f32(anchor.x + MOVE_X_OFFSET), _f32(anchor.y), _f32(anchor.z)),
            _f32(MOVE_HEADING),
        ),
        NEGATIVE_CONTROL_STEP_LABEL: (
            "C", MOVEMENT_MASK_FULL,
            (_f32(anchor.x + PROBE_C_X_OFFSET), _f32(anchor.y), _f32(anchor.z)),
            _f32(0.0),
        ),
    }
    rows: list[dict[str, Any]] = []
    saw_negative_control = False
    for index, action in enumerate(actions):
        if type(action) is not tuple or len(action) != 4:
            raise RemotePlayerValidationError(
                "each sweep entry must be (label, pc, frame, delay)"
            )
        label, pc, frame, delay = action
        step = profile.step_order[index]
        expected_label = profile.action_label_prefix + step
        if label != expected_label:
            raise RemotePlayerValidationError(
                "step_order_or_delay_not_pinned: step %d is labelled %r, "
                "expected %r" % (index, label, expected_label)
            )
        expected_delay = (
            profile.first_delay_seconds if index == 0
            else profile.spacing_seconds
        )
        if type(delay) is not float or delay != expected_delay:
            raise RemotePlayerValidationError(
                "step_order_or_delay_not_pinned: step %d delay %r != %r"
                % (index, delay, expected_delay)
            )
        if type(frame) is not bytes or not frame:
            raise RemotePlayerValidationError("step %d has no frame" % index)
        read = decode_remote_player_actor_entry_frame(pc)
        if read["actor_type"] != REMOTE_PLAYER_ACTOR_TYPE:
            raise RemotePlayerValidationError(
                "actor_type_not_the_remote_player_branch: %d"
                % read["actor_type"]
            )
        role, want_move_mask, want_xyz, want_heading = expected_geometry[step]
        probe = by_role[role]
        if read["identity"] != probe.identity:
            raise RemotePlayerValidationError(
                "step %d entry identity 0x%X is not probe %s's 0x%X"
                % (index, read["identity"], role, probe.identity)
            )
        movement = read["attrs"].get(MOVEMENT_ATTR_ID)
        if movement is None:
            raise RemotePlayerValidationError(
                "step %d carries no MovementAttr" % index
            )
        if movement["identity"] != probe.identity:
            raise RemotePlayerValidationError(
                "step %d MovementAttr identity differs from the entry" % index
            )
        if movement["mask"] != want_move_mask:
            raise RemotePlayerValidationError(
                "movement_mask_outside_the_pinned_set: step %d mask 0x%02X"
                % (index, movement["mask"])
            )
        if movement.get("position") != want_xyz:
            raise RemotePlayerValidationError(
                "position_not_derived_from_the_frozen_placement_source: "
                "step %d" % index
            )
        if want_heading is not None and want_move_mask != (
            MOVEMENT_MASK_POSITION
        ):
            got_heading = movement.get("heading", 0.0)
            if got_heading != want_heading:
                raise RemotePlayerValidationError(
                    "step %d heading %r is not the pinned %r"
                    % (index, got_heading, want_heading)
                )
        row: dict[str, Any] = {
            "index": index,
            "label": label,
            "delay_seconds": delay,
            "identity": read["identity"],
            "actor_type": read["actor_type"],
            "attr_order": read["attr_order"],
            "movement_mask": movement["mask"],
            "pc_size": len(pc),
            "frame_size": len(frame),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
        }
        if step in (SPAWN_BARE_STEP_LABEL, SPAWN_AVATAR_STEP_LABEL):
            actor = read["attrs"].get(ACTOR_ATTR_ID)
            if actor is None:
                raise RemotePlayerValidationError(
                    "step %d carries no ActorAttr" % index
                )
            if actor["identity"] != probe.identity:
                raise RemotePlayerValidationError(
                    "step %d ActorAttr identity differs from the entry" % index
                )
            name = actor["fields"].get(BASIC_BIT_NAME)
            if actor["basic_mask"] & BASIC_BIT_NAME and not name:
                raise RemotePlayerValidationError(
                    "basic_name_bit_set_without_a_name"
                )
            if name and not actor["basic_mask"] & BASIC_BIT_NAME:
                raise RemotePlayerValidationError("basic_name_without_the_bit")
            if name != probe.name:
                raise RemotePlayerValidationError(
                    "step %d name %r is not the pinned %r"
                    % (index, name, probe.name)
                )
            hp = actor["fields"].get(BASIC_BIT_CURRENT_HP)
            if hp is None or hp < REMOTE_PLAYER_HP_MIN:
                raise RemotePlayerValidationError(
                    "hp_zero_would_cross_into_the_death_chain"
                )
            row["basic_mask"] = actor["basic_mask"]
            row["name"] = name
            row["hp_current"] = hp
        if step == SPAWN_AVATAR_STEP_LABEL:
            avatar = read["attrs"].get(AVATAR_ATTR_ID)
            if avatar is None:
                raise RemotePlayerValidationError(
                    "the SPAWN_AVATAR step carries no AvatarAttr tail"
                )
            if avatar["identity"] != probe.identity:
                raise RemotePlayerValidationError(
                    "avatar_wire_identity_rebind_failed"
                )
            if read["attr_order"][-1] != AVATAR_ATTR_ID:
                raise RemotePlayerValidationError(
                    "the opaque AvatarAttr must be the LAST attr"
                )
            avatar_body_size = avatar["body_size"]
            skeleton = pc[:len(pc) - avatar_body_size]
            row["avatar_tail_excluded_from_pin"] = True
            row["avatar_body_size"] = avatar_body_size
            row["avatar_body_sha256"] = avatar["body_sha256"]
            row["pc_skeleton_size"] = len(skeleton)
            row["pc_skeleton_sha256"] = (
                hashlib.sha256(skeleton).hexdigest().upper()
            )
            # The full-byte keys stay OUT of the pinned row for this step on
            # purpose: they vary with the database character.
            del row["pc_sha256"], row["frame_sha256"]
            del row["pc_size"], row["frame_size"]
        if step == NEGATIVE_CONTROL_STEP_LABEL:
            saw_negative_control = True
            npc = read["attrs"].get(NPC_ATTR_ID)
            if npc is None:
                raise RemotePlayerValidationError(
                    "sweep_does_not_contain_the_negative_control: the control "
                    "frame lost its wrong-class NPCAttr"
                )
            if npc["identity"] != probe.identity:
                raise RemotePlayerValidationError(
                    "the control's NPCAttr identity differs from the entry"
                )
            if npc["fields"].get(BASIC_BIT_NAME) != probe.name:
                raise RemotePlayerValidationError(
                    "the control's NPCAttr must carry the pinned name: a "
                    "nameless control could not falsify the bind-gate claim"
                )
            row["basic_mask"] = npc["basic_mask"]
            row["npc_template_id"] = npc["template_id"]
            row["npc_visual_preset"] = npc["visual_preset"]
        if step in (MOVE_A_1_STEP_LABEL, MOVE_A_2_STEP_LABEL):
            if read["attr_order"] != (MOVEMENT_ATTR_ID,):
                raise RemotePlayerValidationError(
                    "step %d must carry EXACTLY one MovementAttr: the whole "
                    "experiment is what a lone movement frame does to a "
                    "known identity" % index
                )
        if ACTOR_ATTR_ID in read["attrs"] and step not in (
            SPAWN_BARE_STEP_LABEL, SPAWN_AVATAR_STEP_LABEL,
        ):
            raise RemotePlayerValidationError(
                "step %d carries an off-plan ActorAttr" % index
            )
        if NPC_ATTR_ID in read["attrs"] and step != (
            NEGATIVE_CONTROL_STEP_LABEL
        ):
            raise RemotePlayerValidationError(
                "npc_attr_inside_actor_type_2_outside_the_negative_control"
            )
        rows.append(row)
    if not saw_negative_control:
        raise RemotePlayerValidationError(
            "sweep_does_not_contain_the_negative_control"
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


REMOTE_PLAYER_CAPABILITIES = (
    "emit_gscn_runtimeprotocolres_0x6e9d_derived_mask_bit_0x02_actor_entries",
    "put_actor_type_2_cnetactor_on_the_actor_entry_wire_for_the_first_time",
    "emit_basicattr_bit_0x0001_the_name_on_the_actor_attr_wire_for_the_first_time",
    "replay_the_selected_characters_opaque_avatar_attr_under_a_probe_identity",
    "re_send_a_known_identity_with_a_lone_movement_attr_mask_0x01_and_0x03",
    "ship_a_wrong_class_npc_attr_as_the_negative_control_of_the_experiment",
    "reproduce_the_frozen_make_npc_attr_basic_prefix_byte_for_byte",
    "refuse_to_return_a_sweep_that_is_not_the_pinned_five_frame_plan",
)
REMOTE_PLAYER_NONCLAIMS = (
    "this_is_our_design_not_the_original_servers_which_is_unrecoverable",
    "no_client_has_ever_been_shown_one_byte_of_this_profile",
    "no_claim_that_actor_type_2_renders_at_all_or_renders_as_a_person",
    "no_claim_about_which_actor_attr_mask_bits_a_cnetactor_needs_to_render",
    "no_claim_that_the_avatar_attr_is_accepted_under_a_foreign_identity",
    "no_claim_that_the_name_board_fills_from_basicattr_0x28_on_screen",
    "no_despawn_path_exists_on_this_lane_a_probe_stays_until_disconnect",
    "ground_z_at_the_offset_positions_is_unchecked_floating_does_not_falsify",
    "no_interest_management_no_cadence_no_interpolation_that_is_chunk_3",
    "no_second_connection_no_broadcast_no_send_lock_no_population_py_change",
    "the_229_unresolved_vtable_0x20_dispatch_sites_are_inherited_not_narrowed",
    "production_dispatch_wiring_the_wiring_is_opt_in_and_production_allowed_is_false",
)


def _expected_scenario() -> dict[str, Any]:
    profile = _PROFILE
    return {
        "schema": 1,
        "id": profile.scenario_id,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": REMOTE_PLAYER_HYPOTHESIS_ID,
        "hypothesis_id_is_registered_in_the_ledger": True,
        "design_not_recovery": (
            "this_is_our_design_not_the_original_servers_which_is_"
            "unrecoverable"
        ),
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_actor_type_2_remote_player_probe_frames_"
                "no_write_no_close"
            ),
        },
        "dispatch": {
            "wired": True,
            "wiring_owner": "remote_player_dispatch_001_round_96",
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
        },
        "wire": {
            "vital_id": RUNTIME_PROTOCOL_RES_ID,
            "vital_version": RUNTIME_PROTOCOL_RES_VERSION,
            "envelope": "gscn_runtime_protocol_res_v4_actor_entry_collection",
            "inherited_change_mask": INHERITED_CHANGE_MASK_ABSENT,
            "derived_change_mask": DERIVED_CHANGE_MASK_ACTOR_ENTRIES,
            "derived_object_offset": DERIVED_CHANGE_MASK_OBJECT_OFFSET,
            "actor_type": REMOTE_PLAYER_ACTOR_TYPE,
            "actor_type_semantics": "cnetactor_the_remote_player_branch",
            "attr_ids": [
                ACTOR_ATTR_ID, AVATAR_ATTR_ID, MOVEMENT_ATTR_ID, NPC_ATTR_ID,
            ],
            "field_order_rule": "ascending_mask_bit_within_each_block",
            "basic_mask_probe": BASIC_MASK_PROBE,
            "basic_name_bit": BASIC_BIT_NAME,
            "actor_attr_mask_probe": ACTOR_ATTR_MASK_PROBE,
            "actor_attr_extra_group_value": ACTOR_ATTR_EXTRA_GROUP_VALUE,
            "movement_masks": list(MOVEMENT_MASKS_PINNED),
            "death_timer_bit_forbidden": BASIC_BIT_DEATH_TIMER_FORBIDDEN,
            "avatar_attr_policy": (
                "opaque_replay_of_the_selected_characters_avatar_wire_"
                "rebound_to_probe_b_and_always_the_last_attr_of_its_entry"
            ),
            "chain": {
                "inbound_handler": 0x5E4060,
                "actor_reconcile": 0x446F30,
                "identity_lookup": 0x446170,
                "spawn_when_unknown": 0x446990,
                "update_when_known_vtable_slot": 0x20,
                "bind_thunk_actor_attr_gates": "cnetactor",
                "bind_thunk_npc_attr_gates": "cnetnpc_so_frame_5_must_drop",
                "bind_is_copy_to_not_masked_merge": True,
                "movement_merge_is_against_the_previous_frame_only": True,
            },
        },
        "probe": {
            "source": "port_royal_unambiguous_placements_frozen_v141",
            "selection_rule": (
                "nearest_placement_to_the_frozen_v135_player_spawn"
            ),
            "anchor_placement_index": REMOTE_PLAYER_ANCHOR_PLACEMENT_INDEX,
            "anchor_template_id": REMOTE_PLAYER_ANCHOR_TEMPLATE_ID,
            "anchor_npc_identity": REMOTE_PLAYER_ANCHOR_NPC_IDENTITY,
            "anchor_visual_preset": REMOTE_PLAYER_ANCHOR_VISUAL_PRESET,
            "anchor_source_name": REMOTE_PLAYER_ANCHOR_SOURCE_NAME,
            "identities": {
                "A": PROBE_IDENTITY_A,
                "B": PROBE_IDENTITY_B,
                "C": PROBE_IDENTITY_C,
            },
            "names": {
                "A": PROBE_NAME_A,
                "B": PROBE_NAME_B,
                "C": PROBE_NAME_C,
            },
            "identity_band_is_a_design_choice_with_no_proven_meaning": True,
            "x_offsets": {
                "B": PROBE_B_X_OFFSET,
                "C": PROBE_C_X_OFFSET,
                "move": MOVE_X_OFFSET,
            },
            "move_heading_radians": MOVE_HEADING,
            "hp_alive": REMOTE_PLAYER_HP_ALIVE,
            "hp_max": REMOTE_PLAYER_HP_MAX,
            "hp_floor": REMOTE_PLAYER_HP_MIN,
            "scene_id": SCENE_ID,
            "scene_sequence": SCENE_SEQUENCE,
            "per_step": {
                label: dict(REMOTE_PLAYER_PINS[label])
                for label in profile.step_order
            },
            "baseline_crosscheck": (
                "the_actor_attr_basic_prefix_reproduces_legacy_make_npc_attr_"
                "byte_for_byte"
            ),
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": list(REMOTE_PLAYER_CAPABILITIES),
        "nonclaims": list(REMOTE_PLAYER_NONCLAIMS),
    }


def load_remote_player_hypothesis_scenario(
    path: str | Path,
) -> RemotePlayerHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid remote player hypothesis scenario") from exc
    if type(data) is not dict or not _exact_equal(data, _expected_scenario()):
        raise ValueError(
            "remote player hypothesis scenario exceeds the exact allowlist"
        )
    return require_remote_player_hypothesis_scenario(_PROFILE)
