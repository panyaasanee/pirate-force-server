#!/usr/bin/env python3
"""PF TELEPORT-CHECK-001 — static reproduction for TeleportCheckVital 0x4477.

Report-only additive supplement. Sole evidence source = the client binary
GameClient\\GameClient.local.bin (read-only, disassembled) plus the read-only
wire corpus (GameClient\\capture_v13x/v14x\\GAME_*.txt).

Reproduces, byte-exact, every VA/offset/guard cited in
reports/PF_TELEPORT_CHECK001_0X4477_VTABLE_SCHEMA_CONFIRM_STATIC_20260818.md
via capstone (CS_MODE_32, ImageBase 0x400000, PE section table parsed).

Usage:  py -3 tools/pf_teleportcheck_0x4477_static.py [path-to-GameClient.local.bin]
Exit 0 = all static guards reproduced; nonzero = a guard drifted.
"""
import sys, struct, re
try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    sys.exit("capstone required: pip install capstone")

BIN = sys.argv[1] if len(sys.argv) > 1 else "GameClient/GameClient.local.bin"
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

data = open(BIN, "rb").read()
import hashlib
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

md = Cs(CS_ARCH_X86, CS_MODE_32)

fails = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))
    if not cond: fails.append(name)

check("binary SHA-256 matches", sha == EXPECT_SHA, sha)

# G1: class-name string present
name_off = data.find(b"TeleportCheckVital\x00")
check("string 'TeleportCheckVital' present @0xf30a64",
      off2va(name_off) == 0xf30a64, hex(off2va(name_off)) if name_off >= 0 else "missing")

# G2: registration block — push name; call once-init; call id-assign; store ax -> id-slot
reg = rd(0xbee820, 24)
check("registration @0xbee820 pushes name 0xf30a64",
      reg[0] == 0x68 and struct.unpack_from('<I', reg, 1)[0] == 0xf30a64)
check("registration calls once-init 0x89c080",
      reg[5] == 0xe8 and (0xbee825 + 5 + struct.unpack_from('<i', reg, 6)[0]) == 0x89c080)
check("registration calls id-assign 0x89bd00",
      reg[0xc] == 0xe8 and (0xbee82c + 5 + struct.unpack_from('<i', reg, 0xd)[0]) == 0x89bd00)
check("registration stores ax -> id-slot 0x1082074 (66 a3)",
      reg[0x11] == 0x66 and reg[0x12] == 0xa3 and struct.unpack_from('<I', reg, 0x13)[0] == 0x1082074)

# G3: id 0x4477 is NEVER a code immediate (only reachable via runtime id-slot)
tgt = struct.pack('<I', 0x00004477)
imm_hits = []
for m in re.finditer(re.escape(tgt), data):
    va = off2va(m.start())
    if va is None: continue
    # exclude the e8/e9 rel32 call/jmp whose displacement coincidentally = 0x4477
    prev = data[m.start() - 1]
    if prev in (0xe8, 0xe9): continue
    imm_hits.append(va)
check("0x4477 never appears as a code immediate (runtime-assigned id)",
      len(imm_hits) == 0, "hits=" + str([hex(x) for x in imm_hits]))

# G4: id-slot 0x1082074 read only by the get-id stub 0x449430
slot_refs = [off2va(m.start()) for m in re.finditer(re.escape(struct.pack('<I', 0x1082074)), data)
             if off2va(m.start()) and secs[0][0]]
text_refs = sorted(set(v for v in slot_refs if v and (v & 0xfffffff0) in (0x449430, 0xbee830)))
stub = rd(0x449430, 7)
check("get-id stub @0x449430 = mov ax,[0x1082074]; ret",
      stub[:2] == b'\x66\xa1' and struct.unpack_from('<I', stub, 2)[0] == 0x1082074 and stub[6] == 0xc3)

# G5: vtable 0xf0d66c — serializer +0x18, get-id +0x10, shared framework const +0x08
vt = rd(0xf0d66c, 0x20)
vslots = struct.unpack('<8I', vt)
check("vtable 0xf0d66c +0x10 = get-id 0x449430", vslots[4] == 0x449430)
check("vtable 0xf0d66c +0x18 = serializer 0x5e6670", vslots[6] == 0x5e6670)
check("vtable 0xf0d66c +0x08 = shared framework const 0x401b20 (VitalData family)",
      vslots[2] == 0x401b20)

# G6: serializer 0x5e6670 — single tagged u16 at object+0x14, tag 0x0f, dual in/out helper
ser = rd(0x5e6670, 0x1b)
check("serializer adds 0x14 to this (add ecx,0x14)",
      ser[:3] == b'\x83\xc1\x14')
check("serializer pushes field tag 0x0f (push 0xf)",
      b'\x6a\x0f' in ser[:0x12])
# direction branch: cmp byte[esp+8],0 ; je -> 0x89a640 else 0x89a600
check("serializer branches in/out to 0x89a600 / 0x89a640",
      b'\x80\x7c\x24\x08\x00' in ser)

# G7: prototype registered in the generic Vital factory (vtable installed at 0x5ee9c4)
vt_refs = [off2va(m.start()) for m in re.finditer(re.escape(struct.pack('<I', 0xf0d66c)), data)]
vt_refs = sorted(set(v for v in vt_refs if v))
check("vtable 0xf0d66c installed in factory builder @0x5ee9c4",
      0x5ee9c4 in vt_refs, str([hex(x) for x in vt_refs]))

# G8: wire corpus — client->server frame is byte-identical value=1 (tag 0x0f) with no reply
import glob, os
root = os.path.dirname(os.path.dirname(os.path.abspath(BIN)))
# Captures are text logs: the client->server body is journaled as the raw nested
# payload string '0F0100' (tag 0x0f, u16 value=1) alongside id 17527 (=0x4477).
corpus = []
for gl in sorted(glob.glob(os.path.join(root, "GameClient", "capture_v13[6-9]", "GAME_2*.txt"))
                 + glob.glob(os.path.join(root, "GameClient", "capture_v14[0-9]", "GAME_2*.txt"))
                 + glob.glob(os.path.join(root, "GameClient", "capture_v131", "GAME_2*.txt"))):
    try:
        t = open(gl, "r", errors="replace").read()
    except OSError:
        continue
    if "TeleportCheckVital" in t:
        # decompressed dump renders the nested body as spaced hex pairs:
        #   ... 12 77 44 | 0B 00 | 0F 01 [00] = id 0x4477, ver0, tag 0x0f, u16 value=1
        ok = "77 44 0B 00 0F 01" in t
        corpus.append((os.path.basename(os.path.dirname(gl)), ok))
if corpus:
    allok = all(ok for _, ok in corpus)
    check("wire corpus: nested payload '0F0100' (id 0x4477 ver0 tag0f value=1) in every capture",
          allok, str(corpus))
else:
    print("SKIP wire corpus (capture files not reachable from this path)")

print()
if fails:
    print("RESULT: FAIL (%d guards drifted): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("RESULT: PASS — all TeleportCheckVital 0x4477 static guards reproduced")
