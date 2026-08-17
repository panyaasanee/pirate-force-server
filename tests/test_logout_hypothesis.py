"""Runtime wire hookup for the HYP-PF-012 acknowledged logout.

Every test drives the real dispatch path behind the logout opt-in scenario.
The two captured LogoutVital requests (subcode 01 exit-game, subcode 03
return-to-character-select; R38/R40 decode) are acknowledged with a designed
echo composition only after the session lease commits ``closed_at``; wrong
payloads, wrong sequences, replays after the ack, and every frame without the
opt-in scenario fail closed with no reply and no write.  Nothing here is
production behavior: ``production_allowed`` stays false and the lane is
unreachable without the opt-in scenario.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    LOGOUT_ACK_FRAME_SHA256,
    LOGOUT_ACK_PC_SHA256,
    LOGOUT_REQUEST_PAYLOADS,
    LOGOUT_REQUEST_PCS,
    LOGOUT_VITAL_ID,
    load_logout_hypothesis_scenario,
    make_logout_ack_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "logout_hypothesis_ack_echo.json"


class LogoutHypothesisRuntimeTests(unittest.TestCase):
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
        self.scenario = load_logout_hypothesis_scenario(SCENARIO_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, logout=True, ready=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            logout_hypothesis_scenario=self.scenario if logout else None,
        )
        state = state_type(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
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

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    def _logout_parsed(self, subcode):
        return self.legacy.parse_outer(LOGOUT_REQUEST_PCS[subcode])

    def test_subcode01_ack_after_clean_close(self):
        state, _character = self._state("logout01")
        session_id = state.foundation.session_id
        self.assertIsNone(self._session_closed_at(session_id))
        expected_pc, expected_frame = make_logout_ack_response(self.legacy, 1)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(actions, [(
            "HYP_PF_012_LOGOUT_SUBCODE01_ACK_AFTER_CLEAN_CLOSE",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertTrue(state.logout_acknowledged)
        self.assertEqual(state.logout_ack_count, 1)
        self.assertIn(
            "logout_hypothesis_subcode01_session_closed_before_ack",
            state.events,
        )
        # The lease is already closed; the socket teardown close is a no-op.
        self.assertFalse(state.foundation.close_connection())

    def test_subcode03_ack_after_clean_close(self):
        state, _character = self._state("logout03")
        session_id = state.foundation.session_id
        expected_pc, expected_frame = make_logout_ack_response(self.legacy, 3)
        actions = state.dispatch(self._logout_parsed(3))
        self.assertEqual(actions, [(
            "HYP_PF_012_LOGOUT_SUBCODE03_ACK_AFTER_CLEAN_CLOSE",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertIn(
            "logout_hypothesis_subcode03_session_closed_before_ack",
            state.events,
        )

    def test_connection_is_silent_after_acknowledged_logout(self):
        state, _character = self._state("logout-silent")
        self.assertEqual(len(state.dispatch(self._logout_parsed(1))), 1)
        rx_before = state.rx_frames
        # A duplicate logout, an empty runtime poll, and a login-shaped frame
        # are all counted and ignored after the acknowledged logout.
        for pc in (
            LOGOUT_REQUEST_PCS[1],
            LOGOUT_REQUEST_PCS[3],
            self.legacy._synthetic_client_login_pc(),
        ):
            self.assertEqual(state.dispatch(self.legacy.parse_outer(pc)), [])
        self.assertEqual(state.rx_frames, rx_before + 3)
        self.assertEqual(state.logout_ack_count, 1)
        self.assertEqual(
            state.events.count("logout_hypothesis_post_ack_frame_no_reply"), 3,
        )

    def test_wrong_payload_and_wrong_envelope_fail_closed(self):
        state, _character = self._state("logout-wrong")
        session_id = state.foundation.session_id
        # Subcode 02 was never captured; every other byte stays exact.
        subcode02 = LOGOUT_REQUEST_PCS[1].replace(
            LOGOUT_REQUEST_PAYLOADS[1], bytes.fromhex(
                "0802080014000000001400000000"
            ),
        )
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(subcode02)), [],
        )
        self.assertIn("logout_hypothesis_wrong_payload_no_reply", state.events)
        # Truncated payload fails the exact comparison the same way.
        truncated = LOGOUT_REQUEST_PCS[1][:-2]
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(truncated)), [],
        )
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)

    def test_wrong_sequence_fails_closed(self):
        state, _character = self._state("logout-seq", ready=False)
        session_id = state.foundation.session_id
        self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_wrong_sequence_no_reply", state.events,
        )
        self.assertIsNone(self._session_closed_at(session_id))

    def test_without_scenario_nothing_changes(self):
        state, _character = self._state("logout-off", logout=False)
        session_id = state.foundation.session_id
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(
            [a for a in actions if a[0].startswith("HYP_PF_012")], [],
        )
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)
        self.assertEqual(state.logout_ack_count, 0)

    def test_composed_ack_is_pinned_echo(self):
        for subcode in (1, 3):
            pc, frame = make_logout_ack_response(self.legacy, subcode)
            self.assertEqual(len(pc), 36)
            self.assertEqual(len(frame), 46)
            self.assertIn(LOGOUT_REQUEST_PAYLOADS[subcode], pc)
            expected_pc, expected_frame = self.legacy.make_runtime_vitals([
                (LOGOUT_VITAL_ID, 0, LOGOUT_REQUEST_PAYLOADS[subcode]),
            ])
            self.assertEqual(pc, expected_pc)
            self.assertEqual(frame, expected_frame)
        with self.assertRaises(ValueError):
            make_logout_ack_response(self.legacy, 2)

    def test_scenario_allowlist_is_exact(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        data["production_allowed"] = True
        tampered = Path(self.tmp.name) / "tampered.json"
        tampered.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_logout_hypothesis_scenario(tampered)

    def test_logout_and_item_move_scenarios_are_mutually_exclusive(self):
        from pirateforce_foundation.item_move_hypothesis import (
            load_item_move_hypothesis_scenario,
        )
        item_scenario = load_item_move_hypothesis_scenario(
            ROOT / "scenarios" / "item_move_hypothesis_v111_slot2.json"
        )
        with self.assertRaises(ValueError):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                item_move_hypothesis_scenario=item_scenario,
                logout_hypothesis_scenario=self.scenario,
            )

    def test_pinned_hashes_cover_both_subcodes(self):
        self.assertEqual(set(LOGOUT_ACK_PC_SHA256), {1, 3})
        self.assertEqual(set(LOGOUT_ACK_FRAME_SHA256), {1, 3})


if __name__ == "__main__":
    unittest.main()
