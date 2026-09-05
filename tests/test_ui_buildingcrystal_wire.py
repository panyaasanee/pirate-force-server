"""Pure unit tests for ``ui_buildingcrystal_wire.py`` -- 11 of the
``BuildingCrystal_`` catalog group's 13 classes' encode/decode.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring.
``BuildingCrystal_UpdateCrystalSlotVital`` and ``BuildingCrystal_
UpdateNextAbsorbTime`` are out of scope (see ``ui_buildingcrystal_wire.py``'s
module docstring) and have no module/tests here.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_buildingcrystal_wire as bc  # noqa: E402


class PurchaseServiceWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.PurchaseServiceFields(field1_u8=1, field2_u8=2)
        payload = bc.encode_purchase_service_payload(fields)
        self.assertEqual(bc.decode_purchase_service_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_purchase_service_payload(
            bc.PurchaseServiceFields(1, 2)
        )
        self.assertIsNone(bc.decode_purchase_service_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        # COO-DECISION 20260904_1745 item 2 -- see test_ui_party_wire.py's
        # equivalent test for the full rationale.
        clean = bc.encode_purchase_service_payload(
            bc.PurchaseServiceFields(1, 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_purchase_service_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_purchase_service_payload(
            bc.PurchaseServiceFields(1, 2)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(bc.decode_purchase_service_payload(corrupted))


class OpenCrystalSlotWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.OpenCrystalSlotFields(
            field1_u64=99, field2_u8=1, field3_u8=2, field4_u8=3,
        )
        payload = bc.encode_open_crystal_slot_payload(fields)
        self.assertEqual(bc.decode_open_crystal_slot_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_open_crystal_slot_payload(
            bc.OpenCrystalSlotFields(1, 2, 3, 4)
        )
        self.assertIsNone(bc.decode_open_crystal_slot_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_open_crystal_slot_payload(
            bc.OpenCrystalSlotFields(1, 2, 3, 4)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_open_crystal_slot_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_open_crystal_slot_payload(
            bc.OpenCrystalSlotFields(1, 2, 3, 4)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(bc.decode_open_crystal_slot_payload(corrupted))


class IncreaseCrystalSlotMaxNutrientWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.IncreaseCrystalSlotMaxNutrientFields(
            field1_u8=1, field2_u8=2,
        )
        payload = bc.encode_increase_crystal_slot_max_nutrient_payload(fields)
        self.assertEqual(
            bc.decode_increase_crystal_slot_max_nutrient_payload(payload),
            fields,
        )

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_increase_crystal_slot_max_nutrient_payload(
            bc.IncreaseCrystalSlotMaxNutrientFields(1, 2)
        )
        self.assertIsNone(
            bc.decode_increase_crystal_slot_max_nutrient_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_increase_crystal_slot_max_nutrient_payload(
            bc.IncreaseCrystalSlotMaxNutrientFields(1, 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_increase_crystal_slot_max_nutrient_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_increase_crystal_slot_max_nutrient_payload(
            bc.IncreaseCrystalSlotMaxNutrientFields(1, 2)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            bc.decode_increase_crystal_slot_max_nutrient_payload(corrupted)
        )


class AddCrystalLusterWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.AddCrystalLusterFields(
            field1_u64=1, field2_u64=2, field3_u8=3, field4_u16=4,
        )
        payload = bc.encode_add_crystal_luster_payload(fields)
        self.assertEqual(bc.decode_add_crystal_luster_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_add_crystal_luster_payload(
            bc.AddCrystalLusterFields(1, 2, 3, 4)
        )
        self.assertIsNone(bc.decode_add_crystal_luster_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_add_crystal_luster_payload(
            bc.AddCrystalLusterFields(1, 2, 3, 4)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_add_crystal_luster_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_add_crystal_luster_payload(
            bc.AddCrystalLusterFields(1, 2, 3, 4)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(bc.decode_add_crystal_luster_payload(corrupted))


class SpeedUpBuildCrystalWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.SpeedUpBuildCrystalFields(field1_u8=7)
        payload = bc.encode_speed_up_build_crystal_payload(fields)
        self.assertEqual(
            bc.decode_speed_up_build_crystal_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_speed_up_build_crystal_payload(
            bc.SpeedUpBuildCrystalFields(7)
        )
        self.assertIsNone(
            bc.decode_speed_up_build_crystal_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_speed_up_build_crystal_payload(
            bc.SpeedUpBuildCrystalFields(7)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_speed_up_build_crystal_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_speed_up_build_crystal_payload(
            bc.SpeedUpBuildCrystalFields(7)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(bc.decode_speed_up_build_crystal_payload(corrupted))


class InsertCrystalToSlotWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.InsertCrystalToSlotFields(
            field1_u64=9, field2_u8=1, field3_u8=2, field4_u8=3,
        )
        payload = bc.encode_insert_crystal_to_slot_payload(fields)
        self.assertEqual(
            bc.decode_insert_crystal_to_slot_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_insert_crystal_to_slot_payload(
            bc.InsertCrystalToSlotFields(1, 2, 3, 4)
        )
        self.assertIsNone(
            bc.decode_insert_crystal_to_slot_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_insert_crystal_to_slot_payload(
            bc.InsertCrystalToSlotFields(1, 2, 3, 4)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_insert_crystal_to_slot_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_insert_crystal_to_slot_payload(
            bc.InsertCrystalToSlotFields(1, 2, 3, 4)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(bc.decode_insert_crystal_to_slot_payload(corrupted))


class ExtractCrystalFailedWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.ExtractCrystalFailedFields(
            field1_u8=1, field2_u8=2, field3_u8=3,
        )
        payload = bc.encode_extract_crystal_failed_payload(fields)
        self.assertEqual(
            bc.decode_extract_crystal_failed_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_extract_crystal_failed_payload(
            bc.ExtractCrystalFailedFields(1, 2, 3)
        )
        self.assertIsNone(
            bc.decode_extract_crystal_failed_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_extract_crystal_failed_payload(
            bc.ExtractCrystalFailedFields(1, 2, 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_extract_crystal_failed_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_extract_crystal_failed_payload(
            bc.ExtractCrystalFailedFields(1, 2, 3)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(bc.decode_extract_crystal_failed_payload(corrupted))


class ExtractCrystalFromSlotWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.ExtractCrystalFromSlotFields(
            field1_u64=9, field2_u8=1, field3_u8=2, field4_u8=3, field5_u8=4,
        )
        payload = bc.encode_extract_crystal_from_slot_payload(fields)
        self.assertEqual(
            bc.decode_extract_crystal_from_slot_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_extract_crystal_from_slot_payload(
            bc.ExtractCrystalFromSlotFields(1, 2, 3, 4, 5)
        )
        self.assertIsNone(
            bc.decode_extract_crystal_from_slot_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_extract_crystal_from_slot_payload(
            bc.ExtractCrystalFromSlotFields(1, 2, 3, 4, 5)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_extract_crystal_from_slot_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_extract_crystal_from_slot_payload(
            bc.ExtractCrystalFromSlotFields(1, 2, 3, 4, 5)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            bc.decode_extract_crystal_from_slot_payload(corrupted)
        )


class ExtractCrystalSucceededWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.ExtractCrystalSucceededFields(
            field1_u8=1, field2_u8=2, field3_u8=3, field4_u8=4, field5_u64=5,
        )
        payload = bc.encode_extract_crystal_succeeded_payload(fields)
        self.assertEqual(
            bc.decode_extract_crystal_succeeded_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_extract_crystal_succeeded_payload(
            bc.ExtractCrystalSucceededFields(1, 2, 3, 4, 5)
        )
        self.assertIsNone(
            bc.decode_extract_crystal_succeeded_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_extract_crystal_succeeded_payload(
            bc.ExtractCrystalSucceededFields(1, 2, 3, 4, 5)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_extract_crystal_succeeded_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_extract_crystal_succeeded_payload(
            bc.ExtractCrystalSucceededFields(1, 2, 3, 4, 5)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            bc.decode_extract_crystal_succeeded_payload(corrupted)
        )

    def test_distinct_type_from_extract_crystal_failed(self):
        # Different field-count/tag sequence than ExtractCrystalFailedFields
        # -- confirm the two dataclasses stay separate Python types even
        # though both live in this one module.
        self.assertIsNot(
            bc.ExtractCrystalSucceededFields, bc.ExtractCrystalFailedFields
        )


class AddNutrientToCrystalSlotWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.AddNutrientToCrystalSlotFields(
            field1_u64=9, field2_u8=1, field3_u8=2, field4_u8=3, field5_u8=4,
        )
        payload = bc.encode_add_nutrient_to_crystal_slot_payload(fields)
        self.assertEqual(
            bc.decode_add_nutrient_to_crystal_slot_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_add_nutrient_to_crystal_slot_payload(
            bc.AddNutrientToCrystalSlotFields(1, 2, 3, 4, 5)
        )
        self.assertIsNone(
            bc.decode_add_nutrient_to_crystal_slot_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_add_nutrient_to_crystal_slot_payload(
            bc.AddNutrientToCrystalSlotFields(1, 2, 3, 4, 5)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_add_nutrient_to_crystal_slot_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_add_nutrient_to_crystal_slot_payload(
            bc.AddNutrientToCrystalSlotFields(1, 2, 3, 4, 5)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            bc.decode_add_nutrient_to_crystal_slot_payload(corrupted)
        )

    def test_distinct_type_from_extract_crystal_from_slot(self):
        # Same field-count/tag sequence as ExtractCrystalFromSlotFields --
        # confirm the two dataclasses still stay separate Python types even
        # though both live in this one module and share a shape.
        self.assertIsNot(
            bc.AddNutrientToCrystalSlotFields, bc.ExtractCrystalFromSlotFields
        )


class DoAbsorbingWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = bc.DoAbsorbingFields(
            field1_u8=1, field2_u8=2, field3_u64=3, field4_u8=4,
        )
        payload = bc.encode_do_absorbing_payload(fields)
        self.assertEqual(bc.decode_do_absorbing_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = bc.encode_do_absorbing_payload(
            bc.DoAbsorbingFields(1, 2, 3, 4)
        )
        self.assertIsNone(bc.decode_do_absorbing_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = bc.encode_do_absorbing_payload(
            bc.DoAbsorbingFields(1, 2, 3, 4)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    bc.decode_do_absorbing_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = bc.encode_do_absorbing_payload(
            bc.DoAbsorbingFields(1, 2, 3, 4)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(bc.decode_do_absorbing_payload(corrupted))


if __name__ == "__main__":
    unittest.main()
