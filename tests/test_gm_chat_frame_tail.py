"""LANE-GM / CHAT-TAIL-001: the chat body of a MULTI-VITAL frame.

WHAT THIS FILE IS ABOUT.  `runtime.py` hands the GM chat route
`bytes(parsed.nested_payload)`, and v141 sets that to every byte after the
FIRST nested vital's header.  With one vital in the frame it is the chat body
and everything works; with two it is the chat body plus the next vital's
bytes, and `chat_command.decode_local_talk_payload` refuses the whole command
with "trailing bytes after wstring#2".  `gm/chat_frame_tail.py` finds the
boundary -- or refuses, by name, and leaves main's behaviour untouched.

THE HONEST FRAME, repeated here because a test file is where a claim gets
believed: NO CAPTURED CHAT FRAME CARRYING A SECOND VITAL EXISTS.  Every case
below builds its multi-vital frames by hand.  What is measured is that this
client bundles up to five vitals into one frame on other traffic (R303,
`vital_walk.py`'s docstring), and that today's route would refuse a GM
command inside such a frame while blaming a codec.  Nothing here is evidence
that the client has ever done it.

THE PROPERTY EVERY CASE IS SERVING: a frame that works on main today must go
down exactly the path it goes down today, and a frame this module cannot
read exactly must be refused, never salvaged.
"""
from __future__ import annotations

import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import vital_walk  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import chat_frame_tail  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

UNPROVEN_TEST_VERSION = 7


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


def nested_vital(vital_id: int, body: bytes, version: int = 0) -> bytes:
    """One nested vital as v141's `Cursor` reads it: 5-byte header + body."""
    return (
        bytes([0x12])
        + struct.pack("<H", vital_id)
        + bytes([0x0B, version])
        + body
    )


class FakeSelected:
    def __init__(self):
        self.position = FakePosition()
        self.id = 41


class FakePosition:
    def __init__(self, scene_id=2, x=10.0, y=20.0, z=30.0):
        self.scene_id = scene_id
        self.scene_seq = 0
        self.x = x
        self.y = y
        self.z = z


class FakeFoundation:
    def __init__(self):
        self.selected = FakeSelected()


class FakeSession:
    def __init__(self, token="GM_ONE"):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation()


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"
    PLAYER_ACCOUNT = "DECKHAND"

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
        self.login_scene_config_path = self.tmp / "config" / "gm_login_scene.json"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.table = vital_walk.body_length_table(self.legacy)

    def target_pos_vital(self, version: int = 0) -> bytes:
        vital_id = self.legacy.TARGET_POS_VITAL
        return nested_vital(vital_id, b"\x00" * self.table[vital_id], version)

    def on_land_vital(self) -> bytes:
        vital_id = self.legacy.ON_LAND_VITAL
        return nested_vital(vital_id, b"\x00" * self.table[vital_id])

    def split(self, payload, legacy=None):
        return chat_frame_tail.split_local_talk_payload(
            payload, self.legacy if legacy is None else legacy
        )

    def act(self, session, payload, **kwargs):
        kwargs.setdefault(
            "login_scene_config_path", str(self.login_scene_config_path)
        )
        return chat_command_action.make_gm_chat_command_action(
            session,
            payload,
            self.legacy,
            config_path=str(self.config_path),
            log_path=str(self.log_path),
            **kwargs,
        )

    def open_the_version_gate(self):
        return mock.patch.object(
            teleport_wire,
            "FORCE_POS_VITAL_VERSION_CONFIRMED",
            UNPROVEN_TEST_VERSION,
        )

    def log_records(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def tail_events(self, session):
        return [
            event
            for event in session.events
            if event.startswith(chat_command_action.EVENT_CHAT_TAIL_PREFIX)
        ]


class SingleVitalFrameTests(_Case):
    """The frame every capture this project holds actually carries."""

    def test_an_ordinary_chat_payload_reports_no_tail_and_keeps_its_bytes(self):
        payload = make_chat_payload("/warp 2 100 200")
        split = self.split(payload)
        self.assertEqual(split.reason, chat_frame_tail.NO_TAIL)
        self.assertFalse(split.split)
        self.assertEqual(split.body, payload)
        self.assertEqual(split.tail_ids, ())

    def test_an_empty_message_still_reports_no_tail(self):
        split = self.split(make_chat_payload(""))
        self.assertEqual(split.reason, chat_frame_tail.NO_TAIL)

    def test_the_no_tail_path_writes_no_event_and_no_console_line(self):
        session = FakeSession()
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.open_the_version_gate():
            self.act(session, make_chat_payload("/warp 2 100 200"))
        self.assertEqual(self.tail_events(session), [])
        self.assertNotIn(chat_frame_tail.CHAT_TAIL_TOKEN, stream.getvalue())


class WalkedTailTests(_Case):
    def test_a_chat_body_followed_by_target_pos_yields_the_body_alone(self):
        body = make_chat_payload("/warp 2 100 200")
        split = self.split(body + self.target_pos_vital())
        self.assertEqual(split.reason, chat_frame_tail.TAIL_WALKED)
        self.assertTrue(split.split)
        self.assertEqual(split.body, body)
        self.assertEqual(split.tail_ids, (self.legacy.TARGET_POS_VITAL,))

    def test_four_on_land_vitals_and_a_target_pos_all_walk(self):
        body = make_chat_payload("/warp 2 100 200")
        tail = self.on_land_vital() * 4 + self.target_pos_vital()
        split = self.split(body + tail)
        self.assertEqual(split.reason, chat_frame_tail.TAIL_WALKED)
        self.assertEqual(
            split.tail_ids,
            (self.legacy.ON_LAND_VITAL,) * 4 + (self.legacy.TARGET_POS_VITAL,),
        )

    def test_the_isolated_body_is_what_the_strict_decoder_reads(self):
        """The split may never hand on a body the real decoder refuses."""
        body = make_chat_payload("/warp 2 100 200", speaker="GM_ONE")
        split = self.split(body + self.target_pos_vital())
        speaker, message = chat_command.decode_local_talk_payload(split.body)
        self.assertEqual(speaker, "GM_ONE")
        self.assertEqual(message, "/warp 2 100 200")

    def test_a_tail_carrying_wstring_shaped_bytes_cannot_move_the_boundary(self):
        """The attack this module has to survive to be worth having.

        The boundary comes from the two length fields at the FRONT of the
        payload and from nothing else, so a tail stuffed with bytes that
        look like a third wstring header cannot lengthen the text the GM is
        recorded as having typed.
        """
        body = make_chat_payload("/warp 2")
        fake_header = (
            bytes([chat_command.WSTRING_TAG])
            + struct.pack("<I", 4)
            + "AB".encode("utf-16-le")
        )
        vital_id = self.legacy.TARGET_POS_VITAL
        stuffed = fake_header + b"\x00" * (self.table[vital_id] - len(fake_header))
        split = self.split(body + nested_vital(vital_id, stuffed))
        self.assertEqual(split.reason, chat_frame_tail.TAIL_WALKED)
        self.assertEqual(
            chat_command.decode_local_talk_payload(split.body), ("", "/warp 2")
        )

    def test_a_nonzero_nested_version_in_the_tail_still_walks(self):
        body = make_chat_payload("/warp 2 100 200")
        split = self.split(body + self.target_pos_vital(version=3))
        self.assertEqual(split.reason, chat_frame_tail.TAIL_WALKED)


class RefusedTailTests(_Case):
    """Every one of these means "the caller keeps exactly what it had"."""

    def assertRefused(self, split, reason):
        self.assertEqual(split.reason, reason)
        self.assertIsNone(split.body)
        self.assertEqual(split.tail_ids, ())
        self.assertFalse(split.split)

    def test_an_id_with_no_declared_body_length_stops_the_walk(self):
        unknown = 0x4321
        self.assertNotIn(unknown, self.table)
        split = self.split(
            make_chat_payload("/warp 2 100 200") + nested_vital(unknown, b"\x00" * 8)
        )
        self.assertRefused(split, chat_frame_tail.TAIL_UNKNOWN_VITAL_ID)

    def test_a_body_shorter_than_its_declared_length_is_refused(self):
        vital_id = self.legacy.TARGET_POS_VITAL
        short = nested_vital(vital_id, b"\x00" * (self.table[vital_id] - 1))
        split = self.split(make_chat_payload("/warp 2 100 200") + short)
        self.assertRefused(split, chat_frame_tail.TAIL_TRUNCATED)

    def test_one_leftover_byte_after_the_last_tail_vital_is_refused(self):
        split = self.split(
            make_chat_payload("/warp 2 100 200") + self.target_pos_vital() + b"\x00"
        )
        self.assertRefused(split, chat_frame_tail.TAIL_TRUNCATED)

    def test_a_truncated_nested_header_is_refused(self):
        split = self.split(make_chat_payload("/warp 2 100 200") + b"\x12\x90")
        self.assertRefused(split, chat_frame_tail.TAIL_TRUNCATED)

    def test_a_tail_byte_that_is_not_a_vital_tag_is_refused(self):
        split = self.split(make_chat_payload("/warp 2 100 200") + b"\xff" * 8)
        self.assertRefused(split, chat_frame_tail.TAIL_TRUNCATED)

    def test_a_wstring_tag_that_is_not_0x48_is_unreadable(self):
        payload = bytearray(make_chat_payload("/warp 2 100 200"))
        payload[0] = 0x49
        self.assertRefused(
            self.split(bytes(payload)), chat_frame_tail.CHAT_PREFIX_UNREADABLE
        )

    def test_an_odd_wstring_length_is_unreadable(self):
        payload = bytearray(make_chat_payload("ab"))
        payload[6:10] = struct.pack("<I", 3)
        self.assertRefused(
            self.split(bytes(payload)), chat_frame_tail.CHAT_PREFIX_UNREADABLE
        )

    def test_a_length_field_past_the_end_is_unreadable(self):
        payload = bytearray(make_chat_payload("/warp 2"))
        payload[1:5] = struct.pack("<I", 0xFFFFFFFF)
        self.assertRefused(
            self.split(bytes(payload)), chat_frame_tail.CHAT_PREFIX_UNREADABLE
        )

    def test_a_payload_shorter_than_two_headers_is_unreadable(self):
        self.assertRefused(
            self.split(b"\x48\x00"), chat_frame_tail.CHAT_PREFIX_UNREADABLE
        )

    def test_a_prefix_the_strict_decoder_refuses_is_refused_here(self):
        """Headers that read, bytes that are not UTF-16LE: the decoder wins.

        A lone high surrogate passes every length rule this module checks and
        fails `decode_local_talk_payload`, which is exactly the case that
        proves the boundary is only a PROPOSAL.
        """
        lone_surrogate = b"\x00\xd8"
        prefix = (
            bytes([chat_command.WSTRING_TAG])
            + struct.pack("<I", 0)
            + bytes([chat_command.WSTRING_TAG])
            + struct.pack("<I", len(lone_surrogate))
            + lone_surrogate
        )
        with self.assertRaises(chat_command.ChatDecodeError):
            chat_command.decode_local_talk_payload(prefix)
        self.assertRefused(
            self.split(prefix + self.target_pos_vital()),
            chat_frame_tail.CHAT_PREFIX_DECODER_REFUSED,
        )

    def test_a_payload_that_is_not_bytes_is_named_not_crashed(self):
        self.assertRefused(self.split("/warp 2"), chat_frame_tail.PAYLOAD_NOT_BYTES)

    def test_a_known_vital_followed_by_an_unknown_one_still_stops_the_walk(self):
        """The only shape that tells fail-closed apart from salvage.

        pf-adversary (D4) turned the unknown-id return into
        `if length is None and ids: return TAIL_WALKED` -- a partial-walk
        salvage that hands the route a body whose frame end was never
        established -- and every test passed, because the sibling case above
        puts the unknown vital FIRST, where `ids` is still empty.
        """
        split = self.split(
            make_chat_payload("/warp 2 100 200")
            + self.target_pos_vital()
            + nested_vital(0x4321, b"\x00" * 8)
        )
        self.assertRefused(split, chat_frame_tail.TAIL_UNKNOWN_VITAL_ID)

    def test_a_declared_length_that_overshoots_the_tail_is_refused(self):
        """A declared body that runs off the end of the tail.

        !! AND THE EXPLICIT GUARD IS NOT PINNED BY IT, said plainly rather
        than implied: pf-adversary (D11) deleted `if cursor.remain() <
        length` and this case still passes, because the overshoot makes the
        next header read raise and land on the same refusal name.  The guard
        is defence in depth whose removal is behaviour-preserving today, and
        this round could not build an input that separates the two.
        """
        vital_id = self.legacy.ACTION_VITAL
        short = nested_vital(vital_id, b"\x00" * (self.table[vital_id] - 1))
        self.assertRefused(
            self.split(make_chat_payload("/warp 2") + short),
            chat_frame_tail.TAIL_TRUNCATED,
        )

    def test_more_tail_vitals_than_a_frame_may_carry_is_refused(self):
        tail = self.on_land_vital() * (vital_walk.MAX_VITALS_PER_FRAME + 1)
        self.assertRefused(
            self.split(make_chat_payload("/warp 2") + tail),
            chat_frame_tail.TAIL_TOO_MANY_VITALS,
        )

    def test_a_legacy_module_without_a_cursor_is_named(self):
        class NoCursor:
            TARGET_POS_VITAL = 0x2A90

        self.assertRefused(
            self.split(
                make_chat_payload("/warp 2") + self.target_pos_vital(),
                legacy=NoCursor(),
            ),
            chat_frame_tail.LEGACY_MODULE_MISSING_FIELDS,
        )

    def test_a_legacy_module_that_raises_is_caught_and_named(self):
        class Exploding:
            ON_LAND_VITAL = self.legacy.ON_LAND_VITAL
            TARGET_POS_VITAL = self.legacy.TARGET_POS_VITAL
            ACTION_VITAL = self.legacy.ACTION_VITAL

            @staticmethod
            def Cursor(data):
                raise RuntimeError("no cursor for you")

        self.assertRefused(
            self.split(
                make_chat_payload("/warp 2") + self.target_pos_vital(),
                legacy=Exploding(),
            ),
            chat_frame_tail.TAIL_REFUSED_TO_ANSWER,
        )


class TheRouteTests(_Case):
    """End to end, through `make_gm_chat_command_action`."""

    def test_a_gm_command_inside_a_two_vital_frame_now_produces_an_action(self):
        session = FakeSession()
        payload = make_chat_payload("/warp 2 100 200") + self.target_pos_vital()
        with self.open_the_version_gate():
            action = self.act(session, payload)
        self.assertIsNotNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_CHAT_TAIL_PREFIX}walked_1",
            session.events,
        )

    def test_the_same_frame_is_refused_when_the_split_is_taken_away(self):
        """The before picture, measured rather than asserted in prose."""
        session = FakeSession()
        payload = make_chat_payload("/warp 2 100 200") + self.target_pos_vital()
        with self.assertRaises(chat_command.ChatDecodeError):
            chat_command.decode_local_talk_payload(payload)
        with mock.patch.object(
            chat_frame_tail,
            "split_local_talk_payload",
            return_value=chat_frame_tail.ChatTailSplit(
                None, (), chat_frame_tail.CHAT_PREFIX_UNREADABLE
            ),
        ), self.open_the_version_gate():
            action = self.act(session, payload)
        self.assertIsNone(action)
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_REFUSED_PREFIX)
                and chat_command.REFUSAL_UNDECODABLE_PREFIX in event
                for event in session.events
            ),
            session.events,
        )

    def test_an_unwalkable_tail_is_refused_and_says_which_half_failed(self):
        session = FakeSession()
        payload = make_chat_payload("/warp 2 100 200") + nested_vital(
            0x4321, b"\x00" * 8
        )
        with self.open_the_version_gate():
            action = self.act(session, payload)
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_CHAT_TAIL_PREFIX}"
            f"{chat_frame_tail.TAIL_UNKNOWN_VITAL_ID}",
            session.events,
        )

    def test_a_non_gm_gains_nothing_from_wrapping_a_command_in_two_vitals(self):
        session = FakeSession(token=self.PLAYER_ACCOUNT)
        payload = make_chat_payload("/warp 2 100 200") + self.target_pos_vital()
        with self.open_the_version_gate():
            action = self.act(session, payload)
        self.assertIsNone(action)
        self.assertEqual(self.log_records(), [])
        self.assertIn(
            f"{chat_command_action.EVENT_REFUSED_PREFIX}"
            f"{chat_command.REFUSAL_NOT_GM}",
            session.events,
        )

    def test_a_non_gm_reaches_no_decode_no_event_and_no_console_line(self):
        """IDENTITY FIRST, and the whole of pf-adversary's D1.

        The first draft split before `handle_local_talk_chat`, so a
        stranger's chat line reached a UTF-16 decode, an events append and a
        stderr write -- falsifying this module's own measured sentence and
        `runtime.py`'s "a non-GM chat line produces stdout='' AND stderr=''".
        """
        session = FakeSession(token=self.PLAYER_ACCOUNT)
        payload = make_chat_payload("/warp 2 100 200") + self.target_pos_vital()
        decoded = []
        stream = io.StringIO()
        real_decode = chat_command.decode_local_talk_payload

        def spy(raw):
            decoded.append(len(raw))
            return real_decode(raw)

        with mock.patch.object(
            chat_frame_tail, "decode_local_talk_payload", spy
        ), mock.patch.object(
            chat_command, "decode_local_talk_payload", spy
        ), contextlib.redirect_stderr(
            stream
        ), self.open_the_version_gate():
            self.act(session, payload)
        self.assertEqual(decoded, [])
        self.assertEqual(self.tail_events(session), [])
        self.assertNotIn(chat_frame_tail.CHAT_TAIL_TOKEN, stream.getvalue())

    def test_the_payload_ceiling_is_still_read_before_any_split_work(self):
        """The 4096 ceiling applies to the WHOLE payload, as it did on main.

        Also pf-adversary D1: with the split first, an 8 KB payload reached
        a full decode before the ceiling that exists to prevent exactly that.
        """
        session = FakeSession()
        payload = (
            make_chat_payload("/warp 2 " + "9" * chat_command.MAX_CHAT_PAYLOAD_LENGTH)
            + self.target_pos_vital()
        )
        self.assertGreater(len(payload), chat_command.MAX_CHAT_PAYLOAD_LENGTH)
        with self.open_the_version_gate():
            action = self.act(session, payload)
        self.assertIsNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_REFUSED_PREFIX}"
            f"{chat_command.REFUSAL_PAYLOAD_TOO_LARGE}",
            session.events,
        )
        self.assertEqual(self.tail_events(session), [])

    def test_a_session_with_no_token_never_reaches_the_split(self):
        """pf-adversary D11/M8: the ordering claim, pinned.

        Moving the split above the token and payload guards left every test
        green while a pre-login session ran the whole decode, table build,
        console print and event write.
        """
        session = FakeSession(token=None)
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.open_the_version_gate():
            action = self.act(
                session, make_chat_payload("/warp 2") + self.target_pos_vital()
            )
        self.assertIsNone(action)
        self.assertEqual(self.tail_events(session), [])
        self.assertNotIn(chat_frame_tail.CHAT_TAIL_TOKEN, stream.getvalue())

    def test_a_refused_split_hands_back_the_callers_own_object(self):
        """pf-adversary D5: "the caller keeps what it had", measured.

        Returning `split.body` (None on every refusal) instead of `payload`
        on the non-quiet branch passed every test, and turned the frame's
        own named refusal into `gm_chat_action_unexpected_TypeError` -- the
        module blaming itself for the client's bytes.
        """
        session = FakeSession()
        payload = make_chat_payload("/warp 2") + nested_vital(0x4321, b"\x00" * 8)
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            handed_back = chat_command_action._isolated_chat_payload(
                session, payload, self.legacy
            )
        self.assertIs(handed_back, payload)

    def test_a_frame_with_no_tail_hands_back_the_callers_own_object(self):
        session = FakeSession()
        payload = make_chat_payload("/warp 2 100 200")
        self.assertIs(
            chat_command_action._isolated_chat_payload(
                session, payload, self.legacy
            ),
            payload,
        )

    def test_an_unwalkable_tail_keeps_the_codec_refusal_and_names_no_bug(self):
        session = FakeSession()
        payload = make_chat_payload("/warp 2 100 200") + nested_vital(
            0x4321, b"\x00" * 8
        )
        with self.open_the_version_gate():
            self.act(session, payload)
        self.assertTrue(
            any(
                event.startswith(chat_command_action.EVENT_REFUSED_PREFIX)
                and chat_command.REFUSAL_UNDECODABLE_PREFIX in event
                for event in session.events
            ),
            session.events,
        )
        self.assertFalse(
            any(
                event.startswith(chat_command_action.EVENT_UNEXPECTED_PREFIX)
                for event in session.events
            ),
            session.events,
        )

    def test_a_frame_that_decodes_never_reaches_the_split_at_all(self):
        """The strongest form of pf-adversary's D6, after D1 moved the call.

        A single-vital frame decodes on the first try, so the retry branch
        is not entered and `_isolated_chat_payload` never runs -- no latch,
        no event, no console line, and nothing for a latching mutant to do.
        Pinned on the call itself rather than on its effects, because the
        session-surface guard next door is a SUBSET assertion and cannot
        narrow the allowlist entry this round added to it.
        """
        session = FakeSession()
        with mock.patch.object(
            chat_frame_tail, "split_local_talk_payload"
        ) as never, self.open_the_version_gate():
            action = self.act(session, make_chat_payload("/warp 2 100 200"))
        self.assertIsNotNone(action)
        never.assert_not_called()
        self.assertFalse(
            hasattr(session, chat_command_action.SESSION_CHAT_TAIL_REPORTED)
        )

    def test_the_split_itself_writes_no_latch_when_there_is_no_tail(self):
        """And if it is ever called with one anyway, it still must not."""
        session = FakeSession()
        chat_command_action._isolated_chat_payload(
            session, make_chat_payload("/warp 2 100 200"), self.legacy
        )
        self.assertFalse(
            hasattr(session, chat_command_action.SESSION_CHAT_TAIL_REPORTED)
        )
        self.assertEqual(self.tail_events(session), [])

    def test_the_console_line_is_latched_to_one_per_reason_per_session(self):
        session = FakeSession()
        payload = make_chat_payload("/warp 2 100 200") + self.target_pos_vital()
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.open_the_version_gate():
            for _ in range(5):
                gm_dispatch.reset_rate_limit_state_for_tests()
                self.act(session, payload)
        lines = [
            line
            for line in stream.getvalue().splitlines()
            if line.startswith(chat_frame_tail.CHAT_TAIL_TOKEN)
        ]
        self.assertEqual(len(lines), 1, stream.getvalue())
        self.assertEqual(
            len(self.tail_events(session)), 5, session.events
        )

    def test_a_second_reason_gets_its_own_single_line(self):
        session = FakeSession()
        walked = make_chat_payload("/warp 2 100 200") + self.target_pos_vital()
        unknown = make_chat_payload("/warp 2 100 200") + nested_vital(
            0x4321, b"\x00" * 8
        )
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.open_the_version_gate():
            for payload in (walked, unknown, walked, unknown):
                gm_dispatch.reset_rate_limit_state_for_tests()
                self.act(session, payload)
        lines = [
            line
            for line in stream.getvalue().splitlines()
            if line.startswith(chat_frame_tail.CHAT_TAIL_TOKEN)
        ]
        self.assertEqual(len(lines), 2, stream.getvalue())

    def test_the_console_line_never_carries_what_was_typed(self):
        session = FakeSession()
        secret = "/warp 2 100 200"
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.open_the_version_gate():
            self.act(session, make_chat_payload(secret) + self.target_pos_vital())
        # THIS FILE'S LINES ONLY.  The command route's own token prints the
        # lane-authored command NAME beside it (`LANE_GM_CHAT_ACTION warp
        # route=action`), which is its decision and not this one's; asserting
        # over the whole stream would be this test grading a sibling module.
        printed = "\n".join(
            line
            for line in stream.getvalue().splitlines()
            if line.startswith(chat_frame_tail.CHAT_TAIL_TOKEN)
        )
        self.assertIn(chat_frame_tail.CHAT_TAIL_TOKEN, printed)
        self.assertNotIn(secret, printed)
        self.assertNotIn("warp", printed)

    def test_a_session_that_refuses_the_latch_still_gets_its_command(self):
        class NoSetattr(FakeSession):
            def __setattr__(self, name, value):
                if name == chat_command_action.SESSION_CHAT_TAIL_REPORTED:
                    raise AttributeError(name)
                object.__setattr__(self, name, value)

        session = NoSetattr()
        payload = make_chat_payload("/warp 2 100 200") + self.target_pos_vital()
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.open_the_version_gate():
            action = self.act(session, payload)
        self.assertIsNotNone(action)
        self.assertIn(
            f"{chat_command_action.EVENT_CHAT_TAIL_PREFIX}latch_unavailable",
            session.events,
        )


class SplitCeilingTests(_Case):
    """`MAX_SPLIT_PAYLOAD_LENGTH`, pinned in BOTH directions.

    pf-adversary (D3) raised the constant to ~851 MB and every test passed,
    because the oversized-input case derives its payload FROM the constant
    and is therefore oversized for any value of it.  A literal pin plus a
    re-derivation is the only shape that catches the widening direction.
    """

    def test_the_ceiling_is_the_number_it_has_always_been(self):
        self.assertEqual(chat_frame_tail.MAX_SPLIT_PAYLOAD_LENGTH, 8512)

    def test_the_ceiling_is_still_what_its_three_inputs_make_it(self):
        self.assertEqual(
            chat_frame_tail.MAX_SPLIT_PAYLOAD_LENGTH,
            chat_command.MAX_CHAT_PAYLOAD_LENGTH
            + vital_walk.MAX_VITALS_PER_FRAME * (5 + 64),
        )

    def test_no_declared_body_in_the_table_is_longer_than_the_ceiling_assumes(self):
        """The guard for the typed 64 (pf-adversary D9).

        The constant cannot read the table -- the table needs `legacy` and
        the constant is built at import -- so the day LANE-E declares a
        longer body, this fails instead of a legitimate frame quietly
        refusing as `payload_too_large_to_split`.
        """
        self.assertLessEqual(max(self.table.values()), 64)

    def test_a_payload_over_the_ceiling_is_refused(self):
        oversized = make_chat_payload(
            "x" * chat_frame_tail.MAX_SPLIT_PAYLOAD_LENGTH
        )
        split = self.split(oversized)
        self.assertEqual(split.reason, chat_frame_tail.PAYLOAD_TOO_LARGE_TO_SPLIT)
        self.assertIsNone(split.body)


class ConsoleLineTests(_Case):
    # Every field the line may carry, in order.  A test that greps the line
    # for a leaked sentence CANNOT WORK -- the chat body is UTF-16LE, so
    # `assertNotIn("password", line)` never matches `p\x00a\x00s\x00s\x00`,
    # which is how pf-adversary's D2 mutant printed the whole typed sentence
    # past the old guard.  Fixing the shape of the whole line is the only
    # guard that fires.
    LINE_PATTERN = (
        r"^LANE_GM_CHAT_TAIL reason=[a-z_]+ tail_vitals=\d+ "
        r"ids=(none|0x[0-9A-F]{4}(,0x[0-9A-F]{4})*) chat_bytes=(none|\d+) "
        r"payload_bytes=\d+ vital_count=unavailable$"
    )

    def test_the_walked_line_carries_these_fields_and_nothing_else(self):
        body = make_chat_payload("/warp 2 100 200")
        payload = body + self.target_pos_vital()
        line = chat_frame_tail.tail_console_line(
            self.split(payload), len(payload)
        )
        line.encode("ascii")
        self.assertRegex(line, self.LINE_PATTERN)
        self.assertIn(f"reason={chat_frame_tail.TAIL_WALKED}", line)
        self.assertIn("tail_vitals=1", line)
        self.assertIn("0x%04X" % self.legacy.TARGET_POS_VITAL, line)
        self.assertIn(f"chat_bytes={len(body)}", line)

    def test_the_line_cannot_carry_the_body_even_in_a_codec_it_survives(self):
        """The D2 mutant's own payload, checked the way that catches it."""
        secret = "hunter2"
        payload = make_chat_payload(secret) + self.target_pos_vital()
        line = chat_frame_tail.tail_console_line(
            self.split(payload), len(payload)
        )
        self.assertRegex(line, self.LINE_PATTERN)
        self.assertNotIn(secret, line)
        # And the UTF-16 spelling the ASCII check above would miss.
        self.assertNotIn(
            secret.encode("utf-16-le").replace(b"\x00", b"").decode("latin-1"),
            line.replace("\x00", ""),
        )

    def test_a_refusal_line_says_none_where_there_is_no_body(self):
        split = self.split(
            make_chat_payload("/warp 2") + nested_vital(0x4321, b"\x00" * 8)
        )
        line = chat_frame_tail.tail_console_line(split, 40)
        self.assertRegex(line, self.LINE_PATTERN)
        self.assertIn("chat_bytes=none", line)
        self.assertIn("ids=none", line)

    def test_the_line_never_claims_to_know_the_frames_vital_count(self):
        """pf-adversary D8: this token cannot retire the round's nonclaim.

        `parsed.vital_count` is not passed to this lane, so `tail_walked`
        cannot tell a bundled second vital from trailing bytes shaped like
        one.  The word `unavailable` is on the line so an attended round
        cannot cite it as the first capture of a multi-vital chat frame.
        """
        payload = make_chat_payload("/warp 2") + self.target_pos_vital()
        line = chat_frame_tail.tail_console_line(self.split(payload), len(payload))
        self.assertIn("vital_count=unavailable", line)


class QuietReasonTests(_Case):
    """Which refusals may reach the console, and which may never.

    The quiet set is the one that fires on ORDINARY corrupt traffic, where a
    line per frame would be an unbounded wire-driven write.  A reason moving
    out of that set is a decision, so it is pinned here rather than left to
    whoever edits the tuple.
    """

    def test_the_quiet_set_is_exactly_the_reasons_with_no_tail_evidence(self):
        self.assertEqual(
            chat_frame_tail.QUIET_REASONS,
            (
                chat_frame_tail.NO_TAIL,
                chat_frame_tail.PAYLOAD_NOT_BYTES,
                chat_frame_tail.CHAT_PREFIX_UNREADABLE,
            ),
        )

    def test_tail_walked_is_not_quiet(self):
        self.assertNotIn(chat_frame_tail.TAIL_WALKED, chat_frame_tail.QUIET_REASONS)

    def test_a_corrupt_payload_with_no_tail_prints_nothing(self):
        session = FakeSession()
        payload = bytearray(make_chat_payload("/warp 2 100 200"))
        payload[0] = 0x49
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.open_the_version_gate():
            self.act(session, bytes(payload))
        self.assertNotIn(chat_frame_tail.CHAT_TAIL_TOKEN, stream.getvalue())
        self.assertEqual(self.tail_events(session), [])


if __name__ == "__main__":
    unittest.main()
