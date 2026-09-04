"""Activity_CheatCodeVital (0x6CEC): structural decoder for the pinned
six-field layout (PF_SERIALIZER_FIELDS.tsv rows 4345-4356), with all five
wide-string fields carrying the 0x48 tag PF_A2_STRING_WIRE_TAG_DELTA.tsv
rows 4347-4356 prove for THIS message directly (not by analogy to another
one).

These tests build synthetic wire bytes from the pinned shape rather than
importing an encoder, because this module intentionally has no encoder: it
decodes an inbound (client->server) message, it does not compose one -- the
same posture gm/command_wire.py's tests take for GM_RunGMCommandVital.
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.activity_cheat_code_wire import (
    ACTIVITY_CHEAT_CODE_VITAL_ID,
    MAX_STRING_LENGTH,
    ActivityCheatCodeBody,
    GmActivityCheatCodeWireError,
    decode_activity_cheat_code_vital,
)


def _wstring(text: str) -> bytes:
    # 0x48 tag + uint32le byte count + UTF-16LE payload (PF_A2_STRING_WIRE_
    # TAG_DELTA.tsv rows 4347-4356, tag_instruction push_0x48).
    payload = text.encode("utf-16-le")
    return bytes((0x48,)) + struct.pack("<I", len(payload)) + payload


def _payload(
    field_0x14: int, s18: str, s34: str, s50: str, s6c: str, s88: str
) -> bytes:
    return (
        bytes((0x14,)) + struct.pack("<I", field_0x14)
        + _wstring(s18)
        + _wstring(s34)
        + _wstring(s50)
        + _wstring(s6c)
        + _wstring(s88)
    )


class VitalIdTests(unittest.TestCase):
    def test_vital_id_matches_the_registry(self):
        # pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv row 270:
        # Activity_CheatCodeVital
        self.assertEqual(ACTIVITY_CHEAT_CODE_VITAL_ID, 0x6CEC)


class DecodeTests(unittest.TestCase):
    def test_decodes_all_six_fields_in_order(self):
        raw = _payload(7, "a", "bb", "ccc", "dddd", "eeeee")
        body = decode_activity_cheat_code_vital(raw)
        self.assertIsInstance(body, ActivityCheatCodeBody)
        self.assertEqual(body.field_0x14, 7)
        self.assertEqual(body.text_0x18, "a")
        self.assertEqual(body.text_0x34, "bb")
        self.assertEqual(body.text_0x50, "ccc")
        self.assertEqual(body.text_0x6c, "dddd")
        self.assertEqual(body.text_0x88, "eeeee")

    def test_all_five_strings_may_be_empty(self):
        raw = _payload(0, "", "", "", "", "")
        body = decode_activity_cheat_code_vital(raw)
        self.assertEqual(
            (body.text_0x18, body.text_0x34, body.text_0x50, body.text_0x6c, body.text_0x88),
            ("", "", "", "", ""),
        )

    def test_first_field_must_carry_tag_0x14(self):
        raw = bytearray(_payload(1, "", "", "", "", ""))
        raw[0] = 0x0B
        with self.assertRaises(GmActivityCheatCodeWireError):
            decode_activity_cheat_code_vital(bytes(raw))

    def test_rejects_buffer_shorter_than_the_first_field(self):
        with self.assertRaises(GmActivityCheatCodeWireError):
            decode_activity_cheat_code_vital(bytes((0x14, 0x00)))

    def test_rejects_a_string_with_the_uncorrected_untagged_shape(self):
        # Exactly what the coarser PF_SERIALIZER_FIELDS.tsv column alone
        # would predict for field 2 (4+N, no tag byte) -- must not silently
        # decode as if it were the pinned 5+N shape.
        malformed = (
            bytes((0x14,)) + struct.pack("<I", 0)
            + struct.pack("<I", 0) + _wstring("") + _wstring("") + _wstring("") + _wstring("")
        )
        with self.assertRaises(GmActivityCheatCodeWireError):
            decode_activity_cheat_code_vital(malformed)

    def test_rejects_wrong_string_tag(self):
        raw = bytearray(_payload(0, "a", "", "", "", ""))
        # byte 0 = u32 tag, bytes 1-4 = u32 value, byte 5 = the first
        # string's tag byte.
        raw[5] = 0x44  # the NARROW string tag: right shape, wrong kind
        with self.assertRaises(GmActivityCheatCodeWireError):
            decode_activity_cheat_code_vital(bytes(raw))

    def test_rejects_declared_string_length_longer_than_buffer(self):
        malformed = (
            bytes((0x14,)) + struct.pack("<I", 0)
            + bytes((0x48,)) + (10).to_bytes(4, "little") + b"ab"
        )
        with self.assertRaises(GmActivityCheatCodeWireError):
            decode_activity_cheat_code_vital(malformed)

    def test_rejects_declared_length_over_the_cap(self):
        # +2, not +1: the declared length must stay even (a whole number of
        # UTF-16LE code units) or the odd-length guard fires first and this
        # test would never reach the cap check it is named after.
        malformed = (
            bytes((0x14,)) + struct.pack("<I", 0)
            + bytes((0x48,)) + (MAX_STRING_LENGTH + 2).to_bytes(4, "little")
            + b"x" * 8
        )
        with self.assertRaises(GmActivityCheatCodeWireError):
            decode_activity_cheat_code_vital(malformed)
        with self.assertRaisesRegex(GmActivityCheatCodeWireError, "MAX_STRING_LENGTH"):
            decode_activity_cheat_code_vital(malformed)

    def test_rejects_odd_declared_byte_length(self):
        malformed = (
            bytes((0x14,)) + struct.pack("<I", 0)
            + bytes((0x48,)) + (3).to_bytes(4, "little") + b"abc"
        )
        with self.assertRaises(GmActivityCheatCodeWireError):
            decode_activity_cheat_code_vital(malformed)

    def test_rejects_trailing_bytes_after_all_six_fields(self):
        raw = _payload(0, "", "", "", "", "") + b"\x00extra"
        with self.assertRaises(GmActivityCheatCodeWireError):
            decode_activity_cheat_code_vital(raw)

    def test_rejects_truncated_buffer_missing_the_last_string(self):
        raw = _payload(0, "a", "b", "c", "d", "e")
        with self.assertRaises(GmActivityCheatCodeWireError):
            decode_activity_cheat_code_vital(raw[:-3])

    def test_rejects_non_bytes_input(self):
        with self.assertRaises(TypeError):
            decode_activity_cheat_code_vital("not bytes")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
