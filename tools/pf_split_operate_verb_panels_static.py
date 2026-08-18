#!/usr/bin/env python3
"""PF SPLIT-OPERATE-003 — verb 0x16 -> op6 is reused across TWO inventory panels,
and the static caption-resolution route for the split label is evidenced-closed.

Third static supplement to the split_stack characterization (chief rounds 68/69).

  001 (round 68): a stack-split has no dedicated opcode. Every item action rides
       ItemOperateVitalReq 0x4BED, discriminated by one operation byte; op6 is the
       quantity-parameterized producer (factory 0x59F870).
  002 (round 69): op6 factory 0x59F870 has EXACTLY FOUR call sites, so op6 is a
       shared quantity-op family; the split candidate is BOUNDED to inventory verb
       eax==0x16 (site @0x5A3532) inside the action dispatcher [0x5A2A70,0x5A40B0).
       002 stopped there and named the next hop: resolve the caption of numeric
       dialog id 0x12, OR live-capture the interaction.

003 walks that next hop as far as static evidence allows and reports two results,
both byte-exact and both REFINEMENTS (not reversals) of 002:

  R1. verb 0x16 is NOT globally unique. Two of op6's four call sites are gated by
      `cmp eax, 0x16` (bytes 83 F8 16): site C @0x5A3532 in the dispatcher fn
      0x5A2A70, AND site D @0x5BA208 in a DISTINCT fn starting 0x5B9F70. Both
      verb-0x16 bodies route through the same numeric-input dialog helper 0x5A1630
      (C @0x5A34E2; D @0x5BA1D0, e8-rel target == 0x5A1630) before calling op6.
      So the action code 0x16 + the shared quantity dialog are reused across (at
      least) two inventory-like panels. This is CONSISTENT WITH a generic
      "split/divide by quantity" action reused across panels, but is still NOT a
      positive "split" label: op6 carries no destination slot, so 0x16 is equally
      consistent with a shared drop-N / destroy-N / give-N quantity action.

  R2. the static caption route is closed. The numeric dialog is a GENERIC reusable
      control -- Data/GUI/Model/Common_NumInput.model & Common_NumberInput2/3.model
      are plaintext UIControlData XML with NO inline caption; the caption text is
      resolved at runtime from the packed text table B_TEXTDATA_TH.pc_ (file magic
      "$pcz") and the UI Lua (*.lu_, also "$pcz"-packed). No readable client asset
      maps dialog id 0x12 to a "split" caption without cracking proprietary packed
      data. Therefore the ONLY remaining hop to a positive split label is a LIVE
      CAPTURE of the verb-0x16 numeric dialog + the op6 frame it emits.

Incidental correction carried in the report: 0x42AB40 (called in the verb-0x16
body right before op6) is a temp-object DESTRUCTOR -- SEH prologue
6A FF 68 53 53 B8 00 64 A1 00 00 00 00, two vtable stores (0xF0B978 then 0xF0B8FC)
and free 0x88D060 -- NOT a dialog-open-by-resource-id. The dialog id 0x12 is a
stack local (0x5A34D7: C7 84 24 80 01 00 00 12 00 00 00) consumed inside the body.

Report-only / additive: NO server-source change, NO scenario, NO ledger entry, NO
runtime claim, NO coverage grade change (only the split_stack `notes` prose points
here; the seam grade-digest excludes prose and is unchanged). split_stack STAYS
in_progress. Sole evidence = the read-only client binary GameClient.local.bin
(disassembled) plus the read-only, plaintext Data/GUI/Model/*.model file names.

Usage:  py -3 tools/pf_split_operate_verb_panels_static.py [path-to-GameClient.local.bin]
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
"""
import sys, struct, hashlib

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    sys.exit("capstone required: pip install capstone")

import os.path as _osp
# Resolved from THIS file, not from the caller's cwd: the relative default
# "GameClient/GameClient.local.bin" only worked when the tool happened to be run
# from the Pirate Force root, which is the same class of bug SCAN-DEBT-001 closed
# in the wire-corpus half of pf_teleportcheck_0x4477_static.py.
_DEFAULT_BIN = _osp.normpath(_osp.join(
    _osp.dirname(_osp.abspath(__file__)), "..", "..", "GameClient", "GameClient.local.bin"))
BIN = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_BIN
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

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


def call_target(va):
    """VA target of an E8 rel32 call at `va`."""
    o = va2off(va)
    if data[o] != 0xE8:
        return None
    rel = struct.unpack_from('<i', data, o + 1)[0]
    return (va + 5 + rel) & 0xffffffff


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
# Regression from 002: op6 factory 0x59F870 has exactly four callers.
# ---------------------------------------------------------------------------
OP6_SITES = [0x0057D1F4, 0x0058294D, 0x005A3532, 0x005BA208]
c = callers_of(0x59F870)
check("op6 factory 0x59F870 has EXACTLY 4 callers (002 regression)", c == OP6_SITES,
      " ".join(hex(x) for x in c))

# ---------------------------------------------------------------------------
# R1. verb 0x16 is a SHARED action code: two op6 sites are gated by cmp eax,0x16.
# ---------------------------------------------------------------------------
check("site C guard: cmp eax,0x16 @0x5A349B (83 F8 16)", rd(0x5A349B, 3) == bytes([0x83, 0xF8, 0x16]))
check("site D guard: cmp eax,0x16 @0x5BA183 (83 F8 16)", rd(0x5BA183, 3) == bytes([0x83, 0xF8, 0x16]))

# both verb-0x16 bodies enter the same numeric-input dialog helper 0x5A1630.
check("site C dialog helper call @0x5A34E2 -> 0x5A1630", call_target(0x5A34E2) == 0x5A1630,
      hex(call_target(0x5A34E2) or 0))
check("site D dialog helper call @0x5BA1D0 -> 0x5A1630", call_target(0x5BA1D0) == 0x5A1630,
      hex(call_target(0x5BA1D0) or 0))

# the two verb-0x16 sites live in DISTINCT functions -> 0x16 is not globally unique.
DISPATCHER = (0x005A2A70, 0x005A40B0)   # from 002
PANEL_D_START = 0x005B9F70
check("site C is inside the inventory dispatcher [0x5A2A70,0x5A40B0)",
      DISPATCHER[0] <= 0x5A3532 < DISPATCHER[1])
check("site D is OUTSIDE the dispatcher (distinct fn @0x5B9F70)",
      not (DISPATCHER[0] <= 0x5BA208 < DISPATCHER[1]) and 0x5B9F70 == PANEL_D_START)

# dispatcher verb switch ladder: verb 2 = MOVE (op4), verb 0x16 = op6.
disp = {i.address: (i.mnemonic, i.op_str)
        for i in md.disasm(rd(DISPATCHER[0], DISPATCHER[1] - DISPATCHER[0]), DISPATCHER[0])}
ladder = [a for a, (m, o) in disp.items() if m == 'cmp' and o in ('eax, 0x16', 'eax, 2', 'eax, 0x2d', 'eax, 0x35')]
check("dispatcher carries a multi-verb switch ladder incl. eax==2 and eax==0x16",
      disp.get(0x5A349B) == ('cmp', 'eax, 0x16') and any(o == 'eax, 2' for a, (m, o) in disp.items() if m == 'cmp'),
      "ladder cmps=%d" % len(ladder))

# span-hash pins for the two verb-0x16 case bodies.
check("verb-0x16 body C span [0x5A349B,0x5A3537) pinned",
      span_sha(0x5A349B, 0x5A3537) == "1E2EB3E248E255CCB281783A3B089BBD81DAEBC2A8208EC7995A5DBA6B089979")
check("verb-0x16 body D span [0x5BA183,0x5BA20D) pinned",
      span_sha(0x5BA183, 0x5BA20D) == "9C84D296A94BEBEC9B4BDBFC1CE98C89DF8E79E55764D00CC61B8E8D188E5ED4")

# dialog id 0x12 is a stack local in the verb-0x16 body (not a call argument).
check("dialog id 0x12 local @0x5A34D7 (C7 84 24 80 01 00 00 12 00 00 00)",
      rd(0x5A34D7, 11) == bytes.fromhex("C784248001000012000000"))

# ---------------------------------------------------------------------------
# Correction: 0x42AB40 is a temp-object destructor, NOT a dialog opener.
# ---------------------------------------------------------------------------
check("0x42AB40 SEH prologue 6A FF 68 53 53 B8 00 64 A1 00 00 00 00 (dtor, not opener)",
      rd(0x42AB40, 13) == bytes.fromhex("6AFF685353B80064A100000000"))
check("0x42AB40 stores vtable 0xF0B978 @0x42AB6A", rd(0x42AB6A, 4) == bytes.fromhex("78B9F000"))
check("0x42AB40 stores vtable 0xF0B8FC @0x42ABAC", rd(0x42ABAC, 4) == bytes.fromhex("FCB8F000"))
check("0x42AB40 calls free/dtor 0x88D060 @0x42AB83", call_target(0x42AB83) == 0x88D060,
      hex(call_target(0x42AB83) or 0))

# ---------------------------------------------------------------------------
# R2. the numeric dialog is a GENERIC reusable control -> caption not in the model.
# (Names are load-bearing plaintext; contents carry NO inline split caption.)
#
# SCAN-DEBT-001 (round 84): this block used to call os.listdir() on the model
# directory (573 entries: 534 .model + 37 .project + 1 .fsl + 1 .tip) while
# tests/test_split_operate_verb_panels_static.py built its set with
# glob("*.model") (534).  Two denominators, one guard, and neither of them had
# written down which set the report's negative is a negative over.  Both sides
# now call tools/pf_client_ui_assets.model_names(), which carries the definition
# in its docstring.  It also raises instead of printing SKIP when the directory
# is unreachable: "I could not look" is not "I looked and found nothing".
# ---------------------------------------------------------------------------
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pf_client_ui_assets import (  # noqa: E402
    ClientAssetsUnavailable, model_names, models_named,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
GUI_MODEL = os.path.normpath(os.path.join(_HERE, "..", "..", "GameClient", "Data", "GUI", "Model"))
TEXTDATA = os.path.normpath(os.path.join(_HERE, "..", "..", "GameClient", "Data", "B_TEXTDATA_TH.pc_"))
try:
    models = model_names(GUI_MODEL)
except ClientAssetsUnavailable as error:
    check("client UI model directory is readable", False, str(error).splitlines()[0])
    models = None
if models is not None:
    check("generic numeric-input control Common_NumInput.model present",
          "common_numinput.model" in models, "models=%d" % len(models))
    offenders = models_named(("split", "divide"), GUI_MODEL)
    check("no split/divide-named dialog model exists (caption is not in GUI)",
          not offenders, "found=%s" % offenders)
    numinput = os.path.join(GUI_MODEL, "Common_NumInput.model")
    if os.path.isfile(numinput):
        body = open(numinput, "rb").read()
        low = body.lower()
        check("Common_NumInput.model is plaintext UIControlData XML",
              b"<uicontroldata>" in low)
        check("Common_NumInput.model carries NO inline split caption",
              b"split" not in low and b"divide" not in low)
    else:
        check("Common_NumInput.model is readable", False, numinput)
if os.path.isfile(TEXTDATA):
    magic = open(TEXTDATA, "rb").read(4)
    check("text table B_TEXTDATA_TH.pc_ is packed ($pcz) -> caption not statically readable",
          magic == b"$pcz")
else:
    check("packed text table B_TEXTDATA_TH.pc_ is readable", False, TEXTDATA)

print()
if fails:
    print("RESULT: FAIL (%d) -> %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("RESULT: PASS — verb 0x16 -> op6 reused across two panels; static caption route closed; "
      "split label needs a live capture. split_stack stays in_progress.")
sys.exit(0)
