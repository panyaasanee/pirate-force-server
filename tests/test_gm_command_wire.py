"""RE-088: structural decoder for GM_RunGMCommandVital / GM_RunGMCommandResultVital.

These tests build synthetic wire bytes from the RE-088 pinned shape (tag
0x0B = one byte, tag 0x14 = little-endian u32, untagged wstring = u32le
byte_len + UTF-16LE payload) rather than importing an encoder, because this
module intentionally has no encoder: it decodes an inbound (client->server)
message, it does not compose one.
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.command_wire import (
    GM_RUN_GM_COMMAND_RESULT_VITAL_ID,
    GM_RUN_GM_COMMAND_VITAL_ID,
    NESTED_SERIALIZER_SPAN_SHA256,
    OUTER_SERIALIZER_SPAN_SHA256,
    RESULT_SERIALIZER_SPAN_SHA256,
    GmCommandWireError,
    GmRunCommandBody,
    decode_gm_run_command_result_vital,
    decode_gm_run_command_vital,
)


def _wstring(text: str) -> bytes:
    payload = text.encode("utf-16-le")
    return struct.pack("<I", len(payload)) + payload


def _nested_body(
    field_0x10: int, field_0x14: int, field_0x18: int, s1: str, s2: str, presence: int = 1
) -> bytes:
    return (
        bytes([0x0B, presence])
        + bytes([0x14]) + struct.pack("<I", field_0x10)
        + bytes([0x14]) + struct.pack("<I", field_0x14)
        + bytes([0x0B, field_0x18])
        + _wstring(s1)
        + _wstring(s2)
    )


class VitalIdTests(unittest.TestCase):
    def test_vital_ids_match_the_registry(self):
        self.assertEqual(GM_RUN_GM_COMMAND_VITAL_ID, 0x51E9)
        self.assertEqual(GM_RUN_GM_COMMAND_RESULT_VITAL_ID, 0x8C77)


class SpanShaPinLockTests(unittest.TestCase):
    """Not a re-derivation (no client binary on this cloud clone) -- a
    pin-lock against accidental edits.  These three literals were
    independently re-derived from pf_bridge/external/PF_SERIALIZER_FIELDS.tsv
    at RE-088 result time (2026-08-26); if this test ever needs to change,
    that change must cite a new RE result, not just a passing test run.
    """

    def test_outer_span_sha256_is_pinned(self):
        self.assertEqual(
            OUTER_SERIALIZER_SPAN_SHA256,
            "541d82f511ba87d444587da9f217ee7eb436431c21e7cfca6dd026d19a8c8554",
        )

    def test_nested_span_sha256_is_pinned(self):
        self.assertEqual(
            NESTED_SERIALIZER_SPAN_SHA256,
            "aa3c7c8d2d92eeee48508da2c26d78e360c612aaa2b682dfb608d7b08493559d",
        )

    def test_result_span_sha256_is_pinned(self):
        self.assertEqual(
            RESULT_SERIALIZER_SPAN_SHA256,
            "ad65d125ab8a97db872ae5b2e957280a431d55beb7956050652a2d58dee633e9",
        )


class DecodeGmRunCommandVitalTests(unittest.TestCase):
    def test_presence_zero_decodes_to_none(self):
        self.assertIsNone(decode_gm_run_command_vital(bytes([0x0B, 0])))

    def test_presence_zero_with_trailing_bytes_is_rejected(self):
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(bytes([0x0B, 0, 0xFF]))

    def test_full_nested_body_round_trips(self):
        raw = _nested_body(111, 222, 7, "warp", "1 100 200")
        body = decode_gm_run_command_vital(raw)
        self.assertEqual(
            body,
            GmRunCommandBody(
                presence=1,
                field_0x10=111,
                field_0x14=222,
                field_0x18=7,
                string_0x1c="warp",
                string_0x38="1 100 200",
            ),
        )

    def test_nonzero_presence_other_than_one_gates_the_body_and_is_preserved(self):
        # RE-088's own gate condition is "!= 0" (setne al), so any nonzero
        # byte gates the nested body exactly like 1 does -- but the decoded
        # value must be the byte actually observed, not normalized to 1, so
        # a caller logging it (see gm/command_capture.py) never reports a
        # measurement that did not happen.
        raw = _nested_body(1, 2, 3, "a", "b", presence=200)
        body = decode_gm_run_command_vital(raw)
        self.assertEqual(body.presence, 200)

    def test_empty_strings_decode_cleanly(self):
        raw = _nested_body(0, 0, 0, "", "")
        body = decode_gm_run_command_vital(raw)
        self.assertEqual(body.string_0x1c, "")
        self.assertEqual(body.string_0x38, "")

    def test_non_ascii_string_survives_utf16le_round_trip(self):
        raw = _nested_body(1, 2, 3, "สวัสดี", "ทดสอบ")
        body = decode_gm_run_command_vital(raw)
        self.assertEqual(body.string_0x1c, "สวัสดี")
        self.assertEqual(body.string_0x38, "ทดสอบ")

    def test_wrong_presence_tag_byte_is_rejected(self):
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(bytes([0x14, 1]))

    def test_wrong_scalar_tag_byte_is_rejected(self):
        raw = bytearray(_nested_body(1, 2, 3, "a", "b"))
        raw[2] = 0x0B  # was 0x14 for field_0x10
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(bytes(raw))

    def test_truncated_after_presence_is_rejected(self):
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(bytes([0x0B, 1, 0x14, 0x01, 0x02]))

    def test_odd_string_byte_len_is_rejected(self):
        raw = bytearray(_nested_body(1, 2, 3, "a", "b"))
        # string_0x1c's length prefix immediately follows the fixed 11-byte
        # scalar prefix (1 presence tag+byte + 2*(1 tag+4 byte) + 1 tag+byte).
        length_offset = 1 + 1 + 5 + 5 + 2
        raw[length_offset] = 0x01  # odd byte length, not a whole UTF-16LE run
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(bytes(raw))

    def test_declared_string_length_longer_than_buffer_is_rejected(self):
        raw = bytearray(_nested_body(1, 2, 3, "a", "b"))
        length_offset = 1 + 1 + 5 + 5 + 2
        struct.pack_into("<I", raw, length_offset, 0xFFFF)
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(bytes(raw))

    def test_maximum_u32_declared_string_length_is_rejected_not_a_hang_or_crash(self):
        raw = bytearray(_nested_body(1, 2, 3, "a", "b"))
        length_offset = 1 + 1 + 5 + 5 + 2
        struct.pack_into("<I", raw, length_offset, 0xFFFFFFFF)
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(bytes(raw))

    def test_trailing_bytes_after_a_clean_nested_body_are_rejected(self):
        raw = _nested_body(1, 2, 3, "a", "b") + b"\x00\x00"
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(raw)

    def test_rejects_non_bytes(self):
        with self.assertRaises(TypeError):
            decode_gm_run_command_vital("not bytes")

    def test_empty_buffer_is_rejected(self):
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_vital(b"")


class DecodeGmRunCommandResultVitalTests(unittest.TestCase):
    def test_decodes_the_single_byte_field(self):
        self.assertEqual(decode_gm_run_command_result_vital(bytes([0x0B, 5])), 5)

    def test_wrong_tag_is_rejected(self):
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_result_vital(bytes([0x14, 5]))

    def test_trailing_bytes_are_rejected(self):
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_result_vital(bytes([0x0B, 5, 0x00]))

    def test_truncated_is_rejected(self):
        with self.assertRaises(GmCommandWireError):
            decode_gm_run_command_result_vital(bytes([0x0B]))


if __name__ == "__main__":
    unittest.main()
