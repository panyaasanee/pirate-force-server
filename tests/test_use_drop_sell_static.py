"""PF USE-DROP-SELL-001 — static byte-exact characterization of how the client
produces USE / DROP / SELL, opening `inventory/use_drop_sell` from not_started ->
in_progress.

Independent reproduction of the findings in
reports/PF_USE_DROP_SELL001_ITEM_OPERATE_USE_DROP_SELL_STATIC_20260818.md. This
module deliberately does NOT import tools/pf_use_drop_sell_static.py (that file is
an exiting script); every address, byte pattern and span hash below is recomputed
here from the read-only client binary with pefile + capstone.

  * op3 (`ItemOperateVitalReq` operation 3) is reached from exactly one call site
    0x5B9D0C, inside a 0x3E-byte function [0x5B9CE0,0x5B9D1E) that is never
    e8-called: its only image-wide dword reference is `push 0x5B9CE0` @0x5BA16C,
    i.e. it is a MODAL-DIALOG CALLBACK (registrar 0x405D40 stores it into
    dialog+0x12CC). It fires op3 only when the dialog result `[arg1+0x94] == 1`,
    reads the item identity from the global qword pair 0x1080F40/0x1080F44 and
    clears that pair unconditionally. The pair is latched in the verb-`eax==2`
    body of inventory panel fn 0x5B9F70, right before a message box with template
    id 0x69 is opened. op3 carries identity only — no quantity, no destination,
    no counterparty.

  * the other three op6 sites: site A 0x57D1F4 (fn 0x57CF50) is a THIRD verb-0x16
    gate expressed as `cmp dword [esi+0x94], 0x16`, carries two distinct item
    handles and is followed by two op5 (equip) producers; site B 0x58294D
    (fn 0x582730) is gated by the context field `[ctx+8]` (mode 2), not by a verb
    code, and its sibling mode-1 arm is a GetAsyncKeyState SHIFT/CTRL path; site D
    0x5BA208 is the verb-0x16 arm of fn 0x5B9F70.

  * none of the five ItemOperate-producing functions references any
    stall/market/store/sell/buy/shop/vendor/money/price string: there is no
    vendor, price or counterparty context at any op6 site.

  * USE and SELL ride other transports. `UseItemVital` @0xF30950 is its own
    registered class (registration 0xBEE600, id-slot 0x1082030, get-id 0x5BEA50,
    vtable 0xF2D0B0 in the ItemOperate cohort shape) whose serializer 0x6C0180
    emits EXACTLY ONE field: qword tag 0x32 @+0x18. Selling has StallModule_Client
    / StallStartVital / StallOpenVital / StallOperateVital, the GSCN_BlackMarket*
    family and UpdateConditionalStoreItemVital; StallOperateVital's serializer
    0x76A630 is a PRICED wire (u8 tag 0x08 @+0x14, qword tag 0x32 @+0x18, string
    @+0x24, u32 tag 0x14 @+0x20).

  * server: USE_ITEM_VITAL = 0x1F4F is declared and named but never dispatched;
    ItemOperate handling covers operation 4 and 5 only; no stall / black-market
    id exists; the NPC-store path that IS implemented rides TradeCmdVital 0x23B5
    and accepts only the cart-add (buy) command.

  * incidental correction: the `mov dword [esp+0x180], 0x12` @0x5A34D7 that
    001/002 labelled "numeric-input dialog resource 0x12" is an MSVC EH trylevel
    store. The same slot receives 0xFFFFFFFF @0x5A3502 and 0x0A @0x5A335A. The
    verb-0x16 -> 0x5A1630 -> strict-positive guard -> op6 chain is untouched.

Report-only / additive: no server behavior is changed by this milestone. The lane
moves not_started -> in_progress and never runtime_pass here.
"""
from __future__ import annotations

import hashlib
import re
import struct
import unittest
from pathlib import Path

import capstone

try:  # pragma: no cover - environment shim
    import pytest
except ImportError:  # pragma: no cover
    pytest = None

import pefile

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT.parent / "GameClient" / "GameClient.local.bin"
BINARY_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
SERVER = ROOT / "current" / "pf_login_game_server_v141.py"
FOUNDATION_RUNTIME = ROOT / "src" / "pirateforce_foundation" / "runtime.py"

if not BINARY.is_file():  # pragma: no cover - packaging layout without the binary
    _reason = f"client binary not reachable: {BINARY}"
    if pytest is not None:
        pytest.skip(_reason, allow_module_level=True)
    raise unittest.SkipTest(_reason)

# --- ItemOperate producer map (SPLIT-OPERATE-001/002/003 anchors) -------------
ITEM_OPERATE_ALLOC = 0x59F0D0
ALLOC_SITES = [0x59F78C, 0x59F7CC, 0x59F83D, 0x59F87C, 0x5A25C3, 0x5EB05C]
OP3_FACTORY, OP4_FACTORY, OP5_FACTORY, OP6_FACTORY = 0x59F780, 0x59F7C0, 0x59F800, 0x59F870
OP3_SITES = [0x5B9D0C]
OP4_SITES = [0x5A3491]
OP5_SITES = [0x57D0A7, 0x57D220, 0x57D277, 0x5A6884, 0x5A6F07]
OP6_SITES = [0x57D1F4, 0x58294D, 0x5A3532, 0x5BA208]

# --- op3 confirm-callback path ------------------------------------------------
OP3_CALLBACK = 0x5B9CE0
OP3_CALLBACK_END = 0x5B9D1E
OP3_CALLBACK_PUSH = 0x5BA16C
DIALOG_CB_REGISTER = 0x405D40
MSGBOX_OPEN = 0x5AB5F0
MSGBOX_TEMPLATE = 0x69
LATCH_LO, LATCH_HI = 0x1080F40, 0x1080F44

# --- the four op6-bearing functions ------------------------------------------
FN_A = (0x57CF50, 0x57D2BC)
FN_B = (0x582730, 0x58298F)
FN_C = (0x5A2A70, 0x5A40B0)
FN_D = (0x5B9F70, 0x5BABF7)
GETASYNCKEYSTATE_WRAPPER = 0x448EC0

# --- other transports ---------------------------------------------------------
CLASS_REGISTRY = 0x89C080
USEITEM_NAME = 0xF30950
USEITEM_REG_CALL = 0xBEE605
USEITEM_IDSLOT = 0x1082030
USEITEM_GETID = 0x5BEA50
USEITEM_VTABLE = 0xF2D0B0
USEITEM_SERIAL = 0x6C0180
ITEMOP_VTABLE = 0xF30374
ITEMOP_SERIAL = 0x5E5AF0
STALLOP_VTABLE = 0xF4A418
STALLOP_SERIAL = 0x76A630
FIELD_CODEC_OUT, FIELD_CODEC_IN = 0x89A600, 0x89A640

OTHER_TRANSPORT_CLASSES = (
    ("StallModule_Client", 0xF4A404, 0xC0E3D5),
    ("StallStartVital", 0xF4A4C8, 0xC0E5B5),
    ("StallOpenVital", 0xF4A4D8, 0xC0E5D5),
    ("StallOperateVital", 0xF4A4E8, 0xC0E5F5),
    ("GSCN_BlackMarketPutOnSale", 0xF3E89C, 0xC00765),
    ("GSCN_BlackMarketOffSale", 0xF3E8B8, 0xC00785),
    ("GSCN_BlackMarketBuy", 0xF3E8D0, 0xC007A5),
    ("UpdateConditionalStoreItemVital", 0xF0B328, 0xBF8895),
    ("PickupTerrainThing", 0xF3093C, 0xBEE5E5),
)

# (start, end, sha256) byte-span pins — instruction-aligned, byte-identical.
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


def _read_va(pe: pefile.PE, start: int, end: int) -> bytes:
    return pe.get_data(start - pe.OPTIONAL_HEADER.ImageBase, end - start)


def _instructions(pe: pefile.PE, start: int, end: int):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return {i.address: (i.mnemonic, i.op_str) for i in md.disasm(_read_va(pe, start, end), start)}


def _dword(pe: pefile.PE, va: int) -> int:
    return struct.unpack("<I", _read_va(pe, va, va + 4))[0]


def _text_section(pe: pefile.PE):
    base = pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        if s.Name.rstrip(b"\x00") == b".text":
            return base + s.VirtualAddress, pe.get_data(s.VirtualAddress, s.Misc_VirtualSize)
    raise AssertionError(".text not found")


def _pattern_sites(pe: pefile.PE, pattern_hex: str) -> list[int]:
    start, blob = _text_section(pe)
    pat = bytes.fromhex(pattern_hex)
    res, i = [], blob.find(pat)
    while i >= 0:
        res.append(start + i)
        i = blob.find(pat, i + 1)
    return res


def _callers_of(pe: pefile.PE, target: int) -> list[int]:
    """Every .text e8 rel32 call whose destination is `target`."""
    start, blob = _text_section(pe)
    res = []
    for off in range(len(blob) - 5):
        if blob[off] == 0xE8:
            rel = struct.unpack_from("<i", blob, off + 1)[0]
            va = start + off
            if ((va + 5 + rel) & 0xFFFFFFFF) == target:
                res.append(va)
    return res


def _call_target(pe: pefile.PE, va: int) -> int | None:
    raw = _read_va(pe, va, va + 5)
    if raw[0] != 0xE8:
        return None
    return (va + 5 + struct.unpack("<i", raw[1:])[0]) & 0xFFFFFFFF


def _image_refs(pe: pefile.PE, value: int) -> list[tuple[int, str]]:
    """Every image-wide dword occurrence of `value`, as (VA, section name)."""
    base = pe.OPTIONAL_HEADER.ImageBase
    packed = struct.pack("<I", value)
    out = []
    for s in pe.sections:
        blob = s.get_data()
        i = blob.find(packed)
        while i >= 0:
            out.append((base + s.VirtualAddress + i, s.Name.rstrip(b"\x00").decode("latin1")))
            i = blob.find(packed, i + 1)
    return sorted(out)


def _cstr(pe: pefile.PE, va: int, limit: int = 96) -> str | None:
    try:
        b = _read_va(pe, va, va + limit)
    except Exception:
        return None
    n = 0
    while n < len(b) and 0x20 <= b[n] < 0x7F:
        n += 1
    if n >= 4 and n < len(b) and b[n] == 0:
        return b[:n].decode("latin1")
    return None


def _referenced_strings(pe: pefile.PE, lo: int, hi: int) -> set[str]:
    base = pe.OPTIONAL_HEADER.ImageBase
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    out = set()
    for ins in md.disasm(_read_va(pe, lo, hi), lo):
        for tok in re.findall(r"0x[0-9a-f]+", ins.op_str):
            v = int(tok, 16)
            if v > base:
                s = _cstr(pe, v)
                if s:
                    out.add(s)
    return out


def _name_id(name: str) -> int:
    """The server's protocol_name_id, recomputed here (pure python)."""
    return sum((i + 1) * ord(c) for i, c in enumerate(name)) & 0xFFFF


def _use_item_wire(item_identity: int) -> bytes:
    """UseItemVital wire per the client serializer 0x6C0180: one tag-0x32 qword."""
    return bytes([0x32]) + struct.pack("<Q", item_identity & 0xFFFFFFFFFFFFFFFF)


def _item_operate_wire(operation: int, value32: int, qword: int) -> bytes:
    """ItemOperateVitalReq wire per the client serializer 0x5E5AF0 (SPLIT-OPERATE-001)."""
    return (bytes([0x0B, operation & 0xFF])
            + bytes([0x14]) + struct.pack("<I", value32 & 0xFFFFFFFF)
            + bytes([0x32]) + struct.pack("<Q", qword & 0xFFFFFFFFFFFFFFFF))


class UseDropSellStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pe = pefile.PE(str(BINARY), fast_load=True)

    # -- 1 ------------------------------------------------------------------
    def test_binary_hash_is_the_pinned_client(self):
        self.assertEqual(hashlib.sha256(BINARY.read_bytes()).hexdigest().upper(), BINARY_SHA)

    # -- 2 ------------------------------------------------------------------
    def test_spans_are_byte_identical(self):
        for label, (start, end, expected) in SPANS.items():
            blob = _read_va(self.pe, start, end)
            self.assertEqual(len(blob), end - start, label)
            self.assertEqual(hashlib.sha256(blob).hexdigest().upper(), expected, label)

    # -- 3 ------------------------------------------------------------------
    def test_item_operate_producer_callsite_enumeration(self):
        # the whole ItemOperate producer surface, recomputed by e8 scan
        self.assertEqual(_callers_of(self.pe, ITEM_OPERATE_ALLOC), ALLOC_SITES)
        self.assertEqual(_callers_of(self.pe, OP3_FACTORY), OP3_SITES)
        self.assertEqual(_callers_of(self.pe, OP4_FACTORY), OP4_SITES)
        self.assertEqual(_callers_of(self.pe, OP5_FACTORY), OP5_SITES)
        self.assertEqual(_callers_of(self.pe, OP6_FACTORY), OP6_SITES)
        # three of the five op5 sites live inside the op6 site-A function
        self.assertEqual([s for s in OP5_SITES if FN_A[0] <= s < FN_A[1]],
                         [0x57D0A7, 0x57D220, 0x57D277])

    # -- 4 ------------------------------------------------------------------
    def test_op3_factory_is_identity_only_stdcall_ret8(self):
        f = _instructions(self.pe, OP3_FACTORY, OP3_FACTORY + 0x40)
        # operation immediate 3 and the two-dword identity store
        self.assertEqual(_read_va(self.pe, 0x59F79E, 0x59F7A2).hex(), "c6401403")
        self.assertEqual(f[0x59F7A2], ("mov", "dword ptr [eax + 0x20], ecx"))
        self.assertEqual(f[0x59F7A5], ("mov", "dword ptr [eax + 0x24], edx"))
        # value32 @+0x18 is never written by op3 (that is what makes it identity-only)
        self.assertFalse(any(op.startswith("dword ptr [eax + 0x18]")
                             for (mn, op) in f.values() if mn == "mov"))
        self.assertEqual(_read_va(self.pe, 0x59F7B4, 0x59F7B7), bytes([0xC2, 0x08, 0x00]))
        # op4/op6 by contrast take more arguments
        self.assertEqual(_read_va(self.pe, 0x59F7FB, 0x59F7FE), bytes([0xC2, 0x18, 0x00]))
        self.assertEqual(_read_va(self.pe, 0x59F8AB, 0x59F8AE), bytes([0xC2, 0x0C, 0x00]))

    # -- 5 ------------------------------------------------------------------
    def test_op3_caller_is_a_modal_dialog_callback(self):
        # the function is int3-padded on both sides and 0x3E bytes long
        self.assertEqual(_read_va(self.pe, OP3_CALLBACK - 1, OP3_CALLBACK), b"\xcc")
        self.assertEqual(_read_va(self.pe, OP3_CALLBACK_END - 1, OP3_CALLBACK_END + 2), b"\xc3\xcc\xcc")
        # never e8-called; only ever pushed as a function pointer
        self.assertEqual(_callers_of(self.pe, OP3_CALLBACK), [])
        self.assertEqual(_image_refs(self.pe, OP3_CALLBACK), [(OP3_CALLBACK_PUSH + 1, ".text")])
        self.assertEqual(_read_va(self.pe, OP3_CALLBACK_PUSH, OP3_CALLBACK_PUSH + 5).hex(),
                         "68e09c5b00")
        # the registrar stores that pointer into dialog+0x12CC
        self.assertEqual(_call_target(self.pe, 0x5BA179), DIALOG_CB_REGISTER)
        reg = _instructions(self.pe, DIALOG_CB_REGISTER, DIALOG_CB_REGISTER + 0x50)
        self.assertEqual(reg[0x405D79], ("mov", "dword ptr [esi + 0x12cc], eax"))

    # -- 6 ------------------------------------------------------------------
    def test_op3_callback_result_gate_and_identity_latch(self):
        cb = _instructions(self.pe, OP3_CALLBACK, OP3_CALLBACK_END)
        self.assertEqual(cb[0x5B9CE4], ("cmp", "dword ptr [eax + 0x94], 1"))
        self.assertEqual(cb[0x5B9CED], ("mov", "eax, dword ptr [0x1080f40]"))
        self.assertEqual(cb[0x5B9CF2], ("mov", "ecx, dword ptr [0x1080f44]"))
        self.assertEqual(cb[0x5B9D0C], ("call", "0x59f780"))
        self.assertEqual(cb[0x5B9D13], ("mov", "dword ptr [0x1080f40], eax"))
        self.assertEqual(cb[0x5B9D18], ("mov", "dword ptr [0x1080f44], eax"))
        # exactly four references to each half of the latched identity qword
        self.assertEqual([hex(v) for v, _ in _image_refs(self.pe, LATCH_LO)],
                         ["0x5b9cee", "0x5b9d14", "0x5b9da1", "0x5ba116"])
        self.assertEqual([hex(v) for v, _ in _image_refs(self.pe, LATCH_HI)],
                         ["0x5b9cf4", "0x5b9d19", "0x5b9dab", "0x5ba107"])

    # -- 7 ------------------------------------------------------------------
    def test_panel_d_verb2_latches_then_opens_a_confirm(self):
        d = _instructions(self.pe, FN_D[0], 0x5BA220)
        self.assertEqual(_read_va(self.pe, FN_D[0], FN_D[0] + 13).hex(),
                         "6aff68cacdb90064a100000000")           # SEH prologue
        self.assertEqual(d[0x5B9FE0], ("mov", "eax, dword ptr [eax + 0x94]"))   # verb load
        self.assertEqual(d[0x5B9FE6], ("cmp", "eax, 1"))
        self.assertEqual(d[0x5BA03C], ("cmp", "eax, 2"))
        self.assertEqual(d[0x5BA183], ("cmp", "eax, 0x16"))
        self.assertEqual(d[0x5BA105], ("mov", "dword ptr [0x1080f44], ecx"))
        self.assertEqual(d[0x5BA115], ("mov", "dword ptr [0x1080f40], eax"))
        self.assertEqual(_read_va(self.pe, 0x5BA13B, 0x5BA13D), bytes([0x6A, MSGBOX_TEMPLATE]))
        self.assertEqual(_call_target(self.pe, 0x5BA13D), MSGBOX_OPEN)
        self.assertEqual(_call_target(self.pe, 0x5BA208), OP6_FACTORY)

    # -- 8 ------------------------------------------------------------------
    def test_op6_site_a_is_a_third_verb16_gate_with_two_handles(self):
        self.assertEqual(_read_va(self.pe, FN_A[0], FN_A[0] + 13).hex(),
                         "6aff68688db90064a100000000")
        self.assertTrue(FN_A[0] <= 0x57D1F4 < FN_A[1])
        # memory-operand verb test: invisible to a `83 F8 16` (cmp eax,0x16) scan
        self.assertEqual(_read_va(self.pe, 0x57D0C0, 0x57D0C7).hex(), "83be9400000016")
        cmp_eax_16 = _pattern_sites(self.pe, "83f816")
        self.assertIn(0x5A349B, cmp_eax_16)          # 003's site C gate
        self.assertIn(0x5BA183, cmp_eax_16)          # 003's site D gate
        self.assertEqual([v for v in cmp_eax_16 if FN_A[0] <= v < FN_A[1]], [])
        a = _instructions(self.pe, 0x57D0C0, 0x57D2A0)
        self.assertEqual(a[0x57D16D], ("mov", "eax, dword ptr [edi + 0x94]"))
        self.assertEqual(a[0x57D173], ("mov", "esi, dword ptr [esi + 0x94]"))
        self.assertEqual(a[0x57D179], ("mov", "dword ptr [esp + 0x14], eax"))
        self.assertEqual(_call_target(self.pe, 0x57D1F4), OP6_FACTORY)
        self.assertEqual(_call_target(self.pe, 0x57D220), OP5_FACTORY)
        self.assertEqual(_call_target(self.pe, 0x57D277), OP5_FACTORY)

    # -- 9 ------------------------------------------------------------------
    def test_op6_site_b_is_context_mode_gated_not_verb_gated(self):
        self.assertEqual(_read_va(self.pe, FN_B[0], FN_B[0] + 13).hex(),
                         "6aff68e390b90064a100000000")
        self.assertTrue(FN_B[0] <= 0x58294D < FN_B[1])
        b = _instructions(self.pe, 0x582844, 0x582952)
        self.assertEqual(b[0x58284B], ("mov", "ecx, dword ptr [ecx + 8]"))
        self.assertEqual(b[0x58284E], ("cmp", "ecx, 1"))
        self.assertEqual(b[0x58292D], ("cmp", "ecx, 2"))
        # no verb-code compare anywhere in this function
        self.assertEqual([v for v in _pattern_sites(self.pe, "83f816")
                          if FN_B[0] <= v < FN_B[1]], [])
        # the mode-1 arm is a keyboard-modifier path
        self.assertEqual(_read_va(self.pe, 0x582857, 0x582859), bytes([0x6A, 0x10]))  # VK_SHIFT
        self.assertEqual(_call_target(self.pe, 0x582859), GETASYNCKEYSTATE_WRAPPER)
        self.assertEqual(_read_va(self.pe, 0x5828EE, 0x5828F0), bytes([0x6A, 0x11]))  # VK_CONTROL
        self.assertEqual(_call_target(self.pe, 0x5828F0), GETASYNCKEYSTATE_WRAPPER)
        w = _instructions(self.pe, GETASYNCKEYSTATE_WRAPPER, GETASYNCKEYSTATE_WRAPPER + 0x20)
        self.assertEqual(w[0x448EC5], ("call", "dword ptr [0xc3b990]"))
        self.assertEqual(w[0x448ECB], ("mov", "ecx, 0x8000"))
        self.assertEqual(_call_target(self.pe, 0x58294D), OP6_FACTORY)

    # -- 10 -----------------------------------------------------------------
    def test_no_vendor_or_price_context_at_any_item_operate_producer(self):
        for label, (lo, hi) in (("A", FN_A), ("B", FN_B), ("C", FN_C), ("D", FN_D),
                                ("op3cb", (OP3_CALLBACK, OP3_CALLBACK_END))):
            strings = _referenced_strings(self.pe, lo, hi)
            self.assertEqual(sorted(s for s in strings if VENDOR_WORDS.search(s)), [], label)
        self.assertEqual(
            _referenced_strings(self.pe, *FN_C),
            {"CGCGuildModule", "EquipmentModule", "GetBack", "ItemMallModule_Client",
             "PopItem", "StorageModule_Client", "TradeModule_Client"},
        )

    # -- 11 -----------------------------------------------------------------
    def test_use_rides_its_own_useitemvital_class(self):
        self.assertEqual(_read_va(self.pe, USEITEM_NAME, USEITEM_NAME + 13), b"UseItemVital\x00")
        self.assertEqual(_pattern_sites(self.pe, "68" + struct.pack("<I", USEITEM_NAME).hex()),
                         [0xBEE600])
        self.assertEqual(_call_target(self.pe, USEITEM_REG_CALL), CLASS_REGISTRY)
        self.assertEqual(_pattern_sites(self.pe, "66a3" + struct.pack("<I", USEITEM_IDSLOT).hex()),
                         [0xBEE611])
        self.assertEqual(_pattern_sites(self.pe, "66a1" + struct.pack("<I", USEITEM_IDSLOT).hex()),
                         [USEITEM_GETID])
        self.assertEqual(_read_va(self.pe, USEITEM_GETID, USEITEM_GETID + 7).hex(),
                         "66a130200801c3")
        # same 9-slot cohort shape as ItemOperateVitalReq
        for vt, serial in ((USEITEM_VTABLE, USEITEM_SERIAL), (ITEMOP_VTABLE, ITEMOP_SERIAL)):
            self.assertEqual(_dword(self.pe, vt + 0x08), 0x401B20)
            self.assertEqual(_dword(self.pe, vt + 0x18), serial)
            self.assertEqual(_dword(self.pe, vt + 0x1C), 0x710440)
        self.assertEqual(_dword(self.pe, USEITEM_VTABLE + 0x10), USEITEM_GETID)
        # serializer 0x6C0180 = exactly one tag-0x32 qword @+0x18, stdcall ret 8
        s = _instructions(self.pe, USEITEM_SERIAL, USEITEM_SERIAL + 0x24)
        self.assertEqual(s[0x6C0180], ("add", "ecx, 0x18"))
        self.assertEqual(_read_va(self.pe, 0x6C0188, 0x6C018A), bytes([0x6A, 0x08]))   # width 8
        self.assertEqual(_read_va(self.pe, 0x6C018F, 0x6C0191), bytes([0x6A, 0x32]))   # tag 0x32
        self.assertEqual(_call_target(self.pe, 0x6C0193), FIELD_CODEC_OUT)
        self.assertEqual(_call_target(self.pe, 0x6C019B), FIELD_CODEC_IN)
        self.assertEqual(s[0x6C0198], ("ret", "8"))
        # no operation byte and no value32 anywhere in the routine
        self.assertNotIn(bytes([0x6A, 0x0B]), _read_va(self.pe, USEITEM_SERIAL, 0x6C01A3))
        self.assertNotIn(bytes([0x6A, 0x14]), _read_va(self.pe, USEITEM_SERIAL, 0x6C01A3))

    # -- 12 -----------------------------------------------------------------
    def test_sell_rides_stall_blackmarket_and_store_classes(self):
        for name, name_va, reg_call in OTHER_TRANSPORT_CLASSES:
            self.assertEqual(_cstr(self.pe, name_va), name)
            self.assertEqual(_read_va(self.pe, reg_call - 5, reg_call),
                             b"\x68" + struct.pack("<I", name_va), name)
            self.assertEqual(_call_target(self.pe, reg_call), CLASS_REGISTRY, name)
        # StallOperateVital carries a price: u8 tag 0x08 @+0x14, qword tag 0x32 @+0x18,
        # a string @+0x24 and u32 tag 0x14 @+0x20 — a different wire from ItemOperate.
        self.assertEqual(_dword(self.pe, STALLOP_VTABLE + 0x08), 0x401B20)
        self.assertEqual(_dword(self.pe, STALLOP_VTABLE + 0x18), STALLOP_SERIAL)
        st = _instructions(self.pe, STALLOP_SERIAL, STALLOP_SERIAL + 0x60)
        self.assertEqual(st[0x76A63F], ("lea", "eax, [esi + 0x14]"))
        self.assertEqual(_read_va(self.pe, 0x76A645, 0x76A647), bytes([0x6A, 0x08]))
        self.assertEqual(st[0x76A652], ("lea", "ecx, [esi + 0x18]"))
        self.assertEqual(_read_va(self.pe, 0x76A656, 0x76A658), bytes([0x6A, 0x32]))
        self.assertEqual(st[0x76A65F], ("lea", "edx, [esi + 0x24]"))
        self.assertEqual(_call_target(self.pe, 0x76A665), 0x89A810)
        self.assertEqual(st[0x76A66C], ("lea", "eax, [esi + 0x20]"))
        self.assertEqual(_read_va(self.pe, 0x76A670, 0x76A672), bytes([0x6A, 0x14]))
        # and no ItemOperate producer lives in that code band
        for site in OP3_SITES + OP4_SITES + OP5_SITES + OP6_SITES:
            self.assertFalse(0x6C0000 <= site < 0x790000, hex(site))

    # -- 13 -----------------------------------------------------------------
    def test_dialog_resource_0x12_is_actually_an_eh_trylevel(self):
        # the EHRec anchor fixes the trylevel slot for both functions
        d = _instructions(self.pe, 0x5A2A70, 0x5A2AB0)
        self.assertEqual(d[0x5A2A76], ("push", "-1"))
        self.assertEqual(d[0x5A2AA3], ("lea", "eax, [esp + 0x170]"))
        self.assertEqual(d[0x5A2AAA], ("mov", "dword ptr fs:[0], eax"))
        # the SAME slot takes 0x12, 0xFFFFFFFF and 0x0A at the matching esp depths
        self.assertEqual(_read_va(self.pe, 0x5A34D7, 0x5A34E2).hex(), "c784248001000012000000")
        self.assertEqual(_read_va(self.pe, 0x5A3502, 0x5A350D).hex(), "c7842478010000ffffffff")
        self.assertEqual(_read_va(self.pe, 0x5A335A, 0x5A3362).hex(), "c68424780100000a")
        self.assertEqual(_read_va(self.pe, 0x5A30C0, 0x5A30CB).hex(), "c78424800100000a000000")
        # the same pattern in panel fn 0x5B9F70
        self.assertEqual(_read_va(self.pe, 0x5B9F9D, 0x5B9FA4).hex(), "8d842428010000")
        self.assertEqual(_read_va(self.pe, 0x5BA07B, 0x5BA086).hex(), "c784243801000000000000")
        self.assertEqual(_read_va(self.pe, 0x5BA1C5, 0x5BA1D0).hex(), "c784243801000002000000")
        self.assertEqual(_read_va(self.pe, 0x5BA211, 0x5BA21C).hex(), "c7842430010000ffffffff")
        # 001-003's structural chain is unchanged by the relabel
        self.assertEqual(_read_va(self.pe, 0x5A349B, 0x5A349E).hex(), "83f816")
        self.assertEqual(_call_target(self.pe, 0x5A34E2), 0x5A1630)
        self.assertEqual(_read_va(self.pe, 0x5A34EF, 0x5A34F3).hex(), "83782c00")
        self.assertEqual(_call_target(self.pe, 0x5A3532), OP6_FACTORY)

    # -- 14 -----------------------------------------------------------------
    def test_name_hash_links_client_class_names_to_server_ids(self):
        # recomputed here, not imported: sum((i+1)*ord(c)) & 0xFFFF
        self.assertEqual(_name_id("UseItemVital"), 0x1F4F)
        self.assertEqual(_name_id("ItemOperateVitalReq"), 0x4BED)
        self.assertEqual(_name_id("ItemOperateVitalRes"), 0x4C13)
        self.assertEqual(_name_id("TradeCmdVital"), 0x23B5)

    # -- 15 -----------------------------------------------------------------
    def test_wire_shapes_of_use_versus_item_operate(self):
        use = _use_item_wire(0x1122334455667788)
        self.assertEqual(len(use), 9)
        self.assertEqual(use[0], 0x32)
        self.assertEqual(struct.unpack_from("<Q", use, 1)[0], 0x1122334455667788)
        # no operation byte and no value32 exist on the use wire at all
        self.assertNotIn(0x0B, use[:1])
        self.assertNotIn(0x14, use[:1])
        # the ItemOperate wire is a strictly larger, three-field shape
        op3 = _item_operate_wire(3, 0, 0x1122334455667788)
        op6 = _item_operate_wire(6, 0xDEADBEEF, 7)
        self.assertEqual(len(op3), 2 + 5 + 9)
        self.assertEqual(op3[:2], bytes([0x0B, 3]))
        self.assertEqual(op6[:2], bytes([0x0B, 6]))
        self.assertEqual(struct.unpack_from("<I", op6, 3)[0], 0xDEADBEEF)   # value32 = handle
        self.assertEqual(struct.unpack_from("<Q", op6, 8)[0], 7)            # qword = quantity
        self.assertNotEqual(len(use), len(op3))

    # -- 16 -----------------------------------------------------------------
    def test_server_has_no_use_drop_sell_handler(self):
        src = SERVER.read_text(encoding="utf-8", errors="replace")
        flat = src.replace(" ", "")
        # USE: named but never dispatched
        self.assertIn("USE_ITEM_VITAL = 0x1F4F", src)
        self.assertIn('USE_ITEM_VITAL: "UseItemVital"', src)
        self.assertEqual(src.count("USE_ITEM_VITAL"), 3)
        self.assertNotIn("nested_id==USE_ITEM_VITAL", flat)
        # ItemOperate: operation 4 and 5 only
        self.assertIn("V123_EQUIP_FROM_BAG_OPERATION = 5", src)
        self.assertIn("operation==4", flat)
        self.assertNotIn("operation==3", flat)
        self.assertNotIn("operation==6", flat)
        # SELL: no stall / black-market surface at all
        self.assertNotIn("StallOperateVital", src)
        self.assertNotIn("BlackMarket", src)
        defs = re.findall(r"^\s*def (\w+)", src, re.M)
        self.assertEqual([d for d in defs if re.search(
            r"(sell|stall|market|vendor|discard|destroy_item|drop_item|use_item)", d, re.I)], [])
        # the NPC-store path that IS implemented is a different wire, and buy-only
        self.assertIn("TRADE_CMD_VITAL = 0x23B5", src)
        self.assertIn("V118_TRADE_CART_ADD_COMMAND = 6", src)
        self.assertIn("def make_trade_item_result_store_buy_cart_ack", src)
        self.assertEqual(flat.count("trade['field_u8']==V118_TRADE_CART_ADD_COMMAND"), 1)
        # the foundation fails closed on any operation other than 4
        found = FOUNDATION_RUNTIME.read_text(encoding="utf-8", errors="replace")
        self.assertIn("if operation != ITEM_MOVE_CAPTURE_FIELDS[0]:", found)
        self.assertIn("item_move_generalized_wrong_operation_no_reply", found)


if __name__ == "__main__":
    unittest.main()
