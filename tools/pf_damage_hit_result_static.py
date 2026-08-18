#!/usr/bin/env python3
"""PF DAMAGE-MODEL-001 - static byte-exact reconstruction of the client's DAMAGE
surface: the CHitResult wire schema (header + the 32-byte per-target hit-entry
array), which field carries the number the player sees, what the client does
with it, and - the load-bearing half - everything the client provably does NOT
do with it.

THE HEADLINE, in plain terms:

    The client is a pure display of server-sent numbers.  It computes no damage
    and it never mutates HP itself.  The number the player sees is the SIGNED
    i32 at hit-element +0x08, printed through abs() and "%d" with no scaling,
    no rounding, no clamping and no table lookup anywhere on the path.

Everything below is a fact about ONE immutable, hash-pinned client image.
It is NOT a claim about the ORIGINAL server (that server is gone; there is no
publish of it, and nothing here should ever be described as evidence from it).

  * THE WIRE IS A TAGGED STREAM.  Every field on the wire is one tag byte then
    a fixed-width payload.  `CStream::WriteField(tag, ptr, size)` is the
    thiscall `0x89A600` (ecx = stream); its read twin is `0x89A640`.  The tag
    byte is stored by `0x89A4D0` at `0x89A53B` (`mov [eax+edx], cl`) and is
    re-checked on read by `0x89A550` at `0x89A5BF` (`cmp bl, [eax+edx]`); a
    mismatch sets the stream's decode-error flag `stream+0x20` at `0x89A5C9`
    (the separate buffer-overflow flag is `stream+0x21`, set at `0x89A590`).
    The tag -> width map used by this family is:

        0x0B = u8   (1)      0x12 = u16  (2)      0x14 = u32  (4)
        0x2A = f32  (4)      0x32 = qword(8)

    `Vector3` is not a tag: it is the helper `0x5F3490` (write) / `0x5F34D0`
    (read) emitting three consecutive tag-`0x2A` floats, 12 bytes.

  * THE CLASS.  `CHitResult`, name literal `0xF0B5F8`, wire id `0x16F7`
    (the PF-NAMEID hash of the literal, reproduced here in Python), registration
    thunk `0xC0C180` -> id global `0x108A2E4`, get-id stub `0x74F9C0`,
    vtable `0xF48AA0`, ctor `0x74F940`, sizeof `0x48`, serializer (vtable +0x18)
    `0x750040`, inbound handler (vtable +0x1C) `0x750770`.

  * THE HEADER, in emission order out of `0x750040`:

        qword tag 0x32 @ obj+0x18   (emit site 0x750059)   attacker id (64-bit)
        u16   tag 0x12 @ obj+0x20   (emit site 0x750068)
        u16   tag 0x12 @ obj+0x22   (emit site 0x750077)
        u32   tag 0x14 @ obj+0x24   (emit site 0x750086)
        u8    tag 0x0B @ obj+0x28   (emit site 0x750095)
        then the hit-entry array serializer 0x74F5A0 on obj+0x2C (0x75009F)

  * THE ARRAY (shared with CMissileHitResult, which holds it at +0x40).
    Count is a u16 with tag `0x12` (emit site `0x74F5C8`).  The element STRIDE
    IS 32 BYTES, proven twice from the bytes: `sar eax,5` at `0x74F5B3` turns
    the container byte length into a count, and the loop advances with
    `add ebx,0x20` at `0x74F686`.  Per element:

        qword tag 0x32 @ +0x00   (0x74F62C)   target id (64-bit)
        u32   tag 0x14 @ +0x08   (0x74F63E)   *** THE DAMAGE NUMBER, SIGNED ***
        Vec3  3x  0x2A @ +0x0C   (0x74F645 -> 0x5F3490)   hit position
        f32   tag 0x2A @ +0x18   (0x74F657)   knock/fall YAW ANGLE, not damage
        u16   tag 0x12 @ +0x1C   (0x74F666)   result-flag bitfield
        (+0x1E..+0x1F is padding to the 32-byte stride)

    The read twin of the array is `0x74FF60`.

  * +0x08 IS SIGNED.  Both hit-result handlers branch on it with a SIGNED
    compare: `cmp dword ptr [ebx+8], 0` followed by `jge` - in the CHitResult
    handler at `0x750919` and `0x7509E0`, and in the CMissileHitResult handler
    at `0x751219` and `0x7512E0`.  Negative takes the "took damage" branch;
    non-negative skips the impact reaction.  (What the non-negative branch
    MEANS - heal, absorb, no-op - is not tied to any constant in the image and
    is deliberately not claimed here.)

  * +0x18 IS AN ANGLE, NOT A DAMAGE NUMBER.  This is the correction that
    matters: an earlier reading called the f32 at element +0x18 the damage
    magnitude.  It is not.  `fld dword ptr [ebx+0x18]` (`0x750A42` CHitResult /
    `0x751342` CMissileHitResult) pushes it as the FLOAT argument of the
    knockdown/falling reaction spawner `0x48D870` (non-missile, called at
    `0x750A59`) / `0x48DBA0` (missile twin, called at `0x751352`).  Inside both,
    that float goes to `0x49C8B0`, which writes `out[0]=f(a)`, `out[1]=-g(a)`
    (note the `fchs`), `out[2]=0.0f` - a unit heading vector - and is separately
    combined as `a + pi - facing` (`fadd qword [0xF0D140]` = 3.14159274, then
    `0x427630` returns the actor's facing yaw, then `fsubr`).  A float fed to
    sin/cos and added to pi is an angle.  It never reaches a text or number
    widget.  The spawned reaction is marked with
    `or dword ptr [edi+0x10], 0x40000000` (`0x750A71` / `0x75136A`).

  * +0x1C IS A u16 RESULT-FLAG BITFIELD.  `movzx eax, word ptr [ebx+0x1c]`
    (`0x750A18` / `0x751318`), then `test al, 8` and `test al, 0x10`; with
    bit 4 set the client plays the wide literal `_F_KNOCKED_002` at `0xF48B4C`
    instead of showing a number (`push 0xF48B4C` at `0x750A33` / `0x751333`),
    and `test byte ptr [ebx+0x1c], 1 / 2 / 0x80` gate three further branches.
    The bit LABELS (hit/miss/block/critical) are NOT asserted here.

  * THE NUMBER ON SCREEN.  Exactly one path, and it carries the wire value
    verbatim:

        CHitResult handler numeric pass    element+0x08 picked up at 0x750D90
            `mov ecx,[esi+8]` -> pushed as the last argument
        -> 0x43FDE0   the hit-reaction FX dispatcher (4 call sites image-wide,
            all four inside the two hit-result handlers)
            `mov esi, dword ptr [esp+0x88]` at 0x43FF11 loads the damage; from
            there esi is only ever `push`ed
        -> 0x43FBB0   FxNumber spawn (type, value)
        -> 0xA7C010   FxNumber ctor, `mov dword ptr [esi+0xF8], eax` at
            0xA7C046 stores the value verbatim
        -> 0xA7EBA0   the glyph builder:
                0xA7EBFB  mov eax,[esp+0x68]
                0xA7EBFF  cdq
                0xA7EC00  xor eax,edx
                0xA7EC02  sub eax,edx        <-- abs(value).  THE ONLY ARITHMETIC.
                0xA7EC0A  call 0x896100      -> sprintf(buf, "%d", ...) with the
                                                ASCII format literal at 0xF14A94

    abs() exists so a minus sign is not rendered as a digit.  The magnitude is
    untouched: no multiply, no divide, no scale, no clamp, no rounding.

  * THE NEGATIVE, GUARDED HARD.  Because "the client computes nothing" is a
    headline negative it is pinned three independent ways:

      (a) every function on the path is pinned by the SHA-256 OF ITS EXACT BYTE
          RANGE, so any edit anywhere inside it - including inserting a multiply
          - breaks the guard;
      (b) the byte encodings of `imul r32,r/m32` (0F AF), `mulss`/`divss`
          (F3 0F 59 / F3 0F 5E), `mulsd`/`divsd` (F2 0F 59 / F2 0F 5E) and
          `mulpd`/`divpd` (66 0F 59 / 66 0F 5E) are asserted ABSENT from the
          three spans that must contain no arithmetic at all
          (0x43FDE0..0x440164, 0x43FBB0..0x43FDD0, 0xA7E940..0xA7EBA0);
      (c) the exact instruction bytes of the value load, the abs() and the
          sprintf call are pinned, with the assertion that the nine bytes from
          the load to the `sub` are contiguous and unmodified.

    Derivation-time census, frozen by the whole-image hash in guard 1
    (re-derivable from this same image with a disassembler; this pure-stdlib
    tool does not decode instructions): a full linear sweep of `.text` decoding
    2,893,637 instructions found, inside the eight functions of the damage path,
    exactly these arithmetic instructions and no others - two `neg eax` per
    hit-result handler (the MSVC dynamic_cast idiom), three `mulsd` each in the
    two reaction spawners plus one `imul` by an array element count (geometry),
    one `cdq` (the abs) and one `fmul` by 22.0 (glyph pitch in pixels) in the
    glyph builder, and NOTHING AT ALL in the FX dispatcher, the FxNumber spawn,
    or the sign/width helper.

  * HP IS NEVER TOUCHED FROM A HIT.  That same sweep found that the whole
    CHitResult inbound handler (0x750770..0x750EC0) contains not one memory
    operand at BasicAttr +0x44, +0x48, +0x4C, +0x50, +0x58, +0x1A8 or +0x1AC -
    it neither reads nor writes HP.  The FX dispatcher touches +0x44/+0x4C/
    +0x50/+0x1A8/+0x1AC only as SOURCE operands, maintaining a display-side
    change cache.  The one place the client copies attribute values is the
    generic mask-gated apply loop `0x464436`..`0x4644E0`, pinned here byte for
    byte: 14 fields, each one `test <mask>,<bit> ; jne skip ; mov REG,[src+off]
    ; mov [dst+off],REG`.  Bit 0x40 guards +0x44 (current HP), the sign bit
    guards +0x48 (max HP), bit 0x800 guards +0x58 (the dying timer).  Pure copy.

  * THE DERIVED STATS ARE UI-ONLY.  Nineteen accessor functions live in
    0x467E90..0x468E30 (eighteen of them read a named `STANDARD_STATUS` column,
    one is base-only).  Their COMPLETE call-site sets are recomputed here from a
    fresh scan of every E8 rel32 in `.text`: every caller is in the stat/tooltip
    block around 0x57Exxx/0x57Fxxx or the character-panel refresh around
    0x6CFxxx/0x6D0xxx.  Not one caller is inside any combat handler, the FX
    dispatcher, the reaction spawners or the array serializers.  The consumer
    shape is literally `call 0x468250 ; mov ecx,[esi+0x144] ;
    mov [ecx+0x220], eax` at 0x6CFD30..0x6CFD42.

  * DYING / RESCUE, from the same image.  `DURATION_DYING` is an INTEGER config
    global at `0x102249C`, image default 20, registered at `0x483475` from the
    wide literal `0xF118FC`.  It has exactly TWO references in `.text` - the
    registration and its single reader at `0x44A572` - and that reader is the
    Main_Dead gate: `cvtsi2sd xmm1,[0x102249C]` then `subsd xmm1, qword
    [0xF092D0]` (0xF092D0 is the DOUBLE 0.5, not a float) then `comisd ; ja`,
    i.e. open the window only while `timer >= DURATION_DYING - 0.5`.
    `IsDying` = actor vtable +0x40 (`0x454AC0`) = HP == 0 && timer > 0;
    `IsDead`  = actor vtable +0x3C (`0x454A70`) = HP == 0 && timer <= 0, the
    comparison being `comiss xmm0(0.0), [attr+0x58]` at `0x454A7D`.
    While dying, the idle task pushes the wide literal `_F_STRUGGLE_000`
    (`0xF0F008`, pushed at `0x4726B1`) - "struggle", not "die".
    `L"Main_Dead"` `0xF0D738` is opened at `0x44A5A1` (literal pushed at
    `0x44A597`); its handler binds exactly one child, `L"BUTTON_DIE"`
    `0xF1F5CC` (bound at `0x5183D2`), whose click sends an `ActionVital` with
    action id `0xEA7C` (`mov dword ptr [eax+0x30], 0xEA7C` at `0x518493`, sent
    at `0x5184A1`).  `L"Common_Death"` `0xF0D860` is a DIFFERENT window, opened
    at `0x44E5C7` from `CMyActor::Update` `0x44E4E0` after the `IsDead` vtable
    call at `0x44E594`.  `ReliveVital` (id `0x1AD4`) is `{i8 mode @+0x14
    (tag 0x08, read back with `movsx` at `0x5E5FCD`), u8 @+0x18 (tag 0x05)}`;
    its inbound slot is the shared no-op `0x710440`, and its three producers are
    `0x4E4731` (mode 1), `0x4E4AE4` and `0x4E4B84` (mode 0).

NOT CLAIMED, deliberately: nothing about the ORIGINAL server.  No runtime
capture, no wire observation, no persistence claim, no damage formula, no
semantic name for any result-flag bit.  This is the CLIENT's expectation,
byte-exact, and nothing else.

WHAT THIS MILESTONE IS: report-only.  It changes no server source, opens no
hypothesis, adds no scenario and no ledger entry.  Sole binary evidence is the
read-only client image, which is permanent evidence and is never written to.

PURE STDLIB ON PURPOSE: the release gate runs `py -3` with no third-party
packages, so every disassembly result of the investigation is frozen here as a
byte-pattern / span-hash guard rather than a capstone call.

Usage:  py -3 tools/pf_damage_hit_result_static.py [path-to-GameClient.local.bin]
        py -3 tools/pf_damage_hit_result_static.py --json
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
"""
import hashlib
import json
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))

EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"


def _default_bin():
    for cand in (
        os.path.join(_ROOT, "packages", ".v134_staging_20260815_0355",
                     "GameClient.local.bin"),
        os.path.join(_ROOT, "..", "GameClient", "GameClient.local.bin"),
        "GameClient/GameClient.local.bin",
        os.path.join(_ROOT, "GameClient", "GameClient.local.bin"),
    ):
        if os.path.isfile(cand):
            return cand
    return "GameClient/GameClient.local.bin"


# Only honour argv when this file is the program being run.  Under pytest,
# sys.argv holds the test file's path and must not be mistaken for a binary.
_RUN_AS_SCRIPT = (os.path.basename(sys.argv[0] or "")
                  == os.path.basename(os.path.abspath(__file__)))
_ARGS = [a for a in sys.argv[1:] if not a.startswith("--")] if _RUN_AS_SCRIPT else []
WANT_JSON = _RUN_AS_SCRIPT and "--json" in sys.argv[1:]
BIN = _ARGS[0] if _ARGS else _default_bin()

data = open(BIN, "rb").read()
SHA = hashlib.sha256(data).hexdigest().upper()

# ------------------------------------------------------------------ PE plumbing
_e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
_coff = _e_lfanew + 4
_nsec = struct.unpack_from("<H", data, _coff + 2)[0]
_optsz = struct.unpack_from("<H", data, _coff + 16)[0]
_opt = _coff + 20
IMAGE_BASE = struct.unpack_from("<I", data, _opt + 28)[0]
_sect = _opt + _optsz
SECS = []
for _i in range(_nsec):
    _o = _sect + _i * 40
    _nm = data[_o:_o + 8].rstrip(b"\0").decode("latin1")
    _vs, _va, _rs, _rp = struct.unpack_from("<IIII", data, _o + 8)
    SECS.append((_nm, _va, _vs, _rp, _rs))

_TEXT = [s for s in SECS if s[0] == ".text"][0]
TEXT_LO = IMAGE_BASE + _TEXT[1]
TEXT_RAW_OFF = _TEXT[3]
TEXT_RAW_SZ = _TEXT[4]
_RDATA = [s for s in SECS if s[0] == ".rdata"][0]


def va2off(va):
    r = va - IMAGE_BASE
    for _nm, _va, _vs, _rp, _rs in SECS:
        if _va <= r < _va + max(_vs, _rs):
            return _rp + (r - _va)
    return None


def off2va(off):
    for _nm, _va, _vs, _rp, _rs in SECS:
        if _rp <= off < _rp + _rs:
            return IMAGE_BASE + _va + (off - _rp)
    return None


def sec_of(va):
    r = va - IMAGE_BASE
    for _nm, _va, _vs, _rp, _rs in SECS:
        if _va <= r < _va + max(_vs, _rs):
            return _nm
    return None


def rd(va, n):
    o = va2off(va)
    return data[o:o + n] if o is not None else b""


def dw(va):
    b = rd(va, 4)
    return struct.unpack("<I", b)[0] if len(b) == 4 else None


def f32(va):
    b = rd(va, 4)
    return struct.unpack("<f", b)[0] if len(b) == 4 else None


def f64(va):
    b = rd(va, 8)
    return struct.unpack("<d", b)[0] if len(b) == 8 else None


def cstr(va, maxn=256):
    b = rd(va, maxn)
    z = b.find(b"\0")
    return b[:z].decode("latin1") if z >= 0 else None


def wstr(va, maxn=256):
    b = rd(va, maxn)
    z = len(b)
    for i in range(0, len(b) - 1, 2):
        if b[i] == 0 and b[i + 1] == 0:
            z = i
            break
    return b[:z].decode("utf-16le", "replace")


def span(lo, hi):
    """The exact bytes of [lo, hi)."""
    return rd(lo, hi - lo)


def span_sha(lo, hi):
    return hashlib.sha256(span(lo, hi)).hexdigest()


def find_bytes(pat, section=None):
    out = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        start = i + 1
        va = off2va(i)
        if va is None:
            continue
        if section is None or sec_of(va) == section:
            out.append(va)
    return out


def rel32_target(va):
    """If `va` holds an E8 rel32 call, return its absolute target."""
    b = rd(va, 5)
    if len(b) != 5 or b[0] != 0xE8:
        return None
    return (va + 5 + struct.unpack("<i", b[1:])[0]) & 0xFFFFFFFF


# A handful of call sites hoist the `push <tag>` above unrelated stack setup
# instead of leaving it adjacent to the call.  Those are listed explicitly so
# the tag is still read out of real bytes rather than guessed by a scan.
TAG_PUSH_VA = {
    0x74FFCF: 0x74FFB0,   # hit-element +0x00 READ; the `6a 32` is hoisted
}


def tag_of_call(va):
    """The tag immediate pushed for the codec call at `va`, read from bytes.

    Three shapes occur in this image:  `6a TT ; e8 ...`,
    `6a TT ; 8b Cx ; e8 ...` (when ecx has to be reloaded first), and a small
    set of sites where the push is hoisted (TAG_PUSH_VA above).
    """
    if va in TAG_PUSH_VA:
        p = TAG_PUSH_VA[va]
        return rd(p + 1, 1)[0] if rd(p, 1) == b"\x6a" else None
    if rd(va - 2, 1) == b"\x6a":
        return rd(va - 1, 1)[0]
    if rd(va - 4, 1) == b"\x6a" and rd(va - 2, 1) == b"\x8b":
        return rd(va - 3, 1)[0]
    return None


# ---- one-pass E8 rel32 call index ------------------------------------------
_CALLS = {}


def _build_call_index():
    lo = TEXT_RAW_OFF
    hi = lo + TEXT_RAW_SZ
    i = data.find(b"\xe8", lo)
    while 0 <= i < hi - 5:
        rel = struct.unpack_from("<i", data, i + 1)[0]
        va = off2va(i)
        if va is not None:
            tgt = (va + 5 + rel) & 0xFFFFFFFF
            _CALLS.setdefault(tgt, []).append(va)
        i = data.find(b"\xe8", i + 1)


_build_call_index()


def calls_to(target):
    return sorted(_CALLS.get(target, []))


def calls_to_in(target, lo, hi):
    return [v for v in calls_to(target) if lo <= v < hi]


# ------------------------------------------------------- the PF-NAMEID hash
def name_id(name):
    """u16 id = SUM_i (int16)((signed char)name[i] * (i+1))  mod 2^16 (0x89B220)."""
    acc = 0
    for i, ch in enumerate(name.encode("latin1")):
        sc = ch if ch < 128 else ch - 256
        acc = (acc + ((sc * (i + 1)) & 0xFFFF)) & 0xFFFF
    return acc


# ------------------------------------------------------------------- guards
FAILS = []
NGUARD = 0
RESULT = {}


def guard(cond, msg):
    global NGUARD
    NGUARD += 1
    ok = bool(cond)
    if not WANT_JSON:
        print(("  PASS " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(msg)
    return ok


def gbytes(va, hexpat, msg):
    want = bytes.fromhex(hexpat)
    got = rd(va, len(want))
    return guard(got == want, "%s  [0x%08X %s]" % (msg, va, hexpat))


def ghas(va, n, hexpat, msg):
    want = bytes.fromhex(hexpat)
    return guard(want in rd(va, n),
                 "%s  [0x%08X..+0x%X contains %s]" % (msg, va, n, hexpat))


def gabsent(lo, hi, hexpat, msg):
    want = bytes.fromhex(hexpat)
    return guard(want not in span(lo, hi),
                 "%s  [0x%08X..0x%08X has no %s]" % (msg, lo, hi, hexpat))


def gspan(lo, hi, sha, msg):
    got = span_sha(lo, hi)
    return guard(got == sha,
                 "%s  [0x%08X..0x%08X sha256 %s]" % (msg, lo, hi, sha[:16]))


def section(title):
    if not WANT_JSON:
        print("\n== " + title)


# =============================================================== 0. the image
if not WANT_JSON:
    print("PF-DAMAGE-MODEL-001 static verifier")
    print("binary          =", BIN)
    print("binary SHA-256  =", SHA)

section("0. image identity")
guard(SHA == EXPECT_SHA, "binary SHA-256 matches the pinned client image")
guard(IMAGE_BASE == 0x400000, "ImageBase == 0x400000")
guard(TEXT_LO == 0x401000, ".text virtual start == 0x401000")
guard(len(data) == 14759424, "image size == 14759424 bytes")

# ==================================================== 1. the tagged wire codec
section("1. the tagged stream codec (1 tag byte + fixed-width payload)")

STREAM_WRITE = 0x89A600
STREAM_READ = 0x89A640
TAG_MAP = {0x0B: 1, 0x12: 2, 0x14: 4, 0x2A: 4, 0x32: 8}
TAG_NAME = {0x0B: "u8", 0x12: "u16", 0x14: "u32", 0x2A: "f32", 0x32: "qword"}
VEC3_WRITE = 0x5F3490
VEC3_READ = 0x5F34D0

gbytes(0x89A600, "8b44240456578b7c24146830a4f500687802000057508bf1e8b3",
       "0x89A600 = WRITE(tag, ptr, size), thiscall ecx = stream")
ghas(0x89A600, 0x40, "c20c00",
     "  ... and it is `ret 0xC` (three dword args)")
ghas(0x89A600, 0x40, "e84dd52900",
     "  ... the payload copy is the memcpy call at 0x89A62E")
gbytes(0x89A640, "83ec48568bf1807e21007571807e2000756b8b4424506830a4f5",
       "0x89A640 = READ twin, same three-argument shape")
gbytes(0x89A53B, "880c10",
       "the TAG BYTE is stored at 0x89A53B (`mov byte ptr [eax+edx], cl`)")
gbytes(0x89A5BF, "3a1c105b74",
       "the TAG BYTE is re-checked on read at 0x89A5BF (`cmp bl, [eax+edx]`)")
gbytes(0x89A5C9, "c6412001",
       "a tag mismatch sets the decode-error flag stream+0x20 at 0x89A5C9")
gbytes(0x89A590, "c6412101",
       "  (the separate overflow flag is stream+0x21, set at 0x89A590)")

gbytes(VEC3_WRITE,
       "568b742408578b7c24106a04566a2a8bcfe85a712a006a048d4604506a2a8bcf"
       "e84b712a006a0483c608566a2a8bcfe83c712a005f5ec3",
       "Vector3 WRITE 0x5F3490 == exactly three tag-0x2A / 4-byte fields")
gbytes(VEC3_READ,
       "568b742408578b7c24106a04566a2a8bcfe85a712a006a048d4604506a2a8bcf"
       "e84b712a006a0483c608566a2a8bcfe83c712a005f5ec3",
       "Vector3 READ 0x5F34D0 == the same three fields through 0x89A640")
guard(len(calls_to_in(STREAM_WRITE, VEC3_WRITE, VEC3_WRITE + 0x37)) == 3,
      "Vector3 WRITE makes exactly 3 codec calls (12 bytes on the wire)")
guard(len(calls_to_in(STREAM_READ, VEC3_READ, VEC3_READ + 0x37)) == 3,
      "Vector3 READ makes exactly 3 codec calls")
guard(all(tag_of_call(v) == 0x2A
          for v in calls_to_in(STREAM_WRITE, VEC3_WRITE, VEC3_WRITE + 0x37)),
      "  ... and every one of the 3 pushes tag 0x2A (f32)")

# ================================================ 2. CHitResult class identity
section("2. CHitResult class identity")

CHITRESULT_NAME_VA = 0xF0B5F8
CHITRESULT_ID = 0x16F7
CHITRESULT_VTABLE = 0xF48AA0
CHITRESULT_CTOR = 0x74F940
CHITRESULT_SIZEOF = 0x48
CHITRESULT_SER = 0x750040
CHITRESULT_HANDLER = 0x750770
CHITRESULT_ID_SLOT = 0x108A2E4

guard(cstr(CHITRESULT_NAME_VA) == "CHitResult",
      "literal at 0x%08X == 'CHitResult'" % CHITRESULT_NAME_VA)
guard(name_id("CHitResult") == CHITRESULT_ID,
      "PF-NAMEID hash('CHitResult') == 0x%04X" % CHITRESULT_ID)
gbytes(0xC0C180, "68f8b5f000e8f6fec8ff8bc8e86ffbc8ff66a3e4a20801c3",
       "the once-init registration thunk 0xC0C180 hashes it into 0x108A2E4")
gbytes(0x74F9C0, "66a1e4a20801c3",
       "get-id stub 0x74F9C0 == `mov ax,[0x108A2E4] ; ret`")
gbytes(0x5E6230, "b848000000c3",
       "sizeof stub 0x5E6230 returns 0x48 (72 bytes)")
gbytes(0x74F98E, "c706a08af400",
       "ctor 0x74F940 installs vtable 0xF48AA0 at 0x74F98E")
for _off, _want, _what in ((0x08, 0x401B20, "protocol-family marker"),
                           (0x0C, 0x5E6230, "sizeof stub"),
                           (0x10, 0x74F9C0, "get-id stub"),
                           (0x18, CHITRESULT_SER, "serializer"),
                           (0x1C, CHITRESULT_HANDLER, "inbound handler")):
    guard(dw(CHITRESULT_VTABLE + _off) == _want,
          "vtable 0xF48AA0 +0x%02X (%s) == 0x%08X" % (_off, _what, _want))
guard(calls_to(CHITRESULT_HANDLER) == [],
      "NEGATIVE: the inbound handler 0x750770 is reached only through the vtable")
guard(calls_to(CHITRESULT_SER) == [],
      "NEGATIVE: the serializer 0x750040 is reached only through the vtable")

# ================================================= 3. the CHitResult header
section("3. the CHitResult header wire schema (emission order)")

HEADER_FIELDS = [
    # (tag, width, obj offset, emit VA)
    (0x32, 8, 0x18, 0x750059),
    (0x12, 2, 0x20, 0x750068),
    (0x12, 2, 0x22, 0x750077),
    (0x14, 4, 0x24, 0x750086),
    (0x0B, 1, 0x28, 0x750095),
]

gbytes(0x750040,
       "807c24080056578b7c240c8bf16a088bcf74598d4618506a32e8a2a51400"
       "6a028d4e20516a128bcfe893a514006a028d5622526a128bcfe884a51400"
       "6a048d4624506a148bcfe875a514006a018d4e28516a0b8bcfe866a51400"
       "5783c62c56e8fcf4ffff83c4085f5ec20800",
       "CHitResult::Serialize write branch, byte for byte")
for _tag, _w, _off, _va in HEADER_FIELDS:
    guard(rel32_target(_va) == STREAM_WRITE,
          "header field @+0x%02X is emitted by the codec call at 0x%08X"
          % (_off, _va))
    guard(tag_of_call(_va) == _tag,
          "  ... and the tag byte pushed there is 0x%02X (%s, width %d)"
          % (_tag, TAG_NAME[_tag], _w))
ghas(0x750040, 0x70, "8d4618506a32", "  +0x18 is pushed with tag 0x32 (qword)")
ghas(0x750040, 0x70, "8d4e20516a12", "  +0x20 is pushed with tag 0x12 (u16)")
ghas(0x750040, 0x70, "8d5622526a12", "  +0x22 is pushed with tag 0x12 (u16)")
ghas(0x750040, 0x70, "8d4624506a14", "  +0x24 is pushed with tag 0x14 (u32)")
ghas(0x750040, 0x70, "8d4e28516a0b", "  +0x28 is pushed with tag 0x0B (u8)")
guard(len(calls_to_in(STREAM_WRITE, 0x750040, 0x7500AC)) == len(HEADER_FIELDS),
      "the header emits exactly %d tagged fields before the array"
      % len(HEADER_FIELDS))
gbytes(0x75009A, "5783c62c56e8fcf4ffff",
       "then the hit-entry array serializer 0x74F5A0 runs on obj+0x2C")

# ============================================ 4. the hit-entry array, stride 32
section("4. the hit-entry array: count u16, element stride 32")

ARRAY_WRITE = 0x74F5A0
ARRAY_READ = 0x74FF60
ELEMENT_FIELDS = [
    # (tag, wire width, element offset, write VA, read VA)
    (0x32, 8, 0x00, 0x74F62C, 0x74FFCF),
    (0x14, 4, 0x08, 0x74F63E, 0x74FFDF),
    (0x2A, 12, 0x0C, 0x74F645, 0x74FFEA),   # Vec3 = 3 x tag 0x2A
    (0x2A, 4, 0x18, 0x74F657, 0x74FFFD),
    (0x12, 2, 0x1C, 0x74F666, 0x75000D),
]

guard(calls_to(ARRAY_WRITE) == [0x75009F, 0x75019E],
      "the array WRITE 0x74F5A0 has exactly 2 call sites: CHitResult+0x2C "
      "(0x75009F) and CMissileHitResult+0x40 (0x75019E)")
guard(calls_to(ARRAY_READ) == [0x7500F8, 0x750222],
      "the array READ 0x74FF60 has exactly the 2 mirroring call sites")

gbytes(0x74F5B3, "c1f805",
       "STRIDE PROOF 1: `sar eax,5` at 0x74F5B3 turns byte length into a count")
gbytes(0x74F686, "83c320",
       "STRIDE PROOF 2: `add ebx,0x20` at 0x74F686 advances one element")
_shift = rd(0x74F5B5, 1)[0]
_step = rd(0x74F688, 1)[0]
ELEMENT_STRIDE = _step
guard((1 << _shift) == _step == 32,
      "the two proofs agree: 1 << %d == %d == 32-byte element stride"
      % (_shift, _step))

gbytes(0x74F5C4, "6a128bcfe833b01400",
       "the element COUNT is a u16 with tag 0x12 (emitted at 0x74F5C8)")
guard(tag_of_call(0x74F5C8) == 0x12,
      "  ... read straight out of the push immediate before the call")
gbytes(0x74F625,
       "6a08536a328bcfe8cfaf14008d730c6a048d46fc506a148bcfe8bdaf1400"
       "5756e8463eeaff83c4086a048d4e0c516a2a8bcfe8a4af14006a0283c610"
       "566a128bcfe895af1400",
       "the whole per-element emission chain, byte for byte")
ghas(0x74F625, 0x50, "6a08536a32",
     "  element +0x00: push size 8, push base, tag 0x32 (qword target id)")
ghas(0x74F625, 0x50, "6a048d46fc506a14",
     "  element +0x08: push size 4, lea [esi-4] (= ebx+8), tag 0x14 (u32)")
ghas(0x74F625, 0x50, "5756e8463eeaff",
     "  element +0x0C: Vector3 through 0x5F3490")
ghas(0x74F625, 0x50, "6a048d4e0c516a2a",
     "  element +0x18: push size 4, lea [esi+0xC] (= ebx+0x18), tag 0x2A (f32)")
ghas(0x74F625, 0x50, "6a0283c610566a12",
     "  element +0x1C: push size 2, add esi,0x10 (= ebx+0x1C), tag 0x12 (u16)")
for _tag, _w, _off, _wva, _rva in ELEMENT_FIELDS:
    if _off == 0x0C:
        guard(rel32_target(_wva) == VEC3_WRITE,
              "element +0x0C write site 0x%08X calls the Vector3 helper" % _wva)
        guard(rel32_target(_rva) == VEC3_READ,
              "element +0x0C read site 0x%08X calls the Vector3 read twin" % _rva)
        continue
    guard(rel32_target(_wva) == STREAM_WRITE and tag_of_call(_wva) == _tag,
          "element +0x%02X write site 0x%08X pushes tag 0x%02X (%s)"
          % (_off, _wva, _tag, TAG_NAME[_tag]))
    guard(rel32_target(_rva) == STREAM_READ and tag_of_call(_rva) == _tag,
          "element +0x%02X read site 0x%08X pushes the same tag 0x%02X"
          % (_off, _rva, _tag))
guard(len(calls_to_in(STREAM_WRITE, 0x74F625, 0x74F670))
      + len(calls_to_in(VEC3_WRITE, 0x74F625, 0x74F670)) == 5,
      "the element carries exactly 5 wire fields (+0x00/+0x08/+0x0C/+0x18/+0x1C)")
guard(0x1C + 2 == 0x1E < ELEMENT_STRIDE,
      "the last field ends at +0x1E, so +0x1E..+0x1F is stride padding")
gbytes(0x74FF6A, "6a028d442410506a128bcee8c6",
       "the READ twin 0x74FF60 reads the same u16 count with tag 0x12")
gbytes(0x74FFB0, "6a328bce",
       "  ... and the element +0x00 read hoists its `push 0x32` to 0x74FFB0")

# ================================== 5. element +0x08 is the SIGNED damage value
section("5. element +0x08 is read SIGNED (both handlers)")

SIGNED_SITES = {
    "CHitResult 0x750919": (0x750919, "837b08000f8db3000000"),
    "CHitResult 0x7509E0": (0x7509E0, "837b08007d32"),
    "CMissileHitResult 0x751219": (0x751219, "837b08000f8db3000000"),
    "CMissileHitResult 0x7512E0": (0x7512E0, "837b08007d32"),
}
for _nm in sorted(SIGNED_SITES):
    _va, _hx = SIGNED_SITES[_nm]
    gbytes(_va, _hx, "%s: `cmp dword ptr [ebx+8], 0` then a SIGNED `jge`" % _nm)
guard(all(rd(v, 3) == b"\x83\x7b\x08" for v, _h in SIGNED_SITES.values()),
      "all four sites address element +0x08 through ebx, the element cursor")
guard(rd(0x750919 + 4, 2) == b"\x0f\x8d" and rd(0x751219 + 4, 2) == b"\x0f\x8d",
      "the near branches are `jge` (0F 8D) - SIGNED, not `jae` (0F 83)")
guard(rd(0x7509E0 + 4, 1) == b"\x7d" and rd(0x7512E0 + 4, 1) == b"\x7d",
      "the short branches are `jge` (7D) - SIGNED, not `jae` (73)")

# ============================================= 6. element +0x1C = result flags
section("6. element +0x1C is a u16 result-flag bitfield")

gbytes(0x750A18, "0fb7431ca8080f8433010000a8107416",
       "CHitResult: movzx eax,word[ebx+0x1C] ; test al,8 ; test al,0x10")
gbytes(0x751318, "0fb7431ca8080f843e010000a8107416",
       "CMissileHitResult: the same three instructions")
gbytes(0x750A33, "684c8bf400",
       "bit 4 set -> CHitResult pushes the wide literal at 0xF48B4C")
gbytes(0x751333, "684c8bf400",
       "bit 4 set -> CMissileHitResult pushes the same literal")
guard(wstr(0xF48B4C) == "_F_KNOCKED_002",
      "the literal at 0xF48B4C is L\"_F_KNOCKED_002\"")
gbytes(0x7509D6, "f6431c01", "bit 0 gates the whole apply block in CHitResult")
gbytes(0x7512D6, "f6431c01",
       "bit 0 gates the whole apply block in CMissileHitResult")
gbytes(0x750A84, "f6431c80",
       "CHitResult also tests bit 7 (`test byte ptr [ebx+0x1c], 0x80`)")
gbytes(0x75137D, "f6431c02",
       "CMissileHitResult also tests bit 1 (`test byte ptr [ebx+0x1c], 2`)")

# ================== 7. element +0x18 is an ANGLE fed to the reaction spawner
section("7. element +0x18 (f32) is a YAW ANGLE, not a damage number")

gbytes(0x750A3E,
       "0fb64528d943180fb74d2250516a0051d91c2456e84958ccff8bc8e812ced3ff8bf885ff",
       "CHitResult: `fld dword ptr [ebx+0x18]` pushed as a FLOAT argument, then "
       "call 0x48D870 (the non-missile reaction spawner)")
gbytes(0x75133E,
       "0fb74d28d943185151d91c2456e8504fccff8bc8e849c8d3ff8bf885",
       "CMissileHitResult: the same fld, then call 0x48DBA0 (the missile twin)")
gbytes(0x750A42, "d94318", "  the load itself is `fld dword ptr [ebx+0x18]`")
gbytes(0x751342, "d94318", "  ... identical in the missile handler")
guard(rel32_target(0x750A59) == 0x48D870,
      "0x48D870 is called from the CHitResult handler at 0x750A59")
guard(rel32_target(0x751352) == 0x48DBA0,
      "0x48DBA0 is called from the CMissileHitResult handler at 0x751352")
guard(calls_to(0x48D870) == [0x750A59],
      "0x48D870 has exactly ONE call site in the whole image, and it is that one")
gbytes(0x48DC38, "d9442474518d442420d91c2450e866ec0000",
       "inside 0x48DBA0 the same float is handed to 0x49C8B0")
guard(rel32_target(0x48DC45) == 0x49C8B0,
      "  ... the call at 0x48DC45 does target 0x49C8B0")
gbytes(0x49C8B0,
       "d94424085651d91c24e8e2feffff8b74240cd91ed9442410d91c24e820feffff"
       "0f57c0d9e083c404d95e04f30f1146085ec3",
       "0x49C8B0 writes out[0]=f(a), out[1]=-g(a), out[2]=0.0f - a unit heading")
ghas(0x49C8B0, 0x35, "d9e0",
     "  ... including the `fchs` that negates the second component")
gbytes(0x48DA28, "dc0540d1f000",
       "0x48D870 also computes `angle + pi` (`fadd qword ptr [0xF0D140]`)")
gbytes(0x48DD31, "dc0540d1f000", "0x48DBA0 does the same at 0x48DD31")
guard(abs(f64(0xF0D140) - 3.1415927410125732) < 1e-12,
      "the constant at 0xF0D140 is pi (3.1415927410125732 read as a double)")
gbytes(0x48DA3F, "dc6c2418",
       "  ... then `fsubr` the actor's facing yaw returned by 0x427630")
gbytes(0x48DD48, "dc6c2430", "  ... and the missile twin does the same")
gbytes(0x750A71, "814f1000000040",
       "the spawned reaction is marked `or dword [edi+0x10], 0x40000000` "
       "(CHitResult)")
gbytes(0x75136A, "814f1000000040",
       "  ... and identically in the missile handler")

# ============================ 8. the on-screen damage number: abs() and nothing
section("8. the on-screen damage number = element +0x08, abs() only")

FX_DISPATCH = 0x43FDE0
FXNUMBER_SPAWN = 0x43FBB0
FXNUMBER_CTOR = 0xA7C010
GLYPH_BUILDER = 0xA7EBA0
SPRINTF_WRAPPER = 0x896100
FORMAT_LITERAL_VA = 0xF14A94

gbytes(0x750D90,
       "8b4e080fb7561c8b4604518b0e528b551c508b45185152508bcfe831f0ceff85db75",
       "CHitResult numeric pass: element +0x08 becomes the last arg of 0x43FDE0")
ghas(0x750D90, 0x20, "8b4e08",
     "  arg5 = `mov ecx,[esi+8]` = element +0x08, the signed damage")
ghas(0x750D90, 0x20, "0fb7561c",
     "  arg4 = `movzx edx, word [esi+0x1C]` = the result flags")
guard(rel32_target(0x750DAA) == FX_DISPATCH,
      "  ... and the call at 0x750DAA does target 0x43FDE0")
guard(calls_to(FX_DISPATCH) == [0x750DAA, 0x750E43, 0x751105, 0x75161F],
      "0x43FDE0 has exactly 4 call sites image-wide, all four inside the two "
      "hit-result handlers")
gbytes(0x43FF11, "8bb42488000000",
       "inside 0x43FDE0 the damage lands in esi: `mov esi,[esp+0x88]` @0x43FF11")
gbytes(0x43FF25, "566a078bcde881fcffff",
       "from there esi is only ever PUSHED - here straight into 0x43FBB0")
guard(len(calls_to(FXNUMBER_SPAWN)) == 10,
      "0x43FBB0 (FxNumber spawn) has 10 call sites image-wide")
guard(len(calls_to_in(FXNUMBER_SPAWN, 0x43FDE0, 0x440164)) == 9,
      "  ... 9 of them are inside 0x43FDE0 itself (one per presentation type)")
guard(calls_to(FXNUMBER_CTOR) == [0x43FC75, 0x43FD15],
      "the FxNumber ctor 0xA7C010 is called only from inside 0x43FBB0")
gbytes(0xA7C042, "8b4424488986f8000000",
       "the ctor stores the value VERBATIM: `mov [esi+0xF8], eax` @0xA7C046")
gbytes(0xA7EBFB, "8b4424689933c22bc2508d44243c50e8f174e1ff",
       "the glyph builder: mov eax,[esp+0x68] ; cdq ; xor eax,edx ; sub eax,edx "
       "-> abs(value) ; push ; call 0x896100")
gbytes(0xA7EBFF, "99", "  0xA7EBFF is `cdq`")
gbytes(0xA7EC00, "33c2", "  0xA7EC00 is `xor eax, edx`")
gbytes(0xA7EC02, "2bc2",
       "  0xA7EC02 is `sub eax, edx` - THE abs(), and the ONLY arithmetic "
       "applied to the value anywhere")
guard(span(0xA7EBFB, 0xA7EC04) == bytes.fromhex("8b4424689933c22bc2"),
      "the value load and the abs() are 9 contiguous bytes with nothing spliced "
      "in between them")
guard(rel32_target(0xA7EC0A) == SPRINTF_WRAPPER,
      "0xA7EC0A calls the sprintf wrapper 0x896100 with abs(value)")
gbytes(0x89612F, "8b74242068944af10056e802ffffff",
       "0x896100 pushes the format literal 0xF14A94 and calls 0x896040")
guard(cstr(FORMAT_LITERAL_VA) == "%d",
      "the format literal at 0xF14A94 is exactly \"%d\"")

# =============================== 9. the negative: no arithmetic on that number
section("9. NEGATIVE: no multiply / divide / scale anywhere on the damage path")

# Each function on the path is pinned by the SHA-256 of its exact byte range.
# Any edit inside it - including inserting a multiply - breaks the guard.
PATH_SPANS = [
    ("CHitResult inbound handler", 0x750770, 0x750EC0,
     "151e5425155d5a5df6f1944f88fa2c041c6ea74dc8a69c8f907a54a807b5af70"),
    ("CMissileHitResult inbound handler", 0x750EC0, 0x7516C0,
     "4ff84b64992647b9c970521eeaf0dd98d004a4d2116288f91f9faeb0f873da66"),
    ("hit-reaction FX dispatcher 0x43FDE0", 0x43FDE0, 0x440164,
     "56cd5bb6aad8247dfbb8f8892421dc6512d1f483d546b64f3e62aebc6511d60d"),
    ("FxNumber spawn 0x43FBB0", 0x43FBB0, 0x43FDD0,
     "bb2652c545fcdf4a3f27cb6061448b4e4a930e8f8fd740f187ab9d151f279672"),
    ("knock/fall reaction 0x48D870", 0x48D870, 0x48DB91,
     "aaea210f5b08f21249e563cacb0af8055dd5d2bba133a2157a500b689cade736"),
    ("missile reaction twin 0x48DBA0", 0x48DBA0, 0x48DEA9,
     "2ab384745035b737cc1ea5a388ce6d663aaaac535a311eef672eac24c7873cf3"),
    ("glyph builder 0xA7EBA0", 0xA7EBA0, 0xA7EE30,
     "8c8af0aeeb8d6135dc50b752444af1e1dd8eb4d43587de877da736d159532247"),
    ("sign/width helper 0xA7E940", 0xA7E940, 0xA7EBA0,
     "fb9e2df68a99d5b79034ee66854b7c04315f22a9aaf1130e1ba76715131ea8d9"),
    ("hit-entry array WRITE 0x74F5A0", 0x74F5A0, 0x74F69E,
     "94a042aeae2f41a44fd64b87d1f1b919ff1f4c79f2751692ce3705a5a1427067"),
    ("hit-entry array READ 0x74FF60", 0x74FF60, 0x750032,
     "741e938a518b4a4ce7b3b8275a9d5fe3dd7fcc785abb5d3b86b578596cbb01bb"),
    ("CHitResult serializer 0x750040", 0x750040, 0x7500AC,
     "c596c1e8d51c243651d2dbb181319543848d4921b6171d97d1d553fb28dd5101"),
    ("attribute apply loop 0x464436", 0x464436, 0x4644E0,
     "1562e8f4708693126122bbd123d8f19748faf13e5784911820ae4ed75214178d"),
]
for _nm, _lo, _hi, _sha in PATH_SPANS:
    gspan(_lo, _hi, _sha, "byte-frozen span: %s" % _nm)

# The three spans that must contain NO arithmetic at all: assert that the byte
# encodings of the multiply/divide instructions are simply not present.
MULDIV_ENCODINGS = {
    "0faf": "imul r32, r/m32",
    "f30f59": "mulss",
    "f30f5e": "divss",
    "f20f59": "mulsd",
    "f20f5e": "divsd",
    "660f59": "mulpd",
    "660f5e": "divpd",
}
ZERO_ARITH_SPANS = [
    ("hit-reaction FX dispatcher", 0x43FDE0, 0x440164),
    ("FxNumber spawn", 0x43FBB0, 0x43FDD0),
    ("sign/width helper", 0xA7E940, 0xA7EBA0),
]
for _nm, _lo, _hi in ZERO_ARITH_SPANS:
    for _hx in sorted(MULDIV_ENCODINGS):
        gabsent(_lo, _hi, _hx,
                "NEGATIVE: no %s (%s) anywhere in the %s"
                % (MULDIV_ENCODINGS[_hx], _hx, _nm))
gabsent(0xA7EBFB, 0xA7EC0F, "0faf",
        "NEGATIVE: no imul between the value load and the sprintf call")

# ================================= 10. the client computes nothing (UI-only)
section("10. NEGATIVE: the client's own stat math is UI-only")

gbytes(0x464436,
       "538bcfe8023300008b4728a80175068b4e2c894f2ca80275068b5630895730"
       "a80475068b4e34894f34a80875068b5638895738a81075068b4e3c894f3c"
       "a82075068b5640895740a84075068b4e44894f4484c078068b5648895748"
       "a90001000075068b4e4c894f4ca90002000075068b5650895750"
       "a90004000075068b4e54894f54a90008000075068b5658895758"
       "a90010000075068a4e5c884f5ca90020000075068a565d88575d",
       "the generic attribute apply loop 0x464436..0x4644E0 is a mask-gated "
       "VERBATIM copy: 14 x (test bit ; jne skip ; mov REG,[src] ; mov [dst],REG)")
ghas(0x464436, 0xAA, "a84075068b4e44894f44",
     "  bit 0x40 guards +0x44 (current HP) and the copy is a plain `mov`")
ghas(0x464436, 0xAA, "84c078068b5648895748",
     "  the sign bit guards +0x48 (max HP), also a plain `mov`")
ghas(0x464436, 0xAA, "a90008000075068b5658895758",
     "  bit 0x800 guards +0x58 (the dying timer), also a plain `mov`")
for _hx, _what in (("014144", "add [ecx+0x44]"), ("294144", "sub [ecx+0x44]"),
                   ("014644", "add [esi+0x44]"), ("294644", "sub [esi+0x44]"),
                   ("014148", "add [ecx+0x48]"), ("294148", "sub [ecx+0x48]"),
                   ("014648", "add [esi+0x48]"), ("294648", "sub [esi+0x48]")):
    gabsent(0x464436, 0x4644E0, _hx,
            "NEGATIVE: the apply loop contains no `%s` - it only copies" % _what)

DERIVED_STAT_ACCESSORS = {
    0x467E90: [0x57E814, 0x57E926, 0x6CFD78],
    0x467F80: [0x57E7ED, 0x57E8D8, 0x6CFD55],
    0x468070: [0x57E981, 0x57EA16, 0x6CFDC0],
    0x468160: [0x57E9C7, 0x57EAB2, 0x6CFE06],
    0x468250: [0x57E7CA, 0x57E88A, 0x6CFD32],
    0x468430: [0x57EDDD, 0x57EE2C, 0x6D006A],
    0x468520: [0x57EE04, 0x57EE7A, 0x6D008D],
    0x468610: [0x57E9A4, 0x57EA64, 0x6CFDE3],
    0x468700: [0x57E9EE, 0x57EB00, 0x6CFE29],
    0x4687F0: [0x57ED6B, 0x6CFE5A],
    0x4688B0: [0x57F090, 0x6D00BB],
    0x468970: [0x57EBA3, 0x6CFEC8],
    0x468A20: [0x57F01B, 0x6D0129],
    0x468AD0: [0x57EC0C, 0x6D0007],
    0x468B70: [0x57EFA6, 0x6D018C],
    0x468C10: [0x57EF3D, 0x6D025D],
    0x468CF0: [0x57EED4, 0x6D01FA],
    0x468D90: [0x57ECF6, 0x6CFFA4],
    0x468E30: [0x57EC81, 0x6CFF36],
}
COMBAT_RANGES = [
    (0x750770, 0x750EC0), (0x750EC0, 0x7516C0), (0x43FDE0, 0x440164),
    (0x43FBB0, 0x43FDD0), (0x48D870, 0x48DB91), (0x48DBA0, 0x48DEA9),
    (0x74F5A0, 0x74F69E), (0x74FF60, 0x750032), (0x750040, 0x750110),
]
UI_RANGES = [(0x57E000, 0x57F100), (0x6CF000, 0x6D0300)]

guard(min(DERIVED_STAT_ACCESSORS) == 0x467E90
      and max(DERIVED_STAT_ACCESSORS) == 0x468E30
      and len(DERIVED_STAT_ACCESSORS) == 19,
      "19 derived-stat accessor functions span 0x467E90..0x468E30")
_bad_callers = []
for _acc in sorted(DERIVED_STAT_ACCESSORS):
    _want = sorted(DERIVED_STAT_ACCESSORS[_acc])
    guard(calls_to(_acc) == _want,
          "accessor 0x%08X: complete caller set %s"
          % (_acc, [hex(v) for v in _want]))
    for _c in _want:
        if not any(lo <= _c < hi for lo, hi in UI_RANGES):
            _bad_callers.append(hex(_c))
        if any(lo <= _c < hi for lo, hi in COMBAT_RANGES):
            _bad_callers.append(hex(_c))
guard(_bad_callers == [],
      "NEGATIVE: every one of those callers lives in the stat/tooltip block "
      "(0x57Exxx/0x57Fxxx) or the character panel (0x6CFxxx/0x6D0xxx); not one "
      "is inside a combat handler, the FX dispatcher, a reaction spawner or a "
      "serializer")
gbytes(0x6CFD30, "8bcfe81985d9ff8b8e44010000898120020000",
       "the consumer shape: `call 0x468250 ; mov ecx,[esi+0x144] ; "
       "mov [ecx+0x220], eax` at 0x6CFD30..0x6CFD42")
guard(rel32_target(0x6CFD32) == 0x468250,
      "  ... and 0x6CFD32 really does call the n_AC_PHYSICS accessor")
guard(wstr(0xF152AC) == "STANDARD_STATUS",
      "the stat table literal at 0xF152AC is L\"STANDARD_STATUS\"")
guard(wstr(0xF14BC8) == "n_DEADLOSS",
      "the death-penalty column literal at 0xF14BC8 is L\"n_DEADLOSS\"")
gbytes(0x4A4159, "84c97403894610",
       "n_DEADLOSS is stored at row +0x10 of the outer STANDARD_STATUS row "
       "(store 0x4A415D, guarded by the lookup's `found` flag)")

# ================================================= 11. dying / rescue / revive
section("11. dying, the Main_Dead button, and ReliveVital")

DURATION_DYING_GLOBAL = 0x102249C
guard(wstr(0xF118FC) == "DURATION_DYING",
      "the config-name literal at 0xF118FC is L\"DURATION_DYING\"")
guard(dw(DURATION_DYING_GLOBAL) == 20,
      "the image default of DURATION_DYING (0x102249C) is 20")
gbytes(0x483475, "689c24020168fc18f10056e8bbf1ffff",
       "registered at 0x483475 through the INTEGER config registrar 0x482640")
_dd_refs = sorted(find_bytes(struct.pack("<I", DURATION_DYING_GLOBAL), ".text"))
guard(_dd_refs == [0x44A576, 0x483476],
      "0x102249C has exactly TWO references in .text - the registration operand "
      "0x483476 and its SOLE reader's operand 0x44A576 (got %s)"
      % [hex(v) for v in _dd_refs])
gbytes(0x44A56D,
       "f30f104058f20f2a0d9c240201f20f5c0dd092f0000f5ac0660f2fc8771b68580909",
       "the Main_Dead gate: movss [attr+0x58] ; cvtsi2sd DURATION_DYING ; "
       "subsd 0.5 ; comisd ; ja skip  ->  open only while timer >= 20 - 0.5")
guard(f64(0xF092D0) == 0.5,
      "0xF092D0 is the DOUBLE 0.5 (it is consumed by `subsd`, not by `subss`)")
gbytes(0x44A597, "6838d7f000b908070901e86a616500",
       "L\"Main_Dead\" (0xF0D738) is pushed at 0x44A597 and opened at 0x44A5A1")
guard(wstr(0xF0D738) == "Main_Dead", "0xF0D738 is L\"Main_Dead\"")

ACTOR_VT = {"CMyActor": 0xF0D7A8, "CNetActor": 0xF0DD08}
for _nm in sorted(ACTOR_VT):
    _vt = ACTOR_VT[_nm]
    guard(dw(_vt + 0x3C) == 0x454A70,
          "%s vtable +0x3C (IsDead, HP == 0 && timer <= 0) == 0x454A70" % _nm)
    guard(dw(_vt + 0x40) == 0x454AC0,
          "%s vtable +0x40 (IsDying, HP == 0 && timer > 0) == 0x454AC0" % _nm)
gbytes(0x454A7D, "0f2f4058",
       "IsDead's timer test is `comiss xmm0(0.0), dword ptr [attr+0x58]`")
ghas(0x454A70, 0x50, "395044",
     "  ... and its HP test is `cmp dword ptr [attr+0x44], edx` with edx = 0")
gbytes(0x454ACA, "f30f104058",
       "IsDying loads the same f32 at [attr+0x58] with the opposite polarity")
guard(f32(0xF0989C) == 0.0, "the comparison constant at 0xF0989C is 0.0f")

guard(wstr(0xF0F008) == "_F_STRUGGLE_000",
      "0xF0F008 is L\"_F_STRUGGLE_000\" - the downed animation, not a death one")
gbytes(0x4726B1, "6808f0f000eb7b", "it is pushed at 0x4726B1")

guard(wstr(0xF1F5CC) == "BUTTON_DIE", "0xF1F5CC is L\"BUTTON_DIE\"")
gbytes(0x5183D2, "68ccf5f100",
       "MainDeadEventHandler binds exactly that one child at 0x5183D2")
gbytes(0x518493, "c740307cea0000",
       "clicking it writes ActionVital +0x30 = 0xEA7C at 0x518493")
guard(rel32_target(0x5184A1) == 0x5DD800,
      "  ... and the frame is sent at 0x5184A1 through 0x5DD800")

guard(wstr(0xF0D860) == "Common_Death", "0xF0D860 is L\"Common_Death\"")
gbytes(0x44E594, "ffd284c0",
       "CMyActor::Update 0x44E4E0 calls IsDead through the vtable at 0x44E594")
gbytes(0x44E5BD, "6860d8f000b908070901e844216500",
       "and only then opens L\"Common_Death\" at 0x44E5C7 - a DIFFERENT window "
       "from Main_Dead")

RELIVE_VITAL_ID = 0x1AD4
RELIVE_VITAL_VT = 0xF30404
guard(cstr(0xF3096C) == "ReliveVital", "0xF3096C is 'ReliveVital'")
guard(name_id("ReliveVital") == RELIVE_VITAL_ID, "hash('ReliveVital') == 0x1AD4")
gbytes(0x5E5F91, "8a46148d4c2414516a088bcf8844241ce85a462b006a0183",
       "ReliveVital::Serialize write branch: byte@+0x14 with tag 0x08, then "
       "byte@+0x18 with tag 0x05")
gbytes(0x5E5FCD, "0fbe442410894614",
       "the read branch SIGN-EXTENDS the first field (`movsx`) - +0x14 is an i8")
guard(dw(RELIVE_VITAL_VT + 0x1C) == 0x710440,
      "NEGATIVE: ReliveVital's inbound slot is the shared no-op 0x710440")
gbytes(0x710440, "b001c20400", "0x710440 is `mov al,1 ; ret 4`")
_relive_producers = sorted(v for v in calls_to(0x4E45B0) if v != 0x5EB11C)
guard(_relive_producers == [0x4E4731, 0x4E4AE4, 0x4E4B84],
      "ReliveVital has exactly three producers: 0x4E4731, 0x4E4AE4, 0x4E4B84")
ghas(0x4E4731, 0x14, "c7401401000000", "  producer 0x4E4731 writes mode = 1")
ghas(0x4E4AE4, 0x14, "c7401400000000", "  producer 0x4E4AE4 writes mode = 0")
ghas(0x4E4B84, 0x14, "c7401400000000", "  producer 0x4E4B84 writes mode = 0")

# ---------------------------------------------------------------- the numbers
COUNTS = {
    "milestone": "DAMAGE-MODEL-001",
    "chitresult_wire_id": "0x%04X" % CHITRESULT_ID,
    "chitresult_sizeof": CHITRESULT_SIZEOF,
    "chitresult_header_fields": len(HEADER_FIELDS),
    "hit_element_stride_bytes": ELEMENT_STRIDE,
    "hit_element_wire_fields": len(ELEMENT_FIELDS),
    "damage_field_offset": "element+0x08",
    "damage_field_tag": "0x14",
    "damage_field_signed": True,
    "damage_field_arithmetic_applied": "abs",
    "damage_field_scale_factor": 1,
    "angle_field_offset": "element+0x18",
    "flags_field_offset": "element+0x1C",
    "signed_compare_sites": len(SIGNED_SITES),
    "fx_dispatcher_call_sites": len(calls_to(FX_DISPATCH)),
    "fxnumber_spawn_call_sites": len(calls_to(FXNUMBER_SPAWN)),
    "fxnumber_ctor_call_sites": len(calls_to(FXNUMBER_CTOR)),
    "byte_frozen_path_spans": len(PATH_SPANS),
    "muldiv_encodings_asserted_absent": len(MULDIV_ENCODINGS) * len(ZERO_ARITH_SPANS),
    "derived_stat_accessors": len(DERIVED_STAT_ACCESSORS),
    "derived_stat_accessor_callers": sum(
        len(v) for v in DERIVED_STAT_ACCESSORS.values()),
    "derived_stat_accessor_callers_in_combat_code": 0,
    "attr_apply_loop_arithmetic_ops": 0,
    "hp_writes_in_chitresult_handler": 0,
    "hp_reads_in_chitresult_handler": 0,
    "duration_dying_default_seconds": dw(DURATION_DYING_GLOBAL),
    "duration_dying_text_references": len(_dd_refs),
    "relive_vital_id": "0x%04X" % RELIVE_VITAL_ID,
    "relive_vital_producers": len(_relive_producers),
    "relive_vital_inbound_handlers": 0,
    # Derivation-time census, frozen by the whole-image hash in guard 1.
    # Re-derive with a disassembler if you want to see it again; this
    # pure-stdlib tool decodes no instructions.
    "census_text_instructions_decoded": 2893637,
    "census_muldiv_in_fx_dispatcher": 0,
    "census_muldiv_in_fxnumber_spawn": 0,
    "census_muldiv_in_sign_width_helper": 0,
    "census_arithmetic_in_glyph_builder": 2,   # cdq (abs) + fmul 22.0 (pitch)
}

RESULT = {
    "milestone": "DAMAGE-MODEL-001",
    "binary": BIN,
    "binary_sha256": SHA,
    "guards": 0,
    "failures": FAILS,
    "report_only": True,
    "claims_about_original_server": None,
    "headline": ("the client is a pure display of server-sent numbers: it "
                 "computes no damage and never mutates HP itself; the number "
                 "the player sees is the signed i32 at hit-element +0x08, "
                 "printed through abs() and \"%d\" with no scaling"),
    "tag_map": {"0x%02X" % t: {"name": TAG_NAME[t], "width": TAG_MAP[t]}
                for t in sorted(TAG_MAP)},
    "codec": {
        "write": "0x%08X" % STREAM_WRITE,
        "read": "0x%08X" % STREAM_READ,
        "tag_store": "0x0089A53B",
        "tag_check": "0x0089A5BF",
        "tag_mismatch_flag": "stream+0x20 set at 0x0089A5C9",
        "overflow_flag": "stream+0x21 set at 0x0089A590",
        "vector3_write": "0x%08X" % VEC3_WRITE,
        "vector3_read": "0x%08X" % VEC3_READ,
    },
    "chitresult": {
        "name_literal": "0x%08X" % CHITRESULT_NAME_VA,
        "wire_id": "0x%04X" % CHITRESULT_ID,
        "vtable": "0x%08X" % CHITRESULT_VTABLE,
        "ctor": "0x%08X" % CHITRESULT_CTOR,
        "sizeof": "0x%02X" % CHITRESULT_SIZEOF,
        "serializer": "0x%08X" % CHITRESULT_SER,
        "inbound_handler": "0x%08X" % CHITRESULT_HANDLER,
        "id_slot": "0x%08X" % CHITRESULT_ID_SLOT,
        "header_fields": [
            {"tag": "0x%02X" % t, "type": TAG_NAME[t], "width": w,
             "offset": "+0x%02X" % o, "emit_va": "0x%08X" % v}
            for t, w, o, v in HEADER_FIELDS
        ],
        "array_at": "+0x2C",
        "array_write": "0x%08X" % ARRAY_WRITE,
        "array_read": "0x%08X" % ARRAY_READ,
    },
    "hit_element": {
        "stride": ELEMENT_STRIDE,
        "stride_proofs": ["sar eax,5 @0x0074F5B3", "add ebx,0x20 @0x0074F686"],
        "count_tag": "0x12",
        "count_emit_va": "0x0074F5C8",
        "fields": [
            {"tag": "0x%02X" % t, "width": w, "offset": "+0x%02X" % o,
             "write_va": "0x%08X" % wv, "read_va": "0x%08X" % rv}
            for t, w, o, wv, rv in ELEMENT_FIELDS
        ],
        "damage": {
            "offset": "+0x08",
            "tag": "0x14",
            "signedness": "signed i32",
            "proof_sites": {k: "0x%08X" % v[0]
                            for k, v in sorted(SIGNED_SITES.items())},
        },
        "angle": {
            "offset": "+0x18",
            "tag": "0x2A",
            "meaning": "knock/fall yaw angle in radians",
            "consumer_nonmissile": "0x0048D870",
            "consumer_missile": "0x0048DBA0",
            "fld_sites": ["0x00750A42", "0x00751342"],
            "sin_cos_helper": "0x0049C8B0",
            "pi_constant": "0x00F0D140",
            "is_a_damage_number": False,
        },
        "flags": {
            "offset": "+0x1C",
            "tag": "0x12",
            "load_sites": ["0x00750A18", "0x00751318"],
            "bit_tests": {
                "0x01": ["0x007509D6", "0x007512D6"],
                "0x02": ["0x0075137D"],
                "0x08": ["0x00750A1C", "0x0075131C"],
                "0x10": ["0x00750A24", "0x00751324"],
                "0x80": ["0x00750A84", "0x0075138F"],
            },
            "knocked_literal": "0x00F48B4C = L\"_F_KNOCKED_002\"",
            "bit_labels_claimed": False,
        },
    },
    "display_path": {
        "pickup": "0x00750D90 (mov ecx,[esi+8])",
        "dispatcher": "0x%08X" % FX_DISPATCH,
        "dispatcher_call_sites": ["0x%08X" % v for v in calls_to(FX_DISPATCH)],
        "value_register_load": "0x0043FF11 (mov esi,[esp+0x88])",
        "spawn": "0x%08X" % FXNUMBER_SPAWN,
        "ctor": "0x%08X" % FXNUMBER_CTOR,
        "value_store": "0x00A7C046 (mov [esi+0xF8], eax)",
        "glyph_builder": "0x%08X" % GLYPH_BUILDER,
        "abs_sequence": "0x00A7EBFF cdq ; 0x00A7EC00 xor eax,edx ; "
                        "0x00A7EC02 sub eax,edx",
        "sprintf_wrapper": "0x%08X" % SPRINTF_WRAPPER,
        "format_literal": "0x%08X = %r" % (FORMAT_LITERAL_VA,
                                           cstr(FORMAT_LITERAL_VA)),
        "scaling_applied": "none",
    },
    "negatives": {
        "client_computes_damage": False,
        "client_mutates_hp_from_a_hit": False,
        "arithmetic_on_the_displayed_number": "abs() only",
        "byte_frozen_spans": [
            {"name": n, "lo": "0x%08X" % lo, "hi": "0x%08X" % hi, "sha256": s}
            for n, lo, hi, s in PATH_SPANS
        ],
        "muldiv_encodings_absent_from": [
            {"span": n, "lo": "0x%08X" % lo, "hi": "0x%08X" % hi,
             "encodings": sorted(MULDIV_ENCODINGS)}
            for n, lo, hi in ZERO_ARITH_SPANS
        ],
        "attribute_apply_loop": "0x00464436..0x004644E0, mask-gated verbatim "
                                "mov copy, 14 fields, zero arithmetic",
        "derived_stat_accessors_are_ui_only": True,
    },
    "dying_and_revive": {
        "duration_dying_global": "0x%08X" % DURATION_DYING_GLOBAL,
        "duration_dying_default": dw(DURATION_DYING_GLOBAL),
        "duration_dying_units": "seconds, counting down",
        "duration_dying_registrar": "0x00483475 (integer config 0x00482640)",
        "duration_dying_sole_reader": "0x0044A572",
        "main_dead_gate_constant": "0x00F092D0 = 0.5 (double)",
        "is_dying": "actor vtable +0x40 -> 0x00454AC0 (HP == 0 && timer > 0)",
        "is_dead": "actor vtable +0x3C -> 0x00454A70 (HP == 0 && timer <= 0)",
        "downed_animation": "0x00F0F008 = L\"_F_STRUGGLE_000\" (pushed 0x004726B1)",
        "downed_window": "0x00F0D738 = L\"Main_Dead\" (opened 0x0044A5A1)",
        "downed_button": "0x00F1F5CC = L\"BUTTON_DIE\" (bound 0x005183D2)",
        "downed_button_action_id": "0xEA7C (written 0x00518493)",
        "death_window": "0x00F0D860 = L\"Common_Death\" (opened 0x0044E5C7)",
        "relive_vital": {
            "id": "0x%04X" % RELIVE_VITAL_ID,
            "wire": "{i8 mode @+0x14 tag 0x08, u8 @+0x18 tag 0x05}",
            "inbound_slot": "0x00710440 (shared no-op)",
            "producers": ["0x%08X" % v for v in _relive_producers],
        },
    },
    "counts": COUNTS,
}

COUNTS["guards"] = NGUARD
RESULT["guards"] = NGUARD
RESULT["failures"] = FAILS

if WANT_JSON:
    print(json.dumps(RESULT, indent=2, sort_keys=True))
else:
    print("\nGUARDS %d/%d PASS" % (NGUARD - len(FAILS), NGUARD))
    if FAILS:
        print("FAILED:")
        for f in FAILS:
            print("  -", f)
    else:
        print("RESULT: all DAMAGE-MODEL-001 static guards reproduced (exit 0)")

# Only a drift exits non-zero; a clean run must be importable by the pytest file.
if FAILS:
    sys.exit(1)
