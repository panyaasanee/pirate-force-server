"""CHAT-CHANNEL-002 -- server-side decoder/emitter for the shared-serializer
``Channel_*Message`` family (HYP-PF-019).

Where CHAT-ECHO-001/002 stop
----------------------------
``chat_input_hypothesis.py`` treats the first 10 bytes of the captured
0xAC52 payload as ONE opaque pinned blob (``CHAT_INPUT_PREFIX``) and echoes
the request back; its own docstring says the 0x18 at index 6 is only a
*candidate* length field and that "nothing here claims or decodes it".  The
speaker variant splices bytes 0..4 without ever parsing them.  So the server
can only ever answer a request it has already received, byte-for-byte, at
one fixed text length.

What CHAT-CHANNEL-001 proved (commit b2e4669, do not re-prove)
--------------------------------------------------------------
``tools/pf_chat_channel_family_static.py`` (69 static guards) +
``reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md``
read the read-only client binary
(SHA-256 ``9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623``)
byte-exact:

  * The whole ``Channel_*Vital`` family registers from one contiguous thunk
    block ``0xBF72B0..0xBF74F0`` of the PF-NAMEID-HASH-001 shape, so every
    channel's 16-bit wire id is the position-weighted signed-char hash
    (client ``0x89B220``) of its in-image class-name literal.  ANCHOR:
    ``name_id("Channel_LocalTalkMessageVital") == 0xAC52`` == the id GT-006
    actually captured on the wire.
  * FIVE channels share ONE serializer, ``0x65AD40`` (the base
    ``Channel_MessageVtial`` Serialize, vtable +0x18):
    ``Channel_LocalTalkMessageVital`` 0xAC52,
    ``Channel_PartyMessageVital`` 0x82E6,
    ``Channel_GuildMessageVital`` 0x8189,
    ``Channel_ActorBoardcastMessageVital`` 0xEDFA,
    ``Channel_GMGlobalMessageVital`` 0x9F2C.
    They are wire-IDENTICAL; the only thing that says which channel a
    message belongs to is the 16-bit class id in the envelope.  There is no
    channel selector inside the payload.
  * That serializer's field order is exactly two wstrings:
    ``wstring@+0x34`` (speaker) then ``wstring@+0x18`` (body); the wstring
    codec ``0x89A810``/``0x89A880`` emits tag ``0x48`` + u32 byte-length +
    byte-length bytes of UTF-16LE with no NUL terminator.
  * ``Channel_WhisperVital`` 0x556C uses a DIFFERENT serializer ``0x65AEA0``
    (a third wstring @+0x50 = recipient, plus a u8 result @+0x6C), so it is
    not decodable by this lane and is refused here by construction.

What this module adds
---------------------
The 10-byte "opaque prefix" becomes two parsed headers, and the lane gains a
*generator*: ``(channel, speaker, body) -> payload`` composes a message the
server was never handed a template for, and ``payload -> (speaker, body)``
reads one back.  The proof that the decode is real, not a story:

  * ``encode_channel_message_payload("", "PFCHATPROBE1")`` reproduces the
    captured GT-006 probe1 payload byte-for-byte (and probe2 likewise), and
  * composing that payload for ``channel_id == 0xAC52`` through the SAME
    ``legacy.make_runtime_vitals`` collection envelope the echo lane uses
    reproduces the CHAT-ECHO-001 pinned response PC and frame hashes
    (``scenarios/chat_input_hypothesis_echo.json``) exactly, and
  * ``encode_channel_message_payload("test01", "PFCHATPROBE1")`` reproduces
    the CHAT-ECHO-002 speaker-variant pinned payload/PC/frame hashes exactly.

Those three are byte-level cross-checks against pins that were produced by a
completely different code path (opaque splice, no parsing), so a wrong field
order, a wrong tag, a wrong length width or a wrong endianness cannot pass.

Fail-closed contract
--------------------
Refused with no reply and no write: any channel id outside the five sharing
``0x65AD40`` (Whisper 0x556C included -- different schema), a truncated
wstring header, tag != 0x48, an odd byte length, a declared length longer
than the remaining payload, bytes left over after the second wstring, text
that is not two bytes per character (non-BMP or unpaired surrogates), and an
empty body.  An empty *speaker* is accepted on decode because that is what
every captured client request contains.

OWNERSHIP GATE -- READ BEFORE MERGING
------------------------------------
``tests/test_presentation_ownership.py`` pins an exact allowlist of Foundation
modules allowed to mention the GT-006 chat vital id (regex ``(?i)AC52|44114``,
allowlist, settled by the chief in round 76 as
``["channel_message_hypothesis.py", "chat_input_hypothesis.py",
"runtime.py"]``).  This module is a SECOND deliberate owner of that id.  The
id could have been derived from the name hash at import time to keep the
scanner quiet -- that was deliberately NOT done, and CHAT-CHANNEL-003 does
not do it either: the repository is supposed to be able to say truthfully how
many modules touch 0xAC52.

CHAT-CHANNEL-003 -- the dispatch hookup (this is a deliberate change)
--------------------------------------------------------------------
CHAT-CHANNEL-002 stopped one step short on purpose: the codec existed but
nothing could put a byte on the wire, so GT-016 stayed BLOCKED.  This
milestone adds a SECOND profile,
``scenarios/channel_message_hypothesis_channel_sweep.json``, and wires it
into ``runtime.py``.  Under that profile only, one accepted chat input frame
(the exact ascii12 0xAC52 shape ``chat_input_hypothesis`` already classifies)
is decoded into ``(speaker, body)`` and answered with FIVE composed frames --
one per shared-serializer channel, in the order GT-016 asks to read them on
screen: LocalTalk, Party, Guild, GMGlobal, ActorBoardcast -- spaced by
``spacing_seconds`` so the client cannot coalesce them into one line.

The speaker is deliberately empty on all five.  That is the whole point of
the experiment: with an empty speaker the five nested payloads are IDENTICAL
byte for byte and the composed PCs differ in exactly the two bytes at
``pc[16:18]`` (the 16-bit class id), so whatever the client does differently
between the five lines it did on the strength of the class id alone.

Opt-in, test-only
-----------------
Both scenario files carry ``test_only: true`` / ``production_allowed: false``
and load through an exact allowlist.  The lane is reachable ONLY when one of
them is handed in: with no scenario the dispatch branch does not exist, the
module composes nothing, it owns no session state beyond a counter, and
``database_write`` is ``none`` (chat has no table).  There is no production
path to any of this, and no default-mode behaviour changed.

NOT CLAIMED here: that the client renders any of the five channels (that is
GT-016, attended, not run); the original server's routing/fan-out or
membership policy (never captured -- two concurrent sessions have never
existed in this project); the meaning of Whisper's result byte; and any
behaviour for the four channels other than LocalTalk, which have never been
observed on this project's wire in either direction.  A sweep is five frames
sent to the ONE session that asked for them: it is not fan-out, not routing,
and not membership.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .chat_input_hypothesis import (
    CHAT_INPUT_ECHO_FRAME_SHA256,
    CHAT_INPUT_ECHO_PC_SHA256,
    CHAT_INPUT_PROBE_PAYLOADS,
    CHAT_INPUT_PROBE_PAYLOAD_SHA256,
    CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256,
    CHAT_INPUT_SPEAKER_ECHO_PC_SHA256,
    CHAT_INPUT_SPEAKER_PROBE_NAME,
    CHAT_INPUT_SPEAKER_PROBE_PAYLOAD_SHA256,
    CHAT_INPUT_VITAL_ID,
)


# ---------------------------------------------------------------- static pins
# Every address below is a client-binary VA proven in CHAT-CHANNEL-001; they
# are carried here as documentation-grade constants, never dereferenced.
CHANNEL_MESSAGE_SERIALIZER_VA = 0x65AD40    # base Channel_MessageVtial Serialize
CHANNEL_WHISPER_SERIALIZER_VA = 0x65AEA0    # Channel_WhisperVital Serialize
CHANNEL_NAME_ID_HASH_VA = 0x89B220          # PF-NAMEID-HASH-001
CHANNEL_WSTRING_WRITE_CODEC_VA = 0x89A810
CHANNEL_WSTRING_READ_CODEC_VA = 0x89A880

# wstring codec 0x89A810/0x89A880: tag 0x48 + u32 byte-length + UTF-16LE.
CHANNEL_WSTRING_TAG = 0x48
CHANNEL_WSTRING_HEADER_SIZE = 5
CHANNEL_WSTRING_LENGTH_WIDTH = 4

# Serializer 0x65AD40 field order, exactly as disassembled.
CHANNEL_MESSAGE_FIELD_ORDER = ("speaker", "body")
CHANNEL_MESSAGE_FIELD_OFFSETS = {"speaker": 0x34, "body": 0x18}

# The five channels that share serializer 0x65AD40.  Ids are DERIVED from the
# in-image class-name literals by the same hash, not asserted (see
# _require_derived_channel_ids below).
SHARED_SERIALIZER_CHANNELS = (
    "Channel_LocalTalkMessageVital",
    "Channel_PartyMessageVital",
    "Channel_GuildMessageVital",
    "Channel_ActorBoardcastMessageVital",
    "Channel_GMGlobalMessageVital",
)
SHARED_SERIALIZER_CHANNEL_IDS = {
    "Channel_LocalTalkMessageVital": 0xAC52,
    "Channel_PartyMessageVital": 0x82E6,
    "Channel_GuildMessageVital": 0x8189,
    "Channel_ActorBoardcastMessageVital": 0xEDFA,
    "Channel_GMGlobalMessageVital": 0x9F2C,
}
CHANNEL_NAME_BY_ID = {
    value: key for key, value in SHARED_SERIALIZER_CHANNEL_IDS.items()
}

# Refused by construction: a different serializer (third wstring + result u8).
CHANNEL_WHISPER_NAME = "Channel_WhisperVital"
CHANNEL_WHISPER_VITAL_ID = 0x556C

# Rejection reasons; every one of them means "no reply, no write".
CHANNEL_MESSAGE_ACCEPTED = "shared_serializer_message"
CHANNEL_MESSAGE_REJECTIONS = (
    "channel_outside_shared_serializer",
    "truncated_wstring_header",
    "wrong_wstring_tag",
    "odd_wstring_byte_length",
    "wstring_length_exceeds_payload",
    "trailing_bytes_after_body",
    "text_not_two_bytes_per_character",
    "empty_body",
)

# Composition shape: the one-vital GSCN_RunTimeProtocolRes v4 collection
# envelope (legacy.make_runtime_vitals) puts the nested payload at a fixed
# 20-byte offset and appends the proven 2-byte derived-class mask tail.
CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET = 20
CHANNEL_MESSAGE_PC_OVERHEAD = 22

# The GT-006 capture, expressed as the (speaker, body) pair this lane decodes.
CHANNEL_MESSAGE_PROBE_SPEAKER = ""
CHANNEL_MESSAGE_PROBE_BODIES = {
    "probe1": "PFCHATPROBE1",
    "probe2": "PFCHATPROBE2",
}

# Composed responses for the probe1 message on each of the five channels
# (speaker empty, body "PFCHATPROBE1").  The LocalTalk row is NOT a new pin:
# it is CHAT_INPUT_ECHO_*_SHA256["probe1"], i.e. the hash CHAT-ECHO-001 put
# on the wire through the opaque-splice path, and _require_localtalk_
# crosscheck below fails loudly if the two ever diverge.
CHANNEL_MESSAGE_PROBE1_PC_SHA256 = {
    "Channel_LocalTalkMessageVital": (
        "B92C185ABB0C707EA6512409CAAF5ADC03D911E0399F0CC0DC60A2C49111FA06"
    ),
    "Channel_PartyMessageVital": (
        "23063CB9B2C66DC6DE59F52F9DAB1E3EE2F67D66BA0226BBAD0EA2F49EB44B03"
    ),
    "Channel_GuildMessageVital": (
        "E1B235C1F014E245FFCCC7E30A081755DFE4DEE4045D7DEBA5C5C7507F34A9CE"
    ),
    "Channel_ActorBoardcastMessageVital": (
        "8EC02EC28784C7FEC46DED02421917E632015C71F972B403125D0E5915AB4FC4"
    ),
    "Channel_GMGlobalMessageVital": (
        "6F6566C0FAE8CAD9EE2C6B1CE1BC75EC7C6E93654666A6CE6C8E5B20228B8C5E"
    ),
}
CHANNEL_MESSAGE_PROBE1_FRAME_SHA256 = {
    "Channel_LocalTalkMessageVital": (
        "06C23375BE9A115C59AF410E1446393E2EE3B3294254BCDF6EB88FADFF7E2323"
    ),
    "Channel_PartyMessageVital": (
        "73C2B4C15C63A42FB182D5537081122B9D6EB9FFA9A039B0FED5658C832BDD53"
    ),
    "Channel_GuildMessageVital": (
        "4CD610FE9C996E46D76E95B3A121160C9D0C32191CCCD7BB20BF6330C8589AA2"
    ),
    "Channel_ActorBoardcastMessageVital": (
        "A09A8C768A982C227492342947EFDDE70C358FD5A764562D615211AFC899760F"
    ),
    "Channel_GMGlobalMessageVital": (
        "E9619EFA94A8FB02FD67E0477C2538367C32ED9B93422295D6DD348BB35BDEA3"
    ),
}
CHANNEL_MESSAGE_PROBE1_PC_SIZE = 56
CHANNEL_MESSAGE_PROBE1_FRAME_SIZE = 66

# ------------------------------------------------------- CHAT-CHANNEL-003 sweep
# The order GT-016 asks to read the five lines in on screen.  It is NOT the
# declaration order of SHARED_SERIALIZER_CHANNELS: GMGlobal is pulled ahead of
# ActorBoardcast because the attended tester reads the two "loud" channels
# last.  _require_sweep_order below proves it is a permutation of the five, so
# a typo cannot silently drop or duplicate a channel.
CHANNEL_SWEEP_SCENARIO_ID = "channel_message_hypothesis_channel_sweep"
CHANNEL_SWEEP_ORDER = (
    "Channel_LocalTalkMessageVital",
    "Channel_PartyMessageVital",
    "Channel_GuildMessageVital",
    "Channel_GMGlobalMessageVital",
    "Channel_ActorBoardcastMessageVital",
)
# Seconds between consecutive sends.  The frozen V141 sender treats the fourth
# action-tuple field as a gap on a cumulative deadline (it does
# ``send_deadline += delay`` then sleeps to it), so the first frame carries 0.0
# and each later frame carries the full spacing.  Three seconds is what an
# attended reader needs to see five separate chat lines rather than a burst.
CHANNEL_SWEEP_SPACING_SECONDS = 3.0
CHANNEL_SWEEP_FIRST_DELAY_SECONDS = 0.0
# Empty speaker on every channel, so the five nested payloads are identical
# byte for byte and the class id is the only difference on the wire.
CHANNEL_SWEEP_SPEAKER = CHANNEL_MESSAGE_PROBE_SPEAKER
CHANNEL_SWEEP_ACTION_LABEL_PREFIX = "HYP_PF_019_CHANNEL_SWEEP_"


@dataclass(frozen=True)
class ChannelMessage:
    """One decoded shared-serializer channel message."""

    channel_id: int
    channel_name: str
    speaker: str
    body: str


@dataclass(frozen=True)
class ChannelMessageHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    probe1_payload_sha256: str
    probe2_payload_sha256: str
    localtalk_probe1_pc_sha256: str
    localtalk_probe1_frame_sha256: str
    # CHAT-CHANNEL-003 dispatch policy.  The CHAT-CHANNEL-002 codec-only
    # profile carries the empty defaults: it composes nothing on dispatch
    # because it is never handed to a dispatch branch.
    channel_order: tuple[str, ...] = ()
    spacing_seconds: float = 0.0


# ---------------------------------------------------------------- id derivation
def channel_name_id(name: str) -> int:
    """PF-NAMEID-HASH-001 / client 0x89B220: signed-char position-weighted u16.

    Re-used verbatim from ``tools/pf_chat_channel_family_static.py`` (which
    re-used it from ``tools/pf_vital_id_hash_static.py``); it is not
    re-derived here.  The spelling of the class name matters: four classes in
    this family are spelled ``Vtial`` in the binary and the hash uses the
    literal verbatim.
    """
    if type(name) is not str or not name:
        raise ValueError("channel name is unavailable")
    accumulator = 0
    for index, char in enumerate(name.encode("latin1")):
        signed = char if char < 128 else char - 256
        accumulator = (accumulator + ((signed * (index + 1)) & 0xFFFF)) & 0xFFFF
    return accumulator


def _require_derived_channel_ids() -> None:
    """Every pinned id must fall out of the class-name literal, not a table."""
    for name, pinned in SHARED_SERIALIZER_CHANNEL_IDS.items():
        if channel_name_id(name) != pinned:
            raise RuntimeError("HYP-PF-019 channel id derivation drift")
    if channel_name_id(CHANNEL_WHISPER_NAME) != CHANNEL_WHISPER_VITAL_ID:
        raise RuntimeError("HYP-PF-019 whisper id derivation drift")
    if SHARED_SERIALIZER_CHANNEL_IDS[
        "Channel_LocalTalkMessageVital"
    ] != CHAT_INPUT_VITAL_ID:
        raise RuntimeError("HYP-PF-019 LocalTalk anchor drift")
    if len(set(SHARED_SERIALIZER_CHANNEL_IDS.values())) != len(
        SHARED_SERIALIZER_CHANNEL_IDS
    ):
        raise RuntimeError("HYP-PF-019 channel id collision")


def channel_short_name(name: str) -> str:
    """Derive the action-label token from the class-name literal.

    Derived, not transcribed, for the same reason the ids are: a second table
    is a second thing that can drift away from the first.
    """
    if name not in SHARED_SERIALIZER_CHANNEL_IDS:
        raise ValueError("channel message rejected: "
                         "channel_outside_shared_serializer")
    return name.removeprefix("Channel_").removesuffix("MessageVital").upper()


def _require_sweep_order() -> None:
    """The sweep order must be a permutation of the five, no more, no less."""
    if len(CHANNEL_SWEEP_ORDER) != len(SHARED_SERIALIZER_CHANNELS):
        raise RuntimeError("HYP-PF-019 sweep order length drift")
    if set(CHANNEL_SWEEP_ORDER) != set(SHARED_SERIALIZER_CHANNELS):
        raise RuntimeError("HYP-PF-019 sweep order membership drift")
    if len(set(CHANNEL_SWEEP_ORDER)) != len(CHANNEL_SWEEP_ORDER):
        raise RuntimeError("HYP-PF-019 sweep order duplicate channel")
    if CHANNEL_SWEEP_ORDER[0] != "Channel_LocalTalkMessageVital":
        # The only channel this project has ever seen on the wire leads, so an
        # attended run that dies after one frame still produced a comparable.
        raise RuntimeError("HYP-PF-019 sweep order anchor drift")
    if len({channel_short_name(name) for name in CHANNEL_SWEEP_ORDER}) != len(
        CHANNEL_SWEEP_ORDER
    ):
        raise RuntimeError("HYP-PF-019 sweep action label collision")


# ---------------------------------------------------------------- classification
def classify_channel_id(channel_id: Any) -> str:
    """Accept only the five channels that share serializer 0x65AD40."""
    if type(channel_id) is not int or type(channel_id) is bool:
        return "channel_outside_shared_serializer"
    if channel_id not in CHANNEL_NAME_BY_ID:
        return "channel_outside_shared_serializer"
    return CHANNEL_MESSAGE_ACCEPTED


def _read_wstring(payload: bytes, cursor: int) -> tuple[str, int, str]:
    """Read one tag-0x48 wstring; return (text, next_cursor, reason)."""
    if len(payload) - cursor < CHANNEL_WSTRING_HEADER_SIZE:
        return "", cursor, "truncated_wstring_header"
    if payload[cursor] != CHANNEL_WSTRING_TAG:
        return "", cursor, "wrong_wstring_tag"
    start = cursor + 1
    byte_length = int.from_bytes(
        payload[start:start + CHANNEL_WSTRING_LENGTH_WIDTH], "little",
    )
    cursor += CHANNEL_WSTRING_HEADER_SIZE
    if byte_length % 2:
        return "", cursor, "odd_wstring_byte_length"
    if byte_length > len(payload) - cursor:
        return "", cursor, "wstring_length_exceeds_payload"
    raw = payload[cursor:cursor + byte_length]
    cursor += byte_length
    try:
        text = raw.decode("utf-16-le")
    except UnicodeDecodeError:
        return "", cursor, "text_not_two_bytes_per_character"
    # A valid surrogate PAIR decodes fine but is four wire bytes for one
    # character, which breaks the two-bytes-per-character invariant the
    # encoder round-trips on; refuse it with the same reason.
    if len(text) * 2 != byte_length:
        return "", cursor, "text_not_two_bytes_per_character"
    return text, cursor, CHANNEL_MESSAGE_ACCEPTED


def classify_channel_message_payload(payload: Any) -> str:
    """Classify one nested payload against the 0x65AD40 wire schema."""
    if type(payload) is not bytes and type(payload) is not bytearray:
        return "truncated_wstring_header"
    payload = bytes(payload)
    cursor = 0
    fields = []
    for _field in CHANNEL_MESSAGE_FIELD_ORDER:
        text, cursor, reason = _read_wstring(payload, cursor)
        if reason != CHANNEL_MESSAGE_ACCEPTED:
            return reason
        fields.append(text)
    if cursor != len(payload):
        return "trailing_bytes_after_body"
    if not fields[CHANNEL_MESSAGE_FIELD_ORDER.index("body")]:
        return "empty_body"
    return CHANNEL_MESSAGE_ACCEPTED


def classify_channel_message_frame(channel_id: Any, payload: Any) -> str:
    """Classify one (channel id, payload) pair; the channel gate comes first."""
    reason = classify_channel_id(channel_id)
    if reason != CHANNEL_MESSAGE_ACCEPTED:
        return reason
    return classify_channel_message_payload(payload)


# ---------------------------------------------------------------- decoder
# PF-HYPOTHESIS-LEDGER: HYP-PF-019 active
def decode_channel_message_payload(payload: bytes) -> tuple[str, str]:
    """Decode one 0x65AD40 payload into ``(speaker, body)``.

    The field order is the disassembled one: wstring @+0x34 (speaker) then
    wstring @+0x18 (body).  Every rejection reason in
    ``CHANNEL_MESSAGE_REJECTIONS`` raises ``ValueError`` carrying that
    reason; no partial result is ever returned.
    """
    reason = classify_channel_message_payload(payload)
    if reason != CHANNEL_MESSAGE_ACCEPTED:
        raise ValueError("channel message payload rejected: " + reason)
    payload = bytes(payload)
    cursor = 0
    values = {}
    for field in CHANNEL_MESSAGE_FIELD_ORDER:
        values[field], cursor, _reason = _read_wstring(payload, cursor)
    return values["speaker"], values["body"]


def decode_channel_message(channel_id: int, payload: bytes) -> ChannelMessage:
    """Decode one (channel id, payload) pair into a ``ChannelMessage``."""
    reason = classify_channel_message_frame(channel_id, payload)
    if reason != CHANNEL_MESSAGE_ACCEPTED:
        raise ValueError("channel message rejected: " + reason)
    speaker, body = decode_channel_message_payload(payload)
    return ChannelMessage(
        channel_id, CHANNEL_NAME_BY_ID[channel_id], speaker, body,
    )


# ---------------------------------------------------------------- encoder
def _encode_wstring(text: Any, *, allow_empty: bool) -> bytes:
    if type(text) is not str:
        raise ValueError("channel message text is unavailable")
    if not text and not allow_empty:
        raise ValueError("channel message payload rejected: empty_body")
    try:
        raw = text.encode("utf-16-le")
    except UnicodeEncodeError as exc:
        raise ValueError(
            "channel message payload rejected: "
            "text_not_two_bytes_per_character"
        ) from exc
    if len(raw) != 2 * len(text):
        raise ValueError(
            "channel message payload rejected: "
            "text_not_two_bytes_per_character"
        )
    return (
        bytes([CHANNEL_WSTRING_TAG])
        + len(raw).to_bytes(CHANNEL_WSTRING_LENGTH_WIDTH, "little")
        + raw
    )


# Ledger annotation for this lane is carried once, on
# decode_channel_message_payload above: the ledger verifier allows exactly one
# emitter annotation per (file, hypothesis) pair.
def encode_channel_message_payload(speaker: str, body: str) -> bytes:
    """Compose one 0x65AD40 payload from ``(speaker, body)``.

    No captured request is needed: the payload is generated from the decoded
    schema.  An empty speaker is legal (that is what every captured client
    request carries); an empty body is not.  The composed payload is
    re-decoded before it is returned, so the encoder can never emit something
    its own decoder would refuse.
    """
    payload = (
        _encode_wstring(speaker, allow_empty=True)
        + _encode_wstring(body, allow_empty=False)
    )
    if decode_channel_message_payload(payload) != (speaker, body):
        raise RuntimeError("HYP-PF-019 encoder is not decoder-inverse")
    return payload


def encode_channel_message(channel_id: int, speaker: str, body: str) -> bytes:
    """Compose one payload for a named channel; refuse every other channel."""
    reason = classify_channel_id(channel_id)
    if reason != CHANNEL_MESSAGE_ACCEPTED:
        raise ValueError("channel message rejected: " + reason)
    return encode_channel_message_payload(speaker, body)


# Ledger annotation for this lane is carried once, on
# decode_channel_message_payload above (one emitter annotation per file/id).
def make_channel_message_response(
    legacy: Any, channel_id: int, speaker: str, body: str,
) -> tuple[bytes, bytes]:
    """Compose ``(pc, frame)`` for one generated channel message.

    The envelope is NOT rebuilt here: this reuses the same frozen v141
    ``make_runtime_vitals`` one-vital GSCN_RunTimeProtocolRes v4 collection
    helper the chat echo lane uses, so the only new thing on the wire is the
    payload and the 16-bit channel id.  The composed PC is independently
    re-checked (payload at the fixed offset, exact size), and any composition
    that matches a pinned probe form is drift-checked against the hash
    CHAT-ECHO-001/002 already put on the wire.
    """
    payload = encode_channel_message(channel_id, speaker, body)
    pc, frame = legacy.make_runtime_vitals([(channel_id, 0, payload)])
    offset = CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET
    if len(pc) != len(payload) + CHANNEL_MESSAGE_PC_OVERHEAD:
        raise RuntimeError("HYP-PF-019 composed PC size drift")
    if pc[offset:offset + len(payload)] != payload:
        raise RuntimeError("HYP-PF-019 composed PC is not the encoded payload")
    if decode_channel_message(
        channel_id, pc[offset:offset + len(payload)],
    ) != ChannelMessage(
        channel_id, CHANNEL_NAME_BY_ID[channel_id], speaker, body,
    ):
        raise RuntimeError("HYP-PF-019 composed PC does not re-decode")
    _require_pinned_composition(channel_id, speaker, body, pc, frame)
    return pc, frame


def _require_pinned_composition(
    channel_id: int, speaker: str, body: str, pc: bytes, frame: bytes,
) -> None:
    """Drift-check the compositions that an earlier lane already pinned."""
    name = CHANNEL_NAME_BY_ID[channel_id]
    pc_digest = hashlib.sha256(pc).hexdigest().upper()
    frame_digest = hashlib.sha256(frame).hexdigest().upper()
    if speaker == CHANNEL_MESSAGE_PROBE_SPEAKER:
        if body == CHANNEL_MESSAGE_PROBE_BODIES["probe1"]:
            if pc_digest != CHANNEL_MESSAGE_PROBE1_PC_SHA256[name]:
                raise RuntimeError("HYP-PF-019 composed PC drift")
            if frame_digest != CHANNEL_MESSAGE_PROBE1_FRAME_SHA256[name]:
                raise RuntimeError("HYP-PF-019 composed frame drift")
        if name != "Channel_LocalTalkMessageVital":
            return
        for probe, probe_body in CHANNEL_MESSAGE_PROBE_BODIES.items():
            if body != probe_body:
                continue
            # CHAT-ECHO-001 cross-check: the generated LocalTalk response must
            # be the exact response the echo lane emitted for that capture.
            if pc_digest != CHAT_INPUT_ECHO_PC_SHA256[probe]:
                raise RuntimeError("HYP-PF-019 CHAT-ECHO-001 PC cross-check drift")
            if frame_digest != CHAT_INPUT_ECHO_FRAME_SHA256[probe]:
                raise RuntimeError(
                    "HYP-PF-019 CHAT-ECHO-001 frame cross-check drift"
                )
        return
    if speaker != CHAT_INPUT_SPEAKER_PROBE_NAME:
        return
    if name != "Channel_LocalTalkMessageVital":
        return
    for probe, probe_body in CHANNEL_MESSAGE_PROBE_BODIES.items():
        if body != probe_body:
            continue
        # CHAT-ECHO-002 cross-check: same for the speaker-name variant.
        if pc_digest != CHAT_INPUT_SPEAKER_ECHO_PC_SHA256[probe]:
            raise RuntimeError("HYP-PF-019 CHAT-ECHO-002 PC cross-check drift")
        if frame_digest != CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256[probe]:
            raise RuntimeError("HYP-PF-019 CHAT-ECHO-002 frame cross-check drift")


def _require_capture_roundtrip() -> None:
    """The captured GT-006 payloads must decode and re-encode byte-exactly."""
    for probe, payload in CHAT_INPUT_PROBE_PAYLOADS.items():
        digest = hashlib.sha256(payload).hexdigest().upper()
        if digest != CHAT_INPUT_PROBE_PAYLOAD_SHA256[probe]:
            raise RuntimeError("HYP-PF-019 capture fixture drift")
        speaker, body = decode_channel_message_payload(payload)
        if speaker != CHANNEL_MESSAGE_PROBE_SPEAKER:
            raise RuntimeError("HYP-PF-019 decoded speaker drift")
        if body != CHANNEL_MESSAGE_PROBE_BODIES[probe]:
            raise RuntimeError("HYP-PF-019 decoded body drift")
        if encode_channel_message_payload(speaker, body) != payload:
            raise RuntimeError("HYP-PF-019 capture round-trip is not byte-exact")
        variant = encode_channel_message_payload(
            CHAT_INPUT_SPEAKER_PROBE_NAME, body,
        )
        variant_digest = hashlib.sha256(variant).hexdigest().upper()
        if variant_digest != CHAT_INPUT_SPEAKER_PROBE_PAYLOAD_SHA256[probe]:
            raise RuntimeError("HYP-PF-019 CHAT-ECHO-002 payload cross-check drift")


# ---------------------------------------------------------------- scenario gate
_PROFILE_SHARED_SERIALIZER = ChannelMessageHypothesisScenario(
    "channel_message_hypothesis_shared_serializer",
    "HYP-PF-019",
    CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe1"],
    CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe2"],
    CHANNEL_MESSAGE_PROBE1_PC_SHA256["Channel_LocalTalkMessageVital"],
    CHANNEL_MESSAGE_PROBE1_FRAME_SHA256["Channel_LocalTalkMessageVital"],
)

_EXPECTED_SHARED_SERIALIZER = {
    "schema": 1,
    "id": _PROFILE_SHARED_SERIALIZER.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_SHARED_SERIALIZER.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "response_policy": (
            "decode_and_compose_shared_serializer_channel_message_"
            "no_write_no_close"
        ),
    },
    "requests": {
        "shape": {
            "serializer_va": "0x65AD40",
            "field_order": ["wstring_speaker_at_0x34", "wstring_body_at_0x18"],
            "wstring_codec": "tag_0x48_u32_byte_length_utf16le_no_nul",
            "accepted_channel_ids": [
                SHARED_SERIALIZER_CHANNEL_IDS[name]
                for name in SHARED_SERIALIZER_CHANNELS
            ],
            "rejected_channel_ids": [CHANNEL_WHISPER_VITAL_ID],
        },
        "probe1": {
            "channel_id": CHAT_INPUT_VITAL_ID,
            "speaker": CHANNEL_MESSAGE_PROBE_SPEAKER,
            "body": CHANNEL_MESSAGE_PROBE_BODIES["probe1"],
            "payload_size": 34,
            "payload_sha256": CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe1"],
        },
        "probe2": {
            "channel_id": CHAT_INPUT_VITAL_ID,
            "speaker": CHANNEL_MESSAGE_PROBE_SPEAKER,
            "body": CHANNEL_MESSAGE_PROBE_BODIES["probe2"],
            "payload_size": 34,
            "payload_sha256": CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe2"],
        },
    },
    "composed_responses": {
        "policy": (
            "encode_speaker_and_body_into_the_shared_serializer_payload_"
            "in_accepted_runtime_res_envelope"
        ),
        "pc_size_rule": "22_plus_encoded_payload_bytes",
        "probe_speaker": CHANNEL_MESSAGE_PROBE_SPEAKER,
        "probe_body": CHANNEL_MESSAGE_PROBE_BODIES["probe1"],
        "pc_size": CHANNEL_MESSAGE_PROBE1_PC_SIZE,
        "frame_size": CHANNEL_MESSAGE_PROBE1_FRAME_SIZE,
        "per_channel": {
            name: {
                "channel_id": SHARED_SERIALIZER_CHANNEL_IDS[name],
                "pc_sha256": CHANNEL_MESSAGE_PROBE1_PC_SHA256[name],
                "frame_sha256": CHANNEL_MESSAGE_PROBE1_FRAME_SHA256[name],
            }
            for name in SHARED_SERIALIZER_CHANNELS
        },
        "crosscheck": {
            "chat_echo_001_scenario": "scenarios/chat_input_hypothesis_echo.json",
            "chat_echo_001_probe1_pc_sha256": CHAT_INPUT_ECHO_PC_SHA256["probe1"],
            "chat_echo_001_probe1_frame_sha256": (
                CHAT_INPUT_ECHO_FRAME_SHA256["probe1"]
            ),
            "chat_echo_002_speaker": CHAT_INPUT_SPEAKER_PROBE_NAME,
            "chat_echo_002_probe1_payload_sha256": (
                CHAT_INPUT_SPEAKER_PROBE_PAYLOAD_SHA256["probe1"]
            ),
            "chat_echo_002_probe1_pc_sha256": (
                CHAT_INPUT_SPEAKER_ECHO_PC_SHA256["probe1"]
            ),
        },
    },
    "persisted_post_state": {
        "database_write": "none",
    },
    "capabilities": [
        "decode_shared_serializer_channel_payload_to_speaker_and_body",
        "compose_shared_serializer_channel_payload_without_a_request_template",
        "byte_exact_round_trip_of_both_captured_gt006_payloads",
        "repeatable_composition_per_session_no_state_change",
    ],
    "nonclaims": [
        "client_rendering_of_any_of_the_five_channels_pending_gt016",
        "any_wire_observation_of_the_four_non_localtalk_channels",
        "original_server_routing_fanout_or_membership_policy",
        "whisper_channel_0x556C_schema_or_result_byte_meaning",
        "delivery_to_any_other_client",
        "message_persistence_or_database_write",
        "production_dispatch_wiring",
        "production_baseline_behavior",
    ],
}

_PROFILE_CHANNEL_SWEEP = ChannelMessageHypothesisScenario(
    CHANNEL_SWEEP_SCENARIO_ID,
    "HYP-PF-019",
    CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe1"],
    CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe2"],
    CHANNEL_MESSAGE_PROBE1_PC_SHA256["Channel_LocalTalkMessageVital"],
    CHANNEL_MESSAGE_PROBE1_FRAME_SHA256["Channel_LocalTalkMessageVital"],
    CHANNEL_SWEEP_ORDER,
    CHANNEL_SWEEP_SPACING_SECONDS,
)

# CHAT-CHANNEL-003.  The shared-serializer profile above is left byte-identical
# (it is pinned end to end by tests/test_channel_message_hypothesis.py); the
# dispatch policy lives in its own file, exactly as CHAT-ECHO-002 did.
_EXPECTED_CHANNEL_SWEEP = {
    "schema": 1,
    "id": _PROFILE_CHANNEL_SWEEP.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_CHANNEL_SWEEP.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "response_policy": (
            "sweep_one_decoded_chat_input_across_five_shared_serializer_"
            "channels_no_write_no_close"
        ),
    },
    "dispatch": {
        "trigger": (
            "accepted_chat_input_frame_vital_0xAC52_exact_ascii12_shape"
        ),
        "trigger_classifier": "classify_chat_input_attempt",
        "body_source": "decode_channel_message_payload_of_the_request_payload",
        "frames_per_accepted_request": len(CHANNEL_SWEEP_ORDER),
        "channel_order": list(CHANNEL_SWEEP_ORDER),
        "channel_id_order": [
            SHARED_SERIALIZER_CHANNEL_IDS[name] for name in CHANNEL_SWEEP_ORDER
        ],
        "spacing_seconds": CHANNEL_SWEEP_SPACING_SECONDS,
        "first_frame_delay_seconds": CHANNEL_SWEEP_FIRST_DELAY_SECONDS,
        "delay_semantics": "gap_before_each_send_on_a_cumulative_deadline",
        "speaker_policy": (
            "empty_speaker_so_payload_bytes_are_identical_across_channels"
        ),
        "action_label_prefix": CHANNEL_SWEEP_ACTION_LABEL_PREFIX,
        "action_labels": [
            CHANNEL_SWEEP_ACTION_LABEL_PREFIX + channel_short_name(name)
            for name in CHANNEL_SWEEP_ORDER
        ],
        "one_shot": False,
        "socket_action": "none",
    },
    "requests": {
        "shape": {
            "vital_id": CHAT_INPUT_VITAL_ID,
            "payload_size": 34,
            "envelope": (
                "gscn_runtime_protocol_req_one_vital_outer_version_0_mask_0x02"
            ),
            "serializer_va": "0x65AD40",
            "field_order": ["wstring_speaker_at_0x34", "wstring_body_at_0x18"],
            "wstring_codec": "tag_0x48_u32_byte_length_utf16le_no_nul",
        },
        "probe1": {
            "channel_id": CHAT_INPUT_VITAL_ID,
            "speaker": CHANNEL_MESSAGE_PROBE_SPEAKER,
            "body": CHANNEL_MESSAGE_PROBE_BODIES["probe1"],
            "payload_size": 34,
            "payload_sha256": CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe1"],
        },
        "probe2": {
            "channel_id": CHAT_INPUT_VITAL_ID,
            "speaker": CHANNEL_MESSAGE_PROBE_SPEAKER,
            "body": CHANNEL_MESSAGE_PROBE_BODIES["probe2"],
            "payload_size": 34,
            "payload_sha256": CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe2"],
        },
    },
    "composed_responses": {
        "policy": (
            "encode_empty_speaker_and_decoded_body_once_per_channel_"
            "in_accepted_runtime_res_envelope"
        ),
        "pc_size_rule": "22_plus_encoded_payload_bytes",
        "probe_speaker": CHANNEL_MESSAGE_PROBE_SPEAKER,
        "probe_body": CHANNEL_MESSAGE_PROBE_BODIES["probe1"],
        # One payload, five envelopes: this hash is the SAME for all five
        # channels and is the request payload GT-006 captured.
        "payload_size": 34,
        "payload_sha256": CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe1"],
        "pc_size": CHANNEL_MESSAGE_PROBE1_PC_SIZE,
        "frame_size": CHANNEL_MESSAGE_PROBE1_FRAME_SIZE,
        "pc_channel_id_offset": 16,
        "pc_bytes_differing_across_channels": 2,
        "per_channel": {
            name: {
                "channel_id": SHARED_SERIALIZER_CHANNEL_IDS[name],
                "pc_sha256": CHANNEL_MESSAGE_PROBE1_PC_SHA256[name],
                "frame_sha256": CHANNEL_MESSAGE_PROBE1_FRAME_SHA256[name],
            }
            for name in CHANNEL_SWEEP_ORDER
        },
    },
    "persisted_post_state": {
        "database_write": "none",
    },
    "capabilities": [
        "decode_one_accepted_chat_input_frame_into_speaker_and_body",
        "emit_five_shared_serializer_channel_frames_for_one_request",
        "identical_payload_bytes_across_all_five_channels",
        "repeatable_sweep_per_session_no_state_change",
    ],
    "nonclaims": [
        "client_rendering_of_any_of_the_five_channels_pending_gt016",
        "any_wire_observation_of_the_four_non_localtalk_channels",
        "original_server_routing_fanout_or_membership_policy",
        "delivery_to_any_other_client_or_session",
        "channel_membership_or_join_leave_authority",
        "whisper_channel_0x556C_schema_or_result_byte_meaning",
        "message_persistence_or_database_write",
        "text_lengths_other_than_12_characters_on_the_request_side",
        "non_ascii_or_thai_text",
        "original_server_response_policy",
        "production_baseline_behavior",
    ],
}

_EXPECTED_BY_ID = {
    _PROFILE_SHARED_SERIALIZER.scenario_id: (
        _EXPECTED_SHARED_SERIALIZER, _PROFILE_SHARED_SERIALIZER,
    ),
    _PROFILE_CHANNEL_SWEEP.scenario_id: (
        _EXPECTED_CHANNEL_SWEEP, _PROFILE_CHANNEL_SWEEP,
    ),
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


def load_channel_message_hypothesis_scenario(
    path: str | Path,
) -> ChannelMessageHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid channel message hypothesis scenario") from exc
    if type(data) is not dict or data.get("id") not in _EXPECTED_BY_ID:
        raise ValueError(
            "channel message hypothesis scenario exceeds the exact allowlist"
        )
    expected, profile = _EXPECTED_BY_ID[data["id"]]
    if not _exact_equal(data, expected):
        raise ValueError(
            "channel message hypothesis scenario exceeds the exact allowlist"
        )
    return require_channel_message_hypothesis_scenario(profile)


def require_channel_message_hypothesis_scenario(
    value: Any,
) -> ChannelMessageHypothesisScenario:
    if type(value) is not ChannelMessageHypothesisScenario or value not in (
        _PROFILE_SHARED_SERIALIZER, _PROFILE_CHANNEL_SWEEP,
    ):
        raise ValueError(
            "channel message hypothesis scenario object exceeds the allowlist"
        )
    _require_derived_channel_ids()
    _require_sweep_order()
    _require_capture_roundtrip()
    return value
