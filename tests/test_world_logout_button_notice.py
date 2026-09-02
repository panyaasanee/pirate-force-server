"""The UI-A click composes twelve visible characters; the UI-B click does not.

WHERE THE TWO FRAMES IN THIS FILE COME FROM
-------------------------------------------
They are the owner's own capture, not fixtures this lane invented: she
clicked both HOME-menu buttons herself on 2026-09-01 on a boot with NO
logout scenario, and the exact bytes were carried into
`pf_bridge/notes_to_chief/consumed/20260901_1930_KA1A-CAPTURE-the-owner-
clicked-both-UI-A-and-UI-B-buttons-herself-exact-bytes-plus-a-design-
problem-for-HYP-PF-040.md` (capture `gt192_20260901_184254`, frames
`[G< #1397]` 34 bytes and `[G< #1402]` 119 bytes).  They are parsed here by
the REAL parser (`legacy.parse_outer`), so a drift in that parser cannot
pass unnoticed.

WHICH RUNG THIS FILE PROVES -- AND IT IS NOT WIRE/DB
----------------------------------------------------
COMPOSITION / UNIT ONLY.  `EVIDENCE_GATES.md` defines the wire/DB rung as
frames in a console log, rows in a DB, events a server recorded; this file
has no socket, no DB, no server, and no request was received -- the request
frames are hex literals sitting in this file.  What it proves is that the
bytes this module hands back are exactly `say_wire`'s, for exactly the
click the live classifier accepts.  The wire/DB rung arrives when chief's
call site is on `main` and a boot logs the token; the client-observable
rung is `GT-205`, and nothing here may be offered as either.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import logout_hypothesis  # noqa: E402
from pirateforce_foundation import logout_request_envelope  # noqa: E402
from pirateforce_foundation import world_logout_button_notice as notice  # noqa: E402
from pirateforce_foundation.gm import say_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

LEGACY_PATH = ROOT / "current/pf_login_game_server_v141.py"


def _hex(text: str) -> bytes:
    return bytes.fromhex("".join(text.split()))


# [G< #1397] -- "back to character select" (UI-A), subcode 3, 34 bytes.
UIA_REQUEST_FRAME = _hex(
    """
    12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12
    40 1B 0B 00 08 03 08 00 14 00 00 00 00 14 00 00
    00 00
    """
)

# [G< #1402] -- "exit game" (UI-B), subcode 1, 119 bytes, carrying three
# other vitals (two 0x1EB4 and one 0x2A90) behind the logout entry.
UIB_REQUEST_FRAME = _hex(
    """
    12 6F 6E 14 00 00 00 00 08 00 0B 02 12 04 00 12
    40 1B 0B 00 08 01 08 00 14 00 00 00 00 14 00 00
    00 00 12 B4 1E 0B 00 2A 27 E3 D8 C2 2A 54 19 97
    46 2A DF 29 F5 C5 2A 00 80 F3 43 0F 01 00 12 B4
    1E 0B 00 2A 8B 70 FA C2 2A A1 90 96 46 2A 4B 95
    FC C5 2A 00 00 F2 43 0F 01 00 12 90 2A 0B 00 2A
    34 80 96 46 2A 86 79 FD C5 2A 00 00 F2 43 2A 9F
    5C DC 3F 0B 01 0B 00
    """
)

# SYNTHETIC, AND SAID SO: a well-formed envelope carrying an empty
# `GetWorldInfoVital 0x3D4B` instead of `0x1B40`.  It is BUILT here, not
# lifted from a capture -- the real `#1398` frame that sits between the
# owner's two clicks is 51 bytes and its exact bytes are not in this repo,
# only RE-197's decode of them is.  Pinning a reconstruction and calling it
# a capture is the over-claim this comment exists to refuse.
SYNTHETIC_NON_LOGOUT_FRAME = _hex(
    """
    12 6F 6E 14 00 00 00 00 08 00 0B 02 12 02 00 12
    4B 3D 0B 00 0B 00
    """
)


class TheCapturedFramesAreTheOnesTheOwnerSentTests(unittest.TestCase):
    """Guard the fixtures themselves before anything is asserted about them.

    A transcription slip in the hex above would make every other test in
    this file green about the wrong bytes.
    """

    def test_the_two_frames_have_the_captured_lengths(self):
        self.assertEqual(len(UIA_REQUEST_FRAME), 34)
        self.assertEqual(len(UIB_REQUEST_FRAME), 119)

    def test_the_subcode_byte_pair_is_where_the_capture_letter_says(self):
        # `08 03` for UI-A and `08 01` for UI-B, at the same offset in both.
        self.assertEqual(UIA_REQUEST_FRAME[20:22], b"\x08\x03")
        self.assertEqual(UIB_REQUEST_FRAME[20:22], b"\x08\x01")

    def test_the_two_frames_share_the_first_thirteen_bytes(self):
        self.assertEqual(UIA_REQUEST_FRAME[:13], UIB_REQUEST_FRAME[:13])


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def _classify(self, frame):
        return notice.classify_parsed(self.legacy, self.legacy.parse_outer(frame))

    def test_the_uia_frame_is_named_the_character_select_button(self):
        result = self._classify(UIA_REQUEST_FRAME)
        self.assertIsNotNone(result)
        self.assertEqual(result.button, notice.BUTTON_CHARACTER_SELECT)
        self.assertEqual(
            result.subcode,
            logout_request_envelope.LOGOUT_SUBCODE_CHARACTER_SELECT,
        )
        self.assertTrue(result.is_character_select)
        self.assertFalse(result.is_exit_game)
        # The owner's capture: subcode 3 arrived alone, with nothing behind it.
        self.assertEqual(result.envelope_vital_count, 1)
        self.assertEqual(result.trailing_byte_count, 0)

    def test_the_uib_frame_is_named_the_exit_game_button(self):
        result = self._classify(UIB_REQUEST_FRAME)
        self.assertIsNotNone(result)
        self.assertEqual(result.button, notice.BUTTON_EXIT_GAME)
        self.assertEqual(
            result.subcode, logout_request_envelope.LOGOUT_SUBCODE_EXIT_GAME
        )
        self.assertTrue(result.is_exit_game)
        self.assertFalse(result.is_character_select)
        # Four vitals in the envelope; 85 bytes ride behind the logout entry.
        self.assertEqual(result.envelope_vital_count, 4)
        self.assertEqual(result.trailing_byte_count, 119 - 34)

    def test_the_two_buttons_do_not_classify_the_same(self):
        first = self._classify(UIA_REQUEST_FRAME)
        second = self._classify(UIB_REQUEST_FRAME)
        self.assertNotEqual(first.button, second.button)
        self.assertNotEqual(first.subcode, second.subcode)

    def test_this_lane_accepts_exactly_what_the_live_dispatch_accepts(self):
        # The reason there is only one classifier: a frame the live logout
        # dispatch calls `wrong_payload` must never get an answer from this
        # lane. The junk shape below is the one pf-adversary closed inside
        # `classify_logout_attempt` itself (vital_count == 1 plus trailing
        # junk), and an earlier draft of THIS module answered it.
        junk = UIA_REQUEST_FRAME + b"\xaa" * 50
        parsed = self.legacy.parse_outer(junk)
        self.assertEqual(
            logout_hypothesis.classify_logout_attempt(self.legacy, parsed),
            "wrong_payload",
        )
        self.assertIsNone(notice.classify_parsed(self.legacy, parsed))
        composed, line = notice.observe_parsed(self.legacy, parsed)
        self.assertIsNone(composed)
        self.assertIn("wrong_payload", line)

    def test_the_trailing_count_follows_the_pinned_payload_not_a_literal(self):
        # If the pinned LogoutVital payload length ever moves, the number
        # GT-205 grades on must move with it rather than stay at 14.
        pinned = logout_hypothesis.LOGOUT_REQUEST_PAYLOADS[
            logout_request_envelope.LOGOUT_SUBCODE_EXIT_GAME
        ]
        parsed = self.legacy.parse_outer(UIB_REQUEST_FRAME)
        result = notice.classify_parsed(self.legacy, parsed)
        self.assertEqual(
            result.trailing_byte_count,
            len(parsed.nested_payload) - len(pinned),
        )


class ObserveIsTheOneDoorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def _observe(self, frame, legacy=None):
        return notice.observe_parsed(
            self.legacy if legacy is None else legacy,
            self.legacy.parse_outer(frame),
        )

    def test_the_uia_click_yields_bytes_and_a_composed_line(self):
        composed, line = self._observe(UIA_REQUEST_FRAME)
        self.assertIsNotNone(composed)
        self.assertTrue(line.startswith(notice.TOKEN_NOTICE_COMPOSED), line)
        self.assertTrue(composed.classification.is_character_select)

    def test_the_composed_line_carries_every_field_gt205_grades_on(self):
        # GT-205's wire/DB criterion is copied verbatim by a human off a
        # console. Every field it names has to be in the line this module
        # actually emits -- an earlier draft's line had none of them.
        _, line = self._observe(UIA_REQUEST_FRAME)
        for field in (
            "button=BACK_TO_CHARSELECT",
            "subcode=3",
            "vitals=1",
            "trailing=0",
            "text=BACK REFUSED",
        ):
            self.assertIn(field, line)

    def test_the_uib_click_yields_no_bytes_but_still_a_full_line(self):
        composed, line = self._observe(UIB_REQUEST_FRAME)
        self.assertIsNone(composed)
        self.assertTrue(line.startswith(notice.TOKEN_STOOD_DOWN), line)
        for field in ("button=EXIT_GAME", "subcode=1", "vitals=4", "trailing=85"):
            self.assertIn(field, line)

    def test_the_composed_token_never_appears_without_bytes(self):
        # The token is the proof GT-205 reads. It must be impossible to
        # print it when nothing was composed: with the composer itself
        # refusing, the line must say FAILED, not COMPOSED.
        def _refuse(*args, **kwargs):
            raise say_wire.NoticeWireError("refused on purpose")

        original = say_wire.make_local_talk_notice_frame
        try:
            say_wire.make_local_talk_notice_frame = _refuse
            composed, line = self._observe(UIA_REQUEST_FRAME)
        finally:
            say_wire.make_local_talk_notice_frame = original
        self.assertIsNone(composed)
        self.assertTrue(line.startswith(notice.TOKEN_NOTICE_FAILED), line)
        self.assertNotIn(notice.TOKEN_NOTICE_COMPOSED, line)
        # And the composer works again afterwards, so the patch is not a
        # silent one-way door for the rest of the file.
        self.assertIsNotNone(self._observe(UIA_REQUEST_FRAME)[0])

    def test_a_withdrawn_module_says_withdrawn_not_failed(self):
        # This lane's own decision and a composer bug are opposite messages
        # to whoever reads the log; they must not share a token.
        original = notice.production_allowed
        try:
            notice.production_allowed = False
            composed, line = self._observe(UIA_REQUEST_FRAME)
        finally:
            notice.production_allowed = original
        self.assertIsNone(composed)
        self.assertTrue(line.startswith(notice.TOKEN_WITHDRAWN), line)
        self.assertNotIn(notice.TOKEN_NOTICE_FAILED, line)
        # And the flag is back on, so the module ships live by default.
        self.assertIs(notice.production_allowed, True)
        self.assertIsNone(
            notice.make_uia_notice(
                self.legacy, self.legacy.parse_outer(UIB_REQUEST_FRAME)
            )
        )

    def test_an_unclassified_frame_carries_the_live_verdict_word(self):
        composed, line = self._observe(SYNTHETIC_NON_LOGOUT_FRAME)
        self.assertIsNone(composed)
        self.assertTrue(line.startswith(notice.TOKEN_UNCLASSIFIED), line)
        self.assertIn("wrong_envelope", line)

    def test_every_broken_parsed_shape_returns_a_line_and_no_bytes(self):
        class _Blank:
            pass

        class _Exploding:
            def __getattr__(self, name):
                raise RuntimeError("no attribute survives this object")

        for name, value in (
            ("none", None),
            ("blank", _Blank()),
            ("exploding", _Exploding()),
            ("int", 3),
            ("bytes", UIA_REQUEST_FRAME),
        ):
            with self.subTest(shape=name):
                self.assertIsNone(notice.classify_parsed(self.legacy, value))
                composed, line = notice.observe_parsed(self.legacy, value)
                self.assertIsNone(composed)
                self.assertTrue(line.startswith(notice.TOKEN_UNCLASSIFIED), line)
                self.assertTrue(line.isascii() and line.isprintable(), line)

    def test_a_broken_seam_names_itself_in_the_line(self):
        # A `legacy` that is not the legacy module cannot even be asked
        # what the frame is, so the honest outcome is "unclassified" -- but
        # the LINE has to say the seam broke, or a tester chasing GT-205's
        # P3 outcome cannot tell a wiring mistake from a seam fault.
        parsed = self.legacy.parse_outer(UIA_REQUEST_FRAME)
        composed, line = notice.observe_parsed(object(), parsed)
        self.assertIsNone(composed)
        self.assertTrue(line.startswith(notice.TOKEN_UNCLASSIFIED), line)
        self.assertIn("seam_AttributeError", line)

    def test_every_line_it_can_emit_is_printable_ascii(self):
        class _Exploding:
            def __getattr__(self, name):
                raise RuntimeError("boom")

        cases = (
            (self.legacy, self.legacy.parse_outer(UIA_REQUEST_FRAME)),
            (self.legacy, self.legacy.parse_outer(UIB_REQUEST_FRAME)),
            (self.legacy, self.legacy.parse_outer(SYNTHETIC_NON_LOGOUT_FRAME)),
            (self.legacy, _Exploding()),
            (self.legacy, None),
            (object(), self.legacy.parse_outer(UIA_REQUEST_FRAME)),
        )
        for seam, parsed in cases:
            with self.subTest(parsed=type(parsed).__name__):
                _, line = notice.observe_parsed(seam, parsed)
                self.assertTrue(line.isascii() and line.isprintable(), line)

    def test_the_five_tokens_are_distinct(self):
        tokens = {
            notice.TOKEN_NOTICE_COMPOSED,
            notice.TOKEN_STOOD_DOWN,
            notice.TOKEN_WITHDRAWN,
            notice.TOKEN_NOTICE_FAILED,
            notice.TOKEN_UNCLASSIFIED,
        }
        self.assertEqual(len(tokens), 5)


class NoticeCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_the_uia_click_composes_exactly_the_say_wire_notice(self):
        composed = notice.make_uia_notice(
            self.legacy, self.legacy.parse_outer(UIA_REQUEST_FRAME)
        )
        self.assertIsNotNone(composed)
        expected_pc, expected_frame = say_wire.make_local_talk_notice_frame(
            self.legacy, notice.UIA_NOTICE_TEXT
        )
        # Byte equality against the proven composer: this lane adds no wire
        # knowledge of its own and must not be able to drift from it.
        self.assertEqual(composed.pc, expected_pc)
        self.assertEqual(composed.frame, expected_frame)
        self.assertEqual(composed.text, notice.UIA_NOTICE_TEXT)

    def test_the_notice_text_really_is_in_the_bytes_that_go_out(self):
        # A second, independent reading: not "the composer agrees with
        # itself" but "the twelve characters are actually in the frame".
        composed = notice.make_uia_notice(
            self.legacy, self.legacy.parse_outer(UIA_REQUEST_FRAME)
        )
        ascii_body = notice.UIA_NOTICE_TEXT.encode("ascii")
        utf16_body = notice.UIA_NOTICE_TEXT.encode("utf-16-le")
        self.assertTrue(
            ascii_body in composed.frame or utf16_body in composed.frame,
            composed.frame.hex(),
        )

    def test_the_uib_click_composes_nothing_at_all(self):
        # GT-194 is live on this exact frame; no byte from this lane may
        # appear in the middle of that ticket's evidence.
        self.assertIsNone(
            notice.make_uia_notice(
                self.legacy, self.legacy.parse_outer(UIB_REQUEST_FRAME)
            )
        )


class TheNoticeTextIsPinnedByEvidenceTests(unittest.TestCase):
    def test_the_text_is_exactly_the_twelve_characters_gt205_asks_for(self):
        # GT-205 asks a human to read one exact spelling off the screen; if
        # nothing pins the spelling, a one-character edit makes that entry
        # unmeetable with the suite green (pf-adversary D3).
        self.assertEqual(notice.UIA_NOTICE_TEXT, "BACK REFUSED")

    def test_the_retired_assumption_label_cannot_come_back_unstruck(self):
        # Round 8z9h9n, pf-adversary D11/D14.  COO-DECISION 20260902_0943
        # settled this wording, so the file must not read as if it were
        # still waiting for an answer -- a stale "awaiting COO" invites the
        # next round to re-litigate a decided question, and the sweep that
        # finds those greps for the label text.  The house shape (see
        # mob_scene_recompose.py, and the same guard in
        # tests/test_mob_pickup.py) is strikethrough plus RULED plus the
        # decision, ON the matched line; nothing pinned that here, so a
        # revert of the comment block was silently green.
        source = (
            Path(__file__).resolve().parents[1]
            / "src/pirateforce_foundation/world_logout_button_notice.py"
        ).read_text(encoding="utf-8")
        for line in source.splitlines():
            if "awaiting COO" in line:
                self.assertIn("~~", line, msg=(
                    "a live-looking 'awaiting COO' label is back on this "
                    "line; retire it with ~~...~~ plus RULED instead"
                ))
        self.assertIn("RULED, round 8z9h9n", source)
        self.assertIn("20260902_0943_COO-DECISION", source)
        # The alternative COO never adjudicated must stay visible: it is
        # the wording a later round would need if the transition becomes
        # performable, and the ask letter offered four options, not two.
        self.assertIn("BACK NOT YET", source)

    def test_the_text_is_twelve_printable_ascii_characters(self):
        text = notice.UIA_NOTICE_TEXT
        self.assertEqual(len(text), say_wire.NOTICE_TEXT_EXACT_LENGTH)
        self.assertEqual(len(text), 12)
        self.assertTrue(text.isascii())
        self.assertTrue(text.isprintable())

    def test_the_pin_is_not_vacuous(self):
        # Mutation control: if the constant changed, the composed bytes
        # must change with it.
        legacy = load_legacy(LEGACY_PATH)
        mine, _ = say_wire.make_local_talk_notice_frame(
            legacy, notice.UIA_NOTICE_TEXT
        )
        other, _ = say_wire.make_local_talk_notice_frame(legacy, "BACK ALLOWED")
        self.assertNotEqual(mine, other)

    def test_the_text_is_not_the_gm_lanes_speed_notice(self):
        # Two different refusals must not read as one on a screenshot.
        self.assertNotEqual(
            notice.UIA_NOTICE_TEXT, say_wire.SPEED_DENIED_NOTICE_TEXT
        )


class ThisModuleOnlyComposesTests(unittest.TestCase):
    """It must not be able to send, close, or reach into the runtime."""

    SOURCE = ROOT / "src/pirateforce_foundation/world_logout_button_notice.py"

    def _tree(self):
        return ast.parse(self.SOURCE.read_text(encoding="utf-8"))

    def test_it_imports_no_runtime_socket_or_app_module(self):
        forbidden = {"runtime", "app", "socket", "threading", "asyncio"}
        imported = set()
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.split(".")[0])
                imported.update(alias.name for alias in node.names)
        self.assertEqual(imported & forbidden, set(), sorted(imported))

    def test_it_calls_nothing_that_sends_or_closes(self):
        banned = {"send", "sendall", "close", "close_connection", "shutdown"}
        called = set()
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                called.add(name)
        self.assertEqual(called & banned, set(), sorted(called & banned))

    def test_there_is_exactly_one_public_entry_point_for_a_call_site(self):
        # Two doors with different acceptance sets is the defect this file
        # was rewritten to remove; keep it removed.
        public = {
            node.name
            for node in self._tree().body
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        }
        self.assertEqual(
            public,
            {"classify_parsed", "make_uia_notice", "observe_parsed"},
            sorted(public),
        )

    def test_the_source_is_ascii(self):
        # The bridge console is cp874; a stray Thai character in a module
        # this lane may one day print from is a console crash waiting.
        raw = self.SOURCE.read_bytes()
        self.assertTrue(raw.decode("utf-8").isascii())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
