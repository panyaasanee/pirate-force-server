#!/usr/bin/env python3
"""LANE-CS: per-class FULL skill-list data extractor, from CURRICULUM.

WHAT THIS TOOL IS FOR.  ``class_skill_curriculum.py`` is a committed data
module the server imports with no pf_bridge sibling present.  This is its
generator: it reads the committed client tables on the bridge clone and
writes the local TSV copies that module loads.

    gamedata/tables/CONSTDATA_TH__CURRICULUM.tsv     class code -> skill id
    gamedata/tables/CONSTDATA_TH__SKILL_CONTEXT.tsv  per-skill fields
    gamedata/tables/TEXTDATA_TH__SKILL_TEXT.tsv      skill display titles

WHY THIS EXISTS: IT RETIRES ONE OF THE FOUR "NO FULL SKILL LIST" BLOCKERS.
``tools/pf_class_skill_starting_kit_extract.py`` (round ``iazmrv``) mined
only the 4-skill starting kit and its docstring lists four measured reasons
why no committed table answered "every skill of a class".  Reason 3 was:

    "``CONSTDATA_TH__CURRICULUM.tsv`` keys skills by a different class code
    (``n_PPCLASS``) than ``CHARCREATE_CLASS.n_ID``"

That reason is FALSIFIED by the committed data, and this tool is the
measurement.  CURRICULUM's ``n_PPCLASS`` column takes exactly six distinct
values across its 137 data rows -- 1, 2, 4, 16, 32 and 1024.  Five of those
six ARE, byte for byte, the five ``CHARCREATE_CLASS.n_ID`` values (1, 2, 4,
16, 32); no third code scheme is involved.

THE PROOF IS NOT "THE NUMBERS LOOK THE SAME."  A shared set of five small
powers of two could be coincidence, so this tool verifies the mapping
against a SECOND, INDEPENDENT witness that the starting-kit catalog already
pinned: each class's own "Basic Training" skill id, taken from that class's
own ``CHARCREATE_CLASS.s_SKILL_2`` row.  Those ids are block prefixes --
class 1 Gladiator owns 40000, class 2 Paladin owns 43000, class 4 Sniper
owns 41000, class 16 Necromancer owns 42000, class 32 Sorcerer owns 44000
(note that the block order is NOT the class-id order: 2 -> 43xxx and 4 ->
41xxx cross over, which is exactly what makes this witness worth something
-- a wrong mapping would not survive it).  For all five classes, every
single skill id CURRICULUM files under that class code falls inside that
same class's own block:

    n_PPCLASS 1  -> 25 ids, all 40001..40025   (class 1's block is 40000)
    n_PPCLASS 2  -> 25 ids, all 43001..43025   (class 2's block is 43000)
    n_PPCLASS 4  -> 25 ids, all 41001..41025   (class 4's block is 41000)
    n_PPCLASS 16 -> 26 ids, all 42001..42026   (class 16's block is 42000)
    n_PPCLASS 32 -> 25 ids, all 44001..44025   (class 32's block is 44000)

5 of 5 agreement, including both crossed pairs.  ``verify_ppclass_is_
charcreate_class_id`` below recomputes this every run and refuses to write
if any bucket ever straddles two blocks -- so the day the tables drift, this
tool stops rather than shipping a mapping it can no longer prove.

THE SIXTH BUCKET, 1024, IS NOT A CLASS.  It is not a CHARCREATE_CLASS n_ID.
What is measurable about it: it holds 11 skill ids, none of them in any of
the five class blocks, and it contains exactly the three skill ids that all
five classes share in CHARCREATE_CLASS (99 Normal Attack, 110 Strive Jump,
111 VIP Strive Jump -- s_SKILL_1/3/4, identical on every one of the five
rows).  Reading 1024 as "the every-class bucket" is the obvious inference
and this lane records it as an assumption pending COO confirmation, NOT as a
decoded fact: the tool carries the bucket under its raw number and the
module exposes it as ``SHARED_BUCKET_CODE``, never as a sixth class.

WHAT THIS TOOL STILL DOES NOT CLAIM.  Retiring blocker 3 does not retire the
other three from the sibling tool's docstring.  In particular the client's
own quest Lua scripts (``gamedata/lua/Quest/q_add_skill*.lua``) grant further
skills out of band, so "the skills CURRICULUM files under a class" is a
lower bound on that class's real skill list, not proven to be all of it.
That is why the module names its accessor ``curriculum_skill_ids`` after the
table it came from rather than anything like "all_skills_of_class".

NO SKILL TYPE IS INVENTED HERE (same rule as the sibling tool).  SKILL_CONTEXT
still has no "basic attack / attack / AOE / buff / heal / passive" enum column
and no MP column; the raw rows are copied verbatim under the client's own
column names and any classification remains future RE work.

ASCII ONLY, ON PURPOSE (lesson 86): titles are carried from ``s_SKILL_TITLE``
in English only.  All 137 curriculum titles are ASCII in this snapshot and
the tool refuses rather than writing a byte the bridge console cannot print.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


# The sixth n_PPCLASS bucket.  Deliberately not called a class id.
SHARED_BUCKET_CODE = 1024


class MineError(RuntimeError):
    """Any refusal.  There is no partial output: the tool writes or it does not."""


def _read_tsv_rows(path: Path) -> list:
    if not path.is_file():
        raise MineError("missing source table: %s" % path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))
    if not rows:
        raise MineError("empty source table: %s" % path)
    return rows


def _render_tsv(rows: list) -> str:
    return "\n".join("\t".join(row) for row in rows) + "\n"


def _class_blocks(gamedata_tables: Path) -> dict:
    """class id -> its own Basic Training skill id, from CHARCREATE_CLASS.

    The second, independent witness the module docstring describes.  Read
    from ``s_SKILL_2`` (the ``<id>;<count>`` starting-kit slot that carries
    the class-specific "Basic Training" skill) of the class's own row.
    """
    path = gamedata_tables / "CONSTDATA_TH__CHARCREATE_CLASS.tsv"
    rows = _read_tsv_rows(path)
    header = rows[0]
    data_rows = [row for row in rows[1:] if row]
    if len(data_rows) != 5:
        raise MineError(
            "CONSTDATA_TH__CHARCREATE_CLASS.tsv has %d data row(s), expected "
            "5 -- the selectable class roster changed; re-check the catalog "
            "by hand before trusting a mechanical re-mine" % len(data_rows))
    id_col = header.index("n_ID")
    skill2_col = header.index("s_SKILL_2")
    blocks = {}
    for row in data_rows:
        class_id = int(row[id_col])
        # s_SKILL_2 is "<skill id>;<count>" in this table.
        blocks[class_id] = int(row[skill2_col].split(";")[0])
    return blocks


def _curriculum_buckets(gamedata_tables: Path) -> dict:
    """n_PPCLASS -> sorted tuple of the n_SKILL ids filed under it."""
    path = gamedata_tables / "CONSTDATA_TH__CURRICULUM.tsv"
    rows = _read_tsv_rows(path)
    header = rows[0]
    ppclass_col = header.index("n_PPCLASS")
    skill_col = header.index("n_SKILL")
    buckets = {}
    for row in rows[1:]:
        if not row:
            continue
        buckets.setdefault(int(row[ppclass_col]), []).append(int(row[skill_col]))
    return {code: tuple(sorted(ids)) for code, ids in buckets.items()}


def verify_ppclass_is_charcreate_class_id(gamedata_tables: Path) -> dict:
    """Re-measure the mapping claim; raise MineError if it no longer holds.

    Returns the verified ``class id -> tuple of skill ids`` mapping.  Every
    run of this tool goes through here, so a drifted table stops the mine
    instead of silently shipping an unprovable mapping.
    """
    blocks = _class_blocks(gamedata_tables)
    buckets = _curriculum_buckets(gamedata_tables)

    unexplained = set(buckets) - set(blocks) - {SHARED_BUCKET_CODE}
    if unexplained:
        raise MineError(
            "CURRICULUM n_PPCLASS has value(s) %s that are neither a "
            "CHARCREATE_CLASS n_ID %s nor the known shared bucket %d -- the "
            "class-code scheme changed; re-do the mapping proof by hand"
            % (sorted(unexplained), sorted(blocks), SHARED_BUCKET_CODE))

    verified = {}
    for class_id, block_start in sorted(blocks.items()):
        ids = buckets.get(class_id)
        if not ids:
            raise MineError(
                "CURRICULUM files no skill at all under n_PPCLASS %d, but "
                "CHARCREATE_CLASS has a row for that class -- the two tables "
                "no longer agree" % class_id)
        block_end = block_start + 999
        strays = [i for i in ids if not block_start < i <= block_end]
        if strays:
            raise MineError(
                "n_PPCLASS %d holds skill id(s) %s outside class %d's own "
                "Basic Training block %d..%d -- the second witness that "
                "n_PPCLASS == CHARCREATE_CLASS.n_ID no longer holds; do NOT "
                "ship this mapping" % (
                    class_id, strays, class_id, block_start, block_end))
        verified[class_id] = ids

    shared = buckets.get(SHARED_BUCKET_CODE, ())
    for class_id, block_start in blocks.items():
        overlap = [i for i in shared if block_start < i <= block_start + 999]
        if overlap:
            raise MineError(
                "shared bucket %d holds skill id(s) %s inside class %d's own "
                "block -- the bucket is no longer disjoint from the class "
                "blocks" % (SHARED_BUCKET_CODE, overlap, class_id))
    return verified


def extract_curriculum(gamedata_tables: Path) -> str:
    """The CURRICULUM table's own three load-bearing columns, verbatim."""
    verify_ppclass_is_charcreate_class_id(gamedata_tables)
    path = gamedata_tables / "CONSTDATA_TH__CURRICULUM.tsv"
    rows = _read_tsv_rows(path)
    header = rows[0]
    keep = [header.index(name) for name in ("n_ID", "n_PPCLASS", "n_SKILL")]
    out_rows = [["n_ID", "n_PPCLASS", "n_SKILL"]]
    for row in rows[1:]:
        if not row:
            continue
        out_rows.append([row[i] for i in keep])
    return _render_tsv(out_rows)


def _curriculum_skill_ids(gamedata_tables: Path) -> tuple:
    buckets = _curriculum_buckets(gamedata_tables)
    everything = set()
    for ids in buckets.values():
        everything.update(ids)
    return tuple(sorted(everything))


def extract_skill_context_curriculum(gamedata_tables: Path) -> str:
    path = gamedata_tables / "CONSTDATA_TH__SKILL_CONTEXT.tsv"
    rows = _read_tsv_rows(path)
    header = rows[0]
    by_id = {row[0]: row for row in rows[1:] if row}
    out_rows = [header]
    missing = []
    for skill_id in _curriculum_skill_ids(gamedata_tables):
        row = by_id.get(str(skill_id))
        if row is None:
            missing.append(skill_id)
            continue
        out_rows.append(row)
    if missing:
        raise MineError(
            "SKILL_CONTEXT is missing curriculum skill id(s) %s -- the table "
            "changed underneath the curriculum" % missing)
    return _render_tsv(out_rows)


def extract_skill_text_curriculum(gamedata_tables: Path) -> str:
    path = gamedata_tables / "TEXTDATA_TH__SKILL_TEXT.tsv"
    rows = _read_tsv_rows(path)
    by_id = {row[0]: row for row in rows[1:] if row}
    out_rows = [["n_ID", "s_SKILL_TITLE"]]
    missing = []
    for skill_id in _curriculum_skill_ids(gamedata_tables):
        row = by_id.get(str(skill_id))
        if row is None:
            missing.append(skill_id)
            continue
        title = row[1].strip()
        try:
            title.encode("ascii")
        except UnicodeEncodeError as exc:
            raise MineError(
                "skill %d title %r is not ASCII-only -- this tool refuses to "
                "carry it rather than write a byte the bridge console cannot "
                "print" % (skill_id, title)) from exc
        out_rows.append([str(skill_id), title])
    if missing:
        raise MineError("SKILL_TEXT is missing curriculum skill id(s) %s" % missing)
    return _render_tsv(out_rows)


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--gamedata", type=Path,
        default=here.parent / "pf_bridge" / "gamedata",
        help="the bridge clone's gamedata directory")
    parser.add_argument(
        "--out-dir", type=Path,
        default=here / "src" / "pirateforce_foundation" / "data",
        help="directory holding the committed local TSV copies")
    parser.add_argument(
        "--check", action="store_true",
        help="compose and compare against --out-dir; write nothing")
    args = parser.parse_args(argv)

    gamedata_tables = args.gamedata / "tables"
    rendered = {
        "class_skill_curriculum.tsv": extract_curriculum(gamedata_tables),
        "skill_context_curriculum.tsv":
            extract_skill_context_curriculum(gamedata_tables),
        "skill_text_curriculum.tsv":
            extract_skill_text_curriculum(gamedata_tables),
    }

    if args.check:
        mismatched = []
        for name, text in rendered.items():
            out_path = args.out_dir / name
            if not out_path.is_file():
                mismatched.append("%s does not exist" % out_path)
                continue
            current = out_path.read_text(encoding="ascii")
            if current != text:
                mismatched.append("%s differs from a fresh mining" % out_path)
        if mismatched:
            print("CHECK FAILED:")
            for line in mismatched:
                print("  %s" % line)
            return 1
        print("CHECK OK: all %d curriculum tables match a fresh mining"
              % len(rendered))
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in rendered.items():
        out_path = args.out_dir / name
        out_path.write_text(text, encoding="ascii")
        print("wrote %s (%d bytes)" % (out_path, len(text)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except MineError as error:
        print("REFUSED: %s" % error, file=sys.stderr)
        sys.exit(2)
