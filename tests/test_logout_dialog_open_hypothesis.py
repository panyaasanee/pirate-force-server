"""Direct-call tests for the branch-6 dialog-open push (RE-189 Job 2, #6).

~~This module is UNWIRED on ``main`` -- nothing in ``runtime.py`` imports or
calls ``dispatch_logout_dialog_open_hypothesis`` yet (see the module's own
docstring, "WHAT THE CORE-REQUEST NEEDS TO DO, EXACTLY").~~ STALE as of
``pirate-force-server`` main ``4ff782b`` (round `liq4ri`, PR #476): the
CORE-REQUEST wiring landed -- ``runtime.py`` now imports and calls
``dispatch_logout_dialog_open_hypothesis`` from a top-level ``nested_id``
routing branch (``runtime.py:5541-5559``). A fresh pf-adversary read this
round (LANE-A round `qw9tz4`) drove that wired branch through the real
``make_state_class``/``_dispatch_with_lanes`` chain in an isolated worktree
(not committed here) and confirmed no ``rx_frames`` double-count and a
correctly-enforced one-shot latch -- but that was a throwaway experiment,
not a committed test, and its allowlist bypass (there is still no
``LogoutHypothesisScenario`` profile carrying
``LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH`` -- see the open
CORE-REQUEST asking ``logout_hypothesis.py``'s owner for a sixth profile)
cannot ship in a committed test without also shipping a test-only allowlist
override. **What remains true and still applies below**: these tests still
drive the pure dispatch function directly with a minimal duck-typed
connection double, the same "responder's own logic, independent of the
still-missing runtime.py wiring" split ``test_lane_a_choose_npc_scene1.py``
uses for its own still-unwired module -- but the reason for that split is
now "no allowlisted scenario profile exists yet to construct a real wired
state instance with this policy", not "runtime.py doesn't call this
function yet". A real end-to-end ``runtime.py`` dispatch test is still
deferred, now to the round that adds the sixth allowlist profile.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    logout_dialog_open_hypothesis as dialog_open_mod,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.logout_dialog_open_hypothesis import (  # noqa: E402
    DIALOG_OPEN_PUSH_EVENT,
    DIALOG_OPEN_PUSH_LABEL,
    dispatch_logout_dialog_open_hypothesis,
)
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
    RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_PC_SIZE,
    WORLDINFO_PROBE_PAYLOADS,
    make_return_select_server_response,
)

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# Same pinned R40 captured envelope prefixes test_logout_worldinfo_first.py
# uses -- 20-byte GSCN_RunTimeProtocolReq v0, mask 0x02, nested 0x3D4B v0.
WORLDINFO_FULL_PC_PREFIX = bytes.fromhex(
    "126F6E140000000008000B02120300124B3D0B00"
)
WORLDINFO_EMPTY_PC = bytes.fromhex(
    "126F6E140000000008000B02120100124B3D0B000B00"
)
GT002 = WORLDINFO_PROBE_PAYLOADS["capture_gt002"]


def _sha(blob: bytes) -> str:
    import hashlib
    return hashlib.sha256(blob).hexdigest().upper()


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class FakeFoundation:
    def __init__(self, selected=object()):
        self.selected = selected


class FakeConnection:
    """The exact duck-typed surface this dispatch function is allowed to
    touch, per its own docstring: ``.events``, ``.foundation.selected``,
    ``.teleport_sent``, ``.runtime_ack_sent``,
    ``.logout_dialog_open_push_count``, ``.rx_frames``. Pinned for real by
    ``SurfaceTests`` below, not just this docstring sentence."""

    def __init__(
        self, *, selected=object(), teleport_sent=True,
        runtime_ack_sent=True, push_count=0,
    ):
        self.events = []
        self.foundation = FakeFoundation(selected)
        self.teleport_sent = teleport_sent
        self.runtime_ack_sent = runtime_ack_sent
        self.logout_dialog_open_push_count = push_count
        self.rx_frames = 0


class LogoutDialogOpenHypothesisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def _full_form_parsed(self):
        return self.legacy.parse_outer(WORLDINFO_FULL_PC_PREFIX + GT002)

    def _empty_form_parsed(self):
        return self.legacy.parse_outer(WORLDINFO_EMPTY_PC)

    # ----- the module flag ---------------------------------------------

    def test_production_allowed_is_false(self):
        self.assertIs(dialog_open_mod.production_allowed, False)

    # ----- refusal ladder -------------------------------------------------

    def test_classification_not_full_form_is_no_reply(self):
        conn = FakeConnection()
        actions = dispatch_logout_dialog_open_hypothesis(
            conn, self._empty_form_parsed(), self.legacy,
        )
        self.assertEqual(actions, [])
        self.assertIn(
            "logout_dialog_open_hypothesis_empty_form_no_reply", conn.events,
        )
        self.assertEqual(conn.logout_dialog_open_push_count, 0)
        self.assertEqual(conn.rx_frames, 1)

    def test_no_selected_character_is_no_reply(self):
        conn = FakeConnection(selected=None)
        actions = dispatch_logout_dialog_open_hypothesis(
            conn, self._full_form_parsed(), self.legacy,
        )
        self.assertEqual(actions, [])
        self.assertIn(
            "logout_dialog_open_hypothesis_no_selected_no_reply", conn.events,
        )
        self.assertEqual(conn.logout_dialog_open_push_count, 0)

    def test_wrong_sequence_teleport_not_sent_is_no_reply(self):
        conn = FakeConnection(teleport_sent=False)
        actions = dispatch_logout_dialog_open_hypothesis(
            conn, self._full_form_parsed(), self.legacy,
        )
        self.assertEqual(actions, [])
        self.assertIn(
            "logout_dialog_open_hypothesis_wrong_sequence_no_reply",
            conn.events,
        )

    def test_wrong_sequence_runtime_ack_not_sent_is_no_reply(self):
        conn = FakeConnection(runtime_ack_sent=False)
        actions = dispatch_logout_dialog_open_hypothesis(
            conn, self._full_form_parsed(), self.legacy,
        )
        self.assertEqual(actions, [])
        self.assertIn(
            "logout_dialog_open_hypothesis_wrong_sequence_no_reply",
            conn.events,
        )

    def test_already_sent_one_shot_is_no_reply(self):
        conn = FakeConnection(push_count=1)
        actions = dispatch_logout_dialog_open_hypothesis(
            conn, self._full_form_parsed(), self.legacy,
        )
        self.assertEqual(actions, [])
        self.assertIn(
            "logout_dialog_open_hypothesis_already_sent_no_reply",
            conn.events,
        )
        self.assertEqual(conn.logout_dialog_open_push_count, 1)

    def test_compose_refusal_value_error_is_caught_and_named(self):
        conn = FakeConnection()
        with mock.patch.object(
            dialog_open_mod, "make_return_select_server_response",
            side_effect=ValueError("drift"),
        ):
            actions = dispatch_logout_dialog_open_hypothesis(
                conn, self._full_form_parsed(), self.legacy,
            )
        self.assertEqual(actions, [])
        self.assertTrue(any(
            e.startswith(
                "logout_dialog_open_hypothesis_compose_refused_no_reply_"
            )
            for e in conn.events
        ), conn.events)
        self.assertEqual(conn.logout_dialog_open_push_count, 0)

    def test_compose_refusal_runtime_error_is_caught_and_named(self):
        conn = FakeConnection()
        with mock.patch.object(
            dialog_open_mod, "make_return_select_server_response",
            side_effect=RuntimeError("frame drift"),
        ):
            actions = dispatch_logout_dialog_open_hypothesis(
                conn, self._full_form_parsed(), self.legacy,
            )
        self.assertEqual(actions, [])
        self.assertTrue(any(
            e.startswith(
                "logout_dialog_open_hypothesis_compose_refused_no_reply_"
            )
            for e in conn.events
        ), conn.events)
        self.assertEqual(conn.logout_dialog_open_push_count, 0)

    # ----- the accepted trigger --------------------------------------------

    def test_full_form_pushes_the_pinned_frame_exactly_once(self):
        conn = FakeConnection()
        expected_pc, expected_frame = make_return_select_server_response(
            self.legacy,
        )
        actions = dispatch_logout_dialog_open_hypothesis(
            conn, self._full_form_parsed(), self.legacy,
        )
        self.assertEqual(actions, [
            (DIALOG_OPEN_PUSH_LABEL, expected_pc, expected_frame, 0.0),
        ])
        self.assertEqual(len(actions[0][1]), RETURN_SELECT_SERVER_RESPONSE_PC_SIZE)
        self.assertEqual(
            len(actions[0][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
        )
        self.assertEqual(
            _sha(actions[0][1]), RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
        )
        self.assertEqual(
            _sha(actions[0][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
        )
        self.assertEqual(conn.events.count(DIALOG_OPEN_PUSH_EVENT), 1)
        self.assertEqual(conn.logout_dialog_open_push_count, 1)
        self.assertEqual(conn.rx_frames, 1)

    def test_the_push_is_one_shot_across_two_calls_on_the_same_connection(self):
        conn = FakeConnection()
        first = dispatch_logout_dialog_open_hypothesis(
            conn, self._full_form_parsed(), self.legacy,
        )
        self.assertEqual(len(first), 1)
        second = dispatch_logout_dialog_open_hypothesis(
            conn, self._full_form_parsed(), self.legacy,
        )
        self.assertEqual(second, [])
        self.assertIn(
            "logout_dialog_open_hypothesis_already_sent_no_reply",
            conn.events,
        )
        self.assertEqual(conn.events.count(DIALOG_OPEN_PUSH_EVENT), 1)
        self.assertEqual(conn.logout_dialog_open_push_count, 1)
        self.assertEqual(conn.rx_frames, 2)

    def test_returned_action_shape_matches_the_project_wide_convention(self):
        """Every dispatch function in this project returns
        ``[(label, pc, frame, delay)]`` -- a 4-tuple list -- on success, the
        same shape ``_dispatch_logout_chat_push_hypothesis`` returns for its
        own HYP-PF-031 push."""
        conn = FakeConnection()
        actions = dispatch_logout_dialog_open_hypothesis(
            conn, self._full_form_parsed(), self.legacy,
        )
        self.assertEqual(len(actions), 1)
        label, pc, frame, delay = actions[0]
        self.assertIsInstance(label, str)
        self.assertIsInstance(pc, bytes)
        self.assertIsInstance(frame, bytes)
        self.assertEqual(delay, 0.0)


class SurfaceTests(unittest.TestCase):
    """What the module may read/write on the connection double, pinned by
    measurement rather than trusted from a docstring sentence (the same
    lesson ``test_gm_chat_command_action.py``'s own ``SessionSurfaceTests``
    exists to enforce)."""

    ALLOWED_ON_CONNECTION = {
        "events", "foundation", "teleport_sent", "runtime_ack_sent",
        "logout_dialog_open_push_count", "rx_frames",
    }
    ALLOWED_ON_FOUNDATION = {"selected"}

    def test_the_dispatch_touches_only_the_named_surface(self):
        legacy = _legacy()
        seen_connection = set()
        seen_foundation = set()

        class Watched:
            def __init__(self, seen, **attributes):
                object.__setattr__(self, "_seen", seen)
                for name, value in attributes.items():
                    object.__setattr__(self, name, value)

            def __getattribute__(self, name):
                if not name.startswith("_"):
                    object.__getattribute__(self, "_seen").add(name)
                return object.__getattribute__(self, name)

            def __setattr__(self, name, value):
                object.__getattribute__(self, "_seen").add(name)
                object.__setattr__(self, name, value)

        foundation = Watched(seen_foundation, selected=object())
        connection = Watched(
            seen_connection,
            events=[], foundation=foundation, teleport_sent=True,
            runtime_ack_sent=True, logout_dialog_open_push_count=0,
            rx_frames=0,
        )
        parsed = legacy.parse_outer(WORLDINFO_FULL_PC_PREFIX + GT002)
        actions = dispatch_logout_dialog_open_hypothesis(
            connection, parsed, legacy,
        )
        self.assertEqual(len(actions), 1)
        self.assertLessEqual(
            seen_connection, self.ALLOWED_ON_CONNECTION, seen_connection,
        )
        self.assertLessEqual(
            seen_foundation, self.ALLOWED_ON_FOUNDATION, seen_foundation,
        )
        # And the surface is actually exercised on the success path.
        self.assertIn("logout_dialog_open_push_count", seen_connection)
        self.assertIn("selected", seen_foundation)


if __name__ == "__main__":
    unittest.main()
