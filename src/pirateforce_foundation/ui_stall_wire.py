"""``StallOpenVital`` (``0x2A3E``) / ``StallStartVital`` (``0x30FE``) /
``StallOperateVital`` (``0x3DE4``) -- pure encode/decode, wire shape only.

The player-facing feature behind these three classes is the personal market
stall: open it, put an item in a priced slot, another player buys. This
module is the wire layer only -- nothing here opens a stall, prices an item
or moves money.

Why this module can exist now, and could not one round ago
---------------------------------------------------------
``docs/UI_LANE.md``'s Stall row read ``NEEDS-RE-STATIC`` and said in as many
words: "Do NOT encode the prefix before that answer". The answer is
``RE-294 STALL-VITAL-TAIL-CALLS-WRITE-BYTES-OR-NOT-001``, result letter
``pf_bridge/notes_to_chief/20260907_1350_RE-294-RESULT-stallopen-writes-
nothing-extra-stallstart-writes-via-766C00.md`` (consumed by this lane in
round ``gkxzei``). It answers the one question the ticket asked -- do the
``PE_IMPORT_*`` / ``CALL_UNCLASSIFIED:`` / ``MUTATING_CHAIN_*`` /
``ATOMIC_*`` call sites after the tagged prefix write bytes into the same
serializer stream? -- with, per class:

* ``StallOpenVital`` (serializer ``0x0076A960``): **no**. A census of every
  call in the function found none that takes the stream pointer as an
  argument except the four tagged/string primitives themselves
  (``0x0089A600``/``0x0089A640`` write/read tagged field, ``0x0089A810``/
  ``0x0089A880`` write/read string). The ``ds:0x00C3B4C0`` calls are MSVC's
  invalid-parameter reporter, ``0x0088D050``/``0x0088D060`` are
  ``InterlockedIncrement``/``Decrement`` on a refcount at ``this+0x0C``, and
  ``0x0068E8B0`` takes two stack locals, not the stream.
* ``StallStartVital`` (``0x0076A740``) and ``StallOperateVital``
  (``0x0076A630``): **yes**, but only through ``SUBCALL:0x00766C00``, which
  the same RE round decoded end to end: it is short, self-contained
  (``ret 8``, no further subcall) and writes exactly four tagged fields per
  container member -- ``0x32`` (8) from ``elem+0x10`` at ``0x00766C19``,
  ``0x14`` (4) from ``elem+0x18`` at ``0x00766C28``, ``0x0F`` (2) from
  ``elem+0x1C`` at ``0x00766C37``, ``0x19`` (4) from ``elem+0x20`` at
  ``0x00766C46``. The read side (``0x00766C50``) mirrors it field for field
  via ``0x0089A640``. So there is nothing left unresolved to encode around.

The same letter corrects a column error this lane made in
``docs/UI_LANE.md`` and in the RE ticket body: ``0x0076AC20`` /
``0x0076ACB0`` / ``0x0076A080`` are the ``getter_va`` column of
``external/PF_PROTOCOL_REGISTRY.tsv`` (two instructions, ``mov ax, ds:...;
ret`` -- a class-id getter, writing nothing), NOT serializers, and the
``0x0076B0D0`` all three share is the ``handler``, not a shared serializer.
The three serializer VAs are the ones named above. Fixed in the row this
module's docstring is cited from.

Field shapes: copied row for row from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv``, ``StallStartVital``
``:6807-6850`` (44 rows), ``StallOpenVital`` ``:6851-6890`` (40),
``StallOperateVital`` ``:6891-6916`` (26) -- boundaries counted in this
round, not inherited: ``docs/UI_LANE.md`` carried the two outer numbers
only, and this lane's first split of them (``:6848``/``:6849``) was wrong
by two rows in both directions. Every row NOT implemented below is one of the
non-writing categories RE-294 cleared; no row carrying a real tag byte is
skipped, in either direction. Counted against RE-294's own call census for
``StallOpenVital`` -- 5 tagged writes / 5 tagged reads / 1 string write /
1 string read -- the tagged rows this module encodes are exactly 5 + 1 in
each direction, which is the strongest independent check available on this
class without a capture. (See the nonclaims for the class where that
cross-check does NOT line up.)

Tag legend (each width taken from the table's own ``len`` column, not
guessed): ``0x08`` = u8, ``0x0B`` = u8, ``0x0F`` = u16, ``0x14`` = u32,
``0x19`` = u32, ``0x32`` = u64, wstring rows = tagged ``0x48`` +
u32 LE byte length + UTF-16LE (``ui_social_wire.wstring_tag``; the stale
``UNTAGGED_WSTRING16LE_LEN32LE`` spelling in the table is corrected to
``0x48`` for all six of these classes' string rows by
``notes_to_chief/reference_codex_attr/PF_A2_STRING_WIRE_TAG_DELTA.tsv``
base rows 6809/6831/6853/6873/6893/6903 -- ``CHANGED``).

Grepped first, per ``AGENTS.md`` section 7's mandatory search, before
writing a line: ``Stall`` in ``pf_bridge/external/`` -> the three registry/
priority/validation tables and the serializer rows above; in
``pf_bridge/archive/`` -> ``...R77.md:64`` only, which names
``0x0076A630`` as ``StallOperateVital``'s serializer and agrees with the
registry column (RE-294 says the two sources do not conflict -- the
``direct_call_not_proven_serializer`` label meant "unproven", not
"disproven"). ``CLIENT_RE_QUEUE.md:1587`` = ``RE-294`` itself, now
answered. ``GAME_TEST_QUEUE.md``: no live Stall entry (``GT-262`` was
cancelled, ``20260907_0456_LANE-UI-TO-K-gt262-cancel-with-reason.md``).
``grep -rn "Stall" src/pirateforce_foundation/`` before this file: 0 hits.

Scope, in ``CORE-REQUEST 1120``'s own words and identical to every sibling
module in this batch: "รับเฟรม (decode) + ตอบ ack/error frame ที่วางเปล่า
... ไม่ใช่การทำ business logic เต็ม". Not wired into ``runtime.py`` or
``vital_walk.py`` -- both are outside this lane's write zone and wiring
either class is a separate ``CORE-REQUEST``.

nonclaims -- what this module does NOT prove
--------------------------------------------
1. **No field here has a proven meaning.** ``external/PF_FIELD_VALIDATION
   .tsv`` reads ``status=NOT_OBSERVED``, ``observed_frames=0`` for all
   three classes in both directions, and ``proven_semantics`` is
   ``UNKNOWN`` for every row, so fields are named positionally
   (``field1_u64`` ...), never ``stall_id`` or ``price``. Nothing here
   claims which side sends which class, or that any class acks another.
2. **The trailing u16 is not proven to be the member count.** In
   ``StallStartVital`` it is written from ``PHI(DEREF(DEREF(OBJ+0x4C))|
   DEREF(STACK+0x1C))+0xC`` -- ``+0xC`` of the same container object whose
   members the loop then writes -- which makes "it is the count" the
   obvious reading. It is a reading, not a measurement. So
   ``decode_stall_start_payload`` reads member records until the buffer is
   exhausted and does NOT consult that field, and it never rewrites the
   field to match: a payload whose field5 disagrees with its member count
   round-trips unchanged, and ``member_count_field_agrees`` reports the
   disagreement without deciding anything. The same shape appears in
   ``StallOpenVital`` W9/R13 with no loop after it.
3. **``StallOperateVital``'s primitive census does not reconcile.**
   RE-294 reports "primitive 13/13/3/3" for ``0x0076A630`` while the
   serializer table lists 4 tagged + 1 string row per direction for that
   class (and the function's own span, ``0x0076A630``-``0x0076A738``, is
   264 bytes). The two numbers are not made to agree here, and this
   module follows the TABLE, which is the house layout source of truth.
   The letter's own nonclaim 3 says its function-boundary heuristic
   overshot into a neighbouring constructor on the sibling class, which
   is one candidate explanation and is NOT asserted to be the answer.
   Question sent to COO in round ``gkxzei``'s letter.
4. **``StallOperateVital``'s per-field layout is NOT R77's.** RE-294
   explicitly declines to confirm R77's ``u8 0x08@+0x14, qword 0x32@+0x18,
   u32 0x14@+0x20, string@+0x24`` ordering ("อย่าเพิ่งเอาเลย์เอาต์ของ
   R77 ไปใช้"). This module orders the fields by the table's own ``order``
   column, which puts the string third and the ``0x14`` fourth -- the
   file offsets agree with that order (``0x00369A65`` < ``0x00369A74``).
5. **No client has ever seen a byte of this.** Static only: there is a
   wire/DB layer here and NO client-observable layer. Nothing below is
   evidence that a stall opens on screen.
6. **The ``vital_version`` byte is not included in these payloads.**
   ``RE-292`` (same RE round) measures that every frame carries a leading
   ``vital_version`` u8 under tag ``0x0B``; the ``*_VITAL_VERSION``
   constants below are the same unproven ``0`` default every sibling
   module in this lane declares, and the payload encoders start after
   that byte, exactly as the siblings do.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

STALL_OPEN_VITAL_ID = 0x2A3E
STALL_START_VITAL_ID = 0x30FE
STALL_OPERATE_VITAL_ID = 0x3DE4

# Unproven default (see ui_party_wire.py's version-byte note, and nonclaim 6).
STALL_OPEN_VITAL_VERSION = 0
STALL_START_VITAL_VERSION = 0
STALL_OPERATE_VITAL_VERSION = 0

_TAG_U8_A = 0x08
_TAG_U8_B = 0x0B
_TAG_U16 = 0x0F
_TAG_U32_A = 0x14
_TAG_U32_B = 0x19
_TAG_U64 = 0x32


@dataclass(frozen=True)
class StallMemberRecord:
    """One container member, as written by ``SUBCALL:0x00766C00``.

    Wire order u64, u32, u16, u32 -- the four writes RE-294 decoded at
    ``0x00766C19`` / ``0x00766C28`` / ``0x00766C37`` / ``0x00766C46``,
    sourced from ``elem+0x10`` / ``+0x18`` / ``+0x1C`` / ``+0x20``. The
    same helper serves ``StallStartVital`` (``PF_SERIALIZER_FIELDS.tsv``
    W12-W15 / R15-R18) and ``StallOperateVital`` (W7-W10 / R10-R13), which
    is why the record is defined once here rather than per class.
    """

    field1_u64: int
    field2_u32: int
    field3_u16: int
    field4_u32: int


@dataclass(frozen=True)
class StallOpenFields:
    """Wire order: u64, u16, wstring, u32, u16, u16 -- identical shape for
    W and R (``PF_SERIALIZER_FIELDS.tsv`` W1-W5 + W9, R8-R13).

    No member records: ``StallOpenVital`` never calls ``0x00766C00``, which
    is the half of RE-294 that came back a flat "writes nothing extra".
    """

    field1_u64: int
    field2_u16: int
    field3_wstring: str
    field4_u32: int
    field5_u16: int
    field6_u16: int


@dataclass(frozen=True)
class StallStartFields:
    """Wire order: u8, u16, wstring, u16, u16, then N member records
    (``PF_SERIALIZER_FIELDS.tsv`` W1-W4 + W8 + W11-W15, R7-R11 + R14-R18).

    ``members`` may legitimately be empty -- an empty container writes the
    prefix and stops.
    """

    field1_u8: int
    field2_u16: int
    field3_wstring: str
    field4_u16: int
    field5_u16: int
    members: tuple[StallMemberRecord, ...] = ()


@dataclass(frozen=True)
class StallOperateFields:
    """Wire order: u8, u64, wstring, u32, u8, then N member records
    (``PF_SERIALIZER_FIELDS.tsv`` W1-W5 + W6-W10, R1-R5 + R9-R13).

    Note the two u8 tags differ: field1 is ``0x08``, field5 is ``0x0B``.
    """

    field1_u8: int
    field2_u64: int
    field3_wstring: str
    field4_u32: int
    field5_u8: int
    members: tuple[StallMemberRecord, ...] = ()


def _encode_member(record: StallMemberRecord) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, record.field1_u64)
    out += wire.u32tag(_TAG_U32_A, record.field2_u32)
    out += wire.u16tag(_TAG_U16, record.field3_u16)
    out += wire.u32tag(_TAG_U32_B, record.field4_u32)
    return bytes(out)


def _read_member(
    payload: bytes, offset: int
) -> tuple[StallMemberRecord, int]:
    field1, offset = wire.read_u64tag(payload, offset, _TAG_U64)
    field2, offset = wire.read_u32tag(payload, offset, _TAG_U32_A)
    field3, offset = wire.read_u16tag(payload, offset, _TAG_U16)
    field4, offset = wire.read_u32tag(payload, offset, _TAG_U32_B)
    return StallMemberRecord(field1, field2, field3, field4), offset


def _read_members(
    payload: bytes, offset: int
) -> tuple[tuple[StallMemberRecord, ...], int]:
    """Read member records until the buffer runs out.

    Deliberately NOT driven by any count field -- see nonclaim 2. A
    trailing byte that does not start a complete record raises, so a
    truncated or padded payload fails closed rather than decoding to a
    short member list.
    """

    members: list[StallMemberRecord] = []
    while offset < len(payload):
        record, offset = _read_member(payload, offset)
        members.append(record)
    return tuple(members), offset


def encode_stall_open_payload(fields: StallOpenFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u16tag(_TAG_U16, fields.field2_u16)
    out += wire.wstring_tag(fields.field3_wstring)
    out += wire.u32tag(_TAG_U32_A, fields.field4_u32)
    out += wire.u16tag(_TAG_U16, fields.field5_u16)
    out += wire.u16tag(_TAG_U16, fields.field6_u16)
    return bytes(out)


def decode_stall_open_payload(payload: bytes) -> StallOpenFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u16tag(payload, offset, _TAG_U16)
        field3, offset = wire.read_wstring_tag(payload, offset)
        field4, offset = wire.read_u32tag(payload, offset, _TAG_U32_A)
        field5, offset = wire.read_u16tag(payload, offset, _TAG_U16)
        field6, offset = wire.read_u16tag(payload, offset, _TAG_U16)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return StallOpenFields(field1, field2, field3, field4, field5, field6)


def encode_stall_start_payload(fields: StallStartFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8_A, fields.field1_u8 & 0xFF])
    out += wire.u16tag(_TAG_U16, fields.field2_u16)
    out += wire.wstring_tag(fields.field3_wstring)
    out += wire.u16tag(_TAG_U16, fields.field4_u16)
    out += wire.u16tag(_TAG_U16, fields.field5_u16)
    for record in fields.members:
        out += _encode_member(record)
    return bytes(out)


def decode_stall_start_payload(payload: bytes) -> StallStartFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8_A)
        field2, offset = wire.read_u16tag(payload, offset, _TAG_U16)
        field3, offset = wire.read_wstring_tag(payload, offset)
        field4, offset = wire.read_u16tag(payload, offset, _TAG_U16)
        field5, offset = wire.read_u16tag(payload, offset, _TAG_U16)
        members, offset = _read_members(payload, offset)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return StallStartFields(field1, field2, field3, field4, field5, members)


def encode_stall_operate_payload(fields: StallOperateFields) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8_A, fields.field1_u8 & 0xFF])
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += wire.wstring_tag(fields.field3_wstring)
    out += wire.u32tag(_TAG_U32_A, fields.field4_u32)
    out += bytes([_TAG_U8_B, fields.field5_u8 & 0xFF])
    for record in fields.members:
        out += _encode_member(record)
    return bytes(out)


def decode_stall_operate_payload(payload: bytes) -> StallOperateFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8_A)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field3, offset = wire.read_wstring_tag(payload, offset)
        field4, offset = wire.read_u32tag(payload, offset, _TAG_U32_A)
        field5, offset = wire.read_u8tag(payload, offset, _TAG_U8_B)
        members, offset = _read_members(payload, offset)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return StallOperateFields(field1, field2, field3, field4, field5, members)


def member_count_field_agrees(
    fields: StallStartFields | StallOperateFields,
) -> bool:
    """Report whether the trailing prefix u16 equals the member count.

    A REPORT, not a rule: nothing in this module calls it, no encoder or
    decoder consults it, and neither direction is rejected when it returns
    ``False``. It exists so a caller that wants to act on the "field5 is
    the member count" reading can see the disagreement, while the reading
    itself stays unproven (nonclaim 2). ``StallOperateFields``' field5 is
    a u8 under a different tag and is included here for the same
    report-only purpose, not because the two classes are claimed to use
    the field the same way.
    """

    declared = (
        fields.field5_u16
        if isinstance(fields, StallStartFields)
        else fields.field5_u8
    )
    return declared == len(fields.members)
