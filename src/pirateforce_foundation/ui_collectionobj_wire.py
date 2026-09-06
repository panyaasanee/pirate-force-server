"""``CollectionObj_*`` -- pure encode/decode, wire shape only, for the four
classes in this catalog group whose ``PF_SERIALIZER_FIELDS.tsv`` rows are
FULLY TAGGED (every field row has a real tag byte, no
``CALL_UNCLASSIFIED``/``PE_IMPORT_*``/``JUMP_UNCLASSIFIED``/``ATOMIC_*``/
``DYNAMIC_INTERLOCKED_*``/``SUBCALL:`` entries):

    CollectionObj_CollectObjVital           0xABA4  5 fields
    CollectionObj_GetCollectEffectVital     0xF851  2 fields
    CollectionObj_SailorLevelUpRequestVital 0x3B06  3 fields
    CollectionObj_SailorLvUpResponseVital   0x1B8B  2 fields

Two classes in the same registry group (``CollectionObj`` 6, per
``pf_bridge/prompts/LANE-UI.md``'s catalog) are deliberately NOT
implemented here:
    - ``CollectionObj_UpdateCollectEffectVital`` (0x254E, 14 rows) -- mixes
      real ``0x12`` tags with ``PE_IMPORT_INVALID_PARAMETER_NOINFO_CALL``
      and ``CALL_UNCLASSIFIED:0x006564E0``/``0x00656C50`` entries (10 of 14
      rows unresolved).
    - ``CollectionObj_UpdateCollectionObjBagVital`` (0x51A2, 12 rows) --
      mixes a real ``0x0B`` tag with ``CALL_UNCLASSIFIED:INDIRECT(...)``,
      ``DYNAMIC_INTERLOCKED_DECREMENT_ECX_PLUS_0C_VTABLE_PLUS_04``, and
      ``ATOMIC_INTERLOCKED_INCREMENT_ECX_PLUS_0C`` entries (10 of 12 rows
      unresolved).

Field shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`` (grep ``^CollectionObj_``,
lines 5279-5288 / 5289-5292 / 5307-5312 / 5313-5316 for the four classes
implemented here); W and R rows are identical shape for every class (same
span_start/span_sha256 per class, both directions, and each class has its
own distinct span -- no shared-serializer case here, unlike
``ui_channel_wire.py``/``ui_express_wire.py``). The four ``*_VITAL_ID`` hex
constants below come from
``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` (grep
``CollectionObj_``) -- that file, not ``PF_SERIALIZER_FIELDS.tsv`` (which
has no id column), is this project's id-on-the-wire source per
``docs/UI_LANE.md`` item 1.

A note on a tag family NOT used here even though it appears elsewhere in
this catalog group's rejected rows: ``SUBCALL:<VA>`` (seen throughout the
sibling ``KnowledgeGuru_`` group, checked and rejected this same round --
every one of its five classes carries a ``SUBCALL:0x0069F980`` first
field) marks a call into another, unresolved sub-serializer function, the
same "we don't know this field's shape" meaning as
``CALL_UNCLASSIFIED``/``PE_IMPORT_*`` for this lane's purposes -- it is
added to this module's own exclusion list precedent
(``world_island_dock_table.py``'s ``TriggerVital`` note documents the same
tag family as evidence context, not as an implemented field). None of the
four classes below carry a ``SUBCALL:`` row.

Tag ``0x32`` = u64/qword, ``0x0B`` = u8, and ``0x12`` = u16 are documented
in ``ui_social_wire.py``'s module docstring (``0x32``, ``0x0B``) and in
``ui_buildingcrystal_wire.py``/``ui_channel_wire.py``'s docstrings plus
``external/PF_TAG_CENSUS.tsv`` row ``0x12  2  FIXED  ...  uint16`` (``0x12``).

Grepped first, per ``AGENTS.md`` section 7's mandatory search: no hit for
any of the six ``CollectionObj_*`` class names above in
``CLIENT_RE_QUEUE.md``, ``GAME_TEST_QUEUE.md``, or ``archive/`` (grep on
the bridge repo) -- no open or closed RE/GT ticket references any of them,
and no prior module in ``src/`` or ``tests/`` names this group. The only
hits are the static census tables (expected background coverage, not a
ticket).

Same scope line as every sibling module in this lane's wire-shape batch:
"receive frame (decode) + compose the same shape back (encode), no
business logic". Nothing here claims what any field MEANS (collectible
id, sailor level, effect id, etc.) -- the registry's ``proven_semantics``
column is ``UNKNOWN`` for every row of all four classes, and
``external/PF_FIELD_VALIDATION.tsv`` reads ``status=NOT_OBSERVED``,
``observed_frames=0`` for both ``W``/``R`` on every one of them, same as
every sibling wire-shape-only module this lane has already shipped. Not
wired into ``runtime.py`` or ``vital_walk.py``; wiring any of these is a
separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

COLLECTIONOBJ_COLLECT_OBJ_VITAL_ID = 0xABA4
COLLECTIONOBJ_GET_COLLECT_EFFECT_VITAL_ID = 0xF851
COLLECTIONOBJ_SAILOR_LEVEL_UP_REQUEST_VITAL_ID = 0x3B06
COLLECTIONOBJ_SAILOR_LV_UP_RESPONSE_VITAL_ID = 0x1B8B

# Unproven default (see ui_party_wire.py's version-byte note).
COLLECTIONOBJ_COLLECT_OBJ_VITAL_VERSION = 0
COLLECTIONOBJ_GET_COLLECT_EFFECT_VITAL_VERSION = 0
COLLECTIONOBJ_SAILOR_LEVEL_UP_REQUEST_VITAL_VERSION = 0
COLLECTIONOBJ_SAILOR_LV_UP_RESPONSE_VITAL_VERSION = 0

_TAG_U8 = 0x0B
_TAG_U16 = 0x12
_TAG_U64 = 0x32


@dataclass(frozen=True)
class CollectObjFields:
    """Wire order: u64, u8, u8, u8, u64 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv`` ``CollectionObj_CollectObjVital`` rows,
    lines 5279-5288)."""

    field1_u64: int
    field2_u8: int
    field3_u8: int
    field4_u8: int
    field5_u64: int


@dataclass(frozen=True)
class GetCollectEffectFields:
    """Wire order: u16, u8 -- identical shape for W and R (lines
    5289-5292)."""

    field1_u16: int
    field2_u8: int


@dataclass(frozen=True)
class SailorLevelUpRequestFields:
    """Wire order: u64, u64, u64 -- identical shape for W and R (lines
    5307-5312)."""

    field1_u64: int
    field2_u64: int
    field3_u64: int


@dataclass(frozen=True)
class SailorLvUpResponseFields:
    """Wire order: u8, u64 -- identical shape for W and R (lines
    5313-5316)."""

    field1_u8: int
    field2_u64: int


def encode_collect_obj_payload(fields: CollectObjFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    out += wire.u64tag(_TAG_U64, fields.field5_u64)
    return bytes(out)


def decode_collect_obj_payload(payload: bytes) -> CollectObjFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field5, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return CollectObjFields(field1, field2, field3, field4, field5)


def encode_get_collect_effect_payload(fields: GetCollectEffectFields) -> bytes:
    out = bytearray()
    out += wire.u16tag(_TAG_U16, fields.field1_u16)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    return bytes(out)


def decode_get_collect_effect_payload(
    payload: bytes,
) -> GetCollectEffectFields | None:
    try:
        field1, offset = wire.read_u16tag(payload, 0, _TAG_U16)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return GetCollectEffectFields(field1, field2)


def encode_sailor_level_up_request_payload(
    fields: SailorLevelUpRequestFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += wire.u64tag(_TAG_U64, fields.field3_u64)
    return bytes(out)


def decode_sailor_level_up_request_payload(
    payload: bytes,
) -> SailorLevelUpRequestFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field3, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return SailorLevelUpRequestFields(field1, field2, field3)


def encode_sailor_lv_up_response_payload(
    fields: SailorLvUpResponseFields,
) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    return bytes(out)


def decode_sailor_lv_up_response_payload(
    payload: bytes,
) -> SailorLvUpResponseFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return SailorLvUpResponseFields(field1, field2)
