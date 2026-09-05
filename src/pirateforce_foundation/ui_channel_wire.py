"""Nine ``Channel_*Vital`` classes -- pure encode/decode, wire shape only.

Grepped first, per ``AGENTS.md`` section 7's mandatory search: ``Channel_``
has a lot of history in this repo, all of it read before writing a single
line here.

  * This project already has a dedicated module (a sibling file in this
    same package, deliberately not named again here -- see below) that owns
    FIVE classes sharing serializer ``0x65AD40``:
    ``Channel_LocalTalkMessageVital``, ``Channel_PartyMessageVital``,
    ``Channel_GuildMessageVital``, ``Channel_ActorBoardcastMessageVital``,
    ``Channel_GMGlobalMessageVital`` -- NOT touched here (that module's own
    docstring: "OWNERSHIP GATE", an exact allowlist of the two files
    (``app.py``, ``runtime.py``) allowed to even mention its module name,
    enforced by that sibling module's own test file's scenario-gate test --
    which is exactly why this docstring spells that module's name only as a
    description, never as the literal filename/import string, so this file
    does not become an accidental sixth mention and break that pin).
    ``docs/GM_LANE.md``'s row for ``Channel_GMGlobalMessageVital`` says the
    same thing from the GM lane's side: "already proven elsewhere in this
    repo -- do not re-derive or re-codec in this lane's zone."
  * ``reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md``
    (grade A, byte-exact static, GM lane's own retracted-build round) already
    resolved the wire schema of ALL 17 ``Channel_*`` classes, including the
    ``UNTAGGED_WSTRING16LE_LEN32LE`` label
    ``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv`` gives every wstring field
    below -- that TSV label is WRONG for this family (coarser than reality):
    the report's disassembly of the wstring codec (``0x89A810``/``0x89A880``)
    proves every one of these strings actually carries a leading tag byte
    ``0x48`` before the u32 length, the same correction the five-class
    sibling module above already made for its own classes. This module
    would have built an incorrect codec (missing the tag byte) had this not
    been grepped first -- reusing the report's byte-exact finding instead of
    the coarser TSV row, per the class-by-class table at that report's line
    63-76.
  * Two classes from that report, ``Channel_JoinClassChannelVital`` and
    ``Channel_ClassChannelMessageVital``, are deliberately EXCLUDED here even
    though their layout is equally proven: ``prompts/COMMON_LANE_ROUND.md``'s
    per-lane grep hint table lists ``Channel_JoinClassChannel`` under
    **LANE-CS**'s search terms (grouped with ``CLearnSkill*``/skill-class
    vitals), not this lane's. Building a codec for a class-channel pair that
    turns out to be CS's is a one-round mistake to avoid by just not picking
    it up; CS can grep this module and the report directly if it wants them.
  * No open RE/GT ticket for any of the nine classes below in
    ``CLIENT_RE_QUEUE.md`` or ``GAME_TEST_QUEUE.md`` (both empty grep hits),
    and no prior wire module in ``src/``/``tests/`` for any of them
    (``archive/`` checked too: only unrelated GM chat-command history hits).

The nine classes covered here, with their proven field order (report lines
66-76; every wstring is tag ``0x48`` + u32 byte-length + UTF-16LE, no NUL):

  * ``Channel_WhisperVital`` ``0x556C`` -- serializer ``0x65AEA0``:
    ``wstring@+0x34`` (speaker) -> ``wstring@+0x18`` (body) ->
    ``wstring@+0x50`` (recipient) -> ``u8(0x0B)@+0x6C`` (result)
  * ``Channel_CustomChannelMessageVital`` ``0xE064`` -- serializer
    ``0x65B1E0``: ``wstring@+0x34`` -> ``wstring@+0x18`` ->
    ``u8(0x08)@+0x50`` -> ``u64(0x32)@+0x58`` (channel handle)
  * ``Channel_OriginalSinChannelMessageVital`` ``0x265C`` -- serializer
    ``0x65B310``: ``wstring@+0x34`` -> ``wstring@+0x18`` -> ``u8(0x08)@+0x50``
  * ``Channel_JoinCustomChannelVital`` ``0xBA58`` -- serializer ``0x65AF80``:
    ``u64(0x32)@+0x18`` (channel handle) -> ``wstring@+0x20`` (channel name)
    -> ``u8(0x0B)@+0x3C`` -> ``u8(0x0B)@+0x3D`` (result)
  * ``Channel_LeaveCustomChannelVital`` ``0xC663`` -- serializer
    ``0x65B060``: ``u64(0x32)@+0x18`` -> ``u8(0x0B)@+0x20`` ->
    ``u8(0x0B)@+0x21`` (result) -> ``wstring@+0x24``
  * ``Channel_OnActorJoinCustomChannelVital`` ``0x18DA`` -- serializer
    ``0x65B140`` (shared with the Leave-notification twin below):
    ``u64(0x32)@+0x18`` -> ``wstring@+0x20`` (channel name) ->
    ``wstring@+0x3C`` (actor name)
  * ``Channel_OnActorLeaveCustomChannelVital`` ``0x2770`` -- same shape as
    ``OnActorJoinCustomChannel`` immediately above (shared serializer
    ``0x65B140``)
  * ``Channel_JoinOriginalSinChannelVital`` ``0xFA07`` -- serializer
    ``0x65B260``: ``u64(0x32)@+0x18`` -> ``u8(0x08)@+0x20`` ->
    ``u8(0x0B)@+0x21`` (result)
  * ``Channel_LocalPerformanceVital`` ``0xAE8C`` -- serializer ``0x65AE30``:
    ``u64(0x32)@+0x18`` -> ``u64(0x32)@+0x20`` -> ``u16(0x12)@+0x28``

Scalar tag widths (``0x0B``/``0x08`` = u8, ``0x12`` = u16, ``0x32`` = u64)
are the exact same legend already confirmed project-wide by
``ui_social_wire.py``'s own docstring and reused unchanged by every sibling
``ui_*_wire.py`` module in this batch -- none invented here.

``external/PF_FIELD_VALIDATION.tsv`` shows ``status=NOT_OBSERVED``,
``observed_frames=0`` for both ``W`` and ``R`` on all nine classes above
(unlike ``Channel_LocalTalkMessageVital``, which IS ``VALIDATED`` with real
captured frames -- that is exactly the class this module does not touch, see
the ownership note above). So nothing below claims which side sends which
class in production, what any field MEANS (channel handle values, result
byte semantics, etc. are all ``proven_semantics=UNKNOWN``), or reproduces a
live-captured frame -- the report's grade A is byte-exact STATIC disassembly
cross-checked against the GT-006 capture for the five shared-serializer
classes only, not a live capture of any of these nine. Same "receive frame
(decode) + compose the same shape back (encode), no business logic" scope as
every sibling module in this batch (``CORE-REQUEST 1120``'s own words). Not
wired into ``runtime.py``/``vital_walk.py`` -- wiring any of these is a
separate ``CORE-REQUEST``.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ui_social_wire as wire

CHANNEL_WHISPER_VITAL_ID = 0x556C
CHANNEL_CUSTOM_CHANNEL_MESSAGE_VITAL_ID = 0xE064
CHANNEL_ORIGINAL_SIN_CHANNEL_MESSAGE_VITAL_ID = 0x265C
CHANNEL_JOIN_CUSTOM_CHANNEL_VITAL_ID = 0xBA58
CHANNEL_LEAVE_CUSTOM_CHANNEL_VITAL_ID = 0xC663
CHANNEL_ON_ACTOR_JOIN_CUSTOM_CHANNEL_VITAL_ID = 0x18DA
CHANNEL_ON_ACTOR_LEAVE_CUSTOM_CHANNEL_VITAL_ID = 0x2770
CHANNEL_JOIN_ORIGINAL_SIN_CHANNEL_VITAL_ID = 0xFA07
CHANNEL_LOCAL_PERFORMANCE_VITAL_ID = 0xAE8C

# wstring codec 0x89A810/0x89A880 (report line 60): tag 0x48 + u32
# byte-length + UTF-16LE, no NUL. Same tag/shape the five-class sibling
# module (see module docstring) already proved for the shared-serializer
# classes -- defined fresh here (not imported) because that module's
# wstring helpers are private (its own underscore-prefixed encode/read
# functions) and scoped to its own five-class ownership gate, the same
# reasoning ``u64tag``'s docstring in ``ui_social_wire.py`` gives for not
# reaching into ``v141``'s frozen file.
_CHANNEL_WSTRING_TAG = 0x48

_TAG_U8_A = 0x0B
_TAG_U8_B = 0x08
_TAG_U16 = 0x12
_TAG_U64 = 0x32


def encode_channel_tagged_wstring(s: str) -> bytes:
    """``tag 0x48 + u32 byte-length + UTF-16LE`` -- see module docstring."""

    payload = s.encode("utf-16le")
    return bytes([_CHANNEL_WSTRING_TAG]) + len(payload).to_bytes(4, "little") + payload


def read_channel_tagged_wstring(buf: bytes, offset: int) -> tuple[str, int]:
    if offset + 5 > len(buf):
        raise wire.WireDecodeError("truncated tagged wstring header")
    tag = buf[offset]
    if tag != _CHANNEL_WSTRING_TAG:
        raise wire.WireDecodeError(
            "expected wstring tag 0x%02X, got 0x%02X" % (_CHANNEL_WSTRING_TAG, tag)
        )
    length = int.from_bytes(buf[offset + 1 : offset + 5], "little")
    start = offset + 5
    end = start + length
    if end > len(buf):
        raise wire.WireDecodeError("truncated tagged wstring payload")
    if length % 2 != 0:
        raise wire.WireDecodeError("odd-length UTF-16LE payload")
    try:
        text = buf[start:end].decode("utf-16le")
    except UnicodeDecodeError as error:
        raise wire.WireDecodeError("malformed UTF-16LE payload") from error
    return text, end


@dataclass(frozen=True)
class WhisperFields:
    """Wire order: wstring, wstring, wstring, u8 (report line 66)."""

    speaker: str
    body: str
    recipient: str
    result_u8: int


@dataclass(frozen=True)
class CustomChannelMessageFields:
    """Wire order: wstring, wstring, u8, u64 (report line 67)."""

    speaker: str
    body: str
    field3_u8: int
    channel_handle_u64: int


@dataclass(frozen=True)
class OriginalSinChannelMessageFields:
    """Wire order: wstring, wstring, u8 (report line 68)."""

    speaker: str
    body: str
    field3_u8: int


@dataclass(frozen=True)
class JoinCustomChannelFields:
    """Wire order: u64, wstring, u8, u8 (report line 70)."""

    channel_handle_u64: int
    channel_name: str
    field3_u8: int
    result_u8: int


@dataclass(frozen=True)
class LeaveCustomChannelFields:
    """Wire order: u64, u8, u8, wstring (report line 71)."""

    channel_handle_u64: int
    field2_u8: int
    result_u8: int
    channel_name: str


@dataclass(frozen=True)
class ActorCustomChannelNotificationFields:
    """Wire order: u64, wstring, wstring (report line 72) -- shared shape
    for both ``OnActorJoinCustomChannel`` and ``OnActorLeaveCustomChannel``
    (same serializer ``0x65B140``)."""

    channel_handle_u64: int
    channel_name: str
    actor_name: str


@dataclass(frozen=True)
class JoinOriginalSinChannelFields:
    """Wire order: u64, u8, u8 (report line 73)."""

    channel_handle_u64: int
    field2_u8: int
    result_u8: int


@dataclass(frozen=True)
class LocalPerformanceFields:
    """Wire order: u64, u64, u16 (report line 76)."""

    field1_u64: int
    field2_u64: int
    field3_u16: int


def encode_whisper_payload(fields: WhisperFields) -> bytes:
    out = bytearray()
    out += encode_channel_tagged_wstring(fields.speaker)
    out += encode_channel_tagged_wstring(fields.body)
    out += encode_channel_tagged_wstring(fields.recipient)
    out += bytes([_TAG_U8_A, fields.result_u8 & 0xFF])
    return bytes(out)


def decode_whisper_payload(payload: bytes) -> WhisperFields | None:
    try:
        speaker, offset = read_channel_tagged_wstring(payload, 0)
        body, offset = read_channel_tagged_wstring(payload, offset)
        recipient, offset = read_channel_tagged_wstring(payload, offset)
        result, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return WhisperFields(speaker, body, recipient, result)


def encode_custom_channel_message_payload(
    fields: CustomChannelMessageFields,
) -> bytes:
    out = bytearray()
    out += encode_channel_tagged_wstring(fields.speaker)
    out += encode_channel_tagged_wstring(fields.body)
    out += bytes([_TAG_U8_B, fields.field3_u8 & 0xFF])
    out += wire.u64tag(_TAG_U64, fields.channel_handle_u64)
    return bytes(out)


def decode_custom_channel_message_payload(
    payload: bytes,
) -> CustomChannelMessageFields | None:
    try:
        speaker, offset = read_channel_tagged_wstring(payload, 0)
        body, offset = read_channel_tagged_wstring(payload, offset)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8_B)
        handle, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return CustomChannelMessageFields(speaker, body, field3, handle)


def encode_original_sin_channel_message_payload(
    fields: OriginalSinChannelMessageFields,
) -> bytes:
    out = bytearray()
    out += encode_channel_tagged_wstring(fields.speaker)
    out += encode_channel_tagged_wstring(fields.body)
    out += bytes([_TAG_U8_B, fields.field3_u8 & 0xFF])
    return bytes(out)


def decode_original_sin_channel_message_payload(
    payload: bytes,
) -> OriginalSinChannelMessageFields | None:
    try:
        speaker, offset = read_channel_tagged_wstring(payload, 0)
        body, offset = read_channel_tagged_wstring(payload, offset)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8_B)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return OriginalSinChannelMessageFields(speaker, body, field3)


def encode_join_custom_channel_payload(fields: JoinCustomChannelFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.channel_handle_u64)
    out += encode_channel_tagged_wstring(fields.channel_name)
    out += bytes([_TAG_U8_A, fields.field3_u8 & 0xFF])
    out += bytes([_TAG_U8_A, fields.result_u8 & 0xFF])
    return bytes(out)


def decode_join_custom_channel_payload(
    payload: bytes,
) -> JoinCustomChannelFields | None:
    try:
        handle, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        name, offset = read_channel_tagged_wstring(payload, offset)
        field3, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        result, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return JoinCustomChannelFields(handle, name, field3, result)


def encode_leave_custom_channel_payload(fields: LeaveCustomChannelFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.channel_handle_u64)
    out += bytes([_TAG_U8_A, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8_A, fields.result_u8 & 0xFF])
    out += encode_channel_tagged_wstring(fields.channel_name)
    return bytes(out)


def decode_leave_custom_channel_payload(
    payload: bytes,
) -> LeaveCustomChannelFields | None:
    try:
        handle, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        result, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        name, offset = read_channel_tagged_wstring(payload, offset)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return LeaveCustomChannelFields(handle, field2, result, name)


def encode_actor_custom_channel_notification_payload(
    fields: ActorCustomChannelNotificationFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.channel_handle_u64)
    out += encode_channel_tagged_wstring(fields.channel_name)
    out += encode_channel_tagged_wstring(fields.actor_name)
    return bytes(out)


def decode_actor_custom_channel_notification_payload(
    payload: bytes,
) -> ActorCustomChannelNotificationFields | None:
    try:
        handle, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        channel_name, offset = read_channel_tagged_wstring(payload, offset)
        actor_name, offset = read_channel_tagged_wstring(payload, offset)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return ActorCustomChannelNotificationFields(handle, channel_name, actor_name)


def encode_join_original_sin_channel_payload(
    fields: JoinOriginalSinChannelFields,
) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.channel_handle_u64)
    out += bytes([_TAG_U8_B, fields.field2_u8 & 0xFF])
    out += bytes([_TAG_U8_A, fields.result_u8 & 0xFF])
    return bytes(out)


def decode_join_original_sin_channel_payload(
    payload: bytes,
) -> JoinOriginalSinChannelFields | None:
    try:
        handle, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u8tag(payload, offset, _TAG_U8_B)
        result, offset = wire.read_u8tag(payload, offset, _TAG_U8_A)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return JoinOriginalSinChannelFields(handle, field2, result)


def encode_local_performance_payload(fields: LocalPerformanceFields) -> bytes:
    out = bytearray()
    out += wire.u64tag(_TAG_U64, fields.field1_u64)
    out += wire.u64tag(_TAG_U64, fields.field2_u64)
    out += wire.u16tag(_TAG_U16, fields.field3_u16)
    return bytes(out)


def decode_local_performance_payload(
    payload: bytes,
) -> LocalPerformanceFields | None:
    try:
        field1, offset = wire.read_u64tag(payload, 0, _TAG_U64)
        field2, offset = wire.read_u64tag(payload, offset, _TAG_U64)
        field3, offset = wire.read_u16tag(payload, offset, _TAG_U16)
        wire.require_exhausted(payload, offset)
    except wire.WireDecodeError:
        return None
    return LocalPerformanceFields(field1, field2, field3)
