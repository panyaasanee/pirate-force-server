"""``TreasureHunt_StartExcavatingVital`` (``0xE40B``) /
``TreasureHunt_ExcavatingResultVital`` (``0xF33F``) -- pure encode/decode,
wire shape only.

See ``ui_social_wire.py``'s module docstring for the shared tag legend, the
"why no wire offsets" explanation, and ``ui_party_wire.py``'s docstring for
why fields are named positionally rather than by guessed meaning. Field
shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv:6341-6350`` (``StartExcavating``,
``W``/``R`` identical) and ``:6351-6360`` (``ExcavatingResult``, ``W``/``R``
identical) -- both classes are fully tagged (every field row has a real tag
byte, no ``CALL_UNCLASSIFIED`` entries), unlike this catalog group's third
class, ``TreasureHunt_UpdateSceneTreasurePointVital`` (``0x6D75``), whose
rows mix real tags with ten ``CALL_UNCLASSIFIED``/``PE_IMPORT_*`` entries
per direction and are therefore NOT implemented here.

Grepped first, per ``AGENTS.md`` section 7's mandatory search: no hit for
``TreasureHunt`` in ``CLIENT_RE_QUEUE.md`` or ``GAME_TEST_QUEUE.md``. Hits
elsewhere are all about a different, unrelated class family
(``ActorTreasureHuntExcavatingInfoAttr``/a ``TreasurePointAttr``) rejected
as a false lead in a separate ground-drop-transport investigation, not
about either wire class implemented here: ``notes_to_chief/reference_codex_
attr/`` (static census files), ``notes_to_chief/reference_codex_audit/
Pirate_Force_Codex_Audit_Recommendations.md``, ``notes_to_chief/consumed/
20260831_2329_CODEX-CHECKPOINT-P06-DROP-TRANSPORT.md``, and the matching
``archive/`` copy of that same checkpoint. This catalog group has no open
RE/GT ticket and no prior wire module in ``src/``.

Tag widths used below are each independently confirmed elsewhere in this
project, not invented here: ``0x12`` = u16 (``CLIENT_RE_QUEUE.md:54``,
"``0x12``=uint16"), ``0x19`` = u32 (``GAME_TEST_QUEUE.md:9918``,
"``ActorAttr`` class (``u32tag 0x19``)"), ``0x0F`` = u16 and ``0x14`` = u32
(both already in ``ui_social_wire.u16tag``/``u32tag``'s own docstrings, via
``ui_tracepath_wire.py``), ``0x0B`` = u8 and ``0x32`` = u64 (``ui_social_
wire.py``'s own tag legend).

Same scope line as every sibling module in this batch (``CORE-REQUEST
1120``'s own words): "รับเฟรม (decode) + ตอบ ack/error frame ที่วางเปล่า ...
ไม่ใช่การทำ business logic เต็ม". Nothing here claims what these fields MEAN
(dig site id / roll seed / loot table index, etc.) or composes a real
ack/result frame -- the registry's ``proven_semantics`` column is
``UNKNOWN`` for every row of both classes. Not wired into ``runtime.py`` or
``vital_walk.py``; wiring either class is a separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

TREASUREHUNT_START_EXCAVATING_VITAL_ID = 0xE40B
TREASUREHUNT_EXCAVATING_RESULT_VITAL_ID = 0xF33F

# Unproven default (see ui_party_wire.py's version-byte note).
TREASUREHUNT_START_EXCAVATING_VITAL_VERSION = 0
TREASUREHUNT_EXCAVATING_RESULT_VITAL_VERSION = 0

_TAG_U8 = 0x0B
_TAG_U16_A = 0x12
_TAG_U16_B = 0x0F
_TAG_U32_A = 0x19
_TAG_U32_B = 0x14
_TAG_U64 = 0x32


@dataclass(frozen=True)
class StartExcavatingFields:
    """Wire order: u16, u32, u8, u64, u64 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:6341-6350``)."""

    field1_u16: int
    field2_u32: int
    field3_u8: int
    field4_u64: int
    field5_u64: int


@dataclass(frozen=True)
class ExcavatingResultFields:
    """Wire order: u8, u16, u32, u16, u32 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:6351-6360``)."""

    field1_u8: int
    field2_u16: int
    field3_u32: int
    field4_u16: int
    field5_u32: int


def encode_start_excavating_payload(fields: StartExcavatingFields) -> bytes:
    out = bytearray()
    out += wire.u16tag(_TAG_U16_A, fields.field1_u16)
    out += wire.u32tag(_TAG_U32_A, fields.field2_u32)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += wire.u64tag(_TAG_U64, fields.field4_u64)
    out += wire.u64tag(_TAG_U64, fields.field5_u64)
    return bytes(out)


def decode_start_excavating_payload(
    payload: bytes,
) -> StartExcavatingFields | None:
    try:
        field1, offset = wire.read_u16tag(payload, 0, _TAG_U16_A)
        field2, offset = wire.read_u32tag(payload, offset, _TAG_U32_A)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field4, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field5, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return StartExcavatingFields(field1, field2, field3, field4, field5)


def encode_excavating_result_payload(fields: ExcavatingResultFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += wire.u16tag(_TAG_U16_A, fields.field2_u16)
    out += wire.u32tag(_TAG_U32_A, fields.field3_u32)
    out += wire.u16tag(_TAG_U16_B, fields.field4_u16)
    out += wire.u32tag(_TAG_U32_B, fields.field5_u32)
    return bytes(out)


def decode_excavating_result_payload(
    payload: bytes,
) -> ExcavatingResultFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u16tag(payload, offset, _TAG_U16_A)
        field3, offset = wire.read_u32tag(payload, offset, _TAG_U32_A)
        field4, offset = wire.read_u16tag(payload, offset, _TAG_U16_B)
        field5, offset = wire.read_u32tag(payload, offset, _TAG_U32_B)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ExcavatingResultFields(field1, field2, field3, field4, field5)
