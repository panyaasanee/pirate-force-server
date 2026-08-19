#!/usr/bin/env python3
"""NAMES-FOLD-002 - prove (or refuse) the LITERAL -> SLOT half of the admission
rule for candidate Vital names, statically, with no disassembler.

WHAT QUESTION THIS ANSWERS
--------------------------
pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv lists 327 candidate
(id, name) pairs recovered from client strings.  Every one of them satisfies
condition (a) of docs/PF_VITAL_NAMES.json rule (4): wire_id(name) == id.
NOBODY had ever checked condition (b): that the name is a *unique* identifier
string literal in GameClient/GameClient.local.bin whose single push sits in the
round-62 registration thunk, and which id-slot that thunk writes.

This tool checks (b) for all 327, byte-exactly, and sorts them into four tiers
whose sizes are pinned as numeric guards so the next round detects drift.

WHY NO DISASSEMBLER
-------------------
tools/pf_vital_id_resolve_static.py needs capstone.  The bash sandbox has no
capstone, and - more important - round 83 settled that we do not trust "I swept
the whole image" claims from a linear disassembler.  This tool never decodes an
instruction stream.  It looks for one exact byte template at byte offsets that
it computes itself, and every offset it reports is backed by the raw bytes.

THE ACCEPTED BYTE SHAPE (written down, on purpose, so it can be argued with)
---------------------------------------------------------------------------
A registration thunk is accepted if and only if these bytes are CONTIGUOUS,
in this order, starting at some file offset p that maps into a PE section:

    p + 0   68 <lit_va : u32 LE>          push  offset <name literal>
    p + 5   E8 <rel32>                    call  ONCE_INIT   (must resolve to 0x89C080)
    p + 10  8B C8                         mov   ecx, eax
    p + 12  E8 <rel32>                    call  ID_ASSIGN   (must resolve to 0x89BD00)
    p + 17  one of
              66 A3 <slot_va : u32 LE>    mov   word ptr [slot], ax   (A3 short form)
              66 89 05 <slot_va : u32 LE> mov   word ptr [slot], ax   (ModRM form)
    then    C3                            ret

Call targets are resolved as (VA of the instruction after the call) + rel32,
masked to 32 bits, and must equal the two constants EXACTLY.

WHAT IS DELIBERATELY *NOT* ACCEPTED (do not relax these without a finding):
  * no gaps, no padding, no NOPs between the seven steps - the three names
    round 62 proved are byte-contiguous, so a gap-tolerant matcher would only
    ever buy us shapes nobody has ever seen;
  * no other call target, no other store width, no store to a register;
  * `ret n` is not accepted, only the bare C3;
  * the push must carry the literal's own VA - we never match "some push near
    the string".
The only latitude in the whole matcher is the two encodings of the 16-bit
store, which are the same instruction; as it happens the image uses 66 A3 for
all 519 thunks, and the 66 89 05 arm has never fired.  It is kept because it is
the same instruction and dropping it would make the rule an accident of one
compiler run - but the guard THUNKS_MODRM_FORM == 0 records that it is unused,
so if it ever fires we find out instead of quietly widening.

A NAME LITERAL is: the exact ASCII bytes of the name, NUL-terminated, whose
preceding byte is NOT an identifier character.  The "preceding byte" rule is
what stops "CBuffVital" from matching the tail of "AVCBuffVital".

THE FOUR TIERS
--------------
  PROVEN      exactly 1 literal occurrence, exactly 1 push of that literal in
              the whole image, and that push is a complete thunk.  -> id_slot_va
  AMBIGUOUS   literal occurs more than once, OR the literal is pushed from more
              than one site, OR more than one thunk claims it.
  NO_THUNK    literal found, but no site matching the template.
  NO_LITERAL  the name is not in the image as a standalone NUL-terminated
              identifier literal at all.

The "pushed from exactly one site" clause is condition (b) of
docs/PF_VITAL_NAMES.json rule (4) taken literally ("the single push of that
literal").  It is the reason 37 candidates sit in AMBIGUOUS even though each of
them has exactly ONE well-formed thunk: their literal is ALSO pushed by a
string-table constructor around 0x0042xxxx (shape `push <lit>; lea ecx,[esp+N];
call ds:[0xC3B480]`), which is not a registration site and does not touch an
id-slot.  Admitting them would mean amending rule (4)(b) in the JSON header,
which is a chief decision and a separate round - not something this tool may
decide by loosening a threshold.  See reports/PF_NAMES_FOLD002_*.md.

ACCEPTANCE TEST (this runs FIRST; if it fails, ignore every other number here)
-----------------------------------------------------------------------------
The three names PF-NAMEID-RESOLVE-001 pinned with capstone in round 62 must
come out of this capstone-free matcher with the identical id-slot VAs:
    LogoutVital                    -> 0x0108207C
    DeleteActorVital               -> 0x01081FD0
    Channel_LocalTalkMessageVital  -> 0x01084458

Usage:
    python3 tools/pf_vital_name_thunk_static.py [--list TIER] [binary] [tsv]
Exit 0 = every guard reproduced.  Nonzero = something drifted.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pf_vital_names import (  # pure stdlib, no side effects
    VitalNamesError,
    load_names_table,
    wire_id,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BIN = ROOT.parent / "GameClient" / "GameClient.local.bin"
DEFAULT_TSV = ROOT.parent / "pf_bridge" / "VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv"

EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
EXPECT_IMAGE_BASE = 0x00400000

ONCE_INIT = 0x89C080
ID_ASSIGN = 0x89BD00

# ---- numeric guards, pinned round 85 -------------------------------------
EXPECT_THUNKS_TOTAL = 519          # registration thunks in the whole image
EXPECT_THUNKS_MODRM = 0            # thunks using the 66 89 05 store form
EXPECT_CANDIDATES = 327
EXPECT_HASH_MISMATCH = 0
EXPECT_TIERS = {
    "PROVEN": 273,
    "AMBIGUOUS": 37,
    "NO_THUNK": 15,
    "NO_LITERAL": 2,
}
EXPECT_AMBIG_REASONS = {
    "literal occurs more than once": 0,
    "literal pushed from more than one site": 37,
    "more than one thunk claims the literal": 0,
}
# PROVEN candidates whose id docs/PF_VITAL_NAMES.json already holds, and the
# rest.  BEFORE the round-85 fold these read 27 / 246: 27 of the 273 PROVEN ids
# were already in the table (and all 27 agreed name-for-name, which is the
# independent corroboration that the tsv and the table were describing the same
# binary).  The fold added the other 246, so the steady state is 273 / 0 - and
# a nonzero EXPECT_PROVEN_NEW again means the tsv grew a name the table lacks.
EXPECT_PROVEN_ALREADY_IN_TABLE = 273
EXPECT_PROVEN_NEW = 0

ACCEPTANCE = {
    "LogoutVital": 0x0108207C,
    "DeleteActorVital": 0x01081FD0,
    "Channel_LocalTalkMessageVital": 0x01084458,
}

IDENT_BYTES = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"
)

FAILS = []


def guard(cond, msg):
    if cond:
        print(f"  PASS  {msg}")
    else:
        print(f"  FAIL  {msg}")
        FAILS.append(msg)
    return bool(cond)


# ==========================================================================
# PE image (same header walk as tools/pf_vital_id_resolve_static.py, minus
# capstone; kept deliberately verbose so the offsets can be checked by hand)
# ==========================================================================
class Image:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        data = self.data
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        coff = e_lfanew + 4
        nsec = struct.unpack_from("<H", data, coff + 2)[0]
        opt_size = struct.unpack_from("<H", data, coff + 16)[0]
        opt = coff + 20
        self.image_base = struct.unpack_from("<I", data, opt + 28)[0]
        sect = opt + opt_size
        self.sections = []
        for i in range(nsec):
            o = sect + i * 40
            name = data[o : o + 8].rstrip(b"\0").decode("latin1")
            vsize = struct.unpack_from("<I", data, o + 8)[0]
            vaddr = struct.unpack_from("<I", data, o + 12)[0]
            rsize = struct.unpack_from("<I", data, o + 16)[0]
            praw = struct.unpack_from("<I", data, o + 20)[0]
            self.sections.append((name, vaddr, vsize, praw, rsize))

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest().upper()

    def off_to_va(self, off):
        for _name, vaddr, _vsize, praw, rsize in self.sections:
            if praw <= off < praw + rsize:
                return self.image_base + vaddr + (off - praw)
        return None

    def va_to_off(self, va):
        for _name, vaddr, _vsize, praw, rsize in self.sections:
            start = self.image_base + vaddr
            if start <= va < start + rsize:
                return praw + (va - start)
        return None

    # ---- literals -------------------------------------------------------
    def literal_vas(self, name: str):
        """VAs of every standalone NUL-terminated occurrence of `name`."""
        needle = name.encode("latin1") + b"\x00"
        data = self.data
        out = []
        start = 0
        while True:
            off = data.find(needle, start)
            if off < 0:
                break
            start = off + 1
            if off > 0 and data[off - 1] in IDENT_BYTES:
                continue  # tail of a longer identifier, not its own literal
            va = self.off_to_va(off)
            if va is not None:
                out.append(va)
        return out

    def push_sites(self, lit_va: int):
        """File offsets of every `68 <lit_va>` in the image."""
        needle = b"\x68" + struct.pack("<I", lit_va)
        data = self.data
        out = []
        start = 0
        while True:
            off = data.find(needle, start)
            if off < 0:
                break
            start = off + 1
            if self.off_to_va(off) is not None:
                out.append(off)
        return out

    # ---- the one byte template ------------------------------------------
    def match_thunk(self, off: int):
        """Return (lit_va, slot_va, thunk_va, store_form) or None.

        Matches EXACTLY the shape documented in this module's docstring.
        """
        data = self.data
        if off + 24 > len(data):
            return None
        if data[off] != 0x68:
            return None
        va = self.off_to_va(off)
        if va is None:
            return None
        lit_va = struct.unpack_from("<I", data, off + 1)[0]
        if data[off + 5] != 0xE8:
            return None
        if ((va + 10 + struct.unpack_from("<i", data, off + 6)[0]) & 0xFFFFFFFF) != ONCE_INIT:
            return None
        if data[off + 10 : off + 12] != b"\x8b\xc8":
            return None
        if data[off + 12] != 0xE8:
            return None
        if ((va + 17 + struct.unpack_from("<i", data, off + 13)[0]) & 0xFFFFFFFF) != ID_ASSIGN:
            return None
        if data[off + 17 : off + 19] == b"\x66\xa3":
            slot = struct.unpack_from("<I", data, off + 19)[0]
            end, form = off + 23, "A3"
        elif data[off + 17 : off + 20] == b"\x66\x89\x05":
            slot = struct.unpack_from("<I", data, off + 20)[0]
            end, form = off + 24, "MODRM"
        else:
            return None
        if end >= len(data) or data[end] != 0xC3:
            return None
        return lit_va, slot, va, form

    def scan_all_thunks(self):
        """Every registration thunk in the image, keyed by pushed literal VA."""
        by_literal = {}
        forms = {"A3": 0, "MODRM": 0}
        data = self.data
        off = 0
        while True:
            off = data.find(b"\x68", off)
            if off < 0:
                break
            hit = self.match_thunk(off)
            off += 1
            if hit is None:
                continue
            lit_va, slot, thunk_va, form = hit
            by_literal.setdefault(lit_va, []).append((thunk_va, slot))
            forms[form] += 1
        return by_literal, forms

    def read_cstring(self, va: int, limit: int = 256):
        off = self.va_to_off(va)
        if off is None:
            return None
        end = self.data.find(b"\x00", off)
        if end < 0 or end - off > limit:
            return None
        return self.data[off:end].decode("latin1")


# ==========================================================================
# candidate list
# ==========================================================================
def load_candidates(path: Path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        rows.append((int(parts[0], 16), parts[1]))
    return rows


def classify(image: Image, thunks_by_literal: dict, candidates):
    """Sort candidates into the four tiers.  Pure function of the image."""
    results = []
    for ident, name in candidates:
        row = {
            "id": ident,
            "name": name,
            "hash_ok": wire_id(name) == ident,
            "literal_vas": image.literal_vas(name),
            "push_sites": [],
            "thunks": [],
            "id_slot_va": None,
            "tier": None,
            "why": "",
        }
        lits = row["literal_vas"]
        if not lits:
            row["tier"], row["why"] = "NO_LITERAL", "no standalone NUL-terminated literal"
            results.append(row)
            continue
        if len(lits) > 1:
            row["tier"] = "AMBIGUOUS"
            row["why"] = "literal occurs more than once"
            results.append(row)
            continue
        lit_va = lits[0]
        row["push_sites"] = [image.off_to_va(o) for o in image.push_sites(lit_va)]
        row["thunks"] = list(thunks_by_literal.get(lit_va, []))
        if not row["thunks"]:
            row["tier"] = "NO_THUNK"
            row["why"] = f"literal at 0x{lit_va:08X} pushed {len(row['push_sites'])}x, no thunk shape"
        elif len(row["thunks"]) > 1:
            row["tier"] = "AMBIGUOUS"
            row["why"] = "more than one thunk claims the literal"
        elif len(row["push_sites"]) != 1:
            row["tier"] = "AMBIGUOUS"
            row["why"] = "literal pushed from more than one site"
            # recorded, but NOT admitted - see module docstring
            row["thunk_slot_if_admitted"] = row["thunks"][0][1]
        else:
            row["tier"] = "PROVEN"
            row["id_slot_va"] = row["thunks"][0][1]
            row["why"] = (
                f"literal 0x{lit_va:08X} unique, single push at "
                f"0x{row['push_sites'][0]:08X} is a complete thunk"
            )
        results.append(row)
    return results


# ==========================================================================
def main(argv):
    argv = list(argv)
    want_list = None
    if "--list" in argv:
        i = argv.index("--list")
        want_list = argv[i + 1]
        del argv[i : i + 2]
    binary = Path(argv[1]) if len(argv) > 1 else DEFAULT_BIN
    tsv = Path(argv[2]) if len(argv) > 2 else DEFAULT_TSV

    print("== NAMES-FOLD-002 literal->slot static verifier (no disassembler) ==")
    print(f"binary : {binary}")
    print(f"tsv    : {tsv}")

    image = Image(binary)
    guard(image.sha256 == EXPECT_SHA,
          f"binary SHA256 pinned == {EXPECT_SHA[:16]}... (got {image.sha256[:16]}...)")
    guard(image.image_base == EXPECT_IMAGE_BASE,
          f"ImageBase == 0x{EXPECT_IMAGE_BASE:08X} (got 0x{image.image_base:08X})")

    # ---------- [0] ACCEPTANCE: reproduce the three capstone-era pins ----------
    print("\n[0] ACCEPTANCE - reproduce the three round-62 pins without capstone")
    print("    (if any of these fails, every number below is void)")
    thunks_by_literal, forms = image.scan_all_thunks()
    acceptance_ok = True
    for name, want_slot in ACCEPTANCE.items():
        lits = image.literal_vas(name)
        pushes = image.push_sites(lits[0]) if len(lits) == 1 else []
        found = thunks_by_literal.get(lits[0], []) if len(lits) == 1 else []
        got = found[0][1] if len(found) == 1 else None
        acceptance_ok &= guard(
            len(lits) == 1 and len(pushes) == 1 and got == want_slot,
            f"{name}: unique literal + single push + thunk -> id-slot "
            f"0x{want_slot:08X} (got {'0x%08X' % got if got is not None else None}, "
            f"{len(lits)} literal(s), {len(pushes)} push(es))",
        )
    if not acceptance_ok:
        print("\n== RESULT ==\nFAIL (acceptance test failed - matcher is wrong, results discarded)")
        return 1

    # ---------- [1] the thunk universe ----------
    print("\n[1] registration-thunk universe in the image")
    total = sum(len(v) for v in thunks_by_literal.values())
    slots = [slot for sites in thunks_by_literal.values() for _va, slot in sites]
    guard(total == EXPECT_THUNKS_TOTAL,
          f"{total} registration thunks match the byte template (pinned {EXPECT_THUNKS_TOTAL})")
    guard(len(thunks_by_literal) == total,
          f"every thunk pushes its own literal: {len(thunks_by_literal)} distinct literals for {total} thunks")
    guard(len(set(slots)) == total,
          f"every thunk writes its own id-slot: {len(set(slots))} distinct slots for {total} thunks")
    guard(forms["MODRM"] == EXPECT_THUNKS_MODRM,
          f"the 66 89 05 store form is unused in this image "
          f"({forms['MODRM']} thunk(s), pinned {EXPECT_THUNKS_MODRM}; 66 A3 form: {forms['A3']})")

    # ---------- [2] candidates ----------
    print("\n[2] candidate table")
    candidates = load_candidates(tsv)
    guard(len(candidates) == EXPECT_CANDIDATES,
          f"{len(candidates)} candidates parsed from the tsv (pinned {EXPECT_CANDIDATES})")
    bad_hash = [(n, i) for i, n in candidates if wire_id(n) != i]
    guard(len(bad_hash) == EXPECT_HASH_MISMATCH,
          f"condition (a) HASH MATCH holds for all candidates "
          f"({len(bad_hash)} mismatch, pinned {EXPECT_HASH_MISMATCH})"
          + (f" -> {bad_hash[:3]}" if bad_hash else ""))
    dup_ids = len(candidates) - len({i for i, _ in candidates})
    guard(dup_ids == 0, f"no duplicate id in the candidate table ({dup_ids} duplicate(s))")

    # ---------- [3] tiers ----------
    print("\n[3] condition (b) LITERAL -> SLOT, tier counts")
    rows = classify(image, thunks_by_literal, candidates)
    counts = {tier: 0 for tier in EXPECT_TIERS}
    for row in rows:
        counts[row["tier"]] += 1
    for tier, expect in EXPECT_TIERS.items():
        guard(counts[tier] == expect, f"{tier:<11} = {counts[tier]:>3} (pinned {expect})")
    guard(sum(counts.values()) == len(candidates),
          f"tiers partition the candidate table ({sum(counts.values())} == {len(candidates)})")

    reasons = {}
    for row in rows:
        if row["tier"] == "AMBIGUOUS":
            reasons[row["why"]] = reasons.get(row["why"], 0) + 1
    for why, expect in EXPECT_AMBIG_REASONS.items():
        guard(reasons.get(why, 0) == expect,
              f"AMBIGUOUS because '{why}' = {reasons.get(why, 0)} (pinned {expect})")

    proven = [r for r in rows if r["tier"] == "PROVEN"]
    guard(all(r["id_slot_va"] for r in proven),
          f"every PROVEN row carries an id-slot VA ({sum(1 for r in proven if not r['id_slot_va'])} without)")
    guard(len({r["id_slot_va"] for r in proven}) == len(proven),
          f"PROVEN rows do not share an id-slot ({len({r['id_slot_va'] for r in proven})} slots for {len(proven)} rows)")

    # ---------- [4] agreement with the project names table ----------
    print("\n[4] agreement with docs/PF_VITAL_NAMES.json (the single home)")
    table = None
    try:
        table = load_names_table()
    except VitalNamesError as exc:
        guard(False, f"names table loads [{exc}]")
    if table is not None:
        already = [r for r in proven if r["id"] in table.by_id]
        new = [r for r in proven if r["id"] not in table.by_id]
        guard(len(already) == EXPECT_PROVEN_ALREADY_IN_TABLE,
              f"{len(already)} PROVEN ids were already in the table "
              f"(pinned {EXPECT_PROVEN_ALREADY_IN_TABLE})")
        disagree = [
            (r["id"], r["name"], table.by_id[r["id"]]["name"])
            for r in already
            if table.by_id[r["id"]]["name"] != r["name"]
        ]
        guard(not disagree,
              f"every overlapping id carries the identical name in both "
              f"({len(disagree)} disagreement(s))" + (f" -> {disagree[:3]}" if disagree else ""))
        guard(len(new) == EXPECT_PROVEN_NEW,
              f"{len(new)} PROVEN ids are new to the table (pinned {EXPECT_PROVEN_NEW})")

        # every id_slot_va the table publishes must be what the binary writes
        published = [e for e in table.entries if e.get("id_slot_va")]
        by_name = {r["name"]: r for r in rows}
        drift = []
        for entry in published:
            row = by_name.get(entry["name"])
            if row is None or row["id_slot_va"] is None:
                drift.append((entry["name"], entry["id_slot_va"], None))
            elif int(entry["id_slot_va"], 16) != row["id_slot_va"]:
                drift.append((entry["name"], entry["id_slot_va"], "0x%08X" % row["id_slot_va"]))
        guard(not drift,
              f"all {len(published)} published id_slot_va values are the slot the binary "
              f"thunk writes ({len(drift)} drift)" + (f" -> {drift[:3]}" if drift else ""))

    # ---------- optional listing (so the report can be re-derived) ----------
    if want_list:
        print(f"\n[--list {want_list}]")
        for row in rows:
            if row["tier"] == want_list or want_list == "ALL":
                slot = "0x%08X" % row["id_slot_va"] if row["id_slot_va"] else "-"
                print(f"  0x{row['id']:04X}\t{row['name']}\t{row['tier']}\t{slot}\t{row['why']}")

    print("\n== RESULT ==")
    if FAILS:
        print(f"FAIL ({len(FAILS)} guard(s) drifted)")
        return 1
    print("PASS - all guards reproduced")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
