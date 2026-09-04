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


if __name__ == "__main__":
    unittest.main()
