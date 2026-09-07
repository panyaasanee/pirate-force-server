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
import tempfile
import types
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


class TokenNamesTheTreeItCameFromTests(unittest.TestCase):
    """pf-adversary F7 of round `uw3bxb`: the token named no commit.

    ka1-A re-runs this proof immediately before an attended boot and culls
    the ticket when the token does not reproduce (PANYA `20260907_0159`).
    Without these two fields, two tokens minted from different trees are the
    same string, and the ticket cannot be told which one it quotes.
    """

    def test_every_token_line_carries_head_and_code_before_the_result(self):
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            code = H.main([])
        self.assertEqual(code, 0)
        lines = [
            line for line in out.getvalue().splitlines()
            if line.startswith(H.TOKEN_PREFIX)
        ]
        self.assertEqual(len(lines), 3, lines)
        for line in lines:
            self.assertIn(" head=", line)
            self.assertIn(" code=", line)
            self.assertLess(
                line.index("code="), line.index("RESULT="),
                "the stamp must precede RESULT so a grep for the verdict "
                "keeps working unchanged: " + line,
            )

    def test_the_stamp_is_ascii_and_shaped_for_a_cp874_console(self):
        stamp = H.stamp()
        stamp.encode("ascii")  # raises on anything the bridge cannot print
        head, _, rest = stamp.partition(" ")
        self.assertTrue(head.startswith("head="), stamp)
        self.assertTrue(rest.startswith("code="), stamp)
        self.assertEqual(len(rest[len("code="):]), 12, stamp)

    def test_the_fingerprint_covers_every_module_the_proof_imported(self):
        # pf-adversary D1 of round `53yj9g`: the first version hashed a
        # hand-written four-name tuple, so a rewrite of `store.close_session`
        # that closed EVERY session of the account still printed PASS under a
        # byte-identical `code=`.  The list is derived from sys.modules now,
        # and these two names are the ones that measurement burned.
        names = {path.name for path in H.fingerprinted_files()}
        for required in ("store.py", "runtime.py", "logout_hypothesis.py",
                         "ui_logout_exit_game.py"):
            self.assertIn(required, names)
        self.assertGreater(
            len(names), 50,
            "the proof imports hundreds of modules; a handful means the "
            "derivation stopped working and code= went back to a list",
        )

    def test_code_fingerprint_is_over_the_file_bytes_not_the_module(self):
        # Drive it: a module of this package whose FILE changes must move the
        # digest, with no import machinery involved.
        with tempfile.TemporaryDirectory() as tmp:
            fake_file = Path(tmp) / "zzz_fake_module_for_this_test.py"
            fake_file.write_text("first\n", encoding="utf-8")
            fake = types.ModuleType("pirateforce_foundation.zzz_fake")
            fake.__file__ = str(fake_file)
            with mock.patch.dict(
                sys.modules,
                {"pirateforce_foundation.zzz_fake": fake},
            ):
                self.assertIn(fake_file, H.fingerprinted_files())
                before = H.code_fingerprint()
                fake_file.write_text("second\n", encoding="utf-8")
                after = H.code_fingerprint()
                fake_file.unlink()
                missing = H.code_fingerprint()
            without = H.code_fingerprint()
        self.assertNotEqual(before, after)
        self.assertNotEqual(after, missing)
        self.assertNotEqual(missing, without)
        self.assertEqual(len(before), 12)

    def test_head_commit_never_raises_and_says_unknown_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(H, "ROOT", Path(tmp)):
                self.assertEqual(H.head_commit(), "unknown")
                # A stamp is still printable when git is not there at all --
                # the proof runs on plain checkouts and must not die on one.
                self.assertIn("head=unknown", H.stamp())

    def test_head_commit_reads_a_ref_a_detached_head_and_packed_refs(self):
        sha = "0123456789abcdef0123456789abcdef01234567"
        for label, build in (
            ("ref", lambda git: (
                (git / "refs" / "heads").mkdir(parents=True),
                (git / "HEAD").write_text(
                    "ref: refs/heads/main\n", encoding="utf-8"),
                (git / "refs" / "heads" / "main").write_text(
                    sha + "\n", encoding="utf-8"),
            )),
            ("detached", lambda git: (
                (git / "HEAD").write_text(sha + "\n", encoding="utf-8"),
            )),
            ("packed", lambda git: (
                (git / "HEAD").write_text(
                    "ref: refs/heads/main\n", encoding="utf-8"),
                (git / "packed-refs").write_text(
                    "# pack-refs with: peeled\n"
                    + sha + " refs/heads/main\n",
                    encoding="utf-8"),
            )),
            # pf-adversary D7: a BRANCH worktree keeps HEAD beside a
            # `commondir` file and its refs in the common dir named there.
            # This shape printed `head=unknown` on a real `git worktree add
            # -b`, and a worktree rehearsal is what HOWTO_OPEN_A_PR asks for
            # before a push.
            ("branch-worktree", lambda git: (
                (git / "worktrees" / "wt").mkdir(parents=True),
                (git / "refs" / "heads").mkdir(parents=True),
                (git / "refs" / "heads" / "topic").write_text(
                    sha + "\n", encoding="utf-8"),
                (git / "worktrees" / "wt" / "HEAD").write_text(
                    "ref: refs/heads/topic\n", encoding="utf-8"),
                (git / "worktrees" / "wt" / "commondir").write_text(
                    "../..\n", encoding="utf-8"),
            )),
        ):
            with self.subTest(shape=label):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    git = root / ".git"
                    git.mkdir()
                    build(git)
                    if label == "branch-worktree":
                        # The checkout's `.git` is a FILE naming the
                        # per-worktree directory, exactly as git writes it.
                        root = root / "checkout"
                        root.mkdir()
                        (root / ".git").write_text(
                            "gitdir: %s\n"
                            % (git / "worktrees" / "wt"), encoding="utf-8")
                    with mock.patch.object(H, "ROOT", root):
                        self.assertEqual(H.head_commit(), sha[:12])


if __name__ == "__main__":
    unittest.main()
