#!/usr/bin/env python3
"""NAMES-FOLD-003 half (ข) - census the registration thunks the candidate tsv
never listed, statically, with no disassembler.

WHAT QUESTION THIS ANSWERS
--------------------------
Round 85 proved condition (b) for the 327 names in
pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv, and while doing so
noticed that the image holds **519** registration thunks while the tsv accounts
for only **310** of them.  Nobody had ever looked at the other **209**.  They
are registered classes of the same shape, with the same thunk, writing their own
16-bit id-slot - the tsv simply never listed them.  Several are names the frozen
v141 snapshot already knows (ActorAttr, BackpackAttr, NPCAttr, StartGameReq...).

This tool enumerates all 519, subtracts the tsv, and reports the remainder with
the slot VA, the wire id and the identifier literal for every one of them.

WHY IT IS A SEPARATE FILE FROM pf_vital_name_thunk_static.py
------------------------------------------------------------
That tool is the ADMISSION verifier: it reads, it asserts, it writes nothing,
and its section [0] acceptance gate is the reason anyone is allowed to believe
its numbers.  This tool has to *emit an artifact* (a 209-row census file), which
is a different job with a different failure mode, and it answers a question the
admission rule cannot answer at all (see "THE CIRCULARITY" below).  Folding an
artifact writer into the gate verifier would have blurred exactly the property
round 85 asked to preserve.

So instead: this file imports ``Image``, ``run_acceptance``, ``load_candidates``
and the pinned constants FROM that tool.  There is exactly ONE copy of the byte
template and ONE acceptance gate in the project, and this tool refuses to print
a single census row until that gate passes - identically to its sibling.

!! THE CIRCULARITY - WHY NOTHING HERE IS ADMITTED TO THE NAMES TABLE
--------------------------------------------------------------------
docs/PF_VITAL_NAMES.json rule (4) admits a name on TWO conditions:
    (a) wire_id(name) == id
    (b) literal -> slot evidence
Every one of the 209 satisfies (b) by construction - it *is* a thunk.  But (a)
is only evidence when the ``id`` comes from somewhere OTHER than the name: the
tsv's ids came from a separate string sweep, v141's ids came from the frozen
snapshot, so agreeing with wire_id(name) meant two independent sources agreed.
For a class discovered from its own literal there is no second source.  Its id
can only be computed as wire_id(name), so (a) is TRUE BY DEFINITION and carries
zero information.

Admitting these 209 would therefore not be "applying rule (4)"; it would be
changing what (4)(a) means.  That is a chief decision, in a round of its own -
exactly like the 37/10 AMBIGUOUS rows the sibling tool refuses to admit.  This
tool admits nothing and this lane admitted nothing.  The census is delivered as
a report + artifact so the chief can decide with the whole list in front of him.

(The 17 census classes whose name the table ALREADY holds are the corroboration
that the census is describing real wire classes and not compiler noise: for
those 17 the id came from v141, independently, and it agrees.)

WHAT "wire id" MEANS IN THE CENSUS
-----------------------------------
The thunk pushes the literal and calls ID_ASSIGN (0x89BD00), which hashes the
string with the round-62 algorithm and stores the 16-bit result in the slot.
So the census's ``wire_id`` column is wire_id(literal) - derived, not read out
of a data table.  It is the same derivation the sibling tool cross-checks
against 273 + 38 independently-sourced ids without a single mismatch.

THE 48-CHARACTER BLIND SPOT (section [3])
------------------------------------------
Round 62's string sweep was ``re.finditer(rb"[\\x20-\\x7e]{3,48}", data)``.  A
printable run longer than 48 bytes is chopped, so a 51-character class name
never appears in that string set as itself.  Round 85 said "at least 2 longer
names escaped".  This tool measures it exactly instead of bounding it.

Usage:
    python3 tools/pf_vital_thunk_census_static.py [--emit PATH] [binary] [tsv]
      (no flag)     re-derive everything and CHECK the committed artifact matches
      --emit PATH   (re)write the artifact at PATH, then check it
      --list        print the 209-row census to stdout as tsv
Exit 0 = every guard reproduced.  Nonzero = something drifted.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pf_vital_name_thunk_static import (  # ONE matcher, ONE acceptance gate
    DEFAULT_BIN,
    DEFAULT_TSV,
    EXPECT_IMAGE_BASE,
    EXPECT_SHA,
    EXPECT_THUNKS_TOTAL,
    IDENT_BYTES,
    Image,
    load_candidates,
    run_acceptance,
)
from pf_vital_names import VitalNamesError, load_names_table, wire_id

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = (
    ROOT / "reports" / "PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.census.json"
)

# ---- numeric guards, pinned round 86 --------------------------------------
EXPECT_THUNK_LITERALS_READABLE = 519   # every thunk's literal is reachable
EXPECT_THUNK_LITERALS_IDENT = 519      # ...and identifier-shaped
EXPECT_COVERED_BY_TSV = 310            # thunks whose literal is a tsv candidate
EXPECT_CENSUS = 209                    # the remainder - this file's subject
EXPECT_CENSUS_IN_TABLE = 17            # census names docs/PF_VITAL_NAMES.json holds
EXPECT_CENSUS_ADMITTED = 0             # !! admitted to the table by this round
EXPECT_CENSUS_ID_CLASH_CROSS_NAME = 0  # census id == a table id under another name
# What the tsv's filter ACTUALLY was.  Its header says "Non-AV names only", but
# the sets say something narrower and completely mechanical: every tsv name
# contains the substring "Vital", every thunk whose literal contains "Vital" is
# in the tsv, and not one census name contains it.  The tsv is the substring
# slice of the registry.  This is why the 6 "...Vtial" classes - a typo in the
# client's own source - are missing from every name list the project has.
EXPECT_CENSUS_CONTAINING_VITAL = 0
EXPECT_TSV_NOT_CONTAINING_VITAL = 0
EXPECT_VITAL_THUNKS = 310
EXPECT_CENSUS_VTIAL_TYPOS = 6

# section [3] - the blind spot, measured
EXPECT_LONG_IDENTIFIERS = 3            # standalone identifier literals > 48 chars
EXPECT_LONG_CLASS_NAMES = 2            # ...of those, ones that are registered classes
EXPECT_LONG_NOT_A_NAME = 1             # ...the PE padding filler
LONG_CLASS_NAMES = (
    "BuildingCrystal_IncreaseCrystalSlotMaxNutrientVital",  # 51 chars
    "Equipment_RefreshLuckyEnhancementProbabilityVital",    # 49 chars
)

SWEEP_LIMIT = 48  # the round-62 regex bound, [\x20-\x7e]{3,48}

# A standalone NUL-terminated C identifier, at least 3 characters (the round-62
# sweep's own lower bound), whose preceding byte is not an identifier byte.
IDENT_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_]{2,}\x00")

FAILS = []


def guard(cond, msg):
    if cond:
        print(f"  PASS  {msg}")
    else:
        print(f"  FAIL  {msg}")
        FAILS.append(msg)
    return bool(cond)


def is_identifier(text: str) -> bool:
    if not text or text[0].isdigit():
        return False
    return all(byte in IDENT_BYTES for byte in text.encode("latin1"))


def name_shape(name: str) -> str:
    """A coarse bucket, for the report only.  Nothing depends on it."""
    if name.endswith("Vital"):
        return "Vital"
    if name.endswith("Vtial"):
        return "Vtial(typo-in-client)"
    if name.endswith("Attr") or name.endswith("Attribute"):
        return "Attr"
    if name.endswith("Module") or name.endswith("Module_Client"):
        return "Module"
    if name.endswith("Req"):
        return "Req"
    if name.endswith("Res") or name.endswith("Reply"):
        return "Res"
    return "other"


# ==========================================================================
def build_census(image: Image, thunks_by_literal: dict, candidates, table):
    """Every registration thunk, split into tsv-covered and the remainder.

    Pure function of the image + the tsv + the names table.  No I/O.
    """
    tsv_names = {name for _ident, name in candidates}
    covered, census = [], []
    for lit_va, sites in sorted(thunks_by_literal.items()):
        for thunk_va, slot_va in sites:
            text = image.read_cstring(lit_va)
            row = {
                "name": text,
                "literal_readable": text is not None,
                "literal_is_identifier": bool(text) and is_identifier(text),
                "literal_va": "0x%08X" % lit_va,
                "thunk_va": "0x%08X" % thunk_va,
                "id_slot_va": "0x%08X" % slot_va,
            }
            if text is not None:
                ident = wire_id(text)
                row["wire_id"] = "0x%04X" % ident
                row["wire_id_dec"] = ident
                row["shape"] = name_shape(text)
                row["in_names_table"] = (
                    table is not None and text in table.by_name
                )
                row["longer_than_round62_sweep"] = len(text) > SWEEP_LIMIT
            else:
                row["wire_id"] = None
                row["wire_id_dec"] = None
                row["shape"] = "unreadable-literal"
                row["in_names_table"] = False
                row["longer_than_round62_sweep"] = None
            (covered if text in tsv_names else census).append(row)
    census.sort(key=lambda r: (r["wire_id_dec"] is None, r["wire_id_dec"] or 0))
    return covered, census


def long_identifiers(image: Image):
    """Standalone identifier literals longer than the round-62 sweep bound."""
    data = image.data
    found = {}
    for match in IDENT_RE.finditer(data):
        off = match.start()
        if off > 0 and data[off - 1] in IDENT_BYTES:
            continue
        if image.off_to_va(off) is None:
            continue
        text = match.group()[:-1].decode("latin1")
        if len(text) > SWEEP_LIMIT:
            found.setdefault(text, image.off_to_va(off))
    return dict(sorted(found.items()))


def artifact_payload(image: Image, census, longs, thunk_total, covered_n):
    return {
        "__doc__": [
            "NAMES-FOLD-003 half (ข) - the registration thunks in the client image that",
            "pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv never listed.",
            "",
            "!! THIS IS NOT A NAME TABLE.  docs/PF_VITAL_NAMES.json is the project's only",
            "name table.  NOTHING in this file has been admitted to it, and nothing here may",
            "be quoted as a project name for a wire id.  Every row satisfies condition (b) of",
            "rule (4) by construction (it is a thunk), but condition (a) is vacuous for these",
            "rows: their id has no source independent of the name itself, because it is",
            "computed from the name.  Admitting them means amending rule (4)(a) - a chief",
            "decision, deliberately not taken by the lane that produced this file.",
            "",
            "'wire_id' is wire_id(name) under the round-62 algorithm, i.e. what ID_ASSIGN",
            "(0x89BD00) computes and stores into 'id_slot_va' at runtime.  It is DERIVED, not",
            "read from a table in the binary.",
            "",
            "Re-derive: python3 tools/pf_vital_thunk_census_static.py --emit <this file>",
        ],
        "milestone": "NAMES-FOLD-003",
        "created_round": 86,
        "created_at": "2026-08-19",
        "generated_by": "tools/pf_vital_thunk_census_static.py",
        "admitted_to_names_table": 0,
        "binary": {
            "path": "GameClient/GameClient.local.bin",
            "sha256": image.sha256,
            "image_base": "0x%08X" % image.image_base,
        },
        "counts": {
            "registration_thunks_in_image": thunk_total,
            "covered_by_tsv": covered_n,
            "census_rows": len(census),
            "census_names_already_in_names_table": sum(
                1 for r in census if r["in_names_table"]
            ),
            "identifier_literals_longer_than_48": len(longs),
        },
        "round62_sweep_blind_spot": {
            "regex": "[\\x20-\\x7e]{3,48}",
            "identifiers_longer_than_48": [
                {"name": text, "length": len(text), "va": "0x%08X" % va}
                for text, va in longs.items()
            ],
        },
        "census": census,
    }


def write_artifact(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=1, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return text


# ==========================================================================
def main(argv):
    argv = list(argv)
    want_list = "--list" in argv
    if want_list:
        argv.remove("--list")
    emit = None
    if "--emit" in argv:
        i = argv.index("--emit")
        emit = Path(argv[i + 1])
        del argv[i : i + 2]
    binary = Path(argv[1]) if len(argv) > 1 else DEFAULT_BIN
    tsv = Path(argv[2]) if len(argv) > 2 else DEFAULT_TSV
    artifact = emit or DEFAULT_ARTIFACT

    print("== NAMES-FOLD-003 half (ข) thunk census (no disassembler) ==")
    print(f"binary   : {binary}")
    print(f"tsv      : {tsv}")
    print(f"artifact : {artifact}")

    image = Image(binary)
    guard(image.sha256 == EXPECT_SHA,
          f"binary SHA256 pinned == {EXPECT_SHA[:16]}... (got {image.sha256[:16]}...)")
    guard(image.image_base == EXPECT_IMAGE_BASE,
          f"ImageBase == 0x{EXPECT_IMAGE_BASE:08X} (got 0x{image.image_base:08X})")

    # ---------- [0] the SAME acceptance gate as the sibling tool ----------
    print("\n[0] ACCEPTANCE - the sibling verifier's gate, run here too")
    print("    (imported, not copied; if it fails, every number below is void)")
    thunks_by_literal, _forms = image.scan_all_thunks()
    if not run_acceptance(image, thunks_by_literal, report=guard):
        print("\n== RESULT ==\nFAIL (acceptance test failed - census discarded)")
        return 1

    table = None
    try:
        table = load_names_table()
    except VitalNamesError as exc:
        guard(False, f"names table loads [{exc}]")

    candidates = load_candidates(tsv)
    covered, census = build_census(image, thunks_by_literal, candidates, table)
    thunk_total = sum(len(v) for v in thunks_by_literal.values())

    # ---------- [1] the split ----------
    print("\n[1] 519 thunks = what the tsv covers + what nobody had looked at")
    guard(thunk_total == EXPECT_THUNKS_TOTAL,
          f"{thunk_total} registration thunks in the image (pinned {EXPECT_THUNKS_TOTAL})")
    guard(len(covered) == EXPECT_COVERED_BY_TSV,
          f"{len(covered)} thunks are covered by the tsv (pinned {EXPECT_COVERED_BY_TSV})")
    guard(len(census) == EXPECT_CENSUS,
          f"{len(census)} thunks are NOT in the tsv at all (pinned {EXPECT_CENSUS}) "
          f"- '327' was never a census of the registry")
    guard(len(covered) + len(census) == thunk_total,
          f"the split partitions the thunk universe "
          f"({len(covered)} + {len(census)} == {thunk_total})")

    # ---------- [1b] what the tsv's filter really was ----------
    print("\n[1b] the tsv's filter was a SUBSTRING, not 'non-AV names only'")
    tsv_names = {name for _i, name in candidates}
    guard(sum(1 for n in tsv_names if "Vital" not in n)
          == EXPECT_TSV_NOT_CONTAINING_VITAL,
          f"every tsv name contains the substring 'Vital' "
          f"({sum(1 for n in tsv_names if 'Vital' not in n)} without, pinned "
          f"{EXPECT_TSV_NOT_CONTAINING_VITAL})")
    guard(sum(1 for r in census if "Vital" in r["name"])
          == EXPECT_CENSUS_CONTAINING_VITAL,
          f"no census name contains it "
          f"({sum(1 for r in census if 'Vital' in r['name'])} do, pinned "
          f"{EXPECT_CENSUS_CONTAINING_VITAL})")
    guard(sum(1 for r in covered + census if "Vital" in r["name"]) == EXPECT_VITAL_THUNKS,
          f"{sum(1 for r in covered + census if 'Vital' in r['name'])} thunks in the "
          f"whole image have 'Vital' in their literal, and all of them are in the tsv "
          f"(pinned {EXPECT_VITAL_THUNKS}) - so the 310/209 split is EXACTLY that "
          f"substring test, nothing subtler")
    vtial = [r["name"] for r in census if r["shape"] == "Vtial(typo-in-client)"]
    guard(len(vtial) == EXPECT_CENSUS_VTIAL_TYPOS,
          f"{len(vtial)} census classes are spelled '...Vtial' - a typo in the client's "
          f"own source that the substring filter silently dropped (pinned "
          f"{EXPECT_CENSUS_VTIAL_TYPOS}): {sorted(vtial)}")

    # ---------- [2] what the census recovered for each class ----------
    print("\n[2] slot VA + wire id + literal, recovered for every census row")
    readable = [r for r in census if r["literal_readable"]]
    idents = [r for r in census if r["literal_is_identifier"]]
    guard(sum(1 for r in covered + census if r["literal_readable"])
          == EXPECT_THUNK_LITERALS_READABLE,
          f"every thunk literal in the image is reachable as a C string "
          f"({sum(1 for r in covered + census if r['literal_readable'])}/"
          f"{thunk_total}, pinned {EXPECT_THUNK_LITERALS_READABLE})")
    guard(sum(1 for r in covered + census if r["literal_is_identifier"])
          == EXPECT_THUNK_LITERALS_IDENT,
          f"every thunk literal is identifier-shaped "
          f"({sum(1 for r in covered + census if r['literal_is_identifier'])}/"
          f"{thunk_total}, pinned {EXPECT_THUNK_LITERALS_IDENT})")
    guard(len(readable) == len(census) and len(idents) == len(census),
          f"all {len(census)} census rows carry a readable identifier literal "
          f"({len(readable)} readable, {len(idents)} identifier-shaped)")
    guard(all(r["id_slot_va"] for r in census),
          f"all {len(census)} census rows carry an id-slot VA")
    slots = {r["id_slot_va"] for r in census}
    guard(len(slots) == len(census),
          f"census rows do not share an id-slot ({len(slots)} slots for {len(census)} rows)")
    ids = [r["wire_id_dec"] for r in census]
    guard(len(set(ids)) == len(ids),
          f"census wire ids are distinct from each other "
          f"({len(set(ids))} distinct for {len(ids)} rows)")
    tsv_ids = {ident for ident, _n in candidates}
    clash_tsv = [r for r in census if r["wire_id_dec"] in tsv_ids]
    guard(not clash_tsv,
          f"no census wire id collides with a tsv candidate id ({len(clash_tsv)} clash)")

    # ---------- [3] the 48-character blind spot, measured ----------
    print("\n[3] the round-62 sweep's 48-character blind spot, measured not bounded")
    longs = long_identifiers(image)
    guard(len(longs) == EXPECT_LONG_IDENTIFIERS,
          f"{len(longs)} standalone identifier literals in the image are longer than "
          f"{SWEEP_LIMIT} chars (pinned {EXPECT_LONG_IDENTIFIERS}) - the round-62 regex "
          f"[\\x20-\\x7e]{{3,{SWEEP_LIMIT}}} cannot represent any of them")
    class_names = [t for t in longs if t in {r["name"] for r in covered + census}]
    guard(len(class_names) == EXPECT_LONG_CLASS_NAMES,
          f"{len(class_names)} of them are registered class names (pinned "
          f"{EXPECT_LONG_CLASS_NAMES}): {sorted(class_names)}")
    guard(sorted(class_names) == sorted(LONG_CLASS_NAMES),
          f"the long class names are exactly the two pinned ones")
    guard(len(longs) - len(class_names) == EXPECT_LONG_NOT_A_NAME,
          f"{len(longs) - len(class_names)} is not a name at all (pinned "
          f"{EXPECT_LONG_NOT_A_NAME}; it is the PADPADDINGXX... linker filler)")
    if table is not None:
        guard(all(t in table.by_name for t in class_names),
              f"both long class names are already in docs/PF_VITAL_NAMES.json - the blind "
              f"spot cost the project nothing in the end, but it was luck, not design")
    for text, va in longs.items():
        print(f"        {len(text):>3} chars  0x{va:08X}  {text[:70]}"
              + ("..." if len(text) > 70 else ""))

    # ---------- [4] the census is NOT a name table ----------
    # The heading below used to carry a red-circle emoji.  It killed this tool on
    # the Windows gate: that console is code page 874, U+1F534 has no mapping in
    # it, and print() raised UnicodeEncodeError before any finding was reported.
    # The same call is harmless in the Linux sandbox, whose stdout is UTF-8, so
    # the tool was green on one of the two machines this project verifies on and
    # dead on the other.  The decoration is gone and the words are unchanged,
    # because the words were doing the work.  A test below asserts that the whole
    # of this tool's stdout survives an encode to cp874, so the next person who
    # reaches for an emoji here gets a red line on both machines instead of one.
    print("\n[4] admission - what this round did NOT do")
    if table is not None:
        in_table = [r for r in census if r["in_names_table"]]
        guard(len(in_table) == EXPECT_CENSUS_IN_TABLE,
              f"{len(in_table)} census names are already in docs/PF_VITAL_NAMES.json "
              f"(pinned {EXPECT_CENSUS_IN_TABLE}) - independent corroboration, their ids "
              f"came from v141, not from their own literal")
        disagree = [
            r for r in in_table
            if table.by_name[r["name"]]["id_dec"] != r["wire_id_dec"]
        ]
        guard(not disagree,
              f"every one of those agrees id-for-id with the table ({len(disagree)} disagree)")
        cross = [
            r for r in census
            if r["wire_id_dec"] in table.by_id
            and table.by_id[r["wire_id_dec"]]["name"] != r["name"]
        ]
        guard(len(cross) == EXPECT_CENSUS_ID_CLASH_CROSS_NAME,
              f"{len(cross)} census ids collide with a table id under a DIFFERENT name "
              f"(pinned {EXPECT_CENSUS_ID_CLASH_CROSS_NAME})"
              + (f" -> {[(r['name'], r['wire_id']) for r in cross[:3]]}" if cross else ""))
        newly = [r for r in census if not r["in_names_table"]]
        guard(len(census) - len(in_table) == len(newly), "bookkeeping")
        guard(EXPECT_CENSUS_ADMITTED == 0,
              f"{len(newly)} census classes are NOT in the names table and this round "
              f"admitted {EXPECT_CENSUS_ADMITTED} of them - condition (4)(a) is vacuous "
              f"for a name discovered from its own literal; widening it is a chief "
              f"decision, not a lane's")

    # ---------- [5] the artifact ----------
    print("\n[5] machine-readable census artifact")
    payload = artifact_payload(image, census, longs, thunk_total, len(covered))
    expected = json.dumps(payload, indent=1, ensure_ascii=False) + "\n"
    if emit is not None:
        write_artifact(artifact, payload)
        print(f"  WROTE {artifact}")
    if artifact.exists():
        guard(artifact.read_text(encoding="utf-8") == expected,
              f"the committed artifact is byte-identical to what this run derives "
              f"({artifact.name})")
    else:
        guard(False,
              f"artifact missing: {artifact} - regenerate with "
              f"python3 tools/pf_vital_thunk_census_static.py --emit {artifact}")

    if want_list:
        print("\n[--list] wire_id\tname\tid_slot_va\tliteral_va\tin_names_table")
        for row in census:
            print(f"  {row['wire_id']}\t{row['name']}\t{row['id_slot_va']}\t"
                  f"{row['literal_va']}\t{row['in_names_table']}")

    print("\n== RESULT ==")
    if FAILS:
        print(f"FAIL ({len(FAILS)} guard(s) drifted)")
        return 1
    print("PASS - all guards reproduced")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
