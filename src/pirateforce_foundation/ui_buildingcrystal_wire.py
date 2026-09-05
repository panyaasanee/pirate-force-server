"""``BuildingCrystal_*`` -- pure encode/decode, wire shape only, for the 11
of this catalog group's 13 classes whose rows are fully tagged (crystal-
socket crafting minigame: extract/insert/absorb/nutrient/luster/purchase/
speed-up).

See ``ui_social_wire.py``'s module docstring for the shared tag legend, the
"why no wire offsets" explanation, and ``ui_party_wire.py``'s docstring for
why fields are named positionally rather than by guessed meaning. Field
shapes are copied field-for-field from ``pf_bridge/external/
PF_SERIALIZER_FIELDS.tsv`` (``W``/``R`` identical for every class below):

- ``BuildingCrystal_PurchaseServiceVital`` ``0x0D27``: u8, u8 (``:4151-4154``)
- ``BuildingCrystal_OpenCrystalSlotVital`` ``0x0ED3``: u64, u8, u8, u8
  (``:4085-4092``)
- ``BuildingCrystal_IncreaseCrystalSlotMaxNutrientVital`` ``0x1C37``: u8, u8
  (``:4147-4150``)
- ``BuildingCrystal_AddCrystalLusterVital`` ``0x1D0C``: u64, u64, u8, u16
  (``:4155-4162``)
- ``BuildingCrystal_SpeedUpBuildCrystalVital`` ``0x4942``: u8 (``:4137-4138``)
- ``BuildingCrystal_InsertCrystalToSlotVital`` ``0x4D86``: u64, u8, u8, u8
  (``:4103-4110``)
- ``BuildingCrystal_ExtractCrystalFailedVital`` ``0x59AB``: u8, u8, u8
  (``:4121-4126``)
- ``BuildingCrystal_ExtractCrystalFromSlotVital`` ``0x80A0``: u64, u8, u8,
  u8, u8 (``:4111-4120``)
- ``BuildingCrystal_ExtractCrystalSucceededVital`` ``0x8E98``: u8, u8, u8,
  u8, u64 (``:4127-4136``)
- ``BuildingCrystal_AddNutrientToCrystalSlotVital`` ``0xA3CD``: u64, u8, u8,
  u8, u8 (``:4093-4102``)
- ``BuildingCrystal_DoAbsorbingVital`` ``0xD339``: u8, u8, u64, u8
  (``:4139-4146``)

Every row above has a plain hex tag byte for every field, no
``CALL_UNCLASSIFIED``/``PE_IMPORT_*``/atomic-helper entries -- confirmed by
reading the raw TSV rows directly, same bar as every sibling module in this
batch. Two of this catalog group's 13 classes are explicitly NOT
implemented here, the same way ``ui_treasurehunt_wire.py`` excludes
``TreasureHunt_UpdateSceneTreasurePointVital``:

- ``BuildingCrystal_UpdateCrystalSlotVital`` (``0x2D5C``,
  ``PF_SERIALIZER_FIELDS.tsv:4073-4084``): its six rows per direction mix
  one real ``0x0B`` tag with ``CALL_UNCLASSIFIED``/``DYNAMIC_INTERLOCKED_
  DECREMENT_ECX_PLUS_0C_VTABLE_PLUS_04``/``ATOMIC_INTERLOCKED_INCREMENT_
  ECX_PLUS_0C`` entries -- not fully tagged.
- ``BuildingCrystal_UpdateNextAbsorbTime`` (``PF_SERIALIZER_FIELDS.tsv:4163-
  4164``, one fully-tagged ``u32`` field): it has no vital id at all in
  ``VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` (``grep -n
  "BuildingCrystal" VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` lists
  the other 12 ``BuildingCrystal_*`` names and vital ids but not this one)
  -- not a real client-facing action, so there is no id to hang a wire
  class on even though its own field row is clean.

Grepped first, per ``AGENTS.md`` section 7's mandatory search:
``grep -rn "BuildingCrystal" CLIENT_RE_QUEUE.md GAME_TEST_QUEUE.md`` --
no hit in either file. ``grep -rl "BuildingCrystal" archive/ notes_to_chief/
notes_to_chief/reference_codex_attr/`` -- every hit is either the static
registry mirror itself (``notes_to_chief/reference_codex_attr/
PF_PROTOCOL_REGISTRY.tsv``, ``PF_FIELD_VALIDATION.tsv``,
``PF_PROTOCOL_PRIORITY.tsv``/``.md``, ``PF_DUMP_REQUEST.md``,
``PF_ATTR_*_CENSUS.tsv``/``PF_ATTR_UNRESOLVED_BUCKETS.tsv``/
``PF_ATTR_DATA_BINDINGS.tsv``, ``PF_V2_P1_OPEN.tsv``..``PF_V5_P1_OPEN.tsv``,
``pf_rederive_attr_semantics.py``) or an unrelated open RE ticket about the
``Options apply server setting`` class family
(``notes_to_chief/20260904_1054_LANE-UI-RE-TICKET-options-apply-server-
setting-vital-fields-need-dynamic-capture.md`` and its ``consumed/`` copy)
that only shares a directory listing with this group's rows, not a claim
about ``BuildingCrystal_`` itself -- no open RE/GT ticket names this catalog
group. Also confirmed: no existing ``src/*.py``/``tests/test_ui_*.py``
module touches ``BuildingCrystal_`` before this one
(``grep -rln "BuildingCrystal" src/ tests/`` -- no hit).

Tag widths used below are each independently confirmed elsewhere in this
project, not invented here (same legend already used by every sibling
module in this batch): ``0x08`` = u8 (``ui_social_wire.py``'s own tag
legend, citing ``FINDINGS_R38_0x1B40_DECODED_LOGOUTVITAL.md``), ``0x32`` =
u64/qword (``ui_social_wire.py``'s own tag legend, citing
``CLIENT_RE_QUEUE.md:3425``), ``0x12`` = u16 (``CLIENT_RE_QUEUE.md:54``,
"``0x12``=uint16", also already used by ``ui_treasurehunt_wire.py`` and
``ui_winemaking_wire.py``).

``external/PF_FIELD_VALIDATION.tsv`` shows ``status=NOT_OBSERVED``,
``observed_frames=0`` for both ``W`` and ``R`` on every one of these 11
classes -- same as every sibling module in this batch -- so nothing below
claims which side sends which class, that any class acks another, or what
any field means (item id / slot index / crystal type / nutrient amount /
luster value, etc. all ``proven_semantics=UNKNOWN`` in the registry); that
would be an unlabeled guess by analogy to the (separately, actually proven)
``LogoutVital`` ack pattern, which this module does not make.

Same scope line as every sibling module in this batch (``CORE-REQUEST
1120``'s own words): "รับเฟรม (decode) + ตอบ ack/error frame ที่วางเปล่า ...
ไม่ใช่การทำ business logic เต็ม". Not wired into ``runtime.py`` or
``vital_walk.py``; wiring any class is a separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

BUILDINGCRYSTAL_PURCHASE_SERVICE_VITAL_ID = 0x0D27
BUILDINGCRYSTAL_OPEN_CRYSTAL_SLOT_VITAL_ID = 0x0ED3
BUILDINGCRYSTAL_INCREASE_CRYSTAL_SLOT_MAX_NUTRIENT_VITAL_ID = 0x1C37
BUILDINGCRYSTAL_ADD_CRYSTAL_LUSTER_VITAL_ID = 0x1D0C
BUILDINGCRYSTAL_SPEED_UP_BUILD_CRYSTAL_VITAL_ID = 0x4942
BUILDINGCRYSTAL_INSERT_CRYSTAL_TO_SLOT_VITAL_ID = 0x4D86
BUILDINGCRYSTAL_EXTRACT_CRYSTAL_FAILED_VITAL_ID = 0x59AB
BUILDINGCRYSTAL_EXTRACT_CRYSTAL_FROM_SLOT_VITAL_ID = 0x80A0
BUILDINGCRYSTAL_EXTRACT_CRYSTAL_SUCCEEDED_VITAL_ID = 0x8E98
BUILDINGCRYSTAL_ADD_NUTRIENT_TO_CRYSTAL_SLOT_VITAL_ID = 0xA3CD
BUILDINGCRYSTAL_DO_ABSORBING_VITAL_ID = 0xD339

# Unproven default (see ui_party_wire.py's version-byte note).
BUILDINGCRYSTAL_PURCHASE_SERVICE_VITAL_VERSION = 0
BUILDINGCRYSTAL_OPEN_CRYSTAL_SLOT_VITAL_VERSION = 0
BUILDINGCRYSTAL_INCREASE_CRYSTAL_SLOT_MAX_NUTRIENT_VITAL_VERSION = 0
BUILDINGCRYSTAL_ADD_CRYSTAL_LUSTER_VITAL_VERSION = 0
BUILDINGCRYSTAL_SPEED_UP_BUILD_CRYSTAL_VITAL_VERSION = 0
BUILDINGCRYSTAL_INSERT_CRYSTAL_TO_SLOT_VITAL_VERSION = 0
BUILDINGCRYSTAL_EXTRACT_CRYSTAL_FAILED_VITAL_VERSION = 0
BUILDINGCRYSTAL_EXTRACT_CRYSTAL_FROM_SLOT_VITAL_VERSION = 0
BUILDINGCRYSTAL_EXTRACT_CRYSTAL_SUCCEEDED_VITAL_VERSION = 0
BUILDINGCRYSTAL_ADD_NUTRIENT_TO_CRYSTAL_SLOT_VITAL_VERSION = 0
BUILDINGCRYSTAL_DO_ABSORBING_VITAL_VERSION = 0

_TAG_U8 = 0x08
_TAG_U16 = 0x12
_TAG_U64 = 0x32


@dataclass(frozen=True)
class PurchaseServiceFields:
    """Wire order: u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4151-4154``)."""

    field1_u8: int
    field2_u8: int


@dataclass(frozen=True)
class OpenCrystalSlotFields:
    """Wire order: u64, u8, u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4085-4092``)."""

    field1_u64: int
    field2_u8: int
    field3_u8: int
    field4_u8: int


@dataclass(frozen=True)
class IncreaseCrystalSlotMaxNutrientFields:
    """Wire order: u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4147-4150``)."""

    field1_u8: int
    field2_u8: int


@dataclass(frozen=True)
class AddCrystalLusterFields:
    """Wire order: u64, u64, u8, u16 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4155-4162``)."""

    field1_u64: int
    field2_u64: int
    field3_u8: int
    field4_u16: int


@dataclass(frozen=True)
class SpeedUpBuildCrystalFields:
    """Wire order: u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4137-4138``)."""

    field1_u8: int


@dataclass(frozen=True)
class InsertCrystalToSlotFields:
    """Wire order: u64, u8, u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4103-4110``)."""

    field1_u64: int
    field2_u8: int
    field3_u8: int
    field4_u8: int


@dataclass(frozen=True)
class ExtractCrystalFailedFields:
    """Wire order: u8, u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4121-4126``)."""

    field1_u8: int
    field2_u8: int
    field3_u8: int


@dataclass(frozen=True)
class ExtractCrystalFromSlotFields:
    """Wire order: u64, u8, u8, u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4111-4120``)."""

    field1_u64: int
    field2_u8: int
    field3_u8: int
    field4_u8: int
    field5_u8: int


@dataclass(frozen=True)
class ExtractCrystalSucceededFields:
    """Wire order: u8, u8, u8, u8, u64 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4127-4136``)."""

    field1_u8: int
    field2_u8: int
    field3_u8: int
    field4_u8: int
    field5_u64: int


@dataclass(frozen=True)
class AddNutrientToCrystalSlotFields:
    """Wire order: u64, u8, u8, u8, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4093-4102``)."""

    field1_u64: int
    field2_u8: int
    field3_u8: int
    field4_u8: int
    field5_u8: int


@dataclass(frozen=True)
class DoAbsorbingFields:
    """Wire order: u8, u8, u64, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv:4139-4146``)."""

    field1_u8: int
    field2_u8: int
    field3_u64: int
    field4_u8: int


def encode_purchase_service_payload(fields: PurchaseServiceFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    return bytes(out)


def decode_purchase_service_payload(
    payload: bytes,
) -> PurchaseServiceFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return PurchaseServiceFields(field1, field2)


def encode_open_crystal_slot_payload(fields: OpenCrystalSlotFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    return bytes(out)


def decode_open_crystal_slot_payload(
    payload: bytes,
) -> OpenCrystalSlotFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return OpenCrystalSlotFields(field1, field2, field3, field4)


def encode_increase_crystal_slot_max_nutrient_payload(
    fields: IncreaseCrystalSlotMaxNutrientFields,
) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    return bytes(out)


def decode_increase_crystal_slot_max_nutrient_payload(
    payload: bytes,
) -> IncreaseCrystalSlotMaxNutrientFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return IncreaseCrystalSlotMaxNutrientFields(field1, field2)


def encode_add_crystal_luster_payload(fields: AddCrystalLusterFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += wire.u16tag(_TAG_U16, fields.field4_u16)
    return bytes(out)


def decode_add_crystal_luster_payload(
    payload: bytes,
) -> AddCrystalLusterFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field4, offset = wire.read_u16tag(payload, offset, _TAG_U16)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return AddCrystalLusterFields(field1, field2, field3, field4)


def encode_speed_up_build_crystal_payload(
    fields: SpeedUpBuildCrystalFields,
) -> bytes:
    return bytes([_TAG_U8, fields.field1_u8 & 0xFF])


def decode_speed_up_build_crystal_payload(
    payload: bytes,
) -> SpeedUpBuildCrystalFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return SpeedUpBuildCrystalFields(field1)


def encode_insert_crystal_to_slot_payload(
    fields: InsertCrystalToSlotFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    return bytes(out)


def decode_insert_crystal_to_slot_payload(
    payload: bytes,
) -> InsertCrystalToSlotFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return InsertCrystalToSlotFields(field1, field2, field3, field4)


def encode_extract_crystal_failed_payload(
    fields: ExtractCrystalFailedFields,
) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_extract_crystal_failed_payload(
    payload: bytes,
) -> ExtractCrystalFailedFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ExtractCrystalFailedFields(field1, field2, field3)


def encode_extract_crystal_from_slot_payload(
    fields: ExtractCrystalFromSlotFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field5_u8 & 0xFF])
    return bytes(out)


def decode_extract_crystal_from_slot_payload(
    payload: bytes,
) -> ExtractCrystalFromSlotFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field5, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ExtractCrystalFromSlotFields(field1, field2, field3, field4, field5)


def encode_extract_crystal_succeeded_payload(
    fields: ExtractCrystalSucceededFields,
) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    out += wire.u64tag(_TAG_U64, fields.field5_u64)
    return bytes(out)


def decode_extract_crystal_succeeded_payload(
    payload: bytes,
) -> ExtractCrystalSucceededFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field5, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ExtractCrystalSucceededFields(field1, field2, field3, field4, field5)


def encode_add_nutrient_to_crystal_slot_payload(
    fields: AddNutrientToCrystalSlotFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field5_u8 & 0xFF])
    return bytes(out)


def decode_add_nutrient_to_crystal_slot_payload(
    payload: bytes,
) -> AddNutrientToCrystalSlotFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field5, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return AddNutrientToCrystalSlotFields(field1, field2, field3, field4, field5)


def encode_do_absorbing_payload(fields: DoAbsorbingFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += wire.u64tag(_TAG_U64, fields.field3_u64)
    out += bytes([_TAG_U8, fields.field4_u8 & 0xFF])
    return bytes(out)


def decode_do_absorbing_payload(payload: bytes) -> DoAbsorbingFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field4, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return DoAbsorbingFields(field1, field2, field3, field4)
