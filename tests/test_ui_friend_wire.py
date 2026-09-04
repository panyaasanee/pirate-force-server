"""Pure unit tests for ``ui_friend_wire.py`` --
``Community_RequestBeFriendVital`` (``0xB9E9``) /
``Community_RemoveFriendVital`` (``0x98A1``) encode/decode.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_friend_wire as friend  # noqa: E402


class RequestBeFriendWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = friend.RequestBeFriendFields(
            field1_u64=0x1122334455667788,
            field2_wstring="Anne Bonny",
            field3_u8=1,
        )
        payload = friend.encode_request_be_friend_payload(fields)
        decoded = friend.decode_request_be_friend_payload(payload)
        self.assertEqual(decoded, fields)

    def test_field_order_matches_registry(self):
        payload = friend.encode_request_be_friend_payload(
            friend.RequestBeFriendFields(1, "", 0)
        )
        self.assertEqual(payload[0], 0x32)  # u64 first
        # wstring's 4-byte length prefix follows immediately after the
        # 9-byte u64 field.
        self.assertEqual(payload[9], 0)
        self.assertEqual(payload[9:13], (0).to_bytes(4, "little"))

    def test_truncated_payload_fails_closed(self):
        payload = friend.encode_request_be_friend_payload(
            friend.RequestBeFriendFields(1, "hi", 1)
        )
        self.assertIsNone(
            friend.decode_request_be_friend_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        # COO-DECISION 20260904_1745 item 2 -- see test_ui_party_wire.py's
        # equivalent test for the full rationale.
        clean = friend.encode_request_be_friend_payload(
            friend.RequestBeFriendFields(1, "hi", 1)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    friend.decode_request_be_friend_payload(clean + extra)
                )


class RemoveFriendWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = friend.RemoveFriendFields(
            field1_u64=1, field2_u64=2, field3_u8=0,
        )
        payload = friend.encode_remove_friend_payload(fields)
        decoded = friend.decode_remove_friend_payload(payload)
        self.assertEqual(decoded, fields)

    def test_payload_length_is_two_u64_fields_plus_one_u8_field(self):
        payload = friend.encode_remove_friend_payload(
            friend.RemoveFriendFields(0, 0, 0)
        )
        self.assertEqual(len(payload), 9 + 9 + 2)

    def test_two_u64_fields_are_independent(self):
        fields = friend.RemoveFriendFields(
            field1_u64=0xAAAA, field2_u64=0xBBBB, field3_u8=0,
        )
        decoded = friend.decode_remove_friend_payload(
            friend.encode_remove_friend_payload(fields)
        )
        self.assertNotEqual(decoded.field1_u64, decoded.field2_u64)
        self.assertEqual(decoded.field1_u64, 0xAAAA)
        self.assertEqual(decoded.field2_u64, 0xBBBB)

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = friend.encode_remove_friend_payload(
            friend.RemoveFriendFields(1, 2, 0)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    friend.decode_remove_friend_payload(clean + extra)
                )


if __name__ == "__main__":
    unittest.main()
