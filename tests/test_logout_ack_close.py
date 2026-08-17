"""Runtime hookup for the HYP-PF-013 ack + server-initiated socket close.

Every test drives the real dispatch path behind the ack_close opt-in
scenario.  The ack bytes are the unchanged hash-pinned HYP-PF-012 echo
composition; the single new lever is a delayed clean shutdown+close of the
accepted GAME socket, scheduled only after the session lease commits
``closed_at`` and the ack is queued.  Without the close_socket flag the
PF-012 behavior is byte-identical and no close is ever scheduled; without
an attached transport closer the whole lane fails closed with no write and
no reply.  ``production_allowed`` stays false everywhere.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.connection import (  # noqa: E402
    AcceptedGameSocket,
    GameConnectionBindings,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    LOGOUT_ACK_FRAME_SHA256,
    LOGOUT_ACK_PC_SHA256,
    LOGOUT_CLOSE_DELAY_MS,
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_REQUEST_PAYLOADS,
    LOGOUT_REQUEST_PCS,
    load_logout_hypothesis_scenario,
    make_logout_ack_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

import hashlib  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
CLOSE_SCENARIO_PATH = ROOT / "scenarios" / "logout_hypothesis_ack_close.json"
ECHO_SCENARIO_PATH = ROOT / "scenarios" / "logout_hypothesis_ack_echo.json"


class _RecordingTimerFactory:
    """Deterministic stand-in for the threading.Timer close schedule."""

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


class _FakeRawSocket:
    """Minimal raw-socket double recording shutdown/close ordering."""

    def __init__(self) -> None:
        self.ops: list[tuple[str, object]] = []

    def shutdown(self, how) -> None:
        self.ops.append(("shutdown", how))

    def close(self) -> None:
        self.ops.append(("close", None))


class LogoutAckCloseRuntimeTests(unittest.TestCase):
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
        self.scenario = load_logout_hypothesis_scenario(CLOSE_SCENARIO_PATH)
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

    def test_subcode01_ack_then_scheduled_clean_close(self):
        state = self._state("close01")
        session_id = state.foundation.session_id
        expected_pc, expected_frame = make_logout_ack_response(self.legacy, 1)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(actions, [(
            "HYP_PF_013_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertTrue(state.logout_acknowledged)
        self.assertTrue(state.logout_close_scheduled)
        self.assertIn(
            "logout_hypothesis_subcode01_session_closed_before_ack",
            state.events,
        )
        self.assertIn(
            "logout_hypothesis_post_ack_socket_close_scheduled_250ms",
            state.events,
        )
        # The close is scheduled at the pinned delay but has not fired yet.
        self.assertEqual(
            [delay for delay, _cb in self.timer_factory.scheduled],
            [LOGOUT_CLOSE_DELAY_MS / 1000.0],
        )
        self.assertEqual(self.closer.calls, 0)
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)

    def test_subcode03_ack_then_scheduled_clean_close(self):
        state = self._state("close03")
        session_id = state.foundation.session_id
        expected_pc, expected_frame = make_logout_ack_response(self.legacy, 3)
        actions = state.dispatch(self._logout_parsed(3))
        self.assertEqual(actions, [(
            "HYP_PF_013_LOGOUT_SUBCODE03_ACK_THEN_SERVER_SOCKET_CLOSE",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertEqual(len(self.timer_factory.scheduled), 1)
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)

    def test_ack_bytes_are_the_unchanged_pf012_pins(self):
        self.assertEqual(
            self.scenario.post_ack_action, LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        )
        self.assertEqual(self.scenario.close_delay_ms, LOGOUT_CLOSE_DELAY_MS)
        for subcode in (1, 3):
            pc, frame = make_logout_ack_response(self.legacy, subcode)
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                LOGOUT_ACK_PC_SHA256[subcode],
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                LOGOUT_ACK_FRAME_SHA256[subcode],
            )

    def test_missing_transport_closer_fails_closed_with_no_write(self):
        state = self._state("close-nolever", attach_closer=False)
        session_id = state.foundation.session_id
        self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_close_unavailable_no_reply", state.events,
        )
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)
        self.assertFalse(state.logout_close_scheduled)
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_echo_scenario_never_schedules_a_close(self):
        echo = load_logout_hypothesis_scenario(ECHO_SCENARIO_PATH)
        state = self._state("close-echo", scenario=echo)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(
            actions[0][0],
            "HYP_PF_012_LOGOUT_SUBCODE01_ACK_AFTER_CLEAN_CLOSE",
        )
        self.assertFalse(state.logout_close_scheduled)
        self.assertEqual(self.timer_factory.scheduled, [])
        self.assertEqual(self.closer.calls, 0)

    def test_wrong_payload_and_wrong_sequence_fail_closed(self):
        state = self._state("close-wrong")
        session_id = state.foundation.session_id
        subcode02 = LOGOUT_REQUEST_PCS[1].replace(
            LOGOUT_REQUEST_PAYLOADS[1], bytes.fromhex(
                "0802080014000000001400000000"
            ),
        )
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(subcode02)), [],
        )
        self.assertIn("logout_hypothesis_wrong_payload_no_reply", state.events)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(self.timer_factory.scheduled, [])

        sequence_state = self._state("close-seq", ready=False)
        self.assertEqual(sequence_state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_wrong_sequence_no_reply", sequence_state.events,
        )
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_post_ack_frames_stay_silent_inside_the_close_window(self):
        state = self._state("close-silent")
        self.assertEqual(len(state.dispatch(self._logout_parsed(1))), 1)
        rx_before = state.rx_frames
        for pc in (
            LOGOUT_REQUEST_PCS[1],
            LOGOUT_REQUEST_PCS[3],
            self.legacy._synthetic_client_login_pc(),
        ):
            self.assertEqual(state.dispatch(self.legacy.parse_outer(pc)), [])
        self.assertEqual(state.rx_frames, rx_before + 3)
        self.assertEqual(state.logout_ack_count, 1)
        self.assertEqual(len(self.timer_factory.scheduled), 1)
        self.assertEqual(
            state.events.count("logout_hypothesis_post_ack_frame_no_reply"), 3,
        )

    def test_close_scenario_allowlist_is_exact(self):
        data = json.loads(CLOSE_SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d["entry"].__setitem__("close_delay_ms", 5000),
            lambda d: d["entry"].__setitem__("post_ack_action", "reset"),
            lambda d: d["entry"].pop("post_ack_action"),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_logout_hypothesis_scenario(tampered)

    def test_bind_attaches_a_shutdown_then_close_lever(self):
        bindings = GameConnectionBindings()
        raw = _FakeRawSocket()
        accepted = AcceptedGameSocket(raw, bindings)

        class _AcceptingState:
            def __init__(self) -> None:
                self.attached = None

            def attach_transport_socket_closer(self, closer) -> None:
                self.attached = closer

            def close_connection(self) -> bool:
                return False

        state = _AcceptingState()
        accepted.bind(state)
        self.assertIsNotNone(state.attached)
        self.assertEqual(raw.ops, [])
        state.attached()
        self.assertEqual(raw.ops, [("shutdown", 2), ("close", None)])
        # The lever is idempotent against an already-closed raw socket.
        state.attached()
        self.assertEqual(
            raw.ops,
            [("shutdown", 2), ("close", None), ("shutdown", 2), ("close", None)],
        )

    def test_duplicate_closer_attach_is_rejected(self):
        state = self._state("close-dup")
        with self.assertRaises(RuntimeError):
            state.attach_transport_socket_closer(self.closer)
        with self.assertRaises(TypeError):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                logout_hypothesis_scenario=self.scenario,
            )("close-notcallable").attach_transport_socket_closer(object())


if __name__ == "__main__":
    unittest.main()
