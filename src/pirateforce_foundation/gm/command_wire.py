"""Structural decoder for GM_RunGMCommandVital (0x51E9, client->server), plus
the one-field reader for GM_RunGMCommandResultVital (0x8C77, server->client).

Layout is PROVEN at the byte level by RE-088 (STRUCTURAL-LAYOUT-PINNED,
``pf_bridge/notes_to_chief/20260826_1811_RE-088-RESULT-GM-COMMAND-WIRE-PINNED.md``).
That result closes the earlier "two runtime-selected sub-paths" open
question recorded in ``docs/GM_LANE.md``: there is exactly one nested body,
gated by a presence flag, and RE-088 found no field proven to be a separate
sub-opcode.  Pinned against
    pf_bridge/external/PF_SERIALIZER_FIELDS.tsv
    GM_RunGMCommandVital        outer  span [0x00729E10,0x00729EB7) sha256
        541d82f511ba87d444587da9f217ee7eb436431c21e7cfca6dd026d19a8c8554
    GM_RunGMCommandVital        nested span [0x00726C20,0x00726CB1) sha256
        aa3c7c8d2d92eeee48508da2c26d78e360c612aaa2b682dfb608d7b08493559d
    GM_RunGMCommandResultVital  span [0x00729790,0x007297B3) sha256
        ad65d125ab8a97db872ae5b2e957280a431d55beb7956050652a2d58dee633e9

CORRECTION 2026-09-02 (LANE-GM round q6p0pb, consuming ka1-B's letter
notes_to_chief/20260901_2215_KA1B-TO-LANE-GM-third-untagged-string-module-...):
``string_0x1c`` and ``string_0x38`` are NOT untagged.  The client's wide
string helper pushes a type tag byte 0x48 BEFORE the uint32-LE byte count, so
each string is  0x48 + uint32le byte_count + payload  = 5+N bytes on the
wire, not 4+N.  Rows 6266/6267 (W ord 6/7) and 6279/6280 (R ord 9/10) of
    pf_bridge/notes_to_chief/reference_codex_attr/PF_A2_STRING_WIRE_TAG_DELTA.tsv
    sha256 e1f4f987c31f53d4dd87845aab01857c8415a8dbcd750af12df9c4cde208b3a2
carry the SAME nested-span sha256 pinned above
(aa3c7c8d...93559d), byte for byte, so this corrects a re-read of RE-088's
own bytes rather than setting a second source against it -- which also means
the delta is not independent of it, and needs the outside corroboration
below.
Corroboration beyond that table -- this correction is NOT IMAGE-only evidence
even though the delta rows themselves are (`PF_A2_A3_STRING_WIRE_CORRECTION.md`
states `source=IMAGE`, and the delta is the SAME lineage re-reading the SAME
helper bytes, so it is not an independent second source on its own):
  * the shared `Channel_*` string codec that already exists in this
    repository -- named in `docs/GM_LANE.md` row 0x9F2C, deliberately NOT
    named here because a lane gate test forbids modules in this package from
    naming it -- has carried tag 0x48 with a 5-byte header against the SAME
    helper VAs (W 0x0089A810 / R 0x0089A880) since 2026-08-18, corroborated
    against real captured frames (GT-006).
  * `current/pf_login_game_server_v141.py:21-24` records a LIVE client
    rejecting a frame (ErrorData=0x2A7A) because that helper's string went out
    with tag 0x44 instead of 0x48.
What is still NOT proven: the tag byte's own semantics (domain, signedness,
sentinel values) -- `PF_HANDOFF_V1.md` 8.5 gives proven meanings only for
0x2A/0x12.  We reproduce the byte; we do not claim to know what it encodes.
  Tag instructions:
0x0089A833 (W) / 0x0089A89C (R), both ``push 0x48``.  Nothing had ever
decoded a real frame through the old shape -- ``PF_FIELD_VALIDATION.tsv``
still has zero captured GM_RunGMCommandVital frames -- so no earlier result
rests on the 4+N reading.

[สมมติของสาย GM - รอ RE] What RE-088 proves stops at "this many fields, these
tags, this order, no separate sub-opcode".  It explicitly does NOT prove what
any field means: the two wide strings are NOT confirmed to be a command name
and its argument text (that mapping, and the live chat-input trigger
condition, is RE-091 -- still open), the three scalars have no confirmed
meaning, and the result byte is not confirmed to be a success/error code
(``PF_FIELD_VALIDATION.tsv`` status is NOT_OBSERVED for all of them -- zero
real frames captured yet).  Every field below is named by its wire position
only (``field_0x10``, ``field_0x14``, ``field_0x18``, ``string_0x1c``,
``string_0x38``) -- do not rename these to "command"/"argument"/"result_code"
or similar without a citation to the RE answer that proves it.

This module decodes a payload already split out of its runtime-vital
envelope; it does not execute, dispatch, or interpret anything, and it does
not read off a live socket.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

GM_RUN_GM_COMMAND_VITAL_ID = 0x51E9
GM_RUN_GM_COMMAND_RESULT_VITAL_ID = 0x8C77

OUTER_SERIALIZER_SPAN_SHA256 = (
    "541d82f511ba87d444587da9f217ee7eb436431c21e7cfca6dd026d19a8c8554"
)
NESTED_SERIALIZER_SPAN_SHA256 = (
    "aa3c7c8d2d92eeee48508da2c26d78e360c612aaa2b682dfb608d7b08493559d"
)
RESULT_SERIALIZER_SPAN_SHA256 = (
    "ad65d125ab8a97db872ae5b2e957280a431d55beb7956050652a2d58dee633e9"
)

_TAG_U8 = 0x0B
_TAG_U32 = 0x14


class GmCommandWireError(ValueError):
    """Raw bytes do not match the RE-088 pinned wire shape.

    Callers that must never lose a raw capture (see gm/command_capture.py)
    should catch this and keep the raw bytes regardless -- this exception
    means "does not decode against the current pin", not "malicious" or
    "discard".
    """


@dataclass(frozen=True)
class GmRunCommandBody:
    """One decoded GM_RunGMCommandVital nested body.

    Field names are positional only (see module docstring) -- none of them
    is a confirmed command name, argument, or flag.

    ``presence`` is the *actual* byte value read from the wire, not a
    normalized 0/1: RE-088's own gate condition is "!= 0" (`setne al`), so
    any nonzero byte gates the nested body exactly like 1 does, but a caller
    logging or displaying this value must show what was actually observed
    (e.g. 200), not silently normalize it to 1 -- a forensic capture record
    that always prints "presence=1" regardless of the real byte would be
    lying about what a fuzzed or malformed send actually contained.
    """

    presence: int
    field_0x10: int
    field_0x14: int
    field_0x18: int
    string_0x1c: str
    string_0x38: str


def _read_u8_tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 2 > len(buf):
        raise GmCommandWireError(
            f"truncated: need 2 bytes for tag 0x{expected_tag:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != expected_tag:
        raise GmCommandWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected "
            f"0x{expected_tag:02X}"
        )
    return buf[offset + 1], offset + 2


def _read_u32_tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 5 > len(buf):
        raise GmCommandWireError(
            f"truncated: need 5 bytes for tag 0x{expected_tag:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != expected_tag:
        raise GmCommandWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected "
            f"0x{expected_tag:02X}"
        )
    value = struct.unpack_from("<I", buf, offset + 1)[0]
    return value, offset + 5


# The client's wide-string helper (W 0x0089A810, R 0x0089A880) pushes this tag
# byte before the uint32-LE byte count: `push 0x48` at 0x0089A833 (W) and
# 0x0089A89C (R).  See CORRECTION 2026-09-02 in the module docstring.
_TAG_WSTRING16 = 0x48


def _read_tagged_wstring(buf: bytes, offset: int) -> tuple[str, int]:
    field_offset = offset  # messages name where the FIELD starts, not the length
    if offset + 5 > len(buf):
        raise GmCommandWireError(
            f"truncated: need 1 tag byte + 4 bytes for a string length at "
            f"offset {offset}, have {len(buf) - offset}"
        )
    if buf[offset] != _TAG_WSTRING16:
        raise GmCommandWireError(
            f"unexpected string tag 0x{buf[offset]:02X} at offset {offset}, "
            f"expected 0x{_TAG_WSTRING16:02X}"
        )
    offset += 1
    byte_len = struct.unpack_from("<I", buf, offset)[0]
    if byte_len % 2 != 0:
        raise GmCommandWireError(
            f"string at offset {field_offset} declares byte_len={byte_len}, not a "
            "whole number of UTF-16LE code units"
        )
    start = offset + 4
    end = start + byte_len
    if end > len(buf):
        raise GmCommandWireError(
            f"truncated: string at offset {field_offset} declares {byte_len} bytes, "
            f"have {len(buf) - start}"
        )
    try:
        text = buf[start:end].decode("utf-16-le")
    except UnicodeDecodeError as exc:
        raise GmCommandWireError(
            f"string at offset {field_offset} is not valid UTF-16LE: {exc}"
        ) from exc
    return text, end


def decode_gm_run_command_vital(raw: bytes) -> GmRunCommandBody | None:
    """Decode the RE-088 pinned wire shape of one GM_RunGMCommandVital payload.

    ``raw`` is the vital's payload bytes only (the bytes after vital id and
    version in the runtime-vital envelope), not the whole frame.

    Returns ``None`` when the presence flag is 0 -- a structurally valid,
    empty message (RE-088: "if zero, serializer stops").  Raises
    ``GmCommandWireError`` when the bytes do not match the pinned shape,
    including any bytes left over after a nested body decodes cleanly: a
    real client payload is expected to consume the buffer exactly.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be bytes")
    buf = bytes(raw)
    presence, offset = _read_u8_tag(buf, 0, _TAG_U8)
    if presence == 0:
        if offset != len(buf):
            raise GmCommandWireError(
                f"presence=0 but {len(buf) - offset} trailing byte(s) remain"
            )
        return None
    field_0x10, offset = _read_u32_tag(buf, offset, _TAG_U32)
    field_0x14, offset = _read_u32_tag(buf, offset, _TAG_U32)
    field_0x18, offset = _read_u8_tag(buf, offset, _TAG_U8)
    string_0x1c, offset = _read_tagged_wstring(buf, offset)
    string_0x38, offset = _read_tagged_wstring(buf, offset)
    if offset != len(buf):
        raise GmCommandWireError(
            f"nested body decoded cleanly but {len(buf) - offset} trailing "
            "byte(s) remain"
        )
    return GmRunCommandBody(
        presence, field_0x10, field_0x14, field_0x18, string_0x1c, string_0x38
    )


def decode_gm_run_command_result_vital(raw: bytes) -> int:
    """Decode the single tag(0x0B) byte field of GM_RunGMCommandResultVital.

    Its meaning is NOT proven (RE-088 explicitly declines to call it a
    success/error code) -- do not rename this return value without a
    citation to the RE answer that proves what it means.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be bytes")
    buf = bytes(raw)
    value, offset = _read_u8_tag(buf, 0, _TAG_U8)
    if offset != len(buf):
        raise GmCommandWireError(
            f"decoded cleanly but {len(buf) - offset} trailing byte(s) remain"
        )
    return value
