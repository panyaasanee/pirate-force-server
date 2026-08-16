import contextlib
import hashlib
import io
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.connection import (
    GameConnectionBindings,
    adapt_game_listener,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.session import FoundationSession, ReadOnlyFoundationSession
from pirateforce_foundation.store import SQLiteStore


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
EXPECTED_V141 = "2eb05ed2fdbdd5ee3d91f7fbb8c1d16a4c7a02a843bc97169b16a389e4ea4c22"


class _RawAccepted:
    def __init__(self, events, *, exit_error=None, close_error=None):
        self.events = events
        self.closed = False
        self.exit_error = exit_error
        self.close_error = close_error

    def __enter__(self):
        self.events.append("socket_enter")
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        self.closed = True
        self.events.append("socket_exit")
        if self.exit_error is not None:
            raise self.exit_error
        return False

    def close(self):
        self.closed = True
        self.events.append("socket_abort")
        if self.close_error is not None:
            raise self.close_error


class _RawListener:
    def __init__(self, accepted, events, *, exit_error=None):
        self.accepted = accepted
        self.events = events
        self.exit_error = exit_error

    def __enter__(self):
        self.events.append("listener_enter")
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        self.events.append("listener_exit")
        if self.exit_error is not None:
            raise self.exit_error
        return False

    def accept(self):
        self.events.append("accept")
        return self.accepted, ("127.0.0.1", 1)


class _SocketModule:
    AF_INET = 2
    SOCK_STREAM = 1

    def __init__(self, listener):
        self.listener = listener

    def socket(self, *_args, **_kwargs):
        return self.listener


def _listener_function(socket_module, state_type, events, raise_body=False):
    namespace = {
        "socket": socket_module,
        "GameSessionState": state_type,
        "events": events,
        "raise_body": raise_body,
    }
    exec(
        "def game_listener(port, capdir, ready, stop, token):\n"
        "    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:\n"
        "        c, address = s.accept()\n"
        "        state = GameSessionState(token)\n"
        "        with c:\n"
        "            try:\n"
        "                events.append('body')\n"
        "                if raise_body:\n"
        "                    raise ValueError('dispatch failed')\n"
        "            finally:\n"
        "                events.append('heartbeat_join')\n",
        namespace,
    )
    return namespace["game_listener"]


class ConnectionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.default = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, self.default,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row[0]

    def _run_adapted(self, *, raise_body=False):
        events = []
        bindings = GameConnectionBindings()
        base_state = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            connection_bindings=bindings,
        )

        class ObservedState(base_state):
            instances = []

            def __init__(self, token):
                super().__init__(token)
                self.instances.append(self)

            def close_connection(self):
                events.append("lease_close")
                return super().close_connection()

        accepted = _RawAccepted(events)
        socket_module = _SocketModule(_RawListener(accepted, events))
        original = _listener_function(
            socket_module, ObservedState, events, raise_body=raise_body,
        )
        adapted = adapt_game_listener(original, bindings, socket_module)
        return events, bindings, accepted, original, adapted, ObservedState

    def test_normal_game_teardown_closes_exact_unselected_lease_after_join(self):
        events, _bindings, accepted, original, adapted, state_type = self._run_adapted()
        adapted(1, None, None, None, "normal")
        state = state_type.instances[0]
        self.assertTrue(accepted.closed)
        self.assertIsNotNone(self._closed_at(state.foundation.session_id))
        self.assertEqual(
            events,
            ["listener_enter", "accept", "socket_enter", "body",
             "heartbeat_join", "socket_exit", "lease_close", "listener_exit"],
        )
        self.assertIs(adapted.__foundation_original_code__, original.__code__)
        self.assertFalse(state.foundation.close_connection())

    def test_dispatch_exception_closes_lease_without_masking_original(self):
        events, _bindings, accepted, _original, adapted, state_type = self._run_adapted(
            raise_body=True,
        )
        with self.assertRaisesRegex(ValueError, "dispatch failed"):
            adapted(1, None, None, None, "exception")
        state = state_type.instances[0]
        self.assertTrue(accepted.closed)
        self.assertIsNotNone(self._closed_at(state.foundation.session_id))
        self.assertLess(events.index("heartbeat_join"), events.index("lease_close"))

    def test_close_failure_is_observable_and_does_not_mask_dispatch_error(self):
        events = []
        bindings = GameConnectionBindings()

        class FailingState:
            def __init__(self, _token):
                bindings.bind(self)

            def close_connection(self):
                events.append("lease_close_failed")
                raise RuntimeError("close failed")

        accepted = _RawAccepted(events)
        socket_module = _SocketModule(_RawListener(accepted, events))
        original = _listener_function(socket_module, FailingState, events, True)
        adapted = adapt_game_listener(original, bindings, socket_module)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(ValueError, "dispatch failed"):
                adapted(1, None, None, None, "failure")
        self.assertIn("game teardown also failed", stderr.getvalue().lower())
        self.assertIn("close failed", stderr.getvalue())

    def test_standalone_close_failure_is_logged_and_next_connection_can_bind(self):
        events = []
        bindings = GameConnectionBindings()

        class FailingState:
            def close_connection(self):
                events.append("first_close")
                raise RuntimeError("first close failed")

        class GoodState:
            def close_connection(self):
                events.append("second_close")
                return True

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            first = bindings.accepted(_RawAccepted(events))
            bindings.bind(FailingState())
            with first:
                pass
            second = bindings.accepted(_RawAccepted(events))
            bindings.bind(GoodState())
            with second:
                pass
        self.assertIn("Foundation GAME teardown failed", stderr.getvalue())
        self.assertEqual(events.count("first_close"), 1)
        self.assertEqual(events.count("second_close"), 1)

    def test_idempotence_selected_position_and_cross_account_isolation(self):
        one = FoundationSession(self.lifecycle, self.projector, "one")
        two = FoundationSession(self.lifecycle, self.projector, "two")
        actor_wire = self.legacy.get_preset_actor_wire()
        character, _ = one.create("test01", actor_wire)
        one.select_and_start(character.selector)
        checkpoint = Position(1, 0, 123.25, -456.5, 789.0, 1.25)
        one.checkpoint(checkpoint)
        self.assertTrue(one.close_connection())
        closed_once = self._closed_at(one.session_id)
        self.assertFalse(one.close_connection())
        self.assertEqual(self._closed_at(one.session_id), closed_once)
        self.assertIsNone(self._closed_at(two.session_id))
        self.assertEqual(self.store.get_character(character.id).position, checkpoint)
        self.assertTrue(two.close_connection())

    def test_state_binding_failure_and_login_list_failure_close_only_new_sid(self):
        bindings = GameConnectionBindings()
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            connection_bindings=bindings,
        )
        with self.assertRaisesRegex(RuntimeError, "without an accepted connection"):
            state_type("bind-failure")
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions s JOIN accounts a ON a.id=s.account_id "
                "WHERE a.login_name='bind-failure' ORDER BY lease_generation DESC LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(row[0])

        class FailingListStore:
            def __init__(self):
                self.closed = []
            def ensure_account(self, _name): return 7
            def open_session(self, _account): return "exact-new-sid"
            def list_characters(self, _account): raise RuntimeError("list failed")
            def close_session(self, sid): self.closed.append(sid)

        store = FailingListStore()
        lifecycle = CharacterLifecycle(store, self.default)
        with self.assertRaisesRegex(RuntimeError, "list failed"):
            lifecycle.login("broken")
        self.assertEqual(store.closed, ["exact-new-sid"])

    def test_constructor_failures_abort_socket_without_leaking_a_lease(self):
        events = []
        bindings = GameConnectionBindings()
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            connection_bindings=bindings,
        )
        accepted = _RawAccepted(events)
        socket_module = _SocketModule(_RawListener(accepted, events))
        adapted = adapt_game_listener(
            _listener_function(socket_module, state_type, events),
            bindings, socket_module,
        )
        with mock.patch(
            "pirateforce_foundation.session.threading.RLock",
            side_effect=RuntimeError("lock init failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "lock init failed"):
                adapted(1, None, None, None, "pre-login-failure")
        self.assertTrue(accepted.closed)
        with self.store.connect() as db:
            count = db.execute(
                "SELECT COUNT(*) FROM sessions s JOIN accounts a "
                "ON a.id=s.account_id WHERE a.login_name='pre-login-failure'"
            ).fetchone()[0]
        self.assertEqual(count, 0)

        class RejectingBindings(GameConnectionBindings):
            def bind(self, _state):
                raise RuntimeError("bind rejected")

        rejecting = RejectingBindings()
        second_events = []
        second_state = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            connection_bindings=rejecting,
        )
        second_accepted = _RawAccepted(second_events)
        second_socket_module = _SocketModule(
            _RawListener(second_accepted, second_events),
        )
        second_adapted = adapt_game_listener(
            _listener_function(
                second_socket_module, second_state, second_events,
            ),
            rejecting, second_socket_module,
        )
        with self.assertRaisesRegex(RuntimeError, "bind rejected"):
            second_adapted(1, None, None, None, "post-login-failure")
        self.assertTrue(second_accepted.closed)
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions s JOIN accounts a "
                "ON a.id=s.account_id WHERE a.login_name='post-login-failure'"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertIsNotNone(row[0])

    def test_post_bind_subclass_failure_aborts_socket_and_closes_exact_sid(self):
        events = []
        bindings = GameConnectionBindings()
        base_state = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            connection_bindings=bindings,
        )

        class FailingAfterBind(base_state):
            session_id = None
            def __init__(self, token):
                super().__init__(token)
                type(self).session_id = self.foundation.session_id
                raise RuntimeError("subclass init failed after bind")

        accepted = _RawAccepted(events)
        socket_module = _SocketModule(_RawListener(accepted, events))
        adapted = adapt_game_listener(
            _listener_function(socket_module, FailingAfterBind, events),
            bindings, socket_module,
        )
        with self.assertRaisesRegex(RuntimeError, "failed after bind"):
            adapted(1, None, None, None, "post-bind-failure")
        self.assertTrue(accepted.closed)
        self.assertIn("socket_abort", events)
        self.assertIsNotNone(self._closed_at(FailingAfterBind.session_id))

    def test_accepted_socket_exit_errors_close_lease_and_preserve_primary(self):
        for body_error in (False, True):
            with self.subTest(body_error=body_error):
                events = []
                bindings = GameConnectionBindings()
                base_state = make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                    connection_bindings=bindings,
                )

                class ObservedState(base_state):
                    instance = None
                    def __init__(self, token):
                        super().__init__(token)
                        type(self).instance = self

                accepted = _RawAccepted(
                    events, exit_error=OSError("accepted exit failed"),
                )
                socket_module = _SocketModule(_RawListener(accepted, events))
                adapted = adapt_game_listener(
                    _listener_function(
                        socket_module, ObservedState, events,
                        raise_body=body_error,
                    ),
                    bindings, socket_module,
                )
                stderr = io.StringIO()
                expected = ValueError if body_error else OSError
                expected_text = "dispatch failed" if body_error else "accepted exit failed"
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaisesRegex(expected, expected_text):
                        adapted(1, None, None, None, f"exit-{body_error}")
                sid = ObservedState.instance.foundation.session_id
                self.assertIsNotNone(self._closed_at(sid))
                if body_error:
                    self.assertIn("accepted exit failed", stderr.getvalue())

    def test_abort_and_listener_exit_failures_are_aggregated_and_pending_clears(self):
        events = []
        bindings = GameConnectionBindings()
        base_state = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            connection_bindings=bindings,
        )

        class FailingAfterBind(base_state):
            session_id = None
            def __init__(self, token):
                super().__init__(token)
                type(self).session_id = self.foundation.session_id
                raise RuntimeError("primary constructor failure")

        accepted = _RawAccepted(
            events, close_error=OSError("accepted abort failed"),
        )
        listener = _RawListener(
            accepted, events, exit_error=OSError("listener exit failed"),
        )
        socket_module = _SocketModule(listener)
        adapted = adapt_game_listener(
            _listener_function(socket_module, FailingAfterBind, events),
            bindings, socket_module,
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(RuntimeError, "primary constructor failure"):
                adapted(1, None, None, None, "aggregate-failure")
        self.assertIsNotNone(self._closed_at(FailingAfterBind.session_id))
        self.assertIn("accepted abort failed", stderr.getvalue())
        self.assertIn("listener exit failed", stderr.getvalue())

        class GoodState:
            def close_connection(self):
                return True

        next_connection = bindings.accepted(_RawAccepted(events))
        bindings.bind(GoodState())
        with next_connection:
            pass

    def test_read_only_and_login_listener_globals_are_untouched(self):
        class ReadOnlyStore:
            def list_characters_for_login_read_only(self, _login):
                return 1, [type("Character", (), {"name": "only", "selector": 0})()]

        scenario = type("Scenario", (), {"required_character_name": "only"})()
        session = ReadOnlyFoundationSession(
            ReadOnlyStore(), self.projector, "read-only", scenario,
        )
        self.assertFalse(session.close_connection())

        bindings = GameConnectionBindings()
        original_socket = self.legacy.game_listener.__globals__["socket"]
        adapted = adapt_game_listener(
            self.legacy.game_listener, bindings, self.legacy.socket,
        )
        self.assertIs(self.legacy.game_listener.__globals__["socket"], original_socket)
        self.assertIs(self.legacy.main.__globals__["socket"], original_socket)
        self.assertIs(adapted.__foundation_original_code__, self.legacy.game_listener.__code__)
        self.assertEqual(
            hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest(), EXPECTED_V141,
        )

    def test_adapted_listener_reads_globals_mutated_after_install(self):
        events = []
        bindings = GameConnectionBindings()

        class State:
            def __init__(self, _token):
                bindings.bind(self)
            def close_connection(self):
                return True

        accepted = _RawAccepted(events)
        socket_module = _SocketModule(_RawListener(accepted, events))
        namespace = {
            "socket": socket_module,
            "GameSessionState": State,
            "events": events,
            "runtime_value": "before",
        }
        exec(
            "def game_listener(port, capdir, ready, stop, token):\n"
            "    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:\n"
            "        c, address = s.accept()\n"
            "        state = GameSessionState(token)\n"
            "        with c:\n"
            "            events.append(runtime_value)\n",
            namespace,
        )
        original = namespace["game_listener"]
        adapted = adapt_game_listener(original, bindings, socket_module)
        namespace["runtime_value"] = "after"
        adapted(1, None, None, None, "late")
        self.assertIn("after", events)
        self.assertNotIn("before", events)


if __name__ == "__main__":
    unittest.main()
