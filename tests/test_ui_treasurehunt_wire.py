"""Pure unit tests for ``ui_treasurehunt_wire.py`` -- ``TreasureHunt_Start
ExcavatingVital`` (``0xE40B``) / ``TreasureHunt_ExcavatingResultVital``
(``0xF33F``) encode/decode.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring.
``TreasureHunt_UpdateSceneTreasurePointVital`` is out of scope (see
``ui_treasurehunt_wire.py``'s module docstring) and has no module here.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_treasurehunt_wire as th  # noqa: E402


class StartExcavatingWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = th.StartExcavatingFields(
            field1_u16=7, field2_u32=1234, field3_u8=1,
            field4_u64=99, field5_u64=100,
        )
        payload = th.encode_start_excavating_payload(fields)
        decoded = th.decode_start_excavating_payload(payload)
        self.assertEqual(decoded, fields)

    def test_truncated_payload_fails_closed(self):
        payload = th.encode_start_excavating_payload(
            th.StartExcavatingFields(1, 2, 3, 4, 5)
        )
        self.assertIsNone(th.decode_start_excavating_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        # COO-DECISION 20260904_1745 item 2 -- see test_ui_party_wire.py's
        # equivalent test for the full rationale.
        clean = th.encode_start_excavating_payload(
            th.StartExcavatingFields(1, 2, 3, 4, 5)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    th.decode_start_excavating_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = th.encode_start_excavating_payload(
            th.StartExcavatingFields(1, 2, 3, 4, 5)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(th.decode_start_excavating_payload(corrupted))


class ExcavatingResultWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = th.ExcavatingResultFields(
            field1_u8=1, field2_u16=2, field3_u32=3,
            field4_u16=4, field5_u32=5,
        )
        payload = th.encode_excavating_result_payload(fields)
        decoded = th.decode_excavating_result_payload(payload)
        self.assertEqual(decoded, fields)

    def test_truncated_payload_fails_closed(self):
        payload = th.encode_excavating_result_payload(
            th.ExcavatingResultFields(1, 2, 3, 4, 5)
        )
        self.assertIsNone(th.decode_excavating_result_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = th.encode_excavating_result_payload(
            th.ExcavatingResultFields(1, 2, 3, 4, 5)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    th.decode_excavating_result_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = th.encode_excavating_result_payload(
            th.ExcavatingResultFields(1, 2, 3, 4, 5)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(th.decode_excavating_result_payload(corrupted))

    def test_distinct_type_from_start_excavating(self):
        # Different field-count/tag sequence than StartExcavatingFields --
        # confirm the two dataclasses stay separate Python types even
        # though both live in this one module.
        self.assertIsNot(
            th.ExcavatingResultFields, th.StartExcavatingFields
        )


if __name__ == "__main__":
    unittest.main()
