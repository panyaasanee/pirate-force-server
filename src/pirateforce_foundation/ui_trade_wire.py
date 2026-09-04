"""``TradeInviteVital`` (``0x3700``) -- pure encode/decode, wire shape only.

See ``ui_social_wire.py``'s module docstring for the shared tag legend,
the "why no wire offsets" explanation, and ``ui_party_wire.py``'s
docstring for why fields are named positionally rather than by guessed
meaning. Field shape is copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv``.

NOT ``TradeCmdVital``.  This is only the ``TradeInviteVital`` class
(opcode/fields fully resolved, per ``CORE-REQUEST 1120``). ``TradeCmdVital``
(the class that would actually execute the exchange) is separately tracked --
``notes_to_chief/20260904_0621_LANE-UI-CORE-REQUEST-wire-tradecmdvital-
*.md`` -- with 14/20 fields resolved and no known-good live capture yet
(``parse_success=0`` on all eight attempted parses); it is out of scope
for this file and is not implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

TRADE_INVITE_VITAL_ID = 0x3700

# Unproven default (see ui_party_wire.py's version-byte note).
TRADE_INVITE_VITAL_VERSION = 0

_TAG_FIELD1_U8 = 0x08
_TAG_FIELD2_U64 = 0x32


@dataclass(frozen=True)
class TradeInviteFields:
    """Wire order: u8, u64, untagged wstring -- identical field shape to
    ``ui_party_wire.PartyInviteFields`` (same tags, same order), but kept
    as its own type: nothing proves the two classes share a meaning, only
    that they happen to share a shape."""

    field1_u8: int
    field2_u64: int
    field3_wstring: str


def encode_trade_invite_payload(fields: TradeInviteFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_FIELD1_U8, fields.field1_u8 & 0xFF])
    out += wire.u64tag(_TAG_FIELD2_U64, fields.field2_u64)
    out += wire.encode_untagged_wstring(fields.field3_wstring)
    return bytes(out)


def decode_trade_invite_payload(payload: bytes) -> TradeInviteFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_FIELD1_U8)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_FIELD2_U64)
        field3, offset = wire.read_untagged_wstring(payload, offset)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return TradeInviteFields(field1, field2, field3)
