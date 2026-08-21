"""PF MOVE-AUTHORITY-001 — static byte-exact characterization of the client
TargetPosVital(0x2A90) movement-report producer and its wire schema, cross-checked
against the read-only server, opening `movement/local_player_movement_authority`
from not_started -> in_progress.

The local player's movement report (the frame the client emits as it walks / clicks
a destination) rides TargetPosVital. The coverage note said reported positions are
"accepted as given ... no corrective reposition is ever sent." This test pins, from
the read-only client binary, the transport a movement-authority model must ride:

  * IDENTITY: name string "TargetPosVital\\0" @0xF30818, a single registration site
    0xBEE380 storing the runtime id into id-slot 0x1081FE0; the id 0x2A90 is never a
    code immediate (runtime-assigned wall, same cohort as ItemOperateVitalReq); the
    id-slot is read by exactly one get-id stub 0x5E50A0.
  * VTABLE 0xF30230: +0x08 shared VitalData const 0x401B20, +0x10 get-id, +0x18
    serializer 0x5E50E0; ctor 0x5E5050 zero-inits four f32 (x,y,z,heading @+0x14..+0x20)
    and two u8 (moving,mask @+0x24,+0x25).
  * WIRE SCHEMA = four f32(tag 0x2A) then two u8(tag 0x0B) via serializer 0x5E50E0 and
    vec3 helper 0x5F3490 — byte-exact with the server parse_target_pos_vital; the
    authentic captured V139_MARKER1_TARGETPOS_PC decodes to MARKER1 (-10322,-755,671),
    heading 0, moving 1, mask 0, remain 0.
  * SERVER GAP: the server decodes the identical schema and stores last_target_pos,
    performing no local-player speed/distance/collision validation and sending no
    corrective reposition.

Report-only / additive: no server behavior is changed by this milestone. See
reports/PF_MOVE_AUTHORITY001_TARGETPOS_PRODUCER_STATIC_20260818.md. The lane stays
in_progress (characterized, not implemented; the authority model itself is uncaptured).
"""
from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path

import capstone
import pefile

# The proprietary client image cannot be in a fresh clone; every test that
# reads it is guarded below.  See tests/pf_preconditions.py.
from pf_preconditions import CLIENT_IMAGE

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT.parent / "GameClient" / "GameClient.local.bin"
BINARY_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
SERVER = ROOT / "current" / "pf_login_game_server_v141.py"

NAME_VA = 0xF30818
REGISTRATION = 0xBEE380
ID_SLOT = 0x1081FE0
GETID = 0x5E50A0
VTABLE = 0xF30230
CTOR = 0x5E5050
SERIALIZER = 0x5E50E0
VEC3_HELPER = 0x5F3490
FIELD_SER = 0x89A600
CLASS_ID = 0x2A90

# (start, end, sha256) byte-span pins — instruction-aligned, byte-identical.
SPANS = {
    "registration":     (0xBEE380, 0xBEE398, "2B99D6C3B73F63263E88245DA8BF3EA8B4FB724969B60C567EF8D7503CB0645D"),
    "vtable":           (0xF30230, 0xF30250, "359909F9070BA1F4A88560648668B2E299C40C08439BA15CD7DDAA99A97DB467"),
    "ctor":             (0x5E5050, 0x5E508D, "1A21C3EE1CDCC6E302C24E6C0C9CD28FB01DE06FFB1BAE8FAFFCA7F635E1F034"),
    "serializer":       (0x5E50E0, 0x5E512E, "E7807751909BF14F07A371D9ED6DD79F9EE6AA1F62D15AEB2A14B4225929E097"),
    "vec3_helper":      (0x5F3490, 0x5F34C7, "B5F5A2063FF9FC8F22830E3238A8B30387D781505ACE23D889C3A1500EA47454"),
}

CAP_NESTED = bytes.fromhex("2A004821C6" "2A00C03CC4" "2A00C02744" "2A00000000" "0B01" "0B00")


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


def _dword_immediate_hits(pe: pefile.PE, val: int) -> list[int]:
    start, blob = _text_section(pe)
    packed = struct.pack("<I", val)
    res, i = [], blob.find(packed)
    while i >= 0:
        if blob[i - 1] not in (0xE8, 0xE9):
            res.append(start + i)
        i = blob.find(packed, i + 1)
    return res


def _decode_targetpos(nested: bytes):
    p, vals = 0, []
    for _ in range(4):
        assert nested[p] == 0x2A
        vals.append(struct.unpack("<f", nested[p + 1:p + 5])[0]); p += 5
    assert nested[p] == 0x0B; moving = nested[p + 1]; p += 2
    assert nested[p] == 0x0B; mask = nested[p + 1]; p += 2
    return vals, moving, mask, len(nested) - p


class MoveAuthorityTargetPosStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only parse the PE when the client image exists; the capture-replay
        # and server tests below must still run without it.  See
        # tests/pf_preconditions.py.
        cls.pe = pefile.PE(str(BINARY), fast_load=True) if CLIENT_IMAGE.present else None

    @CLIENT_IMAGE.skip_unless_present()
    def test_binary_hash_is_the_pinned_client(self):
        self.assertEqual(hashlib.sha256(BINARY.read_bytes()).hexdigest().upper(), BINARY_SHA)

    @CLIENT_IMAGE.skip_unless_present()
    def test_spans_are_byte_identical(self):
        for label, (start, end, expected) in SPANS.items():
            data = _read_va(self.pe, start, end)
            self.assertEqual(len(data), end - start, label)
            self.assertEqual(hashlib.sha256(data).hexdigest().upper(), expected, label)

    @CLIENT_IMAGE.skip_unless_present()
    def test_identity_name_and_single_registration(self):
        self.assertEqual(_read_va(self.pe, NAME_VA, NAME_VA + 15), b"TargetPosVital\x00")
        # registration pushes the name string and stores the id into the id-slot
        self.assertEqual(
            _read_va(self.pe, REGISTRATION, REGISTRATION + 24).hex(),
            "681808f300e8f6dccaff8bc8e86fd9caff66a3e01f0801c3",
        )

    @CLIENT_IMAGE.skip_unless_present()
    def test_class_id_is_runtime_assigned(self):
        # 0x2A90 never appears as a code immediate (rel32 tails excluded)
        self.assertEqual(_dword_immediate_hits(self.pe, CLASS_ID), [])
        # id-slot read by exactly one get-id stub
        stub = bytes.fromhex("66a1") + struct.pack("<I", ID_SLOT)
        start, blob = _text_section(self.pe)
        sites, i = [], blob.find(stub)
        while i >= 0:
            sites.append(start + i); i = blob.find(stub, i + 1)
        self.assertEqual(sites, [GETID])
        self.assertEqual(_read_va(self.pe, GETID, GETID + 7).hex(), "66a1e01f0801c3")

    @CLIENT_IMAGE.skip_unless_present()
    def test_vtable_slots(self):
        slots = [struct.unpack("<I", _read_va(self.pe, VTABLE + k * 4, VTABLE + k * 4 + 4))[0] for k in range(8)]
        self.assertEqual(slots[2], 0x401B20)   # shared VitalData const cohort
        self.assertEqual(slots[4], GETID)      # +0x10 get-id
        self.assertEqual(slots[6], SERIALIZER)  # +0x18 serializer

    @CLIENT_IMAGE.skip_unless_present()
    def test_ctor_field_layout(self):
        ctor = _instructions(self.pe, CTOR, CTOR + 0x3D)
        self.assertEqual(_read_va(self.pe, 0x5E506C, 0x5E5072), bytes.fromhex("c7003002f300"))  # store vtable
        self.assertEqual(ctor[0x5E507C], ("movss", "dword ptr [eax + 0x14], xmm0"))  # x
        self.assertEqual(ctor[0x5E5077], ("movss", "dword ptr [eax + 0x18], xmm0"))  # y
        self.assertEqual(ctor[0x5E5072], ("movss", "dword ptr [eax + 0x1c], xmm0"))  # z
        self.assertEqual(ctor[0x5E5081], ("movss", "dword ptr [eax + 0x20], xmm0"))  # heading
        self.assertEqual(ctor[0x5E5086], ("mov", "byte ptr [eax + 0x24], cl"))       # moving
        self.assertEqual(ctor[0x5E5089], ("mov", "byte ptr [eax + 0x25], cl"))       # mask

    @CLIENT_IMAGE.skip_unless_present()
    def test_wire_schema_is_four_f32_then_two_u8(self):
        # field serializer signature: stdcall(tag, ptr, width) ret 0xC
        self.assertEqual(_read_va(self.pe, 0x89A63D, 0x89A640), bytes([0xC2, 0x0C, 0x00]))
        ser = _instructions(self.pe, SERIALIZER, SERIALIZER + 0x50)
        self.assertEqual(ser[0x5E50ED], ("lea", "eax, [esi + 0x14]"))
        self.assertEqual(ser[0x5E50F4], ("call", "0x5f3490"))                 # x,y,z via vec3
        self.assertEqual(_read_va(self.pe, 0x5E50FC, 0x5E50FE), bytes([0x6A, 0x04]))  # width 4
        self.assertEqual(ser[0x5E50FE], ("lea", "ecx, [esi + 0x20]"))         # heading ptr
        self.assertEqual(_read_va(self.pe, 0x5E5102, 0x5E5104), bytes([0x6A, 0x2A]))  # tag 0x2A
        self.assertEqual(ser[0x5E510D], ("lea", "edx, [esi + 0x24]"))         # moving ptr
        self.assertEqual(_read_va(self.pe, 0x5E5111, 0x5E5113), bytes([0x6A, 0x0B]))  # tag 0x0B
        self.assertEqual(ser[0x5E511C], ("add", "esi, 0x25"))                 # mask ptr
        self.assertEqual(_read_va(self.pe, 0x5E5120, 0x5E5122), bytes([0x6A, 0x0B]))  # tag 0x0B
        self.assertEqual(ser[0x5E512B], ("ret", "8"))
        # vec3 helper = three tag-0x2A width-4 fields at +0,+4,+8
        v3 = _instructions(self.pe, VEC3_HELPER, VEC3_HELPER + 0x40)
        self.assertEqual(_read_va(self.pe, 0x5F349D, 0x5F349F), bytes([0x6A, 0x2A]))
        self.assertEqual(v3[0x5F34A8], ("lea", "eax, [esi + 4]"))
        self.assertEqual(v3[0x5F34B7], ("add", "esi, 8"))

    @CLIENT_IMAGE.skip_unless_present()
    def test_producer_is_factory_constructed(self):
        # object is allocated (0x28 bytes) then constructed at exactly two sites;
        # get-id/serializer are vtable-dispatched (no direct E8 callers).
        self.assertEqual(_callers_of(self.pe, CTOR), [0x0044B7C4, 0x0044B842])
        self.assertEqual(_read_va(self.pe, 0x44B7AC, 0x44B7AE), bytes([0x6A, 0x28]))
        self.assertEqual(_callers_of(self.pe, SERIALIZER), [])
        self.assertEqual(_callers_of(self.pe, GETID), [])

    def test_captured_marker1_payload_matches_schema(self):
        (x, y, z, heading), moving, mask, remain = _decode_targetpos(CAP_NESTED)
        self.assertEqual((x, y, z), (-10322.0, -755.0, 671.0))
        self.assertEqual((heading, moving, mask, remain), (0.0, 1, 0, 0))
        # and the same bytes are what the server ships as the authentic capture
        flat = SERVER.read_text(encoding="utf-8").replace(" ", "").replace("\n", "").replace("'", "")
        self.assertIn(CAP_NESTED.hex().upper(), flat.upper())

    def test_server_decodes_but_has_no_local_movement_authority(self):
        src = SERVER.read_text(encoding="utf-8")
        self.assertIn("TARGET_POS_VITAL = 0x2A90", src)
        self.assertIn("def parse_target_pos_vital", src)
        self.assertIn("self.last_target_pos = (x, y, z, heading)", src)
        flat = src.replace(" ", "").lower()
        self.assertNotIn("corrective", flat)
        self.assertNotIn("reposition", flat)
        self.assertNotIn("movement_authority", flat)
        self.assertNotIn("def validate_movement", src)
        self.assertNotIn("def check_movement_speed", src)


if __name__ == "__main__":
    unittest.main()
