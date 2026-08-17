#!/usr/bin/env python3
"""PF-NAMEID-HASH-001 - static reproduction: the 16-bit Vital wire id is a PURE
HASH of the plaintext class-name string, computed at once-init startup.

Report-only additive supplement. Sole binary evidence source = the client
GameClient\\GameClient.local.bin (read-only, disassembled via capstone,
CS_MODE_32, ImageBase 0x400000, PE section table parsed). Wire ids are the
already-committed constants in current/pf_login_game_server_v141.py.

Settles the open question queued by CHAT-ECHO-008 ("walk 0x89bd00/0x89b220 to
falsify 'id is a pure hash of the name'"): the answer is HASH, not a
config/counter. The once-init guard 0x89c080 is (as ECHO-008 stated) NOT a hash;
the hash lives one call deeper, at 0x89b220.

Algorithm (0x89b220), reproduced byte-exact below:
    uint16 id = 0
    for i in 0..len-1:  id += (int16)( (signed char)name[i] * (i+1) )   # mod 2^16
    return id & 0xFFFF

Usage:  py -3 tools/pf_vital_id_hash_static.py [path-to-GameClient.local.bin]
Exit 0 = all guards reproduced; nonzero = a guard drifted.
"""
import sys, struct, hashlib
try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    sys.exit("capstone required: pip install capstone")

BIN = sys.argv[1] if len(sys.argv) > 1 else "GameClient/GameClient.local.bin"
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

data = open(BIN, "rb").read()
sha = hashlib.sha256(data).hexdigest().upper()

# ---- PE section table ----
e_lfanew = struct.unpack_from('<I', data, 0x3c)[0]; coff = e_lfanew + 4
nsec = struct.unpack_from('<H', data, coff + 2)[0]
opt_size = struct.unpack_from('<H', data, coff + 16)[0]; opt = coff + 20
IMAGE_BASE = struct.unpack_from('<I', data, opt + 28)[0]
sect = opt + opt_size
secs = []
for i in range(nsec):
    off = sect + i * 40
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, off + 8)
    secs.append((vaddr, vsize, rawptr, rawsize))

def va2off(va):
    r = va - IMAGE_BASE
    for vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= r < vaddr + max(vsize, rawsize):
            return rawptr + (r - vaddr)
    return None

def raw(va, n):
    o = va2off(va); return data[o:o+n] if o is not None else None

def cstr(va, maxn=96):
    o = va2off(va)
    if o is None: return None
    b = data[o:o+maxn]; z = b.find(b'\x00')
    return b[:z].decode('latin1') if z >= 0 else None

md = Cs(CS_ARCH_X86, CS_MODE_32)

def ins_at(va, nbytes=64):
    o = va2off(va)
    return list(md.disasm(data[o:o+nbytes], va))

# ---- the recovered hash (what we CLAIM the client computes) ----
def name_id_signed(name):
    """signed char (client movsx), 16-bit position-weighted sum, mod 2^16."""
    acc = 0
    for i, ch in enumerate(name.encode('latin1')):
        sc = ch if ch < 128 else ch - 256
        acc = (acc + ((sc * (i + 1)) & 0xFFFF)) & 0xFFFF
    return acc

def name_id_unsigned(name):
    """unsigned ord() - the model in server protocol_name_id()."""
    return sum((i + 1) * ch for i, ch in enumerate(name.encode('latin1'))) & 0xFFFF

# (name, wire id) pairs - the committed constants / protocol_name_id asserts in v141
KNOWN = {
    "TeleportCheckVital": 0x4477, "TargetPosVital": 0x2A90, "TeleportVital": 0x25A2,
    "GetWorldInfoVital": 0x3D4B, "LogoutVital": 0x1B40,
    "Channel_LocalTalkMessageVital": 0xAC52, "ItemOperateVital": 0x36FE,
    "ItemOperateVitalReq": 0x4BED, "ItemOperateVitalRes": 0x4C13,
    "QuestOperateVital": 0x3E34, "TradeCmdVital": 0x23B5, "TradeZoomVital": 0x2A7A,
    "UseItemVital": 0x1F4F,
}
# in-image registration thunks (found by full-.text scan) that push the literal
# class name and store the id; slots tie to prior rounds (TeleportCheck slot =
# 0x1082074 exactly matches TELEPORT-CHECK-001, round 61).
THUNKS = {  # name -> (thunk_va, id_slot)
    "TeleportCheckVital": (0xbee820, 0x1082074),
    "TargetPosVital":     (0xbee380, 0x1081FE0),
    "TeleportVital":      (0xbee400, 0x1081FF0),
    "GetWorldInfoVital":  (0xbee7c0, 0x1082068),
    "LogoutVital":        (0xbee860, 0x108207C),
    "UseItemVital":       (0xbee600, 0x1082030),
    "QuestOperateVital":  (0xbf2b70, 0x108324C),
    "Channel_LocalTalkMessageVital": (0xbf72d0, 0x1084458),
    "TradeCmdVital":      (0xbf8830, 0x1084AE8),
    "TradeZoomVital":     (0xbf8870, 0x1084AF0),
}

fail = []
def guard(cond, msg):
    print(("  PASS " if cond else "  FAIL ") + msg)
    if not cond: fail.append(msg)

print("PF-NAMEID-HASH-001 static verifier")
print("binary SHA-256 =", sha)
guard(sha == EXPECT_SHA, "binary SHA-256 matches pinned image")
guard(IMAGE_BASE == 0x400000, "ImageBase == 0x400000")

# G1: 0x89b220 is the hash - signed-char position-weighted MAC loop
b = raw(0x89b220, 96)
guard(b is not None and b'\x66\x0f\xbe\x3c\x31' in b,
      "0x89b220 has `movsx di, byte [ecx+esi]` (signed char load)")
guard(b is not None and b'\x66\x0f\xaf\xfb' in b,
      "0x89b220 has `imul di, bx` (multiply by 1-based index)")
guard(b is not None and b'\x66\x03\xd7' in b,
      "0x89b220 has `add dx, di` (16-bit accumulate)")
guard(b is not None and b'\x66\x8b\xc2' in b,
      "0x89b220 returns accumulator in ax (`mov ax, dx`)")

# G2: 0x89bd00 id-assign calls the hash and returns its result
b2 = raw(0x89bd00, 64)
# push ebx (53) ; call rel32 -> 0x89b220 ; movzx edi, ax (0f b7 f8)
has_call_hash = False
for ins in ins_at(0x89bd00, 64):
    if ins.mnemonic == 'call' and ins.op_str == '0x89b220':
        has_call_hash = True
guard(has_call_hash, "0x89bd00 (id-assign) calls 0x89b220 (the hash)")
guard(b2 is not None and b'\x0f\xb7\xf8' in b2, "0x89bd00 keeps hash result (`movzx edi, ax`)")

# G3: 0x89c080 is the _Init_thread-style singleton guard (NOT a hash) - agrees w/ ECHO-008
b3 = raw(0x89c080, 48)
guard(b3 is not None and b'\xa1\x90\xcf\x08\x01' in b3,
      "0x89c080 tests singleton @0x108cf90 (once-init guard, not a hash)")

# G4: a representative in-image thunk pushes the literal class name, once-inits,
# id-assigns, stores id -> slot. Verify byte pattern + literal + slot for each tie.
tie = 0
for nm, (tva, slot) in THUNKS.items():
    o = va2off(tva)
    okpat = (o is not None and data[o] == 0x68 and data[o+5] == 0xE8
             and data[o+10:o+12] == b'\x8b\xc8' and data[o+12] == 0xE8
             and data[o+17:o+19] == b'\x66\xa3')
    nameptr = struct.unpack_from('<I', data, o+1)[0] if o is not None else 0
    lit = cstr(nameptr)
    slot_in_ins = struct.unpack_from('<I', data, o+19)[0] if o is not None else 0
    # id-assign target
    rel = struct.unpack_from('<i', data, o+13)[0] if o is not None else 0
    idassign = (tva+12+5+rel) if o is not None else 0
    good = okpat and lit == nm and slot_in_ins == slot and idassign == 0x89bd00 \
           and name_id_signed(nm) == KNOWN[nm]
    tie += good
    guard(good, "thunk 0x%06x pushes literal %-30s -> id-assign -> slot 0x%X ; hash 0x%04X == wire id 0x%04X"
          % (tva, repr(nm), slot, name_id_signed(nm), KNOWN[nm]))
guard(tie == len(THUNKS), "all %d in-image name-literal -> wire-id ties reproduced" % len(THUNKS))

# G5: recovered hash reproduces every committed (name, id) pair byte-exact
n_ok = sum(name_id_signed(k) == v for k, v in KNOWN.items())
guard(n_ok == len(KNOWN), "recovered signed-char hash reproduces %d/%d known wire ids" % (n_ok, len(KNOWN)))

# G6: signed (client) vs unsigned (server ord) - identical on ASCII, diverges on high-bit
ascii_same = all(name_id_signed(k) == name_id_unsigned(k) for k in KNOWN)
hb_diverge = name_id_signed("A\x80") != name_id_unsigned("A\x80")
guard(ascii_same, "signed==unsigned for all ASCII protocol names (server model exact here)")
guard(hb_diverge, "signed!=unsigned for a high-bit byte (documented divergence edge)")

print()
if fail:
    print("RESULT: FAIL (%d guard(s) drifted)" % len(fail)); sys.exit(1)
print("RESULT: PASS - all guards reproduced from this binary"); sys.exit(0)
