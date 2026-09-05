"""``Gathering_StartGatheringVital`` (``0xAFF7``) /
``Gathering_GatheringResultVital`` (``0xBD8E``) -- pure encode/decode,
wire shape only.

See ``ui_social_wire.py``'s module docstring for the shared tag legend, the
"why no wire offsets" explanation, and ``ui_party_wire.py``'s docstring for
why fields are named positionally rather than by guessed meaning. Field
shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv:4315-4322`` (``StartGathering``,
``W``/``R`` identical) and ``:4323-4334`` (``GatheringResult``, ``W``/``R``
identical) -- both classes are fully tagged (every field row has a real tag
byte, no ``CALL_UNCLASSIFIED`` entries), unlike this catalog group's third
class, ``Gathering_UpdateSceneGatheringPointVital`` (``0x4966``), whose rows
mix real tags with unresolved entries per direction (14 rows total, of
which 10 are ``CALL_UNCLASSIFIED``/``PE_IMPORT_*``/atomic-helper entries
and 4 are real ``0x12`` tags) and are therefore NOT implemented here
(pf-adversary, round ``c585y5``: flagged the prior draft's "fourteen" as
overstating the unclassified-only count).

Grepped first, per ``AGENTS.md`` section 7's mandatory search: no hit for
``Gathering_`` in ``CLIENT_RE_QUEUE.md`` or ``GAME_TEST_QUEUE.md``. The only
hits elsewhere are the static census/registry files themselves
(``notes_to_chief/reference_codex_attr/PF_PROTOCOL_REGISTRY.tsv``,
``PF_FIELD_VALIDATION.tsv``, ``PF_PROTOCOL_PRIORITY.tsv``/``.md``,
``PF_V2_P1_OPEN.tsv``..``PF_V5_P1_OPEN.tsv``, ``PF_DUMP_REQUEST.md``) -- no
open RE/GT ticket and no prior wire module in ``src/``/``tests/`` for this
class family (also checked ``archive/``: no hit).
``external/PF_FIELD_VALIDATION.tsv`` shows ``status=NOT_OBSERVED``,
``observed_frames=0`` for both ``W`` and ``R`` on both classes -- same as
``TreasureHunt``'s two classes above -- so nothing below claims which side
sends which class, or that either acks the other; that would be an
unlabeled guess by analogy to the (separately, actually proven)
``LogoutVital`` ack pattern, which this row does not make.

Tag widths used below are each independently confirmed elsewhere in this
project, not invented here (same legend already used by
``ui_treasurehunt_wire.py``): ``0x12`` = u16, ``0x19`` = u32, ``0x0B`` = u8,
``0x08`` = u8 (a second flavour, ``ui_social_wire.py``'s own tag legend),
``0x14`` = u32 (``ui_social_wire.u32tag``'s own docstring, via
``ui_tracepath_wire.py``).

Same scope line as every sibling module in this batch (``CORE-REQUEST
1120``'s own words): "รับเฟรม (decode) + ตอบ ack/error frame ที่วางเปล่า ...
ไม่ใช่การทำ business logic เต็ม". Nothing here claims what these fields MEAN
(gathering point id / item roll / yield count, etc.) or composes a real
ack/result frame -- the registry's ``proven_semantics`` column is
``UNKNOWN`` for every row of both classes. Not wired into ``runtime.py`` or
``vital_walk.py``; wiring either class is a separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

GATHERING_START_GATHERING_VITAL_ID = 0xAFF7
GATHERING_GATHERING_RESULT_VITAL_ID = 0xBD8E

# Unproven default (see ui_party_wire.py's version-byte note).
GATHERING_START_GATHERING_VITAL_VERSION = 0
GATHERING_GATHERING_RESULT_VITAL_VERSION = 0

_TAG_U8_A = 0x0B
_TAG_U8_B = 0x08
_TAG_U16 = 0x12
_TAG_U32_A = 0x19
_TAG_U32_B = 0x14


@dataclass(frozen=True)
class StartGatheringFields:
    """Wire order: u16, u32, u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4315-4322``)."""

    field1_u16: int
    field2_u32: int
    field3_u8: int
    field4_u8: int


@dataclass(frozen=True)
class GatheringResultFields:
    """Wire order: u8, u16, u32, u8, u8, u32 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4323-4334``)."""

    field1_u8: int
    field2_u16: int
    field3_u32: int
    field4_u8: int
    field5_u8: int
    field6_u32: int


def encode_start_gathering_payload(fields: StartGatheringFields) -> bytes:
    out = bytearray()
    out += wire.u16tag(_TAG_U16, fields.field1_u16)
    out += wire.u32tag(_TAG_U32_A, fields.field2_u32)
    out += bytes([_TAG_U8_A, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8_A, fields.field4_u8 & 0xFF])
    return bytes(out)


def decode_start_gathering_payload(
    payload: bytes,
) -> StartGatheringFields | None:
    try:
        field1, offset = wire.read_u16tag(payload, 0, _TAG_U16)
        field2, offset = wire.read_u32tag(payload, offset, _TAG_U32_A)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return StartGatheringFields(field1, field2, field3, field4)


def encode_gathering_result_payload(fields: GatheringResultFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8_A, fields.field1_u8 & 0xFF])
    out += wire.u16tag(_TAG_U16, fields.field2_u16)
    out += wire.u32tag(_TAG_U32_A, fields.field3_u32)
    out += bytes([_TAG_U8_B, fields.field4_u8 & 0xFF])
    out += bytes([_TAG_U8_B, fields.field5_u8 & 0xFF])
    out += wire.u32tag(_TAG_U32_B, fields.field6_u32)
    return bytes(out)


def decode_gathering_result_payload(
    payload: bytes,
) -> GatheringResultFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8_A)
        field2, offset = wire.read_u16tag(payload, offset, _TAG_U16)
        field3, offset = wire.read_u32tag(payload, offset, _TAG_U32_A)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8_B)
        field5, offset = wire.read_u8tag(payload, offset, _TAG_U8_B)
        field6, offset = wire.read_u32tag(payload, offset, _TAG_U32_B)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return GatheringResultFields(field1, field2, field3, field4, field5, field6)
