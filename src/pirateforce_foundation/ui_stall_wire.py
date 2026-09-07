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
each direction. That is a consistency check worth having, but it is NOT
independent evidence: both sides are the static-image layer, derived from
the same binary, and the letter's own census is produced by the tool whose
function-boundary heuristic RE-294's nonclaim 3 declares unreliable in this
address neighbourhood (nonclaim 3 below shows it triple-counting a sibling
class). No client-observable layer exists for any of this.

Tag legend (each width taken from the table's own ``len`` column, not
guessed): ``0x08`` = u8, ``0x0B`` = u8, ``0x0F`` = u16, ``0x14`` = u32,
``0x19`` = u32, ``0x32`` = u64, wstring rows = tagged ``0x48`` +
u32 LE byte length + UTF-16LE (``ui_social_wire.wstring_tag``; the stale
``UNTAGGED_WSTRING16LE_LEN32LE`` spelling in the table is corrected to
``0x48`` for all six of these classes' string rows by
``notes_to_chief/reference_codex_attr/PF_A2_STRING_WIRE_TAG_DELTA.tsv``
base rows 6809/6831/6853/6873/6893/6903 -- ``CHANGED``).

Grepped first, per ``AGENTS.md`` section 7's mandatory search. The first
draft of this paragraph got two of its four claims wrong; these are the
re-measured ones (round ``gkxzei``, after pf-adversary):

* ``Stall`` in ``pf_bridge/external/`` -> the registry/priority/validation
  tables plus the serializer rows above. Two neighbouring ``Stall*``
  messages there are NOT vitals of this group and are not implemented:
  ``StallModule_Client`` (rows 6801-6806) and ``StallActorAttr``
  (6917-6918).
* ``grep -rn "Stall" pf_bridge/archive/`` -> **7 hits in 5 files**, not
  "``...R77.md:64`` only" as the first draft said. The one that mattered
  is ``archive/GAME_TEST_QUEUE_ARCHIVE_20260827_closed.md:971``, which
  points at the in-repo disassembly nonclaim 4 above now cites. Saying
  "only" is what turned a two-hop lookup into a false nonclaim.
* ``CLIENT_RE_QUEUE.md:1688`` = ``RE-294`` (the first draft said
  ``:1587``, inherited from ``docs/UI_LANE.md`` and never re-derived;
  ``:1587`` is an unrelated ticket). Its header still reads ``OPEN``:
  folding the result and flipping that header is LANE-K's, asked for in
  ``notes_to_chief/20260907_1358_LANE-UI-TO-K-re294-consumed-please-fold.md``.
* ``GAME_TEST_QUEUE.md:5988`` -> ``GT-262`` is still ``READY`` in the
  queue. The first draft called it "cancelled", which describes this
  lane's own cancel LETTER (``20260907_0456_LANE-UI-TO-K-gt262-cancel-
  with-reason.md``), not the queue it was sent to. Sending is not
  landing.
* ``grep -rn "Stall" src/pirateforce_foundation/`` before this file:
  0 hits (verified). Outside ``src/`` the same repo does carry Stall
  evidence -- ``reports/``, ``tools/``, ``docs/FUNCTIONAL_COVERAGE.json``
  -- which the first draft never searched, and which is where nonclaim
  4's correction came from.

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
3. **RE-294's ``13/13/3/3`` for ``0x0076A630`` is a census of all THREE
   serializers, not of that one.** This started as a "does not
   reconcile" nonclaim and a question to COO; pf-adversary reconciled it
   from committed artifacts in the same round, and this lane re-measured
   the arithmetic itself before accepting it. Counting the table's own
   real-tag rows, per direction, excluding the four member rows that
   belong to ``0x00766C00``:

       StallOperateVital   4 tagged + 1 string
       StallStartVital     4 tagged + 1 string
       StallOpenVital      5 tagged + 1 string
       sum                13 tagged + 3 strings, per direction

   and the table carries exactly 4 ``SUBCALL:0x00766C00`` rows in total
   (rows 6822, 6838, 6896, 6912) -- which is the letter's "called 4
   times". Five of the letter's numbers land on one hypothesis with no
   remainder: the RE runner's ``ret``-then-``int3`` boundary finder ran
   from ``0x0076A630`` through the whole neighbourhood instead of
   stopping at ``0x0076A738``. The table's own ``span_end`` column shows
   the same overshoot already happened to a sibling -- ``StallStartVital``
   is recorded as ``0x0076A740``-``0x0076AC12``, which swallows
   ``StallOpenVital``'s ``0x0076A960``-``0x0076AC12`` entirely -- and
   RE-294's nonclaim 3 confesses it at that address. So the table's
   4 + 1 for this class is right, this module follows it, and NO further
   RE ticket is needed. (The withdrawn question is kept in
   ``pf_bridge/notes_to_chief/20260907_1358_LANE-UI-ASK-COO-re294-operate-primitive-count-does-not-reconcile.md``,
   marked withdrawn, so the record shows what was asked and why it was
   dropped.)
4. **``StallOperateVital``'s field order is confirmed in THIS repository,
   which an earlier draft of this nonclaim wrongly called unconfirmed.**
   RE-294 declines to confirm R77's enumeration, and this module orders
   fields by the table's ``order`` column (string third, ``0x14`` fourth;
   file offsets agree, ``0x00369A65`` < ``0x00369A74``). What the first
   draft missed -- found by pf-adversary, re-read here before accepting --
   is that the instruction-level disassembly RE-294 says it did not do is
   already committed at
   ``reports/PF_USE_DROP_SELL001_ITEM_OPERATE_USE_DROP_SELL_STATIC_20260818.md:160-166``:
   ``0x0076a63f`` ``push 8`` @+0x14, ``0x0076a652`` ``push 0x32`` @+0x18,
   ``0x0076a65f`` ``call 0x89a810`` string @+0x24, ``0x0076a66c``
   ``push 0x14`` @+0x20, ``0x0076a68b`` ``push 0xb`` -- ascending address
   order, identical to what ``encode_stall_operate_payload`` emits. It is
   a live guard, not stale prose: ``tools/pf_use_drop_sell_static.py:286``,
   ``:302``, ``:568-581`` assert those exact bytes, and the span sha256
   there is character-for-character the one on the table's own rows
   (``3d1138e7...dbd501``). Both are the static-image layer -- two
   independently produced static artifacts agreeing, NOT a
   client-observable confirmation. R77's own prose enumeration is sorted
   by offset, not by wire order, which is why it must not be copied
   directly.
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


    NOTE (pf-adversary, round ``gkxzei``, re-measured here): because this
    loop runs until the buffer is exactly exhausted, the
    ``wire.require_exhausted`` call that follows it in
    ``decode_stall_start_payload`` / ``decode_stall_operate_payload`` can
    never fire -- it is defence in depth against a future edit, NOT the
    thing that rejects trailing bytes. What rejects them is this loop:
    trailing garbage is read as the start of another record and raises
    here. ``MemberReaderIsWhatRejectsTrailingBytesTests`` pins that, so
    the two decoders' trailing-byte tests cannot silently start passing
    for a different reason than their names say.

    WHO GUARANTEES ``payload``'S BOUNDARY (round ``rgmulk``, answering the
    design question pf-adversary left open on round ``gkxzei``): today,
    NOBODY -- and that is a statement about callers, not about this loop.
    Measured this round: ``grep -rn "decode_stall_" src/ tools/`` finds no
    caller outside ``tests/``, so no dispatch site has yet been asked to
    cut a frame for these two decoders. When one is written, this is its
    contract, in one sentence:

        ``payload`` MUST be exactly one frame body, because for these two
        classes the buffer end IS the member count.

    The consequence is not defence in depth, it is a silent wrong answer:
    a caller that slices short or long by a WHOLE record (22 bytes) gets a
    successful decode carrying one member too few or too many, with no
    exception anywhere -- ``RE-292`` says the class serializer reads a
    STREAM, so the frame's own bytes carry no end marker to catch it. Only
    a slice that lands mid-record, or off by anything that is not a
    multiple of 22, fails closed. ``WhoGuaranteesThePayloadBoundaryTests``
    pins both halves of that sentence with real bytes.

    The only in-frame cross-check that exists is
    ``member_count_field_agrees()``, and it covers ``StallStartVital``
    ONLY (``StallOperateVital``'s field5 is a presence flag, not a count --
    see that function's docstring). It reads a field this lane has NOT
    proven to be a count (nonclaim 2), so it stays a report a caller may
    consult, not a rule this module enforces: turning it into a rejection
    would be acting on an unproven reading. For ``StallOperateVital``
    there is no in-frame detector at all.
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
    """Decode one StallStartVital body.

    PRECONDITION: ``payload`` is exactly one frame body. The
    member list is delimited by the end of the buffer and by
    nothing else, so a caller that slices short or long by a whole
    member record gets a successful decode with the wrong member
    count and no error -- see ``_read_members``' "WHO GUARANTEES"
    note. Returns ``None`` when the bytes do not parse.
    """

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
    """Decode one StallOperateVital body.

    PRECONDITION: ``payload`` is exactly one frame body. The
    member list is delimited by the end of the buffer and by
    nothing else, so a caller that slices short or long by a whole
    member record gets a successful decode with the wrong member
    count and no error -- see ``_read_members``' "WHO GUARANTEES"
    note. Returns ``None`` when the bytes do not parse.
    """

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


def member_count_field_agrees(fields: StallStartFields) -> bool:
    """Report whether ``StallStartVital``'s trailing prefix u16 equals the
    member count.

    A REPORT, not a rule: nothing in this module calls it, no encoder or
    decoder consults it, and nothing is rejected when it returns
    ``False``. It exists so a caller that wants to act on the "field5 is
    the member count" reading can see a disagreement, while the reading
    itself stays unproven (nonclaim 2).

    ``StallOperateFields`` is deliberately NOT accepted here, though a
    first draft of this function did accept it. Its field5 is the ``0x0B``
    byte at ``STACK@0x0076A630+0x14`` (``push 0x0B`` at ``0x0076A68B``),
    and three committed artifacts read that byte as a PRESENCE flag, not
    a count: ``tools/pf_use_drop_sell_static.py:572-574``,
    ``reports/PF_USE_DROP_SELL001_...20260818.md:164``, and ``RE-292``,
    which measures the same tag/offset shape as a presence pair written
    from ``[this+0x14] != 0``. Reporting it as a count would have called
    every legitimate two-or-more-member frame a disagreement, and every
    empty one an agreement by coincidence. Found by pf-adversary, round
    ``gkxzei``; the three sources were re-read here before the argument
    type was narrowed.
    """

    return fields.field5_u16 == len(fields.members)
