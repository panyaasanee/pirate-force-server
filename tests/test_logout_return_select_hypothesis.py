"""Runtime hookup for the HYP-PF-028 return-select-server logout.

LOGOUT-RETURN-SELECT-001 is GT-033 variant B.  Round-100 static RE (agent D)
proved that echoing any vital inside GSCN_RunTimeProtocolRes is consumed by the
inbound actor-vital reconcile pass 0x446F30 and can never transition the
client, and it named ReturnSelectServerVital (0x709E) the strongest candidate
for the "return to character select" direction while finding no client code
that consumes it -- so whether sending it transitions the client is undecidable
statically and is exactly the queued attended A/B.  This lane answers the two
pinned captured LogoutVital forms (subcode 01 exit-game, subcode 03
return-to-character-select) with the designed 0x709E vital FIRST -- a
well-formed body composed from the client serializer 0x5e69f0's own field
layout with every field zero (no client producer exists for the values) --
then the byte-identical hash-pinned PF-012 ack, then the PF-013 clean socket
close at 250 ms.  The session lease commits ``closed_at`` before any response
byte is queued.  Wrong payloads, wrong sequences, replays after the ack, a
missing close lever, and every frame without the opt-in scenario fail closed
with no reply and no write, and ``production_allowed`` stays false everywhere.
No byte of this profile has ever been shown to a client.
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

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    LOGOUT_ACK_FRAME_SHA256,
    LOGOUT_ACK_PC_SHA256,
    LOGOUT_CLOSE_DELAY_MS,
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_REQUEST_PCS,
    LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
    RETURN_SELECT_SERVER_BODY,
    RETURN_SELECT_SERVER_BODY_SIZE,
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
    RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_PC_SIZE,
    RETURN_SELECT_SERVER_VITAL_ID,
    load_logout_hypothesis_scenario,
    make_logout_ack_response,
    make_return_select_server_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
RETURN_SELECT_SCENARIO_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_return_select_server.json"
)
ECHO_SCENARIO_PATH = ROOT / "scenarios" / "logout_hypothesis_ack_echo.json"
CLOSE_SCENARIO_PATH = ROOT / "scenarios" / "logout_hypothesis_ack_close.json"
WORLDINFO_SCENARIO_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_worldinfo_first.json"
)


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest().upper()


class _RecordingTimerFactory:
    def __init__(self) -> None:
        self.scheduled: list[tuple[float, object]] = []

    def __call__(self, delay_seconds, callback):
        self.scheduled.append((delay_seconds, callback))
        return self

    def fire_all(self) -> None:
        for _delay, callback in self.scheduled:
            callback()


class _RecordingCloser:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


class LogoutReturnSelectRuntimeTests(unittest.TestCase):
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
        self.scenario = load_logout_hypothesis_scenario(
            RETURN_SELECT_SCENARIO_PATH
        )
        self.timer_factory = _RecordingTimerFactory()
        self.closer = _RecordingCloser()

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, scenario=None, ready=True, attach_closer=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            logout_hypothesis_scenario=(
                scenario if scenario is not None else self.scenario
            ),
            close_timer_factory=self.timer_factory,
        )
        state = state_type(login)
        if attach_closer:
            state.attach_transport_socket_closer(self.closer)
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
        return state

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    def _logout_parsed(self, subcode):
        return self.legacy.parse_outer(LOGOUT_REQUEST_PCS[subcode])

    # --- scenario / profile --------------------------------------------

    def test_scenario_profile_fields(self):
        self.assertEqual(
            self.scenario.response_policy,
            LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
        )
        self.assertEqual(
            self.scenario.post_ack_action, LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        )
        self.assertEqual(self.scenario.close_delay_ms, LOGOUT_CLOSE_DELAY_MS)
        self.assertEqual(self.scenario.hypothesis_id, "HYP-PF-028")

    # --- the designed 0x709E body has full serializer provenance --------

    def test_return_select_body_is_client_serializer_layout(self):
        # field1 +0x14 tag 0x08 u8 ; field2 +0x18 tag 0x32 8-byte scalar ;
        # field3 +0x20 tag 0x44 std::string (empty).  Every tag byte is the
        # client serializer 0x5e69f0's own; the values are the honest zero
        # default because 0x709E has no client producer.
        self.assertEqual(len(RETURN_SELECT_SERVER_BODY), 16)
        self.assertEqual(RETURN_SELECT_SERVER_BODY_SIZE, 16)
        self.assertEqual(RETURN_SELECT_SERVER_BODY[0], 0x08)
        self.assertEqual(RETURN_SELECT_SERVER_BODY[1], 0x00)
        self.assertEqual(RETURN_SELECT_SERVER_BODY[2], 0x32)
        self.assertEqual(RETURN_SELECT_SERVER_BODY[3:11], b"\x00" * 8)
        self.assertEqual(RETURN_SELECT_SERVER_BODY[11], 0x44)
        self.assertEqual(RETURN_SELECT_SERVER_BODY[12:], b"\x00\x00\x00\x00")

    def test_composed_response_is_pinned(self):
        pc, frame = make_return_select_server_response(self.legacy)
        self.assertEqual(len(pc), RETURN_SELECT_SERVER_RESPONSE_PC_SIZE)
        self.assertEqual(len(frame), RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE)
        # Res v4 envelope, one vital, nested id 0x709E version 0, the 16-byte
        # body, trailing derived-class change mask 0B 00.
        self.assertEqual(
            pc[:15],
            bytes.fromhex("129D6E140000000008040B02120100"),
        )
        # nested id 0x709E as u16tag 0x12 -> 12 9E 70
        self.assertEqual(pc[15:18], bytes.fromhex("129E70"))
        self.assertEqual(pc[18:20], bytes.fromhex("0B00"))  # nested version 0
        self.assertEqual(pc[20:20 + 16], RETURN_SELECT_SERVER_BODY)
        self.assertEqual(pc[-2:], bytes.fromhex("0B00"))
        self.assertEqual(_sha(pc), RETURN_SELECT_SERVER_RESPONSE_PC_SHA256)
        self.assertEqual(_sha(frame), RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(RETURN_SELECT_SERVER_VITAL_ID, 0x709E)

    def test_ack_bytes_are_the_unchanged_pf012_pins(self):
        for subcode in (1, 3):
            pc, frame = make_logout_ack_response(self.legacy, subcode)
            self.assertEqual(_sha(pc), LOGOUT_ACK_PC_SHA256[subcode])
            self.assertEqual(_sha(frame), LOGOUT_ACK_FRAME_SHA256[subcode])

    # --- dispatch: response first, ack second, FIN last -----------------

    def test_subcode01_return_select_then_ack_then_close(self):
        state = self._state("rs01")
        session_id = state.foundation.session_id
        self.assertIsNone(self._session_closed_at(session_id))
        expected_rss = make_return_select_server_response(self.legacy)
        expected_ack = make_logout_ack_response(self.legacy, 1)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(actions, [
            (
                "HYP_PF_028_LOGOUT_SUBCODE01_RETURN_SELECT_SERVER_RESPONSE_FIRST",
                expected_rss[0], expected_rss[1], 0.0,
            ),
            (
                "HYP_PF_028_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE",
                expected_ack[0], expected_ack[1], 0.0,
            ),
        ])
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertTrue(state.logout_acknowledged)
        self.assertTrue(state.logout_close_scheduled)
        self.assertIn(
            "logout_hypothesis_subcode01_session_closed_before_ack",
            state.events,
        )
        self.assertIn(
            "logout_hypothesis_subcode01_return_select_response_before_ack",
            state.events,
        )
        self.assertIn(
            "logout_hypothesis_post_ack_socket_close_scheduled_250ms",
            state.events,
        )
        self.assertEqual(
            [delay for delay, _cb in self.timer_factory.scheduled],
            [LOGOUT_CLOSE_DELAY_MS / 1000.0],
        )
        self.assertEqual(self.closer.calls, 0)
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)

    def test_subcode03_return_select_then_ack_then_close(self):
        state = self._state("rs03")
        session_id = state.foundation.session_id
        expected_rss = make_return_select_server_response(self.legacy)
        expected_ack = make_logout_ack_response(self.legacy, 3)
        actions = state.dispatch(self._logout_parsed(3))
        self.assertEqual([label for label, *_ in actions], [
            "HYP_PF_028_LOGOUT_SUBCODE03_RETURN_SELECT_SERVER_RESPONSE_FIRST",
            "HYP_PF_028_LOGOUT_SUBCODE03_ACK_THEN_SERVER_SOCKET_CLOSE",
        ])
        self.assertEqual(actions[0][1:], (expected_rss[0], expected_rss[1], 0.0))
        self.assertEqual(actions[1][1:], (expected_ack[0], expected_ack[1], 0.0))
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertEqual(len(self.timer_factory.scheduled), 1)
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)

    def test_both_subcodes_emit_the_same_pinned_return_select_frame(self):
        # The 0x709E frame is fixed (no per-connection input) so subcode 01
        # and 03 must emit byte-identical return-select bytes.
        s1 = self._state("rs-same-1")
        a1 = s1.dispatch(self._logout_parsed(1))
        s3 = self._state("rs-same-3")
        a3 = s3.dispatch(self._logout_parsed(3))
        self.assertEqual(a1[0][1], a3[0][1])
        self.assertEqual(_sha(a1[0][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256)
        self.assertEqual(_sha(a3[0][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256)

    # --- fail-closed guards --------------------------------------------

    def test_wrong_payload_and_sequence_fail_closed(self):
        state = self._state("rs-wrong")
        session_id = state.foundation.session_id
        subcode02 = LOGOUT_REQUEST_PCS[1].replace(
            bytes.fromhex("0801080014000000001400000000"),
            bytes.fromhex("0802080014000000001400000000"),
        )
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(subcode02)), [],
        )
        self.assertIn("logout_hypothesis_wrong_payload_no_reply", state.events)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(self.timer_factory.scheduled, [])

        sequence_state = self._state("rs-wrong-seq", ready=False)
        self.assertEqual(sequence_state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_wrong_sequence_no_reply",
            sequence_state.events,
        )
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_missing_transport_closer_fails_closed_with_no_write(self):
        state = self._state("rs-nolever", attach_closer=False)
        session_id = state.foundation.session_id
        self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_close_unavailable_no_reply", state.events,
        )
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_already_closed_lease_gets_no_response(self):
        state = self._state("rs-closed")
        self.assertTrue(state.foundation.close_connection())
        self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_already_closed_no_reply", state.events,
        )
        self.assertFalse(state.logout_acknowledged)
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_post_ack_frames_stay_silent(self):
        state = self._state("rs-silent")
        self.assertEqual(len(state.dispatch(self._logout_parsed(1))), 2)
        rx_before = state.rx_frames
        for pc in (LOGOUT_REQUEST_PCS[1], LOGOUT_REQUEST_PCS[3]):
            self.assertEqual(state.dispatch(self.legacy.parse_outer(pc)), [])
        self.assertEqual(state.rx_frames, rx_before + 2)
        self.assertEqual(state.logout_ack_count, 1)
        self.assertEqual(
            state.events.count("logout_hypothesis_post_ack_frame_no_reply"), 2,
        )

    # --- isolation: other scenarios stay byte-identical -----------------

    def test_other_logout_scenarios_are_unaffected(self):
        for path, label in (
            (ECHO_SCENARIO_PATH,
             "HYP_PF_012_LOGOUT_SUBCODE01_ACK_AFTER_CLEAN_CLOSE"),
            (CLOSE_SCENARIO_PATH,
             "HYP_PF_013_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE"),
        ):
            scenario = load_logout_hypothesis_scenario(path)
            state = self._state(f"rs-old-{scenario.hypothesis_id}",
                                scenario=scenario)
            expected_pc, expected_frame = make_logout_ack_response(
                self.legacy, 1,
            )
            actions = state.dispatch(self._logout_parsed(1))
            self.assertEqual(
                actions, [(label, expected_pc, expected_frame, 0.0)],
            )
            # The return-select response never leaks onto other lanes.
            self.assertFalse(
                [e for e in state.events if "return_select" in e]
            )

    def test_scenario_allowlist_is_exact(self):
        data = json.loads(
            RETURN_SELECT_SCENARIO_PATH.read_text(encoding="utf-8")
        )
        loaded = load_logout_hypothesis_scenario(RETURN_SELECT_SCENARIO_PATH)
        self.assertEqual(loaded.hypothesis_id, "HYP-PF-028")
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("test_only", False),
            lambda d: d["entry"].__setitem__("close_delay_ms", 5000),
            lambda d: d["entry"].__setitem__("post_ack_action", "none"),
            lambda d: d["entry"].__setitem__("response_policy", "ack_only"),
            lambda d: d["entry"].pop("return_select_source"),
            lambda d: d["composed_responses"]["return_select_first"].__setitem__(
                "pc_sha256", "00" * 32,
            ),
            lambda d: d["composed_responses"]["return_select_first"].__setitem__(
                "vital_id", 0x1B40,
            ),
            lambda d: d["composed_responses"]["return_select_first"].__setitem__(
                "body_size", 2,
            ),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_logout_hypothesis_scenario(tampered)


if __name__ == "__main__":
    unittest.main()
