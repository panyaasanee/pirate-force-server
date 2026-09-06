"""``Community_SendMailVital`` (``0x6E12``) /
``Community_GetMailContentVital`` (``0xAF60``) /
``Community_DeleteMailVital`` (``0x8183``) -- pure encode/decode, wire
shape only.

See ``ui_social_wire.py``'s module docstring for the shared tag legend,
the "why no wire offsets" explanation, and ``ui_party_wire.py``'s
docstring for why fields are named positionally rather than by guessed
meaning (``CORE-REQUEST 1120`` nonclaim (2): `CALL_UNCLASSIFIED` for every
class in this batch -- ``Community_SendMailVital`` has five wstring
fields in a row and it would be easy to guess "recipient/subject/body"
etc., but nothing in the registry or any capture proves which is which,
so none of that guessing happens here). Field shapes are copied
field-for-field from ``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv``.

MIGRATED round `rqwwp8` (`COO-DECISION 20260906_1745` item 2) off
``ui_social_wire.py``'s ``encode_untagged_wstring``/``read_untagged_wstring``
(proven wrong, tag byte ``0x48`` missing) onto ``wstring_tag``/
``read_wstring_tag`` for all seven wstring fields in this file (six in
``SendMailFields``, one in ``GetMailContentFields``). ``runtime.py`` imports
``COMMUNITY_SEND_MAIL_VITAL_ID``/``COMMUNITY_GET_MAIL_CONTENT_VITAL_ID``/
``COMMUNITY_DELETE_MAIL_VITAL_ID`` and dispatches real inbound frames to
``lane_hooks/lane_ui_mail_wire_log.py`` (``production_allowed = True``,
report-only, ``bytes_out=0``) -- before this fix, every real
``Community_SendMailVital``/``Community_GetMailContentVital`` frame shaped
per the proven-correct tag was silently failing to decode (falling back to
an ``UNPARSED`` hex dump), same defect class as ``ui_friend_wire.py``'s
``RequestBeFriendFields`` (round `4u0ncx`, `pirate-force-server#934`).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

COMMUNITY_SEND_MAIL_VITAL_ID = 0x6E12
COMMUNITY_GET_MAIL_CONTENT_VITAL_ID = 0xAF60
COMMUNITY_DELETE_MAIL_VITAL_ID = 0x8183

# Unproven default (see ui_party_wire.py's version-byte note).
COMMUNITY_SEND_MAIL_VITAL_VERSION = 0
COMMUNITY_GET_MAIL_CONTENT_VITAL_VERSION = 0
COMMUNITY_DELETE_MAIL_VITAL_VERSION = 0

_TAG_U64 = 0x32
_TAG_U8 = 0x0B


@dataclass(frozen=True)
class SendMailFields:
    """Wire order: u64, wstring, u64, wstring, wstring, wstring, wstring,
    wstring, u8 -- nine fields, matching the registry's 9-field W/R rows."""

    field1_u64: int
    field2_wstring: str
    field3_u64: int
    field4_wstring: str
    field5_wstring: str
    field6_wstring: str
    field7_wstring: str
    field8_wstring: str
    field9_u8: int


@dataclass(frozen=True)
class GetMailContentFields:
    """Wire order: u64, u64, u8, wstring."""

    field1_u64: int
    field2_u64: int
    field3_u8: int
    field4_wstring: str


@dataclass(frozen=True)
class DeleteMailFields:
    """Wire order: u64, u64, u8."""

    field1_u64: int
    field2_u64: int
    field3_u8: int


def encode_send_mail_payload(fields: SendMailFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.wstring_tag(fields.field2_wstring)
    out += wire.u64tag(_TAG_U64, fields.field3_u64)
    out += wire.wstring_tag(fields.field4_wstring)
    out += wire.wstring_tag(fields.field5_wstring)
    out += wire.wstring_tag(fields.field6_wstring)
    out += wire.wstring_tag(fields.field7_wstring)
    out += wire.wstring_tag(fields.field8_wstring)
    out += bytes([_TAG_U8, fields.field9_u8 & 0xFF])
    return bytes(out)


def decode_send_mail_payload(payload: bytes) -> SendMailFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_wstring_tag(payload, offset)
        f3, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f4, offset = wire.read_wstring_tag(payload, offset)
        f5, offset = wire.read_wstring_tag(payload, offset)
        f6, offset = wire.read_wstring_tag(payload, offset)
        f7, offset = wire.read_wstring_tag(payload, offset)
        f8, offset = wire.read_wstring_tag(payload, offset)
        f9, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return SendMailFields(f1, f2, f3, f4, f5, f6, f7, f8, f9)


def encode_get_mail_content_payload(fields: GetMailContentFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += wire.wstring_tag(fields.field4_wstring)
    return bytes(out)


def decode_get_mail_content_payload(
    payload: bytes,
) -> GetMailContentFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        f4, offset = wire.read_wstring_tag(payload, offset)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return GetMailContentFields(f1, f2, f3, f4)


def encode_delete_mail_payload(fields: DeleteMailFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_delete_mail_payload(payload: bytes) -> DeleteMailFields | None:
    try:
        f1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        f2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        f3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return DeleteMailFields(f1, f2, f3)
