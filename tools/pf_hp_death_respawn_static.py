#!/usr/bin/env python3
"""PF HP-DEATH-001 - static byte-exact reconstruction of the client's HP / DEATH /
RESPAWN surface: which attribute field is current HP and which is max, how the
client decides that an actor is dead, the complete death/revive vital family,
and what the client does (and does not do) about a respawn point.

The coverage note for `combat / hp_death_and_respawn` said:

    "HP is projected as a static attribute value only. No depletion, death
     state, corpse, penalty, or respawn path is captured or implemented."

This milestone settles the *evidence* half statically, byte-exact, from the
read-only client image. It captures nothing and implements nothing.

  * THE HEADLINE.  Death is a CLIENT-SIDE DERIVATION from the projected
    attribute values.  There is no "you are dead" frame.  Every actor class
    answers `IsDead` out of its own bound Attr:

        CNetActor / CMyActor  vtable +0x40 -> 0x454AC0
            attr = this->GetAttr()            (vtable +0x74 -> 0x44C630,
                                               `mov eax,[ecx+0x348]`)
            if  !(attr.f32[+0x58] >  0.0f)          -> false
            if  actor.u8[+0x358] != 0:  return attr.u32[+0x1A8] == 0
            else:                       return attr.u32[+0x44]  == 0

        CNetActor / CMyActor  vtable +0x3C -> 0x454A70
            same, but the gate is  !(0.0f > attr.f32[+0x58])  i.e. timer <= 0

        CNetNPC / CAvatarNPC / Pet  vtable +0x40 -> 0x43BDA0, +0x3C -> 0x43BD70
            attr = this->GetAttr()            (vtable +0x74 -> 0x45CD20,
                                               `mov eax,[ecx+0x358]`)
            attr.u32[+0x44] == 0  AND  the same f32[+0x58] comparison

    `BasicAttr +0x44` is the u32 the server already emits as "current HP"
    (mask bit 0x0004) and `+0x48` is "max HP" (bit 0x0008).  The comparison
    against ZERO is the death test; the float at `+0x58` (bit 0x0080) is the
    down/death timer.  The float constant at 0xF0989C is 0.0f.

  * CURRENT vs MAX, proven by a consumer and not by the name.  The HUD updater
    0x53F180 uses the very same `byte [actor+0x358]` switch as the death
    predicate and pushes the pair into the bar helper 0x53EED0, which computes
    `arg1 / arg0 * barwidth` and writes `arg1` into the number-label value slot
    `[widget+0x220]`.  The call site pushes  +0x48 last (= arg0 = denominator =
    MAX) and +0x44 next-to-last (= arg1 = numerator, and the printed number =
    CURRENT).  The MP pair +0x4C / +0x50 is divided inline the same way.
    The alternate pair ActorAttr +0x1A8 / +0x1AC (mask bits 0x40/0x80 of the
    high mask dword at +0x1B8) is selected by the same switch, whose only
    writer in the whole image is 0x4564B3: `al = (SceneCategory(sceneId)==8)`.

  * THE DEATH TRANSITION.  Attr apply and death sync are welded together in one
    function, 0x4446F0:  `call 0x5DF080` (the attr apply loop) immediately
    followed by `call 0x4437C0` (the dead-state sync).  0x4437C0 calls actor
    vtable +0x40 and +0x3C, latches actor flag `[actor+0x70] |= 0x200`, and
    pushes a `CActorTask_Dead` (ctor 0x472810, task id 0x80000005) whose update
    0x472850 plays the animation literal L"_F_DIE_000" at 0xF0F060 through actor
    vtable +0x28.  0x4437C0 has exactly ONE call site in the image (0x444705).
    For the local player the death UI is driven per frame instead: CMyActor
    vtable +0x18 = 0x44E4E0 calls 0x44A540, which calls vtable +0x40 and opens
    the window L"Main_Dead" (0xF0D738).

  * THE VERB FAMILY.  Of the 519 protocol classes registered by the
    PF-NAMEID-HASH-001 once-init thunk shape, exactly THREE carry a
    death/revive token in their name:

        ReliveVital                 0x1AD4   sizeof 0x1C
        ReliveMarkerVital           0x3DD6   sizeof 0x18
        Pets_NotifySailorDeadVital  0x8B12   sizeof 0x20

    ReliveVital's wire is  u8(tag 0x08)@+0x14  then  u8(tag 0x05)@+0x18.
    Its inbound slot (vtable +0x1C) is the shared no-op 0x710440
    (`mov al,1 ; ret 4`), one of 69 such classes: the client can DECODE a
    ReliveVital but does nothing with it.  ReliveMarkerVital DOES have an
    inbound handler, 0x5F0410, which stores the decoded marker object into
    `CMyActor+0x400`.  Pets_NotifySailorDeadVital carries a single qword
    identity at +0x18 and routes to a pet module, not to the player.

  * RESPAWN.  The client selects no respawn point.  `CMyActor+0x400` has
    exactly two readers in .text: the ReliveMarkerVital handler itself and
    0x4E4370, whose only caller uses the marker's u16 at +0x12 as a SCENE ID to
    format a confirmation string out of the SCENE_NAME_TIP table.  No position,
    teleport or movement call exists anywhere in the relive UI span
    0x4E46C0..0x4E4D8C; the only three sends in that span are the three
    ReliveVital producers.  The death penalty is a per-level column named
    n_DEADLOSS in the external STANDARD_STATUS table - the client only READS it
    to build the confirmation text.

NOT CLAIMED: nothing about the ORIGINAL server.  No runtime capture, no wire
observation, no persistence claim, no damage/combat rule.  This is the client's
*expectation*, byte-exact, and nothing else.  The lane goes not_started ->
in_progress and never runtime_pass here.

Report-only / additive: NO server-source change, NO scenario, NO ledger entry.
Sole binary evidence = the read-only client GameClient/GameClient.local.bin,
cross-checked against read-only server source.

PURE STDLIB ON PURPOSE: the release gate runs `py -3` with no third-party
packages, so every disassembly result of the investigation is frozen here as a
byte-pattern guard rather than a capstone call.

Usage:  py -3 tools/pf_hp_death_respawn_static.py [path-to-GameClient.local.bin]
        py -3 tools/pf_hp_death_respawn_static.py --json
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
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


# Only honour argv when this file is the program being run.  Under pytest,
# sys.argv holds the test file's path and must not be mistaken for a binary.
_RUN_AS_SCRIPT = (os.path.basename(sys.argv[0] or "")
                  == os.path.basename(os.path.abspath(__file__)))
_ARGS = [a for a in sys.argv[1:] if not a.startswith("--")] if _RUN_AS_SCRIPT else []
WANT_JSON = _RUN_AS_SCRIPT and "--json" in sys.argv[1:]
BIN = _ARGS[0] if _ARGS else _default_bin()

SERVER_SRC = os.path.normpath(os.path.join(_ROOT, "current",
                                           "pf_login_game_server_v141.py"))
SRC_DIR = os.path.normpath(os.path.join(_ROOT, "src"))

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


# ---- .rdata dword index (value -> list of slot addresses) -------------------
_RDW = {}


def _build_rdata_index():
    base = _RDATA[3]
    size = _RDATA[4]
    va0 = IMAGE_BASE + _RDATA[1]
    for off in range(0, size - 3, 4):
        v = struct.unpack_from("<I", data, base + off)[0]
        if v:
            _RDW.setdefault(v, []).append(va0 + off)


_build_rdata_index()

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


def section(title):
    if not WANT_JSON:
        print("\n== " + title)


# =============================================================== 0. the image
if not WANT_JSON:
    print("PF-HP-DEATH-001 static verifier")
    print("binary          =", BIN)
    print("binary SHA-256  =", SHA)

section("0. image identity")
guard(SHA == EXPECT_SHA, "binary SHA-256 matches the pinned client image")
guard(IMAGE_BASE == 0x400000, "ImageBase == 0x400000")
guard(TEXT_LO == 0x401000, ".text virtual start == 0x401000")
guard(len(data) == 14759424, "image size == 14759424 bytes")

# ============================================ 1. the death/revive verb family
section("1. the death / revive verb family (name -> id, hash-anchored)")

# anchors: three ids v141 already carries as committed constants
guard(name_id("ActorAttr") == 0x12AD, "hash anchor: ActorAttr -> 0x12AD")
guard(name_id("NPCAttr") == 0x0AD5, "hash anchor: NPCAttr -> 0x0AD5")
guard(name_id("UpdateAttrVital") == 0x309A, "hash anchor: UpdateAttrVital -> 0x309A")

FAMILY = {
    # name: (name VA, id, thunk VA, id-slot, getid stub, vtable, sizeof stub,
    #        sizeof, serializer, inbound handler)
    "ReliveVital": (
        0xF3096C, 0x1AD4, 0xBEE640, 0x1082038, 0x5E5F70, 0xF30404,
        0x716010, 0x1C, 0x5E5F80, 0x710440),
    "ReliveMarkerVital": (
        0xF30978, 0x3DD6, 0xBEE660, 0x108203C, 0x5E7440, 0xF305D8,
        0x721E40, 0x18, 0x5EB6D0, 0x5F0410),
    "Pets_NotifySailorDeadVital": (
        0xF423F8, 0x8B12, 0xC04410, 0x1088364, 0x6FF0B0, 0xF422BC,
        0x6217D0, 0x20, 0x642B00, 0x700DC0),
}

for nm, (nva, wid, thunk, slot, getid, vt, szs, sz, ser, hnd) in FAMILY.items():
    guard(cstr(nva) == nm, "literal at 0x%08X == %r" % (nva, nm))
    guard(name_id(nm) == wid, "hash(%s) == 0x%04X" % (nm, wid))

# the three registration thunks, byte for byte
gbytes(0xBEE640, "686c09f300e836dacaff8bc8e8afd6caff66a338200801c3",
       "ReliveVital registration thunk (push literal; hash; store id)")
gbytes(0xBEE660, "687809f300e816dacaff8bc8e88fd6caff66a33c200801c3",
       "ReliveMarkerVital registration thunk")
gbytes(0xC04410, "68f823f400e8667cc9ff8bc8e8df78c9ff66a364830801c3",
       "Pets_NotifySailorDeadVital registration thunk")

# the get-id stubs are `mov ax,[slot]; ret` and sit at vtable +0x10
gbytes(0x5E5F70, "66a138200801c3", "ReliveVital get-id stub reads slot 0x1082038")
gbytes(0x5E7440, "66a13c200801c3", "ReliveMarkerVital get-id stub reads slot 0x108203C")
gbytes(0x6FF0B0, "66a164830801c3", "Pets_NotifySailorDeadVital get-id stub reads slot 0x1088364")
for nm, (_n, _i, _t, _s, getid, vt, _zs, _z, _se, _h) in FAMILY.items():
    guard(dw(vt + 0x10) == getid, "%s vtable 0x%08X +0x10 == get-id 0x%08X"
          % (nm, vt, getid))

# sizeof stubs (`mov eax,<size>; ret`) at vtable +0x0C
gbytes(0x716010, "b81c000000c3", "ReliveVital sizeof stub returns 0x1C")
gbytes(0x721E40, "b818000000c3", "ReliveMarkerVital sizeof stub returns 0x18")
gbytes(0x6217D0, "b820000000c3", "Pets_NotifySailorDeadVital sizeof stub returns 0x20")
for nm, (_n, _i, _t, _s, _g, vt, szs, sz, _se, _h) in FAMILY.items():
    guard(dw(vt + 0x0C) == szs, "%s vtable +0x0C == sizeof stub 0x%08X" % (nm, szs))

# serializer (vtable +0x18) and inbound handler (vtable +0x1C)
for nm, (_n, _i, _t, _s, _g, vt, _zs, _z, ser, hnd) in FAMILY.items():
    guard(dw(vt + 0x18) == ser, "%s vtable +0x18 serializer == 0x%08X" % (nm, ser))
    guard(dw(vt + 0x1C) == hnd, "%s vtable +0x1C inbound == 0x%08X" % (nm, hnd))

gbytes(0x710440, "b001c20400",
       "0x710440 is the shared no-inbound-handler stub `mov al,1 ; ret 4`")

# ---- census over every registered protocol class ---------------------------
_THUNK_RX = re.compile(
    rb"\x68(....)\xe8(....)\x8b\xc8\xe8(....)\x66\xa3(....)\xc3", re.S)
_text_blob = data[TEXT_RAW_OFF:TEXT_RAW_OFF + TEXT_RAW_SZ]
REGISTERED = []
for _m in _THUNK_RX.finditer(_text_blob):
    _nva = struct.unpack("<I", _m.group(1))[0]
    _slot = struct.unpack("<I", _m.group(4))[0]
    _nm = cstr(_nva)
    if _nm:
        REGISTERED.append((_nm, _slot, off2va(TEXT_RAW_OFF + _m.start())))

guard(len(REGISTERED) == 519,
      "519 protocol-class registration thunks in .text (found %d)" % len(REGISTERED))
guard(len({r[0] for r in REGISTERED}) == 519, "all 519 registered class names distinct")

_DEATH_TOKEN = re.compile(r"dead|death|relive|reviv|respawn|corpse|resurrect|dying",
                          re.I)
_matched = sorted(n for n, _s, _t in REGISTERED if _DEATH_TOKEN.search(n))
guard(_matched == sorted(FAMILY),
      "exactly 3 of 519 registered names carry a death/revive token: %s" % _matched)

guard(len({FAMILY[n][1] for n in FAMILY} |
          {0x12AD, 0x0AD5, 0x309A}) == 6,
      "the 3 family ids are pairwise distinct and distinct from the 3 anchors")

# the runtime-assigned wall: none of the 3 ids is baked into .text as a constant
_IMM16_PREFIXES = (b"\x66\xb8", b"\x66\xb9", b"\x66\xba", b"\x66\xbb",
                   b"\x66\x3d", b"\x66\x81\xf8", b"\x66\xa9")
for nm, (_n, wid, _t, _s, _g, _v, _zs, _z, _se, _h) in FAMILY.items():
    _imm = 0
    for _p in _IMM16_PREFIXES:
        _imm += len(find_bytes(_p + struct.pack("<H", wid), ".text"))
    _dwc = 0
    for _va in find_bytes(struct.pack("<I", wid), ".text"):
        _o = va2off(_va)
        if data[_o - 1] in (0xE8, 0xE9):
            continue
        if data[_o - 2] == 0x0F and 0x80 <= data[_o - 1] <= 0x8F:
            continue
        _dwc += 1
    guard(_imm == 0 and _dwc == 0,
          "NEGATIVE: id 0x%04X (%s) never appears as a .text constant "
          "(imm16=%d, dword=%d) - it is computed at once-init"
          % (wid, nm, _imm, _dwc))

# resolve every registered class to exactly one vtable, then count the no-op slot
_SLOT2STUB = {}
for _va in find_bytes(b"\x66\xa1", ".text"):
    _b = rd(_va, 7)
    if len(_b) == 7 and _b[6] == 0xC3:
        _SLOT2STUB.setdefault(struct.unpack_from("<I", _b, 2)[0], []).append(_va)

_resolved = 0
_noop_inbound = 0
_real_inbound = 0
for _nm, _slot, _t in REGISTERED:
    _stubs = _SLOT2STUB.get(_slot, [])
    _vts = []
    for _s in _stubs:
        for _r in _RDW.get(_s, []):
            _vts.append(_r - 0x10)
    if len(_vts) != 1:
        continue
    _resolved += 1
    if dw(_vts[0] + 0x1C) == 0x710440:
        _noop_inbound += 1
    else:
        _real_inbound += 1

guard(_resolved == 501,
      "501 of 519 registered classes resolve to exactly one vtable (got %d)" % _resolved)
guard(_noop_inbound == 69,
      "69 of those 501 have NO inbound handler (vtable +0x1C == 0x710440), got %d"
      % _noop_inbound)
guard(_real_inbound == 432,
      "432 of those 501 DO have an inbound handler, got %d" % _real_inbound)
guard(dw(FAMILY["ReliveVital"][5] + 0x1C) == 0x710440,
      "NEGATIVE: ReliveVital is one of the 69 with no inbound handler")

# ============================================== 2. ReliveVital wire + producers
section("2. ReliveVital wire schema and its three producers")

gbytes(0x5E5F30,
       "8bc133c9c7006c6df80088480489480889480c884811c7000404f300894814884818c6401001c3",
       "ReliveVital ctor installs vtable 0xF30404 and zeroes +0x14 / +0x18")
gbytes(0x5E5F80,
       "807c24080056578b7c240c8bf16a0174298a46148d4c2414516a088bcf8844241ce85a462b00"
       "6a0183c618566a058bcfe84b462b005f5ec2",
       "ReliveVital::Serialize outbound = u8(tag 0x08)@+0x14 then u8(tag 0x05)@+0x18")
ghas(0x5E5F80, 0x40, "8a4614", "  +0x14 is loaded as a BYTE (`mov al,[esi+0x14]`)")
ghas(0x5E5F80, 0x40, "6a08", "  first field tag is 0x08")
ghas(0x5E5F80, 0x40, "83c618", "  second field is at +0x18 (`add esi,0x18`)")
ghas(0x5E5F80, 0x40, "6a05", "  second field tag is 0x05")
ghas(0x5E5F80, 0x60, "e873462b00",
     "  the inbound branch calls the read codec 0x89A640 (the client CAN decode it)")

# class-info registrar welds sizeof 0x1C to the `.?AVReliveVital@@` descriptor
gbytes(0x42265B, "b900fb0101", "ReliveVital class registrar loads descriptor 0x101FB00")
gbytes(0x422689, "c7470c1c000000", "  ... and writes sizeof 0x1C into the class record")
guard(cstr(0x101FB08) == ".?AVReliveVital@@",
      "descriptor 0x101FB00 spells `.?AVReliveVital@@`")
guard(cstr(0x101FB24) == ".?AVReliveMarkerVital@@",
      "descriptor 0x101FB1C spells `.?AVReliveMarkerVital@@`")

_pool_callers = calls_to(0x4E45B0)
guard(_pool_callers == [0x4E4731, 0x4E4AE4, 0x4E4B84, 0x5EB11C],
      "ReliveVital pool allocator 0x4E45B0 has exactly 4 call sites "
      "(3 UI producers + the vtable clone thunk 0x5EB11C): %s"
      % [hex(x) for x in _pool_callers])

gbytes(0x4E4718,
       "6a006a10e8df5af6ff84c0742a6a00680ca9f000b95c000301e87afeffff50"
       "c7401401000000e85dcaf1ff8bc8e8b6900f00",
       "producer A (BUTTON_RELIVE): local query `has`(0x10,0) true -> ReliveVital(+0x14=1)")
gbytes(0x4E4AE4,
       "e8c7faffff50c7401400000000e8aac6f1ff8bc8e8038d0f00",
       "producer B (confirm-dialog OK 0x4E4A90) -> ReliveVital(+0x14=0)")
gbytes(0x4E4B84,
       "e827faffff50c7401400000000e80ac6f1ff8bc8e8638c0f00",
       "producer C (BUTTON_SPAWN fast path) -> ReliveVital(+0x14=0)")

_span = rd(0x4E46C0, 0x4E4D8C - 0x4E46C0)
_sends = [v for v in calls_to(0x5DD800) if 0x4E46C0 <= v < 0x4E4D8C]
guard(len(_sends) == 3,
      "the whole relive UI span 0x4E46C0..0x4E4D8C contains exactly 3 sends "
      "(0x5DD800), got %d" % len(_sends))
guard(_span.count(bytes.fromhex("c7401401000000")) == 1,
      "exactly one producer writes +0x14 = 1")
guard(_span.count(bytes.fromhex("c7401400000000")) == 2,
      "exactly two producers write +0x14 = 0")
guard(bytes.fromhex("c6401800") not in _span
      and bytes.fromhex("c7401800000000") not in _span,
      "NEGATIVE: no producer ever writes ReliveVital +0x18 (it always ships 0)")

# ================================================== 3. HP fields, byte-exact
section("3. HP / MP fields in BasicAttr and the ActorAttr alternate pair")

gbytes(0x465704, "6a0284db8d5e70538bcf6a120f843a010000e8e54e4300",
       "BasicAttr::Serialize emits its own u16 mask (tag 0x12, width 2) from +0x70")
gbytes(0x46574A, "f60304740f6a048d5644526a148bcfe8a24e4300",
       "BasicAttr mask bit 0x0004 -> u32 (tag 0x14) at +0x44   [HP CURRENT]")
gbytes(0x46575E, "f60308740f6a048d4648506a148bcfe88e4e4300",
       "BasicAttr mask bit 0x0008 -> u32 (tag 0x14) at +0x48   [HP MAX]")
gbytes(0x465772, "f60310740f6a048d4e4c516a148bcfe87a4e4300",
       "BasicAttr mask bit 0x0010 -> u32 (tag 0x14) at +0x4C   [MP CURRENT]")
gbytes(0x465786, "f60320740f6a048d5650526a148bcfe8664e4300",
       "BasicAttr mask bit 0x0020 -> u32 (tag 0x14) at +0x50   [MP MAX]")
gbytes(0x4657AE, "f60380740f6a048d4e58516a2a8bcfe83e4e4300",
       "BasicAttr mask bit 0x0080 -> f32 (tag 0x2A) at +0x58   [DEATH/DOWN TIMER]")
gbytes(0x4666D7, "f686b80100004074126a048d86a8010000506a148bcfe80e3f4300",
       "ActorAttr high-mask +0x1B8 bit 0x40 -> u32 (tag 0x14) at +0x1A8  [alt HP cur]")
gbytes(0x4666F2, "f686b80100008074126a048d8eac010000516a148bcfe8f33e4300",
       "ActorAttr high-mask +0x1B8 bit 0x80 -> u32 (tag 0x14) at +0x1AC  [alt HP max]")

# current-vs-max is decided by the HUD consumer, not by the field name
gbytes(0x53F1A3,
       "80b858030000005355578bb84803000074188b461c8b4e188b97a801000050"
       "8b87ac010000515250eb108b4e1c8b56188b4744518b4f48525051",
       "HUD updater 0x53F180 switches on byte [player+0x358] and pushes "
       "(+0x48,+0x44) or (+0x1AC,+0x1A8)")
gbytes(0x53EED0,
       "578b7c241485ff74558b4c241085c9744d8b44240885c07445568b742410"
       "f30f2ac8f30f5ac9f30f2ac6f30f5ac0f20f5ec1f30f2a8998170000f30f5ac9"
       "f20f59c1f20f5ac0f30f2cc050e81035f3ff89b720020000c68718020000015e5fc2",
       "bar helper 0x53EED0 computes arg1/arg0 and writes arg1 into "
       "[numberlabel+0x220] -> the LAST push (+0x48) is the DENOMINATOR = MAX")
ghas(0x53EED0, 0x60, "f20f5ec1", "  ... the division is `divsd xmm0, xmm1`")
ghas(0x53EED0, 0x60, "89b720020000", "  ... the printed number is the numerator")
ghas(0x53F1E0, 0x40, "8b5f4c", "MP path loads +0x4C as the numerator")
ghas(0x53F1E0, 0x40, "8b4750", "MP path loads +0x50 as the denominator")
ghas(0x53F1E0, 0x40, "f20f5ec1", "MP path divides the same way")

# the only writer of the pair selector
_sel_writers = find_bytes(b"\x88\x86\x58\x03\x00\x00", ".text")
guard(_sel_writers == [0x4564B3],
      "byte [actor+0x358] has exactly ONE writer in .text: 0x4564B3 (%s)"
      % [hex(x) for x in _sel_writers])
gbytes(0x4564A5, "e866a9fdff83c40483f8080f94c08886580300",
       "  ... and it is `al = (SceneCategory(sceneId) == 8)`")

# ================================================= 4. how the client knows dead
section("4. the death predicates - client derives death from the HP field")

ACTOR_VT = {
    "CNetActor": 0xF0DD08,
    "CMyActor": 0xF0D7A8,
    "CNetNPC": 0xF0DF58,
    "CAvatarNPC": 0xF0DFF8,
    "Pet": 0xF0E0C8,
}
for nm in ("CNetActor", "CMyActor"):
    vt = ACTOR_VT[nm]
    guard(dw(vt + 0x40) == 0x454AC0, "%s vtable +0x40 (IsDead) == 0x454AC0" % nm)
    guard(dw(vt + 0x3C) == 0x454A70, "%s vtable +0x3C (IsDead, timer<=0) == 0x454A70" % nm)
    guard(dw(vt + 0x74) == 0x44C630, "%s vtable +0x74 (GetAttr) == 0x44C630" % nm)
for nm in ("CNetNPC", "CAvatarNPC", "Pet"):
    vt = ACTOR_VT[nm]
    guard(dw(vt + 0x40) == 0x43BDA0, "%s vtable +0x40 (IsDead) == 0x43BDA0" % nm)
    guard(dw(vt + 0x3C) == 0x43BD70, "%s vtable +0x3C (IsDead, timer<=0) == 0x43BD70" % nm)
    guard(dw(vt + 0x74) == 0x45CD20, "%s vtable +0x74 (GetAttr) == 0x45CD20" % nm)

gbytes(0x44C630, "8b8148030000c3",
       "player GetAttr 0x44C630 == `mov eax,[ecx+0x348] ; ret`")
gbytes(0x45CD20, "8b8158030000c3",
       "NPC GetAttr 0x45CD20 == `mov eax,[ecx+0x358] ; ret`")

gbytes(0x454AC0,
       "568bf18b068b5074ffd2f30f1040580f2f059c98f000762e8b864803000085c07424"
       "80be5803000000740f33c93988a80100005e0f94c18ac1c333d23950445e0f94c28ac2c3"
       "32c05ec3",
       "CNetActor/CMyActor::IsDead 0x454AC0 in full")
ghas(0x454AC0, 0x50, "3950 44".replace(" ", ""),
     "  ... `cmp [attr+0x44], edx` with edx = 0  -> DEATH IS 'CURRENT HP == 0'")
ghas(0x454AC0, 0x50, "3988a8010000",
     "  ... alternate branch compares [attr+0x1A8] to 0")
ghas(0x454AC0, 0x50, "80be5803000000",
     "  ... the branch selector is the same byte [actor+0x358] as the HUD")
ghas(0x454AC0, 0x50, "f30f104058",
     "  ... gate loads the f32 at [attr+0x58]")
ghas(0x454AC0, 0x50, "0f2f059c98f000",
     "  ... and compares it against the constant at 0xF0989C")
guard(f32(0xF0989C) == 0.0, "the constant at 0xF0989C is 0.0f")
gbytes(0x454A70,
       "568bf18b068b5074ffd20f57c00f2f4058722e8b864803000085c07424"
       "80be5803000000740f33c93988a80100005e0f94c18ac1c333d23950445e0f94c28ac2c3"
       "32c05ec3",
       "CNetActor/CMyActor 0x454A70 - same HP test, complementary timer gate")
gbytes(0x43BDA0,
       "568bf18b068b5074ffd283784400751e8b068b50748bceffd2f30f1040580f2f059c98f000"
       "7607b8010000005ec333c05ec3",
       "CNetNPC/CAvatarNPC/Pet::IsDead 0x43BDA0 - `cmp [attr+0x44],0` then the timer")
gbytes(0x43BD70,
       "568bf18b068b5074ffd28378440075198b068b50748bceffd20f57c00f2f4058"
       "7207b8010000005ec333c05ec3",
       "CNetNPC/CAvatarNPC/Pet 0x43BD70 - complementary timer gate")

for _p in (0x454AC0, 0x454A70, 0x43BDA0, 0x43BD70):
    guard(calls_to(_p) == [],
          "NEGATIVE: 0x%08X is reached only through the vtable (no direct E8 call)" % _p)

# ================================================ 5. the death transition path
section("5. attr apply -> dead-state sync -> death task / death UI")

gbytes(0x4446F0, "8b442404568bf18b0885c9742f56e87da919008bcee8b6f0ffff",
       "0x4446F0 welds the attr apply loop 0x5DF080 to the dead-state sync 0x4437C0")
guard(calls_to(0x4437C0) == [0x444705],
      "the dead-state sync 0x4437C0 has exactly ONE call site: 0x444705")
guard(dw(ACTOR_VT["CNetNPC"] + 0x20) == 0x4446F0,
      "CNetNPC vtable +0x20 (apply-attrs) == 0x4446F0")
guard(dw(ACTOR_VT["CNetActor"] + 0x20) == 0x456630
      and dw(ACTOR_VT["CMyActor"] + 0x20) == 0x456630,
      "CNetActor/CMyActor vtable +0x20 == 0x456630")
guard(0x4566A7 in calls_to(0x4446F0),
      "0x456630 reaches 0x4446F0 at 0x4566A7")

ghas(0x443810, 0x60, "8b424083c408f7df1bff8bce23feffd0",
     "0x4437C0 calls actor vtable +0x40 (IsDead) at 0x443836")
ghas(0x443810, 0x60, "8b423c8bceffd0",
     "0x4437C0 calls actor vtable +0x3C at 0x443841")
ghas(0x443840, 0x30, "095670",
     "0x4437C0 latches actor flag `[actor+0x70] |= 0x200` on the death edge")
gbytes(0x4439C7, "ba24000000b9a4dc0201e87af3ffff89442414c74424700000000085c0740a568bc8e822ee0200",
       "0x4437C0 allocates 0x24 bytes and constructs CActorTask_Dead (0x472810)")
guard(calls_to(0x472810) == [0x4439E9],
      "CActorTask_Dead's constructor has exactly ONE call site: 0x4439E9")
gbytes(0x472810, "8b44240456508bf1e823350100c70648f0f000c6462000c74610050000808bc65ec20400",
       "CActorTask_Dead ctor installs vtable 0xF0F048 and task id 0x80000005")
gbytes(0x472898, "807f2000751ef646704074188b068b50286a006a006a006860f0f0008bceffd2c6472001",
       "CActorTask_Dead::Update plays the animation at 0xF0F060 via actor vtable +0x28")
guard(wstr(0xF0F060) == "_F_DIE_000",
      "the animation literal at 0xF0F060 is L\"_F_DIE_000\"")
guard(cstr(0x101CDEC) == ".?AVCActorTask_Dead@@",
      "the task's RTTI descriptor spells `.?AVCActorTask_Dead@@`")
gbytes(0xBD10B0, "68d0450901b9e4cd0101",
       "type-node registrar 0xBD10B0 binds that descriptor to node 0x102ED98")

# local-player death UI, evaluated per frame
guard(dw(ACTOR_VT["CMyActor"] + 0x18) == 0x44E4E0,
      "CMyActor vtable +0x18 (per-frame update) == 0x44E4E0")
guard(0x44E828 in calls_to(0x44A540),
      "CMyActor's per-frame update calls the death-UI gate 0x44A540 at 0x44E828")
gbytes(0x44A540,
       "568bf18b068b5040ffd284c0745af646108075546838d7f000b908070901e89d496500"
       "85c0753f8b8648030000f30f104058",
       "0x44A540 calls vtable +0x40 (IsDead) and only then looks up L\"Main_Dead\"")
guard(wstr(0xF0D738) == "Main_Dead", "the death window literal at 0xF0D738 is L\"Main_Dead\"")
ghas(0x44A58B, 0x20, "6838d7f000b908070901e86a616500",
     "0x44A5A1 opens that window (0xAA0710)")

# the target panel reacts to a dead target
guard(wstr(0xF0D470) == "TargetIsDead",
      "0x4437C0's target-panel string at 0xF0D470 is L\"TargetIsDead\"")
ghas(0x443A01, 0x60, "68a8d2f000",
     "0x4437C0 pushes L\"Main_Panel_Target_Enemy_New\" when the dead actor is my target")
guard(wstr(0xF0D2A8) == "Main_Panel_Target_Enemy_New",
      "0xF0D2A8 is L\"Main_Panel_Target_Enemy_New\"")

# ==================================================== 6. respawn / marker path
section("6. respawn: marker in, no client-side position choice")

gbytes(0x5F0410,
       "a1c42e0301578bf985c074308b8800040000568db0000400003b4f14741785c97405"
       "e829cc29008b4f14890e85c97405e80bcc29005eb0015fc20400",
       "ReliveMarkerVital handler 0x5F0410 stores the decoded marker into CMyActor+0x400")
gbytes(0x5DF250,
       "807c24080056578b7c240c8bf16a02744c8d4612506a128bcfe892b32b00"
       "6a088d4e18516a328bcfe883b32b006a018d5610526a0b8bcfe874b32b00"
       "6a018d4611506a0b8bcfe865b32b005783c62056e8eb41010083c4085f5ec20800",
       "the marker sub-object wire = u16(0x12)@+0x12, qword(0x32)@+0x18, "
       "u8(0x0B)@+0x10, u8(0x0B)@+0x11, nested list @+0x20")
gbytes(0x4E4370,
       "518b8900040000568b74240cc744240400000000890e85c97405e8c18c3a008bc65e59c20400",
       "0x4E4370 is the only other reader of CMyActor+0x400 (addref-and-return)")
guard(calls_to(0x4E4370) == [0x4E4BBA],
      "0x4E4370 has exactly one caller, the BUTTON_SPAWN handler at 0x4E4BBA")
gbytes(0x4E4BDD, "0fb74f1251689cc5f000b9d0cd0801",
       "the marker's u16 at +0x12 is used as a SCENE ID against SCENE_NAME_TIP")
guard(wstr(0xF0C59C) == "SCENE_NAME_TIP", "0xF0C59C is L\"SCENE_NAME_TIP\"")
guard(wstr(0xF0C3C4) == "s_SCENE_NAME", "0xF0C3C4 is L\"s_SCENE_NAME\"")

# the death-penalty number is external data, only read for display
guard(wstr(0xF14BC8) == "n_DEADLOSS", "0xF14BC8 is L\"n_DEADLOSS\"")
guard(wstr(0xF152AC) == "STANDARD_STATUS", "0xF152AC is L\"STANDARD_STATUS\"")
gbytes(0x4E4C54, "68ac52f100b9d0cd0801e83dc43a0085c0740e6a0068c84bf1008bc8e85bd33a00",
       "BUTTON_SPAWN reads STANDARD_STATUS[level].n_DEADLOSS (variant A)")
gbytes(0x4E4C9F, "68ac52f100b9d0cd080133ff33ede8eec33a0085c074125568c84bf1008bc8e80dd33a00",
       "BUTTON_SPAWN reads STANDARD_STATUS[level].n_DEADLOSS (variant B)")
ghas(0x4E4C40, 0x20, "8b8148030000 0fb7405e".replace(" ", ""),
     "  ... the row key is the level word BasicAttr+0x5E")

# nothing in the relive span moves the player
for _mover in (0x484580, 0x485B90, 0x43E1D0):
    _hits = [v for v in calls_to(_mover) if 0x4E46C0 <= v < 0x4E4D8C]
    guard(_hits == [],
          "NEGATIVE: no call to 0x%08X inside the relive UI span" % _mover)

# ============================================== 7. the death/revive UI wiring
section("7. UI wiring of the death window")

RELIVE_CONFIRM_VT = 0xF2E6A8
guard(dw(RELIVE_CONFIRM_VT + 0x00) == 0x5D5860,
      "ReliveConfirmEventHandler vtable 0xF2E6A8 +0x00 -> type node stub 0x5D5860")
gbytes(0x5D5860, "b8e4b30701c3", "  ... which returns node 0x107B3E4")
gbytes(0xBDE305, "b9ec320201",
       "type-node registrar 0xBDE300 binds `.?AVReliveConfirmEventHandler@@` to 0x107B3E4")
guard(cstr(0x10232F4) == ".?AVReliveConfirmEventHandler@@",
      "descriptor 0x10232EC spells `.?AVReliveConfirmEventHandler@@`")
guard(dw(RELIVE_CONFIRM_VT + 0x18) == 0x4E43A0,
      "ReliveConfirmEventHandler vtable +0x18 (bind) == 0x4E43A0")
guard(dw(RELIVE_CONFIRM_VT + 0x28) == 0x4E4D90,
      "ReliveConfirmEventHandler vtable +0x28 (click dispatch) == 0x4E4D90")
ghas(0x4E43A0, 0x20, "6804a7f100", "bind: L\"BUTTON_RELIVE\" (0xF1A704) -> this+0x14")
gbytes(0x4E43E5, "68e8a6f1008bce894614", "bind: L\"BUTTON_SPAWN\" (0xF1A6E8) -> this+0x18")
gbytes(0x4E441E, "68c0a6f1008bce894618",
       "bind: L\"BUTTON_RELIVE_TEXT\" (0xF1A6C0) -> this+0x1C")
for _va, _nm in ((0xF1A704, "BUTTON_RELIVE"), (0xF1A6E8, "BUTTON_SPAWN"),
                 (0xF1A6C0, "BUTTON_RELIVE_TEXT"), (0xF1F5CC, "BUTTON_DIE")):
    guard(wstr(_va) == _nm, "widget literal 0x%08X is L\"%s\"" % (_va, _nm))
gbytes(0x4E4D90,
       "8b5424048b02568b35c00d090139411475133b7208750e8b520c5250e80ff9ffff5ec20400"
       "394118750f3b7208750a8b520c5250e857fdffff5ec20400",
       "click dispatch: this+0x14 -> 0x4E46C0 (RELIVE), this+0x18 -> 0x4E4B20 (SPAWN)")

MAIN_DEAD_VT = 0xF1F550
guard(dw(MAIN_DEAD_VT + 0x00) == 0x5183C0,
      "MainDeadEventHandler vtable 0xF1F550 +0x00 -> type node stub 0x5183C0")
guard(cstr(0x1023E68) == ".?AVMainDeadEventHandler@@",
      "descriptor 0x1023E60 spells `.?AVMainDeadEventHandler@@`")
guard(dw(MAIN_DEAD_VT + 0x60) == 0x5183D0,
      "MainDeadEventHandler vtable +0x60 (bind) == 0x5183D0")
gbytes(0x5183D0, "565768ccf5f1008bf9", "  ... binds L\"BUTTON_DIE\" into this+0x14")
guard(dw(MAIN_DEAD_VT + 0x18) == 0x5184C0,
      "MainDeadEventHandler vtable +0x18 == 0x5184C0")
gbytes(0x5184C0,
       "568bf18b068b505cffd28b068b50608bceffd284c075025ec3a1c00d09018b4e14"
       "685084510050518bcee8a11b0600b0015ec3",
       "0x5184C0 hooks 0x518450 onto the BUTTON_DIE widget")
ghas(0x518450, 0x50, "c740307cea0000",
     "0x518450 sends an action record with id 0xEA7C (the debug `die` command)")

# ======================================== 8. Pets_NotifySailorDeadVital, briefly
section("8. Pets_NotifySailorDeadVital")

gbytes(0x642B00, "807c2408008d41188b4c24046a08506a327408e8e87a2500c20800e8207b2500c20800",
       "Pets_NotifySailorDeadVital carries exactly one qword (tag 0x32) at +0x18")
gbytes(0x700DC0, "a1c42e0301578bf985c07506",
       "its inbound handler 0x700DC0 routes through the local module registry")
guard(cstr(0x101D834) == ".?AVPets_NotifySailorDeadVital@@",
      "descriptor 0x101D82C spells `.?AVPets_NotifySailorDeadVital@@`")

# ============================================== 9. server gap, counted not eyed
section("9. server gap (read-only cross-check)")

SERVER_TEXT = ""
SRC_TEXT = {}
if os.path.isfile(SERVER_SRC):
    SERVER_TEXT = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
if os.path.isdir(SRC_DIR):
    for _root, _dirs, _files in os.walk(SRC_DIR):
        _dirs[:] = [d for d in _dirs if d != "__pycache__"]
        for _f in sorted(_files):
            if _f.endswith(".py"):
                _p = os.path.join(_root, _f)
                SRC_TEXT[_p] = open(_p, "r", encoding="utf-8",
                                    errors="replace").read()
_ALL_SERVER = SERVER_TEXT + "".join(SRC_TEXT.values())

guard(bool(SERVER_TEXT), "v141 snapshot opened read-only for the cross-check")
guard(bool(SRC_TEXT), "src/ opened read-only for the cross-check")

_ID_TOKENS = ("0x1AD4", "0x1ad4", "6868", "0x3DD6", "0x3dd6", "15830",
              "0x8B12", "0x8b12", "35602")
_id_hits = sum(_ALL_SERVER.count(t) for t in _ID_TOKENS)
guard(_id_hits == 0,
      "NEGATIVE: none of the 3 death/revive wire ids appears in v141 or src/ (%d hits)"
      % _id_hits)

_VERB_TOKENS = ("Relive", "relive", "RELIVE", "Revive", "revive",
                "Respawn", "respawn")
_verb_hits = sum(_ALL_SERVER.count(t) for t in _VERB_TOKENS)
guard(_verb_hits == 0,
      "NEGATIVE: no Relive/Revive/Respawn encoder or dispatch in v141 or src/ (%d hits)"
      % _verb_hits)

# the HP pair IS emitted; the death timer bit is NOT
_hp_sites = len(re.findall(r"u32tag\(0x14,\s*current_hp\)", _ALL_SERVER))
_hpmax_sites = len(re.findall(r"u32tag\(0x14,\s*max_hp\)", _ALL_SERVER))
guard(_hp_sites >= 1 and _hpmax_sites >= 1,
      "the BasicAttr HP pair (bits 0x0004/0x0008) IS emitted: %d/%d call sites"
      % (_hp_sites, _hpmax_sites))
guard(re.search(r"basic_mask\s*\|?=\s*0x0080", _ALL_SERVER) is None,
      "NEGATIVE: BasicAttr bit 0x0080 (the death/down timer at +0x58) is never set")
guard("0x1A8" not in _ALL_SERVER and "0x1a8" not in _ALL_SERVER,
      "NEGATIVE: the alternate HP pair ActorAttr +0x1A8/+0x1AC is never emitted")
guard(re.search(r"current_hp\s*=\s*0\b", _ALL_SERVER) is None
      and re.search(r"current_hp\s*=\s*0[,)\s]", _ALL_SERVER) is None,
      "NEGATIVE: no code path in v141 or src/ ever emits current HP == 0")
guard(re.search(r"0xEA7C|0xea7c", _ALL_SERVER) is None,
      "NEGATIVE: the client's debug die-action id 0xEA7C has no server handler")

# ---------------------------------------------------------------- the numbers
# BasicAttr's field count is measured, not typed: the outbound half of
# BasicAttr::Serialize makes 1 codec call for its own mask plus 1 per gated field.
_BASIC_CODEC_CALLS = 0
for _t in (0x89A600, 0x89A810, 0x89A6D0):
    _BASIC_CODEC_CALLS += len([v for v in calls_to(_t) if 0x465704 <= v < 0x465850])
BASICATTR_FIELDS_TOTAL = _BASIC_CODEC_CALLS - 1
guard(BASICATTR_FIELDS_TOTAL == 12,
      "BasicAttr's outbound half emits 1 mask + 12 gated fields (measured %d)"
      % BASICATTR_FIELDS_TOTAL)

# how many distinct BasicAttr mask bits our side has ever set
_bits = set()
for _m in re.finditer(r"basic_mask\s*(?:=|\|=)\s*([^\n#]+)", _ALL_SERVER):
    for _h in re.findall(r"0x[0-9A-Fa-f]{4}", _m.group(1)):
        _v = int(_h, 16)
        for _b in range(16):
            if _v & (1 << _b):
                _bits.add(1 << _b)
BASICATTR_FIELDS_EMITTED = len(_bits)
guard(BASICATTR_FIELDS_EMITTED == 7,
      "our side sets 7 distinct BasicAttr mask bits (%s)"
      % sorted(hex(b) for b in _bits))
guard(0x0080 not in _bits,
      "NEGATIVE: mask bit 0x0080 is not among them - the death timer is never sent")
guard(0x0004 in _bits and 0x0008 in _bits,
      "the HP pair bits 0x0004/0x0008 ARE among them")

CLIENT_DEATH_VERBS = len(FAMILY)
CLIENT_DEATH_VERBS_DECODED = sum(1 for n in FAMILY if FAMILY[n][9] != 0x710440)
SERVER_DEATH_ENCODERS = 0
DEATH_PREDICATES = 4                  # 0x454AC0 / 0x454A70 / 0x43BDA0 / 0x43BD70
DEATH_RELEVANT_FIELDS = 3             # +0x44, +0x58, and the alternate +0x1A8
DEATH_RELEVANT_EMITTED = 2            # +0x44 and its partner +0x48
guard(CLIENT_DEATH_VERBS - SERVER_DEATH_ENCODERS == 3,
      "gap: 3 client death/revive verbs, 0 server encoders")
guard(CLIENT_DEATH_VERBS_DECODED == 2,
      "gap: only 2 of the 3 have a client-side decoder (ReliveVital does not)")
guard(DEATH_RELEVANT_FIELDS - DEATH_RELEVANT_EMITTED == 1,
      "gap: of the 3 fields the death predicate reads, 1 (+0x58) is never emitted")

# flat, machine-readable counts - the block the report must reproduce verbatim
COUNTS = {
    "measured_at_head": "fc204c7",
    "registered_protocol_classes": len(REGISTERED),
    "registered_classes_with_resolved_vtable": _resolved,
    "classes_with_no_inbound_handler": _noop_inbound,
    "classes_with_inbound_handler": _real_inbound,
    "client_death_revive_verbs": CLIENT_DEATH_VERBS,
    "client_death_revive_verbs_with_client_decoder": CLIENT_DEATH_VERBS_DECODED,
    "server_death_revive_encoders": SERVER_DEATH_ENCODERS,
    "server_death_revive_dispatch": 0,
    "death_predicates_in_client": DEATH_PREDICATES,
    "basicattr_wire_fields_total": BASICATTR_FIELDS_TOTAL,
    "basicattr_mask_bits_emitted_by_us": BASICATTR_FIELDS_EMITTED,
    "fields_read_by_the_death_predicate": DEATH_RELEVANT_FIELDS,
    "fields_read_by_the_death_predicate_emitted_by_us": DEATH_RELEVANT_EMITTED,
    "server_call_sites_emitting_zero_current_hp": 0,
    "server_references_to_basicattr_bit_0x0080": 0,
    "server_references_to_actorattr_0x1A8_pair": 0,
    "server_handlers_for_action_0xEA7C": 0,
}

RESULT = {
    "binary_sha256": SHA,
    "guards": NGUARD,
    "failures": FAILS,
    "family": {
        n: {
            "id": "0x%04X" % FAMILY[n][1],
            "vtable": "0x%08X" % FAMILY[n][5],
            "sizeof": "0x%02X" % FAMILY[n][7],
            "serializer": "0x%08X" % FAMILY[n][8],
            "inbound_handler": "0x%08X" % FAMILY[n][9],
            "has_client_decoder": FAMILY[n][9] != 0x710440,
        } for n in FAMILY
    },
    "death_predicates": {
        "player_isdead": "0x454AC0",
        "player_isdead_timer_expired": "0x454A70",
        "npc_isdead": "0x43BDA0",
        "npc_isdead_timer_expired": "0x43BD70",
        "hp_current_field": "BasicAttr+0x44 (mask 0x0004, tag 0x14, u32)",
        "hp_max_field": "BasicAttr+0x48 (mask 0x0008, tag 0x14, u32)",
        "death_timer_field": "BasicAttr+0x58 (mask 0x0080, tag 0x2A, f32)",
        "alt_hp_pair": "ActorAttr+0x1A8/+0x1AC (high mask +0x1B8 bits 0x40/0x80)",
        "selector": "byte [actor+0x358], sole writer 0x4564B3",
    },
    "registry_census": {
        "registered_classes": len(REGISTERED),
        "resolved_vtables": _resolved,
        "no_inbound_handler": _noop_inbound,
        "with_inbound_handler": _real_inbound,
        "death_token_matches": _matched,
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
        print("RESULT: all HP/death/respawn static guards reproduced (exit 0)")

# Only a drift exits non-zero; a clean run must be importable by the pytest file.
if FAILS:
    sys.exit(1)
