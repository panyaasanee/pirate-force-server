"""Shared wire primitives for CORE-REQUEST 1120's eight resolved
friend/mail/party classes, plus ``TradeInviteVital``.

Nothing in this file is wired into ``runtime.py`` or ``vital_walk.py`` --
see COO-DECISION ``20260904_1244`` item 3 (LANE-UI writes these as pure
encode/decode modules; chief owns the single dispatch hook separately,
``notes_to_chief/20260904_1245_COO-DECISION-chief-queue-*.md``) and
``notes_to_chief/20260904_1120_*.md``'s own scope line: "เปิด branch รับเฟรม + ตอบ ack/error
frame ที่วางเปล่า ... ไม่ใช่การทำ business logic เต็ม". This module supplies
the "รับเฟรม" (decode) half and the raw field-shape encode half only; it
does not compose an ack/error response of its own, because no class in
this batch has a proven ack/error shape (``CORE-REQUEST 1120`` nonclaim (2):
caller/verb semantics -- what any of these fields MEAN, or what the server
should say back -- are `CALL_UNCLASSIFIED` for all eight classes, and this
file does not guess one).

WHY THE +0xNN OFFSETS IN THE REGISTRY ARE NOT USED HERE, STATED ONCE FOR
ALL EIGHT CLASSES SO EACH ``ui_*.py`` FILE DOES NOT HAVE TO REPEAT IT:
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv``'s ``field_offset`` column
(``+0x14``, ``+0x18``, ...) is the CLIENT C++ OBJECT's in-memory field
offset, recorded there for RE provenance -- it is not a wire byte offset.
On the wire, a class's fields are simply its tag+value pairs written back
to back in the TSV's own ``order`` column sequence, with no padding and no
offset gaps: this is proven directly by ``CTracePathReqVital``'s one real
captured frame (eight fields, back to back, RE-119 /
``archive/notes_to_chief_2026-08/20260828_0235_KA1A-FOUND-*.md``), and by
``current/pf_login_game_server_v141.py:make_runtime_vitals`` composing its
own multi-field payloads the same way (``u16tag`` then ``u32tag`` then
``u8tag`` ... with no gaps). Every encoder/decoder in this file's sibling
modules follows that same sequential-tag-pair shape.

TAG LEGEND (every value below is confirmed elsewhere in this project, not
invented here): ``0x08`` = u8
(``FINDINGS_R38_0x1B40_DECODED_LOGOUTVITAL.md``), ``0x0B`` = u8, a second
flavour used throughout ``current/pf_login_game_server_v141.py`` (e.g. its
own ``vital_version`` field inside ``make_runtime_vitals``), ``0x32`` =
u64/qword (``CLIENT_RE_QUEUE.md:3425``, ``FACTPACK_R100_INREPO_LOOT_SPAWN_
GAPLIST.md:143`` identity qword). The registry's
``UNTAGGED_WSTRING16LE_LEN32LE`` is exactly what its name says: a u32 LE
length prefix followed by UTF-16LE payload bytes, with **no** leading tag
byte -- unlike ``current/pf_login_game_server_v141.py``'s own ``wstr_tag``
helper, which prepends tag ``0x48``. Reusing ``wstr_tag`` here would put a
byte on the wire this registry entry does not license, which is why this
file defines its own untagged variant instead.

FAIL-CLOSED ON DECODE, STATED AS A PROPERTY: every ``decode_*`` function in
this file's sibling modules returns ``None`` on any malformed input
(truncated buffer, wrong tag byte, odd-length UTF-16LE payload) rather than
raising -- the same convention as
``world_logout_button_notice.py``'s ``classify_parsed``. The only
exceptions are ``KeyboardInterrupt``/``SystemExit``/``GeneratorExit``,
which are never meant to be caught by a frame parser.

TRAILING BYTES ARE ALSO A DECODE FAILURE (COO-DECISION ``20260904_1745``
item 2, from a ``pf-adversary`` finding on round ``qwhlua``): a payload
that matches this class's fixed field shape for its first ``c`` bytes but
carries ``n - c`` unexplained bytes afterwards is not a full decode of that
payload, even though every field read so far succeeded. Every sibling
module's ``decode_*`` calls ``require_exhausted`` as its last step inside
the same ``try`` block so that case returns ``None`` (``UNPARSED``) like
any other malformed input, instead of quietly reporting a partial match as
if it were a complete one -- a class this project's field model does not
yet fully cover must surface as unproven, not as a false "decoded".
"""

from __future__ import annotations

import struct


class WireDecodeError(Exception):
    """Internal only -- every public ``decode_*`` function catches this and
    returns ``None``. Never escapes this module's public surface."""


def u64tag(tag: int, v: int) -> bytes:
    """Tag byte + 8-byte little-endian value -- the same shape as
    ``current/pf_login_game_server_v141.py``'s ``u8tag``/``u16tag``/
    ``u32tag`` family, extended to 8 bytes. Not defined in the frozen v141
    file itself (no existing wire class there needed a bare u64 tag write);
    ``V141_FREEZE.md`` forbids editing that file, so this is a new, small,
    house-pattern-identical helper living in this lane's own module, not a
    modification of the frozen one.
    """

    return bytes([tag]) + struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF)


def encode_untagged_wstring(s: str) -> bytes:
    """``UNTAGGED_WSTRING16LE_LEN32LE``: u32 LE length + UTF-16LE payload,
    no tag byte. See module docstring for why this is not
    ``current/pf_login_game_server_v141.py``'s ``wstr_tag``."""

    payload = s.encode("utf-16le")
    return struct.pack("<I", len(payload)) + payload


def read_u8tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 2 > len(buf):
        raise WireDecodeError("truncated u8 field")
    tag = buf[offset]
    if tag != expected_tag:
        raise WireDecodeError(
            "expected tag 0x%02X, got 0x%02X" % (expected_tag, tag)
        )
    return buf[offset + 1], offset + 2


def read_u32tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 5 > len(buf):
        raise WireDecodeError("truncated u32 field")
    tag = buf[offset]
    if tag != expected_tag:
        raise WireDecodeError(
            "expected tag 0x%02X, got 0x%02X" % (expected_tag, tag)
        )
    value = struct.unpack_from("<I", buf, offset + 1)[0]
    return value, offset + 5


def read_u64tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 9 > len(buf):
        raise WireDecodeError("truncated u64 field")
    tag = buf[offset]
    if tag != expected_tag:
        raise WireDecodeError(
            "expected tag 0x%02X, got 0x%02X" % (expected_tag, tag)
        )
    value = struct.unpack_from("<Q", buf, offset + 1)[0]
    return value, offset + 9


def read_untagged_wstring(buf: bytes, offset: int) -> tuple[str, int]:
    if offset + 4 > len(buf):
        raise WireDecodeError("truncated wstring length prefix")
    length = struct.unpack_from("<I", buf, offset)[0]
    start = offset + 4
    end = start + length
    if end > len(buf):
        raise WireDecodeError("truncated wstring payload")
    if length % 2 != 0:
        raise WireDecodeError("odd-length UTF-16LE payload")
    try:
        text = buf[start:end].decode("utf-16le")
    except UnicodeDecodeError as error:
        # An unpaired UTF-16 surrogate (e.g. a lone 0xD800/0xDC00 code
        # unit) is a perfectly even-length, in-bounds payload that Python's
        # "utf-16le" codec still refuses -- this is not a truncation or a
        # tag mismatch, so it needs its own branch to stay inside the
        # module's fail-closed contract instead of escaping as a raw
        # UnicodeDecodeError (pf-adversary: every decode_* caller here
        # only ever catches WireDecodeError).
        raise WireDecodeError("malformed UTF-16LE payload") from error
    return text, end


def require_exhausted(buf: bytes, offset: int) -> None:
    """Raise ``WireDecodeError`` if bytes remain after ``offset`` -- see the
    module docstring's "TRAILING BYTES ARE ALSO A DECODE FAILURE" note.
    Every sibling module's ``decode_*`` calls this as its last parse step."""

    if offset != len(buf):
        raise WireDecodeError(
            "trailing bytes after full field match: consumed=%d/%d"
            % (offset, len(buf))
        )
