"""Runtime routing for RE-189 Job 2, branch 3 (the ack-first reorder).

CORE-REQUEST: pf_bridge/notes_to_chief/20260901_1844_LANE-A-CORE-REQUEST-
re189-branch2-built-branch3-needs-runtime-py-hyp041-ledger.md, section 3.
Lane A checked ``runtime.py`` before asking (the "no-guessing" rule) and
found the existing ``return_select_first`` branch hardcodes the
0x709E-before-ack order inline, with no parameter to swap.  This round
(chief, option (a) of the CORE-REQUEST) adds a new ``response_policy``
constant (``LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER``,
``logout_hypothesis.py``) and a sibling routing branch in ``runtime.py``
that composes the SAME two already-pinned composers --
``make_logout_ack_response`` and ``make_return_select_server_response`` --
in the reverse order: the ack goes out first, the 0x709E response goes
out second.  Neither composer is touched; only the calling order and
which frame is sent first change.  No new byte is invented anywhere.

THIS ROUND ADDS ROUTING ONLY.  No scenario JSON and no allowlisted
``LogoutHypothesisScenario`` profile exist yet for this policy -- that is
lane A's next-round work, the same two-step pattern HYP-PF-040 used
(``test_logout_dialog_open_scenario_wired.py``'s own docstring records
that precedent: chief wired an unreachable branch first, lane A added
the allowlisted profile + scenario file the following round).  So
``require_logout_hypothesis_scenario``'s allowlist correctly refuses any
scenario object carrying this ``response_policy`` today -- this is
demonstrated directly below
(``test_scenario_carrying_the_new_policy_is_not_yet_allowlisted``), not
merely asserted, and it is the reason this branch is provably
unreachable from any default boot this round.

To still prove the REAL dispatch path composes the reversed order
correctly (not just a unit-level composer call), the remaining tests
build the scenario in memory from the existing allowlisted
return-select-server profile's own pinned fields
(``dataclasses.replace``, changing only ``response_policy`` and the two
identifying fields) and patch ``require_logout_hypothesis_scenario`` at
its ``runtime.py`` import site to pass the value through unchanged for
the duration of one ``make_state_class`` call.  This is the same kind of
"prove the otherwise-unreachable branch is wired correctly first, wire
up real construction later" technique the dialog-open lane used
(``mock.patch.object(dialog_open_mod, "production_allowed", True)``),
applied here to the identity allowlist gate instead of a module flag
because the allowlist is the specific gate that blocks this branch from
any accepted construction path today.  The patch does not change the
allowlist itself, is reverted at the end of every ``with`` block, and
the unpatched test in this file proves the gate is intact on the
unmodified code path.
"""
from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    LOGOUT_ACK_FRAME_SHA256,
    LOGOUT_ACK_PC_SHA256,
    LOGOUT_CLOSE_DELAY_MS,
    LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER,
    LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
    LOGOUT_REQUEST_PCS,
    RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
    RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
    load_logout_hypothesis_scenario,
    make_logout_ack_response,
    make_return_select_server_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
RETURN_SELECT_SCENARIO_PATH = (
    ROOT / "scenarios" / "logout_hypothesis_return_select_server.json"
)

# The require_* guard is imported by name into runtime.py's own module
# namespace, so it must be patched there (not on logout_hypothesis) to
# affect what make_state_class actually calls.
_REQUIRE_GUARD_TARGET = (
    "pirateforce_foundation.runtime.require_logout_hypothesis_scenario"
)


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


class LogoutAckFirstReorderRoutingWiredTests(unittest.TestCase):
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
        # The only allowlisted profile that shares the pinned request/ack
        # SHA256s and the close-socket post-ack action this new branch
        # needs -- reused as the base so this in-memory probe scenario is
        # byte-identical to a real profile everywhere except the one
        # field under test.
        base = load_logout_hypothesis_scenario(RETURN_SELECT_SCENARIO_PATH)
        self.assertEqual(
            base.response_policy, LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
        )
        self.ack_first_scenario = dataclasses.replace(
            base,
            scenario_id="in_memory_ack_first_reorder_routing_probe_re189_branch3",
            hypothesis_id="RE-189-BRANCH-3-UNASSIGNED",
            response_policy=LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER,
        )
        self.timer_factory = _RecordingTimerFactory()
        self.closer = _RecordingCloser()

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, scenario, ready=True, attach_closer=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            logout_hypothesis_scenario=scenario,
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

    def _logout_parsed(self, subcode):
        return self.legacy.parse_outer(LOGOUT_REQUEST_PCS[subcode])

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        return None if row is None else row["closed_at"]

    # --- the routing branch is unreachable from any real construction ---

    def test_scenario_carrying_the_new_policy_is_not_yet_allowlisted(self):
        """No profile exists yet, so the real guard must refuse this value.

        This is the direct proof (not an assertion of intent) that the
        new branch cannot be reached by any accepted boot path this
        round -- exactly the state HYP-PF-040's routing branch was in
        before its own allowlisted profile landed.
        """
        with self.assertRaises(ValueError) as ctx:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                logout_hypothesis_scenario=self.ack_first_scenario,
                close_timer_factory=self.timer_factory,
            )
        self.assertIn("allowlist", str(ctx.exception))

    # --- with the allowlist guard patched: prove the wiring itself ------

    def test_subcode01_ack_first_then_return_select_through_real_dispatch(self):
        with mock.patch(_REQUIRE_GUARD_TARGET, side_effect=lambda v: v):
            state = self._state("arf01", scenario=self.ack_first_scenario)
            session_id = state.foundation.session_id
            self.assertIsNone(self._session_closed_at(session_id))
            expected_ack = make_logout_ack_response(self.legacy, 1)
            expected_rss = make_return_select_server_response(self.legacy)
            actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual(actions, [
            (
                "RE_189_BRANCH3_LOGOUT_SUBCODE01_ACK_FIRST",
                expected_ack[0], expected_ack[1], 0.0,
            ),
            (
                "RE_189_BRANCH3_LOGOUT_SUBCODE01_RETURN_SELECT_SERVER_"
                "RESPONSE_THEN_SERVER_SOCKET_CLOSE",
                expected_rss[0], expected_rss[1], 0.0,
            ),
        ])
        # Both frames are the unchanged pinned bytes -- only the order
        # changed.
        self.assertEqual(_sha(actions[0][1]), LOGOUT_ACK_PC_SHA256[1])
        self.assertEqual(_sha(actions[0][2]), LOGOUT_ACK_FRAME_SHA256[1])
        self.assertEqual(
            _sha(actions[1][1]), RETURN_SELECT_SERVER_RESPONSE_PC_SHA256,
        )
        self.assertEqual(
            _sha(actions[1][2]), RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256,
        )
        self.assertIsNotNone(self._session_closed_at(session_id))
        self.assertTrue(state.logout_acknowledged)
        self.assertTrue(state.logout_close_scheduled)
        self.assertIn(
            "logout_hypothesis_subcode01_ack_before_return_select_response",
            state.events,
        )
        self.assertEqual(
            [delay for delay, _cb in self.timer_factory.scheduled],
            [LOGOUT_CLOSE_DELAY_MS / 1000.0],
        )
        self.assertEqual(self.closer.calls, 0)
        self.timer_factory.fire_all()
        self.assertEqual(self.closer.calls, 1)

    def test_subcode03_ack_first_then_return_select_through_real_dispatch(self):
        with mock.patch(_REQUIRE_GUARD_TARGET, side_effect=lambda v: v):
            state = self._state("arf03", scenario=self.ack_first_scenario)
            expected_ack = make_logout_ack_response(self.legacy, 3)
            expected_rss = make_return_select_server_response(self.legacy)
            actions = state.dispatch(self._logout_parsed(3))
        self.assertEqual([label for label, *_ in actions], [
            "RE_189_BRANCH3_LOGOUT_SUBCODE03_ACK_FIRST",
            "RE_189_BRANCH3_LOGOUT_SUBCODE03_RETURN_SELECT_SERVER_"
            "RESPONSE_THEN_SERVER_SOCKET_CLOSE",
        ])
        self.assertEqual(actions[0][1:], (expected_ack[0], expected_ack[1], 0.0))
        self.assertEqual(actions[1][1:], (expected_rss[0], expected_rss[1], 0.0))

    def test_order_is_the_exact_reverse_of_return_select_first(self):
        """Same two pinned frames, opposite send order, side by side."""
        return_select_scenario = load_logout_hypothesis_scenario(
            RETURN_SELECT_SCENARIO_PATH
        )
        baseline_state = self._state(
            "arf-baseline", scenario=return_select_scenario,
        )
        baseline_actions = baseline_state.dispatch(self._logout_parsed(1))
        with mock.patch(_REQUIRE_GUARD_TARGET, side_effect=lambda v: v):
            reordered_state = self._state(
                "arf-reordered", scenario=self.ack_first_scenario,
            )
            reordered_actions = reordered_state.dispatch(self._logout_parsed(1))
        # return_select_first: [0x709E frame, ack frame]
        self.assertEqual(baseline_actions[0][1], reordered_actions[1][1])
        self.assertEqual(baseline_actions[0][2], reordered_actions[1][2])
        self.assertEqual(baseline_actions[1][1], reordered_actions[0][1])
        self.assertEqual(baseline_actions[1][2], reordered_actions[0][2])

    def test_missing_transport_closer_still_fails_closed(self):
        with mock.patch(_REQUIRE_GUARD_TARGET, side_effect=lambda v: v):
            state = self._state(
                "arf-nolever", scenario=self.ack_first_scenario,
                attach_closer=False,
            )
            session_id = state.foundation.session_id
            self.assertEqual(state.dispatch(self._logout_parsed(1)), [])
        self.assertIn(
            "logout_hypothesis_close_unavailable_no_reply", state.events,
        )
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertFalse(state.logout_acknowledged)
        self.assertEqual(self.timer_factory.scheduled, [])

    # --- isolation: unrelated, already-allowlisted scenarios untouched --

    def test_return_select_first_branch_labels_are_unaffected(self):
        return_select_scenario = load_logout_hypothesis_scenario(
            RETURN_SELECT_SCENARIO_PATH
        )
        state = self._state("arf-untouched", scenario=return_select_scenario)
        actions = state.dispatch(self._logout_parsed(1))
        self.assertEqual([label for label, *_ in actions], [
            "HYP_PF_028_LOGOUT_SUBCODE01_RETURN_SELECT_SERVER_RESPONSE_FIRST",
            "HYP_PF_028_LOGOUT_SUBCODE01_ACK_THEN_SERVER_SOCKET_CLOSE",
        ])
        self.assertFalse(
            [e for e in state.events if "ack_before_return_select" in e]
        )


if __name__ == "__main__":
    unittest.main()
