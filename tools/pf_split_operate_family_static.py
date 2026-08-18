#!/usr/bin/env python3
"""PF SPLIT-OPERATE-002 — static enumeration of the op6 quantity-op FAMILY and
the bounding of the stack-split candidate to a single inventory verb.

Supplement to SPLIT-OPERATE-001 (chief round 68). 001 proved that a stack-split
has no dedicated opcode: every item action rides ItemOperateVitalReq 0x4BED and
is discriminated by one operation byte (obj+0x14, wire tag 0x0B), with op6 being
the quantity-parameterized producer. 001 deliberately did NOT claim "op6 == split
specifically", because op6 is a quantity-op family (split / drop-N / sell-N / ...).

002 closes the open question of 001's next hop as far as static disassembly can:
it enumerates, byte-exact, every producer callsite of the op6 factory 0x59F870 and
shows the search space is bounded and structured, without a live capture:

  * op6 factory 0x59F870 has EXACTLY FOUR call sites in .text:
        0x0057D1F4, 0x0058294D, 0x005A3532, 0x005BA208
    -> op6 is definitively a SHARED quantity-op family, not a split opcode.
  * every site passes the identical (qty_low, qty_high, item_handle) triad and the
    factory serializes value32(+0x18)=item_handle and qword(+0x20/+0x24)=64-bit
    quantity, with `ret 0xc` (three dword args). No destination-slot argument at any
    site -> the op6 wire shape is uniform regardless of which verb produced it.
  * the inventory ACTION DISPATCHER is one function [0x005A2A70, 0x005A40B0):
    it contains the op4=MOVE producer call (verb eax==2 @0x5A3491, factory 0x59F7C0)
    AND exactly ONE op6 site (verb eax==0x16 @0x5A3532). The other three op6 sites
    live in three DISTINCT functions (starts 0x0057D041, 0x00582730, 0x005B9F70),
    outside the dispatcher. So within the backpack move/equip dispatcher, verb 0x16
    is the UNIQUE quantity-op path -> the bounded split candidate.
  * verb 0x16 opens numeric-input dialog resource 0x12 (0x5A34D7), guards the entry
    strictly positive (0x5A34EF), and only then calls op6.
  * server gap unchanged: current/pf_login_game_server_v141.py builds an operation-4
    move response and special-cases the operation-5 equip decode, but has NO handler
    for operation 6 (or 3). All four op6 verbs are unimplemented server-side.

STILL NOT CLAIMED: verb 0x16 == split specifically. Even bounded to one inventory
verb, op6-with-no-destination is equally consistent with backpack drop-N / destroy-N.
A positive "split" label needs the dialog-resource 0x12 caption resolution or a live
capture of the interaction. 002 narrows the next-hop search space from "some op6
verb somewhere" to "verb 0x16 in the inventory dispatcher (one of four op6 verbs)".

Report-only / additive: NO server-source change, NO scenario, NO ledger entry, NO
runtime claim. Sole evidence = the read-only client binary GameClient/GameClient.local.bin
(disassembled) cross-checked against the read-only server source. split_stack stays
in_progress (characterized, not implemented; no runtime_pass).

Usage:  py -3 tools/pf_split_operate_family_static.py [path-to-GameClient.local.bin]
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
"""
import sys, struct, hashlib

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    sys.exit("capstone required: pip install capstone")

BIN = sys.argv[1] if len(sys.argv) > 1 else "GameClient/GameClient.local.bin"
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

# Server cross-check source (read-only; frozen V141).
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_SRC = os.path.normpath(os.path.join(_HERE, "..", "current", "pf_login_game_server_v141.py"))

data = open(BIN, "rb").read()
sha = hashlib.sha256(data).hexdigest().upper()

e_lfanew = struct.unpack_from('<I', data, 0x3c)[0]; coff = e_lfanew + 4
nsec = struct.unpack_from('<H', data, coff + 2)[0]
opt_size = struct.unpack_from('<H', data, coff + 16)[0]; opt = coff + 20
image_base = struct.unpack_from('<I', data, opt + 28)[0]
sect = opt + opt_size
secs = []
for i in range(nsec):
    off = sect + i * 40
    nm = data[off:off + 8].rstrip(b'\0').decode('latin1')
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, off + 8)
    secs.append((nm, vaddr, vsize, rawptr, rawsize))


def va2off(va):
    r = va - image_base
    for n, vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= r < vaddr + max(vsize, rawsize):
            return rawptr + (r - vaddr)
    return None


def rd(va, n):
    o = va2off(va); return data[o:o + n]


def span_sha(a, b):
    return hashlib.sha256(rd(a, b - a)).hexdigest().upper()


TEXT = [s for s in secs if s[0] == '.text'][0]
_, TVADDR, TVSIZE, _, _ = TEXT
TSTART = image_base + TVADDR
TEND = TSTART + TVSIZE

md = Cs(CS_ARCH_X86, CS_MODE_32)

fails = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    if not cond:
        fails.append(name)


def callers_of(target):
    """Every E8 rel32 in .text whose target is `target` VA (byte-exact)."""
    res = []
    for va in range(TSTART, TEND - 5):
        o = va2off(va)
        if data[o] == 0xE8:
            rel = struct.unpack_from('<i', data, o + 1)[0]
            if ((va + 5 + rel) & 0xffffffff) == target:
                res.append(va)
    return res


check("binary SHA-256 matches", sha == EXPECT_SHA, sha)

# ---------------------------------------------------------------------------
# 1. op6 factory 0x59F870: operation immediate, field layout, calling contract
# ---------------------------------------------------------------------------
check("op6 factory writes operation=6 (C6 40 14 06) @0x59F895",
      rd(0x59f895, 4) == bytes([0xC6, 0x40, 0x14, 0x06]))
o6 = {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(0x59f870, 0x40), 0x59f870)}
check("op6 value32 field obj+0x18 = 3rd dword arg (item handle)",
      o6.get(0x59f88d) == ('mov', 'dword ptr [eax + 0x18], ecx'))
check("op6 qword field low  obj+0x20 = 1st dword arg (qty low)",
      o6.get(0x59f899) == ('mov', 'dword ptr [eax + 0x20], edx'))
check("op6 qword field high obj+0x24 = 2nd dword arg (qty high)",
      o6.get(0x59f89c) == ('mov', 'dword ptr [eax + 0x24], ecx'))
check("op6 factory is stdcall with three dword args (ret 0xC) @0x59F8AB",
      rd(0x59f8ab, 3) == bytes([0xC2, 0x0C, 0x00]))

# ---------------------------------------------------------------------------
# 2. op6 has EXACTLY four call sites; op4/op3 cross-check has exactly one each
# ---------------------------------------------------------------------------
OP6_SITES = [0x0057d1f4, 0x0058294d, 0x005a3532, 0x005ba208]
op6_callers = callers_of(0x59f870)
check("op6 factory 0x59F870 has exactly 4 call sites",
      op6_callers == OP6_SITES, str([hex(x) for x in op6_callers]))

op4_callers = callers_of(0x59f7c0)
check("op4(move) factory 0x59F7C0 has exactly one call site @0x5A3491 (verb eax==2)",
      op4_callers == [0x005a3491], str([hex(x) for x in op4_callers]))
op3_callers = callers_of(0x59f780)
check("op3 factory 0x59F780 has exactly one call site @0x5B9D0C",
      op3_callers == [0x005b9d0c], str([hex(x) for x in op3_callers]))

# byte-span pin of each op6 call site window [call-0x14, call+5]
OP6_SITE_SPANS = {
    0x0057d1f4: "D5BC98C5D2BD7C8790AAF92AE248948DFA4394CD8CD13E5BB29EC95F68B8055B",
    0x0058294d: "0E1D6182C225FE0CDA77D22AF42AEECB18CD893D1BFF78268E26F73F9F53D457",
    0x005a3532: "69927F2F32DAB0B7403098B0BCFB4CB0B9D00C5CE1B4BD16DDC153B5A0A4A4CB",
    0x005ba208: "33CA0EB8DF85EEE9BAB15D2CC0E26550B753DBB446ADBFE1DFD81B3D010FC3B7",
}
for site, exp in OP6_SITE_SPANS.items():
    check(f"op6 call site {site:#08x} window byte-identical",
          span_sha(site - 0x14, site + 5) == exp, span_sha(site - 0x14, site + 5))

# ---------------------------------------------------------------------------
# 3. inventory action dispatcher = one function [0x5A2A70, 0x5A40B0)
#    holds op4/verb2 AND exactly one op6 site (verb 0x16); others are outside
# ---------------------------------------------------------------------------
DISP_START, DISP_END = 0x005a2a70, 0x005a40b0
check("dispatcher prologue @0x5A2A70 (push ebp;mov ebp,esp;and esp,-8;push -1;push 0xB9AFD7)",
      rd(0x5a2a70, 13) == bytes.fromhex("558bec83e4f86aff68d7afb900"))
# no int3 padding between the prologue and the op6 site -> one contiguous function
int3s = [i.address for i in md.disasm(rd(DISP_START, 0x5a3540 - DISP_START), DISP_START)
         if i.mnemonic == 'int3']
check("no int3 boundary in [0x5A2A70, 0x5A3540) (contiguous dispatcher body)",
      int3s == [], str([hex(x) for x in int3s]))
# next function prologue after the dispatcher body confirms the [start,end) window
nb = None
for va in range(0x5a3540, 0x5a4200):
    o = va2off(va)
    if data[o] == 0x55 and data[o + 1] == 0x8b and data[o + 2] == 0xec:
        nb = va; break
check("next function prologue begins at 0x5A40B0 (dispatcher end bound)",
      nb == DISP_END, hex(nb) if nb else "none")
# membership: op4-move site and exactly one op6 site fall inside the dispatcher
check("op4(move) verb-2 site 0x5A3491 is inside the dispatcher",
      DISP_START <= 0x005a3491 < DISP_END)
inside = [s for s in OP6_SITES if DISP_START <= s < DISP_END]
check("exactly one op6 site is inside the dispatcher, and it is verb-0x16 @0x5A3532",
      inside == [0x005a3532], str([hex(x) for x in inside]))
# the other three op6 sites are in three distinct functions, none == dispatcher start
def func_start(va):
    for a in range(va - 1, va - 0x2000, -1):
        o = va2off(a)
        if data[o] == 0x55 and data[o + 1] == 0x8b and data[o + 2] == 0xec:
            return a
        if data[o] == 0xcc and data[o + 1] != 0xcc:
            return a + 1
    return None
others = [s for s in OP6_SITES if s != 0x005a3532]
other_funcs = [func_start(s) for s in others]
check("the other three op6 sites live in three distinct functions (0x57D041,0x582730,0x5B9F70)",
      other_funcs == [0x0057d041, 0x00582730, 0x005b9f70]
      and DISP_START not in other_funcs, str([hex(x) for x in other_funcs]))

# ---------------------------------------------------------------------------
# 4. verb 0x16 path: cmp eax,0x16 -> numeric dialog res 0x12 -> positive guard -> op6
# ---------------------------------------------------------------------------
check("verb dispatch compares eax==0x16 @0x5A349B (83 F8 16)",
      rd(0x5a349b, 3) == bytes([0x83, 0xF8, 0x16]))
check("verb 0x16 opens numeric-input dialog resource 0x12 @0x5A34D7",
      rd(0x5a34d7, 11) == bytes.fromhex("c784248001000012000000"))
inv = {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(0x5a34e2, 6), 0x5a34e2)}
check("verb 0x16 calls numeric-input dialog 0x5A1630 @0x5A34E2",
      inv.get(0x5a34e2) == ('call', '0x5a1630'))
check("verb 0x16 guards dialog result strictly positive @0x5A34EF (cmp dword[eax+0x2c],0)",
      rd(0x5a34ef, 4) == bytes([0x83, 0x78, 0x2C, 0x00]))
callop6 = {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(0x5a3532, 6), 0x5a3532)}
check("verb 0x16 then calls op6 factory 0x59F870 @0x5A3532",
      callop6.get(0x5a3532) == ('call', '0x59f870'))
# byte-span pin of the whole verb-0x16 case body [0x5A349B, 0x5A3537)
check("verb-0x16 case body span 0x5A349B..0x5A3537 byte-identical",
      span_sha(0x5a349b, 0x5a3537) ==
      "1E2EB3E248E255CCB281783A3B089BBD81DAEBC2A8208EC7995A5DBA6B089979",
      span_sha(0x5a349b, 0x5a3537))

# ---------------------------------------------------------------------------
# 5. server op6 gap (read-only cross-check): op4 response + op5 decode, no op6/op3
# ---------------------------------------------------------------------------
src = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
check("server declares ITEM_OPERATE_REQ_VITAL = 0x4BED",
      "ITEM_OPERATE_REQ_VITAL = 0x4BED" in src)
check("server special-cases the equip operation (V123_EQUIP_FROM_BAG_OPERATION = 5)",
      "V123_EQUIP_FROM_BAG_OPERATION = 5" in src)
check("server builds an operation-4 move response (make_item_operate_move_delta_success)",
      "def make_item_operate_move_delta_success" in src)
def _has(op):
    return (f"operation=={op}" in src.replace(" ", "")) or (f"operation is {op}" in src)
check("server has NO operation==6 handler (quantity op unimplemented)", not _has(6))
check("server has NO operation==3 handler (single-target op unimplemented)", not _has(3))
check("server builds NO split/quantity item-operate response",
      "def make_item_operate_split" not in src
      and "def make_item_operate_quantity" not in src)

print()
if fails:
    print(f"RESULT: {len(fails)} guard(s) drifted: {fails}")
    sys.exit(1)
print("RESULT: all op6 quantity-op family static guards reproduced (exit 0)")
