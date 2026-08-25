"""GROUND-LOOT-001: one opt-in frame asking whether derived bit 0x08 draws.

WHY THIS MODULE EXISTS -- and what it deliberately does NOT do
--------------------------------------------------------------
The attended ground-drop evidence (frame measurement, 2026-08-23: a loot
object stood on the ground for 0.633 s as a 3D piece with a floating white
name label, then vanished in the SAME frame as the green "received item"
chat line) proves the real client CAN draw a loot object on the ground.
Nothing we hold proves which transport puts it there.  Static work GT-040/
GT-042 found exactly one shipped pipe for non-actor records that carry a
world position: GSCN_RunTimeProtocolRes (0x6E9D) derived change-mask bit
0x08 -> object +0x20 -> the list parsed at client VA 0x5F85B0.  Whether the
client RENDERS anything for that list is unknown and is precisely the
attended question GT-045 asks.

This module composes ONE such frame, behind an opt-in scenario flag, so an
attended tester can watch the screen while the wire layer is provable from
the server log.  It does nothing else: no database write, no persistence,
no reaction to any later frame, no claim about what the bytes mean to the
client.

PROVENANCE OF EVERY BYTE (layer-tagged; see docs/HYPOTHESIS_LEDGER.json)
------------------------------------------------------------------------
* [STATIC, survived adversarial re-derive in GT-042] The 0x5F85B0 wire
  shape, read from both the write path 0x89A600 and the read path 0x89A640
  of the client image span [0x005F85B0,0x005F8869) sha256 ce0a58f7..:
    list  = tag12 u16 count, then count elements
    element = tag14 u32 key(+0x10)            -- always present
              tag0B u8  dirty mask(+0x28)     -- always present
              then per mask bit, in this order:
              0x02 -> tag14 u32 (+0x14)
              0x04 -> tag0F u16 (+0x18)
              0x08 -> tag05 u8  (+0x1B)
              0x10 -> tag2A f32 x3 (+0x1C/+0x20/+0x24, world position)
              0x20 -> tag08 u8  (+0x1A)
* [STATIC, same grade] The parent frame shape is the proven RuntimeRes v4
  envelope already used byte-exact by make_runtime_remote_actors() for the
  sibling bit 0x02: msg id 0x6E9D, version 4, inherited VitalData mask 0,
  then the derived mask byte selecting the sub-object.  This module only
  changes that derived mask byte to 0x08 and substitutes the 0x5F85B0 list
  body.  No client has ever been shown a bit-0x08 frame by us or by anyone
  we can observe.
* [OUR DESIGN] Everything else: firing at the first TargetPos after the
  runtime ack (the house scene-load moment), sending exactly TWO elements
  (one near the triggering position, one far, so "does not draw" can be
  told apart from "draws off-screen"), the element keys 1 and 2, the payload
  dwords 2200423 and 2200003, and the element mask 0x12 = 0x10|0x02
  (position + the one dword the GT-045 ticket names).  NOTHING proves +0x14
  is an item id at all -- that nonclaim is unchanged.
* [MEASURED, attended GT-045 round 1104, 2026-08-24] With 2600001 on both
  elements, an attended observer watched the client play a brown
  ground-drop dust effect on the ground at the position this lane sent,
  for about 0.45 s, and then nothing: no item model, no floating name, and
  nothing left standing when she walked onto both coordinates afterwards.
  That is the whole of what was seen.  The wire half measured byte-exact
  in the same round (near = trigger+30.000, far = trigger+800.000, Y and Z
  the trigger's own to the bit).
* [MEASURED, committed tables] CONSTDATA_TH__ITEM_MISC n_ID=1 (the id that
  round carried) has n_DROPMODEL_TYPE=0, and only 7 of that table's 1646
  rows carry a drop model at all.  CONSTDATA_TH__EQUIPMENT_BASE carries one
  on 925 of its 974 rows.  n_ID=423 there is the item the owner's reference
  clip drops, and n_ID=3 is a starter weapon; both carry
  n_DROPMODEL_TYPE=1.
* [PROPOSED -- this is a hypothesis, not a finding] That the missing model
  is explained by the id, i.e. that the client looks the payload dword up
  in an item table and had no drop model to draw.  This lane now sends
  2200423 on element 1 and 2200003 on element 2 to ask that question at a
  screen.  What the change may NOT be read as:
    - It is NOT a field experiment.  n_ID_MODEL=0 is a VALID model index,
      not "absent": s_ID_ICON == ICON_<PARTS>_<n_ID_MODEL:03d>_<n_ID_MAP:03d>
      holds on 376 of 376 parts-bearing EQUIPMENT_BASE rows, 18 rows across
      6 model families carry a _000_ member, and every one of the 1646
      ITEM_MISC rows has n_ID_MODEL=0 including the 7 that DO carry a drop
      model.  So a model at element 1 says NOTHING about which of
      n_ID_MODEL or n_DROPMODEL_TYPE the client reads.
    - The two ids do NOT differ in one field.  They differ in 10 of 39
      columns, four of them visual (s_ID_ICON, n_ID_MODEL, n_ID_MAP,
      n_QUALITY).
    - Moving 2600001 -> 2200423 also moves the TABLE CODE, 26 -> 22, and
      RE-060 pinned that the client decodes full_id/100000 into a runtime
      table-object lookup.  A positive therefore cannot separate "this item
      has a drop model" from "code 22 resolves and code 26 does not".  The
      same-table control that would separate them is 2600022 (ITEM_MISC,
      n_DROPMODEL_TYPE=12); it is named in the GT-045 ticket as the next
      experiment, deliberately NOT bundled into this one-shot round.
    - Element 2 sits 800 units out, where a negative is equally explained
      by distance.  It stays the off-screen control it always was.  Only
      element 1 is readable, and it is readable only as "did anything get
      drawn", never as a field verdict.
  The original server is gone and unrecoverable; none of this claims to
  reproduce it.
* [PROVEN, and it reshaped this lane before it ever shipped] The two
  elements travel as TWO single-element frames, count=1 each, NOT as one
  count=2 collection.  V43 measured a real client raising ErrorData=28317
  on a combined multi-record derived-mask RuntimeRes collection, and the
  fix this project still ships is one record per frame
  (make_port_royal_npc_single_packets).  Whether the 0x5F85B0 list parser
  shares that fragility is unknown -- and that is exactly why the lane
  must not bet the one attended run on it: a count=2 frame that errors
  would measure the count, not the rendering.  Round-124's adversarial
  review raised this; the single-record shape is the answer.

COORDINATES [OUR DESIGN, derived from committed constants]
----------------------------------------------------------
NEAR = trigger + 30 on X only; FAR = trigger + 800 on X only, where the
trigger is the exact first TargetPos frame after the runtime ack -- the
same frame that fires the emission.  Y and Z are the trigger's own, so the
points sit on the ground plane the player actually stands on.  +X is the
direction of placement P0 / the 'Navy Transfer' NPC, ground an attended
tester has actually walked.  The world unit is not convertible to any
real-world measure from anything we hold.

The first shipped version pinned ABSOLUTE coordinates derived from the
V135 default-boot placement.  The attended GT-045 run (2026-08-23)
measured the real spawn at (-8553.947265625, -2579.68896484375, 186.0):
the character's persisted DB position had long since drifted away from
V135, so the pinned points stood ~700 and ~1500 world units from the
player and the near/far geometry the ticket needed was silently gone.
The V135 guard below guarded the frozen module's constants -- the wrong
thing; the player's position lives in the DB.  Trigger-relative offsets
remove that failure mode: the geometry claim now travels with the frame
that proves where the player is.

FAIL-CLOSED, AND NEVER SILENTLY
-------------------------------
The scenario file is a PERMISSION TOKEN, never a source of values: the
frame the dispatcher emits is composed from this module's own frozen
profile, and the composer re-asserts, on every call, the exact pc/frame
lengths and a sha256 over the composed pc with its twelve coordinate
payload bytes zeroed (the coordinates are the one input that is
legitimately per-run; every other byte is pinned).  The coordinate bytes
themselves are re-asserted against an f32 round-trip of trigger+offset.
An unreadable, drifted or lookalike file refuses by raising with a named
reason.

NONCLAIMS
---------
* Bit 0x08 = "ground loot" is UNPROVEN.  The list is only proven to carry
  non-actor records with a world position; it could be markers, waypoints,
  FX anchors or anything else.  A negative attended result (wire proven,
  nothing drawn at either coordinate) permanently retires this candidate
  and is a complete answer, not a failure.
* The payload dword is NOT claimed to be an item template id, and NOTHING
  at any layer shows the client ever READS +0x14.  Round 1104 sent an id
  with no drop model and still got the dust, so "the handler plays a
  positional effect on record arrival and never touches the dword" fits
  the evidence exactly as well as "the client looked the row up".  If that
  is the true shape, both new ids produce dust, and a negative round would
  retire the right explanation for the wrong reason.  The static question
  that would settle it -- does the 0x5F85B0 read path at 0x89A640 ever
  reach the item decoder RE-060 pinned -- is queued on the bridge, not
  assumed here.
* The observed drop DOES have an exact name match in the committed tables:
  TEXTDATA_TH__EQUIPMENT_BASE_TIP n_ID=423 s_NAME is literally "Red leaves
  Hammer".  RE-060 pinned that the client resolves display names from the
  linked TEXTDATA TIP table, not from the CONSTDATA CJK s_NAME, so that is
  the correct table to cite -- but a name match in a client table is still
  not proof that +0x14 is the field the client looks that row up by.
* Drawing is not pickup.  Pickup direction is a separate static question
  (GT-046, PickupTerrainThing) and this module does not touch it.
* No aging/removal mechanism for the bit-0x08 list is known; whether the
  client keeps, culls or expires an entry is part of the attended question.
* production_baseline_behavior is untouched: with the scenario absent this
  module is never imported by the dispatch path and no branch consults it.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Tuple


# PF-HYPOTHESIS-LEDGER: HYP-PF-032 active
GROUND_LOOT_CHECKPOINT = "GROUND-LOOT-001"
GROUND_LOOT_HYPOTHESIS_ID = "HYP-PF-032"
production_allowed = False

# The RuntimeRes derived change-mask bit this lane exists to exercise, and
# the per-element dirty mask the GT-045 ticket names: position + dword.
GROUND_LOOT_DERIVED_BIT = 0x08
GROUND_LOOT_ELEMENT_MASK = 0x12  # 0x10 position | 0x02 dword at +0x14

@dataclass(frozen=True)
class GroundLootElement:
    """One 0x5F85B0 list element this lane is allowed to emit.

    Coordinates are TRIGGER-RELATIVE: x = trigger.x + x_offset, y and z are
    the trigger's own.  The attended GT-045 run proved absolute pins die
    the moment the character's persisted DB position drifts (and it had).
    """

    element_key: int      # +0x10, always on the wire (tag 0x14 u32)
    payload_dword: int    # +0x14, mask bit 0x02 (tag 0x14 u32)
    x_offset: float       # added to the triggering TargetPos x (+0x1C f32)


@dataclass(frozen=True)
class GroundLootScenario:
    scenario_id: str
    hypothesis_id: str
    elements: Tuple[GroundLootElement, ...]


_NEAR = GroundLootElement(
    element_key=1,
    payload_dword=2200423,
    x_offset=30.0,
)
_FAR = GroundLootElement(
    element_key=2,
    payload_dword=2200003,
    x_offset=800.0,
)

_BIT08_RENDER = GroundLootScenario(
    "ground_loot_hypothesis_bit08_render",
    GROUND_LOOT_HYPOTHESIS_ID,
    (_NEAR, _FAR),
)

# Masked-template pins for the two frames this lane may emit -- one per
# element, count=1 each (the V43-proven-safe single-record shape).  The
# template sha256 is taken over the composed 44-byte pc with its twelve
# coordinate payload bytes (offsets [30:34]/[35:39]/[40:44], the three
# tag-0x2A f32 payloads) zeroed: coordinates are the one legitimately
# per-run input, every other byte is pinned.  The coordinate bytes are
# separately re-asserted against struct.pack of trigger+offset on every
# call, so silent drift cannot reach a socket through either half.
GROUND_LOOT_PC_SIZE = 44
GROUND_LOOT_FRAME_SIZE = 54
GROUND_LOOT_COORD_SPANS = ((30, 34), (35, 39), (40, 44))
# The frame is the 10-byte snappy-literal header (content-independent for a
# fixed 44-byte pc) followed by the pc, so the frame's coordinate bytes sit
# at the same spans shifted by +10.  Both layers are template-pinned so the
# framing header stays as covered as it was under the v1 whole-frame pins.
GROUND_LOOT_FRAME_COORD_SHIFT = 10
GROUND_LOOT_NEAR_PC_TEMPLATE_SHA256 = (
    "F9875639513F38E0D2603A53137D205AF47246447102B431665B27AE23BD4576"
)
GROUND_LOOT_FAR_PC_TEMPLATE_SHA256 = (
    "159DD1AB3074519EF95821DE6953697A03C035F35804024F8CD27FFFD22E39D7"
)
GROUND_LOOT_NEAR_FRAME_TEMPLATE_SHA256 = (
    "A67230FCC80A619F0ADBD35F99332DC3597768A28C603368D41D8DD0192E7902"
)
GROUND_LOOT_FAR_FRAME_TEMPLATE_SHA256 = (
    "6B0F7FA8B3685914B68503891A5E4CCCD988278B93F8BF72E3C2FB772EE33B1B"
)

_EXPECTED = {
    "schema": 1,
    "id": _BIT08_RENDER.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _BIT08_RENDER.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_only",
        "trigger": "first_target_pos_after_runtime_ack",
        "emission": (
            "two_single_element_runtimeres_derived_bit08_frames_v43_shape"
        ),
    },
    "elements": [
        {
            "element_key": _NEAR.element_key,
            "payload_dword": _NEAR.payload_dword,
            "x_offset": _NEAR.x_offset,
            "coordinate_provenance": (
                "triggering_target_pos_plus_30x_same_y_same_z"
            ),
        },
        {
            "element_key": _FAR.element_key,
            "payload_dword": _FAR.payload_dword,
            "x_offset": _FAR.x_offset,
            "coordinate_provenance": (
                "triggering_target_pos_plus_800x_same_y_same_z"
            ),
        },
    ],
    "frame_pins": {
        "pc_size_each": GROUND_LOOT_PC_SIZE,
        "frame_size_each": GROUND_LOOT_FRAME_SIZE,
        "coordinate_bytes_masked": "pc[30:34]+pc[35:39]+pc[40:44]",
        "near_pc_template_sha256": GROUND_LOOT_NEAR_PC_TEMPLATE_SHA256,
        "far_pc_template_sha256": GROUND_LOOT_FAR_PC_TEMPLATE_SHA256,
        "near_frame_template_sha256": (
            GROUND_LOOT_NEAR_FRAME_TEMPLATE_SHA256
        ),
        "far_frame_template_sha256": GROUND_LOOT_FAR_FRAME_TEMPLATE_SHA256,
    },
    "capabilities": [
        "emit_two_single_element_runtimeres_derived_bit08_frames_at_scene_load",
    ],
    "nonclaims": [
        "bit08_list_is_ground_loot",
        "payload_dword_is_an_item_template_id",
        "client_renders_anything_for_bit08",
        "drawing_implies_pickup",
        "bit08_entry_lifetime_or_removal",
        "original_server_ever_sent_bit08",
        "unit_of_measure_of_client_world_coordinates",
        "production_baseline_behavior",
    ],
}

_PROFILES = {_BIT08_RENDER.scenario_id: _BIT08_RENDER}


def _exact_equal(actual: Any, expected: Any) -> bool:
    """Type-strict recursive equality.

    Plain ``==`` would accept ``True`` where ``1`` is expected and ``2``
    where ``2.0`` is expected.  A permission token that accepts near misses
    is not a permission token, so every node is compared by type first.
    """
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        if set(actual) != set(expected):
            return False
        return all(_exact_equal(actual[key], expected[key]) for key in expected)
    if type(expected) is list:
        if len(actual) != len(expected):
            return False
        return all(
            _exact_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def require_ground_loot_hypothesis_scenario(value: Any) -> GroundLootScenario:
    """Refuse anything that is not the module's own frozen profile.

    Compared by identity, so a value-equal lookalike dataclass built outside
    this module opens nothing.
    """
    if not any(value is profile for profile in _PROFILES.values()):
        raise ValueError(
            "ground_loot_scenario_not_allowlisted: HYP-PF-032 refuses to "
            "emit a bit-0x08 frame for a profile this module did not issue"
        )
    return value


def load_ground_loot_hypothesis_scenario(path) -> GroundLootScenario:
    """Load the one allowlisted opt-in scenario file, or refuse by name.

    The file is a PERMISSION TOKEN, never a source of values: the frame the
    dispatcher emits comes from the module's own frozen profile.  A file
    that differs from the allowlisted body anywhere -- one extra key, one
    missing key, one int where a float is expected -- is refused.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "ground_loot_scenario_unreadable: HYP-PF-032 refuses an "
            "unreadable or malformed opt-in file"
        ) from exc
    if type(data) is not dict or data.get("id") not in _PROFILES:
        raise ValueError(
            "ground_loot_scenario_unknown_id: HYP-PF-032 refuses a file "
            "that does not name the one allowlisted profile"
        )
    if not _exact_equal(data, _EXPECTED):
        raise ValueError(
            "ground_loot_scenario_exceeds_allowlist: HYP-PF-032 refuses a "
            "scenario body that drifted from the allowlisted one"
        )
    return require_ground_loot_hypothesis_scenario(_PROFILES[data["id"]])


def _f32(value: float) -> float:
    """Quantize to the exact f32 the wire will carry."""
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _element_wire(legacy, element: GroundLootElement,
                  x: float, y: float, z: float) -> bytes:
    """One 0x5F85B0 element, mask 0x12, in the re-derived field order."""
    return (
        legacy.u32tag(0x14, element.element_key)          # +0x10 key
        + legacy.u8tag(0x0B, GROUND_LOOT_ELEMENT_MASK)    # +0x28 dirty mask
        + legacy.u32tag(0x14, element.payload_dword)      # +0x14 (bit 0x02)
        + legacy.f32tag(x)                                # +0x1C (bit 0x10)
        + legacy.f32tag(y)                                # +0x20
        + legacy.f32tag(z)                                # +0x24
    )


def make_ground_loot_frames(
    legacy, scenario, trigger_xyz,
) -> Tuple[Tuple[bytes, bytes], ...]:
    """Compose the two allowlisted bit-0x08 frames from the trigger position.

    ``trigger_xyz`` is the (x, y, z) of the exact TargetPos frame that fires
    the emission -- already f32-exact because it was parsed from wire f32.
    NEAR/FAR are trigger + 30/800 on X only, same Y/Z, so the geometry claim
    holds wherever the character's persisted DB position actually is (the
    first shipped version pinned V135-derived absolutes and the attended run
    measured the real spawn ~700 units away -- see the module docstring).

    Envelope restated from the proven sibling make_runtime_remote_actors():
    only the derived mask byte differs (0x08 instead of 0x02) and the list
    body is the re-derived 0x5F85B0 shape instead of actor entries.  ONE
    element per frame, count=1, deliberately mirroring the V43 lesson
    (make_port_royal_npc_single_packets): a combined multi-record
    derived-mask collection is the one shape a real client has already
    rejected with ErrorData=28317, and this lane must not spend the
    attended run measuring the count instead of the rendering.
    """
    scenario = require_ground_loot_hypothesis_scenario(scenario)
    try:
        tx, ty, tz = (float(v) for v in trigger_xyz)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "ground_loot_trigger_malformed: HYP-PF-032 refuses to compose "
            "without the triggering TargetPos coordinates"
        ) from exc
    if not all(math.isfinite(v) for v in (tx, ty, tz)):
        raise RuntimeError(
            "ground_loot_trigger_not_finite: HYP-PF-032 refuses to place "
            "elements relative to a non-finite trigger position"
        )
    pins = (
        (GROUND_LOOT_NEAR_PC_TEMPLATE_SHA256,
         GROUND_LOOT_NEAR_FRAME_TEMPLATE_SHA256),
        (GROUND_LOOT_FAR_PC_TEMPLATE_SHA256,
         GROUND_LOOT_FAR_FRAME_TEMPLATE_SHA256),
    )
    out = []
    for element, (template_sha, frame_template_sha) in zip(
            scenario.elements, pins):
        try:
            x, y, z = _f32(tx + element.x_offset), _f32(ty), _f32(tz)
        except OverflowError:
            x = y = z = float("inf")
        if not all(math.isfinite(v) for v in (x, y, z)):
            # f32 overflow after the offset (struct raises OverflowError on
            # a too-large double): refuse rather than emit inf.
            raise RuntimeError(
                "ground_loot_offset_overflow: HYP-PF-032 refuses an offset "
                "position that does not survive the f32 round-trip"
            )
        pc = bytearray()
        pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
        pc += legacy.u32tag(0x14, 0)
        pc += legacy.u8tag(0x08, 4)
        pc += legacy.u8tag(0x0B, 0)                        # inherited: none
        pc += legacy.u8tag(0x0B, GROUND_LOOT_DERIVED_BIT)  # derived bit 0x08
        pc += legacy.u16tag(0x12, 1)                       # ONE element
        pc += _element_wire(legacy, element, x, y, z)
        pc = bytes(pc)
        masked = bytearray(pc)
        for start, end in GROUND_LOOT_COORD_SPANS:
            masked[start:end] = b"\x00" * (end - start)
        # NOTE: this coordinate-byte comparison shares its inputs with the
        # element wire above, so it only catches f32tag/encoding drift; the
        # trigger+offset DERIVATION is enforced by construction and by the
        # dispatch tests and the headless replay, not by this line.
        coord_bytes = struct.pack("<fff", x, y, z)
        actual_coords = b"".join(
            pc[start:end] for start, end in GROUND_LOOT_COORD_SPANS
        )
        frame = legacy.frame_pc(pc)
        masked_frame = bytearray(frame)
        for start, end in GROUND_LOOT_COORD_SPANS:
            shift = GROUND_LOOT_FRAME_COORD_SHIFT
            masked_frame[start + shift:end + shift] = (
                b"\x00" * (end - start)
            )
        if (
            len(pc) != GROUND_LOOT_PC_SIZE
            or hashlib.sha256(bytes(masked)).hexdigest().upper()
            != template_sha
            or actual_coords != coord_bytes
            or len(frame) != GROUND_LOOT_FRAME_SIZE
            or hashlib.sha256(bytes(masked_frame)).hexdigest().upper()
            != frame_template_sha
        ):
            raise RuntimeError(
                "ground_loot_frame_drift: HYP-PF-032 refuses to emit bytes "
                "that do not match the pinned composition"
            )
        out.append((pc, frame))
    return tuple(out)
