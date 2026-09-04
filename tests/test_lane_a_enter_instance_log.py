"""The log-only NavigationEx_EnterInstanceVital (0xC723) hook: RE-227's
five-byte fixed shape, decoded without walking tags.

LANE-A, round `09:51`, for COO-DECISION 20260904_0747 item 3(a) and
COO-DECISION 20260904_0850 item 3, correcting the chief (LANE-E) letter of
round `8nh6q5`/R334 at 08:01+07 with its own 09:10+07 follow-up: this frame's
body is `12 <opaque-u16 LE> 0B 06`, and its first byte IS the tag
`lane_a_island_trigger_log`'s walker deliberately cannot step over -- so this
module decodes the fixed shape directly instead of reusing that walker.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_enter_instance_log as hooklog,
)


def _body(opaque: int, trailer: bytes = b"\x0b\x06") -> bytes:
    return b"\x12" + opaque.to_bytes(2, "little") + trailer


class DecodeOpaqueTests(unittest.TestCase):
    def test_the_shape_re_227_pinned_decodes_to_its_own_u16(self):
        for opaque in (0x0000, 0x0001, 0x1234, 0xBEEF, 0xFFFF):
            with self.subTest(opaque=hex(opaque)):
                self.assertEqual(hooklog.decode_opaque(_body(opaque)), opaque)

    def test_little_endian_is_load_bearing(self):
        # 0x1234 read big-endian would be 0x3412 -- a byte-order slip a
        # same-value round trip could never catch.
        self.assertEqual(hooklog.decode_opaque(b"\x12\x34\x12\x0b\x06"), 0x1234)
        self.assertNotEqual(hooklog.decode_opaque(b"\x12\x34\x12\x0b\x06"), 0x1234 // 0x100 + (0x1234 % 0x100) * 0x100)

    def test_wrong_length_refuses(self):
        for payload in (b"", b"\x12", b"\x12\x34\x12", b"\x12\x34\x12\x0b", b"\x12\x34\x12\x0b\x06\x00"):
            with self.subTest(payload=payload):
                self.assertIsNone(hooklog.decode_opaque(payload))

    def test_wrong_leading_tag_refuses(self):
        # This is the exact case chief's first (08:01) letter would have
        # gotten wrong by mirroring the trigger-vital walker: that walker's
        # table has no entry for 0x12 at all, so it is not a "wrong tag", it
        # is "no tag" -- here the tag is checked and rejected explicitly.
        self.assertIsNone(hooklog.decode_opaque(b"\x0f\x34\x12\x0b\x06"))

    def test_wrong_trailer_refuses(self):
        self.assertIsNone(hooklog.decode_opaque(b"\x12\x34\x12\x0b\x07"))
        self.assertIsNone(hooklog.decode_opaque(b"\x12\x34\x12\x0c\x06"))

    def test_the_confirm_bodys_own_encoder_round_trips(self):
        # Same construction the dispatch-wiring test's `_confirm_body` uses
        # (`legacy.u16tag(0x12, opaque) + legacy.u8tag(0x0B, 6)`), built here
        # from the frozen tag encoders directly so a change to either side
        # of that pairing is caught without importing the other test module.
        sys.path.insert(0, str(ROOT / "current"))
        import pf_login_game_server_v141 as legacy

        for opaque in (0, 1, 0x1234, 0xFFFF):
            body = legacy.u16tag(0x12, opaque) + legacy.u8tag(0x0B, 6)
            with self.subTest(opaque=hex(opaque)):
                self.assertEqual(body, _body(opaque))
                self.assertEqual(hooklog.decode_opaque(body), opaque)


class ConsoleLineTests(unittest.TestCase):
    def test_a_matching_payload_prints_the_raw_opaque_value(self):
        line = hooklog.console_line(_body(0x1234))
        self.assertIn("opaque=0x1234", line)
        self.assertIn("no_responder bytes_out=0", line)
        self.assertNotIn("UNPARSED", line)

    def test_the_value_is_never_named_island_scene_or_trigger_tip(self):
        # RE-227 nonclaim 3, restated by chief 09:10: the u16 is proven only
        # to be copied unchanged, never what it means.
        line = hooklog.console_line(_body(153))
        self.assertNotIn("island", line.lower())
        self.assertNotIn("scene", line.lower())
        self.assertNotIn("trigger", line.lower())

    def test_a_non_matching_payload_prints_unparsed_with_hex(self):
        line = hooklog.console_line(b"\xff\xee\xdd")
        self.assertIn("UNPARSED", line)
        self.assertIn("hex=ffeedd", line)
        self.assertIn("len=3", line)
        self.assertIn("no_responder bytes_out=0", line)

    def test_console_output_is_ascii(self):
        for payload in (_body(0x1234), b"\xff\xee\xdd", b""):
            hooklog.console_line(payload).encode("ascii")

    def test_an_unparsed_payloads_hex_is_capped_not_written_unbounded(self):
        # pf-adversary (this round): the first draft had no cap at all --
        # a 2,000,000-byte payload produced a 4,000,072-character line.
        # Same constant and reasoning as the trigger-vital sibling's own
        # `_MAX_HEX_BYTES`.
        huge = b"\xab" * 2_000_000
        line = hooklog.console_line(huge)
        self.assertLess(len(line), 1_000)
        self.assertIn(f"len={len(huge)}", line)
        self.assertIn("hex=" + ("ab" * hooklog._MAX_HEX_BYTES) + "+", line)

    def test_a_payload_no_longer_than_the_cap_is_not_marked_truncated(self):
        payload = b"\xff" * hooklog._MAX_HEX_BYTES
        line = hooklog.console_line(payload)
        self.assertIn("hex=" + ("ff" * hooklog._MAX_HEX_BYTES), line)
        self.assertNotIn("+", line)


class TheHookNeverSendsAndNeverRaisesTests(unittest.TestCase):
    def test_it_is_registered_declares_production_allowed_and_survives_discovery(self):
        points = lane_hooks.registered_points()
        self.assertIn(hooklog.POINT, points)
        self.assertGreaterEqual(points[hooklog.POINT], 1)
        self.assertIs(hooklog.production_allowed, True)
        self.assertIs(lane_hooks.module_production_allowed(hooklog.__name__), True)

    def test_the_hook_returns_none_for_every_payload_shape(self):
        for payload in (
            b"",
            b"\x12",
            b"\x12\x34\x12\x0b\x06",
            b"\xff\xff\xff",
            _body(0) + b"\x00" * 400,
        ):
            with self.subTest(payload=payload[:8]):
                self.assertIsNone(
                    hooklog._on_enter_instance(session=object(), payload=payload)
                )

    def test_a_non_bytes_payload_is_refused_loudly_not_raised(self):
        import contextlib
        import io

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = hooklog._on_enter_instance(session=object(), payload="not bytes")
        self.assertIsNone(result)
        console = stderr.getvalue()
        self.assertIn("UNPARSED", console)
        self.assertIn("bad_payload_type=str", console)

    def test_a_bytearray_and_memoryview_payload_both_decode(self):
        body = _body(0x42)
        self.assertEqual(hooklog.decode_opaque(bytes(bytearray(body))), 0x42)
        self.assertEqual(hooklog.decode_opaque(bytes(memoryview(body))), 0x42)


if __name__ == "__main__":
    unittest.main()
