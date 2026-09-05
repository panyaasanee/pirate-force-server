"""Pure unit tests for ``ui_activity_wire.py`` -- the seven fully-tagged
``Activity_*``/``ActorActivity_*`` classes.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring.
``Activity_CheatCodeVital`` (LANE-GM), ``Activity_BasicVital``,
``Activity_ActorCommandVital``, ``Activity_SendRankingVital``, and
``ActorActivity_UpdateDailyActivityStateVital`` are out of scope (see
``ui_activity_wire.py``'s module docstring) and have no module here.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_activity_wire as act  # noqa: E402


class NewActivityWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = act.NewActivityFields(field1_u32=1, field2_u32=2, field3_u8=3)
        payload = act.encode_new_activity_payload(fields)
        self.assertEqual(act.decode_new_activity_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = act.encode_new_activity_payload(
            act.NewActivityFields(1, 2, 3)
        )
        self.assertIsNone(act.decode_new_activity_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = act.encode_new_activity_payload(
            act.NewActivityFields(1, 2, 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(act.decode_new_activity_payload(clean + extra))

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = act.encode_new_activity_payload(
            act.NewActivityFields(1, 2, 3)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(act.decode_new_activity_payload(corrupted))


class ActivityStateChangedWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = act.ActivityStateChangedFields(field1_u32=10, field2_u8=1)
        payload = act.encode_activity_state_changed_payload(fields)
        self.assertEqual(
            act.decode_activity_state_changed_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = act.encode_activity_state_changed_payload(
            act.ActivityStateChangedFields(10, 1)
        )
        self.assertIsNone(
            act.decode_activity_state_changed_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = act.encode_activity_state_changed_payload(
            act.ActivityStateChangedFields(10, 1)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    act.decode_activity_state_changed_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = act.encode_activity_state_changed_payload(
            act.ActivityStateChangedFields(10, 1)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            act.decode_activity_state_changed_payload(corrupted)
        )


class ActorJoinActivityWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = act.ActorJoinActivityFields(
            field1_u32=1, field2_u8=2, field3_u8=3,
            field4_u32=4, field5_u32=5, field6_u32=6,
        )
        payload = act.encode_actor_join_activity_payload(fields)
        self.assertEqual(
            act.decode_actor_join_activity_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = act.encode_actor_join_activity_payload(
            act.ActorJoinActivityFields(1, 2, 3, 4, 5, 6)
        )
        self.assertIsNone(
            act.decode_actor_join_activity_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = act.encode_actor_join_activity_payload(
            act.ActorJoinActivityFields(1, 2, 3, 4, 5, 6)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    act.decode_actor_join_activity_payload(clean + extra)
                )

    def test_wrong_tag_at_field4_fails_closed(self):
        # field4 is the first of the three tag-0x26 fields -- confirm the
        # decoder actually checks that tag byte, not just field-count.
        payload = act.encode_actor_join_activity_payload(
            act.ActorJoinActivityFields(1, 2, 3, 4, 5, 6)
        )
        field4_tag_index = 5 + 2 + 2  # u32tag(1+4) + u8(1+1) + u8(1+1)
        corrupted = (
            payload[:field4_tag_index]
            + bytes([0x00])
            + payload[field4_tag_index + 1:]
        )
        self.assertIsNone(act.decode_actor_join_activity_payload(corrupted))


class ActorLeaveActivityWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = act.ActorLeaveActivityFields(
            field1_u32=1, field2_u8=2, field3_u8=3
        )
        payload = act.encode_actor_leave_activity_payload(fields)
        self.assertEqual(
            act.decode_actor_leave_activity_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = act.encode_actor_leave_activity_payload(
            act.ActorLeaveActivityFields(1, 2, 3)
        )
        self.assertIsNone(
            act.decode_actor_leave_activity_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = act.encode_actor_leave_activity_payload(
            act.ActorLeaveActivityFields(1, 2, 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    act.decode_actor_leave_activity_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = act.encode_actor_leave_activity_payload(
            act.ActorLeaveActivityFields(1, 2, 3)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(act.decode_actor_leave_activity_payload(corrupted))


class UpdateActivityPointWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = act.UpdateActivityPointFields(field1_u32=1, field2_u16=2)
        payload = act.encode_update_activity_point_payload(fields)
        self.assertEqual(
            act.decode_update_activity_point_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = act.encode_update_activity_point_payload(
            act.UpdateActivityPointFields(1, 2)
        )
        self.assertIsNone(
            act.decode_update_activity_point_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = act.encode_update_activity_point_payload(
            act.UpdateActivityPointFields(1, 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    act.decode_update_activity_point_payload(clean + extra)
                )

    def test_wrong_tag_at_field2_fails_closed(self):
        payload = act.encode_update_activity_point_payload(
            act.UpdateActivityPointFields(1, 2)
        )
        corrupted = payload[:5] + bytes([0x00]) + payload[6:]
        self.assertIsNone(
            act.decode_update_activity_point_payload(corrupted)
        )


class ClientReportActivityResultWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = act.ClientReportActivityResultFields(
            field1_u32=1, field2_u16=2, field3_u8=3
        )
        payload = act.encode_client_report_activity_result_payload(fields)
        self.assertEqual(
            act.decode_client_report_activity_result_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = act.encode_client_report_activity_result_payload(
            act.ClientReportActivityResultFields(1, 2, 3)
        )
        self.assertIsNone(
            act.decode_client_report_activity_result_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = act.encode_client_report_activity_result_payload(
            act.ClientReportActivityResultFields(1, 2, 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    act.decode_client_report_activity_result_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = act.encode_client_report_activity_result_payload(
            act.ClientReportActivityResultFields(1, 2, 3)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            act.decode_client_report_activity_result_payload(corrupted)
        )


class ResetDailyActivityResultWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = act.ResetDailyActivityResultFields(field1_u8=1, field2_u32=2)
        payload = act.encode_reset_daily_activity_result_payload(fields)
        self.assertEqual(
            act.decode_reset_daily_activity_result_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = act.encode_reset_daily_activity_result_payload(
            act.ResetDailyActivityResultFields(1, 2)
        )
        self.assertIsNone(
            act.decode_reset_daily_activity_result_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = act.encode_reset_daily_activity_result_payload(
            act.ResetDailyActivityResultFields(1, 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    act.decode_reset_daily_activity_result_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = act.encode_reset_daily_activity_result_payload(
            act.ResetDailyActivityResultFields(1, 2)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            act.decode_reset_daily_activity_result_payload(corrupted)
        )

    def test_distinct_type_from_new_activity(self):
        self.assertIsNot(
            act.ResetDailyActivityResultFields, act.NewActivityFields
        )


if __name__ == "__main__":
    unittest.main()
