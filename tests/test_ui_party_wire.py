"""Pure unit tests for ``ui_party_wire.py`` -- ``PartyInviteVital``
(``0x37B1``) / ``PartyCmdVital`` (``0x2466``) encode/decode.

Not wiring tests: nothing here is wired into ``runtime.py`` (see
``ui_social_wire.py``'s module docstring and COO-DECISION ``20260904_1244``
item 3). These tests pin the field SHAPE the registry proves; they say
nothing about what any field means in the game.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_party_wire as party  # noqa: E402


class PartyInviteWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = party.PartyInviteFields(
            field1_u8=7, field2_u64=0xDEADBEEF, field3_wstring="Blackbeard",
        )
        payload = party.encode_party_invite_payload(fields)
        decoded = party.decode_party_invite_payload(payload)
        self.assertEqual(decoded, fields)

    def test_field_order_matches_registry(self):
        fields = party.PartyInviteFields(1, 2, "x")
        payload = party.encode_party_invite_payload(fields)
        self.assertEqual(payload[0], 0x08)  # field1 tag
        self.assertEqual(payload[2], 0x32)  # field2 tag, right after field1

    def test_wrong_first_tag_fails_closed(self):
        payload = bytes([0x99, 1]) + party.encode_party_invite_payload(
            party.PartyInviteFields(1, 2, "x")
        )[2:]
        self.assertIsNone(party.decode_party_invite_payload(payload))

    def test_truncated_payload_fails_closed(self):
        payload = party.encode_party_invite_payload(
            party.PartyInviteFields(1, 2, "hello")
        )
        self.assertIsNone(party.decode_party_invite_payload(payload[:-3]))

    def test_empty_buffer_fails_closed(self):
        self.assertIsNone(party.decode_party_invite_payload(b""))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        # COO-DECISION 20260904_1745 item 2, from a pf-adversary finding on
        # round qwhlua: a payload whose first bytes match this class's
        # field shape exactly, followed by unexplained trailer bytes, used
        # to decode successfully anyway. A class this project's field
        # model does not fully cover must surface as UNPARSED, not as a
        # false "decoded".
        clean = party.encode_party_invite_payload(
            party.PartyInviteFields(1, 2, "hello")
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    party.decode_party_invite_payload(clean + extra)
                )

    def test_malformed_wstring_field_fails_closed_not_raises(self):
        # pf-adversary (round md7pjz-recovery): the module's fail-closed
        # contract promised every decode_* returns None on malformed input,
        # but an unpaired UTF-16 surrogate inside the field3 wstring used to
        # escape as a raw UnicodeDecodeError instead -- reproduced here at
        # the payload-decode level (not just the raw wire.read_untagged_
        # wstring level covered in test_ui_social_wire.py) since this is the
        # entry point a future dispatch caller would actually use.
        payload = bytearray(
            party.encode_party_invite_payload(
                party.PartyInviteFields(1, 2, "x")
            )
        )
        # field3's untagged-wstring payload is the last 2 bytes (length=1
        # char "x", encoded as 2 bytes of UTF-16LE) -- overwrite with a lone
        # high surrogate, an even-length, in-bounds, still-invalid payload.
        payload[-2:] = bytes([0x00, 0xD8])
        self.assertIsNone(party.decode_party_invite_payload(bytes(payload)))


class PartyCmdWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = party.PartyCmdFields(field1_u8=3, field2_u64=42)
        payload = party.encode_party_cmd_payload(fields)
        decoded = party.decode_party_cmd_payload(payload)
        self.assertEqual(decoded, fields)

    def test_payload_is_exactly_eleven_bytes(self):
        # tag(1)+u8(1) + tag(1)+u64(8) = 11, no trailing bytes -- PartyCmdVital
        # has no third field in the registry, unlike PartyInviteVital.
        payload = party.encode_party_cmd_payload(party.PartyCmdFields(0, 0))
        self.assertEqual(len(payload), 11)

    def test_wrong_second_tag_fails_closed(self):
        good = party.encode_party_cmd_payload(party.PartyCmdFields(1, 2))
        corrupted = good[:2] + bytes([0x99]) + good[3:]
        self.assertIsNone(party.decode_party_cmd_payload(corrupted))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = party.encode_party_cmd_payload(party.PartyCmdFields(1, 2))
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    party.decode_party_cmd_payload(clean + extra)
                )


if __name__ == "__main__":
    unittest.main()
