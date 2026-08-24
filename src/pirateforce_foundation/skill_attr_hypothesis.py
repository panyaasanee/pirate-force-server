"""SKILL-ATTR-001 -- server-side encoder for the CSkillAttr attr block
carried by the ``UpdateAttrVital`` 0x309A attr collection (HYP-PF-035).

Where the project stops without this module
-------------------------------------------
GT-058 measured that the Skill window (Skill_Main2, hotkey K) does not open
against this server, and RE-061 (letter pf_bridge/notes_to_chief/
20260824_1437_RE-061-RESULT-SKILLATTR-GATE-PINNED.md, static, read-only client
image sha256 9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623)
pinned the leading hypothesis for why: the window's controller constructor
0x760DE0 reads the local actor's skill-attr pointer at ``[actor+0x3E8]``, and
the controller init method 0x761ED0 returns false -- init fail, window does
not open -- when the container derived from that pointer is absent
(``cmp [esi+0x88],0`` at 0x761F3B, null branch ``xor al,al; ret`` at
0x761EE7).  Nothing in this repository could compose the attr block that
populates that slot, so the attended question "does sending one change what K
does" had nothing to run against.  This lane builds the server side of
exactly the RE-061-pinned wire shape and nothing more.

What RE-061 proved (static, verified two independent ways; do not re-prove)
---------------------------------------------------------------------------
  * CSkillAttr is NOT a standalone vital: it is an attr block, class id
    0x1661, inside the ``UpdateAttrVital`` 0x309A attr collection.  The id is
    derived at client init (registration thunk 0xC0C530..0xC0C548 hashes the
    class-name literal and stores AX at 0x108A32C; getter 0x751BF0 reads it);
    the raw image carries no 0x1661 or 0x309A literal.
  * The outer carrier chain: ``UpdateAttrVital`` serializer wrapper 0x5E42C0
    re-bases ``this+0x14`` and tail-jumps to the shared attr-collection codec
    0x463DE0, whose tag chain is ``0x12 u16 attr_count``, then per element
    ``0x12 u16 attr_class_id`` -> ``0x14 u32 body_len`` -> indirect call of
    the attr's serializer at vtable ``+0x34``.
  * The body serializer is 0x7520B0 (span [0x7520B0,0x752281), len 465,
    sha256 9227cc6009fff2f20c79a3b19c395f9623d87f68a4ee3462e541aed62aa7e906).
    Its byte-exact W/R order, implemented verbatim here:

        DBAttribute chain first (0x467790): u8 tag 0x0B db_mask;
          if db_mask & 0x01: u64 tag 0x32 identity
        u16 tag 0x12 record_count
        repeat record_count times:
          u16 tag 0x12 key
          u16 tag 0x12 opaque_u16
          u32 tag 0x14 opaque_u32

  * The inbound apply path is REAL: ``UpdateAttrVital`` handler 0x5F2400
    (span len 538, sha256
    65a7095cc493e33988f816efcd63d48220ee9cf39437e543389d54e3718acfaf)
    iterates attr blocks and calls the incoming attr's ``vtable+0x24`` copy,
    which for this class is 0x751C70 (span len 72, sha256
    1e8d5b2e6a7814bc88cec812188d05a8673aa5d3c69e9ba9c963a2d0cd98738e); the
    bind thunk 0x4698B0 type-checks the local actor class and reads
    ``[actor+0x3E8]`` as the apply target.

NONCLAIMS -- read these before using one symbol from this file
--------------------------------------------------------------
  * ONE PACKET IS NOT PROVEN SUFFICIENT TO OPEN THE SKILL WINDOW.  RE-061
    pins the attr block as a falsifiable PREREQUISITE of the 0x761ED0 gate,
    not as sufficient: the init method has base/UI checks before and after
    the gate, and whether ``[actor+0x3E8]`` is even null at runtime under
    GT-058's conditions was not observed.  Nothing here claims the client
    accepts these frames or that K starts opening the window.
  * The SEMANTICS of the two opaque record fields are NOT known.  They are
    encoded as declared values named by wire position and width only
    (``opaque_u16`` / ``opaque_u32``); nothing here calls either one a skill
    level, a cooldown, a slot or anything else, and nothing may.
  * The record ``key`` is named for its position as the map key the ordered
    record tree at object +0x2C is keyed on; no key VALUE is claimed
    meaningful, and the sweep's key=1 is an arbitrary probe value.
  * The per-vital u8 version byte in the collection envelope is OUR DESIGN
    (0, the value every other vital lane in this tree sends absent a proven
    pin); no capture or static pin fixes it for this delivery.
  * Nothing is claimed about the ORIGINAL server, which is closed,
    unpublished and unrecoverable: no capture holds this attr block in
    either direction (PF_FIELD_VALIDATION rows NOT_OBSERVED), so the step
    plan, the record values, the db_mask policy, the spacing and the
    trigger policy are this project's own design.
  * NO CLIENT HAS EVER SEEN ONE OF THESE FRAMES from this project.  That
    half is an attended GT ticket, queued and not run, and no coverage row
    grade moves on this module alone.

Fail-closed contract
--------------------
Refused with ``ValueError`` and no bytes: a records container that is not a
tuple of this module's own record type, a record member that is not a plain
``int`` (``bool`` included), a member outside its wire width, a record count
outside u16, an identity half that is not a plain ``int`` in u32, and a step
index outside the pinned plan.  The decoder refuses, by named reason, a wrong
tag at every tag position, a db_mask other than the one value this lane ever
emits (0x01, identity present), any truncation, and any byte left over after
the last record.  Every composed payload is re-decoded and compared with the
request before the bytes are returned, and every sweep composition is
hash-pinned in the module AND in the scenario file from the same live
computation.  No database call exists on any path in this file.

Opt-in, test-only
-----------------
``production_allowed`` is False in the module and in the scenario file, the
scenario loads through an exact allowlist, and with no scenario handed in the
dispatch branch does not exist: nothing in default mode composes one byte of
this.  ``database_write`` is ``none`` -- skill state has no table, and this
lane deliberately does not open one.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


SKILL_ATTR_CHECKPOINT = "SKILL-ATTR-001"
SKILL_ATTR_HYPOTHESIS_ID = "HYP-PF-035"
production_allowed = False

# ---------------------------------------------------------------- static pins
# Client-binary provenance closed by RE-061; carried as documentation-grade
# constants and never dereferenced.  Spans and hashes are re-stated in the
# module docstring.
SKILL_ATTR_ID = 0x1661                      # attr collection class id
SKILL_ATTR_SERIALIZER_VA = 0x7520B0         # attr body W/R codec (vtable +0x34)
SKILL_ATTR_SERIALIZER_LEN = 465
SKILL_ATTR_SERIALIZER_SHA256 = (
    "9227cc6009fff2f20c79a3b19c395f9623d87f68a4ee3462e541aed62aa7e906"
)
SKILL_ATTR_APPLY_VA = 0x751C70              # attr vtable +0x24 apply/copy
SKILL_ATTR_APPLY_LEN = 72
SKILL_ATTR_APPLY_SHA256 = (
    "1e8d5b2e6a7814bc88cec812188d05a8673aa5d3c69e9ba9c963a2d0cd98738e"
)
UPDATE_ATTR_VITAL_ID = 0x309A               # outer carrier vital id
UPDATE_ATTR_VITAL_SERIALIZER_VA = 0x5E42C0  # rebases +0x14, tail-jumps codec
ATTR_COLLECTION_CODEC_VA = 0x463DE0         # shared attr-collection codec
UPDATE_ATTR_VITAL_HANDLER_VA = 0x5F2400     # inbound apply handler
UPDATE_ATTR_VITAL_HANDLER_LEN = 538
UPDATE_ATTR_VITAL_HANDLER_SHA256 = (
    "65a7095cc493e33988f816efcd63d48220ee9cf39437e543389d54e3718acfaf"
)
DB_ATTRIBUTE_SERIALIZER_VA = 0x467790       # base-chain mask+identity codec
SKILL_ATTR_BIND_THUNK_VA = 0x4698B0         # reads [actor+0x3E8] as target
SKILL_WINDOW_GATE_INIT_VA = 0x761ED0        # controller init; null -> false
SKILL_WINDOW_CONTROLLER_CTOR_VA = 0x760DE0  # reads the actor slot below
ACTOR_SKILL_ATTR_SLOT_OFFSET = 0x3E8        # [actor+0x3E8]

# The per-vital version byte of the one-vital collection envelope.  OUR
# DESIGN, not a pin: no capture or static evidence fixes this value for
# this delivery, and 0 is what every other vital lane in this tree sends
# absent a proven pin.  Stated in the module docstring nonclaims.
UPDATE_ATTR_VITAL_VERSION = 0

# The proven body geometry, exactly as the 0x7520B0 W/R branches agree on it.
SKILL_ATTR_DB_MASK_TAG = 0x0B               # u8 db_mask (DBAttribute +0x20)
SKILL_ATTR_DB_IDENTITY_BIT = 0x01           # gates the identity qword
SKILL_ATTR_DB_IDENTITY_TAG = 0x32           # u64 identity (DBAttribute +0x18)
SKILL_ATTR_COUNT_TAG = 0x12                 # u16 record_count
SKILL_ATTR_RECORD_KEY_TAG = 0x12            # u16 key
SKILL_ATTR_RECORD_OPAQUE_U16_TAG = 0x12     # u16 opaque_u16 (meaning unknown)
SKILL_ATTR_RECORD_OPAQUE_U32_TAG = 0x14     # u32 opaque_u32 (meaning unknown)
# On the wire each record is tag+2 / tag+2 / tag+4 = 11 bytes, and the fixed
# body overhead is 2 (mask) + 9 (identity) + 3 (count header).
SKILL_ATTR_RECORD_WIRE_SIZE = 11
SKILL_ATTR_BODY_BASE_SIZE = 14
# This lane always emits the identity (db_mask exactly 0x01) and refuses any
# other mask on decode: the inbound apply resolves its live target from the
# identity, and no other mask value has any pinned meaning here.
SKILL_ATTR_DB_MASK_VALUE = 0x01

# Attr-collection payload geometry: u16tag count (3) + u16tag class id (3)
# + u32tag body length (5), then the body.  Same outer layout the frozen
# v141 UpdateAttrVital encoder and the HYP-PF-020 stats lane use.
SKILL_ATTR_COLLECTION_COUNT = 1
SKILL_ATTR_COLLECTION_HEADER_SIZE = 11

# One-vital GSCN_RunTimeProtocolRes v4 collection geometry (v141
# make_runtime_vitals), identical to the geometry the chat, stats and
# learn-skill lanes pin: nested payload at a fixed 20-byte offset, 22 bytes
# of envelope, vital id little-endian at bytes 16..17.
SKILL_ATTR_PC_PAYLOAD_OFFSET = 20
SKILL_ATTR_PC_OVERHEAD = 22
SKILL_ATTR_PC_VITAL_ID_SLICE = slice(16, 18)
SKILL_ATTR_PC_BODY_OFFSET = (
    SKILL_ATTR_PC_PAYLOAD_OFFSET + SKILL_ATTR_COLLECTION_HEADER_SIZE
)

# Rejection reasons; every one of them means "no bytes, no reply, no write".
SKILL_ATTR_REJECTIONS = (
    "records_not_a_tuple_of_records",
    "record_value_type_not_integer",
    "record_value_outside_field_width",
    "record_count_outside_u16",
    "identity_type_not_integer",
    "identity_outside_u32_half",
    "unknown_step_label",
    "truncated_body",
    "wrong_db_mask_tag",
    "unimplemented_db_mask",
    "wrong_identity_tag",
    "wrong_count_tag",
    "wrong_record_key_tag",
    "wrong_record_opaque_u16_tag",
    "wrong_record_opaque_u32_tag",
    "trailing_bytes_after_records",
    "truncated_payload",
    "wrong_collection_count_tag",
    "unimplemented_attr_count",
    "wrong_attr_class_tag",
    "wrong_attr_class_id",
    "wrong_body_length_tag",
    "body_length_mismatch",
)


@dataclass(frozen=True)
class SkillAttrRecord:
    """One record of the ordered tree: key plus two UNNAMED opaque values.

    ``key`` is the u16 the client's record tree is keyed on; ``opaque_u16``
    and ``opaque_u32`` are named by wire position and width ONLY -- their
    meanings are unknown and deliberately unnamed (module docstring
    nonclaims).
    """

    key: int
    opaque_u16: int
    opaque_u32: int


@dataclass(frozen=True)
class SkillAttrHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float


# ------------------------------------------------------------ the sweep plan
SKILL_ATTR_SCENARIO_ID = "skill_attr_hypothesis_attr_sweep"

# The two pinned variants.  The VALUES are OUR DESIGN, arbitrary probe
# values chosen only to be minimal and tellable-apart -- none of them is
# claimed to be a meaningful skill record:
#   * COUNT0_EMPTY: record_count = 0, the smallest well-formed body -- does
#     an empty attr block alone populate the actor slot the window gate
#     reads?
#   * COUNT1_KEY1: one record, key=1, opaque_u16=0, opaque_u32=0 --
#     arbitrary pinned probe bytes, NOT claimed meaningful.
SKILL_ATTR_RECORD_PROBE = SkillAttrRecord(1, 0, 0)
SKILL_ATTR_STEPS = (
    ("COUNT0_EMPTY", ()),
    ("COUNT1_KEY1", (SKILL_ATTR_RECORD_PROBE,)),
)
SKILL_ATTR_STEP_ORDER = tuple(label for label, _records in SKILL_ATTR_STEPS)
SKILL_ATTR_STEP_RECORDS = {
    label: records for label, records in SKILL_ATTR_STEPS
}

# The composition is pinned to ONE explicit probe actor so every sweep frame
# is pinned absolutely: the first character of the first account of a fresh
# store (lifecycle identity_lo = 0x10000000 + account_id * 0x10000 +
# selector + 1 with account_id 1 and selector 0), the same canonical smoke
# identity the HYP-PF-020 and HYP-PF-026 pins use.  The dispatcher refuses
# to fire for any other selected identity, so a tester sees the pinned
# bytes byte for byte or nothing.
SKILL_ATTR_PROBE_IDENTITY_LO = 0x10010001
SKILL_ATTR_PROBE_IDENTITY_HI = 0

# Seconds between consecutive sends.  The frozen V141 sender treats the
# fourth action-tuple field as a gap on a cumulative deadline (send_deadline
# += delay, then sleep to it), so the first frame carries 0.0 and each later
# frame the full spacing -- exactly the stats/learn-skill sweep convention.
SKILL_ATTR_SPACING_SECONDS = 3.0
SKILL_ATTR_FIRST_DELAY_SECONDS = 0.0
SKILL_ATTR_ACTION_LABEL_PREFIX = "HYP_PF_035_SKILL_ATTR_"

# ----------------------------------------------------------------- the pins
# Computed by running THIS encoder deterministically over the probe identity
# (the composition takes no other per-session input, so the pins are
# absolute); every value below is a sha256 of bytes this encoder produced,
# never a value copied in.
SKILL_ATTR_PROBE_BODY_SHA256 = {
    "COUNT0_EMPTY": (
        "524FEA50CFF0091A1C59F1C200F8188866537ACA060605C96868C882F4B90B3B"
    ),
    "COUNT1_KEY1": (
        "9AA0F18736C239528B4CB2D61197A46EB570907A19316AE019C2C86E38B5D8CD"
    ),
}
SKILL_ATTR_PROBE_PAYLOAD_SHA256 = {
    "COUNT0_EMPTY": (
        "F9FF70C890CE0DEF0E518F22B8EBB1725A2CEF52E38F6D4CAF0FF820D629E458"
    ),
    "COUNT1_KEY1": (
        "6EA7986777BE67BE884E5846A45D0BAFC20FD0CBE2B34D75283381ECF705EF16"
    ),
}
SKILL_ATTR_PROBE_PC_SHA256 = {
    "COUNT0_EMPTY": (
        "53964014F74102513B76A512CD62F1789D375625838BF4235A55E55CDADDAC00"
    ),
    "COUNT1_KEY1": (
        "46330301695F235D4B84A4A79BA20AD4D021886BCBDF95D80960E9DFBA449E6A"
    ),
}
SKILL_ATTR_PROBE_FRAME_SHA256 = {
    "COUNT0_EMPTY": (
        "62BDFD389A618E12E784A58C8E8D1411BA86E0536D136EE6EE63DEB22173718F"
    ),
    "COUNT1_KEY1": (
        "489331F80430F700638BA660B1D1292CCBC9BB7AB62160FD7A6E8D4AE0B1722E"
    ),
}
SKILL_ATTR_PROBE_BODY_SIZE = {
    "COUNT0_EMPTY": 14,
    "COUNT1_KEY1": 25,
}
SKILL_ATTR_PROBE_PAYLOAD_SIZE = {
    "COUNT0_EMPTY": 25,
    "COUNT1_KEY1": 36,
}
SKILL_ATTR_PROBE_PC_SIZE = {
    "COUNT0_EMPTY": 47,
    "COUNT1_KEY1": 58,
}
SKILL_ATTR_PROBE_FRAME_SIZE = {
    "COUNT0_EMPTY": 57,
    "COUNT1_KEY1": 68,
}


# ---------------------------------------------------------------- self-guards
def _require_step_plan() -> None:
    """The pinned plan must keep asking the questions it was built to ask."""
    if len(set(SKILL_ATTR_STEP_ORDER)) != len(SKILL_ATTR_STEP_ORDER):
        raise RuntimeError("HYP-PF-035 duplicate step label")
    counts = {
        len(SKILL_ATTR_STEP_RECORDS[label])
        for label in SKILL_ATTR_STEP_ORDER
    }
    if counts != {0, 1}:
        raise RuntimeError(
            "HYP-PF-035 the sweep must keep exactly the count 0 and count 1 "
            "variants"
        )
    for label in SKILL_ATTR_STEP_ORDER:
        for record in SKILL_ATTR_STEP_RECORDS[label]:
            if type(record) is not SkillAttrRecord:
                raise RuntimeError("HYP-PF-035 step plan record type drift")
    if SKILL_ATTR_STEP_RECORDS["COUNT1_KEY1"] != (SkillAttrRecord(1, 0, 0),):
        raise RuntimeError(
            "HYP-PF-035 the one-record variant must stay the arbitrary "
            "pinned probe record key=1 opaque_u16=0 opaque_u32=0"
        )


def _require_int(value: Any, width_bits: int, reason_type: str,
                 reason_range: str) -> int:
    if type(value) is not int or type(value) is bool:
        raise ValueError("skill attr rejected: " + reason_type)
    if value < 0 or value >= (1 << width_bits):
        raise ValueError("skill attr rejected: " + reason_range)
    return value


# ---------------------------------------------------------------- encoder
# PF-HYPOTHESIS-LEDGER: HYP-PF-035 active
def encode_skill_attr(
    legacy: Any,
    identity_lo: int,
    identity_hi: int,
    records: tuple[SkillAttrRecord, ...],
) -> bytes:
    """Compose one 0x1661 attr body from an identity and declared records.

    The wire order is the RE-061-proven one and nothing else: the
    DBAttribute chain first (u8 tag 0x0B db_mask, always 0x01 here, then the
    u64 tag 0x32 identity that bit gates), then u16 tag 0x12 record_count,
    then per record u16 tag 0x12 key / u16 tag 0x12 opaque_u16 / u32 tag
    0x14 opaque_u32.  The opaque member semantics are unknown and unnamed;
    the values pass through as declared or the composition refuses with a
    named reason and no bytes.  The composed body is re-decoded before it is
    returned, so the encoder can never emit something its own decoder would
    refuse.
    """
    if type(records) is not tuple:
        raise ValueError("skill attr rejected: records_not_a_tuple_of_records")
    for record in records:
        if type(record) is not SkillAttrRecord:
            raise ValueError(
                "skill attr rejected: records_not_a_tuple_of_records"
            )
    count = _require_int(
        len(records), 16, "record_count_outside_u16", "record_count_outside_u16",
    )
    identity_lo = _require_int(
        identity_lo, 32, "identity_type_not_integer", "identity_outside_u32_half",
    )
    identity_hi = _require_int(
        identity_hi, 32, "identity_type_not_integer", "identity_outside_u32_half",
    )
    body = bytearray()
    body += legacy.u8tag(SKILL_ATTR_DB_MASK_TAG, SKILL_ATTR_DB_MASK_VALUE)
    body += legacy.qwordtag(
        SKILL_ATTR_DB_IDENTITY_TAG, (identity_hi << 32) | identity_lo,
    )
    body += legacy.u16tag(SKILL_ATTR_COUNT_TAG, count)
    for record in records:
        body += legacy.u16tag(
            SKILL_ATTR_RECORD_KEY_TAG,
            _require_int(
                record.key, 16,
                "record_value_type_not_integer",
                "record_value_outside_field_width",
            ),
        )
        body += legacy.u16tag(
            SKILL_ATTR_RECORD_OPAQUE_U16_TAG,
            _require_int(
                record.opaque_u16, 16,
                "record_value_type_not_integer",
                "record_value_outside_field_width",
            ),
        )
        body += legacy.u32tag(
            SKILL_ATTR_RECORD_OPAQUE_U32_TAG,
            _require_int(
                record.opaque_u32, 32,
                "record_value_type_not_integer",
                "record_value_outside_field_width",
            ),
        )
    body = bytes(body)
    expected_size = (
        SKILL_ATTR_BODY_BASE_SIZE + SKILL_ATTR_RECORD_WIRE_SIZE * count
    )
    if len(body) != expected_size:
        raise RuntimeError("HYP-PF-035 composed body size drift")
    if decode_skill_attr(body) != (identity_lo, identity_hi, records):
        raise RuntimeError("HYP-PF-035 encoder is not decoder-inverse")
    return body


# ---------------------------------------------------------------- decoder
def decode_skill_attr(
    body: Any,
) -> tuple[int, int, tuple[SkillAttrRecord, ...]]:
    """Read one 0x1661 attr body back into ``(lo, hi, records)``.

    This is the inverse the encoder checks itself against, written strictly
    from the same RE-061 wire order: every tag byte is verified at its
    position, a db_mask other than the one value this lane emits refuses
    (no other mask meaning is pinned, so none is guessed), every truncation
    refuses, and a byte left over after the last record refuses.  No
    partial result is ever returned.
    """
    if type(body) is not bytes and type(body) is not bytearray:
        raise ValueError("skill attr rejected: truncated_body")
    body = bytes(body)
    if len(body) < 2:
        raise ValueError("skill attr rejected: truncated_body")
    if body[0] != SKILL_ATTR_DB_MASK_TAG:
        raise ValueError("skill attr rejected: wrong_db_mask_tag")
    if body[1] != SKILL_ATTR_DB_MASK_VALUE:
        raise ValueError("skill attr rejected: unimplemented_db_mask")
    if len(body) < 11:
        raise ValueError("skill attr rejected: truncated_body")
    if body[2] != SKILL_ATTR_DB_IDENTITY_TAG:
        raise ValueError("skill attr rejected: wrong_identity_tag")
    identity = int.from_bytes(body[3:11], "little")
    cursor = 11
    if len(body) - cursor < 3:
        raise ValueError("skill attr rejected: truncated_body")
    if body[cursor] != SKILL_ATTR_COUNT_TAG:
        raise ValueError("skill attr rejected: wrong_count_tag")
    count = int.from_bytes(body[cursor + 1:cursor + 3], "little")
    cursor += 3
    records = []
    for _index in range(count):
        if len(body) - cursor < SKILL_ATTR_RECORD_WIRE_SIZE:
            raise ValueError("skill attr rejected: truncated_body")
        if body[cursor] != SKILL_ATTR_RECORD_KEY_TAG:
            raise ValueError("skill attr rejected: wrong_record_key_tag")
        key = int.from_bytes(body[cursor + 1:cursor + 3], "little")
        cursor += 3
        if body[cursor] != SKILL_ATTR_RECORD_OPAQUE_U16_TAG:
            raise ValueError("skill attr rejected: wrong_record_opaque_u16_tag")
        opaque_u16 = int.from_bytes(body[cursor + 1:cursor + 3], "little")
        cursor += 3
        if body[cursor] != SKILL_ATTR_RECORD_OPAQUE_U32_TAG:
            raise ValueError("skill attr rejected: wrong_record_opaque_u32_tag")
        opaque_u32 = int.from_bytes(body[cursor + 1:cursor + 5], "little")
        cursor += 5
        records.append(SkillAttrRecord(key, opaque_u16, opaque_u32))
    if cursor != len(body):
        raise ValueError("skill attr rejected: trailing_bytes_after_records")
    return (
        identity & 0xFFFFFFFF,
        (identity >> 32) & 0xFFFFFFFF,
        tuple(records),
    )


# ---------------------------------------------------------------- payload wrap
def make_skill_attr_payload(legacy: Any, body: bytes) -> bytes:
    """Wrap one 0x1661 attr body in the shared attr-collection payload.

    Layout is the one the frozen v141 UpdateAttrVital encoder and the
    HYP-PF-020 stats lane use: tag12/u16 count, tag12/u16 attr class id,
    tag14/u32 body length, then the body.  The outer vital id is
    drift-checked against the frozen legacy module on every call; the class
    id 0x1661 has no v141 constant to drift against (the frozen module never
    names it), which is itself re-checked so this lane notices if that ever
    changes.
    """
    if legacy.UPDATE_ATTR_VITAL != UPDATE_ATTR_VITAL_ID:
        raise RuntimeError(
            "HYP-PF-035 UpdateAttrVital id drift against the frozen module"
        )
    if getattr(legacy, "SKILL_ATTR", None) is not None:
        raise RuntimeError(
            "HYP-PF-035 the frozen module unexpectedly names the 0x1661 "
            "class id; re-derive the drift checks before composing"
        )
    if type(body) is not bytes:
        raise ValueError("skill attr rejected: truncated_body")
    return (
        legacy.u16tag(0x12, SKILL_ATTR_COLLECTION_COUNT)
        + legacy.u16tag(0x12, SKILL_ATTR_ID)
        + legacy.u32tag(0x14, len(body))
        + body
    )


def unwrap_skill_attr_payload(payload: Any) -> bytes:
    """Strictly unwrap the attr-collection payload back to the attr body.

    Accepts only what this lane composes: attr_count exactly 1, class id
    exactly 0x1661, body length exactly the remaining bytes.  Anything else
    refuses by name with no partial result.
    """
    if type(payload) is not bytes and type(payload) is not bytearray:
        raise ValueError("skill attr rejected: truncated_payload")
    payload = bytes(payload)
    if len(payload) < SKILL_ATTR_COLLECTION_HEADER_SIZE:
        raise ValueError("skill attr rejected: truncated_payload")
    if payload[0] != 0x12:
        raise ValueError("skill attr rejected: wrong_collection_count_tag")
    if int.from_bytes(payload[1:3], "little") != SKILL_ATTR_COLLECTION_COUNT:
        raise ValueError("skill attr rejected: unimplemented_attr_count")
    if payload[3] != 0x12:
        raise ValueError("skill attr rejected: wrong_attr_class_tag")
    if int.from_bytes(payload[4:6], "little") != SKILL_ATTR_ID:
        raise ValueError("skill attr rejected: wrong_attr_class_id")
    if payload[6] != 0x14:
        raise ValueError("skill attr rejected: wrong_body_length_tag")
    body_len = int.from_bytes(payload[7:11], "little")
    body = payload[SKILL_ATTR_COLLECTION_HEADER_SIZE:]
    if body_len != len(body):
        raise ValueError("skill attr rejected: body_length_mismatch")
    return body


# ---------------------------------------------------------------- composition
def make_skill_attr_response(
    legacy: Any,
    identity_lo: int,
    identity_hi: int,
    records: tuple[SkillAttrRecord, ...],
) -> tuple[bytes, bytes]:
    """Compose ``(pc, frame)`` for one UpdateAttrVital 0x309A delivery.

    The envelope is NOT rebuilt here: this reuses the frozen v141
    ``make_runtime_vitals`` one-vital GSCN_RunTimeProtocolRes v4 collection
    helper, the same envelope the already client-accepted lanes use, so the
    only new thing on the wire is the 0x1661 attr block.  The composed PC is
    independently re-checked: exact size, the payload at the fixed offset,
    the vital id bytes, and a full unwrap-and-re-decode of the embedded body
    back to the declared ``(identity, records)``.
    """
    body = encode_skill_attr(legacy, identity_lo, identity_hi, records)
    payload = make_skill_attr_payload(legacy, body)
    pc, frame = legacy.make_runtime_vitals([
        (UPDATE_ATTR_VITAL_ID, UPDATE_ATTR_VITAL_VERSION, payload),
    ])
    offset = SKILL_ATTR_PC_PAYLOAD_OFFSET
    if len(pc) != len(payload) + SKILL_ATTR_PC_OVERHEAD:
        raise RuntimeError("HYP-PF-035 composed PC size drift")
    if pc[SKILL_ATTR_PC_VITAL_ID_SLICE] != (
        UPDATE_ATTR_VITAL_ID.to_bytes(2, "little")
    ):
        raise RuntimeError("HYP-PF-035 composed PC vital id drift")
    if pc[offset:offset + len(payload)] != payload:
        raise RuntimeError("HYP-PF-035 composed PC is not the encoded payload")
    if decode_skill_attr(
        unwrap_skill_attr_payload(pc[offset:offset + len(payload)])
    ) != (identity_lo, identity_hi, records):
        raise RuntimeError("HYP-PF-035 composed PC does not re-decode")
    return pc, frame


def make_skill_attr_step_response(
    legacy: Any, step_index: int,
) -> tuple[bytes, bytes]:
    """Compose one numbered frame of the pinned sweep, then drift-check pins.

    The composition takes NO per-session input -- the step plan and the
    probe identity are entirely module-frozen -- so every sweep frame is
    pinned absolutely: body, payload, pc and frame hash and size must all
    match the committed values or the composition refuses rather than
    letting drift reach a socket.
    """
    _require_step_plan()
    if type(step_index) is not int or type(step_index) is bool:
        raise ValueError("skill attr rejected: unknown_step_label")
    if step_index < 0 or step_index >= len(SKILL_ATTR_STEP_ORDER):
        raise ValueError("skill attr rejected: unknown_step_label")
    label = SKILL_ATTR_STEP_ORDER[step_index]
    pc, frame = make_skill_attr_response(
        legacy,
        SKILL_ATTR_PROBE_IDENTITY_LO,
        SKILL_ATTR_PROBE_IDENTITY_HI,
        SKILL_ATTR_STEP_RECORDS[label],
    )
    # The two bytes after the nested payload are the collection tail the
    # frozen envelope writes (u8 tag 0x0B, value 0); the payload proper ends
    # two bytes before the PC does.
    payload = pc[SKILL_ATTR_PC_PAYLOAD_OFFSET:len(pc) - 2]
    if len(payload) != SKILL_ATTR_PROBE_PAYLOAD_SIZE[label]:
        raise RuntimeError("HYP-PF-035 composed step size drift")
    if hashlib.sha256(payload).hexdigest().upper() != (
        SKILL_ATTR_PROBE_PAYLOAD_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-035 composed payload drift")
    attr_body = payload[SKILL_ATTR_COLLECTION_HEADER_SIZE:]
    if len(attr_body) != SKILL_ATTR_PROBE_BODY_SIZE[label]:
        raise RuntimeError("HYP-PF-035 composed body size pin drift")
    if hashlib.sha256(attr_body).hexdigest().upper() != (
        SKILL_ATTR_PROBE_BODY_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-035 composed body drift")
    if len(pc) != SKILL_ATTR_PROBE_PC_SIZE[label]:
        raise RuntimeError("HYP-PF-035 composed PC size pin drift")
    if hashlib.sha256(pc).hexdigest().upper() != (
        SKILL_ATTR_PROBE_PC_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-035 composed PC drift")
    if len(frame) != SKILL_ATTR_PROBE_FRAME_SIZE[label]:
        raise RuntimeError("HYP-PF-035 composed frame size pin drift")
    if hashlib.sha256(frame).hexdigest().upper() != (
        SKILL_ATTR_PROBE_FRAME_SHA256[label].upper()
    ):
        raise RuntimeError("HYP-PF-035 composed frame drift")
    return pc, frame


# ---------------------------------------------------------------- scenario gate
_PROFILE_ATTR_SWEEP = SkillAttrHypothesisScenario(
    SKILL_ATTR_SCENARIO_ID,
    SKILL_ATTR_HYPOTHESIS_ID,
    SKILL_ATTR_STEP_ORDER,
    SKILL_ATTR_SPACING_SECONDS,
)


def _record_schema(record: SkillAttrRecord) -> dict[str, int]:
    return {
        "key": record.key,
        "opaque_u16": record.opaque_u16,
        "opaque_u32": record.opaque_u32,
    }


def _expected_sweep() -> dict[str, Any]:
    return {
        "schema": 1,
        "id": SKILL_ATTR_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": SKILL_ATTR_HYPOTHESIS_ID,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_pinned_skill_attr_update_attr_vital_sweep_"
                "no_write_no_close"
            ),
        },
        "dispatch": {
            "trigger": "accepted_chat_input_frame_exact_ascii12_shape",
            "trigger_classifier": "classify_chat_input_attempt",
            "frames_per_accepted_request": len(SKILL_ATTR_STEP_ORDER),
            "step_order": list(SKILL_ATTR_STEP_ORDER),
            "step_records": {
                label: [
                    _record_schema(record)
                    for record in SKILL_ATTR_STEP_RECORDS[label]
                ]
                for label in SKILL_ATTR_STEP_ORDER
            },
            "identity_policy": "refuse_unless_selected_is_the_pinned_probe",
            "probe_identity_lo": SKILL_ATTR_PROBE_IDENTITY_LO,
            "probe_identity_hi": SKILL_ATTR_PROBE_IDENTITY_HI,
            "spacing_seconds": SKILL_ATTR_SPACING_SECONDS,
            "first_frame_delay_seconds": SKILL_ATTR_FIRST_DELAY_SECONDS,
            "delay_semantics": "gap_before_each_send_on_a_cumulative_deadline",
            "action_label_prefix": SKILL_ATTR_ACTION_LABEL_PREFIX,
            "action_labels": [
                SKILL_ATTR_ACTION_LABEL_PREFIX + label
                for label in SKILL_ATTR_STEP_ORDER
            ],
            "one_shot": False,
            "socket_action": "none",
        },
        "wire": {
            "carrier_vital_id": UPDATE_ATTR_VITAL_ID,
            "attr_class_id": SKILL_ATTR_ID,
            "vital_version": UPDATE_ATTR_VITAL_VERSION,
            "vital_version_provenance": (
                "our_design_no_capture_or_static_pin_fixes_it"
            ),
            "envelope": "gscn_runtime_protocol_res_v4_one_vital_collection",
            "payload_order": [
                "u16_tag_0x12_attr_count_1",
                "u16_tag_0x12_attr_class_id_0x1661",
                "u32_tag_0x14_body_len",
                "attr_body",
            ],
            "body_order": [
                "u8_tag_0x0B_db_mask_0x01",
                "u64_tag_0x32_identity",
                "u16_tag_0x12_record_count",
                "per_record_u16_tag_0x12_key_then_u16_tag_0x12_opaque_u16_"
                "then_u32_tag_0x14_opaque_u32",
            ],
            "record_wire_size": SKILL_ATTR_RECORD_WIRE_SIZE,
            "provenance": {
                "ticket": "RE-061",
                "letter": (
                    "pf_bridge/notes_to_chief/20260824_1437_RE-061-RESULT-"
                    "SKILLATTR-GATE-PINNED.md"
                ),
                "serializer_va": "0x007520B0",
                "serializer_len": SKILL_ATTR_SERIALIZER_LEN,
                "serializer_sha256": SKILL_ATTR_SERIALIZER_SHA256,
                "apply_va": "0x00751C70",
                "apply_len": SKILL_ATTR_APPLY_LEN,
                "apply_sha256": SKILL_ATTR_APPLY_SHA256,
                "handler_va": "0x005F2400",
                "handler_len": UPDATE_ATTR_VITAL_HANDLER_LEN,
                "handler_sha256": UPDATE_ATTR_VITAL_HANDLER_SHA256,
                "window_gate_init_va": "0x00761ED0",
                "actor_slot_offset": "0x3E8",
            },
        },
        "probe": {
            "per_step": {
                label: {
                    "body_size": SKILL_ATTR_PROBE_BODY_SIZE[label],
                    "body_sha256": SKILL_ATTR_PROBE_BODY_SHA256[label],
                    "payload_size": SKILL_ATTR_PROBE_PAYLOAD_SIZE[label],
                    "payload_sha256": SKILL_ATTR_PROBE_PAYLOAD_SHA256[label],
                    "pc_size": SKILL_ATTR_PROBE_PC_SIZE[label],
                    "pc_sha256": SKILL_ATTR_PROBE_PC_SHA256[label],
                    "frame_size": SKILL_ATTR_PROBE_FRAME_SIZE[label],
                    "frame_sha256": SKILL_ATTR_PROBE_FRAME_SHA256[label],
                }
                for label in SKILL_ATTR_STEP_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": [
            "compose_the_re061_proven_0x1661_attr_body_shape",
            "emit_record_count_0_and_1_frames_for_the_pinned_probe_identity",
            "decode_every_composed_body_back_to_the_declared_records",
            "repeatable_sweep_per_session_no_state_change",
        ],
        "nonclaims": [
            "one_packet_sufficient_to_open_the_skill_window",
            "any_meaning_for_the_two_opaque_record_fields",
            "any_meaning_for_the_record_key_values",
            "the_vital_version_byte_which_is_our_design",
            "client_acceptance_or_rendering_pending_the_attended_gt_ticket",
            "any_wire_observation_of_the_0x1661_attr_block_in_either_direction",
            "original_server_skill_attr_behavior_which_is_unrecoverable",
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


def load_skill_attr_hypothesis_scenario(
    path: str | Path,
) -> SkillAttrHypothesisScenario:
    """Load the one allowlisted opt-in scenario file, or refuse by name.

    The file is a PERMISSION TOKEN, never a source of values: the frames the
    dispatcher emits come from the module's own frozen step plan.  A file
    that differs from the allowlisted body anywhere -- one extra key, one
    missing key, one int where a float is expected -- is refused.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid skill attr hypothesis scenario") from exc
    if type(data) is not dict or data.get("id") != SKILL_ATTR_SCENARIO_ID:
        raise ValueError(
            "skill attr hypothesis scenario exceeds the exact allowlist"
        )
    if not _exact_equal(data, _expected_sweep()):
        raise ValueError(
            "skill attr hypothesis scenario exceeds the exact allowlist"
        )
    return require_skill_attr_hypothesis_scenario(_PROFILE_ATTR_SWEEP)


def require_skill_attr_hypothesis_scenario(
    value: Any,
) -> SkillAttrHypothesisScenario:
    if (
        type(value) is not SkillAttrHypothesisScenario
        or value != _PROFILE_ATTR_SWEEP
    ):
        raise ValueError(
            "skill attr hypothesis scenario object exceeds the allowlist"
        )
    _require_step_plan()
    return value
