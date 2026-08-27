"""GM-003 `say` -> `Channel_GMGlobalMessageVital` (0x9F2C) frame composition.

Reuses the proven `channel_message_hypothesis.py` encoder (CHAT-CHANNEL-001/
002) via import, per the lesson of the retracted broadcast-wire round
(`rounds/GM_20260827_1415_broadcast-wire-attempted-and-retracted.md`): this
lane does not build a second wire codec for a vital another lane already
proved.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.channel_message_hypothesis import (
    SHARED_SERIALIZER_CHANNEL_IDS,
    decode_channel_message,
    make_channel_message_response,
)
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm.commands import GmCommand, parse_gm_command
from pirateforce_foundation.gm.say_wire import (
    GM_GLOBAL_CHANNEL_ID,
    SayWireError,
    make_say_broadcast_frame,
)


class SayWireIdentityTests(unittest.TestCase):
    def test_gm_global_channel_id_matches_the_proven_channel_table(self):
        self.assertEqual(
            GM_GLOBAL_CHANNEL_ID,
            SHARED_SERIALIZER_CHANNEL_IDS["Channel_GMGlobalMessageVital"],
        )
        self.assertEqual(GM_GLOBAL_CHANNEL_ID, 0x9F2C)


class SayWireFrameTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_say_builds_the_same_frame_the_channel_codec_would(self):
        command = parse_gm_command("say server is going down in 5 minutes")
        pc, frame = make_say_broadcast_frame(self.legacy, command)
        expected_pc, expected_frame = make_channel_message_response(
            self.legacy,
            GM_GLOBAL_CHANNEL_ID,
            "",
            "server is going down in 5 minutes",
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_frame_round_trips_through_the_channel_decoder(self):
        command = parse_gm_command("say hello sailors")
        pc, _frame = make_say_broadcast_frame(self.legacy, command)
        payload = pc[20:20 + len(pc) - 22]
        message = decode_channel_message(GM_GLOBAL_CHANNEL_ID, payload)
        self.assertEqual(message.channel_id, GM_GLOBAL_CHANNEL_ID)
        self.assertEqual(message.speaker, "")
        self.assertEqual(message.body, "hello sailors")

    def test_custom_speaker_is_carried_through(self):
        command = parse_gm_command("say all hands on deck")
        pc, frame = make_say_broadcast_frame(self.legacy, command, speaker="GM_Panya")
        expected_pc, expected_frame = make_channel_message_response(
            self.legacy, GM_GLOBAL_CHANNEL_ID, "GM_Panya", "all hands on deck",
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)


class SayWireRefusalTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_refuses_a_non_say_command(self):
        command = parse_gm_command("lv 60")
        with self.assertRaises(SayWireError):
            make_say_broadcast_frame(self.legacy, command)

    def test_refuses_a_non_str_speaker_with_say_wire_error_not_bare_type_error(self):
        command = parse_gm_command("say hi")
        with self.assertRaises(SayWireError):
            make_say_broadcast_frame(self.legacy, command, speaker=123)

    def test_refuses_an_empty_body_with_say_wire_error_not_bare_value_error(self):
        # say's own grammar cannot produce an empty message (parse_gm_command
        # rejects `say` with no text) but this module re-validates every
        # GmCommand "regardless of source" (docs/GM_LANE.md), same policy
        # gm/warp_executor.py follows -- so a hand-built GmCommand must still
        # be refused through this module's own error type.
        bad = GmCommand("say", ("",), "say")
        with self.assertRaises(SayWireError) as ctx:
            make_say_broadcast_frame(self.legacy, bad)
        self.assertNotIsInstance(ctx.exception, TypeError)

    def test_refuses_a_say_command_with_the_wrong_arg_count(self):
        bad = GmCommand("say", ("a", "b"), "say a b")
        with self.assertRaises(SayWireError):
            make_say_broadcast_frame(self.legacy, bad)

    def test_refuses_a_non_str_message_with_say_wire_error_not_bare_type_error(self):
        bad = GmCommand("say", (None,), "say")
        with self.assertRaises(SayWireError):
            make_say_broadcast_frame(self.legacy, bad)


class SayWireAdversaryFindingsTests(unittest.TestCase):
    """pf-adversary (this round) found two gaps not covered above: (1) the
    480-char MAX_SAY_MESSAGE_LENGTH cap gm/commands.py enforces only inside
    parse_gm_command was not re-checked here, so a hand-built GmCommand
    (docs/GM_LANE.md "regardless of source") could bypass it entirely; (2)
    command.args was indexed/measured with plain len()/[0], which raises a
    bare TypeError/KeyError/IndexError -- never SayWireError -- for an args
    container of the wrong shape (None, a set, a dict), not just the wrong
    value. These tests prove both are closed.
    """

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_refuses_a_message_over_the_max_say_length_with_say_wire_error(self):
        bad = GmCommand("say", ("A" * 481,), "say " + "A" * 481)
        with self.assertRaises(SayWireError) as ctx:
            make_say_broadcast_frame(self.legacy, bad)
        self.assertIn("480", str(ctx.exception))

    def test_accepts_a_message_exactly_at_the_max_say_length(self):
        command = GmCommand("say", ("A" * 480,), "say " + "A" * 480)
        pc, frame = make_say_broadcast_frame(self.legacy, command)
        self.assertTrue(pc)
        self.assertTrue(frame)

    def test_refuses_none_args_with_say_wire_error_not_bare_type_error(self):
        bad = GmCommand("say", None, "say hi")
        with self.assertRaises(SayWireError) as ctx:
            make_say_broadcast_frame(self.legacy, bad)
        self.assertNotIsInstance(ctx.exception, TypeError)

    def test_refuses_a_set_args_container_with_say_wire_error_not_bare_type_error(self):
        bad = GmCommand("say", {"hello"}, "say hello")
        with self.assertRaises(SayWireError) as ctx:
            make_say_broadcast_frame(self.legacy, bad)
        self.assertNotIsInstance(ctx.exception, TypeError)

    def test_refuses_a_dict_args_container_with_say_wire_error_not_bare_key_error(self):
        bad = GmCommand("say", {"body": "hello"}, "say hello")
        with self.assertRaises(SayWireError) as ctx:
            make_say_broadcast_frame(self.legacy, bad)
        self.assertNotIsInstance(ctx.exception, KeyError)


if __name__ == "__main__":
    unittest.main()
