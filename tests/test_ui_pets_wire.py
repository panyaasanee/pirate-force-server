"""Pure unit tests for ``ui_pets_wire.py`` -- round-trip + fail-closed
(truncated / wrong-tag / trailing-bytes) coverage for the ten fully-tagged
``Pets_*`` classes. Not wiring tests -- see ``ui_social_wire.py``'s module
docstring. The six excluded classes (``ChangePetEquipment``/``SetPetAI``/
``SetPetSkill``/``UpdateLearnedPetSkill``/``UpdatePetsData``/
``UpdatePetsMegringData``) have no module and no tests here -- see
``ui_pets_wire.py``'s module docstring for why.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_pets_wire as pets  # noqa: E402


class VitalIdTests(unittest.TestCase):
    # pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv (grep
    # `^0x....\tPets_`) -- pins every constant this module hardcodes so a
    # future transposition/typo (e.g. copy-paste from the wrong TSV row)
    # fails the suite instead of shipping silently (pf-adversary, round
    # `avt7pt`: mutating one of these ten IDs left all other tests green).

    def test_summon_pet_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_SUMMON_PET_VITAL_ID, 0x4CEC)

    def test_unsummon_pet_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_UNSUMMON_PET_VITAL_ID, 0x5E3C)

    def test_update_pet_property_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_UPDATE_PET_PROPERTY_VITAL_ID, 0x9B50)

    def test_restore_pet_amity_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_RESTORE_PET_AMITY_VITAL_ID, 0x83B5)

    def test_notify_sailor_dead_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_NOTIFY_SAILOR_DEAD_VITAL_ID, 0x8B12)

    def test_merge_pets_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_MERGE_PETS_VITAL_ID, 0x4C4D)

    def test_merge_pets_result_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_MERGE_PETS_RESULT_VITAL_ID, 0x845C)

    def test_claim_pets_megring_item_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_CLAIM_PETS_MEGRING_ITEM_VITAL_ID, 0xB96F)

    def test_learn_pet_skill_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_LEARN_PET_SKILL_VITAL_ID, 0x6E55)

    def test_update_summon_pets_time_out_vital_id_matches_the_registry(self):
        self.assertEqual(pets.PETS_UPDATE_SUMMON_PETS_TIME_OUT_VITAL_ID, 0xE28A)


class SummonPetWireTests(unittest.TestCase):
    def _fields(self):
        return pets.SummonPetFields(
            field1_u64=1, field2_u64=2, field3_u32=3, field4_u8=4, field5_u8=5
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_summon_pet_payload(fields)
        self.assertEqual(pets.decode_summon_pet_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_summon_pet_payload(self._fields())
        self.assertIsNone(pets.decode_summon_pet_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_summon_pet_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(pets.decode_summon_pet_payload(clean + extra))

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_summon_pet_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(pets.decode_summon_pet_payload(corrupted))


class UnsummonPetWireTests(unittest.TestCase):
    def _fields(self):
        return pets.UnsummonPetFields(field1_u64=1, field2_u8=2, field3_u8=3)

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_unsummon_pet_payload(fields)
        self.assertEqual(pets.decode_unsummon_pet_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_unsummon_pet_payload(self._fields())
        self.assertIsNone(pets.decode_unsummon_pet_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_unsummon_pet_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(pets.decode_unsummon_pet_payload(clean + extra))

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_unsummon_pet_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(pets.decode_unsummon_pet_payload(corrupted))


class UpdatePetPropertyWireTests(unittest.TestCase):
    def _fields(self):
        return pets.UpdatePetPropertyFields(field1_u64=1, field2_u32=2, field3_u8=3)

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_update_pet_property_payload(fields)
        self.assertEqual(pets.decode_update_pet_property_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_update_pet_property_payload(self._fields())
        self.assertIsNone(pets.decode_update_pet_property_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_update_pet_property_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    pets.decode_update_pet_property_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_update_pet_property_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(pets.decode_update_pet_property_payload(corrupted))


class RestorePetAmityWireTests(unittest.TestCase):
    def _fields(self):
        return pets.RestorePetAmityFields(field1_u64=1, field2_u64=2, field3_u8=3)

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_restore_pet_amity_payload(fields)
        self.assertEqual(pets.decode_restore_pet_amity_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_restore_pet_amity_payload(self._fields())
        self.assertIsNone(pets.decode_restore_pet_amity_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_restore_pet_amity_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    pets.decode_restore_pet_amity_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_restore_pet_amity_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(pets.decode_restore_pet_amity_payload(corrupted))


class NotifySailorDeadWireTests(unittest.TestCase):
    def _fields(self):
        return pets.NotifySailorDeadFields(field1_u64=1)

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_notify_sailor_dead_payload(fields)
        self.assertEqual(pets.decode_notify_sailor_dead_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_notify_sailor_dead_payload(self._fields())
        self.assertIsNone(pets.decode_notify_sailor_dead_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_notify_sailor_dead_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    pets.decode_notify_sailor_dead_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_notify_sailor_dead_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(pets.decode_notify_sailor_dead_payload(corrupted))


class MergePetsWireTests(unittest.TestCase):
    def _fields(self):
        return pets.MergePetsFields(
            field1_u8=1, field2_u8=2, field3_u64=3, field4_u64=4
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_merge_pets_payload(fields)
        self.assertEqual(pets.decode_merge_pets_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_merge_pets_payload(self._fields())
        self.assertIsNone(pets.decode_merge_pets_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_merge_pets_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(pets.decode_merge_pets_payload(clean + extra))

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_merge_pets_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(pets.decode_merge_pets_payload(corrupted))


class MergePetsResultWireTests(unittest.TestCase):
    def _fields(self):
        return pets.MergePetsResultFields(field1_u8=1, field2_u8=2)

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_merge_pets_result_payload(fields)
        self.assertEqual(pets.decode_merge_pets_result_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_merge_pets_result_payload(self._fields())
        self.assertIsNone(pets.decode_merge_pets_result_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_merge_pets_result_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    pets.decode_merge_pets_result_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_merge_pets_result_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(pets.decode_merge_pets_result_payload(corrupted))

    def test_distinct_type_from_merge_pets(self):
        # Same tag/length shape as MergePetsFields' first two fields but a
        # different class -- a decoder for one must not silently accept the
        # other's payload just because the leading bytes happen to match.
        merge_payload = pets.encode_merge_pets_payload(
            pets.MergePetsFields(1, 2, 3, 4)
        )
        self.assertIsNone(pets.decode_merge_pets_result_payload(merge_payload))


class ClaimPetsMegringItemWireTests(unittest.TestCase):
    def _fields(self):
        return pets.ClaimPetsMegringItemFields(field1_u8=1, field2_u8=2, field3_u64=3)

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_claim_pets_megring_item_payload(fields)
        self.assertEqual(
            pets.decode_claim_pets_megring_item_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_claim_pets_megring_item_payload(self._fields())
        self.assertIsNone(pets.decode_claim_pets_megring_item_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_claim_pets_megring_item_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    pets.decode_claim_pets_megring_item_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_claim_pets_megring_item_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(pets.decode_claim_pets_megring_item_payload(corrupted))


class LearnPetSkillWireTests(unittest.TestCase):
    def _fields(self):
        return pets.LearnPetSkillFields(field1_u16=1, field2_u8=2)

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_learn_pet_skill_payload(fields)
        self.assertEqual(pets.decode_learn_pet_skill_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_learn_pet_skill_payload(self._fields())
        self.assertIsNone(pets.decode_learn_pet_skill_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_learn_pet_skill_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    pets.decode_learn_pet_skill_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_learn_pet_skill_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(pets.decode_learn_pet_skill_payload(corrupted))


class UpdateSummonPetsTimeOutWireTests(unittest.TestCase):
    def _fields(self):
        return pets.UpdateSummonPetsTimeOutFields(field1_u32=1)

    def test_round_trip(self):
        fields = self._fields()
        payload = pets.encode_update_summon_pets_time_out_payload(fields)
        self.assertEqual(
            pets.decode_update_summon_pets_time_out_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = pets.encode_update_summon_pets_time_out_payload(self._fields())
        self.assertIsNone(
            pets.decode_update_summon_pets_time_out_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = pets.encode_update_summon_pets_time_out_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    pets.decode_update_summon_pets_time_out_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = pets.encode_update_summon_pets_time_out_payload(self._fields())
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            pets.decode_update_summon_pets_time_out_payload(corrupted)
        )


if __name__ == "__main__":
    unittest.main()
