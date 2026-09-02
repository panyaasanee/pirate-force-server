"""CheatVital (0x162E): payload matches the pinned narrow-string layout
(PF_SERIALIZER_FIELDS.tsv rows 565-566), CORRECTED 2026-09-02 to carry the
0x44 string tag the client's helper pushes before the length
(PF_A2_STRING_WIRE_TAG_DELTA.tsv rows 565/566, tag instructions 0x0089A6F1 /
0x0089A75C)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.cheat_wire import (
    CHEAT_VITAL_ID,
    CheatVitalBody,
    GmCheatWireError,
    MAX_STRING_LENGTH,
    STRING8_TAG,
    decode_cheat_vital_payload,
    make_cheat_vital_payload,
)


class CheatVitalEncodeTests(unittest.TestCase):
    def test_payload_is_tag_then_length_prefix_then_bytes(self):
        payload = make_cheat_vital_payload(b"hp 999")
        self.assertEqual(payload[0], STRING8_TAG)
        self.assertEqual(payload[0], 0x44)
        self.assertEqual(payload[1:5], (6).to_bytes(4, "little"))
        self.assertEqual(payload[5:], b"hp 999")
        # The whole field is 5+N bytes, not the 4+N this module shipped
        # before the 2026-09-02 correction.
        self.assertEqual(len(payload), 5 + 6)

    def test_empty_string_is_a_valid_payload(self):
        payload = make_cheat_vital_payload(b"")
        self.assertEqual(payload, bytes((STRING8_TAG,)) + (0).to_bytes(4, "little"))

    def test_decode_rejects_a_wrong_string_tag(self):
        payload = bytearray(make_cheat_vital_payload(b"hp 999"))
        payload[0] = 0x48  # the WIDE string tag: right shape, wrong kind
        with self.assertRaises(GmCheatWireError):
            decode_cheat_vital_payload(bytes(payload))

    def test_decode_rejects_the_old_untagged_shape(self):
        # Exactly what this module used to emit.  It must not silently
        # decode: the first length byte would be read as a tag.
        with self.assertRaises(GmCheatWireError):
            decode_cheat_vital_payload((6).to_bytes(4, "little") + b"hp 999")

    def test_rejects_non_bytes_input(self):
        with self.assertRaises(TypeError):
            make_cheat_vital_payload("hp 999")  # type: ignore[arg-type]

    def test_rejects_oversized_text(self):
        with self.assertRaises(GmCheatWireError):
            make_cheat_vital_payload(b"x" * (MAX_STRING_LENGTH + 1))

    def test_accepts_text_at_exactly_the_length_cap(self):
        text = b"x" * MAX_STRING_LENGTH
        payload = make_cheat_vital_payload(text)
        self.assertEqual(len(payload), 1 + 4 + MAX_STRING_LENGTH)


class CheatVitalDecodeTests(unittest.TestCase):
    def test_round_trip_recovers_the_original_bytes(self):
        original = b"whatever bytes a real capture would show"
        payload = make_cheat_vital_payload(original)
        decoded = decode_cheat_vital_payload(payload)
        self.assertIsInstance(decoded, CheatVitalBody)
        self.assertEqual(decoded.text, original)

    def test_round_trip_empty_string(self):
        payload = make_cheat_vital_payload(b"")
        decoded = decode_cheat_vital_payload(payload)
        self.assertEqual(decoded.text, b"")

    def test_decoded_text_is_bytes_not_str(self):
        # Module docstring: byte encoding (cp874/ascii/other) is not proven,
        # so this codec must never silently decode to str.
        payload = make_cheat_vital_payload(b"\xa1\xa2\xa3")
        decoded = decode_cheat_vital_payload(payload)
        self.assertIsInstance(decoded.text, bytes)
        self.assertEqual(decoded.text, b"\xa1\xa2\xa3")

    def test_rejects_non_bytes_input(self):
        with self.assertRaises(TypeError):
            decode_cheat_vital_payload("not bytes")  # type: ignore[arg-type]

    def test_rejects_buffer_shorter_than_tag_plus_length_prefix(self):
        with self.assertRaises(GmCheatWireError):
            decode_cheat_vital_payload(bytes((STRING8_TAG,)) + b"\x01\x00\x00")

    def test_rejects_declared_length_longer_than_buffer(self):
        # Declares 10 bytes but only 3 follow.  The tag must be correct, or
        # this test would pass on the tag check and never reach the branch it
        # is named after (that is exactly what the 2026-09-02 tag correction
        # did to it before this pin was moved).
        malformed = bytes((STRING8_TAG,)) + (10).to_bytes(4, "little") + b"abc"
        with self.assertRaises(GmCheatWireError):
            decode_cheat_vital_payload(malformed)

    def test_rejects_trailing_bytes_after_the_declared_string(self):
        payload = make_cheat_vital_payload(b"abc") + b"\x00extra"
        with self.assertRaises(GmCheatWireError):
            decode_cheat_vital_payload(payload)

    def test_rejects_declared_length_over_the_cap_even_if_buffer_is_long_enough(self):
        malformed = (
            bytes((STRING8_TAG,))
            + (MAX_STRING_LENGTH + 1).to_bytes(4, "little")
            + b"x" * 8
        )
        with self.assertRaises(GmCheatWireError):
            decode_cheat_vital_payload(malformed)
        # and prove the message is the cap one, not the tag one -- this guard
        # was silently disarmed once already.
        with self.assertRaisesRegex(GmCheatWireError, "MAX_STRING_LENGTH"):
            decode_cheat_vital_payload(malformed)


class CheatVitalIdTests(unittest.TestCase):
    def test_vital_id_matches_bridge_registry(self):
        # pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv row 14:
        # 0x162E CheatVital
        self.assertEqual(CHEAT_VITAL_ID, 0x162E)


if __name__ == "__main__":
    unittest.main()
