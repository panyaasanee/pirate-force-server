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
        opaque = "กัปตัน海".encode("utf-8")
        raw = nested_request(op=1, selector=0xA5, opaque=opaque)
        parsed = parse_delete_actor_vital_request(raw)
        self.assertEqual(parsed, DeleteActorVitalRequest(
            vital_id=0x36DB,
            version=1,
            op=1,
            selector=0xA5,
            field_u32=0,
            opaque_string8=opaque,
        ))
        self.assertEqual(parsed.opaque_string8, raw[-len(opaque):])

    def test_exact_op1_natural_capture_token(self):
        # The first natural 0x36DB (GT-010/GT-018) carried 32 contiguous ASCII
        # bytes with no interleaved NULs -- the byte shape GT-055 used to decide
        # the field is string8, not UTF-16LE.
        opaque = b"7D014E541AFAA43267CA80BCCBC3FD6B"
        parsed = parse_delete_actor_vital_request(
            nested_request(op=1, selector=0, opaque=opaque)
        )
        self.assertEqual(parsed.opaque_string8, opaque)

    def test_exact_op1_odd_byte_length_is_accepted(self):
        # string8 payloads may be any byte length; the superseded UTF-16LE
        # reading wrongly rejected odd lengths (GT-055).
        parsed = parse_delete_actor_vital_request(
            nested_request(op=1, selector=1, opaque=b"ABC")
        )
        self.assertEqual(parsed.opaque_string8, b"ABC")

    def test_exact_op2_empty_profile(self):
        parsed = parse_delete_actor_vital_request(nested_request(op=2, selector=0))
        self.assertEqual(parsed.op, 2)
        self.assertEqual(parsed.selector, 0)
        self.assertEqual(parsed.opaque_string8, b"")

    def test_schema_fields_are_exact(self):
        self.assertEqual(
            [field.name for field in dataclasses.fields(DeleteActorVitalRequest)],
            [
                "vital_id", "version", "op", "selector", "field_u32",
                "opaque_string8",
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

    def test_rejects_truncated_and_declared_length_mismatch(self):
        cases = (
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
