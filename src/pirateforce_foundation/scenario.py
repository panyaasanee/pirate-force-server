"""Strict, test-only scenario configuration and projection for Test Arena."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct

from .npc_wire import make_npc_attr_with_basic_faction


@dataclass(frozen=True)
class ArenaScenario:
    scenario_id: str
    scene_id: int
    trigger: str
    reapply_ms: int
    placement_index: int
    profile: str
    dx: float
    dy: float
    dz: float
    capabilities: tuple[str, ...]
    nonclaims: tuple[str, ...]
    basic_faction: int | None


_TOP = {"schema", "id", "test_only", "entry", "spawn", "target", "capabilities", "nonclaims"}
_CAPABILITIES = {"spawn", "target"}
_NONCLAIMS = {"authentic_position", "tab", "combat", "ai", "damage", "loot"}
_PROFILES = {
    "arena_v1_player_p30_target": ("v119_p30", None),
    # PF-HYPOTHESIS-LEDGER: RET-PF-001 retired
    "arena_v2_p30_basic_faction6_diagnostic": ("p30_basic_faction6_diagnostic", 6),
}


def load_scenario(path: str | Path) -> ArenaScenario:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if type(data) is not dict:
        raise ValueError("scenario root must be an object")
    if (
        set(data) != _TOP
        or type(data["schema"]) is not int
        or data["schema"] != 1
        or data["id"] not in _PROFILES
        or data["test_only"] is not True
    ):
        raise ValueError("unsupported or incomplete test scenario")
    expected_profile, basic_faction = _PROFILES[data["id"]]
    if type(data["entry"]) is not dict or (
        set(data["entry"]) != {"flow", "scene_id"}
        or data["entry"]["flow"] != "full"
        or type(data["entry"]["scene_id"]) is not int
    ):
        raise ValueError("Test Arena V1 requires the proven Full Flow entry")
    if type(data["spawn"]) is not dict or set(data["spawn"]) != {"trigger", "reapply_ms"}:
        raise ValueError("unsupported spawn schema")
    if data["spawn"]["trigger"] != "first_target_pos_after_runtime_ack":
        raise ValueError("unsupported spawn trigger")
    target = data["target"]
    if type(target) is not dict or set(target) != {"placement_index", "profile", "position"}:
        raise ValueError("unsupported target schema")
    position = target["position"]
    if (
        type(position) is not dict
        or set(position) != {"mode", "dx", "dy", "dz"}
        or position["mode"] != "player_relative"
    ):
        raise ValueError("unsupported target position")
    if type(data["capabilities"]) is not list or type(data["nonclaims"]) is not list:
        raise ValueError("capabilities and nonclaims must be arrays")
    caps = tuple(data["capabilities"])
    nonclaims = tuple(data["nonclaims"])
    values = (position["dx"], position["dy"], position["dz"])
    if (
        data["entry"]["scene_id"] != 1
        or type(data["spawn"]["reapply_ms"]) is not int
        or target["placement_index"] != 30
        or type(target["placement_index"]) is not int
        or target["profile"] != expected_profile
        or not (0 <= data["spawn"]["reapply_ms"] <= 60000)
        or caps != ("spawn", "target")
        or nonclaims != ("authentic_position", "tab", "combat", "ai", "damage", "loot")
        or not all(type(value) in (int, float) and math.isfinite(value) for value in values)
    ):
        raise ValueError("scenario exceeds the evidence-backed Arena allowlist")
    return ArenaScenario(
        str(data["id"]), 1, data["spawn"]["trigger"],
        int(data["spawn"]["reapply_ms"]), 30, expected_profile,
        *(float(value) for value in values), caps, nonclaims, basic_faction,
    )


def make_p30_target(legacy, scenario: ArenaScenario, player_position):
    """Build one P30 actor at explicit test-only player-relative geometry."""
    # PF-HYPOTHESIS-LEDGER: GEO-PF-001 harness_only
    x, y, z, _heading, _flags, _moving = player_position
    target_x, target_y, target_z = x + scenario.dx, y + scenario.dy, z + scenario.dz
    row = legacy._v112_test_rows((scenario.placement_index,))[0]
    idx, template_id, _px, _py, _pz, preset, _name = row
    if (idx, template_id, 0x2000 + idx + 1) != (30, 31, legacy.V112_MONSTER_ACTOR_ID):
        raise AssertionError("P30 identity/template provenance drift")
    actor_id = legacy.V112_MONSTER_ACTOR_ID
    npc_kwargs = dict(
        template_id=template_id, actor_identity=actor_id,
        scene_id=1, scene_seq=0, visual_preset=preset,
        current_hp=legacy.V117_P30_EXACT_HP,
        max_hp=legacy.V117_P30_EXACT_HP,
        basic_name=legacy.V119_P30_TARGET_NAME,
    )
    if scenario.basic_faction is None:
        npc_attr = legacy.make_npc_attr(**npc_kwargs)
    else:
        npc_attr = make_npc_attr_with_basic_faction(
            legacy, **npc_kwargs, basic_faction=scenario.basic_faction,
        )
    heading = legacy._heading_to_player(target_x, target_y, x, y)
    movement = legacy.make_remote_movement_attr(
        actor_id, target_x, target_y, target_z, heading, mask=0xFF,
    )
    entry = legacy.make_remote_actor_entry(
        4, actor_id,
        [(legacy.NPC_ATTR, npc_attr), (legacy.MOVEMENT_ATTR, movement)],
    )
    pc, frame = legacy.make_runtime_remote_actors([entry])
    return pc, frame, (target_x, target_y, target_z, heading)


def is_p30_target_observation(legacy, parsed) -> bool:
    """Accept only complete, observed Target/Choose shapes for P30."""
    if not (
        parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
        and parsed.outer_version == 0
        and parsed.outer_mask == 2
        and parsed.nested_id == legacy.TARGET_VITAL
        and parsed.nested_version == 0
        and 1 <= parsed.vital_count <= 4
    ):
        return False
    try:
        cursor = legacy.Cursor(parsed.nested_payload)
        if struct.unpack("<Q", cursor.raw8(0x32))[0] != legacy.V112_MONSTER_ACTOR_ID:
            return False
        if cursor.u8(0x08) != 2:
            return False
        choose_count = 0
        target_pos_seen = False
        for ordinal in range(1, parsed.vital_count):
            nested_id = cursor.u16(0x12)
            if cursor.u8(0x0B) != 0:
                return False
            if nested_id == legacy.CHOOSE_NPC and not target_pos_seen:
                if struct.unpack("<Q", cursor.raw8(0x32))[0] != legacy.V112_MONSTER_ACTOR_ID:
                    return False
                choose_count += 1
                if choose_count > 2:
                    return False
            elif nested_id == legacy.TARGET_POS_VITAL and ordinal == parsed.vital_count - 1:
                values = tuple(cursor.f32(0x2A) for _ in range(4))
                cursor.u8(0x0B)
                cursor.u8(0x0B)
                if not all(math.isfinite(value) for value in values):
                    return False
                target_pos_seen = True
            else:
                return False
        return cursor.remain() == 0
    except (ValueError, struct.error):
        return False
