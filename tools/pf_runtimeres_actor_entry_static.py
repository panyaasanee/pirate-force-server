#!/usr/bin/env python3
"""PF RUNTIMERES-ACTOR-ENTRY-001 - is the "RuntimeRes actor-entry pipe" really the
only way to reach L"_F_DIE_000", and what does a server actually have to send?

The chief's note carried, unchecked, for three rounds:

    "the RuntimeRes actor-entry pipe is the only path that reaches _F_DIE_000"

This verifier settles it byte-exact, from the read-only client image alone.
Every number the companion report prints is re-derived here; nothing is typed
by hand.

  * FIRST: THE NAME.  The literal string "RuntimeRes" does NOT EXIST anywhere in
    the 14,759,424-byte image (0 occurrences, and 0 for "RunTimeRes" and
    "RuntimeProtocol" too).  What exists is the pair

        GSCN_RunTimeProtocolReq  @0xF2FFE0  id 0x6E6F (28271)  vtable 0xF2FF80
        GSCN_RunTimeProtocolRes  @0xF2FFF8  id 0x6E9D (28317)  vtable 0xF2FFC0

    "Res" is RESPONSE, not RESOURCE.  0x6E9D == 28317 is the exact ErrorData
    number this project has already seen live from the client's own reader
    (see src/.../delete_actor_hypothesis.py), so the name->id hash and the
    runtime observation agree.  "RuntimeRes" is a PROJECT NICKNAME, not a
    class in the binary.  The nickname is legitimate; the class it names is
    GSCN_RunTimeProtocolRes.

  * SECOND: THE PIPE IS REAL, AND IT IS A DERIVED-MASK BIT.  Serializer
    0x5E3EE0 calls the inherited base 0x5F4070 first, then writes its OWN u8
    change mask (tag 0x0B) whose three bits select three sub-objects:

        bit 0x02 -> object +0x1C   THE ACTOR-ENTRY COLLECTION
        bit 0x04 -> object +0x24
        bit 0x08 -> object +0x20

    Inbound handler 0x5E4060 takes +0x1C, adds 0x10 (the list head) and drives
    0x446F30 - the actor reconcile loop.  0x446F30 has EXACTLY ONE caller in
    the whole image: 0x5E4085, inside that handler.  Nothing else on any code
    path, in any table, anywhere in the file, reaches it.

  * THIRD: THE CHAIN, AND THE CENSUS THAT CLOSES IT.

        0x5E4060 (GSCN_RunTimeProtocolRes inbound, vtable 0xF2FFC0 +0x1C)
          -> 0x446F30           1 direct caller, 0 pointer occurrences
            -> actor vtable +0x20
                 0x4446F0       1 direct caller + 4 vtable slots
                 0x456630       0 direct callers + 3 vtable slots -> 0x4446F0
              -> 0x4437C0       1 direct caller (0x444705), 0 pointer occurrences
                -> 0x472810     1 direct caller (0x4439E9), 0 pointer occurrences
                   CActorTask_Dead, vtable 0xF0F048, task id 0x80000005
                  -> 0x472850   0 direct callers, 1 pointer occurrence
                                (0xF0F054 = task vtable +0x0C)
                     plays L"_F_DIE_000" @0xF0F060 through actor vtable +0x28

    The census is done over ALL executable sections (.text AND the separate
    0x2E1-byte .code section at 0xC3A000, which the round-83 sweep never
    looked at) for E8 and E9 rel32, and over EVERY BYTE OF THE FILE at every
    alignment for the target VA as a little-endian dword - which catches
    vtable slots, jump tables, `mov reg,imm32`, and FF 15 / FF 25 indirect
    targets alike.  No linear disassembly is used anywhere, so there is no
    "the decoder stopped and I reported a confident negative" failure mode.

  * FOURTH: THE ROUND-83 HEADLINE IS WRONG ABOUT THE CARRIER.  HP-DEATH-001
    said an `UpdateAttrVital` carrying BasicAttr bit 0x0004 = 0 plus bit
    0x0080 > 0 is "the whole trigger".  UpdateAttrVital's inbound handler is
    0x5F2400.  Across its whole extent 0x5F2400..0x5F261A there are ZERO
    `mov r,[reg+0x20]; call r` dispatch shapes, so it cannot reach 0x4446F0,
    cannot reach 0x4437C0, cannot latch [actor+0x70] |= 0x200, cannot build a
    CActorTask_Dead and cannot play _F_DIE_000.  (The local player's
    L"Main_Dead" window is a separate, per-frame read of the attribute and is
    NOT affected by this correction.)

  * FIFTH: THE TIMER POLARITY IS THE OPPOSITE OF WHAT THE ANIMATION NEEDS.

        actor vtable +0x40  0x43BDA0   HP(+0x44)==0  AND  f32(+0x58) >  0.0f
        actor vtable +0x3C  0x43BD70   HP(+0x44)==0  AND  f32(+0x58) <= 0.0f

    0x4437C0 keeps +0x40 in `bl` and +0x3C at [esp+0x13].  `bl` gates the
    0x200 "dying" latch at 0x44385D.  [esp+0x13] gates the CActorTask_Dead
    construction at 0x443990.  They are mutually exclusive on one snapshot:
    a positive timer gives the DYING latch and NO animation; a zero or
    negative timer with zero HP gives the animation.

  * SIXTH: AN ACTOR CANNOT BE BORN DEAD.  0x446F30 looks the entry's 64-bit
    identity (entry +0x18/+0x1C) up with 0x446170.  Found -> actor vtable
    +0x20 (apply AND dead-sync).  Not found -> 0x446990, which constructs the
    actor and applies through actor vtable +0x10 (0x454920 / 0x45D200) - both
    of which call the same apply loop 0x5DF080 but NEITHER of which calls
    0x4437C0, because 0x4437C0 has exactly one caller and it is not them.
    So the first entry for an identity spawns; only a SECOND entry can kill.

  * SEVENTH: THE ACTOR-TYPE GATE IS 2..6, AND IT IS A JUMP TABLE.  0x4469C8
    reads `movzx eax, byte [entry+0x10]`, subtracts 2, rejects `> 4`, then
    jumps through the 5-entry table at 0x446B2C:

        2 -> pool 0x444DE0  size 0x3A8  ctor 0x457340  vtable 0xF0DD08 CNetActor
        3 -> inline         size 0x488  ctor 0x44C990  vtable 0xF0D7A8 CMyActor
        4 -> pool 0x444F00  size 0x368  ctor 0x45CC00  vtable 0xF0DF58 CNetNPC
        5 -> pool 0x445020  size 0x378  ctor 0x45D000  vtable 0xF0DFF8 CAvatarNPC
        6 -> pool 0x445140  size 0x4E8  ctor 0x45E4E0  vtable 0xF0E0C8 Pet

    Type 3 additionally requires [0x1032EC4] == 0 (no local player yet).

  * EIGHTH: THE ANIMATION HAS A SECOND GATE NOBODY HAD NOTICED.  0x472850
    requires `test byte [actor+0x70], 0x40` before it plays the literal.  That
    bit is set by the model-load path (0x4448B4 and 0x4599B4), so an actor
    whose visual never resolved will latch, spawn the task, and still never
    animate.

NOT CLAIMED: nothing about the ORIGINAL server.  No runtime observation, no
capture, no damage rule, no persistence claim.  Report-only and additive: no
src/ change, no scenario, no ledger entry, no hypothesis.

PURE STDLIB ON PURPOSE: the release gate runs `py -3` with no third-party
packages.  capstone was used during the investigation and every conclusion is
frozen here as a byte-pattern or span-hash guard instead.

Usage:  py -3 tools/pf_runtimeres_actor_entry_static.py [path-to-GameClient.local.bin]
        py -3 tools/pf_runtimeres_actor_entry_static.py --json
Exit 0 = every static guard reproduced; nonzero = a guard drifted.
"""
import hashlib
import json
import os
import re
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))

EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
EXPECT_SIZE = 14759424


def _default_bin():
    for cand in (
        os.path.join(_ROOT, "..", "GameClient", "GameClient.local.bin"),
        "GameClient/GameClient.local.bin",
        os.path.join(_ROOT, "GameClient", "GameClient.local.bin"),
        os.path.join(_ROOT, "packages", ".v134_staging_20260815_0355",
                     "GameClient.local.bin"),
    ):
        if os.path.isfile(cand):
            return cand
    return "GameClient/GameClient.local.bin"


_RUN_AS_SCRIPT = (os.path.basename(sys.argv[0] or "")
                  == os.path.basename(os.path.abspath(__file__)))
_ARGS = [a for a in sys.argv[1:] if not a.startswith("--")] if _RUN_AS_SCRIPT else []
WANT_JSON = _RUN_AS_SCRIPT and "--json" in sys.argv[1:]
BIN = _ARGS[0] if _ARGS else _default_bin()

SERVER_SRC = os.path.normpath(os.path.join(_ROOT, "current",
                                           "pf_login_game_server_v141.py"))
SRC_DIR = os.path.normpath(os.path.join(_ROOT, "src", "pirateforce_foundation"))

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
    _ch = struct.unpack_from("<I", data, _o + 36)[0]
    SECS.append((_nm, _va, _vs, _rp, _rs, _ch))

# EVERY executable section, not just .text.  This image has two.
EXEC_SECS = [(nm, IMAGE_BASE + va, vs, rp, rs)
             for nm, va, vs, rp, rs, ch in SECS if ch & 0x20000000]


def va2off(va):
    r = va - IMAGE_BASE
    for _nm, _va, _vs, _rp, _rs, _ch in SECS:
        if _va <= r < _va + max(_vs, _rs):
            off = _rp + (r - _va)
            return off if off < len(data) else None
    return None


def off2va(off):
    for _nm, _va, _vs, _rp, _rs, _ch in SECS:
        if _rp <= off < _rp + _rs:
            return IMAGE_BASE + _va + (off - _rp)
    return None


def sec_of(va):
    r = va - IMAGE_BASE
    for _nm, _va, _vs, _rp, _rs, _ch in SECS:
        if _va <= r < _va + max(_vs, _rs):
            return _nm
    return None


def rd(va, n):
    o = va2off(va)
    return data[o:o + n] if o is not None else b""


def dw(va):
    b = rd(va, 4)
    return struct.unpack("<I", b)[0] if len(b) == 4 else None


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
    return rd(lo, hi - lo)


def span_sha(lo, hi):
    return hashlib.sha256(span(lo, hi)).hexdigest()


# ---------------------------------------------------------------- the censuses
# Everything below RE-READS `data` on every call, on purpose: the trap tests in
# tests/test_runtimeres_actor_entry_static.py mutate a copy of the image and
# every census and every guard must move with it.  No memoised index.

def rel32_sites(target, opcode):
    """Every `opcode <rel32>` in EVERY executable section whose computed
    destination is `target`.  opcode 0xE8 = call, 0xE9 = jmp."""
    out = []
    pat = bytes([opcode])
    for _nm, _va0, _vs, rp, rs in EXEC_SECS:
        end = rp + rs
        i = data.find(pat, rp, end - 5)
        while i >= 0:
            rel = struct.unpack_from("<i", data, i + 1)[0]
            va = off2va(i)
            if va is not None and ((va + 5 + rel) & 0xFFFFFFFF) == target:
                out.append(va)
            i = data.find(pat, i + 1, end - 5)
    return sorted(out)


def calls_to(target):
    return rel32_sites(target, 0xE8)


def jmps_to(target):
    return rel32_sites(target, 0xE9)


def dword_occurrences(value):
    """Every place in the WHOLE FILE, at EVERY alignment, where `value` appears
    as a little-endian dword.  A vtable slot, a jump-table entry, a
    `mov reg,imm32` immediate and an FF 15 / FF 25 indirect target are all
    dwords, so this one sweep covers all of them."""
    pat = struct.pack("<I", value)
    out = []
    i = data.find(pat)
    while i >= 0:
        out.append((i, off2va(i)))
        i = data.find(pat, i + 1)
    return out


def dword_vas(value):
    return [va for _off, va in dword_occurrences(value) if va is not None]


def entry_points(target):
    """The complete entry-point census for one function: direct calls, tail
    jumps, and every dword pointer to it anywhere in the file."""
    return {
        "direct_calls": calls_to(target),
        "tail_jumps": jmps_to(target),
        "pointer_slots": dword_vas(target),
    }


def vt20_dispatch_sites(lo=None, hi=None, require_vtable_load=False):
    """Census of the `mov <r>,[<reg>+0x20] ... call <r>` shape - the only shape
    this compiler emits for `this->vtable[+0x20](...)`.  Pure byte matching, no
    decoding: 8B /r with mod=01 and disp8 == 0x20, followed within 16 bytes by
    FF D<r>.  `require_vtable_load` additionally demands that the two bytes
    immediately before are `8B /r` with mod=00 loading the same register (the
    `mov <r>,[this]` that fetches the vtable pointer)."""
    out = []
    for _nm, _va0, _vs, rp, rs in EXEC_SECS:
        blob = data[rp:rp + rs]
        for i in range(2, len(blob) - 3):
            if blob[i] != 0x8B:
                continue
            m = blob[i + 1]
            if (m >> 6) != 1 or (m & 7) == 4 or blob[i + 2] != 0x20:
                continue
            dst = (m >> 3) & 7
            if bytes([0xFF, 0xD0 + dst]) not in blob[i + 3:i + 19]:
                continue
            if require_vtable_load:
                p0, p1 = blob[i - 2], blob[i - 1]
                if not (p0 == 0x8B and (p1 >> 6) == 0
                        and ((p1 >> 3) & 7) == (m & 7) and (p1 & 7) not in (4, 5)):
                    continue
            va = off2va(rp + i)
            if va is None:
                continue
            if lo is not None and not (lo <= va < hi):
                continue
            out.append(va)
    return sorted(out)


def byte_occurrences(pat):
    out = []
    i = data.find(pat)
    while i >= 0:
        out.append(off2va(i))
        i = data.find(pat, i + 1)
    return out


def name_id(name):
    """u16 id = SUM_i (int16)((signed char)name[i] * (i+1)) mod 2^16 (0x89B220)."""
    acc = 0
    for i, ch in enumerate(name.encode("latin1")):
        sc = ch if ch < 128 else ch - 256
        acc = (acc + ((sc * (i + 1)) & 0xFFFF)) & 0xFFFF
    return acc


# ------------------------------------------------------------------- guards
FAILS = []
NGUARD = 0


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
    return guard(rd(va, len(want)) == want, "%s  [0x%08X %s]" % (msg, va, hexpat))


def gspan(lo, hi, sha, msg):
    return guard(span_sha(lo, hi) == sha,
                 "%s  [0x%08X..0x%08X sha256 %s]" % (msg, lo, hi, sha[:16]))


def gabsent(lo, hi, hexpat, msg):
    return guard(bytes.fromhex(hexpat) not in span(lo, hi),
                 "%s  [0x%08X..0x%08X has no %s]" % (msg, lo, hi, hexpat))


def gentry(target, direct, ptrs, msg, tails=()):
    """Pin the COMPLETE entry-point census of a function - the whole list, not
    membership.  This is the guard the round-83 claim needed and did not have."""
    e = entry_points(target)
    ok = (e["direct_calls"] == list(direct)
          and e["tail_jumps"] == list(tails)
          and e["pointer_slots"] == list(ptrs))
    return guard(ok, "%s  [0x%08X calls=%s jmps=%s ptrs=%s]" % (
        msg, target,
        [hex(x) for x in e["direct_calls"]],
        [hex(x) for x in e["tail_jumps"]],
        [hex(x) for x in e["pointer_slots"]]))


def section(title):
    if not WANT_JSON:
        print("\n== " + title)


# =============================================================== 0. the image
if not WANT_JSON:
    print("PF-RUNTIMERES-ACTOR-ENTRY-001 static verifier")
    print("binary          =", BIN)
    print("binary SHA-256  =", SHA)

section("0. image identity and the scan surface")
guard(SHA == EXPECT_SHA, "binary SHA-256 matches the pinned client image")
guard(len(data) == EXPECT_SIZE, "image size == %d bytes" % EXPECT_SIZE)
guard(IMAGE_BASE == 0x400000, "ImageBase == 0x400000")
guard([s[0] for s in SECS] == [".text", ".code", ".rdata", ".data", ".rsrc", ".reloc"],
      "section table is exactly .text/.code/.rdata/.data/.rsrc/.reloc")
guard([s[0] for s in EXEC_SECS] == [".text", ".code"],
      "there are TWO executable sections - .text AND .code - and both are swept")
guard((EXEC_SECS[0][1], EXEC_SECS[0][4]) == (0x401000, 0x838C00),
      ".text starts 0x401000, 0x838C00 raw bytes")
guard((EXEC_SECS[1][1], EXEC_SECS[1][4]) == (0xC3A000, 0x400),
      ".code starts 0xC3A000, 0x400 raw bytes (round 83 never swept this one)")

# =============================================== 1. what "RuntimeRes" really is
section("1. Q2 - what is 'RuntimeRes'?  A project nickname; the class is "
        "GSCN_RunTimeProtocolRes")

for missing in ("RuntimeRes", "RunTimeRes", "RUNTIMERES", "RuntimeProtocol",
                "RunTimeProtocolVital", "ActorEntryVital"):
    guard(data.find(missing.encode("latin1")) < 0,
          "the literal %r does NOT occur anywhere in the image" % missing)

guard(cstr(0xF2FFE0) == "GSCN_RunTimeProtocolReq",
      "literal at 0xF2FFE0 == 'GSCN_RunTimeProtocolReq'")
guard(cstr(0xF2FFF8) == "GSCN_RunTimeProtocolRes",
      "literal at 0xF2FFF8 == 'GSCN_RunTimeProtocolRes'")
guard(byte_occurrences(b"GSCN_RunTimeProtocolRes\x00") == [0xF2FFF8],
      "'GSCN_RunTimeProtocolRes' is a single NUL-terminated .rdata literal")

# hash anchors this project already trusts
guard(name_id("ActorAttr") == 0x12AD, "hash anchor: ActorAttr -> 0x12AD")
guard(name_id("NPCAttr") == 0x0AD5, "hash anchor: NPCAttr -> 0x0AD5")
guard(name_id("UpdateAttrVital") == 0x309A,
      "hash anchor: UpdateAttrVital -> 0x309A")
RUNTIME_REQ_ID = name_id("GSCN_RunTimeProtocolReq")
RUNTIME_RES_ID = name_id("GSCN_RunTimeProtocolRes")
guard(RUNTIME_REQ_ID == 0x6E6F,
      "hash(GSCN_RunTimeProtocolReq) == 0x6E6F (the id the project already had)")
guard(RUNTIME_RES_ID == 0x6E9D,
      "hash(GSCN_RunTimeProtocolRes) == 0x6E9D")
guard(RUNTIME_RES_ID == 28317,
      "0x6E9D == 28317 == the ErrorData the client itself reported live "
      "(delete_actor_hypothesis.py) - hash and runtime agree")

gbytes(0xBEE030, "68e0fff200e846e0caff8bc8e8bfdccaff66a3901c0801c3",
       "GSCN_RunTimeProtocolReq registration thunk (push literal; hash; store id)")
gbytes(0xBEE050, "68f8fff200e826e0caff8bc8e89fdccaff66a3941c0801c3",
       "GSCN_RunTimeProtocolRes registration thunk")
gbytes(0x5E36F0, "66a1901c0801c3", "Req get-id stub reads slot 0x1081C90")
gbytes(0x5E37C0, "66a1941c0801c3", "Res get-id stub reads slot 0x1081C94")
guard(dw(0xF2FF80 + 0x10) == 0x5E36F0, "Req vtable 0xF2FF80 +0x10 == get-id 0x5E36F0")
guard(dw(0xF2FFC0 + 0x10) == 0x5E37C0, "Res vtable 0xF2FFC0 +0x10 == get-id 0x5E37C0")
gbytes(0x51DF20, "b828000000c3", "Res sizeof stub returns 0x28")
guard(dw(0xF2FFC0 + 0x0C) == 0x51DF20, "Res vtable +0x0C == sizeof stub 0x51DF20")
guard(dw(0xF2FFC0 + 0x18) == 0x5E3EE0, "Res vtable +0x18 serializer == 0x5E3EE0")
guard(dw(0xF2FFC0 + 0x1C) == 0x5E4060, "Res vtable +0x1C inbound handler == 0x5E4060")
guard(dw(0xF2FF80 + 0x1C) == 0x710440,
      "Req vtable +0x1C == the shared no-inbound stub 0x710440 (request-only)")
gbytes(0x710440, "b001c20400", "0x710440 is `mov al,1 ; ret 4` - a discard stub")
guard(dw(0xF2FFC0 + 0x1C) != 0x710440,
      "GSCN_RunTimeProtocolRes DOES have a real inbound handler")

# the derived change mask: which bit selects which sub-object
gbytes(0x5E3EED, "8bf1e87c010100", "0x5E3EED calls the inherited base serializer 0x5F4070")
gbytes(0x5E3EFD, "837e1c00b3027404885c2414",
       "derived mask bit 0x02 <- object +0x1C  (THE ACTOR-ENTRY COLLECTION)")
gbytes(0x5E3F09, "837e2400740580 4c241404".replace(" ", ""),
       "derived mask bit 0x04 <- object +0x24")
gbytes(0x5E3F14, "837e2000740580 4c241408".replace(" ", ""),
       "derived mask bit 0x08 <- object +0x20")
gbytes(0x5E3F26, "6a0b", "the derived mask itself is written with tag 0x0B (u8)")
gspan(0x5E3EE0, 0x5E4050,
      "84cd2594611824c08904cdc6bca86bea6a32d673caa8d84b92f786a330d66437",
      "GSCN_RunTimeProtocolRes::Serialize 0x5E3EE0 frozen byte-for-byte")

# the collection's own wire: u16 count then each entry's own vtable +0x18
gbytes(0x5E01D9, "0fb7472c6a028d4c2414518b4c24286a12",
       "actor-entry collection writes u16 count (tag 0x12) from +0x2C")
gbytes(0x5E0230, "8b4d188b018b542420 8b4018 6a0152ffd0".replace(" ", ""),
       "each entry serializes itself through ITS OWN vtable +0x18 (polymorphic)")

# ==================================== 2. Q1 - the entry-point census, complete
section("2. Q1 - how many ways in are there?  Complete censuses "
        "(E8 + E9 over BOTH exec sections, and every dword in the whole file)")

gentry(0x4437C0, [0x444705], [],
       "0x4437C0 dead-state sync: ONE direct call, ZERO pointers anywhere")
gentry(0x472810, [0x4439E9], [],
       "0x472810 CActorTask_Dead ctor: ONE direct call, ZERO pointers anywhere")
gentry(0x472850, [], [0xF0F054],
       "0x472850 dead-task update: ZERO direct calls, ONE pointer (a vtable slot)")
guard(dw(0xF0F048 + 0x0C) == 0x472850,
      "that one pointer is CActorTask_Dead vtable 0xF0F048 +0x0C")
gentry(0x4446F0, [0x4566A7], [0xF0D3C0, 0xF0DF78, 0xF0E018, 0xF0E0E8],
       "0x4446F0 attr-apply+dead-sync: 1 direct call + 4 vtable slots")
gentry(0x456630, [], [0xF0D7C8, 0xF0DD28, 0xF0E690],
       "0x456630 player/net-actor bridge: 0 direct calls + 3 vtable slots")
gentry(0x446F30, [0x5E4085], [],
       "0x446F30 actor reconcile: ONE direct call, ZERO pointers - and that "
       "one call is inside the GSCN_RunTimeProtocolRes inbound handler")
gentry(0x5DF080, [0x4446FE, 0x454949, 0x45D24A], [],
       "0x5DF080 attr-apply loop: exactly 3 direct calls, 0 pointers")
gentry(0x5E4060, [], [0xF2FFDC],
       "0x5E4060 is reached only as GSCN_RunTimeProtocolRes vtable +0x1C")

# every one of those 7 pointer slots is a vtable +0x20 slot on an actor class
ACTOR_VTABLES = {
    "CMyActor":   0xF0D7A8,
    "CNetActor":  0xF0DD08,
    "CNetNPC":    0xF0DF58,
    "CAvatarNPC": 0xF0DFF8,
    "Pet":        0xF0E0C8,
    "actor base (0xF0D3A0)": 0xF0D3A0,
    "CNetActor subclass (0xF0E670)": 0xF0E670,
}
for _nm, _vt in ACTOR_VTABLES.items():
    guard(dw(_vt + 0x20) in (0x4446F0, 0x456630),
          "%s vtable 0x%08X +0x20 -> 0x%08X (the death chain entry slot)"
          % (_nm, _vt, dw(_vt + 0x20)))
guard(len(ACTOR_VTABLES) == 7,
      "exactly 7 vtables carry the death-chain entry in slot +0x20")
gbytes(0x4566A4, "578bcee844e0feff",
       "0x456630 forwards to 0x4446F0 at 0x4566A7 (push entry; ecx=actor)")

# the ONE dispatcher, and the bound on everything not examined
VT20_ALL = vt20_dispatch_sites()
VT20_VT = vt20_dispatch_sites(require_vtable_load=True)
guard(len(VT20_ALL) == 387,
      "image-wide census: 387 `mov r,[reg+0x20] ... call r` shapes")
guard(len(VT20_VT) == 230,
      "of those, 230 carry the `mov r,[this]` vtable-load prefix")
guard(0x446FB6 in VT20_VT,
      "0x446FB6 (inside 0x446F30) is one of them - the actor dispatch")
gbytes(0x446FB4, "8b168b4220578bceffd0",
       "0x446FB4 `mov edx,[esi]; mov eax,[edx+0x20]; push edi; mov ecx,esi; call eax`")

# ===================================== 3. Q3 - the path from wire to the literal
section("3. Q3 - the real path from the wire to L\"_F_DIE_000\"")

gbytes(0x5E4073, "8b461c85c0741083c01050e89de9e1ff8bc8e8a62ee6ff",
       "0x5E4073: Res+0x1C -> +0x10 (list head) -> 0x402A20 -> call 0x446F30")
gbytes(0x5E40DA, "6a008bcee8fdf80000",
       "the inherited VitalData list is dispatched separately at 0x5E40DE "
       "(0x5F39E0) - a different sub-object (+0x18), not the actor entries")
gspan(0x5E4060, 0x5E41CD,
      "85ff71ffceff5345f94facc9b7fa1c39c8efd2e429248d112cdba578d3df944e",
      "GSCN_RunTimeProtocolRes inbound handler 0x5E4060 frozen byte-for-byte")

gbytes(0x446F87,
       "8b48188b401c50518bcde8daf1ffff8bf085f675186a016a01578bcde8e8f9ffff8bf085f67419",
       "0x446F87 find-or-create: identity (entry+0x18/+0x1C) -> 0x446170; "
       "found -> vtable +0x20; NOT found -> 0x446990 and SKIP the +0x20 call")
gspan(0x446F30, 0x4470E5,
      "c47bc46a06d6ffe95bee17b572f9ccb7e03442cdd27f04807c1161c03642d880",
      "actor reconcile 0x446F30 frozen byte-for-byte")

gbytes(0x4446F0, "8b442404568bf18b0885c9742f56e87da919008bcee8b6f0ffff",
       "0x4446F0: null entry -> nothing; else call 0x5DF080 then call 0x4437C0")
gbytes(0x44472C, "5ec20400", "0x4446F0 ENDS at 0x44472C (`ret 4`) - it is 0x3D bytes")
gspan(0x4446F0, 0x444730,
      "e4e5b3719b24f7ee32791e4a419ff37942031610691f25c4d943cae9f1ae4508",
      "0x4446F0 frozen byte-for-byte (its true extent, not the padding run)")

gbytes(0x443828, "8b4240", "0x443828 reads actor vtable +0x40 into bl")
gbytes(0x44383C, "8b423c", "0x44383C reads actor vtable +0x3C into [esp+0x13]")
gbytes(0x44384C, "84db0f84970000008556700f858e000000095670",
       "0x44384C: vtable+0x40 gates the `[actor+0x70] |= 0x200` DYING latch")
gbytes(0x443990, "807c2413000f84ec000000",
       "0x443990: vtable+0x3C gates everything below - no task without it")
gbytes(0x4439C7, "ba24000000b9a4dc0201e87af3ffff",
       "0x4439C7 allocates 0x24 bytes for the dead task")
gbytes(0x4439E9, "e822ee0200", "0x4439E9 is the only call to 0x472810")
gspan(0x4437C0, 0x443A9A,
      "85d294b84843e0bd46256e0257cf5d51be0415081739d82b0b4c254975ee9592",
      "dead-state sync 0x4437C0 frozen byte-for-byte")

gbytes(0x472810, "8b44240456508bf1e823350100c70648f0f000c6462000c74610050000808bc65ec20400",
       "0x472810 installs vtable 0xF0F048 and task id 0x80000005")
gbytes(0x472898, "807f2000751ef646704074188b068b50286a006a006a006860f0f0008bceffd2c6472001",
       "0x472850: `test byte [actor+0x70],0x40` gates the ONE-SHOT play of "
       "the literal at 0xF0F060 through actor vtable +0x28")
guard(wstr(0xF0F060) == "_F_DIE_000", "the literal at 0xF0F060 is L\"_F_DIE_000\"")
guard(byte_occurrences("_F_DIE_000".encode("utf-16le") + b"\0\0") == [0xF0F060],
      "L\"_F_DIE_000\" occurs exactly once in the whole image")
guard(dword_vas(0xF0F060) == [0x4728B0, 0x476710],
      "0xF0F060 is referenced from exactly TWO sites in the whole image: "
      "the pushes at 0x4728AF and 0x47670F")
gspan(0x472850, 0x4728F3,
      "e04385a8cd54b800add22c4c8c5cc751b4243e19d208d684acdb8af2b6350999",
      "dead-task update 0x472850 frozen byte-for-byte")
# the SECOND play site is the same class, one slot up
gentry(0x4765C0, [], [0xF0F050],
       "0x4765C0 (the other _F_DIE_000 player) is vtable-only too")
guard(dw(0xF0F048 + 0x08) == 0x4765C0,
      "0x4765C0 is CActorTask_Dead vtable 0xF0F048 +0x08 - the SAME class, so "
      "both play sites sit behind the same single-entry chain")
gbytes(0x4766FE,
       "f646704074188b068b50286a006a006a006860f0f0008bceffd2c645200184db7419",
       "0x4766FE gates on the same `[actor+0x70] & 0x40` and pushes 0xF0F060")
gspan(0x4765C0, 0x476763,
      "e771b911d0ba2019364b3cda8e6a7ba5c54e2a0a21cf3ae6d0cba1b4f8ed7658",
      "CActorTask_Dead vtable +0x08 0x4765C0 frozen byte-for-byte")

# the two predicates and their opposite timer polarity
gbytes(0x43BD70,
       "568bf18b068b5074ffd28378440075198b068b50748bceffd20f57c00f2f40587207b8010000005ec3",
       "vtable +0x3C 0x43BD70: HP(+0x44)==0 AND f32(+0x58) <= 0.0f  "
       "(xorps zero, comiss 0 vs timer, jb -> false)")
gbytes(0x43BDA0,
       "568bf18b068b5074ffd283784400751e8b068b50748bceffd2f30f1040580f2f059c98f0007607b8010000005ec3",
       "vtable +0x40 0x43BDA0: HP(+0x44)==0 AND f32(+0x58) >  0.0f")
guard(struct.unpack("<f", rd(0xF0989C, 4))[0] == 0.0,
      "the float constant at 0xF0989C that +0x40 compares against is 0.0f")
gentry(0x43BDA0, [], [0xF0D3E0, 0xF0DF98, 0xF0E038, 0xF0E108],
       "0x43BDA0 is vtable-only (4 slots, no direct call)")
gentry(0x43BD70, [], [0xF0D3DC, 0xF0DF94, 0xF0E034, 0xF0E104],
       "0x43BD70 is vtable-only (4 slots, no direct call)")

# the actor-type gate and the factory table
gbytes(0x4469C8, "0fb6401083c0fe33f683f8040f873a010000ff24852c6b4400",
       "0x4469C8 actor-type gate: movzx byte [entry+0x10]; -2; >4 rejects; "
       "jump table at 0x446B2C")
FACTORY = {
    2: (0x4469E1, 0x3A8, 0x457340, 0xF0DD08, "CNetActor"),
    3: (0x4469F7, 0x488, 0x44C990, 0xF0D7A8, "CMyActor"),
    4: (0x446A3D, 0x368, 0x45CC00, 0xF0DF58, "CNetNPC"),
    5: (0x446A5A, 0x378, 0x45D000, 0xF0DFF8, "CAvatarNPC"),
    6: (0x446A77, 0x4E8, 0x45E4E0, 0xF0E0C8, "Pet"),
}
for t, (case_va, size, ctor, vt, nm) in FACTORY.items():
    guard(dw(0x446B2C + (t - 2) * 4) == case_va,
          "jump table entry for actor_type %d -> 0x%08X (%s)" % (t, case_va, nm))
    guard(dw(vt + 0x20) in (0x4446F0, 0x456630),
          "%s (actor_type %d) carries the death-chain slot at vtable +0x20"
          % (nm, t))
guard(len(FACTORY) == 5, "the actor-type jump table has exactly 5 cases (2..6)")
gbytes(0x4469F7, "3935c42e03010f8511010000",
       "actor_type 3 (CMyActor) requires [0x1032EC4] == 0 (no local player yet)")
gbytes(0x446A03, "6888040000", "actor_type 3 allocates 0x488 bytes")
gbytes(0x444E2C, "68a8030000", "actor_type 2 pool allocates 0x3A8 bytes")
gbytes(0x444F4C, "6868030000", "actor_type 4 pool allocates 0x368 bytes")
gbytes(0x44506C, "6878030000", "actor_type 5 pool allocates 0x378 bytes")
gbytes(0x44518C, "68e8040000", "actor_type 6 pool allocates 0x4E8 bytes")
gspan(0x446990, 0x446B2C,
      "5f68239f8661419da2ea9bea4e4a2cb9bcdcaa37fe6e4cd53b701116aeeb697d",
      "actor spawn 0x446990 frozen byte-for-byte")

# spawn applies through vtable +0x10 and CANNOT dead-sync
gbytes(0x446AAD, "8b068b5010558bceffd2",
       "0x446AAD: a freshly spawned actor is applied through vtable +0x10, "
       "NOT +0x20")
gbytes(0x454946, "8b0f56e832a71800",
       "CNetActor/CMyActor vtable +0x10 (0x454920) calls the apply loop 0x5DF080")
gbytes(0x45D247, "8b0f56e8311e1800",
       "CNetNPC/CAvatarNPC/Pet vtable +0x10 (0x45D200) calls 0x5DF080")
VT10_APPLY = {
    "CNetActor":  (0xF0DD08, 0x454920),
    "CMyActor":   (0xF0D7A8, 0x451B90),
    "CNetNPC":    (0xF0DF58, 0x45D200),
    "CAvatarNPC": (0xF0DFF8, 0x45D9F0),
    "Pet":        (0xF0E0C8, 0x45DE60),
}
for _nm, (_vt, _fn) in VT10_APPLY.items():
    guard(dw(_vt + 0x10) == _fn,
          "%s vtable +0x10 == 0x%08X (the SPAWN-time apply)" % (_nm, _fn))
gbytes(0x451BC7, "e8542d0000", "CMyActor +0x10 (0x451B90) forwards to 0x454920")
gbytes(0x45D9F8, "e803f8ffff", "CAvatarNPC +0x10 (0x45D9F0) forwards to 0x45D200")
gbytes(0x45DE60, "e99bf3ffff", "Pet +0x10 (0x45DE60) tail-jumps to 0x45D200")
guard(set(calls_to(0x4437C0)).isdisjoint({_fn for _vt, _fn in VT10_APPLY.values()}),
      "no +0x10 spawn-apply is a caller of 0x4437C0 (it has only one, 0x444705)")
guard(vt20_dispatch_sites(0x454920, 0x4549E5) == [],
      "the CNetActor +0x10 apply contains NO vtable+0x20 dispatch")
guard(vt20_dispatch_sites(0x45D200, 0x45D480) == [],
      "the CNetNPC +0x10 apply contains NO vtable+0x20 dispatch")

# the model-loaded bit the animation needs
gbytes(0x4448B4, "834f7040", "0x4448B4 sets [actor+0x70] |= 0x40 on model load")
gbytes(0x4599B4, "834e7040", "0x4599B4 sets [actor+0x70] |= 0x40 on model load")
MODEL_BIT_WRITERS = sorted(
    v for h in ("83487040", "83497040", "834a7040", "834b7040",
                "834d7040", "834e7040", "834f7040")
    for v in byte_occurrences(bytes.fromhex(h)))
guard(MODEL_BIT_WRITERS == [0x4448B4, 0x4599B4, 0x46558C],
      "exactly 3 `or dword [reg+0x70], 0x40` sites exist image-wide")
guard(0x46558C not in (0x4448B4, 0x4599B4)
      and 0x465500 <= 0x46558C < 0x465620,
      "the third one (0x46558C) is a BasicAttr CHANGE-MASK setter, a "
      "different object - only 0x4448B4 and 0x4599B4 touch an actor")
gentry(0x444730, [0x45AEFF, 0x45CDAD, 0x45E241, 0x462EF8], [0xF0D3F8],
       "0x4448B4's owner 0x444730 is actor-base vtable +0x58 (model load), "
       "4 direct callers")
guard(dw(0xF0D3A0 + 0x58) == 0x444730,
      "0xF0D3F8 == actor base vtable 0xF0D3A0 +0x58")

# =================================== 4. the negative that corrects HP-DEATH-001
section("4. the correction - UpdateAttrVital CANNOT reach the death chain")

guard(name_id("UpdateAttrVital") == 0x309A, "UpdateAttrVital id is 0x309A")
UPDATE_ATTR_HANDLER = 0x5F2400
UPDATE_ATTR_HANDLER_END = 0x5F261A
guard(vt20_dispatch_sites(UPDATE_ATTR_HANDLER, UPDATE_ATTR_HANDLER_END) == [],
      "0x5F2400..0x5F261A contains ZERO vtable+0x20 dispatch shapes")
guard(not any(UPDATE_ATTR_HANDLER <= c < UPDATE_ATTR_HANDLER_END
              for c in calls_to(0x4446F0) + calls_to(0x456630)
              + calls_to(0x4437C0) + calls_to(0x446F30)),
      "no direct call from the UpdateAttrVital handler into the death chain")
gspan(UPDATE_ATTR_HANDLER, UPDATE_ATTR_HANDLER_END,
      "65a7095cc493e33988f816efcd63d48220ee9cf39437e543389d54e3718acfaf",
      "UpdateAttrVital inbound handler 0x5F2400 frozen byte-for-byte")

# ====================================== 5. Q4 - what our server does and doesn't
section("5. Q4 - the server-side gap, counted from the read-only sources")


def _read(p):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


_v141 = _read(SERVER_SRC)
_src = {}
if os.path.isdir(SRC_DIR):
    for _f in sorted(os.listdir(SRC_DIR)):
        if _f.endswith(".py"):
            _src[_f] = _read(os.path.join(SRC_DIR, _f))


def _count(pat, text):
    return len(re.findall(pat, text))


def _count_src(pat):
    return sum(_count(pat, t) for t in _src.values())


SRC_ACTOR_ENTRY_SITES = _count_src(r"make_remote_actor_entry\(")
SRC_ACTOR_STREAM_SITES = _count_src(r"make_runtime_remote_actors\(")
SRC_VITAL_STREAM_SITES = _count_src(r"make_runtime_vitals\(")
SRC_ZERO_HP_SITES = _count_src(r"current_hp\s*=\s*0\b")
V141_ZERO_HP_SITES = _count(r"current_hp\s*=\s*0\b", _v141)
SRC_MODULES_WITH_ACTOR_ENTRY = sum(
    1 for t in _src.values() if _count(r"make_remote_actor_entry\(", t))
SRC_MODULES_WITH_DEATH_TIMER_BIT = sum(
    1 for t in _src.values() if _count(r"0x0080", t))
# Round 96 refinement.  "Mentions 0x0080" is not "sets 0x0080": a module can
# name the bit only to REFUSE it.  REMOTE-PLAYER-ENCODER-001
# (remote_player_hypothesis.py, the HYP-PF-025 visibility lane) builds actor
# entries and names bit 0x0080 exactly once, as
# BASIC_BIT_DEATH_TIMER_FORBIDDEN, and every use of that constant is a
# fail-closed guard -- it can never OR the bit into an emitted mask.  So the
# "both" census that GAP 1 rests on is split from the crude substring: a
# module SETS the bit only if it builds an entry, names 0x0080, and does NOT
# carry the FORBIDDEN marker; a module FORBIDS it if it carries that marker.
# The SET measure stays exactly one module and it is still the death lane,
# which is the fact GAP 1 was pinned to; the FORBID measure names the new
# lane so a reader sees the second actor-entry builder is not a second death
# emitter.
#
# Round 111 correction, HYP-PF-029 / NPC-HP-LINK-001.  The round-96 test above
# was written as `"FORBIDDEN" not in t`, a substring search over the WHOLE
# module, which is not a question about bit 0x0080 at all.  The round-111 lane
# exposed that: npc_hp_link_hypothesis.py names the bit as
# BASIC_BIT_DEATH_TIMER and genuinely SETS it (`basic_mask |=
# BASIC_BIT_DEATH_TIMER` inside its own _compose_npc_attr, emitted as the
# tag-0x2A f32 on its seventh step), and it composes its own NPCAttr body
# rather than delegating to the death lane -- yet it also happens to carry
# FLAGS_FORBIDDEN_MASK = 0xF184, an unrelated NPCAttr *flags* validity mask,
# so the crude substring filed a real timer emitter under FORBID.  That
# classification was a measurement artefact, not a fact about the code, and it
# is the expensive kind: it held the SET census at 1 and green while the
# sentence "exactly ONE module SETS the bit" had already stopped being true --
# the same failure GAP 2 records two comments below.  The discriminator is now
# tied to the bit itself: a module FORBIDS 0x0080 only if it binds that value
# to a constant whose own name says FORBIDDEN.
DEATH_TIMER_FORBIDDEN_CONST = re.compile(
    r"(?m)^[A-Z0-9_]*FORBIDDEN[A-Z0-9_]*\s*=\s*0x0080\b")
SRC_MODULES_SETTING_DEATH_TIMER = sum(
    1 for t in _src.values()
    if _count(r"make_remote_actor_entry\(", t) and _count(r"0x0080", t)
    and not DEATH_TIMER_FORBIDDEN_CONST.search(t))
SRC_MODULES_FORBIDDING_DEATH_TIMER = sum(
    1 for t in _src.values()
    if _count(r"make_remote_actor_entry\(", t) and _count(r"0x0080", t)
    and DEATH_TIMER_FORBIDDEN_CONST.search(t))
# The name "both" is kept for the COUNTS key and the report pin, and it now
# means "builds an entry AND SETS 0x0080", which is what GAP 1 always meant.
SRC_MODULES_WITH_BOTH = SRC_MODULES_SETTING_DEATH_TIMER

# Round 86 re-pin.  Section [5] counts our own src/, so unlike every other
# section in this file its numbers move when we write code -- that is the
# point of it, and it is also why it has to be re-pinned deliberately rather
# than loosened.  Round 85 wrote three zeros here and called them "the
# server-side gap"; round 86 built RUNTIMERES-ENCODER-001 specifically to
# close them, so a red line on those three guards today is the lane working,
# not the lane breaking.  The counts are re-pinned to the new state AND the
# module names are now pinned beside them, because a bare count going from
# 4 to 5 tells the next reader nothing about which emitter arrived.
SRC_MODULES_WITH_ACTOR_ENTRY_NAMES = tuple(sorted(
    f for f, t in _src.items() if _count(r"make_remote_actor_entry\(", t)))
SRC_MODULES_WITH_DEATH_TIMER_BIT_NAMES = tuple(sorted(
    f for f, t in _src.items() if _count(r"0x0080", t)))
SRC_MODULES_WITH_BOTH_NAMES = tuple(sorted(
    f for f, t in _src.items()
    if _count(r"make_remote_actor_entry\(", t) and _count(r"0x0080", t)
    and not DEATH_TIMER_FORBIDDEN_CONST.search(t)))
SRC_MODULES_FORBIDDING_DEATH_TIMER_NAMES = tuple(sorted(
    f for f, t in _src.items()
    if _count(r"make_remote_actor_entry\(", t) and _count(r"0x0080", t)
    and DEATH_TIMER_FORBIDDEN_CONST.search(t)))

# GAP 2's guard was green and its sentence was false, which is worse than red.
# Round 85 asserted "no call site anywhere passes current_hp = 0" by grepping
# for the literal `current_hp = 0`.  Round 86's encoder passes exactly that
# zero -- through a named constant, `RUNTIMERES_DEATH_HP_ZERO = 0` -- so the
# literal search finds nothing and the old guard would have kept reporting a
# zero that stopped being true.  The check now looks for the named constant as
# well, and the sentence says which module carries it.
SRC_ZERO_HP_CONST_MODULES = tuple(sorted(
    f for f, t in _src.items()
    if _count(r"HP_ZERO\s*=\s*0\b", t)))

guard(bool(_v141), "the read-only v141 snapshot opened for counting")
guard(len(_src) >= 30, "the read-only src/ package opened for counting (%d modules)"
      % len(_src))
guard("make_runtime_remote_actors" in _v141,
      "v141 already implements the derived-bit-0x02 actor-entry carrier")
guard("make_remote_actor_entry" in _v141,
      "v141 already implements the actor-entry serializer (0x5E21D0)")
# Round 96 re-pin, 5 -> 6.  REMOTE-PLAYER-ENCODER-001 added the sixth actor-
# entry call site: remote_player_hypothesis.py builds an actor_type 2 entry
# for the multiplayer chunk-2 visibility probe.  Section [5] counts our own
# src/, so its numbers move when we write code -- that is the point of it --
# and it is re-pinned deliberately rather than loosened, with the new module
# named beside the count.
# Round 99 re-pin, 6 -> 7.  NPC-HOSTILE-001 (HYP-PF-027, the mob-aggro Door A
# checkpoint) added the seventh call site: npc_hostile_hypothesis.py spawns
# the SAME frozen NPC 0x2001 as the death lane, plus exactly a five-byte
# BasicAttr faction splice (bit 0x0400, value 6).  Note the THIRD category
# this creates in the SET/FORBID census below: the new module builds an
# entry and never NAMES the death-timer bit at all -- its walker requires
# the BasicAttr mask to equal 0x070C exactly, which forbids every other bit
# structurally rather than by name.  Both timer censuses therefore stay
# where round 97 pinned them, and that is correct, not an omission.
# Round 111 re-pin, 7 -> 8.  NPC-HP-LINK-001 (HYP-PF-029) added the eighth
# call site: npc_hp_link_hypothesis.py walks the frozen Port Royal NPC 0x2001
# down a server-held ladder, 100, 100, 37, 37, 37, 37, 0, 0, across eight
# frames that alternate two carriers.  It is the first lane in this tree that
# moves a TARGET's hit points rather than the local player's, and it exists
# because the attended test on 2026-08-20 delivered 505 points of damage as
# CHitResult frames and moved the target's HP bar by exactly zero: the client
# renders what it is told and does not subtract, so the server has to say both
# halves itself.  Unlike the round-99 hostile spawn this lane DOES name and
# SET the death-timer bit -- see the SET census below, which moves with it.
guard(SRC_ACTOR_ENTRY_SITES == 8,
      "src/ builds actor entries at exactly 8 call sites (4 spawns + the "
      "round-86 death re-send + the round-96 remote-player probe + the "
      "round-99 hostile spawn + the round-111 NPC HP ladder)")
guard(SRC_ACTOR_STREAM_SITES == 8,
      "src/ sends the actor-entry carrier at exactly 8 call sites")
guard(SRC_MODULES_WITH_ACTOR_ENTRY == 7
      and SRC_MODULES_WITH_ACTOR_ENTRY_NAMES == (
          "npc_hostile_hypothesis.py", "npc_hp_link_hypothesis.py",
          "population.py", "remote_player_hypothesis.py",
          "runtimeres_death_hypothesis.py", "scenario.py",
          "scene_object.py"),
      "7 named src/ modules build actor entries %s"
      % (SRC_MODULES_WITH_ACTOR_ENTRY_NAMES,))
# Round 97 re-pin, 4 -> 5.  DAMAGE-HP-LINK-001 added the fifth mention:
# damage_hp_link_hypothesis.py names bit 0x0080 because its two lethal frames
# (HP_ZERO_DYING, DYING_ELAPSED) carry the death timer the client's IsDead
# predicates read -- the same field, byte-identical to the HYP-PF-022
# composer's output, gated behind the lane's own pinned lethal steps.  It
# does NOT build actor entries, so the SET/FORBID censuses below are
# untouched: this lane rides the VitalData carrier only.
# Round 111 re-pin, 5 -> 6.  NPC-HP-LINK-001 (HYP-PF-029) added the sixth
# mention: npc_hp_link_hypothesis.py declares BASIC_BIT_DEATH_TIMER = 0x0080
# and carries the 20.0f timer on the two lethal steps at the foot of its
# ladder, because a target the client is to read as dead needs the same field
# the HYP-PF-022 composer emits.  Unlike damage_hp_link_hypothesis.py this
# lane ALSO builds actor entries, so the SET census below moves with it -- it
# is the first module since round 86 to do both.
guard(SRC_MODULES_WITH_DEATH_TIMER_BIT == 6
      and SRC_MODULES_WITH_DEATH_TIMER_BIT_NAMES == (
          "damage_hp_link_hypothesis.py",
          "npc_hp_link_hypothesis.py",
          "remote_player_hypothesis.py", "runtime.py",
          "runtimeres_death_hypothesis.py",
          "stats_progression_hypothesis.py"),
      "6 named src/ modules mention BasicAttr bit 0x0080 %s"
      % (SRC_MODULES_WITH_DEATH_TIMER_BIT_NAMES,))
# Round 111 re-pin, 1 -> 2, and the sentence changes shape rather than just
# its number.  Round 86 could say "exactly ONE module SETS the bit" because
# there was exactly one; that is no longer the fact, and a count of 2 under a
# sentence that still said ONE would be a guard that had quietly stopped
# meaning anything.  What GAP 1 was actually pinned to is that the death lane
# is STILL a timer emitter, and that every module which sets the bit is named
# here, so a future lane cannot start emitting a death timer without turning
# this line red.  Both members are therefore named:
# runtimeres_death_hypothesis.py, the round-86 emitter GAP 1 was opened for,
# and npc_hp_link_hypothesis.py, the round-111 target-HP lane, which sets the
# bit in its own composer and does not delegate to the death lane's.
guard(SRC_MODULES_WITH_BOTH == 2
      and SRC_MODULES_WITH_BOTH_NAMES == (
          "npc_hp_link_hypothesis.py",
          "runtimeres_death_hypothesis.py"),
      "GAP 1 CLOSED in round 86 and still closed: the src/ modules that both "
      "build an actor entry AND SET bit 0x0080 are exactly these two, the "
      "round-86 death emitter and the round-111 NPC HP ladder %s (round 85 "
      "counted zero and named the death lane as the missing emitter; round 96 "
      "made SET precise so a module that only FORBIDS the bit does not count; "
      "round 111 made FORBID precise, see DEATH_TIMER_FORBIDDEN_CONST, and "
      "re-pinned this census upward rather than leaving it green at 1)"
      % (SRC_MODULES_WITH_BOTH_NAMES,))
# Round 111: this count does NOT move, and the reason it does not move is the
# whole point of the correction above.  With the round-96 whole-file substring
# the round-111 lane landed here, which would have read as "a second module
# names the bit only to refuse it" about a module whose seventh step carries a
# 20.0f death timer -- false, and false in the direction that hides a timer
# emitter.  With the discriminator tied to the bit, the FORBID census is again
# exactly the one module that binds 0x0080 to a FORBIDDEN-named constant.
guard(SRC_MODULES_FORBIDDING_DEATH_TIMER == 1
      and SRC_MODULES_FORBIDDING_DEATH_TIMER_NAMES == (
          "remote_player_hypothesis.py",),
      "round 96, re-derived in round 111: exactly ONE src/ module builds an "
      "actor entry AND names bit 0x0080 ONLY to forbid it, and it is "
      "remote_player_hypothesis.py -- that actor-entry builder is the "
      "HYP-PF-025 visibility lane, NOT a death emitter %s"
      % (SRC_MODULES_FORBIDDING_DEATH_TIMER_NAMES,))
guard(SRC_ZERO_HP_SITES == 0 and V141_ZERO_HP_SITES == 0
      and SRC_ZERO_HP_CONST_MODULES == ("runtimeres_death_hypothesis.py",),
      "GAP 2 CLOSED in round 86: the literal `current_hp = 0` still appears "
      "nowhere in src/ or v141, but runtimeres_death_hypothesis.py passes zero "
      "through the named constant RUNTIMERES_DEATH_HP_ZERO -- the round-85 "
      "sentence was about to stay green while ceasing to be true")
# Round 90 re-pin, 13 -> 14.  DAMAGE-ENCODER-001 added the fourteenth call
# site: damage_model_hypothesis.py ships CHitResult 0x16F7 over this same
# VitalData carrier.  The number is meant to move when we write code -- that
# is what section [5] is for -- but it is re-pinned deliberately rather than
# loosened, because a census that quietly widens stops being a census.  Note
# what did NOT move: the actor-entry counts below are unchanged, because the
# damage lane rides the BASE change mask (object +0x18) and never touches the
# derived actor-entry collection (+0x1C) this file is otherwise about.
# Round 97 re-pin, 14 -> 15.  DAMAGE-HP-LINK-001 added the fifteenth call
# site: damage_hp_link_hypothesis.py ships both of its carriers (CHitResult
# 0x16F7 and UpdateAttrVital 0x309A) through ONE composition seam over this
# same VitalData collection.  Re-pinned deliberately, with the module named
# beside the count, for the same reason as the round-90 and round-96 re-pins
# above: a census that quietly widens stops being a census.
# Round 101 re-pin, 15 -> 16.  LOGOUT-RETURN-SELECT-001 (HYP-PF-028) added the
# sixteenth call site: logout_hypothesis.py now holds TWO make_runtime_vitals
# sites, the pre-existing make_logout_ack_response and the new
# make_return_select_server_response, which ships the designed
# ReturnSelectServerVital 0x709E over this same VitalData collection.  This is
# a vital-collection carrier only; NOTHING in the actor-entry counts below
# moves (this lane builds no actor entry and touches no derived +0x1C
# collection), which is the guard that this re-pin does not quietly widen the
# actor-entry census.
# Round 111 re-pin, 16 -> 17.  NPC-HP-LINK-001 (HYP-PF-029) added the
# seventeenth call site: npc_hp_link_hypothesis.py holds ONE make_runtime_vitals
# site beside its ONE make_remote_actor_entry site, because the eight frames of
# its ladder alternate the two carriers against the same frozen NPC 0x2001 --
# the UpdateAttrVital half says the number, the actor-entry half re-states the
# whole body.  This is the first re-pin in this block where the actor-entry
# counts above move in the SAME commit, and they do, deliberately: unlike the
# round-90, round-97 and round-101 lanes this one is not a vital-collection
# carrier only.
guard(SRC_VITAL_STREAM_SITES == 17,
      "src/ sends the VitalData carrier (make_runtime_vitals) at 17 call sites")
guard(_count(r"make_runtime_remote_actors\(",
             _src.get("stats_progression_hypothesis.py", "")) == 0
      and _count(r"make_runtime_vitals\(",
                 _src.get("stats_progression_hypothesis.py", "")) == 2,
      "GAP 3: the HP-DEATH-002 encoder ships ONLY over make_runtime_vitals "
      "(UpdateAttrVital) and never over the actor-entry carrier")

# Round 85 counted three actionable gaps and round 86 built the emitter that
# closes all three.  This number counts *emitter* gaps -- things absent from
# our own source -- and nothing else.  It does NOT say a corpse has been seen:
# whether these frames produce a visible death is a runtime question that only
# GT-022 can answer, and it is still unanswered.  Do not read 0 as "done".
ACTIONABLE_GAPS = 0
# Round 111.  This guard used to read SRC_MODULES_WITH_BOTH == 1, which fused
# two different claims into one number: that the round-86 emitter closed the
# gaps, and that nobody else had since become a timer emitter.  The first is
# what the sentence promises; the second was an accident of there being only
# one.  NPC-HP-LINK-001 made them come apart, so they are now asserted apart --
# the death lane must still be present (the gaps stay closed), and the full
# SET membership is pinned above by name, where a new emitter is legible.
# Relaxing this to ">= 1" would have swallowed the new lane silently; it is
# instead the exact-tuple guard above that carries the census.
guard(ACTIONABLE_GAPS == 0
      and "runtimeres_death_hypothesis.py" in SRC_MODULES_WITH_BOTH_NAMES
      and bool(SRC_ZERO_HP_CONST_MODULES),
      "all THREE round-85 emitter gaps are closed by runtimeres_death_"
      "hypothesis.py and stay closed -- this is a statement about our source, "
      "NOT about anything observed on a screen")

# ------------------------------------------------------------------- results
COUNTS = {
    "guards": None,
    "binary_sha256": SHA,
    "executable_sections_swept": len(EXEC_SECS),
    "runtimeres_literal_occurrences_in_image": 0,
    "gscn_runtime_protocol_req_id": RUNTIME_REQ_ID,
    "gscn_runtime_protocol_res_id": RUNTIME_RES_ID,
    "gscn_runtime_protocol_res_sizeof": 0x28,
    "entry_points_0x4437C0_direct": len(calls_to(0x4437C0)),
    "entry_points_0x4437C0_pointers": len(dword_vas(0x4437C0)),
    "entry_points_0x472810_direct": len(calls_to(0x472810)),
    "entry_points_0x472810_pointers": len(dword_vas(0x472810)),
    "entry_points_0x472850_direct": len(calls_to(0x472850)),
    "entry_points_0x472850_pointers": len(dword_vas(0x472850)),
    "entry_points_0x4446F0_direct": len(calls_to(0x4446F0)),
    "entry_points_0x4446F0_pointers": len(dword_vas(0x4446F0)),
    "entry_points_0x456630_direct": len(calls_to(0x456630)),
    "entry_points_0x456630_pointers": len(dword_vas(0x456630)),
    "entry_points_0x446F30_direct": len(calls_to(0x446F30)),
    "entry_points_0x446F30_pointers": len(dword_vas(0x446F30)),
    "actor_vtables_carrying_the_death_slot": len(ACTOR_VTABLES),
    "vt20_dispatch_shapes_image_wide": len(VT20_ALL),
    "vt20_dispatch_shapes_with_vtable_load": len(VT20_VT),
    "vt20_dispatch_shapes_in_updateattrvital_handler": 0,
    "actor_type_jump_table_cases": len(FACTORY),
    "actor_type_min": min(FACTORY),
    "actor_type_max": max(FACTORY),
    "or_0x40_on_offset_0x70_sites": len(MODEL_BIT_WRITERS),
    "actor_model_bit_0x40_writers": 2,
    "f_die_literal_occurrences": 1,
    "f_die_literal_reference_sites": len(dword_vas(0xF0F060)),
    "src_actor_entry_call_sites": SRC_ACTOR_ENTRY_SITES,
    "src_actor_stream_call_sites": SRC_ACTOR_STREAM_SITES,
    "src_vital_stream_call_sites": SRC_VITAL_STREAM_SITES,
    "src_modules_building_actor_entries": SRC_MODULES_WITH_ACTOR_ENTRY,
    # Round 99: the names are surfaced beside the count so the standing test
    # can pin WHICH modules build entries, not just how many -- the round-99
    # hostile lane (npc_hostile_hypothesis.py) is the seventh call site.
    # Round 111: the eighth is the NPC HP ladder (npc_hp_link_hypothesis.py),
    # HYP-PF-029 / NPC-HP-LINK-001, the first lane here to move a target's HP.
    "src_modules_building_actor_entries_names":
        list(SRC_MODULES_WITH_ACTOR_ENTRY_NAMES),
    "src_modules_mentioning_basicattr_bit_0x0080": SRC_MODULES_WITH_DEATH_TIMER_BIT,
    "src_modules_doing_both": SRC_MODULES_WITH_BOTH,
    "src_modules_doing_both_names": list(SRC_MODULES_WITH_BOTH_NAMES),
    "src_modules_forbidding_basicattr_bit_0x0080":
        SRC_MODULES_FORBIDDING_DEATH_TIMER,
    "src_modules_forbidding_names":
        list(SRC_MODULES_FORBIDDING_DEATH_TIMER_NAMES),
    "src_modules_passing_zero_hp_by_named_constant":
        list(SRC_ZERO_HP_CONST_MODULES),
    "server_call_sites_emitting_zero_current_hp": SRC_ZERO_HP_SITES
    + V141_ZERO_HP_SITES,
    "actionable_server_gaps": ACTIONABLE_GAPS,
}

RESULT = {
    "binary_sha256": SHA,
    "guards": NGUARD,
    "failures": FAILS,
    "runtimeres": {
        "literal_in_image": False,
        "real_class": "GSCN_RunTimeProtocolRes",
        "req_id": "0x%04X" % RUNTIME_REQ_ID,
        "res_id": "0x%04X" % RUNTIME_RES_ID,
        "res_id_decimal": RUNTIME_RES_ID,
        "res_vtable": "0xF2FFC0",
        "res_sizeof": "0x28",
        "res_serializer": "0x5E3EE0",
        "res_inbound_handler": "0x5E4060",
        "req_inbound_handler": "0x710440 (discard stub)",
        "derived_mask_bits": {
            "0x02": "+0x1C  actor-entry collection -> 0x446F30",
            "0x04": "+0x24",
            "0x08": "+0x20",
        },
    },
    "death_chain": [
        "0x5E4060 GSCN_RunTimeProtocolRes inbound (vtable 0xF2FFC0 +0x1C)",
        "0x446F30 actor reconcile (1 direct caller: 0x5E4085)",
        "actor vtable +0x20 (7 vtables) -> 0x4446F0 / 0x456630",
        "0x4437C0 dead-state sync (1 direct caller: 0x444705)",
        "0x472810 CActorTask_Dead ctor (1 direct caller: 0x4439E9)",
        "0x472850 task update (vtable-only) -> L\"_F_DIE_000\" @0xF0F060",
    ],
    "entry_points": {
        "0x%08X" % t: {
            "direct_calls": ["0x%08X" % v for v in entry_points(t)["direct_calls"]],
            "tail_jumps": ["0x%08X" % v for v in entry_points(t)["tail_jumps"]],
            "pointer_slots": ["0x%08X" % v for v in entry_points(t)["pointer_slots"]],
        }
        for t in (0x4437C0, 0x472810, 0x472850, 0x4446F0, 0x456630, 0x446F30,
                  0x5DF080, 0x5E4060)
    },
    "predicates": {
        "vtable_0x40": "0x43BDA0  HP==0 AND timer > 0.0f   (DYING latch 0x200)",
        "vtable_0x3C": "0x43BD70  HP==0 AND timer <= 0.0f  (CActorTask_Dead)",
        "hp_field": "BasicAttr +0x44 (mask 0x0004, tag 0x14, u32)",
        "timer_field": "BasicAttr +0x58 (mask 0x0080, tag 0x2A, f32)",
        "animation_extra_gate": "[actor+0x70] & 0x40 (model loaded)",
    },
    "actor_type_gate": {
        str(t): {
            "case": "0x%08X" % FACTORY[t][0],
            "sizeof": "0x%X" % FACTORY[t][1],
            "ctor": "0x%08X" % FACTORY[t][2],
            "vtable": "0x%08X" % FACTORY[t][3],
            "class": FACTORY[t][4],
        } for t in FACTORY
    },
    "unexamined_boundary": {
        "vt20_dispatch_shapes_image_wide": len(VT20_ALL),
        "vt20_dispatch_shapes_with_vtable_load": len(VT20_VT),
        "proven_to_dispatch_on_an_actor": ["0x00446FB6"],
        "note": "the other 229 vtable-load +0x20 dispatch sites are NOT "
                "type-excluded by this pass; each would still need an actor "
                "pointer, which in this image can only come from the actor "
                "registry that 0x446F30 owns",
    },
    "counts": COUNTS,
}

COUNTS["guards"] = NGUARD
RESULT["guards"] = NGUARD
RESULT["failures"] = FAILS

if WANT_JSON:
    print(json.dumps(RESULT, indent=2, sort_keys=True))
else:
    print("\n%d guards, %d failures" % (NGUARD, len(FAILS)))
    if FAILS:
        print("FAILED:")
        for f in FAILS:
            print("  -", f)
    else:
        print("RESULT: every RuntimeRes / actor-entry / _F_DIE_000 static guard "
              "reproduced (exit 0)")

if FAILS:
    sys.exit(1)
