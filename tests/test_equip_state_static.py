from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import unittest

import capstone
import pefile


ROOT = Path(__file__).resolve().parents[1]

BINARIES = {
    "GameClient.bin": "C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD",
    "GameClient.local.bin": "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623",
}

SPANS = {
    "equipped_registration": (
        0xBD9690,
        0xBD96A8,
        "D3BE48FDE64E0D28E7A8E3260CEBF4339970D6C503BF2EA7589EA28B26B8F15A",
    ),
    "equipped_type_registration": (
        0xBD9770,
        0xBD97A7,
        "0C433A34D012331DFA6E397837D9440FDAEC9327EA2C834F707EEE3E9E1B0560",
    ),
    "equipped_pool_factory": (
        0x46A210,
        0x46A32F,
        "FCC0401C2F27F7698B0EFC7BAB5BC4FB7BB2514E47AA88AFE024E8F188EDCFD8",
    ),
    "equipped_vtable": (
        0xF0EA30,
        0xF0EA78,
        "1DE9B7944B65EB1E6C4F6CC318EF6B68D88551E58C64192F3886990D61751184",
    ),
    "itembag_codec": (
        0x46F180,
        0x46F3E9,
        "29E38267AB54C852E3F1338C2FB833E3B9D1A41903544A390489C264C09FA813",
    ),
    "collection_registration": (
        0xBD97B0,
        0xBD97C8,
        "877E8A2A02E08B046AA5737003E4549A211AC3CC22A7939EF84B27DC86B36568",
    ),
    "collection_type_registration": (
        0xBD97F0,
        0xBD9827,
        "9CFA6AC21E95B97422964E50713AA0956927E2354D553BADE4877EB58C668614",
    ),
    "collection_ctor": (
        0x46AEA0,
        0x46AEB6,
        "35D6C2578D944AD1C538C13D65297A4947CAD4A77C0639359DF78F4940BF025F",
    ),
    "collection_vtable": (
        0xF0EAF8,
        0xF0EB40,
        "05C9297DB41EA3C3082EC3745E3F623C1F46D354CFE2BAC71F846AE2EBEF0570",
    ),
    "collection_codec": (
        0x471830,
        0x471910,
        "0756593899A697399B4CBDC8F03F32928F1829C20EBCC9CBCD34B8254C0A0692",
    ),
    "itembag_clone": (
        0x46EFF0,
        0x46F12D,
        "06DF2A41B6A5201A26128AB7337B546C58B656DF617FE0A0758BA30EDABE27FC",
    ),
    "plain_itembag_factory": (
        0x46F4D0,
        0x46F5DB,
        "B9308ABC49969DED9194D369823DE1F29207CA8ADDCFE22F838A4B3D1EA45885",
    ),
    "item_operate_result_codec": (
        0x5EDA20,
        0x5EDC31,
        "B5F6A1586A810C0A98CEB7C925A0D4AFA10CFF41DB661EB0947B8918F3A11D54",
    ),
    "item_operate_result_handler": (
        0x5EF5E0,
        0x5EF61A,
        "436B856FC41EB2D1F90B103BDDABA29B621E21DF99633C0F181A609224A9FF1D",
    ),
    "generic_attr_import": (
        0x463870,
        0x4638F3,
        "2F607A9A1E3E36A22D5420DF5871D8CCE89349A41E6C2112FE94C4FB5ADD601C",
    ),
    "startgame_consumer": (
        0x5DDAE0,
        0x5DDCFF,
        "3F958430ED9EFE41BA760FEE8AF192FF7EC802B4E3E31A32EC8C34AA393FBCB8",
    ),
    "equipment_ui_lookup": (
        0x5832C7,
        0x583455,
        "3601887A7BA7E2EA8983ABFB363907EF236DCB497021CC64428F79367565046F",
    ),
}

EQUIPPED_NAME = 0xF0EAE4
EQUIPPED_ID_GLOBAL = 0x1033544
COLLECTION_NAME = 0xF0EB40
COLLECTION_ID_GLOBAL = 0x1033570


def _read_va(pe: pefile.PE, start: int, end: int) -> bytes:
    return pe.get_data(start - pe.OPTIONAL_HEADER.ImageBase, end - start)


def _instructions(pe: pefile.PE, start: int, end: int):
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return {
        instruction.address: (instruction.mnemonic, instruction.op_str)
        for instruction in decoder.disasm(_read_va(pe, start, end), start)
    }


def _weighted_name_hash(name: bytes) -> int:
    return sum(
        (index + 1) * (value if value < 0x80 else value - 0x100)
        for index, value in enumerate(name)
    ) & 0xFFFF


def _raw_va_refs(pe: pefile.PE, value: int) -> list[int]:
    expected = struct.pack("<I", value)
    result: list[int] = []
    for section in pe.sections:
        data = section.get_data()
        offset = 0
        while True:
            offset = data.find(expected, offset)
            if offset < 0:
                break
            result.append(
                pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress + offset,
            )
            offset += 1
    return result


class EquipStateStaticTests(unittest.TestCase):
    def test_exact_original_and_local_spans_are_identical(self):
        observed = {}
        for filename, whole_hash in BINARIES.items():
            path = ROOT.parent / "GameClient" / filename
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest().upper(), whole_hash,
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

    def test_registered_equipped_bag_has_only_the_shared_itembag_shape(self):
        pe = pefile.PE(
            str(ROOT.parent / "GameClient" / "GameClient.bin"), fast_load=True,
        )
        registration = _instructions(pe, *SPANS["equipped_registration"][:2])
        factory = _instructions(pe, *SPANS["equipped_pool_factory"][:2])
        codec = _instructions(pe, *SPANS["itembag_codec"][:2])

        name = _read_va(pe, EQUIPPED_NAME, EQUIPPED_NAME + 21).split(b"\0", 1)[0]
        self.assertEqual(name, b"ItemBagAttr_Equiped")
        self.assertEqual(_weighted_name_hash(name), 0x4B83)
        self.assertEqual(registration[0xBD9690], ("push", "0xf0eae4"))
        self.assertEqual(registration[0xBD9695], ("call", "0x89c080"))
        self.assertEqual(registration[0xBD969C], ("call", "0x89bd00"))
        self.assertEqual(
            registration[0xBD96A1], ("mov", "word ptr [0x1033544], ax"),
        )

        vtable = struct.unpack(
            "<18I", _read_va(pe, *SPANS["equipped_vtable"][:2]),
        )
        self.assertEqual(vtable[4], 0x469E80)
        self.assertEqual(vtable[5], 0x46A360)
        self.assertEqual(vtable[9], 0x46EFF0)
        self.assertEqual(vtable[13], 0x46F180)
        self.assertEqual(factory[0x46A25C], ("push", "0x68"))
        self.assertEqual(factory[0x46A27A], ("call", "0x46f3f0"))
        self.assertEqual(factory[0x46A27F], ("mov", "dword ptr [edi], 0xf0ea30"))

        # The shared ItemBag codec writes/reads an ItemAttr collection followed
        # by a qword-identity collection.  It carries no class-specific equip
        # slot or visual-state field outside the ItemAttr records themselves.
        self.assertEqual(codec[0x46F1B3], ("call", "0x467790"))
        self.assertEqual(codec[0x46F1D6], ("call", "0x89a600"))
        self.assertEqual(codec[0x46F24B], ("mov", "eax, dword ptr [eax + 0x34]"))
        self.assertEqual(codec[0x46F27C], ("call", "0x89a600"))
        self.assertEqual(codec[0x46F2D6], ("call", "0x89a600"))
        self.assertEqual(codec[0x46F2FD], ("call", "0x89a640"))
        self.assertEqual(codec[0x46F388], ("call", "0x89a640"))

        # Bounded immediate/xref inventory: the registered ID global is only
        # written by registration and read by the getter, while the class name
        # is referenced only by registration.  Indirect framework use remains
        # possible and is deliberately not excluded by this check.
        self.assertEqual(_raw_va_refs(pe, EQUIPPED_NAME), [0xBD9691])
        self.assertEqual(
            _raw_va_refs(pe, EQUIPPED_ID_GLOBAL), [0x469E82, 0xBD96A3],
        )

    def test_startgame_imports_all_attrs_but_has_no_equipped_specific_lookup(self):
        pe = pefile.PE(
            str(ROOT.parent / "GameClient" / "GameClient.bin"), fast_load=True,
        )
        start = _instructions(pe, *SPANS["startgame_consumer"][:2])
        generic = _instructions(pe, *SPANS["generic_attr_import"][:2])
        start_bytes = _read_va(pe, *SPANS["startgame_consumer"][:2])

        # The whole incoming attr aggregate is imported first.  The helper
        # iterates source nodes and inserts/clones each through 0x463720.
        self.assertEqual(start[0x5DDB57], ("mov", "ecx, dword ptr [ebp + 0x1a0]"))
        self.assertEqual(start[0x5DDB5E], ("call", "0x463870"))
        self.assertEqual(generic[0x4638C9], ("add", "ebp, 0x10"))
        self.assertEqual(generic[0x4638CD], ("call", "0x463720"))

        # Class-specific StartGame handling then looks up exactly BackpackAttr,
        # ActorAttr, AvatarAttr and MovementAttr.  Neither equipped-bag ID is a
        # direct lookup in this handler.
        self.assertEqual(
            start[0x5DDB63], ("movzx", "ecx, word ptr [0x103353c]"),
        )
        self.assertEqual(
            start[0x5DDB81], ("movzx", "edx, word ptr [0x10334a0]"),
        )
        self.assertEqual(
            start[0x5DDBA9], ("movzx", "eax, word ptr [0x1033468]"),
        )
        self.assertEqual(
            start[0x5DDBCC], ("movzx", "ecx, word ptr [0x10334a8]"),
        )
        self.assertNotIn(struct.pack("<I", EQUIPPED_ID_GLOBAL), start_bytes)
        self.assertNotIn(struct.pack("<I", COLLECTION_ID_GLOBAL), start_bytes)

    def test_character_equipment_ui_requests_collection_bag_not_equipped_bag(self):
        pe = pefile.PE(
            str(ROOT.parent / "GameClient" / "GameClient.bin"), fast_load=True,
        )
        registration = _instructions(pe, *SPANS["collection_registration"][:2])
        ctor = _instructions(pe, *SPANS["collection_ctor"][:2])
        codec = _instructions(pe, *SPANS["collection_codec"][:2])
        ui = _instructions(pe, *SPANS["equipment_ui_lookup"][:2])
        ui_bytes = _read_va(pe, *SPANS["equipment_ui_lookup"][:2])

        name = _read_va(pe, COLLECTION_NAME, COLLECTION_NAME + 18).split(b"\0", 1)[0]
        self.assertEqual(name, b"CollectionBagAttr")
        self.assertEqual(_weighted_name_hash(name), 0x3CD0)
        self.assertEqual(registration[0xBD97B0], ("push", "0xf0eb40"))
        self.assertEqual(
            registration[0xBD97C1], ("mov", "word ptr [0x1033570], ax"),
        )
        self.assertEqual(ctor[0x46AEA3], ("call", "0x471970"))
        self.assertEqual(ctor[0x46AEA8], ("mov", "dword ptr [esi], 0xf0eaf8"))
        self.assertEqual(ctor[0x46AEAE], ("mov", "byte ptr [esi + 0x10], 4"))

        vtable = struct.unpack(
            "<18I", _read_va(pe, *SPANS["collection_vtable"][:2]),
        )
        self.assertEqual(vtable[4], 0x46AEC0)
        self.assertEqual(vtable[5], 0x46B160)
        self.assertEqual(vtable[9], 0x46EFF0)
        self.assertEqual(vtable[13], 0x471830)
        self.assertEqual(codec[0x471842], ("call", "0x46f180"))
        self.assertEqual(codec[0x47184F], ("add", "edi, 0x8a"))
        self.assertEqual(codec[0x471858], ("call", "0x89a600"))
        self.assertEqual(codec[0x471866], ("lea", "eax, [edi + 0x8a]"))
        self.assertEqual(codec[0x47186F], ("call", "0x89a640"))

        # The Character equipment refresh resolves the exact CollectionBagAttr
        # name from the current actor attr manager, type-checks it, then maps
        # each non-FF ItemAttr +0x39 byte to an identity.  It does not request
        # ItemBagAttr_Equiped.
        self.assertEqual(ui[0x5832EA], ("mov", "ecx, dword ptr [0x1032ec4]"))
        self.assertEqual(ui[0x5832F0], ("push", "0xf0eb40"))
        self.assertEqual(ui[0x5832F5], ("add", "ecx, 0x130"))
        self.assertEqual(ui[0x583306], ("call", "0x5f8de0"))
        self.assertEqual(ui[0x58331E], ("call", "0x46aed0"))
        self.assertEqual(ui[0x5833AF], ("mov", "dl, byte ptr [ecx + 0x39]"))
        self.assertEqual(ui[0x5833F6], ("mov", "cl, byte ptr [eax + 0x39]"))
        self.assertEqual(ui[0x5833FE], ("shl", "edx, cl"))
        self.assertNotIn(struct.pack("<I", EQUIPPED_NAME), ui_bytes)

    def test_item_operate_result_optional_bag_is_plain_not_collection(self):
        pe = pefile.PE(
            str(ROOT.parent / "GameClient" / "GameClient.bin"), fast_load=True,
        )
        result_codec = _instructions(pe, *SPANS["item_operate_result_codec"][:2])
        plain_factory = _instructions(pe, *SPANS["plain_itembag_factory"][:2])
        handler = _instructions(pe, *SPANS["item_operate_result_handler"][:2])

        # On read, the optional result bag is always allocated as the 0x68-byte
        # plain ItemBag base through 0x46F4D0/0x46F3F0.  This does not allocate
        # the 0x90-byte CollectionBagAttr or install its vtable.
        self.assertEqual(result_codec[0x5EDB56], ("push", "ebp"))
        self.assertEqual(result_codec[0x5EDB61], ("call", "0x46f4d0"))
        self.assertEqual(plain_factory[0x46F51C], ("push", "0x68"))
        self.assertEqual(plain_factory[0x46F534], ("call", "0x46f3f0"))
        factory_bytes = _read_va(pe, *SPANS["plain_itembag_factory"][:2])
        self.assertNotIn(struct.pack("<I", 0xF0EAF8), factory_bytes)

        # The consumer passes that optional bag into the ordinary ItemOperate
        # response-apply path.  It is not a hidden CollectionBagAttr update.
        self.assertEqual(handler[0x5EF5E0], ("movzx", "eax, byte ptr [ecx + 0x30]"))
        self.assertEqual(handler[0x5EF5FB], ("call", "0x5a8a00"))

    def test_current_foundation_has_no_equipped_container_builder(self):
        paths = [ROOT / "current" / "pf_login_game_server_v141.py"]
        paths.extend(sorted((ROOT / "src" / "pirateforce_foundation").glob("*.py")))
        forbidden = (
            "ItemBagAttr_Equiped",
            "CollectionBagAttr",
            "0x3CD0",
            "0x4B83",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text, f"unexpected equipped builder in {path}")


if __name__ == "__main__":
    unittest.main()
