"""LANE-GM / CHAT-TAIL-001: find the chat body inside a MULTI-VITAL frame.

WHY THIS FILE EXISTS.  ``runtime.py`` hands this lane
``bytes(parsed.nested_payload)``, and ``current/pf_login_game_server_v141.py``
sets ``nested_payload`` to EVERY BYTE AFTER THE FIRST NESTED VITAL'S HEADER
-- not to the first vital's body.  On a frame carrying one vital those two
are the same bytes and nothing is wrong.  On a frame carrying two, the chat
body is followed by the next vital's bytes, and
``chat_command.decode_local_talk_payload`` ends with::

    if offset != len(raw):
        raise ChatDecodeError(f"{len(raw) - offset} trailing bytes after wstring#2")

so the whole GM command is refused as ``chat_payload_undecodable_*``.  The GM
types ``/warp 5``, nothing happens, and the refusal names a codec rather than
the real cause.

THE PRECEDENT, AND IT IS MEASURED, NOT ARGUED.  Attended round R303 measured
``vital_count`` of 5 on live inbound traffic from this client (ka1-A, pf_bridge
letter ``20260902_1800``), which is the same fact that cost 42 of 46 pickup
clicks and produced ``vital_walk.py``.  This module is that fact applied to the
one door this lane owns.

!! WHAT IS *NOT* CLAIMED HERE, and it is the honest half of the round.  NO
CAPTURED CHAT FRAME CARRYING A SECOND VITAL EXISTS.  All three chat captures
this project holds (GT-006/GT-009) carry exactly one vital, and this module
has never seen a real multi-vital chat frame.  What is measured is (a) that
the client bundles up to five vitals into one frame on OTHER traffic, and
(b) that if it ever does it on a chat frame, today's route refuses the
command and says the wrong thing about why.  This is hardening plus a named
diagnostic, not the repair of an observed failure -- do not read it as one.

WHY THE BOUNDARY IS NOT GUESSED.  The chat body is self-delimiting: two
``tag 0x48 + u32 LE byte length`` wstring headers, whose lengths account for
every byte of the body (``chat_command``'s module docstring, three captures,
three lengths).  This module reads those two headers to PROPOSE a boundary
and then makes ``decode_local_talk_payload`` -- the strict decoder itself,
unchanged -- the authority on whether the proposal is a chat body.  A
proposal the real decoder refuses is a refusal here too.

AND THE TAIL HAS TO WALK, CLOSED, OR THERE IS NO SPLIT.  The bytes after the
boundary must parse as whole nested vitals -- ``u16(tag 0x12)`` id,
``u8(tag 0x0B)`` version, then a body whose length is DECLARED in
``vital_walk.body_length_table`` -- landing exactly on the end of the
payload.  An id with no declared length, a short body, or one leftover byte
means this module says nothing and the caller keeps today's behaviour, byte
for byte.  Nothing here scans for a plausible next header and nothing falls
back to a partial answer, for ``vital_walk``'s own reason: a guessed boundary
hands a lane the bytes belonging to the vital next door.

NO NEW AUTHORITY, STATED PLAINLY.  Splitting is byte arithmetic that runs
BEFORE ``handle_local_talk_chat`` and changes nothing about who may command:
identity is still decided there, against ``gm_accounts``, on
``session.token``.  A client that could reach a command by wrapping it in a
multi-vital frame could already reach the same command by sending the chat
body alone, so this grants no reach that was not already there.

WHAT IT DOES NOT DO: it does not consume, forward or act on the tail vitals.
They were invisible to every lane on this path before this file existed and
they are invisible after it.  A movement that rode along with a chat line is
still not processed -- this module only proves where the chat body ENDS.
"""
from dataclasses import dataclass
import struct
from typing import Any

from ..vital_walk import MAX_VITALS_PER_FRAME, body_length_table
from .chat_command import (
    MAX_CHAT_PAYLOAD_LENGTH,
    MIN_CHAT_PAYLOAD_LENGTH,
    WSTRING_HEADER_LENGTH,
    WSTRING_TAG,
    ChatDecodeError,
    decode_local_talk_payload,
)

# One ASCII token for the console.  Deliberately NOT `LANE_GM_CHAT_ACTION`:
# an operator grepping for the command route must not have to tell two
# different questions apart inside one token.
CHAT_TAIL_TOKEN = "LANE_GM_CHAT_TAIL"

# The two outcomes that are not refusals.
NO_TAIL = "no_tail"
TAIL_WALKED = "tail_walked"

# Refusal names.  Every one of them means "the caller keeps what it had".
PAYLOAD_NOT_BYTES = "payload_not_bytes"
PAYLOAD_TOO_LARGE_TO_SPLIT = "payload_too_large_to_split"
CHAT_PREFIX_UNREADABLE = "chat_prefix_unreadable"
CHAT_PREFIX_DECODER_REFUSED = "chat_prefix_decoder_refused"
TAIL_UNKNOWN_VITAL_ID = "tail_unknown_vital_id"
TAIL_TRUNCATED = "tail_truncated"
TAIL_TOO_MANY_VITALS = "tail_too_many_vitals"
LEGACY_MODULE_MISSING_FIELDS = "legacy_module_missing_fields"
TAIL_REFUSED_TO_ANSWER = "tail_refused_to_answer"

# The refusals that carry NO evidence of a tail, so they must stay silent:
# they fire on ordinary corrupt or truncated frames, which arrive from the
# wire and would make a console line an unbounded wire-driven write.  This is
# the same lesson `chat_command.py` records for its own format-character
# refusal (pf-adversary D3, round `9wy444`: 100 lines from 100 frames).
QUIET_REASONS = (NO_TAIL, PAYLOAD_NOT_BYTES, CHAT_PREFIX_UNREADABLE)

# The largest body any declared row can have today, read from the table
# rather than typed: the walk cannot need more than this per vital.
_MAX_DECLARED_BODY = 64

# Nested vital header: `u16(tag 0x12)` id + `u8(tag 0x0B)` version, the same
# five bytes v141's own `nested_payload == raw_pc[nested_offset + 5:]`
# invariant is built on (`vital_walk._isolated`).
_NESTED_HEADER_LENGTH = 5

# A bound on what will even be considered for a split, so this file cannot
# turn a size refusal into work.  `handle_local_talk_chat` refuses a payload
# over MAX_CHAT_PAYLOAD_LENGTH; with a tail, the payload legitimately holds a
# body up to that ceiling PLUS whole vitals, and nothing more.
MAX_SPLIT_PAYLOAD_LENGTH = MAX_CHAT_PAYLOAD_LENGTH + MAX_VITALS_PER_FRAME * (
    _NESTED_HEADER_LENGTH + _MAX_DECLARED_BODY
)


@dataclass(frozen=True)
class ChatTailSplit:
    """One payload, split or not.  `body` is None on every refusal."""

    body: bytes | None
    tail_ids: tuple
    reason: str

    @property
    def split(self) -> bool:
        """True only when a tail was proved and the body is shorter."""
        return self.reason == TAIL_WALKED


def split_local_talk_payload(payload: Any, legacy: Any) -> ChatTailSplit:
    """Return the chat body of `payload`, or a named refusal.

    Never raises for wire reasons.  `NO_TAIL` returns the payload unchanged
    and is the answer for every frame this server has ever captured.
    """
    try:
        return _split(payload, legacy)
    except Exception:  # noqa: BLE001 - a split may never break the route
        return ChatTailSplit(None, (), TAIL_REFUSED_TO_ANSWER)


def _split(payload: Any, legacy: Any) -> ChatTailSplit:
    if not isinstance(payload, (bytes, bytearray)):
        return ChatTailSplit(None, (), PAYLOAD_NOT_BYTES)
    raw = bytes(payload)
    if len(raw) > MAX_SPLIT_PAYLOAD_LENGTH:
        return ChatTailSplit(None, (), PAYLOAD_TOO_LARGE_TO_SPLIT)
    boundary = _chat_body_boundary(raw)
    if boundary is None:
        return ChatTailSplit(None, (), CHAT_PREFIX_UNREADABLE)
    if boundary == len(raw):
        # The single-vital frame, which is every frame on main today: the
        # caller's own bytes come back, not a copy of a re-derived slice.
        return ChatTailSplit(raw, (), NO_TAIL)
    body = raw[:boundary]
    try:
        decode_local_talk_payload(body)
    except (ChatDecodeError, TypeError, ValueError):
        return ChatTailSplit(None, (), CHAT_PREFIX_DECODER_REFUSED)
    return _walk_tail(body, raw[boundary:], legacy)


def _chat_body_boundary(raw: bytes) -> int | None:
    """Byte offset just past wstring#2, or None if the headers do not read.

    PROPOSES a boundary; never accepts one.  `_split` hands the proposal to
    `decode_local_talk_payload` and keeps the refusal if that decoder
    disagrees, so the rules that decide what a chat body IS stay in one file.
    """
    if len(raw) < MIN_CHAT_PAYLOAD_LENGTH:
        return None
    offset = 0
    for _index in (1, 2):
        if offset + WSTRING_HEADER_LENGTH > len(raw):
            return None
        if raw[offset] != WSTRING_TAG:
            return None
        (byte_length,) = struct.unpack_from("<I", raw, offset + 1)
        offset += WSTRING_HEADER_LENGTH
        # Read before the slice, exactly as the strict decoder does: a
        # length field of 0xFFFFFFFF is a refusal, never a short slice.
        if byte_length > len(raw) - offset:
            return None
        if byte_length % 2:
            return None
        offset += byte_length
    return offset


def _walk_tail(body: bytes, tail: bytes, legacy: Any) -> ChatTailSplit:
    if not hasattr(legacy, "Cursor"):
        return ChatTailSplit(None, (), LEGACY_MODULE_MISSING_FIELDS)
    table = body_length_table(legacy)
    if not table:
        return ChatTailSplit(None, (), LEGACY_MODULE_MISSING_FIELDS)
    cursor = legacy.Cursor(tail)
    ids: list = []
    while cursor.remain() != 0:
        if len(ids) >= MAX_VITALS_PER_FRAME:
            return ChatTailSplit(None, (), TAIL_TOO_MANY_VITALS)
        try:
            vital_id = cursor.u16(0x12)
            cursor.u8(0x0B)
        except Exception:  # noqa: BLE001 - a short header is a refusal
            return ChatTailSplit(None, (), TAIL_TRUNCATED)
        length = table.get(vital_id)
        if length is None:
            # The fail-closed line, kept identical in spirit to
            # `vital_walk._walk_fields`: an id with no declared length ends
            # the walk and the frame keeps main's behaviour.
            return ChatTailSplit(None, (), TAIL_UNKNOWN_VITAL_ID)
        if cursor.remain() < length:
            return ChatTailSplit(None, (), TAIL_TRUNCATED)
        cursor.p += length
        ids.append(vital_id)
    if not ids:
        # Unreachable while `_split` only calls this with a non-empty tail;
        # kept so a future caller cannot get `TAIL_WALKED` with no evidence.
        return ChatTailSplit(None, (), TAIL_TRUNCATED)
    return ChatTailSplit(body, tuple(ids), TAIL_WALKED)


def tail_console_line(split: ChatTailSplit, payload_length: int) -> str:
    """One ASCII line about ONE frame's split.  Never prints what was typed.

    The GM's sentence is not in reach of this file and must never be: the
    numbers here are byte counts and vital ids, which is what an operator
    needs to tell "the client bundled vitals" apart from "the frame was
    corrupt".
    """
    ids = ",".join("0x%04X" % vital_id for vital_id in split.tail_ids)
    return "%s reason=%s tail_vitals=%d ids=%s chat_bytes=%s payload_bytes=%d" % (
        CHAT_TAIL_TOKEN,
        split.reason,
        len(split.tail_ids),
        ids if ids else "none",
        len(split.body) if split.body is not None else "none",
        payload_length,
    )
