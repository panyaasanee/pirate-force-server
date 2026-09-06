"""Pure unit tests for ``ui_express_wire.py`` -- round-trip + fail-closed
(truncated / wrong-tag / trailing-bytes) coverage for the four fully-tagged
``Express_*`` classes. Not wiring tests -- see ``ui_social_wire.py``'s
module docstring. The eight excluded classes (four with unresolved TSV
rows, four with no TSV rows at all) have no module and no tests here -- see
``ui_express_wire.py``'s module docstring for why.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_express_wire as express  # noqa: E402


class VitalIdTests(unittest.TestCase):
    # pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv (grep
    # `^0x....\tExpress_`) -- pins every constant this module hardcodes so a
    # future transposition/typo (e.g. copy-paste from the wrong TSV row)
    # fails the suite instead of shipping silently (same pattern as
    # ui_pets_wire.py's VitalIdTests, added there after pf-adversary found
    # the gap in round `avt7pt`).

    def test_client_remove_express_vital_id_matches_the_registry(self):
        self.assertEqual(
            express.EXPRESS_CLIENT_REMOVE_EXPRESS_VITAL_ID, 0xD82D
        )

    def test_client_send_express_result_vital_id_matches_the_registry(self):
        self.assertEqual(
            express.EXPRESS_CLIENT_SEND_EXPRESS_RESULT_VITAL_ID, 0x1091
        )

    def test_client_claim_express_vital_id_matches_the_registry(self):
        self.assertEqual(
            express.EXPRESS_CLIENT_CLAIM_EXPRESS_VITAL_ID, 0xD5A8
        )

    def test_reset_express_count_vital_id_matches_the_registry(self):
        self.assertEqual(
            express.EXPRESS_RESET_EXPRESS_COUNT_VITAL_ID, 0xBECD
        )

    def test_remove_and_claim_ids_are_distinct_despite_shared_wire_shape(self):
        # ClientRemoveExpressVital and ClientcClaimExpressVital share an
        # identical field table (same shared-serializer span in the TSV)
        # but are still two different actions on the wire -- guard against
        # a future edit collapsing them onto the same id by accident.
        self.assertNotEqual(
            express.EXPRESS_CLIENT_REMOVE_EXPRESS_VITAL_ID,
            express.EXPRESS_CLIENT_CLAIM_EXPRESS_VITAL_ID,
        )


class ClientRemoveExpressWireTests(unittest.TestCase):
    def _fields(self):
        return express.ClientRemoveExpressFields(
            field1_u64=1, field2_u64=2, field3_u8=3
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = express.encode_client_remove_express_payload(fields)
        self.assertEqual(
            express.decode_client_remove_express_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = express.encode_client_remove_express_payload(self._fields())
        self.assertIsNone(
            express.decode_client_remove_express_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = express.encode_client_remove_express_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    express.decode_client_remove_express_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = express.encode_client_remove_express_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            express.decode_client_remove_express_payload(corrupted)
        )

    def test_wrong_tag_at_field3_fails_closed(self):
        payload = bytearray(
            express.encode_client_remove_express_payload(self._fields())
        )
        payload[-2] = 0x99  # the trailing u8 field's tag byte
        self.assertIsNone(
            express.decode_client_remove_express_payload(bytes(payload))
        )


class ClientSendExpressResultWireTests(unittest.TestCase):
    def _fields(self):
        return express.ClientSendExpressResultFields(
            field1_u64=1, field2_u8=2, field3_wstring="hello"
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = express.encode_client_send_express_result_payload(fields)
        self.assertEqual(
            express.decode_client_send_express_result_payload(payload), fields
        )

    def test_empty_wstring_round_trips(self):
        fields = express.ClientSendExpressResultFields(
            field1_u64=1, field2_u8=2, field3_wstring=""
        )
        payload = express.encode_client_send_express_result_payload(fields)
        self.assertEqual(
            express.decode_client_send_express_result_payload(payload), fields
        )

    def test_wstring_is_last_field(self):
        payload = express.encode_client_send_express_result_payload(
            express.ClientSendExpressResultFields(0, 0, "tail")
        )
        # 9 (u64 tag+value) + 2 (u8 tag+value) = 11 bytes before the
        # wstring's u32 length prefix starts.
        self.assertEqual(payload[11:15], (8).to_bytes(4, "little"))

    def test_truncated_payload_fails_closed(self):
        payload = express.encode_client_send_express_result_payload(
            self._fields()
        )
        self.assertIsNone(
            express.decode_client_send_express_result_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = express.encode_client_send_express_result_payload(
            self._fields()
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    express.decode_client_send_express_result_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = express.encode_client_send_express_result_payload(
            self._fields()
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            express.decode_client_send_express_result_payload(corrupted)
        )


class ClientClaimExpressWireTests(unittest.TestCase):
    def _fields(self):
        return express.ClientClaimExpressFields(
            field1_u64=1, field2_u64=2, field3_u8=3
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = express.encode_client_claim_express_payload(fields)
        self.assertEqual(
            express.decode_client_claim_express_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = express.encode_client_claim_express_payload(self._fields())
        self.assertIsNone(
            express.decode_client_claim_express_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = express.encode_client_claim_express_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    express.decode_client_claim_express_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = express.encode_client_claim_express_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            express.decode_client_claim_express_payload(corrupted)
        )

    def test_same_field_values_as_remove_but_different_type(self):
        # ClientRemoveExpressFields and ClientClaimExpressFields share a
        # wire shape (see module docstring) but are not the same Python
        # type -- guard against a future refactor accidentally merging
        # them into one dataclass and silently erasing the vital-id
        # distinction.
        remove_fields = express.ClientRemoveExpressFields(1, 2, 3)
        claim_fields = express.ClientClaimExpressFields(1, 2, 3)
        self.assertNotEqual(type(remove_fields), type(claim_fields))
        self.assertEqual(
            express.encode_client_remove_express_payload(remove_fields),
            express.encode_client_claim_express_payload(claim_fields),
        )


class ResetExpressCountWireTests(unittest.TestCase):
    def _fields(self):
        return express.ResetExpressCountFields(field1_u64=1, field2_u8=2)

    def test_round_trip(self):
        fields = self._fields()
        payload = express.encode_reset_express_count_payload(fields)
        self.assertEqual(
            express.decode_reset_express_count_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = express.encode_reset_express_count_payload(self._fields())
        self.assertIsNone(
            express.decode_reset_express_count_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = express.encode_reset_express_count_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    express.decode_reset_express_count_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = express.encode_reset_express_count_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            express.decode_reset_express_count_payload(corrupted)
        )


if __name__ == "__main__":
    unittest.main()
