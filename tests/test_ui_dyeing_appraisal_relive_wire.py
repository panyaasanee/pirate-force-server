"""Pure unit tests for ``ui_dyeing_appraisal_relive_wire.py`` -- round-trip
+ fail-closed (truncated / wrong-tag / trailing-bytes) coverage for the
seven fully-tagged classes across the ``Appraisal``/``Dyeing``/``Relive``
catalog groups (``DyeingVitalReq`` added round `42w728`, see that module's
docstring for the tag-0x44 provenance). Not wiring tests -- see
``ui_social_wire.py``'s module docstring. The remaining excluded classes
(``UserSetting_UpdateServerSettingVital``, ``ReliveMarkerVital``,
``ItemLockVital``, ``DyeingModule_Client``, ``AppraisalModule_Client``)
have no module and no tests here -- see
``ui_dyeing_appraisal_relive_wire.py``'s module docstring for why.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    ui_dyeing_appraisal_relive_wire as dar,
)


class VitalIdTests(unittest.TestCase):
    # pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv (grep
    # `Appraisal`/`Dyeing`/`Relive`) -- pins every constant this module
    # hardcodes so a future transposition/typo fails the suite instead of
    # shipping silently (same pattern as ui_collectionobj_wire.py's
    # VitalIdTests).

    def test_appraisal_vital_id_matches_the_registry(self):
        self.assertEqual(dar.APPRAISAL_VITAL_ID, 0x2AB1)

    def test_appraisal_stop_vital_id_matches_the_registry(self):
        self.assertEqual(dar.APPRAISAL_STOP_VITAL_ID, 0x45CF)

    def test_dyeing_vital_res_id_matches_the_registry(self):
        self.assertEqual(dar.DYEING_VITAL_RES_ID, 0x2A00)

    def test_dyeing_remove_vital_id_matches_the_registry(self):
        self.assertEqual(dar.DYEING_REMOVE_VITAL_ID, 0x3E1C)

    def test_dyeing_ship_vital_req_id_matches_the_registry(self):
        self.assertEqual(dar.DYEING_SHIP_VITAL_REQ_ID, 0x441A)

    def test_relive_vital_id_matches_the_registry(self):
        self.assertEqual(dar.RELIVE_VITAL_ID, 0x1AD4)

    def test_dyeing_vital_req_id_matches_the_registry(self):
        self.assertEqual(dar.DYEING_VITAL_REQ_ID, 0x29E4)

    def test_all_seven_ids_are_distinct(self):
        ids = {
            dar.APPRAISAL_VITAL_ID,
            dar.APPRAISAL_STOP_VITAL_ID,
            dar.DYEING_VITAL_RES_ID,
            dar.DYEING_REMOVE_VITAL_ID,
            dar.DYEING_SHIP_VITAL_REQ_ID,
            dar.RELIVE_VITAL_ID,
            dar.DYEING_VITAL_REQ_ID,
        }
        self.assertEqual(len(ids), 7)


class AppraisalWireTests(unittest.TestCase):
    def _fields(self):
        return dar.AppraisalFields(field1_u8=7, field2_u32=1000, field3_u32=2000)

    def test_round_trip(self):
        fields = self._fields()
        payload = dar.encode_appraisal_payload(fields)
        self.assertEqual(dar.decode_appraisal_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = dar.encode_appraisal_payload(self._fields())
        self.assertIsNone(dar.decode_appraisal_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = dar.encode_appraisal_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    dar.decode_appraisal_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = dar.encode_appraisal_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(dar.decode_appraisal_payload(corrupted))

    def test_wrong_tag_at_field3_fails_closed(self):
        payload = bytearray(dar.encode_appraisal_payload(self._fields()))
        payload[-5] = 0x99  # the trailing u32 field's tag byte
        self.assertIsNone(dar.decode_appraisal_payload(bytes(payload)))


class AppraisalStopWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = dar.AppraisalStopFields()
        payload = dar.encode_appraisal_stop_payload(fields)
        self.assertEqual(payload, b"")
        self.assertEqual(dar.decode_appraisal_stop_payload(payload), fields)

    def test_nonempty_payload_fails_closed(self):
        self.assertIsNone(dar.decode_appraisal_stop_payload(b"\xaa"))
        self.assertIsNone(dar.decode_appraisal_stop_payload(b"\xaa" * 12))


class DyeingVitalResWireTests(unittest.TestCase):
    def _fields(self):
        return dar.DyeingVitalResFields(field1_u8=3)

    def test_round_trip(self):
        fields = self._fields()
        payload = dar.encode_dyeing_vital_res_payload(fields)
        self.assertEqual(dar.decode_dyeing_vital_res_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = dar.encode_dyeing_vital_res_payload(self._fields())
        self.assertIsNone(dar.decode_dyeing_vital_res_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = dar.encode_dyeing_vital_res_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    dar.decode_dyeing_vital_res_payload(clean + extra)
                )

    def test_wrong_tag_fails_closed(self):
        payload = dar.encode_dyeing_vital_res_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(dar.decode_dyeing_vital_res_payload(corrupted))


class DyeingRemoveWireTests(unittest.TestCase):
    def _fields(self):
        return dar.DyeingRemoveFields(field1_u64=111, field2_u64=222)

    def test_round_trip(self):
        fields = self._fields()
        payload = dar.encode_dyeing_remove_payload(fields)
        self.assertEqual(dar.decode_dyeing_remove_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = dar.encode_dyeing_remove_payload(self._fields())
        self.assertIsNone(dar.decode_dyeing_remove_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = dar.encode_dyeing_remove_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    dar.decode_dyeing_remove_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = dar.encode_dyeing_remove_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(dar.decode_dyeing_remove_payload(corrupted))

    def test_wrong_tag_at_field2_fails_closed(self):
        payload = bytearray(dar.encode_dyeing_remove_payload(self._fields()))
        payload[-9] = 0x99  # the trailing u64 field's tag byte
        self.assertIsNone(dar.decode_dyeing_remove_payload(bytes(payload)))


class DyeingShipWireTests(unittest.TestCase):
    def _fields(self):
        return dar.DyeingShipFields(field1_u64=555, field2_u32=666)

    def test_round_trip(self):
        fields = self._fields()
        payload = dar.encode_dyeing_ship_payload(fields)
        self.assertEqual(dar.decode_dyeing_ship_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = dar.encode_dyeing_ship_payload(self._fields())
        self.assertIsNone(dar.decode_dyeing_ship_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = dar.encode_dyeing_ship_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    dar.decode_dyeing_ship_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = dar.encode_dyeing_ship_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(dar.decode_dyeing_ship_payload(corrupted))

    def test_wrong_tag_at_field2_fails_closed(self):
        payload = bytearray(dar.encode_dyeing_ship_payload(self._fields()))
        payload[-5] = 0x99  # the trailing u32 field's tag byte
        self.assertIsNone(dar.decode_dyeing_ship_payload(bytes(payload)))


class DyeingVitalReqWireTests(unittest.TestCase):
    def _fields(self):
        return dar.DyeingVitalReqFields(
            field1_u64=987654321, field2_string8=b"a dye color name, opaque"
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = dar.encode_dyeing_vital_req_payload(fields)
        self.assertEqual(dar.decode_dyeing_vital_req_payload(payload), fields)

    def test_round_trip_with_empty_string8(self):
        fields = dar.DyeingVitalReqFields(field1_u64=0, field2_string8=b"")
        payload = dar.encode_dyeing_vital_req_payload(fields)
        self.assertEqual(dar.decode_dyeing_vital_req_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = dar.encode_dyeing_vital_req_payload(self._fields())
        self.assertIsNone(dar.decode_dyeing_vital_req_payload(payload[:-1]))

    def test_truncated_string8_length_header_fails_closed(self):
        # cut inside the u32 length prefix itself, not the string payload
        payload = dar.encode_dyeing_vital_req_payload(self._fields())
        cut_before_length_complete = payload[:-len(b"a dye color name, opaque") - 2]
        self.assertIsNone(
            dar.decode_dyeing_vital_req_payload(cut_before_length_complete)
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = dar.encode_dyeing_vital_req_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    dar.decode_dyeing_vital_req_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = dar.encode_dyeing_vital_req_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(dar.decode_dyeing_vital_req_payload(corrupted))

    def test_wrong_tag_at_field2_string8_fails_closed(self):
        payload = bytearray(dar.encode_dyeing_vital_req_payload(self._fields()))
        payload[9] = 0x99  # the string8 field's own tag byte, right after u64
        self.assertIsNone(dar.decode_dyeing_vital_req_payload(bytes(payload)))

    def test_string8_payload_bytes_are_preserved_exactly(self):
        # opaque bytes -- no charset assumed, arbitrary bytes must survive
        fields = dar.DyeingVitalReqFields(
            field1_u64=1, field2_string8=bytes(range(256))
        )
        payload = dar.encode_dyeing_vital_req_payload(fields)
        self.assertEqual(dar.decode_dyeing_vital_req_payload(payload), fields)


class ReliveWireTests(unittest.TestCase):
    def _fields(self):
        return dar.ReliveFields(field1_u8=1, field2_u8=0)

    def test_round_trip(self):
        fields = self._fields()
        payload = dar.encode_relive_payload(fields)
        self.assertEqual(dar.decode_relive_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = dar.encode_relive_payload(self._fields())
        self.assertIsNone(dar.decode_relive_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = dar.encode_relive_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(dar.decode_relive_payload(clean + extra))

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = dar.encode_relive_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(dar.decode_relive_payload(corrupted))

    def test_wrong_tag_at_field2_fails_closed(self):
        payload = bytearray(dar.encode_relive_payload(self._fields()))
        payload[-2] = 0x99  # the second u8 field's tag byte
        self.assertIsNone(dar.decode_relive_payload(bytes(payload)))


if __name__ == "__main__":
    unittest.main()
