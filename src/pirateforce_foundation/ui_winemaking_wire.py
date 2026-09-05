"""``Winemaking_LearnFomulaVital`` (``0x972E``) /
``Winemaking_StartWinemakingVital`` (``0xC8EB``) /
``Winemaking_FinishWinemakingVital`` (``0xD4D1``) -- pure encode/decode,
wire shape only.

See ``ui_social_wire.py``'s module docstring for the shared tag legend, the
"why no wire offsets" explanation, and ``ui_party_wire.py``'s docstring for
why fields are named positionally rather than by guessed meaning. Field
shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv:4577-4580`` (``LearnFomula``,
``W``/``R`` identical), ``:4545-4552`` (``StartWinemaking``, ``W``/``R``
identical), and ``:4553-4562`` (``FinishWinemaking``, ``W``/``R``
identical) -- all three classes are fully tagged (every field row has a
real tag byte, no ``CALL_UNCLASSIFIED``/``PE_IMPORT_*`` entries), unlike
this catalog group's other two classes,
``Winemaking_UpdateLearnedFormulaVital`` and
``Winemaking_UpdateWindPotSlotVital``, whose rows mix real tags with
``CALL_UNCLASSIFIED``/``PE_IMPORT_INVALID_PARAMETER_NOINFO_CALL``/atomic-
helper entries per direction and are therefore NOT implemented here
(confirmed independently in
``pf_bridge/notes_to_chief/reference_codex_attr/PF_PROTOCOL_PRIORITY.md``
lines 113-114, which lists exactly those two names as unproven-serializer
open items and does not list ``LearnFomulaVital``/``StartWinemakingVital``/
``FinishWinemakingVital``).

Grepped first, per ``AGENTS.md`` section 7's mandatory search: no hit for
``Winemaking`` in ``CLIENT_RE_QUEUE.md`` or ``GAME_TEST_QUEUE.md`` (both
empty grep). ``archive/`` -- no hit. ``src/`` and ``tests/`` -- no hit (no
prior module or test file for this class family). ``notes_to_chief/`` --
hits are all in ``notes_to_chief/reference_codex_attr/`` (the static
registry mirror described in ``prompts/LANE-UI.md``'s three-file map item
3, e.g. ``PF_ATTR_DATA_BINDINGS.tsv``'s "five exact Winemaking model/
project definitions" and ``PF_PROTOCOL_PRIORITY.md``'s two-line note
above) -- these are raw evidence tables, not an open ticket or a prior
module claiming this class family; none of them assign meaning to any
field or claim a wire shape different from what is transcribed below.
``docs/UI_LANE.md`` only lists ``Winemaking_`` as one of the 15 catalog
groups (5 rows total per the vital registry) with no per-class detail --
this module is the first one to itemize it. This catalog group has no open
RE/GT ticket and no prior wire module in ``src/``.

Tag widths used below are each independently confirmed elsewhere in this
project, not invented here: ``0x12`` = u16 (``external/PF_TAG_CENSUS.tsv``,
"uint16"; also ``CLIENT_RE_QUEUE.md:54``, "``0x12``=uint16"), ``0x0B`` =
u8 and ``0x08`` = u8 (both already in ``ui_social_wire.py``'s own tag
legend docstring), ``0x14`` = u32 (``ui_treasurehunt_wire.py``'s own tag
legend, itself citing ``GAME_TEST_QUEUE.md:9918``/``PF_TAG_CENSUS.tsv``
which lists ``0x14`` as ``len 4``), ``0x32`` = u64 (``ui_social_wire.py``'s
own tag legend).

Same scope line as every sibling module in this batch (``CORE-REQUEST
1120``'s own words): "รับเฟรม (decode) + ตอบ ack/error frame ที่วางเปล่า ...
ไม่ใช่การทำ business logic เต็ม". Nothing here claims what these fields MEAN
(formula id / vat slot index / wine quality roll, etc.) or composes a real
ack/result frame -- ``external/PF_FIELD_VALIDATION.tsv`` shows
``status=NOT_OBSERVED``, ``observed_frames=0`` for all three classes in
both ``W`` and ``R`` (same as the ``TreasureHunt``/``Gathering`` sibling
rows in ``docs/UI_LANE.md``), so nothing below claims which side sends
which class, that any class acks another, or any field's meaning -- the
registry's ``proven_semantics`` column is ``UNKNOWN`` for every row of all
three classes. Not wired into ``runtime.py`` or ``vital_walk.py``; wiring
any class is a separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

WINEMAKING_LEARN_FOMULA_VITAL_ID = 0x972E
WINEMAKING_START_WINEMAKING_VITAL_ID = 0xC8EB
WINEMAKING_FINISH_WINEMAKING_VITAL_ID = 0xD4D1

# Unproven default (see ui_party_wire.py's version-byte note).
WINEMAKING_LEARN_FOMULA_VITAL_VERSION = 0
WINEMAKING_START_WINEMAKING_VITAL_VERSION = 0
WINEMAKING_FINISH_WINEMAKING_VITAL_VERSION = 0

_TAG_U8_A = 0x0B
_TAG_U8_B = 0x08
_TAG_U16 = 0x12
_TAG_U32 = 0x14


@dataclass(frozen=True)
class LearnFomulaFields:
    """Wire order: u16, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4577-4580``)."""

    field1_u16: int
    field2_u8: int


@dataclass(frozen=True)
class StartWinemakingFields:
    """Wire order: u32, u64, u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4545-4552``)."""

    field1_u32: int
    field2_u64: int
    field3_u8: int
    field4_u8: int


@dataclass(frozen=True)
class FinishWinemakingFields:
    """Wire order: u8, u8, u8, u8, u32 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4553-4562``)."""

    field1_u8: int
    field2_u8: int
    field3_u8: int
    field4_u8: int
    field5_u32: int


def encode_learn_fomula_payload(fields: LearnFomulaFields) -> bytes:
    out = bytearray()
    out += wire.u16tag(_TAG_U16, fields.field1_u16)
    out += bytes([_TAG_U8_A, fields.field2_u8 & 0xFF])
    return bytes(out)


def decode_learn_fomula_payload(payload: bytes) -> LearnFomulaFields | None:
    try:
        field1, offset = wire.read_u16tag(payload, 0, _TAG_U16)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return LearnFomulaFields(field1, field2)


def encode_start_winemaking_payload(fields: StartWinemakingFields) -> bytes:
    out = bytearray()
    out += wire.u32tag(_TAG_U32, fields.field1_u32)
    out += wire.u64tag(0x32, fields.field2_u64)
    out += bytes([_TAG_U8_A, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8_B, fields.field4_u8 & 0xFF])
    return bytes(out)


def decode_start_winemaking_payload(
    payload: bytes,
) -> StartWinemakingFields | None:
    try:
        field1, offset = wire.read_u32tag(payload, 0, _TAG_U32)
        field2, offset = wire.read_u64tag(payload, offset, 0x32)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8_B)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return StartWinemakingFields(field1, field2, field3, field4)


def encode_finish_winemaking_payload(fields: FinishWinemakingFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8_A, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8_A, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8_A, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8_A, fields.field4_u8 & 0xFF])
    out += wire.u32tag(_TAG_U32, fields.field5_u32)
    return bytes(out)


def decode_finish_winemaking_payload(
    payload: bytes,
) -> FinishWinemakingFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8_A)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        field5, offset = wire.read_u32tag(payload, offset, _TAG_U32)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return FinishWinemakingFields(field1, field2, field3, field4, field5)
