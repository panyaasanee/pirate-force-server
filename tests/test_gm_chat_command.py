"""LANE-GM: GM commands typed into the ordinary chat box (0xAC52).

Proves `gm/chat_command.py` on both halves it claims:

1. THE DECODER matches the shape three attended captures measured
   (GT-006/GT-009, tabulated in
   `pf_bridge/reports/PF_CHAT_ECHO002_SPEAKER_FIELD_RESEARCH_20260818.md`
   section (a)).  The three real captured payloads are pinned here as
   literal bytes and must decode to the three strings the tester actually
   typed -- this file fails if the reading of the frame ever drifts from
   what was measured, not merely if the code disagrees with itself.

2. THE PERMISSION STORY holds for every path.  The lane's founding rule is
   "default = nobody is a GM, and a client can never promote itself".  The
   tests below drive a non-GM account through the exact same command text
   that works for a GM and assert it gets nothing -- no parse, no audit
   record, no text carried back out of the module at all.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm.commands import GmCommandParseError  # noqa: E402


# The three payloads GT-006/GT-009 actually captured, byte for byte, with
# the text the tester actually typed.  Lengths 34/20/46 for 12/5/18
# characters == 10 + 2*N in all three.
CAPTURED_SAMPLES = (
    (
        "PFCHATPROBE1",
        bytes.fromhex(
            "48000000004818000000"
            "500046004300480041005400500052004F00420045003100"
        ),
    ),
    (
        "SHORT",
        bytes.fromhex("4800000000480a000000") + "SHORT".encode("utf-16-le"),
    ),
    (
        "PFCHATPROBETOOLONG",
        bytes.fromhex("48000000004824000000")
        + "PFCHATPROBETOOLONG".encode("utf-16-le"),
    ),
)


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """Build a 0xAC52 payload in the measured shape.

    Kept in the test file, not in the module: the server has no reason to
    ever COMPOSE a client->server chat frame, and a composer living next to
    the decoder would be an untested code path in production for the
    convenience of tests.
    """
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class DecodeTests(unittest.TestCase):
    def test_the_three_captured_payloads_decode_to_the_typed_text(self):
        for typed, payload in CAPTURED_SAMPLES:
            with self.subTest(typed=typed):
                speaker, message = chat_command.decode_local_talk_payload(
                    payload
                )
                self.assertEqual(message, typed)
                # Empty in every captured sample; the module never reads a
                # value out of it (see its nonclaim 1) but must still see
                # it well-formed.
                self.assertEqual(speaker, "")

    def test_the_builder_reproduces_the_captured_bytes_exactly(self):
        # Guards the tests below: if make_chat_payload drifted from the
        # captured shape, every permission test would be proving the wrong
        # frame.
        for typed, payload in CAPTURED_SAMPLES:
            with self.subTest(typed=typed):
                self.assertEqual(make_chat_payload(typed), payload)

    def test_length_field_tracks_the_text_in_the_three_captured_lengths(self):
        for typed, payload in CAPTURED_SAMPLES:
            with self.subTest(typed=typed):
                (declared,) = struct.unpack_from("<I", payload, 6)
                self.assertEqual(declared, 2 * len(typed))
                self.assertEqual(len(payload), 10 + 2 * len(typed))

    def test_a_speaker_that_is_not_empty_still_decodes(self):
        # No captured sample has one, so this is a shape test only, not a
        # claim that the client ever sends one (nonclaim 1).
        speaker, message = chat_command.decode_local_talk_payload(
            make_chat_payload("hello", speaker="Bosun")
        )
        self.assertEqual((speaker, message), ("Bosun", "hello"))

    def test_non_ascii_text_round_trips(self):
        payload = make_chat_payload("ทดสอบ")
        _speaker, message = chat_command.decode_local_talk_payload(payload)
        self.assertEqual(message, "ทดสอบ")

    def test_a_wrong_tag_is_refused(self):
        payload = bytearray(make_chat_payload("hello"))
        payload[0] = 0x47
        with self.assertRaises(chat_command.ChatDecodeError):
            chat_command.decode_local_talk_payload(bytes(payload))

    def test_a_wrong_second_tag_is_refused(self):
        payload = bytearray(make_chat_payload("hello"))
        payload[5] = 0x00
        with self.assertRaises(chat_command.ChatDecodeError):
            chat_command.decode_local_talk_payload(bytes(payload))

    def test_a_length_field_past_the_end_is_refused_not_truncated(self):
        payload = bytearray(make_chat_payload("hello"))
        struct.pack_into("<I", payload, 6, 0xFFFFFFFF)
        with self.assertRaises(chat_command.ChatDecodeError):
            chat_command.decode_local_talk_payload(bytes(payload))

    def test_an_odd_length_field_is_refused(self):
        payload = bytearray(make_chat_payload("hello"))
        struct.pack_into("<I", payload, 6, 9)
        with self.assertRaises(chat_command.ChatDecodeError):
            chat_command.decode_local_talk_payload(bytes(payload))

    def test_trailing_bytes_are_refused(self):
        with self.assertRaises(chat_command.ChatDecodeError):
            chat_command.decode_local_talk_payload(
                make_chat_payload("hello") + b"\x00\x01"
            )

    def test_a_lone_surrogate_is_refused_not_replaced(self):
        # `errors="replace"` here would put U+FFFD inside a command
        # argument and hand an invented value to the parser.
        payload = bytearray()
        payload.append(chat_command.WSTRING_TAG)
        payload += struct.pack("<I", 0)
        payload.append(chat_command.WSTRING_TAG)
        payload += struct.pack("<I", 2)
        payload += b"\x00\xd8"  # high surrogate, unpaired
        with self.assertRaises(chat_command.ChatDecodeError):
            chat_command.decode_local_talk_payload(bytes(payload))

    def test_an_empty_payload_is_refused(self):
        with self.assertRaises(chat_command.ChatDecodeError):
            chat_command.decode_local_talk_payload(b"")

    def test_a_non_bytes_payload_raises_type_error(self):
        with self.assertRaises(TypeError):
            chat_command.decode_local_talk_payload("48000000")


class SigilTests(unittest.TestCase):
    def test_a_leading_slash_is_a_command(self):
        self.assertTrue(chat_command.looks_like_gm_command("/warp 2"))

    def test_ordinary_chat_is_not_a_command(self):
        for text in ("warp 2", "hello there", "", "he said /warp 2"):
            with self.subTest(text=text):
                self.assertFalse(chat_command.looks_like_gm_command(text))

    def test_a_leading_space_before_the_slash_is_chat_not_a_command(self):
        # A lane that stripped first would silently eat this chat line.
        self.assertFalse(chat_command.looks_like_gm_command(" /warp 2"))

    def test_the_sigil_is_stripped_before_the_grammar_sees_the_text(self):
        command = chat_command.parse_chat_command_text("/warp 2")
        self.assertEqual(command.name, "warp")
        self.assertEqual(command.args, ("2",))
        # The audit log must record the same `raw` for the same typed words
        # whichever door they arrived through.
        self.assertEqual(command.raw, "warp 2")

    def test_text_without_the_sigil_is_refused_by_the_parser_entry(self):
        with self.assertRaises(GmCommandParseError):
            chat_command.parse_chat_command_text("warp 2")


class _AllowlistCase(unittest.TestCase):
    """Base: a temp dir with a gm_accounts.json and a temp audit log."""

    GM_ACCOUNT = "gmtester"
    PLAYER_ACCOUNT = "ordinaryplayer"

    def setUp(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.config_path = self.tmp / "gm_accounts.json"
        self.config_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.log_path = self.tmp / "capture" / "gm_command_log.ndjson"

    def handle(self, account, text, **kwargs):
        return chat_command.handle_local_talk_chat(
            account,
            make_chat_payload(text),
            config_path=str(self.config_path),
            log_path=str(self.log_path),
            **kwargs,
        )

    def log_records(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


class PermissionTests(_AllowlistCase):
    def test_a_gm_account_gets_the_command_parsed_and_logged(self):
        outcome = self.handle(self.GM_ACCOUNT, "/warp 2")
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.refusal_reason)
        self.assertIsNotNone(outcome.command)
        self.assertEqual(outcome.command.name, "warp")
        self.assertEqual(outcome.command.args, ("2",))
        records = self.log_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["account"], self.GM_ACCOUNT)
        self.assertEqual(records[0]["command"], "warp")
        # GM-003 v1 still applies no gameplay effect of its own.
        self.assertFalse(records[0]["executed"])

    def test_a_non_gm_account_typing_the_same_command_gets_nothing(self):
        outcome = self.handle(self.PLAYER_ACCOUNT, "/warp 2")
        self.assertFalse(outcome.authorized)
        self.assertEqual(outcome.refusal_reason, gm_dispatch.REFUSAL_NOT_GM)
        self.assertIsNone(outcome.command)
        # Not merely "no command": the module never decoded the sentence.
        self.assertIsNone(outcome.text)
        self.assertEqual(self.log_records(), [])

    def test_an_empty_allowlist_means_nobody_is_a_gm(self):
        self.config_path.write_text(
            json.dumps({"gm_accounts": []}), encoding="utf-8"
        )
        for account in (self.GM_ACCOUNT, self.PLAYER_ACCOUNT):
            with self.subTest(account=account):
                outcome = self.handle(account, "/warp 2")
                self.assertFalse(outcome.authorized)
                self.assertIsNone(outcome.command)
                self.assertIsNone(outcome.text)
        self.assertEqual(self.log_records(), [])

    def test_a_missing_allowlist_config_means_nobody_is_a_gm(self):
        self.config_path.unlink()
        outcome = self.handle(self.GM_ACCOUNT, "/warp 2")
        self.assertFalse(outcome.authorized)
        self.assertIsNone(outcome.command)
        self.assertEqual(self.log_records(), [])

    def test_a_malformed_allowlist_refuses_instead_of_raising(self):
        # Same reasoning as test_gm_dispatch.py's malformed-config test: one
        # operator typo must not take down the thread handling every
        # player's chat.
        self.config_path.write_text("{not json", encoding="utf-8")
        outcome = self.handle(self.GM_ACCOUNT, "/warp 2")
        self.assertFalse(outcome.authorized)
        self.assertIsNotNone(outcome.refusal_reason)
        self.assertTrue(
            outcome.refusal_reason.startswith(
                gm_dispatch.REFUSAL_LOOKUP_FAILED_PREFIX
            )
        )
        self.assertIsNone(outcome.command)
        self.assertEqual(self.log_records(), [])

    def test_the_payload_can_never_name_the_account_that_is_checked(self):
        # The client's only input here is the payload. Putting the GM
        # account's name inside the chat text must not authorize anything.
        outcome = self.handle(
            self.PLAYER_ACCOUNT, f"/say {self.GM_ACCOUNT}"
        )
        self.assertFalse(outcome.authorized)
        self.assertIsNone(outcome.command)

    def test_a_str_subclass_account_is_rejected_outright(self):
        class Sneaky(str):
            def __eq__(self, other):  # pragma: no cover - never reached
                return True

            def __hash__(self):
                return hash(str(self))

        with self.assertRaises(ValueError):
            chat_command.handle_local_talk_chat(
                Sneaky(self.PLAYER_ACCOUNT),
                make_chat_payload("/warp 2"),
                config_path=str(self.config_path),
            )

    def test_an_empty_account_name_is_rejected_outright(self):
        with self.assertRaises(ValueError):
            chat_command.handle_local_talk_chat(
                "", make_chat_payload("/warp 2"),
                config_path=str(self.config_path),
            )


class OrdinaryChatTests(_AllowlistCase):
    def test_a_gms_ordinary_chat_is_not_a_command_and_is_never_logged(self):
        outcome = self.handle(self.GM_ACCOUNT, "sailing to port royal")
        self.assertTrue(outcome.authorized)
        self.assertEqual(
            outcome.refusal_reason, chat_command.REFUSAL_NOT_A_COMMAND
        )
        self.assertIsNone(outcome.command)
        self.assertEqual(outcome.text, "sailing to port royal")
        self.assertEqual(self.log_records(), [])

    def test_ordinary_chat_does_not_consume_the_rate_limit_budget(self):
        # A GM holding a conversation must still be able to issue a command
        # immediately afterwards.
        for index in range(gm_dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW * 2):
            self.handle(self.GM_ACCOUNT, f"chatting {index}", now_ts=1000.0)
        outcome = self.handle(self.GM_ACCOUNT, "/warp 2", now_ts=1000.0)
        self.assertIsNotNone(outcome.command)

    def test_an_undecodable_payload_refuses_without_carrying_text_out(self):
        outcome = chat_command.handle_local_talk_chat(
            self.GM_ACCOUNT,
            b"\x47\x00\x00\x00\x00\x48\x00\x00\x00\x00",
            config_path=str(self.config_path),
            log_path=str(self.log_path),
        )
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.text)
        self.assertTrue(
            outcome.refusal_reason.startswith(
                chat_command.REFUSAL_UNDECODABLE_PREFIX
            )
        )
        self.assertEqual(self.log_records(), [])

    def test_an_oversized_payload_is_refused_before_it_is_decoded(self):
        huge = make_chat_payload(
            "x" * (chat_command.MAX_CHAT_PAYLOAD_LENGTH // 2)
        )
        self.assertGreater(len(huge), chat_command.MAX_CHAT_PAYLOAD_LENGTH)
        outcome = chat_command.handle_local_talk_chat(
            self.GM_ACCOUNT,
            huge,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
        )
        self.assertTrue(outcome.authorized)
        self.assertEqual(
            outcome.refusal_reason, chat_command.REFUSAL_PAYLOAD_TOO_LARGE
        )
        self.assertIsNone(outcome.text)


class CommandBehaviourTests(_AllowlistCase):
    def test_every_command_name_in_the_lane_grammar_arrives_through_chat(self):
        typed = {
            "warp": "/warp 2",
            "npc": "/npc on 4",
            "item": "/item 100 5",
            "lv": "/lv 30",
            "spawn": "/spawn 8223",
            "say": "/say ahoy",
        }
        for name, text in typed.items():
            with self.subTest(command=name):
                gm_dispatch.reset_rate_limit_state_for_tests()
                outcome = self.handle(self.GM_ACCOUNT, text)
                self.assertIsNotNone(
                    outcome.command, msg=outcome.refusal_reason
                )
                self.assertEqual(outcome.command.name, name)

    def test_an_ungrammatical_command_refuses_and_keeps_the_typed_text(self):
        outcome = self.handle(self.GM_ACCOUNT, "/warp")
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.command)
        self.assertEqual(outcome.text, "/warp")
        self.assertTrue(
            outcome.refusal_reason.startswith(
                chat_command.REFUSAL_PARSE_ERROR_PREFIX
            )
        )
        self.assertEqual(self.log_records(), [])

    def test_an_unknown_command_word_refuses(self):
        outcome = self.handle(self.GM_ACCOUNT, "/banhammer someone")
        self.assertIsNone(outcome.command)
        self.assertTrue(
            outcome.refusal_reason.startswith(
                chat_command.REFUSAL_PARSE_ERROR_PREFIX
            )
        )

    def test_the_rate_limit_is_shared_with_the_0x51e9_door(self):
        # Two doors, one budget: the ceiling this lane advertises is per
        # account, so filling the window through chat must also close it
        # for the other path.
        for index in range(gm_dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW):
            outcome = self.handle(self.GM_ACCOUNT, "/lv 1", now_ts=2000.0)
            self.assertIsNotNone(outcome.command, msg=f"call {index}")
        blocked = self.handle(self.GM_ACCOUNT, "/lv 1", now_ts=2000.0)
        self.assertEqual(
            blocked.refusal_reason, gm_dispatch.REFUSAL_RATE_LIMITED
        )
        self.assertFalse(
            gm_dispatch.rate_limit_allows(self.GM_ACCOUNT, 2000.0)
        )

    def test_a_full_window_reopens_once_it_ages_out(self):
        for _ in range(gm_dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW):
            self.handle(self.GM_ACCOUNT, "/lv 1", now_ts=3000.0)
        self.assertEqual(
            self.handle(
                self.GM_ACCOUNT, "/lv 1", now_ts=3000.0
            ).refusal_reason,
            gm_dispatch.REFUSAL_RATE_LIMITED,
        )
        later = 3000.0 + gm_dispatch.RATE_LIMIT_WINDOW_SECONDS + 1.0
        self.assertIsNotNone(
            self.handle(self.GM_ACCOUNT, "/lv 1", now_ts=later).command
        )

    def test_an_unwritable_audit_log_fails_closed(self):
        # The log path's parent is a FILE, so the directory create fails.
        blocker = self.tmp / "blocked"
        blocker.write_text("not a directory", encoding="utf-8")
        outcome = chat_command.handle_local_talk_chat(
            self.GM_ACCOUNT,
            make_chat_payload("/warp 2"),
            config_path=str(self.config_path),
            log_path=str(blocker / "log.ndjson"),
        )
        self.assertTrue(outcome.authorized)
        self.assertIsNone(
            outcome.command,
            msg="an unauditable GM command must not be handed onward",
        )
        self.assertTrue(
            outcome.refusal_reason.startswith(
                chat_command.REFUSAL_LOG_WRITE_FAILED_PREFIX
            )
        )


class _FakeSession:
    """The two attributes runtime.py's real session exposes to a hook.

    `token` is the authenticated login name (what runtime.py's own GM-state
    login check already uses) and `events` is the list every other hook in
    this package appends to.  Nothing else is provided ON PURPOSE: a hook
    that reaches for a third attribute should fail here, in a test, rather
    than at 2 a.m. on a real connection.
    """

    def __init__(self, token: str):
        self.token = token
        self.events: list[str] = []


class AdversarySweepTests(_AllowlistCase):
    """Regressions for the pf-adversary findings of round `hs9m2r`."""

    def test_a_short_write_to_the_audit_log_is_not_reported_as_success(self):
        # Finding 2: `os.write` may write fewer bytes than asked WITHOUT
        # raising (a disk filling up mid-write is the classic case). The
        # old code discarded the return value, so the caller handed the
        # command onward believing it was audited while the file held a
        # truncated record. Simulate the short write directly.
        real_write = os.write
        state = {"first": True}

        def short_once(fd, data):
            if state["first"] and len(data) > 1:
                state["first"] = False
                return real_write(fd, data[:1])
            return real_write(fd, data)

        with mock.patch("pirateforce_foundation.gm.commands.os.write",
                        side_effect=short_once):
            outcome = self.handle(self.GM_ACCOUNT, "/warp 2")
        # The resumed write must complete the record...
        self.assertIsNotNone(outcome.command, msg=outcome.refusal_reason)
        records = self.log_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["command"], "warp")

    def test_a_write_making_no_progress_fails_closed(self):
        with mock.patch("pirateforce_foundation.gm.commands.os.write",
                        return_value=0):
            outcome = self.handle(self.GM_ACCOUNT, "/warp 2")
        self.assertIsNone(
            outcome.command,
            msg="a command whose audit record never landed must not be "
                "handed onward",
        )
        self.assertTrue(
            outcome.refusal_reason.startswith(
                chat_command.REFUSAL_LOG_WRITE_FAILED_PREFIX
            )
        )

    def test_the_audit_log_stops_accepting_once_it_passes_its_cap(self):
        # Finding 1: the shared rate limiter is generous enough never to
        # refuse a human, so without a volume cap a scripted GM account can
        # append to this file forever.
        # The cap is patched down rather than writing a real 64 MiB file:
        # the guard compares `st_size` against the constant, so a small cap
        # exercises the identical code path without making every CI run
        # write (and every developer's disk hold) 64 MiB of filler twice.
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_bytes(b"x" * 4096)
        with mock.patch.object(chat_command, "MAX_COMMAND_LOG_BYTES", 4096):
            outcome = self.handle(self.GM_ACCOUNT, "/warp 2")
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.command)
        self.assertEqual(
            outcome.refusal_reason, chat_command.REFUSAL_LOG_QUOTA_EXCEEDED
        )

    def test_a_log_just_under_the_cap_still_accepts(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_bytes(b"x" * 4095)
        with mock.patch.object(chat_command, "MAX_COMMAND_LOG_BYTES", 4096):
            self.assertIsNotNone(
                self.handle(self.GM_ACCOUNT, "/warp 2").command
            )

    def test_the_shipped_cap_is_a_real_bound_not_effectively_infinite(self):
        # The tests above patch the constant, so this is what pins the
        # value that actually ships.
        self.assertEqual(
            chat_command.MAX_COMMAND_LOG_BYTES, 64 * 1024 * 1024
        )

    def test_a_bidi_override_in_a_command_never_reaches_the_audit_log(self):
        # Finding 3: json.dumps escapes the C0 control range but not
        # category-Cf characters, which reorder how a line renders. An
        # audit log that displays something other than what was typed is
        # not an audit log.
        outcome = self.handle(self.GM_ACCOUNT, "/say abc‮def")
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.command)
        self.assertEqual(
            outcome.refusal_reason, chat_command.REFUSAL_UNSAFE_COMMAND_TEXT
        )
        self.assertEqual(self.log_records(), [])

    def test_other_format_characters_are_refused_too(self):
        for codepoint in ("​", "⁦", "‏", "﻿"):
            with self.subTest(codepoint=hex(ord(codepoint))):
                gm_dispatch.reset_rate_limit_state_for_tests()
                outcome = self.handle(
                    self.GM_ACCOUNT, f"/say hi{codepoint}there"
                )
                self.assertEqual(
                    outcome.refusal_reason,
                    chat_command.REFUSAL_UNSAFE_COMMAND_TEXT,
                )

    def test_ordinary_thai_text_is_not_mistaken_for_a_format_character(self):
        # The Cf guard must not become a "no non-ASCII" rule by accident.
        outcome = self.handle(self.GM_ACCOUNT, "/say สวัสดีชาวเรือ")
        self.assertIsNotNone(outcome.command, msg=outcome.refusal_reason)
        self.assertEqual(outcome.command.name, "say")

    def test_a_mutable_payload_cannot_change_between_the_size_check_and_decode(
        self,
    ):
        # Finding 6: the size check and the decode must read one snapshot.
        buffer = bytearray(make_chat_payload("/warp 2"))
        outcome = chat_command.handle_local_talk_chat(
            self.GM_ACCOUNT,
            buffer,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
        )
        self.assertIsNotNone(outcome.command, msg=outcome.refusal_reason)
        # Mutating the caller's buffer afterwards must not change what was
        # decoded -- proof the module kept its own copy.
        buffer[0] = 0x00
        self.assertEqual(outcome.text, "/warp 2")


class HookRegistrationTests(unittest.TestCase):
    def test_the_lane_hook_module_declares_production_allowed(self):
        from pirateforce_foundation.lane_hooks import lane_gm_chat_command

        self.assertIs(lane_gm_chat_command.production_allowed, True)

    def test_the_hook_is_registered_for_its_agreed_point_name(self):
        from pirateforce_foundation import lane_hooks

        lane_hooks._discover()
        registered = lane_hooks._HOOKS.get("vital_inbound_chat_local_talk", [])
        self.assertTrue(
            any(
                name.endswith("lane_gm_chat_command")
                for name, _fn in registered
            ),
            msg=f"registered hooks for this point: {registered}",
        )


class HookBehaviourTests(_AllowlistCase):
    """Drive the registered hook function itself, not just its registration.

    Written because the two registration tests above prove only that a
    callable is in `_HOOKS` under the right name -- they would pass
    unchanged against a hook whose body called the handler with its
    arguments swapped, or read a misspelled session attribute.  Both of
    those are silent in production: `lane_hooks.fire()` catches every
    exception a hook raises, prints `LANE_HOOK ... ERR`, and moves on, so a
    broken hook looks exactly like a hook whose point never fired.  These
    tests call the function directly, with no `fire()` in between, so a
    mistake in it is an ordinary red test.
    """

    def setUp(self):
        super().setUp()
        # The hook passes NO config_path and NO log_path -- that is the
        # production call, and these tests must exercise exactly it. So
        # point the lane's own env override at the temp allowlist and run
        # from the temp directory, which is where the default relative
        # `capture/gm_command_log.ndjson` then lands.
        self.enterContext(
            mock.patch.dict(
                os.environ,
                {gm_accounts.ENV_OVERRIDE: str(self.config_path)},
            )
        )
        previous_cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, previous_cwd)
        self.log_path = self.tmp / "capture" / "gm_command_log.ndjson"

    def hook_fn(self):
        from pirateforce_foundation.lane_hooks import lane_gm_chat_command

        return lane_gm_chat_command._on_chat_local_talk

    def fire(self, account, text):
        session = _FakeSession(account)
        self.hook_fn()(session, make_chat_payload(text))
        return session

    def test_the_hook_reads_the_account_from_the_session_not_the_payload(self):
        # The single most important line in the file: `session.token` is
        # the authenticated identity and the payload is client-supplied
        # text. Swapping them, or misspelling the attribute, must be red.
        session = self.fire(self.GM_ACCOUNT, "/warp 2")
        self.assertEqual(session.events, ["gm_chat_command_accepted_warp"])

    def test_the_hook_names_the_command_it_accepted(self):
        session = self.fire(self.GM_ACCOUNT, "/lv 30")
        self.assertEqual(session.events, ["gm_chat_command_accepted_lv"])

    def test_the_hook_refuses_a_non_gm_account(self):
        session = self.fire(self.PLAYER_ACCOUNT, "/warp 2")
        self.assertEqual(
            session.events, ["gm_chat_command_refused_not_gm_account"]
        )

    def test_the_hook_marks_ordinary_chat_as_not_a_command(self):
        session = self.fire(self.GM_ACCOUNT, "hello there")
        self.assertEqual(
            session.events, ["gm_chat_command_refused_not_a_command"]
        )

    def test_no_event_the_hook_emits_ever_carries_the_typed_text(self):
        # A console line per chat message is fine; a console line
        # containing what a player said is not.
        secret = "meet me behind the tavern"
        for account in (self.GM_ACCOUNT, self.PLAYER_ACCOUNT):
            with self.subTest(account=account):
                session = self.fire(account, secret)
                self.assertEqual(len(session.events), 1)
                self.assertNotIn(secret, session.events[0])
                self.assertNotIn("tavern", session.events[0])

    def test_the_hook_raises_nothing_of_its_own_on_a_malformed_payload(self):
        # fire() would swallow an exception here, so a hook that raised
        # would be indistinguishable from one that was never called.
        session = _FakeSession(self.GM_ACCOUNT)
        self.hook_fn()(session, b"\x00\x01\x02")
        self.assertEqual(len(session.events), 1)
        self.assertTrue(session.events[0].startswith(
            "gm_chat_command_refused_"
        ))

    def test_the_hook_works_when_driven_through_lane_hooks_fire(self):
        # pf-adversary finding 4: `fire()` calls `fn(**kwargs)` inside a
        # broad `except Exception`, so if the eventual runtime.py call site
        # used different keyword names than this hook's parameters, every
        # real chat frame would print LANE_HOOK_FIRED followed by an
        # invisible-in-practice ERR line and the lane would be silently
        # dead forever. This test fires the point with the EXACT kwargs
        # CORE-REQUEST-GM-028 asks chief to write, so a mismatch on this
        # side of the contract is red here instead.
        from pirateforce_foundation import lane_hooks

        lane_hooks._discover()
        session = _FakeSession(self.GM_ACCOUNT)
        lane_hooks.fire(
            "vital_inbound_chat_local_talk",
            session=session,
            payload=make_chat_payload("/warp 2"),
        )
        self.assertEqual(
            session.events,
            ["gm_chat_command_accepted_warp"],
            msg="fire() swallowed an exception from the hook -- check the "
                "keyword names against the hook's parameters",
        )

    def test_with_no_allowlist_reachable_at_all_nobody_is_a_gm(self):
        # The production call passes no config_path, so if the env override
        # and the default file are both absent the lane must fall back to
        # "nobody is GM" -- never to "everybody".
        with mock.patch.dict(os.environ, {}, clear=True):
            session = _FakeSession(self.GM_ACCOUNT)
            self.hook_fn()(session, make_chat_payload("/warp 2"))
        self.assertEqual(
            session.events, ["gm_chat_command_refused_not_gm_account"]
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
