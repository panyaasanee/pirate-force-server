"""Runtime wire hookup for the HYP-PF-017 occupied-destination swap.

Every test drives the real dispatch path.  The swap activates only under the
dedicated ``item_move_hypothesis_v111_occupied_swap`` profile of the existing
item-move opt-in flag: under that profile an occupied destination swaps the
governed source item with the different occupying identity (one atomic
persistence transaction, two-item delta response composed before commit and
queued only after post-state re-validation), while free destinations keep the
exact HYP-PF-010 lane and the same-slot request keeps its silent no-op.
Under the original profile -- and with no scenario at all -- occupied
destinations stay fail-closed exactly as pinned by HYP-PF-010.  Nothing here
is production behavior: ``production_allowed`` stays false in both profiles.
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
    make_item_move_delta_response,
    make_item_swap_delta_response,
    move_known_item_to_free_slot,
    swap_known_item_with_occupied_slot,
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


class SwapScenarioLoaderTests(unittest.TestCase):
    def test_swap_profile_loads_with_occupied_swap_enabled(self):
        scenario = load_item_move_hypothesis_scenario(SWAP_SCENARIO_PATH)
        self.assertTrue(scenario.occupied_swap)
        self.assertEqual(scenario.hypothesis_id, "HYP-PF-017")
        self.assertEqual(
            scenario.scenario_id, "item_move_hypothesis_v111_occupied_swap",
        )

    def test_move_profile_still_loads_without_swap(self):
        scenario = load_item_move_hypothesis_scenario(MOVE_SCENARIO_PATH)
        self.assertFalse(scenario.occupied_swap)
        self.assertEqual(scenario.hypothesis_id, "HYP-PF-008")

    def test_any_field_drift_is_rejected(self):
        data = json.loads(SWAP_SCENARIO_PATH.read_text(encoding="utf-8"))
        drifts = [
            {**data, "production_allowed": True},
            {**data, "test_only": False},
            {**data, "hypothesis_id": "HYP-PF-999"},
            {**data, "entry": {**data["entry"], "destination_policy": "displace"}},
            {**data, "extra": 1},
        ]
        removed = dict(data)
        del removed["nonclaims"]
        drifts.append(removed)
        for drifted in drifts:
            with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False
            ) as handle:
                json.dump(drifted, handle)
                path = handle.name
            with self.assertRaises(ValueError):
                load_item_move_hypothesis_scenario(path)


class SwapPureTransitionTests(unittest.TestCase):
    def test_swap_exchanges_only_the_two_slots(self):
        after, moved, displaced = swap_known_item_with_occupied_slot(
            INITIAL_BACKPACK, 1, 2,
        )
        self.assertEqual(
            [(item.identity, item.slot) for item in after.items],
            [(1, 2), (2, 1), (3, 0), (4, 3)],
        )
        self.assertEqual((moved.identity, moved.slot), (1, 2))
        self.assertEqual((displaced.identity, displaced.slot), (3, 0))
        self.assertEqual(moved.quantity, 1)
        self.assertEqual(displaced.template_id, 2600001)

    def test_swap_on_merged_contents(self):
        after, moved, displaced = swap_known_item_with_occupied_slot(
            MERGED_V111_BACKPACK, 1, 1,
        )
        self.assertEqual(
            [(item.identity, item.slot) for item in after.items],
            [(1, 1), (2, 0), (4, 3)],
        )
        self.assertEqual(moved.quantity, 2)

    def test_unowned_cases_raise(self):
        with self.assertRaises(KeyError):
            swap_known_item_with_occupied_slot(INITIAL_BACKPACK, 99, 1)
        with self.assertRaises(ValueError):
            swap_known_item_with_occupied_slot(INITIAL_BACKPACK, 1, 0)
        with self.assertRaises(LookupError):
            swap_known_item_with_occupied_slot(INITIAL_BACKPACK, 1, 7)
        with self.assertRaises(ValueError):
            swap_known_item_with_occupied_slot(INITIAL_BACKPACK, 1, 40)
        with self.assertRaises(ValueError):
            swap_known_item_with_occupied_slot(INITIAL_BACKPACK, 1, -1)


class SwapResponseCodecTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)

    def test_two_item_delta_structure(self):
        legacy = self.legacy
        _, moved, displaced = swap_known_item_with_occupied_slot(
            INITIAL_BACKPACK, 1, 1,
        )
        pc, frame = make_item_swap_delta_response(legacy, moved, displaced)
        single_pc, _ = make_item_move_delta_response(
            legacy,
            move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 5)[1],
        )
        item_wire_size = 8 + 1 + 4 + 1 + 2 + 1 + 2 + 1 + 3 + 3
        # One extra complete ItemAttr payload distinguishes the two shapes.
        self.assertEqual(len(pc), len(single_pc) + item_wire_size)
        # The two ItemAttr identity qwords appear in order: moved, displaced.
        moved_tag = legacy.qwordtag(0x32, moved.identity)
        displaced_tag = legacy.qwordtag(0x32, displaced.identity)
        self.assertIn(moved_tag, pc)
        self.assertIn(displaced_tag, pc)
        self.assertLess(pc.index(moved_tag), pc.index(displaced_tag))
        # The first collection count word says 2.
        base_prefix = (
            legacy.u8tag(0x0B, 0xFF)
            + legacy.qwordtag(0x32, 0)
            + legacy.u16tag(0x0F, 2)
        )
        self.assertIn(base_prefix, pc)
        self.assertEqual(frame[-len(pc):], pc)

    def test_codec_guards(self):
        _, moved, displaced = swap_known_item_with_occupied_slot(
            INITIAL_BACKPACK, 1, 1,
        )
        with self.assertRaises(ValueError):
            make_item_swap_delta_response(self.legacy, moved, moved)
        with self.assertRaises(TypeError):
            make_item_swap_delta_response(self.legacy, moved, object())


class SessionGateTests(unittest.TestCase):
    def test_swap_flag_requires_move_flag(self):
        with self.assertRaises(ValueError):
            FoundationSession.__new__(FoundationSession).__init__(
                None, None, "x",
                allow_hypothesized_item_move=False,
                allow_hypothesized_item_swap=True,
            )


class ItemSwapRuntimeTests(unittest.TestCase):
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
        self.swap_scenario = load_item_move_hypothesis_scenario(
            SWAP_SCENARIO_PATH
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

    def test_occupied_swap_commits_before_two_item_response(self):
        state, character, _ = self._state("swap", scenario=self.swap_scenario)
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
        # The (slot2, id1) tuple is the exact tracked HYP-PF-008 request and
        # keeps its frozen lane; this test therefore swaps id1 into slot1.
        expected_backpack, moved, displaced = (
            swap_known_item_with_occupied_slot(INITIAL_BACKPACK, 1, 1)
        )
        expected_pc, expected_frame = make_item_swap_delta_response(
            self.legacy, moved, displaced,
        )
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(1, 1)))
        self.assertEqual(actions, [(
            "HYP_PF_017_ITEM_SWAP_ID1_TO_SLOT1_DISPLACING_ID2_TO_SLOT0"
            "_COMMITTED",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertEqual(state.foundation.backpack, expected_backpack)
        self.assertEqual(state.item_swap_occupied_count, 1)
        self.assertEqual(state.item_move_generalized_count, 0)
        self.assertIn(
            "item_swap_occupied_committed_before_composed_response",
            state.events,
        )
        self.assertEqual(
            [(row["item_identity"], row["slot"]) for row in self._rows(character.id)],
            [(1, 1), (2, 0), (3, 2), (4, 3)],
        )
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            expected_backpack,
        )
        # Swapping back in the same session also commits: the authority is
        # per-transition, not once-per-character.
        second = state.dispatch(self.legacy.parse_outer(_move_request_pc(0, 1)))
        self.assertEqual(
            second[0][0],
            "HYP_PF_017_ITEM_SWAP_ID1_TO_SLOT0_DISPLACING_ID2_TO_SLOT1"
            "_COMMITTED",
        )
        self.assertEqual(state.item_swap_occupied_count, 2)
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
        # The exact tracked request itself still keeps its frozen HYP-PF-008
        # lane under the swap profile (wrong pre-state here: silence).
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(_move_request_pc(2, 1))), [],
        )
        self.assertIn(
            "item_move_hypothesis_wrong_current_state_no_reply", state.events,
        )
        self.assertEqual(state.item_swap_occupied_count, 2)

    def test_free_slot_move_under_swap_profile_stays_hyp_pf_010(self):
        state, character, _ = self._state("free", scenario=self.swap_scenario)
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(7, 3)))
        self.assertEqual(
            actions[0][0], "HYP_PF_010_ITEM_MOVE_ID3_TO_FREE_SLOT7_COMMITTED",
        )
        self.assertEqual(state.item_move_generalized_count, 1)
        self.assertEqual(state.item_swap_occupied_count, 0)

    def test_same_slot_under_swap_profile_stays_silent_noop(self):
        state, character, _ = self._state("noop", scenario=self.swap_scenario)
        before_rows = self._rows(character.id)
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(_move_request_pc(0, 1))), [],
        )
        self.assertIn(
            "item_move_generalized_same_slot_noop_no_reply", state.events,
        )
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_swap_occupied_count, 0)

    def test_unknown_and_out_of_range_stay_fail_closed_under_swap_profile(self):
        state, character, _ = self._state("guards", scenario=self.swap_scenario)
        before_rows = self._rows(character.id)
        cases = [
            (_move_request_pc(5, 99), "item_move_generalized_fail_closed_no_reply_KeyError"),
            (_move_request_pc(40, 1), "item_move_generalized_fail_closed_no_reply_ValueError"),
        ]
        for pc, expected_event in cases:
            self.assertEqual(state.dispatch(self.legacy.parse_outer(pc)), [])
            self.assertIn(expected_event, state.events)
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_swap_occupied_count, 0)

    def test_occupied_under_move_profile_keeps_pinned_fail_closed_silence(self):
        state, character, _ = self._state("pinned", scenario=self.move_scenario)
        before_rows = self._rows(character.id)
        with mock.patch.object(
            self.store, "swap_backpack_item_with_occupied_slot",
            side_effect=AssertionError("swap repository must not be reached"),
        ):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(_move_request_pc(1, 1))),
                [],
            )
        self.assertIn(
            "item_move_generalized_fail_closed_no_reply_FileExistsError",
            state.events,
        )
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_swap_occupied_count, 0)

    def test_wrong_sequence_fails_closed_before_any_repository_call(self):
        state, character, _ = self._state(
            "sequence", scenario=self.swap_scenario, ready=False,
        )
        before_rows = self._rows(character.id)
        with mock.patch.object(
            self.store, "swap_backpack_item_with_occupied_slot",
            side_effect=AssertionError("repository must not be reached"),
        ):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(_move_request_pc(1, 1))),
                [],
            )
        self.assertIn(
            "item_move_generalized_wrong_sequence_no_reply", state.events,
        )
        self.assertEqual(self._rows(character.id), before_rows)

    def test_repository_failure_rolls_back_and_queues_nothing(self):
        state, character, _ = self._state("rollback", scenario=self.swap_scenario)
        before_rows = self._rows(character.id)
        with mock.patch.object(
            self.store, "_load_backpack",
            side_effect=[INITIAL_BACKPACK, RuntimeError("after validation")],
        ):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(_move_request_pc(1, 1))),
                [],
            )
        failures = [
            event for event in state.events
            if event.startswith("item_swap_occupied_repository_failure_no_reply_")
        ]
        self.assertEqual(len(failures), 1)
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
        self.assertEqual(state.item_swap_occupied_count, 0)

    def test_merged_contents_swap_and_reconnect_projection(self):
        baseline, character, _ = self._state("merged", scenario=None)
        actions = baseline.dispatch(self.legacy.parse_outer(V111_MERGE_REQUEST_PC))
        self.assertEqual(
            actions[0][0],
            "FOUNDATION_V111_ITEM_STACK_ID3_INTO_ID1_QTY2_COMMITTED",
        )
        baseline.foundation.close_connection()
        state, same, _ = self._state(
            "merged", scenario=self.swap_scenario, create=False,
        )
        self.assertEqual(same.id, character.id)
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(1, 1)))
        self.assertEqual(
            actions[0][0],
            "HYP_PF_017_ITEM_SWAP_ID1_TO_SLOT1_DISPLACING_ID2_TO_SLOT0"
            "_COMMITTED",
        )
        self.assertEqual(
            [(row["item_identity"], row["slot"]) for row in self._rows(character.id)],
            [(1, 1), (2, 0), (4, 3)],
        )
        # A fresh session projects the swapped state back from the store.
        state.foundation.close_connection()
        reconnect, again, _ = self._state(
            "merged", scenario=self.swap_scenario, create=False,
        )
        self.assertEqual(again.id, character.id)
        self.assertEqual(
            [(item.identity, item.slot) for item in reconnect.foundation.backpack.items],
            [(1, 1), (2, 0), (4, 3)],
        )


if __name__ == "__main__":
    unittest.main()
