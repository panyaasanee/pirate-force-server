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
own ``vital_version`` field inside ``make_runtime_vitals``), ``0x05`` = u8,
a third flavour added for ``ui_dyeing_appraisal_relive_wire.py``'s
``ReliveVital`` (``external/PF_TAG_CENSUS.tsv`` row
``0x05  1  FIXED  56  UNKNOWN`` -- same "FIXED length 1" shape as ``0x08``/
``0x0B``, no prior module needed this specific byte value before), ``0x32``
= u64/qword (``CLIENT_RE_QUEUE.md:3425``, ``FACTPACK_R100_INREPO_LOOT_SPAWN_
GAPLIST.md:143`` identity qword). ``0x44`` = tagged string8 (one byte per
char, opaque, u32 LE length prefix) -- ``delete_actor.py``'s
``DeleteActorVital`` parser proved this shape first (GT-055); see
``string8tag``/``read_string8tag`` below for the reusable pair added when
``DyeingVitalReq`` was proven to share the identical helper span.

CORRECTED round `42w728`, previously wrong in this file since it was
written: the registry's ``UNTAGGED_WSTRING16LE_LEN32LE`` label does NOT
mean "no tag byte" -- that was this file's own misreading of a label that
only describes a helper CALL SPAN boundary (the exact same misreading
RE-196 already caught once for the ``0x44``/string8 flavour, on the exact
same label-naming pattern). ``notes_to_chief/reference_codex_attr/
PF_A2_STRING_WIRE_TAG_DELTA.tsv`` measures a real ``push_0x48`` tag
instruction inside the shared codec (helper VA ``0x0089A810``/
``0x0089A880``) for every one of this label's 348 rows, matching
``current/pf_login_game_server_v141.py``'s own ``wstr_tag`` helper
exactly -- there never was a conflict to avoid by not reusing it. Use
``wstring_tag``/``read_wstring_tag`` below for any new wstring16le field;
``encode_untagged_wstring``/``read_untagged_wstring`` are kept only for
six already-shipped modules' existing call sites pending migration (see
that function's own docstring for the full list and status).

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


def u16tag(tag: int, v: int) -> bytes:
    """Tag byte + 2-byte little-endian value -- same family as ``u64tag``
    below. Added round `wkrfl6` for ``ui_tracepath_wire.py`` (``CTracePathReq
    Vital``, tag ``0x0F``, six of its eight fields): no class resolved by
    this lane before that round needed a bare u16 tag *write* (only reads,
    via ``read_u32tag``'s sibling below), even though ``0x0F``/2-byte-LE is
    the exact same shape ``CLIENT_RE_QUEUE.md:53``'s tag legend already
    documents project-wide."""

    return bytes([tag]) + struct.pack("<H", v & 0xFFFF)


def u32tag(tag: int, v: int) -> bytes:
    """Tag byte + 4-byte little-endian value -- same family as ``u64tag``
    below. Added round `wkrfl6` alongside ``u16tag`` for the same reason:
    ``read_u32tag`` already existed for the read direction, nothing here
    needed to *write* a bare u32 tag before ``ui_tracepath_wire.py``'s
    field3 (``+0x18``, tag ``0x14``)."""

    return bytes([tag]) + struct.pack("<I", v & 0xFFFFFFFF)


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
    no tag byte.

    PROVEN WRONG for every field this registry label actually covers
    (found round `42w728`'s pf-adversary pass, filed to COO/chief the same
    round -- this function's own callers were never re-audited against it
    until then): ``notes_to_chief/reference_codex_attr/
    PF_A2_STRING_WIRE_TAG_DELTA.tsv`` -- the SAME [MEASURED] correction
    table ``string8tag`` below already relies on for the ``0x44`` string8
    flavour -- also carries a ``corrected_tag=0x48`` row for every one of
    its 348 ``UNTAGGED_WSTRING16LE_LEN32LE`` rows (174 W + 174 R, 87
    unique messages; ``PF_A2_A3_STRING_WIRE_CORRECTION.md``'s stated
    census), each with a real ``push_0x48`` tag instruction proven to live
    inside the SAME shared codec (helper VA ``0x0089A810``/``0x0089A880``)
    this registry label's own name claims has "no tag byte". This function
    (and ``read_untagged_wstring`` below) omit that tag byte and were
    already relied on, before this correction was noticed, by every
    wstring field in ``ui_friend_wire.py``, ``ui_mail_wire.py``,
    ``ui_party_wire.py``, ``ui_trade_wire.py``, ``ui_express_wire.py``, and
    ``ui_community_social_wire.py``. ``ui_channel_wire.py`` already proves
    the fix in production (its own local
    ``encode_channel_tagged_wstring``/``read_channel_tagged_wstring``,
    tag ``0x48``, same helper VAs cited above) -- ``wstring_tag``/
    ``read_wstring_tag`` below promote that same pattern into this shared
    module.

    CORRECTION (round `4u0ncx`, pf-adversary): this docstring previously
    claimed "NONE of the six affected modules are wired into
    ``runtime.py``/``vital_walk.py`` yet (grepped clean this round)" --
    that was wrong for four of the six. ``ui_friend_wire.py``,
    ``ui_mail_wire.py``, ``ui_party_wire.py``, and ``ui_trade_wire.py`` are
    all imported into ``runtime.py`` and dispatched to
    ``production_allowed = True`` report-only lane hooks
    (``lane_hooks/lane_ui_{friend,mail,party,trade}_wire_log.py``) that
    call these modules' ``decode_*`` functions on genuine inbound payload
    bytes today -- the hooks never reply or mutate state (``bytes_out=0``
    throughout), so no byte sent to the client or persisted state was ever
    wrong, but every one of those four modules was, at the time this
    correction was written, silently failing to decode real frames shaped
    per the proven-correct tag (falling back to an ``UNPARSED`` hex dump).
    Only ``ui_express_wire.py`` and ``ui_community_social_wire.py`` are
    genuinely unwired (no ``runtime.py`` import found).

    STATUS as of round `rqwwp8` (`COO-DECISION 20260906_1745` item 2, one
    PR for all three remaining wired modules instead of one-per-round --
    every real frame shaped per the proven-correct tag was misdecoding
    live traffic daily, so stretching the fix over three more rounds only
    stretched the bug): ``ui_friend_wire.py`` (round `4u0ncx`,
    `pirate-force-server#934`), ``ui_mail_wire.py``, ``ui_party_wire.py``,
    and ``ui_trade_wire.py`` are now all migrated onto ``wstring_tag``/
    ``read_wstring_tag``. ``ui_express_wire.py`` migrated too (round
    `me7s4u`) despite staying unwired -- nothing forbids fixing a module
    early, only wiring one before its own fix lands. Only
    ``ui_community_social_wire.py`` still calls this pair, and remains
    unwired (`COO-DECISION 20260906_1649`: no module of the six gets wired
    before its own migration lands). This pair is left in place,
    unmodified, so a round's fix does not silently change other modules'
    already-passing tests out from under a diff that never touches them;
    new work must use ``wstring_tag``/``read_wstring_tag`` instead, never
    this pair. See
    module docstring for why this pair was never
    ``current/pf_login_game_server_v141.py``'s ``wstr_tag`` to begin with
    (a separate, still-true point: that frozen file's own tag is
    ``0x48`` too, which is what this correction converges back onto)."""

    payload = s.encode("utf-16le")
    return struct.pack("<I", len(payload)) + payload


_TAG_WSTRING16LE = 0x48


def wstring_tag(s: str) -> bytes:
    """Tag byte ``0x48`` + u32 LE byte length + UTF-16LE payload -- the
    CORRECT shape for ``UNTAGGED_WSTRING16LE_LEN32LE`` registry rows (see
    ``encode_untagged_wstring`` above for the full provenance and why that
    sibling function is wrong). Same proof shape as ``string8tag`` below,
    promoted from ``ui_channel_wire.py``'s already-shipped
    ``encode_channel_tagged_wstring`` (identical helper VAs
    ``0x0089A810``/``0x0089A880``) into this shared module so new modules
    do not have to redefine it locally. Use this, never
    ``encode_untagged_wstring``, for any new wstring16le field."""

    payload = s.encode("utf-16le")
    return bytes([_TAG_WSTRING16LE]) + struct.pack("<I", len(payload)) + payload


def string8tag(tag: int, s: bytes) -> bytes:
    """Tag byte + u32 LE byte length + N raw ``basic_string<char>`` bytes
    (one byte per char, opaque -- no charset assumed). This is the SAME
    wire shape ``delete_actor.py``'s strict parser proved for
    ``DeleteActorVital``'s trailing field under tag ``0x44`` (GT-055,
    ``44 | uint32le byte_len | N raw string8 bytes``), added here as a
    reusable pair (this function + ``read_string8tag`` below) because
    ``DyeingVitalReq``'s field 2 shares it: ``PF_A2_STRING_WIRE_TAG_DELTA
    .tsv:362-363`` records the identical helper VA/file_off/span_end/
    SHA-256 for both classes' string call sites (``0x0089A6D0``..
    ``0x0089A733``, sha ``a0674fb3...96c29319bd``) and the same
    ``tag_instruction_va=0x0089A6F1``/``push_0x44`` -- not a guess by
    class-name similarity, a byte-identical shared helper span. Kept
    opaque (``bytes``, not decoded to ``str``) for the same reason
    ``delete_actor.py`` does: no proven charset for this string8 flavour,
    unlike the UTF-16LE wstring helpers above."""

    return bytes([tag]) + struct.pack("<I", len(s)) + s


def read_u8tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 2 > len(buf):
        raise WireDecodeError("truncated u8 field")
    tag = buf[offset]
    if tag != expected_tag:
        raise WireDecodeError(
            "expected tag 0x%02X, got 0x%02X" % (expected_tag, tag)
        )
    return buf[offset + 1], offset + 2


def read_u16tag(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 3 > len(buf):
        raise WireDecodeError("truncated u16 field")
    tag = buf[offset]
    if tag != expected_tag:
        raise WireDecodeError(
            "expected tag 0x%02X, got 0x%02X" % (expected_tag, tag)
        )
    value = struct.unpack_from("<H", buf, offset + 1)[0]
    return value, offset + 3


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


def read_wstring_tag(buf: bytes, offset: int) -> tuple[str, int]:
    """Read ``wstring_tag``'s shape back: tag byte ``0x48``, u32 LE length,
    UTF-16LE payload (see ``wstring_tag``/``encode_untagged_wstring``
    above for provenance). Reuses ``read_untagged_wstring``'s decode body
    for the length+payload half so the UTF-16LE edge cases (odd length,
    unpaired surrogate) stay defined in exactly one place."""

    if offset + 1 > len(buf):
        raise WireDecodeError("truncated wstring tag byte")
    tag = buf[offset]
    if tag != _TAG_WSTRING16LE:
        raise WireDecodeError(
            "expected tag 0x%02X, got 0x%02X" % (_TAG_WSTRING16LE, tag)
        )
    return read_untagged_wstring(buf, offset + 1)


def read_string8tag(
    buf: bytes, offset: int, expected_tag: int
) -> tuple[bytes, int]:
    """Read ``string8tag``'s shape back: tag byte, u32 LE length, then that
    many raw bytes, returned opaque (see ``string8tag`` above)."""

    if offset + 5 > len(buf):
        raise WireDecodeError("truncated string8 tag+length header")
    tag = buf[offset]
    if tag != expected_tag:
        raise WireDecodeError(
            "expected tag 0x%02X, got 0x%02X" % (expected_tag, tag)
        )
    length = struct.unpack_from("<I", buf, offset + 1)[0]
    start = offset + 5
    end = start + length
    if end > len(buf):
        raise WireDecodeError("truncated string8 payload")
    return buf[start:end], end


def require_exhausted(buf: bytes, offset: int) -> None:
    """Raise ``WireDecodeError`` if bytes remain after ``offset`` -- see the
    module docstring's "TRAILING BYTES ARE ALSO A DECODE FAILURE" note.
    Every sibling module's ``decode_*`` calls this as its last parse step."""

    if offset != len(buf):
        raise WireDecodeError(
            "trailing bytes after full field match: consumed=%d/%d"
            % (offset, len(buf))
        )
