"""Pure unit tests for ``ui_community_social_wire.py`` -- the sixteen
fully-tagged ``Community_*`` classes not already covered by
``ui_friend_wire.py``/``ui_mail_wire.py``.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring. The eight
excluded classes (``AddBlackListVital``/``AddFriendVital``/
``GetActorVowLockListVital``/``InitalizeActorCommunityVital``/
``ReceiveNewMailVital``/``ReplyPenpalLetterVital``/
``RequestSoulMateMatchVital``/``UpdateActorVowLockVital``) and the nine
TSV-absent classes are out of scope (see
``ui_community_social_wire.py``'s module docstring) and have no module
here.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_community_social_wire as comm  # noqa: E402


class ChangeActorCommentWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.ChangeActorCommentFields(
            field1_u64=1, field2_wstring="hi", field3_u8=2
        )
        payload = comm.encode_change_actor_comment_payload(fields)
        self.assertEqual(
            comm.decode_change_actor_comment_payload(payload), fields
        )

    def test_empty_wstring_round_trips(self):
        fields = comm.ChangeActorCommentFields(
            field1_u64=1, field2_wstring="", field3_u8=2
        )
        payload = comm.encode_change_actor_comment_payload(fields)
        self.assertEqual(
            comm.decode_change_actor_comment_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_change_actor_comment_payload(
            comm.ChangeActorCommentFields(1, "hi", 2)
        )
        self.assertIsNone(
            comm.decode_change_actor_comment_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_change_actor_comment_payload(
            comm.ChangeActorCommentFields(1, "hi", 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_change_actor_comment_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_change_actor_comment_payload(
            comm.ChangeActorCommentFields(1, "hi", 2)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(comm.decode_change_actor_comment_payload(corrupted))

    def test_wstring_field_uses_tag_0x48(self):
        # Pins the actual bug this class was migrated to fix (round
        # `on8hbb`): field2's wstring must carry tag byte 0x48 right
        # after the 9-byte u64tag(field1). A round-trip test alone
        # would not catch a silent revert to encode_untagged_wstring
        # (that pair simply omits this byte and everything downstream
        # still round-trips against itself) -- see pf-adversary's
        # finding on this round.
        payload = comm.encode_change_actor_comment_payload(
            comm.ChangeActorCommentFields(1, "hi", 2)
        )
        self.assertEqual(payload[9], 0x48)
        corrupted = payload[:9] + bytes([0x00]) + payload[10:]
        self.assertIsNone(comm.decode_change_actor_comment_payload(corrupted))


class ChangeActorPenNameWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.ChangeActorPenNameFields(
            field1_u64=1, field2_wstring="pen", field3_u8=2
        )
        payload = comm.encode_change_actor_pen_name_payload(fields)
        self.assertEqual(
            comm.decode_change_actor_pen_name_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_change_actor_pen_name_payload(
            comm.ChangeActorPenNameFields(1, "pen", 2)
        )
        self.assertIsNone(
            comm.decode_change_actor_pen_name_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_change_actor_pen_name_payload(
            comm.ChangeActorPenNameFields(1, "pen", 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_change_actor_pen_name_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_change_actor_pen_name_payload(
            comm.ChangeActorPenNameFields(1, "pen", 2)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_change_actor_pen_name_payload(corrupted)
        )

    def test_distinct_type_from_change_actor_comment(self):
        self.assertIsNot(
            comm.ChangeActorPenNameFields, comm.ChangeActorCommentFields
        )

    def test_wstring_field_uses_tag_0x48(self):
        # See ChangeActorCommentWireTests.test_wstring_field_uses_tag_0x48
        # for why a round-trip test alone cannot catch this class's bug.
        payload = comm.encode_change_actor_pen_name_payload(
            comm.ChangeActorPenNameFields(1, "pen", 2)
        )
        self.assertEqual(payload[9], 0x48)
        corrupted = payload[:9] + bytes([0x00]) + payload[10:]
        self.assertIsNone(
            comm.decode_change_actor_pen_name_payload(corrupted)
        )


class ChangeActorPersonalDataWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.ChangeActorPersonalDataFields(
            field1_u64=1,
            field2_wstring="a",
            field3_wstring="b",
            field4_wstring="c",
            field5_u8=2,
        )
        payload = comm.encode_change_actor_personal_data_payload(fields)
        self.assertEqual(
            comm.decode_change_actor_personal_data_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_change_actor_personal_data_payload(
            comm.ChangeActorPersonalDataFields(1, "a", "b", "c", 2)
        )
        self.assertIsNone(
            comm.decode_change_actor_personal_data_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_change_actor_personal_data_payload(
            comm.ChangeActorPersonalDataFields(1, "a", "b", "c", 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_change_actor_personal_data_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field5_uses_the_alternate_u8_tag(self):
        # field5 uses tag 0x08, not the 0x0B every other field in this
        # module uses -- confirm the decoder checks that specific byte.
        payload = comm.encode_change_actor_personal_data_payload(
            comm.ChangeActorPersonalDataFields(1, "a", "b", "c", 2)
        )
        field5_tag_index = len(payload) - 2
        self.assertEqual(payload[field5_tag_index], 0x08)
        corrupted = (
            payload[:field5_tag_index]
            + bytes([0x0B])
            + payload[field5_tag_index + 1:]
        )
        self.assertIsNone(
            comm.decode_change_actor_personal_data_payload(corrupted)
        )


class CommunityCommandNotAllowWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.CommunityCommandNotAllowFields(field1_u64=42)
        payload = comm.encode_community_command_not_allow_payload(fields)
        self.assertEqual(
            comm.decode_community_command_not_allow_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_community_command_not_allow_payload(
            comm.CommunityCommandNotAllowFields(42)
        )
        self.assertIsNone(
            comm.decode_community_command_not_allow_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_community_command_not_allow_payload(
            comm.CommunityCommandNotAllowFields(42)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_community_command_not_allow_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_fails_closed(self):
        payload = comm.encode_community_command_not_allow_payload(
            comm.CommunityCommandNotAllowFields(42)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_community_command_not_allow_payload(corrupted)
        )


class CommunityPropertyChangedWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.CommunityPropertyChangedFields(
            field1_u64=1, field2_u64=2, field3_u8=3, field4_u32=4,
            field5_wstring="x",
        )
        payload = comm.encode_community_property_changed_payload(fields)
        self.assertEqual(
            comm.decode_community_property_changed_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_community_property_changed_payload(
            comm.CommunityPropertyChangedFields(1, 2, 3, 4, "x")
        )
        self.assertIsNone(
            comm.decode_community_property_changed_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_community_property_changed_payload(
            comm.CommunityPropertyChangedFields(1, 2, 3, 4, "x")
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_community_property_changed_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field4_fails_closed(self):
        payload = comm.encode_community_property_changed_payload(
            comm.CommunityPropertyChangedFields(1, 2, 3, 4, "x")
        )
        field4_tag_index = 9 + 9 + 2  # u64tag + u64tag + u8
        corrupted = (
            payload[:field4_tag_index]
            + bytes([0x00])
            + payload[field4_tag_index + 1:]
        )
        self.assertIsNone(
            comm.decode_community_property_changed_payload(corrupted)
        )


class OpenLetterInABottleWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.OpenLetterInABottleFields(
            field1_u64=1, field2_u64=2, field3_u8=3, field4_wstring="a",
            field5_wstring="b", field6_u8=4, field7_u32=5,
        )
        payload = comm.encode_open_letter_in_a_bottle_payload(fields)
        self.assertEqual(
            comm.decode_open_letter_in_a_bottle_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_open_letter_in_a_bottle_payload(
            comm.OpenLetterInABottleFields(1, 2, 3, "a", "b", 4, 5)
        )
        self.assertIsNone(
            comm.decode_open_letter_in_a_bottle_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_open_letter_in_a_bottle_payload(
            comm.OpenLetterInABottleFields(1, 2, 3, "a", "b", 4, 5)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_open_letter_in_a_bottle_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_open_letter_in_a_bottle_payload(
            comm.OpenLetterInABottleFields(1, 2, 3, "a", "b", 4, 5)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_open_letter_in_a_bottle_payload(corrupted)
        )


class OpenPenpalLetterWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.OpenPenpalLetterFields(
            field1_u64=1, field2_u64=2, field3_u8=3, field4_wstring="a",
            field5_wstring="b", field6_u32=4,
        )
        payload = comm.encode_open_penpal_letter_payload(fields)
        self.assertEqual(
            comm.decode_open_penpal_letter_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_open_penpal_letter_payload(
            comm.OpenPenpalLetterFields(1, 2, 3, "a", "b", 4)
        )
        self.assertIsNone(
            comm.decode_open_penpal_letter_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_open_penpal_letter_payload(
            comm.OpenPenpalLetterFields(1, 2, 3, "a", "b", 4)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_open_penpal_letter_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_open_penpal_letter_payload(
            comm.OpenPenpalLetterFields(1, 2, 3, "a", "b", 4)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_open_penpal_letter_payload(corrupted)
        )


class RemoveBlackListWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.RemoveBlackListFields(
            field1_u64=1, field2_wstring="name", field3_u8=2
        )
        payload = comm.encode_remove_black_list_payload(fields)
        self.assertEqual(
            comm.decode_remove_black_list_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_remove_black_list_payload(
            comm.RemoveBlackListFields(1, "name", 2)
        )
        self.assertIsNone(
            comm.decode_remove_black_list_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_remove_black_list_payload(
            comm.RemoveBlackListFields(1, "name", 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_remove_black_list_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_remove_black_list_payload(
            comm.RemoveBlackListFields(1, "name", 2)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(comm.decode_remove_black_list_payload(corrupted))

    def test_distinct_type_from_change_actor_comment(self):
        self.assertIsNot(
            comm.RemoveBlackListFields, comm.ChangeActorCommentFields
        )

    def test_wstring_field_uses_tag_0x48(self):
        # See ChangeActorCommentWireTests.test_wstring_field_uses_tag_0x48
        # for why a round-trip test alone cannot catch this class's bug.
        payload = comm.encode_remove_black_list_payload(
            comm.RemoveBlackListFields(1, "name", 2)
        )
        self.assertEqual(payload[9], 0x48)
        corrupted = payload[:9] + bytes([0x00]) + payload[10:]
        self.assertIsNone(comm.decode_remove_black_list_payload(corrupted))


class ReplyLetterInABottleWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.ReplyLetterInABottleFields(
            field1_u64=1, field2_u64=2, field3_u8=3
        )
        payload = comm.encode_reply_letter_in_a_bottle_payload(fields)
        self.assertEqual(
            comm.decode_reply_letter_in_a_bottle_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_reply_letter_in_a_bottle_payload(
            comm.ReplyLetterInABottleFields(1, 2, 3)
        )
        self.assertIsNone(
            comm.decode_reply_letter_in_a_bottle_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_reply_letter_in_a_bottle_payload(
            comm.ReplyLetterInABottleFields(1, 2, 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_reply_letter_in_a_bottle_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_reply_letter_in_a_bottle_payload(
            comm.ReplyLetterInABottleFields(1, 2, 3)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_reply_letter_in_a_bottle_payload(corrupted)
        )


class RequestorConfirmSoulMateMatchWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.RequestorConfirmSoulMateMatchFields(
            field1_u64=1, field2_wstring="soulmate", field3_u8=2, field4_u8=3
        )
        payload = comm.encode_requestor_confirm_soul_mate_match_payload(
            fields
        )
        self.assertEqual(
            comm.decode_requestor_confirm_soul_mate_match_payload(payload),
            fields,
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_requestor_confirm_soul_mate_match_payload(
            comm.RequestorConfirmSoulMateMatchFields(1, "soulmate", 2, 3)
        )
        self.assertIsNone(
            comm.decode_requestor_confirm_soul_mate_match_payload(
                payload[:-1]
            )
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_requestor_confirm_soul_mate_match_payload(
            comm.RequestorConfirmSoulMateMatchFields(1, "soulmate", 2, 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_requestor_confirm_soul_mate_match_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field4_fails_closed(self):
        payload = comm.encode_requestor_confirm_soul_mate_match_payload(
            comm.RequestorConfirmSoulMateMatchFields(1, "soulmate", 2, 3)
        )
        corrupted = payload[:-2] + bytes([0x00]) + payload[-1:]
        self.assertIsNone(
            comm.decode_requestor_confirm_soul_mate_match_payload(corrupted)
        )


class SetReceiveActiveChangeWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.SetReceiveActiveChangeFields(
            field1_u64=1, field2_wstring="s", field3_u8=2, field4_u8=3
        )
        payload = comm.encode_set_receive_active_change_payload(fields)
        self.assertEqual(
            comm.decode_set_receive_active_change_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_set_receive_active_change_payload(
            comm.SetReceiveActiveChangeFields(1, "s", 2, 3)
        )
        self.assertIsNone(
            comm.decode_set_receive_active_change_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_set_receive_active_change_payload(
            comm.SetReceiveActiveChangeFields(1, "s", 2, 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_set_receive_active_change_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_set_receive_active_change_payload(
            comm.SetReceiveActiveChangeFields(1, "s", 2, 3)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_set_receive_active_change_payload(corrupted)
        )

    def test_distinct_type_from_requestor_confirm(self):
        self.assertIsNot(
            comm.SetReceiveActiveChangeFields,
            comm.RequestorConfirmSoulMateMatchFields,
        )


class TargetConfirmSoulMateMatchWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.TargetConfirmSoulMateMatchFields(
            field1_u64=1, field2_wstring="t", field3_u8=2
        )
        payload = comm.encode_target_confirm_soul_mate_match_payload(fields)
        self.assertEqual(
            comm.decode_target_confirm_soul_mate_match_payload(payload),
            fields,
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_target_confirm_soul_mate_match_payload(
            comm.TargetConfirmSoulMateMatchFields(1, "t", 2)
        )
        self.assertIsNone(
            comm.decode_target_confirm_soul_mate_match_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_target_confirm_soul_mate_match_payload(
            comm.TargetConfirmSoulMateMatchFields(1, "t", 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_target_confirm_soul_mate_match_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_target_confirm_soul_mate_match_payload(
            comm.TargetConfirmSoulMateMatchFields(1, "t", 2)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_target_confirm_soul_mate_match_payload(corrupted)
        )


class ThrowLetterInABottleWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.ThrowLetterInABottleFields(
            field1_u64=1, field2_wstring="msg", field3_u8=2
        )
        payload = comm.encode_throw_letter_in_a_bottle_payload(fields)
        self.assertEqual(
            comm.decode_throw_letter_in_a_bottle_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_throw_letter_in_a_bottle_payload(
            comm.ThrowLetterInABottleFields(1, "msg", 2)
        )
        self.assertIsNone(
            comm.decode_throw_letter_in_a_bottle_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_throw_letter_in_a_bottle_payload(
            comm.ThrowLetterInABottleFields(1, "msg", 2)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_throw_letter_in_a_bottle_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_throw_letter_in_a_bottle_payload(
            comm.ThrowLetterInABottleFields(1, "msg", 2)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_throw_letter_in_a_bottle_payload(corrupted)
        )


class ThrowPenpalLetterWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.ThrowPenpalLetterFields(
            field1_u64=1, field2_u64=2, field3_wstring="a",
            field4_wstring="b", field5_u8=3,
        )
        payload = comm.encode_throw_penpal_letter_payload(fields)
        self.assertEqual(
            comm.decode_throw_penpal_letter_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_throw_penpal_letter_payload(
            comm.ThrowPenpalLetterFields(1, 2, "a", "b", 3)
        )
        self.assertIsNone(
            comm.decode_throw_penpal_letter_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_throw_penpal_letter_payload(
            comm.ThrowPenpalLetterFields(1, 2, "a", "b", 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_throw_penpal_letter_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_throw_penpal_letter_payload(
            comm.ThrowPenpalLetterFields(1, 2, "a", "b", 3)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_throw_penpal_letter_payload(corrupted)
        )


class UseBlankPenpalLetterWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.UseBlankPenpalLetterFields(
            field1_u64=1, field2_u64=2, field3_u8=3
        )
        payload = comm.encode_use_blank_penpal_letter_payload(fields)
        self.assertEqual(
            comm.decode_use_blank_penpal_letter_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_use_blank_penpal_letter_payload(
            comm.UseBlankPenpalLetterFields(1, 2, 3)
        )
        self.assertIsNone(
            comm.decode_use_blank_penpal_letter_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_use_blank_penpal_letter_payload(
            comm.UseBlankPenpalLetterFields(1, 2, 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_use_blank_penpal_letter_payload(clean + extra)
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_use_blank_penpal_letter_payload(
            comm.UseBlankPenpalLetterFields(1, 2, 3)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_use_blank_penpal_letter_payload(corrupted)
        )

    def test_distinct_type_from_reply_letter_in_a_bottle(self):
        self.assertIsNot(
            comm.UseBlankPenpalLetterFields, comm.ReplyLetterInABottleFields
        )


class WriteBlankPenpalLetterWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = comm.WriteBlankPenpalLetterFields(
            field1_u64=1, field2_u64=2, field3_wstring="draft", field4_u8=3
        )
        payload = comm.encode_write_blank_penpal_letter_payload(fields)
        self.assertEqual(
            comm.decode_write_blank_penpal_letter_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = comm.encode_write_blank_penpal_letter_payload(
            comm.WriteBlankPenpalLetterFields(1, 2, "draft", 3)
        )
        self.assertIsNone(
            comm.decode_write_blank_penpal_letter_payload(payload[:-1])
        )

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        clean = comm.encode_write_blank_penpal_letter_payload(
            comm.WriteBlankPenpalLetterFields(1, 2, "draft", 3)
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    comm.decode_write_blank_penpal_letter_payload(
                        clean + extra
                    )
                )

    def test_wrong_tag_at_field1_fails_closed(self):
        payload = comm.encode_write_blank_penpal_letter_payload(
            comm.WriteBlankPenpalLetterFields(1, 2, "draft", 3)
        )
        corrupted = bytes([0x00]) + payload[1:]
        self.assertIsNone(
            comm.decode_write_blank_penpal_letter_payload(corrupted)
        )


if __name__ == "__main__":
    unittest.main()
