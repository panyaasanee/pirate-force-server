"""PF SPLIT-OPERATE-003 — verb 0x16 -> op6 is reused across two inventory panels,
and the static caption-resolution route for the split label is evidenced-closed.

Third static supplement to split_stack (chief rounds 68/69). 002 bounded the
split candidate to inventory verb eax==0x16 and named the next hop: resolve the
numeric-dialog-id 0x12 caption, or live-capture. 003 walks that hop statically and
reports two byte-exact REFINEMENTS (not reversals) of 002:

  R1. verb 0x16 is not globally unique — two of op6's four call sites gate on
      `cmp eax,0x16`: site C @0x5A3532 in the dispatcher fn 0x5A2A70 AND site D
      @0x5BA208 in a distinct fn @0x5B9F70, both routing through the same
      numeric-input helper 0x5A1630 before op6. The shared action code + shared
      dialog is consistent with a generic quantity-split reused across panels, but
      op6 has no destination slot, so 0x16 is still equally consistent with a
      shared drop-N / destroy-N / give-N action — no positive "split" label.
  R2. the caption route is closed statically — the numeric dialog is the generic
      reusable control Common_NumInput.model (plaintext UIControlData XML, no inline
      caption); caption text comes at runtime from the packed B_TEXTDATA_TH.pc_
      ("$pcz") string table. Only a live capture can pin the split label now.

Incidental correction: 0x42AB40 (called in the verb-0x16 body before op6) is a
temp-object DESTRUCTOR (SEH prologue + two vtable stores + free 0x88D060), not a
dialog opener. Dialog id 0x12 is a stack local consumed inside the body.

Report-only / additive: no server change, no scenario, no ledger entry, no grade
change. See reports/PF_SPLIT_OPERATE003_VERB16_TWO_PANELS_STATIC_20260818.md.
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
GUI_MODEL = ROOT.parent / "GameClient" / "Data" / "GUI" / "Model"
TEXTDATA = ROOT.parent / "GameClient" / "Data" / "B_TEXTDATA_TH.pc_"

OP6_FACTORY = 0x59F870
OP6_SITES = [0x0057D1F4, 0x0058294D, 0x005A3532, 0x005BA208]
DISP_START, DISP_END = 0x005A2A70, 0x005A40B0
PANEL_D_START = 0x005B9F70
SITE_C, SITE_D = 0x005A3532, 0x005BA208
DIALOG_HELPER = 0x5A1630

# (start, end, sha256) byte-span pins for the two verb-0x16 case bodies.
SPANS = {
    "verb16_body_C": (0x5A349B, 0x5A3537, "1E2EB3E248E255CCB281783A3B089BBD81DAEBC2A8208EC7995A5DBA6B089979"),
    "verb16_body_D": (0x5BA183, 0x5BA20D, "9C84D296A94BEBEC9B4BDBFC1CE98C89DF8E79E55764D00CC61B8E8D188E5ED4"),
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
            return base + s.VirtualAddress, pe.get_data(s.VirtualAddress, s.Misc_VirtualSize)
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


def _call_target(pe: pefile.PE, va: int) -> int:
    o = _read_va(pe, va, va + 5)
    assert o[0] == 0xE8, "not an E8 call at %#x" % va
    rel = struct.unpack_from("<i", o, 1)[0]
    return (va + 5 + rel) & 0xFFFFFFFF


class SplitOperateVerbPanelsStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pe = pefile.PE(str(BINARY), fast_load=True)

    def test_binary_hash_is_the_pinned_client(self):
        self.assertEqual(hashlib.sha256(BINARY.read_bytes()).hexdigest().upper(), BINARY_SHA)

    def test_op6_still_has_exactly_four_call_sites(self):
        # 002 regression: op6 remains a four-site family.
        self.assertEqual(_callers_of(self.pe, OP6_FACTORY), OP6_SITES)

    def test_two_op6_sites_are_gated_by_verb_0x16(self):
        # bytes 83 F8 16 = cmp eax,0x16 immediately before the dialog+op6 sequence.
        self.assertEqual(_read_va(self.pe, 0x5A349B, 0x5A349E), bytes([0x83, 0xF8, 0x16]))  # site C
        self.assertEqual(_read_va(self.pe, 0x5BA183, 0x5BA186), bytes([0x83, 0xF8, 0x16]))  # site D

    def test_both_verb0x16_bodies_share_the_numeric_dialog_helper(self):
        self.assertEqual(_call_target(self.pe, 0x5A34E2), DIALOG_HELPER)  # site C
        self.assertEqual(_call_target(self.pe, 0x5BA1D0), DIALOG_HELPER)  # site D

    def test_the_two_verb0x16_sites_live_in_distinct_functions(self):
        # site C is inside the inventory dispatcher; site D is a separate panel fn.
        self.assertTrue(DISP_START <= SITE_C < DISP_END)
        self.assertFalse(DISP_START <= SITE_D < DISP_END)
        # site D's function starts at 0x5B9F70: a real boundary (preceding int3
        # padding CC CC, with a ret C3 at 0x5B9F68) and an SEH frame prologue
        # (push -1; push handler; fs:[0]).
        self.assertEqual(_read_va(self.pe, PANEL_D_START - 2, PANEL_D_START), bytes([0xCC, 0xCC]))
        self.assertEqual(_read_va(self.pe, 0x5B9F68, 0x5B9F69), bytes([0xC3]))
        self.assertEqual(_read_va(self.pe, PANEL_D_START, PANEL_D_START + 13).hex(),
                         "6aff68cacdb90064a100000000")

    def test_verb0x16_bodies_are_byte_identical(self):
        for label, (start, end, expected) in SPANS.items():
            data = _read_va(self.pe, start, end)
            self.assertEqual(len(data), end - start, label)
            self.assertEqual(hashlib.sha256(data).hexdigest().upper(), expected, label)

    def test_dispatcher_verb_switch_ladder(self):
        disp = _instructions(self.pe, DISP_START, DISP_END)
        self.assertEqual(disp[0x5A349B], ("cmp", "eax, 0x16"))  # verb 0x16 -> op6
        cmps = {o for (a, (m, o)) in disp.items() if m == "cmp" and o.startswith("eax, 0x") or (m == "cmp" and o == "eax, 2")}
        self.assertIn("eax, 2", cmps)      # verb 2 = MOVE (op4)
        self.assertIn("eax, 0x16", cmps)   # verb 0x16 = op6

    def test_dialog_id_0x12_is_a_stack_local_not_a_call_argument(self):
        # C7 84 24 80 01 00 00 12 00 00 00 = mov dword [esp+0x180], 0x12
        self.assertEqual(_read_va(self.pe, 0x5A34D7, 0x5A34E2).hex(), "c784248001000012000000")

    def test_0x42AB40_is_a_temp_object_destructor_not_a_dialog_opener(self):
        # SEH prologue 6A FF 68 53 53 B8 00 64 A1 00 00 00 00, two vtable stores,
        # and free/dtor 0x88D060 — a teardown, not an "open dialog by id".
        self.assertEqual(_read_va(self.pe, 0x42AB40, 0x42AB4D).hex(), "6aff685353b80064a100000000")
        self.assertEqual(_read_va(self.pe, 0x42AB6A, 0x42AB6E), bytes.fromhex("78B9F000"))  # vtable 0xF0B978
        self.assertEqual(_read_va(self.pe, 0x42ABAC, 0x42ABB0), bytes.fromhex("FCB8F000"))  # vtable 0xF0B8FC
        self.assertEqual(_call_target(self.pe, 0x42AB83), 0x88D060)

    def test_the_numeric_dialog_is_a_generic_reusable_control(self):
        # caption is NOT baked into a split-specific model; it's the shared NumInput.
        names = {p.name.lower() for p in GUI_MODEL.glob("*.model")}
        self.assertIn("common_numinput.model", names)
        self.assertFalse(any("split" in n or "divide" in n for n in names),
                         "no split/divide-named dialog model exists")
        body = (GUI_MODEL / "Common_NumInput.model").read_bytes().lower()
        self.assertIn(b"<uicontroldata>", body)
        self.assertNotIn(b"split", body)
        self.assertNotIn(b"divide", body)

    def test_the_caption_text_table_is_packed_and_not_statically_readable(self):
        self.assertEqual(TEXTDATA.read_bytes()[:4], b"$pcz")


if __name__ == "__main__":
    unittest.main()
