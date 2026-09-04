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

~~!! WHAT IS *NOT* CLAIMED HERE, and it is the honest half of the round.  NO
CAPTURED CHAT FRAME CARRYING A SECOND VITAL EXISTS.  All three chat captures
this project holds (GT-006/GT-009) carry exactly one vital, and this module
has never seen a real multi-vital chat frame.  What is measured is (a) that
the client bundles up to five vitals into one frame on OTHER traffic, and
(b) that if it ever does it on a chat frame, today's route refuses the
command and says the wrong thing about why.  This is hardening plus a named
diagnostic, not the repair of an observed failure -- do not read it as one.~~

RETIRED BY MEASUREMENT, round `ff30oi`.  The nonclaim above is struck rather
than deleted because it was true when written and the history of what this
house believed is not editable.  Attended round R313 (pf_bridge letter
``20260905_0212_KA1A-R313-RESULTS-...``, section 3) captured the frame it
said did not exist: 02:01:58, frame #8, 171 B, vital ``0xAC52`` carrying the
chat text ``/warp 126`` IMMEDIATELY FOLLOWED BY vital ``0x0F01``
(``UserSetting_UpdateServerSettingVital``) in the same frame.  The GM typed
the command, the console printed
``LANE_GM_CHAT_TAIL reason=tail_unknown_vital_id tail_vitals=0 ids=none
chat_bytes=none payload_bytes=151``, and NOTHING HAPPENED -- no
``GM_CHAT_STAGED``, no row written, no message to the player.  The letter's
own note says the client emits ``UserSetting_UpdateServerSettingVital`` every
time a UI window opens or closes, so this is not a rare shape: it is what a
GM command typed within a few seconds of opening any window looks like.
That is why the ``tail_unknown_vital_id`` branch below no longer discards the
chat body -- see ``TAIL_UNDECLARED_BODY``.

WHAT IS STILL NOT CLAIMED.  The tail is still not consumed, forwarded or
acted on by anything (see the cost paragraph below); ``vital_count`` on the
console line is still ``unavailable`` because ``runtime.py`` does not pass
it to this lane; and nothing here is evidence about what ``0x0F01``'s body
means -- only that its five-byte nested header reads, which is all the
boundary argument needs.

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

WHAT IT DOES NOT DO, AND THIS IS A COST RATHER THAN A VIRTUE.  It does not
consume, forward or act on the tail vitals.  They were invisible to every
lane on this path before this file existed and they are invisible after it.
Say the consequence in R303's own terms, because pf-adversary (D10, round
`uyzr8c`) is right that the neutral wording hid it: 0xAC52 has no row in
``vital_walk.body_length_table`` and can never have one (its body is two
length-prefixed strings, not a declared length), so a frame that LEADS with
0xAC52 is exactly a frame ``walk_nested_vitals`` refuses with
``unknown_vital_id`` -- the TargetPos-promotion lane stands down and the
R303 position freeze is NOT fixed for it.  This module computes the one
number that would fix that (``boundary`` IS the chat vital's body length)
and then discards it.  Handing it to LANE-E is the letter
``20260903_1230_LANE-GM-TO-CHIEF-chat-route-cannot-see-a-chat-vital-that-is-
not-first.md``, not a change this lane may make in ``vital_walk.py``.

WHERE IT SITS IN THE CALL, which is load-bearing after pf-adversary's D1:
``chat_command_action`` asks this module only AFTER
``handle_local_talk_chat`` has authorized the account and refused the frame
as ``chat_payload_undecodable_*``.  A non-GM therefore reaches nothing here
-- no decode, no event, no console line -- and a payload over
``MAX_CHAT_PAYLOAD_LENGTH`` is refused by that ceiling before any of this
runs.  The first draft asked first and cost both properties.
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

# The outcomes that are not refusals.
NO_TAIL = "no_tail"
TAIL_WALKED = "tail_walked"

#: R313's outcome, and the one this round adds.  The boundary is proved --
#: the strict decoder accepted the prefix and accounted for every byte of it
#: -- and the tail begins with a WELL-FORMED nested-vital header (`u16(tag
#: 0x12)` id, `u8(tag 0x0B)` version) whose id this house declares no body
#: length for.  The chat command runs on the isolated body; the tail is NOT
#: consumed, exactly as under `TAIL_WALKED`.
#:
#: WHY THIS IS NOT A GUESSED BOUNDARY, which is the objection to answer.
#: There is only ever ONE candidate boundary: `_chat_body_boundary` derives
#: it from the two length fields at the FRONT of the payload and from
#: nothing else, and `decode_local_talk_payload` -- the strict decoder,
#: unchanged -- must then accept those exact bytes with none left over.  The
#: tail walk never contributed to FINDING the boundary; it only corroborated
#: it, and on R313's frame corroboration is impossible in principle: 0x0F01's
#: body is not a declared fixed length, so no future table row makes that
#: walk close.  Refusing there did not keep a bad boundary out, it threw a
#: proved one away.
#:
#: WHAT IT STILL REFUSES.  A tail whose first five bytes are not a nested
#: header (wrong tag, short) is `TAIL_TRUNCATED` and the caller keeps main's
#: behaviour, exactly as before.  So the frame must still LOOK like "chat
#: body, then a nested vital" in both halves; only the length of that
#: vital's body is allowed to be unknown.
#:
#: NO NEW AUTHORITY: identity is still decided in `handle_local_talk_chat`
#: against `gm_accounts`, below this, and a client that can reach a command
#: this way could already reach it by sending the chat body alone.
TAIL_UNDECLARED_BODY = "tail_undeclared_body"

# Refusal names.  Every one of them means "the caller keeps what it had".
# `PAYLOAD_NOT_BYTES` is DEAD ON THE WIRE PATH and named here so no coverage
# claim is made about it: `make_gm_chat_command_action` refuses a non-bytes
# payload with its own event before this module is reached (pf-adversary
# D14).  It stays because this function is public and a future caller does
# not inherit that check.
PAYLOAD_NOT_BYTES = "payload_not_bytes"
PAYLOAD_TOO_LARGE_TO_SPLIT = "payload_too_large_to_split"
CHAT_PREFIX_UNREADABLE = "chat_prefix_unreadable"
CHAT_PREFIX_DECODER_REFUSED = "chat_prefix_decoder_refused"
#: RETIRED AS AN OUTCOME BY R313, kept as a name so the console lines this
#: server has already printed stay readable and so nothing silently reuses
#: the string.  No code path returns it any more; `TAIL_UNDECLARED_BODY`
#: replaces it.  `RetiredReasonTests` pins that it is unreachable, because a
#: constant nobody returns is otherwise indistinguishable from one nobody
#: noticed had stopped firing.
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

# The largest body any declared row has today.  IT IS TYPED, and the earlier
# comment claiming it was "read from the table" was simply false
# (pf-adversary D9): the table needs a `legacy` module and this constant is
# built at import time, where there is none.  What keeps it honest is a test
# -- `MaxDeclaredBodyTests` asserts `max(body_length_table(legacy).values())`
# is not above this number -- so the day LANE-E declares a longer body, the
# suite says so instead of a legitimate frame quietly refusing as
# `payload_too_large_to_split`.
_MAX_DECLARED_BODY = 64

# Nested vital header: `u16(tag 0x12)` id + `u8(tag 0x0B)` version, the same
# five bytes v141's own `nested_payload == raw_pc[nested_offset + 5:]`
# invariant is built on (`vital_walk._isolated`).
_NESTED_HEADER_LENGTH = 5

# A bound on what will even be considered for a split.  It is a WORK bound,
# not the security bound it was in the first draft: since D1 moved the split
# below `handle_local_talk_chat`, a payload over MAX_CHAT_PAYLOAD_LENGTH is
# already refused by that ceiling and never arrives here at all.  What is
# left for this number to do is cap the arithmetic on a frame that IS under
# the ceiling, at the largest size a real one could be: a body up to the
# ceiling PLUS whole declared vitals, and nothing more.  Pinned as a literal
# by `SplitCeilingTests`, because a test that derives its oversized input
# from the constant passes for every value of it (pf-adversary D3).
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
        """True only when a tail was proved and the body is shorter.

        Both non-refusal tail outcomes count: under `TAIL_WALKED` every tail
        vital closed, under `TAIL_UNDECLARED_BODY` the first tail header read
        and its body length is undeclared.  In both, `body` is the isolated
        chat body and it is shorter than the payload.
        """
        return self.reason in (TAIL_WALKED, TAIL_UNDECLARED_BODY)


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
            # R313's line.  The header read (both tags, both widths), so the
            # tail IS a nested vital; this house just declares no body length
            # for its id.  The walk ends here -- nothing past this id is
            # inspected and nothing is consumed -- but the BODY stands,
            # because the boundary was never the walk's to prove.  The id is
            # reported so the console line names what needs a declared
            # length, which is the whole of what a reader can do about it.
            ids.append(vital_id)
            return ChatTailSplit(body, tuple(ids), TAIL_UNDECLARED_BODY)
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

    THE FIELDS ARE FIXED AND PINNED (`ConsoleLineTests`): a token, then
    exactly `reason`, `tail_vitals`, `ids`, `chat_bytes`, `payload_bytes`,
    `vital_count`.  The pin is not tidiness.  pf-adversary (D2, round
    `uyzr8c`) added `body=%r` to this line and every test still passed,
    because the chat body is UTF-16LE and an ASCII `assertNotIn("password")`
    can never match `p\\x00a\\x00s\\x00s\\x00`.  A test that greps for a
    leaked sentence cannot work here; a test that fixes the whole line can.

    `vital_count=unavailable` IS THE HONEST HALF, and it is printed rather
    than omitted.  The number that would corroborate what this line is FOR
    -- how many vitals the frame declared -- lives in `parsed.vital_count`,
    which `runtime.py:7026` does not pass to this lane.  Without it, this
    line cannot separate "the client bundled a second vital into a chat
    frame" from "the payload carried trailing bytes shaped like one", and a
    round that read `reason=tail_walked` as the first capture of a
    multi-vital chat frame would be retiring this module's own NONCLAIM on
    evidence that does not reach it (pf-adversary D8).  The word is on the
    line so nobody has to remember that from a docstring.
    """
    ids = ",".join("0x%04X" % vital_id for vital_id in split.tail_ids)
    return (
        "%s reason=%s tail_vitals=%d ids=%s chat_bytes=%s payload_bytes=%d"
        " vital_count=unavailable"
    ) % (
        CHAT_TAIL_TOKEN,
        split.reason,
        len(split.tail_ids),
        ids if ids else "none",
        len(split.body) if split.body is not None else "none",
        payload_length,
    )
