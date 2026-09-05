"""Pure unit tests for ``ui_gathering_wire.py`` -- ``Gathering_Start
GatheringVital`` (``0xAFF7``) / ``Gathering_GatheringResultVital``
(``0xBD8E``) encode/decode.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring.
``Gathering_UpdateSceneGatheringPointVital`` is out of scope (see
``ui_gathering_wire.py``'s module docstring) and has no module here.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_gathering_wire as gw  # noqa: E402


class StartGatheringWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = gw.StartGatheringFields(
            field1_u16=7, field2_u32=1234, field3_u8=1, field4_u8=2,
        )
        payload = gw.encode_start_gathering_payload(fields)
        decoded = gw.decode_start_gathering_payload(payload)
        self.assertEqual(decoded, fields)

    def test_truncated_payload_fails_closed(self):
        payload = gw.encode_start_gathering_payload(
            gw.StartGatheringFields(1, 2, 3, 4)
        )
        self.assertIsNone(gw.decode_start_gathering_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        # COO-DECISION 20260904_1745 item 2 -- see test_ui_party_wire.py's
        # equivalent test for the full rationale.
        clean = gw.encode_start_gathering_payload(
            gw.StartGatheringFields(1, 2, 3, 4)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    gw.decode_start_gathering_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = gw.encode_start_gathering_payload(
            gw.StartGatheringFields(1, 2, 3, 4)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(gw.decode_start_gathering_payload(corrupted))


class GatheringResultWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = gw.GatheringResultFields(
            field1_u8=1, field2_u16=2, field3_u32=3,
            field4_u8=4, field5_u8=5, field6_u32=6,
        )
        payload = gw.encode_gathering_result_payload(fields)
        decoded = gw.decode_gathering_result_payload(payload)
        self.assertEqual(decoded, fields)

    def test_truncated_payload_fails_closed(self):
        payload = gw.encode_gathering_result_payload(
            gw.GatheringResultFields(1, 2, 3, 4, 5, 6)
        )
        self.assertIsNone(gw.decode_gathering_result_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = gw.encode_gathering_result_payload(
            gw.GatheringResultFields(1, 2, 3, 4, 5, 6)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    gw.decode_gathering_result_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = gw.encode_gathering_result_payload(
            gw.GatheringResultFields(1, 2, 3, 4, 5, 6)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(gw.decode_gathering_result_payload(corrupted))

    def test_distinct_type_from_start_gathering(self):
        # Different field-count/tag sequence than StartGatheringFields --
        # confirm the two dataclasses stay separate Python types even
        # though both live in this one module.
        self.assertIsNot(
            gw.GatheringResultFields, gw.StartGatheringFields
        )


if __name__ == "__main__":
    unittest.main()
