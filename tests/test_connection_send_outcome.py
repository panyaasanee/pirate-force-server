"""CORE-REQUEST-GM-057: AcceptedGameSocket.sendall offers the send outcome
to an opt-in observer on the bound state without ever changing sendall's
own behavior toward its caller (v141's send loop).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.connection import GameConnectionBindings


class _RawSocket:
    def __init__(self, *, raises=None):
        self._raises = raises
        self.sent = []

    def sendall(self, data, *args, **kwargs):
        self.sent.append(data)
        if self._raises is not None:
            raise self._raises
        return None


class _StateWithHooks:
    def __init__(self):
        self.sent_calls = []
        self.failed_calls = []

    def close_connection(self):
        return False

    def on_game_frame_sent(self, data):
        self.sent_calls.append(data)

    def on_game_frame_send_failed(self, data, error):
        self.failed_calls.append((data, error))


class _StateWithoutHooks:
    def close_connection(self):
        return False


class _StateWithExplodingHook:
    def __init__(self):
        self.sent_calls = []

    def close_connection(self):
        return False

    def on_game_frame_sent(self, data):
        self.sent_calls.append(data)
        raise RuntimeError("observer blew up")

    def on_game_frame_send_failed(self, data, error):
        raise RuntimeError("observer blew up on failure too")


class SendOutcomeObserverTests(unittest.TestCase):
    def test_successful_send_reaches_raw_socket_and_notifies_observer(self):
        bindings = GameConnectionBindings()
        raw = _RawSocket()
        connection = bindings.accepted(raw)
        state = _StateWithHooks()
        bindings.bind(state)

        result = connection.sendall(b"frame-bytes")

        self.assertIsNone(result)
        self.assertEqual(raw.sent, [b"frame-bytes"])
        self.assertEqual(state.sent_calls, [b"frame-bytes"])
        self.assertEqual(state.failed_calls, [])

    def test_send_failure_still_raises_to_the_caller_unmasked(self):
        bindings = GameConnectionBindings()
        error = ConnectionResetError("peer reset")
        raw = _RawSocket(raises=error)
        connection = bindings.accepted(raw)
        state = _StateWithHooks()
        bindings.bind(state)

        with self.assertRaises(ConnectionResetError) as caught:
            connection.sendall(b"warp-frame")

        self.assertIs(caught.exception, error)
        self.assertEqual(state.sent_calls, [])
        self.assertEqual(state.failed_calls, [(b"warp-frame", error)])

    def test_state_without_hooks_is_unaffected_duck_typed_opt_in(self):
        bindings = GameConnectionBindings()
        raw = _RawSocket()
        connection = bindings.accepted(raw)
        bindings.bind(_StateWithoutHooks())

        result = connection.sendall(b"frame-bytes")

        self.assertIsNone(result)
        self.assertEqual(raw.sent, [b"frame-bytes"])

    def test_state_without_hooks_on_a_failed_send_still_raises(self):
        bindings = GameConnectionBindings()
        error = BrokenPipeError("gone")
        raw = _RawSocket(raises=error)
        connection = bindings.accepted(raw)
        bindings.bind(_StateWithoutHooks())

        with self.assertRaises(BrokenPipeError):
            connection.sendall(b"frame-bytes")

    def test_an_exploding_observer_does_not_change_sendall_s_own_outcome(self):
        bindings = GameConnectionBindings()
        raw = _RawSocket()
        connection = bindings.accepted(raw)
        state = _StateWithExplodingHook()
        bindings.bind(state)

        result = connection.sendall(b"frame-bytes")

        self.assertIsNone(result)
        self.assertEqual(raw.sent, [b"frame-bytes"])
        self.assertEqual(state.sent_calls, [b"frame-bytes"])

    def test_an_exploding_observer_on_failure_does_not_mask_the_send_error(self):
        bindings = GameConnectionBindings()
        error = ConnectionResetError("peer reset")
        raw = _RawSocket(raises=error)
        connection = bindings.accepted(raw)
        state = _StateWithExplodingHook()
        bindings.bind(state)

        with self.assertRaises(ConnectionResetError) as caught:
            connection.sendall(b"frame-bytes")

        self.assertIs(caught.exception, error)


if __name__ == "__main__":
    unittest.main()
