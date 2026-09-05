"""pf-adversary pass 2 on `#837` (round `w7gah1`): D1, D2, D6, D7.

The pass ran on MAIN, because `#837` had already merged -- `COO-DECISION
20260905_1747` item 2 says a finding there is a fix PR under the same round
code, which this is the pinning half of.  It came back NOT APPROVED with three
ship-blocking findings.  Two of them are closed here.  The third (D3, the
unserialized park/relabel window) and D4 (the twelve resync side effects this
lane cannot reach) are reported to the COO instead, because the fix for either
lives in `runtime.py`, which this lane may not edit (`AGENTS.md` section 7).

D1, CRITICAL, MEASURED WITH A CONTROL -- and a REGRESSION `#837` introduced.
`#837` taught the send-failure undo to put the in-memory scene label back.
That is right and stays.  But the label is one member of a set
`_gm_warp_resync_selected_scene` writes as a group, and restoring it alone
turned a loud failure into a false SUCCESS:

    restore OFF: the next walk step is a 43,413-unit MISMATCH, the token is
                 withheld -- correct, and correct for the wrong reason
    restore ON:  the walk step is in the same scene as the label, so
                 `distance_to_target` answers `unknown` (not `mismatch`),
                 `runtime.py:4227` reads "not a mismatch" as confirmation and
                 prints GM_WARP_POSITION_CONFIRMED for a warp whose frame
                 never reached the wire -- then notes
                 `client_confirmed_scene_1_warp_confirmed` and clears
                 `scene_label_is_server_guess`

A false green is worse than the defect it hid: the project's own warp proof
token is what every gate downstream reads.  The fix is that a send failure
also SHUTS the confirmation window the warp opened
(`warp_send_watch._disarm_warp_confirm_window`).

D2, HIGH, MEASURED.  On a park whose `previous_position` is missing, the
fallback delegate re-derives the row to revert from
`foundation.selected.position` -- which the resync has already moved to the
DESTINATION.  So the "rollback" wrote the durable row FORWARD, reported it as
`rolled_back`, and the next login landed in a scene the client was never sent
to.  The park held `previous_selected_scene_id` the whole time and the branch
did not use it.  Fixed by ORDER: put the label back first, then delegate.

D6, MAJOR, MEASURED.  Deleting the label carry-forward in `park_warp_send`
left 286 tests green -- the strings `previous_selected_scene_id` and
`_selected_scene_id` appeared in zero test files.  Pinned below.

D7, LOW.  `test_the_label_restored_is_the_one_given_not_the_rows` passes under
D1's own mutant, because it hands the value in directly and no row is
involved.  Not deleted -- deleting a test is not this lane's move -- but the
claim it was meant to make is made properly here, at the dispatch level, by
`test_the_departure_label_survives_a_replacement_park`.

NONCLAIM.  Headless and server-side.  Nothing here is evidence about a screen.
The GM road is used to reach these states at all; no account gains GM status
below (the fail-closed shapes are pinned as refusals in the sibling file), and
no milestone may be read off any of it.  In particular: this file makes
GM_WARP_POSITION_CONFIRMED harder to print, and that is a correction to the
evidence machinery, not a feature.
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import (  # noqa: E402
    accounts as gm_accounts,
    chat_command_action,
    warp_send_watch,
)
from pirateforce_foundation.model import Position  # noqa: E402

from test_gm_warp_send_watch import (  # noqa: E402
    DESTINATION_SCENE,
    RealDispatchSendFailureTests,
)


class ConfirmWindowDisarmTests(unittest.TestCase):
    """D1's mechanism, on its own, before the dispatch-level proof below."""

    class _Session:
        def __init__(self):
            self.gm_warp_position_pending = True
            self.gm_warp_confirm_window_open = True
            self.gm_warp_confirm_target = Position(2, 0, 1.0, 2.0, 3.0)
            self.gm_warp_confirm_target_reason = "warp"

    def test_every_armed_field_is_put_back_to_its_shut_value(self):
        session = self._Session()
        self.assertEqual(
            warp_send_watch.CONFIRM_WINDOW_DISARMED,
            warp_send_watch._disarm_warp_confirm_window(session),
        )
        for name, cleared in warp_send_watch.CONFIRM_WINDOW_ATTRIBUTES:
            with self.subTest(name=name):
                self.assertEqual(cleared, getattr(session, name))

    def test_an_already_shut_window_says_so_rather_than_claiming_a_disarm(self):
        session = self._Session()
        warp_send_watch._disarm_warp_confirm_window(session)
        self.assertEqual(
            warp_send_watch.CONFIRM_WINDOW_ALREADY_SHUT,
            warp_send_watch._disarm_warp_confirm_window(session),
        )

    def test_the_server_guess_flag_is_not_touched(self):
        """It is HONESTLY set after an undone warp -- the client confirmed
        nothing.  Restoring its pre-warp value is `CORE-REQUEST-GM-060`'s ask
        of chief, not a guess to be made here."""
        session = self._Session()
        session.scene_label_is_server_guess = True
        warp_send_watch._disarm_warp_confirm_window(session)
        self.assertTrue(session.scene_label_is_server_guess)

    def test_a_session_that_refuses_everything_answers_a_word(self):
        """`NEVER RAISES` is this module's contract, and this function runs on
        the failure path, where a second exception has nowhere to go."""

        class _Hostile:
            def __getattr__(self, name):
                raise RuntimeError("no attributes here")

            def __setattr__(self, name, value):
                raise RuntimeError("nor writes")

        self.assertEqual(
            warp_send_watch.CONFIRM_WINDOW_ALREADY_SHUT,
            warp_send_watch._disarm_warp_confirm_window(_Hostile()),
        )

    def test_the_attribute_names_are_the_ones_runtime_actually_arms(self):
        """Spelled once here, and checked against chief's file rather than
        remembered -- a silent third spelling is how this pin dies."""
        source = (ROOT / "src" / "pirateforce_foundation" / "runtime.py").read_text(
            encoding="utf-8"
        )
        for name, _cleared in warp_send_watch.CONFIRM_WINDOW_ATTRIBUTES:
            with self.subTest(name=name):
                self.assertIn(f"self.{name} =", source)


class FalseConfirmedTokenTests(RealDispatchSendFailureTests):
    """D1 through the real dispatch: the token must NOT print."""

    def test_a_walk_after_a_failed_warp_does_not_print_confirmed(self):
        token = "gm_confirm01"
        state, wrapped = self._production_state(
            token, error=ConnectionResetError(),
        )
        self._login_and_start(state, token)
        before = state.foundation.selected.position

        config_path = self._gm_config(token)
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(config_path)},
        ):
            actions = self._say(state, f"/warp {DESTINATION_SCENE}")
        frame = bytes(next(
            action[2] for action in actions
            if action[0] ==
            chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL
        ))
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(ConnectionResetError):
                wrapped.sendall(frame)

        # The window the warp opened is shut by the failure itself.
        self.assertFalse(getattr(state, "gm_warp_position_pending", False))
        self.assertIn(
            f"{warp_send_watch.EVENT_PREFIX}failed_"
            f"{warp_send_watch.CONFIRM_WINDOW_DISARMED}",
            state.events,
        )

        stream = io.StringIO()
        with redirect_stderr(stream):
            state.dispatch(self.legacy.parse_outer(
                self._target_pos_pc(before.x + 1.0, before.y + 1.0, before.z)
            ))

        # THE MEASUREMENT.  Before the fix this console line was present and
        # the trail carried `gm_warp_position_confirmed` plus
        # `client_confirmed_scene_1_warp_confirmed`, for a warp whose frame
        # raised ConnectionResetError on the way out.
        self.assertNotIn("GM_WARP_POSITION_CONFIRMED", stream.getvalue())
        self.assertNotIn("gm_warp_position_confirmed", state.events)
        self.assertFalse(
            any(
                event.startswith("client_confirmed_scene_")
                and event.endswith("_warp_confirmed")
                for event in state.events
            ),
            state.events,
        )
        # And the flag that exists to stay set until a REAL confirmation is
        # still set.  Clearing it was the second half of D1's damage.
        self.assertTrue(getattr(state, "scene_label_is_server_guess", False))


class DelegateBranchRollsBackwardTests(RealDispatchSendFailureTests):
    """D2: a park with no row must not roll the row FORWARD."""

    def test_a_park_without_a_row_still_lands_in_the_departure_scene(self):
        token = "gm_confirm02"
        state, wrapped = self._production_state(
            token, error=ConnectionResetError(),
        )
        self._login_and_start(state, token)
        before = state.foundation.selected.position

        config_path = self._gm_config(token)
        # The shape a transient read failure at compose time produces -- this
        # module's own `SendLockLivenessTests` measured
        # `rollback_refused_OperationalError` under 7s/12s contention, so a
        # pre-warp read that fails while the later write succeeds is not
        # hypothetical.
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(config_path)},
        ), mock.patch.object(
            chat_command_action, "row_before_warp", return_value=None,
        ):
            actions = self._say(state, f"/warp {DESTINATION_SCENE}")
        frame = bytes(next(
            action[2] for action in actions
            if action[0] ==
            chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL
        ))
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(ConnectionResetError):
                wrapped.sendall(frame)

        # MEASURED BEFORE THE FIX: `1 -> 2`, under the word `rolled_back`.
        self.assertEqual(
            before.scene_id, self._row(state).scene_id,
            "the delegate branch re-derives the row from the in-memory "
            "label; with the label left at the destination it wrote the row "
            "FORWARD and called it a rollback",
        )
        self.assertEqual(
            before.scene_id, state.foundation.selected.position.scene_id,
        )


class LabelCarryForwardTests(RealDispatchSendFailureTests):
    """D6/D7: the carry-forward that no test in the tree touched."""

    def test_the_departure_label_survives_a_replacement_park(self):
        """Two warps, then a failure: the label restored must be the one from
        BEFORE THE FIRST warp, not the one the second park found.

        This is the claim `test_the_label_restored_is_the_one_given_not_the_
        rows` was named for and could not make -- that test hands the value in
        directly, so nothing in it decides which value travels.  Deleting the
        four carry-forward lines in `park_warp_send` left 286 tests green;
        this one goes red.
        """
        token = "gm_confirm03"
        state, wrapped = self._production_state(
            token, error=ConnectionResetError(),
        )
        self._login_and_start(state, token)
        departure = state.foundation.selected.position.scene_id

        config_path = self._gm_config(token)
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(config_path)},
        ):
            self._say(state, f"/warp {DESTINATION_SCENE}")
            self.assertEqual(
                departure,
                warp_send_watch._parked_record(state).previous_selected_scene_id,
            )
            actions = self._say(state, f"/warp {DESTINATION_SCENE}")

        # The replacement park still names the FIRST warp's departure label.
        record = warp_send_watch._parked_record(state)
        self.assertEqual(departure, record.previous_selected_scene_id)

        frame = bytes(next(
            action[2] for action in actions
            if action[0] ==
            chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL
        ))
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(ConnectionResetError):
                wrapped.sendall(frame)

        self.assertEqual(
            departure, state.foundation.selected.position.scene_id,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
