#!/usr/bin/env python3
"""RUNTIMERES-ENCODER-001 - re-derive every byte-level claim the spawn-then-kill
encoder rests on, from the read-only client image AND from the frames the
encoder actually composes.

WHAT THIS TOOL IS FOR
---------------------
``src/pirateforce_foundation/runtimeres_death_hypothesis.py`` claims that three
composed ``GSCN_RunTimeProtocolRes`` frames can drive a KNOWN actor through the
client's real engine death chain to ``L"_F_DIE_000"``.  Every load-bearing part
of that claim is a statement about bytes: bytes in the client image (which
predicate gates which slot, which mask bit selects which sub-object, which
function has how many callers) and bytes on the wire (where the derived mask
sits, whether the identity repeats, whether the timer ever reaches <= 0).

This tool re-derives BOTH halves and then cross-checks them against each other.
It is **pure stdlib** - no capstone, no pefile, no third-party package at all -
because this project verifies on two machines and only one of them has capstone.
A test asserts that.

SECTION 0 IS A GATE, NOT A COURTESY
-----------------------------------
A verifier that has never been shown to agree with a previously-established
answer is just a printout of its own opinions.  Section 0 therefore reproduces
SEVEN answers this project already published in
``reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md`` (round 85), each
cited by address, **before this tool is allowed to assert anything new**:

  * s.5 item 3   ``0x446F30`` - the actor reconcile - has EXACTLY ONE direct
                 caller (``0x5E4085``) and ZERO dword pointers anywhere in the
                 14,759,424-byte file.
  * s.5 item 4   ``0x4437C0`` - the dead-state sync - has exactly one direct
                 caller (``0x444705``) and zero pointers; ``0x472810`` (the
                 ``CActorTask_Dead`` ctor) has exactly one (``0x4439E9``).
  * s.5 item 6   ``L"_F_DIE_000"`` at ``0xF0F060`` occurs exactly ONCE in the
                 image and is referenced from exactly two sites.
  * s.5 item 8   ``0x5F2400..0x5F261A`` - the ``UpdateAttrVital`` inbound
                 handler - contains ZERO ``mov r,[reg+0x20] ... call r``
                 dispatch shapes.
  * s.5 item 9   ``0x43BDA0`` (vtable +0x40) is ``HP==0 AND timer > 0.0f`` and
                 ``0x43BD70`` (vtable +0x3C) is ``HP==0 AND timer <= 0.0f`` -
                 the inverted polarity this whole lane is built around.
  * s.5 item 10  spawn applies through vtable ``+0x10`` (``0x446AAD``), which
                 never reaches ``0x4437C0``.
  * s.5 item 11  the actor-type gate at ``0x4469C8`` is a five-case jump table
                 at ``0x446B2C`` covering types 2..6, and type 4 is ``CNetNPC``.

If ANY of those seven fails, this tool prints the failures, asserts NOTHING new,
and exits non-zero.  Reproducing an old answer is the licence to state a new one.

DISCIPLINE
----------
No server, no socket, no network, no GameClient process, no database.  The
client image, ``current/pf_login_game_server_v141.py`` and
``src/pirateforce_foundation/`` are opened read-only.  Nothing is written.

Usage:
    py -3 tools/pf_runtimeres_death_encoder_static.py [path-to-GameClient.local.bin]
    py -3 tools/pf_runtimeres_death_encoder_static.py --json

Exit 0 = every guard reproduced.  Non-zero = at least one drifted, with a list.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

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

LEGACY_PATH = os.path.join(_ROOT, "current", "pf_login_game_server_v141.py")
SCENARIO_PATH = os.path.join(
    _ROOT, "scenarios", "runtimeres_death_hypothesis_spawn_then_kill.json",
)

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

# EVERY executable section, not just .text.  This image has two; round 83's
# negative was asserted over a surface that never included .code.
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


def rd(va, n):
    o = va2off(va)
    return data[o:o + n] if o is not None else b""


def dw(va):
    b = rd(va, 4)
    return struct.unpack("<I", b)[0] if len(b) == 4 else None


def wstr(va, maxn=256):
    b = rd(va, maxn)
    z = len(b)
    for i in range(0, len(b) - 1, 2):
        if b[i] == 0 and b[i + 1] == 0:
            z = i
            break
    return b[:z].decode("utf-16le", "replace")


# ---------------------------------------------------------------- the censuses
# Everything below RE-READS `data` on every call, on purpose, so a test that
# mutates a copy of the image moves every census and every guard with it.
def rel32_sites(target, opcode):
    """Every `opcode <rel32>` in EVERY executable section whose computed
    destination is `target`.  No decoding, no alignment assumption."""
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


def dword_vas(value):
    """Every occurrence of `value` as a little-endian dword anywhere in the WHOLE
    file - one sweep that simultaneously covers vtable slots, jump tables,
    `mov reg,imm32`, `FF 15` and `FF 25`, because all of them store a dword."""
    pat = struct.pack("<I", value)
    out = []
    i = data.find(pat)
    while i >= 0:
        va = off2va(i)
        if va is not None:
            out.append(va)
        i = data.find(pat, i + 1)
    return out


def byte_occurrences(pat):
    out = []
    i = data.find(pat)
    while i >= 0:
        out.append(off2va(i))
        i = data.find(pat, i + 1)
    return out


def vt20_dispatch_sites(lo=None, hi=None):
    """Census of `mov <r>,[<reg>+0x20] ... call <r>` - the shape this compiler
    emits for `this->vtable[+0x20](...)`.  Pure byte matching."""
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
            va = off2va(rp + i)
            if va is None:
                continue
            if lo is not None and not (lo <= va < hi):
                continue
            out.append(va)
    return sorted(out)


def name_id(name):
    """u16 id = SUM_i (int16)((signed char)name[i] * (i+1)) mod 2^16."""
    acc = 0
    for i, ch in enumerate(name.encode("latin1")):
        sc = ch if ch < 128 else ch - 256
        acc = (acc + ((sc * (i + 1)) & 0xFFFF)) & 0xFFFF
    return acc


# -------------------------------------------------------------------- guards
FAILS = []
REGRESSION_FAILS = []
NGUARD = 0
_PHASE = "regression"


def guard(cond, msg):
    global NGUARD
    NGUARD += 1
    ok = bool(cond)
    if not WANT_JSON:
        print(("  PASS " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(msg)
        if _PHASE == "regression":
            REGRESSION_FAILS.append(msg)
    return ok


def gbytes(va, hexpat, msg):
    want = bytes.fromhex(hexpat)
    return guard(rd(va, len(want)) == want, "%s  [0x%08X %s]" % (msg, va, hexpat))


def gentry(target, direct, ptrs, msg, tails=()):
    """Pin the COMPLETE entry-point census - the whole list, not membership."""
    d, j, p = calls_to(target), jmps_to(target), dword_vas(target)
    ok = (d == list(direct) and j == list(tails) and p == list(ptrs))
    return guard(ok, "%s  [0x%08X calls=%s jmps=%s ptrs=%s]" % (
        msg, target, [hex(x) for x in d], [hex(x) for x in j],
        [hex(x) for x in p]))


def section(title):
    if not WANT_JSON:
        print("\n== " + title)


# ==========================================================================
# SECTION 0 - THE GATE.  Reproduce round 85's published answers, by address,
# before this tool is allowed to assert anything new.
# ==========================================================================
if not WANT_JSON:
    print("RUNTIMERES-ENCODER-001 spawn-then-kill encoder verifier")
    print("binary          =", BIN)
    print("binary SHA-256  =", SHA)

section("0. REGRESSION GATE - reproduce round 85 "
        "(reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md)")

guard(SHA == EXPECT_SHA, "binary SHA-256 matches the image round 85 read")
guard(len(data) == EXPECT_SIZE, "image size == %d bytes" % EXPECT_SIZE)
guard(IMAGE_BASE == 0x400000, "ImageBase == 0x400000")
guard([s[0] for s in EXEC_SECS] == [".text", ".code"],
      "both executable sections (.text AND .code) are in the scan surface")

# round 85 s.5 item 3
gentry(0x446F30, [0x5E4085], [],
       "R85 s.5#3: 0x446F30 actor reconcile has ONE direct caller (0x5E4085, "
       "inside the GSCN_RunTimeProtocolRes inbound handler) and ZERO pointers")
# round 85 s.5 item 4
gentry(0x4437C0, [0x444705], [],
       "R85 s.5#4: 0x4437C0 dead-state sync has ONE direct caller (0x444705) "
       "and ZERO pointers")
gentry(0x472810, [0x4439E9], [],
       "R85 s.5#4: 0x472810 CActorTask_Dead ctor has ONE direct caller "
       "(0x4439E9) and ZERO pointers")
# round 85 s.5 item 6
guard(wstr(0xF0F060) == "_F_DIE_000",
      "R85 s.5#6: the literal at 0xF0F060 is L\"_F_DIE_000\"")
guard(byte_occurrences("_F_DIE_000".encode("utf-16le") + b"\0\0") == [0xF0F060],
      "R85 s.5#6: L\"_F_DIE_000\" occurs exactly ONCE in the whole image")
guard(dword_vas(0xF0F060) == [0x4728B0, 0x476710],
      "R85 s.5#6: it is referenced from exactly two sites, both inside the "
      "CActorTask_Dead vtable 0xF0F048")
# round 85 s.5 item 8 - the negative that makes this lane necessary
guard(vt20_dispatch_sites(0x5F2400, 0x5F261A) == [],
      "R85 s.5#8: 0x5F2400..0x5F261A (UpdateAttrVital inbound) contains ZERO "
      "vtable+0x20 dispatch shapes, so HP-DEATH-002's carrier cannot reach "
      "the death chain")
# round 85 s.5 item 9 - THE POLARITY this whole lane is built around
gbytes(0x43BD70,
       "568bf18b068b5074ffd28378440075198b068b50748bceffd20f57c00f2f40587207"
       "b8010000005ec3",
       "R85 s.5#9: vtable +0x3C 0x43BD70 == HP(+0x44)==0 AND f32(+0x58) <= 0.0f "
       "(xorps zero; comiss 0 vs timer; jb -> false) - the DEATH TASK gate")
gbytes(0x43BDA0,
       "568bf18b068b5074ffd283784400751e8b068b50748bceffd2f30f1040580f2f059c"
       "98f0007607b8010000005ec3",
       "R85 s.5#9: vtable +0x40 0x43BDA0 == HP(+0x44)==0 AND f32(+0x58) > 0.0f "
       "- the DYING LATCH")
guard(struct.unpack("<f", rd(0xF0989C, 4))[0] == 0.0,
      "R85 s.5#9: the float at 0xF0989C the +0x40 predicate compares to is 0.0f")
gbytes(0x44384C, "84db0f84970000008556700f858e000000095670",
       "R85 s.3: 0x44384C - vtable+0x40 gates `[actor+0x70] |= 0x200`")
gbytes(0x443990, "807c2413000f84ec000000",
       "R85 s.3: 0x443990 - vtable+0x3C gates everything below it, including "
       "0x4439E9 `call 0x472810`.  A positive timer = latch and NO animation")
# round 85 s.5 item 10 - an actor cannot be born dead
gbytes(0x446F87,
       "8b48188b401c50518bcde8daf1ffff8bf085f675186a016a01578bcde8e8f9ffff8b"
       "f085f67419",
       "R85 s.5#10: 0x446F87 find-or-create - FOUND goes to vtable +0x20, NOT "
       "FOUND goes to the spawn 0x446990 and SKIPS the +0x20 call")
gbytes(0x446AAD, "8b068b5010558bceffd2",
       "R85 s.5#10: 0x446AAD - a freshly spawned actor is applied through "
       "vtable +0x10, which is not a caller of 0x4437C0")
# round 85 s.5 item 11 - the actor-type gate
gbytes(0x4469C8, "0fb6401083c0fe33f683f8040f873a010000ff24852c6b4400",
       "R85 s.5#11: 0x4469C8 actor-type gate - movzx byte [entry+0x10]; -2; "
       ">4 rejects; jump table at 0x446B2C")
_FACTORY = {
    2: (0x4469E1, 0xF0DD08, "CNetActor"),
    3: (0x4469F7, 0xF0D7A8, "CMyActor"),
    4: (0x446A3D, 0xF0DF58, "CNetNPC"),
    5: (0x446A5A, 0xF0DFF8, "CAvatarNPC"),
    6: (0x446A77, 0xF0E0C8, "Pet"),
}
for _t, (_case, _vt, _cls) in _FACTORY.items():
    guard(dw(0x446B2C + (_t - 2) * 4) == _case,
          "R85 s.5#11: jump table case actor_type %d -> 0x%08X (%s)"
          % (_t, _case, _cls))
guard(dw(0xF0DF58 + 0x20) in (0x4446F0, 0x456630),
      "R85 s.2: CNetNPC (actor_type 4, the type this lane emits) carries the "
      "death-chain entry in vtable slot +0x20")
# the envelope identity, from the same hash the project already trusts
guard(name_id("ActorAttr") == 0x12AD and name_id("NPCAttr") == 0x0AD5
      and name_id("UpdateAttrVital") == 0x309A,
      "R85 s.1: the three name-hash anchors v141 already carries reproduce")
RES_ID = name_id("GSCN_RunTimeProtocolRes")
guard(RES_ID == 0x6E9D == 28317,
      "R85 s.1: hash('GSCN_RunTimeProtocolRes') == 0x6E9D == 28317")
guard(dw(0xF2FFC0 + 0x1C) == 0x5E4060,
      "R85 s.1: Res vtable 0xF2FFC0 +0x1C is the real inbound handler 0x5E4060")
gbytes(0x5E3EFD, "837e1c00b3027404885c2414",
       "R85 s.1: derived change-mask bit 0x02 selects the object at +0x1C - "
       "the actor-entry collection")
gbytes(0x5E4073, "8b461c85c0741083c01050e89de9e1ff8bc8e8a62ee6ff",
       "R85 s.2: 0x5E4073 takes Res+0x1C, +0x10 (list head), and calls "
       "0x446F30")

REGRESSION_GUARDS = NGUARD
if REGRESSION_FAILS:
    if WANT_JSON:
        print(json.dumps({
            "binary_sha256": SHA,
            "guards": NGUARD,
            "regression_gate": "FAILED",
            "failures": FAILS,
            "new_claims_asserted": False,
        }, indent=2, sort_keys=True))
    else:
        print("\n%d guards, %d failures" % (NGUARD, len(FAILS)))
        print("REGRESSION GATE FAILED - refusing to assert anything new.")
        for f in REGRESSION_FAILS:
            print("  -", f)
    sys.exit(2)

if not WANT_JSON:
    print("\n  [gate open: %d round-85 answers reproduced; new claims follow]"
          % REGRESSION_GUARDS)

# ==========================================================================
# SECTION 1 - the composed frames, and what the image says about them.
# ==========================================================================
_PHASE = "new"
section("1. the composed spawn-then-kill sweep")

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as rdh  # noqa: E402

legacy = load_legacy(LEGACY_PATH)
scenario = rdh.load_runtimeres_death_hypothesis_scenario(SCENARIO_PATH)
unlock = rdh.runtimeres_death_lethal_unlock(scenario)
probe = rdh.resolve_probe(legacy)
actions = rdh.build_runtimeres_death_sweep(legacy, probe, unlock, scenario)

guard(len(actions) == 3, "the sweep is exactly three frames")
guard([a[0] for a in actions] == list(rdh.RUNTIMERES_DEATH_ACTION_LABELS),
      "in the pinned order SPAWN -> DYING_LATCH -> DEATH_TASK")
with open(SCENARIO_PATH, "r", encoding="utf-8") as _fh:
    _SCENARIO_JSON = json.load(_fh)
guard(_SCENARIO_JSON["production_allowed"] is False
      and _SCENARIO_JSON["test_only"] is True
      and _SCENARIO_JSON["lethal"] is True,
      "the scenario file declares test_only, lethal and NOT production_allowed")
guard(rdh.production_allowed is False,
      "the module declares production_allowed = False")
# Round 86, second edit.  This guard was written by RUNTIMERES-ENCODER-001,
# which shipped an encoder with nothing behind the flag and said so honestly.
# RUNTIMERES-DISPATCH-001 landed the wiring later the same round, so the guard
# is re-pinned to the state that is now true.  What still has to hold, and is
# the reason this check exists at all, is that a lethal sweep may only ever be
# reachable behind an explicit opt-in -- so wired and production_allowed are
# asserted together, and a lane that ever flips production_allowed to True
# turns this line red rather than sailing past it.
guard(_SCENARIO_JSON["dispatch"]["wired"] is True
      and _SCENARIO_JSON["dispatch"]["wiring_owner"]
      == "runtimeres_dispatch_001_round_86"
      and _SCENARIO_JSON["production_allowed"] is False,
      "the scenario is wired to a dispatcher AND still not production_allowed")

# ------------------------------------------------------------------ an
# INDEPENDENT tag walker.  It deliberately does not import the module's
# decoder: the point is to read the dispatcher's bytes with a second pair of
# eyes, exactly as tools/pf_hp_death002_headless_replay.py does.
_SCALAR_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x12: 2, 0x14: 4, 0x19: 4,
                 0x26: 4, 0x2A: 4, 0x32: 8}
_BASIC_ORDER = ((0x0001, 0x48), (0x0002, 0x12), (0x0004, 0x14), (0x0008, 0x14),
                (0x0010, 0x14), (0x0020, 0x14), (0x0040, 0x2A), (0x0080, 0x2A),
                (0x0100, 0x12), (0x0200, 0x32), (0x0400, 0x14))


def walk(pc):
    """Read one RuntimeRes actor-entry PC by hand.  Raises on anything that is
    not the shape this lane claims to emit."""
    if pc[0] != 0x12 or int.from_bytes(pc[1:3], "little") != 0x6E9D:
        raise ValueError("not GSCN_RunTimeProtocolRes 0x6E9D")
    if pc[3] != 0x14 or int.from_bytes(pc[4:8], "little") != 0:
        raise ValueError("envelope u32 drift")
    if pc[8] != 0x08 or pc[9] != 4:
        raise ValueError("not envelope version 4")
    if pc[10] != 0x0B:
        raise ValueError("inherited mask tag drift")
    inherited = pc[11]
    if pc[12] != 0x0B:
        raise ValueError("derived mask tag drift")
    derived = pc[13]
    if pc[14] != 0x12:
        raise ValueError("count tag drift")
    count = int.from_bytes(pc[15:17], "little")
    cur = 17
    if pc[cur] != 0x0B:
        raise ValueError("actor type tag drift")
    actor_type = pc[cur + 1]
    cur += 2
    if pc[cur] != 0x32:
        raise ValueError("entry identity tag drift")
    identity = int.from_bytes(pc[cur + 1:cur + 9], "little")
    cur += 9
    if pc[cur] != 0x0B:
        raise ValueError("attr count tag drift")
    nattr = pc[cur + 1]
    cur += 2
    attr_ids, basic_mask, fields, preset, template = [], None, {}, None, None
    for _ in range(nattr):
        if pc[cur] != 0x12:
            raise ValueError("attr id tag drift")
        aid = int.from_bytes(pc[cur + 1:cur + 3], "little")
        attr_ids.append(aid)
        cur += 3
        if pc[cur] != 0x0B or pc[cur + 1] != 0x01 or pc[cur + 2] != 0x32:
            raise ValueError("DBAttribute identity block drift")
        cur += 11
        if aid == 0x0AD5:
            if pc[cur] != 0x12:
                raise ValueError("BasicAttr mask tag drift")
            basic_mask = int.from_bytes(pc[cur + 1:cur + 3], "little")
            cur += 3
            for bit, tag in _BASIC_ORDER:
                if not basic_mask & bit:
                    continue
                if pc[cur] != tag:
                    raise ValueError("BasicAttr 0x%04X tag drift" % bit)
                if tag == 0x48:
                    n = int.from_bytes(pc[cur + 1:cur + 5], "little")
                    fields[bit] = pc[cur + 5:cur + 5 + n].decode("utf-16le")
                    cur += 5 + n
                    continue
                w = _SCALAR_WIDTH[tag]
                raw = pc[cur + 1:cur + 1 + w]
                fields[bit] = (struct.unpack("<f", raw)[0] if tag == 0x2A
                               else int.from_bytes(raw, "little"))
                cur += 1 + w
            if pc[cur] != 0x0B:
                raise ValueError("NPCAttr mask tag drift")
            npc_mask = pc[cur + 1]
            cur += 2
            if npc_mask & 0x01:
                template = int.from_bytes(pc[cur + 1:cur + 3], "little")
                cur += 3
            if npc_mask & 0x04:
                n = int.from_bytes(pc[cur + 1:cur + 5], "little")
                preset = pc[cur + 5:cur + 5 + n].decode("utf-16le")
                cur += 5 + n
        elif aid == 0x2067:
            if pc[cur] != 0x0B:
                raise ValueError("MovementAttr mask tag drift")
            mmask = pc[cur + 1]
            cur += 2
            for bit, adv in ((0x01, 15), (0x02, 5), (0x04, 2), (0x08, 5),
                             (0x10, 5), (0x20, 5), (0x40, 5)):
                if mmask & bit:
                    cur += adv
        else:
            raise ValueError("unexpected attr id 0x%04X" % aid)
    if cur != len(pc):
        raise ValueError("%d unaccounted trailing bytes" % (len(pc) - cur))
    return {"inherited": inherited, "derived": derived, "count": count,
            "actor_type": actor_type, "identity": identity,
            "attr_ids": attr_ids, "basic_mask": basic_mask, "fields": fields,
            "visual_preset": preset, "template_id": template}


READ = []
for _label, _pc, _frame, _delay in actions:
    READ.append(walk(_pc))

section("2. REQUIREMENT 1 - id 0x6E9D, derived mask bit 0x02, object +0x1C")
for _i, (_label, _pc, _frame, _delay) in enumerate(actions):
    r = READ[_i]
    guard(int.from_bytes(_pc[1:3], "little") == RES_ID,
          "%s carries the id the image itself hashes to (0x%04X)"
          % (_label, RES_ID))
    guard(_pc[9] == 4, "%s is envelope version 4" % _label)
    guard(r["inherited"] == 0x00,
          "%s leaves the INHERITED VitalData collection (+0x18) absent - the "
          "sub-object UpdateAttrVital rides, dispatched separately at 0x5E40DE"
          % _label)
    guard(r["derived"] == 0x02,
          "%s sets the DERIVED change mask to 0x02, the bit 0x5E3EFD binds to "
          "the object at +0x1C" % _label)
    guard(r["count"] == 1, "%s carries exactly one actor entry" % _label)
    guard(r["actor_type"] == 4,
          "%s uses actor_type 4, which the jump table at 0x446B2C maps to "
          "CNetNPC (0x446A3D, vtable 0xF0DF58)" % _label)
    guard(r["visual_preset"] == probe.visual_preset and bool(r["visual_preset"]),
          "%s carries a visual preset, without which [actor+0x70] |= 0x40 "
          "never happens and 0x47289E can never play the literal" % _label)
    guard(_frame == legacy.frame_pc(_pc), "%s frame == frame_pc(pc)" % _label)

section("3. REQUIREMENT 2 - spawn first, kill second, SAME identity")
guard(len({r["identity"] for r in READ}) == 1,
      "all three frames carry ONE identity (0x%X), so frames 2 and 3 take the "
      "FOUND branch at 0x446F98 -> vtable +0x20, not the spawn 0x446990"
      % READ[0]["identity"])
guard(READ[0]["identity"] == probe.actor_identity
      == rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY,
      "the identity is the pinned frozen-placement identity 0x%X"
      % rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY)
guard(READ[0]["fields"].get(0x0004) not in (None, 0),
      "frame 1 is ALIVE (current HP != 0): an unknown identity takes the spawn "
      "path, and 0x446AAD applies it through vtable +0x10 which never reaches "
      "0x4437C0 - an actor cannot be born dead")
guard(0x0080 not in READ[0]["fields"],
      "frame 1 does NOT carry BasicAttr bit 0x0080")
guard(0x2067 in READ[0]["attr_ids"],
      "frame 1 places the actor (MovementAttr 0x2067) so it is visible")
guard(all(r["fields"].get(0x0004) == 0 for r in READ[1:]),
      "frames 2 and 3 carry current HP == 0 (BasicAttr bit 0x0004, +0x44), "
      "the half both predicates share")
guard(all(0x2067 not in r["attr_ids"] for r in READ[1:]),
      "frames 2 and 3 do not re-place the actor")

section("4. REQUIREMENT 3 - the timer polarity, and that the sweep REACHES <= 0")
_t1 = READ[1]["fields"].get(0x0080)
_t2 = READ[2]["fields"].get(0x0080)
guard(READ[1]["basic_mask"] & 0x0080 and _t1 is not None,
      "frame 2 sets BasicAttr bit 0x0080 (f32 @ +0x58, wire tag 0x2A)")
guard(_t1 == rdh.DYING_LATCH_TIMER_SECONDS and _t1 > 0.0,
      "frame 2 timer == %.1f > 0.0f, which satisfies 0x43BDA0 (vtable +0x40): "
      "HP==0 AND timer>0 -> the [actor+0x70] |= 0x200 DYING latch at 0x44384C"
      % rdh.DYING_LATCH_TIMER_SECONDS)
guard(not (_t1 <= 0.0),
      "frame 2 does NOT satisfy 0x43BD70 (vtable +0x3C) - the two predicates "
      "are mutually exclusive on one snapshot, exactly as the image says")
guard(_t2 is not None and _t2 <= 0.0,
      "frame 3 timer == %r <= 0.0f, which satisfies 0x43BD70 (vtable +0x3C): "
      "HP==0 AND timer<=0 -> 0x443990 opens -> 0x4439E9 call 0x472810 -> "
      "CActorTask_Dead -> L\"_F_DIE_000\"" % _t2)
guard(_t2 == rdh.DEATH_TASK_TIMER_SECONDS == rdh.DEATH_TASK_TIMER_CEILING,
      "frame 3 uses the named constant DEATH_TASK_TIMER_SECONDS, not a "
      "coincidence")
guard(READ[2]["fields"].get(0x0004) == 0 and _t2 <= 0.0,
      "the LAST frame is the one that opens the task gate, so the sweep does "
      "not re-arm the timer after reaching <= 0")
# the encoded bytes of the two timers, read straight out of the PC
guard(bytes([0x2A]) + struct.pack("<f", 20.0) in actions[1][1],
      "frame 2 literally contains the bytes 2A 0000A041 (tag 0x2A, 20.0f)")
guard(bytes([0x2A]) + struct.pack("<f", 0.0) in actions[2][1],
      "frame 3 literally contains the bytes 2A 00000000 (tag 0x2A, 0.0f)")

section("5. the encoder degrades to the frozen, already-accepted projection")
_timerless = rdh.encode_death_capable_npc_attr(
    legacy, probe, current_hp=rdh.RUNTIMERES_DEATH_HP_ALIVE,
)
_frozen = legacy.make_npc_attr(
    probe.template_id, probe.actor_identity, probe.scene_id,
    probe.scene_sequence, probe.visual_preset,
    rdh.RUNTIMERES_DEATH_HP_ALIVE, rdh.RUNTIMERES_DEATH_HP_MAX,
)
guard(_timerless == _frozen,
      "with no timer the widened encoder reproduces legacy.make_npc_attr byte "
      "for byte (%d bytes) - it is a superset that degrades to the known-good "
      "body" % len(_frozen))
_lethal = rdh.encode_death_capable_npc_attr(
    legacy, probe, current_hp=0, death_timer=0.0, lethal=unlock,
)
guard(len(_lethal) == len(_frozen) + 5,
      "the lethal body is the frozen body plus EXACTLY the five bytes of the "
      "tag-0x2A f32")
guard(READ[1]["basic_mask"] == READ[0]["basic_mask"] | 0x0080,
      "the lethal BasicAttr mask differs from the spawn's by exactly bit "
      "0x0080 (0x%04X -> 0x%04X)" % (READ[0]["basic_mask"],
                                     READ[1]["basic_mask"]))
try:
    rdh.encode_death_capable_npc_attr(legacy, probe, current_hp=0,
                                      death_timer=0.0)
except ValueError:
    guard(True, "FAIL CLOSED: without the lethal unlock the encoder refuses to "
                "name BasicAttr bit 0x0080 at all")
else:
    guard(False, "the encoder emitted bit 0x0080 without the lethal unlock")

section("6. the composition is pinned")
for _i, _label in enumerate(rdh.RUNTIMERES_DEATH_STEP_ORDER):
    _pin = rdh.RUNTIMERES_DEATH_PINS[_label]
    _pc, _frame = actions[_i][1], actions[_i][2]
    guard(len(_pc) == _pin["pc_size"]
          and hashlib.sha256(_pc).hexdigest().upper() == _pin["pc_sha256"],
          "%s PC is the pinned %d bytes / %s" % (_label, _pin["pc_size"],
                                                 _pin["pc_sha256"][:16]))
    guard(len(_frame) == _pin["frame_size"]
          and hashlib.sha256(_frame).hexdigest().upper() == _pin["frame_sha256"],
          "%s frame is the pinned %d bytes / %s"
          % (_label, _pin["frame_size"], _pin["frame_sha256"][:16]))

section("7. the validator can actually reject (a guard that cannot fail is a "
        "printout)")


def _rejects(label, mutate):
    bad = [list(a) for a in actions]
    mutate(bad)
    try:
        rdh.validate_runtimeres_death_sweep(
            [tuple(a) for a in bad], scenario,
        )
    except rdh.RuntimeResDeathValidationError:
        return guard(True, "the validator REJECTS: " + label)
    return guard(False, "the validator ACCEPTED a bad sweep: " + label)


def _clear_derived(rows):
    pc = bytearray(rows[2][1])
    pc[13] = 0x00
    rows[2][1] = bytes(pc)


def _positive_final_timer(rows):
    pc = bytearray(rows[2][1])
    off = pc.find(bytes([0x2A]) + struct.pack("<f", 0.0))
    pc[off + 1:off + 5] = struct.pack("<f", 5.0)
    rows[2][1] = bytes(pc)


def _dead_on_arrival(rows):
    rows[0][1] = rows[1][1]


def _different_identity(rows):
    # move BOTH identities in the frame, so the rejection has to be "this is
    # not the actor we spawned" and not an internal inconsistency
    old = struct.pack("<Q", rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY)
    new = struct.pack("<Q", rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY + 1)
    rows[2][1] = rows[2][1].replace(old, new)


_rejects("derived change mask bit 0x02 cleared (the ErrorData 28317 over-read "
         "shape, and the shape that never reaches 0x446F30)", _clear_derived)
_rejects("the final timer left POSITIVE, so vt+0x3C is never true and "
         "CActorTask_Dead is never constructed", _positive_final_timer)
_rejects("frame 1 already dead (an actor cannot be born dead)", _dead_on_arrival)
_rejects("the kill frame re-targeted to a different identity (a second spawn, "
         "not a vtable +0x20 update)", _different_identity)

# ------------------------------------------------------------------- results
RESULT = {
    "binary_sha256": SHA,
    "guards": NGUARD,
    "regression_gate_guards": REGRESSION_GUARDS,
    "regression_gate": "PASSED",
    "new_claims_asserted": True,
    "failures": FAILS,
    "scenario": SCENARIO_PATH.replace("\\", "/").split("/")[-1],
    "probe": {
        "placement_index": probe.placement_index,
        "template_id": probe.template_id,
        "actor_identity": probe.actor_identity,
        "visual_preset": probe.visual_preset,
        "source_name": probe.source_name,
    },
    "polarity": {
        "dying_latch_predicate": "0x0043BDA0 (vtable +0x40) HP==0 AND timer>0",
        "dying_latch_timer_seconds": rdh.DYING_LATCH_TIMER_SECONDS,
        "death_task_predicate": "0x0043BD70 (vtable +0x3C) HP==0 AND timer<=0",
        "death_task_timer_seconds": rdh.DEATH_TASK_TIMER_SECONDS,
        "sweep_reaches_le_zero": True,
    },
    "frames": [
        {
            "label": actions[i][0],
            "delay_seconds": actions[i][3],
            "pc_size": len(actions[i][1]),
            "frame_size": len(actions[i][2]),
            "pc_sha256": hashlib.sha256(actions[i][1]).hexdigest().upper(),
            "frame_sha256": hashlib.sha256(actions[i][2]).hexdigest().upper(),
            "inherited_change_mask": READ[i]["inherited"],
            "derived_change_mask": READ[i]["derived"],
            "actor_type": READ[i]["actor_type"],
            "identity": READ[i]["identity"],
            "attr_ids": ["0x%04X" % a for a in READ[i]["attr_ids"]],
            "basic_mask": "0x%04X" % READ[i]["basic_mask"],
            "hp_current_bit_0x0004": READ[i]["fields"].get(0x0004),
            "death_timer_bit_0x0080": READ[i]["fields"].get(0x0080),
            "satisfies_vt40_dying_latch":
                READ[i]["fields"].get(0x0004) == 0
                and READ[i]["fields"].get(0x0080) is not None
                and READ[i]["fields"].get(0x0080) > 0.0,
            "satisfies_vt3c_death_task":
                READ[i]["fields"].get(0x0004) == 0
                and READ[i]["fields"].get(0x0080) is not None
                and READ[i]["fields"].get(0x0080) <= 0.0,
            "pc_hex": actions[i][1].hex(),
        }
        for i in range(len(actions))
    ],
    "nonclaims": list(rdh.RUNTIMERES_DEATH_NONCLAIMS),
}

if WANT_JSON:
    print(json.dumps(RESULT, indent=2, sort_keys=True))
else:
    print("\n%d guards (%d of them the round-85 regression gate), %d failures"
          % (NGUARD, REGRESSION_GUARDS, len(FAILS)))
    if FAILS:
        print("FAILED:")
        for f in FAILS:
            print("  -", f)
    else:
        print("RESULT: the spawn-then-kill sweep reproduces every static and "
              "wire guard (exit 0)")

if FAILS:
    sys.exit(1)
