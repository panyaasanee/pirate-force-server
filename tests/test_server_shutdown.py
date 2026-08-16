import contextlib
import hashlib
import io
import sys
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.connection import (
    GameConnectionBindings,
    adapt_game_listener,
)
from pirateforce_foundation.shutdown import (
    ManagedSocketModule,
    ServerShutdownController,
    adapt_server_main,
    installed_signal_handlers,
    run_server,
)


LEGACY_PATH = ROOT / "current/pf_login_game_server_v141.py"
EXPECTED_V141 = "2eb05ed2fdbdd5ee3d91f7fbb8c1d16a4c7a02a843bc97169b16a389e4ea4c22"


class _BlockingListener:
    def __init__(self, events, listen_count):
        self.events = events
        self.listen_count = listen_count
        self.closed = threading.Event()

    def __enter__(self):
        self.events.append("listener_enter")
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        self.close()
        self.events.append("listener_exit")
        return False

    def setsockopt(self, *_args): pass
    def bind(self, *_args): pass
    def settimeout(self, *_args): pass

    def listen(self, _count):
        self.events.append("listen")
        with self.listen_count.get_lock():
            self.listen_count.value += 1

    def accept(self):
        self.events.append("accept_blocked")
        self.closed.wait(5)
        raise OSError("listener closed")

    def close(self):
        if not self.closed.is_set():
            self.events.append("listener_close")
            self.closed.set()


class _BlockingSocketModule:
    AF_INET = 2
    SOCK_STREAM = 1
    SOL_SOCKET = 1
    SO_REUSEADDR = 2
    timeout = TimeoutError

    class _Counter:
        def __init__(self):
            self.value = 0
            self._lock = threading.Lock()
        def get_lock(self): return self._lock

    def __init__(self, events):
        self.events = events
        self.listen_count = self._Counter()

    def socket(self, *_args, **_kwargs):
        return _BlockingListener(self.events, self.listen_count)


class _RawAccepted:
    def __init__(self, events, *, shutdown_error=None):
        self.events = events
        self.shutdown_error = shutdown_error

    def __enter__(self):
        self.events.append("raw_enter")
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        self.events.append("raw_close")
        return False

    def shutdown(self, how):
        self.events.append(("raw_shutdown", how))
        if self.shutdown_error is not None:
            raise self.shutdown_error


class _BlockingRecvAccepted(_RawAccepted):
    def __init__(self, events):
        super().__init__(events)
        self.unblocked = threading.Event()

    def recv(self, _size):
        self.events.append("recv_blocked")
        self.unblocked.wait(5)
        raise OSError("accepted socket shutdown")

    def settimeout(self, _value): pass

    def shutdown(self, how):
        super().shutdown(how)
        self.unblocked.set()


class _RawImmediateListener:
    def __init__(self, accepted, events, *, close_error=None):
        self.accepted = accepted
        self.events = events
        self.close_error = close_error

    def __enter__(self): return self
    def __exit__(self, _exc_type, _exc, _traceback):
        self.close()
        return False
    def listen(self, _count): self.events.append("listen")
    def accept(self): return self.accepted, ("127.0.0.1", 1)
    def close(self):
        self.events.append("listener_close")
        if self.close_error is not None:
            raise self.close_error


class _OneSocketModule:
    AF_INET = 2
    SOCK_STREAM = 1
    def __init__(self, listener): self.listener = listener
    def socket(self, *_args, **_kwargs): return self.listener


class _QueuedSocketModule:
    AF_INET = 2
    SOCK_STREAM = 1
    SOL_SOCKET = 1
    SO_REUSEADDR = 2
    SHUT_RDWR = 2
    timeout = TimeoutError

    def __init__(self, sockets):
        self.sockets = list(sockets)
        self._lock = threading.Lock()

    def socket(self, *_args, **_kwargs):
        with self._lock:
            if not self.sockets:
                raise RuntimeError("unexpected socket construction")
            return self.sockets.pop(0)


class _FakeSignalModule:
    SIGINT = 2
    SIGTERM = 15

    class _Named:
        def __init__(self, value):
            self.name = {2: "SIGINT", 15: "SIGTERM"}[value]

    def __init__(self):
        self.handlers = {self.SIGINT: "old-int", self.SIGTERM: "old-term"}
    def Signals(self, value): return self._Named(value)
    def getsignal(self, value): return self.handlers[value]
    def signal(self, value, handler):
        old = self.handlers[value]
        self.handlers[value] = handler
        return old


def _frozen_shape(socket_module, events):
    namespace = {
        "socket": socket_module,
        "threading": threading,
        "events": events,
    }
    exec(
        "def game_listener(_port, _capdir, _ready, stop):\n"
        "    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:\n"
        "        s.listen(4)\n"
        "        while not stop.is_set():\n"
        "            s.accept()\n"
        "def main():\n"
        "    ready=threading.Event()\n"
        "    stop=threading.Event()\n"
        "    threading.Thread(target=game_listener,args=(1,None,ready,stop),daemon=True).start()\n"
        "    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:\n"
        "        s.listen(4)\n"
        "        s.accept()\n",
        namespace,
    )
    return namespace["main"]


def _active_frozen_shape(socket_module, state_type, events):
    namespace = {
        "socket": socket_module,
        "threading": threading,
        "GameSessionState": state_type,
        "events": events,
    }
    exec(
        "def game_listener(port, capdir, ready, stop, token):\n"
        "    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:\n"
        "        s.listen(4)\n"
        "        ready.set()\n"
        "        c,address=s.accept()\n"
        "        state=GameSessionState(token)\n"
        "        with c:\n"
        "            conn_done=threading.Event()\n"
        "            def heartbeat():\n"
        "                while not conn_done.wait(0.01):\n"
        "                    pass\n"
        "            hb=threading.Thread(target=heartbeat,daemon=True)\n"
        "            hb.start()\n"
        "            try:\n"
        "                c.recv(1)\n"
        "            except OSError:\n"
        "                pass\n"
        "            finally:\n"
        "                conn_done.set()\n"
        "                hb.join(0.5)\n"
        "                events.append('heartbeat_join')\n"
        "def main():\n"
        "    ready=threading.Event()\n"
        "    stop=threading.Event()\n"
        "    threading.Thread(target=game_listener,args=(1,None,ready,stop,'token'),daemon=True).start()\n"
        "    if not ready.wait(1):\n"
        "        raise RuntimeError('game listener not ready')\n"
        "    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:\n"
        "        s.listen(4)\n"
        "        s.accept()\n",
        namespace,
    )
    return namespace["main"]


class ServerShutdownTests(unittest.TestCase):
    def test_direct_stop_unblocks_login_and_game_accepts_and_joins(self):
        events = []
        raw_sockets = _BlockingSocketModule(events)
        controller = ServerShutdownController()
        managed = ManagedSocketModule(raw_sockets, controller)
        original = _frozen_shape(raw_sockets, events)
        original.__globals__["game_listener"] = adapt_game_listener(
            original.__globals__["game_listener"],
            GameConnectionBindings(), managed,
        )
        adapted = adapt_server_main(original, controller, managed, threading)
        output = io.StringIO()
        result = []

        runner = threading.Thread(
            target=lambda: result.append(run_server(
                adapted, controller, join_timeout=1,
                install_signals=False, output=output,
            )),
        )
        runner.start()
        deadline = time.monotonic() + 2
        while raw_sockets.listen_count.value < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(raw_sockets.listen_count.value, 2)
        self.assertTrue(controller.request_stop("direct-test"))
        self.assertFalse(controller.request_stop("duplicate"))
        runner.join(2)
        self.assertFalse(runner.is_alive())
        self.assertEqual(result, [0])
        self.assertEqual(output.getvalue().count("[FOUNDATION] stopped"), 1)
        self.assertEqual(events.count("listener_close"), 2)
        self.assertIs(adapted.__foundation_original_code__, original.__code__)

    def test_active_game_shutdown_waits_for_heartbeat_before_close_and_lease(self):
        events = []
        raw_accepted = _RawAccepted(events)
        raw_listener = _RawImmediateListener(raw_accepted, events)
        controller = ServerShutdownController()
        managed = ManagedSocketModule(_OneSocketModule(raw_listener), controller)
        listener = managed.socket()
        listener.listen(4)
        connection, _address = listener.accept()
        bindings = GameConnectionBindings()
        game_connection = bindings.accepted(connection)

        class State:
            def close_connection(self):
                events.append("lease_close")
                return True

        bindings.bind(State())
        with game_connection:
            controller.request_stop("active-game")
            self.assertIn(("raw_shutdown", 2), events)
            self.assertNotIn("raw_close", events)
            events.append("heartbeat_join")
        self.assertLess(events.index("heartbeat_join"), events.index("raw_close"))
        self.assertLess(events.index("raw_close"), events.index("lease_close"))

    def test_active_frozen_game_recv_shutdown_joins_and_closes_exact_lease(self):
        events = []
        controller = ServerShutdownController()
        bindings = GameConnectionBindings(controller.record_connection_failure)

        class State:
            def __init__(self, _token):
                bindings.bind(self)
            def close_connection(self):
                events.append("lease_close")
                return True

        accepted = _BlockingRecvAccepted(events)
        game_listener = _RawImmediateListener(accepted, events)
        login_listener = _BlockingListener(
            events, _BlockingSocketModule._Counter(),
        )
        raw_sockets = _QueuedSocketModule((game_listener, login_listener))
        managed = ManagedSocketModule(raw_sockets, controller)
        original = _active_frozen_shape(raw_sockets, State, events)
        original.__globals__["game_listener"] = adapt_game_listener(
            original.__globals__["game_listener"], bindings, managed,
        )
        adapted = adapt_server_main(original, controller, managed, threading)
        result = []
        output = io.StringIO()
        runner = threading.Thread(target=lambda: result.append(run_server(
            adapted, controller, join_timeout=1,
            install_signals=False, output=output,
        )))
        runner.start()
        deadline = time.monotonic() + 2
        while "recv_blocked" not in events and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertIn("recv_blocked", events)
        controller.request_stop("active-recv")
        runner.join(2)
        self.assertFalse(runner.is_alive())
        self.assertEqual(result, [0])
        self.assertLess(events.index(("raw_shutdown", 2)), events.index("heartbeat_join"))
        self.assertLess(events.index("heartbeat_join"), events.index("raw_close"))
        self.assertLess(events.index("raw_close"), events.index("lease_close"))
        self.assertEqual(events.count("lease_close"), 1)

    def test_game_lease_close_failure_reaches_controller(self):
        events = []
        raw_accepted = _RawAccepted(events)
        controller = ServerShutdownController()
        managed = ManagedSocketModule(
            _OneSocketModule(_RawImmediateListener(raw_accepted, events)),
            controller,
        )
        listener = managed.socket(); listener.listen(4)
        connection, _ = listener.accept()
        bindings = GameConnectionBindings(controller.record_connection_failure)
        game_connection = bindings.accepted(connection)

        class State:
            def close_connection(self):
                raise RuntimeError("exact lease close failed")

        bindings.bind(State())
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with game_connection:
                controller.request_stop("lease-close-failure")
        self.assertTrue(any(
            "exact lease close failed" in repr(error)
            for error in controller.failures
        ))
        self.assertIn("connection-close", stderr.getvalue())
        self.assertIn("GAME teardown failed", stderr.getvalue())

    def test_login_only_shutdown_has_no_foundation_session(self):
        events = []
        raw_accepted = _RawAccepted(events)
        controller = ServerShutdownController()
        managed = ManagedSocketModule(
            _OneSocketModule(_RawImmediateListener(raw_accepted, events)),
            controller,
        )
        listener = managed.socket(); listener.listen(4)
        login_connection, _ = listener.accept()
        with login_connection:
            controller.request_stop("login-only")
            self.assertIn(("raw_shutdown", 2), events)
        self.assertEqual(events.count("raw_close"), 1)
        self.assertNotIn("lease_close", events)

    def test_sigint_sigterm_are_idempotent_and_handlers_restore(self):
        fake = _FakeSignalModule()
        controller = ServerShutdownController()
        output = io.StringIO()
        with installed_signal_handlers(controller, fake):
            sigint_handler = fake.handlers[fake.SIGINT]
            sigterm_handler = fake.handlers[fake.SIGTERM]
            sigint_handler(fake.SIGINT, None)
            sigterm_handler(fake.SIGTERM, None)
            self.assertTrue(controller.requested)
        self.assertEqual(fake.handlers[fake.SIGINT], "old-int")
        self.assertEqual(fake.handlers[fake.SIGTERM], "old-term")
        self.assertTrue(controller.emit_stopped(output))
        self.assertFalse(controller.emit_stopped(output))
        self.assertEqual(output.getvalue().count("stopped"), 1)

    def test_signal_partial_install_and_restore_failures_are_fail_closed(self):
        class InstallFailure(_FakeSignalModule):
            def signal(self, value, handler):
                if value == self.SIGTERM and callable(handler):
                    raise OSError("SIGTERM install failed")
                return super().signal(value, handler)

        install = InstallFailure()
        controller = ServerShutdownController()
        with self.assertRaisesRegex(OSError, "install failed"):
            run_server(
                lambda: None, controller,
                signal_module=install, install_signals=True,
            )
        self.assertEqual(install.handlers[install.SIGINT], "old-int")

        class RestoreFailure(_FakeSignalModule):
            def signal(self, value, handler):
                if value == self.SIGINT and handler == "old-int":
                    raise OSError("SIGINT restore failed")
                return super().signal(value, handler)

        restore = RestoreFailure()
        second = ServerShutdownController()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with installed_signal_handlers(second, restore):
                restore.handlers[restore.SIGTERM](restore.SIGTERM, None)
        self.assertTrue(any(
            "restore failed" in repr(error) for error in second.failures
        ))
        self.assertIn("signal-restore", stderr.getvalue())

    def test_unrelated_pre_stop_accept_error_is_primary(self):
        class FailingAccept(_RawImmediateListener):
            def accept(self):
                raise OSError("unrelated accept failure")

        events = []
        controller = ServerShutdownController()
        managed = ManagedSocketModule(
            _OneSocketModule(FailingAccept(_RawAccepted(events), events)),
            controller,
        )
        listener = managed.socket(); listener.listen(4)
        with self.assertRaisesRegex(OSError, "unrelated accept failure"):
            run_server(
                listener.accept, controller, install_signals=False,
            )

    def test_close_failures_are_observable_and_make_requested_stop_nonzero(self):
        events = []
        controller = ServerShutdownController()
        raw_accepted = _RawAccepted(
            events, shutdown_error=OSError("accepted shutdown failed"),
        )
        managed = ManagedSocketModule(
            _OneSocketModule(_RawImmediateListener(
                raw_accepted, events,
                close_error=OSError("listener close failed"),
            )),
            controller,
        )
        listener = managed.socket(); listener.listen(4)
        connection, _ = listener.accept()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            controller.request_stop("failure-test")
        self.assertEqual(len(controller.failures), 2)
        self.assertIn("listener close failed", stderr.getvalue())
        self.assertIn("accepted shutdown failed", stderr.getvalue())
        self.assertEqual(
            run_server(lambda: None, controller, install_signals=False), 1,
        )
        # Make the connection collectible without claiming the failed shutdown.
        connection._controller.unregister_socket(connection)

    def test_primary_exception_is_preserved_with_cleanup_failure(self):
        events = []
        controller = ServerShutdownController()
        managed = ManagedSocketModule(
            _OneSocketModule(_RawImmediateListener(
                _RawAccepted(events), events,
                close_error=OSError("cleanup failed"),
            )),
            controller,
        )
        listener = managed.socket(); listener.listen(4)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(ValueError, "primary") as raised:
                run_server(
                    lambda: (_ for _ in ()).throw(ValueError("primary")),
                    controller, install_signals=False,
                )
        self.assertIn("cleanup failed", stderr.getvalue())
        self.assertTrue(any("shutdown also failed" in note for note in raised.exception.__notes__))

    def test_thread_timeout_is_bounded_failure_without_stopped_marker(self):
        class Event:
            def __init__(self): self.set_count = 0
            def set(self): self.set_count += 1
        class Thread:
            def __init__(self): self.joined = []
            def join(self, timeout): self.joined.append(timeout)
            def is_alive(self): return True

        controller = ServerShutdownController()
        event = Event(); thread = Thread()
        controller.register_thread(thread, event)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            controller.request_stop("timeout")
            failures = controller.finish(0.01)
        self.assertEqual(event.set_count, 1)
        self.assertEqual(thread.joined, [0.01])
        self.assertTrue(any(isinstance(x, TimeoutError) for x in failures))
        self.assertIn("thread-timeout", stderr.getvalue())

    def test_thread_join_exception_is_observable(self):
        class Event:
            def set(self): pass
        class Thread:
            def join(self, _timeout): raise RuntimeError("join failed")
            def is_alive(self): return False

        controller = ServerShutdownController()
        controller.register_thread(Thread(), Event())
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            controller.request_stop("join-error")
            failures = controller.finish(0.01)
        self.assertTrue(any("join failed" in repr(x) for x in failures))
        self.assertIn("thread-join", stderr.getvalue())

    def test_unrequested_return_fails_even_before_resources_and_v141_is_preserved(self):
        controller = ServerShutdownController()
        with self.assertRaisesRegex(
            RuntimeError, "server main returned without a shutdown request",
        ):
            run_server(lambda: None, controller, install_signals=False)
        self.assertTrue(controller.requested)
        self.assertEqual(
            hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest(), EXPECTED_V141,
        )


if __name__ == "__main__":
    unittest.main()
