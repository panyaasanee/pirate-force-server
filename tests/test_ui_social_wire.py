"""Pure unit tests for ``ui_social_wire.py``'s shared primitives.

Nothing here touches ``runtime.py`` or any dispatcher -- these are not
wiring tests, because nothing in this module is wired (see
``ui_social_wire.py``'s own docstring and COO-DECISION ``20260904_1244``
item 3).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_social_wire as wire  # noqa: E402


class U64TagTests(unittest.TestCase):
    def test_round_trip(self):
        encoded = wire.u64tag(0x32, 0x0123456789ABCDEF)
        self.assertEqual(encoded[0], 0x32)
        value, offset = wire.read_u64tag(encoded, 0, 0x32)
        self.assertEqual(value, 0x0123456789ABCDEF)
        self.assertEqual(offset, len(encoded))

    def test_masks_to_64_bits(self):
        encoded = wire.u64tag(0x32, (1 << 64) + 5)
        value, _ = wire.read_u64tag(encoded, 0, 0x32)
        self.assertEqual(value, 5)

    def test_wrong_tag_fails_closed(self):
        encoded = wire.u64tag(0x32, 1)
        with self.assertRaises(wire.WireDecodeError):
            wire.read_u64tag(encoded, 0, 0x99)

    def test_truncated_buffer_fails_closed(self):
        with self.assertRaises(wire.WireDecodeError):
            wire.read_u64tag(bytes([0x32, 1, 2]), 0, 0x32)


class UntaggedWstringTests(unittest.TestCase):
    def test_round_trip_ascii(self):
        encoded = wire.encode_untagged_wstring("hello")
        text, offset = wire.read_untagged_wstring(encoded, 0)
        self.assertEqual(text, "hello")
        self.assertEqual(offset, len(encoded))

    def test_round_trip_empty_string(self):
        encoded = wire.encode_untagged_wstring("")
        self.assertEqual(encoded, bytes([0, 0, 0, 0]))
        text, offset = wire.read_untagged_wstring(encoded, 0)
        self.assertEqual(text, "")
        self.assertEqual(offset, 4)

    def test_round_trip_non_ascii(self):
        # UTF-16LE, not the client's ASCII/cp874 console convention -- this
        # is a WIRE string field, unrelated to console-output character
        # rules.
        encoded = wire.encode_untagged_wstring("ทดสอบ")
        text, offset = wire.read_untagged_wstring(encoded, 0)
        self.assertEqual(text, "ทดสอบ")
        self.assertEqual(offset, len(encoded))

    def test_no_leading_tag_byte(self):
        # UNTAGGED means untagged: byte 0 must be the length prefix's low
        # byte, never a tag like wstr_tag's 0x48.
        encoded = wire.encode_untagged_wstring("A")
        self.assertNotEqual(encoded[0], 0x48)

    def test_truncated_length_prefix_fails_closed(self):
        with self.assertRaises(wire.WireDecodeError):
            wire.read_untagged_wstring(bytes([1, 0, 0]), 0)

    def test_truncated_payload_fails_closed(self):
        # Length prefix claims 4 bytes of payload but only 2 are present.
        malformed = bytes([4, 0, 0, 0]) + bytes([0, 0])
        with self.assertRaises(wire.WireDecodeError):
            wire.read_untagged_wstring(malformed, 0)

    def test_odd_length_payload_fails_closed(self):
        malformed = bytes([1, 0, 0, 0]) + bytes([0])
        with self.assertRaises(wire.WireDecodeError):
            wire.read_untagged_wstring(malformed, 0)

    def test_unpaired_surrogate_payload_fails_closed(self):
        # An even-length, fully in-bounds payload that still is not valid
        # UTF-16LE: a lone high surrogate (0xD800) with no low surrogate to
        # pair with. This slipped past the module's original fail-closed
        # claim (pf-adversary, round md7pjz-recovery): "utf-16le".decode()
        # raises UnicodeDecodeError on this input, which is neither a
        # truncation nor a tag mismatch, so it needs its own coverage
        # distinct from the two malformed-length cases above.
        malformed = bytes([2, 0, 0, 0]) + bytes([0x00, 0xD8])
        with self.assertRaises(wire.WireDecodeError):
            wire.read_untagged_wstring(malformed, 0)


class RequireExhaustedTests(unittest.TestCase):
    def test_exact_offset_passes(self):
        wire.require_exhausted(b"\x01\x02\x03", 3)  # must not raise

    def test_empty_buffer_at_offset_zero_passes(self):
        wire.require_exhausted(b"", 0)  # must not raise

    def test_one_trailing_byte_fails_closed(self):
        with self.assertRaises(wire.WireDecodeError):
            wire.require_exhausted(b"\x01\x02\x03", 2)

    def test_many_trailing_bytes_fail_closed(self):
        with self.assertRaises(wire.WireDecodeError):
            wire.require_exhausted(b"\x01" * 40, 3)


class U8U32TagReaderTests(unittest.TestCase):
    def test_read_u8tag_wrong_tag_fails_closed(self):
        with self.assertRaises(wire.WireDecodeError):
            wire.read_u8tag(bytes([0x08, 5]), 0, 0x0B)

    def test_read_u8tag_truncated_fails_closed(self):
        with self.assertRaises(wire.WireDecodeError):
            wire.read_u8tag(bytes([0x08]), 0, 0x08)

    def test_read_u32tag_round_trip(self):
        encoded = bytes([0x14]) + (12345).to_bytes(4, "little")
        value, offset = wire.read_u32tag(encoded, 0, 0x14)
        self.assertEqual(value, 12345)
        self.assertEqual(offset, 5)


class U16TagTests(unittest.TestCase):
    # Added round `wkrfl6` for ui_tracepath_wire.py -- see u16tag's own
    # docstring for why no earlier resolved class needed a write-direction
    # u16 helper.
    def test_round_trip(self):
        encoded = wire.u16tag(0x0F, 0x0165)
        self.assertEqual(encoded[0], 0x0F)
        value, offset = wire.read_u16tag(encoded, 0, 0x0F)
        self.assertEqual(value, 0x0165)
        self.assertEqual(offset, len(encoded))

    def test_masks_to_16_bits(self):
        encoded = wire.u16tag(0x0F, (1 << 16) + 7)
        value, _ = wire.read_u16tag(encoded, 0, 0x0F)
        self.assertEqual(value, 7)

    def test_read_u16tag_wrong_tag_fails_closed(self):
        encoded = wire.u16tag(0x0F, 1)
        with self.assertRaises(wire.WireDecodeError):
            wire.read_u16tag(encoded, 0, 0x99)

    def test_read_u16tag_truncated_fails_closed(self):
        with self.assertRaises(wire.WireDecodeError):
            wire.read_u16tag(bytes([0x0F, 1]), 0, 0x0F)

    def test_matches_the_gt246_capture_bytes_for_field1(self):
        # RE-236's static bonus this round: GT-246's real captured frame
        # opens with tag 0x0F, value 0 (little-endian 00 00).
        encoded = wire.u16tag(0x0F, 0)
        self.assertEqual(encoded, bytes.fromhex("0F0000"))


class U32TagEncodeTests(unittest.TestCase):
    # read_u32tag already existed (U8U32TagReaderTests above); u32tag is the
    # write-direction counterpart, added round `wkrfl6` alongside u16tag.
    def test_round_trip(self):
        encoded = wire.u32tag(0x14, 0x12345678)
        self.assertEqual(encoded[0], 0x14)
        value, offset = wire.read_u32tag(encoded, 0, 0x14)
        self.assertEqual(value, 0x12345678)
        self.assertEqual(offset, len(encoded))

    def test_masks_to_32_bits(self):
        encoded = wire.u32tag(0x14, (1 << 32) + 9)
        value, _ = wire.read_u32tag(encoded, 0, 0x14)
        self.assertEqual(value, 9)


if __name__ == "__main__":
    unittest.main()
