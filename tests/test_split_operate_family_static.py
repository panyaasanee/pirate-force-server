"""PF SPLIT-OPERATE-002 — static enumeration of the op6 quantity-op FAMILY and
the bounding of the stack-split candidate to a single inventory verb.

Supplement to SPLIT-OPERATE-001. 001 characterized the ItemOperateVitalReq 0x4BED
operation space and deliberately did NOT claim "op6 == split specifically" (op6 is
a quantity-op family). 002 pins, byte-exact from the read-only client binary
cross-checked against the read-only server source, why the split candidate is
bounded — and why it is still not pinned to one verb without a live capture:

  * the op6 factory 0x59F870 has EXACTLY FOUR call sites (a shared family);
  * every site passes (qty_low, qty_high, item_handle) and the factory serializes
    value32=item_handle, qword=64-bit quantity, ret 0xC — uniform, no destination;
  * the inventory action dispatcher [0x5A2A70,0x5A40B0) holds the op4=move producer
    (verb eax==2) and EXACTLY ONE op6 site (verb eax==0x16); the other three op6
    sites live in three distinct functions outside the dispatcher;
  * verb 0x16 opens numeric-input dialog resource 0x12, guards it strictly positive,
    then calls op6;
  * the server builds an operation-4 move response and special-cases the operation-5
    equip decode, but has NO operation-6 (or -3) handler.

Report-only / additive: no server behavior is changed by this milestone. See
reports/PF_SPLIT_OPERATE002_OP6_QUANTITY_FAMILY_ENUMERATION_STATIC_20260818.md.
"""
from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path

import capstone
import pefile

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT.parent / "GameClient" / "GameClient.local.bin"
BINARY_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
SERVER = ROOT / "current" / "pf_login_game_server_v141.py"

OP6_FACTORY = 0x59F870
OP4_FACTORY = 0x59F7C0
OP3_FACTORY = 0x59F780
OP6_SITES = [0x0057D1F4, 0x0058294D, 0x005A3532, 0x005BA208]
VERB16_OP6_SITE = 0x005A3532
DISP_START, DISP_END = 0x005A2A70, 0x005A40B0

# (start, end, sha256) byte-span pins — instruction-aligned, byte-identical.
SPANS = {
    "dispatcher_prologue": (0x5A2A70, 0x5A2A90, "33AFA95078A863F2C7CCB59E86541D0A017B5228C64363E3758F6827C9A49AB1"),
    "verb16_case_body":    (0x5A349B, 0x5A3537, "1E2EB3E248E255CCB281783A3B089BBD81DAEBC2A8208EC7995A5DBA6B089979"),
    "op6_site_57d1f4":     (0x57D1E0, 0x57D1F9, "D5BC98C5D2BD7C8790AAF92AE248948DFA4394CD8CD13E5BB29EC95F68B8055B"),
    "op6_site_58294d":     (0x582939, 0x582952, "0E1D6182C225FE0CDA77D22AF42AEECB18CD893D1BFF78268E26F73F9F53D457"),
    "op6_site_5a3532":     (0x5A351E, 0x5A3537, "69927F2F32DAB0B7403098B0BCFB4CB0B9D00C5CE1B4BD16DDC153B5A0A4A4CB"),
    "op6_site_5ba208":     (0x5BA1F4, 0x5BA20D, "33CA0EB8DF85EEE9BAB15D2CC0E26550B753DBB446ADBFE1DFD81B3D010FC3B7"),
}


def _read_va(pe: pefile.PE, start: int, end: int) -> bytes:
    return pe.get_data(start - pe.OPTIONAL_HEADER.ImageBase, end - start)


def _instructions(pe: pefile.PE, start: int, end: int):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return {i.address: (i.mnemonic, i.op_str) for i in md.disasm(_read_va(pe, start, end), start)}


def _text_section(pe: pefile.PE):
    base = pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        if s.Name.rstrip(b"\x00") == b".text":
            start = base + s.VirtualAddress
            return start, pe.get_data(s.VirtualAddress, s.Misc_VirtualSize)
    raise AssertionError(".text not found")


def _callers_of(pe: pefile.PE, target: int) -> list[int]:
    start, blob = _text_section(pe)
    res = []
    for i in range(0, len(blob) - 5):
        if blob[i] == 0xE8:
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            va = start + i
            if ((va + 5 + rel) & 0xFFFFFFFF) == target:
                res.append(va)
    return res


class SplitOperateFamilyStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pe = pefile.PE(str(BINARY), fast_load=True)

    def test_binary_hash_is_the_pinned_client(self):
        self.assertEqual(hashlib.sha256(BINARY.read_bytes()).hexdigest().upper(), BINARY_SHA)

    def test_spans_are_byte_identical(self):
        for label, (start, end, expected) in SPANS.items():
            data = _read_va(self.pe, start, end)
            self.assertEqual(len(data), end - start, label)
            self.assertEqual(hashlib.sha256(data).hexdigest().upper(), expected, label)

    def test_op6_factory_operation_and_calling_contract(self):
        # operation immediate = 6; value32=3rd arg (handle); qword=(1st,2nd args)=qty; ret 0xC
        self.assertEqual(_read_va(self.pe, 0x59F895, 0x59F899), bytes([0xC6, 0x40, 0x14, 0x06]))
        o6 = _instructions(self.pe, 0x59F870, 0x59F8B0)
        self.assertEqual(o6[0x59F88D], ("mov", "dword ptr [eax + 0x18], ecx"))  # value32 = item handle
        self.assertEqual(o6[0x59F899], ("mov", "dword ptr [eax + 0x20], edx"))  # qword low = qty low
        self.assertEqual(o6[0x59F89C], ("mov", "dword ptr [eax + 0x24], ecx"))  # qword high = qty high
        self.assertEqual(_read_va(self.pe, 0x59F8AB, 0x59F8AE), bytes([0xC2, 0x0C, 0x00]))  # ret 0xC

    def test_op6_has_exactly_four_call_sites(self):
        self.assertEqual(_callers_of(self.pe, OP6_FACTORY), OP6_SITES)

    def test_op4_and_op3_have_one_call_site_each(self):
        # cross-check: the move producer is reached from the single verb-2 site,
        # op3 from a single site — so op6's four sites are a real family, not an
        # artifact of the scan.
        self.assertEqual(_callers_of(self.pe, OP4_FACTORY), [0x005A3491])
        self.assertEqual(_callers_of(self.pe, OP3_FACTORY), [0x005B9D0C])

    def test_dispatcher_is_one_contiguous_function(self):
        # prologue + no int3 boundary through the op6 site + next prologue at DISP_END
        self.assertEqual(_read_va(self.pe, 0x5A2A70, 0x5A2A7D).hex(), "558bec83e4f86aff68d7afb900")
        body = _instructions(self.pe, DISP_START, 0x5A3540)
        self.assertNotIn("int3", [m for (m, _o) in body.values()])
        nxt = None
        blob = _read_va(self.pe, 0x5A3540, 0x5A4200)
        for j in range(len(blob) - 3):
            if blob[j] == 0x55 and blob[j + 1] == 0x8B and blob[j + 2] == 0xEC:
                nxt = 0x5A3540 + j
                break
        self.assertEqual(nxt, DISP_END)

    def test_exactly_one_op6_site_is_the_inventory_verb0x16(self):
        # op4-move (verb 2) is inside the dispatcher; exactly one op6 site is too,
        # and it is verb 0x16. The other three op6 sites are outside.
        self.assertTrue(DISP_START <= 0x005A3491 < DISP_END)
        inside = [s for s in OP6_SITES if DISP_START <= s < DISP_END]
        self.assertEqual(inside, [VERB16_OP6_SITE])

    def test_verb0x16_opens_positive_quantity_dialog_then_op6(self):
        self.assertEqual(_read_va(self.pe, 0x5A349B, 0x5A349E), bytes([0x83, 0xF8, 0x16]))  # cmp eax,0x16
        self.assertEqual(_read_va(self.pe, 0x5A34D7, 0x5A34E2).hex(), "c784248001000012000000")  # dlg res 0x12
        seq = _instructions(self.pe, 0x5A34E2, 0x5A34E8)
        self.assertEqual(seq[0x5A34E2], ("call", "0x5a1630"))                                 # numeric dialog
        self.assertEqual(_read_va(self.pe, 0x5A34EF, 0x5A34F3), bytes([0x83, 0x78, 0x2C, 0x00]))  # >0 guard
        callop6 = _instructions(self.pe, 0x5A3532, 0x5A3538)
        self.assertEqual(callop6[0x5A3532], ("call", "0x59f870"))                             # op6

    def test_server_has_no_op6_quantity_handler(self):
        # The gap a split must fill: server builds a move (op4) response and decodes
        # the equip (op5) case, but has no op6/op3 handler and no split response.
        src = SERVER.read_text(encoding="utf-8")
        self.assertIn("ITEM_OPERATE_REQ_VITAL = 0x4BED", src)
        self.assertIn("V123_EQUIP_FROM_BAG_OPERATION = 5", src)
        self.assertIn("def make_item_operate_move_delta_success", src)
        flat = src.replace(" ", "")
        self.assertNotIn("operation==6", flat)
        self.assertNotIn("operation==3", flat)
        self.assertNotIn("def make_item_operate_split", src)
        self.assertNotIn("def make_item_operate_quantity", src)


if __name__ == "__main__":
    unittest.main()
