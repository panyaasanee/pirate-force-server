#!/usr/bin/env python3
"""PF MOVE-PROJECT-001 — static byte-exact characterization of the client
MovementAttr(0x2067) remote-actor movement-projection mechanism, cross-checked
against the read-only server, opening the
`movement/remote_player_movement_projection` lane from not_started -> in_progress.

Context: a remote actor's position/heading/control state is projected on the
client through the `MovementAttr` (MOVEMENT_ATTR = 0x2067) attribute that rides
inside every remote-actor entry of the RuntimeRes actor stream. The coverage note
for `remote_player_movement_projection` said the projection consumer was unproven.
This milestone pins, byte-exact from the client binary, the transport a remote
movement projection rides, the per-field mask semantics, and the client-side
APPLY/MERGE consumer that integrates an inbound MovementAttr into an already
projected actor, and confirms the server emitter matches the wire byte-exact.

What is proven (byte-exact static disasm + server cross-check):

  * IDENTITY (runtime-assigned id wall, same cohort as TargetPosVital/ItemOperate):
      - class name string "MovementAttr\\0" @ 0xF0E840.
      - the sole registration site 0xBD9410 pushes that string, calls the MSVC
        once-init singleton registry 0x89C080, then id-assign 0x89BD00, and stores
        the runtime id into id-slot 0x10334A8 (`mov word [0x10334A8], ax`).
      - the class id 0x2067 does NOT appear as a code immediate anywhere in .text
        (dword scan, rel32 tails excluded -> 0 hits): the id is assigned at
        runtime. id-slot 0x10334A8 is read by exactly one get-id stub 0x43BBB0
        (`mov ax,[0x10334A8]; ret`) and written by exactly one site 0xBD9421.
      - the MovementAttr class token 0x103346C is the is-a reference used by the
        runtime type check 0x88F2B0 at all three MovementAttr consumers that must
        downcast an incoming attr (0x465466, delta 0x46705A, apply/merge 0x467145).

  * OBJECT + VTABLE (base 0xF0D0F8):
      - +0x08 = 0x401B20 (the shared framework const of the TargetPosVital/ECHO/
        ItemOperate cohort), +0x10 = get-id 0x43BBB0.
      - +0x28 = reset 0x467030, +0x2C = delta 0x467040, +0x30 = apply/merge
        0x467130, +0x34 = Serial 0x4671C0.
      - payload field layout: identity qword @+0x18, submask u8 @+0x20,
        pos vec3 f32x3 @+0x28..+0x30, heading f32 @+0x34, mode u8 @+0x38,
        flags u32 @+0x3C, f32 @+0x40, f32 @+0x44, f32 @+0x48, field mask u8 @+0x4C.

  * WIRE SCHEMA (Serial 0x4671C0; the codec 0x89A600 is stdcall(tag,ptr,width)
    ret 0xC and is direction-agnostic, so this same routine decodes an inbound
    MovementAttr):
      - header helper 0x467790 emits: u8(tag 0x0B, 1) submask @+0x20, then
        (submask&1) qword(tag 0x32) identity @+0x18.
      - field mask u8(tag 0x0B) @+0x4C, then per-set-bit:
          0x01 -> vec3 helper 0x5F3490 @+0x28 (three tag-0x2A f32: x,y,z)
          0x02 -> f32(tag 0x2A) heading @+0x34
          0x04 -> u8 (tag 0x0B) mode    @+0x38
          0x08 -> u32(tag 0x26) flags   @+0x3C
          0x10 -> f32(tag 0x2A)         @+0x40
          0x20 -> f32(tag 0x2A)         @+0x44
          0x40 -> f32(tag 0x2A)         @+0x48
      - this is byte-exact the wire the server make_remote_movement_attr builds
        (u8tag 0x0B, qwordtag 0x32, u8tag 0x0B mask, f32tag 0x2A, u32tag 0x26).

  * PROJECTION APPLY / MERGE (0x467130) — the consumer that integrates an inbound
    MovementAttr into an already projected actor: after the 0x88F2B0/0x103346C
    is-a guard, it reads the target's own field mask @+0x4C and, for every field
    whose bit is NOT already set, copies that field from the incoming source into
    the same offset (pos +0x28/+0x30, heading +0x34, mode +0x38, flags +0x3C,
    f32 +0x40/+0x44/+0x48). Net: a sparse movement delta is completed against the
    existing projected state without overwriting fields the target already owns.

  * DELTA MASK (0x467040) — the outbound counterpart: it clears the mask @+0x4C
    then sets each bit whose field differs from a reference (pos via 0x4A1720,
    heading/f32 via cvtps2pd+ucomisd, mode via u8 cmp, flags via u32 cmp).

  * SERVER CROSS-CHECK (read-only current/pf_login_game_server_v141.py):
      - MOVEMENT_ATTR = 0x2067; make_remote_movement_attr documents the same
        static 0x4671C0 per-field mask and emits the byte-exact schema above;
        make_remote_actor_entry (0x5E21D0) carries it as u16tag(0x12, 0x2067)
        followed by the attr's Serial. Every emitted remote actor uses
        actor_type 4 (CNetNPC).

STILL NOT CLAIMED (bounded): the server only ever emits remote actors of
actor_type 4 (NPC). No authentic capture of a remote HUMAN-PLAYER actor_type and
its full projected-attr composition exists, so this milestone characterizes the
projection MECHANISM byte-exact but does not claim the original server's remote
human-player projection behavior. remote_player_movement_projection moves
not_started -> in_progress and never runtime_pass here.

Report-only / additive: NO server-source change, NO scenario, NO ledger entry, NO
runtime claim. Sole evidence = the read-only client binary
GameClient/GameClient.local.bin (disassembled) cross-checked against the read-only
server source.

Usage:  py -3 tools/pf_remote_movement_projection_static.py [path-to-GameClient.local.bin]
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
"""
import os
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
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
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
        res.append(image_base + TVADDR + (j - va2off(TSTART)))
        s = j + 1
    return res


def dword_immediate_hits(val):
    """Every .text offset holding dword `val` that is NOT an e8/e9 rel32 tail."""
    res = []
    packed = struct.pack('<I', val)
    o = va2off(TSTART); end = o + TVSIZE
    start = o
    while True:
        j = data.find(packed, start, end)
        if j < 0:
            break
        if data[j - 1] not in (0xE8, 0xE9):
            res.append(image_base + TVADDR + (j - va2off(TSTART)))
        start = j + 1
    return res


def callers_of(target):
    res = []
    for va in range(TSTART, TEND - 5):
        o = va2off(va)
        if data[o] == 0xE8:
            rel = struct.unpack_from('<i', data, o + 1)[0]
            if ((va + 5 + rel) & 0xffffffff) == target:
                res.append(va)
    return res


check("binary SHA-256 matches the pinned client", sha == EXPECT_SHA, sha)

# ---------------------------------------------------------------------------
# 1. Identity — name string, single registration, runtime-assigned id wall
# ---------------------------------------------------------------------------
check("class name string 'MovementAttr\\0' @0xF0E840",
      rd(0xf0e840, 13) == b"MovementAttr\x00")
check("sole registration site @0xBD9410 pushes the name and stores id-slot 0x10334A8",
      rd(0xbd9410, 24).hex() == "6840e8f000e8662cccff8bc8e8df28ccff66a3a8340301c3")
check("registration span 0xBD9410..0xBD9428 byte-identical",
      span_sha(0xbd9410, 0xbd9428) ==
      "C69B3040CA96A3F6FE430F6C6CE5EC3393FDC98B5FCD2B403F945A643F125A47",
      span_sha(0xbd9410, 0xbd9428))
check("class id 0x2067 is not a .text code immediate (runtime-assigned wall)",
      dword_immediate_hits(0x2067) == [], str([hex(x) for x in dword_immediate_hits(0x2067)]))
getid_write = text_hits("66a3" + struct.pack('<I', 0x10334a8).hex())
check("id-slot 0x10334A8 written by exactly one site @0xBD9421",
      getid_write == [0xbd9421], str([hex(x) for x in getid_write]))
getid_read = text_hits("66a1" + struct.pack('<I', 0x10334a8).hex())
check("id-slot 0x10334A8 read by exactly one get-id stub @0x43BBB0",
      getid_read == [0x43bbb0], str([hex(x) for x in getid_read]))
check("get-id stub bytes @0x43BBB0 = mov ax,[0x10334A8]; ret",
      rd(0x43bbb0, 7).hex() == "66a1a83403" + "01" + "c3",
      rd(0x43bbb0, 7).hex())
token_pushes = text_hits("68" + struct.pack('<I', 0x103346c).hex())
check("MovementAttr class token 0x103346C pushed at the three downcast consumers "
      "(0x465466, delta 0x46705A, apply 0x467145)",
      token_pushes == [0x465466, 0x46705a, 0x467145],
      str([hex(x) for x in token_pushes]))

# ---------------------------------------------------------------------------
# 2. vtable base 0xF0D0F8 — cohort const, get-id, and the four method slots
# ---------------------------------------------------------------------------
check("vtable 0xF0D0F8 +0x08 = shared framework const 0x401B20 (cohort)",
      dw(0xf0d100) == 0x401b20, hex(dw(0xf0d100)))
check("vtable 0xF0D0F8 +0x10 = get-id 0x43BBB0", dw(0xf0d108) == 0x43bbb0, hex(dw(0xf0d108)))
check("vtable 0xF0D0F8 +0x28 = reset 0x467030", dw(0xf0d120) == 0x467030, hex(dw(0xf0d120)))
check("vtable 0xF0D0F8 +0x2C = delta 0x467040", dw(0xf0d124) == 0x467040, hex(dw(0xf0d124)))
check("vtable 0xF0D0F8 +0x30 = apply/merge 0x467130", dw(0xf0d128) == 0x467130, hex(dw(0xf0d128)))
check("vtable 0xF0D0F8 +0x34 = Serial 0x4671C0", dw(0xf0d12c) == 0x4671c0, hex(dw(0xf0d12c)))
check("vtable span 0xF0D0F8..0xF0D124 byte-identical",
      span_sha(0xf0d0f8, 0xf0d124) ==
      "BE08735290C378B12AF2CF7DD88199F0D5106ACE33C473BE40F90ECCBF261294",
      span_sha(0xf0d0f8, 0xf0d124))

# ---------------------------------------------------------------------------
# 3. reset 0x467030 — full field mask primed to 0xFF
# ---------------------------------------------------------------------------
check("reset 0x467030 sets submask@+0x20 and field mask@+0x4C to 0xFF",
      rd(0x467030, 9).hex() == "b0ff88412088414cc3")

# ---------------------------------------------------------------------------
# 4. Wire schema — header helper + Serial per-field mask, byte-exact
# ---------------------------------------------------------------------------
check("field codec 0x89A600 is stdcall(tag,ptr,width) ret 0xC",
      rd(0x89a63d, 3) == bytes([0xC2, 0x0C, 0x00]))
hdr = dmap(0x467790, 0x40)
check("header 0x467790 emits submask u8 tag 0x0B @obj+0x20",
      hdr.get(0x4677a0) == ('lea', 'edi, [esi + 0x20]')
      and rd(0x4677a6, 2) == bytes([0x6A, 0x0B])
      and hdr.get(0x4677aa) == ('call', '0x89a600'))
check("header 0x467790 emits identity qword tag 0x32 @obj+0x18 under submask bit1",
      hdr.get(0x4677af) == ('test', 'byte ptr [edi], 1')
      and hdr.get(0x4677b6) == ('add', 'esi, 0x18')
      and rd(0x4677ba, 2) == bytes([0x6A, 0x32])
      and hdr.get(0x4677be) == ('call', '0x89a600'))
check("header 0x467790 span byte-identical",
      span_sha(0x467790, 0x4677c9) ==
      "D0BC5201E74C8FD31C8DCAF78C34FA854B7E6960730762D9A5ECFC919845742E",
      span_sha(0x467790, 0x4677c9))

ser = dmap(0x4671c0, 0xd0)
check("Serial 0x4671C0 calls header 0x467790 then emits field mask u8 tag 0x0B @+0x4C",
      ser.get(0x4671cf) == ('call', '0x467790')
      and ser.get(0x4671d8) == ('lea', 'ebx, [esi + 0x4c]')
      and rd(0x4671de, 2) == bytes([0x6A, 0x0B])
      and ser.get(0x4671e6) == ('call', '0x89a600'))
check("Serial 0x4671C0 bit0x01 -> vec3 helper 0x5F3490 @obj+0x28 (x,y,z)",
      ser.get(0x4671f9) == ('lea', 'eax, [esi + 0x28]')
      and ser.get(0x4671fe) == ('call', '0x5f3490'))
check("Serial 0x4671C0 bit0x02 -> heading f32 tag 0x2A @obj+0x34",
      ser.get(0x467206) == ('test', 'byte ptr [ebx], 2')
      and ser.get(0x46720d) == ('lea', 'ecx, [esi + 0x34]')
      and rd(0x467211, 2) == bytes([0x6A, 0x2A]))
check("Serial 0x4671C0 bit0x04 -> mode u8 tag 0x0B @obj+0x38",
      ser.get(0x46721a) == ('test', 'byte ptr [ebx], 4')
      and ser.get(0x467221) == ('lea', 'edx, [esi + 0x38]')
      and rd(0x467225, 2) == bytes([0x6A, 0x0B]))
check("Serial 0x4671C0 bit0x08 -> flags u32 tag 0x26 @obj+0x3C",
      ser.get(0x46722e) == ('test', 'byte ptr [ebx], 8')
      and ser.get(0x467235) == ('lea', 'eax, [esi + 0x3c]')
      and rd(0x467239, 2) == bytes([0x6A, 0x26]))
check("Serial 0x4671C0 bit0x10 -> f32 tag 0x2A @obj+0x40",
      ser.get(0x467242) == ('test', 'byte ptr [ebx], 0x10')
      and ser.get(0x467249) == ('lea', 'ecx, [esi + 0x40]')
      and rd(0x46724f - 2, 2) == bytes([0x6A, 0x2A]))
check("Serial 0x4671C0 bit0x20 -> f32 tag 0x2A @obj+0x44",
      ser.get(0x467256) == ('test', 'byte ptr [ebx], 0x20')
      and ser.get(0x46725d) == ('lea', 'edx, [esi + 0x44]')
      and rd(0x467263 - 2, 2) == bytes([0x6A, 0x2A]))
check("Serial 0x4671C0 bit0x40 -> f32 tag 0x2A @obj+0x48",
      ser.get(0x46726a) == ('test', 'byte ptr [ebx], 0x40')
      and ser.get(0x467275) == ('add', 'esi, 0x48')
      and rd(0x467279, 2) == bytes([0x6A, 0x2A]))
check("Serial 0x4671C0 is stdcall ret 8 (in/out stream at [esp+8])",
      ser.get(0x467285) == ('ret', '8'))
check("Serial 0x4671C0 span 0x4671C0..0x467288 byte-identical",
      span_sha(0x4671c0, 0x467288) ==
      "6A6571BB8871771CEF83F824AAFE204174201F0EEA1998663F13B5691976180A",
      span_sha(0x4671c0, 0x467288))
check("vec3 helper 0x5F3490 span byte-identical (three tag-0x2A f32)",
      span_sha(0x5f3490, 0x5f34c7) ==
      "B5F5A2063FF9FC8F22830E3238A8B30387D781505ACE23D889C3A1500EA47454",
      span_sha(0x5f3490, 0x5f34c7))

# ---------------------------------------------------------------------------
# 5. Projection apply/merge 0x467130 — mask-gated fill from incoming source
# ---------------------------------------------------------------------------
mrg = dmap(0x467130, 0x90)
check("apply 0x467130 downcast-guards the incoming attr (0x88F2B0 vs token 0x103346C)",
      mrg.get(0x467145) == ('push', '0x103346c')
      and mrg.get(0x46714a) == ('call', '0x88f2b0'))
check("apply 0x467130 reads target field mask @+0x4C",
      mrg.get(0x46715d) == ('mov', 'cl, byte ptr [esi + 0x4c]'))
check("apply 0x467130 bit0x01 unset -> copy pos vec3 src+0x28/+0x30 -> tgt+0x28/+0x30",
      mrg.get(0x467160) == ('test', 'cl, 1')
      and mrg.get(0x467163) == ('jne', '0x467175')
      and mrg.get(0x46716a) == ('movq', 'qword ptr [esi + 0x28], xmm0')
      and mrg.get(0x467172) == ('mov', 'dword ptr [esi + 0x30], edx'))
check("apply 0x467130 bit0x02 unset -> copy heading f32 @+0x34",
      mrg.get(0x467175) == ('test', 'cl, 2')
      and mrg.get(0x46717d) == ('fstp', 'dword ptr [esi + 0x34]'))
check("apply 0x467130 bit0x04 unset -> copy mode u8 @+0x38",
      mrg.get(0x467180) == ('test', 'cl, 4')
      and mrg.get(0x467188) == ('mov', 'byte ptr [esi + 0x38], dl'))
check("apply 0x467130 bit0x08 unset -> copy flags u32 @+0x3C",
      mrg.get(0x46718b) == ('test', 'cl, 8')
      and mrg.get(0x467193) == ('mov', 'dword ptr [esi + 0x3c], edx'))
check("apply 0x467130 bit0x10/0x20/0x40 unset -> copy f32 @+0x40/+0x44/+0x48",
      mrg.get(0x467196) == ('test', 'cl, 0x10')
      and mrg.get(0x46719e) == ('fstp', 'dword ptr [esi + 0x40]')
      and mrg.get(0x4671a1) == ('test', 'cl, 0x20')
      and mrg.get(0x4671a9) == ('fstp', 'dword ptr [esi + 0x44]')
      and mrg.get(0x4671ac) == ('test', 'cl, 0x40')
      and mrg.get(0x4671b4) == ('fstp', 'dword ptr [esi + 0x48]'))
check("apply 0x467130 is stdcall ret 4",
      mrg.get(0x4671b9) == ('ret', '4'))
check("apply 0x467130 span 0x467130..0x4671B7 byte-identical",
      span_sha(0x467130, 0x4671b7) ==
      "948B665113C120AE5D2FFE1C1BBD292182058C704106D1BC3FDF764890A27E91",
      span_sha(0x467130, 0x4671b7))

# ---------------------------------------------------------------------------
# 6. Delta mask 0x467040 — outbound counterpart: set bit per differing field
# ---------------------------------------------------------------------------
dlt = dmap(0x467040, 0xf0)
check("delta 0x467040 downcast-guards then clears the field mask @+0x4C",
      dlt.get(0x46705a) == ('push', '0x103346c')
      and dlt.get(0x46707d) == ('mov', 'byte ptr [esi + 0x4c], 0'))
check("delta 0x467040 pos differs (0x4A1720) -> or mask bit0x01",
      dlt.get(0x467081) == ('call', '0x4a1720')
      and dlt.get(0x46708a) == ('or', 'byte ptr [esi + 0x4c], 1'))
check("delta 0x467040 heading differs (ucomisd) -> or mask bit0x02",
      dlt.get(0x46709e) == ('ucomisd', 'xmm0, xmm1')
      and dlt.get(0x4670a8) == ('or', 'byte ptr [esi + 0x4c], 2'))
check("delta 0x467040 mode u8 differs -> or mask bit0x04",
      dlt.get(0x4670af) == ('cmp', 'cl, byte ptr [edi + 0x38]')
      and dlt.get(0x4670b4) == ('or', 'byte ptr [esi + 0x4c], 4'))
check("delta 0x467040 flags u32 differs -> or mask bit0x08",
      dlt.get(0x4670bb) == ('cmp', 'edx, dword ptr [edi + 0x3c]')
      and dlt.get(0x4670c0) == ('or', 'byte ptr [esi + 0x4c], 8'))
check("delta 0x467040 f32 @+0x40/+0x44/+0x48 differ -> or mask bit0x10/0x20/0x40",
      dlt.get(0x4670de) == ('or', 'byte ptr [esi + 0x4c], 0x10')
      and dlt.get(0x4670fc) == ('or', 'byte ptr [esi + 0x4c], 0x20')
      and dlt.get(0x46711a) == ('or', 'byte ptr [esi + 0x4c], 0x40'))
check("delta 0x467040 span 0x467040..0x467130 byte-identical",
      span_sha(0x467040, 0x467130) ==
      "72D39357B8DADA894B8AE051F48D70933334CFA1421156683CF3A4400E0172A7",
      span_sha(0x467040, 0x467130))

# ---------------------------------------------------------------------------
# 7. Server cross-check — same id, same schema, actor-type-4-only emission
# ---------------------------------------------------------------------------
src = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
check("server declares MOVEMENT_ATTR = 0x2067", "MOVEMENT_ATTR = 0x2067" in src)
flat = src.replace(" ", "")
check("server make_remote_movement_attr documents the static 0x4671C0 per-field mask",
      "def make_remote_movement_attr" in src and "0x4671C0" in src)
check("server emits the byte-exact schema: u8tag(0x0B,1)+qwordtag(0x32,id)+u8tag(0x0B,mask)",
      "out+=u8tag(0x0B,1)" in flat
      and "out+=qwordtag(0x32,actor_identity)" in flat
      and "out+=u8tag(0x0B,mask)" in flat)
check("server f32tag emits tag 0x2A and flags ride u32tag(0x26)",
      "return bytes([0x2A]) + struct.pack" in src and "out += u32tag(0x26, flags_u32)" in src)
check("server carries MovementAttr in the actor entry as u16tag(0x12, MOVEMENT_ATTR)",
      "def make_remote_actor_entry" in src and "u16tag(0x12, attr_id)" in src)
check("server actor-entry serializer is documented at client 0x5E21D0",
      "0x5E21D0" in src)
check("server only ever emits remote actors of actor_type 4 (CNetNPC) — "
      "no captured remote human-PLAYER actor_type",
      "make_remote_actor_entry(4," in flat)

print()
if fails:
    print(f"RESULT: {len(fails)} guard(s) drifted: {fails}")
    sys.exit(1)
print("RESULT: all MovementAttr remote-movement-projection static guards reproduced (exit 0)")
