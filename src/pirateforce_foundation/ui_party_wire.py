"""``PartyInviteVital`` (``0x37B1``) / ``PartyCmdVital`` (``0x2466``) --
pure encode/decode, wire shape only.

See ``ui_social_wire.py``'s module docstring for the shared tag legend and
the "why no wire offsets" explanation. Field shapes here are copied
field-for-field from ``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv``
(``PartyInviteVital``/``PartyCmdVital`` rows, both W and R directions --
the two directions share an identical field layout for both classes).

WHAT THIS FILE DOES NOT CLAIM.  Every field below has a proven wire
SHAPE (tag byte, width, order) and zero proven MEANING.
``notes_to_chief/20260904_1120_*.md`` nonclaim (2) is explicit: caller/verb semantics for all
eight classes in this batch are ``CALL_UNCLASSIFIED`` -- nobody has traced
which client code calls these, with what field values, for what game
action. Field names below are therefore positional
(``field1_u8``/``field2_u64``/...), not "sender_id" or "invite_target" or
similar -- naming a field for what it is guessed to mean, with no
evidence, is exactly what ``RE_STATIC_SEARCH_RULES.md`` and this project's
"ห้ามเดา" (do not guess) discipline forbid. A later RE ticket that traces
the caller and pins real semantics should rename these; this file does not
pre-empt that ticket by inventing names now.

Opcodes: ``notes_to_chief/20260904_1120_...md``, table row citing
``PF_VITAL_NAMES.json`` (NAMES-FOLD-002, tier PROVEN, registration-thunk
byte-match) for both classes.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

PARTY_INVITE_VITAL_ID = 0x37B1
PARTY_CMD_VITAL_ID = 0x2466

# Unproven default, same convention trace_path.py documents for itself:
# no capture has ever pinned a non-zero version byte for either class.
PARTY_INVITE_VITAL_VERSION = 0
PARTY_CMD_VITAL_VERSION = 0

_TAG_FIELD1_U8 = 0x08
_TAG_FIELD2_U64 = 0x32


@dataclass(frozen=True)
class PartyInviteFields:
    """``PartyInviteVital``'s three proven fields, in wire order."""

    field1_u8: int
    field2_u64: int
    field3_wstring: str


@dataclass(frozen=True)
class PartyCmdFields:
    """``PartyCmdVital``'s two proven fields, in wire order."""

    field1_u8: int
    field2_u64: int


def encode_party_invite_payload(fields: PartyInviteFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_FIELD1_U8, fields.field1_u8 & 0xFF])
    out += wire.u64tag(_TAG_FIELD2_U64, fields.field2_u64)
    out += wire.encode_untagged_wstring(fields.field3_wstring)
    return bytes(out)


def decode_party_invite_payload(payload: bytes) -> PartyInviteFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_FIELD1_U8)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_FIELD2_U64)
        field3, offset = wire.read_untagged_wstring(payload, offset)
    except wire.WireDecodeError:
        return None
    return PartyInviteFields(field1, field2, field3)


def encode_party_cmd_payload(fields: PartyCmdFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_FIELD1_U8, fields.field1_u8 & 0xFF])
    out += wire.u64tag(_TAG_FIELD2_U64, fields.field2_u64)
    return bytes(out)


def decode_party_cmd_payload(payload: bytes) -> PartyCmdFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_FIELD1_U8)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_FIELD2_U64)
    except wire.WireDecodeError:
        return None
    return PartyCmdFields(field1, field2)
