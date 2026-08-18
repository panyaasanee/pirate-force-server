"""Runtime wire hookup for the HYP-PF-010 generalized free-slot move (M4).

Every test drives the real dispatch path behind the existing item-move opt-in
scenario.  The exact HYP-PF-008 request keeps its frozen lane; every other
well-formed ItemOperate tuple is owned by the generalized lane, which commits
one governed free-slot move atomically before replying and fails closed with
no reply and no write for occupied, unknown, out-of-range, same-slot, wrong
operation, and wrong-sequence attempts.  Nothing here is production behavior:
``production_allowed`` stays false and the lane is unreachable without the
opt-in scenario.
"""
from __future__ import annotations

from dataclasses import replace
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
    make_backpack_attr,
    make_item_move_delta_response,
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
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "item_move_hypothesis_v111_slot2.json"


def _move_request_pc(destination_slot: int, item_identity: int) -> bytes:
    """Rebuild the accepted 36-byte ItemOperate move shape for other targets.

    Only the little-endian ``value32`` dword and identity qword differ from the
    captured original-client request; every envelope byte is preserved.
    """
    pc = (
        ITEM_MOVE_CAPTURE_REQUEST_PC[:23]
        + struct.pack("<I", destination_slot)
        + ITEM_MOVE_CAPTURE_REQUEST_PC[27:28]
        + struct.pack("<Q", item_identity)
    )
    assert len(pc) == len(ITEM_MOVE_CAPTURE_REQUEST_PC)
    return pc


class ItemMoveGeneralizedRuntimeTests(unittest.TestCase):
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
        # The request builder must reproduce the captured request byte-for-byte
        # for the tracked destination so variants only differ where intended.
        self.assertEqual(_move_request_pc(2, 1), ITEM_MOVE_CAPTURE_REQUEST_PC)

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, hypothesis=True, create=True, ready=True):
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

    def _merged_state(self, login):
        baseline, character, _ = self._state(login, hypothesis=False)
        actions = baseline.dispatch(self.legacy.parse_outer(V111_MERGE_REQUEST_PC))
        self.assertEqual(
            actions[0][0],
            "FOUNDATION_V111_ITEM_STACK_ID3_INTO_ID1_QTY2_COMMITTED",
        )
        baseline.foundation.close_connection()
        state, same, actions = self._state(login, create=False)
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

    def test_generic_move_commits_before_one_composed_response(self):
        state, character, _ = self._merged_state("generic")
        expected_backpack, moved = move_known_item_to_free_slot(
            MERGED_V111_BACKPACK, 2, 5,
        )
        expected_pc, expected_frame = make_item_move_delta_response(
            self.legacy, moved,
        )
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(5, 2)))
        self.assertEqual(actions, [(
            "HYP_PF_010_ITEM_MOVE_ID2_TO_FREE_SLOT5_COMMITTED",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertEqual(state.foundation.backpack, expected_backpack)
        self.assertEqual(state.item_move_generalized_count, 1)
        self.assertEqual(state.item_move_hypothesis_count, 0)
        self.assertIn(
            "item_move_generalized_committed_before_composed_response",
            state.events,
        )
        self.assertEqual(
            [(row["item_identity"], row["slot"]) for row in self._rows(character.id)],
            [(1, 0), (2, 5), (4, 3)],
        )
        self.assertEqual(
            self.store.get_backpack(state.foundation.session_id, character.id),
            expected_backpack,
        )
        # A second distinct governed move in the same session also commits:
        # the generalization is per-transition, not once-per-character.
        second = state.dispatch(self.legacy.parse_outer(_move_request_pc(1, 2)))
        self.assertEqual(second[0][0], "HYP_PF_010_ITEM_MOVE_ID2_TO_FREE_SLOT1_COMMITTED")
        self.assertEqual(state.item_move_generalized_count, 2)
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)

    def test_initial_contents_are_governed_and_tracked_lane_still_guards(self):
        state, character, _ = self._state("initial-contents")
        self.assertEqual(state.foundation.backpack, INITIAL_BACKPACK)
        actions = state.dispatch(self.legacy.parse_outer(_move_request_pc(7, 3)))
        self.assertEqual(actions[0][0], "HYP_PF_010_ITEM_MOVE_ID3_TO_FREE_SLOT7_COMMITTED")
        self.assertEqual(
            [(row["item_identity"], row["slot"]) for row in self._rows(character.id)],
            [(1, 0), (2, 1), (3, 7), (4, 3)],
        )
        # The frozen HYP-PF-008 lane requires the exact merged pre-state and
        # must stay silent here rather than inherit the generalized authority.
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(ITEM_MOVE_CAPTURE_REQUEST_PC)),
            [],
        )
        self.assertEqual(state.item_move_hypothesis_count, 0)
        self.assertIn(
            "item_move_hypothesis_wrong_current_state_no_reply", state.events,
        )

    def test_fail_closed_paths_write_nothing_and_never_reply(self):
        state, character, _ = self._merged_state("fail-closed")
        before_rows = self._rows(character.id)
        cases = [
            (_move_request_pc(1, 2), "item_move_generalized_same_slot_noop_no_reply"),
            (_move_request_pc(3, 1), "item_move_generalized_fail_closed_no_reply_FileExistsError"),
            (_move_request_pc(5, 99), "item_move_generalized_fail_closed_no_reply_KeyError"),
            (_move_request_pc(40, 1), "item_move_generalized_fail_closed_no_reply_ValueError"),
        ]
        for pc, expected_event in cases:
            self.assertEqual(state.dispatch(self.legacy.parse_outer(pc)), [])
            self.assertIn(expected_event, state.events)
        wrong_operation = (
            ITEM_MOVE_CAPTURE_REQUEST_PC[:21]
            + b"\x03"
            + _move_request_pc(5, 2)[22:]
        )
        self.assertEqual(state.dispatch(self.legacy.parse_outer(wrong_operation)), [])
        self.assertIn(
            "item_move_generalized_wrong_operation_no_reply", state.events,
        )
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_move_generalized_count, 0)

    def test_wrong_sequence_fails_closed_before_any_repository_call(self):
        state, character, _ = self._merged_state("sequence")
        state.runtime_ack_sent = False
        before_rows = self._rows(character.id)
        with mock.patch.object(
            self.store, "move_backpack_item_to_free_slot",
            side_effect=AssertionError("repository must not be reached"),
        ):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(_move_request_pc(5, 2))),
                [],
            )
        self.assertIn(
            "item_move_generalized_wrong_sequence_no_reply", state.events,
        )
        self.assertEqual(self._rows(character.id), before_rows)

    def test_repository_failure_rolls_back_and_queues_nothing(self):
        state, character, _ = self._merged_state("rollback")
        before_rows = self._rows(character.id)
        with mock.patch.object(
            self.store, "_load_backpack",
            side_effect=[MERGED_V111_BACKPACK, RuntimeError("after validation")],
        ):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(_move_request_pc(5, 2))),
                [],
            )
        self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
        self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_move_generalized_count, 0)
        self.assertTrue(any(
            event.startswith("item_move_generalized_repository_failure_no_reply_")
            for event in state.events
        ))

    def test_exact_tracked_request_keeps_the_frozen_hyp_pf_008_lane(self):
        state, _, _ = self._merged_state("frozen-lane")
        actions = state.dispatch(self.legacy.parse_outer(
            ITEM_MOVE_CAPTURE_REQUEST_PC
        ))
        self.assertEqual(
            actions[0][0],
            "HYP_PF_008_ITEM_MOVE_ID1_SLOT0_TO_FREE_SLOT2_COMMITTED",
        )
        self.assertEqual(state.item_move_hypothesis_count, 1)
        self.assertEqual(state.item_move_generalized_count, 0)

    def test_moved_state_reconnect_is_opt_in_and_baseline_fails_closed(self):
        state, character, _ = self._merged_state("reconnect")
        self.assertEqual(len(state.dispatch(
            self.legacy.parse_outer(_move_request_pc(5, 2))
        )), 1)
        moved_backpack = state.foundation.backpack
        state.foundation.close_connection()

        reconnected, same, actions = self._state(
            "reconnect", create=False,
        )
        self.assertEqual(same.id, character.id)
        self.assertEqual(reconnected.foundation.backpack, moved_backpack)
        self.assertEqual(
            actions[0][1].count(make_backpack_attr(self.legacy, moved_backpack)),
            1,
        )
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
        self.assertIn("foundation_start_game_rejected_no_reply", baseline.events)
        with self.assertRaisesRegex(PermissionError, "explicit opt-in scenario"):
            baseline.foundation.move_backpack_item_to_free_slot(2, 5)

    def test_same_slot_noop_is_idempotent_under_replay(self):
        """Repeated same-slot requests stay a silent no-op with no write.

        The occupied-destination swap milestone proved same-slot silence once
        under the swap profile.  This locks the ``same_slot_noop`` capability
        under the default free-slot profile and adds the replay dimension the
        coverage note requires: no response, no write, and no replay effect
        across several identities and repeats.  The generalized move count
        never advances because ``move_known_item_to_free_slot`` returns the
        exact same-slot ``None`` every time.
        """
        state, character, _ = self._merged_state("same-slot-replay")
        before_rows = self._rows(character.id)
        # MERGED_V111_BACKPACK holds identity 1 at slot 0, identity 2 at slot 1
        # and identity 4 at slot 3.  Each request targets an item's own slot.
        same_slot_cases = [(0, 1), (1, 2), (3, 4)]
        for destination_slot, item_identity in same_slot_cases:
            # The pure transition is the exact same-slot no-op signal.
            self.assertIsNone(move_known_item_to_free_slot(
                MERGED_V111_BACKPACK, item_identity, destination_slot,
            ))
            for _ in range(3):
                self.assertEqual(state.dispatch(self.legacy.parse_outer(
                    _move_request_pc(destination_slot, item_identity)
                )), [])
                self.assertEqual(
                    state.events[-1],
                    "item_move_generalized_same_slot_noop_no_reply",
                )
                self.assertEqual(state.foundation.backpack, MERGED_V111_BACKPACK)
                self.assertEqual(self._rows(character.id), before_rows)
        self.assertEqual(state.item_move_generalized_count, 0)
        self.assertEqual(state.item_move_hypothesis_count, 0)


class ItemMoveIsolationInvariantTests(unittest.TestCase):
    """Prove the two independent layers that isolate a generalized free-slot
    move to the session's own selected character.

    Layer 1 (wire): parse_item_operate_req decodes exactly one operation byte,
    one destination dword, and one item-identity qword, and rejects any
    trailing bytes.  There is no owner/character field a client could send, so
    no request can name another character.

    Layer 2 (persistence): every Backpack read and write is guarded by
    _require_selected_session, whose predicate accepts only the open session
    that has itself selected that character within its own account.

    These are the offline companions to the MOVE-ISOLATION-001 headless probe,
    which proves the same invariant to the wire and the DB on a live server.
    Nothing here is production behavior; the lane stays opt-in only.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.pos = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _make_character(self, account_id, name, identity_lo):
        def build(_selector):
            return b"\x00", b"\x00", identity_lo, 0
        return self.store.create_character(
            account_id, name, name.casefold(), f"fp-{name}", build, self.pos,
        )

    def _select_own(self, account_id, selector):
        sid = self.store.open_session(account_id)
        self.store.select_character(sid, selector)
        return sid

    # ---- Layer 1: the wire carries no owner field --------------------------

    def test_item_operate_request_decodes_exactly_three_unowned_fields(self):
        parsed = self.legacy.parse_outer(_move_request_pc(4, 1))
        fields = self.legacy.parse_item_operate_req(parsed)
        # Exactly (operation, destination_slot, item_identity): no fourth
        # field by which a request could address another character.
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields, (4, 4, 1))

    def test_item_operate_request_rejects_trailing_owner_bytes(self):
        # One extra tagged dword on the nested payload -- the only place a
        # smuggled owner id could ride -- must be refused, not silently used.
        parsed = self.legacy.parse_outer(_move_request_pc(4, 1))
        tampered = replace(
            parsed,
            nested_payload=parsed.nested_payload
            + self.legacy.u32tag(0x14, 0xDEADBEEF),
        )
        with self.assertRaises(ValueError):
            self.legacy.parse_item_operate_req(tampered)

    # ---- Layer 2: the persistence guard ------------------------------------

    def test_guard_accepts_owning_selected_session(self):
        aid = self.store.ensure_account("acct-own")
        ch = self._make_character(aid, "alpha", 0x11110001)
        sid = self.store.open_session(aid)
        self.store.select_character(sid, ch.selector)
        # No raise; returns exactly the seeded INITIAL Backpack.
        self.assertEqual(self.store.get_backpack(sid, ch.id), INITIAL_BACKPACK)

    def test_guard_rejects_foreign_account_character_on_read_and_write(self):
        aid1 = self.store.ensure_account("acct-a")
        aid2 = self.store.ensure_account("acct-b")
        ch1 = self._make_character(aid1, "alpha", 0x22220001)
        ch2 = self._make_character(aid2, "bravo", 0x33330001)
        sid1 = self.store.open_session(aid1)
        self.store.select_character(sid1, ch1.selector)
        with self.assertRaises(PermissionError):
            self.store.get_backpack(sid1, ch2.id)
        # The generalized move write path is guarded by the same predicate and
        # never touches a foreign character's rows.
        with self.assertRaises(PermissionError):
            self.store.move_backpack_item_to_free_slot(sid1, ch2.id, 1, 4)
        # The foreign character's own owning session still reads it intact.
        self.assertEqual(
            self.store.get_backpack(
                self._select_own(aid2, ch2.selector), ch2.id,
            ),
            INITIAL_BACKPACK,
        )

    def test_guard_rejects_unselected_sibling_character(self):
        aid = self.store.ensure_account("acct-sib")
        ch1 = self._make_character(aid, "alpha", 0x44440001)
        ch2 = self._make_character(aid, "bravo", 0x44440002)
        sid = self.store.open_session(aid)
        self.store.select_character(sid, ch1.selector)
        # A session reaches only the character it has itself selected, even a
        # sibling in the same account.
        with self.assertRaises(PermissionError):
            self.store.get_backpack(sid, ch2.id)

    def test_guard_rejects_closed_session(self):
        aid = self.store.ensure_account("acct-closed")
        ch = self._make_character(aid, "alpha", 0x55550001)
        sid = self.store.open_session(aid)
        self.store.select_character(sid, ch.selector)
        self.store.close_session(sid)
        with self.assertRaises(PermissionError):
            self.store.get_backpack(sid, ch.id)


if __name__ == "__main__":
    unittest.main()
