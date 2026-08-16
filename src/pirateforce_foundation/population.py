"""Typed, frozen-proven scene-actor membership transitions.

This module reproduces only the authoritative V91/V94 NPC-style collection
shape.  It does not classify an entry as a monster or remote player, invent a
placement, or install a runtime policy.  Callers must opt in explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any


PORT_ROYAL_SOURCE_COUNT = 115
PORT_ROYAL_SOURCE_SHA256 = (
    "22D7430E5954196E007D56CF1116BA1635BFFBB9AADA4501D2166E3772659618"
)
AUTHORITATIVE_COUNT = 20
REFRESH_DISTANCE = 1000.0
NPC_STYLE_ACTOR_TYPE = 4
NPC_ATTR_ID = 0x0AD5
MOVEMENT_ATTR_ID = 0x2067
RUNTIME_PROTOCOL_RES_ID = 0x6E9D
SCENE_ID = 1
SCENE_SEQUENCE = 0
FULL_MOVEMENT_MASK = 0xFF
_FLOAT32_MAX = 3.4028234663852886e38
_HEADINGS = (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)


@dataclass(frozen=True)
class SceneActorPlacement:
    placement_index: int
    template_id: int
    x: float
    y: float
    z: float
    visual_preset: str
    source_name: str

    @property
    def actor_identity(self) -> int:
        return 0x2000 + self.placement_index + 1


@dataclass(frozen=True)
class SceneActorMembershipTransition:
    previous_indices: tuple[int, ...]
    current_indices: tuple[int, ...]
    retained_indices: tuple[int, ...]
    entrant_indices: tuple[int, ...]
    omitted_indices: tuple[int, ...]
    current_actor_identities: tuple[int, ...]
    retained_actor_identities: tuple[int, ...]
    entrant_actor_identities: tuple[int, ...]
    omitted_actor_identities: tuple[int, ...]
    pc: bytes
    frame: bytes


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer in [{minimum},{maximum}]")
    return value


def _require_float32(value: Any, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be a finite float32 value")
    result = float(value)
    if not math.isfinite(result) or abs(result) > _FLOAT32_MAX:
        raise ValueError(f"{label} must be a finite float32 value")
    return result


def _source_digest(rows: Any) -> str:
    try:
        encoded = json.dumps(
            rows, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid frozen placement source") from exc
    return hashlib.sha256(encoded).hexdigest().upper()


def load_port_royal_placements(legacy: Any) -> tuple[SceneActorPlacement, ...]:
    """Validate and type the exact immutable V141 placement source."""
    required = {
        "NPC_ATTR": NPC_ATTR_ID,
        "MOVEMENT_ATTR": MOVEMENT_ATTR_ID,
        "GSCN_RUNTIME_PROTOCOL_RES": RUNTIME_PROTOCOL_RES_ID,
        "V94_LOCAL_LIMIT": AUTHORITATIVE_COUNT,
        "V94_REFRESH_DISTANCE": REFRESH_DISTANCE,
    }
    for name, expected in required.items():
        if getattr(legacy, name, None) != expected:
            raise ValueError(f"frozen population constant drift: {name}")
    for name in (
        "make_npc_attr", "make_remote_movement_attr",
        "make_remote_actor_entry", "make_runtime_remote_actors",
    ):
        if not callable(getattr(legacy, name, None)):
            raise ValueError(f"missing frozen population serializer: {name}")

    rows = getattr(legacy, "PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS", None)
    if type(rows) is not list or len(rows) != PORT_ROYAL_SOURCE_COUNT:
        raise ValueError("frozen placement source count drift")
    if _source_digest(rows) != PORT_ROYAL_SOURCE_SHA256:
        raise ValueError("frozen placement source hash drift")

    placements: list[SceneActorPlacement] = []
    seen: set[int] = set()
    for ordinal, row in enumerate(rows):
        if type(row) is not tuple or len(row) != 7:
            raise ValueError(f"placement row {ordinal} has wrong shape")
        placement_index = _require_int(row[0], "placement index", 0, 0xDFFE)
        template_id = _require_int(row[1], "template id", 0, 0xFFFF)
        if placement_index in seen:
            raise ValueError("duplicate placement index")
        seen.add(placement_index)
        x = _require_float32(row[2], "placement x")
        y = _require_float32(row[3], "placement y")
        z = _require_float32(row[4], "placement z")
        visual_preset, source_name = row[5], row[6]
        if type(visual_preset) is not str or not visual_preset:
            raise ValueError("placement visual preset must be non-empty text")
        if type(source_name) is not str:
            raise ValueError("placement source name must be text")
        placements.append(SceneActorPlacement(
            placement_index, template_id, x, y, z,
            visual_preset, source_name,
        ))
    return tuple(placements)


def _validate_previous(
    previous_indices: Any,
    known_indices: set[int],
) -> tuple[int, ...]:
    if type(previous_indices) is not tuple:
        raise ValueError("previous indices must be an exact tuple")
    if len(previous_indices) != AUTHORITATIVE_COUNT:
        raise ValueError("previous authoritative membership must contain 20 indices")
    checked = tuple(
        _require_int(value, "previous placement index", 0, 0xDFFE)
        for value in previous_indices
    )
    if len(set(checked)) != len(checked):
        raise ValueError("previous membership contains a duplicate index")
    if not set(checked) <= known_indices:
        raise ValueError("previous membership contains an unknown index")
    return checked


def _validate_player_xyz(player_xyz: Any) -> tuple[float, float, float]:
    if type(player_xyz) is not tuple or len(player_xyz) != 3:
        raise ValueError("player XYZ must be an exact three-value tuple")
    return tuple(
        _require_float32(value, f"player {axis}")
        for axis, value in zip("xyz", player_xyz)
    )  # type: ignore[return-value]


def build_port_royal_membership_transition(
    legacy: Any,
    previous_indices: tuple[int, ...],
    player_xyz: tuple[float, float, float],
) -> SceneActorMembershipTransition:
    """Build one exact authoritative generation without installing it.

    Current members are ordered by squared distance and placement index, exactly
    as frozen V94.  Retained entries carry NPCAttr only; entrants additionally
    carry the exact full-mask MovementAttr.  Previous members outside the new
    generation are represented only by their omission.
    """
    placements = load_port_royal_placements(legacy)
    by_index = {placement.placement_index: placement for placement in placements}
    previous = _validate_previous(previous_indices, set(by_index))
    x, y, z = _validate_player_xyz(player_xyz)

    candidates = []
    for placement in placements:
        distance2 = (
            (placement.x - x) ** 2
            + (placement.y - y) ** 2
            + (placement.z - z) ** 2
        )
        if not math.isfinite(distance2):
            raise ValueError("placement distance is non-finite")
        candidates.append((distance2, placement.placement_index, placement))
    candidates.sort(key=lambda item: (item[0], item[1]))
    current = tuple(item[2] for item in candidates[:AUTHORITATIVE_COUNT])
    if len(current) != AUTHORITATIVE_COUNT:
        raise ValueError("insufficient exact placements for authoritative membership")

    previous_set = set(previous)
    current_indices = tuple(item.placement_index for item in current)
    current_set = set(current_indices)
    retained_indices = tuple(index for index in current_indices if index in previous_set)
    entrant_indices = tuple(index for index in current_indices if index not in previous_set)
    omitted_indices = tuple(index for index in previous if index not in current_set)

    entries = []
    for placement in current:
        actor_identity = placement.actor_identity
        npc_attr = legacy.make_npc_attr(
            placement.template_id, actor_identity,
            SCENE_ID, SCENE_SEQUENCE, placement.visual_preset,
        )
        attrs = [(NPC_ATTR_ID, npc_attr)]
        if placement.placement_index in entrant_indices:
            attrs.append((
                MOVEMENT_ATTR_ID,
                legacy.make_remote_movement_attr(
                    actor_identity,
                    placement.x, placement.y, placement.z,
                    _HEADINGS[placement.placement_index & 3],
                    mask=FULL_MOVEMENT_MASK,
                ),
            ))
        entries.append(legacy.make_remote_actor_entry(
            NPC_STYLE_ACTOR_TYPE, actor_identity, attrs,
        ))
    pc, frame = legacy.make_runtime_remote_actors(entries)

    identity = lambda index: by_index[index].actor_identity
    return SceneActorMembershipTransition(
        previous,
        current_indices,
        retained_indices,
        entrant_indices,
        omitted_indices,
        tuple(identity(index) for index in current_indices),
        tuple(identity(index) for index in retained_indices),
        tuple(identity(index) for index in entrant_indices),
        tuple(identity(index) for index in omitted_indices),
        pc,
        frame,
    )
