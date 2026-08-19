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

NAMES-HOME-001 rewiring: the id->name table this tool verifies is no longer
hardcoded here and is no longer read out of v141. The primary source is now
docs/PF_VITAL_NAMES.json (the project's single home for Vital names, loaded via
tools/pf_vital_names.py). Section [1c] proves that table hash-clean and a strict
superset of the frozen v141 NAMES dict, and section [2] takes both the resolved
names and their expected id-slot VAs FROM that table. The v141 parse is kept, as
a read-only guard only: v141 is a frozen delivery snapshot (the comparison
reference for the rewrite), never a place to add a name.

SCOPE OF SECTIONS [2] AND [3] - RESOLVE-SCOPE-001 (round 85), read this before
changing the selector
-------------------------------------------------------------------------------
Between NAMES-HOME-001 and NAMES-FOLD-002 the names table grew 52 -> 298
entries, and sections [2]/[3] used to select their targets as "every id in the
table that v141 never had". That selector was written when those two phrasings
described the same three ids; after the fold it described 249, and it made this
tool assert, of 246 names that were never claimed to be in the corpus at all,
that they "appear UNNAMED in the golden corpus". They do not, so the tool went
red - not because a fact drifted, but because the question had silently widened.

PF-NAMEID-RESOLVE-001 is a claim about exactly THREE wire ids: the ids the
golden decoder printed as bare hex because v141 had no name for them. That -
"the id is in the golden corpus AND v141 has no name for it" - is the selector
used here, and it is checked against the independent provenance field
(source == "PF-NAMEID-RESOLVE-001 ...") so the two ways of saying it cannot
drift apart. The target count is PINNED at RESOLVE_TARGET_COUNT == 3 and the
target ids at RESOLVE_TARGET_IDS: a future round that resolves a fourth
bare-hex corpus id turns this tool RED and has to widen the pin deliberately,
in the same change that publishes the finding. Silence is not an option here,
which is the whole point of a pin.

The 246 NAMES-FOLD-002 names are NOT unguarded by this narrowing: their
literal -> slot -> id-slot-VA evidence is produced and pinned by
tools/pf_vital_name_thunk_static.py (no disassembler) and asserted by
tests/test_vital_names_table.py. Section [1c] here additionally requires every
one of them to carry a non-null id_slot_va, so a fold entry can never be
admitted on hash evidence alone.

Under pytest: tests/test_vital_id_resolve_scope.py runs this file for real (no
mocks) and re-derives the same scope from the JSON, so the "no test imports it,
so it goes red only on the day someone runs the gate by hand" failure mode that
RESOLVE-SCOPE-001 was created to clean up cannot come back.

Usage:  py -3 tools/pf_vital_id_resolve_static.py [path-to-GameClient.local.bin] [path-to-capture_v141]
Exit 0 = all guards reproduced; nonzero = a guard drifted.
"""
import os, re, sys, struct, hashlib, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pf_capture_corpus import (        # pure stdlib, no side effects
    CaptureCorpus,
    CaptureCorpusError,
)
from pf_vital_names import (            # pure stdlib, no side effects
    DEFAULT_TABLE,
    VitalNamesError,
    cross_check_v141,
    load_names_table,
    parse_v141_names,
    wire_id,                            # round-62 algorithm, single definition
)

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    sys.exit("capstone required: pip install capstone")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))


def _default_bin():
    """Same staging fallback the other static tools use.

    RESOLVE-SCOPE-001 (round 85): this tool used to hardcode the relative string
    "GameClient/GameClient.local.bin", so `py -3 tools/pf_vital_id_resolve_static.py`
    with no argument died with FileNotFoundError from the repo root - the client
    lives one directory ABOVE the repo.  The tool was therefore only ever run with
    an explicit path, which is part of why its scope drift went unnoticed.
    """
    for cand in (
        os.path.join(_ROOT, "..", "GameClient", "GameClient.local.bin"),
        "GameClient/GameClient.local.bin",
        os.path.join(_ROOT, "GameClient", "GameClient.local.bin"),
        os.path.join(_ROOT, "packages", ".v134_staging_20260815_0355",
                     "GameClient.local.bin"),
    ):
        if os.path.isfile(cand):
            return cand
    return "GameClient/GameClient.local.bin"


BIN = sys.argv[1] if len(sys.argv) > 1 else _default_bin()
CORPUS = sys.argv[2] if len(sys.argv) > 2 else "capture_v141"
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

# ---------------------------------------------------------------------------
# RESOLVE-SCOPE-001 pins.  See "SCOPE OF SECTIONS [2] AND [3]" in the docstring
# for why these exist; the short version is that the selector for [2]/[3] must
# describe PF-NAMEID-RESOLVE-001's three ids and nothing else, and must go red -
# never quietly wider - when the names table grows.
# ---------------------------------------------------------------------------
RESOLVE_SOURCE_PREFIX = "PF-NAMEID-RESOLVE-001"   # provenance in the JSON table
RESOLVE_TARGET_COUNT = 3                          # the claim is about 3 ids
RESOLVE_TARGET_IDS = (0x1B40, 0x36DB, 0xAC52)     # LogoutVital/DeleteActor/Chat
FOLD_SOURCE_PREFIX = "NAMES-FOLD-002"             # the fold bucket (may grow)
FOLD_ENTRY_MIN = 246                              # admitted round 85
V141_SOURCE = "v141_NAMES"                        # frozen snapshot provenance
V141_ENTRY_COUNT = 49                             # frozen: v141 cannot be edited
TABLE_ENTRY_MIN = 298                             # 49 v141 + 3 resolved + 246 fold

# The three semantic tokens section [3] expects to find next to each resolved id
# in the golden frames.  Keyed by id so [3] cannot silently skip a target.
SEM = {0x1B40: "LOGOUT", 0x36DB: "DELETE_ACTOR", 0xAC52: "CHAT_INPUT"}


def resolve_scope(table, v141_ids):
    """Return (corpus_side, source_side) - the two independent spellings of the
    PF-NAMEID-RESOLVE-001 target set, as sorted id lists.

    corpus_side  the claim itself: the id appears in the golden corpus AND the
                 frozen v141 NAMES dict has no name for it, i.e. exactly the
                 ids the golden decoder had to print as bare hex.
    source_side  the provenance field, recorded independently by whoever added
                 the entry to docs/PF_VITAL_NAMES.json.

    They must be equal.  If they are not, either a name was filed under the
    wrong finding or in_golden_corpus is wrong - both are bugs in the table,
    and neither may be papered over by preferring one side.
    """
    corpus_side = sorted(
        ident for ident, entry in table.by_id.items()
        if entry.get("in_golden_corpus") and ident not in v141_ids
    )
    source_side = sorted(
        ident for ident, entry in table.by_id.items()
        if str(entry.get("source", "")).startswith(RESOLVE_SOURCE_PREFIX)
    )
    return corpus_side, source_side

FAILS = []
def guard(cond, msg):
    if cond:
        print(f"  PASS  {msg}")
    else:
        print(f"  FAIL  {msg}")
        FAILS.append(msg)

# ---------- hash (round-62 algorithm, signed char, 1-based index) ----------
# wire_id() now lives in tools/pf_vital_names.py so the names table, this
# verifier and tests/test_vital_names_table.py all hash with one definition:
#     uint16 id = ( sum_i (signed char)name[i] * (i+1) ) mod 2^16

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
# CORPUS-PIN-001 (round 82).  This used to be
#     corpus_files = sorted(glob.glob(os.path.join(CORPUS, "*.txt")))
# with CORPUS defaulting to the RELATIVE string "capture_v141", so the set of
# files depended on the caller's working directory, swept in the two live tails
# the server rewrites on every run, and would have silently absorbed any capture
# a mis-configured job dropped into the corpus.  When no explicit corpus is
# given on the command line the pinned name set in docs/PF_CAPTURE_CORPUS.json
# is authoritative; an explicit argument still scans, so ad-hoc corpora keep
# working.
if len(sys.argv) > 2:
    corpus_files = sorted(glob.glob(os.path.join(CORPUS, "*.txt")))
    guard(len(corpus_files) > 0,
          f"golden corpus present ({len(corpus_files)} files under {CORPUS})")
else:
    _set = CaptureCorpus.load()["game_v141_archived"]
    try:
        corpus_files = [str(p) for p in _set.resolve()]
        _corpus_ok, _corpus_why = True, f"{len(corpus_files)} pinned captures, byte-identical"
    except CaptureCorpusError as exc:
        corpus_files, _corpus_ok = [], False
        _corpus_why = " ".join(str(exc).split())[:200]
    guard(_corpus_ok, f"pinned golden corpus intact ({_corpus_why})")
    _strays = _set.strays()
    guard(not _strays,
          f"no capture outside the pinned set ({len(_strays)} stray: {_strays[:3]})")
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

# ---------- (1b) all v141 NAMES entries reproduce (frozen-snapshot guard) ----------
print("\n[1b] hash reproduces every entry in the v141 protocol NAMES table")
print("     (v141 is a FROZEN delivery snapshot, read-only; it is a guard here, not the source)")
V141_PAIRS = []
try:
    V141_PAIRS = [(v, nm) for v, nm, _const in parse_v141_names()]
except VitalNamesError as exc:
    print(f"  SKIP  {exc}; v141 NAMES cross-check skipped")
if V141_PAIRS:
    bad = [(nm, v) for v, nm in V141_PAIRS if wire_id(nm) != v]
    guard(len(V141_PAIRS) >= 40, f"v141 NAMES parsed ({len(V141_PAIRS)} entries)")
    guard(not bad, f"all {len(V141_PAIRS)} v141 NAMES entries hash-match byte-exact ({len(bad)} mismatch)")

v141_ids = {v for v, _ in V141_PAIRS}

# ---------- (1c) docs/PF_VITAL_NAMES.json is the primary id->name source ----------
print("\n[1c] project names table (PRIMARY SOURCE) is hash-clean and covers v141")
TABLE = None
try:
    TABLE = load_names_table()
except VitalNamesError as exc:
    guard(False, f"docs/PF_VITAL_NAMES.json loads and validates [{exc}]")

if TABLE is not None:
    guard(True, f"names table loaded from {DEFAULT_TABLE.name} ({len(TABLE)} entries)")
    guard(len(TABLE) >= TABLE_ENTRY_MIN,
          f"names table holds at least {V141_ENTRY_COUNT} v141 + {RESOLVE_TARGET_COUNT} "
          f"resolved + {FOLD_ENTRY_MIN} folded = {TABLE_ENTRY_MIN} entries "
          f"({len(TABLE)} entries)")
    bad_hash = TABLE.hash_mismatches()
    guard(not bad_hash,
          f"all {len(TABLE)} names-table entries hash-match byte-exact ({len(bad_hash)} mismatch)"
          + (f" -> fix docs/PF_VITAL_NAMES.json: {bad_hash}" if bad_hash else ""))
    cover = cross_check_v141(TABLE, [(v, nm, None) for v, nm in V141_PAIRS]) if V141_PAIRS else []
    guard(not cover,
          f"names table is a superset of v141 NAMES and agrees name-for-name "
          f"({len(cover)} problem(s))" + (f" -> {cover[0]}" if cover else ""))

    # --- provenance partition (RESOLVE-SCOPE-001) ---------------------------
    # Every entry must declare which finding admitted it.  An entry with an
    # unrecognised source is a name nobody can trace, and this tool refuses to
    # let one in silently - a new provenance has to be added here on purpose.
    _known = (V141_SOURCE, RESOLVE_SOURCE_PREFIX, FOLD_SOURCE_PREFIX)
    by_source = {"v141": [], "resolved": [], "fold": [], "unknown": []}
    for _ident, _entry in TABLE.by_id.items():
        _src = str(_entry.get("source", ""))
        if _src == V141_SOURCE:
            by_source["v141"].append(_ident)
        elif _src.startswith(RESOLVE_SOURCE_PREFIX):
            by_source["resolved"].append(_ident)
        elif _src.startswith(FOLD_SOURCE_PREFIX):
            by_source["fold"].append(_ident)
        else:
            by_source["unknown"].append((_ident, _src))
    guard(not by_source["unknown"],
          f"every entry declares a known provenance ({len(by_source['unknown'])} unknown"
          + (f": {by_source['unknown'][:3]}" if by_source["unknown"] else "") + f"); known = {_known}")
    guard(sorted(by_source["v141"]) == sorted(v141_ids) and V141_PAIRS != [],
          f"the {len(by_source['v141'])} entries sourced '{V141_SOURCE}' are EXACTLY the "
          f"{len(v141_ids)} ids the frozen v141 NAMES dict carries (no more, no fewer)")
    guard(len(by_source["v141"]) == V141_ENTRY_COUNT,
          f"v141-sourced entries pinned == {V141_ENTRY_COUNT} (v141 is byte-frozen, this "
          f"number cannot legitimately move) (got {len(by_source['v141'])})")
    # The fold bucket is the ONLY one allowed to grow: NAMES-FOLD-002 admits a
    # name whenever the literal->slot evidence is produced for it, so a floor is
    # the honest guard there.  Every other bucket is pinned exactly.
    guard(len(by_source["fold"]) >= FOLD_ENTRY_MIN,
          f"NAMES-FOLD-002 bucket holds at least the {FOLD_ENTRY_MIN} names round 85 "
          f"admitted ({len(by_source['fold'])}); this is the one bucket allowed to grow")
    fold_no_slot = sorted(
        i for i in by_source["fold"] if not TABLE.by_id[i].get("id_slot_va"))
    guard(not fold_no_slot,
          f"every NAMES-FOLD-002 entry carries a non-null id_slot_va "
          f"({len(fold_no_slot)} without one"
          + (f": {[f'0x{i:04X}={TABLE.name_for(i)}' for i in fold_no_slot[:3]]}" if fold_no_slot else "")
          + ") - a folded name is admitted on literal->slot evidence, never on the hash alone")
    bad_slot = sorted(
        i for i in by_source["fold"] + by_source["resolved"]
        if not re.fullmatch(r"0[xX][0-9A-Fa-f]{6,8}",
                            str(TABLE.by_id[i].get("id_slot_va") or ""))
    )
    guard(not bad_slot,
          f"every id_slot_va outside the v141 bucket is a well-formed VA literal "
          f"({len(bad_slot)} malformed"
          + (f": {[(f'0x{i:04X}', TABLE.by_id[i].get('id_slot_va')) for i in bad_slot[:3]]}" if bad_slot else "") + ")")
    extra = sorted(set(TABLE.by_id) - v141_ids)
    guard(len(extra) == len(TABLE) - V141_ENTRY_COUNT,
          f"names table carries {len(extra)} name(s) v141 never had "
          f"(= {len(TABLE)} - {V141_ENTRY_COUNT}); their literal->slot evidence lives in "
          f"tools/pf_vital_name_thunk_static.py, NOT in section [2] below")

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
print("\n[2] resolve the PF-NAMEID-RESOLVE-001 ids to unique in-image name literals")
print("     (names and expected id-slot VAs are read from docs/PF_VITAL_NAMES.json)")
print("     SCOPE: ids that appear in the golden corpus AND that v141 has no name for.")
print("     Names folded in from the client registry (NAMES-FOLD-002) are NOT in scope")
print("     here - they were never claimed to be in the corpus; their literal->slot")
print("     evidence is pinned by tools/pf_vital_name_thunk_static.py.")

# RESOLVE-SCOPE-001: the target set is the claim, not "everything in the table".
# It is derived two independent ways (corpus membership vs. the provenance field)
# and pinned by count AND by id, so a fourth resolution turns this red instead of
# widening the assertion silently.
RESOLVED = []
if TABLE is not None:
    corpus_side, source_side = resolve_scope(TABLE, v141_ids)
    guard(corpus_side == source_side,
          f"[2] scope agrees two ways: {len(corpus_side)} id(s) are in the golden corpus "
          f"and absent from v141, and {len(source_side)} id(s) are sourced "
          f"'{RESOLVE_SOURCE_PREFIX}...' -> "
          + ("same set" if corpus_side == source_side
             else f"DISAGREE corpus-only={[f'0x{i:04X}' for i in sorted(set(corpus_side)-set(source_side))]} "
                  f"source-only={[f'0x{i:04X}' for i in sorted(set(source_side)-set(corpus_side))]}"))
    guard(len(corpus_side) == RESOLVE_TARGET_COUNT,
          f"[2] target count pinned == {RESOLVE_TARGET_COUNT} (got {len(corpus_side)}). "
          f"PF-NAMEID-RESOLVE-001 is a claim about {RESOLVE_TARGET_COUNT} bare-hex corpus ids; "
          f"if a round resolves another one, widen RESOLVE_TARGET_COUNT/RESOLVE_TARGET_IDS "
          f"in the same change that publishes it")
    guard(tuple(corpus_side) == tuple(sorted(RESOLVE_TARGET_IDS)),
          f"[2] target ids pinned == {[f'0x{i:04X}' for i in sorted(RESOLVE_TARGET_IDS)]} "
          f"(got {[f'0x{i:04X}' for i in corpus_side]})")
    RESOLVED = [
        (ident, TABLE.by_id[ident]["name"], TABLE.by_id[ident].get("id_slot_va"))
        for ident in corpus_side
    ]
else:  # table unreadable: fall back to the round-62 findings so [2] still runs
    RESOLVED = [
        (0x1B40, "LogoutVital", "0x108207C"),
        (0x36DB, "DeleteActorVital", "0x1081FD0"),
        (0xAC52, "Channel_LocalTalkMessageVital", "0x1084458"),
    ]
    guard(len(RESOLVED) == RESOLVE_TARGET_COUNT,
          f"[2] fallback target set is the pinned {RESOLVE_TARGET_COUNT} ids "
          f"(names table unreadable)")

for wid, name, want_slot in RESOLVED:
    guard(wire_id(name) == wid, f"hash({name}) == 0x{wid:04X}")
    guard(wid not in v141_ids, f"0x{wid:04X} absent from v141 NAMES (was decoded as bare hex)")
    guard((wid, f"0x{wid:04X}") in corpus_unnamed, f"0x{wid:04X} appears UNNAMED in golden corpus")
    allc, identc = collisions(wid)
    identc_names = sorted({s.decode('latin1') for s in identc})
    guard(identc_names == [name],
          f"0x{wid:04X}: unique identifier-style preimage among {len(strings)} image strings == {name} (all-collisions={len(allc)})")
    slot, why = thunk_ok(name.encode("latin1"), wid)
    guard(slot is not None,
          f"0x{wid:04X}: registration thunk byte-exact (push;call 0x89c080;mov ecx,eax;call 0x89bd00;mov {slot or '?'};ret) [{why}]")
    got_slot = re.search(r"0x[0-9a-fA-F]+", slot).group(0) if slot else None
    guard(got_slot is not None and want_slot is not None
          and int(got_slot, 16) == int(want_slot, 16),
          f"0x{wid:04X}: id-slot VA in docs/PF_VITAL_NAMES.json ({want_slot}) == the slot the "
          f"binary thunk writes ({got_slot})")

# ---------- (3) semantic corroboration ----------
print("\n[3] golden-frame hypothesis labels corroborate resolved names")
print(f"     SCOPE: the same {RESOLVE_TARGET_COUNT} ids as section [2] (SEM is keyed by id,")
print("     so a target without an expected label is a FAIL, never a silent skip).")
resolved_ids = [wid for wid, _n, _s in RESOLVED]
guard(sorted(SEM) == sorted(resolved_ids),
      f"[3] every section-[2] target has an expected hypothesis token "
      f"(SEM covers {[f'0x{i:04X}' for i in sorted(SEM)]}, targets are "
      f"{[f'0x{i:04X}' for i in sorted(resolved_ids)]})")
corpus_text = "\n".join(open(f, encoding="utf-8", errors="replace").read() for f in corpus_files)
for wid in resolved_ids:
    token = SEM.get(wid)
    if token is None:      # already FAILed above; do not pretend it passed
        continue
    hit = re.search(rf"0x{wid:04X}'\).*?\n.*?HYP_[A-Z0-9_]*{token}", corpus_text)
    guard(hit is not None, f"0x{wid:04X} golden frame labelled HYP_..._{token}_...")

print("\n== RESULT ==")
if FAILS:
    print(f"FAIL ({len(FAILS)} guard(s) drifted)")
    sys.exit(1)
print("PASS - all guards reproduced")
sys.exit(0)
