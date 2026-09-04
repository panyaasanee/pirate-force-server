"""``ui_tracepath_wire.py`` -- encode/decode round-trip plus a real captured
frame check.

Mirrors ``tests/test_ui_trade_wire.py``'s own shape (synthetic round-trip,
fail-closed on truncation/trailing-bytes/wrong-tag, no-guessed-meaning
check) and adds one thing none of the ``CORE-REQUEST 1120`` sibling test
files have: a real attended capture, not just this module's own synthetic
fixtures. ``GT-246`` (``pf_bridge/GAME_TEST_QUEUE.md``, ANSWERED, R310,
2026-09-04, minimap click) captured the literal 25-byte frame below;
``CLIENT_RE_QUEUE.md``'s ``RE-236`` decoded it by hand against this exact
schema this round. Encoding that decode back through this module's own
``encode_*`` must reproduce the captured bytes exactly, and decoding the
captured bytes directly must reproduce the same eight field values --
either direction failing would mean this module's schema does not actually
match what a real client sent, not merely that it disagrees with itself.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_tracepath_wire as wire  # noqa: E402

# GT-246, R310, 2026-09-04 18:52:12 -- real minimap-click capture, not a
# fixture. CLIENT_RE_QUEUE.md's RE-236 "static bonus" section quotes this
# exact hex and this exact eight-field decode.
_GT246_CAPTURE_HEX = "0F00000F000014000000000F01000F65010FB2000F007D0802"
_GT246_FIELDS = wire.TracePathReqFields(
    field1_u16=0,
    field2_u16=0,
    field3_u32=0,
    field4_u16=1,
    field5_u16=357,
    field6_u16=178,
    field7_u16=32000,
    field8_u8=2,
)


class RealCaptureTests(unittest.TestCase):
    def test_gt246_capture_decodes_to_the_re236_field_values(self):
        payload = bytes.fromhex(_GT246_CAPTURE_HEX)
        self.assertEqual(len(payload), 25)
        decoded = wire.decode_trace_path_req_payload(payload)
        self.assertEqual(decoded, _GT246_FIELDS)

    def test_re236_field_values_encode_back_to_the_gt246_capture_byte_exact(self):
        encoded = wire.encode_trace_path_req_payload(_GT246_FIELDS)
        self.assertEqual(encoded.hex(), _GT246_CAPTURE_HEX.lower())


class RoundTripTests(unittest.TestCase):
    def test_synthetic_fields_round_trip_through_encode_then_decode(self):
        cases = (
            wire.TracePathReqFields(0, 0, 0, 0, 0, 0, 0, 0),
            wire.TracePathReqFields(
                0xFFFF, 0xFFFF, 0xFFFFFFFF, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF, 0xFF,
            ),
            wire.TracePathReqFields(743, 1, 2, 3, 4, 5, 6, 7),
        )
        for fields in cases:
            with self.subTest(fields=fields):
                payload = wire.encode_trace_path_req_payload(fields)
                self.assertEqual(
                    wire.decode_trace_path_req_payload(payload), fields
                )

    def test_encode_is_exactly_25_bytes(self):
        payload = wire.encode_trace_path_req_payload(_GT246_FIELDS)
        self.assertEqual(len(payload), 25)


class FailClosedTests(unittest.TestCase):
    def test_empty_payload_is_none(self):
        self.assertIsNone(wire.decode_trace_path_req_payload(b""))

    def test_truncated_payload_at_every_prefix_length_is_none(self):
        payload = wire.encode_trace_path_req_payload(_GT246_FIELDS)
        for cut in range(len(payload)):
            with self.subTest(cut=cut):
                self.assertIsNone(
                    wire.decode_trace_path_req_payload(payload[:cut])
                )

    def test_trailing_bytes_after_a_full_match_are_none_not_a_partial_success(self):
        payload = wire.encode_trace_path_req_payload(_GT246_FIELDS) + b"\xaa" * 5
        self.assertIsNone(wire.decode_trace_path_req_payload(payload))

    def test_wrong_tag_on_any_field_is_none(self):
        payload = bytearray(wire.encode_trace_path_req_payload(_GT246_FIELDS))
        tag_offsets = (0, 3, 6, 11, 14, 17, 20, 23)
        for offset in tag_offsets:
            with self.subTest(offset=offset):
                mutated = bytearray(payload)
                mutated[offset] = 0xEE
                self.assertIsNone(
                    wire.decode_trace_path_req_payload(bytes(mutated))
                )

    def test_garbage_never_raises(self):
        for payload in (b"\x00", b"\xff" * 3, b"\xff" * 200):
            with self.subTest(length=len(payload)):
                self.assertIsNone(wire.decode_trace_path_req_payload(payload))


class NoGuessedMeaningTests(unittest.TestCase):
    def test_field_names_are_positional_not_semantic(self):
        # RE-236 item (ข) is still open (three unproven readings for
        # field1_u16: quest id / NPC id / list index) -- this module must
        # not decide it by naming the field one of those things.
        forbidden = ("quest_id", "npc_id", "list_index", "discriminator")
        field_names = wire.TracePathReqFields.__dataclass_fields__.keys()
        for word in forbidden:
            with self.subTest(word=word):
                self.assertNotIn(word, field_names)


if __name__ == "__main__":
    unittest.main()
