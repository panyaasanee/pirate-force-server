"""Tests for the structural LogoutVital request classifier.

Three evidence sources, all cross-checked byte-for-byte in this file (not
assumed):
  1. ``logout_hypothesis.LOGOUT_REQUEST_PCS`` -- the existing hash-pinned
     34-byte one-vital-only captures for subcode 1 and subcode 3.
  2. The fresh 2026-09-01 ~19:30 owner capture (``notes_to_chief/
     20260901_1930_KA1A-CAPTURE-*.md``): subcode 3 reproduced (1)
     byte-for-byte; subcode 1 did not -- a genuinely longer, real,
     legally-valid 119-byte frame with three extra bundled vitals.
  3. Negative/malformed inputs, to prove the classifier fails closed.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    LOGOUT_REQUEST_PAYLOADS,
    LOGOUT_REQUEST_PCS,
    LOGOUT_SUBCODE_CHARACTER_SELECT,
    LOGOUT_SUBCODE_EXIT_GAME,
    LOGOUT_VITAL_ID,
    classify_logout_attempt,
)
from pirateforce_foundation.logout_request_envelope import (  # noqa: E402
    classify_logout_vital_request,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _hex_join(*lines: str) -> bytes:
    return bytes.fromhex("".join(line.replace(" ", "") for line in lines))


# Verbatim from notes_to_chief/20260901_1930_KA1A-CAPTURE-*.md, capture
# gt192_20260901_184254, frames #1397 (34 bytes, subcode 3) and #1402
# (119 bytes, subcode 1).
CAPTURED_2026_09_01_CHARACTER_SELECT = _hex_join(
    "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12",
    "40 1B 0B 00 08 03 08 00 14 00 00 00 00 14 00 00",
    "00 00",
)

CAPTURED_2026_09_01_EXIT_GAME = _hex_join(
    "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 04 00 12",
    "40 1B 0B 00 08 01 08 00 14 00 00 00 00 14 00 00",
    "00 00 12 B4 1E 0B 00 2A 27 E3 D8 C2 2A 54 19 97",
    "46 2A DF 29 F5 C5 2A 00 80 F3 43 0F 01 00 12 B4",
    "1E 0B 00 2A 8B 70 FA C2 2A A1 90 96 46 2A 4B 95",
    "FC C5 2A 00 00 F2 43 0F 01 00 12 90 2A 0B 00 2A",
    "34 80 96 46 2A 86 79 FD C5 2A 00 00 F2 43 2A 9F",
    "5C DC 3F 0B 01 0B 00",
)


class ExistingPinsClassifyCorrectlyTests(unittest.TestCase):
    """Every existing hash-pinned request frame must still classify
    correctly: this module is a strict superset, never a contradiction."""

    def test_pinned_exit_game_pc_classifies_as_subcode_1(self):
        result = classify_logout_vital_request(
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME]
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.subcode, LOGOUT_SUBCODE_EXIT_GAME)
        self.assertEqual(result.envelope_vital_count, 1)
        self.assertEqual(result.trailing_bytes, b"")
        self.assertEqual(result.trailing_byte_count, 0)
        self.assertTrue(result.is_exit_game)
        self.assertFalse(result.is_character_select)

    def test_pinned_character_select_pc_classifies_as_subcode_3(self):
        result = classify_logout_vital_request(
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_CHARACTER_SELECT]
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.subcode, LOGOUT_SUBCODE_CHARACTER_SELECT)
        self.assertEqual(result.envelope_vital_count, 1)
        self.assertEqual(result.trailing_bytes, b"")
        self.assertTrue(result.is_character_select)
        self.assertFalse(result.is_exit_game)


class FreshCaptureCrossCheckTests(unittest.TestCase):
    """The load-bearing findings of this round: compare the fresh
    2026-09-01 capture against the existing pins byte-for-byte, then
    classify both fresh frames."""

    def test_character_select_capture_is_byte_identical_to_existing_pin(self):
        self.assertEqual(
            CAPTURED_2026_09_01_CHARACTER_SELECT,
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_CHARACTER_SELECT],
        )

    def test_exit_game_capture_is_NOT_byte_identical_to_existing_pin(self):
        # This is the actual gap this round found: the real client's
        # exit-game envelope can legally be longer than the pinned frame.
        self.assertNotEqual(
            CAPTURED_2026_09_01_EXIT_GAME,
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME],
        )
        self.assertEqual(len(CAPTURED_2026_09_01_EXIT_GAME), 119)
        self.assertEqual(
            len(LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME]), 34
        )
        # ...but the two frames DO share the same fixed 13-byte prefix and
        # the same 19-byte LogoutVital vital entry -- only the envelope
        # vital-count byte (offset 13) and the trailing bundled vitals
        # (offset 34 onward) differ.
        self.assertEqual(
            CAPTURED_2026_09_01_EXIT_GAME[0:13],
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME][0:13],
        )
        self.assertEqual(
            CAPTURED_2026_09_01_EXIT_GAME[15:34],
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME][15:34],
        )

    def test_character_select_capture_classifies_as_subcode_3(self):
        result = classify_logout_vital_request(
            CAPTURED_2026_09_01_CHARACTER_SELECT
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.subcode, LOGOUT_SUBCODE_CHARACTER_SELECT)
        self.assertEqual(result.envelope_vital_count, 1)
        self.assertEqual(result.trailing_byte_count, 0)

    def test_exit_game_capture_classifies_as_subcode_1_with_trailing_data(
        self,
    ):
        result = classify_logout_vital_request(CAPTURED_2026_09_01_EXIT_GAME)
        self.assertIsNotNone(result)
        self.assertEqual(result.subcode, LOGOUT_SUBCODE_EXIT_GAME)
        self.assertEqual(result.envelope_vital_count, 4)
        self.assertEqual(result.trailing_byte_count, 85)
        self.assertEqual(
            result.trailing_bytes, CAPTURED_2026_09_01_EXIT_GAME[34:]
        )
        self.assertTrue(result.is_exit_game)


class LiveDispatchGapEvidenceTests(unittest.TestCase):
    """Runs the fresh capture through the FROZEN legacy parser (read-only
    use of ``current/pf_login_game_server_v141.py``, same pattern
    ``test_logout_hypothesis.py`` already uses -- no edit to that file).

    This proves, with the real parser and not a re-implementation, exactly
    why ``logout_hypothesis.classify_logout_attempt`` (the function
    ``runtime.py``'s dispatch actually calls) returns ``"wrong_envelope"``
    for the captured real exit-game click: its hard ``vital_count == 1``
    check (logout_hypothesis.py:1457) rejects the envelope outright before
    the payload is even compared. It also proves the minimal safe fix
    (envelope check relaxed to ``>= 1``, payload compared as a PREFIX of
    ``nested_payload`` instead of full equality) would recognize it
    correctly -- both claims are load-bearing for the CORE-REQUEST this
    round sends to chief, and this test is the receipt.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_captured_exit_game_frame_parses_with_real_legacy_parser(self):
        parsed = self.legacy.parse_outer(CAPTURED_2026_09_01_EXIT_GAME)
        self.assertEqual(
            parsed.outer_id, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ
        )
        self.assertEqual(parsed.outer_version, 0)
        self.assertEqual(parsed.outer_mask, 0x02)
        self.assertEqual(parsed.nested_id, LOGOUT_VITAL_ID)
        self.assertEqual(parsed.nested_version, 0)
        # This is the actual gap: 4, not the 1 that
        # classify_logout_attempt's envelope check currently requires.
        self.assertEqual(parsed.vital_count, 4)
        # nested_payload is the LogoutVital payload PLUS the three bundled
        # vitals' raw bytes concatenated (99 bytes), so exact equality
        # against the 14-byte pin also fails today -- but the pinned
        # 14-byte payload is an exact PREFIX of it.
        self.assertEqual(len(parsed.nested_payload), 99)
        self.assertNotEqual(
            parsed.nested_payload, LOGOUT_REQUEST_PAYLOADS[LOGOUT_SUBCODE_EXIT_GAME]
        )
        self.assertEqual(
            parsed.nested_payload[:14],
            LOGOUT_REQUEST_PAYLOADS[LOGOUT_SUBCODE_EXIT_GAME],
        )

    def test_captured_character_select_frame_parses_as_vital_count_1(self):
        # The control case: the button whose real click DOES still satisfy
        # today's vital_count == 1 check, matching why subcode 3 needed no
        # fix while subcode 1 does.
        parsed = self.legacy.parse_outer(
            CAPTURED_2026_09_01_CHARACTER_SELECT
        )
        self.assertEqual(parsed.vital_count, 1)
        self.assertEqual(
            parsed.nested_payload,
            LOGOUT_REQUEST_PAYLOADS[LOGOUT_SUBCODE_CHARACTER_SELECT],
        )


class DispatchGapFixedTests(unittest.TestCase):
    """The receipt this CORE-REQUEST asked for: after chief applies option
    (ก) from letter 2007 (``vital_count >= 1`` + prefix compare against
    ``nested_payload``), ``classify_logout_attempt`` -- the exact function
    ``runtime.py`` dispatches through, not a reimplementation -- must
    recognize the real captured "exit game" click instead of rejecting it.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_captured_exit_game_frame_now_classifies_exact_01(self):
        parsed = self.legacy.parse_outer(CAPTURED_2026_09_01_EXIT_GAME)
        self.assertEqual(
            classify_logout_attempt(self.legacy, parsed), "exact_01"
        )

    def test_captured_character_select_frame_still_classifies_exact_03(self):
        # Regression guard: the fix must not change the already-working
        # single-vital case.
        parsed = self.legacy.parse_outer(
            CAPTURED_2026_09_01_CHARACTER_SELECT
        )
        self.assertEqual(
            classify_logout_attempt(self.legacy, parsed), "exact_03"
        )

    def test_wrong_nested_id_still_rejected(self):
        # Fail-closed guard: relaxing vital_count must not relax nested_id.
        parsed = self.legacy.parse_outer(CAPTURED_2026_09_01_EXIT_GAME)
        bad = replace(parsed, nested_id=parsed.nested_id + 1)
        self.assertEqual(
            classify_logout_attempt(self.legacy, bad), "wrong_envelope"
        )

    def test_short_nested_payload_still_rejected(self):
        # A payload shorter than the 14-byte pin must not slice-match by
        # accident (an empty/short prefix comparison must fail closed).
        parsed = self.legacy.parse_outer(CAPTURED_2026_09_01_EXIT_GAME)
        bad = replace(parsed, nested_payload=parsed.nested_payload[:5])
        self.assertEqual(
            classify_logout_attempt(self.legacy, bad), "wrong_payload"
        )

    def test_vital_count_1_with_trailing_junk_still_rejected(self):
        # pf-adversary finding on the first draft of this fix: a frame that
        # claims vital_count == 1 (no bundled vitals) but carries extra
        # bytes after the pinned 14-byte payload anyway must NOT be
        # accepted via prefix truncation -- nothing legitimate produces
        # trailing bytes when only one vital is declared, so the
        # vital_count == 1 case keeps the pre-fix exact-length comparison.
        # Only vital_count >= 2 (the real bundled-vitals case) uses the
        # prefix match.
        pinned = LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME]
        parsed = self.legacy.parse_outer(pinned)
        self.assertEqual(parsed.vital_count, 1)
        self.assertEqual(len(parsed.nested_payload), 14)
        junked = replace(
            parsed, nested_payload=parsed.nested_payload + b"\xff" * 50,
        )
        self.assertEqual(
            classify_logout_attempt(self.legacy, junked), "wrong_payload"
        )


class FailClosedTests(unittest.TestCase):
    def test_too_short_frame_returns_none(self):
        self.assertIsNone(classify_logout_vital_request(b"\x00" * 33))

    def test_empty_frame_returns_none(self):
        self.assertIsNone(classify_logout_vital_request(b""))

    def test_wrong_prefix_returns_none(self):
        mutated = bytearray(
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME]
        )
        mutated[0] = 0xFF
        self.assertIsNone(classify_logout_vital_request(bytes(mutated)))

    def test_zero_vital_count_returns_none(self):
        mutated = bytearray(
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME]
        )
        mutated[13] = 0x00
        self.assertIsNone(classify_logout_vital_request(bytes(mutated)))

    def test_wrong_reserved_byte_returns_none(self):
        mutated = bytearray(
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME]
        )
        mutated[14] = 0x01
        self.assertIsNone(classify_logout_vital_request(bytes(mutated)))

    def test_wrong_vital_id_returns_none(self):
        mutated = bytearray(
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME]
        )
        mutated[16] = 0x00
        mutated[17] = 0x00
        self.assertIsNone(classify_logout_vital_request(bytes(mutated)))

    def test_unrecognised_subcode_returns_none(self):
        mutated = bytearray(
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME]
        )
        mutated[21] = 0x02  # neither 1 (exit game) nor 3 (character select)
        self.assertIsNone(classify_logout_vital_request(bytes(mutated)))

    def test_corrupted_payload_tail_returns_none(self):
        mutated = bytearray(
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_EXIT_GAME]
        )
        mutated[24] = 0xFF
        self.assertIsNone(classify_logout_vital_request(bytes(mutated)))

    def test_bytearray_input_accepted_same_as_bytes(self):
        as_bytearray = bytearray(
            LOGOUT_REQUEST_PCS[LOGOUT_SUBCODE_CHARACTER_SELECT]
        )
        result = classify_logout_vital_request(as_bytearray)
        self.assertIsNotNone(result)
        self.assertEqual(result.subcode, LOGOUT_SUBCODE_CHARACTER_SELECT)

    def test_non_bytes_input_returns_none(self):
        self.assertIsNone(classify_logout_vital_request(None))  # type: ignore[arg-type]
        self.assertIsNone(classify_logout_vital_request("not bytes"))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
