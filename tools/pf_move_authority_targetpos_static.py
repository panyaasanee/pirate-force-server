#!/usr/bin/env python3
"""PF MOVE-AUTHORITY-001 — static byte-exact characterization of the client
TargetPosVital(0x2A90) movement-report producer and its wire schema, cross-checked
against the read-only server, opening the `movement/local_player_movement_authority`
lane from not_started -> in_progress.

Context: the local player's movement report (the frame the client emits when it
walks / clicks a destination) rides `TargetPosVital`. The coverage note for
`local_player_movement_authority` said: "Reported positions are accepted as given.
No speed, distance, collision, terrain, or line-of-sight validation exists, and no
corrective reposition is ever sent." This milestone pins, byte-exact from the
client binary, the transport a movement-authority model must ride, and confirms
against the server source that the acceptance-as-given gap is real.

What is proven (byte-exact static disasm + server cross-check):

  * IDENTITY (runtime-assigned id wall, same cohort as ItemOperateVitalReq/ECHO):
      - RTTI/registration name string "TargetPosVital\\0" @ 0xF30818.
      - the sole registration site 0xBEE380 pushes that string, calls the MSVC
        once-init singleton registry 0x89C080, then id-assign 0x89BD00, and stores
        the runtime id into id-slot 0x1081FE0 (`mov word [0x1081FE0], ax`).
      - the class id 0x2A90 does NOT appear as a code immediate anywhere in .text
        (dword scan, rel32 displacements excluded -> 0 hits): the id is assigned
        at runtime, never a code constant. id-slot 0x1081FE0 is read by exactly one
        get-id stub 0x5E50A0 (`mov ax,[0x1081FE0]; ret`).

  * OBJECT + VTABLE:
      - vtable base 0xF30230; +0x08 = 0x401B20 (the shared VitalData framework const
        of the ECHO/TELEPORT/ItemOperate cohort), +0x10 = get-id 0x5E50A0,
        +0x18 = serializer 0x5E50E0.
      - constructor 0x5E5050 stores the vtable 0xF30230 and zero-inits the payload
        fields: four f32 at obj+0x14/+0x18/+0x1C/+0x20 (x, y, z, heading) and two
        u8 at obj+0x24/+0x25 (moving, mask).

  * WIRE SCHEMA (byte-exact, matches server parse_target_pos_vital):
      - serializer 0x5E50E0 emits, in order:
          vec3 helper 0x5F3490 on obj+0x14 -> x,y,z each (tag 0x2A, width 4 f32),
          0x89A600(tag 0x2A, obj+0x20, width 4)  -> heading  (f32),
          0x89A600(tag 0x0B, obj+0x24, width 1)  -> moving   (u8),
          0x89A600(tag 0x0B, obj+0x25, width 1)  -> mask     (u8).
        Net wire = four f32(tag 0x2A) then two u8(tag 0x0B). The field serializer
        0x89A600 is stdcall (tag, ptr, width), ret 0xC.
      - the authentic captured payload V139_MARKER1_TARGETPOS_PC in the server
        source decodes byte-exact under this schema to MARKER1 (x,y,z)=
        (-10322,-755,671), heading 0, moving 1, mask 0, remain 0.

  * SERVER COVERAGE GAP (read-only cross-check of current/pf_login_game_server_v141.py):
      - the server decodes the identical schema (parse_target_pos_vital / u8/f32 tags)
        and, on inbound TARGET_POS_VITAL, stores self.last_target_pos and continues:
        it performs NO speed / distance / collision / line-of-sight validation of the
        LOCAL player and sends NO corrective reposition. The only movement_speed in
        the file is the NPC walk-speed constant (V73_WALK_SPEED) fed to NPCAttr, not a
        local-player authority check.

STILL NOT CLAIMED (bounded): the original server's authority MODEL itself
(accept threshold, correction packet, cadence) is uncaptured, so this milestone is
characterization only. local_player_movement_authority stays in_progress, never
runtime_pass: no authority behavior is implemented and no validation event is
captured.

Report-only / additive: NO server-source change, NO scenario, NO ledger entry, NO
runtime claim. Sole evidence = the read-only client binary GameClient/GameClient.local.bin
(disassembled) cross-checked against the read-only server source.

Usage:  py -3 tools/pf_move_authority_targetpos_static.py [path-to-GameClient.local.bin]
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
check("class name string 'TargetPosVital\\0' @0xF30818",
      rd(0xf30818, 15) == b"TargetPosVital\x00")
check("sole registration site @0xBEE380 pushes the name and stores id-slot 0x1081FE0",
      rd(0xbee380, 24).hex() == "681808f300e8f6dccaff8bc8e86fd9caff66a3e01f0801c3")
check("registration span 0xBEE380..0xBEE398 byte-identical",
      span_sha(0xbee380, 0xbee398) ==
      "2B99D6C3B73F63263E88245DA8BF3EA8B4FB724969B60C567EF8D7503CB0645D",
      span_sha(0xbee380, 0xbee398))
check("class id 0x2A90 is not a .text code immediate (runtime-assigned wall)",
      dword_immediate_hits(0x2A90) == [], str([hex(x) for x in dword_immediate_hits(0x2A90)]))
getid_sites = []
stub = bytes.fromhex("66a1") + struct.pack('<I', 0x1081fe0)
o = va2off(TSTART); end = o + TVSIZE; start = o
while True:
    j = data.find(stub, start, end)
    if j < 0:
        break
    getid_sites.append(image_base + TVADDR + (j - va2off(TSTART))); start = j + 1
check("id-slot 0x1081FE0 read by exactly one get-id stub @0x5E50A0",
      getid_sites == [0x5e50a0], str([hex(x) for x in getid_sites]))
check("get-id stub bytes @0x5E50A0 = mov ax,[0x1081FE0]; ret",
      rd(0x5e50a0, 7).hex() == "66a1e01f0801c3")

# ---------------------------------------------------------------------------
# 2. vtable + constructor field layout
# ---------------------------------------------------------------------------
vt = [struct.unpack('<I', rd(0xf30230 + k * 4, 4))[0] for k in range(8)]
check("vtable 0xF30230 +0x08 = shared VitalData const 0x401B20 (ECHO/ItemOperate cohort)",
      vt[2] == 0x401b20, hex(vt[2]))
check("vtable 0xF30230 +0x10 = get-id 0x5E50A0", vt[4] == 0x5e50a0, hex(vt[4]))
check("vtable 0xF30230 +0x18 = serializer 0x5E50E0", vt[6] == 0x5e50e0, hex(vt[6]))
check("vtable span 0xF30230..0xF30250 byte-identical",
      span_sha(0xf30230, 0xf30250) ==
      "359909F9070BA1F4A88560648668B2E299C40C08439BA15CD7DDAA99A97DB467",
      span_sha(0xf30230, 0xf30250))
ctor = {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(0x5e5050, 0x3d), 0x5e5050)}
check("ctor 0x5E5050 stores vtable 0xF30230 (mov dword[eax],0xF30230)",
      rd(0x5e506c, 6) == bytes.fromhex("c7003002f300"))
check("ctor zero-inits heading f32 @obj+0x20",
      ctor.get(0x5e5081) == ('movss', 'dword ptr [eax + 0x20], xmm0'))
check("ctor zero-inits x/y/z f32 @obj+0x14/+0x18/+0x1C",
      ctor.get(0x5e507c) == ('movss', 'dword ptr [eax + 0x14], xmm0')
      and ctor.get(0x5e5077) == ('movss', 'dword ptr [eax + 0x18], xmm0')
      and ctor.get(0x5e5072) == ('movss', 'dword ptr [eax + 0x1c], xmm0'))
check("ctor zero-inits moving/mask u8 @obj+0x24/+0x25",
      ctor.get(0x5e5086) == ('mov', 'byte ptr [eax + 0x24], cl')
      and ctor.get(0x5e5089) == ('mov', 'byte ptr [eax + 0x25], cl'))
check("ctor span 0x5E5050..0x5E508D byte-identical",
      span_sha(0x5e5050, 0x5e508d) ==
      "1A21C3EE1CDCC6E302C24E6C0C9CD28FB01DE06FFB1BAE8FAFFCA7F635E1F034",
      span_sha(0x5e5050, 0x5e508d))

# ---------------------------------------------------------------------------
# 3. Serializer wire schema — f32(0x2A)x4 then u8(0x0B)x2, byte-exact
# ---------------------------------------------------------------------------
check("field serializer 0x89A600 is stdcall(tag,ptr,width) ret 0xC",
      rd(0x89a63d, 3) == bytes([0xC2, 0x0C, 0x00]))
ser = {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(0x5e50e0, 0x50), 0x5e50e0)}
check("serializer calls vec3 helper 0x5F3490 on obj+0x14 (x,y,z)",
      ser.get(0x5e50ed) == ('lea', 'eax, [esi + 0x14]')
      and ser.get(0x5e50f4) == ('call', '0x5f3490'))
check("serializer heading field: tag 0x2A width 4 @obj+0x20",
      rd(0x5e50fc, 2) == bytes([0x6A, 0x04])        # push 4 (width)
      and ser.get(0x5e50fe) == ('lea', 'ecx, [esi + 0x20]')
      and rd(0x5e5102, 2) == bytes([0x6A, 0x2A]))   # push 0x2A (tag)
check("serializer moving field: tag 0x0B width 1 @obj+0x24",
      ser.get(0x5e510d) == ('lea', 'edx, [esi + 0x24]')
      and rd(0x5e5111, 2) == bytes([0x6A, 0x0B]))
check("serializer mask field: tag 0x0B width 1 @obj+0x25",
      ser.get(0x5e511c) == ('add', 'esi, 0x25')
      and rd(0x5e5120, 2) == bytes([0x6A, 0x0B]))
check("serializer is stdcall ret 8 (in/out stream at [esp+8])",
      ser.get(0x5e512b) == ('ret', '8'))
check("serializer span 0x5E50E0..0x5E512E byte-identical",
      span_sha(0x5e50e0, 0x5e512e) ==
      "E7807751909BF14F07A371D9ED6DD79F9EE6AA1F62D15AEB2A14B4225929E097",
      span_sha(0x5e50e0, 0x5e512e))
v3 = {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(0x5f3490, 0x40), 0x5f3490)}
check("vec3 helper 0x5F3490 = three tag-0x2A width-4 fields at +0,+4,+8",
      rd(0x5f349a, 2) == bytes([0x6A, 0x04]) and rd(0x5f349d, 2) == bytes([0x6A, 0x2A])
      and v3.get(0x5f34a8) == ('lea', 'eax, [esi + 4]') and rd(0x5f34ac, 2) == bytes([0x6A, 0x2A])
      and v3.get(0x5f34b7) == ('add', 'esi, 8') and rd(0x5f34bb, 2) == bytes([0x6A, 0x2A]))
check("vec3 helper span 0x5F3490..0x5F34C7 byte-identical",
      span_sha(0x5f3490, 0x5f34c7) ==
      "B5F5A2063FF9FC8F22830E3238A8B30387D781505ACE23D889C3A1500EA47454",
      span_sha(0x5f3490, 0x5f34c7))

# ---------------------------------------------------------------------------
# 4. Producer — object is factory-constructed (alloc 0x28) then ctor called
# ---------------------------------------------------------------------------
ctor_callers = callers_of(0x5e5050)
check("ctor 0x5E5050 reached from exactly two factory sites (0x44B7C4, 0x44B842)",
      ctor_callers == [0x0044b7c4, 0x0044b842], str([hex(x) for x in ctor_callers]))
check("factory allocates a 0x28-byte object before construct (push 0x28 @0x44B7AC)",
      rd(0x44b7ac, 2) == bytes([0x6A, 0x28]))
# get-id / serializer are reached via the vtable, not direct calls -> 0 direct callers
check("serializer 0x5E50E0 has no direct E8 caller (vtable-dispatched cohort)",
      callers_of(0x5e50e0) == [])
check("get-id 0x5E50A0 has no direct E8 caller (vtable-dispatched cohort)",
      callers_of(0x5e50a0) == [])

# ---------------------------------------------------------------------------
# 5. Wire<->server binding — captured MARKER1 payload decodes under the schema
# ---------------------------------------------------------------------------
def decode_targetpos(nested):
    """Mirror server parse_target_pos_vital over a nested payload of tag fields."""
    p = 0; vals = []
    for _ in range(4):
        assert nested[p] == 0x2A
        vals.append(struct.unpack('<f', nested[p + 1:p + 5])[0]); p += 5
    assert nested[p] == 0x0B; moving = nested[p + 1]; p += 2
    assert nested[p] == 0x0B; mask = nested[p + 1]; p += 2
    return vals, moving, mask, len(nested) - p


CAP_NESTED = bytes.fromhex(
    "2A004821C6" "2A00C03CC4" "2A00C02744" "2A00000000" "0B01" "0B00"
)
(_x, _y, _z, _h), _mv, _mk, _rem = decode_targetpos(CAP_NESTED)
check("captured MARKER1 TargetPos payload decodes x,y,z=(-10322,-755,671)",
      (_x, _y, _z) == (-10322.0, -755.0, 671.0), f"{_x},{_y},{_z}")
check("captured MARKER1 TargetPos payload: heading 0, moving 1, mask 0, remain 0",
      _h == 0.0 and _mv == 1 and _mk == 0 and _rem == 0, f"h={_h} mv={_mv} mk={_mk} rem={_rem}")

# ---------------------------------------------------------------------------
# 6. Server coverage gap — decodes but accepts-as-given, no local authority
# ---------------------------------------------------------------------------
src = open(SERVER_SRC, "r", encoding="utf-8", errors="replace").read()
check("server declares TARGET_POS_VITAL = 0x2A90", "TARGET_POS_VITAL = 0x2A90" in src)
check("server decodes the same schema (def parse_target_pos_vital)",
      "def parse_target_pos_vital" in src)
check("server stores the reported position as-given (self.last_target_pos =)",
      "self.last_target_pos = (x, y, z, heading)" in src)
check("server ships the authentic captured payload V139_MARKER1_TARGETPOS_PC",
      "V139_MARKER1_TARGETPOS_PC=bytes.fromhex" in src.replace(" ", "")
      or "V139_MARKER1_TARGETPOS_PC=bytes.fromhex" in src)
flat = src.replace(" ", "").lower()
check("server performs NO local-player corrective reposition",
      "corrective" not in flat and "reposition" not in flat)
check("server performs NO local-player speed/distance/collision authority check",
      "def validate_movement" not in src and "def check_movement_speed" not in src
      and "movement_authority" not in flat)

print()
if fails:
    print(f"RESULT: {len(fails)} guard(s) drifted: {fails}")
    sys.exit(1)
print("RESULT: all TargetPosVital movement-report producer static guards reproduced (exit 0)")
