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


class AllWstringFieldsCarryTag0x48Tests(unittest.TestCase):
    """Every wstring field of every class in this module must carry the
    ``0x48`` tag byte -- table-driven so a class added later without an
    entry here is visible as a missing row, not as silent coverage.

    Why this exists at all (pf-adversary, round `on8hbb`): a round-trip
    test alone cannot catch a silent revert to
    ``ui_social_wire.encode_untagged_wstring``/``read_untagged_wstring``.
    That pair simply omits this byte, so encode and decode stay
    self-consistent and every round-trip, truncation and trailing-byte
    test in this file still passes while the bytes on the wire are wrong
    for a real client. Proven by reverting the calls in a scratch copy of
    the module: the rest of this file stayed green.

    Round `on8hbb` covered the first three migrated classes with one
    per-class method each (those three methods are kept above, unchanged);
    round `d1b231` migrated the remaining ten and generalised that shape
    into this table so that EVERY wstring field of EVERY class is checked
    -- the per-class methods only ever checked the first wstring, so
    ``ChangeActorPersonalData``'s second and third wstrings, and the
    second wstring of ``OpenLetterInABottle``/``OpenPenpalLetter``/
    ``ThrowPenpalLetter``, had no byte-level cover before this round.

    Offsets are written out by hand from the tag legend, NOT computed
    from the module under test (deriving them with the same helpers the
    code uses would make the test agree with any mutation of them):
    ``u64tag`` = 1 + 8 bytes, ``u32tag`` = 1 + 4, a bare u8 field = 1 + 1,
    ``wstring_tag`` = 1 + 4 + 2*len(s), so the two-character ``"ab"``
    used everywhere below is 9 bytes wide.
    """

    # (label, encode, decode, fields, expected offsets of each 0x48 byte)
    CASES = (
        (
            "ChangeActorComment",
            comm.encode_change_actor_comment_payload,
            comm.decode_change_actor_comment_payload,
            lambda: comm.ChangeActorCommentFields(1, "ab", 2),
            (9,),
        ),
        (
            "ChangeActorPenName",
            comm.encode_change_actor_pen_name_payload,
            comm.decode_change_actor_pen_name_payload,
            lambda: comm.ChangeActorPenNameFields(1, "ab", 2),
            (9,),
        ),
        (
            "ChangeActorPersonalData",
            comm.encode_change_actor_personal_data_payload,
            comm.decode_change_actor_personal_data_payload,
            lambda: comm.ChangeActorPersonalDataFields(1, "ab", "ab", "ab", 2),
            (9, 18, 27),
        ),
        (
            "CommunityPropertyChanged",
            comm.encode_community_property_changed_payload,
            comm.decode_community_property_changed_payload,
            lambda: comm.CommunityPropertyChangedFields(1, 2, 3, 4, "ab"),
            (25,),
        ),
        (
            "OpenLetterInABottle",
            comm.encode_open_letter_in_a_bottle_payload,
            comm.decode_open_letter_in_a_bottle_payload,
            lambda: comm.OpenLetterInABottleFields(1, 2, 3, "ab", "ab", 4, 5),
            (20, 29),
        ),
        (
            "OpenPenpalLetter",
            comm.encode_open_penpal_letter_payload,
            comm.decode_open_penpal_letter_payload,
            lambda: comm.OpenPenpalLetterFields(1, 2, 3, "ab", "ab", 4),
            (20, 29),
        ),
        (
            "RemoveBlackList",
            comm.encode_remove_black_list_payload,
            comm.decode_remove_black_list_payload,
            lambda: comm.RemoveBlackListFields(1, "ab", 2),
            (9,),
        ),
        (
            "RequestorConfirmSoulMateMatch",
            comm.encode_requestor_confirm_soul_mate_match_payload,
            comm.decode_requestor_confirm_soul_mate_match_payload,
            lambda: comm.RequestorConfirmSoulMateMatchFields(1, "ab", 2, 3),
            (9,),
        ),
        (
            "SetReceiveActiveChange",
            comm.encode_set_receive_active_change_payload,
            comm.decode_set_receive_active_change_payload,
            lambda: comm.SetReceiveActiveChangeFields(1, "ab", 2, 3),
            (9,),
        ),
        (
            "TargetConfirmSoulMateMatch",
            comm.encode_target_confirm_soul_mate_match_payload,
            comm.decode_target_confirm_soul_mate_match_payload,
            lambda: comm.TargetConfirmSoulMateMatchFields(1, "ab", 2),
            (9,),
        ),
        (
            "ThrowLetterInABottle",
            comm.encode_throw_letter_in_a_bottle_payload,
            comm.decode_throw_letter_in_a_bottle_payload,
            lambda: comm.ThrowLetterInABottleFields(1, "ab", 2),
            (9,),
        ),
        (
            "ThrowPenpalLetter",
            comm.encode_throw_penpal_letter_payload,
            comm.decode_throw_penpal_letter_payload,
            lambda: comm.ThrowPenpalLetterFields(1, 2, "ab", "ab", 3),
            (18, 27),
        ),
        (
            "WriteBlankPenpalLetter",
            comm.encode_write_blank_penpal_letter_payload,
            comm.decode_write_blank_penpal_letter_payload,
            lambda: comm.WriteBlankPenpalLetterFields(1, 2, "ab", 3),
            (18,),
        ),
    )

    def test_every_wstring_field_has_the_tag_byte(self):
        for label, encode, _decode, make, offsets in self.CASES:
            with self.subTest(cls=label):
                payload = encode(make())
                for offset in offsets:
                    self.assertEqual(
                        payload[offset], 0x48,
                        f"{label}: expected the 0x48 wstring tag at byte "
                        f"{offset}, found {payload[offset]:#04x}",
                    )

    def test_the_table_offsets_are_exactly_where_the_0x48_bytes_are(self):
        """pf-adversary D3, round `fvp9ke`. The test above only asks
        "is byte N equal to 0x48"; it never asks "is byte N the only place a
        0x48 appears". Measured that round: rewriting
        ``ChangeActorPersonalData``'s row from ``(9, 18, 27)`` to
        ``(9, 9, 9)`` -- i.e. inspecting one byte three times and leaving two
        of its three wstrings completely unchecked -- left this whole file
        green, and stayed green when those two fields were then emitted as
        raw untagged ``len32 + UTF-16LE`` inline (a shape the migration-guard
        detector cannot see either, because it never names the old pair).

        Anchoring the FULL set of 0x48 positions closes that: a row can no
        longer claim N fields while looking at fewer, and a field that stops
        being tagged shows up as a missing position rather than as an
        unexamined byte. Held exactly for all 13 rows when written.
        """
        for label, encode, _decode, make, offsets in self.CASES:
            with self.subTest(cls=label):
                payload = encode(make())
                self.assertEqual(
                    [i for i, b in enumerate(payload) if b == 0x48],
                    list(offsets),
                    f"{label}: the 0x48 bytes in the encoded payload are not "
                    "exactly the offsets this table claims -- either a "
                    "wstring field lost its tag, or the table is inspecting "
                    "fewer fields than it says it does",
                )

    def test_no_row_inspects_the_same_byte_twice(self):
        """Companion to the above, and the cheaper half of the same D3 fix:
        duplicate offsets in a row are never legitimate -- two wstring fields
        cannot begin at the same byte -- so reject them structurally instead
        of relying on the position check to notice."""
        for label, _e, _d, _m, offsets in self.CASES:
            with self.subTest(cls=label):
                self.assertEqual(
                    len(set(offsets)), len(offsets),
                    f"{label}: duplicate offset(s) in the table row",
                )

    def test_corrupting_any_wstring_tag_byte_fails_closed(self):
        for label, encode, decode, make, offsets in self.CASES:
            for offset in offsets:
                with self.subTest(cls=label, offset=offset):
                    payload = encode(make())
                    corrupted = (
                        payload[:offset] + bytes([0x00]) + payload[offset + 1:]
                    )
                    self.assertIsNone(
                        decode(corrupted),
                        f"{label}: decode accepted a payload whose wstring "
                        f"tag byte at {offset} was zeroed",
                    )

    def test_table_covers_every_wstring_carrying_class_in_the_module(self):
        # Guards the table itself: a class added or renamed later without
        # a row above would otherwise be silently uncovered.
        from dataclasses import fields as dataclass_fields

        covered = {label for label, _e, _d, _m, _o in self.CASES}
        expected = {}
        for name in dir(comm):
            if not name.endswith("Fields"):
                continue
            obj = getattr(comm, name)
            if not isinstance(obj, type):
                continue
            wstring_count = sum(
                1 for f in dataclass_fields(obj) if f.name.endswith("_wstring")
            )
            if wstring_count:
                expected[name[: -len("Fields")]] = wstring_count
        self.assertEqual(
            covered, set(expected),
            "table above is out of sync with the module's wstring-carrying "
            "classes",
        )
        for label, _e, _d, _m, offsets in self.CASES:
            with self.subTest(cls=label):
                self.assertEqual(
                    len(offsets), expected[label],
                    f"{label} has {expected[label]} wstring field(s) but "
                    f"{len(offsets)} offset(s) are checked",
                )

    def test_each_row_is_bound_to_its_own_classs_encoder(self):
        """pf-adversary D3 (second half), round `fvp9ke`: rows are matched to
        classes by LABEL STRING only, and this module deliberately keeps
        several byte-identical classes as distinct ids. Measured that round:
        re-pointing the ``SetReceiveActiveChange`` row at
        ``encode/decode_requestor_confirm_soul_mate_match_payload`` and then
        reverting the real ``SetReceiveActiveChange`` field left this file at
        75 passed -- the class became silently uncovered while the table
        still claimed it.

        Bind the row to the module function whose name is derived from the
        label, so a mis-pointed row is a failure rather than a coincidence.
        """
        import re

        for label, encode, decode, _m, _o in self.CASES:
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", label).lower()
            with self.subTest(cls=label):
                self.assertIs(
                    encode,
                    getattr(comm, f"encode_{snake}_payload"),
                    f"{label}: row's encoder is not encode_{snake}_payload",
                )
                self.assertIs(
                    decode,
                    getattr(comm, f"decode_{snake}_payload"),
                    f"{label}: row's decoder is not decode_{snake}_payload",
                )


if __name__ == "__main__":
    unittest.main()
