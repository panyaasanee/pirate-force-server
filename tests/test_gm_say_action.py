"""LANE-GM: the `say` half of the chat line -> outbound ACTION path.

`tests/test_gm_chat_command_action.py` proves the `warp` half.  This file
proves the `say` half, which is a different shape of risk and needs its own
pins:

1. THE VERSION GATE IS REAL.  `say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_
   CONFIRMED` is None today (RE-132 open), so an authorized `/say` must
   produce NO action and a named event.  Everything about the 0x9F2C PAYLOAD
   is proven byte-exact; the one thing that is not is the envelope's
   vital_version byte, and GT-101 measured what a wrong one does to a real
   client (modal ErrorData=23065, socket closed).
2. THE GATE HAS A SECOND MOUTH.  If RE-132 answers with a byte the imported
   codec does not emit, opening the constant must still not send: the
   composed frame would carry the version RE just measured as wrong.  That
   refusal is a distinct event, so "waiting for RE" and "RE answered and the
   codec cannot build it" never read as the same state.
3. THE LABEL MUST NOT SAY TELEPORT.  `runtime.py:3654-3675` reopens the
   move-authority grace window for any queued action whose label contains
   TELEPORT.  A `say` moves nobody; a label copied from the warp path out of
   symmetry would let a GM widen the anti-cheat window one chat line at a
   time.  Pinned here against that call site's own source, not against a
   comment.
4. THE PATH ACTUALLY WORKS once the byte is known -- and the bytes are the
   imported codec's bytes, never new ones composed here.
5. NOTHING ESCAPES, and the permission story survives the new branch: a
   non-GM typing the exact line that works for a GM gets no action and no
   audit row.

!! LAYER TAG FOR POINT 5, after pf-adversary (round `w8hnu9`).  Every
permission test in this file is a MODULE-layer fact: `FakeSession` sets
`.token` per test, so what they prove is "this module decides on the token it
is handed".  They are NOT a server-layer fact, because on this server
`runtime.py`'s `IDENTITY, STATED HONESTLY` comment (4886-4896 at this
commit -- the anchor is the citation, the numbers drift) records that
`session.token` is the process-wide
`--token` CLI value shared by every accepted connection, not a per-connection
authenticated login.  Until that is fixed, two humans cannot be told apart at
this point at all -- so `SayPermissionTests` passing says nothing about what
a second real player could do, and GT-133's step 5 cannot decide it either.
"""
from __future__ import annotations

import json
import re
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
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.gm.commands import (  # noqa: E402
    MAX_SAY_MESSAGE_LENGTH,
    GmCommand,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# NOT the real byte -- RE-132 has not answered.  Tests that need the gate
# open patch this in explicitly, and it is deliberately equal to the version
# the imported codec emits so that the mismatch case below has to be built on
# purpose rather than happening by accident.
TEST_OPEN_VERSION = say_wire.CHANNEL_CODEC_VITAL_VERSION


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class FakeSession:
    """Only the attributes this module is allowed to read.

    `say` reads strictly fewer of them than `warp` does -- no `foundation`,
    no `selected`, no position -- and this class carries none of them so a
    future edit that starts reaching for a position on the say path fails
    here instead of quietly working on a real session.
    """

    def __init__(self, token="GM_ONE"):
        self.token = token
        self.events = []


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"
    PLAYER_ACCOUNT = "DECKHAND"

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

    def act(self, session, text):
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.config_path),
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

    def open_the_version_gate(self, version=TEST_OPEN_VERSION):
        return mock.patch.object(
            say_wire, "GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED", version
        )


class SayVersionGateTests(_Case):
    def test_the_shipped_constant_is_still_none_so_no_bytes_can_go_out(self):
        # If this fails without RE-132 being answered and cited in
        # say_wire.py's own comment, someone inherited 0xAC52's byte for a
        # different vital -- the exact reasoning that produced the hardcoded
        # `1` GT-101 measured as session-killing.
        self.assertIsNone(say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED)

    def test_re132_is_answered_and_the_gate_is_still_shut_for_the_other_reason(self):
        # The point of this test is that those two facts are BOTH true, and
        # that a future round cannot quietly merge them.  RE-132 (result
        # letter 20260829_0010, consumed round `z6gu2n`) measured the byte as
        # 0 from the client's own constructor, and it is the byte the codec
        # already emits -- so nothing about BYTES is blocking `/say` any more.
        # What blocks it is condition (A) in say_wire.py's own comment: every
        # connection shares the process `--token` (`runtime.py`'s
        # `IDENTITY, STATED HONESTLY` comment), so
        # opening the gate hands `/say` to whoever connects and the allowlist
        # cannot tell two humans apart.  If someone flips the gate, this test
        # is where they have to come and say which of those two changed.
        self.assertEqual(say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_RE132_STATIC, 0)
        self.assertEqual(
            say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_RE132_STATIC,
            say_wire.CHANNEL_CODEC_VITAL_VERSION,
        )
        self.assertIsNone(say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED)

    def test_the_re132_pins_are_the_letters_numbers(self):
        # pf-adversary: a pin nothing reads is a comment with an `=` in it.
        # These four are the only handle a later round has on WHICH
        # measurement the byte above came from, so changing one has to be a
        # deliberate edit here, not a quiet edit there.  The values are
        # RE-132's result letter (20260829_0010) verbatim.
        self.assertEqual(
            say_wire.RE132_CLIENT_IMAGE_SHA256,
            "9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623",
        )
        self.assertEqual(say_wire.RE132_VERSION_WRITE_VA, 0x00657CC9)
        self.assertEqual(say_wire.RE132_GM_GLOBAL_CTOR_CALL_VA, 0x0065BCD0)
        self.assertEqual(say_wire.RE132_HANDLER_VA, 0x0065C850)

    def test_the_identity_citation_still_points_at_something(self):
        # The round found the old pin (`runtime.py:4765-4774`) had drifted to
        # damage dispatch, and it is the citation the whole "why the gate
        # stays shut" argument hangs on.  Anchor text, not line numbers, and
        # checked rather than asserted in prose.
        runtime_source = (
            ROOT / "src/pirateforce_foundation/runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn("IDENTITY, STATED HONESTLY", runtime_source)
        self.assertIn("process-wide --token CLI value", runtime_source)

    def test_the_static_pin_is_never_what_the_send_path_reads(self):
        # Two constants, two questions ("what byte?" / "may we send?").  If
        # the action path ever reads the static pin, the gate becomes
        # decorative without a single line of it changing.
        session = FakeSession()
        with mock.patch.object(
            say_wire, "GM_GLOBAL_MESSAGE_VITAL_VERSION_RE132_STATIC", 0
        ):
            self.assertIsNone(self.act(session, "/say all hands on deck"))
        self.assertIn(
            chat_command_action.EVENT_SAY_WITHHELD_NO_VERSION, session.events
        )

    def test_a_valid_gm_say_yields_no_action_while_the_version_is_unknown(self):
        session = FakeSession()
        action = self.act(session, "/say all hands on deck")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SAY_WITHHELD_NO_VERSION, session.events
        )

    def test_the_line_is_still_authorized_and_audited_while_withheld(self):
        session = FakeSession()
        self.act(session, "/say all hands on deck")
        records = self.log_records()
        # Issued row + the outcome row that names the shut gate
        # (CORE-REQUEST-GM-032).  Before that row existed, this log said the
        # same thing whether or not the message reached anyone.
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["command"], "say")
        self.assertFalse(records[0]["executed"])
        self.assertEqual(
            records[1]["outcome"],
            chat_command_action.OUTCOME_SAY_WITHHELD_NO_VERSION,
        )
        self.assertIn(
            f"{chat_command_action.EVENT_ACCEPTED_PREFIX}say", session.events
        )

    def test_a_confirmed_byte_the_codec_cannot_emit_still_sends_nothing(self):
        # RE-132 answering is necessary, not sufficient.  If the answer is a
        # byte channel_message_hypothesis.py does not put on the wire, the
        # composed frame would carry the wrong one -- refuse, distinctly.
        odd_byte = say_wire.CHANNEL_CODEC_VITAL_VERSION + 3
        session = FakeSession()
        with self.open_the_version_gate(odd_byte):
            action = self.act(session, "/say all hands on deck")
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_SAY_VERSION_CODEC_MISMATCH, session.events
        )
        self.assertNotIn(
            chat_command_action.EVENT_SAY_WITHHELD_NO_VERSION, session.events
        )

    def test_the_two_refusals_are_not_the_same_event_name(self):
        self.assertNotEqual(
            chat_command_action.EVENT_SAY_WITHHELD_NO_VERSION,
            chat_command_action.EVENT_SAY_VERSION_CODEC_MISMATCH,
        )


class SayActionTests(_Case):
    def test_a_say_becomes_a_real_gm_global_message_action(self):
        session = FakeSession()
        with self.open_the_version_gate():
            action = self.act(session, "/say all hands on deck")
        self.assertIsNotNone(action)
        label, pc, frame, delay = action
        self.assertEqual(label, chat_command_action.SAY_ACTION_LABEL)
        self.assertEqual(delay, 0.0)
        self.assertIsInstance(pc, (bytes, bytearray))
        self.assertIsInstance(frame, (bytes, bytearray))

    def test_the_bytes_are_the_imported_codecs_bytes_not_new_ones(self):
        # This module must never become a second place that knows how to
        # build a channel message.  The retracted broadcast-wire round is
        # what that mistake costs.
        session = FakeSession()
        with self.open_the_version_gate():
            _label, pc, frame, _delay = self.act(session, "/say all hands on deck")
        expected_pc, expected_frame = say_wire.make_say_broadcast_frame(
            self.legacy, GmCommand("say", ("all hands on deck",), "say all hands on deck")
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))

    def test_the_message_reaches_the_frame_as_the_gm_typed_it(self):
        # Including a Thai body: the wire is UTF-16LE and must not inherit
        # the bridge console's cp874 limits.
        body = "สวัสดี GM"
        session = FakeSession()
        with self.open_the_version_gate():
            _label, pc, _frame, _delay = self.act(session, f"/say {body}")
        self.assertIn(body.encode("utf-16-le"), bytes(pc))

    def test_an_over_length_message_is_refused_by_name_not_by_exception(self):
        session = FakeSession()
        with self.open_the_version_gate():
            action = self.act(session, "/say " + "x" * (MAX_SAY_MESSAGE_LENGTH + 5))
        self.assertIsNone(action)
        # The parser refuses this one before the wire is reached, which is
        # correct -- what this pins is that it is a NAMED refusal either way
        # and never an exception out of the module.
        self.assertTrue(
            any(
                event.startswith(
                    (
                        chat_command_action.EVENT_REFUSED_PREFIX,
                        chat_command_action.EVENT_SAY_REFUSED_PREFIX,
                    )
                )
                for event in session.events
            ),
            session.events,
        )

    def test_a_codec_rejection_surfaces_as_a_named_say_refusal(self):
        session = FakeSession()
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action,
            "make_say_broadcast_frame",
            side_effect=say_wire.SayWireError("nope"),
        ):
            action = self.act(session, "/say all hands on deck")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_SAY_REFUSED_PREFIX}SayWireError",
            session.events,
        )

    def test_the_refusal_event_never_carries_the_gms_typed_text(self):
        secret = "TREASUREATNINEPACES"
        session = FakeSession()
        with self.open_the_version_gate(), mock.patch.object(
            chat_command_action,
            "make_say_broadcast_frame",
            side_effect=say_wire.SayWireError(f"rejected {secret}"),
        ):
            self.act(session, f"/say {secret}")
        for event in session.events:
            self.assertNotIn(secret, event)


class SayLabelTests(_Case):
    """The label is not decoration; runtime.py reads it."""

    def test_the_say_label_does_not_contain_teleport(self):
        self.assertNotIn("TELEPORT", chat_command_action.SAY_ACTION_LABEL)

    def test_the_warp_label_still_does(self):
        # The same pin from the other direction: if a future edit drops
        # TELEPORT from the warp label, the durable row freezes after a warp.
        self.assertIn("TELEPORT", chat_command_action.WARP_ACTION_LABEL)

    def test_the_runtime_rule_this_depends_on_is_still_a_substring_test(self):
        # Re-derived from source at this commit, not carried over from a
        # comment: if runtime.py stops testing the label this way, both pins
        # above are measuring nothing and must be rewritten.
        source = (ROOT / "src/pirateforce_foundation/runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertRegex(source, r'"TELEPORT"\s+in\s+action\[0\]')
        # And that the rule is still REACHED.  pf-adversary (this round)
        # showed the assertion above stays green if the one call site is
        # deleted and the function left orphaned -- which is how a pin
        # quietly stops measuring anything.
        self.assertIn("self._move_authority_note_server_moves(actions)", source)

    def test_the_rule_is_scenario_gated_and_this_file_says_so(self):
        # The label comment used to claim the substring test runs for every
        # queued action.  It does not: the call site is guarded by
        # `move_authority_hypothesis_scenario is not None`.  If that guard is
        # ever removed the rule becomes global, which is a bigger claim than
        # the comment makes -- fail here so the comment gets rewritten
        # deliberately rather than drifting into being true by accident.
        source = (ROOT / "src/pirateforce_foundation/runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "if move_authority_hypothesis_scenario is not None:\n"
            "                self._move_authority_note_server_moves(actions)",
            source,
        )

    def test_the_label_is_ascii_and_carries_no_v98_refresh_prefix(self):
        label = chat_command_action.SAY_ACTION_LABEL
        label.encode("ascii")
        self.assertFalse(
            label.startswith(("V98_LOCAL_REFRESH_", "V141_LOCAL_REFRESH_")),
            "that prefix suppresses the serve loop's hexdump for this action",
        )

    def test_the_two_labels_are_distinct(self):
        self.assertNotEqual(
            chat_command_action.SAY_ACTION_LABEL,
            chat_command_action.WARP_ACTION_LABEL,
        )


class SayPermissionTests(_Case):
    def test_a_non_gm_saying_the_same_line_gets_nothing(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT)
        with self.open_the_version_gate():
            action = self.act(session, "/say all hands on deck")
        self.assertIsNone(action)
        self.assertEqual(self.log_records(), [])
        self.assertFalse(
            any(
                event.startswith(chat_command_action.EVENT_ACCEPTED_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_an_ordinary_chat_line_from_a_gm_is_not_a_say(self):
        # A GM chatting normally must not have his sentence bounced back at
        # him as a GM global message.
        session = FakeSession()
        with self.open_the_version_gate():
            action = self.act(session, "good evening")
        self.assertIsNone(action)
        self.assertFalse(
            any(
                event.startswith(chat_command_action.EVENT_SAY_REFUSED_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_a_session_with_no_token_is_a_named_refusal(self):
        session = FakeSession(token=None)
        with self.open_the_version_gate():
            action = self.act(session, "/say all hands on deck")
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_BAD_SESSION_PREFIX}NoneType",
            session.events,
        )


class SayCoverageHonestyTests(_Case):
    """The "not wired yet" list has to shrink when a wire is built."""

    def test_say_is_no_longer_reported_as_having_no_wire_path(self):
        session = FakeSession()
        with self.open_the_version_gate():
            self.act(session, "/say all hands on deck")
        self.assertNotIn(
            f"{chat_command_action.EVENT_NO_WIRE_PATH_PREFIX}say", session.events
        )

    def test_the_other_four_commands_still_report_no_wire_path(self):
        for line in ("/npc on 5", "/item 3 1", "/lv 4", "/spawn 9"):
            with self.subTest(line=line):
                session = FakeSession()
                with self.open_the_version_gate():
                    action = self.act(session, line)
                self.assertIsNone(action)
                name = line.split()[0].lstrip("/")
                self.assertIn(
                    f"{chat_command_action.EVENT_NO_WIRE_PATH_PREFIX}{name}",
                    session.events,
                )

    def test_the_module_docstring_does_not_still_list_say_as_unwired(self):
        # Round `w8hnu9` changed the behaviour; a docstring that still says
        # `say` sends nothing would be the lane's own worst failure mode --
        # a reader trusting prose over code.  The old sentence is struck
        # through, not deleted (project rule: strike, never erase), so this
        # asserts the live claim, not the absence of the words.
        source = (
            ROOT / "src/pirateforce_foundation/gm/chat_command_action.py"
        ).read_text(encoding="utf-8")
        live_claim = re.search(
            r"\* It does not send anything for ([^.]*)\.", source
        )
        self.assertIsNotNone(live_claim)
        self.assertNotIn("say", live_claim.group(1))


if __name__ == "__main__":
    unittest.main()
