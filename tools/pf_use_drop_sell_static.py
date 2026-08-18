#!/usr/bin/env python3
"""PF USE-DROP-SELL-001 — static byte-exact characterization of how the client
produces USE / DROP / SELL, cross-checked against the read-only server, opening
the `inventory/use_drop_sell` lane from not_started -> in_progress.

Context: SPLIT-OPERATE-001/002/003 (chief rounds 68/69/70) pinned the
`ItemOperateVitalReq 0x4BED` operation space {1,3,4,5,6}, the three-field
serializer 0x5E5AF0 (+0x14 u8 tag 0x0B operation / +0x18 u32 tag 0x14 value32 /
+0x20 qword tag 0x32), the op6 quantity factory 0x59F870 with EXACTLY four call
sites, and the fact that the static caption route for the split label is closed
(packed assets). The `use_drop_sell` lane was still `not_started` with the note
"Tracked as separate later milestones."

This milestone answers, byte-exact from the read-only client binary:

  * WHERE op3 LIVES. The single op3 caller 0x5B9D0C sits in a tiny 0x3E-byte
    function [0x5B9CE0,0x5B9D1E) that is NEVER e8-called: its only image-wide
    dword reference is `push 0x5B9CE0` @0x5BA16C, i.e. it is registered as a
    MODAL-DIALOG CALLBACK (0x405D40 stores it into dialog+0x12CC). The callback
    fires op3 only when the dialog result `[arg1+0x94] == 1`, sourcing the item
    identity from the global qword pair 0x1080F40/0x1080F44 and clearing that
    pair unconditionally afterwards. The latch of that pair happens in the
    verb-`eax==2` body of inventory panel fn 0x5B9F70, which first opens a
    message box with template id 0x69 (`push 0x69` -> 0x5AB5F0).
    Net shape: op3 = single-target, identity-only, NO quantity, NO destination,
    NO counterparty, behind a modal confirm.

  * WHAT THE OTHER THREE op6 SITES ARE.
      - site A 0x57D1F4 lives in fn 0x57CF50 (SEH prologue) and is gated by
        `cmp dword [esi+0x94], 0x16` @0x57D0C0 (bytes 83 BE 94 00 00 00 16) —
        a THIRD verb-0x16 gate that 003's `83 F8 16` byte scan could not see
        because the operand is memory, not eax. Its body carries TWO distinct
        item handles and follows op6 with TWO op5 (equip) producers
        (0x57D220, 0x57D277): a quantity-parameterised equip/swap flow.
      - site B 0x58294D lives in fn 0x582730 (SEH prologue) and is NOT gated by
        a verb code at all: the discriminator is the context field `[ctx+8]`
        (`cmp ecx,1` @0x58284E vs `cmp ecx,2` @0x58292D); op6 is the mode-2 arm.
        The mode-1 arm is a keyboard-modifier path — it calls the
        GetAsyncKeyState wrapper 0x448EC0 with VK 0x10 (SHIFT) and VK 0x11
        (CTRL).
      - site D 0x5BA208 is the verb-0x16 arm of panel fn 0x5B9F70 (003's site D).
    NONE of the five ItemOperate-producing functions references a
    Stall / BlackMarket / Store / Sell / Buy / Shop / Vendor / Money / Price
    string: there is NO vendor, price or counterparty context at any op6 site.

  * USE AND SELL DO NOT RIDE ItemOperate — POSITIVE EVIDENCE.
      - `UseItemVital\0` @0xF30950 is its OWN registered request class: sole
        registration 0xBEE600, id-slot 0x1082030 written once / read once by
        get-id stub 0x5BEA50, vtable 0xF2D0B0 in the same 9-slot cohort shape as
        ItemOperateVitalReq's 0xF30374 (+0x08 = 0x401B20, +0x1C = 0x710440), and
        serializer 0x6C0180 emitting EXACTLY ONE field: tag 0x32 qword @+0x18.
        No operation byte, no value32 — a pure `use(item_identity)` request.
      - selling has its own subsystems: StallModule_Client / StallStartVital /
        StallOpenVital / StallOperateVital (player stall), the GSCN_BlackMarket*
        family (PutOnSale / OffSale / Buy / Search*), UpdateConditionalStoreItemVital
        (+ StoreEventHandler), and the ItemMall* family. StallOperateVital's
        serializer 0x76A630 carries u8(tag 0x08)@+0x14 + qword(tag 0x32)@+0x18 +
        a string @+0x24 + u32(tag 0x14)@+0x20 — a PRICED operate wire, structurally
        different from ItemOperate's three-field wire.
      - `PickupTerrainThing` @0xF3093C is likewise its own class.

  * SERVER GAP. current/pf_login_game_server_v141.py declares
    USE_ITEM_VITAL = 0x1F4F and lists it in NAMES, but has NO dispatch branch for
    it; its ItemOperate dispatch validates operation 4 and special-cases
    operation 5 only — no operation 3, no operation 6; there is no Stall /
    BlackMarket / store-sell id at all. src/pirateforce_foundation/runtime.py
    fails closed on any operation != 4
    (`item_move_generalized_wrong_operation_no_reply`).

  * INCIDENTAL CORRECTION (evidenced, does not disturb 001-003's structure).
    The `mov dword [esp+0x180], 0x12` @0x5A34D7 that 001/002 labelled
    "numeric-input dialog resource 0x12" is an MSVC EH TRYLEVEL store, not a
    dialog id. The same stack slot (anchored by the SEH prologue
    `push -1; push handler; push fs:[0]` + `lea eax,[esp+0x170]; mov fs:[0],eax`)
    receives 0xFFFFFFFF @0x5A3502 and 0x0A @0x5A335A/0x5A30C0 at the matching
    esp depths; panel fn 0x5B9F70 shows the same pattern (0 @0x5BA07B,
    2 @0x5BA1C5, 0xFFFFFFFF @0x5BA211). The verb-0x16 -> helper 0x5A1630 ->
    strict-positive 64-bit guard -> op6 chain that 001-003 proved is untouched;
    only the "dialog resource id" label is withdrawn. 003's R2 (static caption
    route closed) is strengthened: there is no dialog id to caption in the
    first place.

STILL NOT CLAIMED (bounded, same discipline as SPLIT-OPERATE-002):
  * op3 is NOT claimed to be "drop"/"discard"/"destroy". The evidence is
    structural (identity-only + modal confirm + no counterparty). The confirm
    caption lives in the packed text table (003 R2) and cannot be read.
  * op6 verbs are NOT claimed to be "split"/"drop-N"/"sell-N" individually.
  * "the client has no drop request at all" is NOT claimed — only that no
    registered class name in the 521-entry registration table spells drop/discard
    for an inventory item, and that op3/op6 are the only ItemOperate candidates.
  * no runtime claim of any kind. `use_drop_sell` moves not_started ->
    in_progress and never runtime_pass here.

Report-only / additive: NO server-source change, NO scenario, NO ledger entry, NO
runtime claim. Sole evidence = the read-only client binary
GameClient/GameClient.local.bin (disassembled) cross-checked against the read-only
server source.

Usage:  py -3 tools/pf_use_drop_sell_static.py [path-to-GameClient.local.bin]
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
"""
import os
import re
import struct
import sys
import hashlib

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    sys.exit("capstone required: pip install capstone")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))


def _default_bin():
    for cand in (
        "GameClient/GameClient.local.bin",
        os.path.join(_ROOT, "..", "GameClient", "GameClient.local.bin"),
        os.path.join(_ROOT, "GameClient", "GameClient.local.bin"),
    ):
        if os.path.isfile(cand):
            return cand
    return "GameClient/GameClient.local.bin"


BIN = sys.argv[1] if len(sys.argv) > 1 else _default_bin()
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
SERVER_SRC = os.path.normpath(os.path.join(_ROOT, "current", "pf_login_game_server_v141.py"))
FOUNDATION_RUNTIME = os.path.normpath(
    os.path.join(_ROOT, "src", "pirateforce_foundation", "runtime.py"))

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


def off2va(o):
    for n, vaddr, vsize, rawptr, rawsize in secs:
        if rawptr <= o < rawptr + rawsize:
            return image_base + vaddr + (o - rawptr), n
    return None, None


def rd(va, n):
    o = va2off(va); return data[o:o + n]


def span_sha(a, b):
    return hashlib.sha256(rd(a, b - a)).hexdigest().upper()


def dw(va):
    return struct.unpack('<I', rd(va, 4))[0]


TEXT = [s for s in secs if s[0] == '.text'][0]
_, TVADDR, TVSIZE, _, _ = TEXT
TSTART = image_base + TVADDR
TEND = TSTART + TVSIZE

md = Cs(CS_ARCH_X86, CS_MODE_32)

fails = []
guards = 0


def check(name, cond, detail=""):
    global guards
    guards += 1
    print(("[OK]   " if cond else "[FAIL] ") + name + ("  " + detail if detail else ""))
    if not cond:
        fails.append(name)


def dmap(va, size):
    return {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(va, size), va)}


def text_hits(pattern_hex):
    """Every .text VA where the byte pattern appears."""
    pat = bytes.fromhex(pattern_hex)
    lo = va2off(TSTART); hi = lo + TVSIZE
    res = []; s = lo
    while True:
        j = data.find(pat, s, hi)
        if j < 0:
            break
        res.append(image_base + TVADDR + (j - lo)); s = j + 1
    return res


def image_hits(val):
    """Every image offset holding dword `val`, as (VA, section)."""
    p = struct.pack('<I', val); res = []; s = 0
    while True:
        j = data.find(p, s)
        if j < 0:
            break
        va, sec = off2va(j)
        if va is not None:
            res.append((va, sec))
        s = j + 1
    return res


def call_target(va):
    o = va2off(va)
    if data[o] != 0xE8:
        return None
    rel = struct.unpack_from('<i', data, o + 1)[0]
    return (va + 5 + rel) & 0xffffffff


def callers_of(target):
    res = []
    lo = va2off(TSTART); hi = lo + TVSIZE
    for o in range(lo, hi - 5):
        if data[o] == 0xE8:
            rel = struct.unpack_from('<i', data, o + 1)[0]
            va = image_base + TVADDR + (o - lo)
            if ((va + 5 + rel) & 0xffffffff) == target:
                res.append(va)
    return res


def cstr(va, n=96):
    o = va2off(va)
    if o is None:
        return None
    b = data[o:o + n]
    k = 0
    while k < len(b) and 0x20 <= b[k] < 0x7f:
        k += 1
    if k >= 4 and k < len(b) and b[k] == 0:
        return b[:k].decode('latin1')
    return None


# ---------------------------------------------------------------------------
# Address map (all VAs, ImageBase 0x400000)
# ---------------------------------------------------------------------------
OP3_FACTORY, OP4_FACTORY, OP5_FACTORY, OP6_FACTORY = 0x59F780, 0x59F7C0, 0x59F800, 0x59F870
ITEM_OPERATE_ALLOC = 0x59F0D0
OP3_CALLSITE = 0x5B9D0C
OP3_CALLBACK = 0x5B9CE0            # [0x5B9CE0, 0x5B9D1E)
OP3_CALLBACK_END = 0x5B9D1E
LATCH_LO, LATCH_HI = 0x1080F40, 0x1080F44
DIALOG_CB_REGISTER = 0x405D40
MSGBOX_OPEN = 0x5AB5F0
GETASYNCKEYSTATE_WRAPPER = 0x448EC0
FN_A = (0x57CF50, 0x57D2BC)        # op6 site A 0x57D1F4
FN_B = (0x582730, 0x58298F)        # op6 site B 0x58294D
FN_C = (0x5A2A70, 0x5A40B0)        # op6 site C 0x5A3532 (002's dispatcher)
FN_D = (0x5B9F70, 0x5BABF7)        # op6 site D 0x5BA208 + the op3 confirm latch
OP6_SITES = [0x0057D1F4, 0x0058294D, 0x005A3532, 0x005BA208]

USEITEM_NAME = 0xF30950
USEITEM_REG = 0xBEE600
USEITEM_IDSLOT = 0x1082030
USEITEM_GETID = 0x5BEA50
USEITEM_VTABLE = 0xF2D0B0
USEITEM_SERIAL = 0x6C0180
ITEMOP_VTABLE = 0xF30374           # from SPLIT-OPERATE-001
STALLOP_VTABLE = 0xF4A418
STALLOP_SERIAL = 0x76A630
FIELD_CODEC_OUT, FIELD_CODEC_IN = 0x89A600, 0x89A640

SPANS = {
    "op3_factory":          (0x59F780, 0x59F7B7, "0601F7B4AB0A956031FDEA55AE7602A66BFBD731F41671C62F05F51396260767"),
    "op3_callback_fn":      (0x5B9CE0, 0x5B9D1E, "CF572F96F5FD25F49433138EEB664ABF5083A054574ABA9C919BC6E68739E2F7"),
    "op3_confirm_body":     (0x5BA0F1, 0x5BA17E, "816FF7AE8E868A9F3AF9C87955802E2A5DAFECD4146C2A1A5C820EC5054F3F80"),
    "paneld_verb2_gate":    (0x5BA03C, 0x5BA08B, "C6D331C0AB09240038B1854EAA1C18590532F9FC7472B6BC0F01128FB56ECBA6"),
    "siteA_verb16_body":    (0x57D0C0, 0x57D1F9, "29632E47475390E9A3C5586099DAC8512EB94C185E7D436D4EA1BE25FAAB3BE5"),
    "siteB_mode_gate":      (0x582844, 0x582952, "762A003F62500F0CFDC143C89F1204D5B751B63DA73062872811D20C2127B71F"),
    "siteA_fn_prologue":    (0x57CF50, 0x57CF7A, "B7A3CB5720C5FB70C1886CB5F29133630B43CC0649E20C239400E363BAE79805"),
    "siteB_fn_prologue":    (0x582730, 0x58276A, "68BB0A5494484A8644BF925F6B486367B6ECE8749F6DC784557CB652A2DFA734"),
    "paneld_fn_prologue":   (0x5B9F70, 0x5B9FAA, "ED679A6B8FF5A5A9E8A1E738A19381FA81970EEAD0382B52D7E5111BBE5DCFBF"),
    "useitem_registration": (0xBEE600, 0xBEE618, "29646D0D080B55ABCD43B45AF6BF37193EA6991F2ED060C8062FF6A46993FCFB"),
    "useitem_vtable":       (0xF2D0B0, 0xF2D0D4, "95C403FDA248197E65AFBB9908ED206F1B13E8B80B80E425AE7330001FFA0C9E"),
    "useitem_serializer":   (0x6C0180, 0x6C01A3, "C0910C6EA5EBD56E25C4D3C64C7BD97F939A01E97BAEF3F489057467AC943BCE"),
    "stallop_serializer":   (0x76A630, 0x76A738, "3D1138E71595E53FE4D81A781189D0B35C564C2EE562BD90C2114482E2DBD501"),
}

VENDOR_WORDS = re.compile(r"(stall|market|store|sell|buy|shop|vendor|auction|money|price)", re.I)


def referenced_strings(lo, hi):
    """Every plain-ASCII .rdata/.data string referenced by an immediate in [lo,hi)."""
    out = set()
    for ins in md.disasm(rd(lo, hi - lo), lo):
        for tok in re.findall(r"0x[0-9a-f]+", ins.op_str):
            v = int(tok, 16)
            if v > image_base:
                s = cstr(v)
                if s:
                    out.add(s)
    return out


def name_id(name):
    """The server's protocol_name_id: sum((i+1)*ord(c)) & 0xFFFF."""
    return sum((i + 1) * ord(c) for i, c in enumerate(name)) & 0xFFFF


print("PF USE-DROP-SELL-001 — inventory/use_drop_sell static characterization")
print("binary: %s" % BIN)
print()

check("binary SHA-256 matches the pinned client", sha == EXPECT_SHA, sha)

# ---------------------------------------------------------------------------
# 1. Regression anchors from SPLIT-OPERATE-001/002/003
# ---------------------------------------------------------------------------
alloc_callers = callers_of(ITEM_OPERATE_ALLOC)
check("ItemOperateVitalReq allocator 0x59F0D0 has exactly the six known producer "
      "sites (001 regression)",
      alloc_callers == [0x59F78C, 0x59F7CC, 0x59F83D, 0x59F87C, 0x5A25C3, 0x5EB05C],
      " ".join(hex(x) for x in alloc_callers))
c3 = callers_of(OP3_FACTORY)
check("op3 factory 0x59F780 has EXACTLY one caller 0x5B9D0C (002 regression)",
      c3 == [OP3_CALLSITE], " ".join(hex(x) for x in c3))
c4 = callers_of(OP4_FACTORY)
check("op4 factory 0x59F7C0 has EXACTLY one caller 0x5A3491 (002 regression)",
      c4 == [0x5A3491], " ".join(hex(x) for x in c4))
c6 = callers_of(OP6_FACTORY)
check("op6 factory 0x59F870 has EXACTLY four callers (002/003 regression)",
      c6 == OP6_SITES, " ".join(hex(x) for x in c6))
c5 = callers_of(OP5_FACTORY)
check("op5 factory 0x59F800 has EXACTLY five callers — three of them inside the "
      "op6 site-A function 0x57CF50",
      c5 == [0x57D0A7, 0x57D220, 0x57D277, 0x5A6884, 0x5A6F07],
      " ".join(hex(x) for x in c5))

# ---------------------------------------------------------------------------
# 2. op3 arg contract — identity only, no value32, stdcall ret 8
# ---------------------------------------------------------------------------
f3 = dmap(OP3_FACTORY, 0x40)
check("op3 factory writes operation immediate 6 -> `mov byte [eax+0x14], 3` "
      "(C6 40 14 03) @0x59F79E",
      rd(0x59F79E, 4) == bytes.fromhex("c6401403"))
check("op3 factory stores the two stack dwords into the qword field +0x20/+0x24 "
      "and NEVER touches value32 +0x18",
      rd(0x59F7A2, 3) == bytes.fromhex("894820")
      and rd(0x59F7A5, 3) == bytes.fromhex("895024")
      and not any(o.endswith("[eax + 0x18], ecx") or o.endswith("[eax + 0x18], edx")
                  for (m, o) in f3.values()))
check("op3 factory is stdcall ret 8 -> op3(identity_low, identity_high) only",
      rd(0x59F7B4, 3) == bytes([0xC2, 0x08, 0x00]))
a, b, h = SPANS["op3_factory"]
check("op3 factory span 0x59F780..0x59F7B7 byte-identical", span_sha(a, b) == h, span_sha(a, b))

# ---------------------------------------------------------------------------
# 3. op3 lives behind a modal confirm callback
# ---------------------------------------------------------------------------
check("op3 caller function is the 0x3E-byte block [0x5B9CE0,0x5B9D1E) "
      "(int3-padded on both sides)",
      rd(OP3_CALLBACK - 1, 1) == b"\xcc" and rd(OP3_CALLBACK_END - 1, 1) == b"\xc3"
      and rd(OP3_CALLBACK_END, 2) == b"\xcc\xcc")
check("op3 caller function has ZERO e8 callers (it is never called directly)",
      callers_of(OP3_CALLBACK) == [])
cb_refs = image_hits(OP3_CALLBACK)
check("the only image-wide dword reference to 0x5B9CE0 is `push 0x5B9CE0` @0x5BA16C "
      "-> it is registered as a dialog callback",
      cb_refs == [(0x5BA16D, ".text")] and rd(0x5BA16C, 5) == bytes.fromhex("68e09c5b00"),
      str([(hex(x), s) for x, s in cb_refs]))
check("callback registrar 0x405D40 stores its first argument into dialog+0x12CC",
      call_target(0x5BA179) == DIALOG_CB_REGISTER
      and dmap(0x405D40, 0x50).get(0x405D79) == ('mov', 'dword ptr [esi + 0x12cc], eax'))
check("op3 callback gates on the dialog result `cmp dword [eax+0x94], 1` @0x5B9CE4",
      rd(0x5B9CE4, 7) == bytes.fromhex("83b89400000001"))
check("op3 callback sources the identity qword from globals 0x1080F40 (low) / "
      "0x1080F44 (high)",
      rd(0x5B9CED, 5) == bytes.fromhex("a1400f0801")
      and rd(0x5B9CF2, 6) == bytes.fromhex("8b0d440f0801"))
check("op3 callback clears both identity globals unconditionally after the call",
      rd(0x5B9D13, 5) == bytes.fromhex("a3400f0801")
      and rd(0x5B9D18, 5) == bytes.fromhex("a3440f0801"))
lo_refs = [hex(v) for v, s in image_hits(LATCH_LO)]
hi_refs = [hex(v) for v, s in image_hits(LATCH_HI)]
check("identity-latch global 0x1080F40 has exactly 4 references "
      "(panel init clear / verb-2 latch / callback read / callback clear)",
      lo_refs == ['0x5b9cee', '0x5b9d14', '0x5b9da1', '0x5ba116'], str(lo_refs))
check("identity-latch global 0x1080F44 has exactly 4 references (same four sites)",
      hi_refs == ['0x5b9cf4', '0x5b9d19', '0x5b9dab', '0x5ba107'], str(hi_refs))
a, b, h = SPANS["op3_callback_fn"]
check("op3 callback span 0x5B9CE0..0x5B9D1E byte-identical", span_sha(a, b) == h, span_sha(a, b))

# ---------------------------------------------------------------------------
# 4. The op3 confirm path inside panel fn 0x5B9F70, verb eax==2
# ---------------------------------------------------------------------------
check("panel fn 0x5B9F70 has the SEH prologue `push -1; push 0xB9CDCA; push fs:[0]`",
      rd(FN_D[0], 13) == bytes.fromhex("6aff68cacdb90064a100000000"))
check("panel fn 0x5B9F70 loads the verb from record+0x94 @0x5B9FE0",
      rd(0x5B9FE0, 6) == bytes.fromhex("8b8094000000"))
check("panel fn 0x5B9F70 verb ladder: cmp eax,1 @0x5B9FE6 / cmp eax,2 @0x5BA03C / "
      "cmp eax,0x16 @0x5BA183",
      rd(0x5B9FE6, 3) == bytes.fromhex("83f801")
      and rd(0x5BA03C, 3) == bytes.fromhex("83f802")
      and rd(0x5BA183, 3) == bytes.fromhex("83f816"))
check("verb-2 body latches the selected item identity into 0x1080F44 @0x5BA105 and "
      "0x1080F40 @0x5BA115",
      rd(0x5BA105, 6) == bytes.fromhex("890d440f0801")
      and rd(0x5BA115, 5) == bytes.fromhex("a3400f0801"))
check("verb-2 body then opens a message box with template id 0x69 "
      "(`push 0x69` @0x5BA13B -> call 0x5AB5F0)",
      rd(0x5BA13B, 2) == bytes([0x6A, 0x69]) and call_target(0x5BA13D) == MSGBOX_OPEN)
check("panel fn 0x5B9F70 initialises the identity globals to 0 at 0x5B9D9F/0x5B9DA9 "
      "(panel-scoped latch, not a persistent selection)",
      rd(0x5B9D9F, 10) == bytes.fromhex("c705400f080100000000")
      and rd(0x5B9DA9, 10) == bytes.fromhex("c705440f080100000000"))
for key in ("op3_confirm_body", "paneld_verb2_gate", "paneld_fn_prologue"):
    a, b, h = SPANS[key]
    check("span %s 0x%X..0x%X byte-identical" % (key, a, b), span_sha(a, b) == h, span_sha(a, b))

# ---------------------------------------------------------------------------
# 5. op6 site A — third verb-0x16 gate, two handles, op6 then two op5
# ---------------------------------------------------------------------------
check("site A function 0x57CF50 has the SEH prologue `push -1; push 0xB98D68; push fs:[0]`",
      rd(FN_A[0], 13) == bytes.fromhex("6aff68688db90064a100000000"))
check("site A op6 call 0x57D1F4 is inside fn [0x57CF50,0x57D2BC)",
      FN_A[0] <= 0x57D1F4 < FN_A[1] and rd(FN_A[1] - 3, 3) == bytes([0xC2, 0x08, 0x00]))
check("site A is gated by a THIRD verb-0x16 test — `cmp dword [esi+0x94], 0x16` "
      "@0x57D0C0 (83 BE 94 00 00 00 16), invisible to 003's `83 F8 16` scan",
      rd(0x57D0C0, 7) == bytes.fromhex("83be9400000016"))
siteA = dmap(0x57D0C0, 0x57D2A0 - 0x57D0C0)
check("site A body carries TWO distinct item handles (edi+0x94 saved @0x57D179, "
      "esi+0x94 -> op6 arg3 @0x57D173)",
      siteA.get(0x57D16D) == ('mov', 'eax, dword ptr [edi + 0x94]')
      and siteA.get(0x57D173) == ('mov', 'esi, dword ptr [esi + 0x94]')
      and siteA.get(0x57D179) == ('mov', 'dword ptr [esp + 0x14], eax'))
check("site A follows op6 with TWO op5 (equip) producers @0x57D220 and @0x57D277 "
      "-> quantity-parameterised equip/swap, not a bare quantity op",
      call_target(0x57D220) == OP5_FACTORY and call_target(0x57D277) == OP5_FACTORY)
a, b, h = SPANS["siteA_verb16_body"]
check("site A verb-0x16 body span 0x57D0C0..0x57D1F9 byte-identical",
      span_sha(a, b) == h, span_sha(a, b))
a, b, h = SPANS["siteA_fn_prologue"]
check("site A prologue span byte-identical", span_sha(a, b) == h, span_sha(a, b))

# ---------------------------------------------------------------------------
# 6. op6 site B — context-mode gate, not a verb code; SHIFT/CTRL sibling arm
# ---------------------------------------------------------------------------
check("site B function 0x582730 has the SEH prologue `push -1; push 0xB990E3; push fs:[0]`",
      rd(FN_B[0], 13) == bytes.fromhex("6aff68e390b90064a100000000"))
check("site B op6 call 0x58294D is inside fn [0x582730,0x58298F)",
      FN_B[0] <= 0x58294D < FN_B[1] and rd(FN_B[1] - 3, 3) == bytes([0xC2, 0x08, 0x00]))
siteB = dmap(0x582844, 0x582952 - 0x582844)
check("site B discriminates on the context field [ctx+8], NOT on a verb code "
      "(mov ecx,[ecx+8] @0x58284B; cmp ecx,1 @0x58284E; cmp ecx,2 @0x58292D)",
      siteB.get(0x58284B) == ('mov', 'ecx, dword ptr [ecx + 8]')
      and rd(0x58284E, 3) == bytes.fromhex("83f901")
      and rd(0x58292D, 3) == bytes.fromhex("83f902"))
check("site B: NO `cmp eax,0x16` (83 F8 16) anywhere in fn [0x582730,0x58298F)",
      all(not (FN_B[0] <= v < FN_B[1]) for v in text_hits("83f816")))
check("site B mode-1 arm is a keyboard-modifier path: 0x448EC0(0x10=VK_SHIFT) "
      "@0x582857 and 0x448EC0(0x11=VK_CONTROL) @0x5828EE",
      rd(0x582857, 2) == bytes([0x6A, 0x10]) and call_target(0x582859) == GETASYNCKEYSTATE_WRAPPER
      and rd(0x5828EE, 2) == bytes([0x6A, 0x11]) and call_target(0x5828F0) == GETASYNCKEYSTATE_WRAPPER)
check("0x448EC0 is `GetAsyncKeyState(vk) & 0x8000` (import thunk 0xC3B990)",
      rd(GETASYNCKEYSTATE_WRAPPER, 10) == bytes.fromhex("8b44240450ff1590b9c300"[:20])
      and dmap(GETASYNCKEYSTATE_WRAPPER, 0x20).get(0x448ECB) == ('mov', 'ecx, 0x8000'))
a, b, h = SPANS["siteB_mode_gate"]
check("site B mode-gate span 0x582844..0x582952 byte-identical", span_sha(a, b) == h, span_sha(a, b))
a, b, h = SPANS["siteB_fn_prologue"]
check("site B prologue span byte-identical", span_sha(a, b) == h, span_sha(a, b))

# ---------------------------------------------------------------------------
# 7. No vendor / price / counterparty context at ANY ItemOperate producer
# ---------------------------------------------------------------------------
for label, (lo, hi) in (("A 0x57CF50", FN_A), ("B 0x582730", FN_B),
                        ("C 0x5A2A70", FN_C), ("D 0x5B9F70", FN_D),
                        ("op3-callback 0x5B9CE0", (OP3_CALLBACK, OP3_CALLBACK_END))):
    ss = referenced_strings(lo, hi)
    bad = sorted(s for s in ss if VENDOR_WORDS.search(s))
    check("fn %s references NO stall/market/store/sell/buy/shop/vendor/money/price string"
          % label, bad == [], str(bad))
ss_c = referenced_strings(*FN_C)
check("the only module strings in the two verb-ladder panels are Equipment / Trade / "
      "Storage / Guild / PopItem / ItemMall / GetBack (no shop path)",
      {'CGCGuildModule', 'EquipmentModule', 'GetBack', 'ItemMallModule_Client',
       'PopItem', 'StorageModule_Client', 'TradeModule_Client'} == ss_c, str(sorted(ss_c)))

# ---------------------------------------------------------------------------
# 8. USE rides its own request class — UseItemVital
# ---------------------------------------------------------------------------
check("class name string 'UseItemVital\\0' @0xF30950",
      rd(USEITEM_NAME, 13) == b"UseItemVital\x00")
check("sole UseItemVital registration @0xBEE600 pushes the name and stores id-slot 0x1082030",
      rd(USEITEM_REG, 24).hex() == "685009f300e876dacaff8bc8e8efd6caff66a330200801c3"
      and text_hits("68" + struct.pack('<I', USEITEM_NAME).hex()) == [USEITEM_REG])
w = text_hits("66a3" + struct.pack('<I', USEITEM_IDSLOT).hex())
r = text_hits("66a1" + struct.pack('<I', USEITEM_IDSLOT).hex())
check("UseItemVital id-slot 0x1082030 written by exactly one site and read by exactly "
      "one get-id stub 0x5BEA50 (runtime-assigned id wall, same cohort)",
      w == [0xBEE611] and r == [USEITEM_GETID]
      and rd(USEITEM_GETID, 7) == bytes.fromhex("66a130200801c3"),
      str([hex(x) for x in w]) + " / " + str([hex(x) for x in r]))
check("UseItemVital vtable 0xF2D0B0 has the ItemOperateVitalReq cohort shape: "
      "+0x08 = 0x401B20, +0x10 = get-id 0x5BEA50, +0x18 = serializer 0x6C0180, +0x1C = 0x710440",
      dw(USEITEM_VTABLE + 0x08) == 0x401B20 and dw(USEITEM_VTABLE + 0x10) == USEITEM_GETID
      and dw(USEITEM_VTABLE + 0x18) == USEITEM_SERIAL and dw(USEITEM_VTABLE + 0x1C) == 0x710440)
check("the reference cohort ItemOperateVitalReq vtable 0xF30374 has the identical shape "
      "(+0x08 0x401B20, +0x18 serializer 0x5E5AF0, +0x1C 0x710440)",
      dw(ITEMOP_VTABLE + 0x08) == 0x401B20 and dw(ITEMOP_VTABLE + 0x18) == 0x5E5AF0
      and dw(ITEMOP_VTABLE + 0x1C) == 0x710440)
us = dmap(USEITEM_SERIAL, 0x24)
check("UseItemVital serializer 0x6C0180 emits EXACTLY ONE field: qword tag 0x32 @obj+0x18 "
      "(no operation byte, no value32) and is stdcall ret 8",
      us.get(0x6C0180) == ('add', 'ecx, 0x18')
      and rd(0x6C0188, 2) == bytes([0x6A, 0x08])
      and rd(0x6C018F, 2) == bytes([0x6A, 0x32])
      and call_target(0x6C0193) == FIELD_CODEC_OUT
      and call_target(0x6C019B) == FIELD_CODEC_IN
      and rd(0x6C0198, 3) == bytes([0xC2, 0x08, 0x00])
      and rd(0x6C01A0, 3) == bytes([0xC2, 0x08, 0x00]))
check("UseItemVital objects are 0x20 bytes, built by the generic class factory "
      "(vtable store 0xF2D0B0 @0x5BFEAB and @0x5EE649, alloc size 0x20 @0x5EE626)",
      rd(0x5BFEAB, 6) == bytes.fromhex("c700b0d0f200")
      and rd(0x5EE649, 6) == bytes.fromhex("c700b0d0f200")
      and rd(0x5EE626, 2) == bytes([0x6A, 0x20]))
check("the ItemOperate producer path never constructs a UseItemVital: no reference to "
      "vtable 0xF2D0B0 inside any of the five producer functions",
      all(not (lo <= v < hi) for v, s in image_hits(USEITEM_VTABLE)
          for lo, hi in (FN_A, FN_B, FN_C, FN_D, (OP3_CALLBACK, OP3_CALLBACK_END))))
for key in ("useitem_registration", "useitem_vtable", "useitem_serializer"):
    a, b, h = SPANS[key]
    check("span %s 0x%X..0x%X byte-identical" % (key, a, b), span_sha(a, b) == h, span_sha(a, b))

# ---------------------------------------------------------------------------
# 9. SELL rides its own subsystems — Stall / BlackMarket / Store / ItemMall
# ---------------------------------------------------------------------------
CLASS_REGISTRY = 0x89C080
for nm, va, reg in (("StallModule_Client", 0xF4A404, 0xC0E3D5),
                    ("StallStartVital", 0xF4A4C8, 0xC0E5B5),
                    ("StallOpenVital", 0xF4A4D8, 0xC0E5D5),
                    ("StallOperateVital", 0xF4A4E8, 0xC0E5F5),
                    ("GSCN_BlackMarketPutOnSale", 0xF3E89C, 0xC00765),
                    ("GSCN_BlackMarketOffSale", 0xF3E8B8, 0xC00785),
                    ("GSCN_BlackMarketBuy", 0xF3E8D0, 0xC007A5),
                    ("UpdateConditionalStoreItemVital", 0xF0B328, 0xBF8895),
                    ("PickupTerrainThing", 0xF3093C, 0xBEE5E5)):
    check("dedicated request class '%s' is its own registered class "
          "(push name @0x%X -> registry 0x89C080)" % (nm, reg - 5),
          cstr(va) == nm and rd(reg - 5, 5) == b"\x68" + struct.pack('<I', va)
          and call_target(reg) == CLASS_REGISTRY,
          repr(cstr(va)))
check("StallOperateVital vtable 0xF4A418 is the same cohort (+0x08 0x401B20, "
      "+0x18 serializer 0x76A630)",
      dw(STALLOP_VTABLE + 0x08) == 0x401B20 and dw(STALLOP_VTABLE + 0x18) == STALLOP_SERIAL)
ss = dmap(STALLOP_SERIAL, 0x60)
check("StallOperateVital serializer 0x76A630 is a PRICED operate wire: u8 tag 0x08 @+0x14 "
      "+ qword tag 0x32 @+0x18 + string @+0x24 + u32 tag 0x14 @+0x20 + u8 tag 0x0B presence "
      "— structurally different from ItemOperate's three-field wire",
      ss.get(0x76A63F) == ('lea', 'eax, [esi + 0x14]') and rd(0x76A645, 2) == bytes([0x6A, 0x08])
      and ss.get(0x76A652) == ('lea', 'ecx, [esi + 0x18]') and rd(0x76A656, 2) == bytes([0x6A, 0x32])
      and ss.get(0x76A65F) == ('lea', 'edx, [esi + 0x24]') and call_target(0x76A665) == 0x89A810
      and ss.get(0x76A66C) == ('lea', 'eax, [esi + 0x20]') and rd(0x76A670, 2) == bytes([0x6A, 0x14])
      and rd(0x76A68B, 2) == bytes([0x6A, 0x0B]))
a, b, h = SPANS["stallop_serializer"]
check("StallOperateVital serializer span byte-identical", span_sha(a, b) == h, span_sha(a, b))
check("no ItemOperate producer callsite lies inside the Stall/BlackMarket serializer band "
      "0x6C0000..0x790000 (the sell wires are a disjoint code region)",
      all(not (0x6C0000 <= s < 0x790000)
          for s in [OP3_CALLSITE, 0x5A3491] + OP6_SITES + c5))

# ---------------------------------------------------------------------------
# 10. Incidental correction — the `0x12` at 0x5A34D7 is an EH trylevel, not a dialog id
# ---------------------------------------------------------------------------
check("dispatcher 0x5A2A70 EHRec anchor: SEH prologue + `lea eax,[esp+0x170]; mov fs:[0],eax` "
      "-> the trylevel slot sits 8 bytes above the EHRec",
      rd(0x5A2A76, 2) == bytes([0x6A, 0xFF])
      and rd(0x5A2AA3, 7) == bytes.fromhex("8d842470010000")
      and rd(0x5A2AAA, 6) == bytes.fromhex("64a300000000"))
check("that ONE slot receives 0x12 @0x5A34D7 (esp depth -0x180) AND 0xFFFFFFFF @0x5A3502 "
      "AND 0x0A @0x5A335A/@0x5A30C0 -> 0x12 is an MSVC EH trylevel, not a dialog resource id",
      rd(0x5A34D7, 11) == bytes.fromhex("c784248001000012000000")
      and rd(0x5A3502, 11) == bytes.fromhex("c7842478010000ffffffff")
      and rd(0x5A335A, 8) == bytes.fromhex("c68424780100000a")
      and rd(0x5A30C0, 11) == bytes.fromhex("c78424800100000a000000"))
check("panel fn 0x5B9F70 shows the same trylevel pattern (0 @0x5BA07B, 2 @0x5BA1C5, "
      "0xFFFFFFFF @0x5BA211) with EHRec anchor `lea eax,[esp+0x128]`",
      rd(0x5B9F9D, 7) == bytes.fromhex("8d842428010000")
      and rd(0x5BA07B, 11) == bytes.fromhex("c784243801000000000000")
      and rd(0x5BA1C5, 11) == bytes.fromhex("c784243801000002000000")
      and rd(0x5BA211, 11) == bytes.fromhex("c7842430010000ffffffff"))
check("the structural chain 001-003 proved is untouched: verb-0x16 gate 0x5A349B -> "
      "helper 0x5A1630 @0x5A34E2 -> strict-positive 64-bit guard @0x5A34EF -> op6 @0x5A3532",
      rd(0x5A349B, 3) == bytes.fromhex("83f816")
      and call_target(0x5A34E2) == 0x5A1630
      and rd(0x5A34EF, 4) == bytes.fromhex("83782c00")
      and call_target(0x5A3532) == OP6_FACTORY)

# ---------------------------------------------------------------------------
# 11. Server cross-check — read-only
# ---------------------------------------------------------------------------
src = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
flat = src.replace(" ", "")
check("server declares USE_ITEM_VITAL = 0x1F4F and lists it in NAMES",
      "USE_ITEM_VITAL = 0x1F4F" in src and 'USE_ITEM_VITAL: "UseItemVital"' in src)
check("the server's own name hash reproduces both ids from the client class names",
      name_id("UseItemVital") == 0x1F4F and name_id("ItemOperateVitalReq") == 0x4BED,
      "0x%04X / 0x%04X" % (name_id("UseItemVital"), name_id("ItemOperateVitalReq")))
check("USE_ITEM_VITAL appears ONLY as a constant, a NAMES entry and a self-test assert — "
      "there is NO dispatch branch for it",
      src.count("USE_ITEM_VITAL") == 3
      and "nested_id==USE_ITEM_VITAL" not in flat
      and "nested_id == USE_ITEM_VITAL" not in src,
      "occurrences=%d" % src.count("USE_ITEM_VITAL"))
check("server ItemOperate handling covers operation 4 and operation 5 only",
      "V123_EQUIP_FROM_BAG_OPERATION = 5" in src
      and "operation==4" in flat
      and "def make_item_operate_move_delta_success" in src)
check("server has NO operation-3 and NO operation-6 handler",
      "operation==3" not in flat and "operation==6" not in flat
      and "operation!=3" not in flat and "operation!=6" not in flat)
check("server knows no stall / black-market class at all (no id, no NAMES entry, no builder)",
      "StallOperateVital" not in src and "BlackMarket" not in src and "STALL_" not in src)
srv_defs = re.findall(r"^\s*def (\w+)", src, re.M)
check("no server function is named for a sell / stall / market / vendor path",
      [d for d in srv_defs
       if re.search(r"(sell|stall|market|vendor|discard|destroy_item|drop_item|use_item)", d, re.I)] == [],
      "defs=%d" % len(srv_defs))
check("the NPC-store transport the server DOES implement is TradeCmdVital 0x23B5 / "
      "TradeZoomVital 0x2A7A / TradeItemResultVital 0x557B — a different wire from "
      "ItemOperate, and it accepts exactly one command value (cart-add = 6)",
      "TRADE_CMD_VITAL = 0x23B5" in src and "TRADE_ZOOM_VITAL = 0x2A7A" in src
      and "TRADE_ITEM_RESULT_VITAL = 0x557B" in src
      and "V118_TRADE_CART_ADD_COMMAND = 6" in src
      and "def make_trade_item_result_store_buy_cart_ack" in src)
check("that store path is buy-only: the only accepted TradeCmd command is the cart-add, "
      "there is no sell branch",
      flat.count("trade['field_u8']==V118_TRADE_CART_ADD_COMMAND") == 1
      and "cart_add_valid" in src and "cart_sell" not in src and "sell_valid" not in src)
found = open(FOUNDATION_RUNTIME, "r", encoding="utf-8", errors="replace").read()
check("foundation runtime fails closed on any operation != 4 "
      "(`item_move_generalized_wrong_operation_no_reply`)",
      "if operation != ITEM_MOVE_CAPTURE_FIELDS[0]:" in found
      and "item_move_generalized_wrong_operation_no_reply" in found)

print()
print("guards checked: %d" % guards)
if fails:
    print("RESULT: %d guard(s) drifted: %s" % (len(fails), fails))
    sys.exit(1)
print("RESULT: all inventory/use_drop_sell static guards reproduced (exit 0)")
sys.exit(0)
