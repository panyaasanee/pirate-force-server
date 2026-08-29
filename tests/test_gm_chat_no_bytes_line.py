"""An ACCEPTED GM command that sent nothing says so on the console.

THE DEFECT THIS FILE PINS, measured through the real dispatcher this round
(round `tvbiqc`, the five inputs are reproduced in the round record):

    /warp 2 100 200 -> console: `LANE_GM_CHAT_ACTION warp route=action`
    /say hello      -> console: `LANE_GM_CHAT_ACTION say route=action`
    /lv 10          -> console: `LANE_GM_CHAT_ACTION lv route=action`
    /item 1001 5    -> console: `LANE_GM_CHAT_ACTION item route=action`
    /npc on 5       -> console: `LANE_GM_CHAT_ACTION npc route=action`
    /spawn 7        -> console: `LANE_GM_CHAT_ACTION spawn route=action`

and, in every one of those six, NOT ONE BYTE went to the client.  The route
line is printed before any handler runs -- it has always meant "this route
was reached" and nothing more -- so the last thing the console said about a
command that did nothing was a line that reads like success.  A REFUSED
command was better served than an accepted one: `/warp 9999` prints a scene
list, `/warp island` prints a usage line, and `/warp 2 100 200` -- the one
command that can move a character on screen, and the subject of `GT-128` --
printed a line an operator would read as "sent".

WHO PAYS: an attended tester types the warp, nothing moves, and the console
cannot separate "the version gate withheld the frame" (wiring fine, RE open)
from "the client ignored a frame we did send" (wiring fine, client answer)
from "the route is dead" (wiring broken).  The first two are PASS-shaped for
the wiring and the third is not.

WHAT IS NOT CLAIMED HERE
------------------------
Nothing in this file claims a byte reached a client, that anyone at a game
client sees any of this, or that any command became executable.  The line
goes to the SERVER HOST'S stderr and nowhere else -- the same rung
`_print_command_refusal_way_out` and `_print_warp_way_out` sit on, and the
same one `COO-DECISION 20260829_1344` ruled is the operator's, not the
tester's.  What changed is that an operator watching that console can now
tell a shut gate from a dead route; the tester at the client is exactly
where they were.
"""
from __future__ import annotations

import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands as gm_commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import login_scene_stage  # noqa: E402
from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# Not the real one -- RE-129 has not authorized any version to go out.  Only
# the audit-failure case patches it in, because that case needs a frame to
# exist before it can be dropped.
UNPROVEN_TEST_VERSION = 7

TOKEN = chat_command_action.WITHHELD_CONSOLE_TOKEN


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
    def __init__(self, scene_id=2, x=10.0, y=20.0, z=30.0):
        self.scene_id = scene_id
        self.scene_seq = 0
        self.x = x
        self.y = y
        self.z = z


class FakeSelected:
    def __init__(self, position=None):
        self.position = position
        self.id = 77


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

    def act(self, text, session=None, **kwargs):
        """One typed line through the real route; returns (action, stderr)."""
        session = session if session is not None else self.session()
        kwargs.setdefault("config_path", str(self.config_path))
        kwargs.setdefault("log_path", str(self.log_path))
        kwargs.setdefault(
            "login_scene_config_path", str(self.login_scene_config_path)
        )
        err = io.StringIO()
        out = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            action = chat_command_action.make_gm_chat_command_action(
                session, make_chat_payload(text), self.legacy, **kwargs
            )
        self.assertEqual(
            out.getvalue(),
            "",
            "no GM console line may reach stdout -- that is the lane_hooks"
            " --json artifact incident this lane already paid for once",
        )
        return action, err.getvalue()

    def session(self, token=None, position=None):
        return FakeSession(
            token=self.GM_ACCOUNT if token is None else token,
            position=FakePosition() if position is None else position,
        )

    def lines(self, stderr: str, token: str):
        return [ln for ln in stderr.splitlines() if ln.startswith(token)]


class TheSixSilentCommandsTests(_Case):
    """Each accepted command that sends nothing prints exactly one line."""

    CASES = (
        ("/warp 2 100 200", "warp", "withheld_force_pos_vital_version"),
        ("/say hello", "say", "withheld_gm_global_message_vital_version"),
        ("/lv 10", "lv", "refused_no_wire_path"),
        ("/item 1001 5", "item", "refused_no_wire_path"),
        ("/npc on 5", "npc", "refused_no_wire_path"),
        ("/spawn 7", "spawn", "refused_no_wire_path"),
    )

    def test_each_one_says_it_sent_nothing_and_names_the_blocker(self):
        for typed, name, why in self.CASES:
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                action, err = self.act(typed)
                self.assertIsNone(action, "no bytes may go out for any of these")
                said = self.lines(err, TOKEN)
                self.assertEqual(len(said), 1, err)
                self.assertIn(f"command={name} ", said[0])
                self.assertIn(f"why={why} ", said[0])
                # The blocker half is what makes the line worth printing: a
                # line that says "nothing happened" without naming what
                # would change that is the silence with extra steps.
                self.assertIn("blocked_on='", said[0])
                self.assertNotIn(
                    chat_command_action.NO_BLOCKER_RECORDED,
                    said[0],
                    "these six outcomes all have a named blocker",
                )

    def test_the_blocker_is_the_one_that_belongs_to_that_outcome(self):
        # A mutant that prints one hardcoded sentence for every command
        # passes the test above and is useless to the operator it is for.
        _, warp_err = self.act("/warp 2 100 200")
        gm_dispatch.reset_rate_limit_state_for_tests()
        _, say_err = self.act("/say hello")
        gm_dispatch.reset_rate_limit_state_for_tests()
        _, lv_err = self.act("/lv 10")
        self.assertIn("RE-129", warp_err)
        self.assertNotIn("RE-129", say_err)
        self.assertIn("gm/say_wire.py", say_err)
        self.assertNotIn("gm/say_wire.py", warp_err)
        self.assertIn("CORE-REQUEST-GM", lv_err)
        self.assertNotIn("CORE-REQUEST-GM", warp_err)

    def test_the_route_line_is_still_there(self):
        # The new line is an ADDITION.  `LANE_GM_CHAT_ACTION` is what an
        # attended GT-127 run greps for, and a round that "cleaned it up"
        # would fail that drill from the tester's chair, not here.
        _, err = self.act("/lv 10")
        self.assertEqual(
            len(self.lines(err, chat_command_action.CONSOLE_TOKEN)), 1, err
        )


class ItNeverPrintsWhatWasTypedTests(_Case):
    """The founding rule of every console line this module writes."""

    def test_a_say_body_never_reaches_the_console(self):
        _, err = self.act("/say NEEDLEALPHA NEEDLEBETA")
        self.assertIn(TOKEN, err)
        self.assertNotIn("NEEDLE", err)

    def test_command_arguments_never_reach_the_console(self):
        _, err = self.act("/item 424242 77771")
        self.assertIn(TOKEN, err)
        self.assertNotIn("424242", err)
        self.assertNotIn("77771", err)

    def test_a_name_outside_the_vocabulary_renders_unnamed(self):
        # A `GmCommand` is accepted "regardless of source" everywhere in this
        # lane, so the NAME is caller-chosen text until this line checks it.
        # The hostile value is also a line forgery: without the membership
        # check it would spell a second console line carrying another lane's
        # grep token.
        session = self.session()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chat_command_action._print_no_bytes_way_out(
                session,
                self.GM_ACCOUNT,
                "warp\nGM_CHAT_WARP_REFUSED account='x' scene_id=1",
                chat_command_action.OUTCOME_NO_WIRE_PATH,
            )
        printed = err.getvalue()
        self.assertEqual(len(printed.splitlines()), 1, printed)
        self.assertIn("command=unnamed ", printed)
        self.assertNotIn("GM_CHAT_WARP_REFUSED", printed)

    def test_a_newline_in_the_account_cannot_forge_a_line(self):
        session = self.session()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chat_command_action._print_no_bytes_way_out(
                session,
                "GM_ONE\nGM_CHAT_WARP_REFUSED account='x'",
                "lv",
                chat_command_action.OUTCOME_NO_WIRE_PATH,
            )
        printed = err.getvalue()
        self.assertEqual(len(printed.splitlines()), 1, printed)
        self.assertIn("\\n", printed)


class NoSecondLineTests(_Case):
    """A refusal that already explained itself is not explained twice."""

    def test_an_unknown_scene_keeps_its_scene_list_and_gains_nothing(self):
        action, err = self.act("/warp 9999")
        self.assertIsNone(action)
        self.assertEqual(
            len(self.lines(err, chat_command_action.WARP_REFUSED_CONSOLE_TOKEN)),
            1,
            err,
        )
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_a_sanctioned_but_barred_scene_keeps_its_blocker_line(self):
        action, err = self.act("/warp 126")
        self.assertIsNone(action)
        self.assertIn("blocker=", err)
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_a_stage_refusal_the_scene_printer_declines_still_gets_a_line(self):
        # `_print_warp_way_out` answers only DESTINATION_SHAPED_REASONS -- a
        # different destination cannot fix a server-side fault, so naming
        # one would blame the tester's typing.  That is right, and it used to
        # mean those refusals printed NOTHING.  This is the case that fails
        # if a later round decides the outcome word alone can tell whether a
        # line was printed.
        reason = login_scene_stage.REASON_WRITE_FAILED
        self.assertNotIn(reason, login_scene_stage.DESTINATION_SHAPED_REASONS)
        result = mock.Mock(staged=False, reason=reason, previous_scene_id=None)
        with mock.patch.object(
            login_scene_stage, "stage_login_scene", return_value=result
        ):
            action, err = self.act("/warp 278")
        self.assertIsNone(action)
        self.assertEqual(
            self.lines(err, chat_command_action.WARP_REFUSED_CONSOLE_TOKEN), [], err
        )
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertIn(f"why=refused_stage_{reason} ", said[0])
        self.assertIn(chat_command_action.NO_BLOCKER_RECORDED, said[0])

    def test_a_stage_refusal_that_raised_gets_the_type_name(self):
        with mock.patch.object(
            login_scene_stage, "stage_login_scene", side_effect=OSError("disk")
        ):
            action, err = self.act("/warp 278")
        self.assertIsNone(action)
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertIn("why=refused_stage_OSError ", said[0])
        # The exception's MESSAGE is not a field on this line -- type names
        # only, the rule this module states for every event it emits.
        self.assertNotIn("disk", err)


class ThingsThatMustStaySilentTests(_Case):
    def test_a_staged_cross_scene_warp_is_not_called_no_bytes(self):
        action, err = self.act("/warp 278")
        self.assertIsNone(action)
        self.assertEqual(self.lines(err, TOKEN), [], err)
        staged = json.loads(
            self.login_scene_config_path.read_text(encoding="utf-8")
        )["gm_login_scene"]
        self.assertEqual(staged[self.GM_ACCOUNT], 278)

    def test_a_staged_warp_that_carried_coordinates_is_also_silent(self):
        action, err = self.act("/warp 278 100 200")
        self.assertIsNone(action)
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_a_mistyped_command_keeps_its_usage_line_and_gains_nothing(self):
        action, err = self.act("/warp island")
        self.assertIsNone(action)
        self.assertEqual(
            len(
                self.lines(err, chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN)
            ),
            1,
            err,
        )
        self.assertEqual(self.lines(err, TOKEN), [], err)

    def test_an_ordinary_sentence_prints_nothing_at_all(self):
        # The founding rule: a GM's conversation is not decoded, matched or
        # written anywhere.  A backstop that fired here would put a console
        # line under every sentence anyone types.
        action, err = self.act("hello there, sailor")
        self.assertIsNone(action)
        self.assertEqual(err, "")

    def test_a_non_gm_account_gets_no_line_either(self):
        action, err = self.act("/lv 10", session=self.session(token="DECKHAND"))
        self.assertIsNone(action)
        self.assertEqual(self.lines(err, TOKEN), [], err)


class TheAuditFailurePathTests(_Case):
    """The one no-bytes path that reaches the end holding a real frame."""

    def test_a_dropped_frame_says_the_audit_row_is_why(self):
        session = self.session()
        with mock.patch.object(
            teleport_wire, "FORCE_POS_VITAL_VERSION_CONFIRMED", UNPROVEN_TEST_VERSION
        ), mock.patch.object(
            chat_command_action,
            "log_gm_command_outcome",
            # The real shape of this failure: the capture directory is
            # unwritable, which `_log_outcome` turns into False.  Patched at
            # the writer rather than at `_log_outcome` so the branch under
            # test is reached the way a boot reaches it.
            side_effect=OSError("read-only capture directory"),
        ):
            action, err = self.act("/warp 2 100 200", session=session)
        self.assertIsNone(action, "a frame that cannot be audited is not sent")
        said = self.lines(err, TOKEN)
        self.assertEqual(len(said), 1, err)
        self.assertIn("command=warp ", said[0])
        self.assertIn(
            f"why={chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN} ", said[0]
        )
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD,
            session.events,
        )

    def test_the_audit_word_is_not_an_audit_outcome(self):
        # It names a row that could not be written; putting it in the ndjson
        # vocabulary would invent an outcome no reader will ever find.
        self.assertNotIn(
            chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN,
            gm_commands.AUDIT_OUTCOMES,
        )
        self.assertFalse(
            chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN.startswith(
                gm_commands.AUDIT_OUTCOME_PREFIXES
            )
        )


class TheLineNeverAltersDispatchTests(_Case):
    """A diagnostic may never alter dispatch -- held the same way as the rest."""

    def test_a_none_stderr_is_named_and_costs_no_command(self):
        session = self.session()
        real = sys.stderr
        out = io.StringIO()
        try:
            sys.stderr = None
            with contextlib.redirect_stdout(out):
                action = chat_command_action.make_gm_chat_command_action(
                    session,
                    make_chat_payload("/lv 10"),
                    self.legacy,
                    config_path=str(self.config_path),
                    log_path=str(self.log_path),
                    login_scene_config_path=str(self.login_scene_config_path),
                )
        finally:
            sys.stderr = real
        self.assertIsNone(action)
        # `print(file=None)` writes to STDOUT: the incident this whole family
        # of guards exists to prevent.
        self.assertEqual(out.getvalue(), "")
        self.assertIn(
            f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr",
            session.events,
        )

    def test_a_stderr_that_raises_is_named_and_costs_no_command(self):
        class Hostile(io.StringIO):
            def write(self, *args, **kwargs):
                raise ValueError("closed stream")

        session = self.session()
        with contextlib.redirect_stderr(Hostile()):
            action = chat_command_action.make_gm_chat_command_action(
                session,
                make_chat_payload("/lv 10"),
                self.legacy,
                config_path=str(self.config_path),
                log_path=str(self.log_path),
                login_scene_config_path=str(self.login_scene_config_path),
            )
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}ValueError",
            session.events,
        )
        # The command's own event trail is intact: the console failing is not
        # allowed to look like the route refusing.
        self.assertIn("gm_chat_action_accepted_lv", session.events)

    def test_it_does_not_withhold_an_action_that_was_going_out(self):
        # The backstop runs on the same pass as a SENT command; a mutant
        # that returns early from `_make_action` after printing would take
        # the one command that works away from the tester.
        with mock.patch.object(
            teleport_wire, "FORCE_POS_VITAL_VERSION_CONFIRMED", UNPROVEN_TEST_VERSION
        ):
            action, err = self.act("/warp 2 100 200")
        self.assertIsNotNone(action)
        self.assertEqual(self.lines(err, TOKEN), [], err)


class ContractTests(_Case):
    def test_every_blocker_is_one_ascii_line_within_the_cap(self):
        for why, blocker in chat_command_action.NO_BYTES_BLOCKERS.items():
            with self.subTest(why=why):
                blocker.encode("ascii")
                why.encode("ascii")
                self.assertNotIn("\n", blocker)
                self.assertNotIn("\r", blocker)
                self.assertLessEqual(
                    len(blocker), chat_command_action.MAX_CONSOLE_HINT_LENGTH
                )

    def test_every_no_bytes_outcome_this_module_can_write_has_a_blocker(self):
        # The five constants below are every "nothing went out" outcome that
        # is a fixed word rather than a `<prefix><ExcType>` family.  A round
        # that adds a sixth and forgets the sentence gets a red test, not a
        # console line reading `no blocker recorded`.
        for outcome in (
            chat_command_action.OUTCOME_WARP_WITHHELD_NO_VERSION,
            chat_command_action.OUTCOME_SAY_WITHHELD_NO_VERSION,
            chat_command_action.OUTCOME_NO_WIRE_PATH,
            chat_command_action.OUTCOME_WARP_NO_POSITION,
            chat_command_action.OUTCOME_SAY_VERSION_CODEC_MISMATCH,
            chat_command_action.WHY_AUDIT_ROW_NOT_WRITTEN,
        ):
            with self.subTest(outcome=outcome):
                self.assertIn(outcome, chat_command_action.NO_BYTES_BLOCKERS)

    def test_the_token_is_its_own_grep(self):
        # Three tokens already answer three different questions on this
        # console; a fourth that shares a prefix with one of them would make
        # an operator's grep return the other's lines too.
        for other in (
            chat_command_action.CONSOLE_TOKEN,
            chat_command_action.WARP_REFUSED_CONSOLE_TOKEN,
            chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN,
        ):
            with self.subTest(other=other):
                self.assertFalse(TOKEN.startswith(other))
                self.assertFalse(other.startswith(TOKEN))

    def test_a_verdict_reports_whether_it_printed(self):
        # The backstop's only input besides the outcome word.  Default False
        # so a handler added later gets the line rather than silence.
        verdict = chat_command_action._Verdict(None, "refused_no_wire_path")
        self.assertFalse(verdict.line_printed)


if __name__ == "__main__":
    unittest.main()
