#!/usr/bin/env python3
"""Offline verifier for HYP-PF-024 / DAMAGE-ENCODER-001, the CHitResult lane.

WHAT THIS LANE IS
-----------------
HYP-PF-024 composes one ``GSCN_RunTimeProtocolRes`` frame per step carrying a
``CHitResult`` (wire id 0x16F7, version byte 0) as a single element of the
VitalData collection -- the BASE change mask bit 0x02 object at ``this+0x18``,
NOT the actor-entry collection (DERIVED mask bit 0x02, ``this+0x1C``) that the
runtimeres-death lane rides.  Each frame carries exactly one hit entry against
one target: a signed i32 damage value at element +0x08 and a u16 result-flag
word at element +0x1C, plus the pinned position and a pinned 0.0f yaw.

WHOSE FORMULA THIS IS
---------------------
**The damage formula in this repository is OURS, the original server's is
unrecoverable.**  That server was shut down years ago and was never published.
DAMAGE-MODEL-001 (round 83, 235 byte-exact guards) proved the reason it matters
here: the client computes nothing.  It carries no damage formula, applies no
scaling and never subtracts damage from hit points.  The number a player sees
is the signed 32-bit integer the server put at hit-entry +0x08, passed through
abs() and printed with "%d".  So there is nothing in the image to recover a
formula FROM, and this project designed one instead.  Nothing in this file --
and nothing this file verifies -- is evidence about the original server.

WHAT THIS TOOL CHECKS, in the order it checks it
------------------------------------------------
A. REGRESSION GATE.  Reproduce, from the read-only client image, the answers
   earlier rounds already published: the image hash, the CHitResult serializer
   0x750040, the hit-entry array writer 0x74F5A0, the nine-slot vtable
   0xF48AA0, the 32-byte element stride proven twice (``sar eax,5`` @0x74F5B3
   and ``add ebx,0x20`` @0x74F686), and the four SIGNED ``cmp dword ptr
   [ebx+8],0`` / ``jge`` sites that are what make +0x08 mean anything.  If ONE
   of these drifts the tool announces nothing new and exits 2.
B. The round-90 static table (drafts/DAMAGE_MODEL_UNKNOWNS_R90_STATIC.md
   section 6): 16 byte ranges compared by file offset and sha256, and 21
   point-byte guards.
C. The module against the image: every constant in
   src/pirateforce_foundation/damage_model_hypothesis.py that claims to be a
   fact about the client -- the vital id (recomputed as the PF-NAMEID hash of
   the literal "CHitResult" at 0xF0B5F8), the version byte 0 read out of ctor
   0x74F940, every VA in STATIC_ANCHORS, and every wire offset/tag pair read
   out of the emission chains.
D. The module against itself, offline: compose the pinned probe sweep and
   compare all six pinned values per step, assert every wire width instead of
   trusting it, reproduce the formula outputs, and compare the scenario file's
   pins against the module's.
D2. The npc_target profile (DAMAGE-NPC-TARGET-001, round 95): its scenario
   file loads to the module's own profile object, its unlock token opens no
   hit_sweep byte (and vice versa), its composed probe sweep reproduces
   DAMAGE_MODEL_PINS_NPC, its pins DIFFER from the hit_sweep pins on every
   step, its performer is the player while its target is the fixed placement
   identity 0x2001, and the two npc-specific refusals fire by name.  Whether
   0x2001 is in the client's identity map at RUNTIME is not checked here and
   cannot be: that is GT-027, attended.
E. Every rejection family produces NO BYTES: the call raises
   DamageModelValidationError with the right reason and returns nothing.
F. Traps.  A verifier that has never seen itself go red is not a verifier, so
   pinned data is mutated in memory and the same guard helpers are required to
   reject the mutation.

The client image is read-only, is never written to, is never executed, and is
never disassembled here: every opcode claim is a raw byte comparison.  No
server is booted, no client is launched, no database is touched.  If the image
is not found, the image-dependent guards are SKIPPED and the exit code is
unaffected, because a repository gate must not depend on a file outside the
repository.

PURE STDLIB ON PURPOSE, and ASCII-ONLY OUTPUT ON PURPOSE: the release gate runs
`py -3` on a Windows console whose code page is cp874, where one unmappable
character kills the process mid-print.

Usage:  py -3 tools/verify_damage_model_encoder.py
        py -3 tools/verify_damage_model_encoder.py --binary <GameClient.local.bin>
        py -3 tools/verify_damage_model_encoder.py --json
        python3 tools/verify_damage_model_encoder.py

Exit 0 = every guard held.  Exit 1 = at least one guard drifted.
Exit 2 = the regression gate drifted; nothing new is announced.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys


_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "src"))

SCENARIO_PATH = os.path.join(
    _ROOT, "scenarios", "damage_model_hypothesis_hit_sweep.json")
NPC_SCENARIO_PATH = os.path.join(
    _ROOT, "scenarios", "damage_model_hypothesis_npc_sweep.json")
OTHER_SCENARIO_PATH = os.path.join(
    _ROOT, "scenarios", "hp_death_hypothesis_death_sweep.json")
LEGACY_PATH = os.path.join(_ROOT, "current", "pf_login_game_server_v141.py")

EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
EXPECT_IMAGE_SIZE = 14759424
EXPECT_IMAGE_BASE = 0x400000
EXPECT_TEXT_VA = 0x401000


def _default_bin():
    """Find the read-only image the same way pf_damage_hit_result_static.py does."""
    for cand in (
        os.path.join(_ROOT, "packages", ".v134_staging_20260815_0355",
                     "GameClient.local.bin"),
        os.path.join(_ROOT, "..", "GameClient", "GameClient.local.bin"),
        "GameClient/GameClient.local.bin",
        os.path.join(_ROOT, "GameClient", "GameClient.local.bin"),
    ):
        if os.path.isfile(cand):
            return cand
    return None


_ARGV = sys.argv[1:]
WANT_JSON = "--json" in _ARGV
if "--binary" in _ARGV:
    BIN = _ARGV[_ARGV.index("--binary") + 1]
else:
    _POS = [a for a in _ARGV if not a.startswith("--")]
    BIN = _POS[0] if _POS else _default_bin()
HAVE_IMAGE = bool(BIN) and os.path.isfile(BIN)


# ===========================================================================
# A. THE REGRESSION GATE TABLES.  Everything here was published by an earlier
# round; this tool refuses to say anything new until it can reproduce them.
# ===========================================================================
# CHitResult::Serialize, the write branch, byte for byte (DAMAGE-MODEL-001).
SERIALIZER_VA = 0x750040
SERIALIZER_BYTES = (
    "807c24080056578b7c240c8bf16a088bcf74598d4618506a32e8a2a51400"
    "6a028d4e20516a128bcfe893a514006a028d5622526a128bcfe884a51400"
    "6a048d4624506a148bcfe875a514006a018d4e28516a0b8bcfe866a51400"
    "5783c62c56e8fcf4ffff83c4085f5ec20800"
)
SERIALIZER_SPAN = (0x750040, 0x7500AC, 0x34F440,
                   "C596C1E8D51C243651D2DBB181319543848D4921B6171D97D1D553FB28DD5101")

# The header, one row per emitted field: the `lea`+`push`+tag immediate that
# proves the object offset and the tag byte together.
HEADER_EMISSION = (
    (0x18, 0x32, "qword", "8d4618506a32"),
    (0x20, 0x12, "u16", "8d4e20516a12"),
    (0x22, 0x12, "u16", "8d5622526a12"),
    (0x24, 0x14, "u32", "8d4624506a14"),
    (0x28, 0x0B, "u8", "8d4e28516a0b"),
)

ARRAY_WRITE_VA = 0x74F5A0
ARRAY_WRITE_PROLOGUE = "515355568b7424148b46102b460c578b7c241cc1f8050fb7c8"
ARRAY_WRITE_SPAN = (0x74F5A0, 0x74F69E, 0x34E9A0,
                    "94A042AEAE2F41A44FD64B87D1F1B919FF1F4C79F2751692CE3705A5A1427067")
ARRAY_COUNT_BYTES = (0x74F5C4, "6a128bcfe833b01400")
ELEMENT_CHAIN_VA = 0x74F625
ELEMENT_CHAIN_BYTES = (
    "6a08536a328bcfe8cfaf14008d730c6a048d46fc506a148bcfe8bdaf1400"
    "5756e8463eeaff83c4086a048d4e0c516a2a8bcfe8a4af14006a0283c610"
    "566a128bcfe895af1400"
)
# Per element: (offset, tag, kind, the push pattern that proves both).
ELEMENT_EMISSION = (
    (0x00, 0x32, "qword target id", "6a08536a32"),
    (0x08, 0x14, "u32 damage, read signed", "6a048d46fc506a14"),
    (0x0C, 0x2A, "3x f32 position via 0x5F3490", "5756e8463eeaff"),
    (0x18, 0x2A, "f32 yaw angle", "6a048d4e0c516a2a"),
    (0x1C, 0x12, "u16 result flags", "6a0283c610566a12"),
)

CHIT_RESULT_VTABLE = 0xF48AA0
VTABLE_SLOTS = (
    (0x00, 0x74F9D0, "class descriptor"),
    (0x04, 0x74FD80, "destructor"),
    (0x08, 0x401B20, "constant-false stub"),
    (0x0C, 0x5E6230, "sizeof stub"),
    (0x10, 0x74F9C0, "get wire id"),
    (0x14, 0x74FF20, "factory"),
    (0x18, 0x750040, "serializer"),
    (0x1C, 0x750770, "inbound handler"),
    (0x20, 0x710440, "precondition, always true"),
)

STRIDE_PROOFS = (
    (0x74F5B3, "c1f805", "sar eax,5 turns a byte length into an element count"),
    (0x74F686, "83c320", "add ebx,0x20 advances exactly one element"),
)

SIGNED_COMPARE_SITES = (
    ("CHitResult 0x750919", 0x750919, "837b08000f8db3000000"),
    ("CHitResult 0x7509E0", 0x7509E0, "837b08007d32"),
    ("CMissileHitResult 0x751219", 0x751219, "837b08000f8db3000000"),
    ("CMissileHitResult 0x7512E0", 0x7512E0, "837b08007d32"),
)


# ===========================================================================
# B. THE ROUND-90 TABLE.  Transcribed from
# drafts/DAMAGE_MODEL_UNKNOWNS_R90_STATIC.md section 6, every row.
# (lo VA, hi VA, expected file offset of lo, sha256 of [lo, hi), what it pins)
# ===========================================================================
R90_SPANS = (
    (0x5F3E20, 0x5F4070, 0x1F3220,
     "FD8CE6B0298E3A46C3AE1760CA71C6D1F60E45BC02CC60D2C2046A03EBA1C3CA",
     "VitalData collection READER incl. the version compare at 0x5F3EFC"),
    (0x5F38F0, 0x5F39F0, 0x1F2CF0,
     "1AB157252E6D08ACD4F9BFF399C43636E48E35D6CF0281F97AD7AA81A47F36A1",
     "VitalData collection WRITER (version is obj+0x10, tag 0x0B)"),
    (0x5F3840, 0x5F38F0, 0x1F2C40,
     "AE0195A6790A0788463351378C1A68677FA3099D46F761DA344FC17AB9BE3F5E",
     "dispatch loop: gate vtable+0x20 then handler vtable+0x1C"),
    (0x5F3DF0, 0x5F3E11, 0x1F31F0,
     "7B932CD7C54512C0359344D998E7C7ADFDBF6CB790E6B1FC4CD57C8080D35772",
     "RegisterVitalPrototype"),
    (0x5E3260, 0x5E3312, 0x1E2660,
     "2BAAA07EC0DCDBCB52BBAE9AF46A75F070A6136F879726CAE303E880CBCB0DD3",
     "registry singleton accessor [0x1081C44]"),
    (0x5E2E00, 0x5E2E70, 0x1E2200,
     "8C781596A55336DDFEDAB010CD067D3A547E0AC9B9C12E6FC9E62508D3FFCD78",
     "CreateById through the prototype's vtable+0x14"),
    (0x731380, 0x731400, 0x330780,
     "1C65776A35BEA6BE5F5F61B036D8446004C59BBEC971FD65CB5F32536A3A2F6A",
     "map lookup on a u16 key: a tree search, not an allowlist"),
    (0x74F940, 0x74F9C0, 0x34ED40,
     "6A9DFA1B75E5DDA568C1EBABCE86007DA4F76228241099CAC27DB74EDB9F16ED",
     "CHitResult ctor, where the version byte is set to 0"),
    (0x74F9E0, 0x74FA60, 0x34EDE0,
     "22A6C7D6D37C96110C928F0E68536A4CCC5E084520B1468E8119EC174ABF23A2",
     "CMissileHitResult ctor (version 0 as well)"),
    (0x755014, 0x755060, 0x354414,
     "30DF114FCDCEB5CCB82FECD3E721C87B812EFA85B4E75F2C81B59854B8FFD8FE",
     "the prototype registration of CHitResult/CMissileHitResult"),
    (0x750770, 0x750EC0, 0x34FB70,
     "151E5425155D5A5DF6F1944F88FA2C041C6EA74DC8A69C8F907A54A807B5AF70",
     "the whole inbound handler (the Q3 and Q4 evidence)"),
    (0x5CAE00, 0x5CAE2B, 0x1CA200,
     "63C9A17B0EE0BD042C238323D8239E59AF58CFAE691D968427B3F9A2DA8675BC",
     "the gate that header field 2 feeds"),
    (0x702A10, 0x702A22, 0x301E10,
     "626C50DF2FA55EFB2D78702188DDA3AF40127092D27F0BD6141EBB46B897CA36",
     "id == 0 returns NULL: the core of 'zero is inert'"),
    (0xF48AA0, 0xF48AC4, 0xB46EA0,
     "5C02749311D280D7D6EA541EED91968C7C37E1EC6A07429D893A31BAB03D0546",
     "CHitResult vtable, all nine slots"),
    (0xF48AC4, 0xF48AE8, 0xB46EC4,
     "99D4FECE1CD34F3C1E32405CB2FD01F381049004FBEBC6217F30A5E9D0C51B2B",
     "CMissileHitResult vtable, all nine slots"),
    (0x710440, 0x710445, 0x30F840,
     "F4C6D7AE520F88AECB3EA65952E885437FA4A6CE4B5C3439A161D1C5D8E42863",
     "the stub `mov al,1 ; ret 4`: the precondition is always true"),
)

# (VA, expected file offset, bytes, what it pins)
R90_POINTS = (
    (0x5F3EE9, 0x1F32E9, "6a0b", "the tag byte of the version field"),
    (0x5F3EFC, 0x1F32FC, "3a4e10", "cmp cl,[esi+0x10]: the version compare"),
    (0x5F3F01, 0x1F3301, "7436", "the 'versions match' branch"),
    (0x74F979, 0x34ED79, "884610", "CHitResult stores al into +0x10"),
    (0x74F968, 0x34ED68, "33c0", "... and al was zeroed here"),
    (0x5ED71E, 0x1ECB1E, "c646100a", "cross-check: SelectActorVital is 10"),
    (0x7389A0, 0x337DA0, "884810", "cross-check: UpdateNPCAppearVital is 0"),
    (0x5F3EA1, 0x1F32A1, "e8baf3feff", "the reader calls the registry"),
    (0x5F3EA8, 0x1F32A8, "e853effeff", "... and then constructs by id"),
    (0x755048, 0x354448, "e8a3ede9ff", "CHitResult is registered here"),
    (0x75501E, 0x35441E, "6a48", "the registered prototype is 0x48 bytes"),
    (0x5F3888, 0x1F2C88, "8b4220", "the dispatch gate slot vtable+0x20"),
    (0x5F38AE, 0x1F2CAE, "8b421c", "the handler slot vtable+0x1C"),
    (0x710440, 0x30F840, "b001c20400", "the gate returns true unconditionally"),
    (0x7507C3, 0x34FBC3, "7425", "a missing performer does NOT return"),
    (0x7507FE, 0x34FBFE, "751f", "field 3 != 0xEA7A takes the ordinary path"),
    (0x750D45, 0x350145, "7568", "the gate in front of the on-screen number"),
    (0x702A1A, 0x301E1A, "33c0", "a zero id resolves to NULL"),
    (0x750E0A, 0x35020A, "743c", "field 4 == 0 skips a second FX, no return"),
    (0x750E72, 0x350272, "7421",
     "fields 2 and 3 both zero skip 0x5CE010 entirely"),
    (0x7509DA, 0x34FDDA, "0f84770200 00".replace(" ", ""),
     "entry flag bit 0 gates the whole reaction block"),
)


# ===========================================================================
# C. Extra image facts the module's own constants are held to.
# ===========================================================================
CHIT_RESULT_NAME = "CHitResult"
CTOR_VERSION_BLOCK_VA = 0x74F968
CTOR_VERSION_BLOCK = "33c0884604894608c7066c6df80089460c884610"
REGISTRATION_THUNK_VA = 0xC0C180
REGISTRATION_THUNK = "68f8b5f000e8f6fec8ff8bc8e86ffbc8ff66a3e4a20801c3"
GET_ID_STUB_VA = 0x74F9C0
GET_ID_STUB = "66a1e4a20801c3"
SIZEOF_STUB_VA = 0x5E6230
SIZEOF_STUB = "b848000000c3"
ARRAY_CALL_SITE = 0x75009F
REGISTER_PROTOTYPE_VA = 0x5F3DF0
REGISTRATION_CTOR_CALL = 0x75503A

# Anchor -> the section its VA must live in.  chit_result_sizeof is a size, not
# an address, and chit_result_id_global lives in uninitialised .data, so both
# are checked separately below.
ANCHOR_SECTION = {
    "chit_result_name_literal": ".rdata",
    "chit_result_registration_thunk": ".text",
    "chit_result_vtable": ".rdata",
    "chit_result_ctor": ".text",
    "chit_result_serializer": ".text",
    "chit_result_inbound_handler": ".text",
    "cmissile_hit_result_vtable": ".rdata",
    "vital_collection_reader": ".text",
    "vital_collection_writer": ".text",
    "vital_version_tag_site": ".text",
    "vital_version_compare_site": ".text",
    "chit_result_ctor_version_zero": ".text",
    "vital_registry_singleton": ".text",
    "vital_create_by_id": ".text",
    "vital_id_map_lookup": ".text",
    "chit_result_prototype_registration": ".text",
    "vital_dispatch_gate_stub": ".text",
    "damage_signed_compare_hit": ".text",
    "damage_number_gate": ".text",
    "header_field2_lookup": ".text",
    "header_field2_gate": ".text",
    "header_field4_skip": ".text",
    "entry_flag_bit0_reaction_gate": ".text",
    "performer_not_found_does_not_return": ".text",
}

# The composed PC layout, measured here rather than imported, so a drift in the
# module's own constants cannot hide behind them.
PC_ENVELOPE_SIZE = 10        # 0x12 id (3) + 0x14 errdata (5) + 0x08 version (2)
PC_BASE_MASK_AT = 10         # tag byte
PC_VITAL_COUNT_AT = 12       # tag byte
PC_VITAL_ID_AT = 15          # tag byte
PC_VITAL_VERSION_AT = 18     # tag byte
PC_PAYLOAD_AT = 20
EXPECT_HEADER_WIRE_SIZE = 22
EXPECT_COUNT_WIRE_SIZE = 3
EXPECT_ENTRY_WIRE_SIZE = 37
EXPECT_PAYLOAD_WIRE_SIZE = 62
EXPECT_PC_SIZE = 84
EXPECT_FRAME_SIZE = 95
PIN_KEYS = ("damage_wire", "flags", "pc_size", "pc_sha256",
            "frame_size", "frame_sha256")


# ===========================================================================
# Guard machinery.
# ===========================================================================
FAILURES = []
GATE_FAILURES = []
NOTES = []
COUNTS = {"run": 0, "passed": 0, "skipped": 0}
_IN_GATE = [False]


def emit(line):
    if not WANT_JSON:
        print(line)


def section(title):
    emit("")
    emit("== " + title)


def check(label, cond, detail=""):
    COUNTS["run"] += 1
    ok = bool(cond)
    if ok:
        COUNTS["passed"] += 1
        emit("  PASS  " + label)
    else:
        FAILURES.append(label)
        if _IN_GATE[0]:
            GATE_FAILURES.append(label)
        emit("  FAIL  " + label + (("  " + detail) if detail else ""))
    return ok


def skip(count, why):
    COUNTS["skipped"] += count
    emit("  SKIP  %d guard(s): %s" % (count, why))


def note(text):
    NOTES.append(text)
    emit("  NOTE  " + text)


def bytes_match(got, want):
    """The single comparison every byte guard goes through, traps included."""
    return got == want


def span_matches(blob, sha):
    """The single comparison every span guard goes through, traps included."""
    return hashlib.sha256(blob).hexdigest().upper() == sha


def flip(blob, index=0):
    """One flipped bit in a COPY.  The image on disk is never written."""
    out = bytearray(blob)
    out[index] ^= 0x01
    return bytes(out)


# ===========================================================================
# PE plumbing.  VA -> file offset exactly as tools/pf_damage_hit_result_static.py
# does it: off = raw_ptr + (VA - ImageBase - section_VA).
# ===========================================================================
DATA = b""
SECS = []
IMAGE_BASE = 0
IMAGE_SHA = ""


def _load_image(path):
    global DATA, SECS, IMAGE_BASE, IMAGE_SHA
    DATA = open(path, "rb").read()
    IMAGE_SHA = hashlib.sha256(DATA).hexdigest().upper()
    lfanew = struct.unpack_from("<I", DATA, 0x3C)[0]
    coff = lfanew + 4
    nsec = struct.unpack_from("<H", DATA, coff + 2)[0]
    optsz = struct.unpack_from("<H", DATA, coff + 16)[0]
    opt = coff + 20
    IMAGE_BASE = struct.unpack_from("<I", DATA, opt + 28)[0]
    sect = opt + optsz
    for index in range(nsec):
        off = sect + index * 40
        name = DATA[off:off + 8].rstrip(b"\0").decode("latin1")
        vsize, vaddr, rsize, rptr = struct.unpack_from("<IIII", DATA, off + 8)
        SECS.append((name, vaddr, vsize, rptr, rsize))


def va2off(va):
    rel = va - IMAGE_BASE
    for _name, vaddr, vsize, rptr, rsize in SECS:
        if vaddr <= rel < vaddr + max(vsize, rsize):
            return rptr + (rel - vaddr)
    return None


def sec_of(va):
    rel = va - IMAGE_BASE
    for name, vaddr, vsize, _rptr, rsize in SECS:
        if vaddr <= rel < vaddr + max(vsize, rsize):
            return name
    return None


def has_raw(va):
    """True when the VA is backed by bytes in the file, not just by an RVA."""
    rel = va - IMAGE_BASE
    for _name, vaddr, _vsize, rptr, rsize in SECS:
        if vaddr <= rel < vaddr + rsize:
            return rptr + (rel - vaddr) < len(DATA)
    return False


def rd(va, count):
    off = va2off(va)
    return DATA[off:off + count] if off is not None else b""


def span(lo, hi):
    return rd(lo, hi - lo)


def dw(va):
    raw = rd(va, 4)
    return struct.unpack("<I", raw)[0] if len(raw) == 4 else None


def cstr(va, maxn=64):
    raw = rd(va, maxn)
    zero = raw.find(b"\0")
    return raw[:zero].decode("latin1") if zero >= 0 else ""


def rel32_target(va):
    raw = rd(va, 5)
    if len(raw) != 5 or raw[0] != 0xE8:
        return None
    return (va + 5 + struct.unpack("<i", raw[1:])[0]) & 0xFFFFFFFF


def name_id(name):
    """PF-NAMEID: u16 = SUM_i (int16)((signed char)name[i] * (i+1)) mod 2^16."""
    acc = 0
    for index, ch in enumerate(name.encode("latin1")):
        signed = ch if ch < 128 else ch - 256
        acc = (acc + ((signed * (index + 1)) & 0xFFFF)) & 0xFFFF
    return acc


def gbytes(va, hexpat, label):
    want = bytes.fromhex(hexpat)
    return check("%s  [0x%08X %s]" % (label, va, hexpat),
                 bytes_match(rd(va, len(want)), want),
                 "got " + rd(va, len(want)).hex())


def ghas(va, length, hexpat, label):
    want = bytes.fromhex(hexpat)
    return check("%s  [0x%08X..+0x%X has %s]" % (label, va, length, hexpat),
                 want in rd(va, length))


def gspan(lo, hi, sha, label):
    got = hashlib.sha256(span(lo, hi)).hexdigest().upper()
    return check("%s  [0x%08X..0x%08X sha256 %s]" % (label, lo, hi, sha[:16]),
                 span_matches(span(lo, hi), sha), "got " + got[:16])


# ===========================================================================
# Rejection helper: a refusal has to produce NOTHING, not just raise.
# ===========================================================================
def rejects(dm, reason, label, fn, *args, **kwargs):
    produced = None
    message = ""
    try:
        produced = fn(*args, **kwargs)
    except dm.DamageModelValidationError as exc:
        message = str(exc)
    first = message.split(":")[0].strip()
    return check(
        "rejection %s emits no bytes (%s)" % (reason, label),
        produced is None and first == reason,
        "produced=%r message=%r" % (produced, message),
    )


def main():
    # ---------------------------------------------------------------- header
    emit("PF HYP-PF-024 / DAMAGE-ENCODER-001 offline verifier")
    emit("binary          = %s" % (BIN if HAVE_IMAGE else "(not found)"))
    if HAVE_IMAGE:
        _load_image(BIN)
        emit("binary SHA-256  = %s" % IMAGE_SHA)
    emit("module          = src/pirateforce_foundation/damage_model_hypothesis.py")
    emit("scenario        = scenarios/damage_model_hypothesis_hit_sweep.json")

    # ================================================ A. THE REGRESSION GATE
    section("A. REGRESSION GATE - reproduce what earlier rounds published")
    _IN_GATE[0] = True
    if not HAVE_IMAGE:
        gate_guards = (
            4
            + 2 + len(HEADER_EMISSION)
            + 3 + 1 + len(ELEMENT_EMISSION)
            + len(VTABLE_SLOTS) + 1
            + len(STRIDE_PROOFS) + 1
            + len(SIGNED_COMPARE_SITES) + 2
        )
        skip(gate_guards,
             "no client image handed in; a repository gate must not depend on "
             "a file outside the repository")
    else:
        check("the image is the pinned client image (sha256)",
              IMAGE_SHA == EXPECT_SHA, IMAGE_SHA)
        check("ImageBase == 0x400000", IMAGE_BASE == EXPECT_IMAGE_BASE)
        check(".text virtual start == 0x401000",
              IMAGE_BASE + [s for s in SECS if s[0] == ".text"][0][1]
              == EXPECT_TEXT_VA)
        check("image size == %d bytes" % EXPECT_IMAGE_SIZE,
              len(DATA) == EXPECT_IMAGE_SIZE, str(len(DATA)))

        gbytes(SERIALIZER_VA, SERIALIZER_BYTES,
               "serializer 0x750040 write branch, byte for byte")
        gspan(SERIALIZER_SPAN[0], SERIALIZER_SPAN[1], SERIALIZER_SPAN[3],
              "serializer 0x750040 whole-function span")
        for off, tag, kind, pattern in HEADER_EMISSION:
            ghas(SERIALIZER_VA, 0x70, pattern,
                 "header +0x%02X goes out with tag 0x%02X (%s)"
                 % (off, tag, kind))

        gbytes(ARRAY_WRITE_VA, ARRAY_WRITE_PROLOGUE,
               "array writer 0x74F5A0 prologue, byte for byte")
        gspan(ARRAY_WRITE_SPAN[0], ARRAY_WRITE_SPAN[1], ARRAY_WRITE_SPAN[3],
              "array writer 0x74F5A0 whole-function span")
        gbytes(ARRAY_COUNT_BYTES[0], ARRAY_COUNT_BYTES[1],
               "the element count is a u16 with tag 0x12")
        gbytes(ELEMENT_CHAIN_VA, ELEMENT_CHAIN_BYTES,
               "the whole per-element emission chain, byte for byte")
        for off, tag, kind, pattern in ELEMENT_EMISSION:
            ghas(ELEMENT_CHAIN_VA, 0x50, pattern,
                 "element +0x%02X goes out with tag 0x%02X (%s)"
                 % (off, tag, kind))

        for off, want, what in VTABLE_SLOTS:
            check("vtable 0xF48AA0 +0x%02X (%s) == 0x%08X"
                  % (off, what, want),
                  dw(CHIT_RESULT_VTABLE + off) == want,
                  "got 0x%08X" % (dw(CHIT_RESULT_VTABLE + off) or 0))
        check("the vtable is exactly nine slots: +0x24 starts CMissileHitResult's",
              CHIT_RESULT_VTABLE + 0x24 == 0xF48AC4
              and dw(0xF48AC4 + 0x18) == 0x750110
              and dw(0xF48AC4 + 0x1C) == 0x750EC0
              and dw(0xF48AC4 + 0x20) == 0x710440)

        for va, pattern, what in STRIDE_PROOFS:
            gbytes(va, pattern, "STRIDE: " + what)
        shift = rd(0x74F5B5, 1)[0]
        step = rd(0x74F688, 1)[0]
        check("the two stride proofs agree: 1 << %d == %d == 32"
              % (shift, step), (1 << shift) == step == 32)

        for what, va, pattern in SIGNED_COMPARE_SITES:
            gbytes(va, pattern,
                   "%s: cmp dword ptr [ebx+8],0 then a SIGNED jge" % what)
        check("the near branches are jge (0F 8D), not jae (0F 83)",
              rd(0x750919 + 4, 2) == b"\x0f\x8d"
              and rd(0x751219 + 4, 2) == b"\x0f\x8d")
        check("the short branches are jge (7D), not jae (73)",
              rd(0x7509E0 + 4, 1) == b"\x7d"
              and rd(0x7512E0 + 4, 1) == b"\x7d")
    _IN_GATE[0] = False

    if GATE_FAILURES:
        emit("")
        emit("REGRESSION GATE FAILED: %d guard(s) drifted." % len(GATE_FAILURES))
        for item in GATE_FAILURES:
            emit("  - " + item)
        emit("Nothing new is announced.  Everything downstream of this gate "
             "rests on the drifted bytes.")
        return 2

    # ============================================ B. THE ROUND-90 BYTE TABLE
    section("B. round-90 static table (16 ranges + 21 point-byte guards)")
    if not HAVE_IMAGE:
        skip(2 * len(R90_SPANS) + 2 * len(R90_POINTS), "no client image")
    else:
        for lo, hi, off, sha, what in R90_SPANS:
            check("range 0x%08X..0x%08X maps to file offset 0x%06X (%s)"
                  % (lo, hi, off, what), va2off(lo) == off,
                  "got %r" % (va2off(lo),))
            gspan(lo, hi, sha, "range 0x%08X..0x%08X pins %s" % (lo, hi, what))
        for va, off, hexpat, what in R90_POINTS:
            check("point 0x%08X maps to file offset 0x%06X" % (va, off),
                  va2off(va) == off, "got %r" % (va2off(va),))
            gbytes(va, hexpat, "point pins " + what)

    # ================================================ C. MODULE VS THE IMAGE
    section("C. the module's constants against the image")
    from pirateforce_foundation import damage_model_hypothesis as dm  # noqa: E402
    from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

    if not HAVE_IMAGE:
        skip(26 + len(ANCHOR_SECTION) + len(HEADER_EMISSION)
             + len(ELEMENT_EMISSION), "no client image")
    else:
        check("the literal at 0x%08X is 'CHitResult'"
              % dm.STATIC_ANCHORS["chit_result_name_literal"],
              cstr(dm.STATIC_ANCHORS["chit_result_name_literal"])
              == CHIT_RESULT_NAME)
        computed = name_id(CHIT_RESULT_NAME)
        check("CHIT_RESULT_VITAL_ID == PF-NAMEID hash('CHitResult') == 0x%04X"
              % computed,
              computed == dm.CHIT_RESULT_VITAL_ID == 0x16F7,
              "module=0x%04X computed=0x%04X"
              % (dm.CHIT_RESULT_VITAL_ID, computed))
        gbytes(REGISTRATION_THUNK_VA, REGISTRATION_THUNK,
               "the registration thunk hashes the literal into the id global")
        check("the thunk stores the id into STATIC_ANCHORS"
              "['chit_result_id_global']",
              struct.unpack("<I", rd(REGISTRATION_THUNK_VA + 19, 4))[0]
              == dm.STATIC_ANCHORS["chit_result_id_global"])
        gbytes(GET_ID_STUB_VA, GET_ID_STUB,
               "get-id stub is `mov ax,[id global] ; ret`")
        check("the get-id stub reads the same id global",
              struct.unpack("<I", rd(GET_ID_STUB_VA + 2, 4))[0]
              == dm.STATIC_ANCHORS["chit_result_id_global"])
        check("the id global lives in .data",
              sec_of(dm.STATIC_ANCHORS["chit_result_id_global"]) == ".data")

        gbytes(CTOR_VERSION_BLOCK_VA, CTOR_VERSION_BLOCK,
               "ctor: al is zeroed and nothing touches it before the +0x10 store")
        check("CHIT_RESULT_VITAL_VERSION == 0, read out of ctor 0x74F979",
              dm.CHIT_RESULT_VITAL_VERSION == 0
              and rd(dm.STATIC_ANCHORS["chit_result_ctor_version_zero"], 3)
              == bytes.fromhex("884610")
              and rd(CTOR_VERSION_BLOCK_VA, 2) == bytes.fromhex("33c0"))
        check("the reader compares that byte at "
              "STATIC_ANCHORS['vital_version_compare_site']",
              rd(dm.STATIC_ANCHORS["vital_version_compare_site"], 3)
              == bytes.fromhex("3a4e10"))
        check("the writer emits it with tag 0x0B at "
              "STATIC_ANCHORS['vital_version_tag_site']",
              rd(dm.STATIC_ANCHORS["vital_version_tag_site"], 2)
              == bytes.fromhex("6a0b")
              and dm.TAG_U8 == 0x0B)

        gbytes(SIZEOF_STUB_VA, SIZEOF_STUB, "the sizeof stub returns 0x48")
        check("STATIC_ANCHORS['chit_result_sizeof'] == the stub's immediate",
              struct.unpack("<I", rd(SIZEOF_STUB_VA + 1, 4))[0]
              == dm.STATIC_ANCHORS["chit_result_sizeof"] == 0x48)
        check("the registered prototype is allocated with that same size",
              rd(0x75501E, 2) == bytes([0x6A, 0x48]))
        check("STATIC_ANCHORS['chit_result_prototype_registration'] calls "
              "RegisterVitalPrototype",
              rel32_target(dm.STATIC_ANCHORS
                           ["chit_result_prototype_registration"])
              == REGISTER_PROTOTYPE_VA)
        check("the object registered there was built by "
              "STATIC_ANCHORS['chit_result_ctor']",
              rel32_target(REGISTRATION_CTOR_CALL)
              == dm.STATIC_ANCHORS["chit_result_ctor"])
        check("the reader reaches the registry and CreateById",
              rel32_target(0x5F3EA1)
              == dm.STATIC_ANCHORS["vital_registry_singleton"]
              and rel32_target(0x5F3EA8)
              == dm.STATIC_ANCHORS["vital_create_by_id"])
        check("the ctor installs STATIC_ANCHORS['chit_result_vtable']",
              rd(0x74F98E, 6)
              == bytes.fromhex("c706")
              + struct.pack("<I", dm.STATIC_ANCHORS["chit_result_vtable"]))
        check("vtable +0x18 == STATIC_ANCHORS['chit_result_serializer']",
              dw(dm.STATIC_ANCHORS["chit_result_vtable"] + 0x18)
              == dm.STATIC_ANCHORS["chit_result_serializer"])
        check("vtable +0x1C == STATIC_ANCHORS['chit_result_inbound_handler']",
              dw(dm.STATIC_ANCHORS["chit_result_vtable"] + 0x1C)
              == dm.STATIC_ANCHORS["chit_result_inbound_handler"])
        check("vtable +0x20 == STATIC_ANCHORS['vital_dispatch_gate_stub']",
              dw(dm.STATIC_ANCHORS["chit_result_vtable"] + 0x20)
              == dm.STATIC_ANCHORS["vital_dispatch_gate_stub"])
        check("STATIC_ANCHORS['cmissile_hit_result_vtable'] is the next vtable",
              dm.STATIC_ANCHORS["cmissile_hit_result_vtable"]
              == dm.STATIC_ANCHORS["chit_result_vtable"] + 0x24)
        check("HIT_ARRAY_WRITE_VA is what the serializer calls for +0x2C",
              rel32_target(ARRAY_CALL_SITE) == dm.HIT_ARRAY_WRITE_VA
              == ARRAY_WRITE_VA)
        check("HIT_ELEMENT_STRIDE == 32, from both byte proofs",
              dm.HIT_ELEMENT_STRIDE == (1 << rd(0x74F5B5, 1)[0])
              == rd(0x74F688, 1)[0] == 32)
        check("the module's four 'meaning unknown' header offsets are the four "
              "the serializer emits after the performer",
              (dm.HEADER_FIELD2_OFFSET, dm.HEADER_FIELD3_OFFSET,
               dm.HEADER_FIELD4_OFFSET, dm.HEADER_FIELD5_OFFSET)
              == (0x20, 0x22, 0x24, 0x28))
        check("HEADER_PERFORMER_OFFSET / HEADER_ARRAY_OFFSET are the emitted "
              "ones", (dm.HEADER_PERFORMER_OFFSET, dm.HEADER_ARRAY_OFFSET)
              == (0x18, 0x2C))

        module_header = {
            dm.HEADER_PERFORMER_OFFSET: dm.TAG_QWORD,
            dm.HEADER_FIELD2_OFFSET: dm.TAG_U16,
            dm.HEADER_FIELD3_OFFSET: dm.TAG_U16,
            dm.HEADER_FIELD4_OFFSET: dm.TAG_U32,
            dm.HEADER_FIELD5_OFFSET: dm.TAG_U8,
        }
        for off, tag, kind, pattern in HEADER_EMISSION:
            check("module header +0x%02X is tagged 0x%02X, and the image emits "
                  "exactly that (%s)" % (off, tag, kind),
                  module_header.get(off) == tag
                  and bytes.fromhex(pattern) in rd(SERIALIZER_VA, 0x70))
        module_element = {
            dm.HIT_ENTRY_TARGET_OFFSET: dm.TAG_QWORD,
            dm.HIT_ENTRY_DAMAGE_OFFSET: dm.TAG_U32,
            dm.HIT_ENTRY_POSITION_OFFSET: dm.TAG_F32,
            dm.HIT_ENTRY_YAW_OFFSET: dm.TAG_F32,
            dm.HIT_ENTRY_FLAGS_OFFSET: dm.TAG_U16,
        }
        for off, tag, kind, pattern in ELEMENT_EMISSION:
            check("module element +0x%02X is tagged 0x%02X, and the image emits "
                  "exactly that (%s)" % (off, tag, kind),
                  module_element.get(off) == tag
                  and bytes.fromhex(pattern) in rd(ELEMENT_CHAIN_VA, 0x50))

        for anchor in sorted(ANCHOR_SECTION):
            va = dm.STATIC_ANCHORS[anchor]
            check("STATIC_ANCHORS[%r] = 0x%08X points at real bytes in %s"
                  % (anchor, va, ANCHOR_SECTION[anchor]),
                  sec_of(va) == ANCHOR_SECTION[anchor] and has_raw(va)
                  and len(rd(va, 1)) == 1,
                  "section=%r" % (sec_of(va),))

    check("every STATIC_ANCHORS key is either a checked VA or the sizeof",
          set(dm.STATIC_ANCHORS) - set(ANCHOR_SECTION)
          == {"chit_result_sizeof", "chit_result_id_global"},
          str(sorted(set(dm.STATIC_ANCHORS) - set(ANCHOR_SECTION))))

    # ====================================== D. THE MODULE AGAINST ITSELF
    section("D. offline composition: the module against its own pins")
    legacy = load_legacy(LEGACY_PATH)
    profile = dm.load_damage_model_hypothesis_scenario(SCENARIO_PATH)
    check("the scenario file loads and yields the module's own profile object",
          profile is dm._PROFILE
          and profile.scenario_id == dm.DAMAGE_MODEL_SCENARIO_ID
          and profile.hypothesis_id == dm.DAMAGE_MODEL_HYPOTHESIS_ID)
    unlock = dm.damage_model_wire_unlock(profile)
    check("the unlock is the hit_sweep profile's own token, by identity",
          unlock is dm._UNLOCK)
    probe = dm.damage_probe_actor(legacy)
    check("the probe identity is the pinned smoke identity 0x10010001/0",
          (probe.identity_lo, probe.identity_hi)
          == (dm.DAMAGE_PROBE_IDENTITY_LO, dm.DAMAGE_PROBE_IDENTITY_HI)
          == (0x10010001, 0))
    check("the probe position is the frozen V135 player spawn",
          (probe.x, probe.y, probe.z)
          == (float(legacy.V135_PLAYER_X), float(legacy.V135_PLAYER_Y),
              float(legacy.V135_PLAYER_Z)))

    actions = dm.build_damage_model_sweep(legacy, probe, unlock, profile)
    check("the sweep is the four pinned steps in the pinned order",
          [a[0] for a in actions]
          == [profile.action_label_prefix + label
              for label in dm.DAMAGE_MODEL_STEP_ORDER]
          == list(dm.DAMAGE_MODEL_ACTION_LABELS))
    rows = dm.validate_damage_model_sweep(legacy, actions, profile)

    composed = {}
    for index, label in enumerate(dm.DAMAGE_MODEL_STEP_ORDER):
        _name, pc, frame, delay = actions[index]
        composed[label] = (pc, frame)
        pin = dm.DAMAGE_MODEL_PINS[label]
        live = {
            "damage_wire": rows[index]["damage_wire"],
            "flags": rows[index]["flags"],
            "pc_size": len(pc),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_size": len(frame),
            "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
        }
        for key in PIN_KEYS:
            check("%s: composed %s reproduces DAMAGE_MODEL_PINS"
                  % (label, key), live[key] == pin[key],
                  "%r != %r" % (live[key], pin[key]))
        check("%s: the delay is the pinned plan" % label,
              delay == (profile.first_delay_seconds if index == 0
                        else profile.spacing_seconds))
        check("%s: the frame is exactly frame_pc(pc)" % label,
              frame == legacy.frame_pc(pc))

    # Widths.  Asserted from the composed bytes, never taken on trust.
    pc0, frame0 = composed[dm.DAMAGE_MODEL_STEP_ORDER[0]]
    decoded = dm.decode_chit_result_frame(pc0)
    body = decoded["vitals"][0]
    entry = body["entries"][0]
    check("envelope: 0x12 id / 0x14 errdata / 0x08 version = %d bytes"
          % PC_ENVELOPE_SIZE,
          pc0[0] == dm.TAG_U16 and pc0[3] == dm.TAG_U32 and pc0[8] == 0x08
          and decoded["envelope_id"] == 0x6E9D
          and decoded["envelope_version"] == dm.RUNTIME_PROTOCOL_RES_VERSION)
    check("the BASE change mask byte selects the VitalData collection (0x02)",
          pc0[PC_BASE_MASK_AT] == dm.TAG_U8
          and pc0[PC_BASE_MASK_AT + 1]
          == dm.BASE_CHANGE_MASK_VITAL_COLLECTION == 0x02)
    check("the DERIVED change mask is present and zero (the round-82 lesson)",
          pc0[-2] == dm.TAG_U8
          and pc0[-1] == dm.DERIVED_CHANGE_MASK_ABSENT == 0)
    check("the vital collection carries exactly one CHitResult v0",
          pc0[PC_VITAL_COUNT_AT] == dm.TAG_U16
          and struct.unpack("<H", pc0[PC_VITAL_COUNT_AT + 1:
                                      PC_VITAL_COUNT_AT + 3])[0] == 1
          and pc0[PC_VITAL_ID_AT] == dm.TAG_U16
          and struct.unpack("<H", pc0[PC_VITAL_ID_AT + 1:
                                      PC_VITAL_ID_AT + 3])[0]
          == dm.CHIT_RESULT_VITAL_ID
          and pc0[PC_VITAL_VERSION_AT] == dm.TAG_U8
          and pc0[PC_VITAL_VERSION_AT + 1] == dm.CHIT_RESULT_VITAL_VERSION)
    check("WIDTH header == 22 bytes",
          body["header_wire_size"] == EXPECT_HEADER_WIRE_SIZE
          == dm.CHIT_RESULT_HEADER_WIRE_SIZE)
    check("WIDTH hit-entry count == 3 bytes (tag 0x12 + u16)",
          pc0[PC_PAYLOAD_AT + EXPECT_HEADER_WIRE_SIZE] == dm.TAG_U16
          and dm.HIT_COUNT_WIRE_SIZE == EXPECT_COUNT_WIRE_SIZE)
    check("WIDTH entry == 37 bytes",
          entry["wire_size"] == EXPECT_ENTRY_WIRE_SIZE
          == dm.HIT_ELEMENT_WIRE_SIZE)
    check("WIDTH payload == 62 bytes (22 + 3 + 37)",
          dm.CHIT_RESULT_PAYLOAD_WIRE_SIZE == EXPECT_PAYLOAD_WIRE_SIZE
          == EXPECT_HEADER_WIRE_SIZE + EXPECT_COUNT_WIRE_SIZE
          + EXPECT_ENTRY_WIRE_SIZE
          and len(pc0) - PC_PAYLOAD_AT - 2 == EXPECT_PAYLOAD_WIRE_SIZE)
    check("WIDTH pc == 84 bytes", len(pc0) == EXPECT_PC_SIZE)
    check("WIDTH frame == 95 bytes", len(frame0) == EXPECT_FRAME_SIZE)
    check("the entry is one 37-byte element inside a 32-byte-stride array",
          body["entry_count"] == dm.HIT_ENTRY_COUNT_PINNED == 1
          and dm.HIT_ELEMENT_STRIDE == 32)
    check("performer and target are the same identity on every step",
          len({r["target_identity"] for r in rows}) == 1
          and rows[0]["target_identity"] == dm.actor_identity(probe))

    # The eight PC-offset constants in the module are dead code AND wrong.
    module_offsets = (
        dm.BASE_CHANGE_MASK_OFFSET, dm.VITAL_COUNT_TAG_OFFSET,
        dm.VITAL_COUNT_OFFSET, dm.VITAL_ID_TAG_OFFSET, dm.VITAL_ID_OFFSET,
        dm.VITAL_VERSION_TAG_OFFSET, dm.VITAL_VERSION_OFFSET,
        dm.CHIT_RESULT_PAYLOAD_OFFSET,
    )
    real_offsets = (PC_BASE_MASK_AT + 1, PC_VITAL_COUNT_AT,
                    PC_VITAL_COUNT_AT + 1, PC_VITAL_ID_AT, PC_VITAL_ID_AT + 1,
                    PC_VITAL_VERSION_AT, PC_VITAL_VERSION_AT + 1,
                    PC_PAYLOAD_AT)
    if module_offsets != real_offsets:
        note("FINDING (report, do not fix here): the eight PC-offset constants "
             "BASE_CHANGE_MASK_OFFSET..CHIT_RESULT_PAYLOAD_OFFSET in "
             "damage_model_hypothesis.py are each exactly one less than the "
             "composed byte position: module=%s real=%s.  They are unused by "
             "every code path in the repository, so no composed byte is "
             "affected, but anyone indexing a PC with them reads one byte early."
             % (module_offsets, real_offsets))

    # The formula.
    check("compute_damage(MOB_WEAK, PLAYER_BASELINE) == -63",
          dm.compute_damage(dm.ATTACKER_MOB_WEAK,
                            dm.DEFENDER_PLAYER_BASELINE) == -63)
    check("compute_damage(MOB_STRONG, PLAYER_BASELINE) == -379",
          dm.compute_damage(dm.ATTACKER_MOB_STRONG,
                            dm.DEFENDER_PLAYER_BASELINE) == -379)
    floor_defender = dm.DamageProfile("FLOOR_DEFENDER", 100, 0, 0, 500, 0)
    check("the MIN_HIT floor case yields exactly -1 (a hit, never a heal)",
          dm.compute_damage(dm.ATTACKER_MOB_WEAK, floor_defender) == -1
          and dm.MIN_HIT == 1)
    check("attack/defence are the pinned linear forms",
          dm.compute_attack(dm.ATTACKER_MOB_WEAK)
          == dm.ATK_BASE + dm.K_ATK_STR * 3 + dm.K_ATK_LV * 1
          and dm.compute_defense(dm.DEFENDER_PLAYER_BASELINE)
          == dm.DEF_BASE
          + dm.K_DEF_CON * dm.DEFENDER_PLAYER_BASELINE.ability_con
          + dm.K_DEF_LV * dm.DEFENDER_PLAYER_BASELINE.level)
    check("the formula uses no randomness in phase 1",
          dm.JITTER_PCT_MAX == 0
          and dm.compute_damage(dm.ATTACKER_MOB_WEAK,
                                dm.DEFENDER_PLAYER_BASELINE)
          == dm.compute_damage(dm.ATTACKER_MOB_WEAK,
                               dm.DEFENDER_PLAYER_BASELINE))
    check("the sweep carries exactly one MISS control frame, damage 0 flags 0",
          [r["label"] for r in rows
           if r["damage_wire"] == 0 and r["flags"] == dm.FLAGS_MISS]
          == list(dm.DAMAGE_MODEL_MISS_STEP_LABELS))

    # The scenario file.
    raw = json.loads(open(SCENARIO_PATH, encoding="utf-8").read())
    per_step = raw["target"]["per_step"]
    for label in dm.DAMAGE_MODEL_STEP_ORDER:
        for key in PIN_KEYS:
            check("scenario file pin %s.%s equals the module's" % (label, key),
                  per_step[label][key] == dm.DAMAGE_MODEL_PINS[label][key],
                  "%r != %r" % (per_step[label][key],
                                dm.DAMAGE_MODEL_PINS[label][key]))
    check("the scenario file declares the same plan the module carries",
          raw["id"] == dm.DAMAGE_MODEL_SCENARIO_ID
          and raw["hypothesis_id"] == dm.DAMAGE_MODEL_HYPOTHESIS_ID
          and raw["dispatch"]["step_order"] == list(dm.DAMAGE_MODEL_STEP_ORDER)
          and raw["dispatch"]["miss_steps"]
          == list(dm.DAMAGE_MODEL_MISS_STEP_LABELS)
          and raw["dispatch"]["frames_per_accepted_request"]
          == len(dm.DAMAGE_MODEL_STEP_ORDER)
          and raw["dispatch"]["action_labels"]
          == list(dm.DAMAGE_MODEL_ACTION_LABELS))
    check("the scenario file declares the same wire the module composes",
          raw["wire"]["chit_result_vital_id"] == dm.CHIT_RESULT_VITAL_ID
          and raw["wire"]["chit_result_vital_version"]
          == dm.CHIT_RESULT_VITAL_VERSION
          and raw["wire"]["header_wire_size"] == EXPECT_HEADER_WIRE_SIZE
          and raw["wire"]["hit_element_wire_size"] == EXPECT_ENTRY_WIRE_SIZE
          and raw["wire"]["hit_element_stride"] == 32
          and raw["wire"]["hit_entry_count"] == 1)
    check("scenario ctor_version_store_site == the proven ctor store 0x74F979",
          raw["wire"]["chit_result_ctor_version_store_site"]
          == dm.STATIC_ANCHORS["chit_result_ctor_version_zero"] == 0x74F979)
    check("scenario reaction_pass_gate_site == the proven bit-0 gate 0x7509DA",
          raw["wire"]["flag_field"]["reaction_pass_gate_site"]
          == dm.STATIC_ANCHORS["entry_flag_bit0_reaction_gate"] == 0x7509DA)
    check("scenario signed_compare_sites carries the proven 0x750919",
          dm.STATIC_ANCHORS["damage_signed_compare_hit"]
          in raw["wire"]["damage_field"]["signed_compare_sites"])
    declared_sites = [
        ("chit_result_vital_version_compare_site",
         raw["wire"]["chit_result_vital_version_compare_site"]),
        ("chit_result_ctor_version_store_site",
         raw["wire"]["chit_result_ctor_version_store_site"]),
        ("flag_field.reaction_pass_gate_site",
         raw["wire"]["flag_field"]["reaction_pass_gate_site"]),
    ] + [("damage_field.signed_compare_sites[%d]" % i, v) for i, v in
         enumerate(raw["wire"]["damage_field"]["signed_compare_sites"])]
    if HAVE_IMAGE:
        check("every byte site the scenario declares is a real .text address",
              all(sec_of(va) == ".text" and has_raw(va)
                  for _key, va in declared_sites),
              str([(k, hex(v), sec_of(v)) for k, v in declared_sites]))
        proven_sites = {
            0x5F3EFC, 0x74F979, 0x7509DA, 0x750919, 0x7509E0, 0x751219,
            0x7512E0,
        }
        stray = [(key, "0x%08X" % va) for key, va in declared_sites
                 if va not in proven_sites]
        if stray:
            note("FINDING (report, do not fix here): %d byte site(s) declared in "
                 "the scenario file (and in _expected_scenario() in the module, "
                 "which is why the exact-tree loader still accepts the file) do "
                 "not equal any site this lane proved: %s.  The version compare "
                 "is 0x5F3EFC = 6242044, not 6242556 = 0x5F40FC (which lands "
                 "inside the base serializer 0x5F4070); the second signed "
                 "compare is 0x7509E0 = 7670240 or 0x751219 = 7672345, not "
                 "7671613 = 0x750F3D.  Both are documentation fields that no "
                 "composed byte depends on." % (len(stray), stray))
    else:
        skip(1, "no client image for the declared-site section check")
    check("the scenario file stays test-only, opt-in and write-free",
          raw["test_only"] is True and raw["production_allowed"] is False
          and dm.production_allowed is False
          and raw["persisted_post_state"]["database_write"] == "none")
    check("the scenario file states whose formula this is",
          raw["our_own_formula_not_the_original_servers"] is True
          and raw["formula"]["owner"] == "this_project_not_the_original_server"
          and raw["formula"]["uses_random"] is False
          and "the_original_server_damage_formula_which_this_project_cannot_"
              "recover" in raw["nonclaims"])

    # ==================== D2. THE npc_target PROFILE (DAMAGE-NPC-TARGET-001)
    section("D2. the npc_target profile against its own pins")
    npc_profile = dm.load_damage_model_hypothesis_scenario(NPC_SCENARIO_PATH)
    check("the npc scenario file loads and yields the module's npc profile "
          "object",
          npc_profile is dm._PROFILE_NPC
          and npc_profile.scenario_id == dm.DAMAGE_MODEL_NPC_SCENARIO_ID
          and npc_profile.hypothesis_id == dm.DAMAGE_MODEL_HYPOTHESIS_ID)
    npc_unlock = dm.damage_model_wire_unlock(npc_profile)
    check("the npc unlock is the npc profile's own token, by identity",
          npc_unlock is dm._UNLOCK_NPC and npc_unlock is not dm._UNLOCK)
    check("both profiles hold the SAME step tuple object, so the plan cannot "
          "fork",
          npc_profile.step_order is profile.step_order
          is dm.DAMAGE_MODEL_STEP_ORDER)
    check("the npc target is the fixed placement identity 0x2001/0 and the "
          "probe performer differs from it",
          dm.DAMAGE_NPC_TARGET_IDENTITY_LO == 0x2001
          and dm.DAMAGE_NPC_TARGET_IDENTITY_HI == 0
          and dm.npc_target_identity() == 0x2001
          and dm.actor_identity(probe) != dm.npc_target_identity())
    check("the npc spacing is 15.0 s with first delay 0.0 (photography "
          "headroom, the round-84 lesson)",
          npc_profile.spacing_seconds == 15.0
          and npc_profile.first_delay_seconds == 0.0)
    npc_actions = dm.build_damage_model_sweep(
        legacy, probe, npc_unlock, npc_profile)
    check("the npc sweep is the four pinned steps under the npc labels",
          [a[0] for a in npc_actions]
          == list(dm.DAMAGE_MODEL_NPC_ACTION_LABELS))
    npc_raw = json.loads(open(NPC_SCENARIO_PATH, encoding="utf-8").read())
    for index, label in enumerate(dm.DAMAGE_MODEL_STEP_ORDER):
        _lab, pc, frame, _delay = npc_actions[index]
        pin = dm.DAMAGE_MODEL_PINS_NPC[label]
        file_pin = npc_raw["target"]["per_step"][label]
        check("npc %s: composed bytes reproduce DAMAGE_MODEL_PINS_NPC" % label,
              len(pc) == pin["pc_size"] and len(frame) == pin["frame_size"]
              and hashlib.sha256(pc).hexdigest().upper() == pin["pc_sha256"]
              and hashlib.sha256(frame).hexdigest().upper()
              == pin["frame_sha256"])
        check("npc %s: the module pin and the scenario file pin are the SAME "
              "pin" % label,
              file_pin["pc_sha256"] == pin["pc_sha256"]
              and file_pin["frame_sha256"] == pin["frame_sha256"]
              and file_pin["damage_wire"] == pin["damage_wire"]
              and file_pin["flags"] == pin["flags"])
        check("npc %s: the npc pin DIFFERS from the hit_sweep pin (the target "
              "qword is on the wire)" % label,
              pin["pc_sha256"] != dm.DAMAGE_MODEL_PINS[label]["pc_sha256"])
        read = dm.decode_chit_result_frame(pc)
        body = read["vitals"][0]
        entry = body["entries"][0]
        check("npc %s: performer is the probe player, target is 0x2001, and "
              "they differ" % label,
              body["performer_identity"] == dm.actor_identity(probe)
              and entry["target_identity"] == dm.npc_target_identity()
              and body["performer_identity"] != entry["target_identity"])
    check("the npc scenario file stays test-only, opt-in and write-free",
          npc_raw["test_only"] is True
          and npc_raw["production_allowed"] is False
          and npc_raw["persisted_post_state"]["database_write"] == "none")
    check("the npc scenario file carries the map-membership nonclaim GT-027 "
          "exists to test",
          "that_0x2001_is_registered_in_the_clients_identity_map_at_runtime"
          "_gt_027_tests_exactly_that" in npc_raw["nonclaims"])
    rejects(dm, "wire_unlock_is_for_a_different_profile",
            "the hit_sweep key opens no npc byte",
            dm.build_damage_model_sweep, legacy, probe, unlock, npc_profile)
    rejects(dm, "wire_unlock_is_for_a_different_profile",
            "the npc key opens no hit_sweep byte",
            dm.build_damage_model_sweep, legacy, probe, npc_unlock, profile)
    rejects(dm, "npc_target_identity_not_pinned",
            "an npc sweep whose entry names the performer instead",
            dm.validate_damage_model_sweep, legacy,
            [(a[0], actions[i][1], actions[i][2], a[3])
             for i, a in enumerate(npc_actions)],
            npc_profile)
    rejects(dm, "npc_performer_must_not_be_the_npc_target",
            "an actor whose identity IS the npc placement identity",
            dm.build_damage_model_sweep, legacy,
            dm.DamageModelActor(
                dm.DAMAGE_NPC_TARGET_IDENTITY_LO,
                dm.DAMAGE_NPC_TARGET_IDENTITY_HI,
                probe.x, probe.y, probe.z),
            npc_unlock, npc_profile)

    # ================================== E. EVERY REJECTION PRODUCES NO BYTES
    section("E. every rejection produces no bytes")
    position = (probe.x, probe.y, probe.z)
    identity = dm.actor_identity(probe)
    forged = dm.DamageModelWireUnlock(dm.DAMAGE_MODEL_SCENARIO_ID,
                                      dm.DAMAGE_MODEL_HYPOTHESIS_ID)
    check("the forged unlock compares EQUAL to the real one, so identity is "
          "what defends the lane", forged == dm._UNLOCK
          and forged is not dm._UNLOCK)

    def entry_with(damage=-63, flags=1, yaw=0.0, pos=position,
                   target=identity, key=unlock):
        return dm.encode_hit_entry(legacy, target, damage, pos, yaw, flags, key)

    rejects(dm, "damage_not_integer", "a float damage",
            dm.require_damage_wire_value, -63.0)
    rejects(dm, "damage_not_integer", "a bool damage",
            dm.require_damage_wire_value, True)
    rejects(dm, "damage_not_integer", "a string damage",
            dm.require_damage_wire_value, "-63")
    rejects(dm, "damage_positive_heal_semantics_unknown", "a positive number",
            dm.require_damage_wire_value, 1)
    rejects(dm, "damage_is_int32_min", "INT32_MIN, which abs() cannot negate",
            dm.require_damage_wire_value, dm.INT32_MIN)
    rejects(dm, "damage_below_safe_band", "far below the safe band",
            dm.require_damage_wire_value, -2000000)
    rejects(dm, "damage_outside_scenario_band", "five digits on screen",
            dm.require_scenario_band, -10000)
    rejects(dm, "damage_zero_with_apply_flag", "a miss that asks for reaction",
            dm.require_damage_and_flags_agree, 0, dm.FLAGS_HIT)
    rejects(dm, "damage_nonzero_without_apply_flag", "a number with no reaction",
            dm.require_damage_and_flags_agree, -63, dm.FLAGS_MISS)
    rejects(dm, "flags_knockback_bit_suppresses_the_number",
            "bit 4 hides the number behind _F_KNOCKED_002",
            dm.require_damage_and_flags_agree, -63, 0x0011)
    rejects(dm, "flags_not_u16", "a string flag word", dm.require_flags_value, "1")
    rejects(dm, "flags_not_u16", "a bool flag word", dm.require_flags_value, True)
    rejects(dm, "flags_not_u16", "wider than u16", dm.require_flags_value, 0x10000)
    rejects(dm, "flags_not_u16", "negative", dm.require_flags_value, -1)
    rejects(dm, "flags_forbidden_bit", "bit 7, tested at 0x750A84 and unexplained",
            dm.require_flags_value, 0x0080)
    rejects(dm, "flags_bit_outside_allowed_mask", "bit 1, outside phase 1",
            dm.require_flags_value, 0x0002)
    rejects(dm, "flags_bit_outside_allowed_mask", "bit 4 never rides this lane",
            dm.require_flags_value, dm.FLAGS_BIT_SUPPRESSES_THE_NUMBER)
    rejects(dm, "flags_outside_value_allowlist",
            "bit 3 alone is inside the mask but is not a value we defend",
            dm.require_flags_value, 0x0008)
    rejects(dm, "yaw_not_finite_float32", "NaN", dm._require_pinned_yaw,
            float("nan"))
    rejects(dm, "yaw_not_finite_float32", "infinity", dm._require_pinned_yaw,
            float("inf"))
    rejects(dm, "yaw_not_finite_float32", "not a number at all",
            dm._require_pinned_yaw, "0.0")
    rejects(dm, "yaw_outside_pinned_value", "any angle but the pinned 0.0f",
            entry_with, -63, 1, 1.0)
    rejects(dm, "position_not_from_the_pinned_source", "a list, not a tuple",
            entry_with, -63, 1, 0.0, [probe.x, probe.y, probe.z])
    rejects(dm, "position_not_from_the_pinned_source", "an invented position",
            dm._require_pinned_position, legacy,
            dm.DamageModelActor(probe.identity_lo, probe.identity_hi,
                                probe.x + 1.0, probe.y, probe.z))
    rejects(dm, "target_identity_outside_qword", "a negative identity",
            entry_with, -63, 1, 0.0, position, -1)
    rejects(dm, "target_identity_outside_qword", "wider than a qword",
            entry_with, -63, 1, 0.0, position, 1 << 64)
    rejects(dm, "target_identity_outside_qword", "not an actor at all",
            dm.actor_identity, object())
    rejects(dm, "target_identity_outside_qword", "a selection with no identity",
            dm.resolve_actor, legacy, object())
    rejects(dm, "entry_count_not_pinned", "two entries in one frame",
            dm.encode_chit_result, legacy, identity,
            [entry_with(), entry_with()], unlock)
    rejects(dm, "entry_count_not_pinned", "no entries at all",
            dm.encode_chit_result, legacy, identity, [], unlock)
    rejects(dm, "composed_bytes_do_not_match_the_pin", "an entry of the wrong width",
            dm.encode_chit_result, legacy, identity, [b"\x00" * 36], unlock)
    rejects(dm, "missing_or_forged_wire_unlock",
            "a token that compares equal but is not the one",
            entry_with, -63, 1, 0.0, position, identity, forged)
    rejects(dm, "missing_or_forged_wire_unlock", "no token at all",
            entry_with, -63, 1, 0.0, position, identity, None)
    rejects(dm, "scenario_object_exceeds_allowlist", "any other object",
            dm.require_damage_model_hypothesis_scenario, object())
    rejects(dm, "scenario_object_exceeds_allowlist", "a look-alike profile",
            dm.require_damage_model_hypothesis_scenario,
            dm.DamageModelHypothesisScenario(
                dm.DAMAGE_MODEL_SCENARIO_ID, dm.DAMAGE_MODEL_HYPOTHESIS_ID,
                dm.DAMAGE_MODEL_STEP_ORDER, 1.0,
                dm.DAMAGE_MODEL_FIRST_DELAY_SECONDS,
                dm.DAMAGE_MODEL_ACTION_LABEL_PREFIX))
    rejects(dm, "scenario_file_exceeds_allowlist", "no path",
            dm.load_damage_model_hypothesis_scenario, None)
    rejects(dm, "scenario_file_exceeds_allowlist", "another lane's scenario",
            dm.load_damage_model_hypothesis_scenario, OTHER_SCENARIO_PATH)
    rejects(dm, "scenario_file_exceeds_allowlist", "a path that does not exist",
            dm.load_damage_model_hypothesis_scenario,
            os.path.join(_ROOT, "scenarios", "no_such_scenario.json"))
    rejects(dm, "unknown_step_label", "a negative index", dm.step_plan, -1)
    rejects(dm, "unknown_step_label", "past the end of the plan",
            dm.step_plan, len(dm.DAMAGE_MODEL_STEPS))
    rejects(dm, "unknown_step_label", "a bool index", dm.step_plan, True)
    rejects(dm, "unknown_step_label", "a float index", dm.step_plan, 1.0)
    rejects(dm, "formula_input_outside_declared_domain", "wider than the u16 wire",
            dm.compute_attack,
            dm.DamageProfile("OVER_U16", 0x10000, 0, 0, 0, 0))
    rejects(dm, "formula_input_outside_declared_domain", "a negative input",
            dm.compute_defense, dm.DamageProfile("NEGATIVE", 1, 0, 0, -1, 0))
    rejects(dm, "formula_input_outside_declared_domain", "not a profile",
            dm.compute_damage, "MOB_WEAK", dm.DEFENDER_PLAYER_BASELINE)

    def mutated_sweep(index_to_break, offset, value):
        built = []
        for index, label in enumerate(profile.step_order):
            pc, _frame = dm.make_damage_model_step_response(
                legacy, probe, index, unlock, profile)
            if index == index_to_break:
                buf = bytearray(pc)
                buf[offset:offset + len(value)] = value
                pc = bytes(buf)
            delay = (profile.first_delay_seconds if index == 0
                     else profile.spacing_seconds)
            built.append((profile.action_label_prefix + label, pc,
                          legacy.frame_pc(pc), delay))
        return dm.validate_damage_model_sweep(legacy, built, profile)

    header_field2_value_at = PC_PAYLOAD_AT + 9 + 1
    damage_value_at = PC_PAYLOAD_AT + EXPECT_HEADER_WIRE_SIZE \
        + EXPECT_COUNT_WIRE_SIZE + 9 + 1
    check("the mutation offsets land on the fields they claim to",
          pc0[header_field2_value_at - 1] == dm.TAG_U16
          and pc0[damage_value_at - 1] == dm.TAG_U32
          and struct.unpack("<i", pc0[damage_value_at:
                                      damage_value_at + 4])[0] == -63)
    rejects(dm, "header_reserved_field_nonzero",
            "a non-zero value smuggled into reserved header field 2",
            mutated_sweep, 0, header_field2_value_at, b"\x01\x00")
    rejects(dm, "formula_output_not_reproducible",
            "a legal-looking damage value the formula did not produce",
            mutated_sweep, 0, damage_value_at, struct.pack("<i", -64))
    rejects(dm, "damage_positive_heal_semantics_unknown",
            "a positive damage smuggled into a composed frame",
            mutated_sweep, 0, damage_value_at, struct.pack("<i", 63))
    flags_value_at = PC_PAYLOAD_AT + EXPECT_HEADER_WIRE_SIZE \
        + EXPECT_COUNT_WIRE_SIZE + 9 + 5 + 15 + 5 + 1
    check("the flag mutation offset lands on the u16 flag word",
          pc0[flags_value_at - 1] == dm.TAG_U16
          and struct.unpack("<H", pc0[flags_value_at:
                                      flags_value_at + 2])[0] == dm.FLAGS_HIT)
    rejects(dm, "flags_outside_value_allowlist",
            "an in-mask flag word smuggled into a composed frame",
            mutated_sweep, 0, flags_value_at, b"\x08\x00")
    rejects(dm, "flags_bit_outside_allowed_mask",
            "an out-of-mask flag word smuggled into a composed frame",
            mutated_sweep, 0, flags_value_at, b"\x02\x00")
    rejects(dm, "flags_forbidden_bit",
            "a forbidden bit smuggled into a composed frame",
            mutated_sweep, 0, flags_value_at, b"\x81\x00")
    rejects(dm, "position_not_from_the_pinned_source",
            "a sweep composed from an invented position",
            dm.build_damage_model_sweep, legacy,
            dm.DamageModelActor(probe.identity_lo, probe.identity_hi,
                                0.0, 0.0, 0.0), unlock, profile)
    if "sweep_does_not_contain_a_miss_frame" in open(
        os.path.join(_ROOT, "src", "pirateforce_foundation",
                     "damage_model_hypothesis.py"), encoding="utf-8"
    ).read():
        note("FINDING (report, do not fix here): the rejection "
             "'sweep_does_not_contain_a_miss_frame' is declared but is not "
             "reachable from any input.  validate_damage_model_sweep compares "
             "every step against step_damage_wire(index) and "
             "DAMAGE_MODEL_STEPS[index][2] first, and step 2 of the only "
             "accepted plan is damage 0 / flags 0, so seen_miss is always True "
             "by the time the check runs.  It only fires if the shipped plan "
             "itself loses its MISS step, which no external input can do.")

    # ============================================================= F. TRAPS
    section("F. traps - the verifier must be able to go red")
    if not HAVE_IMAGE:
        skip(3, "no client image for the byte-mutation traps")
    else:
        lo, hi, _off, sha, _what = R90_SPANS[7]     # the CHitResult ctor
        original = span(lo, hi)
        check("TRAP: a single flipped bit in a COPY of the pinned ctor range "
              "0x%08X..0x%08X is rejected by the same span guard" % (lo, hi),
              span_matches(original, sha)
              and not span_matches(flip(original, 0x39), sha))
        va, _off, hexpat, _what = R90_POINTS[3]     # 0x74F979 `88 46 10`
        want = bytes.fromhex(hexpat)
        check("TRAP: a flipped bit in a COPY of the version store at 0x%08X is "
              "rejected by the same byte guard" % va,
              bytes_match(rd(va, len(want)), want)
              and not bytes_match(flip(want, 2), want))
        vt = span(CHIT_RESULT_VTABLE, CHIT_RESULT_VTABLE + 0x24)
        swapped = bytearray(vt)
        swapped[0x18:0x1C], swapped[0x1C:0x20] = (
            bytes(swapped[0x1C:0x20]), bytes(swapped[0x18:0x1C]))
        check("TRAP: swapping the serializer and handler slots in a COPY of "
              "the vtable is rejected", len(swapped) == len(vt)
              and not span_matches(bytes(swapped), R90_SPANS[13][3]))

    pin = dm.DAMAGE_MODEL_PINS[dm.DAMAGE_MODEL_STEP_ORDER[0]]
    check("TRAP: a flipped bit in a COPY of the composed HIT_WEAK pc no longer "
          "matches its pinned sha256",
          hashlib.sha256(pc0).hexdigest().upper() == pin["pc_sha256"]
          and hashlib.sha256(flip(pc0, damage_value_at)).hexdigest().upper()
          != pin["pc_sha256"])
    check("TRAP: the pin table itself is not self-fulfilling - two steps that "
          "differ in damage have different pinned hashes",
          len({dm.DAMAGE_MODEL_PINS[label]["pc_sha256"]
               for label in dm.DAMAGE_MODEL_STEP_ORDER}) == 4)
    broke = None
    try:
        broke = dm.validate_damage_model_sweep(
            legacy, list(reversed(actions)), profile)
    except dm.DamageModelValidationError:
        broke = None
    check("TRAP: the sweep validator rejects the four real frames in the "
          "wrong order", broke is None)

    # ============================================================== summary
    emit("")
    # The house summary line every other verifier in tools/ prints, and
    # the one tests/ parses; the second line is this tool's own wording.
    emit("guards run: %d (skipped: %d)"
         % (COUNTS["passed"], COUNTS["skipped"]))
    emit("%d guards PASS, skipped %d" % (COUNTS["passed"], COUNTS["skipped"]))
    if FAILURES:
        emit("RESULT: FAIL - %d guard(s) drifted:" % len(FAILURES))
        for item in FAILURES:
            emit("  - " + item)
        return 1
    emit("RESULT: PASS - HYP-PF-024 / DAMAGE-ENCODER-001 + "
         "DAMAGE-NPC-TARGET-001 verified offline")
    return 0


if __name__ == "__main__":
    CODE = main()
    if WANT_JSON:
        print(json.dumps({
            "tool": "verify_damage_model_encoder",
            "hypothesis_id": "HYP-PF-024",
            "lane": "DAMAGE-ENCODER-001",
            "binary": BIN if HAVE_IMAGE else None,
            "binary_sha256": IMAGE_SHA if HAVE_IMAGE else None,
            "binary_sha256_expected": EXPECT_SHA,
            "guards_run": COUNTS["run"],
            "guards_passed": COUNTS["passed"],
            "guards_failed": len(FAILURES),
            "guards_skipped": COUNTS["skipped"],
            "regression_gate": (
                "FAIL" if GATE_FAILURES
                else ("SKIPPED" if not HAVE_IMAGE else "PASS")),
            "regression_gate_failures": GATE_FAILURES,
            "failures": FAILURES,
            "notes": NOTES,
            "exit_code": CODE,
        }, indent=2, sort_keys=True))
    raise SystemExit(CODE)
