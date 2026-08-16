import dataclasses
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.delete_actor import (
    DELETE_ACTOR_VITAL_ID,
    DELETE_ACTOR_VITAL_VERSION,
    DeleteActorVitalRequest,
    parse_delete_actor_vital_request,
)


def nested_request(
    *,
    op: int = 1,
    selector: int = 7,
    field_u32: int = 0,
    opaque: bytes = b"",
    declared_length: int | None = None,
) -> bytes:
    size = len(opaque) if declared_length is None else declared_length
    return (
        b"\x12" + struct.pack("<H", DELETE_ACTOR_VITAL_ID)
        + b"\x0b" + bytes((DELETE_ACTOR_VITAL_VERSION,))
        + b"\x08" + bytes((op,))
        + b"\x08" + bytes((selector,))
        + b"\x14" + struct.pack("<I", field_u32)
        + b"\x44" + struct.pack("<I", size)
        + opaque
    )


class DeleteActorVitalRequestTests(unittest.TestCase):
    def test_exact_op1_non_ascii_raw_is_lossless(self):
        opaque = "กัปตัน海".encode("utf-16le")
        raw = nested_request(op=1, selector=0xA5, opaque=opaque)
        parsed = parse_delete_actor_vital_request(raw)
        self.assertEqual(parsed, DeleteActorVitalRequest(
            vital_id=0x36DB,
            version=1,
            op=1,
            selector=0xA5,
            field_u32=0,
            opaque_utf16le=opaque,
        ))
        self.assertEqual(parsed.opaque_utf16le, raw[-len(opaque):])

    def test_exact_op2_empty_profile(self):
        parsed = parse_delete_actor_vital_request(nested_request(op=2, selector=0))
        self.assertEqual(parsed.op, 2)
        self.assertEqual(parsed.selector, 0)
        self.assertEqual(parsed.opaque_utf16le, b"")

    def test_schema_fields_are_exact(self):
        self.assertEqual(
            [field.name for field in dataclasses.fields(DeleteActorVitalRequest)],
            [
                "vital_id", "version", "op", "selector", "field_u32",
                "opaque_utf16le",
            ],
        )

    def test_rejects_wrong_id_version_and_each_tag(self):
        raw = nested_request()
        mutations = (
            (0, 0x13),
            (1, 0xDC),
            (3, 0x0C),
            (4, 2),
            (5, 0x09),
            (7, 0x09),
            (9, 0x15),
            (14, 0x48),
        )
        for offset, value in mutations:
            with self.subTest(offset=offset, value=value):
                altered = bytearray(raw)
                altered[offset] = value
                with self.assertRaises(ValueError):
                    parse_delete_actor_vital_request(bytes(altered))

    def test_rejects_wrong_op_u32_and_nonempty_op2(self):
        for raw in (
            nested_request(op=0),
            nested_request(op=3),
            nested_request(field_u32=1),
            nested_request(op=2, opaque=b"A\x00"),
        ):
            with self.subTest(raw=raw.hex()):
                with self.assertRaises(ValueError):
                    parse_delete_actor_vital_request(raw)

    def test_rejects_odd_truncated_and_declared_length_mismatch(self):
        cases = (
            nested_request(opaque=b"A", declared_length=1),
            nested_request(opaque=b"A\x00", declared_length=4),
            nested_request(opaque=b"A\x00B\x00", declared_length=2),
        )
        for raw in cases:
            with self.subTest(raw=raw.hex()):
                with self.assertRaises(ValueError):
                    parse_delete_actor_vital_request(raw)
        valid = nested_request(opaque=b"A\x00")
        for end in range(len(valid)):
            with self.subTest(truncated_at=end):
                with self.assertRaises(ValueError):
                    parse_delete_actor_vital_request(valid[:end])

    def test_rejects_trailing_data_and_non_bytes(self):
        with self.assertRaises(ValueError):
            parse_delete_actor_vital_request(nested_request() + b"\x00")
        with self.assertRaises(TypeError):
            parse_delete_actor_vital_request(bytearray(nested_request()))


if __name__ == "__main__":
    unittest.main()
