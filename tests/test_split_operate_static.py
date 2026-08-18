"""PF SPLIT-OPERATE-001 — static characterization of the ItemOperateVitalReq
0x4BED operation space (the transport a stack-split request must ride).

Byte-exact pins over the read-only client binary GameClient/GameClient.local.bin
cross-checked against the read-only server current/pf_login_game_server_v141.py.
Report-only / additive: no server behavior is changed by this milestone; the test
merely locks the disassembled facts cited in
reports/PF_SPLIT_OPERATE001_ITEM_OPERATE_OPCODE_SPACE_STATIC_20260818.md.
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

# (start, end, sha256) byte-span pins — instruction-aligned, byte-identical.
SPANS = {
    "getid_stub":   (0x5E5AE0, 0x5E5AE7, "E757D9EA8BECCF6298A1736FB90BFE70F85C5C47FCE21E45A24E287248A2AFFA"),
    "serializer":   (0x5E5AF0, 0x5E5B5D, "D25B32EB977D1E5D029DB7F4D7399413B18F2EA004A9C502801580BF11316094"),
    "constructor":  (0x5E5B60, 0x5E5B90, "B93530D850CA1081117666F140F2EECB2AB5E642256DADFC92789C15C6B33ED3"),
    "vtable":       (0xF30374, 0xF30394, "D272EEDB661F43D87A9917484E069B3A811C646D8414C2AC7431B8CBD75845A7"),
    "registration": (0xBEE520, 0xBEE538, "13602513CB3600B04C4C4F3E3CD3BB55AB4C801394498E3195AB5AADDA9F6556"),
    "producer_op3": (0x59F780, 0x59F7B6, "4F6F8E7687946AE90AE40C27E1E5CC06E82DE3C441821DE6E0063F83069F2001"),
    "producer_op4": (0x59F7C0, 0x59F7FE, "D441C505E9AB01E7E232210D45EB2D617CC95591AEB998228CC04B338AE54E44"),
    "producer_op5": (0x59F800, 0x59F868, "70F75803E0CC3937860813CE5E255D2B2184F13013061833FE68748DDF0DAE01"),
    "producer_op6": (0x59F870, 0x59F8AE, "A165878D9441A2CE9FA3272DF291178E53CB239E8A081D67588B1D28AD4BB29A"),
}


def _read_va(pe: pefile.PE, start: int, end: int) -> bytes:
    return pe.get_data(start - pe.OPTIONAL_HEADER.ImageBase, end - start)


def _instructions(pe: pefile.PE, start: int, end: int):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return {i.address: (i.mnemonic, i.op_str) for i in md.disasm(_read_va(pe, start, end), start)}


class SplitOperateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pe = pefile.PE(str(BINARY), fast_load=True)

    def test_binary_hash_is_the_pinned_client(self):
        self.assertEqual(
            hashlib.sha256(BINARY.read_bytes()).hexdigest().upper(), BINARY_SHA
        )

    def test_spans_are_byte_identical(self):
        for label, (start, end, expected) in SPANS.items():
            data = _read_va(self.pe, start, end)
            self.assertEqual(len(data), end - start, label)
            self.assertEqual(
                hashlib.sha256(data).hexdigest().upper(), expected, label
            )

    def test_id_is_runtime_assigned_not_a_code_immediate(self):
        # 0x4BED (ItemOperateVitalReq id) is assigned at startup via the id-slot,
        # never emitted as a code immediate. Same wall as the ECHO/TELEPORT cohort.
        reg = _read_va(self.pe, 0xBEE520, 0xBEE538)
        self.assertEqual(reg[0], 0x68)  # push name
        self.assertEqual(struct.unpack_from("<I", reg, 1)[0], 0xF30904)
        self.assertEqual(0xBEE525 + 5 + struct.unpack_from("<i", reg, 6)[0], 0x89C080)   # once-init
        self.assertEqual(0xBEE52C + 5 + struct.unpack_from("<i", reg, 0xD)[0], 0x89BD00)  # id-assign
        self.assertEqual(reg[0x11], 0x66)  # mov word [id-slot], ax
        self.assertEqual(struct.unpack_from("<I", reg, 0x13)[0], 0x1082014)
        # get-id stub reads the same slot
        self.assertEqual(_read_va(self.pe, 0x5E5AE0, 0x5E5AE7).hex().upper(), "66A114200801C3")

    def test_vtable_is_shared_vitaldata_cohort(self):
        vt = struct.unpack("<8I", _read_va(self.pe, 0xF30374, 0xF30394))
        self.assertEqual(vt[2], 0x401B20)  # +0x08 shared framework const
        self.assertEqual(vt[4], 0x5E5AE0)  # +0x10 get-id
        self.assertEqual(vt[6], 0x5E5AF0)  # +0x18 serializer

    def test_serializer_field_map(self):
        s = _instructions(self.pe, 0x5E5AF0, 0x5E5B60)
        self.assertEqual(s[0x5E5B03], ("lea", "eax, [esi + 0x14]"))   # operation @+0x14
        self.assertEqual(s[0x5E5B07], ("push", "0xb"))                # tag 0x0B
        self.assertEqual(s[0x5E5AFD], ("push", "1"))                  # width 1
        self.assertEqual(s[0x5E5B10], ("lea", "ecx, [esi + 0x18]"))   # value32 @+0x18
        self.assertEqual(s[0x5E5B14], ("push", "0x14"))               # tag 0x14
        self.assertEqual(s[0x5E5B0E], ("push", "4"))                  # width 4
        self.assertEqual(s[0x5E5B1F], ("add", "esi, 0x20"))           # qword @+0x20
        self.assertEqual(s[0x5E5B23], ("push", "0x32"))               # tag 0x32
        self.assertEqual(s[0x5E5B1D], ("push", "8"))                  # width 8

    def test_constructor_default_operation_is_one(self):
        # ctor 0x5E5B60 initializes obj+0x14 = 1 before any producer overwrites it.
        self.assertEqual(_read_va(self.pe, 0x5E5B87, 0x5E5B8B).hex().upper(), "C6401401")

    def test_operation_producer_immediates(self):
        # The full operation space present in the image: {3,4,5,6} (plus ctor default 1).
        for op, va in {3: 0x59F79E, 4: 0x59F7E5, 5: 0x59F84B, 6: 0x59F895}.items():
            self.assertEqual(
                _read_va(self.pe, va, va + 4), bytes([0xC6, 0x40, 0x14, op]), f"op{op}@{va:#x}"
            )
        # op5 also written from a second (equipment UI) callsite
        self.assertEqual(_read_va(self.pe, 0x5A25D1, 0x5A25D5), bytes([0xC6, 0x40, 0x14, 0x05]))

    def test_move_and_quantity_field_usage(self):
        mov = _instructions(self.pe, 0x59F7C0, 0x59F800)
        self.assertEqual(mov[0x59F7DD], ("mov", "dword ptr [eax + 0x18], ecx"))  # move: value32=dest slot
        self.assertEqual(mov[0x59F7E9], ("mov", "dword ptr [eax + 0x20], edx"))  # move: qword=item identity
        o6 = _instructions(self.pe, 0x59F870, 0x59F8B0)
        self.assertEqual(o6[0x59F88D], ("mov", "dword ptr [eax + 0x18], ecx"))   # op6: value32=item handle
        self.assertEqual(o6[0x59F899], ("mov", "dword ptr [eax + 0x20], edx"))   # op6: qword=caller 64-bit value

    def test_server_only_handles_move_and_equip_operations(self):
        # The gap that a split implementation must fill: the server recognizes
        # operation 4 (move/merge) and 5 (equip-from-bag) only. Operations 3 and 6
        # (identity-only and quantity-parameterized) have client producers but no
        # server handler yet — so split_stack is characterized, not implemented.
        src = SERVER.read_text(encoding="utf-8")
        self.assertIn("V123_EQUIP_FROM_BAG_OPERATION = 5", src)
        self.assertIn("operation==V123_EQUIP_FROM_BAG_OPERATION", src)
        self.assertIn("operation==4", src)
        self.assertNotIn("operation==6", src)
        self.assertNotIn("operation==3", src)


if __name__ == "__main__":
    unittest.main()
