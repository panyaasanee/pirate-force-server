"""A MISTYPED GM command says so ON SCREEN, in twelve ASCII characters.

WHAT THIS FILE PINS, AND WHO ORDERED IT
---------------------------------------
COO-DECISION 2026-09-02T06:47+07:00 (`pf_bridge/notes_to_chief/consumed/
20260902_0647_COO-DECISION-typo-layer-notice-is-TYPO-REFUSED-12-ascii-after-
p1.md`): the SYNTAX layer -- the refusal `gm/commands.parse_gm_command`
produces, which `gm/chat_command.py` reports as `command_parse_error_*` --
composes a `Channel_LocalTalkMessageVital` (0xAC52) frame whose body is
exactly the twelve ASCII characters `TYPO REFUSED`, through the SAME composer
`SPEED DENIED` goes out by (`gm/say_wire.make_local_talk_notice_frame`).  One
layer, every command name.  Item 2 of the same decision also says the notice
must NOT arm CORE-REQUEST-GM-040's `queued` confirmation, and that is pinned
here too.

WHY IT IS A SEPARATE FILE FROM `test_gm_speed_denied_notice.py`
---------------------------------------------------------------
That file is chief's pin on the DB-refusal layer and it currently records the
typo layer's SILENCE as the then-current behaviour ("D6: `/speed fast` never
reaches the nine paths"), naming this decision as the thing that would lift
it.  A pin that is being lifted is rewritten in place, not deleted, and the
new behaviour gets its own file so the two layers can go red separately: one
is about a value the DATABASE refused, this one is about a line the GRAMMAR
could not read, and a round that breaks one must not be able to hide in the
other's suite.  Like that file, this one builds its own doubles rather than
importing a sibling test module.

WHAT IS PROVEN HERE, AND AT WHICH RUNG
--------------------------------------
WIRE ONLY.  Every assertion below is about BYTES this server composes and
hands back to `runtime.py`'s serve loop.  NOTHING here claims a human saw
THESE words.  ONE CLAUSE IS NARROWED, and only one -- ~~"no server-composed
0xAC52 line has ever been observed on a screen"~~ -- because attended round
R303 rendered `[thua pai] : BACK REFUSED`, a DIFFERENT notice through the
same composer, on the owner's screen.

!! THE REST OF THAT SENTENCE STANDS AND MUST NOT BE STRUCK.  A first draft
of this correction struck it whole and pf-adversary (round `1nm6hh`, D8)
measured what that costs: `GT-193` step 10 is `/speed fast` -> `TYPO
REFUSED`, a SEPARATE claim about a SEPARATE code path from step 9, and the
ticket says so in its own words.  R303 ran neither step, and `BACK REFUSED`
is a third text again.  So `GT-193` step 10 IS still the first attempt at
putting THIS module's words on a screen, `TYPO REFUSED` has never been on
one, and a later round reading a struck-through step 10 here could drop the
only queued attempt at the thing this file composes.
The length is twelve because twelve is the only body
length anybody has watched render on this channel (GT-006/GT-009), not
because twelve is tidy.
"""
from __future__ import annotations

import contextlib
import inspect
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

from pirateforce_foundation import channel_message_hypothesis  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands as gm_commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# Written as an escape, never as a literal: this file is scanned by
# `test_gm_source_is_cp874_safe.py`'s siblings and a bidi override has no
# cp874 mapping.  RLO is what `has_format_characters` refuses -- one of the
# excluded refusals below.
RLO = "\u202e"


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
        self.identity_lo = 1
        self.identity_hi = 0


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected
        self.lifecycle = None


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
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def act(self, session, text=None, payload=None, config_path=None):
        """Run the whole production path, the way `runtime.py` calls it.

        `payload` is taken raw when given, so the two malformed-frame
        refusals below can be reached at all -- they are refused before any
        text exists.
        """
        if payload is None:
            payload = make_chat_payload("" if text is None else text)
        return chat_command_action.make_gm_chat_command_action(
            session,
            payload,
            self.legacy,
            config_path=str(
                self.config_path if config_path is None else config_path
            ),
            log_path=str(self.log_path),
        )

    def log_records(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def typo_events(self, session):
        return [
            event
            for event in session.events
            if event.startswith("gm_chat_action_typo_refused_notice_")
        ]

    def assertIsTheTypoNotice(self, action):
        """`action` is a `TYPO REFUSED` LocalTalk notice, decoded out of its
        own composed bytes rather than compared against a hand-typed frame."""
        self.assertIsNotNone(
            action,
            "a mistyped GM command returned no action at all, so the person "
            "who typed it still sees nothing -- COO-DECISION 20260902_0647",
        )
        label, pc, frame, delay = action
        self.assertEqual(
            label, chat_command_action.TYPO_REFUSED_NOTICE_ACTION_LABEL
        )
        self.assertNotIn(
            "TELEPORT",
            label,
            "the label carries the substring `runtime.py`'s "
            "`_move_authority_note_server_moves` reopens the move-authority "
            "grace window on, and a refused typo repositions nobody",
        )
        self.assertEqual(delay, 0.0)
        # THE CHANNEL ID, READ OUT OF THE BYTES.  `decode_channel_message`
        # ECHOES BACK the id it is handed, so asserting on `decoded.channel_id`
        # alone is a tautology on the constant the test passed in
        # (pf-adversary, round `aa9ajr`, D1, against the sibling file).  The
        # id lives at pc[16:18] little-endian and that is the only place a
        # mutant cannot follow the test.
        self.assertEqual(
            pc[16:18],
            (0xAC52).to_bytes(2, "little"),
            "the typo notice was composed on channel 0x%04X, not 0xAC52 "
            "LocalTalk. 0x9F2C GMGlobal in particular is LOCKED by "
            "COO-DECISION 20260829_0041 and this route may never reach it."
            % int.from_bytes(pc[16:18], "little"),
        )
        offset = channel_message_hypothesis.CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET
        payload = pc[
            offset:
            len(pc) - (
                channel_message_hypothesis.CHANNEL_MESSAGE_PC_OVERHEAD - offset
            )
        ]
        decoded = channel_message_hypothesis.decode_channel_message(
            say_wire.LOCAL_TALK_CHANNEL_ID, payload
        )
        self.assertEqual(decoded.body, "TYPO REFUSED")
        self.assertEqual(len(decoded.body), 12)
        self.assertTrue(decoded.body.isascii())
        self.assertEqual(decoded.speaker, "")
        # The frame really carries that pc, so a green decode can never be of
        # bytes that never got framed.
        self.assertEqual(frame[len(frame) - len(pc):], pc)
        return decoded


class TheTextItselfTests(_Case):
    """Item 1 of the decision: twelve ASCII characters, no punctuation added."""

    def test_the_text_is_exactly_twelve_ascii_characters(self):
        text = say_wire.TYPO_REFUSED_NOTICE_TEXT
        self.assertEqual(text, "TYPO REFUSED")
        self.assertEqual(len(text), 12)
        self.assertEqual(len(text), say_wire.NOTICE_TEXT_EXACT_LENGTH)
        self.assertTrue(text.isascii())
        self.assertTrue(text.isprintable())
        self.assertEqual(
            text,
            text.strip(),
            "the notice was padded to reach twelve characters; the length is "
            "evidence (GT-006/GT-009), and padding it would put bytes on the "
            "wire that no measurement covers",
        )
        self.assertEqual(
            [character for character in text if not character.isalpha()],
            [" "],
            "punctuation was added to the notice. COO-DECISION 0647 item 1 "
            "chose these twelve characters precisely because they need none.",
        )

    def test_it_is_not_the_speed_sentence_wearing_a_hat(self):
        # The whole reason a second string exists: `SPEED DENIED` in answer to
        # a mistyped `/warp` names a command the GM did not type.
        self.assertNotEqual(
            say_wire.TYPO_REFUSED_NOTICE_TEXT, say_wire.SPEED_DENIED_NOTICE_TEXT
        )
        self.assertEqual(
            len(say_wire.TYPO_REFUSED_NOTICE_TEXT),
            len(say_wire.SPEED_DENIED_NOTICE_TEXT),
            "the two on-screen sentences must be the same pinned length; "
            "only 12 has ever been measured rendering on this channel",
        )

    def test_it_goes_out_through_the_composer_that_already_ships(self):
        """No second wire path (decision item: `use the SAME composer`)."""
        pc, frame = say_wire.make_local_talk_notice_frame(
            self.legacy, say_wire.TYPO_REFUSED_NOTICE_TEXT
        )
        self.assertEqual(pc[16:18], (0xAC52).to_bytes(2, "little"))
        self.assertTrue(frame.endswith(pc))
        source = inspect.getsource(chat_command_action._typo_refused_notice)
        self.assertIn("make_local_talk_notice_frame", source)
        self.assertNotIn(
            "make_channel_message_response",
            source,
            "the typo notice reaches the shared codec directly instead of "
            "through say_wire's composer -- a second composition route, which "
            "tests/test_gm_say_gate_lock.py exists to forbid",
        )


class EveryCommandNameGetsTheNoticeTests(_Case):
    """One layer, EVERY command name (decision item 2).

    The command list is DERIVED from `commands.COMMAND_NAMES`, not typed out
    here, so a ninth command added tomorrow is covered the day it lands
    instead of the day somebody remembers this file.
    """

    def test_a_bare_verb_of_every_command_in_the_grammar_gets_the_notice(self):
        self.assertEqual(
            set(gm_commands.COMMAND_NAMES),
            {"warp", "npc", "item", "lv", "spawn", "say", "gmprobe", "speed"},
            "the grammar's vocabulary changed. That is not a failure by "
            "itself -- but re-read COO-DECISION 0647, whose condition is "
            "stated over EVERY command name, and check the new one here.",
        )
        for name in gm_commands.COMMAND_NAMES:
            with self.subTest(command=name):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition())
                action = self.act(session, "/" + name)
                # Proof that this test exercised the LAYER it claims to: the
                # refusal the module recorded really is the parse one.
                self.assertIn(
                    chat_command_action.EVENT_REFUSED_PREFIX
                    + chat_command.REFUSAL_PARSE_ERROR_PREFIX
                    + "GmCommandParseError",
                    session.events,
                    session.events,
                )
                self.assertIsTheTypoNotice(action)
                self.assertIn(
                    chat_command_action.EVENT_TYPO_REFUSED_NOTICE_COMPOSED,
                    session.events,
                )

    def test_the_typos_a_human_actually_types_get_the_notice(self):
        """The lines the ASK-COO measured as silent, plus one per command.

        A bare verb is the cheapest way to fail every branch of the grammar;
        these are the shapes a tester really produces, including the two the
        `/speed` round had to leave silent (`/speed fast`, `/warp island`).
        """
        for typed in (
            "/warp island",
            "/warp 3 100",
            "/warp 3 x y",
            "/npc on",
            "/npc maybe 5",
            "/item 1",
            "/lv ten",
            "/spawn goblin",
            "/say",
            "/gmprobe",
            "/speed fast",
            "/speed 400 400",
        ):
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition())
                self.assertIsTheTypoNotice(self.act(session, typed))

    def test_a_verb_this_lane_does_not_have_gets_the_notice_too(self):
        # `/nonsense` and the bare sigil: the parse layer reports these under
        # the same word, and a GM who typed a command that does not exist is
        # exactly the person who most needs to be told something.
        # `/WARP 2 1 1` is deliberately NOT here: the grammar accepts a
        # command name case-insensitively (measured, not assumed -- it parses
        # to a real `warp`), so it is not a typo and gets its own frame.
        for typed in ("/nonsense", "/", "/warp2 1", "/w 2", "/wArP island"):
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition())
                self.assertIsTheTypoNotice(self.act(session, typed))

    def test_a_command_that_parses_gets_its_own_frame_and_not_the_notice(self):
        """The control: if the guard fired for everything, every assertion
        above would still be green over a module that refuses all commands."""
        session = FakeSession(position=FakePosition())
        action = self.act(session, "/warp 2 100 200")
        self.assertIsNotNone(action)
        self.assertNotEqual(
            action[0], chat_command_action.TYPO_REFUSED_NOTICE_ACTION_LABEL
        )
        self.assertEqual([], self.typo_events(session))


class TheExcludedRefusalsComposeNothingTests(_Case):
    """The other refusals in `chat_command.py` compose NOTHING.

    Each exclusion is somebody's stated reason, in the long comment above
    `chat_command.py`'s `TYPED_COMMAND_REFUSAL_PREFIXES` and in the decision
    letter, and that reasoning binds this file: a frame per sentence a GM
    speaks, or per frame the rate limiter is already refusing, would be this
    lane composing wire traffic on a client's schedule.

    Every test names the refusal it produced, so a case that stops reaching
    its intended layer fails LOUDLY instead of passing as "no notice".
    """

    def assertRefusedSilently(self, session, action, reason):
        self.assertIsNone(
            action,
            "a refusal outside the parse layer composed a notice: %s"
            % (action[0] if action else None),
        )
        self.assertIn(
            chat_command_action.EVENT_REFUSED_PREFIX + reason,
            session.events,
            "this case no longer reaches the refusal it was written for, so "
            "it proves nothing about it. Events: %s" % session.events,
        )
        self.assertEqual([], self.typo_events(session))

    def test_a_non_gm_gets_nothing(self):
        session = FakeSession(token="NOT_A_GM", position=FakePosition())
        action = self.act(session, "/warp island")
        self.assertRefusedSilently(
            session, action, chat_command.REFUSAL_NOT_GM
        )

    def test_a_gm_chatting_normally_gets_nothing(self):
        for typed in ("where is everyone", "warp island", ""):
            with self.subTest(typed=typed):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition())
                action = self.act(session, typed)
                self.assertRefusedSilently(
                    session, action, chat_command.REFUSAL_NOT_A_COMMAND
                )

    def test_an_oversized_frame_gets_nothing(self):
        session = FakeSession(position=FakePosition())
        payload = make_chat_payload("/warp " + "9" * 5000)
        self.assertGreater(len(payload), chat_command.MAX_CHAT_PAYLOAD_LENGTH)
        action = self.act(session, payload=payload)
        self.assertRefusedSilently(
            session, action, chat_command.REFUSAL_PAYLOAD_TOO_LARGE
        )

    def test_an_undecodable_frame_gets_nothing(self):
        session = FakeSession(position=FakePosition())
        action = self.act(session, payload=b"\x00\x01\x02\x03")
        self.assertIsNone(action)
        self.assertEqual([], self.typo_events(session))
        self.assertTrue(
            any(
                event.startswith(
                    chat_command_action.EVENT_REFUSED_PREFIX
                    + chat_command.REFUSAL_UNDECODABLE_PREFIX
                )
                for event in session.events
            ),
            session.events,
        )

    def test_the_format_character_refusal_gets_nothing(self):
        """The nearest neighbour, and still not this layer.

        `command_text_has_format_characters` IS a typed-command refusal (it
        shares `TYPED_COMMAND_REFUSAL_PREFIXES` with the parse error, so it
        gets the console line) -- but the decision names `parse_gm_command`
        alone, and this refusal is returned ABOVE the parser.  Widening to it
        would mean composing a frame in answer to a line whose bytes render
        in an order other than the one they are in.
        """
        session = FakeSession(position=FakePosition())
        action = self.act(session, "/warp " + RLO + "1")
        self.assertRefusedSilently(
            session, action, chat_command.REFUSAL_UNSAFE_COMMAND_TEXT
        )

    def test_a_rate_limited_line_gets_nothing_and_that_is_the_cap(self):
        """Also the bound on this whole feature, measured rather than argued.

        The parse refusal is returned BELOW `rate_limit_allows`, so a client
        typing rubbish as fast as it likes gets at most
        `RATE_LIMIT_MAX_CALLS_PER_WINDOW` notices per account per window and
        then silence -- not one composed frame per inbound frame.
        """
        session = FakeSession(position=FakePosition())
        composed = 0
        for _ in range(gm_dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW + 5):
            if self.act(session, "/warp island") is not None:
                composed += 1
        self.assertEqual(composed, gm_dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW)
        self.assertIn(
            chat_command_action.EVENT_REFUSED_PREFIX
            + chat_command.REFUSAL_RATE_LIMITED,
            session.events,
        )

    def test_a_full_audit_log_gets_nothing(self):
        session = FakeSession(position=FakePosition())
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("x" * 64, encoding="utf-8")
        with mock.patch.object(chat_command, "MAX_COMMAND_LOG_BYTES", 8):
            action = self.act(session, "/warp 2 100 200")
        self.assertRefusedSilently(
            session, action, chat_command.REFUSAL_LOG_QUOTA_EXCEEDED
        )

    def test_an_unwritable_audit_log_gets_nothing(self):
        session = FakeSession(position=FakePosition())
        blocker = self.tmp / "capture"
        blocker.write_text("i am a file, not a directory", encoding="utf-8")
        action = self.act(session, "/warp 2 100 200")
        self.assertIsNone(action)
        self.assertEqual([], self.typo_events(session))
        self.assertTrue(
            any(
                event.startswith(
                    chat_command_action.EVENT_REFUSED_PREFIX
                    + chat_command.REFUSAL_LOG_WRITE_FAILED_PREFIX
                )
                for event in session.events
            ),
            session.events,
        )

    def test_an_unreadable_allowlist_gets_nothing(self):
        session = FakeSession(position=FakePosition())
        directory = self.tmp / "not_a_file"
        directory.mkdir()
        action = self.act(session, "/warp island", config_path=directory)
        self.assertIsNone(action)
        self.assertEqual([], self.typo_events(session))

    def test_the_guard_names_one_refusal_constant_and_only_one(self):
        """The structural half, because the behavioural half above can only
        cover refusals that exist today.

        A refusal added to `chat_command.py` tomorrow inherits "no notice" by
        default -- which is the safe direction -- and this pins that the gate
        is a single named prefix rather than a list somebody can grow without
        a decision.
        """
        source = inspect.getsource(chat_command_action._typo_refused_notice)
        body = source[source.index('"""', source.index('"""') + 3) + 3:]
        named = sorted(
            {
                name
                for name in dir(chat_command)
                if name.startswith("REFUSAL_") and name in body
            }
        )
        self.assertEqual(
            named,
            ["REFUSAL_PARSE_ERROR_PREFIX"],
            "the typo notice's gate reads refusal constants other than the "
            "one COO-DECISION 0647 names. It covers ONE layer. Found: %s"
            % named,
        )


class TheNoticeIsNotTheCommandsFrameTests(_Case):
    """Decision item: do NOT arm `queued` for this notice (`0419`, accepted).

    A mistyped command has no `issued` row to close -- the grammar refuses it
    above `log_gm_command` -- so a `queued` row here would close nothing and
    would read, in the audit file, like a command that ran.
    """

    def test_a_typo_notice_never_arms_the_queued_confirmation(self):
        session = FakeSession(position=FakePosition())
        self.assertIsTheTypoNotice(self.act(session, "/warp island"))
        self.assertIsNone(
            getattr(session, "_gm_action_queued_confirm", None),
            "a typo notice armed CORE-REQUEST-GM-040's queued confirmation. "
            "`queued` means THIS COMMAND's frame reached runtime; there is "
            "no command here at all.",
        )

    def test_a_command_that_really_runs_still_arms_it(self):
        # The other direction, so the fix above cannot be "never arm".
        session = FakeSession(position=FakePosition())
        action = self.act(session, "/warp 2 100 200")
        self.assertIsNotNone(action)
        self.assertIsNotNone(getattr(session, "_gm_action_queued_confirm", None))

    def test_a_typo_writes_no_audit_row_at_all(self):
        session = FakeSession(position=FakePosition())
        self.assertIsTheTypoNotice(self.act(session, "/warp island"))
        self.assertEqual(
            [],
            self.log_records(),
            "a mistyped command wrote an audit row. Nothing was issued, so "
            "nothing may be recorded as issued, queued or outcome.",
        )

    def test_the_console_way_out_still_prints_beside_the_notice(self):
        """Both halves of COO-DECISION `0147` at once: the operator's console
        line AND the sentence for the person who typed it."""
        session = FakeSession(position=FakePosition())
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            action = self.act(session, "/warp island")
        self.assertIsTheTypoNotice(action)
        printed = stream.getvalue()
        self.assertIn(
            chat_command_action.COMMAND_REFUSED_CONSOLE_TOKEN,
            printed,
            "the notice deleted the operator's console line: %r" % printed,
        )
        self.assertIn(gm_commands.COMMAND_USAGE["warp"], printed)
        self.assertTrue(printed.isascii(), repr(printed))

    def test_nothing_the_gm_typed_reaches_the_notice_or_the_console(self):
        # The notice body is a frozen lane constant, so this can only regress
        # by somebody making it a formatted string.
        session = FakeSession(position=FakePosition())
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            action = self.act(session, "/warp SECRETWORD")
        decoded = self.assertIsTheTypoNotice(action)
        self.assertNotIn("SECRETWORD", decoded.body)
        self.assertNotIn("SECRETWORD", stream.getvalue())


class TheComposerFailureIsNamedNotRaisedTests(_Case):
    """Fail closed, and say so out loud: the courtesy may never break the
    refusal, and may never reach the listener thread as an exception."""

    def test_a_composer_failure_becomes_a_named_event_and_no_action(self):
        session = FakeSession(position=FakePosition())
        with mock.patch.object(
            say_wire,
            "make_local_talk_notice_frame",
            side_effect=RuntimeError("boom"),
        ):
            action = self.act(session, "/warp island")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_TYPO_REFUSED_NOTICE_FAILED_PREFIX
            + "RuntimeError",
            session.events,
            session.events,
        )
        # The refusal itself is untouched, and the event that names it is
        # still the parse one.
        self.assertIn(
            chat_command_action.EVENT_REFUSED_PREFIX
            + chat_command.REFUSAL_PARSE_ERROR_PREFIX
            + "GmCommandParseError",
            session.events,
        )

    def test_the_failure_event_carries_a_type_name_and_never_a_message(self):
        session = FakeSession(position=FakePosition())
        with mock.patch.object(
            say_wire,
            "make_local_talk_notice_frame",
            side_effect=say_wire.NoticeWireError("SECRETWORD in the message"),
        ):
            self.act(session, "/warp island")
        failures = [
            event
            for event in session.events
            if event.startswith(
                chat_command_action.EVENT_TYPO_REFUSED_NOTICE_FAILED_PREFIX
            )
        ]
        self.assertEqual(
            failures,
            [
                chat_command_action.EVENT_TYPO_REFUSED_NOTICE_FAILED_PREFIX
                + "NoticeWireError"
            ],
        )
        self.assertNotIn("SECRETWORD", " ".join(session.events))

    def test_a_broken_legacy_seam_never_escapes_onto_the_listener_thread(self):
        # The `legacy` seam raises `AttributeError`, which is neither
        # `NoticeWireError` nor anything the composer's own checks raise
        # (round `aa9ajr`, D7).  It must land as a NAMED event, and never as
        # `gm_chat_action_unexpected_<Type>` -- that name blames this module
        # for a refusal it handled.
        for broken in (None, object()):
            with self.subTest(legacy=type(broken).__name__):
                gm_dispatch.reset_rate_limit_state_for_tests()
                session = FakeSession(position=FakePosition())
                action = chat_command_action.make_gm_chat_command_action(
                    session,
                    make_chat_payload("/warp island"),
                    broken,
                    config_path=str(self.config_path),
                    log_path=str(self.log_path),
                )
                self.assertIsNone(action)
                self.assertTrue(
                    any(
                        event.startswith(
                            chat_command_action
                            .EVENT_TYPO_REFUSED_NOTICE_FAILED_PREFIX
                        )
                        for event in session.events
                    ),
                    session.events,
                )
                self.assertEqual(
                    [],
                    [
                        event
                        for event in session.events
                        if event.startswith(
                            chat_command_action.EVENT_UNEXPECTED_PREFIX
                        )
                    ],
                    "a composer failure escaped as an unexpected exception: %s"
                    % session.events,
                )

    def test_a_session_that_cannot_hold_events_still_gets_its_notice(self):
        """`_note` swallows its own failure; the notice must survive it."""

        class NoEvents:
            token = "GM_ONE"
            events = None
            foundation = FakeFoundation(FakeSelected(FakePosition()))

        action = self.act(NoEvents(), "/warp island")
        self.assertIsTheTypoNotice(action)


if __name__ == "__main__":
    unittest.main()
