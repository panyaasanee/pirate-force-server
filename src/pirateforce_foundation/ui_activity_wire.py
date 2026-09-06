"""``Activity_*``/``ActorActivity_*`` -- pure encode/decode, wire shape only,
for the seven classes in this catalog group whose ``PF_SERIALIZER_FIELDS.tsv``
rows are FULLY TAGGED (every field row has a real tag byte, no
``CALL_UNCLASSIFIED``/``PE_IMPORT_*``/``JUMP_UNCLASSIFIED`` entries) and are
not yet owned by any other lane:

    Activity_NewActivityVital                    0x858C  3 fields
    Activity_ActivityStateChangedVital           0xEE8D  2 fields
    Activity_ActorJoinActivityVital              0xCA78  6 fields
    Activity_ActorLeaveActivityVital             0xD6CA  3 fields
    Activity_UpdateActivityPointVital            0xE5C9  2 fields
    ActorActivity_ClientReportActivityResultVital 0xAA3F 3 fields
    ActorActivity_ResetDailyActivityResultVital  0x83B1  2 fields

Four classes in the same registry group are deliberately NOT implemented
here, same policy as ``ui_treasurehunt_wire.py``'s exclusion of its own
group's messy third class:
    - ``Activity_CheatCodeVital`` (0x6CEC) -- already owned by LANE-GM
      (``src/pirateforce_foundation/gm/activity_cheat_code_wire.py``).
    - ``Activity_BasicVital`` / ``Activity_ActorCommandVital`` -- registry
      rows are ``UNKNOWN(registry_serializer_unresolved:getter_hits=0)``,
      no tag at all.
    - ``Activity_SendRankingVital`` -- rows mix real tags with
      ``CALL_UNCLASSIFIED``/``PE_IMPORT_*``/atomic-increment entries.
    - ``ActorActivity_UpdateDailyActivityStateVital`` -- single row is
      ``JUMP_UNCLASSIFIED:INDIRECT(...)``, not a proven serializer at all.

Field shapes are copied field-for-field from
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`` (searched via
``awk -F'\\t' '$1 ~ /Activity_|ActorActivity_/'``); W and R rows are
identical shape for every class implemented here (same span/sha256 per
class, both directions). The seven ``*_VITAL_ID`` hex constants below come
from ``pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` (grep
``Activity_``) -- that file, not ``PF_SERIALIZER_FIELDS.tsv`` (which has no
id column), is this project's id-on-the-wire source per ``docs/UI_LANE.md``
item 1.

Grepped first, per ``AGENTS.md`` section 7's mandatory search: no hit for
any of the seven class names above in ``CLIENT_RE_QUEUE.md`` or
``GAME_TEST_QUEUE.md`` (grep on the bridge repo) -- no open RE/GT ticket
references any of them. The only hits are the static census tables
(``notes_to_chief/reference_codex_attr/PF_PROTOCOL_REGISTRY.tsv``,
``PF_FIELD_VALIDATION.tsv``, ``PF_PROTOCOL_PRIORITY.tsv``), which is
expected background coverage, not a ticket. This catalog group has no
prior wire module in ``src/`` other than the GM cheat-code one excluded
above.

See ``ui_social_wire.py``'s module docstring for the shared tag legend,
the "why no wire offsets" explanation, and the fail-closed-on-decode
convention. Tag ``0x26`` (used by three of ``Activity_ActorJoinActivity
Vital``'s fields) is a fourth u32-width tag confirmed by
``pf_bridge/external/PF_TAG_CENSUS.tsv`` row ``0x26  len=4  FIXED``
(``proven_semantics`` there is ``UNKNOWN``, which only means nobody has
named what the field MEANS -- the wire width is proven regardless, which
is all an encode/decode module needs). Tag ``0x12`` = u16 is confirmed by
``ui_treasurehunt_wire.py``'s own docstring citing
``CLIENT_RE_QUEUE.md:54``.

Same scope line as every sibling module in this batch (``CORE-REQUEST
1120``'s own words): "รับเฟรม (decode) + ตอบ ack/error frame ที่วางเปล่า ...
ไม่ใช่การทำ business logic เต็ม". Nothing here claims what any field MEANS
(activity id / actor id / state / rank, etc.) -- the registry's
``proven_semantics`` column is ``UNKNOWN`` for every row of all seven
classes. Not wired into ``runtime.py`` or ``vital_walk.py``; wiring any of
these is a separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

ACTIVITY_NEW_ACTIVITY_VITAL_ID = 0x858C
ACTIVITY_ACTIVITY_STATE_CHANGED_VITAL_ID = 0xEE8D
ACTIVITY_ACTOR_JOIN_ACTIVITY_VITAL_ID = 0xCA78
ACTIVITY_ACTOR_LEAVE_ACTIVITY_VITAL_ID = 0xD6CA
ACTIVITY_UPDATE_ACTIVITY_POINT_VITAL_ID = 0xE5C9
ACTOR_ACTIVITY_CLIENT_REPORT_ACTIVITY_RESULT_VITAL_ID = 0xAA3F
ACTOR_ACTIVITY_RESET_DAILY_ACTIVITY_RESULT_VITAL_ID = 0x83B1

# Unproven default (see ui_party_wire.py's version-byte note).
ACTIVITY_NEW_ACTIVITY_VITAL_VERSION = 0
ACTIVITY_ACTIVITY_STATE_CHANGED_VITAL_VERSION = 0
ACTIVITY_ACTOR_JOIN_ACTIVITY_VITAL_VERSION = 0
ACTIVITY_ACTOR_LEAVE_ACTIVITY_VITAL_VERSION = 0
ACTIVITY_UPDATE_ACTIVITY_POINT_VITAL_VERSION = 0
ACTOR_ACTIVITY_CLIENT_REPORT_ACTIVITY_RESULT_VITAL_VERSION = 0
ACTOR_ACTIVITY_RESET_DAILY_ACTIVITY_RESULT_VITAL_VERSION = 0

_TAG_U8 = 0x0B
_TAG_U16_A = 0x0F
_TAG_U16_B = 0x12
_TAG_U32_A = 0x14
_TAG_U32_B = 0x26


@dataclass(frozen=True)
class NewActivityFields:
    """Wire order: u32, u32, u8 -- identical shape for W and R
    (``PF_SERIALIZER_FIELDS.tsv`` ``Activity_NewActivityVital`` rows)."""

    field1_u32: int
    field2_u32: int
    field3_u8: int


@dataclass(frozen=True)
class ActivityStateChangedFields:
    """Wire order: u32, u8 -- identical shape for W and R."""

    field1_u32: int
    field2_u8: int


@dataclass(frozen=True)
class ActorJoinActivityFields:
    """Wire order: u32, u8, u8, u32(tag 0x26), u32(tag 0x26),
    u32(tag 0x26) -- identical shape for W and R."""

    field1_u32: int
    field2_u8: int
    field3_u8: int
    field4_u32: int
    field5_u32: int
    field6_u32: int


@dataclass(frozen=True)
class ActorLeaveActivityFields:
    """Wire order: u32, u8, u8 -- identical shape for W and R."""

    field1_u32: int
    field2_u8: int
    field3_u8: int


@dataclass(frozen=True)
class UpdateActivityPointFields:
    """Wire order: u32, u16 -- identical shape for W and R."""

    field1_u32: int
    field2_u16: int


@dataclass(frozen=True)
class ClientReportActivityResultFields:
    """Wire order: u32, u16(tag 0x12), u8 -- identical shape for W and R."""

    field1_u32: int
    field2_u16: int
    field3_u8: int


@dataclass(frozen=True)
class ResetDailyActivityResultFields:
    """Wire order: u8, u32 -- identical shape for W and R."""

    field1_u8: int
    field2_u32: int


def encode_new_activity_payload(fields: NewActivityFields) -> bytes:
    out = bytearray()
    out += wire.u32tag(_TAG_U32_A, fields.field1_u32)
    out += wire.u32tag(_TAG_U32_A, fields.field2_u32)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_new_activity_payload(payload: bytes) -> NewActivityFields | None:
    try:
        field1, offset = wire.read_u32tag(payload, 0, _TAG_U32_A)
        field2, offset = wire.read_u32tag(payload, offset, _TAG_U32_A)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return NewActivityFields(field1, field2, field3)


def encode_activity_state_changed_payload(
    fields: ActivityStateChangedFields,
) -> bytes:
    out = bytearray()
    out += wire.u32tag(_TAG_U32_A, fields.field1_u32)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    return bytes(out)


def decode_activity_state_changed_payload(
    payload: bytes,
) -> ActivityStateChangedFields | None:
    try:
        field1, offset = wire.read_u32tag(payload, 0, _TAG_U32_A)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ActivityStateChangedFields(field1, field2)


def encode_actor_join_activity_payload(
    fields: ActorJoinActivityFields,
) -> bytes:
    out = bytearray()
    out += wire.u32tag(_TAG_U32_A, fields.field1_u32)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    out += wire.u32tag(_TAG_U32_B, fields.field4_u32)
    out += wire.u32tag(_TAG_U32_B, fields.field5_u32)
    out += wire.u32tag(_TAG_U32_B, fields.field6_u32)
    return bytes(out)


def decode_actor_join_activity_payload(
    payload: bytes,
) -> ActorJoinActivityFields | None:
    try:
        field1, offset = wire.read_u32tag(payload, 0, _TAG_U32_A)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field4, offset = wire.read_u32tag(payload, offset, _TAG_U32_B)
        field5, offset = wire.read_u32tag(payload, offset, _TAG_U32_B)
        field6, offset = wire.read_u32tag(payload, offset, _TAG_U32_B)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ActorJoinActivityFields(field1, field2, field3, field4, field5, field6)


def encode_actor_leave_activity_payload(
    fields: ActorLeaveActivityFields,
) -> bytes:
    out = bytearray()
    out += wire.u32tag(_TAG_U32_A, fields.field1_u32)
    out += bytes([_TAG_U8, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_actor_leave_activity_payload(
    payload: bytes,
) -> ActorLeaveActivityFields | None:
    try:
        field1, offset = wire.read_u32tag(payload, 0, _TAG_U32_A)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ActorLeaveActivityFields(field1, field2, field3)


def encode_update_activity_point_payload(
    fields: UpdateActivityPointFields,
) -> bytes:
    out = bytearray()
    out += wire.u32tag(_TAG_U32_A, fields.field1_u32)
    out += wire.u16tag(_TAG_U16_A, fields.field2_u16)
    return bytes(out)


def decode_update_activity_point_payload(
    payload: bytes,
) -> UpdateActivityPointFields | None:
    try:
        field1, offset = wire.read_u32tag(payload, 0, _TAG_U32_A)
        field2, offset = wire.read_u16tag(payload, offset, _TAG_U16_A)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return UpdateActivityPointFields(field1, field2)


def encode_client_report_activity_result_payload(
    fields: ClientReportActivityResultFields,
) -> bytes:
    out = bytearray()
    out += wire.u32tag(_TAG_U32_A, fields.field1_u32)
    out += wire.u16tag(_TAG_U16_B, fields.field2_u16)
    out += bytes([_TAG_U8, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_client_report_activity_result_payload(
    payload: bytes,
) -> ClientReportActivityResultFields | None:
    try:
        field1, offset = wire.read_u32tag(payload, 0, _TAG_U32_A)
        field2, offset = wire.read_u16tag(payload, offset, _TAG_U16_B)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ClientReportActivityResultFields(field1, field2, field3)


def encode_reset_daily_activity_result_payload(
    fields: ResetDailyActivityResultFields,
) -> bytes:
    out = bytearray()
    out += bytes([_TAG_U8, fields.field1_u8 & 0xFF])
    out += wire.u32tag(_TAG_U32_A, fields.field2_u32)
    return bytes(out)


def decode_reset_daily_activity_result_payload(
    payload: bytes,
) -> ResetDailyActivityResultFields | None:
    try:
        field1, offset = wire.read_u8tag(payload, 0, _TAG_U8)
        field2, offset = wire.read_u32tag(payload, offset, _TAG_U32_A)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ResetDailyActivityResultFields(field1, field2)
