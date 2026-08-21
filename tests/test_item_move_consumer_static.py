from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import unittest

import capstone
import pefile

# Both proprietary client binaries live in ../GameClient and can never be in a
# fresh clone; every test below reads them.  See tests/pf_preconditions.py.
from pf_preconditions import CLIENT_IMAGE, GAME_INSTALL_TREE


ROOT = Path(__file__).resolve().parents[1]

BINARIES = {
    "GameClient.bin": "C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD",
    "GameClient.local.bin": "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623",
}

SPANS = {
    "response_apply": (
        0x5A8EBD,
        0x5A9068,
        "950135C96FF407BA6326B1A1B6339F8F5D7394DA5D6A1E1C41EE03CA90B4C613",
    ),
    "identity_clear": (
        0x59FB40,
        0x59FC50,
        "57AA9A29838E4C57BC9B6528B43C215B1E2F93F86DC281B4B65ACDD635B7DC61",
    ),
    "slot_assign": (
        0x5A1240,
        0x5A1309,
        "6434F0F14A829A398E3DAB276BBC8823F808D075CA0EDE62C7DB901E260BF971",
    ),
    "slot_replace": (
        0x5C15B0,
        0x5C1668,
        "BFEEBED09703D388B2477815A75E59AB7311979322E70A8A0F40D4D6EAC2420B",
    ),
    "item_ctor": (
        0x46B410,
        0x46B497,
        "5A5D9ABA90E35EEA8119D252751058561C125FF68E54C3416A8BEF6230872DDC",
    ),
    "item_vtable": (
        0xF0EBB0,
        0xF0EBF0,
        "8BE15B9EE799423FDDE3C7D5E31F698188B503FEE54BD6035843B5B79830EDCC",
    ),
    "item_clone": (
        0x46BC50,
        0x46BD2C,
        "FB3FE799D07B56019A747134D39572AA4A7B31EB33961C6858D43535D93B9BFD",
    ),
}


def _read_va(pe: pefile.PE, start: int, end: int) -> bytes:
    return pe.get_data(start - pe.OPTIONAL_HEADER.ImageBase, end - start)


def _instructions(pe: pefile.PE, start: int, end: int):
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return {
        instruction.address: (instruction.mnemonic, instruction.op_str)
        for instruction in decoder.disasm(_read_va(pe, start, end), start)
    }


class ItemMoveConsumerStaticTests(unittest.TestCase):
    # Reads GameClient.bin from the proprietary install tree AND the patched
    # local image; the local image lives inside that tree, so client_image is
    # the stricter single key.  See tests/pf_preconditions.py.
    @CLIENT_IMAGE.skip_unless_present()
    def test_exact_original_and_local_spans_are_identical(self):
        observed = {}
        for filename, whole_hash in BINARIES.items():
            path = ROOT.parent / "GameClient" / filename
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                whole_hash,
            )
            pe = pefile.PE(str(path), fast_load=True)
            observed[filename] = {}
            for label, (start, end, expected_hash) in SPANS.items():
                data = _read_va(pe, start, end)
                self.assertEqual(len(data), end - start)
                self.assertEqual(
                    hashlib.sha256(data).hexdigest().upper(), expected_hash,
                )
                observed[filename][label] = data
        self.assertEqual(
            observed["GameClient.bin"], observed["GameClient.local.bin"],
        )

    # Disassembles GameClient.bin from the proprietary install tree, which is
    # never committed.  See tests/pf_preconditions.py.
    @GAME_INSTALL_TREE.skip_unless_present()
    def test_result_routes_by_identity_and_incoming_slot_not_old_quantity(self):
        pe = pefile.PE(
            str(ROOT.parent / "GameClient" / "GameClient.bin"), fast_load=True,
        )
        apply = _instructions(pe, *SPANS["response_apply"][:2])
        clear = _instructions(pe, *SPANS["identity_clear"][:2])

        self.assertEqual(apply[0x5A8F51], ("mov", "eax, dword ptr [edi + 0x18]"))
        self.assertEqual(apply[0x5A8F54], ("mov", "ecx, dword ptr [eax + 0x2c]"))
        self.assertEqual(apply[0x5A8F57], ("mov", "edx, dword ptr [eax + 0x28]"))
        self.assertEqual(apply[0x5A8F61], ("call", "0x59fb40"))
        self.assertEqual(apply[0x5A8F8E], ("mov", "ecx, dword ptr [edi + 0x18]"))
        self.assertEqual(apply[0x5A8F91], ("movsx", "edx, word ptr [ecx + 0x34]"))
        self.assertEqual(apply[0x5A8F9E], ("call", "0x5a1240"))

        # The route does not consume the incoming quantity at +0x36. The
        # identity-clear helper compares only the existing payload's qword
        # identity against its first two arguments before invoking the slot
        # payload's clear method.
        self.assertFalse(any("+ 0x36]" in operands for _, operands in apply.values()))
        self.assertEqual(clear[0x59FBB4], ("mov", "ecx, dword ptr [eax + 0x28]"))
        self.assertEqual(clear[0x59FBB7], ("mov", "eax, dword ptr [eax + 0x2c]"))
        self.assertEqual(clear[0x59FBC8], ("cmp", "ecx, dword ptr [esp + 0x1c]"))
        self.assertEqual(clear[0x59FBCE], ("cmp", "eax, dword ptr [esp + 0x20]"))
        self.assertFalse(any("+ 0x36]" in operands for _, operands in clear.values()))

    # Disassembles GameClient.bin from the proprietary install tree, which is
    # never committed.  See tests/pf_preconditions.py.
    @GAME_INSTALL_TREE.skip_unless_present()
    def test_slot_payload_is_replaced_with_a_complete_itemattr_clone(self):
        pe = pefile.PE(
            str(ROOT.parent / "GameClient" / "GameClient.bin"), fast_load=True,
        )
        assign = _instructions(pe, *SPANS["slot_assign"][:2])
        replace = _instructions(pe, *SPANS["slot_replace"][:2])
        ctor = _instructions(pe, *SPANS["item_ctor"][:2])
        clone = _instructions(pe, *SPANS["item_clone"][:2])

        # Destination acceptance in this helper is bounded by the configured
        # slot range and the presence of the slot widget; it does not compare
        # an old ItemAttr quantity or old ItemAttr slot.
        self.assertEqual(assign[0x5A124C], ("test", "eax, eax"))
        self.assertEqual(assign[0x5A125B], ("cmp", "eax, ecx"))
        self.assertEqual(assign[0x5A1272], ("call", "0x5f8400"))
        self.assertEqual(assign[0x5A128E], ("cmp", "dword ptr [esp + 0x10], edi"))
        self.assertEqual(assign[0x5A12D8], ("call", "0x5c15b0"))

        # With a non-null incoming payload, the slot setter releases its
        # current payload, creates a fresh ItemAttr, then invokes the incoming
        # ItemAttr vtable +0x24 clone slot.
        self.assertEqual(replace[0x5C15D4], ("cmp", "dword ptr [esp + 0x1c], 0"))
        self.assertEqual(replace[0x5C15E3], ("mov", "ecx, dword ptr [esi + 0x20]"))
        self.assertEqual(replace[0x5C15EA], ("call", "0x88d060"))
        self.assertEqual(replace[0x5C15EF], ("mov", "dword ptr [esi + 0x20], 0"))
        self.assertEqual(replace[0x5C1602], ("call", "0x46baa0"))
        self.assertEqual(replace[0x5C162E], ("mov", "edx, dword ptr [ecx]"))
        self.assertEqual(replace[0x5C1631], ("mov", "eax, dword ptr [edx + 0x24]"))
        self.assertEqual(ctor[0x46B440], ("mov", "dword ptr [esi], 0xf0ebb0"))

        vtable = _read_va(pe, *SPANS["item_vtable"][:2])
        self.assertEqual(struct.unpack_from("<I", vtable, 0x24)[0], 0x46BC50)

        # The exact ItemAttr clone copies the complete decoded identity,
        # template, quantity and slot, rather than deriving them from old UI
        # state.
        self.assertEqual(clone[0x46BC8E], ("mov", "eax, dword ptr [edi + 0x28]"))
        self.assertEqual(clone[0x46BC91], ("mov", "dword ptr [esi + 0x28], eax"))
        self.assertEqual(clone[0x46BC9A], ("mov", "edx, dword ptr [edi + 0x30]"))
        self.assertEqual(clone[0x46BCA0], ("mov", "ax, word ptr [edi + 0x36]"))
        self.assertEqual(clone[0x46BCA4], ("mov", "word ptr [esi + 0x36], ax"))
        self.assertEqual(clone[0x46BCA8], ("mov", "cx, word ptr [edi + 0x34]"))
        self.assertEqual(clone[0x46BCAC], ("mov", "word ptr [esi + 0x34], cx"))


if __name__ == "__main__":
    unittest.main()
