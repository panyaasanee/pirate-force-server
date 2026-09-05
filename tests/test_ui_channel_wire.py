"""Pure unit tests for ``ui_channel_wire.py`` -- the nine ``Channel_*Vital``
classes not already owned by this project's five-class shared-serializer
chat module (see ``ui_channel_wire.py``'s module docstring for why that
module's name is deliberately not spelled out again here -- an ownership
guard elsewhere pins an exact allowlist of files allowed to mention it).

Not wiring tests -- see ``ui_social_wire.py``'s module docstring.
``Channel_LocalTalkMessageVital``/``Channel_PartyMessageVital``/
``Channel_GuildMessageVital``/``Channel_ActorBoardcastMessageVital``/
``Channel_GMGlobalMessageVital`` are out of scope (owned by that sibling
module) and have no coverage here.
``Channel_JoinClassChannelVital``/``Channel_ClassChannelMessageVital`` are
also out of scope (LANE-CS's grep hint per
``prompts/COMMON_LANE_ROUND.md``) and have no coverage here.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_channel_wire as ch  # noqa: E402


class TaggedWstringCodecTests(unittest.TestCase):
    def test_round_trip_nonempty(self):
        payload = ch.encode_channel_tagged_wstring("hello")
        text, offset = ch.read_channel_tagged_wstring(payload, 0)
        self.assertEqual(text, "hello")
        self.assertEqual(offset, len(payload))

    def test_round_trip_empty(self):
        payload = ch.encode_channel_tagged_wstring("")
        text, offset = ch.read_channel_tagged_wstring(payload, 0)
        self.assertEqual(text, "")
        self.assertEqual(offset, len(payload))

    def test_tag_byte_is_0x48(self):
        payload = ch.encode_channel_tagged_wstring("x")
        self.assertEqual(payload[0], 0x48)

    def test_wrong_tag_fails_closed(self):
        payload = bytes([0x00]) + ch.encode_channel_tagged_wstring("x")[1:]
        with self.assertRaises(ch.wire.WireDecodeError):
            ch.read_channel_tagged_wstring(payload, 0)

    def test_truncated_header_fails_closed(self):
        with self.assertRaises(ch.wire.WireDecodeError):
            ch.read_channel_tagged_wstring(b"\x48\x02\x00\x00", 0)

    def test_truncated_payload_fails_closed(self):
        payload = ch.encode_channel_tagged_wstring("ab")
        with self.assertRaises(ch.wire.WireDecodeError):
            ch.read_channel_tagged_wstring(payload[:-1], 0)


class WhisperWireTests(unittest.TestCase):
    def _fields(self):
        return ch.WhisperFields(
            speaker="alice", body="hi", recipient="bob", result_u8=1
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = ch.encode_whisper_payload(fields)
        self.assertEqual(ch.decode_whisper_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = ch.encode_whisper_payload(self._fields())
        self.assertIsNone(ch.decode_whisper_payload(payload[:-1]))

    def test_trailing_bytes_fail_closed(self):
        payload = ch.encode_whisper_payload(self._fields())
        for extra in (b"\xaa", b"\xaa" * 9):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(ch.decode_whisper_payload(payload + extra))

    def test_wrong_tag_at_result_fails_closed(self):
        payload = ch.encode_whisper_payload(self._fields())
        corrupted = payload[:-2] + bytes([0x00]) + payload[-1:]
        self.assertIsNone(ch.decode_whisper_payload(corrupted))


class CustomChannelMessageWireTests(unittest.TestCase):
    def _fields(self):
        return ch.CustomChannelMessageFields(
            speaker="s", body="b", field3_u8=2, channel_handle_u64=0xABCDEF
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = ch.encode_custom_channel_message_payload(fields)
        self.assertEqual(
            ch.decode_custom_channel_message_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = ch.encode_custom_channel_message_payload(self._fields())
        self.assertIsNone(
            ch.decode_custom_channel_message_payload(payload[:-1])
        )

    def test_trailing_bytes_fail_closed(self):
        payload = ch.encode_custom_channel_message_payload(self._fields())
        self.assertIsNone(
            ch.decode_custom_channel_message_payload(payload + b"\xaa")
        )


class OriginalSinChannelMessageWireTests(unittest.TestCase):
    def _fields(self):
        return ch.OriginalSinChannelMessageFields(
            speaker="s", body="b", field3_u8=3
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = ch.encode_original_sin_channel_message_payload(fields)
        self.assertEqual(
            ch.decode_original_sin_channel_message_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = ch.encode_original_sin_channel_message_payload(
            self._fields()
        )
        self.assertIsNone(
            ch.decode_original_sin_channel_message_payload(payload[:-1])
        )


class JoinCustomChannelWireTests(unittest.TestCase):
    def _fields(self):
        return ch.JoinCustomChannelFields(
            channel_handle_u64=42, channel_name="general", field3_u8=1,
            result_u8=0,
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = ch.encode_join_custom_channel_payload(fields)
        self.assertEqual(ch.decode_join_custom_channel_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = ch.encode_join_custom_channel_payload(self._fields())
        self.assertIsNone(ch.decode_join_custom_channel_payload(payload[:-1]))

    def test_trailing_bytes_fail_closed(self):
        payload = ch.encode_join_custom_channel_payload(self._fields())
        self.assertIsNone(
            ch.decode_join_custom_channel_payload(payload + b"\xaa")
        )


class LeaveCustomChannelWireTests(unittest.TestCase):
    def _fields(self):
        return ch.LeaveCustomChannelFields(
            channel_handle_u64=42, field2_u8=0, result_u8=0,
            channel_name="general",
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = ch.encode_leave_custom_channel_payload(fields)
        self.assertEqual(
            ch.decode_leave_custom_channel_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = ch.encode_leave_custom_channel_payload(self._fields())
        self.assertIsNone(
            ch.decode_leave_custom_channel_payload(payload[:-1])
        )


class ActorCustomChannelNotificationWireTests(unittest.TestCase):
    def _fields(self):
        return ch.ActorCustomChannelNotificationFields(
            channel_handle_u64=7, channel_name="general", actor_name="alice"
        )

    def test_round_trip_join_shape(self):
        fields = self._fields()
        payload = ch.encode_actor_custom_channel_notification_payload(fields)
        self.assertEqual(
            ch.decode_actor_custom_channel_notification_payload(payload),
            fields,
        )

    def test_same_codec_serves_leave_notification_too(self):
        # OnActorJoinCustomChannel and OnActorLeaveCustomChannel share
        # serializer 0x65B140 -- same shape, same codec, two different
        # vital ids applied by the caller (see module docstring).
        fields = ch.ActorCustomChannelNotificationFields(
            channel_handle_u64=7, channel_name="general", actor_name="bob"
        )
        payload = ch.encode_actor_custom_channel_notification_payload(fields)
        self.assertEqual(
            ch.decode_actor_custom_channel_notification_payload(payload),
            fields,
        )

    def test_truncated_payload_fails_closed(self):
        payload = ch.encode_actor_custom_channel_notification_payload(
            self._fields()
        )
        self.assertIsNone(
            ch.decode_actor_custom_channel_notification_payload(payload[:-1])
        )

    def test_trailing_bytes_fail_closed(self):
        payload = ch.encode_actor_custom_channel_notification_payload(
            self._fields()
        )
        self.assertIsNone(
            ch.decode_actor_custom_channel_notification_payload(
                payload + b"\xaa"
            )
        )


class JoinOriginalSinChannelWireTests(unittest.TestCase):
    def _fields(self):
        return ch.JoinOriginalSinChannelFields(
            channel_handle_u64=9, field2_u8=1, result_u8=0
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = ch.encode_join_original_sin_channel_payload(fields)
        self.assertEqual(
            ch.decode_join_original_sin_channel_payload(payload), fields
        )

    def test_truncated_payload_fails_closed(self):
        payload = ch.encode_join_original_sin_channel_payload(self._fields())
        self.assertIsNone(
            ch.decode_join_original_sin_channel_payload(payload[:-1])
        )

    def test_wrong_tag_at_field2_fails_closed(self):
        payload = ch.encode_join_original_sin_channel_payload(self._fields())
        corrupted = payload[:9] + bytes([0x00]) + payload[10:]
        self.assertIsNone(
            ch.decode_join_original_sin_channel_payload(corrupted)
        )


class LocalPerformanceWireTests(unittest.TestCase):
    def _fields(self):
        return ch.LocalPerformanceFields(
            field1_u64=1, field2_u64=2, field3_u16=3
        )

    def test_round_trip(self):
        fields = self._fields()
        payload = ch.encode_local_performance_payload(fields)
        self.assertEqual(ch.decode_local_performance_payload(payload), fields)

    def test_truncated_payload_fails_closed(self):
        payload = ch.encode_local_performance_payload(self._fields())
        self.assertIsNone(ch.decode_local_performance_payload(payload[:-1]))

    def test_trailing_bytes_fail_closed(self):
        payload = ch.encode_local_performance_payload(self._fields())
        self.assertIsNone(
            ch.decode_local_performance_payload(payload + b"\xaa")
        )


if __name__ == "__main__":
    unittest.main()
