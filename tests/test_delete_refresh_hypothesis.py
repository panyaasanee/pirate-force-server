"""Runtime hookup for the HYP-PF-021 post-delete list rebuild (DELETE-REFRESH-001).

Attended GT-011 committed the soft delete, raised no error, and left the
character-select list exactly where it was.  UI-REFRESH-001 proved why from
the client image: the list lives in one buffer with no erase-by-key path, so
the 0x36DB acknowledgement can never take a row off the screen and the only
frame that can is a fresh SelectActorVital 0x36EF.

These tests drive the real dispatch path behind the new opt-in scenario and
prove, on dispatched bytes and on the database:

  1. one accepted delete request is answered by exactly TWO frames -- the
     unchanged, hash-pinned HYP-PF-015 echo ack at 0.0 s, then the list
     rebuild 0.35 s later;
  2. the rebuild is not a new composition: it is byte-identical to the
     unchanged, runtime-proven ``LegacyProjector.character_list`` projection
     over the post-delete character set, it carries vital 0x36EF version 10,
     and its record-count byte is the post-delete count;
  3. the rebuild carries the DELETE-SOFT-002 trailing derived-class change
     mask in the exact position the client's stream reader wants it (it is
     byte-equal to ``make_runtime_vitals`` over the same payload minus that
     mask), which is the failure GT-010 hit with ErrorData=28317;
  4. the deleted selector is gone from the rebuilt list, and the deterministic
     empty-list case matches its 45/55-byte hash pins;
  5. the lane fails closed as ONE unit -- wrong envelope, op 2, wrong stage,
     repository refusal and a projection that does not verify all produce no
     bytes at all, not even the ack;
  6. without the scenario nothing changes: the frame is counted and ignored,
     nothing is written, and the soft-delete gate stays shut.

No socket is opened, no server is booted and no GameClient is launched: every
test runs the dispatcher against a throwaway SQLite database.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.delete_actor_hypothesis import (  # noqa: E402
    DELETE_ACTOR_PROBE_ACK_FRAME_SHA256,
    DELETE_ACTOR_PROBE_ACK_PC_SHA256,
    DELETE_ACTOR_PROBE_NESTED_PAYLOADS,
    _login_protocol_request_pc,
)
from pirateforce_foundation.delete_refresh_hypothesis import (  # noqa: E402
    DELETE_REFRESH_ACTION_LABEL,
    DELETE_REFRESH_GAP_SECONDS,
    LIST_REBUILD_EMPTY_FRAME_SHA256,
    LIST_REBUILD_EMPTY_FRAME_SIZE,
    LIST_REBUILD_EMPTY_PC_SHA256,
    LIST_REBUILD_EMPTY_PC_SIZE,
    LIST_REBUILD_PAYLOAD_PREFIX_SIZE,
    LIST_REBUILD_PC_HEADER_SIZE,
    SELECT_ACTOR_VITAL_ID,
    SELECT_ACTOR_VITAL_VERSION,
    STATIC_ANCHORS,
    assert_selector_absent,
    list_rebuild_payload_prefix,
    list_rebuild_pc_header,
    load_delete_refresh_hypothesis_scenario,
    make_delete_actor_list_rebuild_response,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "delete_refresh_hypothesis_list_rebuild.json"
)
DELETE_SCENARIO_PATH = (
    ROOT / "scenarios" / "delete_actor_hypothesis_soft_delete.json"
)
PROBE = "op1_selector0_empty"


class DeleteRefreshHypothesisTests(unittest.TestCase):
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
        self.scenario = load_delete_refresh_hypothesis_scenario(SCENARIO_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    # --- harness --------------------------------------------------------

    def _state_type(self, *, refresh=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            delete_refresh_hypothesis_scenario=self.scenario if refresh else None,
        )

    def _char_select_state(self, login, *, refresh=True, create=False):
        state = self._state_type(refresh=refresh)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        if create:
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC
            ))
            self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        return state

    def _delete_pc(self, probe=PROBE):
        return _login_protocol_request_pc(
            self.legacy, DELETE_ACTOR_PROBE_NESTED_PAYLOADS[probe],
        )

    def _character_rows(self):
        with self.store.connect() as db:
            return db.execute(
                "SELECT id,selector,identity_lo,identity_hi,deleted_at,"
                "create_fingerprint FROM characters ORDER BY id"
            ).fetchall()

    # --- scenario allowlist ---------------------------------------------

    def test_scenario_is_opt_in_and_never_production(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertIs(data["production_allowed"], False)
        self.assertIs(data["test_only"], True)
        self.assertEqual(data["hypothesis_id"], "HYP-PF-021")
        self.assertEqual(self.scenario.hypothesis_id, "HYP-PF-021")
        self.assertEqual(self.scenario.gap_seconds, DELETE_REFRESH_GAP_SECONDS)

    def test_scenario_allowlist_is_exact(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.update(production_allowed=True),
            lambda d: d.update(test_only=False),
            lambda d: d.update(id="delete_refresh_hypothesis_other"),
            lambda d: d.update(extra_key=1),
            lambda d: d.pop("nonclaims"),
            lambda d: d["entry"].update(rebuild_gap_seconds=5.0),
            lambda d: d["entry"].update(
                rebuild_failure_policy="send_the_ack_anyway"
            ),
            lambda d: d["nonclaims"].pop(),
            lambda d: d["composed_responses"]["list_rebuild_empty"].update(
                pc_sha256="00" * 32
            ),
        ):
            broken = json.loads(json.dumps(data))
            mutate(broken)
            path = Path(self.tmp.name) / "broken.json"
            path.write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_delete_refresh_hypothesis_scenario(path)

    def test_the_delete_lane_scenario_is_not_accepted_here(self):
        with self.assertRaises(ValueError):
            load_delete_refresh_hypothesis_scenario(DELETE_SCENARIO_PATH)

    def test_the_two_delete_lanes_are_mutually_exclusive(self):
        from pirateforce_foundation.delete_actor_hypothesis import (
            load_delete_actor_hypothesis_scenario,
        )
        with self.assertRaises(ValueError):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                delete_actor_hypothesis_scenario=(
                    load_delete_actor_hypothesis_scenario(DELETE_SCENARIO_PATH)
                ),
                delete_refresh_hypothesis_scenario=self.scenario,
            )

    # --- accepted dispatch ----------------------------------------------

    def test_accepted_delete_answers_with_the_ack_then_the_list_rebuild(self):
        state = self._char_select_state("probe1", create=True)
        rows = self._character_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["deleted_at"])

        actions = state.dispatch(self.legacy.parse_outer(self._delete_pc()))
        self.assertEqual(len(actions), 2)

        ack_label, ack_pc, ack_frame, ack_delay = actions[0]
        self.assertEqual(
            ack_label,
            "HYP_PF_021_DELETE_ACTOR_SELECTOR00_SOFT_DELETE_COMMITTED",
        )
        self.assertEqual(ack_delay, 0.0)
        # The ack bytes are the UNCHANGED HYP-PF-015 composition.
        self.assertEqual(
            hashlib.sha256(ack_pc).hexdigest().upper(),
            DELETE_ACTOR_PROBE_ACK_PC_SHA256[PROBE],
        )
        self.assertEqual(
            hashlib.sha256(ack_frame).hexdigest().upper(),
            DELETE_ACTOR_PROBE_ACK_FRAME_SHA256[PROBE],
        )

        rebuild_label, rebuild_pc, rebuild_frame, rebuild_delay = actions[1]
        self.assertEqual(rebuild_label, DELETE_REFRESH_ACTION_LABEL)
        self.assertEqual(rebuild_delay, DELETE_REFRESH_GAP_SECONDS)
        self.assertEqual(len(rebuild_pc), LIST_REBUILD_EMPTY_PC_SIZE)
        self.assertEqual(len(rebuild_frame), LIST_REBUILD_EMPTY_FRAME_SIZE)
        self.assertEqual(
            hashlib.sha256(rebuild_pc).hexdigest().upper(),
            LIST_REBUILD_EMPTY_PC_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(rebuild_frame).hexdigest().upper(),
            LIST_REBUILD_EMPTY_FRAME_SHA256,
        )
        self.assertEqual(state.delete_actor_soft_delete_count, 1)
        self.assertEqual(state.delete_refresh_list_rebuild_count, 1)
        self.assertIn(
            "delete_refresh_hypothesis_selector00_committed_before_ack",
            state.events,
        )
        self.assertIn(
            "delete_refresh_hypothesis_list_rebuild_records00_after_ack",
            state.events,
        )
        self.assertIsNotNone(self._character_rows()[0]["deleted_at"])

    def test_the_rebuild_is_the_unchanged_runtime_proven_projection(self):
        state = self._char_select_state("probe1", create=True)
        actions = state.dispatch(self.legacy.parse_outer(self._delete_pc()))
        rebuild_pc, rebuild_frame = actions[1][1], actions[1][2]
        # Byte-for-byte the projection the real client accepts at every login,
        # taken over the post-delete character set.
        expected_pc, expected_frame = self.projector.character_list(
            self.store.list_characters(state.foundation.account_id),
        )
        self.assertEqual(rebuild_pc, expected_pc)
        self.assertEqual(rebuild_frame, expected_frame)
        self.assertEqual(rebuild_frame, self.legacy.frame_pc(rebuild_pc))

    def test_the_rebuild_carries_vital_0x36ef_and_the_post_delete_count(self):
        state = self._char_select_state("probe1", create=True)
        actions = state.dispatch(self.legacy.parse_outer(self._delete_pc()))
        pc = actions[1][1]
        header = list_rebuild_pc_header(self.legacy)
        self.assertEqual(len(header), LIST_REBUILD_PC_HEADER_SIZE)
        self.assertTrue(pc.startswith(header))
        self.assertIn(
            self.legacy.u16tag(0x12, SELECT_ACTOR_VITAL_ID)
            + self.legacy.u8tag(0x0B, SELECT_ACTOR_VITAL_VERSION),
            header,
        )
        payload = pc[LIST_REBUILD_PC_HEADER_SIZE:]
        prefix = list_rebuild_payload_prefix(self.legacy, 0)
        self.assertEqual(len(prefix), LIST_REBUILD_PAYLOAD_PREFIX_SIZE)
        self.assertTrue(payload.startswith(prefix))
        self.assertEqual(
            self.store.list_characters(state.foundation.account_id), [],
        )

    def test_the_rebuild_carries_the_delete_soft002_trailing_mask(self):
        state = self._char_select_state("probe1", create=True)
        actions = state.dispatch(self.legacy.parse_outer(self._delete_pc()))
        pc = actions[1][1]
        payload = pc[LIST_REBUILD_PC_HEADER_SIZE:]
        self.assertTrue(payload.endswith(bytes.fromhex("0B000B00")))
        collection_pc, _frame = self.legacy.make_runtime_vitals([
            (SELECT_ACTOR_VITAL_ID, SELECT_ACTOR_VITAL_VERSION, payload[:-2]),
        ])
        self.assertEqual(collection_pc, pc)

    def test_a_one_record_list_verifies_only_against_the_count_one(self):
        """The non-empty case, on the real one-character projection.

        The bytes here are the very frame the real client accepted at login
        in every runtime pass of this project (one persisted character listed
        and selected); the lane must accept it under record_count 1 and
        refuse it under any other count, so a rebuild can never claim a
        different number of rows than it carries.
        """
        state = self._char_select_state("probe1", create=True)
        listed = self.store.list_characters(state.foundation.account_id)
        self.assertEqual(len(listed), 1)
        one_record = state.foundation.character_list()
        pc, frame = one_record
        self.assertEqual(
            make_delete_actor_list_rebuild_response(
                self.legacy, one_record, record_count=1,
            ),
            (pc, frame),
        )
        self.assertTrue(pc.startswith(list_rebuild_pc_header(self.legacy)))
        payload = pc[LIST_REBUILD_PC_HEADER_SIZE:]
        self.assertTrue(
            payload.startswith(list_rebuild_payload_prefix(self.legacy, 1))
        )
        self.assertGreater(len(pc), LIST_REBUILD_EMPTY_PC_SIZE)
        for wrong_count in (0, 2, 255):
            with self.assertRaises(RuntimeError):
                make_delete_actor_list_rebuild_response(
                    self.legacy, one_record, record_count=wrong_count,
                )
        # ...and after the delete the same lane emits the empty rebuild.
        actions = state.dispatch(self.legacy.parse_outer(self._delete_pc()))
        self.assertEqual(len(actions), 2)
        self.assertEqual(len(actions[1][1]), LIST_REBUILD_EMPTY_PC_SIZE)
        self.assertIn(
            "delete_refresh_hypothesis_list_rebuild_records00_after_ack",
            state.events,
        )

    # --- composer guards -------------------------------------------------

    def test_the_composer_refuses_anything_but_the_projection(self):
        pc, frame = self.projector.character_list([])
        # a good pair verifies
        self.assertEqual(
            make_delete_actor_list_rebuild_response(
                self.legacy, (pc, frame), record_count=0,
            ),
            (pc, frame),
        )
        # wrong declared record count
        with self.assertRaises(RuntimeError):
            make_delete_actor_list_rebuild_response(
                self.legacy, (pc, frame), record_count=1,
            )
        # the tail-less v1 composition DELETE-SOFT-002 falsified live
        tailless = pc[:-2]
        with self.assertRaises(RuntimeError):
            make_delete_actor_list_rebuild_response(
                self.legacy, (tailless, self.legacy.frame_pc(tailless)),
                record_count=0,
            )
        # a different vital riding the same envelope
        wrong_vital, wrong_frame = self.legacy.make_runtime_vitals([
            (0x36DB, 1, DELETE_ACTOR_PROBE_NESTED_PAYLOADS[PROBE]),
        ])
        with self.assertRaises(RuntimeError):
            make_delete_actor_list_rebuild_response(
                self.legacy, (wrong_vital, wrong_frame), record_count=0,
            )
        # a frame that is not frame_pc(pc)
        with self.assertRaises(RuntimeError):
            make_delete_actor_list_rebuild_response(
                self.legacy, (pc, frame + b"\x00"), record_count=0,
            )
        # malformed calls
        for bad in (None, (pc,), (pc, frame, frame), "pair"):
            with self.assertRaises(ValueError):
                make_delete_actor_list_rebuild_response(
                    self.legacy, bad, record_count=0,
                )
        for bad_count in (-1, 256, True, 0.0, "0"):
            with self.assertRaises(ValueError):
                make_delete_actor_list_rebuild_response(
                    self.legacy, (pc, frame), record_count=bad_count,
                )

    def test_the_composer_refuses_a_list_that_still_holds_the_selector(self):
        class Row:
            def __init__(self, selector):
                self.selector = selector

        self.assertEqual(assert_selector_absent([Row(1), Row(2)], 0), 2)
        with self.assertRaises(RuntimeError):
            assert_selector_absent([Row(0), Row(1)], 0)

    # --- fail closed ------------------------------------------------------

    def test_wrong_stage_and_repository_refusals_fail_closed(self):
        state = self._char_select_state("probe1", create=True)
        characters = self.store.list_characters(state.foundation.account_id)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(self._delete_pc())), [],
        )
        self.assertIn(
            "delete_refresh_hypothesis_wrong_stage_no_reply", state.events,
        )
        self.assertIsNone(self._character_rows()[0]["deleted_at"])

        fresh = self._char_select_state("probe2")
        self.assertEqual(
            fresh.dispatch(self.legacy.parse_outer(self._delete_pc())), [],
        )
        self.assertTrue(any(
            event.startswith(
                "delete_refresh_hypothesis_repository_failure_no_reply_"
            )
            for event in fresh.events
        ))

    def test_op2_and_wrong_envelope_fail_closed(self):
        state = self._char_select_state("probe1", create=True)
        op2 = _login_protocol_request_pc(
            self.legacy, bytes.fromhex("0802080014000000004400000000"),
        )
        self.assertEqual(state.dispatch(self.legacy.parse_outer(op2)), [])
        self.assertIn(
            "delete_refresh_hypothesis_op2_unproven_no_reply", state.events,
        )
        runtime_envelope = bytes(
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, 0x36DB)
            + self.legacy.u8tag(0x0B, 1)
            + DELETE_ACTOR_PROBE_NESTED_PAYLOADS[PROBE]
        )
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(runtime_envelope)), [],
        )
        self.assertIn(
            "delete_refresh_hypothesis_wrong_envelope_no_reply", state.events,
        )
        self.assertIsNone(self._character_rows()[0]["deleted_at"])

    def test_a_refused_rebuild_sends_nothing_at_all_not_even_the_ack(self):
        state = self._char_select_state("probe1", create=True)
        # Break the projection the lane is required to send: the composer must
        # refuse it, and the whole reply -- ack included -- must disappear.
        state.foundation.character_list = lambda: (b"\x00", b"\x00")
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(self._delete_pc())), [],
        )
        self.assertTrue(any(
            event.startswith("delete_refresh_hypothesis_rebuild_refused_no_reply_")
            for event in state.events
        ))
        self.assertEqual(state.delete_refresh_list_rebuild_count, 0)
        # The commit-before-any-byte ordering is unchanged and observable.
        self.assertIsNotNone(self._character_rows()[0]["deleted_at"])

    def test_without_scenario_nothing_is_written_or_replied(self):
        state = self._char_select_state("probe1", refresh=False, create=True)
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(self._delete_pc())), [],
        )
        self.assertIsNone(self._character_rows()[0]["deleted_at"])
        self.assertEqual(state.delete_refresh_list_rebuild_count, 0)
        with self.assertRaises(PermissionError):
            state.foundation.soft_delete_character(0)

    # --- static anchors ---------------------------------------------------

    def test_static_anchors_match_the_ui_refresh001_findings(self):
        self.assertEqual(STATIC_ANCHORS["character_list_erase_by_key_paths"], 0)
        self.assertEqual(STATIC_ANCHORS["select_actor_apply"], 0x5EFC40)
        self.assertEqual(STATIC_ANCHORS["character_list_fill"], 0x5DDD00)
        self.assertEqual(STATIC_ANCHORS["page_variable"], 0x0107A2C0)
        self.assertEqual(STATIC_ANCHORS["character_select_enter_hook"], 0x4BD5E0)
        self.assertEqual(
            STATIC_ANCHORS["page_variable_register_write"], 0x4BD650,
        )
        self.assertEqual(
            STATIC_ANCHORS["character_select_enter_hook_vtable_slot"], 0x10,
        )
        self.assertEqual(STATIC_ANCHORS["state_tick"], 0x4C7540)


if __name__ == "__main__":
    unittest.main()
