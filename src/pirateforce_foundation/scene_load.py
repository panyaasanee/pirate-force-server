"""Strict configuration for the isolated Scene2 load-only milestone."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

from .model import Position


@dataclass(frozen=True)
class SceneLoadScenario:
    scenario_id: str
    required_character_name: str
    position: Position


def load_scene_load_scenario(path: str | Path) -> SceneLoadScenario:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {
        "schema", "id", "test_only", "entry", "persistence", "population",
        "capabilities", "nonclaims",
    }:
        raise ValueError("scene-load scenario root is incomplete or has unknown fields")
    if (
        type(data["schema"]) is not int
        or data["schema"] != 1
        or data["id"] != "scene2_load_only_marker2"
        or data["test_only"] is not True
        or data["persistence"] != "read_only_existing_character"
        or data["population"] != "none"
        or data["capabilities"] != ["scene_load"]
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
    return SceneLoadScenario(
        data["id"], entry["required_character_name"],
        Position(2, 0, *(float(value) for value in values)),
    )
