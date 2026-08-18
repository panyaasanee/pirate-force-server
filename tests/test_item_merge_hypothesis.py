"""Runtime wire hookup for the HYP-PF-018 occupied-destination merge.

Every test drives the real dispatch path.  The merge activates only under
the dedicated ``item_move_hypothesis_v111_occupied_merge`` profile of the
existing item-move opt-in flag: under that profile an occupied destination
whose occupant carries the same template and identical variant bytes merges
the governed source stack into the occupying target (one atomic persistence
transaction, merge delta response composed before commit and queued only
after post-state re-validation), while free destinations keep the exact
HYP-PF-010 lane and the same-slot request keeps its silent no-op.  The
response structure is byte-identical to the live-accepted V111 stack-merge
response, and the exact V111 case (identity 3 into identity 1 at slot 0)
reproduces the frozen V141 golden byte for byte.  A different-template
occupant, the reversed merge direction (whose post-state falls outside the
governed allowlist), and every mode without the merge profile keep the
pinned fail-closed silence.  Nothing here is production behavior:
``production_allowed`` stays false in every profile.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.inventory import (  # noqa: E402
    INITIAL_BACKPACK,
    MERGED_V111_BACKPACK,
    V111_MERGE_REQUEST_PC,
    make_item_merge_delta_response,
    make_item_move_delta_response,
    merge_known_item_into_occupied_slot,
    move_known_item_to_free_slot,
)
from pirateforce_foundation.item_move_capture import (  # noqa: E402
    ITEM_MOVE_CAPTURE_REQUEST_PC,
)
from pirateforce_foundation.item_move_hypothesis import (  # noqa: E402
    load_item_move_hypothesis_scenario,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
MOVE_SCENARIO_PATH = ROOT / "scenarios" / "item_move_hypothesis_v111_slot2.json"
SWAP_SCENARIO_PATH = (
    ROOT / "scenarios" / "item_move_hypothesis_v111_occupied_swap.json"
)
MERGE_SCENARIO_PATH = (
    ROOT / "scenarios" / "item_move_hypothesis_v111_occupied_merge.json"
)


def _move_request_pc(destination_slot: int, item_identity: int) -> bytes:
    """Rebuild the accepted 36-byte ItemOperate move shape for other targets."""
    pc = (
        ITEM_MOVE_CAPTURE_REQUEST_PC[:23]
        + struct.pack("<I", destination_slot)
        + ITEM_MOVE_CAPTURE_REQUEST_PC[27:28]
        + struct.pack("<Q", item_identity)
    )
    assert len(pc) == len(ITEM_MOVE_CAPTURE_REQUEST_PC)
    return pc


class MergeScenarioLoaderTests(unittest.TestCase):
    def test_merge_profile_loads_with_occupied_merge_enabled(self):
        scenario = load_item_move_hypothesis_scenario(MERGE_SCENARIO_PATH)
        self.assertEqual(
            scenario.scenario_id, "item_move_hypothesis_v111_occupied_merge",
        )
        self.assertEqual(scenario.hypothesis_id, "HYP-PF-018")
        self.assertFalse(scenario.occupied_swap)
        self.assertTrue(scenario.occupied_merge)

    def test_other_profiles_keep_their_flags(self):
        move = load_item_move_hypothesis_scenario(MOVE_SCENARIO_PATH)
        self.assertFalse(move.occupied_swap)
        self.assertFalse(move.occupied_merge)
        swap = load_item_move_hypothesis_scenario(SWAP_SCENARIO_PATH)
        self.assertTrue(swap.occupied_swap)
        self.assertFalse(swap.occupied_merge)

    def test_any_field_drift_is_rejected(self):
        base = json.loads(MERGE_SCENARIO_PATH.read_text(encoding="utf-8"))
        variants = []
        production = dict(base)
        production["production_allowed"] = True
        variants.append(production)
        hypothesis = dict(base)
        hypothesis["hypothesis_id"] = "HYP-PF-017"
        variants.append(hypothesis)
        policy = dict(base, entry=dict(base["entry"]))
        policy["entry"]["destination_policy"] = (
            "occupied_by_different_identity_swaps"
        )
        variants.append(policy)
        different = dict(base, entry=dict(base["entry"]))
        different["entry"]["different_template_policy"] = "swap"
        variants.append(different)
        extra = dict(base)
        extra["extra_key"] = 1
        variants.append(extra)
        nonclaims = dict(base)
        nonclaims["nonclaims"] = list(base["nonclaims"])[:-1]
        variants.append(nonclaims)
        for variant in variants:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "drift.json"
                path.write_text(json.dumps(variant), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_item_move_hypothesis_scenario(path)


class MergePureTransitionTests(unittest.TestCase):
    def test_exact_v111_direction_reproduces_the_merged_snapshot(self):
        after, merged, consumed = merge_known_item_into_occupied_slot(
            INITIAL_BACKPACK, 3, 0,
        )
        self.assertEqual(after, MERGED_V111_BACKPACK)
        self.assertEqual(
            (merged.identity, merged.quantity, merged.slot), (1, 2, 0),
        )
        self.assertEqual(
            (consumed.identity, consumed.quantity, consumed.slot), (3, 1, 2),
        )

    def test_merge_lands_wherever_the_target_sits(self):
        relocated, _ = move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 7)
        after, merged, consumed = merge_known_item_into_occupied_slot(
            relocated, 3, 7,
        )
        self.assertEqual(
            (merged.identity, merged.quantity, merged.slot), (1, 2, 7),
        )
        self.assertEqual(consumed.identity, 3)
        self.assertEqual(
            sorted((item.identity, item.slot) for item in after.items),
            [(1, 7), (2, 1), (4, 3)],
        )

    def test_unowned_cases_raise(self):
        with self.assertRaises(KeyError):
            merge_known_item_into_occupied_slot(INITIAL_BACKPACK, 99, 0)
        with self.assertRaises(ValueError):
            merge_known_item_into_occupied_slot(INITIAL_BACKPACK, 3, 40)
        with self.assertRaises(ValueError):
            merge_known_item_into_occupied_slot(INITIAL_BACKPACK, 3, 2)
        with self.assertRaises(LookupError):
            merge_known_item_into_occupied_slot(INITIAL_BACKPACK, 3, 9)
        # Different template fails closed.
        with self.assertRaises(ValueError):
            merge_known_item_into_occupied_slot(INITIAL_BACKPACK, 3, 1)
        # The reversed direction would leave identity 3 as the survivor,
        # which is outside the governed allowlist, so it fails closed too.
        relocated, _ = move_known_item_to_free_slot(INITIAL_BACKPACK, 3, 5)
        with self.assertRaises(ValueError):
            merge_known_item_into_occupied_slot(relocated, 1, 5)
        # The merged snapshot holds no same-template pair at all.
        with self.assertRaises(ValueError):
            merge_known_item_into_occupied_slot(MERGED_V111_BACKPACK, 2, 0)


class MergeResponseCodecTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)

    def test_exact_v111_case_is_byte_equal_to_the_frozen_golden(self):
        _after, merged, consumed = merge_known_item_into_occupied_slot(
            INITIAL_BACKPACK, 3, 0,
        )
        pc, frame = make_item_merge_delta_response(
            self.legacy, merged, consumed.identity,
        )
        golden_pc, golden_frame = (
            self.legacy.make_item_operate_stack_merge_success()
        )
        self.assertEqual(pc, golden_pc)
        self.assertEqual(frame, golden_frame)

    def test_other_slots_reuse_the_same_structure(self):
        relocated, _ = move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 7)
        _after, merged, consumed = merge_known_item_into_occupied_slot(
            relocated, 3, 7,
        )
        pc, frame = make_item_merge_delta_response(
            self.legacy, merged, consumed.identity,
        )
        _golden_pc, golden_frame = (
            self.legacy.make_item_operate_stack_merge_success()
        )
        self.assertEqual(len(frame), len(golden_frame))
        self.assertNotEqual(frame, golden_frame)

    def test_codec_guards(self):
        _after, merged, consumed = merge_known_item_into_occupied_slot(
            INITIAL_BACKPACK, 3, 0,
        )
        with self.assertRaises(TypeError):
            make_item_merge_delta_response(self.legacy, None, 3)
        with self.assertRaises(ValueError):
            make_item_merge_delta_response(
                self.legacy, merged, merged.identity,
            )
        single = INITIAL_BACKPACK.items[0]
        with self.assertRaises(ValueError):
            make_item_merge_delta_response(self.legacy, single, 3)


class SessionGateTests(unittest.TestCase):
    def test_merge_flag_requires_move_flag(self):
        with self.assertRaises(ValueError):
            FoundationSession(
                None, None, "gate",
                allow_hypothesized_item_move=False,
                allow_hypothesized_item_merge=True,
            )


class ItemMergeRuntimeTests(unittest.TestCase):
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
        self.merge_scenario = load_item_move_hypothesis_scenario(
            MERGE_SCENARIO_PATH
        )
        self.move_scenario = load_item_move_hypothesis_scenario(
            MOVE_SCENARIO_PATH
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, scenario, create=True, ready=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            item_move_hypothesis_scenario=scenario,
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

    def _rows(self, character_id):
        with self.store.connect() as db:
            return db.execute(
                "SELECT item_identity,template_id,quantity,slot,raw_u8_38,"
                "raw_u8_39,detail_present FROM character_backpack_items "
                "WHERE character_id=? ORDER BY item_identity",
                (character_id,),
            ).fetchall()

    def test_occupied_merge_commits_before_merge_delta_response(self):
        state, character, _ = self._state("merge", scenario=self.merge_scenario)
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
        expected_pc, expected_frame = (
            self.legacy.make_item_operate_stack_merge_success()
        )
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(0, 3)))
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            actions[0][0],
            "HYP_PF_018_ITEM_MERGE_ID3_INTO_ID1_AT_SLOT0_QTY2_COMMITTED",
        )
        self.assertEqual(actions[0][1], expected_pc)
        self.assertEqual(actions[0][2], expected_frame)
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
        self.assertEqual(
            [
                (row["item_identity"], row["quantity"], row["slot"])
                for row in self._rows(character.id)
            ],
            [(1, 2, 0), (2, 1, 1), (4, 1, 3)],
        )
        self.assertEqual(state.item_merge_occupied_count, 1)
        self.assertIn(
            "item_merge_occupied_committed_before_composed_response",
            state.events,
        )

    def test_exact_v111_request_bytes_converge_with_the_frozen_lane(self):
        state, character, _ = self._state("bytes", scenario=self.merge_scenario)
        expected_pc, expected_frame = (
            self.legacy.make_item_operate_stack_merge_success()
        )
        actions = state.dispatch(self.legacy.parse_outer(V111_MERGE_REQUEST_PC))
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][1], expected_pc)
        self.assertEqual(actions[0][2], expected_frame)
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)

    def test_merge_lands_at_a_relocated_target_slot(self):
        state, character, _ = self._state("slot7", scenario=self.merge_scenario)
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(7, 1)))
        self.assertEqual(
            actions[0][0], "HYP_PF_010_ITEM_MOVE_ID1_TO_FREE_SLOT7_COMMITTED",
        )
        relocated, _ = move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 7)
        _after, merged, consumed = merge_known_item_into_occupied_slot(
            relocated, 3, 7,
        )
        expected_pc, expected_frame = make_item_merge_delta_response(
            self.legacy, merged, consumed.identity,
        )
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(7, 3)))
        self.assertEqual(
            actions[0][0],
            "HYP_PF_018_ITEM_MERGE_ID3_INTO_ID1_AT_SLOT7_QTY2_COMMITTED",
        )
        self.assertEqual(actions[0][1], expected_pc)
        self.assertEqual(actions[0][2], expected_frame)
        self.assertEqual(
            [
                (row["item_identity"], row["quantity"], row["slot"])
                for row in self._rows(character.id)
            ],
            [(1, 2, 7), (2, 1, 1), (4, 1, 3)],
        )

    def test_free_slot_move_under_merge_profile_stays_hyp_pf_010(self):
        state, character, _ = self._state("free", scenario=self.merge_scenario)
        _after, moved = move_known_item_to_free_slot(INITIAL_BACKPACK, 4, 7)
        expected_pc, expected_frame = make_item_move_delta_response(
            self.legacy, moved,
        )
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(7, 4)))
        self.assertEqual(
            actions[0][0], "HYP_PF_010_ITEM_MOVE_ID4_TO_FREE_SLOT7_COMMITTED",
        )
        self.assertEqual(actions[0][1], expected_pc)
        self.assertEqual(actions[0][2], expected_frame)
        self.assertEqual(state.item_move_generalized_count, 1)
        self.assertEqual(state.item_merge_occupied_count, 0)

    def test_same_slot_under_merge_profile_stays_silent_noop(self):
        state, character, _ = self._state("noop", scenario=self.merge_scenario)
        before_rows = self._rows(character.id)
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(_move_request_pc(0, 1))), [],
        )
        self.assertIn(
            "item_move_generalized_same_slot_noop_no_reply", state.events,
        )
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_merge_occupied_count, 0)

    def test_different_template_occupied_fails_closed(self):
        state, character, _ = self._state("diff", scenario=self.merge_scenario)
        before_rows = self._rows(character.id)
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(_move_request_pc(1, 1))), [],
        )
        self.assertIn(
            "item_merge_occupied_fail_closed_no_reply_ValueError",
            state.events,
        )
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_merge_occupied_count, 0)

    def test_reversed_direction_fails_closed_outside_the_allowlist(self):
        state, character, _ = self._state("reverse", scenario=self.merge_scenario)
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(5, 3)))
        self.assertEqual(
            actions[0][0], "HYP_PF_010_ITEM_MOVE_ID3_TO_FREE_SLOT5_COMMITTED",
        )
        before_rows = self._rows(character.id)
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(_move_request_pc(5, 1))), [],
        )
        self.assertIn(
            "item_merge_occupied_fail_closed_no_reply_ValueError",
            state.events,
        )
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_merge_occupied_count, 0)

    def test_occupied_under_move_profile_keeps_pinned_fail_closed_silence(self):
        state, character, _ = self._state("pinned", scenario=self.move_scenario)
        before_rows = self._rows(character.id)
        with mock.patch.object(
            self.store, "merge_backpack_item_into_occupied_slot",
            side_effect=AssertionError("merge repository must not be reached"),
        ):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(_move_request_pc(0, 3))),
                [],
            )
        self.assertIn(
            "item_move_generalized_fail_closed_no_reply_FileExistsError",
            state.events,
        )
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_merge_occupied_count, 0)

    def test_wrong_sequence_fails_closed_before_any_repository_call(self):
        state, character, _ = self._state(
            "sequence", scenario=self.merge_scenario, ready=False,
        )
        before_rows = self._rows(character.id)
        with mock.patch.object(
            self.store, "merge_backpack_item_into_occupied_slot",
            side_effect=AssertionError("repository must not be reached"),
        ):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(_move_request_pc(0, 3))),
                [],
            )
        self.assertIn(
            "item_move_generalized_wrong_sequence_no_reply", state.events,
        )
        self.assertEqual(self._rows(character.id), before_rows)

    def test_repository_failure_rolls_back_and_queues_nothing(self):
        state, character, _ = self._state("rollback", scenario=self.merge_scenario)
        before_rows = self._rows(character.id)
        with mock.patch.object(
            self.store, "_load_backpack",
            side_effect=[INITIAL_BACKPACK, RuntimeError("after validation")],
        ):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(_move_request_pc(0, 3))),
                [],
            )
        failures = [
            event for event in state.events
            if event.startswith("item_merge_occupied_repository_failure_no_reply_")
        ]
        self.assertEqual(len(failures), 1)
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
        self.assertEqual(state.item_merge_occupied_count, 0)

    def test_merge_and_reconnect_projection(self):
        state, character, _ = self._state("durable", scenario=self.merge_scenario)
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(0, 3)))
        self.assertEqual(
            actions[0][0],
            "HYP_PF_018_ITEM_MERGE_ID3_INTO_ID1_AT_SLOT0_QTY2_COMMITTED",
        )
        state.foundation.close_connection()
        reconnect, again, _ = self._state(
            "durable", scenario=self.merge_scenario, create=False,
        )
        self.assertEqual(again.id, character.id)
        self.assertEqual(reconnect.foundation.backpack, MERGED_V111_BACKPACK)


if __name__ == "__main__":
    unittest.main()
