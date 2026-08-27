"""GM-001: GM_UpdateGMStateVital payload matches the proven tag/offset layout."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm.state_wire import (
    GM_UPDATE_GM_STATE_VITAL_ID,
    make_gm_update_state_frame,
    make_gm_update_state_payload,
)


class GmStateWirePayloadTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_payload_matches_proven_tag_order(self):
        payload = make_gm_update_state_payload(self.legacy, 1, 0, 7)
        expected = (
            self.legacy.u8tag(0x0B, 1)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.u32tag(0x14, 7)
        )
        self.assertEqual(payload, expected)

    def test_payload_is_exactly_nine_bytes(self):
        # u8tag = tag(1) + value(1) = 2 bytes; u32tag = tag(1) + value(4) = 5 bytes
        # 2 + 2 + 5 = 9
        payload = make_gm_update_state_payload(self.legacy, 0, 0, 0)
        self.assertEqual(len(payload), 9)

    def test_first_two_fields_carry_tag_0x0b(self):
        payload = make_gm_update_state_payload(self.legacy, 1, 1, 0)
        self.assertEqual(payload[0], 0x0B)
        self.assertEqual(payload[2], 0x0B)

    def test_third_field_carries_tag_0x14(self):
        payload = make_gm_update_state_payload(self.legacy, 0, 0, 0)
        self.assertEqual(payload[4], 0x14)

    def test_rejects_out_of_range_u8_field(self):
        with self.assertRaises(ValueError):
            make_gm_update_state_payload(self.legacy, 256, 0, 0)
        with self.assertRaises(ValueError):
            make_gm_update_state_payload(self.legacy, 0, -1, 0)

    def test_rejects_out_of_range_u32_field(self):
        with self.assertRaises(ValueError):
            make_gm_update_state_payload(self.legacy, 0, 0, 1 << 32)


class GmStateWireFrameTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_frame_carries_the_gm_update_state_vital_id(self):
        pc, frame = make_gm_update_state_frame(self.legacy, 4, 1, 0, 0)
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [(GM_UPDATE_GM_STATE_VITAL_ID, 4, make_gm_update_state_payload(self.legacy, 1, 0, 0))]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_frame_carries_the_re113_trailing_change_mask_byte(self):
        # RE-113 (LANE-GM round fmgvbx): GSCN_RunTimeProtocolRes v4 requires a
        # trailing derived-class change-mask byte (u8tag 0x0B, value 0) after
        # its VitalData collection -- omitting it produced ErrorData=28317 on
        # a real client (GT-107). Regression guard: the built PC must end on
        # that exact trailing tag, not on the vital's own last field.
        pc, _frame = make_gm_update_state_frame(self.legacy, 4, 1, 0, 0)
        self.assertEqual(pc[-2:], self.legacy.u8tag(0x0B, 0))

    def test_vital_id_constant_matches_bridge_registry(self):
        # pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv: 0x5A19 GM_UpdateGMStateVital
        self.assertEqual(GM_UPDATE_GM_STATE_VITAL_ID, 0x5A19)


if __name__ == "__main__":
    unittest.main()
