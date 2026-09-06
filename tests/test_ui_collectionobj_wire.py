"""Pure unit tests for ``ui_collectionobj_wire.py`` -- round-trip +
fail-closed (truncated / wrong-tag / trailing-bytes) coverage for the four
fully-tagged ``CollectionObj_*`` classes. Not wiring tests -- see
``ui_social_wire.py``'s module docstring. The two excluded classes
(``UpdateCollectEffectVital``, ``UpdateCollectionObjBagVital``) have no
module and no tests here -- see ``ui_collectionobj_wire.py``'s module
docstring for why.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_collectionobj_wire as collectionobj  # noqa: E402


class VitalIdTests(unittest.TestCase):
    # pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv (grep
    # `CollectionObj_`) -- pins every constant this module hardcodes so a
    # future transposition/typo fails the suite instead of shipping
    # silently (same pattern as ui_express_wire.py's VitalIdTests).

    def test_collect_obj_vital_id_matches_the_registry(self):
        self.assertEqual(
            collectionobj.COLLECTIONOBJ_COLLECT_OBJ_VITAL_ID, 0xABA4
        )

    def test_get_collect_effect_vital_id_matches_the_registry(self):
        self.assertEqual(
            collectionobj.COLLECTIONOBJ_GET_COLLECT_EFFECT_VITAL_ID, 0xF851
        )

    def test_sailor_level_up_request_vital_id_matches_the_registry(self):
        self.assertEqual(
            collectionobj.COLLECTIONOBJ_SAILOR_LEVEL_UP_REQUEST_VITAL_ID,
            0x3B06,
        )

    def test_sailor_lv_up_response_vital_id_matches_the_registry(self):
        self.assertEqual(
            collectionobj.COLLECTIONOBJ_SAILOR_LV_UP_RESPONSE_VITAL_ID,
            0x1B8B,
        )

    def test_all_four_ids_are_distinct(self):
        ids = {
            collectionobj.COLLECTIONOBJ_COLLECT_OBJ_VITAL_ID,
            collectionobj.COLLECTIONOBJ_GET_COLLECT_EFFECT_VITAL_ID,
            collectionobj.COLLECTIONOBJ_SAILOR_LEVEL_UP_REQUEST_VITAL_ID,
            collectionobj.COLLECTIONOBJ_SAILOR_LV_UP_RESPONSE_VITAL_ID,
        }
        self.assertEqual(len(ids), 4)


class CollectObjWireTests(unittest.TestCase):
    def _fields(self):
        return collectionobj.CollectObjFields(
            field1_u64=1, field2_u8=2, field3_u8=3, field4_u8=4, field5_u64=5
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = collectionobj.encode_collect_obj_payload(fields)
        self.assertEqual(
            collectionobj.decode_collect_obj_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = collectionobj.encode_collect_obj_payload(self._fields())
        self.assertIsNone(
            collectionobj.decode_collect_obj_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = collectionobj.encode_collect_obj_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    collectionobj.decode_collect_obj_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = collectionobj.encode_collect_obj_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(collectionobj.decode_collect_obj_payload(corrupted))

    def test_wrong_tag_at_field5_fails_closed(self):
        payload = bytearray(
            collectionobj.encode_collect_obj_payload(self._fields())
        )
        payload[-9] = 0x99  # the trailing u64 field's tag byte
        self.assertIsNone(
            collectionobj.decode_collect_obj_payload(bytes(payload))
        )


class GetCollectEffectWireTests(unittest.TestCase):
    def _fields(self):
        return collectionobj.GetCollectEffectFields(
            field1_u16=1000, field2_u8=2
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = collectionobj.encode_get_collect_effect_payload(fields)
        self.assertEqual(
            collectionobj.decode_get_collect_effect_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = collectionobj.encode_get_collect_effect_payload(
            self._fields()
        )
        self.assertIsNone(
            collectionobj.decode_get_collect_effect_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = collectionobj.encode_get_collect_effect_payload(
            self._fields()
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    collectionobj.decode_get_collect_effect_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = collectionobj.encode_get_collect_effect_payload(
            self._fields()
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            collectionobj.decode_get_collect_effect_payload(corrupted)
        )


class SailorLevelUpRequestWireTests(unittest.TestCase):
    def _fields(self):
        return collectionobj.SailorLevelUpRequestFields(
            field1_u64=1, field2_u64=2, field3_u64=3
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = collectionobj.encode_sailor_level_up_request_payload(
            fields
        )
        self.assertEqual(
            collectionobj.decode_sailor_level_up_request_payload(payload),
            fields,
        )

    def test_truncated_payload_fails_closed(self):
        payload = collectionobj.encode_sailor_level_up_request_payload(
            self._fields()
        )
        self.assertIsNone(
            collectionobj.decode_sailor_level_up_request_payload(
                payload[:-1]
            )
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = collectionobj.encode_sailor_level_up_request_payload(
            self._fields()
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    collectionobj.decode_sailor_level_up_request_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = collectionobj.encode_sailor_level_up_request_payload(
            self._fields()
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            collectionobj.decode_sailor_level_up_request_payload(corrupted)
        )


class SailorLvUpResponseWireTests(unittest.TestCase):
    def _fields(self):
        return collectionobj.SailorLvUpResponseFields(
            field1_u8=1, field2_u64=2
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = collectionobj.encode_sailor_lv_up_response_payload(fields)
        self.assertEqual(
            collectionobj.decode_sailor_lv_up_response_payload(payload),
            fields,
        )

    def test_truncated_payload_fails_closed(self):
        payload = collectionobj.encode_sailor_lv_up_response_payload(
            self._fields()
        )
        self.assertIsNone(
            collectionobj.decode_sailor_lv_up_response_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = collectionobj.encode_sailor_lv_up_response_payload(
            self._fields()
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    collectionobj.decode_sailor_lv_up_response_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = collectionobj.encode_sailor_lv_up_response_payload(
            self._fields()
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            collectionobj.decode_sailor_lv_up_response_payload(corrupted)
        )


if __name__ == "__main__":
    unittest.main()
