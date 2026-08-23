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
  (one near the spawn point, one far, so "does not draw" can be told apart
  from "draws off-screen"), the element keys 1 and 2, the payload dword
  2600001 (a loot-roller-style ITEM_MISC id; NOTHING proves +0x14 is an
  item id at all), and the element mask 0x12 = 0x10|0x02 (position + the
  one dword the GT-045 ticket names).  The original server is gone and
  unrecoverable; none of this claims to reproduce it.
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
The default (non-scenario) boot places the local player's StartGameRes
MovementAttr at V135 = (-9239.95703125, -2830.045166015625,
223.29209899902344) (current/pf_login_game_server_v141.py, V135_PLAYER_*).
NEAR = V135 + 30 on X only; FAR = V135 + 800 on X only.  +X is the
direction of placement P0 / the 'Navy Transfer' NPC, ground an attended
tester has actually walked.  Y and Z are the player's own, so the points
sit on the same ground plane the player stands on.  The world unit is not
convertible to any real-world measure from anything we hold.

FAIL-CLOSED, AND NEVER SILENTLY
-------------------------------
The scenario file is a PERMISSION TOKEN, never a source of values: the
frame the dispatcher emits is composed from this module's own frozen
profile, and the composer re-asserts the exact pc/frame length and sha256
against the pins below on every call.  An unreadable, drifted or lookalike
file refuses by raising with a named reason.

NONCLAIMS
---------
* Bit 0x08 = "ground loot" is UNPROVEN.  The list is only proven to carry
  non-actor records with a world position; it could be markers, waypoints,
  FX anchors or anything else.  A negative attended result (wire proven,
  nothing drawn at either coordinate) permanently retires this candidate
  and is a complete answer, not a failure.
* The payload dword is NOT claimed to be an item template id, and no
  committed artifact maps "Red leaves Hammer" (the one observed drop) to
  any numeric id.
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

# V135 default-boot player placement, restated from the frozen module's
# V135_PLAYER_* constants and re-asserted against them at compose time.
_V135_X = -9239.95703125
_V135_Y = -2830.045166015625
_V135_Z = 223.29209899902344


@dataclass(frozen=True)
class GroundLootElement:
    """One 0x5F85B0 list element this lane is allowed to emit."""

    element_key: int      # +0x10, always on the wire (tag 0x14 u32)
    payload_dword: int    # +0x14, mask bit 0x02 (tag 0x14 u32)
    x: float              # +0x1C, mask bit 0x10 (tag 0x2A f32)
    y: float              # +0x20
    z: float              # +0x24


@dataclass(frozen=True)
class GroundLootScenario:
    scenario_id: str
    hypothesis_id: str
    elements: Tuple[GroundLootElement, ...]


_NEAR = GroundLootElement(
    element_key=1,
    payload_dword=2600001,
    x=_V135_X + 30.0,
    y=_V135_Y,
    z=_V135_Z,
)
_FAR = GroundLootElement(
    element_key=2,
    payload_dword=2600001,
    x=_V135_X + 800.0,
    y=_V135_Y,
    z=_V135_Z,
)

_BIT08_RENDER = GroundLootScenario(
    "ground_loot_hypothesis_bit08_render",
    GROUND_LOOT_HYPOTHESIS_ID,
    (_NEAR, _FAR),
)

# Exact pc/frame pins for the two frames this lane may emit -- one per
# element, count=1 each (the V43-proven-safe single-record shape).
# Computed from the composer below over the frozen profile; the composer
# re-asserts them on every call so silent drift cannot reach a socket.
GROUND_LOOT_PC_SIZE = 44
GROUND_LOOT_FRAME_SIZE = 54
GROUND_LOOT_NEAR_PC_SHA256 = (
    "A3570BC9185BEF70ABB3810448F6E3F605437B2F1BFAB1DF474882AD3661EA03"
)
GROUND_LOOT_NEAR_FRAME_SHA256 = (
    "A9D4F13409DF636C40FEA7FE7DEA38DD542D09E140BB073FBDD367B5758A5AE0"
)
GROUND_LOOT_FAR_PC_SHA256 = (
    "4B14A026763F53FFD65210C2F2BCC0122B096A6877455C84DAAED71366F07F3A"
)
GROUND_LOOT_FAR_FRAME_SHA256 = (
    "B13942BBCC933B4E135BCD40FE0C3D39B4EF053C31892F1F8EC929F702223989"
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
            "position": {"x": _NEAR.x, "y": _NEAR.y, "z": _NEAR.z},
            "coordinate_provenance": (
                "v135_default_boot_placement_plus_30x_same_y_same_z"
            ),
        },
        {
            "element_key": _FAR.element_key,
            "payload_dword": _FAR.payload_dword,
            "position": {"x": _FAR.x, "y": _FAR.y, "z": _FAR.z},
            "coordinate_provenance": (
                "v135_default_boot_placement_plus_800x_same_y_same_z"
            ),
        },
    ],
    "frame_pins": {
        "pc_size_each": GROUND_LOOT_PC_SIZE,
        "frame_size_each": GROUND_LOOT_FRAME_SIZE,
        "near_pc_sha256": GROUND_LOOT_NEAR_PC_SHA256,
        "near_frame_sha256": GROUND_LOOT_NEAR_FRAME_SHA256,
        "far_pc_sha256": GROUND_LOOT_FAR_PC_SHA256,
        "far_frame_sha256": GROUND_LOOT_FAR_FRAME_SHA256,
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


def _element_wire(legacy, element: GroundLootElement) -> bytes:
    """One 0x5F85B0 element, mask 0x12, in the re-derived field order."""
    return (
        legacy.u32tag(0x14, element.element_key)          # +0x10 key
        + legacy.u8tag(0x0B, GROUND_LOOT_ELEMENT_MASK)    # +0x28 dirty mask
        + legacy.u32tag(0x14, element.payload_dword)      # +0x14 (bit 0x02)
        + legacy.f32tag(element.x)                        # +0x1C (bit 0x10)
        + legacy.f32tag(element.y)                        # +0x20
        + legacy.f32tag(element.z)                        # +0x24
    )


def make_ground_loot_frames(legacy, scenario) -> Tuple[Tuple[bytes, bytes], ...]:
    """Compose the two allowlisted bit-0x08 frames, pinned byte-for-byte.

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
    if (
        legacy.V135_PLAYER_X != _V135_X
        or legacy.V135_PLAYER_Y != _V135_Y
        or legacy.V135_PLAYER_Z != _V135_Z
    ):
        # The coordinates are meaningful only relative to where the default
        # boot actually puts the player.  If the frozen placement ever moves,
        # this lane's geometry claim is stale and must not reach a socket.
        raise RuntimeError(
            "ground_loot_placement_drift: HYP-PF-032 refuses to compose -- "
            "V135_PLAYER_* moved away from the profile's baseline"
        )
    pins = (
        (GROUND_LOOT_NEAR_PC_SHA256, GROUND_LOOT_NEAR_FRAME_SHA256),
        (GROUND_LOOT_FAR_PC_SHA256, GROUND_LOOT_FAR_FRAME_SHA256),
    )
    out = []
    for element, (pc_sha, frame_sha) in zip(scenario.elements, pins):
        pc = bytearray()
        pc += legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_RES)
        pc += legacy.u32tag(0x14, 0)
        pc += legacy.u8tag(0x08, 4)
        pc += legacy.u8tag(0x0B, 0)                        # inherited: none
        pc += legacy.u8tag(0x0B, GROUND_LOOT_DERIVED_BIT)  # derived bit 0x08
        pc += legacy.u16tag(0x12, 1)                       # ONE element
        pc += _element_wire(legacy, element)
        pc = bytes(pc)
        frame = legacy.frame_pc(pc)
        if (
            len(pc) != GROUND_LOOT_PC_SIZE
            or hashlib.sha256(pc).hexdigest().upper() != pc_sha
            or len(frame) != GROUND_LOOT_FRAME_SIZE
            or hashlib.sha256(frame).hexdigest().upper() != frame_sha
        ):
            raise RuntimeError(
                "ground_loot_frame_drift: HYP-PF-032 refuses to emit bytes "
                "that do not match the pinned composition"
            )
        out.append((pc, frame))
    return tuple(out)
