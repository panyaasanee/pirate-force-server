"""Strict configuration for the isolated Scene2 load-only milestone."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

from .model import Position


@dataclass(frozen=True)
class SceneRemoteActor:
    placement_index: int
    actor_identity: int
    template_id: int
    visual_preset: str
    name: str
    faction: int
    position: Position


@dataclass(frozen=True)
class SceneLoadScenario:
    scenario_id: str
    required_character_name: str
    position: Position
    remote_actor: SceneRemoteActor | None = None


def load_scene_load_scenario(path: str | Path) -> SceneLoadScenario:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) not in ({
        "schema", "id", "test_only", "entry", "persistence", "population",
        "capabilities", "nonclaims",
    }, {
        "schema", "id", "test_only", "entry", "persistence", "population",
        "capabilities", "nonclaims", "remote_actor",
    }):
        raise ValueError("scene-load scenario root is incomplete or has unknown fields")
    if (
        type(data["schema"]) is not int
        or data["schema"] != 1
        or data["id"] not in {"scene2_load_only_marker2", "scene2_fighting_fish_soldier_p60"}
        or data["test_only"] is not True
        or data["persistence"] != "read_only_existing_character"
        or data["population"] != "none"
        or data["capabilities"] != (["scene_load"] if data["id"] == "scene2_load_only_marker2" else ["scene_load", "spawn", "target"])
        or data["nonclaims"] != [
            "scene_seq_provenance", "heading_mapping", "population", "interaction",
            "monster", "faction", "travel", "combat",
        ]
    ):
        raise ValueError("unsupported scene-load scenario")
    entry = data["entry"]
    if type(entry) is not dict or set(entry) != {
        "flow", "required_character_name", "scene_id", "scene_seq", "position",
    }:
        raise ValueError("scene-load entry is incomplete or has unknown fields")
    position = entry["position"]
    if type(position) is not dict or set(position) != {
        "x", "y", "z", "heading", "coordinate_provenance", "heading_provenance",
    }:
        raise ValueError("scene-load position is incomplete or has unknown fields")
    values = (position["x"], position["y"], position["z"], position["heading"])
    if (
        entry["flow"] != "full_existing_character"
        or entry["required_character_name"] != "Arena01"
        or type(entry["scene_id"]) is not int
        or entry["scene_id"] != 2
        or type(entry["scene_seq"]) is not int
        or entry["scene_seq"] != 0
        or values != (26905, 21185, 1680, 0)
        or position["coordinate_provenance"] != "scene2_marker2"
        or position["heading_provenance"] != "direction8_unmapped_constructor_zero"
        or not all(type(value) in (int, float) and math.isfinite(value) for value in values)
    ):
        raise ValueError("scene-load scenario exceeds the evidence-backed allowlist")
    remote = None
    if data["id"] == "scene2_fighting_fish_soldier_p60":
        actor = data.get("remote_actor")
        expected = {
            "trigger": "first_target_pos_after_runtime_ack", "placement_index": 60,
            "actor_identity": "0x203D", "template_id": 34,
            "visual_preset": "M025_001_000_N", "name": "Fighting Fish soldier",
            "faction": 6, "scene_id": 2, "scene_seq": 0,
            "x": 21421.0059, "y": 9277.1123, "z": 590.6788, "heading": 0,
        }
        if type(actor) is not dict or actor != expected:
            raise ValueError("remote actor exceeds the exact data-backed allowlist")
        remote = SceneRemoteActor(60, 0x203D, 34, "M025_001_000_N",
            "Fighting Fish soldier", 6, Position(2, 0, 21421.0059, 9277.1123, 590.6788, 0))
    elif "remote_actor" in data:
        raise ValueError("load-only scenario cannot include a remote actor")
    return SceneLoadScenario(
        data["id"], entry["required_character_name"],
        Position(2, 0, *(float(value) for value in values)),
        remote,
    )
