"""Foundation-owned GAME connection teardown without editing frozen V141."""
from __future__ import annotations

import functools
import sys
import threading
import types
from typing import Any, Protocol


class ConnectionState(Protocol):
    def close_connection(self) -> bool: ...


def _report_secondary(primary: BaseException, secondary: BaseException) -> None:
    message = f"Foundation GAME teardown also failed: {secondary!r}"
    try:
        primary.add_note(message)
    except AttributeError:
        pass
    print(f"[FOUNDATION!] {message}", file=sys.stderr)


def _report_standalone(error: BaseException) -> None:
    print(
        f"[FOUNDATION!] Foundation GAME teardown failed: {error!r}",
        file=sys.stderr,
    )


class GameConnectionBindings:
    """Bind one accepted GAME socket to one connection-local state per thread."""

    def __init__(self) -> None:
        self._local = threading.local()

    def accepted(self, raw_socket: Any) -> "AcceptedGameSocket":
        if getattr(self._local, "pending", None) is not None:
            raise RuntimeError("GAME connection already pending on listener thread")
        wrapped = AcceptedGameSocket(raw_socket, self)
        self._local.pending = wrapped
        return wrapped

    def bind(self, state: ConnectionState) -> None:
        pending = getattr(self._local, "pending", None)
        if pending is None:
            raise RuntimeError("GAME state constructed without an accepted connection")
        pending.bind(state)

    def release(self, connection: "AcceptedGameSocket") -> bool:
        if connection.released:
            return False
        if getattr(self._local, "pending", None) is not connection:
            raise RuntimeError("GAME connection/state correlation mismatch")
        self._local.pending = None
        connection.released = True
        if connection.state is None:
            return False
        return connection.state.close_connection()

    def abort_pending(self, primary: BaseException | None) -> None:
        pending = getattr(self._local, "pending", None)
        if pending is None:
            return
        pending.abort(primary)


class AcceptedGameSocket:
    """Socket proxy whose exit closes only its bound Foundation lease."""

    def __init__(self, raw_socket: Any, bindings: GameConnectionBindings) -> None:
        self._raw_socket = raw_socket
        self._bindings = bindings
        self.state: ConnectionState | None = None
        self.released = False

    def bind(self, state: ConnectionState) -> None:
        if self.state is not None:
            raise RuntimeError("GAME connection already has a state")
        self.state = state

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_socket, name)

    def __enter__(self) -> "AcceptedGameSocket":
        self._raw_socket.__enter__()
        return self

    def _release_without_masking(self, primary: BaseException | None) -> None:
        try:
            self._bindings.release(self)
        except BaseException as close_error:
            if primary is None:
                _report_standalone(close_error)
            else:
                _report_secondary(primary, close_error)

    def __exit__(self, exc_type, exc, traceback) -> bool:
        suppressed = False
        socket_error: BaseException | None = None
        try:
            suppressed = bool(self._raw_socket.__exit__(exc_type, exc, traceback))
        except BaseException as error:
            socket_error = error

        primary = exc if exc is not None else socket_error
        self._release_without_masking(primary)
        if socket_error is not None:
            if exc is not None:
                _report_secondary(exc, socket_error)
                return False
            raise socket_error
        return suppressed

    def abort(self, primary: BaseException | None) -> None:
        socket_error: BaseException | None = None
        try:
            self._raw_socket.close()
        except BaseException as error:
            socket_error = error
        effective_primary = primary if primary is not None else socket_error
        self._release_without_masking(effective_primary)
        if socket_error is not None:
            if primary is not None:
                _report_secondary(primary, socket_error)
            else:
                raise socket_error


class ListeningGameSocket:
    """Wrap only the socket created inside the cloned GAME listener."""

    def __init__(self, raw_socket: Any, bindings: GameConnectionBindings) -> None:
        self._raw_socket = raw_socket
        self._bindings = bindings

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_socket, name)

    def __enter__(self) -> "ListeningGameSocket":
        self._raw_socket.__enter__()
        return self

    def accept(self):
        connection, address = self._raw_socket.accept()
        return self._bindings.accepted(connection), address

    def __exit__(self, exc_type, exc, traceback) -> bool:
        pending_error: BaseException | None = None
        try:
            self._bindings.abort_pending(exc)
        except BaseException as error:
            pending_error = error

        listener_error: BaseException | None = None
        suppressed = False
        try:
            suppressed = bool(self._raw_socket.__exit__(exc_type, exc, traceback))
        except BaseException as error:
            listener_error = error

        primary = exc
        for secondary in (pending_error, listener_error):
            if secondary is None:
                continue
            if primary is None:
                primary = secondary
            else:
                _report_secondary(primary, secondary)
        if exc is None and primary is not None:
            raise primary
        return suppressed


class GameSocketFacade:
    """Delegate socket constants/types while wrapping the GAME listener socket."""

    def __init__(self, socket_module: Any, bindings: GameConnectionBindings) -> None:
        self._socket_module = socket_module
        self._bindings = bindings

    def __getattr__(self, name: str) -> Any:
        return getattr(self._socket_module, name)

    def socket(self, *args, **kwargs) -> ListeningGameSocket:
        return ListeningGameSocket(
            self._socket_module.socket(*args, **kwargs), self._bindings,
        )


def adapt_game_listener(original, bindings: GameConnectionBindings, socket_module):
    """Run frozen listener code with late-bound globals and a GAME socket facade."""
    @functools.wraps(original)
    def adapted(*args, **kwargs):
        # V141 main updates globals such as HOST after this adapter is installed.
        # Snapshot only when the GAME listener thread actually begins.
        listener_globals = dict(original.__globals__)
        listener_globals["socket"] = GameSocketFacade(socket_module, bindings)
        listener = types.FunctionType(
            original.__code__, listener_globals, original.__name__,
            original.__defaults__, original.__closure__,
        )
        listener.__kwdefaults__ = original.__kwdefaults__
        return listener(*args, **kwargs)

    adapted.__foundation_original_code__ = original.__code__
    return adapted
