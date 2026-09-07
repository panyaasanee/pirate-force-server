"""The UI-B arming proof has to be able to FAIL, and its tokens must be ASCII.

A proof run that prints ``RESULT=PASS`` on every tree is not a proof, it is
a decoration: ka1-A re-runs it on the current main commit before an attended
boot and culls the ticket when it does not reproduce, which only means
anything if a broken tree makes it say FAIL.  These tests break the tree on
purpose (patching the module the proof drives) and assert the line flips.
"""

from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import logout_hypothesis  # noqa: E402
from pirateforce_foundation import ui_logout_exit_game  # noqa: E402
from pirateforce_foundation import ui_logout_exit_game_headless as H  # noqa: E402


class ArmingProofTests(unittest.TestCase):
    def test_the_real_click_proof_passes_on_this_tree(self):
        line = H.prove_the_exit_game_click()
        self.assertTrue(line.startswith(H.TOKEN_PREFIX + " "), line)
        self.assertIn("ack=1", line)
        self.assertIn("lease_closed=1", line)
        self.assertIn("closer_called=1", line)
        self.assertIn("relogin_after=ok", line)
        # Pinned to the number PF_LOGOUT_CLOSE001 measured, not to the
        # dispatcher's own default -- pf-adversary F5: the tautology let
        # DEFAULT_CLOSE_DELAY_MS = 0 (a known-bad variant) print PASS.
        self.assertEqual(logout_hypothesis.LOGOUT_CLOSE_DELAY_MS, 250)
        self.assertIn("close_scheduled_ms=250", line)
        self.assertTrue(line.endswith("RESULT=PASS"), line)

    def test_the_control_line_passes_and_names_subcode_three(self):
        line = H.prove_back_to_select_is_left_alone()
        self.assertIn("subcode=3", line)
        self.assertIn("ui_actions=0", line)
        self.assertIn("lease_still_open=1", line)
        self.assertTrue(line.endswith("RESULT=PASS"), line)

    def test_a_dead_teardown_makes_the_proof_say_fail(self):
        # The exact regression the token exists to catch: the branch is
        # still there, still classified, and answers with nothing.
        dead = ui_logout_exit_game.ExitGameLogoutOutcome(False, "wrong_sequence")
        with mock.patch.object(
            ui_logout_exit_game, "dispatch_real_exit_game_logout",
            return_value=dead,
        ):
            line = H.prove_the_exit_game_click()
        self.assertTrue(line.endswith("RESULT=FAIL"), line)
        self.assertIn("ack=0", line)
        self.assertIn("lease_closed=0", line)

    def test_the_control_says_fail_if_this_lane_starts_answering_uia(self):
        real = ui_logout_exit_game.dispatch_real_exit_game_logout

        def answer_everything(*args, **kwargs):
            outcome = real(*args, **kwargs)
            if outcome.handled:
                return outcome
            return ui_logout_exit_game.ExitGameLogoutOutcome(
                True, "pretend",
                actions=(("UI_LOGOUT_EXIT_GAME_PRETEND", b"", b"", 0.0),),
            )

        with mock.patch.object(
            ui_logout_exit_game, "dispatch_real_exit_game_logout",
            side_effect=answer_everything,
        ):
            line = H.prove_back_to_select_is_left_alone()
        self.assertTrue(line.endswith("RESULT=FAIL"), line)
        self.assertIn("ui_actions=1", line)

    def test_every_token_line_is_pure_ascii(self):
        # The bridge console is cp874; one non-ASCII character in a token
        # takes the tool that reads it down (COMMON_LANE_ROUND).
        for line in (
            H.prove_the_exit_game_click(),
            H.prove_back_to_select_is_left_alone(),
        ):
            line.encode("ascii")

    def test_main_returns_nonzero_when_a_case_fails(self):
        dead = ui_logout_exit_game.ExitGameLogoutOutcome(False, "wrong_sequence")
        with mock.patch.object(
            ui_logout_exit_game, "dispatch_real_exit_game_logout",
            return_value=dead,
        ):
            self.assertEqual(H.main([]), 1)


class ServerSentTokenTests(unittest.TestCase):
    """The token an attended run reads off the console at click time."""

    def test_the_sent_token_is_printed_exactly_once_per_real_teardown(self):
        with mock.patch("builtins.print") as printed:
            line = H.prove_the_exit_game_click()
        self.assertTrue(line.endswith("RESULT=PASS"), line)
        sent = [
            call.args[0] for call in printed.call_args_list
            if call.args
            and str(call.args[0]).startswith(
                ui_logout_exit_game.TOKEN_ACK_COMPOSED)
        ]
        self.assertEqual(len(sent), 1, sent)
        self.assertIn("subcode=1", sent[0])
        self.assertIn("lease_closed=1", sent[0])
        sent[0].encode("ascii")

    def test_a_refused_exit_game_click_says_so_and_names_the_reason(self):
        with mock.patch("builtins.print") as printed:
            H.prove_back_to_select_is_left_alone()
        refused = [
            call.args[0] for call in printed.call_args_list
            if call.args
            and str(call.args[0]).startswith(
                ui_logout_exit_game.TOKEN_NOT_SENT)
        ]
        # subcode 3 is UI-A: this lane classifies it out BEFORE the refusal
        # helper, so it must stay silent and leave the frame to LANE-A.
        self.assertEqual(refused, [])

    def test_the_refusal_token_fires_for_a_real_exit_game_precondition(self):
        outcome = ui_logout_exit_game._refused("wrong_sequence")
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.reason, "wrong_sequence")

    def test_a_dead_console_cannot_take_the_listener_thread_down(self):
        """pf-adversary F1, measured: a bare print() raised here.

        Both token call sites sit after `close_connection()` has committed
        and the close timer is scheduled, and the exception would escape
        into v141's dispatch `try:` (which has a `finally:` and no
        `except:`) and end the game listener thread -- lease closed, ack
        never sent, nothing in `session.events`.  A closed stdout is the
        reproducer; `sys.stdout = None` is not (CPython no-ops that).
        """
        closed = io.StringIO()
        closed.close()
        with mock.patch.object(sys, "stdout", closed):
            outcome = ui_logout_exit_game._refused("repository_failure_OSError")
            ui_logout_exit_game._say("anything at all")
        self.assertEqual(outcome.reason, "repository_failure_OSError")

    def test_the_refusal_path_that_only_an_exception_reaches_is_covered(self):
        """The `except` branch pf-adversary F8 found untested by anything.

        It is also the branch where a raising print would REPLACE the
        original exception, so it is the one that most needs a test.
        """
        class _Blowing:
            logout_acknowledged = False
            teleport_sent = True
            runtime_ack_sent = True
            transport_socket_closer = staticmethod(lambda: None)

            class foundation:
                selected = object()

            def close_connection(self):
                raise OSError("disk went away")

        with mock.patch.object(
            ui_logout_exit_game.logout_hypothesis, "classify_logout_attempt",
            return_value="exact_01",
        ), mock.patch.object(
            ui_logout_exit_game.logout_hypothesis, "make_logout_ack_response",
            return_value=(b"pc", b"frame"),
        ):
            outcome = ui_logout_exit_game.dispatch_real_exit_game_logout(
                _Blowing(), object(), object(),
                close_timer_factory=lambda delay, cb: None,
            )
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.reason, "repository_failure_OSError")


if __name__ == "__main__":
    unittest.main()
