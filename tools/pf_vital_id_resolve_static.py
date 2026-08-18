#!/usr/bin/env python3
"""PF-NAMEID-RESOLVE-001 - resolve three previously-unnamed golden-corpus wire
ids to their plaintext Vital class names, using the confirmed id = hash(name)
algorithm settled by PF-NAMEID-HASH-001 (round 62, commit 7c66b21).

Report-only additive supplement. Sole binary evidence source = the client
GameClient\\GameClient.local.bin (read-only, disassembled via capstone,
CS_MODE_32, ImageBase parsed from the PE header). Golden wire evidence source =
capture_v141/*.txt (the pinned canonical golden corpus B5557E9F..C9ED).

The 16-bit Vital wire id (settled round 62, verifier pf_vital_id_hash_static.py):

    uint16 id = 0
    for i in 0..len-1:  id += (int16)( (signed char)name[i] * (i+1) )   # mod 2^16
    return id & 0xFFFF

This tool proves three things, each byte-exact / corpus-exact:

  (1) GOLDEN CROSS-CHECK. The six *named* structural ids that actually appear in
      the golden corpus are reproduced byte-exact by the hash (real recorded
      frames, not just static image ties):
        StartGameReq 0x1E87, CreateActorVital 0x36CF, LoginVerifyVital 0x3784,
        GetWorldInfoVital 0x3D4B, GSCN_LoginProtocol 0x453A,
        GSCN_RunTimeProtocolReq 0x6E6F.
      Additionally all 49 (id,name) pairs committed in the v141 protocol NAMES
      table reproduce byte-exact (0 mismatch) - a stronger corroboration of the
      algorithm than round 62's 13/13 corpus.

  (2) RESOLUTION. The three ids that the golden decoder prints as bare hex
      (because they are absent from the v141 NAMES table) each resolve to
      EXACTLY ONE identifier-style in-image string literal whose hash equals the
      id, and each literal sits in a registration thunk with the byte-exact
      shape settled round 62:  push <lit>; call 0x89c080 (once-init);
      mov ecx,eax; call 0x89bd00 (id-assign); mov word ptr [id-slot], ax; ret.
        0x1B40 (6976)  -> LogoutVital                    (slot 0x108207c)
        0x36DB (14043) -> DeleteActorVital               (slot 0x1081fd0)
        0xAC52 (44114) -> Channel_LocalTalkMessageVital  (slot 0x1084458)

  (3) SEMANTIC CORROBORATION. Each resolved id appears in golden frames whose
      independent hypothesis label matches the resolved class name:
        0x1B40 under HYP_PF_016_LOGOUT_...            -> LogoutVital
        0x36DB under HYP_PF_015_DELETE_ACTOR_...      -> DeleteActorVital
        0xAC52 under HYP_PF_014_CHAT_INPUT_...        -> Channel_LocalTalkMessageVital

Usage:  py -3 tools/pf_vital_id_resolve_static.py [path-to-GameClient.local.bin] [path-to-capture_v141]
Exit 0 = all guards reproduced; nonzero = a guard drifted.
"""
import os, re, sys, struct, hashlib, glob

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    sys.exit("capstone required: pip install capstone")

BIN = sys.argv[1] if len(sys.argv) > 1 else "GameClient/GameClient.local.bin"
CORPUS = sys.argv[2] if len(sys.argv) > 2 else "capture_v141"
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

FAILS = []
def guard(cond, msg):
    if cond:
        print(f"  PASS  {msg}")
    else:
        print(f"  FAIL  {msg}")
        FAILS.append(msg)

# ---------- hash (round-62 algorithm, signed char, 1-based index) ----------
def wire_id(name: str) -> int:
    s = 0
    for i, ch in enumerate(name.encode("latin1")):
        c = ch - 256 if ch >= 128 else ch      # movsx di, byte  -> signed
        s += c * (i + 1)                        # imul di, bx     -> 1-based index
    return s & 0xFFFF                            # mov ax, dx; ret 4

# ---------- load image + PE section table ----------
data = open(BIN, "rb").read()
sha = hashlib.sha256(data).hexdigest().upper()

print("== PF-NAMEID-RESOLVE-001 static+golden verifier ==")
print(f"binary: {BIN}")
guard(sha == EXPECT_SHA, f"binary SHA256 pinned == {EXPECT_SHA[:16]}... (got {sha[:16]}...)")

e_lfanew = struct.unpack_from("<I", data, 0x3c)[0]; coff = e_lfanew + 4
nsec = struct.unpack_from("<H", data, coff + 2)[0]
opt_size = struct.unpack_from("<H", data, coff + 16)[0]; opt = coff + 20
IMAGE_BASE = struct.unpack_from("<I", data, opt + 28)[0]
sect = opt + opt_size
SECS = []
for i in range(nsec):
    o = sect + i * 40
    vsz = struct.unpack_from("<I", data, o + 8)[0]
    vaddr = struct.unpack_from("<I", data, o + 12)[0]
    rsz = struct.unpack_from("<I", data, o + 16)[0]
    praw = struct.unpack_from("<I", data, o + 20)[0]
    SECS.append((vaddr, vsz, praw, rsz))

def off_to_va(off):
    for vaddr, vsz, praw, rsz in SECS:
        if praw <= off < praw + rsz:
            return IMAGE_BASE + vaddr + (off - praw)
    return None

# ---------- (1) golden cross-check ----------
print("\n[1] golden cross-check: hash reproduces named ids in the golden corpus")
GOLDEN_NAMED = {
    "StartGameReq": 0x1E87, "CreateActorVital": 0x36CF, "LoginVerifyVital": 0x3784,
    "GetWorldInfoVital": 0x3D4B, "GSCN_LoginProtocol": 0x453A,
    "GSCN_RunTimeProtocolReq": 0x6E6F,
}
for name, wid in GOLDEN_NAMED.items():
    guard(wire_id(name) == wid, f"hash({name}) == 0x{wid:04X}")

# every named tuple actually present in the corpus is reproduced
corpus_files = sorted(glob.glob(os.path.join(CORPUS, "*.txt")))
guard(len(corpus_files) > 0, f"golden corpus present ({len(corpus_files)} files under {CORPUS})")
corpus_named = set(); corpus_unnamed = set()
tup = re.compile(r"\((\d+),\s*(\d+),\s*'([^']*)'\)")
for f in corpus_files:
    for line in open(f, encoding="utf-8", errors="replace"):
        if "STRUCTURAL_IDS" in line:
            for m in tup.finditer(line):
                wid, nm = int(m.group(2)), m.group(3)
                (corpus_unnamed if nm.startswith("0x") else corpus_named).add((wid, nm))
for wid, nm in sorted(corpus_named):
    guard(wire_id(nm) == wid, f"corpus named tuple ({nm},0x{wid:04X}) reproduced")

# ---------- (1b) all v141 NAMES entries reproduce ----------
print("\n[1b] hash reproduces every entry in the v141 protocol NAMES table")
V141 = "current/pf_login_game_server_v141.py"
NAMES_PAIRS = []
if os.path.exists(V141):
    src = open(V141, encoding="utf-8").read()
    consts = {m.group(1): int(m.group(2), 16)
              for m in re.finditer(r"^([A-Z][A-Z0-9_]+)\s*=\s*(0x[0-9A-Fa-f]+)\s*$", src, re.M)}
    mnames = re.search(r"NAMES\s*=\s*\{(.*?)\n\}", src, re.S)
    if mnames:
        for em in re.finditer(r'(0x[0-9A-Fa-f]+|[A-Z][A-Z0-9_]+)\s*:\s*"([^"]+)"', mnames.group(1)):
            k = em.group(1); nm = em.group(2)
            val = int(k, 16) if k.startswith("0x") else consts.get(k)
            if val is not None:
                NAMES_PAIRS.append((val, nm))
    bad = [(nm, v) for v, nm in NAMES_PAIRS if wire_id(nm) != v]
    guard(len(NAMES_PAIRS) >= 40, f"v141 NAMES parsed ({len(NAMES_PAIRS)} entries)")
    guard(not bad, f"all {len(NAMES_PAIRS)} v141 NAMES entries hash-match byte-exact ({len(bad)} mismatch)")
else:
    print("  SKIP  v141 protocol file not found; NAMES cross-check skipped")

names_table_ids = {v for v, _ in NAMES_PAIRS}

# ---------- string extraction for collision bound ----------
strings = set()
for m in re.finditer(rb"[\x20-\x7e]{3,48}", data):
    strings.add(m.group(0))
ident_re = re.compile(rb"^[A-Za-z_][A-Za-z0-9_]*$")

def collisions(target):
    allc = [s for s in strings if wire_id(s.decode("latin1")) == target]
    identc = [s for s in allc if ident_re.match(s)]
    return allc, identc

md = Cs(CS_ARCH_X86, CS_MODE_32)

def thunk_ok(lit_bytes, expect_id):
    """Find the single push of the name literal, disasm the registration thunk,
    confirm the round-62 byte shape and return the id-slot VA."""
    off = data.find(lit_bytes + b"\x00")
    if off < 0:
        return None, "literal not found"
    lit_va = off_to_va(off)
    push = b"\x68" + struct.pack("<I", lit_va)
    if data.count(push) != 1:
        return None, f"push of literal not unique ({data.count(push)})"
    poff = data.find(push)
    pva = off_to_va(poff)
    insns = list(md.disasm(data[poff:poff + 40], pva))
    seq = [(i.mnemonic, i.op_str) for i in insns[:6]]
    slot = None
    ok = (
        len(seq) >= 6
        and seq[0] == ("push", f"0x{lit_va:x}")
        and seq[1][0] == "call"
        and seq[2] == ("mov", "ecx, eax")
        and seq[3][0] == "call"
        and seq[4][0] == "mov" and seq[4][1].endswith(", ax") and seq[4][1].startswith("word ptr [0x")
        and seq[5][0] == "ret"
    )
    if ok:
        c1 = insns[1].op_str  # once-init 0x89c080
        c2 = insns[3].op_str  # id-assign 0x89bd00
        slot = seq[4][1]
        ok = (c1 == "0x89c080" and c2 == "0x89bd00")
        if not ok:
            return None, f"thunk calls unexpected targets ({c1},{c2})"
    else:
        return None, f"thunk byte shape drift: {seq}"
    return slot, "ok"

# ---------- (2) resolution ----------
print("\n[2] resolve unnamed golden ids to unique in-image name literals")
RESOLVED = [
    (0x1B40, "LogoutVital"),
    (0x36DB, "DeleteActorVital"),
    (0xAC52, "Channel_LocalTalkMessageVital"),
]
for wid, name in RESOLVED:
    guard(wire_id(name) == wid, f"hash({name}) == 0x{wid:04X}")
    guard(wid not in names_table_ids, f"0x{wid:04X} absent from v141 NAMES (was decoded as bare hex)")
    guard((wid, f"0x{wid:04X}") in corpus_unnamed, f"0x{wid:04X} appears UNNAMED in golden corpus")
    allc, identc = collisions(wid)
    identc_names = sorted({s.decode('latin1') for s in identc})
    guard(identc_names == [name],
          f"0x{wid:04X}: unique identifier-style preimage among {len(strings)} image strings == {name} (all-collisions={len(allc)})")
    slot, why = thunk_ok(name.encode("latin1"), wid)
    guard(slot is not None,
          f"0x{wid:04X}: registration thunk byte-exact (push;call 0x89c080;mov ecx,eax;call 0x89bd00;mov {slot or '?'};ret) [{why}]")

# ---------- (3) semantic corroboration ----------
print("\n[3] golden-frame hypothesis labels corroborate resolved names")
SEM = {0x1B40: "LOGOUT", 0x36DB: "DELETE_ACTOR", 0xAC52: "CHAT_INPUT"}
corpus_text = "\n".join(open(f, encoding="utf-8", errors="replace").read() for f in corpus_files)
for wid, token in SEM.items():
    hit = re.search(rf"0x{wid:04X}'\).*?\n.*?HYP_[A-Z0-9_]*{token}", corpus_text)
    guard(hit is not None, f"0x{wid:04X} golden frame labelled HYP_..._{token}_...")

print("\n== RESULT ==")
if FAILS:
    print(f"FAIL ({len(FAILS)} guard(s) drifted)")
    sys.exit(1)
print("PASS - all guards reproduced")
sys.exit(0)
