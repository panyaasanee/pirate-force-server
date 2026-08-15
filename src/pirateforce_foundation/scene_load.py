"""Strict configuration for the isolated Scene2 load-only milestone."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

from .model import Position
from .action_ack import SceneActionAck


@dataclass(frozen=True)
class SceneRemoteActor:
    placement_index: int
    actor_identity: int
    template_id: int
    visual_preset: str
    name: str
    faction: int
    position: Position
    diagnostic_hp: int | None = None


@dataclass(frozen=True)
class SceneLoadScenario:
    scenario_id: str
    required_character_name: str
    position: Position
    remote_actor: SceneRemoteActor | None = None
    player_basic_faction: int | None = None
    action_ack: SceneActionAck | None = None


def load_scene_load_scenario(path: str | Path) -> SceneLoadScenario:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) not in ({
        "schema", "id", "test_only", "entry", "persistence", "population",
        "capabilities", "nonclaims",
    }, {
        "schema", "id", "test_only", "entry", "persistence", "population",
        "capabilities", "nonclaims", "remote_actor",
    }, {
        "schema", "id", "test_only", "entry", "persistence", "population",
        "capabilities", "nonclaims", "remote_actor", "player_relation",
    }, {
        "schema", "id", "test_only", "entry", "persistence", "population",
        "capabilities", "nonclaims", "remote_actor", "player_relation", "action_ack",
    }):
        raise ValueError("scene-load scenario root is incomplete or has unknown fields")
    if (
        type(data["schema"]) is not int
        or data["schema"] != 1
        or data["id"] not in {"scene2_load_only_marker2", "scene2_fighting_fish_soldier_p60", "scene2_fighting_fish_soldier_p60_hp3857", "scene2_fighting_fish_soldier_p60_hp3857_player_faction1", "scene2_fighting_fish_soldier_p60_hp3857_player_faction1_ea7d_ack"}
        or data["test_only"] is not True
        or data["persistence"] != "read_only_existing_character"
        or data["population"] != "none"
        or data["capabilities"] != (["scene_load"] if data["id"] == "scene2_load_only_marker2" else (["scene_load", "spawn", "target", "action_ack"] if data["id"].endswith("_ea7d_ack") else ["scene_load", "spawn", "target"]))
        or data["nonclaims"] != (
            ["scene_seq_provenance", "heading_mapping", "population",
             "authentic_player_faction", "attack", "travel", "combat"]
            if data["id"] in {"scene2_fighting_fish_soldier_p60_hp3857_player_faction1", "scene2_fighting_fish_soldier_p60_hp3857_player_faction1_ea7d_ack"}
            else ["scene_seq_provenance", "heading_mapping", "population", "interaction",
                  "monster", "faction", "travel", "combat"]
        )
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
    fish_profile = data["id"] != "scene2_load_only_marker2"
    expected_player = (
        (21321.0059, 9227.1123, 590.6788, 0)
        if fish_profile else (26905, 21185, 1680, 0)
    )
    expected_coordinate_provenance = (
        "synthetic_p60_minus100x_minus50y_samez"
        if fish_profile else "scene2_marker2"
    )
    expected_heading_provenance = (
        "constructor_zero" if fish_profile
        else "direction8_unmapped_constructor_zero"
    )
    if (
        entry["flow"] != "full_existing_character"
        or entry["required_character_name"] != "Arena01"
        or type(entry["scene_id"]) is not int
        or entry["scene_id"] != 2
        or type(entry["scene_seq"]) is not int
        or entry["scene_seq"] != 0
        or values != expected_player
        or position["coordinate_provenance"] != expected_coordinate_provenance
        or position["heading_provenance"] != expected_heading_provenance
        or not all(type(value) in (int, float) and math.isfinite(value) for value in values)
    ):
        raise ValueError("scene-load scenario exceeds the evidence-backed allowlist")
    remote = None
    if fish_profile:
        actor = data.get("remote_actor")
        expected = {
            "trigger": "first_target_pos_after_runtime_ack", "placement_index": 60,
            "actor_identity": "0x203D", "template_id": 34,
            "visual_preset": "M025_001_000_N", "name": "Fighting Fish soldier",
            "faction": 6, "scene_id": 2, "scene_seq": 0,
            "x": 21421.0059, "y": 9277.1123, "z": 590.6788, "heading": 0,
        }
        diagnostic_hp = None
        if data["id"] in {"scene2_fighting_fish_soldier_p60_hp3857", "scene2_fighting_fish_soldier_p60_hp3857_player_faction1", "scene2_fighting_fish_soldier_p60_hp3857_player_faction1_ea7d_ack"}:
            expected.update({"diagnostic_current_hp": 3857, "diagnostic_max_hp": 3857,
                             "hp_provenance": "bounded_level27_diagnostic_not_spawn_policy"})
            diagnostic_hp = 3857
        if type(actor) is not dict or actor != expected:
            raise ValueError("remote actor exceeds the exact data-backed allowlist")
        remote = SceneRemoteActor(60, 0x203D, 34, "M025_001_000_N",
            "Fighting Fish soldier", 6, Position(2, 0, 21421.0059, 9277.1123, 590.6788, 0), diagnostic_hp)
    elif "remote_actor" in data:
        raise ValueError("load-only scenario cannot include a remote actor")
    player_basic_faction = None
    if data["id"] in {"scene2_fighting_fish_soldier_p60_hp3857_player_faction1", "scene2_fighting_fish_soldier_p60_hp3857_player_faction1_ea7d_ack"}:
        if data.get("player_relation") != {
            "basic_faction": 1,
            "provenance": "faction_table_relation_candidate_not_authentic_player_faction",
        }:
            raise ValueError("player relation probe exceeds the exact allowlist")
        player_basic_faction = 1
    elif "player_relation" in data:
        raise ValueError("baseline scene-load scenarios cannot set player relation")
    action_ack = None
    if data["id"].endswith("_ea7d_ack"):
        expected_ack = {"action": "0xEA7D", "target_identity": "0x203D", "request_provenance": "scene006_exact_runtime", "response": "single_actionvital_performer_identity_only", "effects": "none"}
        if data.get("action_ack") != expected_ack:
            raise ValueError("action ack exceeds the exact SCENE-007 allowlist")
        action_ack = SceneActionAck(0xEA7D, 0x203D)
    elif "action_ack" in data:
        raise ValueError("baseline scene-load scenarios cannot enable action ack")
    return SceneLoadScenario(
        data["id"], entry["required_character_name"],
        Position(2, 0, *(float(value) for value in values)),
        remote, player_basic_faction, action_ack,
    )
