"""PF MOVE-PROJECT-001 — static byte-exact characterization of the client
MovementAttr(0x2067) remote-actor movement-projection mechanism, cross-checked
against the read-only server, opening `movement/remote_player_movement_projection`
from not_started -> in_progress.

A remote actor's position/heading/control is projected on the client through the
`MovementAttr` (MOVEMENT_ATTR = 0x2067) attribute carried inside every remote-actor
entry of the RuntimeRes actor stream. This test pins, from the read-only client
binary, the transport a remote movement projection rides and the consumer that
applies it:

  * IDENTITY: name string "MovementAttr\\0" @0xF0E840; a single registration site
    0xBD9410 storing the runtime id into id-slot 0x10334A8; the id 0x2067 is never a
    code immediate (runtime-assigned wall, same cohort as TargetPosVital); the id-slot
    is read by exactly one get-id stub 0x43BBB0. The class token 0x103346C is the is-a
    reference used by the 0x88F2B0 type-check at all three downcast consumers.
  * VTABLE 0xF0D0F8: +0x08 shared framework const 0x401B20, +0x10 get-id 0x43BBB0,
    +0x28 reset 0x467030, +0x2C delta 0x467040, +0x30 apply/merge 0x467130,
    +0x34 Serial 0x4671C0.
  * WIRE SCHEMA (Serial 0x4671C0; codec 0x89A600 stdcall(tag,ptr,width) ret 0xC):
    header 0x467790 emits u8(0x0B,1) submask @+0x20 then qword(0x32) identity @+0x18;
    field mask u8(0x0B) @+0x4C, then per-set-bit pos vec3(0x5F3490)@+0x28,
    heading f32(0x2A)@+0x34, mode u8(0x0B)@+0x38, flags u32(0x26)@+0x3C, f32(0x2A)
    @+0x40/+0x44/+0x48 — byte-exact with the server make_remote_movement_attr.
  * PROJECTION APPLY (0x467130): after the 0x88F2B0/0x103346C is-a guard, it reads
    the target field mask @+0x4C and, for every field whose bit is NOT set, copies
    that field from the incoming source into the same offset — a sparse movement
    delta completed against the existing projected state.
  * DELTA MASK (0x467040): the outbound counterpart, setting a mask bit per field
    that differs from a reference.
  * SERVER: MOVEMENT_ATTR = 0x2067; make_remote_actor_entry (0x5E21D0) carries it as
    u16tag(0x12, 0x2067); every emitted remote actor uses actor_type 4 (CNetNPC).

Report-only / additive: no server behavior is changed. See
reports/PF_MOVE_PROJECT001_REMOTE_MOVEMENT_PROJECTION_STATIC_20260818.md. The lane
stays in_progress (mechanism characterized; no remote human-PLAYER actor_type is
captured, so the original server's player-projection behavior is not claimed).
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

NAME_VA = 0xF0E840
REGISTRATION = 0xBD9410
ID_SLOT = 0x10334A8
ID_STORE = 0xBD9421
GETID = 0x43BBB0
CLASS_TOKEN = 0x103346C
VTABLE = 0xF0D0F8
RESET = 0x467030
DELTA = 0x467040
APPLY = 0x467130
SERIAL = 0x4671C0
HEADER = 0x467790
VEC3_HELPER = 0x5F3490
FIELD_CODEC = 0x89A600
CLASS_ID = 0x2067
MOVEMENT_ATTR = 0x2067

# (start, end, sha256) byte-span pins — instruction-aligned, byte-identical.
SPANS = {
    "registration": (0xBD9410, 0xBD9428, "C69B3040CA96A3F6FE430F6C6CE5EC3393FDC98B5FCD2B403F945A643F125A47"),
    "vtable":       (0xF0D0F8, 0xF0D124, "BE08735290C378B12AF2CF7DD88199F0D5106ACE33C473BE40F90ECCBF261294"),
    "header":       (0x467790, 0x4677C9, "D0BC5201E74C8FD31C8DCAF78C34FA854B7E6960730762D9A5ECFC919845742E"),
    "serial":       (0x4671C0, 0x467288, "6A6571BB8871771CEF83F824AAFE204174201F0EEA1998663F13B5691976180A"),
    "apply_merge":  (0x467130, 0x4671B7, "948B665113C120AE5D2FFE1C1BBD292182058C704106D1BC3FDF764890A27E91"),
    "delta_mask":   (0x467040, 0x467130, "72D39357B8DADA894B8AE051F48D70933334CFA1421156683CF3A4400E0172A7"),
    "vec3_helper":  (0x5F3490, 0x5F34C7, "B5F5A2063FF9FC8F22830E3238A8B30387D781505ACE23D889C3A1500EA47454"),
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


def _dword_immediate_hits(pe: pefile.PE, val: int) -> list[int]:
    start, blob = _text_section(pe)
    packed = struct.pack("<I", val)
    res, i = [], blob.find(packed)
    while i >= 0:
        if blob[i - 1] not in (0xE8, 0xE9):
            res.append(start + i)
        i = blob.find(packed, i + 1)
    return res


def _pattern_sites(pe: pefile.PE, pattern_hex: str) -> list[int]:
    start, blob = _text_section(pe)
    pat = bytes.fromhex(pattern_hex)
    res, i = [], blob.find(pat)
    while i >= 0:
        res.append(start + i)
        i = blob.find(pat, i + 1)
    return res


def _server_movement_wire(actor_identity: int, x=0.0, y=0.0, z=0.0, heading=0.0,
                          mask=0xFF, mode_u8=0, flags_u32=0, p40=0.0, p44=0.0, p48=0.0) -> bytes:
    """Replica of the server make_remote_movement_attr tag layout (read-only, no import)."""
    def u8tag(tag, v): return bytes([tag, v & 0xFF])
    def qwordtag(tag, v): return bytes([tag]) + struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF)
    def u32tag(tag, v): return bytes([tag]) + struct.pack("<I", v & 0xFFFFFFFF)
    def f32tag(v): return bytes([0x2A]) + struct.pack("<f", float(v))
    out = bytearray()
    out += u8tag(0x0B, 1)
    out += qwordtag(0x32, actor_identity)
    out += u8tag(0x0B, mask)
    if mask & 0x01:
        out += f32tag(x) + f32tag(y) + f32tag(z)
    if mask & 0x02:
        out += f32tag(heading)
    if mask & 0x04:
        out += u8tag(0x0B, mode_u8)
    if mask & 0x08:
        out += u32tag(0x26, flags_u32)
    if mask & 0x10:
        out += f32tag(p40)
    if mask & 0x20:
        out += f32tag(p44)
    if mask & 0x40:
        out += f32tag(p48)
    return bytes(out)


def _decode_movement_wire(w: bytes):
    """Decode the MovementAttr wire under the client Serial 0x4671C0 schema."""
    p = 0
    assert w[p] == 0x0B and w[p + 1] == 1, "submask u8 tag 0x0B == 1"
    p += 2
    assert w[p] == 0x32, "identity qword tag 0x32"
    ident = struct.unpack_from("<Q", w, p + 1)[0]; p += 9
    assert w[p] == 0x0B, "field mask u8 tag 0x0B"
    mask = w[p + 1]; p += 2
    fields = {}
    if mask & 0x01:
        for k in ("x", "y", "z"):
            assert w[p] == 0x2A; fields[k] = struct.unpack_from("<f", w, p + 1)[0]; p += 5
    if mask & 0x02:
        assert w[p] == 0x2A; fields["heading"] = struct.unpack_from("<f", w, p + 1)[0]; p += 5
    if mask & 0x04:
        assert w[p] == 0x0B; fields["mode"] = w[p + 1]; p += 2
    if mask & 0x08:
        assert w[p] == 0x26; fields["flags"] = struct.unpack_from("<I", w, p + 1)[0]; p += 5
    for k, bit in (("p40", 0x10), ("p44", 0x20), ("p48", 0x40)):
        if mask & bit:
            assert w[p] == 0x2A; fields[k] = struct.unpack_from("<f", w, p + 1)[0]; p += 5
    return ident, mask, fields, len(w) - p


class RemoteMovementProjectionStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only parse the PE when the client image exists; the two server/wire
        # tests below must still run without it.  See tests/pf_preconditions.py.
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
        self.assertEqual(_read_va(self.pe, NAME_VA, NAME_VA + 13), b"MovementAttr\x00")
        self.assertEqual(
            _read_va(self.pe, REGISTRATION, REGISTRATION + 24).hex(),
            "6840e8f000e8662cccff8bc8e8df28ccff66a3a8340301c3",
        )

    @CLIENT_IMAGE.skip_unless_present()
    def test_class_id_is_runtime_assigned(self):
        # 0x2067 never appears as a code immediate (rel32 tails excluded)
        self.assertEqual(_dword_immediate_hits(self.pe, CLASS_ID), [])
        # id-slot written by exactly one site, read by exactly one get-id stub
        self.assertEqual(_pattern_sites(self.pe, "66a3" + struct.pack("<I", ID_SLOT).hex()), [ID_STORE])
        self.assertEqual(_pattern_sites(self.pe, "66a1" + struct.pack("<I", ID_SLOT).hex()), [GETID])
        self.assertEqual(_read_va(self.pe, GETID, GETID + 7).hex(), "66a1a8340301c3")

    @CLIENT_IMAGE.skip_unless_present()
    def test_class_token_used_by_three_downcast_consumers(self):
        # the MovementAttr is-a reference is pushed at exactly the three consumers
        # that must downcast an incoming attr before touching its fields.
        self.assertEqual(
            _pattern_sites(self.pe, "68" + struct.pack("<I", CLASS_TOKEN).hex()),
            [0x465466, DELTA + 0x1A, APPLY + 0x15],
        )

    @CLIENT_IMAGE.skip_unless_present()
    def test_vtable_slots(self):
        slot = lambda off: struct.unpack("<I", _read_va(self.pe, VTABLE + off, VTABLE + off + 4))[0]
        self.assertEqual(slot(0x08), 0x401B20)  # shared framework const cohort
        self.assertEqual(slot(0x10), GETID)     # get-id
        self.assertEqual(slot(0x28), RESET)     # reset
        self.assertEqual(slot(0x2C), DELTA)     # delta mask
        self.assertEqual(slot(0x30), APPLY)     # apply/merge
        self.assertEqual(slot(0x34), SERIAL)    # Serial

    @CLIENT_IMAGE.skip_unless_present()
    def test_reset_primes_full_mask(self):
        # mov al,0xff; mov [ecx+0x20],al; mov [ecx+0x4c],al; ret
        self.assertEqual(_read_va(self.pe, RESET, RESET + 9).hex(), "b0ff88412088414cc3")

    @CLIENT_IMAGE.skip_unless_present()
    def test_wire_schema_header_and_serial(self):
        # codec 0x89A600 signature: stdcall(tag, ptr, width) ret 0xC
        self.assertEqual(_read_va(self.pe, 0x89A63D, 0x89A640), bytes([0xC2, 0x0C, 0x00]))
        hdr = _instructions(self.pe, HEADER, HEADER + 0x40)
        self.assertEqual(hdr[0x4677A0], ("lea", "edi, [esi + 0x20]"))           # submask ptr
        self.assertEqual(_read_va(self.pe, 0x4677A6, 0x4677A8), bytes([0x6A, 0x0B]))  # tag 0x0B
        self.assertEqual(hdr[0x4677AF], ("test", "byte ptr [edi], 1"))          # submask bit1
        self.assertEqual(hdr[0x4677B6], ("add", "esi, 0x18"))                   # identity ptr
        self.assertEqual(_read_va(self.pe, 0x4677BA, 0x4677BC), bytes([0x6A, 0x32]))  # tag 0x32

        ser = _instructions(self.pe, SERIAL, SERIAL + 0xD0)
        self.assertEqual(ser[0x4671CF], ("call", "0x467790"))                   # header first
        self.assertEqual(ser[0x4671D8], ("lea", "ebx, [esi + 0x4c]"))           # field mask ptr
        self.assertEqual(_read_va(self.pe, 0x4671DE, 0x4671E0), bytes([0x6A, 0x0B]))  # tag 0x0B
        # bit0x01 pos vec3
        self.assertEqual(ser[0x4671F9], ("lea", "eax, [esi + 0x28]"))
        self.assertEqual(ser[0x4671FE], ("call", "0x5f3490"))
        # bit0x02 heading f32 tag 0x2A @+0x34
        self.assertEqual(ser[0x46720D], ("lea", "ecx, [esi + 0x34]"))
        self.assertEqual(_read_va(self.pe, 0x467211, 0x467213), bytes([0x6A, 0x2A]))
        # bit0x04 mode u8 tag 0x0B @+0x38
        self.assertEqual(ser[0x467221], ("lea", "edx, [esi + 0x38]"))
        self.assertEqual(_read_va(self.pe, 0x467225, 0x467227), bytes([0x6A, 0x0B]))
        # bit0x08 flags u32 tag 0x26 @+0x3C
        self.assertEqual(ser[0x467235], ("lea", "eax, [esi + 0x3c]"))
        self.assertEqual(_read_va(self.pe, 0x467239, 0x46723B), bytes([0x6A, 0x26]))
        # bit0x10/0x20/0x40 f32 tag 0x2A @+0x40/+0x44/+0x48
        self.assertEqual(ser[0x467249], ("lea", "ecx, [esi + 0x40]"))
        self.assertEqual(ser[0x46725D], ("lea", "edx, [esi + 0x44]"))
        self.assertEqual(ser[0x467275], ("add", "esi, 0x48"))
        self.assertEqual(ser[0x467285], ("ret", "8"))

    @CLIENT_IMAGE.skip_unless_present()
    def test_projection_apply_merge_is_mask_gated(self):
        m = _instructions(self.pe, APPLY, APPLY + 0x90)
        # downcast guard
        self.assertEqual(m[APPLY + 0x15], ("push", "0x103346c"))
        self.assertEqual(m[APPLY + 0x1A], ("call", "0x88f2b0"))
        # read target field mask
        self.assertEqual(m[0x46715D], ("mov", "cl, byte ptr [esi + 0x4c]"))
        # each field copied into the SAME offset when its mask bit is unset
        self.assertEqual(m[0x467160], ("test", "cl, 1"))
        self.assertEqual(m[0x46716A], ("movq", "qword ptr [esi + 0x28], xmm0"))
        self.assertEqual(m[0x467172], ("mov", "dword ptr [esi + 0x30], edx"))
        self.assertEqual(m[0x467175], ("test", "cl, 2"))
        self.assertEqual(m[0x46717D], ("fstp", "dword ptr [esi + 0x34]"))
        self.assertEqual(m[0x467180], ("test", "cl, 4"))
        self.assertEqual(m[0x467188], ("mov", "byte ptr [esi + 0x38], dl"))
        self.assertEqual(m[0x46718B], ("test", "cl, 8"))
        self.assertEqual(m[0x467193], ("mov", "dword ptr [esi + 0x3c], edx"))
        self.assertEqual(m[0x467196], ("test", "cl, 0x10"))
        self.assertEqual(m[0x46719E], ("fstp", "dword ptr [esi + 0x40]"))
        self.assertEqual(m[0x4671A1], ("test", "cl, 0x20"))
        self.assertEqual(m[0x4671A9], ("fstp", "dword ptr [esi + 0x44]"))
        self.assertEqual(m[0x4671AC], ("test", "cl, 0x40"))
        self.assertEqual(m[0x4671B4], ("fstp", "dword ptr [esi + 0x48]"))
        self.assertEqual(m[0x4671B9], ("ret", "4"))

    @CLIENT_IMAGE.skip_unless_present()
    def test_delta_mask_sets_bit_per_differing_field(self):
        d = _instructions(self.pe, DELTA, DELTA + 0xF0)
        self.assertEqual(d[DELTA + 0x1A], ("push", "0x103346c"))
        self.assertEqual(d[0x46707D], ("mov", "byte ptr [esi + 0x4c], 0"))
        self.assertEqual(d[0x467081], ("call", "0x4a1720"))                 # pos compare
        self.assertEqual(d[0x46708A], ("or", "byte ptr [esi + 0x4c], 1"))
        self.assertEqual(d[0x46709E], ("ucomisd", "xmm0, xmm1"))            # heading compare
        self.assertEqual(d[0x4670A8], ("or", "byte ptr [esi + 0x4c], 2"))
        self.assertEqual(d[0x4670AF], ("cmp", "cl, byte ptr [edi + 0x38]"))  # mode u8
        self.assertEqual(d[0x4670B4], ("or", "byte ptr [esi + 0x4c], 4"))
        self.assertEqual(d[0x4670BB], ("cmp", "edx, dword ptr [edi + 0x3c]"))  # flags u32
        self.assertEqual(d[0x4670C0], ("or", "byte ptr [esi + 0x4c], 8"))
        self.assertEqual(d[0x4670DE], ("or", "byte ptr [esi + 0x4c], 0x10"))
        self.assertEqual(d[0x4670FC], ("or", "byte ptr [esi + 0x4c], 0x20"))
        self.assertEqual(d[0x46711A], ("or", "byte ptr [esi + 0x4c], 0x40"))

    def test_server_wire_matches_client_schema_byte_exact(self):
        # A position+heading delta (mask 0x03) built the server way decodes under
        # the client Serial 0x4671C0 schema to the exact values.
        w = _server_movement_wire(0x1122334455667788, 12.0, -34.0, 931.0, 1.5, mask=0x03)
        ident, mask, fields, remain = _decode_movement_wire(w)
        self.assertEqual(ident, 0x1122334455667788)
        self.assertEqual(mask, 0x03)
        self.assertEqual((fields["x"], fields["y"], fields["z"], fields["heading"]),
                         (12.0, -34.0, 931.0, 1.5))
        self.assertEqual(remain, 0)
        # A full-mask (0xFF) snapshot exercises every field offset in order.
        wf = _server_movement_wire(1, mask=0xFF, mode_u8=7, flags_u32=0xAABBCCDD,
                                   p40=1.0, p44=2.0, p48=3.0)
        _, mf, ff, rem = _decode_movement_wire(wf)
        self.assertEqual(mf, 0xFF)
        self.assertEqual(ff["mode"], 7)
        self.assertEqual(ff["flags"], 0xAABBCCDD)
        self.assertEqual((ff["p40"], ff["p44"], ff["p48"]), (1.0, 2.0, 3.0))
        self.assertEqual(rem, 0)

    def test_server_declares_and_carries_movement_attr(self):
        src = SERVER.read_text(encoding="utf-8")
        self.assertIn("MOVEMENT_ATTR = 0x2067", src)
        self.assertIn("def make_remote_movement_attr", src)
        self.assertIn("0x4671C0", src)                        # documents the static serializer
        self.assertIn("def make_remote_actor_entry", src)
        self.assertIn("u16tag(0x12, attr_id)", src)
        self.assertIn("0x5E21D0", src)                        # actor-entry serializer address
        # every emitted remote actor uses actor_type 4 (CNetNPC); no remote-player type
        self.assertIn("make_remote_actor_entry(4,", src.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
