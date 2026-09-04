"""Structural decoder for Activity_CheatCodeVital (client->server, vital id
0x6CEC).

Built per LANE-GM's own backlog (``rounds/GM_20260904_1316_zjbjys_*.md``
item 1): a codec buildable straight from the client's registry plus the
already-proven serializer table, without waiting on any RE ticket -- the
exact "no known answer needed" case GM-003's founding letter (`notes_to_chief
20260826_1630`) calls out as work this lane must build rather than defer.

Layout is PROVEN at the byte level and pinned against the bridge repository:
    pf_bridge/external/PF_SERIALIZER_FIELDS.tsv (rows 4345-4356)
    Activity_CheatCodeVital  W/R  serializer span
        [0x006A0450, 0x006A04F2) sha256
        ba19699b0ff750e75abd226eb3ae25e356f487e4fc325ec6512335dfbf7d3205

Six fields, in order:
    1. tag 0x14 @+0x14, len 4          (u32)
    2. tagged wide string @+0x18       -- see CORRECTION below
    3. tagged wide string @+0x34
    4. tagged wide string @+0x50
    5. tagged wide string @+0x6C
    6. tagged wide string @+0x88

All six fields' W and R rows point at the SAME serializer span and hash,
the same symmetric-shape situation ``gm/cheat_wire.py``'s docstring
explains for CheatVital -- one struct, read and written by the same
client-side function.

CORRECTION -- same lineage as ``gm/command_wire.py``'s and
``gm/cheat_wire.py``'s 2026-09-02 corrections, and NOT an inference by
analogy to either of them: THIS message's own ten string rows are in the
delta table directly.
    pf_bridge/notes_to_chief/reference_codex_attr/PF_A2_STRING_WIRE_TAG_DELTA.tsv
    sha256 e1f4f987c31f53d4dd87845aab01857c8415a8dbcd750af12df9c4cde208b3a2
    base_rows 4347-4356 (W/R ord 2-6): corrected_tag=0x48,
    corrected_full_wire_len=5+N_bytes (not the coarser table's 4+N),
    tag_instruction_va=0x0089A833 (W) / 0x0089A89C (R), all ten rows
    ``push_0x48``.
Each string field is therefore tag(1, =0x48) + uint32-LE byte length +
UTF-16LE payload -- 5+N bytes total, the same shape
``gm/command_wire.py``'s two wide strings and ``gm/forbid_to_talk_wire.py``'s
one wide string already carry.

[สมมติของสาย GM - รอ RE] What is PROVEN stops at "six fields, these tags,
this order, this wide-string shape". What each field MEANS -- is the u32
a cheat-code numeric id, are the five strings a code name plus up to four
parameters, is any of them optional -- is NOT proven. This message has
never been captured (no row for it exists in PF_FIELD_VALIDATION.tsv) and
no RE ticket has ever asked about it. Field names below are positional
only (``field_0x14``, ``text_0x18``, ``text_0x34``, ``text_0x50``,
``text_0x6c``, ``text_0x88``) -- do not rename them to "code_id"/"code_name"/
"arg1".."arg4" or similar without a citation to an RE answer that proves
it.

This module decodes a payload already split out of its runtime-vital
envelope; it does not execute, dispatch, or interpret anything, and it does
not read off a live socket. Intentionally NO encoder: this message is
inbound (client->server) and this repository never sends one, the same
posture ``gm/command_wire.py`` holds for ``GM_RunGMCommandVital`` -- a
round that needs to compose a synthetic frame for testing builds it in the
test file directly, not by adding a server-side encoder this codec has no
use for.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

ACTIVITY_CHEAT_CODE_VITAL_ID = 0x6CEC

SERIALIZER_SPAN_SHA256 = (
    "ba19699b0ff750e75abd226eb3ae25e356f487e4fc325ec6512335dfbf7d3205"
)
STRING_TAG_DELTA_SHA256 = (
    "e1f4f987c31f53d4dd87845aab01857c8415a8dbcd750af12df9c4cde208b3a2"
)

_TAG_U32 = 0x14
# push_0x48 at 0x0089A833 (W) / 0x0089A89C (R) -- see CORRECTION above.
_TAG_WSTRING16 = 0x48

# Defensive upper bound on each decoded string's byte length, same value
# and reason as gm/dispatch.py's MAX_RAW_PAYLOAD_LENGTH / gm/cheat_wire.py's
# MAX_STRING_LENGTH / gm/forbid_to_talk_wire.py's MAX_STRING_LENGTH: no real
# frame of this message has ever been captured, so there is no measured
# real-world length to size this from instead.
MAX_STRING_LENGTH = 65536


class GmActivityCheatCodeWireError(ValueError):
    """Raw bytes do not match the PF_SERIALIZER_FIELDS.tsv pinned wire
    shape, as corrected by PF_A2_STRING_WIRE_TAG_DELTA.tsv rows
    4347-4356."""


@dataclass(frozen=True)
class ActivityCheatCodeBody:
    """One decoded Activity_CheatCodeVital payload.

    Field names are positional only -- see module docstring.
    """

    field_0x14: int
    text_0x18: str
    text_0x34: str
    text_0x50: str
    text_0x6c: str
    text_0x88: str


def _read_u32_tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 5 > len(buf):
        raise GmActivityCheatCodeWireError(
            f"truncated: need 5 bytes for tag 0x{expected_tag:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != expected_tag:
        raise GmActivityCheatCodeWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected "
            f"0x{expected_tag:02X}"
        )
    value = struct.unpack_from("<I", buf, offset + 1)[0]
    return value, offset + 5


def _read_tagged_wstring(buf: bytes, offset: int) -> tuple[str, int]:
    field_offset = offset
    if offset + 5 > len(buf):
        raise GmActivityCheatCodeWireError(
            f"truncated: need 1 tag byte + 4 bytes for a string length at "
            f"offset {offset}, have {len(buf) - offset}"
        )
    if buf[offset] != _TAG_WSTRING16:
        raise GmActivityCheatCodeWireError(
            f"unexpected string tag 0x{buf[offset]:02X} at offset "
            f"{offset}, expected 0x{_TAG_WSTRING16:02X}"
        )
    offset += 1
    byte_len = struct.unpack_from("<I", buf, offset)[0]
    if byte_len % 2 != 0:
        raise GmActivityCheatCodeWireError(
            f"string at offset {field_offset} declares byte_len={byte_len}, "
            "not a whole number of UTF-16LE code units"
        )
    if byte_len > MAX_STRING_LENGTH:
        raise GmActivityCheatCodeWireError(
            f"string at offset {field_offset} declares {byte_len} bytes, "
            f"exceeds MAX_STRING_LENGTH={MAX_STRING_LENGTH}"
        )
    start = offset + 4
    end = start + byte_len
    if end > len(buf):
        raise GmActivityCheatCodeWireError(
            f"truncated: string at offset {field_offset} declares "
            f"{byte_len} bytes, have {len(buf) - start}"
        )
    try:
        text = buf[start:end].decode("utf-16-le")
    except UnicodeDecodeError as exc:
        raise GmActivityCheatCodeWireError(
            f"string at offset {field_offset} is not valid UTF-16LE: {exc}"
        ) from exc
    return text, end


def decode_activity_cheat_code_vital(raw: bytes) -> ActivityCheatCodeBody:
    """Decode the pinned wire shape of one Activity_CheatCodeVital payload.

    ``raw`` is the vital's payload bytes only (the bytes after vital id and
    version in the runtime-vital envelope), not the whole frame. Raises
    ``GmActivityCheatCodeWireError`` when the bytes do not match the pinned
    shape, including any bytes left over after all six fields decode
    cleanly -- a real payload is expected to consume the buffer exactly,
    the same discipline ``gm/command_wire.py`` and ``gm/cheat_wire.py``
    apply.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be bytes")
    buf = bytes(raw)
    field_0x14, offset = _read_u32_tag(buf, 0, _TAG_U32)
    text_0x18, offset = _read_tagged_wstring(buf, offset)
    text_0x34, offset = _read_tagged_wstring(buf, offset)
    text_0x50, offset = _read_tagged_wstring(buf, offset)
    text_0x6c, offset = _read_tagged_wstring(buf, offset)
    text_0x88, offset = _read_tagged_wstring(buf, offset)
    if offset != len(buf):
        raise GmActivityCheatCodeWireError(
            f"decoded cleanly but {len(buf) - offset} trailing byte(s) remain"
        )
    return ActivityCheatCodeBody(
        field_0x14, text_0x18, text_0x34, text_0x50, text_0x6c, text_0x88
    )
