#!/usr/bin/env python3
"""PF SPLIT-OPERATE-001 — static reproduction of the ItemOperateVitalReq 0x4BED
operation space (the transport that a stack-split request must ride).

Report-only additive supplement. Sole evidence source = the client binary
GameClient\\GameClient.local.bin (read-only, disassembled) cross-checked against
the read-only server source current\\pf_login_game_server_v141.py.

Reproduces, byte-exact, every VA / object offset / operation immediate cited in
reports/PF_SPLIT_OPERATE001_ITEM_OPERATE_OPCODE_SPACE_STATIC_20260818.md via
capstone (CS_MODE_32, ImageBase 0x400000, PE section table parsed).

Usage:  py -3 tools/pf_split_operate_static.py [path-to-GameClient.local.bin]
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
"""
import sys, struct, re, hashlib

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    sys.exit("capstone required: pip install capstone")

BIN = sys.argv[1] if len(sys.argv) > 1 else "GameClient/GameClient.local.bin"
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

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


def off2va(off):
    for n, vaddr, vsize, rawptr, rawsize in secs:
        if rawptr <= off < rawptr + rawsize:
            return image_base + vaddr + (off - rawptr)
    return None


def rd(va, n):
    o = va2off(va); return data[o:o + n]


def span_sha(va, end):
    return hashlib.sha256(rd(va, end - va)).hexdigest().upper()


md = Cs(CS_ARCH_X86, CS_MODE_32)

fails = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    if not cond:
        fails.append(name)


check("binary SHA-256 matches", sha == EXPECT_SHA, sha)

# --- Identity: class name + registration + runtime-assigned id (no 0x4BED immediate) ---
name_off = data.find(b"ItemOperateVitalReq\x00")
check("string 'ItemOperateVitalReq' present @0xf30904",
      off2va(name_off) == 0xf30904, hex(off2va(name_off)) if name_off >= 0 else "missing")

reg = rd(0xbee520, 24)
check("registration @0xbee520 pushes name 0xf30904",
      reg[0] == 0x68 and struct.unpack_from('<I', reg, 1)[0] == 0xf30904)
check("registration calls once-init 0x89c080 (MSVC guard, same wall as ECHO/TELEPORT)",
      reg[5] == 0xe8 and (0xbee525 + 5 + struct.unpack_from('<i', reg, 6)[0]) == 0x89c080)
check("registration calls id-assign 0x89bd00",
      reg[0xc] == 0xe8 and (0xbee52c + 5 + struct.unpack_from('<i', reg, 0xd)[0]) == 0x89bd00)
check("registration stores ax -> id-slot 0x1082014 (66 a3)",
      reg[0x11] == 0x66 and reg[0x12] == 0xa3 and struct.unpack_from('<I', reg, 0x13)[0] == 0x1082014)
check("get-id stub @0x5e5ae0 reads id-slot 0x1082014",
      rd(0x5e5ae0, 7).hex().upper() == "66A114200801C3")

# id 0x4BED is NEVER a code immediate (only reachable via runtime id-slot)
tgt = struct.pack('<I', 0x00004BED)
imm_hits = []
for m in re.finditer(re.escape(tgt), data):
    va = off2va(m.start())
    if va is None:
        continue
    prev = data[m.start() - 1]
    if prev in (0xe8, 0xe9):  # rel32 displacement coincidence
        continue
    imm_hits.append(va)
check("id 0x4BED never appears as a non-call code immediate (runtime-assigned)",
      len(imm_hits) == 0, str([hex(x) for x in imm_hits]))

# --- vtable base 0xf30374: shared VitalData cohort const at +0x08, serializer at +0x18 ---
vt = struct.unpack_from('<8I', rd(0xf30374, 32))
check("vtable +0x08 = shared framework const 0x401b20 (VitalData cohort)", vt[2] == 0x401b20)
check("vtable +0x10 = get-id stub 0x5e5ae0", vt[4] == 0x5e5ae0)
check("vtable +0x18 = serializer 0x5e5af0", vt[6] == 0x5e5af0)

# --- serializer 0x5e5af0: three tagged fields, byte-exact offsets/tags/widths ---
ser = {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(0x5e5af0, 0x70), 0x5e5af0)}
# out branch (0x89a600): operation u8 @ +0x14 tag 0x0B ; value32 u32 @ +0x18 tag 0x14 ; qword @ +0x20 tag 0x32
check("serializer field#1 = obj+0x14 (operation)",
      ser.get(0x5e5b03) == ('lea', 'eax, [esi + 0x14]'))
check("serializer field#1 tag 0x0B width 1",
      ser.get(0x5e5afd) == ('push', '1') and ser.get(0x5e5b07) == ('push', '0xb'))
check("serializer field#2 = obj+0x18 (value32)",
      ser.get(0x5e5b10) == ('lea', 'ecx, [esi + 0x18]'))
check("serializer field#2 tag 0x14 width 4",
      ser.get(0x5e5b0e) == ('push', '4') and ser.get(0x5e5b14) == ('push', '0x14'))
check("serializer field#3 = obj+0x20 (qword item_identity/count)",
      ser.get(0x5e5b1f) == ('add', 'esi, 0x20'))
check("serializer field#3 tag 0x32 width 8",
      ser.get(0x5e5b1d) == ('push', '8') and ser.get(0x5e5b23) == ('push', '0x32'))

# --- constructor 0x5e5b60: default operation byte = 1 ---
check("constructor @0x5e5b60 sets default operation obj+0x14 = 1",
      rd(0x5e5b87, 4).hex().upper() == "C6401401")

# --- operation producers: enumerate the operation immediates written to obj+0x14 ---
producers = {3: 0x59f79e, 4: 0x59f7e5, 5: 0x59f84b, 6: 0x59f895}
for op, opva in producers.items():
    b = rd(opva, 4)
    check(f"producer writes operation={op} (C6 40 14 {op:02X}) @{opva:#08x}",
          b == bytes([0xC6, 0x40, 0x14, op]))
# op5 also emitted from a second callsite (equipment UI lookup path)
check("operation=5 also written @0x5a25d1 (second equip producer)",
      rd(0x5a25d1, 4) == bytes([0xC6, 0x40, 0x14, 0x05]))

# move (op4) field usage: value32 = destination slot, qword = item identity
mov = {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(0x59f7c0, 0x40), 0x59f7c0)}
check("op4(move): value32 obj+0x18 set from a caller dword", mov.get(0x59f7dd) == ('mov', 'dword ptr [eax + 0x18], ecx'))
check("op4(move): item identity qword at obj+0x20/0x24", mov.get(0x59f7e9) == ('mov', 'dword ptr [eax + 0x20], edx'))

# op6 field usage: value32 = item handle, qword = a caller-supplied 64-bit value (quantity)
o6 = {i.address: (i.mnemonic, i.op_str) for i in md.disasm(rd(0x59f870, 0x40), 0x59f870)}
check("op6(quantity): value32 obj+0x18 set", o6.get(0x59f88d) == ('mov', 'dword ptr [eax + 0x18], ecx'))
check("op6(quantity): 64-bit value at obj+0x20/0x24", o6.get(0x59f899) == ('mov', 'dword ptr [eax + 0x20], edx'))

# --- byte-span pins (regression guard) ---
SPANS = {
    "getid_stub":    (0x5e5ae0, 0x5e5ae7, "E757D9EA8BECCF6298A1736FB90BFE70F85C5C47FCE21E45A24E287248A2AFFA"),
    "serializer":    (0x5e5af0, 0x5e5b5d, "D25B32EB977D1E5D029DB7F4D7399413B18F2EA004A9C502801580BF11316094"),
    "constructor":   (0x5e5b60, 0x5e5b90, "B93530D850CA1081117666F140F2EECB2AB5E642256DADFC92789C15C6B33ED3"),
    "vtable":        (0xf30374, 0xf30394, "D272EEDB661F43D87A9917484E069B3A811C646D8414C2AC7431B8CBD75845A7"),
    "registration":  (0xbee520, 0xbee538, "13602513CB3600B04C4C4F3E3CD3BB55AB4C801394498E3195AB5AADDA9F6556"),
    "producer_op3":  (0x59f780, 0x59f7b6, "4F6F8E7687946AE90AE40C27E1E5CC06E82DE3C441821DE6E0063F83069F2001"),
    "producer_op4":  (0x59f7c0, 0x59f7fe, "D441C505E9AB01E7E232210D45EB2D617CC95591AEB998228CC04B338AE54E44"),
    "producer_op5":  (0x59f800, 0x59f868, "70F75803E0CC3937860813CE5E255D2B2184F13013061833FE68748DDF0DAE01"),
    "producer_op6":  (0x59f870, 0x59f8ae, "A165878D9441A2CE9FA3272DF291178E53CB239E8A081D67588B1D28AD4BB29A"),
}
for label, (a, b, exp) in SPANS.items():
    check(f"span {label} {a:#08x}..{b:#08x} byte-identical", span_sha(a, b) == exp, span_sha(a, b))

print()
if fails:
    print(f"RESULT: {len(fails)} guard(s) drifted: {fails}")
    sys.exit(1)
print("RESULT: all ItemOperate opcode-space static guards reproduced (exit 0)")
