import hashlib
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.scenario import load_scenario, make_p30_target
from pirateforce_foundation.store import SQLiteStore


class ArenaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.scenario = load_scenario(ROOT / "scenarios/arena_v1.json")
        self.store = SQLiteStore(Path(self.tmp.name) / "arena.sqlite3", ROOT / "migrations")
        self.store.migrate()
        default = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default, self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.projector = LegacyProjector(self.legacy)

    def tearDown(self):
        self.tmp.cleanup()

    def state(self, scenario=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            self.scenario if scenario else None,
        )
        state = state_type("arena")
        state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_client_login_pc()))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[0]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    def target_pos_pc(self, x=10.0, y=20.0, z=30.0, heading=0.0):
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.f32tag(x) + self.legacy.f32tag(y)
            + self.legacy.f32tag(z) + self.legacy.f32tag(heading)
            + self.legacy.u8tag(0x0B, 1)
            + self.legacy.u8tag(0x0B, 0)
        )

    def p30_target_pc(self):
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.qwordtag(0x32, self.legacy.V112_MONSTER_ACTOR_ID)
            + self.legacy.u8tag(0x08, 2)
        )

    def test_scenario_schema_is_strict(self):
        data = json.loads((ROOT / "scenarios/arena_v1.json").read_text())
        bad = Path(self.tmp.name) / "bad.json"
        data["unexpected"] = True
        bad.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_scenario(bad)
        data.pop("unexpected")
        data["target"]["placement_index"] = 31
        bad.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_scenario(bad)
        data["target"]["placement_index"] = 30
        data["schema"] = True
        bad.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_scenario(bad)
        data["schema"] = 1
        data["spawn"]["reapply_ms"] = 3000.9
        bad.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_scenario(bad)
        data["spawn"]["reapply_ms"] = 3000
        data["capabilities"].append("spawn")
        bad.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_scenario(bad)
        for field, invalid in (
            ("entry", 7), ("spawn", None), ("target", False),
            ("capabilities", 7), ("nonclaims", {}),
        ):
            candidate = json.loads((ROOT / "scenarios/arena_v1.json").read_text())
            candidate[field] = invalid
            bad.write_text(json.dumps(candidate), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_scenario(bad)

    def test_arena_packet_golden(self):
        pc, frame, target = make_p30_target(
            self.legacy, self.scenario, (10.0, 20.0, 30.0, 0.0, 0, 1),
        )
        golden = json.loads((ROOT / "tests/golden/arena_v1.json").read_text())
        self.assertEqual(target[:3], (110.0, 70.0, 30.0))
        self.assertEqual(len(pc), golden["pc_length"])
        self.assertEqual(len(frame), golden["frame_length"])
        self.assertEqual(hashlib.sha256(pc).hexdigest().upper(), golden["pc_sha256"])
        self.assertEqual(hashlib.sha256(frame).hexdigest().upper(), golden["frame_sha256"])
        self.assertEqual(pc.count("Tornado Eagle".encode("utf-16le")), 1)
        self.assertEqual(pc.count(self.legacy.u32tag(0x14, 3857)), 2)

    def test_first_strict_target_pos_spawns_only_p30_once(self):
        state = self.state(scenario=True)
        actions = state.dispatch(self.legacy.parse_outer(self.target_pos_pc()))
        arena = [action for action in actions if action[0].startswith("ARENA_V1_")]
        self.assertEqual([a[0] for a in arena], [
            "ARENA_V1_P30_INITIAL", "ARENA_V1_P30_MODEL_READY_REAPPLY",
        ])
        self.assertEqual([a[3] for a in arena], [0.0, 3.0])
        self.assertTrue(state.arena_spawned)
        self.assertEqual(state.population_indices, (30,))
        self.assertNotIn("V134_P0_P30_P91_ISOLATED_INITIAL_READY", [a[0] for a in actions])
        replay = state.dispatch(self.legacy.parse_outer(self.target_pos_pc()))
        self.assertFalse(any(a[0].startswith("ARENA_V1_") for a in replay))

    def test_wrong_shape_and_no_scenario_preserve_boundaries(self):
        state = self.state(scenario=True)
        parsed = self.legacy.parse_outer(self.target_pos_pc())
        parsed.vital_count = 2
        malformed_actions = state.dispatch(parsed)
        self.assertEqual(malformed_actions, [])
        self.assertFalse(any(a[0].startswith("ARENA_V1_") for a in malformed_actions))
        self.assertFalse(any("P0_P30_P91" in a[0] for a in malformed_actions))
        self.assertFalse(state.arena_spawned)
        self.assertFalse(state.npc_spawn_sent)
        self.assertIsNone(state.last_target_pos)
        self.assertEqual(state.dispatch(self.legacy.parse_outer(self.p30_target_pc())), [])
        self.assertFalse(state.arena_spawned)
        self.assertFalse(state.npc_spawn_sent)

        normal = self.state(scenario=False)
        actions = normal.dispatch(self.legacy.parse_outer(self.target_pos_pc()))
        labels = [a[0] for a in actions]
        self.assertIn("V134_P0_P30_P91_ISOLATED_INITIAL_READY", labels)
        self.assertFalse(any(label.startswith("ARENA_V1_") for label in labels))

    def test_target_capture_is_observation_only(self):
        state = self.state(scenario=True)
        state.dispatch(self.legacy.parse_outer(self.target_pos_pc()))
        pc = self.p30_target_pc()
        actions = state.dispatch(self.legacy.parse_outer(pc))
        self.assertEqual(actions, [])
        self.assertTrue(state.arena_target_captured)
        self.assertIn("arena_v1_p30_target_kind2_captured_no_reply", state.events)

        malformed = self.legacy.parse_outer(pc)
        malformed.vital_count = 2
        second = self.state(scenario=True)
        second.dispatch(self.legacy.parse_outer(self.target_pos_pc()))
        self.assertEqual(second.dispatch(malformed), [])
        self.assertFalse(second.arena_target_captured)


if __name__ == "__main__":
    unittest.main()
