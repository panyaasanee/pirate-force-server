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

SECTION 8 - THE TWO-FRAME PROFILE
--------------------------------
Round 91 added a second named profile, ``dying_latch_only``: SPAWN, then
DYING_LATCH, then STOP.  It exists because the attended GT-022 run produced a
real corpse on a real client but could not say WHICH frame produced it - the
photographs land about a second short of the DYING_LATCH/DEATH_TASK boundary
and the capture latency of that path was never measured.  A sweep that stops
after the latch answers that with no appeal to a clock at all.  Section 8
verifies that profile, and its load-bearing guard is byte identity with the
first two frames of the three-frame sweep: the experiment is only decisive if
the single difference between the two runs is the missing third frame.

Nothing in section 8 is an observation.  No client has ever been shown one byte
of the two-frame profile; it is a queued attended test.

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

import dataclasses
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

# ==========================================================================
# SECTION 8 - THE TWO-FRAME "dying_latch_only" PROFILE.
# (RUNTIMERES-LATCHONLY-001, round 91.  Everything above this line is round 86
# and is not touched by it.)
#
# WHY THERE IS A SECOND PROFILE AT ALL.  The attended GT-022 run put a real
# corpse on a real client: the probe NPC went from standing to lying flat and
# stayed there.  What that run could NOT say is which frame did it.  DYING_LATCH
# leaves at t+6 and DEATH_TASK at t+12; the photographs land somewhere around
# t+10.5 to t+11.5, i.e. roughly a second short of the boundary; and nobody ever
# measured the latency of that capture path.  An unmeasured error bar the same
# size as the margin turns "it was already lying down before the third frame"
# into an indication rather than an answer, and this lane does not promote
# indications.
#
# The two-frame profile settles it with no appeal to a clock at all: send SPAWN,
# send DYING_LATCH, and STOP.  If the pose still appears, it belongs to the
# latch.  If it never appears, it belonged to the death task.  Either outcome is
# decisive, and neither depends on when a shutter opened.
#
# THE LOAD-BEARING GUARD.  That argument only works if the single difference
# between the two runs is the missing third frame.  So the guard this section is
# really built around is not a comparison against a constant, it is a comparison
# against the OTHER PROFILE'S ACTUAL COMPOSED BYTES: frames 1 and 2 of the
# two-frame sweep must be `==` the first two frames of the three-frame sweep,
# byte for byte, plus the same SHA-256.  If the composer drifted so much as one
# byte while dropping the third frame, then a difference on screen would no
# longer be attributable to the missing frame and the whole experiment would
# prove nothing - it would be two different sweeps producing two different
# results, which is not an experiment, it is a coincidence.
#
# HOW INDEPENDENT THAT GUARD IS, HONESTLY.  Today it is NOT independent of the
# pinned-hash guard below it: both profiles publish the same per-step pins, so
# equal-to-the-pin already implies equal-to-each-other.  What byte identity adds
# is that it keeps holding if the pins are ever legitimately re-pinned for a
# real wire change - the pins would move together and the identity would still
# have to survive.  Stating that plainly is cheaper than pretending to two
# independent proofs.
#
# WHAT THIS SECTION DOES NOT CLAIM.  No client has ever been shown one byte of
# the two-frame profile.  It is a queued attended test, not an observation.
# Nothing below says the client will lie down, will not lie down, or does
# anything whatsoever when a sweep stops on the positive side of the polarity.
# It says only that the bytes are the bytes the three-frame run already sent,
# that no frame of this sweep can open the task gate, and that every route which
# could quietly turn a two-frame run back into a three-frame one refuses and
# hands back nothing.
# ==========================================================================
section("8. the two-frame dying_latch_only profile (the GT-022 tie-breaker)")

LATCH_SCENARIO_PATH = os.path.join(
    _ROOT, "scenarios", "runtimeres_death_hypothesis_dying_latch_only.json",
)

latch_profile = rdh.load_runtimeres_death_hypothesis_scenario(
    LATCH_SCENARIO_PATH,
)
guard(latch_profile is rdh.RUNTIMERES_DEATH_PROFILE_BY_NAME[
          rdh.RUNTIMERES_DEATH_PROFILE_DYING_LATCH_ONLY]
      and latch_profile is rdh.RUNTIMERES_DEATH_PROFILE_BY_SCENARIO_ID[
          rdh.RUNTIMERES_DEATH_LATCH_ONLY_SCENARIO_ID]
      and latch_profile is not scenario,
      "the new scenario file loads through the exact-tree allowlist and yields "
      "the ONE dying_latch_only profile object this module ships (not a copy, "
      "and not the spawn_then_kill profile)")
guard(latch_profile.profile_name == rdh.RUNTIMERES_DEATH_PROFILE_DYING_LATCH_ONLY
      and latch_profile.ends_on_death_task is False
      and scenario.ends_on_death_task is True,
      "it declares ends_on_death_task = False while the three-frame profile "
      "declares True - the two profiles disagree about exactly one thing")
guard(len(latch_profile.step_order) == 2
      and latch_profile.step_order
      == rdh.RUNTIMERES_DEATH_LATCH_ONLY_STEP_ORDER
      == (rdh.SPAWN_STEP_LABEL, rdh.DYING_LATCH_STEP_LABEL)
      and rdh.DEATH_TASK_STEP_LABEL not in latch_profile.step_order,
      "its plan is exactly 2 steps, SPAWN then DYING_LATCH, and the DEATH_TASK "
      "label appears nowhere in it")
guard(latch_profile.lethal_step_labels == (rdh.DYING_LATCH_STEP_LABEL,)
      and rdh.DEATH_TASK_STEP_LABEL not in latch_profile.lethal_step_labels,
      "its lethal step list names ONLY DYING_LATCH, so the encoder may name "
      "BasicAttr bit 0x0080 on that step and on no other")
# The step rows are the SAME OBJECTS, not equal copies.  A copy could be edited
# on one side only; `is` cannot be satisfied by an edited copy.
guard(all(rdh.RUNTIMERES_DEATH_STEP_BY_LABEL[_lbl]
          is rdh.RUNTIMERES_DEATH_STEPS[_i]
          for _i, _lbl in enumerate(latch_profile.step_order)),
      "each of its two step rows IS (identity, not equality) the row the "
      "three-frame plan holds at the same index")

with open(LATCH_SCENARIO_PATH, "r", encoding="utf-8") as _fh:
    _LATCH_JSON = json.load(_fh)
guard(_LATCH_JSON["production_allowed"] is False
      and _LATCH_JSON["test_only"] is True
      and _LATCH_JSON["lethal"] is True
      and _LATCH_JSON["hypothesis_id"] == rdh.RUNTIMERES_DEATH_HYPOTHESIS_ID,
      "the two-frame scenario file declares test_only, lethal, HYP-PF-023 and "
      "NOT production_allowed, exactly as the three-frame one does")
guard(_LATCH_JSON["dispatch"]["ends_on_death_task"] is False
      and _LATCH_JSON["dispatch"]["frames_per_accepted_request"] == 2
      and _LATCH_JSON["dispatch"]["step_order"] == ["SPAWN", "DYING_LATCH"]
      and _LATCH_JSON["dispatch"]["lethal_steps"] == ["DYING_LATCH"],
      "and the file itself publishes 2 frames, the SPAWN/DYING_LATCH order and "
      "DYING_LATCH as its only lethal step")
guard("no_client_has_ever_been_shown_one_byte_of_this_profile"
      in _LATCH_JSON["nonclaims"]
      and any("this_variant_is_the_test_not_the_answer" in _n
              for _n in _LATCH_JSON["nonclaims"]),
      "and it keeps the nonclaim that NO CLIENT HAS EVER BEEN SHOWN ONE BYTE "
      "of this profile: it is a queued attended test, not an observation")

# ---- the unlock is per profile, so a two-frame run cannot borrow the key ----
latch_unlock = rdh.runtimeres_death_lethal_unlock(latch_profile)
guard(latch_unlock is rdh._UNLOCK_LATCH_ONLY and latch_unlock is not unlock
      and unlock is rdh._UNLOCK,
      "the file yields the two-frame lethal unlock, which is a DIFFERENT object "
      "from the three-frame one")

latch_actions = rdh.build_runtimeres_death_sweep(
    legacy, probe, latch_unlock, latch_profile,
)
guard(len(latch_actions) == 2
      and [a[0] for a in latch_actions]
      == list(rdh.RUNTIMERES_DEATH_LATCH_ONLY_ACTION_LABELS),
      "the composed sweep is exactly two frames, labelled SPAWN then "
      "DYING_LATCH")
guard([a[3] for a in latch_actions] == [a[3] for a in actions[:2]]
      == [rdh.RUNTIMERES_DEATH_FIRST_DELAY_SECONDS,
          rdh.RUNTIMERES_DEATH_SPACING_SECONDS],
      "and its two delays are the same 0.0 / 6.0 the three-frame run uses, so "
      "the tester photographs the same moments in both runs")

# ------------------------------------------------------- THE identity guard
# Written as a function on purpose: the trap at the bottom of this section calls
# THIS function on a mutated copy, so the thing proved capable of failing is the
# same code the guard runs, not a re-implementation of it that happens to agree.
def _first_two_frames_identical(rows):
    """True iff `rows` is two (label, pc, frame, delay) tuples whose pc and
    frame bytes are the SAME BYTES as the three-frame sweep's first two."""
    if type(rows) not in (list, tuple) or len(rows) != 2:
        return False
    for i in range(2):
        pc, frame = rows[i][1], rows[i][2]
        if pc != actions[i][1] or frame != actions[i][2]:
            return False
        if (hashlib.sha256(pc).hexdigest().upper()
                != hashlib.sha256(actions[i][1]).hexdigest().upper()):
            return False
        if (hashlib.sha256(frame).hexdigest().upper()
                != hashlib.sha256(actions[i][2]).hexdigest().upper()):
            return False
    return True


guard(_first_two_frames_identical(latch_actions),
      "LOAD-BEARING: the two composed frames are BYTE-IDENTICAL (== and "
      "SHA-256) to the first two frames of the three-frame sweep, so the ONLY "
      "difference between the two attended runs is the missing third frame")
guard(latch_actions[0][1] == actions[0][1] and latch_actions[1][1] == actions[1][1]
      and latch_actions[0][2] == actions[0][2]
      and latch_actions[1][2] == actions[1][2],
      "spelled out one comparison at a time, because a helper that returned "
      "True for the wrong reason would be the only thing standing here")

# ------------------------------------------------ the pins, from both files
_LATCH_SIZES = tuple(
    [len(latch_actions[0][1]), len(latch_actions[0][2]),
     len(latch_actions[1][1]), len(latch_actions[1][2])]
)
guard(_LATCH_SIZES == (173, 185, 120, 131),
      "the two frames are the pinned 173/185 (SPAWN pc/frame) and 120/131 "
      "(DYING_LATCH pc/frame) bytes")
for _i, _label in enumerate(rdh.RUNTIMERES_DEATH_LATCH_ONLY_STEP_ORDER):
    _pin = rdh.RUNTIMERES_DEATH_PINS[_label]
    _pub_latch = _LATCH_JSON["probe"]["per_step"][_label]
    _pub_kill = _SCENARIO_JSON["probe"]["per_step"][_label]
    _pc, _frame = latch_actions[_i][1], latch_actions[_i][2]
    _pc_sha = hashlib.sha256(_pc).hexdigest().upper()
    _frame_sha = hashlib.sha256(_frame).hexdigest().upper()
    guard(len(_pc) == _pin["pc_size"] == _pub_latch["pc_size"]
          == _pub_kill["pc_size"]
          and _pc_sha == _pin["pc_sha256"] == _pub_latch["pc_sha256"]
          == _pub_kill["pc_sha256"],
          "%s PC reproduces the pin the module AND BOTH scenario files publish "
          "(%d bytes / %s)" % (_label, _pin["pc_size"], _pin["pc_sha256"][:16]))
    guard(len(_frame) == _pin["frame_size"] == _pub_latch["frame_size"]
          == _pub_kill["frame_size"]
          and _frame_sha == _pin["frame_sha256"] == _pub_latch["frame_sha256"]
          == _pub_kill["frame_sha256"],
          "%s frame reproduces the pin the module AND BOTH scenario files "
          "publish (%d bytes / %s)"
          % (_label, _pin["frame_size"], _pin["frame_sha256"][:16]))
    guard(_pub_latch == _pub_kill,
          "%s: the two scenario files publish the SAME pin block, so neither "
          "file can be re-pinned alone" % _label)

# ------------------------------- the polarity, re-read by the hand-written
# walker at the top of this file rather than by the module's own decoder
_LATCH_READ = [walk(a[1]) for a in latch_actions]
guard(_LATCH_READ == READ[:2],
      "the independent tag walker reads the same two frames out of the "
      "two-frame sweep that it read out of the three-frame sweep")


def _vt3c_death_task(read_row):
    """0x43BD70, vtable +0x3C: HP == 0 AND timer <= 0.0f."""
    hp = read_row["fields"].get(0x0004)
    timer = read_row["fields"].get(0x0080)
    return hp == 0 and timer is not None and timer <= 0.0


def _vt40_dying_latch(read_row):
    """0x43BDA0, vtable +0x40: HP == 0 AND timer > 0.0f."""
    hp = read_row["fields"].get(0x0004)
    timer = read_row["fields"].get(0x0080)
    return hp == 0 and timer is not None and timer > 0.0


guard(not any(_vt3c_death_task(r) for r in _LATCH_READ),
      "NO frame of the two-frame sweep satisfies 0x43BD70 (vtable +0x3C, HP==0 "
      "AND timer<=0), so 0x443990 never opens, 0x4439E9 never calls 0x472810 "
      "and CActorTask_Dead is never constructed by this sweep")
guard(_vt40_dying_latch(_LATCH_READ[-1])
      and _LATCH_READ[-1]["fields"].get(0x0004) == 0
      and _LATCH_READ[-1]["fields"].get(0x0080)
      == rdh.DYING_LATCH_TIMER_SECONDS > 0.0,
      "and the LAST frame DOES satisfy 0x43BDA0 (vtable +0x40, HP==0 AND "
      "timer>0), so the sweep ends with the dying latch armed and the task gate "
      "shut - which is the whole experimental design")
guard(not _vt40_dying_latch(_LATCH_READ[0])
      and not _vt3c_death_task(_LATCH_READ[0]),
      "the spawn frame satisfies NEITHER predicate (it is alive and carries no "
      "timer at all): an actor cannot be born dead")

# ==========================================================================
# SECTION 8b - REFUSALS.  Each one has to produce NO BYTES AT ALL, not merely
# raise.  "It raised" is a weaker claim than it looks: a composer that raises
# after handing a frame to a caller has already lost.  So every refusal below is
# built as a call, the exception type is asserted, and then the fact that the
# call bound NOTHING is asserted separately.
#
# WHAT IS NOT PROVEN BY THE HELPER.  It proves nothing left the call.  It does
# not prove no bytes were formed INSIDE the call: build_runtimeres_death_sweep
# composes the (harmless, timerless) spawn body before it ever reaches the
# lethal step where a wrong unlock is caught, and those bytes are dropped on the
# floor unreferenced.  What matters for safety is that no caller can ever be
# handed them, and that is what is measured here.
# ==========================================================================
section("8b. REFUSALS - every one of them returns NOTHING, not merely raises")


def _emitted_bytes(value):
    """Total bytes reachable in whatever a refusing call handed back."""
    if type(value) is bytes or type(value) is bytearray:
        return len(value)
    if type(value) in (list, tuple):
        return sum(_emitted_bytes(item) for item in value)
    return 0


def _refuses_with_no_bytes(label, call, exc, expect_text=None):
    produced = []
    try:
        produced.append(call())
    except exc as err:
        text = str(err)
        if produced:
            return guard(False, "%s: raised %s but had ALREADY produced a "
                                "value" % (label, exc.__name__))
        if expect_text is not None and expect_text not in text:
            return guard(False, "%s: refused for the WRONG reason (%r)"
                         % (label, text[:120]))
        return guard(True, "REFUSES and returns nothing: " + label)
    except Exception as err:
        return guard(False, "%s: raised %s, not the required %s"
                     % (label, type(err).__name__, exc.__name__))
    return guard(False, "%s: returned instead of refusing, carrying %d bytes"
                 % (label, _emitted_bytes(produced[0])))


# Every fixture in the rest of this section is the real latch frame with its
# four timer bytes rewritten and NOTHING else touched.  The offset is found once
# and guarded once, and the rewriter degrades to "return the input unchanged"
# rather than slicing at a negative index: if the composer ever drifts, this
# section has to go RED with a sentence a human can read, not die in a traceback
# raised out of a test fixture.
_LATCH_TIMER_PATTERN = (
    bytes([rdh.DEATH_TIMER_TAG])
    + struct.pack("<f", rdh.DYING_LATCH_TIMER_SECONDS)
)
_LATCH_TIMER_OFFSET = latch_actions[1][1].find(_LATCH_TIMER_PATTERN)
guard(_LATCH_TIMER_OFFSET > 0
      and latch_actions[1][1].count(_LATCH_TIMER_PATTERN) == 1,
      "the latch frame literally contains the bytes 2A 0000A041 (tag 0x2A, "
      "20.0f) exactly ONCE, at offset %d, which is what every fixture below "
      "rewrites" % _LATCH_TIMER_OFFSET)


def _with_timer(pc, seconds):
    """`pc` with those four bytes rewritten to `seconds`, same length."""
    if _LATCH_TIMER_OFFSET < 0:
        return pc
    out = bytearray(pc)
    out[_LATCH_TIMER_OFFSET + 1:_LATCH_TIMER_OFFSET + 5] = struct.pack(
        "<f", seconds)
    return bytes(out)


def _latch_rows_with_final_timer(seconds):
    """A copy of the two-frame sweep whose LAST frame carries `seconds` in the
    tag-0x2A f32, so it is no longer the dying latch."""
    rows = [list(a) for a in latch_actions]
    pc = _with_timer(rows[1][1], seconds)
    rows[1][1] = pc
    rows[1][2] = legacy.frame_pc(pc)
    return [tuple(r) for r in rows]


def _with_widened_allowlist(profile, call):
    """Run `call` with `profile` temporarily inside the module allowlist.

    This is the only way to reach the validator's own DEATH_TASK-label rule,
    because the allowlist refuses the shape first.  The widening is undone in a
    finally and then asserted undone by a guard, so the tool cannot leave a
    forged profile installed in a module the rest of this process shares.
    """
    saved = rdh._ALLOWED_PROFILES
    rdh._ALLOWED_PROFILES = tuple(saved) + (profile,)
    try:
        return call()
    finally:
        rdh._ALLOWED_PROFILES = saved


_SAVED_ALLOWED_PROFILES = rdh._ALLOWED_PROFILES


# 1. a two-frame profile that somehow reaches the task gate.  This is the
#    refusal the whole variant depends on: a two-frame run that opened the gate
#    would answer nothing, because the pose could then have come from either
#    place again - exactly the ambiguity GT-022 already has.
#
#    WHICH RULE ACTUALLY CATCHES IT, measured rather than assumed.  The first
#    two calls below zero (and then negate) the timer of the real two-frame
#    sweep, and the validator refuses them - but NOT on the "must never satisfy
#    vt+0x3C" rule this section was written expecting.  In a two-frame sweep the
#    single kill frame is also the only frame that can latch, so taking its
#    timer to <= 0 removes the latch at the same time, and the earlier "no frame
#    satisfies vt+0x40" rule fires first.  The expected text below is pinned to
#    what the validator really says, because a guard that asserts the wrong
#    reason is a guard that will one day pass for the wrong reason.  The third
#    call then reaches the intended rule the only way it can be reached: a
#    not-ending-on-the-task profile that latches first and opens the gate after.
_refuses_with_no_bytes(
    "a two-frame sweep whose kill frame is taken to timer 0.0f (HP==0 AND "
    "timer<=0) - zeroing the only kill frame also removes the only latch, and "
    "the sweep is refused for that",
    lambda: rdh.validate_runtimeres_death_sweep(
        _latch_rows_with_final_timer(0.0), latch_profile),
    rdh.RuntimeResDeathValidationError,
    "no frame satisfies vt+0x40",
)
_refuses_with_no_bytes(
    "the same with an already-negative timer (-1.0f): <= 0 is <= 0, and this "
    "profile may not emit it either",
    lambda: rdh.validate_runtimeres_death_sweep(
        _latch_rows_with_final_timer(-1.0), latch_profile),
    rdh.RuntimeResDeathValidationError,
    "no frame satisfies vt+0x40",
)
# The gate-opening shape that survives the latch check: latch at 20.0f as
# usual, and then a THIRD frame at 0.0f, i.e. exactly the three-frame sweep
# wearing the two-frame profile's name.  This is the sweep a careless future
# round would produce by extending the plan and forgetting the flag, and it is
# the one that must never be handed back.
_FORGED_REACHES_GATE_PROFILE = dataclasses.replace(
    latch_profile,
    step_order=(rdh.SPAWN_STEP_LABEL, rdh.DYING_LATCH_STEP_LABEL,
                rdh.DYING_LATCH_STEP_LABEL),
)
_GATE_PC = actions[2][1]
_FORGED_REACHES_GATE_ROWS = list(latch_actions) + [(
    rdh.RUNTIMERES_DEATH_ACTION_LABEL_PREFIX + rdh.DYING_LATCH_STEP_LABEL,
    _GATE_PC, actions[2][2], rdh.RUNTIMERES_DEATH_SPACING_SECONDS,
)]
_refuses_with_no_bytes(
    "a not-ending-on-the-task profile that latches AND THEN opens the task "
    "gate (the real DEATH_TASK frame smuggled in under a latch label) - it "
    "would destroy the only question this profile exists to answer",
    lambda: _with_widened_allowlist(
        _FORGED_REACHES_GATE_PROFILE,
        lambda: rdh.validate_runtimeres_death_sweep(
            _FORGED_REACHES_GATE_ROWS, _FORGED_REACHES_GATE_PROFILE)),
    rdh.RuntimeResDeathValidationError,
    "must never satisfy vt+0x3C",
)

# 2. a profile carrying the DEATH_TASK label while claiming not to end on it.
#    The allowlist stops this shape before the validator ever sees it, so the
#    refusal is proved TWICE: once at the allowlist, and once at the validator
#    with the allowlist temporarily widened to let the forgery through.  The
#    second half matters because a check that is only ever reached through a
#    door that is always shut has never actually been run.
_FORGED_TASK_LABEL_PROFILE = dataclasses.replace(
    latch_profile,
    step_order=rdh.RUNTIMERES_DEATH_STEP_ORDER,
    lethal_step_labels=rdh.RUNTIMERES_DEATH_LETHAL_STEP_LABELS,
)
guard(_FORGED_TASK_LABEL_PROFILE.ends_on_death_task is False
      and rdh.DEATH_TASK_STEP_LABEL in _FORGED_TASK_LABEL_PROFILE.step_order,
      "the forgery is what it says on the tin: DEATH_TASK in the plan, "
      "ends_on_death_task still False")
_refuses_with_no_bytes(
    "a profile carrying the DEATH_TASK label with ends_on_death_task False - "
    "the exact-object allowlist refuses it outright",
    lambda: rdh.require_runtimeres_death_hypothesis_scenario(
        _FORGED_TASK_LABEL_PROFILE),
    ValueError,
    "exceeds the allowlist",
)


# The third row re-uses the DYING_LATCH bytes under the DEATH_TASK label, so the
# timer stays at 20.0 and the "never reaches <= 0" rule cannot fire first: the
# only rule left to catch this is the label rule itself.
_FORGED_TASK_LABEL_ROWS = list(latch_actions) + [(
    rdh.RUNTIMERES_DEATH_ACTION_LABEL_PREFIX + rdh.DEATH_TASK_STEP_LABEL,
    latch_actions[1][1], latch_actions[1][2],
    rdh.RUNTIMERES_DEATH_SPACING_SECONDS,
)]
_refuses_with_no_bytes(
    "the same forgery with the allowlist temporarily widened - the validator "
    "itself refuses a not-ending-on-the-task profile that names the DEATH_TASK "
    "step, and does it on the label rather than on the timer",
    lambda: _with_widened_allowlist(
        _FORGED_TASK_LABEL_PROFILE,
        lambda: rdh.validate_runtimeres_death_sweep(
            _FORGED_TASK_LABEL_ROWS, _FORGED_TASK_LABEL_PROFILE)),
    rdh.RuntimeResDeathValidationError,
    "must not carry",
)

# 3. a sweep whose LAST frame is not the latch.
#    Reaching this rule takes some care, and saying how is more useful than
#    hiding it: for any kill frame the timer is either > 0 (the latch) or <= 0
#    (the task gate), so a two-frame sweep whose last frame is not the latch
#    normally trips the "must never satisfy vt+0x3C" rule first - as the two
#    refusals above show.  The one value that is NEITHER is a NaN, which is
#    unordered against 0.0f and therefore satisfies neither predicate as this
#    validator reads them.  That is what the frame below carries, and it is the
#    only shape that reaches the last-frame rule.
#    NOT CLAIMED: anything at all about what the client's comiss/jb pair does
#    with an unordered compare.  This frame is a test fixture; it is never sent,
#    and no conclusion about client behaviour is drawn from it.
_FORGED_TRAILING_PROFILE = dataclasses.replace(
    latch_profile,
    step_order=(rdh.SPAWN_STEP_LABEL, rdh.DYING_LATCH_STEP_LABEL,
                rdh.DYING_LATCH_STEP_LABEL),
)
_NAN_PC = _with_timer(latch_actions[1][1], float("nan"))
guard(_NAN_PC != latch_actions[1][1]
      and len(_NAN_PC) == len(latch_actions[1][1]),
      "the unordered-timer fixture is the latch frame with its four timer bytes "
      "replaced and nothing else (same length, different bytes)")
_FORGED_TRAILING_ROWS = list(latch_actions) + [(
    rdh.RUNTIMERES_DEATH_ACTION_LABEL_PREFIX + rdh.DYING_LATCH_STEP_LABEL,
    _NAN_PC, legacy.frame_pc(_NAN_PC), rdh.RUNTIMERES_DEATH_SPACING_SECONDS,
)]
_refuses_with_no_bytes(
    "a sweep whose LAST frame is not the dying latch (its timer is unordered "
    "against 0.0f, so it satisfies neither vt+0x40 nor vt+0x3C) - the sweep "
    "would end with something other than the latch pending",
    lambda: _with_widened_allowlist(
        _FORGED_TRAILING_PROFILE,
        lambda: rdh.validate_runtimeres_death_sweep(
            _FORGED_TRAILING_ROWS, _FORGED_TRAILING_PROFILE)),
    rdh.RuntimeResDeathValidationError,
    "the LAST frame of profile",
)
guard(rdh._ALLOWED_PROFILES is _SAVED_ALLOWED_PROFILES
      and len(rdh._ALLOWED_PROFILES) == 2
      and rdh.RUNTIMERES_DEATH_PROFILE_BY_NAME[
          rdh.RUNTIMERES_DEATH_PROFILE_DYING_LATCH_ONLY] is latch_profile,
      "the temporary widening is UNDONE: the module allowlist is the same "
      "two-profile object it was before, by identity")

# 4. the unlocks are per profile, in BOTH directions, at the primitive and at
#    the composer.  The composer half is the one that matters for "no bytes":
#    build_runtimeres_death_sweep is the only function in this lane that would
#    hand a caller a frame.
_refuses_with_no_bytes(
    "the THREE-frame unlock used against the two-frame profile "
    "(require_runtimeres_death_lethal_unlock_for)",
    lambda: rdh.require_runtimeres_death_lethal_unlock_for(
        unlock, latch_profile),
    ValueError,
    "issued for a different",
)
_refuses_with_no_bytes(
    "the TWO-frame unlock used against the three-frame profile "
    "(require_runtimeres_death_lethal_unlock_for)",
    lambda: rdh.require_runtimeres_death_lethal_unlock_for(
        latch_unlock, scenario),
    ValueError,
    "issued for a different",
)
_refuses_with_no_bytes(
    "composing the two-frame sweep with the three-frame unlock - no frame is "
    "returned to anyone",
    lambda: rdh.build_runtimeres_death_sweep(
        legacy, probe, unlock, latch_profile),
    ValueError,
    "issued for a different",
)
_refuses_with_no_bytes(
    "composing the three-frame sweep with the two-frame unlock - no frame is "
    "returned to anyone",
    lambda: rdh.build_runtimeres_death_sweep(
        legacy, probe, latch_unlock, scenario),
    ValueError,
    "issued for a different",
)

# 5. a value-equal but DISTINCT forged unlock.  The unlock is a frozen
#    dataclass, so `==` is free to anyone who can read the module; identity is
#    not.  The first guard proves the forgery really is value-equal, otherwise
#    the two refusals below would be proving something much cheaper.
_FORGED_UNLOCK = rdh.RuntimeResDeathLethalUnlock(
    latch_profile.scenario_id, latch_profile.hypothesis_id,
)
guard(_FORGED_UNLOCK == latch_unlock and _FORGED_UNLOCK is not latch_unlock,
      "the forged unlock is EQUAL to the real two-frame unlock and is a "
      "different object - so only an identity check can tell them apart")
_refuses_with_no_bytes(
    "a value-equal but distinct forged unlock at the primitive",
    lambda: rdh.require_runtimeres_death_lethal_unlock_for(
        _FORGED_UNLOCK, latch_profile),
    ValueError,
    "without the lethal unlock",
)
_refuses_with_no_bytes(
    "a value-equal but distinct forged unlock at the composer - it gets no "
    "frames at all",
    lambda: rdh.build_runtimeres_death_sweep(
        legacy, probe, _FORGED_UNLOCK, latch_profile),
    ValueError,
    "without the lethal unlock",
)

# ==========================================================================
# SECTION 8c - TRAPS.  The house rule is that a check which has never been seen
# to fail is not a check, it is a printout.  Each trap mutates a COPY, requires
# the specific guard above to reject it, and then requires the untouched thing
# to pass again - so the trap also proves it left nothing behind.
# ==========================================================================
section("8c. TRAPS - each new guard is watched going red on a mutated copy, "
        "then green again on the real thing")

# TRAP 1 - the byte-identity guard.  The mutation is deliberately BENIGN to
# every other guard in this section: a 20.0f latch timer becomes 19.0f, which is
# still HP==0 with a positive timer, still satisfies vt+0x40, still never
# reaches the task gate, and still ends the sweep on the latch.  Every polarity
# guard above stays green on it.  The identity guard is the one that has to
# notice, because "the two runs differ only by the missing third frame" is
# precisely the thing 19.0f would falsify.
_TRAP_ROWS = _latch_rows_with_final_timer(19.0)
_TRAP_READ = walk(_TRAP_ROWS[1][1])
guard(_TRAP_ROWS[1][1] != latch_actions[1][1]
      and _vt40_dying_latch(_TRAP_READ)
      and not _vt3c_death_task(_TRAP_READ)
      and _TRAP_READ["fields"][0x0080] == 19.0,
      "TRAP 1 setup: the mutated copy is still a valid-looking dying latch "
      "(HP==0, timer 19.0 > 0), so nothing except byte identity can catch it")
guard(_first_two_frames_identical(_TRAP_ROWS) is False,
      "TRAP 1: the byte-identity guard goes RED on that copy - it is a real "
      "check and has now been seen to fail")
guard(_first_two_frames_identical(latch_actions) is True,
      "TRAP 1 restored: the untouched two-frame sweep passes the same guard, "
      "so the trap mutated a copy and nothing else")

# TRAP 2 - the profile allowlist.  A copy of the real two-frame profile with
# ONE field flipped (ends_on_death_task True) is exactly the object that would
# let a two-frame run be validated by three-frame rules.
_TRAP_PROFILE = dataclasses.replace(latch_profile, ends_on_death_task=True)
guard(_TRAP_PROFILE != latch_profile
      and _TRAP_PROFILE.step_order == latch_profile.step_order
      and _TRAP_PROFILE.scenario_id == latch_profile.scenario_id,
      "TRAP 2 setup: the copy differs from the real profile in exactly one "
      "field, and still carries the real scenario id")
_refuses_with_no_bytes(
    "TRAP 2: a copy of the two-frame profile with ends_on_death_task flipped "
    "to True is refused by the allowlist",
    lambda: rdh.require_runtimeres_death_hypothesis_scenario(_TRAP_PROFILE),
    ValueError,
    "exceeds the allowlist",
)
guard(rdh.require_runtimeres_death_hypothesis_scenario(latch_profile)
      is latch_profile,
      "TRAP 2 restored: the real profile still passes the same allowlist")

# TRAP 3 - the exact-tree comparator the loader uses.  No file is written by
# this tool, ever, so the mutation happens on the loaded dict in memory and is
# handed to the SAME comparator load_runtimeres_death_hypothesis_scenario calls.
# NOT CLAIMED: this exercises the comparator, not the file reading around it.
_TRAP_TREE = json.loads(json.dumps(_LATCH_JSON))
_TRAP_TREE["dispatch"]["ends_on_death_task"] = True
guard(rdh._exact_equal(_LATCH_JSON, rdh._expected_scenario(latch_profile)),
      "the two-frame file on disk is EXACTLY the tree the module expects for "
      "this profile - no extra key, no missing key, no loose type")
guard(rdh._exact_equal(_TRAP_TREE, rdh._expected_scenario(latch_profile))
      is False,
      "TRAP 3: one flipped boolean deep inside a copy of that tree makes the "
      "comparator go RED")
guard(rdh._exact_equal(_LATCH_JSON, rdh._expected_scenario(latch_profile)),
      "TRAP 3 restored: the untouched tree still compares equal")


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
    # Additive, round 91.  The three keys above keep their exact meaning; a
    # consumer that never heard of the second profile reads the same values it
    # read before.
    "latch_only_profile": {
        "scenario": LATCH_SCENARIO_PATH.replace("\\", "/").split("/")[-1],
        "profile": latch_profile.profile_name,
        "ends_on_death_task": latch_profile.ends_on_death_task,
        "step_order": list(latch_profile.step_order),
        "lethal_steps": list(latch_profile.lethal_step_labels),
        "frames_byte_identical_to_first_two_of_spawn_then_kill":
            _first_two_frames_identical(latch_actions),
        "frames": [
            {
                "label": latch_actions[i][0],
                "delay_seconds": latch_actions[i][3],
                "pc_size": len(latch_actions[i][1]),
                "frame_size": len(latch_actions[i][2]),
                "pc_sha256": hashlib.sha256(
                    latch_actions[i][1]).hexdigest().upper(),
                "frame_sha256": hashlib.sha256(
                    latch_actions[i][2]).hexdigest().upper(),
                "satisfies_vt40_dying_latch": _vt40_dying_latch(_LATCH_READ[i]),
                "satisfies_vt3c_death_task": _vt3c_death_task(_LATCH_READ[i]),
            }
            for i in range(len(latch_actions))
        ],
        "any_frame_opens_the_task_gate":
            any(_vt3c_death_task(r) for r in _LATCH_READ),
        "nonclaims": list(rdh.RUNTIMERES_DEATH_LATCH_ONLY_NONCLAIMS),
    },
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
