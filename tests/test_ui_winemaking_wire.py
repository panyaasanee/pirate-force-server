"""Pure unit tests for ``ui_winemaking_wire.py`` -- ``Winemaking_
LearnFomulaVital`` (``0x972E``) / ``Winemaking_StartWinemakingVital``
(``0xC8EB``) / ``Winemaking_FinishWinemakingVital`` (``0xD4D1``)
encode/decode.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring.
``Winemaking_UpdateLearnedFormulaVital`` and
``Winemaking_UpdateWindPotSlotVital`` are out of scope (see
``ui_winemaking_wire.py``'s module docstring) and have no module here.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_winemaking_wire as wm  # noqa: E402


class LearnFomulaWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = wm.LearnFomulaFields(field1_u16=7, field2_u8=3)
        payload = wm.encode_learn_fomula_payload(fields)
        decoded = wm.decode_learn_fomula_payload(payload)
        self.assertEqual(decoded, fields)

    def test_truncated_payload_fails_closed(self):
        payload = wm.encode_learn_fomula_payload(
            wm.LearnFomulaFields(1, 2)
        )
        self.assertIsNone(wm.decode_learn_fomula_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        # COO-DECISION 20260904_1745 item 2 -- see test_ui_party_wire.py's
        # equivalent test for the full rationale.
        clean = wm.encode_learn_fomula_payload(wm.LearnFomulaFields(1, 2))
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    wm.decode_learn_fomula_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = wm.encode_learn_fomula_payload(
            wm.LearnFomulaFields(1, 2)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(wm.decode_learn_fomula_payload(corrupted))


class StartWinemakingWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = wm.StartWinemakingFields(
            field1_u32=1234, field2_u64=999999, field3_u8=1, field4_u8=2,
        )
        payload = wm.encode_start_winemaking_payload(fields)
        decoded = wm.decode_start_winemaking_payload(payload)
        self.assertEqual(decoded, fields)

    def test_truncated_payload_fails_closed(self):
        payload = wm.encode_start_winemaking_payload(
            wm.StartWinemakingFields(1, 2, 3, 4)
        )
        self.assertIsNone(wm.decode_start_winemaking_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = wm.encode_start_winemaking_payload(
            wm.StartWinemakingFields(1, 2, 3, 4)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    wm.decode_start_winemaking_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = wm.encode_start_winemaking_payload(
            wm.StartWinemakingFields(1, 2, 3, 4)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(wm.decode_start_winemaking_payload(corrupted))

    def test_distinct_type_from_learn_fomula(self):
        self.assertIsNot(
            wm.StartWinemakingFields, wm.LearnFomulaFields
        )


class FinishWinemakingWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = wm.FinishWinemakingFields(
            field1_u8=1, field2_u8=2, field3_u8=3, field4_u8=4,
            field5_u32=5,
        )
        payload = wm.encode_finish_winemaking_payload(fields)
        decoded = wm.decode_finish_winemaking_payload(payload)
        self.assertEqual(decoded, fields)

    def test_truncated_payload_fails_closed(self):
        payload = wm.encode_finish_winemaking_payload(
            wm.FinishWinemakingFields(1, 2, 3, 4, 5)
        )
        self.assertIsNone(wm.decode_finish_winemaking_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = wm.encode_finish_winemaking_payload(
            wm.FinishWinemakingFields(1, 2, 3, 4, 5)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    wm.decode_finish_winemaking_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = wm.encode_finish_winemaking_payload(
            wm.FinishWinemakingFields(1, 2, 3, 4, 5)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(wm.decode_finish_winemaking_payload(corrupted))

    def test_distinct_type_from_start_winemaking(self):
        self.assertIsNot(
            wm.FinishWinemakingFields, wm.StartWinemakingFields
        )


if __name__ == "__main__":
    unittest.main()
