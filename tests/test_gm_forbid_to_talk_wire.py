"""GM_ForbidToTalkResultVital (0x8D30): payload matches the pinned tag/
offset layout (PF_SERIALIZER_FIELDS.tsv rows 6283-6288), with the wide
string field carrying the 0x48 tag PF_A2_STRING_WIRE_TAG_DELTA.tsv rows
6287/6288 prove for THIS message directly (not by analogy to another one).
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm.forbid_to_talk_wire import (
    GM_FORBID_TO_TALK_RESULT_VITAL_ID,
    ForbidToTalkResultBody,
    GmForbidToTalkWireError,
    MAX_STRING_LENGTH,
    decode_forbid_to_talk_result_payload,
    make_forbid_to_talk_result_frame,
    make_forbid_to_talk_result_payload,
)


class GmForbidToTalkWirePayloadTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_payload_matches_proven_tag_order(self):
        payload = make_forbid_to_talk_result_payload(self.legacy, 1, 300, "hi")
        expected = (
            self.legacy.u8tag(0x0B, 1)
            + self.legacy.u32tag(0x14, 300)
            + self.legacy.wstr_tag("hi")
        )
        self.assertEqual(payload, expected)

    def test_first_field_carries_tag_0x0b(self):
        payload = make_forbid_to_talk_result_payload(self.legacy, 1, 0, "")
        self.assertEqual(payload[0], 0x0B)

    def test_second_field_carries_tag_0x14(self):
        payload = make_forbid_to_talk_result_payload(self.legacy, 0, 0, "")
        self.assertEqual(payload[2], 0x14)

    def test_third_field_carries_the_corrected_0x48_string_tag(self):
        # This is the field PF_A2_STRING_WIRE_TAG_DELTA.tsv row 6287/6288
        # corrects -- the coarser PF_SERIALIZER_FIELDS.tsv column alone
        # would say untagged (4+N), not this (5+N).
        payload = make_forbid_to_talk_result_payload(self.legacy, 0, 0, "x")
        self.assertEqual(payload[7], 0x48)

    def test_rejects_out_of_range_u8_field(self):
        with self.assertRaises(GmForbidToTalkWireError):
            make_forbid_to_talk_result_payload(self.legacy, 256, 0, "")
        with self.assertRaises(GmForbidToTalkWireError):
            make_forbid_to_talk_result_payload(self.legacy, -1, 0, "")

    def test_rejects_out_of_range_u32_field(self):
        with self.assertRaises(GmForbidToTalkWireError):
            make_forbid_to_talk_result_payload(self.legacy, 0, 1 << 32, "")

    def test_rejects_non_str_text(self):
        with self.assertRaises(GmForbidToTalkWireError):
            make_forbid_to_talk_result_payload(self.legacy, 0, 0, b"not a str")  # type: ignore[arg-type]

    def test_rejects_oversized_text(self):
        # MAX_STRING_LENGTH is a byte count; ASCII chars are one UTF-16LE
        # code unit each, so half that many characters is already over it.
        with self.assertRaises(GmForbidToTalkWireError):
            make_forbid_to_talk_result_payload(
                self.legacy, 0, 0, "x" * (MAX_STRING_LENGTH)
            )

    def test_accepts_text_at_exactly_the_length_cap(self):
        text = "x" * (MAX_STRING_LENGTH // 2)  # 1 char = 2 UTF-16LE bytes
        payload = make_forbid_to_talk_result_payload(self.legacy, 0, 0, text)
        self.assertTrue(payload)

    def test_rejects_text_with_a_lone_surrogate(self):
        # A str CAN carry an unpaired surrogate (e.g. via surrogateescape
        # decoding) and utf-16-le encoding of one raises UnicodeEncodeError
        # -- the branch this exercises, not reachable through any plain
        # ASCII/Thai fixture the other tests in this file use.
        with self.assertRaises(GmForbidToTalkWireError):
            make_forbid_to_talk_result_payload(self.legacy, 0, 0, "\udc80")


class GmForbidToTalkWireFrameTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_frame_carries_the_forbid_to_talk_vital_id(self):
        pc, frame = make_forbid_to_talk_result_frame(self.legacy, 0, 1, 300, "hi")
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [
                (
                    GM_FORBID_TO_TALK_RESULT_VITAL_ID,
                    0,
                    make_forbid_to_talk_result_payload(self.legacy, 1, 300, "hi"),
                )
            ]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_vital_id_constant_matches_bridge_registry(self):
        # pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv row 447:
        # GM_ForbidToTalkResultVital
        self.assertEqual(GM_FORBID_TO_TALK_RESULT_VITAL_ID, 0x8D30)


class GmForbidToTalkWireDecodeTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_round_trip_recovers_the_original_fields(self):
        payload = make_forbid_to_talk_result_payload(self.legacy, 1, 300, "muted")
        decoded = decode_forbid_to_talk_result_payload(payload)
        self.assertIsInstance(decoded, ForbidToTalkResultBody)
        self.assertEqual(decoded.field_0x14, 1)
        self.assertEqual(decoded.field_0x18, 300)
        self.assertEqual(decoded.text_0x1c, "muted")

    def test_round_trip_empty_string(self):
        payload = make_forbid_to_talk_result_payload(self.legacy, 0, 0, "")
        decoded = decode_forbid_to_talk_result_payload(payload)
        self.assertEqual(decoded.text_0x1c, "")

    def test_rejects_non_bytes_input(self):
        with self.assertRaises(TypeError):
            decode_forbid_to_talk_result_payload("not bytes")  # type: ignore[arg-type]

    def test_decode_rejects_the_uncorrected_untagged_shape(self):
        # Exactly what the coarser PF_SERIALIZER_FIELDS.tsv column alone
        # would predict (4+N, no tag byte) -- must not silently decode.
        malformed = (
            bytes((0x0B, 1))
            + bytes((0x14,)) + struct.pack("<I", 0)
            + struct.pack("<I", 2) + "hi".encode("utf-16-le")
        )
        with self.assertRaises(GmForbidToTalkWireError):
            decode_forbid_to_talk_result_payload(malformed)

    def test_rejects_wrong_first_tag(self):
        payload = bytearray(make_forbid_to_talk_result_payload(self.legacy, 0, 0, ""))
        payload[0] = 0x14
        with self.assertRaises(GmForbidToTalkWireError):
            decode_forbid_to_talk_result_payload(bytes(payload))

    def test_rejects_wrong_second_tag(self):
        payload = bytearray(make_forbid_to_talk_result_payload(self.legacy, 0, 0, ""))
        payload[2] = 0x0B  # was 0x14
        with self.assertRaises(GmForbidToTalkWireError):
            decode_forbid_to_talk_result_payload(bytes(payload))

    def test_rejects_buffer_truncated_before_the_second_field(self):
        with self.assertRaises(GmForbidToTalkWireError):
            decode_forbid_to_talk_result_payload(self.legacy.u8tag(0x0B, 1) + b"\x14\x00")

    def test_decode_rejects_odd_declared_string_length(self):
        malformed = (
            self.legacy.u8tag(0x0B, 0)
            + self.legacy.u32tag(0x14, 0)
            + bytes((0x48,)) + (3).to_bytes(4, "little") + b"abc"
        )
        with self.assertRaises(GmForbidToTalkWireError):
            decode_forbid_to_talk_result_payload(malformed)

    def test_decode_rejects_declared_length_over_the_cap(self):
        # +2, not +1: must stay even or the odd-length guard fires first.
        malformed = (
            self.legacy.u8tag(0x0B, 0)
            + self.legacy.u32tag(0x14, 0)
            + bytes((0x48,)) + (MAX_STRING_LENGTH + 2).to_bytes(4, "little")
            + b"x" * 8
        )
        with self.assertRaises(GmForbidToTalkWireError):
            decode_forbid_to_talk_result_payload(malformed)
        with self.assertRaisesRegex(GmForbidToTalkWireError, "MAX_STRING_LENGTH"):
            decode_forbid_to_talk_result_payload(malformed)

    def test_rejects_declared_string_length_longer_than_buffer(self):
        malformed = (
            self.legacy.u8tag(0x0B, 0)
            + self.legacy.u32tag(0x14, 0)
            + bytes((0x48,)) + (10).to_bytes(4, "little") + b"ab"
        )
        with self.assertRaises(GmForbidToTalkWireError):
            decode_forbid_to_talk_result_payload(malformed)

    def test_rejects_trailing_bytes(self):
        payload = make_forbid_to_talk_result_payload(self.legacy, 0, 0, "") + b"\x00extra"
        with self.assertRaises(GmForbidToTalkWireError):
            decode_forbid_to_talk_result_payload(payload)


if __name__ == "__main__":
    unittest.main()
