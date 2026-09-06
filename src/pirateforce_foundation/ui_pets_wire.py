"""``Pets_*`` -- pure encode/decode, wire shape only, for the ten classes in
this catalog group whose ``PF_SERIALIZER_FIELDS.tsv`` rows are FULLY TAGGED
(every field row has a real tag byte, no ``CALL_UNCLASSIFIED``/
``PE_IMPORT_*``/``JUMP_UNCLASSIFIED``/``ATOMIC_*``/``DYNAMIC_INTERLOCKED_*``
entries):

    Pets_SummonPetVital               0x4CEC  5 fields
    Pets_UnsummonPetVital              0x5E3C  3 fields
    Pets_UpdatePetPropertyVital        0x9B50  3 fields
    Pets_RestorePetAmityVital          0x83B5  3 fields
    Pets_NotifySailorDeadVital         0x8B12  1 field
    Pets_MergePetsVital                0x4C4D  4 fields
    Pets_MergePetsResultVital          0x845C  2 fields
    Pets_ClaimPetsMegringItemVital     0xB96F  3 fields
    Pets_LearnPetSkillVital            0x6E55  2 fields
    Pets_UpdateSummonPetsTimeOutVital  0xE28A  1 field

Six classes in the same registry group (16 total, per
``pf_bridge/prompts/LANE-UI.md``'s catalog: "Pets 16") are deliberately NOT
implemented here, same exclusion policy as every sibling module in this
batch (``ui_activity_wire.py``'s four exclusions, ``ui_treasurehunt_wire.py``'s
one):
    - ``Pets_ChangePetEquipmentVital`` (0xA466, 34 rows) -- mixes real tags
      with ``CALL_UNCLASSIFIED``/``PE_IMPORT_*`` entries (16 of 34 rows).
    - ``Pets_SetPetAIVital`` (0x4115, 18 rows) -- same mix (10 of 18 rows).
    - ``Pets_SetPetSkillVital`` (0x5C79, 32 rows) -- same mix (16 of 32 rows).
    - ``Pets_UpdateLearnedPetSkillVital`` (0xC574, 12 rows) -- same mix
      (10 of 12 rows).
    - ``Pets_UpdatePetsDataVital`` (0x76B9, 12 rows) -- same mix
      (10 of 12 rows).
    - ``Pets_UpdatePetsMegringDataVital`` (0xC45C, 12 rows) -- same mix
      (10 of 12 rows).

Field shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`` (searched via
``awk -F'\\t' '$1 ~ /^Pets_/'``, 174 rows total across all 16 classes); W
and R rows are identical shape for every class implemented here (same
span/sha256 per class, both directions). The ten ``*_VITAL_ID`` hex
constants below come from
``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` (grep
``^0x....\\tPets_``) -- that file, not ``PF_SERIALIZER_FIELDS.tsv`` (which
has no id column), is this project's id-on-the-wire source per
``docs/UI_LANE.md`` item 1.

``Pets_MergePetsVital``'s third and fourth fields carry a ``PHI(...)``
``field_offset`` (the client object's in-memory address is a compiler-level
merge of two call-site-dependent locations) instead of a plain ``+0xNN``.
This does not affect anything here: per ``ui_social_wire.py``'s module
docstring, ``field_offset`` is client-object provenance only, never a wire
byte offset -- the wire shape is exactly the row's ``tag``+``len`` in
``order`` sequence regardless of what ``field_offset`` says, so an
ambiguous/merged client-memory address does not make the *wire* shape any
less known. Tag and length are plain ``0x32``/8 for both fields, same as
every other qword field in this module.

Grepped first, per ``AGENTS.md`` section 7's mandatory search: no hit for
any of the ten class names above in ``CLIENT_RE_QUEUE.md`` or
``GAME_TEST_QUEUE.md`` (grep on the bridge repo) -- no open RE/GT ticket
references any of them. The only hits are the static census tables
(``notes_to_chief/reference_codex_attr/PF_PROTOCOL_REGISTRY.tsv``,
``PF_FIELD_VALIDATION.tsv``, ``PF_PROTOCOL_PRIORITY.tsv``), which is
expected background coverage, not a ticket. This catalog group has no
prior wire module in ``src/``.

See ``ui_social_wire.py``'s module docstring for the shared tag legend, the
"why no wire offsets" explanation, and the fail-closed-on-decode
convention. Tag ``0x32`` = u64/qword is documented there directly
(``CLIENT_RE_QUEUE.md:3425``). Tag ``0x0F`` = u16 is the same tag
``ui_tracepath_wire.py`` already writes with ``u16tag``.

Same scope line as every sibling module in this batch (``CORE-REQUEST
1120``'s own words): "รับเฟรม (decode) + ตอบ ack/error frame ที่วางเปล่า ...
ไม่ใช่การทำ business logic เต็ม". Nothing here claims what any field MEANS
(pet id / owner id / amity value / slot index, etc.) -- the registry's
``proven_semantics`` column is ``UNKNOWN`` for every row of all ten
classes. Not wired into ``runtime.py`` or ``vital_walk.py``; wiring any of
these is a separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

PETS_SUMMON_PET_VITAL_ID = 0x4CEC
PETS_UNSUMMON_PET_VITAL_ID = 0x5E3C
PETS_UPDATE_PET_PROPERTY_VITAL_ID = 0x9B50
PETS_RESTORE_PET_AMITY_VITAL_ID = 0x83B5
PETS_NOTIFY_SAILOR_DEAD_VITAL_ID = 0x8B12
PETS_MERGE_PETS_VITAL_ID = 0x4C4D
PETS_MERGE_PETS_RESULT_VITAL_ID = 0x845C
PETS_CLAIM_PETS_MEGRING_ITEM_VITAL_ID = 0xB96F
PETS_LEARN_PET_SKILL_VITAL_ID = 0x6E55
PETS_UPDATE_SUMMON_PETS_TIME_OUT_VITAL_ID = 0xE28A

# Unproven default (see ui_party_wire.py's version-byte note).
PETS_SUMMON_PET_VITAL_VERSION = 0
PETS_UNSUMMON_PET_VITAL_VERSION = 0
PETS_UPDATE_PET_PROPERTY_VITAL_VERSION = 0
PETS_RESTORE_PET_AMITY_VITAL_VERSION = 0
PETS_NOTIFY_SAILOR_DEAD_VITAL_VERSION = 0
PETS_MERGE_PETS_VITAL_VERSION = 0
PETS_MERGE_PETS_RESULT_VITAL_VERSION = 0
PETS_CLAIM_PETS_MEGRING_ITEM_VITAL_VERSION = 0
PETS_LEARN_PET_SKILL_VITAL_VERSION = 0
PETS_UPDATE_SUMMON_PETS_TIME_OUT_VITAL_VERSION = 0

_TAG_U8 = 0x0B
_TAG_U16 = 0x0F
_TAG_U32 = 0x14
_TAG_U64 = 0x32


@dataclass(frozen=True)
class SummonPetFields:
    """Wire order: u64, u64, u32, u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv`` ``Pets_SummonPetVital`` rows)."""

    field1_u64: int
    field2_u64: int
    field3_u32: int
    field4_u8: int
    field5_u8: int


@dataclass(frozen=True)
class UnsummonPetFields:
    """Wire order: u64, u8, u8 -- identical shape for W and R."""

    field1_u64: int
    field2_u8: int
    field3_u8: int


@dataclass(frozen=True)
class UpdatePetPropertyFields:
    """Wire order: u64, u32, u8 -- identical shape for W and R."""

    field1_u64: int
    field2_u32: int
    field3_u8: int


@dataclass(frozen=True)
class RestorePetAmityFields:
    """Wire order: u64, u64, u8 -- identical shape for W and R."""

    field1_u64: int
    field2_u64: int
    field3_u8: int


@dataclass(frozen=True)
class NotifySailorDeadFields:
    """Wire order: u64 -- identical shape for W and R."""

    field1_u64: int


@dataclass(frozen=True)
class MergePetsFields:
    """Wire order: u8, u8, u64, u64 -- identical shape for W and R. Fields
    3/4 are the ``PHI(...)`` ``field_offset`` pair discussed in the module
    docstring -- tag/length are plain ``0x32``/8 regardless."""

    field1_u8: int
    field2_u8: int
    field3_u64: int
    field4_u64: int


@dataclass(frozen=True)
class MergePetsResultFields:
    """Wire order: u8, u8 -- identical shape for W and R."""

    field1_u8: int
    field2_u8: int


@dataclass(frozen=True)
class ClaimPetsMegringItemFields:
    """Wire order: u8, u8, u64 -- identical shape for W and R."""

    field1_u8: int
    field2_u8: int
    field3_u64: int


@dataclass(frozen=True)
class LearnPetSkillFields:
    """Wire order: u16, u8 -- identical shape for W and R."""

    field1_u16: int
    field2_u8: int


@dataclass(frozen=True)
class UpdateSummonPetsTimeOutFields:
    """Wire order: u32 -- identical shape for W and R."""

    field1_u32: int


def encode_summon_pet_payload(fields: SummonPetFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += wire.u32tag(_TAG_U32, fields.field3_u32)
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field5_u8 & 0xFF])
    return bytes(out)


def decode_summon_pet_payload(payload: bytes) -> SummonPetFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field3, offset = wire.read_u32tag(payload, offset, _TAG_U32)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field5, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return SummonPetFields(field1, field2, field3, field4, field5)


def encode_unsummon_pet_payload(fields: UnsummonPetFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_unsummon_pet_payload(payload: bytes) -> UnsummonPetFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return UnsummonPetFields(field1, field2, field3)


def encode_update_pet_property_payload(fields: UpdatePetPropertyFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u32tag(_TAG_U32, fields.field2_u32)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_update_pet_property_payload(
    payload: bytes,
) -> UpdatePetPropertyFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u32tag(payload, offset, _TAG_U32)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return UpdatePetPropertyFields(field1, field2, field3)


def encode_restore_pet_amity_payload(fields: RestorePetAmityFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_restore_pet_amity_payload(
    payload: bytes,
) -> RestorePetAmityFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return RestorePetAmityFields(field1, field2, field3)


def encode_notify_sailor_dead_payload(fields: NotifySailorDeadFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    return bytes(out)


def decode_notify_sailor_dead_payload(
    payload: bytes,
) -> NotifySailorDeadFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return NotifySailorDeadFields(field1)


def encode_merge_pets_payload(fields: MergePetsFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += wire.u64tag(_TAG_U64, fields.field3_u64)
    out += wire.u64tag(_TAG_U64, fields.field4_u64)
    return bytes(out)


def decode_merge_pets_payload(payload: bytes) -> MergePetsFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field4, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return MergePetsFields(field1, field2, field3, field4)


def encode_merge_pets_result_payload(fields: MergePetsResultFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    return bytes(out)


def decode_merge_pets_result_payload(
    payload: bytes,
) -> MergePetsResultFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return MergePetsResultFields(field1, field2)


def encode_claim_pets_megring_item_payload(
    fields: ClaimPetsMegringItemFields,
) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += wire.u64tag(_TAG_U64, fields.field3_u64)
    return bytes(out)


def decode_claim_pets_megring_item_payload(
    payload: bytes,
) -> ClaimPetsMegringItemFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ClaimPetsMegringItemFields(field1, field2, field3)


def encode_learn_pet_skill_payload(fields: LearnPetSkillFields) -> bytes:
    out = bytearray()
    out += wire.u16tag(_TAG_U16, fields.field1_u16)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    return bytes(out)


def decode_learn_pet_skill_payload(payload: bytes) -> LearnPetSkillFields | None:
    try:
        field1, offset = wire.read_u16tag(payload, 0, _TAG_U16)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return LearnPetSkillFields(field1, field2)


def encode_update_summon_pets_time_out_payload(
    fields: UpdateSummonPetsTimeOutFields,
) -> bytes:
    out = bytearray()
    out += wire.u32tag(_TAG_U32, fields.field1_u32)
    return bytes(out)


def decode_update_summon_pets_time_out_payload(
    payload: bytes,
) -> UpdateSummonPetsTimeOutFields | None:
    try:
        field1, offset = wire.read_u32tag(payload, 0, _TAG_U32)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return UpdateSummonPetsTimeOutFields(field1)
