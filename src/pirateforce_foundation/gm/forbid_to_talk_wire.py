"""Wire builder for GM_ForbidToTalkResultVital (server->client, vital id
0x8D30).

Built per LANE-GM's own backlog (``rounds/GM_20260904_1316_zjbjys_*.md``
item 1): a codec buildable straight from the client's registry plus the
already-proven serializer table, without waiting on any RE ticket -- the
exact "no known answer needed" case GM-003's founding letter (`notes_to_chief
20260826_1630`) calls out as work this lane must build rather than defer.

Layout is PROVEN at the byte level and pinned against the bridge repository:
    pf_bridge/external/PF_SERIALIZER_FIELDS.tsv (rows 6283-6288)
    GM_ForbidToTalkResultVital  W/R  serializer span
        [0x007297C0, 0x00729821) sha256
        20b2f1df07e0b6619104af56b71e11fffd4c1cac24dd8afdb5f35e35fbc51bfc

Three fields, in order:
    1. tag 0x0B @+0x14, len 1   (u8)
    2. tag 0x14 @+0x18, len 4   (u32)
    3. tagged wide string @+0x1C -- see CORRECTION below for the real shape

All three fields' W and R rows in PF_SERIALIZER_FIELDS.tsv point at the
SAME serializer span and the same hash -- the same symmetric-shape
situation ``gm/cheat_wire.py``'s docstring explains for CheatVital -- which
is why this message is one struct read and written by one function, not a
distinct pair.

CORRECTION -- same lineage as ``gm/command_wire.py``'s and
``gm/cheat_wire.py``'s 2026-09-02 corrections, and NOT an inference by
analogy to either of them: THIS message's own two rows are in the delta
table directly.
    pf_bridge/notes_to_chief/reference_codex_attr/PF_A2_STRING_WIRE_TAG_DELTA.tsv
    sha256 e1f4f987c31f53d4dd87845aab01857c8415a8dbcd750af12df9c4cde208b3a2
    base_row 6287 (W ord 3) / 6288 (R ord 3): corrected_tag=0x48,
    corrected_full_wire_len=5+N_bytes (not the coarser table's 4+N),
    tag_instruction_va=0x0089A833 (W) / 0x0089A89C (R), both ``push_0x48``.
Field 3 is therefore tag(1, =0x48) + uint32-LE byte length + UTF-16LE
payload -- 5+N bytes total. ``legacy.wstr_tag`` (``current/
pf_login_game_server_v141.py:590-592``) already emits exactly that shape
(``b"\\x48" + struct.pack("<I", len(b)) + b``), so this module calls it
rather than re-deriving the bytes -- the same "reuse the shipped encoder"
instruction GM-003's founding letter and this round's own brief both give.

[สมมติของสาย GM - รอ RE] What is PROVEN stops at "three fields, these tags,
this order, this wide-string shape". What each field MEANS -- is field 1 a
mute flag, is field 2 a duration in seconds, is the string a reason shown to
the muted player -- is NOT proven. This message has never been captured
(no row for it exists in PF_FIELD_VALIDATION.tsv) and no RE ticket has ever
asked about it. Field names below are positional only (``field_0x14``,
``field_0x18``, ``text_0x1c``) -- do not rename them to "muted"/
"duration_seconds"/"reason" or similar without a citation to an RE answer
that proves it.

This module builds/reads payload bytes only (the bytes after vital id and
version in the runtime-vital envelope). It does not execute anything, does
not touch player/world/GM state, does not read off a live socket, and is
not wired into ``dispatch.py`` or ``runtime.py`` by this round -- wiring a
real send is CORE-REQUEST territory (``docs/GM_LANE.md``), same posture
``gm/state_wire.py`` and ``gm/teleport_wire.py`` hold for their own
messages before a wiring round picks them up.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

GM_FORBID_TO_TALK_RESULT_VITAL_ID = 0x8D30

SERIALIZER_SPAN_SHA256 = (
    "20b2f1df07e0b6619104af56b71e11fffd4c1cac24dd8afdb5f35e35fbc51bfc"
)
STRING_TAG_DELTA_SHA256 = (
    "e1f4f987c31f53d4dd87845aab01857c8415a8dbcd750af12df9c4cde208b3a2"
)

_TAG_U8 = 0x0B
_TAG_U32 = 0x14
# push_0x48 at 0x0089A833 (W) / 0x0089A89C (R) -- see CORRECTION above.
_TAG_WSTRING16 = 0x48

# Defensive upper bound on the encoded string's byte length, not part of the
# proven wire layout (the length prefix is a full uint32-LE) -- same value
# and same reason as gm/dispatch.py's MAX_RAW_PAYLOAD_LENGTH and
# gm/cheat_wire.py's MAX_STRING_LENGTH: generous for any plausible short
# string, far below anything that could stall a handling thread. No real
# frame of this message has ever been captured, so there is no measured
# real-world length to size this from instead.
MAX_STRING_LENGTH = 65536


class GmForbidToTalkWireError(ValueError):
    """Raw bytes/values do not match the PF_SERIALIZER_FIELDS.tsv pinned
    wire shape, as corrected by PF_A2_STRING_WIRE_TAG_DELTA.tsv row
    6287/6288."""


@dataclass(frozen=True)
class ForbidToTalkResultBody:
    """One decoded/encoded GM_ForbidToTalkResultVital payload.

    Field names are positional only -- see module docstring.
    """

    field_0x14: int
    field_0x18: int
    text_0x1c: str


def make_forbid_to_talk_result_payload(
    legacy, field_0x14: int, field_0x18: int, text_0x1c: str
) -> bytes:
    """Build the tagged-field body: u8tag(0x0B) + u32tag(0x14) + wstr_tag.

    ``legacy`` is the loaded ``pf_login_game_server_v141`` module (see
    ``pirateforce_foundation.legacy_bridge.load_legacy``) -- this module
    does not import the frozen legacy serializer directly, the same seam
    ``gm/state_wire.py`` uses, so the wiring caller (owned by chief, in
    runtime.py) supplies it.
    """
    if not (0 <= field_0x14 <= 0xFF):
        raise GmForbidToTalkWireError("field_0x14 must fit one byte (0-255)")
    if not (0 <= field_0x18 <= 0xFFFFFFFF):
        raise GmForbidToTalkWireError("field_0x18 must fit a u32 (0-4294967295)")
    if type(text_0x1c) is not str:
        # Exact type, not isinstance: a str subclass can lie through
        # __len__/encode, the same discipline gm/say_wire.py's text checks
        # apply for the same reason.
        raise GmForbidToTalkWireError(f"text_0x1c must be a str, got {text_0x1c!r}")
    try:
        encoded_len = len(text_0x1c.encode("utf-16-le"))
    except UnicodeEncodeError as exc:
        raise GmForbidToTalkWireError(
            f"text_0x1c is not encodable as UTF-16LE: {exc}"
        ) from exc
    if encoded_len > MAX_STRING_LENGTH:
        raise GmForbidToTalkWireError(
            f"text_0x1c is {encoded_len} bytes, exceeds MAX_STRING_LENGTH="
            f"{MAX_STRING_LENGTH}"
        )
    return (
        legacy.u8tag(_TAG_U8, field_0x14)
        + legacy.u32tag(_TAG_U32, field_0x18)
        + legacy.wstr_tag(text_0x1c)
    )


def make_forbid_to_talk_result_frame(
    legacy, vital_version: int, field_0x14: int, field_0x18: int, text_0x1c: str
) -> tuple[bytes, bytes]:
    """Wrap the payload in the standard runtime-vital envelope.

    ``vital_version`` is NOT proven for this message (no capture, no RE
    answer) -- required rather than defaulted, the same discipline
    ``gm/state_wire.py``'s own parameter of the same name applies, so a
    caller cannot silently ship an unverified constant.
    """
    payload = make_forbid_to_talk_result_payload(
        legacy, field_0x14, field_0x18, text_0x1c
    )
    return legacy.make_runtime_vitals(
        [(GM_FORBID_TO_TALK_RESULT_VITAL_ID, vital_version, payload)]
    )


def _read_u8_tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 2 > len(buf):
        raise GmForbidToTalkWireError(
            f"truncated: need 2 bytes for tag 0x{expected_tag:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != expected_tag:
        raise GmForbidToTalkWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected "
            f"0x{expected_tag:02X}"
        )
    return buf[offset + 1], offset + 2


def _read_u32_tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 5 > len(buf):
        raise GmForbidToTalkWireError(
            f"truncated: need 5 bytes for tag 0x{expected_tag:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != expected_tag:
        raise GmForbidToTalkWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected "
            f"0x{expected_tag:02X}"
        )
    value = struct.unpack_from("<I", buf, offset + 1)[0]
    return value, offset + 5


def _read_tagged_wstring(buf: bytes, offset: int) -> tuple[str, int]:
    field_offset = offset
    if offset + 5 > len(buf):
        raise GmForbidToTalkWireError(
            f"truncated: need 1 tag byte + 4 bytes for a string length at "
            f"offset {offset}, have {len(buf) - offset}"
        )
    if buf[offset] != _TAG_WSTRING16:
        raise GmForbidToTalkWireError(
            f"unexpected string tag 0x{buf[offset]:02X} at offset {offset}, "
            f"expected 0x{_TAG_WSTRING16:02X}"
        )
    offset += 1
    byte_len = struct.unpack_from("<I", buf, offset)[0]
    if byte_len % 2 != 0:
        raise GmForbidToTalkWireError(
            f"string at offset {field_offset} declares byte_len={byte_len}, "
            "not a whole number of UTF-16LE code units"
        )
    if byte_len > MAX_STRING_LENGTH:
        raise GmForbidToTalkWireError(
            f"string at offset {field_offset} declares {byte_len} bytes, "
            f"exceeds MAX_STRING_LENGTH={MAX_STRING_LENGTH}"
        )
    start = offset + 4
    end = start + byte_len
    if end > len(buf):
        raise GmForbidToTalkWireError(
            f"truncated: string at offset {field_offset} declares "
            f"{byte_len} bytes, have {len(buf) - start}"
        )
    try:
        text = buf[start:end].decode("utf-16-le")
    except UnicodeDecodeError as exc:
        raise GmForbidToTalkWireError(
            f"string at offset {field_offset} is not valid UTF-16LE: {exc}"
        ) from exc
    return text, end


def decode_forbid_to_talk_result_payload(raw: bytes) -> ForbidToTalkResultBody:
    """Decode the pinned wire shape of one GM_ForbidToTalkResultVital
    payload.

    ``raw`` is the vital's payload bytes only (the bytes after vital id and
    version in the runtime-vital envelope), not the whole frame. This
    function does NOT go through ``legacy`` -- it is a standalone reader so
    a test can exercise the shape without booting the frozen legacy module,
    the same split ``gm/command_wire.py`` uses between its ``legacy``-free
    decoder and ``gm/state_wire.py``'s ``legacy``-backed encoder. This
    message is server->client and this repository never receives it, so
    this function exists only to keep the codec's round-trip tested on
    file, the same reference-codec role ``gm/teleport_wire.py``'s
    ``ForcePos``/``CWarpResult`` and ``gm/cheat_wire.py`` hold before a
    wiring round picks the message up.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be bytes")
    buf = bytes(raw)
    field_0x14, offset = _read_u8_tag(buf, 0, _TAG_U8)
    field_0x18, offset = _read_u32_tag(buf, offset, _TAG_U32)
    text_0x1c, offset = _read_tagged_wstring(buf, offset)
    if offset != len(buf):
        raise GmForbidToTalkWireError(
            f"decoded cleanly but {len(buf) - offset} trailing byte(s) remain"
        )
    return ForbidToTalkResultBody(field_0x14, field_0x18, text_0x1c)
