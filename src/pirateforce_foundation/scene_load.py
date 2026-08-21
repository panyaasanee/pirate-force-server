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
    # PF-HYPOTHESIS-LEDGER: HYP-PF-001 frozen
    # PF-HYPOTHESIS-LEDGER: HYP-PF-002 frozen
    # PF-HYPOTHESIS-LEDGER: HYP-PF-007 frozen
    # PF-HYPOTHESIS-LEDGER: DIAG-PF-001 frozen
    # PF-HYPOTHESIS-LEDGER: GEO-PF-002 frozen
    # PF-HYPOTHESIS-LEDGER: GEO-PF-003 frozen
    # PF-HYPOTHESIS-LEDGER: GEO-PF-006 harness_only
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
        or data["id"] not in {"scene2_load_only_marker2", "scene2_fighting_fish_soldier_p60", "scene2_fighting_fish_soldier_p60_hp3857", "scene2_fighting_fish_soldier_p60_hp3857_player_faction1", "port_royal_fighting_fish_soldier_p60_hp3857_player_faction1_ea7d_ack", "port_royal_tornado_eagle_p30_load_only"}
        or data["test_only"] is not True
        or data["persistence"] != "read_only_existing_character"
        or data["population"] != "none"
        or data["capabilities"] != (["scene_load"] if data["id"] in {"scene2_load_only_marker2", "port_royal_tornado_eagle_p30_load_only"} else (["scene_load", "spawn", "target", "action_ack"] if data["id"].endswith("_ea7d_ack") else ["scene_load", "spawn", "target"]))
        or data["nonclaims"] != (
            ["scene_seq_provenance", "heading_mapping", "population",
             "authentic_player_faction", "attack", "travel", "combat"]
            if data["id"] in {"scene2_fighting_fish_soldier_p60_hp3857_player_faction1", "port_royal_fighting_fish_soldier_p60_hp3857_player_faction1_ea7d_ack"}
            else ["scene_seq_provenance", "scene_id_numeric_provenance",
                  "heading_mapping", "camera_orientation", "native_render",
                  "client_standing_position", "population", "interaction",
                  "monster", "faction", "travel", "combat"]
            if data["id"] == "port_royal_tornado_eagle_p30_load_only"
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
    eagle = data["id"] == "port_royal_tornado_eagle_p30_load_only"
    fish_profile = data["id"] not in {"scene2_load_only_marker2", "port_royal_tornado_eagle_p30_load_only"}
    scene007 = data["id"].endswith("_ea7d_ack")
    # GT-034 HOSTILE-NATIVE-001: the bg0001 P30 row 0x201F "Tornado Eagle"
    # sits at (1747.5244140625, -7837.69775390625, 931.0413208007812).  The
    # player is placed +100 X at the row's own Z -- the point V127/V128
    # runtime-passing lanes stood a live client on -- with heading pi from
    # the remote-NPC heading convention (v141 _heading_to_player, +X=0,
    # -X=pi) so the delivered facing points at the placement.  This is the
    # first nonzero local-player spawn heading in the lineage: whether the
    # client applies it to the avatar or the camera is unmeasured (the V134
    # camera workaround suggests the initial camera faces +X regardless),
    # and native render / camera orientation / standing position are all
    # declared nonclaims below.
    expected_player = (
        (1847.5244140625, -7837.69775390625, 931.0413208007812, math.pi) if eagle else
        (0, 0, 931, 0) if scene007 else
        ((21321.0059, 9227.1123, 590.6788, 0) if fish_profile else (26905, 21185, 1680, 0)))
    expected_coordinate_provenance = (
        "bg0001_p30_plus100x_samey_samez_observation_trick" if eagle else
        "v74_exact_port_royal_targetpos" if scene007 else
        ("synthetic_p60_minus100x_minus50y_samez" if fish_profile else "scene2_marker2")
    )
    expected_heading_provenance = (
        "v141_heading_to_player_convention_pi_facing_minus_x_toward_p30" if eagle else
        "v74_exact_targetpos_zero" if scene007 else
        ("constructor_zero" if fish_profile else "direction8_unmapped_constructor_zero")
    )
    expected_scene = 1 if (scene007 or eagle) else 2
    if (
        entry["flow"] != "full_existing_character"
        or entry["required_character_name"] != "Arena01"
        or type(entry["scene_id"]) is not int
        or entry["scene_id"] != expected_scene
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
            "faction": 6, "scene_id": expected_scene, "scene_seq": 0,
            "x": (1788.796875 if scene007 else 21421.0059),
            "y": (-1121.6756591796875 if scene007 else 9277.1123),
            "z": (930.423583984375 if scene007 else 590.6788), "heading": 0,
        }
        if scene007:
            expected["position_provenance"] = "v74_p144_jessica_exact_placement_user_confirmed_beer_tray_visual"
            expected["heading_provenance"] = "v74_emitted_cardinal_calibration_p144_mod4_zero_not_authentic_heading"
        diagnostic_hp = None
        if data["id"] in {"scene2_fighting_fish_soldier_p60_hp3857", "scene2_fighting_fish_soldier_p60_hp3857_player_faction1", "port_royal_fighting_fish_soldier_p60_hp3857_player_faction1_ea7d_ack"}:
            expected.update({"diagnostic_current_hp": 3857, "diagnostic_max_hp": 3857,
                             "hp_provenance": "bounded_level27_diagnostic_not_spawn_policy"})
            diagnostic_hp = 3857
        if type(actor) is not dict or actor != expected:
            raise ValueError("remote actor exceeds the exact data-backed allowlist")
        remote = SceneRemoteActor(60, 0x203D, 34, "M025_001_000_N",
            "Fighting Fish soldier", 6, Position(expected_scene, 0,
            expected["x"], expected["y"], expected["z"], 0), diagnostic_hp)
    elif "remote_actor" in data:
        raise ValueError("load-only scenario cannot include a remote actor")
    player_basic_faction = None
    if data["id"] in {"scene2_fighting_fish_soldier_p60_hp3857_player_faction1", "port_royal_fighting_fish_soldier_p60_hp3857_player_faction1_ea7d_ack"}:
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
        expected_ack = {"action": "0xEA7D", "target_identity": "0x203D", "scene_id": 1, "request_provenance": "scene006_exact_shape_relocated_v74_port_royal_harness", "response": "single_actionvital_performer_identity_only", "effects": "none"}
        if data.get("action_ack") != expected_ack:
            raise ValueError("action ack exceeds the exact SCENE-007 allowlist")
        action_ack = SceneActionAck(0xEA7D, 0x203D, 1)
    elif "action_ack" in data:
        raise ValueError("baseline scene-load scenarios cannot enable action ack")
    return SceneLoadScenario(
        data["id"], entry["required_character_name"],
        Position(expected_scene, 0, *(float(value) for value in values)),
        remote, player_basic_faction, action_ack,
    )
