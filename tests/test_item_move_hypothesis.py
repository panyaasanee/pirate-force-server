from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
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

from pirateforce_foundation.inventory import (  # noqa: E402
    HYPOTHESIZED_V111_SLOT2_BACKPACK,
    INITIAL_BACKPACK,
    MERGED_V111_BACKPACK,
    V111_MERGE_REQUEST_PC,
    make_backpack_attr,
)
from pirateforce_foundation.item_move_capture import (  # noqa: E402
    ITEM_MOVE_CAPTURE_REQUEST_PC,
)
from pirateforce_foundation.item_move_hypothesis import (  # noqa: E402
    HYPOTHESIZED_MOVE_RESPONSE_FRAME_SHA256,
    HYPOTHESIZED_MOVE_RESPONSE_PC_SHA256,
    HYPOTHESIZED_SLOT2_BACKPACK_SHA256,
    ItemMoveHypothesisScenario,
    load_item_move_hypothesis_scenario,
    make_hypothesized_move_response,
    require_item_move_hypothesis_scenario,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "item_move_hypothesis_v111_slot2.json"


class ItemMoveHypothesisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_item_move_hypothesis_scenario(SCENARIO_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, hypothesis=False, create=True, ready=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            item_move_hypothesis_scenario=self.scenario if hypothesis else None,
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
        return state, characters[0], actions

    def _merged_hypothesis_state(self, login="hypothesis"):
        baseline, character, _ = self._state(login)
        actions = baseline.dispatch(self.legacy.parse_outer(V111_MERGE_REQUEST_PC))
        self.assertEqual(actions[0][0], "FOUNDATION_V111_ITEM_STACK_ID3_INTO_ID1_QTY2_COMMITTED")
        self.assertEqual(baseline.foundation.backpack, MERGED_V111_BACKPACK)
        baseline.foundation.close_connection()
        state, same, actions = self._state(
            login, hypothesis=True, create=False,
        )
        self.assertEqual(same.id, character.id)
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
        return state, same, actions

    def _rows(self, character_id):
        with self.store.connect() as db:
            return db.execute(
                "SELECT item_identity,template_id,quantity,slot,raw_u8_38,"
                "raw_u8_39,detail_present FROM character_backpack_items "
                "WHERE character_id=? ORDER BY item_identity",
                (character_id,),
            ).fetchall()

    def test_config_and_all_bytes_are_exact_and_type_strict(self):
        raw = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(raw["hypothesis_id"], "HYP-PF-008")
        self.assertFalse(raw["production_allowed"])
        self.assertEqual(raw["entry"]["destination_policy"], "slot2_must_be_free")
        self.assertEqual(raw["persisted_post_state"]["identity_order"], [1, 2, 4])

        pc, frame = make_hypothesized_move_response(self.legacy)
        self.assertEqual((len(pc), len(frame)), (71, 82))
        self.assertEqual(hashlib.sha256(pc).hexdigest().upper(), HYPOTHESIZED_MOVE_RESPONSE_PC_SHA256)
        self.assertEqual(hashlib.sha256(frame).hexdigest().upper(), HYPOTHESIZED_MOVE_RESPONSE_FRAME_SHA256)
        backpack = make_backpack_attr(self.legacy, HYPOTHESIZED_V111_SLOT2_BACKPACK)
        self.assertEqual(len(backpack), 124)
        self.assertEqual(hashlib.sha256(backpack).hexdigest().upper(), HYPOTHESIZED_SLOT2_BACKPACK_SHA256)

        variants = []
        value = copy.deepcopy(raw); value["schema"] = True; variants.append(value)
        value = copy.deepcopy(raw); value["composed_response"]["slot"] = 3; variants.append(value)
        value = copy.deepcopy(raw); value["persisted_post_state"]["identity_order"] = [2, 1, 4]; variants.append(value)
        value = copy.deepcopy(raw); value["production_allowed"] = True; variants.append(value)
        for ordinal, variant in enumerate(variants):
            path = Path(self.tmp.name) / f"bad-{ordinal}.json"
            path.write_text(json.dumps(variant), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact allowlist"):
                load_item_move_hypothesis_scenario(path)

        with self.assertRaisesRegex(ValueError, "scenario object"):
            require_item_move_hypothesis_scenario(ItemMoveHypothesisScenario(
                self.scenario.scenario_id, "HYP-PF-999",
                self.scenario.request_sha256, self.scenario.response_pc_sha256,
                self.scenario.response_frame_sha256, self.scenario.backpack_sha256,
            ))

    def test_exact_request_commits_before_one_composed_response_and_replay_is_silent(self):
        state, character, _ = self._merged_hypothesis_state()
        before_rows = self._rows(character.id)
        expected_pc, expected_frame = make_hypothesized_move_response(self.legacy)
        actions = state.dispatch(self.legacy.parse_outer(
            ITEM_MOVE_CAPTURE_REQUEST_PC
        ))
        self.assertEqual(actions, [(
            "HYP_PF_008_ITEM_MOVE_ID1_SLOT0_TO_FREE_SLOT2_COMMITTED",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertEqual(state.foundation.backpack, HYPOTHESIZED_V111_SLOT2_BACKPACK)
        self.assertEqual((state.item_slot, state.item_quantity), (2, 2))
        self.assertEqual(state.item_move_hypothesis_count, 1)
        self.assertIn(
            "item_move_hypothesis_committed_before_composed_response",
            state.events,
        )
        self.assertNotEqual(self._rows(character.id), before_rows)
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            HYPOTHESIZED_V111_SLOT2_BACKPACK,
        )

        self.assertEqual(state.dispatch(self.legacy.parse_outer(
            ITEM_MOVE_CAPTURE_REQUEST_PC
        )), [])
        self.assertEqual(state.item_move_hypothesis_count, 1)
        self.assertIn("item_move_hypothesis_replay_no_reply", state.events)

    def test_repository_failure_rolls_back_and_queues_nothing(self):
        state, character, _ = self._merged_hypothesis_state("rollback")
        before_rows = self._rows(character.id)
        with mock.patch.object(
            self.store, "_load_backpack",
            side_effect=[MERGED_V111_BACKPACK, RuntimeError("after validation")],
        ):
            self.assertEqual(state.dispatch(self.legacy.parse_outer(
                ITEM_MOVE_CAPTURE_REQUEST_PC
            )), [])
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertTrue(any(
            event.startswith("item_move_hypothesis_repository_failure_no_reply_")
            for event in state.events
        ))

    def test_reconnect_projection_is_opt_in_and_baseline_fails_closed(self):
        state, character, _ = self._merged_hypothesis_state("reconnect")
        self.assertEqual(len(state.dispatch(self.legacy.parse_outer(
            ITEM_MOVE_CAPTURE_REQUEST_PC
        ))), 1)
        state.foundation.close_connection()

        reconnected, same, actions = self._state(
            "reconnect", hypothesis=True, create=False,
        )
        self.assertEqual(same.id, character.id)
        self.assertEqual(reconnected.foundation.backpack, HYPOTHESIZED_V111_SLOT2_BACKPACK)
        hypothesized_wire = make_backpack_attr(
            self.legacy, HYPOTHESIZED_V111_SLOT2_BACKPACK,
        )
        self.assertEqual(actions[0][1].count(hypothesized_wire), 1)
        reconnected.foundation.close_connection()

        baseline_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        baseline = baseline_type("reconnect")
        baseline.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        rejected = baseline.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        self.assertEqual(rejected, [])
        self.assertIsNone(baseline.foundation.selected)
        self.assertIsNone(baseline.foundation.backpack)
        self.assertIn("foundation_start_game_rejected_no_reply", baseline.events)

    def test_all_other_item_operate_shapes_are_owned_without_mutation(self):
        state, character, _ = self._merged_hypothesis_state("negative")
        before_rows = self._rows(character.id)
        # value32=3 is the currently occupied blade slot.  HYP-PF-008 must
        # never infer swap/displacement behavior from the frozen legacy path.
        occupied_slot3 = (
            ITEM_MOVE_CAPTURE_REQUEST_PC[:23]
            + b"\x03\x00\x00\x00"
            + ITEM_MOVE_CAPTURE_REQUEST_PC[27:]
        )
        variants = [
            V111_MERGE_REQUEST_PC,
            ITEM_MOVE_CAPTURE_REQUEST_PC + b"\x00",
            occupied_slot3,
        ]
        wrong_envelope = self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC)
        wrong_envelope.outer_version = 1
        for value in variants:
            self.assertEqual(state.dispatch(self.legacy.parse_outer(value)), [])
        self.assertEqual(state.dispatch(wrong_envelope), [])
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_move_hypothesis_count, 0)
        self.assertIn("item_move_hypothesis_wrong_tuple_no_reply", state.events)

    def test_session_gate_stale_lease_and_cross_character_fail_closed(self):
        state, character, _ = self._merged_hypothesis_state("gates")
        before_rows = self._rows(character.id)

        baseline_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        baseline = baseline_type("gates")
        baseline.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        with self.assertRaisesRegex(PermissionError, "explicit opt-in scenario"):
            baseline.foundation.move_hypothesized_v111_slot2()
        self.assertEqual(self._rows(character.id), before_rows)
        baseline.foundation.close_connection()

        other, other_character, _ = self._state("other-account")
        with self.assertRaisesRegex(PermissionError, "stale or non-owning"):
            self.store.apply_hypothesized_v111_slot2_move(
                state.foundation.session_id, other_character.id,
            )
        self.assertEqual(other.foundation.backpack, INITIAL_BACKPACK)
        other.foundation.close_connection()

        sid = state.foundation.session_id
        state.foundation.close_connection()
        with self.assertRaisesRegex(PermissionError, "stale or non-owning"):
            self.store.apply_hypothesized_v111_slot2_move(sid, character.id)
        self.assertEqual(self._rows(character.id), before_rows)

    def test_concurrent_repository_calls_have_exactly_one_success(self):
        state, character, _ = self._merged_hypothesis_state("concurrent")
        sid = state.foundation.session_id
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(
                lambda _value: self.store.apply_hypothesized_v111_slot2_move(
                    sid, character.id,
                ),
                range(2),
            ))
        self.assertEqual(results.count(None), 1)
        self.assertEqual(
            sum(result == HYPOTHESIZED_V111_SLOT2_BACKPACK for result in results),
            1,
        )

    def test_cli_requires_explicit_existing_database_and_modes_are_exclusive(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        base = [
            sys.executable, "-m", "pirateforce_foundation.app",
            "--item-move-hypothesis-scenario", str(SCENARIO_PATH),
            "--self-test-only",
        ]
        missing = subprocess.run(
            base, cwd=ROOT, env=env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(missing.returncode, 2)
        self.assertIn("requires an explicit existing --db", missing.stderr)

        absent = Path(self.tmp.name) / "absent.sqlite3"
        result = subprocess.run(
            [*base[:-1], "--db", str(absent), base[-1]], cwd=ROOT, env=env,
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(absent.exists())

        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                item_move_capture_scenario=object(),
                item_move_hypothesis_scenario=self.scenario,
            )


if __name__ == "__main__":
    unittest.main()
