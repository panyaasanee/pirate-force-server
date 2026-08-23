"""LEARN-SKILL-RESULT-001 -- server-side encoder for the CLearnSkillResultVital
0x673C nested-record body (HYP-PF-033).

Where the project stops without this module
-------------------------------------------
STATS-PROG-001 named five progression verbs and measured "0 encoders, 0
dispatch" for all of them; GT-050 (closed 2026-08-24, letter
pf_bridge/notes_to_chief/20260824_0055_GT050-RESULT-CLEARNRESULT-CLOSED-
TRIGGER-DIRECTION-UNRESOLVED.md) then closed the WIRE SHAPE of exactly one of
them, the result vital 0x673C, byte-exactly from the read-only client image.
Until this module nothing in src/ could compose one byte of it, so the
attended question "does the client accept / show anything for a learn-skill
result frame" had nothing to run against.  This lane builds the server side of
exactly the proven shape and nothing more.

What GT-050 proved (static, adversarially re-derived; do not re-prove)
----------------------------------------------------------------------
All spans are client-image VAs against the read-only image SHA-256
9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623:

  * top serializer [0x00756100,0x00756156), len 86, SHA-256
    c6a66b70cc80a48b84ecc433f10aa7696eb8c2a261affd677692a6ab9c90fe94;
  * nested WRITE loop [0x00755D30,0x00755E1E), len 238, SHA-256
    35eaeb4718fc91dcc4b22ab13a0b1d9557834f83c735befb01cfe01bc6654944;
  * nested READ loop [0x00756070,0x007560FB), len 139, SHA-256
    0c78744ea4659a8a0d36a8a4015a4a9ce5904f15ccea7e8b14ccdcfbad70f3b3;
  * the WRITE and READ loops agree on one body order, implemented verbatim
    here:

        u16 tag 0x12  count
        repeat count times (record object stride = 12):
          u32 tag 0x14  record+0
          u16 tag 0x12  record+4
          u32 tag 0x14  record+8
        u8  tag 0x0B  object+0x2C

  * the seven _invalid_parameter_noinfo sites inside the WRITE loop are
    container begin/end/null/range error calls, not wire fields, and the
    post-READ call 0x0077FC30 is a stride-12 vector append, not a serializer.

NONCLAIMS -- read these before using one symbol from this file
--------------------------------------------------------------
  * The SEMANTICS of the three record members are NOT known.  They are
    encoded as opaque declared triples and named by wire position only
    (record_u32_0 / record_u16_4 / record_u32_8).  Nothing here calls any of
    them a skill id, a level, a slot or anything else, and nothing may.
  * The semantics of the trailing u8 at object+0x2C are NOT known.  The sweep
    sends both 0 and 1 precisely because nobody can say what either means.
  * The inbound direction is NOT implemented: no handler, no decoder-dispatch
    and no learn rule exists for the client->server CLearnSkillVital 0x36AA
    request, and this lane never answers one.
  * The per-vital u8 version byte in the collection envelope is OUR DESIGN
    (0, the value every other vital lane in this tree sends absent a proven
    pin); no capture or static pin fixes it for 0x673C.
  * Nothing is claimed about the ORIGINAL server, which is gone forever:
    the step plan, the record values, the spacing and the trigger policy are
    this project's own design.
  * NO CLIENT HAS EVER SEEN ONE OF THESE FRAMES.  That half is an attended
    GT ticket, queued and not run, and no coverage row grade moves on this
    module alone.

Fail-closed contract
--------------------
Refused with ``ValueError`` and no bytes: a records container that is not a
tuple of this module's own record type, a record member that is not a plain
``int`` (``bool`` included), a member outside its wire width, a record count
outside u16, a trailing byte that is not a plain ``int`` in 0..255, and a
step index outside the pinned plan.  The decoder refuses, by named reason,
a wrong tag at any of the five tag positions, any truncation, and any byte
left over after the trailing u8.  Every composed payload is re-decoded and
compared with the request before the bytes are returned, and every sweep
composition is hash-pinned in the module AND in the scenario file from the
same live computation.  No database call exists on any path in this file.

Opt-in, test-only
-----------------
``production_allowed`` is False in the module and in the scenario file, the
scenario loads through an exact allowlist, and with no scenario handed in the
dispatch branch does not exist: nothing in default mode composes one byte of
this.  ``database_write`` is ``none`` -- learned skills have no table, and
this lane deliberately does not open one.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


LEARN_SKILL_RESULT_CHECKPOINT = "LEARN-SKILL-RESULT-001"
LEARN_SKILL_RESULT_HYPOTHESIS_ID = "HYP-PF-033"
production_allowed = False

# ---------------------------------------------------------------- static pins
# Client-binary provenance closed by GT-050; carried as documentation-grade
# constants and never dereferenced.  The spans are re-stated in the module
# docstring with their lengths and byte-range bounds.
LEARN_SKILL_RESULT_VITAL_ID = 0x673C
LEARN_SKILL_RESULT_SERIALIZER_VA = 0x756100
LEARN_SKILL_RESULT_SERIALIZER_LEN = 86
LEARN_SKILL_RESULT_SERIALIZER_SHA256 = (
    "c6a66b70cc80a48b84ecc433f10aa7696eb8c2a261affd677692a6ab9c90fe94"
)
LEARN_SKILL_RESULT_WRITE_LOOP_VA = 0x755D30
LEARN_SKILL_RESULT_WRITE_LOOP_LEN = 238
LEARN_SKILL_RESULT_WRITE_LOOP_SHA256 = (
    "35eaeb4718fc91dcc4b22ab13a0b1d9557834f83c735befb01cfe01bc6654944"
)
LEARN_SKILL_RESULT_READ_LOOP_VA = 0x756070
LEARN_SKILL_RESULT_READ_LOOP_LEN = 139
LEARN_SKILL_RESULT_READ_LOOP_SHA256 = (
    "0c78744ea4659a8a0d36a8a4015a4a9ce5904f15ccea7e8b14ccdcfbad70f3b3"
)

# The per-vital version byte of the one-vital collection envelope.  OUR
# DESIGN, not a pin: no capture or static evidence fixes this value for
# 0x673C, and 0 is what every other vital lane in this tree sends absent a
# proven pin.  Stated in the module docstring nonclaims.
LEARN_SKILL_RESULT_VITAL_VERSION = 0

# The proven body geometry, exactly as the W/R loops agree on it.
LEARN_SKILL_RESULT_COUNT_TAG = 0x12          # u16 record count
LEARN_SKILL_RESULT_RECORD_U32_TAG = 0x14     # record+0 and record+8
LEARN_SKILL_RESULT_RECORD_U16_TAG = 0x12     # record+4
LEARN_SKILL_RESULT_TRAILING_TAG = 0x0B       # u8 at object+0x2C
LEARN_SKILL_RESULT_RECORD_OBJECT_STRIDE = 12
LEARN_SKILL_RESULT_TRAILING_OBJECT_OFFSET = 0x2C
# On the wire each record is tag+4 / tag+2 / tag+4 = 13 bytes, and the fixed
# overhead is the 3-byte count header plus the 2-byte trailing u8.
LEARN_SKILL_RESULT_RECORD_WIRE_SIZE = 13
LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE = 5

# One-vital GSCN_RunTimeProtocolRes v4 collection geometry (v141
# make_runtime_vitals), identical to the geometry the chat and stats lanes
# pin: nested payload at a fixed 20-byte offset, 22 bytes of envelope.
LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET = 20
LEARN_SKILL_RESULT_PC_OVERHEAD = 22
LEARN_SKILL_RESULT_PC_VITAL_ID_SLICE = slice(16, 18)

# Rejection reasons; every one of them means "no bytes, no reply, no write".
LEARN_SKILL_RESULT_REJECTIONS = (
    "records_not_a_tuple_of_records",
    "record_value_type_not_integer",
    "record_value_outside_field_width",
    "record_count_outside_u16",
    "trailing_byte_type_not_integer",
    "trailing_byte_outside_u8",
    "unknown_step_label",
    "truncated_payload",
    "wrong_count_tag",
    "wrong_record_u32_tag",
    "wrong_record_u16_tag",
    "wrong_trailing_tag",
    "trailing_bytes_after_object",
)


@dataclass(frozen=True)
class LearnSkillResultRecord:
    """One opaque declared record triple, named by wire position ONLY.

    The three member names encode nothing but the proven object offset and
    width; the meanings are unknown and deliberately unnamed (see the module
    docstring nonclaims).
    """

    record_u32_0: int
    record_u16_4: int
    record_u32_8: int


@dataclass(frozen=True)
class LearnSkillResultHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float


# ------------------------------------------------------------ the sweep plan
LEARN_SKILL_RESULT_SCENARIO_ID = "learn_skill_result_hypothesis_learn_sweep"

# The record triples the sweep declares.  The VALUES are OUR DESIGN and are
# chosen only to be tellable-apart and to exercise the proven wire widths:
# an all-zero record, an all-maximum record (the u32/u16/u32 boundaries),
# and two mid-range records with three distinct member values each.  None of
# them is claimed to be a skill id, a level, or anything else.
LEARN_SKILL_RESULT_RECORD_A = LearnSkillResultRecord(1000001, 11, 2000001)
LEARN_SKILL_RESULT_RECORD_ZERO = LearnSkillResultRecord(0, 0, 0)
LEARN_SKILL_RESULT_RECORD_MAX = LearnSkillResultRecord(
    0xFFFFFFFF, 0xFFFF, 0xFFFFFFFF,
)
LEARN_SKILL_RESULT_RECORD_B = LearnSkillResultRecord(0x12345678, 0x1234, 0x60606060)

# Five frames per accepted trigger: the count=0 edge with trailing 0, then
# count=1 with trailing 0, then the SAME count=1 body with only the trailing
# byte moved to 1 (isolating the one unexplained byte), then the count=3
# multi-record body with varied values under trailing 0 and again under
# trailing 1.  Both trailing values appear -- on the count=1 and count=3
# bodies -- because the byte's meaning is unknown.
LEARN_SKILL_RESULT_STEPS = (
    ("COUNT0_TRAIL0", (), 0),
    ("COUNT1_TRAIL0", (LEARN_SKILL_RESULT_RECORD_A,), 0),
    ("COUNT1_TRAIL1", (LEARN_SKILL_RESULT_RECORD_A,), 1),
    (
        "COUNT3_TRAIL0",
        (
            LEARN_SKILL_RESULT_RECORD_ZERO,
            LEARN_SKILL_RESULT_RECORD_MAX,
            LEARN_SKILL_RESULT_RECORD_B,
        ),
        0,
    ),
    (
        "COUNT3_TRAIL1",
        (
            LEARN_SKILL_RESULT_RECORD_ZERO,
            LEARN_SKILL_RESULT_RECORD_MAX,
            LEARN_SKILL_RESULT_RECORD_B,
        ),
        1,
    ),
)
LEARN_SKILL_RESULT_STEP_ORDER = tuple(
    label for label, _records, _trailing in LEARN_SKILL_RESULT_STEPS
)
LEARN_SKILL_RESULT_STEP_RECORDS = {
    label: records for label, records, _trailing in LEARN_SKILL_RESULT_STEPS
}
LEARN_SKILL_RESULT_STEP_TRAILING = {
    label: trailing for label, _records, trailing in LEARN_SKILL_RESULT_STEPS
}

# Seconds between consecutive sends.  The frozen V141 sender treats the
# fourth action-tuple field as a gap on a cumulative deadline (send_deadline
# += delay, then sleep to it), so the first frame carries 0.0 and each later
# frame the full spacing -- exactly the stats-sweep convention.
LEARN_SKILL_RESULT_SPACING_SECONDS = 3.0
LEARN_SKILL_RESULT_FIRST_DELAY_SECONDS = 0.0
LEARN_SKILL_RESULT_ACTION_LABEL_PREFIX = "HYP_PF_033_LEARN_SKILL_RESULT_"

# ----------------------------------------------------------------- the pins
# Computed by running THIS encoder deterministically (the composition takes
# no per-character input, so the pins are absolute); every value below is a
# sha256 of bytes this encoder produced, never a value copied in.
LEARN_SKILL_RESULT_PROBE_PAYLOAD_SHA256 = {
    "COUNT0_TRAIL0": (
        "3471BA20F3F76A77DB882AF849AF4FF7BA0567DA391A120F566FA71B855CEB25"
    ),
    "COUNT1_TRAIL0": (
        "F04EF2383EB1F8C7E14B9F96D6DD5FC097D2D148BEB1ED7CC2BA4D95324B46BE"
    ),
    "COUNT1_TRAIL1": (
        "BEA315E33E5C8403AF9A902F67C4C574224CAF581E08289043D79B580C473073"
    ),
    "COUNT3_TRAIL0": (
        "55BAE4B6C9522D978F449A0A574FC8C5B594AC35523C0841644ED09E0BE47C59"
    ),
    "COUNT3_TRAIL1": (
        "E249658720DCE4D6CBE6E26A9400336D13FBBCEF8AE91FC759EBCD8A82009FEB"
    ),
}
LEARN_SKILL_RESULT_PROBE_PC_SHA256 = {
    "COUNT0_TRAIL0": (
        "A5A485A286789275A3C147465F36FCA60B4A60BA215BC2B3AD2C9425CF951B6F"
    ),
    "COUNT1_TRAIL0": (
        "037D795209105CA1FDA42AF5B295561828C7CCB1A802E0FF5891FB01F5F75AB2"
    ),
    "COUNT1_TRAIL1": (
        "1AC59863E7D8C5EF4DAC479B56B7D08703889B0AEC00938E039A83A550E7A353"
    ),
    "COUNT3_TRAIL0": (
        "43E0CA9DA70CB2A95467FF3E88D4485E128547943FF8B87F77EEE78E352BF926"
    ),
    "COUNT3_TRAIL1": (
        "6707ED55E005B1A7BA79BCCAF9CD32908E5A215BE17DAC02D0DAFCB6A9119479"
    ),
}
LEARN_SKILL_RESULT_PROBE_FRAME_SHA256 = {
    "COUNT0_TRAIL0": (
        "B92F0DBE0DD2B6FB01DBFB5419C2BCCB97A9401116BFDB28AE6B926362268F14"
    ),
    "COUNT1_TRAIL0": (
        "0A6A7D93EB7CECF09BD657252AE10FEBB83271AA853208B85D9BC734916F7A7A"
    ),
    "COUNT1_TRAIL1": (
        "1A213A98F458DE2A12BF664533C0D918AAB7B890EDA7C096D6DF150FC9DF3D77"
    ),
    "COUNT3_TRAIL0": (
        "0EE12033D6A917B75B578AD2E4BF1935D597FB5D8CE5D47224EC63BB81CE718A"
    ),
    "COUNT3_TRAIL1": (
        "C445872E4EA632567B85D06001CE951532F42B0FA058DAC9DA40CF5E60612D87"
    ),
}
LEARN_SKILL_RESULT_PROBE_PAYLOAD_SIZE = {
    "COUNT0_TRAIL0": 5,
    "COUNT1_TRAIL0": 18,
    "COUNT1_TRAIL1": 18,
    "COUNT3_TRAIL0": 44,
    "COUNT3_TRAIL1": 44,
}
LEARN_SKILL_RESULT_PROBE_PC_SIZE = {
    "COUNT0_TRAIL0": 27,
    "COUNT1_TRAIL0": 40,
    "COUNT1_TRAIL1": 40,
    "COUNT3_TRAIL0": 66,
    "COUNT3_TRAIL1": 66,
}
LEARN_SKILL_RESULT_PROBE_FRAME_SIZE = {
    "COUNT0_TRAIL0": 37,
    "COUNT1_TRAIL0": 50,
    "COUNT1_TRAIL1": 50,
    "COUNT3_TRAIL0": 77,
    "COUNT3_TRAIL1": 77,
}


# ---------------------------------------------------------------- self-guards
def _require_step_plan() -> None:
    """The pinned plan must keep asking the questions it was built to ask."""
    if len(set(LEARN_SKILL_RESULT_STEP_ORDER)) != len(
        LEARN_SKILL_RESULT_STEP_ORDER
    ):
        raise RuntimeError("HYP-PF-033 duplicate step label")
    counts = {
        len(LEARN_SKILL_RESULT_STEP_RECORDS[label])
        for label in LEARN_SKILL_RESULT_STEP_ORDER
    }
    if not {0, 1, 3} <= counts:
        raise RuntimeError(
            "HYP-PF-033 the sweep must keep the count 0 / 1 / 3 edges"
        )
    trailings = {
        LEARN_SKILL_RESULT_STEP_TRAILING[label]
        for label in LEARN_SKILL_RESULT_STEP_ORDER
    }
    if trailings != {0, 1}:
        raise RuntimeError(
            "HYP-PF-033 the sweep must send both trailing values 0 and 1"
        )
    if (
        LEARN_SKILL_RESULT_STEP_RECORDS["COUNT1_TRAIL0"]
        != LEARN_SKILL_RESULT_STEP_RECORDS["COUNT1_TRAIL1"]
    ):
        raise RuntimeError(
            "HYP-PF-033 the trailing-byte pair must differ in the trailing "
            "byte only"
        )
    for label in LEARN_SKILL_RESULT_STEP_ORDER:
        for record in LEARN_SKILL_RESULT_STEP_RECORDS[label]:
            if type(record) is not LearnSkillResultRecord:
                raise RuntimeError("HYP-PF-033 step plan record type drift")
    multi = LEARN_SKILL_RESULT_STEP_RECORDS["COUNT3_TRAIL0"]
    if len(set(multi)) != len(multi):
        raise RuntimeError("HYP-PF-033 multi-record step repeats a record")
    if LEARN_SKILL_RESULT_RECORD_MAX not in multi:
        raise RuntimeError(
            "HYP-PF-033 the multi-record step must exercise the width maxima"
        )
    if LEARN_SKILL_RESULT_RECORD_ZERO not in multi:
        raise RuntimeError(
            "HYP-PF-033 the multi-record step must exercise the all-zero record"
        )


def _require_int(value: Any, width_bits: int, reason_type: str,
                 reason_range: str) -> int:
    if type(value) is not int or type(value) is bool:
        raise ValueError("learn skill result rejected: " + reason_type)
    if value < 0 or value >= (1 << width_bits):
        raise ValueError("learn skill result rejected: " + reason_range)
    return value


# ---------------------------------------------------------------- encoder
# PF-HYPOTHESIS-LEDGER: HYP-PF-033 active
def encode_learn_skill_result_payload(
    legacy: Any,
    records: tuple[LearnSkillResultRecord, ...],
    trailing: int,
) -> bytes:
    """Compose one 0x673C body from opaque declared record triples.

    The wire order is the GT-050-proven one and nothing else: u16 tag 0x12
    count, then per record u32 tag 0x14 / u16 tag 0x12 / u32 tag 0x14, then
    the trailing u8 tag 0x0B.  The record member semantics are unknown and
    unnamed; the values pass through as declared or the composition refuses
    with a named reason and no bytes.  The composed payload is re-decoded
    before it is returned, so the encoder can never emit something its own
    decoder would refuse.
    """
    if type(records) is not tuple:
        raise ValueError(
            "learn skill result rejected: records_not_a_tuple_of_records"
        )
    for record in records:
        if type(record) is not LearnSkillResultRecord:
            raise ValueError(
                "learn skill result rejected: records_not_a_tuple_of_records"
            )
    count = _require_int(
        len(records), 16,
        "record_count_outside_u16", "record_count_outside_u16",
    )
    trailing = _require_int(
        trailing, 8, "trailing_byte_type_not_integer",
        "trailing_byte_outside_u8",
    )
    payload = bytearray()
    payload += legacy.u16tag(LEARN_SKILL_RESULT_COUNT_TAG, count)
    for record in records:
        payload += legacy.u32tag(
            LEARN_SKILL_RESULT_RECORD_U32_TAG,
            _require_int(
                record.record_u32_0, 32,
                "record_value_type_not_integer",
                "record_value_outside_field_width",
            ),
        )
        payload += legacy.u16tag(
            LEARN_SKILL_RESULT_RECORD_U16_TAG,
            _require_int(
                record.record_u16_4, 16,
                "record_value_type_not_integer",
                "record_value_outside_field_width",
            ),
        )
        payload += legacy.u32tag(
            LEARN_SKILL_RESULT_RECORD_U32_TAG,
            _require_int(
                record.record_u32_8, 32,
                "record_value_type_not_integer",
                "record_value_outside_field_width",
            ),
        )
    payload += legacy.u8tag(LEARN_SKILL_RESULT_TRAILING_TAG, trailing)
    payload = bytes(payload)
    expected_size = (
        LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE
        + LEARN_SKILL_RESULT_RECORD_WIRE_SIZE * count
    )
    if len(payload) != expected_size:
        raise RuntimeError("HYP-PF-033 composed payload size drift")
    if decode_learn_skill_result_payload(payload) != (records, trailing):
        raise RuntimeError("HYP-PF-033 encoder is not decoder-inverse")
    return payload


# ---------------------------------------------------------------- decoder
def decode_learn_skill_result_payload(
    payload: Any,
) -> tuple[tuple[LearnSkillResultRecord, ...], int]:
    """Read one 0x673C body back into ``(records, trailing)``.

    This is the inverse the encoder checks itself against, written strictly
    from the same GT-050 wire order: every tag byte is verified at its
    position, every truncation refuses, and a byte left over after the
    trailing u8 refuses.  No partial result is ever returned.
    """
    if type(payload) is not bytes and type(payload) is not bytearray:
        raise ValueError("learn skill result rejected: truncated_payload")
    payload = bytes(payload)
    if len(payload) < 3:
        raise ValueError("learn skill result rejected: truncated_payload")
    if payload[0] != LEARN_SKILL_RESULT_COUNT_TAG:
        raise ValueError("learn skill result rejected: wrong_count_tag")
    count = int.from_bytes(payload[1:3], "little")
    cursor = 3
    records = []
    for _index in range(count):
        if len(payload) - cursor < LEARN_SKILL_RESULT_RECORD_WIRE_SIZE:
            raise ValueError("learn skill result rejected: truncated_payload")
        if payload[cursor] != LEARN_SKILL_RESULT_RECORD_U32_TAG:
            raise ValueError(
                "learn skill result rejected: wrong_record_u32_tag"
            )
        first = int.from_bytes(payload[cursor + 1:cursor + 5], "little")
        cursor += 5
        if payload[cursor] != LEARN_SKILL_RESULT_RECORD_U16_TAG:
            raise ValueError(
                "learn skill result rejected: wrong_record_u16_tag"
            )
        second = int.from_bytes(payload[cursor + 1:cursor + 3], "little")
        cursor += 3
        if payload[cursor] != LEARN_SKILL_RESULT_RECORD_U32_TAG:
            raise ValueError(
                "learn skill result rejected: wrong_record_u32_tag"
            )
        third = int.from_bytes(payload[cursor + 1:cursor + 5], "little")
        cursor += 5
        records.append(LearnSkillResultRecord(first, second, third))
    if len(payload) - cursor < 2:
        raise ValueError("learn skill result rejected: truncated_payload")
    if payload[cursor] != LEARN_SKILL_RESULT_TRAILING_TAG:
        raise ValueError("learn skill result rejected: wrong_trailing_tag")
    trailing = payload[cursor + 1]
    cursor += 2
    if cursor != len(payload):
        raise ValueError(
            "learn skill result rejected: trailing_bytes_after_object"
        )
    return tuple(records), trailing


# ---------------------------------------------------------------- composition
def make_learn_skill_result_response(
    legacy: Any,
    records: tuple[LearnSkillResultRecord, ...],
    trailing: int,
) -> tuple[bytes, bytes]:
    """Compose ``(pc, frame)`` for one 0x673C vital.

    The envelope is NOT rebuilt here: this reuses the frozen v141
    ``make_runtime_vitals`` one-vital GSCN_RunTimeProtocolRes v4 collection
    helper, the same envelope the already client-accepted lanes use, so the
    only new thing on the wire is the 0x673C body (and the vital id itself).
    The composed PC is independently re-checked: exact size, the payload at
    the fixed offset, the vital id bytes, and a full re-decode of the
    embedded body back to the declared ``(records, trailing)``.
    """
    payload = encode_learn_skill_result_payload(legacy, records, trailing)
    pc, frame = legacy.make_runtime_vitals([
        (
            LEARN_SKILL_RESULT_VITAL_ID,
            LEARN_SKILL_RESULT_VITAL_VERSION,
            payload,
        ),
    ])
    offset = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
    if len(pc) != len(payload) + LEARN_SKILL_RESULT_PC_OVERHEAD:
        raise RuntimeError("HYP-PF-033 composed PC size drift")
    if pc[LEARN_SKILL_RESULT_PC_VITAL_ID_SLICE] != (
        LEARN_SKILL_RESULT_VITAL_ID.to_bytes(2, "little")
    ):
        raise RuntimeError("HYP-PF-033 composed PC vital id drift")
    if pc[offset:offset + len(payload)] != payload:
        raise RuntimeError("HYP-PF-033 composed PC is not the encoded payload")
    if decode_learn_skill_result_payload(
        pc[offset:offset + len(payload)]
    ) != (records, trailing):
        raise RuntimeError("HYP-PF-033 composed PC does not re-decode")
    return pc, frame


def make_learn_skill_result_step_response(
    legacy: Any, step_index: int,
) -> tuple[bytes, bytes]:
    """Compose one numbered frame of the pinned sweep, then drift-check pins.

    The composition takes NO per-session input -- the step plan is entirely
    module-frozen -- so every sweep frame is pinned absolutely: payload, pc
    and frame hash and size must all match the committed values or the
    composition refuses rather than letting drift reach a socket.
    """
    _require_step_plan()
    if type(step_index) is not int or type(step_index) is bool:
        raise ValueError("learn skill result rejected: unknown_step_label")
    if step_index < 0 or step_index >= len(LEARN_SKILL_RESULT_STEP_ORDER):
        raise ValueError("learn skill result rejected: unknown_step_label")
    label = LEARN_SKILL_RESULT_STEP_ORDER[step_index]
    pc, frame = make_learn_skill_result_response(
        legacy,
        LEARN_SKILL_RESULT_STEP_RECORDS[label],
        LEARN_SKILL_RESULT_STEP_TRAILING[label],
    )
    payload = pc[LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET:]
    if (
        len(payload) != LEARN_SKILL_RESULT_PROBE_PC_SIZE[label]
        - LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
    ):
        raise RuntimeError("HYP-PF-033 composed step size drift")
    body = payload[:LEARN_SKILL_RESULT_PROBE_PAYLOAD_SIZE[label]]
    if hashlib.sha256(body).hexdigest().upper() != (
        LEARN_SKILL_RESULT_PROBE_PAYLOAD_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-033 composed payload drift")
    if len(pc) != LEARN_SKILL_RESULT_PROBE_PC_SIZE[label]:
        raise RuntimeError("HYP-PF-033 composed PC size pin drift")
    if hashlib.sha256(pc).hexdigest().upper() != (
        LEARN_SKILL_RESULT_PROBE_PC_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-033 composed PC drift")
    if len(frame) != LEARN_SKILL_RESULT_PROBE_FRAME_SIZE[label]:
        raise RuntimeError("HYP-PF-033 composed frame size pin drift")
    if hashlib.sha256(frame).hexdigest().upper() != (
        LEARN_SKILL_RESULT_PROBE_FRAME_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-033 composed frame drift")
    return pc, frame


# ---------------------------------------------------------------- scenario gate
_PROFILE_LEARN_SWEEP = LearnSkillResultHypothesisScenario(
    LEARN_SKILL_RESULT_SCENARIO_ID,
    LEARN_SKILL_RESULT_HYPOTHESIS_ID,
    LEARN_SKILL_RESULT_STEP_ORDER,
    LEARN_SKILL_RESULT_SPACING_SECONDS,
)


def _record_schema(record: LearnSkillResultRecord) -> dict[str, int]:
    return {
        "record_u32_0": record.record_u32_0,
        "record_u16_4": record.record_u16_4,
        "record_u32_8": record.record_u32_8,
    }


def _expected_sweep() -> dict[str, Any]:
    return {
        "schema": 1,
        "id": LEARN_SKILL_RESULT_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": LEARN_SKILL_RESULT_HYPOTHESIS_ID,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_pinned_learn_skill_result_vital_sweep_"
                "no_write_no_close"
            ),
        },
        "dispatch": {
            "trigger": "accepted_chat_input_frame_exact_ascii12_shape",
            "trigger_classifier": "classify_chat_input_attempt",
            "frames_per_accepted_request": len(LEARN_SKILL_RESULT_STEP_ORDER),
            "step_order": list(LEARN_SKILL_RESULT_STEP_ORDER),
            "step_records": {
                label: [
                    _record_schema(record)
                    for record in LEARN_SKILL_RESULT_STEP_RECORDS[label]
                ]
                for label in LEARN_SKILL_RESULT_STEP_ORDER
            },
            "step_trailing_u8": {
                label: LEARN_SKILL_RESULT_STEP_TRAILING[label]
                for label in LEARN_SKILL_RESULT_STEP_ORDER
            },
            "spacing_seconds": LEARN_SKILL_RESULT_SPACING_SECONDS,
            "first_frame_delay_seconds": (
                LEARN_SKILL_RESULT_FIRST_DELAY_SECONDS
            ),
            "delay_semantics": "gap_before_each_send_on_a_cumulative_deadline",
            "action_label_prefix": LEARN_SKILL_RESULT_ACTION_LABEL_PREFIX,
            "action_labels": [
                LEARN_SKILL_RESULT_ACTION_LABEL_PREFIX + label
                for label in LEARN_SKILL_RESULT_STEP_ORDER
            ],
            "one_shot": False,
            "socket_action": "none",
        },
        "wire": {
            "vital_id": LEARN_SKILL_RESULT_VITAL_ID,
            "vital_version": LEARN_SKILL_RESULT_VITAL_VERSION,
            "vital_version_provenance": (
                "our_design_no_capture_or_static_pin_fixes_it"
            ),
            "envelope": (
                "gscn_runtime_protocol_res_v4_one_vital_collection"
            ),
            "body_order": [
                "u16_tag_0x12_count",
                "per_record_u32_tag_0x14_then_u16_tag_0x12_then_u32_tag_0x14",
                "u8_tag_0x0B_at_object_0x2C",
            ],
            "record_object_stride": LEARN_SKILL_RESULT_RECORD_OBJECT_STRIDE,
            "record_wire_size": LEARN_SKILL_RESULT_RECORD_WIRE_SIZE,
            "provenance": {
                "ticket": "GT-050",
                "letter": (
                    "pf_bridge/notes_to_chief/20260824_0055_GT050-RESULT-"
                    "CLEARNRESULT-CLOSED-TRIGGER-DIRECTION-UNRESOLVED.md"
                ),
                "top_serializer_va": "0x00756100",
                "top_serializer_len": LEARN_SKILL_RESULT_SERIALIZER_LEN,
                "top_serializer_sha256": (
                    LEARN_SKILL_RESULT_SERIALIZER_SHA256
                ),
                "write_loop_va": "0x00755D30",
                "write_loop_len": LEARN_SKILL_RESULT_WRITE_LOOP_LEN,
                "write_loop_sha256": LEARN_SKILL_RESULT_WRITE_LOOP_SHA256,
                "read_loop_va": "0x00756070",
                "read_loop_len": LEARN_SKILL_RESULT_READ_LOOP_LEN,
                "read_loop_sha256": LEARN_SKILL_RESULT_READ_LOOP_SHA256,
            },
        },
        "probe": {
            "per_step": {
                label: {
                    "payload_size": (
                        LEARN_SKILL_RESULT_PROBE_PAYLOAD_SIZE[label]
                    ),
                    "payload_sha256": (
                        LEARN_SKILL_RESULT_PROBE_PAYLOAD_SHA256[label]
                    ),
                    "pc_size": LEARN_SKILL_RESULT_PROBE_PC_SIZE[label],
                    "pc_sha256": LEARN_SKILL_RESULT_PROBE_PC_SHA256[label],
                    "frame_size": LEARN_SKILL_RESULT_PROBE_FRAME_SIZE[label],
                    "frame_sha256": (
                        LEARN_SKILL_RESULT_PROBE_FRAME_SHA256[label]
                    ),
                }
                for label in LEARN_SKILL_RESULT_STEP_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": [
            "compose_the_gt050_proven_0x673C_body_shape",
            "emit_count_0_1_and_3_record_frames_with_both_trailing_values",
            "decode_every_composed_body_back_to_the_declared_triples",
            "repeatable_sweep_per_session_no_state_change",
        ],
        "nonclaims": [
            "any_meaning_for_the_three_record_members",
            "any_meaning_for_the_trailing_u8",
            "the_inbound_clearn_skill_request_0x36AA_or_any_learn_rule",
            "the_vital_version_byte_which_is_our_design",
            "client_acceptance_or_rendering_pending_the_attended_gt_ticket",
            "any_wire_observation_of_0x673C_in_either_direction",
            "original_server_learn_skill_behavior",
            "skill_persistence_or_database_write",
            "production_dispatch_wiring",
            "production_baseline_behavior",
        ],
    }


def _exact_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(
            _exact_equal(actual[key], value) for key, value in expected.items()
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _exact_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def load_learn_skill_result_hypothesis_scenario(
    path: str | Path,
) -> LearnSkillResultHypothesisScenario:
    """Load the one allowlisted opt-in scenario file, or refuse by name.

    The file is a PERMISSION TOKEN, never a source of values: the frames the
    dispatcher emits come from the module's own frozen step plan.  A file
    that differs from the allowlisted body anywhere -- one extra key, one
    missing key, one int where a float is expected -- is refused.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "invalid learn skill result hypothesis scenario"
        ) from exc
    if type(data) is not dict or data.get("id") != (
        LEARN_SKILL_RESULT_SCENARIO_ID
    ):
        raise ValueError(
            "learn skill result hypothesis scenario exceeds the exact "
            "allowlist"
        )
    if not _exact_equal(data, _expected_sweep()):
        raise ValueError(
            "learn skill result hypothesis scenario exceeds the exact "
            "allowlist"
        )
    return require_learn_skill_result_hypothesis_scenario(
        _PROFILE_LEARN_SWEEP
    )


def require_learn_skill_result_hypothesis_scenario(
    value: Any,
) -> LearnSkillResultHypothesisScenario:
    if (
        type(value) is not LearnSkillResultHypothesisScenario
        or value != _PROFILE_LEARN_SWEEP
    ):
        raise ValueError(
            "learn skill result hypothesis scenario object exceeds the "
            "allowlist"
        )
    _require_step_plan()
    return value
