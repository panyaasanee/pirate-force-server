"""Structural codec for CheatVital (0x162E) -- a single 0x44-tagged, narrow
(8-bit char) length-prefixed string field.

Layout is PROVEN at the byte level and pinned against the bridge repository:
    pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv  (row 14: 0x162E CheatVital)
    pf_bridge/external/PF_SERIALIZER_FIELDS.tsv  (rows 565-566)

    CheatVital  W  serializer span [0x005E53A0,0x005E53C7) sha256
        3e7899321da79221d0bf2c5641dc7e0022bc6acf439794c7f61b6c7efe2f6fad
    CheatVital  R  serializer span [0x005E53A0,0x005E53C7) sha256
        3e7899321da79221d0bf2c5641dc7e0022bc6acf439794c7f61b6c7efe2f6fad

Both the W (write/encode, function `string_wire_call@0x005E53AF`) and R
(read/decode, `string_wire_call@0x005E53BF`) rows point at the SAME
serializer span and the same helper target (`0x0089A6D0`/`0x0089A740`,
`kind=basic_string<char>`, `length_prefix=uint32le`, `payload=N_bytes`) --
the row-level proof (`basis=exact_helper_bytes_and_pe_imports`) is symmetric
by construction, which is why this module exposes one shape for both
directions instead of a distinct encoder/decoder pair per direction the way
``gm/command_wire.py`` and ``gm/state_wire.py`` do (those messages have
genuinely different W and R shapes; this one does not).


CORRECTION 2026-09-02 (LANE-GM round q6p0pb, consuming ka1-B's letter
notes_to_chief/20260901_2215_KA1B-TO-LANE-GM-third-untagged-string-module-...):
the string field on this message is NOT untagged.  The client's own string
helper pushes a type tag byte BEFORE the uint32-LE byte count, so the wire
shape is  tag(1) + uint32le byte_count(4) + payload(N)  and the full field is
5+N bytes, not 4+N.  Source, pinned:
    pf_bridge/notes_to_chief/reference_codex_attr/PF_A2_STRING_WIRE_TAG_DELTA.tsv
    sha256 e1f4f987c31f53d4dd87845aab01857c8415a8dbcd750af12df9c4cde208b3a2
The delta rows carry the SAME base_span sha256 this module already pins
below -- and the same helper span -- so this is the same lineage re-reading
the same bytes, which is a reason to look for an outside tiebreaker, not a
reason to trust it on its own.

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

!! WEAKEST LINK, on the record: the corroboration above is for the WIDE
helper (0x48).  The narrow 0x44 this module writes has the delta rows and the
helper disassembly and nothing else -- no captured frame in this project has
ever carried a 0x44 string that a client accepted.  Treat this codec's tag as
the least-supported of the three modules corrected on 2026-09-02.
    rows 565 (W) / 566 (R), tag instructions 0x0089A6F1 / 0x0089A75C,
    both `push 0x44` -- narrow `basic_string<char>`.

What is PROVEN stops at "one tagged field (0x44), a uint32-LE byte length,
then that many raw bytes, `basic_string<char>` (narrow, not the
`basic_string<wchar_t>` the two ``GM_RunGMCommandVital`` strings use)".
What the string's BYTE ENCODING is (CP874, since this is a Thai-language
client that already forces `cp874:strict` on other narrow text -- see
``gm/login_scene_override.py`` -- or plain ASCII/Latin-1, or something else)
is NOT proven anywhere in the cited rows, so this module does not decode the
payload to ``str`` at all -- it hands the caller raw ``bytes`` in both
directions, the same "do not guess a codec this lane cannot cite" discipline
``gm/command_wire.py`` applies to its own two wide strings before RE-091.

docs/GM_LANE.md's "Wire facts used (pinned)" table already carried the note
"(reference only, not reused as GM wire)" for this row before this round,
and that stays true here: the message this lane actually decodes for GM
chat commands is ``GM_RunGMCommandVital`` (0x51E9, ``gm/command_wire.py``),
a completely different serializer with a completely different shape (five
fields including a presence gate and two WIDE strings). CheatVital sharing
the ``+0x14`` field offset with that message's own fields is a coincidence
of position in two unrelated structs, not evidence the two are related, and
nothing in this package imports this module. This module exists only so a
byte-proven layout has a tested round-trip codec on file -- the same
reference-codec role ``gm/teleport_wire.py``'s ``ForcePos``/``CWarpResult``
held (``PF_FIELD_VALIDATION.tsv`` direction NOT_OBSERVED for those two, same
as this message) before ``gm/warp_executor.py`` bridged them to a live
command. This round does not propose wiring CheatVital into ``dispatch.py``
or ``runtime.py``, and does not claim a use for it beyond the codec itself.

This module builds/reads payload bytes only (the bytes after vital id and
version in the runtime-vital envelope). It does not execute anything, does
not touch player/world/GM state, and does not read off a live socket.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

CHEAT_VITAL_ID = 0x162E

SERIALIZER_SPAN_SHA256 = (
    "3e7899321da79221d0bf2c5641dc7e0022bc6acf439794c7f61b6c7efe2f6fad"
)

# Defensive upper bound on the decoded string's byte length. Not part of the
# proven wire layout (the length prefix is a full uint32-LE, so the format
# itself allows up to 0xFFFFFFFF bytes) -- exists only so a malformed or
# hostile 4-byte length prefix cannot make ``decode_cheat_vital_payload``
# attempt to slice/allocate a multi-gigabyte buffer from a tiny input, the
# same failure shape ``gm/command_wire.py``'s wstring reader is exposed to
# and ``gm/dispatch.py``'s ``MAX_RAW_PAYLOAD_LENGTH`` guards against one
# layer up for the message this lane actually dispatches. No real
# CheatVital frame has been captured (``PF_FIELD_VALIDATION.tsv``:
# NOT_OBSERVED both directions), so there is no measured real-world length
# to size this from; 65536 matches ``gm/dispatch.py``'s own
# ``MAX_RAW_PAYLOAD_LENGTH`` for the same reason stated there -- generous
# for any plausible short string, far below anything that could stall a
# handling thread.
MAX_STRING_LENGTH = 65536

# The client's narrow-string helper (W 0x0089A6D0, R 0x0089A740) pushes this
# tag byte before the length.  0x44, not the 0x48 the two wide
# `GM_RunGMCommandVital` strings carry -- see the CORRECTION block above.
STRING8_TAG = 0x44


class GmCheatWireError(ValueError):
    """Raw bytes do not match the PF_SERIALIZER_FIELDS.tsv pinned wire shape."""


@dataclass(frozen=True)
class CheatVitalBody:
    """One decoded CheatVital payload.

    ``text`` is the raw, UNDECODED string bytes -- see the module docstring
    for why this codec does not assume a character encoding.
    """

    text: bytes


def make_cheat_vital_payload(text: bytes) -> bytes:
    """Build the 0x44-tagged uint32-LE-length-prefixed string body.

    ``text`` must already be encoded to bytes by the caller -- this
    function does not encode a ``str`` (see module docstring: the byte
    encoding is not proven).
    """
    if not isinstance(text, (bytes, bytearray)):
        raise TypeError("text must be bytes")
    text = bytes(text)
    if len(text) > MAX_STRING_LENGTH:
        raise GmCheatWireError(
            f"text is {len(text)} bytes, exceeds MAX_STRING_LENGTH="
            f"{MAX_STRING_LENGTH}"
        )
    return bytes((STRING8_TAG,)) + struct.pack("<I", len(text)) + text


def decode_cheat_vital_payload(raw: bytes) -> CheatVitalBody:
    """Decode the pinned wire shape of one CheatVital payload.

    ``raw`` is the vital's payload bytes only (the bytes after vital id and
    version in the runtime-vital envelope), not the whole frame. Raises
    ``GmCheatWireError`` when the bytes do not match the pinned shape,
    including any bytes left over after the string is consumed -- a real
    payload is expected to be exactly the tag byte, the length prefix and its
    declared bytes, nothing more.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be bytes")
    buf = bytes(raw)
    if len(buf) < 5:
        raise GmCheatWireError(
            f"truncated: need 1 tag byte + 4 bytes for the length prefix, "
            f"have {len(buf)}"
        )
    if buf[0] != STRING8_TAG:
        raise GmCheatWireError(
            f"unexpected string tag 0x{buf[0]:02X} at offset 0, expected "
            f"0x{STRING8_TAG:02X}"
        )
    byte_len = struct.unpack_from("<I", buf, 1)[0]
    if byte_len > MAX_STRING_LENGTH:
        raise GmCheatWireError(
            f"declared length {byte_len} exceeds MAX_STRING_LENGTH="
            f"{MAX_STRING_LENGTH}"
        )
    start = 5
    end = start + byte_len
    if end > len(buf):
        raise GmCheatWireError(
            f"truncated: declares {byte_len} bytes, have {len(buf) - start}"
        )
    if end != len(buf):
        raise GmCheatWireError(
            f"decoded cleanly but {len(buf) - end} trailing byte(s) remain"
        )
    return CheatVitalBody(text=buf[start:end])
