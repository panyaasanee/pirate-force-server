"""``CTracePathReqVital`` (``0x4391``) -- pure encode/decode, wire shape only.

See ``ui_social_wire.py``'s module docstring for the shared tag legend, the
"why no wire offsets" explanation, and ``ui_party_wire.py``'s docstring for
why fields are named positionally rather than by guessed meaning. Field
shape is copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv:5521-5528`` (``W`` direction;
``:5529-5536`` repeats the identical eight tags/offsets for ``R``, so one
encode/decode pair covers both directions the same way ``ui_trade_wire.py``
covers ``TradeInviteVital`` with one pair).

WHY THIS MODULE EXISTS NOW, NOT AS PART OF ``trace_path.py``. This class is
not new to the project: ``trace_path.py`` (LANE-A/chief-owned,
CORE-REQUEST-025) already decodes the *opcode* (``nested_id ==
TRACE_PATH_REQ_VITAL_ID``) and replies with a fixed empty-vector
``CTracePathVital``, ending the client's "finding path..." stall -- see
that file's own docstring. What it does NOT do, on ``main`` today, is read
a single byte of the REQUEST payload: the branch at ``runtime.py:7487``
matches on ``nested_id`` alone and never touches ``payload`` fields at all,
by design (``RE-119`` T4 forbids using the request's own discriminator
field, or any guessed record layout, to build a populated response --
CORE-REQUEST-025's letter scopes that file to the empty-vector fallback
only). This module is the payload SHAPE only -- it composes and parses the
eight fields without claiming any of them, leaving ``trace_path.py``'s own
scope (and its own owner) untouched. It does not send a byte anywhere:
nothing in ``runtime.py`` imports this module (see ``notes_to_chief/
20260905_0347_LANE-UI-CORE-REQUEST-*.md`` for the one dispatch-table row
that would change that, mirroring ``_FRIEND_MAIL_PARTY_TRADE_DISPATCH``'s
own shape in ``runtime.py``).

WHAT THIS MODULE PROVES, AND HOW. ``CLIENT_RE_QUEUE.md``'s ``RE-236``
(LANE-UI, this project's own ticket) decoded ``GT-246``'s real captured
25-byte frame (attended, R310, 2026-09-04, boot ``7e14bde1``-family, minimap
click) by hand against this exact schema and got a clean 8-for-8 field
match with zero trailing bytes: ``+0x14=0 +0x16=0 +0x18=0 +0x1C=1 +0x1E=357
+0x20=178 +0x22=32000 +0x24=2``. ``tests/test_ui_tracepath_wire.py``
encodes that literal capture through this module's own ``encode_*`` and
decodes it back through ``decode_*`` -- a stronger check than a synthetic
round-trip, because it is checked against bytes a real client actually put
on the wire, not merely against this module's own inverse.

WHAT THIS MODULE DOES NOT CLAIM (inherits ``RE-119``/``RE-236``'s own
nonclaims rather than overriding them). Field 1 (``+0x14``, the u16 this
project has been calling "the discriminator") is NOT named
``quest_id``/``npc_id``/``list_index`` here, or anywhere in this file's
tests -- ``RE-236`` item (b) is still open, exactly as open as it was
before this round: this module does not narrow it, decide it, or guess at
it, and the single captured value it has ever seen (``0``) is a no-target
minimap click, which is consistent with all three unproven readings at
once and rules out none of them. Nor does encoding a populated (non-empty)
request/response pair here imply the server may ever COMPOSE one -- RE-119
T4's prohibition binds ``trace_path.py``, not this file, but this file
still does not attempt to give any of the eight fields a name that would
read as a decided meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

TRACE_PATH_REQ_VITAL_ID = 0x4391

# Unproven default (see ui_party_wire.py's version-byte note); this file
# does not compose a real frame (no vital_version byte is on the wire this
# module touches -- see the module docstring's "PURE ENCODE/DECODE" line),
# kept only so a future caller has the same convention every ui_*.py file
# already follows.
TRACE_PATH_REQ_VITAL_VERSION = 0

_TAG_FIELD1_U16 = 0x0F
_TAG_FIELD2_U16 = 0x0F
_TAG_FIELD3_U32 = 0x14
_TAG_FIELD4_U16 = 0x0F
_TAG_FIELD5_U16 = 0x0F
_TAG_FIELD6_U16 = 0x0F
_TAG_FIELD7_U16 = 0x0F
_TAG_FIELD8_U8 = 0x08


@dataclass(frozen=True)
class TracePathReqFields:
    """Wire order: six u16-with-tag-0x0F fields (fields 1/2/4/5/6/7) and
    one u32-with-tag-0x14 (field 3) sandwiched between them, then one
    u8-with-tag-0x08 (field 8) -- exactly ``PF_SERIALIZER_FIELDS.tsv``'s own
    field order, ``+0x14`` through ``+0x24``. Field 1 is the field this
    project's open ``RE-236`` item (b) calls "the discriminator"; it keeps
    its positional name here (see module docstring) rather than one of the
    three unproven readings that ticket is still choosing between."""

    field1_u16: int
    field2_u16: int
    field3_u32: int
    field4_u16: int
    field5_u16: int
    field6_u16: int
    field7_u16: int
    field8_u8: int


def encode_trace_path_req_payload(fields: TracePathReqFields) -> bytes:
    out = bytearray()
    out += wire.u16tag(_TAG_FIELD1_U16, fields.field1_u16)
    out += wire.u16tag(_TAG_FIELD2_U16, fields.field2_u16)
    out += wire.u32tag(_TAG_FIELD3_U32, fields.field3_u32)
    out += wire.u16tag(_TAG_FIELD4_U16, fields.field4_u16)
    out += wire.u16tag(_TAG_FIELD5_U16, fields.field5_u16)
    out += wire.u16tag(_TAG_FIELD6_U16, fields.field6_u16)
    out += wire.u16tag(_TAG_FIELD7_U16, fields.field7_u16)
    out += bytes([_TAG_FIELD8_U8, fields.field8_u8 & 0xFF])
    return bytes(out)


def decode_trace_path_req_payload(payload: bytes) -> TracePathReqFields | None:
    try:
        field1, offset = wire.read_u16tag(payload, 0, _TAG_FIELD1_U16)
        field2, offset = wire.read_u16tag(payload, offset, _TAG_FIELD2_U16)
        field3, offset = wire.read_u32tag(payload, offset, _TAG_FIELD3_U32)
        field4, offset = wire.read_u16tag(payload, offset, _TAG_FIELD4_U16)
        field5, offset = wire.read_u16tag(payload, offset, _TAG_FIELD5_U16)
        field6, offset = wire.read_u16tag(payload, offset, _TAG_FIELD6_U16)
        field7, offset = wire.read_u16tag(payload, offset, _TAG_FIELD7_U16)
        field8, offset = wire.read_u8tag(payload, offset, _TAG_FIELD8_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return TracePathReqFields(
        field1, field2, field3, field4, field5, field6, field7, field8,
    )
