"""Runtime hookup for the HYP-PF-016 response-first logout (LOGOUT-RESP-001).

Every test drives the real dispatch path behind the worldinfo_first opt-in
scenario.  During a runtime-ready session the exact full 248-byte
GetWorldInfoVital (0x3D4B) client form is stored in connection-local memory
(no table, no write path); on the two pinned captured LogoutVital forms the
server queues the designed 0x3D4B echo response FIRST (the stored payload
verbatim inside the accepted RuntimeRes v4 envelope, mirrored collection
count 3, trailing derived-class mask 0B 00), then the byte-identical
hash-pinned PF-012 ack, then the PF-013 clean socket close at 250 ms.  The
session lease commits ``closed_at`` before any response byte is queued.
Sessions that never produced a full 0x3D4B payload get silence: no reply,
no write, no ack fallback.  The two pre-existing logout scenarios remain
byte-identical, and ``production_allowed`` stays false everywhere.
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
    LOGOUT_RESPONSE_POLICY_WORLDINFO_FIRST,
    WORLDINFO_FULL_PAYLOAD_SIZE,
    WORLDINFO_PROBE_PAYLOADS,
    WORLDINFO_PROBE_REQUEST_PC_SHA256,
    WORLDINFO_PROBE_RESPONSE_FRAME_SHA256,
    WORLDINFO_PROBE_RESPONSE_PC_SHA256,
    WORLDINFO_RECORD_SIZE,
    WORLDINFO_RESPONSE_FRAME_SIZE,
    WORLDINFO_RESPONSE_PC_SIZE,
    is_full_worldinfo_payload,
    load_logout_hypothesis_scenario,
    make_logout_ack_response,
    make_worldinfo_first_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
WORLDINFO_SCENARIO_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_worldinfo_first.json"
)
ECHO_SCENARIO_PATH = ROOT / "scenarios" / "logout_hypothesis_ack_echo.json"
CLOSE_SCENARIO_PATH = ROOT / "scenarios" / "logout_hypothesis_ack_close.json"

# Captured request container prefixes (R40 oracle decode; the full-form
# envelope is 20 bytes: GSCN_RunTimeProtocolReq v0, mask 0x02, count 3,
# nested 0x3D4B v0).
WORLDINFO_FULL_PC_PREFIX = bytes.fromhex(
    "126F6E140000000008000B02120300124B3D0B00"
)
WORLDINFO_EMPTY_PC = bytes.fromhex(
    "126F6E140000000008000B02120100124B3D0B000B00"
)

GT002 = WORLDINFO_PROBE_PAYLOADS["capture_gt002"]
HYP001 = WORLDINFO_PROBE_PAYLOADS["capture_item_move_hyp001"]


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


class LogoutWorldinfoFirstRuntimeTests(unittest.TestCase):
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
        self.scenario = load_logout_hypothesis_scenario(WORLDINFO_SCENARIO_PATH)
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

    def _worldinfo_parsed(self, payload):
        return self.legacy.parse_outer(WORLDINFO_FULL_PC_PREFIX + payload)

    def _logout_parsed(self, subcode):
        return self.legacy.parse_outer(LOGOUT_REQUEST_PCS[subcode])

    def _store_worldinfo(self, state, payload):
        self.assertEqual(state.dispatch(self._worldinfo_parsed(payload)), [])
        self.assertIn(
            "logout_worldinfo_full_form_stored_no_reply", state.events,
        )
        self.assertEqual(state.worldinfo_last_payload, payload)

    def test_scenario_profile_fields(self):
        self.assertEqual(
            self.scenario.response_policy,
            LOGOUT_RESPONSE_POLICY_WORLDINFO_FIRST,
        )
        self.assertEqual(
            self.scenario.post_ack_action, LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        )
        self.assertEqual(self.scenario.close_delay_ms, LOGOUT_CLOSE_DELAY_MS)

    def test_subcode01_worldinfo_response_then_ack_then_close(self):
        state = self._state("wi01")
        session_id = state.foundation.session_id
        self._store_worldinfo(state, GT002)
        self.assertIsNone(self._session_closed_at(session_id))
        expected_info = make_worldinfo_first_response(self.legacy, GT002)
        expected_ack = make_logout_ack_response(self.legacy, 1)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(actions, [
            (
                "HYP_PF_016_LOGOUT_SUBCODE01_WORLDINFO_RESPONSE_FIRST",
                expected_info[0], expected_info[1], 0.0,
            ),
            (
                "HYP_PF_016_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE",
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
            "logout_hypothesis_subcode01_worldinfo_response_before_ack",
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

    def test_subcode03_with_second_probe_payload(self):
        state = self._state("wi03")
        session_id = state.foundation.session_id
        self._store_worldinfo(state, HYP001)
        expected_info = make_worldinfo_first_response(self.legacy, HYP001)
        expected_ack = make_logout_ack_response(self.legacy, 3)
        actions = state.dispatch(self._logout_parsed(3))
        self.assertEqual([label for label, *_ in actions], [
            "HYP_PF_016_LOGOUT_SUBCODE03_WORLDINFO_RESPONSE_FIRST",
            "HYP_PF_016_LOGOUT_SUBCODE03_ACK_THEN_SERVER_SOCKET_CLOSE",
        ])
        self.assertEqual(actions[0][1:], (expected_info[0], expected_info[1], 0.0))
        self.assertEqual(actions[1][1:], (expected_ack[0], expected_ack[1], 0.0))
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertEqual(len(self.timer_factory.scheduled), 1)
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)

    def test_latest_stored_payload_is_echoed(self):
        state = self._state("wi-latest")
        self._store_worldinfo(state, GT002)
        self._store_worldinfo(state, HYP001)
        self.assertEqual(state.worldinfo_stored_count, 2)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(len(actions), 2)
        expected_info = make_worldinfo_first_response(self.legacy, HYP001)
        self.assertEqual(actions[0][1], expected_info[0])
        self.assertEqual(
            _sha(actions[0][2]),
            WORLDINFO_PROBE_RESPONSE_FRAME_SHA256["capture_item_move_hyp001"],
        )

    def test_composed_response_is_pinned_mirror_echo(self):
        for probe, payload in WORLDINFO_PROBE_PAYLOADS.items():
            pc, frame = make_worldinfo_first_response(self.legacy, payload)
            self.assertEqual(len(pc), WORLDINFO_RESPONSE_PC_SIZE)
            self.assertEqual(len(frame), WORLDINFO_RESPONSE_FRAME_SIZE)
            # Res v4 envelope, mirrored collection count 3, nested 0x3D4B v0.
            self.assertEqual(
                pc[:20],
                bytes.fromhex("129D6E140000000008040B02120300124B3D0B00"),
            )
            # The stored payload is echoed verbatim; the tail is the proven
            # derived-class change mask (the DELETE-SOFT-002 lesson).
            self.assertEqual(pc[20:20 + WORLDINFO_FULL_PAYLOAD_SIZE], payload)
            self.assertEqual(pc[-2:], bytes.fromhex("0B00"))
            self.assertEqual(_sha(pc), WORLDINFO_PROBE_RESPONSE_PC_SHA256[probe])
            self.assertEqual(
                _sha(frame), WORLDINFO_PROBE_RESPONSE_FRAME_SHA256[probe],
            )
            self.assertEqual(
                _sha(WORLDINFO_FULL_PC_PREFIX + payload),
                WORLDINFO_PROBE_REQUEST_PC_SHA256[probe],
            )
            self.assertEqual(frame, self.legacy.frame_pc(pc))
        with self.assertRaises(ValueError):
            make_worldinfo_first_response(self.legacy, GT002[:-1])
        with self.assertRaises(ValueError):
            make_worldinfo_first_response(self.legacy, bytes.fromhex("0B00"))

    def test_ack_bytes_are_the_unchanged_pf012_pins(self):
        for subcode in (1, 3):
            pc, frame = make_logout_ack_response(self.legacy, subcode)
            self.assertEqual(_sha(pc), LOGOUT_ACK_PC_SHA256[subcode])
            self.assertEqual(_sha(frame), LOGOUT_ACK_FRAME_SHA256[subcode])

    def test_logout_without_stored_worldinfo_fails_closed(self):
        state = self._state("wi-none")
        session_id = state.foundation.session_id
        self.assertIsNone(state.worldinfo_last_payload)
        self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_worldinfo_missing_no_reply", state.events,
        )
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)
        self.assertFalse(state.logout_close_scheduled)
        self.assertEqual(self.timer_factory.scheduled, [])
        self.assertEqual(self.closer.calls, 0)

    def test_empty_form_is_never_stored(self):
        state = self._state("wi-empty")
        parsed = self.legacy.parse_outer(WORLDINFO_EMPTY_PC)
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn(
            "logout_worldinfo_empty_form_no_store_no_reply", state.events,
        )
        self.assertIsNone(state.worldinfo_last_payload)
        self.assertEqual(state.dispatch(self._logout_parsed(3)), [])
        self.assertIn(
            "logout_hypothesis_worldinfo_missing_no_reply", state.events,
        )

    def test_malformed_full_forms_are_never_stored(self):
        state = self._state("wi-malformed")
        truncated = GT002[:-1]
        extended = GT002 + b"\x00"
        diverging = (
            GT002[:WORLDINFO_RECORD_SIZE]
            + bytes([GT002[WORLDINFO_RECORD_SIZE] ^ 0xFF])
            + GT002[WORLDINFO_RECORD_SIZE + 1:]
        )
        # Identical records that leave the pinned skeleton (a non-float byte
        # flipped in BOTH records) must be rejected by the skeleton check.
        skeleton_broken = bytes(
            value ^ 0xFF if offset in (0, WORLDINFO_RECORD_SIZE) else value
            for offset, value in enumerate(GT002)
        )
        bad_tail = GT002[:-1] + b"\x01"
        self.assertFalse(is_full_worldinfo_payload(truncated))
        self.assertFalse(is_full_worldinfo_payload(extended))
        self.assertFalse(is_full_worldinfo_payload(diverging))
        self.assertFalse(is_full_worldinfo_payload(skeleton_broken))
        self.assertFalse(is_full_worldinfo_payload(bad_tail))
        for payload in (truncated, diverging, skeleton_broken, bad_tail):
            self.assertEqual(
                state.dispatch(self._worldinfo_parsed(payload)), [],
            )
        self.assertIsNone(state.worldinfo_last_payload)
        self.assertEqual(state.worldinfo_stored_count, 0)
        self.assertEqual(
            state.events.count("logout_worldinfo_wrong_payload_no_store_no_reply"),
            4,
        )
        # A float-slot variation inside the pinned skeleton is a lawful form.
        varied = bytearray(GT002)
        for offset in (58, 59, 60, 61, 58 + WORLDINFO_RECORD_SIZE,
                       59 + WORLDINFO_RECORD_SIZE, 60 + WORLDINFO_RECORD_SIZE,
                       61 + WORLDINFO_RECORD_SIZE):
            varied[offset] ^= 0x5A
        self.assertTrue(is_full_worldinfo_payload(bytes(varied)))

    def test_worldinfo_outside_runtime_ready_is_not_stored(self):
        state = self._state("wi-seq", ready=False)
        self.assertEqual(state.dispatch(self._worldinfo_parsed(GT002)), [])
        self.assertIn(
            "logout_worldinfo_wrong_sequence_no_store_no_reply", state.events,
        )
        self.assertIsNone(state.worldinfo_last_payload)

    def test_wrong_logout_payload_and_sequence_still_fail_closed(self):
        state = self._state("wi-wrong")
        session_id = state.foundation.session_id
        self._store_worldinfo(state, GT002)
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

        sequence_state = self._state("wi-wrong-seq", ready=False)
        self.assertEqual(sequence_state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_wrong_sequence_no_reply",
            sequence_state.events,
        )
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_missing_transport_closer_fails_closed_with_no_write(self):
        state = self._state("wi-nolever", attach_closer=False)
        session_id = state.foundation.session_id
        self._store_worldinfo(state, GT002)
        self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_close_unavailable_no_reply", state.events,
        )
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_already_closed_lease_gets_no_response(self):
        state = self._state("wi-closed")
        self._store_worldinfo(state, GT002)
        self.assertTrue(state.foundation.close_connection())
        self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_already_closed_no_reply", state.events,
        )
        self.assertFalse(state.logout_acknowledged)
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_post_ack_frames_stay_silent_including_worldinfo(self):
        state = self._state("wi-silent")
        self._store_worldinfo(state, GT002)
        self.assertEqual(len(state.dispatch(self._logout_parsed(1))), 2)
        rx_before = state.rx_frames
        for pc in (
            WORLDINFO_FULL_PC_PREFIX + GT002,
            LOGOUT_REQUEST_PCS[1],
            LOGOUT_REQUEST_PCS[3],
        ):
            self.assertEqual(state.dispatch(self.legacy.parse_outer(pc)), [])
        self.assertEqual(state.rx_frames, rx_before + 3)
        self.assertEqual(state.logout_ack_count, 1)
        self.assertEqual(state.worldinfo_stored_count, 1)
        self.assertEqual(
            state.events.count("logout_hypothesis_post_ack_frame_no_reply"), 3,
        )

    def test_ack_only_scenarios_are_byte_identical_and_ignore_worldinfo(self):
        for path, label in (
            (ECHO_SCENARIO_PATH,
             "HYP_PF_012_LOGOUT_SUBCODE01_ACK_AFTER_CLEAN_CLOSE"),
            (CLOSE_SCENARIO_PATH,
             "HYP_PF_013_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE"),
        ):
            scenario = load_logout_hypothesis_scenario(path)
            state = self._state(f"wi-old-{scenario.hypothesis_id}",
                                scenario=scenario)
            # 0x3D4B keeps the frozen inherited no-response path: nothing is
            # stored and no logout_worldinfo event exists on these lanes.
            state.dispatch(self._worldinfo_parsed(GT002))
            self.assertIsNone(state.worldinfo_last_payload)
            self.assertEqual(state.worldinfo_stored_count, 0)
            self.assertFalse(
                [e for e in state.events if e.startswith("logout_worldinfo")]
            )
            expected_pc, expected_frame = make_logout_ack_response(
                self.legacy, 1,
            )
            actions = state.dispatch(self._logout_parsed(1))
            self.assertEqual(
                actions, [(label, expected_pc, expected_frame, 0.0)],
            )

    def test_scenario_allowlist_is_exact(self):
        data = json.loads(
            WORLDINFO_SCENARIO_PATH.read_text(encoding="utf-8")
        )
        loaded = load_logout_hypothesis_scenario(WORLDINFO_SCENARIO_PATH)
        self.assertEqual(loaded.hypothesis_id, "HYP-PF-016")
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d["entry"].__setitem__("close_delay_ms", 5000),
            lambda d: d["entry"].__setitem__("post_ack_action", "none"),
            lambda d: d["entry"].__setitem__("response_policy", "ack_only"),
            lambda d: d["entry"].pop("worldinfo_missing_policy"),
            lambda d: d["requests"]["worldinfo_full"].__setitem__(
                "payload_size", 2,
            ),
            lambda d: d["composed_responses"]["worldinfo_first"][
                "probe_pc_sha256"
            ].__setitem__("capture_gt002", "00" * 32),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_logout_hypothesis_scenario(tampered)


if __name__ == "__main__":
    unittest.main()
