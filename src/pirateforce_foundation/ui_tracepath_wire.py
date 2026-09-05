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
tests -- this frame's own field1 (the 25-byte minimap-click shape decoded
above) has only ever been observed as ``0`` (``GT-246``, and R317's two
repeat minimap clicks, ``notes_to_chief/20260905_1125_KA1A-R317-RESULTS-*
.md`` #328/#333), consistent with all three of RE-236 item (b)'s original
readings at once and ruling out none of them for THIS shape. See
``TRACE_PATH_GO_TARGET_ID_PREFIX`` below for the *separate*, longer wire
shape RE-236 item (b) actually got answered through.

ROUND `9xqzh0` ADDITION -- CTracePathVital(0x2F92) POPULATED REPLY
ENCODER, AND A NAMED-TARGET REQUEST ID EXTRACTOR (DIFFERENT FRAME, NOT THE
25-BYTE ONE ABOVE). ``RE-119`` T2/T3 (``archive/notes_to_chief_2026-08/
20260828_0424_RE-119-RESULT-*.md``) proved the *response* record's wire
shape directly from disassembly, independent of any request-field
semantics: tag ``0x08``/u8 discriminator at record order 1, three tag
``0x0F``/u16 fields at order 2-4 (the client converts these with
``cvtsi2ss`` -- signed i16 -- into the vec3 it walks to), and one tag
``0x14``/u32 at order 5 that is *always* written regardless of
discriminator value, with two more ``0x14`` fields gated strictly behind
discriminator values ``1``/``2`` only (T2's own table, "gate: always" vs
"only kind==2"/"only kind==1"). ``encode_trace_path_found_payload`` below
uses only the "always" fields -- discriminator ``0`` (a value T2 proves
takes the "no extra fields" branch, so this never has to guess what ``1``
or ``2`` mean) and the three i16 coordinate fields -- plus the ``+0x00``
u32, which RE-119 nonclaim (1) explicitly declines to name (``record+0``
is read by the client alongside the vec3, per T3 point 4, but its meaning
is not proven), so it is hardcoded to ``0`` here rather than guessed.
This is still the "payload SHAPE only" half: nothing here decides that the
server should ever call this function -- see ``trace_path.py``'s own
docstring and scope (``CORE-REQUEST-025``, and this round's follow-up,
``notes_to_chief/<CORE_REQUEST_LETTER>.md``) for the caller, which is
chief/LANE-A's to write, not this lane's (this round's letter:
``notes_to_chief/20260905_1226_LANE-UI-CORE-REQUEST-tracepath-populated-
reply-plus-gt-ticket-and-re236-closure.md``).

Separately, ``notes_to_chief/20260905_1125_KA1A-R317-RESULTS-*.md``
(``GT-251``, attended, R317) captured a THIRD, longer ``0x4391`` frame --
sent when the player double-clicks a named row (not a minimap point) in
the "find character in scene" panel and presses GO! -- that is NOT the
25-byte shape ``TracePathReqFields`` above decodes; it does not start with
that shape's first tag/byte pattern. Three attended clicks captured the
exact leading bytes ``0B 00 0F <u16 LE>`` -- literally, byte for byte, off
that letter -- immediately followed by a u16 matching the clicked target's
``gamedata/tables/CONSTDATA_TH__MOBS.tsv`` ``n_ID`` exactly, three separate
times (row 1 "Antique Store Love Millie" -> ``9D 00`` = 157, matching
``CONSTDATA_TH__MOBS.tsv:154``; "Finance Administrator Locher" -> 161,
``:158``; "Harbor Bulletin 2" -> 153, ``:151``) -- not row-ordinal (row
1/row 5/last row), which rules out a list-index reading. This closes
``CLIENT_RE_QUEUE.md``'s ``RE-236`` item (b) this round (see that file for
the full writeup, including the honest caveat that 153/157/161 also
collide with ``QUESTDATA_TH__QUEST.tsv`` ``n_ID`` at the same three values
-- exactly the same collision RE-119 T4 originally hit with 743 -- so the
close rests on the panel being NPC/object-only by construction, per R317's
own observation, not on the numeric collision test RE-236 originally
specified). ``TRACE_PATH_GO_TARGET_ID_PREFIX`` reads ONLY this proven
five-byte prefix and returns ``None`` for anything else -- it does not
attempt to decode the rest of this frame (unknown length beyond the one
45-byte capture cited in the letter, unknown remaining field shapes: the
letter's own hex for that capture ends in an approximate, non-literal
``x4`` shorthand this module refuses to turn into a guessed byte layout).
A dedicated RE ticket for the frame's full shape is left as follow-up, not
a blocker -- this feature only ever needs the one id field.
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


# --- CTracePathVital(0x2F92) populated (non-empty) reply -- see module
# docstring's "ROUND 9xqzh0 ADDITION" section for the RE-119 T2 citation
# behind every tag/order/gate value below. Kept to the "always" fields only
# (discriminator + three coordinate words + the one always-written u32) --
# no field gated behind discriminator 1/2 is ever emitted, so this never
# has to name what those two discriminator values mean.

_FOUND_RECORD_DISCRIMINATOR_TAG = 0x08
_FOUND_RECORD_DISCRIMINATOR_ALWAYS_ONLY = 0  # any value other than 1/2; see docstring
_FOUND_RECORD_COORD_TAG = 0x0F
_FOUND_RECORD_LEAD_U32_TAG = 0x14
_FOUND_RECORD_LEAD_U32_UNPROVEN_DEFAULT = 0  # RE-119 nonclaim (1): record+0's
# meaning is not proven; kept at the same neutral default this codebase uses
# for every other unproven byte (see trace_path.py's own vital_version note).
_FOUND_RESPONSE_COUNT_TAG = 0x12


def encode_trace_path_found_payload(x: int, y: int, z: int) -> bytes:
    """Build the CTracePathVital(0x2F92) populated (record count=1) reply
    payload for a single destination point -- ``x``/``y``/``z`` are the
    signed i16 coordinates RE-119 T2/T3 proved the client reads (via
    ``cvtsi2ss``) as the vec3 it walks to; out-of-range values are masked
    the same way every other ``u16tag`` caller in this project's wire
    layer already masks (two's-complement truncation to 16 bits), not
    rejected, so a caller with a value that does not fit gets a wrong
    coordinate rather than an exception on a hot path.

    Callers (chief/LANE-A's dispatch site, not this lane -- see module
    docstring): wrap this payload the same way
    ``trace_path.make_trace_path_empty_response`` wraps its own, e.g.
    ``legacy.make_runtime_vitals([(TRACE_PATH_VITAL_ID,
    TRACE_PATH_VITAL_VERSION, encode_trace_path_found_payload(x, y, z))])``.
    """

    record = bytearray()
    record += bytes([
        _FOUND_RECORD_DISCRIMINATOR_TAG,
        _FOUND_RECORD_DISCRIMINATOR_ALWAYS_ONLY & 0xFF,
    ])
    record += wire.u16tag(_FOUND_RECORD_COORD_TAG, x & 0xFFFF)
    record += wire.u16tag(_FOUND_RECORD_COORD_TAG, y & 0xFFFF)
    record += wire.u16tag(_FOUND_RECORD_COORD_TAG, z & 0xFFFF)
    record += wire.u32tag(
        _FOUND_RECORD_LEAD_U32_TAG, _FOUND_RECORD_LEAD_U32_UNPROVEN_DEFAULT
    )
    return wire.u16tag(_FOUND_RESPONSE_COUNT_TAG, 1) + bytes(record)


# --- GT-251/R317 named-target GO! request -- id extraction only (NOT a
# full decode of this frame; see module docstring for why the rest of the
# frame is deliberately left unparsed).

_GO_TARGET_LEADING_U8_TAG = 0x0B
_GO_TARGET_LEADING_U8_EXPECTED_VALUE = 0x00
_GO_TARGET_ID_U16_TAG = 0x0F


def read_trace_path_go_target_id_prefix(payload: bytes) -> int | None:
    """Extract the target id from a named-target ``CTracePathReqVital``
    (``0x4391``) GO! request -- ``notes_to_chief/20260905_1125_KA1A-R317-
    RESULTS-*.md``'s ``GT-251`` capture, byte for byte: three attended
    clicks all began ``0B 00 0F`` (tag ``0x0B``/u8 value ``0``, then tag
    ``0x0F``/u16) followed immediately by a little-endian u16 equal to the
    clicked target's ``CONSTDATA_TH__MOBS.tsv`` ``n_ID`` (157/161/153 --
    see that table's lines 154/158/151). Returns ``None`` (fail-closed,
    same convention as every ``decode_*`` above) if the payload does not
    start with exactly this five-byte prefix shape, or is too short to
    contain it -- deliberately does NOT call ``require_exhausted``, unlike
    this file's other decoders: the letter's own capture for this frame
    runs well past 5 bytes (45 B total) with a shape this module does not
    have literal, unambiguous hex for and so does not attempt to parse.
    This function only ever answers "what id, if any, is this frame
    targeting", never "is this a fully-understood frame".
    """

    try:
        leading, offset = wire.read_u8tag(
            payload, 0, _GO_TARGET_LEADING_U8_TAG
        )
        if leading != _GO_TARGET_LEADING_U8_EXPECTED_VALUE:
            return None
        target_id, _offset = wire.read_u16tag(
            payload, offset, _GO_TARGET_ID_U16_TAG
        )
    except wire.WireDecodeError:
        return None
    return target_id
