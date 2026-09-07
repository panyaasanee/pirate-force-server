"""The proven 0x673C wire frame: layout, encoder, decoder, composer.

This module is a PLAIN FRAME MODULE.  It holds the GT-050-proven body shape
of vital ``0x673C`` and nothing else: the static pins that record where the
shape came from in the read-only client image, the record triple, and the
three functions that turn declared triples into bytes and back.  It has no
opt-in gate, no step plan, no sweep, and no probe pins.

WHY IT LIVES ON ITS OWN (COO-DECISION 20260907_2241)
----------------------------------------------------
Two callers need this shape for two different reasons: the HYP-PF-033 sweep
module, which drives a pinned six-step probe through its own opt-in gate,
and the login lane, which composes ONE frame from a character's own database
rows and never opens that gate at all.  Before this split the login lane had
to import the sweep module, which made the sentence "nothing the server runs
may import the sweep lane" false and put a fourth name on a safety pin whose
whole job is to keep that list short.
COO ruled: do not widen the pin -- move the shape out, let both sides import
it from here.  The sweep module re-exports every name below, so its own
importers and tests are unaffected by the move.

RULES THIS MODULE LIVES UNDER
------------------------------
  * it MUST NOT import the sweep module, and MUST NOT name that module's
    opt-in gate, its plan of steps or its probe pins.  The sweep lane's own
    test module asserts both from the parsed AST -- docstrings excluded, so
    this paragraph cannot be what makes the check pass or fail.
  * the composed bytes are unchanged by the move.  Every constant, every
    tag, every refusal string and every self-check below is the code that
    was in the sweep module before, moved verbatim.

NONCLAIMS
---------
  * the record members' SEMANTICS remain unknown.  The three names encode
    the proven object offset and width and nothing else; no member is
    claimed to be a skill id, a level, or anything else.
  * ``LEARN_SKILL_RESULT_VITAL_VERSION = 0`` is OUR DESIGN, not a pin: no
    capture or static evidence fixes the per-vital version byte for this
    vital.  It is the value every other vital lane in this tree sends absent
    a proven pin.
  * this module composes bytes.  It does not claim any client renders them,
    and it never sends anything itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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

def _require_int(value: Any, width_bits: int, reason_type: str,
                 reason_range: str) -> int:
    if type(value) is not int or type(value) is bool:
        raise ValueError("learn skill result rejected: " + reason_type)
    if value < 0 or value >= (1 << width_bits):
        raise ValueError("learn skill result rejected: " + reason_range)
    return value

# ---------------------------------------------------------------- encoder
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
