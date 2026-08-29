"""A refused chat `/warp` names the destinations it would have accepted.

THE DEFECT THIS FILE PINS, which is a testing-throughput one and not a
cosmetic one.  Round `qq0i9u` gave the CONFIG path a way out: an operator
whose hand-edited `gm_login_scene.json` names an unreachable scene gets a
console line carrying the file, the account, the scene AND the admissible
scene ids (`login_scene_override.CONFIG_REFUSED_CONSOLE_TOKEN`).  The CHAT
path -- the one an attended tester actually uses, in game, on every `GT-141`
and `GT-144` boot -- emitted `gm_chat_action_warp_stage_refused_
scene_has_no_login_entry` into the session's event list and nothing else.

So the person holding a shell and a text editor was told what to type next,
and the person sitting at a game client, who has neither (`config/` is in
`.gitignore`), was told only that they were wrong.  That is backwards:
`/warp` exists precisely so a tester can reach a scene WITHOUT a shell, and a
refusal with no way out sends them back to one.

WHAT IS NOT CLAIMED HERE.  Nothing in this file claims a byte reached a
client, that `/warp` moves anyone, or that any scene is reachable in game --
the console is the server's own stderr, and whether the owner's console shows
it is `GT-127`/`GT-141` territory, decided on a screen.  These are
module-layer facts about a line this lane writes.
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import login_scene_admission  # noqa: E402
from pirateforce_foundation.gm import login_scene_override  # noqa: E402
from pirateforce_foundation.gm import login_scene_stage  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class FakePosition:
    def __init__(self, scene_id=1, x=10.0, y=20.0, z=30.0):
        self.scene_id = scene_id
        self.scene_seq = 0
        self.x = x
        self.y = y
        self.z = z


class FakeSelected:
    def __init__(self, position=None):
        self.position = position
        self.id = 4242


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class FakeSession:
    def __init__(self, token="GM_ONE", position=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(FakeSelected(position))


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"

    def setUp(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.config_path = self.tmp / "gm_accounts.json"
        self.config_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.log_path = self.tmp / "capture" / "gm_command_log.ndjson"
        self.login_scene_config_path = self.tmp / "config" / "gm_login_scene.json"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def act(self, session, text):
        """Drive the real dispatch, capturing whatever it writes to stderr."""
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            action = chat_command_action.make_gm_chat_command_action(
                session,
                make_chat_payload(text),
                self.legacy,
                config_path=str(self.config_path),
                log_path=str(self.log_path),
                login_scene_config_path=str(self.login_scene_config_path),
            )
        return action, buffer.getvalue()

    def way_out_lines(self, console: str) -> list[str]:
        return [
            line
            for line in console.splitlines()
            if line.startswith(chat_command_action.WARP_REFUSED_CONSOLE_TOKEN)
        ]

    def an_unreachable_scene_id(self) -> int:
        """A scene id no login could enter, taken from the live predicate.

        Not a hardcoded number: lane A adds registry rows most days, and a
        constant here would quietly become a REACHABLE scene one morning and
        turn this whole file green for the wrong reason.
        """
        stageable = set(login_scene_admission.stageable_scene_ids())
        for candidate in range(1, 4000):
            if candidate not in stageable:
                return candidate
        raise AssertionError("every scene id is stageable -- rewrite this helper")


class TheRefusedWarpNamesTheWayOutTests(_Case):
    def test_a_scene_the_login_path_refuses_prints_the_ids_it_would_accept(self):
        session = FakeSession(position=FakePosition(scene_id=1))
        scene_id = self.an_unreachable_scene_id()

        action, console = self.act(session, f"/warp {scene_id}")

        self.assertIsNone(action, "a refused warp still sends nothing")
        lines = self.way_out_lines(console)
        self.assertEqual(1, len(lines), f"console was: {console!r}")
        line = lines[0]
        # Every field a tester needs to act, asserted one at a time so a
        # mutation that drops any single one is red on its own.
        self.assertIn(f"account='{self.GM_ACCOUNT}'", line)
        self.assertIn(f"scene_id={scene_id}", line)
        self.assertIn(f"reason={login_scene_stage.REASON_NO_LOGIN_ENTRY}", line)
        self.assertIn(
            str(login_scene_admission.stageable_scene_ids()),
            line,
            "the way out is the POINT of the line; printing the refusal "
            "without it is the defect this file exists for",
        )

    def test_the_ids_printed_are_the_live_predicate_not_a_frozen_copy(self):
        """A second implementation of the admissible set would drift.

        Pinned by moving the predicate, not by comparing two constants: if
        the line ever reads a private copy of the scene list, this is red.
        """
        session = FakeSession(position=FakePosition(scene_id=1))
        scene_id = self.an_unreachable_scene_id()
        with mock.patch.object(
            chat_command_action, "stageable_scene_ids", return_value=(1, 2, 3)
        ):
            _, console = self.act(session, f"/warp {scene_id}")
        self.assertIn("stageable=(1, 2, 3)", self.way_out_lines(console)[0])

    def test_the_line_goes_to_stderr_and_never_to_stdout(self):
        """`lane_hooks/__init__.py` 117-123: a token on stdout corrupted a
        `--json` artifact, because the tool that emitted it dispatches a chat
        frame.  This route sits on the same 0xAC52 branch and inherits that
        exposure exactly."""
        session = FakeSession(position=FakePosition(scene_id=1))
        scene_id = self.an_unreachable_scene_id()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            _, console = self.act(session, f"/warp {scene_id}")
        self.assertEqual(1, len(self.way_out_lines(console)))
        self.assertNotIn(
            chat_command_action.WARP_REFUSED_CONSOLE_TOKEN, out.getvalue()
        )

    def test_its_token_is_not_the_config_loaders_token(self):
        """Two different faults must not land in one grep.

        `GM_LOGIN_SCENE_CONFIG_REFUSED` means "a file on disk is malformed";
        this one means "the line you just typed named the wrong scene".  An
        operator hunting the first must not have to sift a tester's typos out
        of the same search.
        """
        self.assertNotEqual(
            login_scene_override.CONFIG_REFUSED_CONSOLE_TOKEN,
            chat_command_action.WARP_REFUSED_CONSOLE_TOKEN,
        )
        session = FakeSession(position=FakePosition(scene_id=1))
        scene_id = self.an_unreachable_scene_id()
        _, console = self.act(session, f"/warp {scene_id}")
        self.assertNotIn(
            login_scene_override.CONFIG_REFUSED_CONSOLE_TOKEN, console
        )


class OnlyTheReasonsADifferentDestinationWouldFixTests(_Case):
    """`stageable=` answers "which scene should I have typed", so it is
    printed only where that question fits.

    Two of these are safety, not tidiness: `not_gm_account` would hand the
    admissible-scene list to a caller the allowlist just refused, and the
    server-fault reasons would blame a tester's typing for something no
    typing can fix.
    """

    def _refuse_with(self, reason):
        return mock.patch.object(
            login_scene_stage,
            "stage_login_scene",
            return_value=login_scene_stage.StageResult(False, reason, 278, None),
        )

    def test_a_destination_reason_prints_the_way_out(self):
        for reason in (
            login_scene_stage.REASON_NO_LOGIN_ENTRY,
            login_scene_stage.REASON_UNKNOWN_SCENE,
        ):
            with self.subTest(reason=reason):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition(scene_id=1))
                with self._refuse_with(reason):
                    _, console = self.act(session, "/warp 278")
                self.assertEqual(
                    1, len(self.way_out_lines(console)), f"console: {console!r}"
                )

    def test_a_reason_no_retyping_could_fix_prints_nothing(self):
        for reason in (
            login_scene_stage.REASON_NOT_GM_ACCOUNT,
            login_scene_stage.REASON_CONFIG_UNREADABLE,
            login_scene_stage.REASON_WRITE_FAILED,
            login_scene_stage.REASON_CONFIG_NOT_WRITABLE,
        ):
            with self.subTest(reason=reason):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition(scene_id=1))
                with self._refuse_with(reason):
                    _, console = self.act(session, "/warp 278")
                self.assertEqual(
                    [], self.way_out_lines(console), f"console: {console!r}"
                )

    def test_a_warp_that_succeeds_prints_no_refusal_at_all(self):
        session = FakeSession(position=FakePosition(scene_id=1))
        stageable = login_scene_admission.stageable_scene_ids()
        target = next(
            scene for scene in stageable
            if scene != session.foundation.selected.position.scene_id
        )
        action, console = self.act(session, f"/warp {target}")
        self.assertIsNone(action, "a cross-scene warp stages, it does not send")
        self.assertEqual([], self.way_out_lines(console))


class TheLineNeverAltersDispatchTests(_Case):
    """`session.py`'s rule: A DIAGNOSTIC MAY NEVER ALTER DISPATCH.

    Held by the `try/except` around the print, not by the fold -- the
    distinction round `7gplcy` got backwards twice before pf-adversary
    measured it.  The refusal is the product; the line is the courtesy.
    """

    def test_a_console_that_refuses_the_write_costs_the_line_not_the_refusal(self):
        session = FakeSession(position=FakePosition(scene_id=1))
        scene_id = self.an_unreachable_scene_id()

        class HostileStream:
            encoding = "ascii"

            def write(self, _text):
                raise OSError("stderr is closed")

            def flush(self):
                raise OSError("stderr is closed")

        with mock.patch.object(sys, "stderr", HostileStream()):
            action = chat_command_action.make_gm_chat_command_action(
                session,
                make_chat_payload(f"/warp {scene_id}"),
                self.legacy,
                config_path=str(self.config_path),
                log_path=str(self.log_path),
                login_scene_config_path=str(self.login_scene_config_path),
            )

        self.assertIsNone(action)
        # The refusal reached the event trail even though the console did not.
        self.assertIn(
            f"{chat_command_action.EVENT_WARP_STAGE_REFUSED_PREFIX}"
            f"{login_scene_stage.REASON_NO_LOGIN_ENTRY}",
            session.events,
        )
        # AND THE COMMAND RAN TO COMPLETION, which is the property this test
        # is actually for.  Asserting the refusal alone is not enough: both
        # console prints happen AFTER that event is noted, so an unwrapped
        # print still leaves the refusal in the trail and only adds a crash
        # behind it.  A surviving `unexpected_` event is the blanket handler
        # catching what the diagnostic threw -- the console's fault, recorded
        # against the command.  (Measured: without this line, unwrapping
        # either print keeps every other assertion here green.)
        self.assertEqual(
            [],
            [
                event
                for event in session.events
                if event.startswith(chat_command_action.EVENT_UNEXPECTED_PREFIX)
            ],
            f"a hostile console must cost the line, not the command: "
            f"{session.events}",
        )
        # And nothing was staged for an account whose console blew up.
        self.assertFalse(self.login_scene_config_path.exists())


class TheAccountNameSurvivesTheConsoleTests(_Case):
    """The `qq0i9u`/`7gplcy` defect, re-pinned in the field this round adds.

    An account name is the one operator-controlled field on this line, and
    the two ways to fold it wrong are symmetrical: fold too little and a
    console that cannot encode it loses the line entirely; fold to ASCII
    always and a tester named `ทดสอบ` greps a `cp874` console -- a THAI code
    page, on a Thai-language project -- for their own account and finds
    nothing.  The fold is asked of the stream, so both worlds are right
    without anyone having to settle which console the owner runs.
    """

    THAI_ACCOUNT = "ทดสอบ"

    def _console_for_a_thai_gm(self, encoding):
        self.config_path.write_text(
            json.dumps({"gm_accounts": [self.THAI_ACCOUNT]}), encoding="utf-8"
        )
        session = FakeSession(
            token=self.THAI_ACCOUNT, position=FakePosition(scene_id=1)
        )
        scene_id = self.an_unreachable_scene_id()

        # Not an `io.StringIO`: its `encoding` is read-only, and the whole
        # point here is to present a console that ANNOUNCES a code page, the
        # way `runtime_console._Mirror` announces `utf-8` and the gate forces
        # `cp874`.  `console_safe` asks the stream what it can carry, so the
        # announcement is the input under test.
        class Stream:
            def __init__(self, encoding):
                self.encoding = encoding
                self._parts = []

            def write(self, text):
                # A real console raises on what it cannot encode; this one
                # does the same, so a fold that is too narrow loses the line
                # here exactly as it would there.
                text.encode(self.encoding)
                self._parts.append(text)
                return len(text)

            def flush(self):
                pass

            def getvalue(self):
                return "".join(self._parts)

        stream = Stream(encoding)
        with mock.patch.object(sys, "stderr", stream):
            chat_command_action.make_gm_chat_command_action(
                session,
                make_chat_payload(f"/warp {scene_id}"),
                self.legacy,
                config_path=str(self.config_path),
                log_path=str(self.log_path),
                login_scene_config_path=str(self.login_scene_config_path),
            )
        return stream.getvalue()

    def test_a_thai_name_reaches_a_thai_console_unfolded(self):
        console = self._console_for_a_thai_gm("cp874")
        self.assertIn(f"account='{self.THAI_ACCOUNT}'", console)

    def test_a_console_that_cannot_carry_it_still_gets_a_line(self):
        console = self._console_for_a_thai_gm("ascii")
        lines = self.way_out_lines(console)
        self.assertEqual(1, len(lines), f"console: {console!r}")
        # Visibly escaped, never a silent `?` and never a lost line.
        self.assertIn("\\u0e17", lines[0])


if __name__ == "__main__":
    unittest.main()
