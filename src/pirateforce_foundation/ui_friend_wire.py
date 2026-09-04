"""``Community_RequestBeFriendVital`` (``0xB9E9``) /
``Community_RemoveFriendVital`` (``0x98A1``) -- pure encode/decode, wire
shape only.

See ``ui_social_wire.py``'s module docstring for the shared tag legend,
the "why no wire offsets" explanation, and ``ui_party_wire.py``'s
docstring for why fields are named positionally rather than by guessed
meaning (``CORE-REQUEST 1120`` nonclaim②: `CALL_UNCLASSIFIED` for every
class in this batch). Field shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID = 0xB9E9
COMMUNITY_REMOVE_FRIEND_VITAL_ID = 0x98A1

# Unproven default (see ui_party_wire.py's version-byte note).
COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION = 0
COMMUNITY_REMOVE_FRIEND_VITAL_VERSION = 0

_TAG_U64 = 0x32
_TAG_U8 = 0x0B


@dataclass(frozen=True)
class RequestBeFriendFields:
    """Wire order: u64, then an untagged wstring, then u8."""

    field1_u64: int
    field2_wstring: str
    field3_u8: int


@dataclass(frozen=True)
class RemoveFriendFields:
    """Wire order: u64, u64, u8."""

    field1_u64: int
    field2_u64: int
    field3_u8: int


def encode_request_be_friend_payload(fields: RequestBeFriendFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.encode_untagged_wstring(fields.field2_wstring)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_request_be_friend_payload(
    payload: bytes,
) -> RequestBeFriendFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_untagged_wstring(payload, offset)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
    except wire.WireDecodeError:
        return None
    return RequestBeFriendFields(field1, field2, field3)


def encode_remove_friend_payload(fields: RemoveFriendFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_remove_friend_payload(payload: bytes) -> RemoveFriendFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
    except wire.WireDecodeError:
        return None
    return RemoveFriendFields(field1, field2, field3)
