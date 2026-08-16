from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

import capstone
import pefile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.inventory import (  # noqa: E402
    HYPOTHESIZED_V111_SLOT2_BACKPACK,
    MERGED_V111_BACKPACK,
)


BINARIES = {
    "GameClient.bin": "C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD",
    "GameClient.local.bin": "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623",
}

SPANS = {
    "item_codec": (0x46BD30, 0x46BEA1, "B21137BDE28452C08F8FA6A2EDA18ACCF9C2D51B9B7D82A1B6997986FEBA86C1"),
    "bag_codec": (0x46F180, 0x46F3E9, "29E38267AB54C852E3F1338C2FB833E3B9D1A41903544A390489C264C09FA813"),
    "bag_insert": (0x46EC20, 0x46EDF0, "4C07FEB6722C81256E3ACECFD8A66BFC88B7B53DAE35AF210A7B3AF78D105F7D"),
    "identity_tree_insert": (0x5FC970, 0x5FCA61, "C97047A3030806658AC26A4BF9569114EBBD63FF3DA2B3C34D121C088B56B1A3"),
    "tree_successor": (0x46D2B0, 0x46D31C, "492E39AFB9FAF38F4F862ABCDAA6278740417A4B1FC1E56D61A6B992421D5CF9"),
}


def _read_va(pe: pefile.PE, start: int, end: int) -> bytes:
    return pe.get_data(start - pe.OPTIONAL_HEADER.ImageBase, end - start)


def _instructions(pe: pefile.PE, start: int, end: int):
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return {
        instruction.address: (instruction.mnemonic, instruction.op_str)
        for instruction in decoder.disasm(_read_va(pe, start, end), start)
    }


class ItemOrderStaticTests(unittest.TestCase):
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

    def test_item_identity_is_the_tree_key_and_writer_uses_successor_order(self):
        pe = pefile.PE(
            str(ROOT.parent / "GameClient" / "GameClient.bin"), fast_load=True,
        )
        item = _instructions(pe, *SPANS["item_codec"][:2])
        insert = _instructions(pe, *SPANS["bag_insert"][:2])
        compare = _instructions(pe, *SPANS["identity_tree_insert"][:2])
        codec = _instructions(pe, *SPANS["bag_codec"][:2])

        # ItemAttr's symmetric codec binds the qword at +0x28 to tag 0x32.
        self.assertEqual(item[0x46BD49], ("lea", "eax, [esi + 0x28]"))
        self.assertEqual(item[0x46BDD6], ("lea", "ebx, [esi + 0x28]"))

        # Backpack insertion copies ItemAttr identity low/high into the tree key.
        self.assertEqual(insert[0x46ED1E], ("mov", "ecx, dword ptr [esi + 0x28]"))
        self.assertEqual(insert[0x46ED21], ("mov", "edx, dword ptr [esi + 0x2c]"))
        self.assertEqual(insert[0x46ED48], ("call", "0x5fc970"))

        # The comparator orders high dword first, then unsigned low dword.
        self.assertEqual(compare[0x5FC991], ("mov", "ebp, dword ptr [ebx]"))
        self.assertEqual(compare[0x5FC993], ("mov", "edx, dword ptr [ebx + 4]"))
        self.assertEqual(compare[0x5FC996], ("cmp", "edx, dword ptr [eax + 0x14]"))
        self.assertEqual(compare[0x5FC99F], ("cmp", "ebp, dword ptr [eax + 0x10]"))
        self.assertEqual(compare[0x5FC9A2], ("jae", "0x5fc9ae"))

        # The write branch serializes the first tree and advances by its exact
        # in-order successor routine, rather than sorting by the ItemAttr slot.
        self.assertEqual(codec[0x46F1C5], ("movzx", "ecx, word ptr [edi + 0x44]"))
        self.assertEqual(codec[0x46F1E0], ("mov", "esi, dword ptr [edi + 0x28]"))
        self.assertEqual(codec[0x46F242], ("mov", "ecx, dword ptr [edx + 0x18]"))
        self.assertEqual(codec[0x46F256], ("call", "0x46d2b0"))

    def test_exact_post_merge_slot2_is_unoccupied_but_policy_remains_hypothesis(self):
        self.assertEqual(
            [(item.identity, item.quantity, item.slot) for item in MERGED_V111_BACKPACK.items],
            [(1, 2, 0), (2, 1, 1), (4, 1, 3)],
        )
        self.assertNotIn(2, {item.slot for item in MERGED_V111_BACKPACK.items})
        self.assertEqual(
            [item.identity for item in HYPOTHESIZED_V111_SLOT2_BACKPACK.items],
            [1, 2, 4],
        )
        self.assertEqual(
            [item.slot for item in HYPOTHESIZED_V111_SLOT2_BACKPACK.items],
            [2, 1, 3],
        )


if __name__ == "__main__":
    unittest.main()
