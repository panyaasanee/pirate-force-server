"""Pure unit tests for ``ui_mail_wire.py`` -- ``Community_SendMailVital``
(``0x6E12``) / ``Community_GetMailContentVital`` (``0xAF60``) /
``Community_DeleteMailVital`` (``0x8183``) encode/decode.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_mail_wire as mail  # noqa: E402


class SendMailWireTests(unittest.TestCase):
    def _fields(self):
        return mail.SendMailFields(
            field1_u64=1,
            field2_wstring="recipient",
            field3_u64=2,
            field4_wstring="subject",
            field5_wstring="body part 1",
            field6_wstring="body part 2",
            field7_wstring="",
            field8_wstring="attachment ref",
            field9_u8=0,
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = mail.encode_send_mail_payload(fields)
        decoded = mail.decode_send_mail_payload(payload)
        self.assertEqual(decoded, fields)

    def test_nine_fields_all_survive_round_trip_independently(self):
        # Five wstring fields in a row is exactly the shape most likely to
        # hide an off-by-one in field ordering; check each one lands where
        # it should rather than just comparing the whole dataclass.
        fields = self._fields()
        decoded = mail.decode_send_mail_payload(
            mail.encode_send_mail_payload(fields)
        )
        self.assertEqual(decoded.field2_wstring, "recipient")
        self.assertEqual(decoded.field4_wstring, "subject")
        self.assertEqual(decoded.field5_wstring, "body part 1")
        self.assertEqual(decoded.field6_wstring, "body part 2")
        self.assertEqual(decoded.field7_wstring, "")
        self.assertEqual(decoded.field8_wstring, "attachment ref")
        self.assertEqual(decoded.field9_u8, 0)

    def test_truncated_payload_fails_closed(self):
        payload = mail.encode_send_mail_payload(self._fields())
        self.assertIsNone(mail.decode_send_mail_payload(payload[:-1]))

    def test_corrupted_final_tag_fails_closed(self):
        payload = bytearray(mail.encode_send_mail_payload(self._fields()))
        payload[-2] = 0x99  # the trailing u8 field's tag byte
        self.assertIsNone(mail.decode_send_mail_payload(bytes(payload)))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        # COO-DECISION 20260904_1745 item 2 -- see test_ui_party_wire.py's
        # equivalent test for the full rationale.
        clean = mail.encode_send_mail_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(mail.decode_send_mail_payload(clean + extra))


class GetMailContentWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = mail.GetMailContentFields(
            field1_u64=10, field2_u64=20, field3_u8=1, field4_wstring="hi",
        )
        payload = mail.encode_get_mail_content_payload(fields)
        decoded = mail.decode_get_mail_content_payload(payload)
        self.assertEqual(decoded, fields)

    def test_wstring_is_last_field(self):
        payload = mail.encode_get_mail_content_payload(
            mail.GetMailContentFields(0, 0, 0, "tail")
        )
        # 9 (u64) + 9 (u64) + 2 (u8) = 20 bytes before the wstring starts.
        self.assertEqual(payload[20:24], (8).to_bytes(4, "little"))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = mail.encode_get_mail_content_payload(
            mail.GetMailContentFields(10, 20, 1, "hi")
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    mail.decode_get_mail_content_payload(clean + extra)
                )


class DeleteMailWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = mail.DeleteMailFields(field1_u64=5, field2_u64=6, field3_u8=1)
        payload = mail.encode_delete_mail_payload(fields)
        decoded = mail.decode_delete_mail_payload(payload)
        self.assertEqual(decoded, fields)

    def test_no_wstring_field(self):
        # Unlike its two siblings in this file, DeleteMailVital has no
        # string field at all per the registry -- confirm the payload is
        # exactly fixed-width.
        payload = mail.encode_delete_mail_payload(
            mail.DeleteMailFields(0, 0, 0)
        )
        self.assertEqual(len(payload), 9 + 9 + 2)

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = mail.encode_delete_mail_payload(
            mail.DeleteMailFields(44, 55, 6)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(mail.decode_delete_mail_payload(clean + extra))


if __name__ == "__main__":
    unittest.main()
