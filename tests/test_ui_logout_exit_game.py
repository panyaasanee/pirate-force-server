"""LANE-UI: UI-B real exit-game logout (`ui_logout_exit_game.py`).

Two evidence layers, kept separate per house rule (never used to prove
each other):

  * WIRE layer -- the composed ack's PC/frame bytes are byte-identical to
    the independently hash-pinned HYP-PF-012 composition
    (`LOGOUT_ACK_PC_SHA256` / `LOGOUT_ACK_FRAME_SHA256`), and the socket
    close is scheduled through the same lever HYP-PF-013 already proved
    puts the FIN strictly after the ack on the wire.
  * DB layer -- the `sessions` row's `closed_at` is set (not stale), and
    a FRESH login can list and re-select the same character afterward
    (the concrete "relogin works" claim PANYA-ORDER `20260905_1911`
    asks for), all on a real `SQLiteStore`, not a mock.

This module is NOT yet wired into `runtime.py`'s dispatch (that hookup is
a CORE-REQUEST to chief -- see the round's letter). Every test below
calls `dispatch_real_exit_game_logout` directly against a real
`PersistentGameSessionState` built with `logout_hypothesis_scenario=None`
(the real production default), which is exactly the calling shape the
CORE-REQUEST hookup will use.
"""
from __future__ import annotations

import hashlib
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
    LOGOUT_REQUEST_PCS,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.ui_logout_exit_game import (  # noqa: E402
    DEFAULT_CLOSE_DELAY_MS,
    ExitGameLogoutOutcome,
    dispatch_real_exit_game_logout,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


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


class UiLogoutExitGameTests(unittest.TestCase):
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
        self.timer_factory = _RecordingTimerFactory()
        self.closer = _RecordingCloser()

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, ready=True, attach_closer=True):
        # `logout_hypothesis_scenario` is left at its default (None): this
        # is a real production boot, not an attended hypothesis boot --
        # the exact shape the CORE-REQUEST hookup will call this module
        # from.
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
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
        selector = characters[0].selector
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state, selector

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    def _logout_parsed(self, subcode):
        return self.legacy.parse_outer(LOGOUT_REQUEST_PCS[subcode])

    # ---- WIRE layer: ack bytes are the unchanged, independently pinned
    #      HYP-PF-012 composition; close is scheduled the HYP-PF-013 way ----

    def test_exit_game_ack_bytes_match_the_independent_pf012_pins(self):
        state, _selector = self._state("exit01")
        outcome = dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(1),
            close_timer_factory=self.timer_factory,
        )
        self.assertIsInstance(outcome, ExitGameLogoutOutcome)
        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.reason, "ack_then_server_socket_close")
        self.assertEqual(len(outcome.actions), 1)
        label, pc, frame, delay = outcome.actions[0]
        self.assertEqual(label, "UI_LOGOUT_EXIT_GAME_ACK_THEN_SERVER_SOCKET_CLOSE")
        self.assertEqual(delay, 0.0)
        self.assertEqual(hashlib.sha256(pc).hexdigest().upper(), LOGOUT_ACK_PC_SHA256[1])
        self.assertEqual(
            hashlib.sha256(frame).hexdigest().upper(), LOGOUT_ACK_FRAME_SHA256[1],
        )

    def test_close_scheduled_at_the_pinned_delay_and_fires_the_real_closer(self):
        state, _selector = self._state("exit02")
        dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(1),
            close_timer_factory=self.timer_factory,
        )
        self.assertEqual(
            [delay for delay, _cb in self.timer_factory.scheduled],
            [DEFAULT_CLOSE_DELAY_MS / 1000.0],
        )
        self.assertEqual(self.closer.calls, 0)
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)
        self.assertTrue(state.logout_acknowledged)
        self.assertTrue(state.logout_close_scheduled)
        self.assertEqual(state.logout_ack_count, 1)

    # ---- DB layer: the lease closes for real, and relogin genuinely works ----

    def test_session_row_closed_and_not_left_stale(self):
        state, _selector = self._state("exit03")
        session_id = state.foundation.session_id
        self.assertIsNone(self._session_closed_at(session_id))
        dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(1),
            close_timer_factory=self.timer_factory,
        )
        self.assertIsNotNone(self._session_closed_at(session_id))

    def test_relogin_after_exit_game_selects_the_same_character_again(self):
        state, selector = self._state("exit04")
        dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(1),
            close_timer_factory=self.timer_factory,
        )
        self.timer_factory.fire_all()  # the socket actually closes

        # A brand-new connection (new state object, same account/character)
        # must be able to select the SAME character again -- the concrete
        # "log back in" claim. If close_connection() had left the
        # character claimed, this select would refuse
        # (bag_already_claimed / an equivalent stale-lock refusal).
        relogin_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            close_timer_factory=self.timer_factory,
        )
        relogin_state = relogin_type("exit04")
        relogin_state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = relogin_state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        self.assertIsNotNone(relogin_state.foundation.selected)

    # ---- fail-closed preconditions: no write, no reply ----

    def test_character_select_subcode_is_left_untouched(self):
        state, _selector = self._state("exit05")
        session_id = state.foundation.session_id
        outcome = dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(3),
            close_timer_factory=self.timer_factory,
        )
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.reason, "not_exit_game_exact_03")
        self.assertEqual(outcome.actions, ())
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)

    def test_wrong_sequence_fails_closed(self):
        state, _selector = self._state("exit06", ready=False)
        session_id = state.foundation.session_id
        outcome = dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(1),
            close_timer_factory=self.timer_factory,
        )
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.reason, "wrong_sequence")
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_no_transport_closer_fails_closed(self):
        state, _selector = self._state("exit07", attach_closer=False)
        session_id = state.foundation.session_id
        outcome = dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(1),
            close_timer_factory=self.timer_factory,
        )
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.reason, "no_transport_closer")
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(self.timer_factory.scheduled, [])

    def test_already_acknowledged_is_not_double_closed(self):
        state, _selector = self._state("exit08")
        first = dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(1),
            close_timer_factory=self.timer_factory,
        )
        self.assertTrue(first.handled)
        second = dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(1),
            close_timer_factory=self.timer_factory,
        )
        self.assertFalse(second.handled)
        self.assertEqual(second.reason, "already_acknowledged")
        self.assertEqual(len(self.timer_factory.scheduled), 1)
        self.assertEqual(state.logout_ack_count, 1)

    def test_no_selected_character_fails_closed(self):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            close_timer_factory=self.timer_factory,
        )
        state = state_type("exit09")
        state.attach_transport_socket_closer(self.closer)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertIsNone(state.foundation.selected)
        outcome = dispatch_real_exit_game_logout(
            state, self.legacy, self._logout_parsed(1),
            close_timer_factory=self.timer_factory,
        )
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.reason, "no_selected_character")


if __name__ == "__main__":
    unittest.main()
