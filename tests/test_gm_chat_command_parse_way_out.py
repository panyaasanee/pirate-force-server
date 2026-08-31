"""A mistyped GM command names the grammar it should have used (D8).

THE DEFECT THIS FILE PINS, measured through the real dispatcher and written
into `notes_to_chief/20260829_1252_LANE-GM-ASK-COO-who-reads-the-way-out.md`
section 3: `/warp 9999` got a way out, while `/warp island`, a bare `/warp`,
`/warp 3 100` and `/nonsense` printed NOTHING AT ALL.  The refusal happens
at the PARSE layer, upstream of every printer this lane owns, so the way out
added in round `c48x1n` could not reach it.  COO-DECISION `20260829_1344`
ruled the fix is the operator's console line (path (a)); a reply to the
client waits behind the same say-gate lock as `/say`.

THE SHAPE OF THE FIX, AND WHY IT IS NARROWER THAN THE FIRST ATTEMPT
-------------------------------------------------------------------
The first version printed the parse error's own message, which quotes the
offending token (`got 'island'`).  pf-adversary (round `9wy444`, D1)
measured what that means on the WIRED server rather than in a test:
`runtime.py:5140-5150` states that `session.token` is the process-wide
`--token` CLI value, NOT a per-connection authenticated login -- every
connection shares one identity.  So on the only configuration where this
feature fires, ANY player's typed sentence would have reached the
operator's console under the operator's own GM account, from a lane whose
founding rule is that a non-GM's chat is never decoded, pattern-matched or
written anywhere.

The line therefore carries NO CLIENT BYTES.  What a typed line can
influence is which of seven fixed sentences is printed -- six grammar lines
or all six joined.  That is the property this file spends most of its tests
on, because it is the one that can regress silently.

WHAT IS NOT CLAIMED HERE
------------------------
Nothing in this file claims a byte reached a client, that anyone at a game
client sees any of this, or that a command executed.  The line goes to the
SERVER HOST'S stderr.  These are module-layer facts about a line this lane
writes and about the silence it keeps everywhere else.
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
from pirateforce_foundation.gm import commands as gm_commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

TOKEN = chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN

# The four lines the ASK-COO measured as silent, plus the two shapes it did
# not type but that fail the same way (an unknown verb, and the sigil alone).
SILENT_BEFORE_THIS_ROUND = (
    "/warp island",
    "/warp",
    "/warp 3 100",
    "/warp 3 x y",
    "/nonsense",
    "/",
)

# Written as escapes, never as literals: this file is scanned by
# `test_gm_source_is_cp874_safe.py` and none of these characters has a cp874
# mapping.  RLO = the bidi override `has_format_characters` refuses.
RLO = "\u202e"
ZWSP = "\u200b"
HEBREW = "\u05d0\u05d1\u05d2"
CJK = "\u4e2d\u6587"
E_ACUTE = "\u00e9"


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class Utf8Console(io.StringIO):
    """A capture stream that ANNOUNCES `utf-8`, the way production does.

    `runtime_console._Mirror.encoding` is hardcoded `"utf-8"` (lines 24-47),
    and `console_safe` folds through whatever the stream says it is.  A bare
    `io.StringIO` reports NO encoding, so `console_safe` assumes the
    narrowest and escapes every non-ASCII character -- which means a test
    using one is green about an ASCII fold production never performs.

    pf-adversary (round `9wy444`, D8) got a mutation past the first version
    of this file through exactly that gap: making the format-character path
    echo the text it had just refused left all 37 tests green, because the
    StringIO console escaped the bidi character the assertion looked for.
    Every "X is not in the console" assertion here uses this stream instead.
    """

    encoding = "utf-8"


class StrictConsole(io.StringIO):
    """A stream that refuses what a real cp874 console refuses."""

    encoding = "cp874"

    def write(self, text):
        text.encode(self.encoding)  # raises the way the real console does
        return super().write(text)


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

    def dispatch(self, session, text):
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
            login_scene_config_path=str(self.login_scene_config_path),
        )

    def act(self, session, text, stream=None):
        """Drive the real dispatch, capturing what it writes to stderr.

        The default stream announces `utf-8` like `runtime_console._Mirror`
        does -- see `Utf8Console`.
        """
        buffer = stream if stream is not None else Utf8Console()
        with mock.patch.object(sys, "stderr", buffer):
            action = self.dispatch(session, text)
        return action, buffer.getvalue()

    def refusal_lines(self, console: str) -> list[str]:
        return [
            line for line in console.splitlines() if line.startswith(TOKEN)
        ]

    def printed_usage(self, line: str) -> str:
        return line.split("usage='", 1)[1].rsplit("'", 1)[0]

    def sentences_this_lane_wrote(self) -> set[str]:
        allowed = set(gm_commands.COMMAND_USAGE.values())
        allowed.add(" | ".join(gm_commands.COMMAND_USAGE.values()))
        allowed.add(chat_command.FORMAT_CHARACTER_REFUSAL_DETAIL)
        return allowed


class EveryLineThatWasSilentNowSpeaksTests(_Case):
    def test_each_measured_silent_line_prints_exactly_one_way_out(self):
        for text in SILENT_BEFORE_THIS_ROUND:
            with self.subTest(typed=text):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition(scene_id=1))

                action, console = self.act(session, text)

                self.assertIsNone(action, "a refused command still sends nothing")
                lines = self.refusal_lines(console)
                self.assertEqual(1, len(lines), f"console was: {console!r}")
                self.assertIn(f"account='{self.GM_ACCOUNT}'", lines[0])
                self.assertIn(chat_command.REFUSAL_PARSE_ERROR_PREFIX, lines[0])

    def test_the_line_says_what_to_type_instead_not_just_that_it_failed(self):
        """`reason=` alone is what `session.events` already carried.

        `command_parse_error_GmCommandParseError` is the SAME string for
        every line in `SILENT_BEFORE_THIS_ROUND`, so a console line carrying
        only that would tell an operator a command was refused and nothing
        whatever about what to do next -- which is not a way out.
        """
        session = FakeSession(position=FakePosition(scene_id=1))

        _, console = self.act(session, "/warp island")

        self.assertIn(
            gm_commands.COMMAND_USAGE["warp"], self.refusal_lines(console)[0]
        )

    def test_an_unknown_verb_gets_the_whole_vocabulary(self):
        """The question `/nonsense` asks is "what CAN I type".  Every command
        has to be in the answer -- and the answer reveals nothing about the
        line that prompted it, which is the other half of why it is the whole
        vocabulary rather than a guess at what was meant."""
        session = FakeSession(position=FakePosition(scene_id=1))

        _, console = self.act(session, "/nonsense")

        line = self.refusal_lines(console)[0]
        for usage in gm_commands.COMMAND_USAGE.values():
            self.assertIn(usage, line, f"missing usage for: {usage!r}")

    def test_the_usage_named_is_the_verb_that_failed_not_the_first_command(self):
        """A hint that ignored the verb would still pass the `/warp` cases
        above, because `warp` is first in the table."""
        session = FakeSession(position=FakePosition(scene_id=1))

        _, console = self.act(session, "/lv")

        line = self.refusal_lines(console)[0]
        self.assertIn(gm_commands.COMMAND_USAGE["lv"], line)
        self.assertNotIn(gm_commands.COMMAND_USAGE["warp"], line)

    def test_the_usage_is_the_live_grammar_and_not_a_second_copy_of_it(self):
        """Pinned by MOVING the grammar, not by comparing two constants.

        If this line ever grows its own private usage table, the day someone
        changes `COMMAND_USAGE` the parser and the way out start saying
        different things -- and a tester follows the wrong one.
        """
        session = FakeSession(position=FakePosition(scene_id=1))
        moved = dict(gm_commands.COMMAND_USAGE)
        moved["warp"] = "warp <PINNED-BY-TEST>"

        with mock.patch.object(gm_commands, "COMMAND_USAGE", moved):
            _, console = self.act(session, "/warp island")

        self.assertIn("warp <PINNED-BY-TEST>", self.refusal_lines(console)[0])


class NothingTypedEverReachesTheConsoleTests(_Case):
    """The contract `refusal_hint` exists to hold, tested from the wire.

    pf-adversary D1: `session.token` is the process-wide `--token`
    (`runtime.py:5140-5150`), so on the wired server EVERY connection is the
    GM account.  A line that echoed typed text would put any player's
    sentence on the operator's console under the operator's name, and
    `decode_local_talk_payload` discards the wire's `speaker` field, so it
    could not even attribute it honestly.

    Driven through the real dispatcher with text designed to be
    recognisable if ANY fragment survives, on a stream that announces
    `utf-8` so no ASCII fold hides the answer.
    """

    def needles(self):
        return (
            "island",
            "my-password-is-hunter2",
            HEBREW,          # printable, category Lo -- `repr` leaves it raw
            CJK,
            "GM_CHAT_WARP_REFUSED",        # a foreign console token
            "it's",                        # flips `repr` to double quotes
            "z" * 400,                     # long enough to be unmissable
        )

    def test_no_fragment_of_a_typed_word_appears_on_the_console(self):
        for needle in self.needles():
            with self.subTest(typed=needle[:24]):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition(scene_id=1))

                _, console = self.act(session, f"/warp {needle}")

                self.assertEqual(1, len(self.refusal_lines(console)))
                self.assertNotIn(needle, console)

    def test_a_typed_line_can_only_choose_among_the_lanes_own_sentences(self):
        """The strongest form of the claim: whatever is typed, the printed
        line is one this lane could have written before the client
        connected.  An echo, an OS message or a payload field fails this
        even if it happens to contain no obvious needle.
        """
        allowed = self.sentences_this_lane_wrote()

        for typed in (
            "/warp island",
            f"/warp {HEBREW}",
            "/say",
            "/nonsense",
            "/",
            f"/warp {RLO}1",
            "/lv two",
        ):
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition(scene_id=1))

                _, console = self.act(session, typed)

                line = self.refusal_lines(console)[0]
                self.assertIn(
                    self.printed_usage(line), allowed, f"line was: {line!r}"
                )

    def test_the_hint_field_itself_is_never_built_from_the_typed_text(self):
        """Asked of the field rather than the console, so a printer that
        started folding an echo away would still be red here."""
        allowed = self.sentences_this_lane_wrote()

        for typed in ("/warp island", "/nonsense", f"/warp {RLO}1", "/"):
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                outcome = chat_command.handle_local_talk_chat(
                    self.GM_ACCOUNT,
                    make_chat_payload(typed),
                    config_path=str(self.config_path),
                    log_path=str(self.log_path),
                )
                self.assertIn(outcome.refusal_hint, allowed)


class TheLineCannotBeFloodedOrForgedTests(_Case):
    def test_a_very_long_verb_cannot_produce_a_very_long_line(self):
        """A 1,900-character unknown verb once printed one console line 2,192
        characters wide, because the parse error quoted the whole verb.  With
        no echo the width is bounded by construction -- asserted anyway,
        because "bounded by construction" is a claim about a supplier and
        this is a property of the line."""
        session = FakeSession(position=FakePosition(scene_id=1))

        _, console = self.act(session, "/" + "z" * 1900)

        self.assertLess(len(self.refusal_lines(console)[0]), 400)

    def test_no_typed_line_can_produce_two_console_lines(self):
        """A second line is a forged line: an operator greps tokens, so a
        newline plus a token an attacker chooses is a fabricated report from
        a different part of this lane."""
        for text in (
            "/warp a\nGM_CHAT_WARP_REFUSED account='x' stageable=(1,)",
            "/warp a\rGM_LOGIN_SCENE_CONFIG_REFUSED file='x'",
            "/\nGM_CHAT_COMMAND_REFUSED account='root'",
        ):
            with self.subTest(typed=text):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition(scene_id=1))

                _, console = self.act(session, text)

                self.assertLessEqual(len(console.splitlines()), 1, repr(console))
                self.assertNotIn(
                    chat_command_action.WARP_REFUSED_CONSOLE_TOKEN, console
                )
                self.assertNotIn("GM_LOGIN_SCENE_CONFIG_REFUSED", console)

    def test_a_terminal_escape_sequence_never_reaches_the_console(self):
        """A raw escape can recolour, reposition or erase what is already on
        screen -- forging or hiding other lines in the same console the
        operator is being told to trust."""
        session = FakeSession(position=FakePosition(scene_id=1))

        _, console = self.act(session, "/warp \x1b[31mRED\x1b[0m")

        self.assertNotIn("\x1b", console)
        self.assertEqual(1, len(self.refusal_lines(console)))

    def test_the_format_character_refusal_is_rate_limited_like_the_rest(self):
        """MEASURED by pf-adversary (D3): `has_format_characters` used to run
        BEFORE the limiter, so this was the one refusal that could print
        without spending a slot -- 100 frames produced 100 console lines,
        against 20 from 100 `/warp island`.  Every line also lands in
        `server_console_live.err.txt`, so an unlimited one is an unbounded
        write driven from the wire."""
        session = FakeSession(position=FakePosition(scene_id=1))
        console = Utf8Console()

        for _ in range(100):
            self.act(session, f"/warp {ZWSP}1", stream=console)

        printed = len(self.refusal_lines(console.getvalue()))
        self.assertLessEqual(printed, 40, f"printed {printed} lines")

    def test_the_parse_refusal_is_rate_limited_too_which_is_the_control(self):
        """The comparison that makes the number above mean something."""
        session = FakeSession(position=FakePosition(scene_id=1))
        console = Utf8Console()

        for _ in range(100):
            self.act(session, "/warp island", stream=console)

        self.assertLessEqual(len(self.refusal_lines(console.getvalue())), 40)


class TheSilenceThatMustStayTests(_Case):
    """Every refusal this line must NOT speak for, one test each.

    The gate is `chat_command.TYPED_COMMAND_REFUSAL_PREFIXES`, and these are
    the cases that make it a gate rather than a formality.
    """

    def test_a_non_gm_typing_a_bad_command_gets_no_line_at_all(self):
        """The safety-order rule: this lane never decoded their chat.

        !! THIS TEST CANNOT SEE D1.  On the wired server there is no such
        session -- `session.token` is the process-wide `--token`, so every
        connection presents the GM's identity and this path is unreachable
        in production.  What it pins is that the MODULE refuses on identity;
        what protects the operator's console from a stranger's typing is
        `NothingTypedEverReachesTheConsoleTests`, not this.
        """
        session = FakeSession(token="NOT_A_GM", position=FakePosition(scene_id=1))

        action, console = self.act(session, "/warp island")

        self.assertIsNone(action)
        self.assertEqual([], self.refusal_lines(console))
        self.assertNotIn("island", console)

    def test_a_gm_chatting_normally_gets_no_line(self):
        """`not_a_command` is the most common outcome on this branch by
        orders of magnitude: it is every sentence a GM says out loud.  One
        console line each would bury the ones that mean something."""
        session = FakeSession(position=FakePosition(scene_id=1))

        _, console = self.act(session, "where is everyone")

        self.assertEqual([], self.refusal_lines(console))

    def test_a_rate_limited_command_prints_nothing_and_that_is_a_known_gap(self):
        """MEASURED by pf-adversary (D4), and pinned as a KNOWN LIMIT rather
        than fixed: the limiter runs before the parser, so a tester retyping
        `/warp island`, `/warp Island`, `/warp isle`... at 5/s loses the way
        out after about four seconds -- at the moment of maximum confusion.

        Not closed this round because printing here is the flood D3 is
        about.  Pinned so the round's claim cannot quietly widen to cover it.
        """
        session = FakeSession(position=FakePosition(scene_id=1))
        console = Utf8Console()
        for _ in range(30):
            self.act(session, "/warp island", stream=console)

        self.assertIn(
            f"{chat_command_action.EVENT_REFUSED_PREFIX}"
            f"{gm_dispatch.REFUSAL_RATE_LIMITED}",
            session.events,
            "the limiter has to have engaged for this to mean anything",
        )
        self.assertLess(
            len(self.refusal_lines(console.getvalue())),
            30,
            "a rate-limited line prints no way out today",
        )

    def test_the_gate_tuple_cannot_match_the_refusals_it_must_not(self):
        """The behavioural tests above pass through one prefix each; this
        one asks the gate itself, so a widened prefix (`""`, `"command"`,
        `"not"`) is red here even if the paths above stay green.

        `REFUSAL_LOOKUP_FAILED_PREFIX` is in this list because pf-adversary
        (D5) found it missing from the first version -- it is the "is my
        config broken" case, and it stays silent on this path.
        """
        for reason in (
            chat_command.REFUSAL_NOT_GM,
            chat_command.REFUSAL_NOT_A_COMMAND,
            chat_command.REFUSAL_PAYLOAD_TOO_LARGE,
            chat_command.REFUSAL_RATE_LIMITED,
            chat_command.REFUSAL_UNDECODABLE_PREFIX,
            chat_command.REFUSAL_LOG_QUOTA_EXCEEDED,
            chat_command.REFUSAL_LOG_WRITE_FAILED_PREFIX,
            gm_dispatch.REFUSAL_LOOKUP_FAILED_PREFIX,
        ):
            with self.subTest(reason=reason):
                self.assertFalse(
                    reason.startswith(
                        chat_command.TYPED_COMMAND_REFUSAL_PREFIXES
                    )
                )

    def test_a_command_that_parses_prints_no_refusal_line(self):
        """`/say hi` is accepted by the grammar.  A refusal line under a
        command that was NOT refused is a false report, and the operator has
        no way to tell it from a real one."""
        session = FakeSession(position=FakePosition(scene_id=1))

        _, console = self.act(session, "/say hello")

        self.assertEqual([], self.refusal_lines(console))


class TheFormatCharacterLineTests(_Case):
    """The sibling silence, closed in the same round and for the same reason.

    `has_format_characters` refuses a command line carrying bidi overrides
    or isolates -- and refused it with no console line either, which is the
    same "I typed something and nothing happened" the ASK-COO measured.
    """

    def test_it_prints_a_line_and_says_what_to_do(self):
        session = FakeSession(position=FakePosition(scene_id=1))

        action, console = self.act(session, f"/warp {RLO}1")

        self.assertIsNone(action)
        line = self.refusal_lines(console)[0]
        self.assertIn(chat_command.REFUSAL_UNSAFE_COMMAND_TEXT, line)
        self.assertIn("retype", line)

    def test_it_never_echoes_the_text_it_refused(self):
        """The whole reason that line is refused is that its bytes render in
        an order other than the one they are in.  Quoting it would carry
        that property straight into the operator's terminal.

        On a `utf-8`-announcing stream, which is what production has -- the
        first version of this test used a bare `StringIO`, whose ASCII fold
        escaped the character and made the assertion pass under a mutation
        that echoed the whole refused line (pf-adversary D8).
        """
        session = FakeSession(position=FakePosition(scene_id=1))

        _, console = self.act(session, f"/warp {RLO}SILENT1")

        self.assertNotIn(RLO, console)
        self.assertNotIn("SILENT", console)


class TheLineNeverAltersDispatchTests(_Case):
    """A DIAGNOSTIC MAY NEVER ALTER DISPATCH -- the rule this module quotes.

    The refusal is already decided when the line is written; the line is the
    courtesy.  Each test here breaks the console in a different way and
    asserts the command's fate is untouched.
    """

    def test_a_none_stderr_writes_nothing_to_stdout_and_names_the_failure(self):
        """`print(file=None)` writes to STDOUT -- the `lane_hooks` incident
        (`lane_hooks/__init__.py` 117-123) where a token landed inside
        another tool's `--json` artifact."""
        session = FakeSession(position=FakePosition(scene_id=1))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(sys, "stderr", None):
            action = self.dispatch(session, "/warp island")

        self.assertIsNone(action)
        self.assertNotIn(TOKEN, out.getvalue())
        self.assertIn(
            f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr",
            session.events,
        )

    def test_a_hostile_console_does_not_become_the_commands_fate(self):
        """MEASURED as a real regression on the sibling line: an unwrapped
        `print` sent the console's own error up through
        `make_gm_chat_command_action`, and the caller's blanket handler
        recorded `gm_chat_action_unexpected_OSError` -- every GM command
        failing, named after this module."""

        class HostileStream:
            encoding = "utf-8"

            def write(self, _text):
                raise OSError("console is gone")

            def flush(self):
                pass

        session = FakeSession(position=FakePosition(scene_id=1))
        with mock.patch.object(sys, "stderr", HostileStream()):
            action = self.dispatch(session, "/warp island")

        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_CONSOLE_WRITE_FAILED_PREFIX}OSError",
            session.events,
        )
        self.assertEqual(
            [],
            [
                event
                for event in session.events
                if event.startswith(chat_command_action.EVENT_UNEXPECTED_PREFIX)
            ],
            "the console's fault must never be reported as this lane's",
        )

    def test_the_event_trail_is_unchanged_by_the_new_line(self):
        session = FakeSession(position=FakePosition(scene_id=1))

        self.act(session, "/warp island")

        self.assertIn(
            f"{chat_command_action.EVENT_REFUSED_PREFIX}"
            f"{chat_command.REFUSAL_PARSE_ERROR_PREFIX}GmCommandParseError",
            session.events,
        )

    def test_a_parse_refusal_still_writes_no_audit_row(self):
        """The audit log records commands that PARSED.  A way-out line that
        also started logging mistyped lines would put a GM's typing into a
        file this lane's own docstrings promise it does not."""
        session = FakeSession(position=FakePosition(scene_id=1))

        self.act(session, "/warp island")

        self.assertFalse(self.log_path.exists(), "no row for a refused line")


class TheLineSurvivesTheConsoleItIsWrittenToTests(_Case):
    def test_a_typed_word_the_console_cannot_encode_cannot_lose_the_line(self):
        """The failure mode this design REMOVES rather than folds.

        pf-adversary (D2) measured the echoing version against a faithful
        `runtime_console._Mirror`: it ANNOUNCES `utf-8` while the real
        console forces `cp874:strict`, so `console_safe` folded nothing,
        `print` raised, the guard swallowed it, and BOTH the console and the
        retained log got nothing -- for exactly the inputs the feature was
        built for.  With no client bytes in the line there is nothing left
        that can be unencodable.
        """
        session = FakeSession(position=FakePosition(scene_id=1))

        for typed in (f"/warp {E_ACUTE}sland", f"/warp {HEBREW}", f"/warp {CJK}"):
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                console = StrictConsole()
                with mock.patch.object(sys, "stderr", console):
                    self.dispatch(session, typed)
                self.assertEqual(1, len(self.refusal_lines(console.getvalue())))

    def test_an_account_name_the_console_cannot_encode_still_prints(self):
        """The account name is OPERATOR-side (`gm_accounts.json`, `--token`),
        so it is folded rather than removed -- and round `qq0i9u` lost a
        refusal to exactly this: a name the console could not encode raised
        out of the print and the refusal was recorded nowhere."""
        name = f"GM_{E_ACUTE}"
        session = FakeSession(token=name, position=FakePosition(scene_id=1))
        self.config_path.write_text(
            json.dumps({"gm_accounts": [name]}), encoding="utf-8"
        )
        console = StrictConsole()
        with mock.patch.object(sys, "stderr", console):
            action = self.dispatch(session, "/warp island")

        self.assertIsNone(action)
        lines = self.refusal_lines(console.getvalue())
        self.assertEqual(1, len(lines), f"console was: {console.getvalue()!r}")
        self.assertIn(gm_commands.COMMAND_USAGE["warp"], lines[0])

    def test_the_line_goes_to_stderr_and_never_to_stdout(self):
        session = FakeSession(position=FakePosition(scene_id=1))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            _, console = self.act(session, "/warp island")

        self.assertEqual(1, len(self.refusal_lines(console)))
        self.assertNotIn(TOKEN, out.getvalue())

    def test_its_token_is_neither_of_the_two_tokens_already_in_use(self):
        """An operator greps one question at a time: "is my config broken",
        "is that scene reachable", "did I type that right" are three."""
        self.assertNotEqual(TOKEN, chat_command_action.WARP_REFUSED_CONSOLE_TOKEN)
        self.assertNotEqual(TOKEN, chat_command_action.CONSOLE_TOKEN)
        self.assertFalse(
            chat_command_action.WARP_REFUSED_CONSOLE_TOKEN.startswith(TOKEN)
        )
        self.assertFalse(
            TOKEN.startswith(chat_command_action.WARP_REFUSED_CONSOLE_TOKEN)
        )


class ThePrinterFoldsWhatItIsHandedTests(unittest.TestCase):
    """The printer's own guarantees, asked at the printer.

    `_print_command_refusal_way_out` reads its fields off an arbitrary
    object with `getattr`, so this IS its call shape, not a contrivance: the
    day a hint comes from somewhere other than `usage_hint_for`, these are
    the properties that still have to hold.
    """

    class Outcome:
        def __init__(self, reason, hint):
            self.refusal_reason = reason
            self.refusal_hint = hint
            self.command = None

    def printed(self, outcome, token="GM_ONE"):
        session = FakeSession()
        buffer = Utf8Console()
        with mock.patch.object(sys, "stderr", buffer):
            chat_command_action._print_command_refusal_way_out(
                session, token, outcome
            )
        return buffer.getvalue(), session

    def test_a_newline_in_the_hint_cannot_start_a_second_line(self):
        console, _ = self.printed(
            self.Outcome(
                f"{chat_command.REFUSAL_PARSE_ERROR_PREFIX}X",
                "boom\nGM_CHAT_WARP_REFUSED account='root' stageable=(1, 2)",
            )
        )
        lines = console.splitlines()
        self.assertEqual(1, len(lines), repr(console))
        self.assertIn("\\n", console)
        # ANCHORED AT LINE START, which is the honest claim.  The fold does
        # not delete a foreign token -- it keeps it QUOTED INSIDE this line.
        # What it prevents is a LINE that begins with a token its author
        # chose, which is what a reader scanning a console, and
        # `grep "^GM_CHAT_WARP_REFUSED"`, would count as a report from
        # another part of this lane.
        self.assertFalse(
            any(
                line.startswith(chat_command_action.WARP_REFUSED_CONSOLE_TOKEN)
                for line in lines
            )
        )

    def test_a_carriage_return_in_the_hint_cannot_overwrite_the_line(self):
        """`\\r` alone does not split a line, it REWINDS one: on a real
        terminal the text after it overwrites the token and account that came
        before, which is the same forgery by a different mechanism."""
        console, _ = self.printed(
            self.Outcome(
                f"{chat_command.REFUSAL_PARSE_ERROR_PREFIX}X", "boom\rall clear"
            )
        )
        self.assertNotIn("\r", console)
        self.assertIn("\\r", console)

    def test_a_newline_in_the_account_name_cannot_start_a_second_line(self):
        console, _ = self.printed(
            self.Outcome(f"{chat_command.REFUSAL_PARSE_ERROR_PREFIX}X", "boom"),
            token="GM\nGM_CHAT_WARP_REFUSED account='root'",
        )
        lines = console.splitlines()
        self.assertEqual(1, len(lines), repr(console))
        self.assertFalse(
            any(
                line.startswith(chat_command_action.WARP_REFUSED_CONSOLE_TOKEN)
                for line in lines
            )
        )

    def test_an_oversized_hint_from_another_supplier_is_capped_here(self):
        """pf-adversary D10: the first version's cap lived in the describer,
        so it was a property of that supplier rather than of this line -- and
        this function takes its fields from any object."""
        console, _ = self.printed(
            self.Outcome(f"{chat_command.REFUSAL_PARSE_ERROR_PREFIX}X", "y" * 5000)
        )
        self.assertLess(len(console), 600, "the printer holds its own bound")
        self.assertIn("...", console)

    def test_a_refusal_in_the_set_with_no_hint_still_prints(self):
        """A missing hint is a bug in this lane, not a reason to go back to
        silence: the operator still learns a command was refused."""
        console, _ = self.printed(
            self.Outcome(f"{chat_command.REFUSAL_PARSE_ERROR_PREFIX}X", None)
        )
        self.assertEqual(1, len(console.splitlines()))
        self.assertIn("no usage recorded", console)

    def test_a_reason_that_is_not_a_string_prints_nothing(self):
        """`getattr` can hand back anything.  `None.startswith` would raise
        inside a diagnostic, and this module's rule is that a diagnostic may
        never alter dispatch."""
        for reason in (None, 17, object()):
            with self.subTest(reason=type(reason).__name__):
                console, _ = self.printed(self.Outcome(reason, "boom"))
                self.assertEqual("", console)


class TheUsageHintItselfTests(unittest.TestCase):
    """Unit-layer facts about `commands.usage_hint_for`."""

    def test_every_command_name_has_a_usage_line(self):
        self.assertEqual(
            set(gm_commands.COMMAND_NAMES), set(gm_commands.COMMAND_USAGE)
        )

    def test_the_vocabulary_order_is_pinned_because_a_human_reads_it(self):
        """pf-adversary D9: reversing `COMMAND_USAGE` left the WHOLE SUITE
        green -- `test_gm_standalone_map_is_not_chat_writable.py` compares
        SETS, so nothing saw the order, while the order reaches a human twice
        (`expected one of (...)` and the joined vocabulary)."""
        self.assertEqual(
            # `gmprobe` appended last, deliberately: CORE-REQUEST-GM-043
            # added a LANE-GM tooling command after the owner's original
            # six (notes_to_chief 20260826_1630 section GM-003), and
            # growing the tuple by one at the end is a smaller drift than
            # reordering the six gameplay commands ahead of it.
            ("warp", "npc", "item", "lv", "spawn", "say", "gmprobe"),
            tuple(gm_commands.COMMAND_USAGE),
        )
        self.assertEqual(
            tuple(gm_commands.COMMAND_USAGE), gm_commands.COMMAND_NAMES
        )

    def test_the_parser_raises_the_same_sentences_the_usage_table_holds(self):
        """Two spellings of one grammar is the drift this table exists to
        prevent -- so the parser's arity errors must BE the table's values,
        not merely resemble them."""
        for name, usage in gm_commands.COMMAND_USAGE.items():
            with self.subTest(command=name):
                with self.assertRaises(gm_commands.GmCommandParseError) as caught:
                    gm_commands.parse_gm_command(name)
                self.assertEqual(usage, str(caught.exception))

    def test_an_unknown_verb_and_an_empty_body_get_the_whole_vocabulary(self):
        whole = " | ".join(gm_commands.COMMAND_USAGE.values())
        for body in ("nonsense", "", "   ", None, 17):
            with self.subTest(body=body):
                self.assertEqual(whole, gm_commands.usage_hint_for(body))

    def test_the_verb_is_read_case_insensitively_like_the_parser_reads_it(self):
        """`parse_gm_command` lowercases the verb, so `WARP island` fails as
        a warp.  A hint that did not would answer with the whole vocabulary
        and look like it had never heard of the command just typed."""
        self.assertEqual(
            gm_commands.COMMAND_USAGE["warp"],
            gm_commands.usage_hint_for("WARP island"),
        )

    def test_the_hint_is_one_of_seven_strings_for_any_input(self):
        """The property the whole design rests on, asked of the function
        directly and driven with inputs no grammar produced."""
        allowed = set(gm_commands.COMMAND_USAGE.values())
        allowed.add(" | ".join(gm_commands.COMMAND_USAGE.values()))
        for body in (
            f"warp {HEBREW}",
            "say " + "x" * 5000,
            f"{RLO}warp 1",
            "warp\tisland",
            "SAY hello",
            "npc",
            "z" * 3000,
        ):
            with self.subTest(body=body[:20]):
                self.assertIn(gm_commands.usage_hint_for(body), allowed)


class TheSigilHasOneDefinitionTests(unittest.TestCase):
    """`command_body` exists so the hint names the verb the PARSER read.

    A hand-written `text[1:]` beside the parser's own slice is quiet when it
    breaks: the day `CHAT_COMMAND_SIGIL` changes, one of them keeps the
    sigil and the way out names the grammar of a verb nobody typed.
    """

    def test_it_strips_exactly_the_sigil(self):
        self.assertEqual("warp 2", chat_command.command_body("/warp 2"))

    def test_it_leaves_a_line_that_has_no_sigil_alone(self):
        self.assertEqual("warp 2", chat_command.command_body("warp 2"))

    def test_the_parser_and_the_hint_read_the_same_verb(self):
        """Pinned by MOVING the sigil: both readers have to follow it."""
        with mock.patch.object(chat_command, "CHAT_COMMAND_SIGIL", "!"):
            self.assertEqual("warp 2", chat_command.command_body("!warp 2"))


if __name__ == "__main__":
    unittest.main()
