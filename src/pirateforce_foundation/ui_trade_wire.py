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
    """Wire order: u8, u64, tagged wstring (tag ``0x48``) -- identical field
    shape to ``ui_party_wire.PartyInviteFields`` (same tags, same order),
    but kept as its own type: nothing proves the two classes share a
    meaning, only that they happen to share a shape.

    MIGRATED round `rqwwp8` (`COO-DECISION 20260906_1745` item 2): field3
    moved off ``ui_social_wire.py``'s ``encode_untagged_wstring``/
    ``read_untagged_wstring`` (proven wrong, tag byte ``0x48`` missing) onto
    ``wstring_tag``/``read_wstring_tag``. ``runtime.py`` imports
    ``TRADE_INVITE_VITAL_ID`` and dispatches real inbound frames to
    ``lane_hooks/lane_ui_trade_wire_log.py`` (``production_allowed = True``,
    report-only, ``bytes_out=0``) -- before this fix every real
    ``TradeInviteVital`` frame shaped per the proven-correct tag was
    silently failing to decode (falling back to an ``UNPARSED`` hex dump),
    same defect class as ``ui_friend_wire.py``'s ``RequestBeFriendFields``
    (round `4u0ncx`, `pirate-force-server#934`)."""

    field1_u8: int
    field2_u64: int
    field3_wstring: str


def encode_trade_invite_payload(fields: TradeInviteFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_FIELD1_U8, fields.field1_u8 & 0xFF])
    out += wire.u64tag(_TAG_FIELD2_U64, fields.field2_u64)
    out += wire.wstring_tag(fields.field3_wstring)
    return bytes(out)


def decode_trade_invite_payload(payload: bytes) -> TradeInviteFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_FIELD1_U8)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_FIELD2_U64)
        field3, offset = wire.read_wstring_tag(payload, offset)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return TradeInviteFields(field1, field2, field3)
