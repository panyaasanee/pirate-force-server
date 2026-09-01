"""Runtime hookup for the HYP-PF-040 dialog-open push (LOGOUT-DIALOG-OPEN-001).

Two earlier rounds built the pieces this file finally exercises together
through the real dispatcher:

* round ``bkgaq8`` (LANE-A) built the standalone dispatch function
  (``logout_dialog_open_hypothesis.py``) and its 12 direct-call unit tests
  (``tests/test_logout_dialog_open_hypothesis.py``), unwired.
* round ``liq4ri`` (chief, CORE-REQUEST) wired that function into
  ``runtime.py``'s top-level ``nested_id`` routing chain, but explicitly
  left no CLI/scenario construction path, so
  ``LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH`` could not yet be
  constructed by ``require_logout_hypothesis_scenario``'s five-item
  allowlist -- the routing branch it added was provably unreachable from
  any real boot.

This round adds the missing sixth allowlisted profile
(``logout_hypothesis.py``'s ``_PROFILE_DIALOG_OPEN`` /
``_EXPECTED_DIALOG_OPEN``) and its scenario file
(``scenarios/logout_hypothesis_dialog_open_push.json``), so
``--logout-hypothesis-scenario scenarios/logout_hypothesis_dialog_open_push.json``
(app.py's existing, generic ``--logout-hypothesis-scenario`` flag, unchanged)
now constructs a real state instance carrying this policy for the first
time. This file is the real end-to-end dispatch test that construction path
unblocks -- it does NOT flip ``logout_dialog_open_hypothesis.production_allowed``
on ``main`` (that stays ``False``, per docs/HYPOTHESIS_LEDGER.json's own
stop_rule: "Do not flip ... to True before an attended GT-184/GT-186 pass");
it only patches that flag True inside two tests to prove the wiring +
allowlist combination is correct together, the same throwaway-worktree
experiment pf-adversary already ran once (round liq4ri) but did not commit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    logout_dialog_open_hypothesis as dialog_open_mod,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    LOGOUT_ACK_FRAME_SHA256,
    LOGOUT_ACK_PC_SHA256,
    LOGOUT_CLOSE_DELAY_MS,
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_REQUEST_PCS,
    LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH,
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
    RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_PC_SIZE,
    WORLDINFO_PROBE_PAYLOADS,
    load_logout_hypothesis_scenario,
    make_logout_ack_response,
    make_return_select_server_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
DIALOG_OPEN_SCENARIO_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_dialog_open_push.json"
)
ECHO_SCENARIO_PATH = ROOT / "scenarios" / "logout_hypothesis_ack_echo.json"

# Same pinned R40 captured envelope prefixes
# test_logout_dialog_open_hypothesis.py / test_logout_worldinfo_first.py use.
WORLDINFO_FULL_PC_PREFIX = bytes.fromhex(
    "126F6E140000000008000B02120300124B3D0B00"
)
WORLDINFO_EMPTY_PC = bytes.fromhex(
    "126F6E140000000008000B02120100124B3D0B000B00"
)
GT002 = WORLDINFO_PROBE_PAYLOADS["capture_gt002"]


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


class LogoutDialogOpenScenarioWiredTests(unittest.TestCase):
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
            DIALOG_OPEN_SCENARIO_PATH
        )
        self.timer_factory = _RecordingTimerFactory()
        self.closer = _RecordingCloser()

    def tearDown(self):
        self.tmp.cleanup()

    _NO_SCENARIO_OVERRIDE = object()

    def _state(
        self, login, *,
        scenario=_NO_SCENARIO_OVERRIDE, ready=True, attach_closer=True,
    ):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            logout_hypothesis_scenario=(
                self.scenario
                if scenario is self._NO_SCENARIO_OVERRIDE else scenario
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

    def _full_form_pc(self):
        return WORLDINFO_FULL_PC_PREFIX + GT002

    def _logout_parsed(self, subcode):
        return self.legacy.parse_outer(LOGOUT_REQUEST_PCS[subcode])

    # --- the scenario is now constructible at all: the actual delta -----

    def test_scenario_loads_and_carries_the_new_policy(self):
        self.assertEqual(
            self.scenario.response_policy,
            LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH,
        )
        self.assertEqual(self.scenario.hypothesis_id, "HYP-PF-040")
        self.assertEqual(
            self.scenario.post_ack_action, LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        )
        self.assertEqual(self.scenario.close_delay_ms, LOGOUT_CLOSE_DELAY_MS)

    def test_scenario_allowlist_is_exact(self):
        data = json.loads(
            DIALOG_OPEN_SCENARIO_PATH.read_text(encoding="utf-8")
        )
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("test_only", False),
            lambda d: d["entry"].__setitem__("close_delay_ms", 5000),
            lambda d: d["entry"].__setitem__("post_ack_action", "none"),
            lambda d: d["entry"].__setitem__(
                "response_policy", "ack_only",
            ),
            lambda d: d["composed_responses"]["dialog_open_push"]
            .__setitem__("pc_sha256", "00" * 32),
            lambda d: d["composed_responses"]["dialog_open_push"]
            .__setitem__("vital_id", 0x1B40),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_logout_hypothesis_scenario(tampered)

    # --- safe by default: production_allowed stays False on main --------

    def test_default_flag_false_leaves_worldinfo_frame_on_the_frozen_fallback(
        self,
    ):
        """With the module flag left False (its default on ``main``), the
        dialog-open branch is unreachable, so this frame must fall through
        to the exact same pre-existing default path a session with NO
        logout scenario at all takes -- proven here by direct comparison,
        not merely "list is not empty" -- rather than being swallowed or
        silently answered by this new profile."""
        self.assertIs(dialog_open_mod.production_allowed, False)
        state = self._state("do-default")
        actions = state.dispatch(self.legacy.parse_outer(self._full_form_pc()))
        baseline = self._state("do-default-baseline", scenario=None)
        baseline_actions = baseline.dispatch(
            self.legacy.parse_outer(self._full_form_pc())
        )
        self.assertEqual([a[0] for a in actions], [a[0] for a in baseline_actions])
        self.assertEqual(state.logout_dialog_open_push_count, 0)
        self.assertNotIn(
            dialog_open_mod.DIALOG_OPEN_PUSH_EVENT, state.events,
        )

    # --- with the flag patched True: the wiring + allowlist together ----

    def test_full_form_frame_pushes_pinned_response_once(self):
        with mock.patch.object(dialog_open_mod, "production_allowed", True):
            state = self._state("do-push")
            rx_before = state.rx_frames
            expected_pc, expected_frame = make_return_select_server_response(
                self.legacy,
            )
            actions = state.dispatch(
                self.legacy.parse_outer(self._full_form_pc())
            )
        self.assertEqual(actions, [
            (
                dialog_open_mod.DIALOG_OPEN_PUSH_LABEL,
                expected_pc, expected_frame, 0.0,
            ),
        ])
        self.assertEqual(len(actions[0][1]), RETURN_SELECT_SERVER_RESPONSE_PC_SIZE)
        self.assertEqual(
            len(actions[0][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SIZE,
        )
        self.assertEqual(_sha(actions[0][1]), RETURN_SELECT_SERVER_RESPONSE_PC_SHA256)
        self.assertEqual(
            _sha(actions[0][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
        )
        self.assertEqual(state.logout_dialog_open_push_count, 1)
        # No double-count: this dispatch's own unconditional increment is
        # the only one for this frame (it is a top-level routing branch,
        # not a nested call into _dispatch_worldinfo_observation).
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertIn(dialog_open_mod.DIALOG_OPEN_PUSH_EVENT, state.events)
        # The existing worldinfo-storage side effect is untouched under
        # this policy (this module's dispatch function does not store).
        self.assertIsNone(state.worldinfo_last_payload)

    def test_the_push_is_one_shot_across_two_frames(self):
        with mock.patch.object(dialog_open_mod, "production_allowed", True):
            state = self._state("do-oneshot")
            first = state.dispatch(
                self.legacy.parse_outer(self._full_form_pc())
            )
            second = state.dispatch(
                self.legacy.parse_outer(self._full_form_pc())
            )
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(state.logout_dialog_open_push_count, 1)
        self.assertIn(
            "logout_dialog_open_hypothesis_already_sent_no_reply",
            state.events,
        )

    def test_logoutvital_after_the_push_still_gets_ack_then_close(self):
        # Branch 6 only changes WHEN the 0x709E push happens; it does not
        # refuse the actual LogoutVital the way HYP-PF-031's chat-push
        # scenario deliberately does -- this scenario reuses the unchanged
        # HYP-PF-013 ack-then-close shape for that frame.
        with mock.patch.object(dialog_open_mod, "production_allowed", True):
            state = self._state("do-then-logout")
            session_id = state.foundation.session_id
            state.dispatch(self.legacy.parse_outer(self._full_form_pc()))
            expected_ack = make_logout_ack_response(self.legacy, 1)
            actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(actions, [
            (
                "HYP_PF_013_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE",
                expected_ack[0], expected_ack[1], 0.0,
            ),
        ])
        self.assertTrue(state.logout_acknowledged)
        self.assertTrue(state.logout_close_scheduled)
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row["closed_at"])
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)

    def test_other_logout_scenarios_are_unaffected(self):
        scenario = load_logout_hypothesis_scenario(ECHO_SCENARIO_PATH)
        with mock.patch.object(dialog_open_mod, "production_allowed", True):
            state = self._state("do-other", scenario=scenario)
            actions = state.dispatch(
                self.legacy.parse_outer(self._full_form_pc())
            )
            baseline = self._state("do-other-baseline", scenario=None)
            baseline_actions = baseline.dispatch(
                self.legacy.parse_outer(self._full_form_pc())
            )
        # Under the unrelated echo scenario the dialog-open branch is
        # unreachable (response_policy does not match, and this policy owns
        # nothing under the echo scenario either) so 0x3D4B keeps its
        # frozen inherited fallback path, byte-identical to no scenario at
        # all -- even with the module flag patched True.
        self.assertEqual(
            [a[0] for a in actions], [a[0] for a in baseline_actions],
        )
        self.assertFalse(
            [e for e in state.events if "dialog_open" in e]
        )


if __name__ == "__main__":
    unittest.main()
