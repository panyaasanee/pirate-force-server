"""Bounded Foundation-owned shutdown around the frozen V141 listener code."""
from __future__ import annotations

import contextlib
import functools
import signal
import sys
import threading
import types
from typing import Any, Callable, Iterator


class ShutdownRequested(Exception):
    """Internal accept-loop sentinel emitted only after an explicit stop request."""


class ServerShutdownController:
    """Own listener/connection/thread resources created by one server invocation."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._requested = threading.Event()
        self._listeners: set[ManagedSocket] = set()
        self._accepted: set[ManagedSocket] = set()
        self._threads: list[ManagedThread] = []
        self._stop_events: list[Any] = []
        self._failures: list[BaseException] = []
        self._failure_keys: set[tuple[str, str]] = set()
        self._reason: str | None = None
        self._started = False
        self._stopped_emitted = False

    @property
    def requested(self) -> bool:
        return self._requested.is_set()

    @property
    def started(self) -> bool:
        with self._lock:
            return self._started

    @property
    def failures(self) -> tuple[BaseException, ...]:
        with self._lock:
            return tuple(self._failures)

    def _record_failure(self, stage: str, error: BaseException) -> None:
        key = (stage, repr(error))
        with self._lock:
            if key in self._failure_keys:
                return
            self._failure_keys.add(key)
            self._failures.append(error)
        print(
            f"[FOUNDATION!] shutdown {stage} failed: {error!r}",
            file=sys.stderr,
        )

    def register_listener(self, sock: "ManagedSocket") -> None:
        with self._lock:
            self._listeners.add(sock)
            self._started = True
            requested = self.requested
        if requested:
            self._stop_listener(sock)

    def register_accepted(self, sock: "ManagedSocket") -> None:
        with self._lock:
            self._accepted.add(sock)
            requested = self.requested
        if requested:
            self._stop_accepted(sock)

    def unregister_socket(self, sock: "ManagedSocket") -> None:
        with self._lock:
            self._listeners.discard(sock)
            self._accepted.discard(sock)

    def register_thread(self, thread: "ManagedThread", stop_event: Any) -> None:
        with self._lock:
            self._threads.append(thread)
            self._stop_events.append(stop_event)
            self._started = True
            requested = self.requested
        if requested:
            self._set_stop_event(stop_event)

    def record_thread_failure(self, error: BaseException) -> None:
        self._record_failure("thread", error)

    def record_connection_failure(self, error: BaseException) -> None:
        self._record_failure("connection-close", error)

    def _set_stop_event(self, event: Any) -> None:
        try:
            event.set()
        except BaseException as error:
            self._record_failure("stop-event", error)

    def _stop_listener(self, sock: "ManagedSocket") -> None:
        try:
            sock.close()
        except BaseException as error:
            self._record_failure("listener-close", error)

    def _stop_accepted(self, sock: "ManagedSocket") -> None:
        try:
            sock.shutdown_for_stop()
        except BaseException as error:
            self._record_failure("accepted-shutdown", error)

    def request_stop(self, reason: str) -> bool:
        """Request one bounded stop; duplicate signals are idempotent."""
        with self._lock:
            if self.requested:
                return False
            self._reason = str(reason)
            self._requested.set()
            stop_events = tuple(self._stop_events)
            listeners = tuple(self._listeners)
            accepted = tuple(self._accepted)
        for event in stop_events:
            self._set_stop_event(event)
        # Stop new accepts first.  Active connections are only shutdown here;
        # their frozen contexts close them after GAME heartbeat coordination.
        for sock in listeners:
            self._stop_listener(sock)
        for sock in accepted:
            self._stop_accepted(sock)
        return True

    def finish(self, join_timeout: float) -> tuple[BaseException, ...]:
        """Join every owned listener thread within one bounded interval each."""
        if not self.requested:
            self.request_stop("finalize")
        with self._lock:
            threads = tuple(self._threads)
        for thread in threads:
            try:
                thread.join(join_timeout)
            except BaseException as error:
                self._record_failure("thread-join", error)
                continue
            if thread.is_alive():
                self._record_failure(
                    "thread-timeout",
                    TimeoutError(
                        f"server thread did not stop within {join_timeout:.3f}s"
                    ),
                )
        return self.failures

    def emit_stopped(self, stream: Any = None) -> bool:
        with self._lock:
            if self._stopped_emitted:
                return False
            self._stopped_emitted = True
        print("[FOUNDATION] stopped", file=stream or sys.stdout)
        return True


class ManagedSocket:
    """Socket proxy registered with one shutdown controller."""

    def __init__(self, raw_socket: Any, controller: ServerShutdownController,
                 shutdown_how: int = 2) -> None:
        self._raw_socket = raw_socket
        self._controller = controller
        self._lock = threading.RLock()
        self._closed = False
        self._listener = False
        self._shutdown_how = shutdown_how

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_socket, name)

    def __enter__(self) -> "ManagedSocket":
        self._raw_socket.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        try:
            return bool(self._raw_socket.__exit__(exc_type, exc, traceback))
        finally:
            with self._lock:
                self._closed = True
            self._controller.unregister_socket(self)

    def listen(self, *args, **kwargs) -> Any:
        result = self._raw_socket.listen(*args, **kwargs)
        with self._lock:
            self._listener = True
        self._controller.register_listener(self)
        return result

    def accept(self):
        try:
            raw_connection, address = self._raw_socket.accept()
        except OSError as error:
            if self._controller.requested:
                raise ShutdownRequested("listener stopped") from None
            raise error
        connection = ManagedSocket(
            raw_connection, self._controller, self._shutdown_how,
        )
        self._controller.register_accepted(connection)
        return connection, address

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self._raw_socket.close()
        finally:
            self._controller.unregister_socket(self)

    def shutdown_for_stop(self) -> None:
        with self._lock:
            if self._closed:
                return
        self._raw_socket.shutdown(self._shutdown_how)


class ManagedSocketModule:
    """Delegate socket constants while registering server-owned sockets."""

    def __init__(self, raw_socket_module: Any,
                 controller: ServerShutdownController) -> None:
        self._raw_socket_module = raw_socket_module
        self._controller = controller

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_socket_module, name)

    def socket(self, *args, **kwargs) -> ManagedSocket:
        return ManagedSocket(
            self._raw_socket_module.socket(*args, **kwargs), self._controller,
            getattr(self._raw_socket_module, "SHUT_RDWR", 2),
        )


class ManagedThread:
    """One exact frozen-main child thread with captured stop ownership."""

    def __init__(self, raw_threading: Any, controller: ServerShutdownController,
                 *args, **kwargs) -> None:
        if args:
            raise TypeError("managed frozen-main Thread requires keyword arguments")
        target = kwargs.get("target")
        target_args = tuple(kwargs.get("args", ()))
        target_kwargs = dict(kwargs.get("kwargs") or {})
        if target is None or len(target_args) < 4 or not hasattr(target_args[3], "set"):
            raise RuntimeError("unexpected frozen GAME thread construction")

        def run_target() -> None:
            try:
                target(*target_args, **target_kwargs)
            except ShutdownRequested as error:
                if not controller.requested:
                    controller.record_thread_failure(error)
            except BaseException as error:
                controller.record_thread_failure(error)
                controller.request_stop("server thread failure")

        raw_kwargs = dict(kwargs)
        raw_kwargs["target"] = run_target
        raw_kwargs["args"] = ()
        raw_kwargs["kwargs"] = {}
        self._raw_thread = raw_threading.Thread(**raw_kwargs)
        controller.register_thread(self, target_args[3])

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_thread, name)

    def start(self) -> None:
        self._raw_thread.start()

    def join(self, timeout: float | None = None) -> None:
        self._raw_thread.join(timeout)

    def is_alive(self) -> bool:
        return bool(self._raw_thread.is_alive())


class ManagedThreadingModule:
    def __init__(self, raw_threading: Any,
                 controller: ServerShutdownController) -> None:
        self._raw_threading = raw_threading
        self._controller = controller

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_threading, name)

    def Thread(self, *args, **kwargs) -> ManagedThread:
        return ManagedThread(
            self._raw_threading, self._controller, *args, **kwargs,
        )


def adapt_server_main(original: Callable[..., Any],
                      controller: ServerShutdownController,
                      socket_module: ManagedSocketModule,
                      raw_threading: Any) -> Callable[..., Any]:
    """Run the exact frozen main code with Foundation-owned resource facades."""
    @functools.wraps(original)
    def adapted(*args, **kwargs):
        main_globals = dict(original.__globals__)
        main_globals["socket"] = socket_module
        main_globals["threading"] = ManagedThreadingModule(
            raw_threading, controller,
        )
        main = types.FunctionType(
            original.__code__, main_globals, original.__name__,
            original.__defaults__, original.__closure__,
        )
        main.__kwdefaults__ = original.__kwdefaults__
        return main(*args, **kwargs)

    adapted.__foundation_original_code__ = original.__code__
    return adapted


@contextlib.contextmanager
def installed_signal_handlers(controller: ServerShutdownController,
                              signal_module: Any = signal) -> Iterator[None]:
    previous: list[tuple[Any, Any]] = []

    def request(signum, _frame) -> None:
        try:
            name = signal_module.Signals(signum).name
        except Exception:
            name = str(signum)
        controller.request_stop(name)

    try:
        for name in ("SIGINT", "SIGTERM"):
            signum = getattr(signal_module, name, None)
            if signum is None:
                continue
            old = signal_module.getsignal(signum)
            signal_module.signal(signum, request)
            previous.append((signum, old))
        yield
    finally:
        for signum, old in reversed(previous):
            try:
                signal_module.signal(signum, old)
            except BaseException as error:
                controller._record_failure("signal-restore", error)


def run_server(server_main: Callable[[], Any],
               controller: ServerShutdownController, *,
               join_timeout: float = 2.0,
               install_signals: bool = True,
               signal_module: Any = signal,
               output: Any = None) -> int:
    """Run until an explicit stop; return zero only after bounded clean teardown."""
    primary: BaseException | None = None
    scope = (
        installed_signal_handlers(controller, signal_module)
        if install_signals else contextlib.nullcontext()
    )
    finished = False
    try:
        with scope:
            try:
                server_main()
            except ShutdownRequested as error:
                if not controller.requested:
                    primary = error
                    controller.request_stop("unexpected shutdown sentinel")
            except KeyboardInterrupt:
                controller.request_stop("KeyboardInterrupt")
            except BaseException as error:
                primary = error
                controller.request_stop("server exception")
            else:
                if not controller.requested:
                    primary = RuntimeError(
                        "server main returned without a shutdown request"
                    )
                    controller.request_stop("unexpected main return")
            if controller.started:
                controller.finish(join_timeout)
                finished = True
    except BaseException as error:
        primary = primary or error
        controller.request_stop("signal setup failure")

    if controller.started and not finished:
        controller.finish(join_timeout)
    failures = controller.failures
    if primary is not None:
        for failure in failures:
            try:
                primary.add_note(f"Foundation shutdown also failed: {failure!r}")
            except AttributeError:
                break
        raise primary
    if failures:
        return 1
    if controller.requested:
        controller.emit_stopped(output)
    return 0
