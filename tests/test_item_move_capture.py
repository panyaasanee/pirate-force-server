import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.inventory import (
    INITIAL_BACKPACK,
    MERGED_V111_BACKPACK,
    V111_MERGE_REQUEST_PC,
)
from pirateforce_foundation.app import resolve_item_move_capture_db
from pirateforce_foundation.item_move_capture import (
    ITEM_MOVE_CAPTURE_FIELDS,
    ITEM_MOVE_CAPTURE_REQUEST_PC,
    ITEM_MOVE_CAPTURE_REQUEST_SHA256,
    ItemMoveCaptureScenario,
    load_item_move_capture_scenario,
    require_item_move_capture_scenario,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.population_scenario import load_population_scenario
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "item_move_capture_v111_slot2.json"


class ItemMoveCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        default = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default, self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_item_move_capture_scenario(SCENARIO_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, capture=False, create=True, ready=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            item_move_capture_scenario=self.scenario if capture else None,
        )
        state = state_type(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        if create:
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC
            ))
            self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(state.foundation.account_id)
        self.assertEqual(len(characters), 1)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state, characters[0]

    def _merged_capture_state(self, login="capture"):
        baseline, character = self._state(login)
        actions = baseline.dispatch(self.legacy.parse_outer(V111_MERGE_REQUEST_PC))
        self.assertEqual(len(actions), 1)
        self.assertEqual(baseline.foundation.backpack, MERGED_V111_BACKPACK)
        baseline.foundation.close_connection()
        captured, same = self._state(login, capture=True, create=False)
        self.assertEqual(same.id, character.id)
        self.assertEqual(captured.foundation.backpack, MERGED_V111_BACKPACK)
        return captured, same

    def _request(self, operation=4, value32=2, identity=1):
        pc = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.ITEM_OPERATE_REQ_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.u8tag(0x0B, operation)
            + self.legacy.u32tag(0x14, value32)
            + self.legacy.qwordtag(0x32, identity)
        )
        return pc, self.legacy.parse_outer(pc)

    def _inventory_rows(self, character_id):
        with self.store.connect() as db:
            return db.execute(
                "SELECT item_identity,template_id,quantity,slot,raw_u8_38,"
                "raw_u8_39,detail_present FROM character_backpack_items "
                "WHERE character_id=? ORDER BY item_identity",
                (character_id,),
            ).fetchall()

    def test_config_is_an_exact_capture_only_allowlist(self):
        raw = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(self.scenario.operation, 4)
        self.assertEqual(self.scenario.value32, 2)
        self.assertEqual(self.scenario.item_identity, 1)
        self.assertEqual(raw["capabilities"], [
            "capture_exact_item_move_request_no_reply"
        ])
        self.assertNotIn("response_bytes", json.dumps(raw, sort_keys=True))
        self.assertNotIn("database_mutation", json.dumps(raw, sort_keys=True))

        variants = []
        value = copy.deepcopy(raw); value["candidate"]["value32"] = True
        variants.append(value)
        value = copy.deepcopy(raw); value["candidate"]["pc_size"] = 36.0
        variants.append(value)
        value = copy.deepcopy(raw); value["candidate"]["extra"] = 0
        variants.append(value)
        value = copy.deepcopy(raw); value["nonclaims"].reverse()
        variants.append(value)
        for ordinal, variant in enumerate(variants):
            path = Path(self.tmp.name) / f"bad-{ordinal}.json"
            path.write_text(json.dumps(variant), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact allowlist"):
                load_item_move_capture_scenario(path)

        with self.assertRaisesRegex(ValueError, "scenario object"):
            require_item_move_capture_scenario(ItemMoveCaptureScenario(
                self.scenario.scenario_id, True, 2, 1,
                ITEM_MOVE_CAPTURE_REQUEST_SHA256,
            ))

    def test_exact_fixture_logs_once_without_response_or_item_mutation(self):
        state, character = self._merged_capture_state()
        request_pc, parsed = self._request()
        self.assertEqual(request_pc, ITEM_MOVE_CAPTURE_REQUEST_PC)
        self.assertEqual(len(request_pc), 36)
        self.assertEqual(
            hashlib.sha256(request_pc).hexdigest().upper(),
            ITEM_MOVE_CAPTURE_REQUEST_SHA256,
        )
        before_rows = self._inventory_rows(character.id)
        before_state = (
            state.foundation.backpack, state.item_slot, state.item_quantity,
            state.stack_source_present,
        )
        with mock.patch.object(
            self.store, "apply_v111_stack_merge",
            side_effect=AssertionError("capture attempted inventory write"),
        ), mock.patch.object(
            self.store, "save_position",
            side_effect=AssertionError("capture attempted position write"),
        ):
            self.assertEqual(state.dispatch(parsed), [])
            self.assertEqual(state.dispatch(parsed), [])

        self.assertEqual(state.item_move_capture_count, 1)
        self.assertEqual(state.item_move_capture_last_fields, ITEM_MOVE_CAPTURE_FIELDS)
        self.assertIn(
            "item_move_capture_exact_op4_slot2_id1_no_reply", state.events,
        )
        self.assertIn("item_move_capture_duplicate_exact_no_reply", state.events)
        self.assertEqual(
            (state.foundation.backpack, state.item_slot, state.item_quantity,
             state.stack_source_present), before_state,
        )
        self.assertEqual(self._inventory_rows(character.id), before_rows)

    def test_malformed_wrong_envelope_and_wrong_tuple_are_owned(self):
        state, character = self._merged_capture_state("invalid")
        wrong_tuples = [
            self._request(operation=5)[1],
            self._request(value32=3)[1],
            self._request(identity=4)[1],
        ]
        malformed = [
            self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC + b"\x00"),
            self.legacy.parse_outer(
                ITEM_MOVE_CAPTURE_REQUEST_PC[:20]
                + b"\x08" + ITEM_MOVE_CAPTURE_REQUEST_PC[21:]
            ),
        ]
        wrong_envelopes = []
        for attribute, value in (
            ("outer_id", self.legacy.GSCN_RUNTIME_PROTOCOL_REQ + 1),
            ("outer_version", 1),
            ("outer_mask", 3),
            ("vital_count", 2),
            ("nested_version", 1),
        ):
            parsed = self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC)
            setattr(parsed, attribute, value)
            wrong_envelopes.append(parsed)
        before_rows = self._inventory_rows(character.id)

        for parsed in (*malformed, *wrong_envelopes, *wrong_tuples):
            self.assertEqual(state.dispatch(parsed), [])
        self.assertEqual(state.item_move_capture_count, 0)
        self.assertEqual(state.item_move_capture_last_fields, None)
        self.assertEqual(
            state.events.count("item_move_capture_malformed_or_trailing_no_reply"),
            len(malformed),
        )
        self.assertEqual(
            state.events.count("item_move_capture_wrong_envelope_no_reply"),
            len(wrong_envelopes),
        )
        self.assertEqual(
            state.events.count("item_move_capture_wrong_tuple_no_reply"),
            len(wrong_tuples),
        )
        self.assertNotIn(
            "V111_ITEM_MOVE_ID1_SLOT0_TO_SLOT3_SUCCESS",
            [event for event in state.events],
        )
        self.assertEqual(self._inventory_rows(character.id), before_rows)

    def test_no_selected_wrong_sequence_and_wrong_current_state_are_distinct(self):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            item_move_capture_scenario=self.scenario,
        )
        no_selected = state_type("no-selected")
        self.assertEqual(no_selected.dispatch(
            self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC)
        ), [])
        self.assertIn("item_move_capture_no_selected_no_reply", no_selected.events)

        merged, _ = self._merged_capture_state("sequence")
        merged.runtime_ack_sent = False
        self.assertEqual(merged.dispatch(
            self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC)
        ), [])
        self.assertIn("item_move_capture_wrong_sequence_no_reply", merged.events)

        initial, character = self._state("initial", capture=True)
        self.assertEqual(initial.foundation.backpack, INITIAL_BACKPACK)
        self.assertEqual(initial.dispatch(
            self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC)
        ), [])
        self.assertIn("item_move_capture_wrong_current_state_no_reply", initial.events)
        self.assertEqual(
            self.store.get_backpack(initial.foundation.session_id, character.id),
            INITIAL_BACKPACK,
        )

        merged, _ = self._merged_capture_state("unknown")
        merged.foundation.backpack = object()
        self.assertEqual(merged.dispatch(
            self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC)
        ), [])
        self.assertIn("item_move_capture_wrong_current_state_no_reply", merged.events)

    def test_capture_mode_owns_frozen_merge_without_replay_or_mutation(self):
        state, character = self._merged_capture_state("own-merge")
        before_rows = self._inventory_rows(character.id)
        before = (
            state.foundation.backpack, state.item_slot, state.item_quantity,
            state.stack_source_present,
        )
        with mock.patch.object(
            self.store, "apply_v111_stack_merge",
            side_effect=AssertionError("capture fell through to persistent merge"),
        ):
            self.assertEqual(state.dispatch(
                self.legacy.parse_outer(V111_MERGE_REQUEST_PC)
            ), [])
        self.assertEqual(state.item_move_capture_count, 0)
        self.assertIsNone(state.item_move_capture_last_fields)
        self.assertIn("item_move_capture_wrong_tuple_no_reply", state.events)
        self.assertNotIn("foundation_v111_merge_replay_no_reply", state.events)
        self.assertNotIn(
            "foundation_v111_merge_committed_before_response", state.events,
        )
        self.assertEqual(
            (state.foundation.backpack, state.item_slot, state.item_quantity,
             state.stack_source_present), before,
        )
        self.assertEqual(self._inventory_rows(character.id), before_rows)

    def test_baseline_frozen_move_bytes_and_behavior_remain_unchanged(self):
        state, character = self._state("baseline")
        request_pc, parsed = self._request(value32=3)
        actions = state.dispatch(parsed)
        expected_pc, expected_frame = self.legacy.make_item_operate_move_delta_success(
            3, 1,
        )
        self.assertIn((
            "V111_ITEM_MOVE_ID1_SLOT0_TO_SLOT3_SUCCESS",
            expected_pc, expected_frame, 0.0,
        ), actions)
        self.assertEqual(state.item_slot, 3)
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            INITIAL_BACKPACK,
        )
        self.assertNotEqual(request_pc, ITEM_MOVE_CAPTURE_REQUEST_PC)

    def test_modes_and_explicit_existing_database_are_fail_closed(self):
        population = load_population_scenario(
            ROOT / "scenarios" / "object_population_v94.json"
        )
        for kwargs in (
            {"scenario": object()},
            {"scene_load_scenario": object()},
            {"population_scenario": population},
        ):
            with self.assertRaisesRegex(ValueError, "mutually exclusive"):
                make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                    item_move_capture_scenario=self.scenario, **kwargs,
                )

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        base = [
            sys.executable, "-m", "pirateforce_foundation.app",
            "--item-move-capture-scenario", str(SCENARIO_PATH),
            "--self-test-only",
        ]
        missing = subprocess.run(
            base, cwd=ROOT, env=env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(missing.returncode, 2)
        self.assertIn("requires an explicit existing --db", missing.stderr)

        absent_path = Path(self.tmp.name) / "absent.sqlite3"
        absent = subprocess.run(
            [*base[:-1], "--db", str(absent_path), base[-1]],
            cwd=ROOT, env=env, text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(absent.returncode, 0)
        self.assertIn(absent_path.name, absent.stderr)
        self.assertFalse(absent_path.exists())

        relative_root = Path(self.tmp.name) / "relative-db"
        relative_root.mkdir()
        relative_db = relative_root / "capture-source.sqlite3"
        SQLiteStore(relative_db, ROOT / "migrations").migrate()
        capture_root = relative_root / "capture-root"
        capture_root.mkdir()
        previous = Path.cwd()
        try:
            os.chdir(relative_root)
            resolved = resolve_item_move_capture_db("capture-source.sqlite3")
            self.assertTrue(Path(resolved).is_absolute())
            self.assertTrue(Path(resolved).samefile(relative_db))
            pinned_store = SQLiteStore(resolved, ROOT / "migrations")
            os.chdir(capture_root)
            with pinned_store.connect() as db:
                self.assertEqual(
                    db.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0],
                    4,
                )
            self.assertFalse((capture_root / "capture-source.sqlite3").exists())
        finally:
            os.chdir(previous)

    def test_v141_is_still_the_exact_immutable_source(self):
        self.assertEqual(
            hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest().upper(),
            "2EB05ED2FDBDD5EE3D91F7FBB8C1D16A4C7A02A843BC97169B16A389E4EA4C22",
        )


if __name__ == "__main__":
    unittest.main()
