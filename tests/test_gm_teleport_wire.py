"""RE-090: wire codec for ForcePos / CWarpResult / TeleportVital."""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm.teleport_wire import (
    CWARP_RESULT_VITAL_ID,
    FORCE_POS_VITAL_ID,
    TELEPORT_VITAL_ID,
    CWarpResultBody,
    ForcePosBody,
    GmTeleportWireError,
    TeleportAux,
    TeleportTarget,
    TeleportVitalBody,
    decode_cwarp_result,
    decode_force_pos,
    decode_teleport_vital,
    make_cwarp_result_frame,
    make_cwarp_result_payload,
    make_force_pos_frame,
    make_force_pos_payload,
    make_teleport_vital_frame,
    make_teleport_vital_payload,
)


class VitalIdTests(unittest.TestCase):
    def test_ids_reproduce_the_documented_v141_protocol_name_id_formula(self):
        # pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv header:
        # hash = sum((i+1)*ord(c) for i,c in enumerate(name)) & 0xFFFF
        # Reproduces the file's own TeleportVital=0x25A2 exactly, so the same
        # formula is trusted for ForcePos/CWarpResult, which that file does
        # not list.
        def name_id(name: str) -> int:
            return sum((i + 1) * ord(c) for i, c in enumerate(name)) & 0xFFFF

        self.assertEqual(name_id("TeleportVital"), 0x25A2)
        self.assertEqual(name_id("TeleportCheckVital"), 0x4477)
        self.assertEqual(name_id("ForcePos"), FORCE_POS_VITAL_ID)
        self.assertEqual(name_id("CWarpResult"), CWARP_RESULT_VITAL_ID)
        self.assertEqual(TELEPORT_VITAL_ID, 0x25A2)


class ForcePosTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_payload_is_three_tagged_floats(self):
        payload = make_force_pos_payload(self.legacy, 1.0, 2.0, 3.0)
        expected = (
            self.legacy.f32tag(1.0) + self.legacy.f32tag(2.0) + self.legacy.f32tag(3.0)
        )
        self.assertEqual(payload, expected)
        self.assertEqual(len(payload), 15)

    def test_round_trips_through_decode(self):
        payload = make_force_pos_payload(self.legacy, 11865.5, 6147.25, -3.0)
        body = decode_force_pos(payload)
        self.assertEqual(body, ForcePosBody(11865.5, 6147.25, -3.0))

    def test_frame_carries_the_force_pos_vital_id(self):
        pc, frame = make_force_pos_frame(self.legacy, 1, 1.0, 2.0, 3.0)
        expected_pc, expected_frame = self.legacy.make_runtime_vital(
            FORCE_POS_VITAL_ID, 1, make_force_pos_payload(self.legacy, 1.0, 2.0, 3.0)
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_trailing_bytes_are_rejected(self):
        payload = make_force_pos_payload(self.legacy, 1.0, 2.0, 3.0) + b"\x00"
        with self.assertRaises(GmTeleportWireError):
            decode_force_pos(payload)

    def test_wrong_tag_is_rejected(self):
        payload = bytearray(make_force_pos_payload(self.legacy, 1.0, 2.0, 3.0))
        payload[0] = 0x0B
        with self.assertRaises(GmTeleportWireError):
            decode_force_pos(bytes(payload))


class CWarpResultTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_payload_matches_pinned_tag_order(self):
        payload = make_cwarp_result_payload(self.legacy, 42, 1.0, 2.0, 3.0, 7)
        expected = (
            self.legacy.qwordtag(0x32, 42)
            + self.legacy.f32tag(1.0)
            + self.legacy.f32tag(2.0)
            + self.legacy.f32tag(3.0)
            + self.legacy.u16tag(0x12, 7)
        )
        self.assertEqual(payload, expected)

    def test_round_trips_through_decode(self):
        payload = make_cwarp_result_payload(self.legacy, 0xFFFFFFFF, 1.5, -2.5, 0.0, 3)
        body = decode_cwarp_result(payload)
        self.assertEqual(body, CWarpResultBody(0xFFFFFFFF, 1.5, -2.5, 0.0, 3))

    def test_frame_carries_the_cwarp_result_vital_id(self):
        pc, frame = make_cwarp_result_frame(self.legacy, 1, 1, 1.0, 2.0, 3.0, 4)
        expected_pc, expected_frame = self.legacy.make_runtime_vital(
            CWARP_RESULT_VITAL_ID, 1, make_cwarp_result_payload(self.legacy, 1, 1.0, 2.0, 3.0, 4)
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_rejects_out_of_range_qword(self):
        with self.assertRaises(ValueError):
            make_cwarp_result_payload(self.legacy, -1, 1.0, 2.0, 3.0, 0)
        with self.assertRaises(ValueError):
            make_cwarp_result_payload(self.legacy, 1 << 64, 1.0, 2.0, 3.0, 0)

    def test_rejects_out_of_range_u16(self):
        with self.assertRaises(ValueError):
            make_cwarp_result_payload(self.legacy, 0, 1.0, 2.0, 3.0, -1)
        with self.assertRaises(ValueError):
            make_cwarp_result_payload(self.legacy, 0, 1.0, 2.0, 3.0, 1 << 16)

    def test_truncated_is_rejected(self):
        payload = make_cwarp_result_payload(self.legacy, 1, 1.0, 2.0, 3.0, 4)
        with self.assertRaises(GmTeleportWireError):
            decode_cwarp_result(payload[:-1])

    def test_wrong_tag_is_rejected(self):
        payload = bytearray(make_cwarp_result_payload(self.legacy, 1, 1.0, 2.0, 3.0, 4))
        payload[0] = 0x14  # was 0x32 for the leading qword
        with self.assertRaises(GmTeleportWireError):
            decode_cwarp_result(bytes(payload))

    def test_trailing_bytes_are_rejected(self):
        payload = make_cwarp_result_payload(self.legacy, 1, 1.0, 2.0, 3.0, 4) + b"\x00"
        with self.assertRaises(GmTeleportWireError):
            decode_cwarp_result(payload)


class TeleportVitalTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.target = TeleportTarget(
            field_0x10=1, field_0x11=0, scene_id=3, scene_seq=0,
            x=100.0, y=200.0, z=0.0,
        )
        self.aux = TeleportAux(
            text="warp 3 100 200", field_0x2c=1, field_0x30=2, field_0x34=3,
            field_0x38=4, field_0x40=5,
        )

    def test_minimal_body_with_no_target_or_aux_round_trips(self):
        payload = make_teleport_vital_payload(self.legacy, 0, None, None, 0, 0)
        body = decode_teleport_vital(payload)
        self.assertEqual(body, TeleportVitalBody(0, None, None, 0, 0))

    def test_full_body_with_target_and_aux_round_trips(self):
        payload = make_teleport_vital_payload(
            self.legacy, 9, self.target, self.aux, 5, 300
        )
        body = decode_teleport_vital(payload)
        self.assertEqual(
            body, TeleportVitalBody(9, self.target, self.aux, 5, 300)
        )

    def test_target_only_round_trips(self):
        payload = make_teleport_vital_payload(self.legacy, 0, self.target, None, 0, 0)
        body = decode_teleport_vital(payload)
        self.assertEqual(body.target, self.target)
        self.assertIsNone(body.aux)

    def test_target_payload_matches_re090_listed_stream_order(self):
        # Independent construction (not via make_teleport_target_payload)
        # pinning RE-090's literal listing order for the target object:
        # scene_id, scene_seq, field_0x10, field_0x11, vec3 -- NOT ascending
        # object-offset order. A round-trip test alone cannot catch an
        # internally-consistent reordering bug in this function; this test
        # can, by building the expected bytes from raw legacy.xxxtag() calls
        # the same way ForcePosTests/CWarpResultTests already do.
        payload = make_teleport_vital_payload(self.legacy, 0, self.target, None, 0, 0)
        expected_target = (
            self.legacy.u16tag(0x12, self.target.scene_id)
            + self.legacy.qwordtag(0x32, self.target.scene_seq)
            + self.legacy.u8tag(0x0B, self.target.field_0x10)
            + self.legacy.u8tag(0x0B, self.target.field_0x11)
            + self.legacy.f32tag(self.target.x)
            + self.legacy.f32tag(self.target.y)
            + self.legacy.f32tag(self.target.z)
        )
        # skip: field_0x18(2) + target_presence(2)
        self.assertEqual(payload[4:4 + len(expected_target)], expected_target)

    def test_aux_field_0x40_is_written_before_field_0x38_on_the_wire(self):
        # RE-090: wire order is +0x40 then +0x38 even though the object
        # offset of +0x38 is lower -- this is the exact fact this test
        # pins, not a transcription slip.
        payload = make_teleport_vital_payload(self.legacy, 0, None, self.aux, 0, 0)
        # skip: field_0x18(2) + target_presence(2) + aux_presence(2)
        offset = 2 + 2 + 2
        # skip untagged wstring: len(4) + utf16le bytes
        str_len = len(self.aux.text.encode("utf-16-le"))
        offset += 4 + str_len
        # skip field_0x2c (u16tag, 3 bytes), field_0x30 (u32tag, 5 bytes),
        # field_0x34 (u32tag, 5 bytes)
        offset += 3 + 5 + 5
        # next byte must be the qword tag (field_0x40), not a u32 tag
        self.assertEqual(payload[offset], 0x32)

    def test_non_ascii_aux_text_survives_utf16le_round_trip(self):
        aux = TeleportAux(
            text="วาร์ปไปเกาะ", field_0x2c=0, field_0x30=0, field_0x34=0,
            field_0x38=0, field_0x40=0,
        )
        payload = make_teleport_vital_payload(self.legacy, 0, None, aux, 0, 0)
        body = decode_teleport_vital(payload)
        self.assertEqual(body.aux.text, "วาร์ปไปเกาะ")

    def test_frame_carries_the_teleport_vital_id(self):
        pc, frame = make_teleport_vital_frame(self.legacy, 1, 0, None, None, 0, 0)
        expected_pc, expected_frame = self.legacy.make_runtime_vital(
            TELEPORT_VITAL_ID, 1,
            make_teleport_vital_payload(self.legacy, 0, None, None, 0, 0),
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_target_presence_byte_other_than_one_is_still_a_presence_gate(self):
        payload = bytearray(
            make_teleport_vital_payload(self.legacy, 0, self.target, None, 0, 0)
        )
        payload[3] = 200  # target-presence byte, was 1
        body = decode_teleport_vital(bytes(payload))
        self.assertIsNotNone(body.target)

    def test_truncated_after_field_0x18_is_rejected(self):
        with self.assertRaises(GmTeleportWireError):
            decode_teleport_vital(bytes([0x0B, 0]))

    def test_trailing_bytes_after_a_clean_decode_are_rejected(self):
        payload = make_teleport_vital_payload(self.legacy, 0, None, None, 0, 0) + b"\x00"
        with self.assertRaises(GmTeleportWireError):
            decode_teleport_vital(payload)

    def test_rejects_non_bytes(self):
        with self.assertRaises(TypeError):
            decode_teleport_vital("not bytes")

    def test_aux_text_rejects_non_str(self):
        aux = TeleportAux(
            text=123, field_0x2c=0, field_0x30=0, field_0x34=0, field_0x38=0,
            field_0x40=0,
        )
        with self.assertRaises(TypeError):
            make_teleport_vital_payload(self.legacy, 0, None, aux, 0, 0)

    def test_aux_odd_declared_string_byte_length_is_rejected(self):
        payload = bytearray(
            make_teleport_vital_payload(self.legacy, 0, None, self.aux, 0, 0)
        )
        # string length prefix follows field_0x18(2) + target_presence(2)
        # + aux_presence(2)
        struct.pack_into("<I", payload, 6, 1)  # odd byte length
        with self.assertRaises(GmTeleportWireError):
            decode_teleport_vital(bytes(payload))

    def test_aux_declared_string_length_longer_than_buffer_is_rejected(self):
        payload = bytearray(
            make_teleport_vital_payload(self.legacy, 0, None, self.aux, 0, 0)
        )
        struct.pack_into("<I", payload, 6, 0xFFFFFFFE)
        with self.assertRaises(GmTeleportWireError):
            decode_teleport_vital(bytes(payload))

    def test_aux_string_with_invalid_utf16_is_rejected_not_a_crash(self):
        # A lone high surrogate is not valid UTF-16LE on its own.
        raw_string_bytes = b"\x00\xd8"
        payload = (
            self.legacy.u8tag(0x0B, 0)  # field_0x18
            + self.legacy.u8tag(0x0B, 0)  # target presence
            + self.legacy.u8tag(0x0B, 1)  # aux presence
            + struct.pack("<I", len(raw_string_bytes))
            + raw_string_bytes
            + self.legacy.u16tag(0x0F, 0)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u32tag(0x19, 0)
            + self.legacy.qwordtag(0x32, 0)
            + self.legacy.u32tag(0x19, 0)
            + self.legacy.u8tag(0x0B, 0)  # field_0x20
            + self.legacy.u16tag(0x0F, 0)  # field_0x22
        )
        with self.assertRaises(GmTeleportWireError):
            decode_teleport_vital(payload)


if __name__ == "__main__":
    unittest.main()
