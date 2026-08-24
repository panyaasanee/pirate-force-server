"""Strict parser for the exact nested DeleteActorVital request record.

This module deliberately stops at the nested record boundary.  In particular, it
does not identify an outer envelope, dispatch the request, build a response, or
mutate character state.  Requiring the input to end with the declared string
payload is a host-side safety rule; it is not a claim about client codec EOF
handling.

The trailing 0x44 field is a string8 (one byte per char), not a UTF-16LE
wstring: GT-055 (STRING-CODEC-DECISION-001, 2026-08-24) decided the full wire
shape ``44 | uint32le byte_len | N raw string8 bytes`` from the GT-018 capture
(32 contiguous ASCII bytes, no interleaved NULs; corroborated by GT-010/011),
matching PF_SERIALIZER_FIELDS rows that bind this field to the
``basic_string<char>`` helpers 0x0089A6D0/0x0089A740.  The parser previously
required an even byte length under the superseded UTF-16LE reading.
"""
from dataclasses import dataclass
import struct


DELETE_ACTOR_VITAL_ID = 0x36DB
DELETE_ACTOR_VITAL_VERSION = 1


@dataclass(frozen=True)
class DeleteActorVitalRequest:
    """Exact decoded fields; the final byte string remains semantically opaque."""

    vital_id: int
    version: int
    op: int
    selector: int
    field_u32: int
    opaque_string8: bytes


class _Cursor:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.offset = 0

    def _take(self, size: int) -> bytes:
        if size < 0 or size > len(self.raw) - self.offset:
            raise ValueError("truncated DeleteActorVital nested record")
        start = self.offset
        self.offset += size
        return self.raw[start:self.offset]

    def u8(self) -> int:
        return self._take(1)[0]

    def u16le(self) -> int:
        return struct.unpack("<H", self._take(2))[0]

    def u32le(self) -> int:
        return struct.unpack("<I", self._take(4))[0]

    def expect(self, expected: int, label: str) -> None:
        if self.u8() != expected:
            raise ValueError(f"wrong {label} tag in DeleteActorVital nested record")


def parse_delete_actor_vital_request(raw: bytes) -> DeleteActorVitalRequest:
    """Parse one exact producer-backed request profile and reject trailing data.

    The ``0x44`` field contains a uint32 byte length followed by that many raw
    string8 bytes (GT-055).  The raw bytes are retained without decoding so their
    representation is lossless.  The declared length is bounded by the supplied
    input and never drives an allocation.
    """
    if type(raw) is not bytes:
        raise TypeError("DeleteActorVital nested record must be bytes")
    cursor = _Cursor(raw)

    cursor.expect(0x12, "vital ID")
    vital_id = cursor.u16le()
    if vital_id != DELETE_ACTOR_VITAL_ID:
        raise ValueError("wrong DeleteActorVital ID")

    cursor.expect(0x0B, "version")
    version = cursor.u8()
    if version != DELETE_ACTOR_VITAL_VERSION:
        raise ValueError("wrong DeleteActorVital version")

    cursor.expect(0x08, "op")
    op = cursor.u8()
    if op not in (1, 2):
        raise ValueError("unsupported DeleteActorVital request op")

    cursor.expect(0x08, "selector")
    selector = cursor.u8()

    cursor.expect(0x14, "uint32")
    field_u32 = cursor.u32le()
    if field_u32 != 0:
        raise ValueError("DeleteActorVital producer uint32 must be zero")

    cursor.expect(0x44, "string8")
    byte_length = cursor.u32le()
    opaque_string8 = cursor._take(byte_length)
    if cursor.offset != len(raw):
        raise ValueError("trailing data after DeleteActorVital nested record")
    if op == 2 and opaque_string8:
        raise ValueError("DeleteActorVital op 2 requires an empty string8 field")

    return DeleteActorVitalRequest(
        vital_id=vital_id,
        version=version,
        op=op,
        selector=selector,
        field_u32=field_u32,
        opaque_string8=opaque_string8,
    )
