"""``Dyeing``/``Appraisal``/``Relive`` -- pure encode/decode, wire shape only,
for the classes in these three catalog groups (``docs/UI_LANE.md``'s
"everything else" row, `prompts/LANE-UI.md`'s function map item 1) whose
``PF_SERIALIZER_FIELDS.tsv`` rows are FULLY TAGGED (every field row has a
real tag byte, no ``CALL_UNCLASSIFIED``/``PE_IMPORT_*``/``SUBCALL:``/
``ATOMIC_*``/``DYNAMIC_INTERLOCKED_*`` entries) AND have a real vital id in
``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` (the
id-on-the-wire source per ``docs/UI_LANE.md`` item 1, not the serializer
TSV, which has no id column):

    AppraisalVital       0x2AB1  3 fields (Appraisal group, 2 of 2 -- full)
    AppraisalStopVital   0x45CF  0 fields (Appraisal group, 2 of 2 -- full)
    DyeingVitalRes       0x2A00  1 field  (Dyeing group, 4 of 4 -- full)
    DyeingRemoveVital    0x3E1C  2 fields (Dyeing group, 4 of 4 -- full)
    DyeingShipVitalReq   0x441A  2 fields (Dyeing group, 4 of 4 -- full)
    DyeingVitalReq       0x29E4  2 fields (Dyeing group, 4 of 4 -- full)
    ReliveVital          0x1AD4  2 fields (Relive group, 1 of 2)

``DyeingVitalReq`` was added this round (round `42w728`), closing the
question the previous round (`dgap6x`) left open below it. All six other
classes are combined in one module (instead of one file per group like
this lane's earlier rounds) to stay inside ``AGENTS.md`` section 7's
"วิธีเปิด PR" ~6-files-per-PR cap: three separate module+test pairs plus the
``docs/UI_LANE.md`` update would be 7 files; one module + one test file +
the doc update is 3.

``DyeingVitalReq`` (0x29E4, the Dyeing group's 4th class) -- resolved this
round, no longer excluded. Its field 2 is tagged
``UNTAGGED_STRING8_LEN32LE`` in ``PF_SERIALIZER_FIELDS.tsv:5182/5184``,
which the previous round (`dgap6x`) correctly refused to treat as "no tag
byte, just len32+payload" on its own: ``src/pirateforce_foundation/
logout_hypothesis.py``'s ``ReturnSelectServerVital`` erratum (RE-196/
GT-055) proved that label only describes the scope of the string-writing
HELPER CALL span -- a tag-push instruction can sit immediately before that
call, outside the labelled span -- and ``DeleteActorVital``'s string field
carries the IDENTICAL label yet GT-018 independently confirmed a real
``0x44`` tag byte precedes it. This round's static-RE pass (pf-static-re
agent, cloud-clone-only, no client binary) closed the question from
already-committed artifacts, not new disassembly: ``notes_to_chief/
reference_codex_attr/PF_A2_STRING_WIRE_TAG_DELTA.tsv:362-363`` records
``DyeingVitalReq``'s W/R string call sites (helper VA ``0x0089A6D0``/
``0x0089A740``, span end ``0x0089A733``/``0x0089A806``, SHA-256
``a0674fb3...96c29319bd``/``90c8c73b...4754dec54e76a``) as BYTE-IDENTICAL
to ``DeleteActorVital``'s own already-proven string field (same TSV,
line 18: same helper VA/span-end/SHA-256), with the same
``tag_instruction_va=0x0089A6F1``, ``tag_instruction_semantics=push_0x44``
recorded for both. Because the two classes' callers dispatch into the
exact same helper span (VA-for-VA and SHA-256-identical, not merely the
same textual label), GT-018's tag-0x44 finding transfers to
``DyeingVitalReq`` by construction. This is the same mechanism (a tag-push
instruction living inside the shared helper's own code, not in caller
code) that independently settled a related, longer-running question for
``ReturnSelectServerVital`` -- corrected here after a pf-adversary pass on
this module (round `42w728`) caught the first draft misattributing that
history: ``ReturnSelectServerVital``'s field 3 shares the SAME
``0x0089A6D0``/``0x0089A740`` helper span as ``DeleteActorVital`` and
``DyeingVitalReq`` (``PF_A2_STRING_WIRE_TAG_DELTA.tsv`` lines 50-51,
identical helper VA/span-end/SHA-256/``push_0x44`` to line 18's
``DeleteActorVital`` row) -- ``0x5E69F0`` in that class's own row is its
CALLER function's ``base_span_start``, not "a different helper" the first
draft claimed. ``rounds/A_20260901_1737_njkvcc_...md`` flagged this as an
open evidentiary gap, not an "invalid" case; that gap was independently
closed positive four days before this round, in
``notes_to_chief/20260902_0325_RE-196-RESULT-TAG44-AND-16BYTE-BODY-
CONFIRMED.md``, which disassembled the pinned client image directly and
confirmed the real ``0x44`` tag. Field 1
(tag ``0x32``/u64 @+0x18, ``PF_SERIALIZER_FIELDS.tsv:5181/5183``) was
already fully tagged and unaffected by this question. Kept opaque as
``bytes`` (not decoded to ``str``): no proven charset for this class's
string8 payload, same posture as ``delete_actor.py``'s own
``opaque_string8`` field.

Excluded from this module, with reasons:

- ``UserSetting_UpdateServerSettingVital`` (the entire ``UserSetting``
  group, 1 row) -- mixes real ``0x0B`` tags with
  ``CALL_UNCLASSIFIED:INDIRECT(...)``/``CALL_UNCLASSIFIED:0x00720FC0``/
  ``DYNAMIC_INTERLOCKED_DECREMENT_ECX_PLUS_0C_VTABLE_PLUS_04``/
  ``ATOMIC_INTERLOCKED_INCREMENT_ECX_PLUS_0C`` entries (5 of 6 rows
  unresolved).
- ``ReliveMarkerVital`` (0x3DD6, the Relive group's 2nd class) -- mixes
  real tags with ``SUBCALL:0x005DF250``/``SUBCALL:0x005F3490``/
  ``SUBCALL:0x005F34D0``/``CALL_UNCLASSIFIED:0x004B1C40``/
  ``DYNAMIC_INTERLOCKED_DECREMENT_ECX_PLUS_0C_VTABLE_PLUS_04``/
  ``ATOMIC_INTERLOCKED_INCREMENT_ECX_PLUS_0C`` entries -- 10 of its 26
  total rows (13 W + 13 R) are unresolved by this count
  (``awk -F'\t' '$1=="ReliveMarkerVital"'`` /
  ``awk -F'\t' '$1=="ReliveMarkerVital" && ($4~/CALL_UNCLASSIFIED/||
  $4~/SUBCALL:/||$4~/DYNAMIC_INTERLOCKED/||$4~/ATOMIC_/)'`` against
  ``external/PF_SERIALIZER_FIELDS.tsv``, re-run and corrected after a
  pf-adversary pass this round flagged the module's first draft as
  miscounting this as "6 of 15").
- ``ItemLockVital`` (a single-row group on its own, checked this round
  and rejected) -- mixes real ``0x05``/``0x0B``/``0x32`` tags with four
  ``PE_IMPORT_INVALID_PARAMETER_NOINFO_CALL`` rows and two
  ``CALL_UNCLASSIFIED:0x006CD400`` rows -- 6 of its 14 total rows are
  unresolved by this count (same awk method as above, substituting
  ``PE_IMPORT`` into the pattern; also corrected after the same
  pf-adversary pass -- the first draft said "4 of 14").
- ``DyeingModule_Client`` / ``AppraisalModule_Client`` -- both EMPTY
  (0-field) and fully tagged in ``PF_SERIALIZER_FIELDS.tsv``, but neither
  has any row in ``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv``
  -- no id-on-the-wire, so not a player action per ``docs/UI_LANE.md``
  item 1 (same exclusion precedent as
  ``BuildingCrystal_UpdateNextAbsorbTime`` in ``ui_buildingcrystal_wire.py``).
- ``Vehicle``/``Potion`` -- checked this round and found to have ZERO rows
  matching in ``VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` under
  those exact prefixes; the only related vital names on the wire are
  ``CVehicle*``/``CPotion*``, which ``prompts/COMMON_LANE_ROUND.md``'s grep-hint
  table assigns to LANE-A (``CVehicle``) and LANE-B (``CPotion``)
  explicitly. Not this lane's to itemize.
- ``NavigationEx_`` -- explicitly a LANE-A grep-hint
  (``prompts/COMMON_LANE_ROUND.md``: "A Trigger*/Teleport*/COnLand/CVehicle/
  Instance*/NavigationEx_*"). Not touched.

Field shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`` (grep ``^AppraisalVital``,
``^AppraisalStopVital``, ``^DyeingVitalRes``, ``^DyeingRemoveVital``,
``^DyeingShipVitalReq``, ``^DyeingVitalReq``, ``^ReliveVital``); W and R
rows are identical shape for every class here, each with its own distinct
span (``DyeingVitalReq`` shares its string-helper span with
``DeleteActorVital`` as explained above, but its own tag+length+field
byte sequence on the wire is still class-local).

Tag ``0x32`` = u64/qword and ``0x14`` = u32 are documented in
``ui_social_wire.py``'s module docstring / ``ui_tracepath_wire.py``. Tag
``0x08`` = u8 is also documented in ``ui_social_wire.py``'s TAG LEGEND
(``FINDINGS_R38_0x1B40_DECODED_LOGOUTVITAL.md``). Tag ``0x05`` is NEW to
this codebase -- no prior ``ui_*``/``gm/*`` module has needed it. It is a
plain fixed-length-1 tag per ``external/PF_TAG_CENSUS.tsv`` row
(``0x05  1  FIXED  56  UNKNOWN``), the same "FIXED length 1, proven_semantics
UNKNOWN" shape as the already-trusted ``0x08``/``0x0B`` u8 flavours -- this
module treats it as a third u8 tag flavour on that same basis, nothing more
(no claim about what value domain or sentinel meaning it carries).

A note on why the scalar tags here are NOT subject to the same
"helper-call-span" ambiguity that used to exclude ``DyeingVitalReq``:
every scalar row this module implements has ``gate_condition=ALWAYS`` and
a ``span_start``/``span_end`` matching the enclosing FUNCTION's own span
(not a narrower ``string_wire_call@...`` sub-span) -- these are direct
tag-byte-then-value-write instruction pairs recorded in place, the same
proof shape every earlier ``ui_*_wire.py`` module in this lane already
relies on for its ``0x0B``/``0x12``/``0x32``/``0x14`` fields. The RE-196
ambiguity is specific to the narrow-string HELPER CALL pattern
(``string_wire_call@<VA>`` with a helper ``target=0x0089A6D0``/
``0x0089A740``); ``DyeingVitalReq``'s field 2 uses exactly that pattern,
which is why it needed the separate SHA-256/VA cross-check above instead
of the scalar-tag reasoning here.

Grepped first, per ``AGENTS.md`` section 7's mandatory search, corrected
this round after a pf-adversary pass caught the first draft's blanket "no
hit for all ten" claim as false for two of them:

- ``AppraisalVital``, ``AppraisalStopVital``, ``DyeingVitalRes``,
  ``DyeingRemoveVital``, ``DyeingShipVitalReq``, ``DyeingVitalReq``, and
  ``ItemLockVital`` -- genuinely zero hits in ``CLIENT_RE_QUEUE.md``,
  ``GAME_TEST_QUEUE.md``, or ``archive/``.
- ``ReliveVital`` (implemented here) -- zero hits in ``CLIENT_RE_QUEUE.md``/
  ``GAME_TEST_QUEUE.md``, but several ``archive/`` hits discussing a death/
  rescue investigation that mentions the class by name without resolving
  any new field semantics; none of those hits touch this module's wire-shape
  scope or contradict it.
- ``UserSetting_UpdateServerSettingVital`` (excluded above) -- FOUND, not
  zero: ``CLIENT_RE_QUEUE.md`` records **197 real captured frames from 117
  capture files** for this class (Options -> Apply button), and
  ``GAME_TEST_QUEUE.md`` plus five ``archive/`` files also reference it.
  This capture evidence does not change the exclusion here (the class's
  own serializer rows still carry ``CALL_UNCLASSIFIED``/
  ``DYNAMIC_INTERLOCKED_*``/``ATOMIC_*`` entries, unrelated to whether real
  frames exist), but the earlier claim that no round had looked at this
  class was false -- real capture work already exists and should be the
  starting point for whoever eventually resolves this class's unclassified
  rows, not a blank slate.
- ``ReliveMarkerVital`` (excluded above) -- FOUND, not zero:
  ``GAME_TEST_QUEUE.md:10598`` and ``archive/`` note the closed ``RE-112``
  ticket, which independently confirms this class has ``NOT_OBSERVED``/
  ``0/0`` frame capture validation and no proven crosswalk to any quest --
  consistent with, not contradicting, this module's exclusion.

No prior module in ``src/`` or ``tests/`` names any of these ten classes,
in either case.

Same scope line as every sibling module in this lane's wire-shape batch:
"receive frame (decode) + compose the same shape back (encode), no
business logic". Nothing here claims what any field MEANS (dye color id,
appraisal target, relive marker id, etc.) -- the registry's
``proven_semantics`` column is ``UNKNOWN`` for every row of all seven classes,
and ``external/PF_FIELD_VALIDATION.tsv`` reads ``status=NOT_OBSERVED``,
``observed_frames=0`` for both ``W``/``R`` on every one of them, same as
every sibling wire-shape-only module this lane has already shipped. Not
wired into ``runtime.py`` or ``vital_walk.py``; wiring any of these is a
separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

APPRAISAL_VITAL_ID = 0x2AB1
APPRAISAL_STOP_VITAL_ID = 0x45CF
DYEING_VITAL_RES_ID = 0x2A00
DYEING_REMOVE_VITAL_ID = 0x3E1C
DYEING_SHIP_VITAL_REQ_ID = 0x441A
DYEING_VITAL_REQ_ID = 0x29E4
RELIVE_VITAL_ID = 0x1AD4

_TAG_U8_PRIMARY = 0x08
_TAG_U8_TERTIARY = 0x05  # new to this codebase -- see module docstring
_TAG_U32 = 0x14
_TAG_U64 = 0x32
_TAG_STRING8 = 0x44


@dataclass(frozen=True)
class AppraisalFields:
    """Wire order: u8, u32, u32 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv`` ``AppraisalVital`` rows)."""

    field1_u8: int
    field2_u32: int
    field3_u32: int


@dataclass(frozen=True)
class AppraisalStopFields:
    """No fields -- ``AppraisalStopVital`` is an EMPTY payload on both W
    and R (``PF_SERIALIZER_FIELDS.tsv`` row: tag ``EMPTY``, len 0,
    ``gate_condition=ALWAYS``)."""


@dataclass(frozen=True)
class DyeingVitalResFields:
    """Wire order: u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv`` ``DyeingVitalRes`` rows)."""

    field1_u8: int


@dataclass(frozen=True)
class DyeingRemoveFields:
    """Wire order: u64, u64 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv`` ``DyeingRemoveVital`` rows)."""

    field1_u64: int
    field2_u64: int


@dataclass(frozen=True)
class DyeingShipFields:
    """Wire order: u64, u32 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv`` ``DyeingShipVitalReq`` rows)."""

    field1_u64: int
    field2_u32: int


@dataclass(frozen=True)
class DyeingVitalReqFields:
    """Wire order: u64 (tag 0x32), string8 (tag 0x44) -- identical shape
    for W and R (``PF_SERIALIZER_FIELDS.tsv`` ``DyeingVitalReq`` rows,
    lines 5181-5184). ``field2_string8`` is kept opaque (``bytes``, not
    ``str``): see module docstring's ``DyeingVitalReq`` section for why."""

    field1_u64: int
    field2_string8: bytes


@dataclass(frozen=True)
class ReliveFields:
    """Wire order: u8 (tag 0x08), u8 (tag 0x05) -- identical shape for W
    and R (``PF_SERIALIZER_FIELDS.tsv`` ``ReliveVital`` rows)."""

    field1_u8: int
    field2_u8: int


def encode_appraisal_payload(fields: AppraisalFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8_PRIMARY, fields.field1_u8 & 0xFF])
    out += wire.u32tag(_TAG_U32, fields.field2_u32)
    out += wire.u32tag(_TAG_U32, fields.field3_u32)
    return bytes(out)


def decode_appraisal_payload(payload: bytes) -> AppraisalFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8_PRIMARY)
        field2, offset = wire.read_u32tag(payload, offset, _TAG_U32)
        field3, offset = wire.read_u32tag(payload, offset, _TAG_U32)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return AppraisalFields(field1, field2, field3)


def encode_appraisal_stop_payload(fields: AppraisalStopFields) -> bytes:
    del fields  # no fields to encode
    return b""


def decode_appraisal_stop_payload(payload: bytes) -> AppraisalStopFields | None:
    if len(payload) != 0:
        return None
    return AppraisalStopFields()


def encode_dyeing_vital_res_payload(fields: DyeingVitalResFields) -> bytes:
    return bytes([_TAG_U8_PRIMARY, fields.field1_u8 & 0xFF])


def decode_dyeing_vital_res_payload(
    payload: bytes,
) -> DyeingVitalResFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8_PRIMARY)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return DyeingVitalResFields(field1)


def encode_dyeing_remove_payload(fields: DyeingRemoveFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    return bytes(out)


def decode_dyeing_remove_payload(payload: bytes) -> DyeingRemoveFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return DyeingRemoveFields(field1, field2)


def encode_dyeing_ship_payload(fields: DyeingShipFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u32tag(_TAG_U32, fields.field2_u32)
    return bytes(out)


def decode_dyeing_ship_payload(payload: bytes) -> DyeingShipFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u32tag(payload, offset, _TAG_U32)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return DyeingShipFields(field1, field2)


def encode_dyeing_vital_req_payload(fields: DyeingVitalReqFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.string8tag(_TAG_STRING8, fields.field2_string8)
    return bytes(out)


def decode_dyeing_vital_req_payload(
    payload: bytes,
) -> DyeingVitalReqFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_string8tag(payload, offset, _TAG_STRING8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return DyeingVitalReqFields(field1, field2)


def encode_relive_payload(fields: ReliveFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8_PRIMARY, fields.field1_u8 & 0xFF])
    out += bytes([_TAG_U8_TERTIARY, fields.field2_u8 & 0xFF])
    return bytes(out)


def decode_relive_payload(payload: bytes) -> ReliveFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8_PRIMARY)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8_TERTIARY)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ReliveFields(field1, field2)
