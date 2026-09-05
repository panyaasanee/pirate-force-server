#!/usr/bin/env python3
"""LANE-CS: class registry + starting-skill-kit data extractor.

WHAT THIS TOOL IS FOR.  ``class_catalog.py`` and ``skill_catalog.py`` are
committed data modules the server imports with no pf_bridge sibling present.
This is their generator: it reads the committed client tables on the bridge
clone and writes the local TSV copies those two modules load.

    gamedata/tables/CONSTDATA_TH__CHARCREATE_CLASS.tsv   5 selectable classes
    gamedata/tables/CONSTDATA_TH__SKILL_CONTEXT.tsv      per-skill fields
    gamedata/tables/TEXTDATA_TH__SKILL_TEXT.tsv          skill display titles

SCOPE, ON PURPOSE.  This tool does not attempt "every skill in the game."
pf-adversary (round iazmrv, reviewing this exact plan before it was code)
measured that no single committed table answers that question:
``SKILL_CONTEXT.n_ISCLASS`` is a bitmask that, for the six "Basic Training"
rows themselves, is self-referential UI bookkeeping (id 40000's own
n_ISCLASS is 1 -- its own bit -- not a general skill-to-class foreign key
usable for other skill ids); ``CONSTDATA_TH__SAILOR_SKILL.tsv`` shares the
same low id range but is a different domain entirely (ship-crew skills, not
player skills); ``CONSTDATA_TH__CURRICULUM.tsv`` keys skills by a different
class code (``n_PPCLASS``) than ``CHARCREATE_CLASS.n_ID``; and the client's
own quest Lua scripts (``gamedata/lua/Quest/q_add_skill*.lua``) grant further
skills out of band.  What IS unambiguous and provable from one row each:
``CHARCREATE_CLASS.s_SKILL_1..4`` names the exact four skill ids every one of
the five selectable classes starts with.  That is the starting kit this tool
mines -- 8 distinct skill ids shared/specific across all 5 classes (99, 110,
111 are identical for every class; one class-specific "Basic Training" skill
each, named by its OWN ``s_SKILL_TITLE`` row, not by ``CHARCREATE_CLASS``'s
``s_ICON``: 40000 "Gladiator Basic Training", 41000 "Sharpshooter Basic
Training", 42000 "Stormherald Basic Training", 43000 "Imperial Knights Basic
Training", 44000 "Light Priest Basic Training" -- ``s_ICON`` names the same
five classes "Gladiator"/"Sniper"/"Necromancer"/"Paladin"/"Sorcerer", which
agrees with the skill title only for class 1; see ``skill_catalog.py``'s
module docstring and ``test_basic_training_title_differs_from_the_
charcreate_icon_name`` for the measured collision).  Extending this to each
class's full skill list is future RE work this tool does not attempt.

VOODOOIST IS NOT A SIXTH ROW HERE.  CHARCREATE_CLASS ships only 5 rows (ids
1/2/4/16/32).  A 6th "Basic Training" skill (id 45000, icon
``ICON_Class_Voodooist_s``, ``n_ISCLASS`` bit 8) exists in SKILL_CONTEXT with
no matching CHARCREATE_CLASS row -- i.e. it is not selectable at character
creation in this data snapshot.  It is a lead for a future RE round, not part
of the starting kit, and this tool does not carry it.

NOT A RENAME OF FACTPACK_L2_CLASSCENSUS001.  pf_bridge's
FACTPACK_L2_CLASSCENSUS001 census counts ~1327 C++ RTTI engine classes; this
tool and the catalogs it feeds are about player professions, an unrelated
sense of the word "class."

ASCII ONLY, ON PURPOSE (lesson 86, cited by pf_mine_scene_drop_tables.py):
skill titles are carried in English only (``s_SKILL_TITLE``); the Thai
descriptions, tips, details and ``$``-macro effect formulas in
TEXTDATA_TH__SKILL_TEXT are real data but are not copied by this tool -- they
belong to the damage-formula work item, not the catalog item, and mixing them
in here would risk shipping an un-RE'd damage claim inside a "just a
catalog" module.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


STARTING_KIT_SKILL_IDS = (99, 110, 111, 40000, 41000, 42000, 43000, 44000)


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


def extract_charcreate_class(gamedata_tables: Path) -> str:
    path = gamedata_tables / "CONSTDATA_TH__CHARCREATE_CLASS.tsv"
    rows = _read_tsv_rows(path)
    data_rows = rows[1:]
    if len(data_rows) != 5:
        raise MineError(
            "CONSTDATA_TH__CHARCREATE_CLASS.tsv has %d data row(s), expected "
            "5 -- the selectable class roster changed; re-check the catalog "
            "by hand before trusting a mechanical re-mine" % len(data_rows))
    return _render_tsv(rows)


def extract_skill_context_starting_kit(gamedata_tables: Path) -> str:
    path = gamedata_tables / "CONSTDATA_TH__SKILL_CONTEXT.tsv"
    rows = _read_tsv_rows(path)
    header = rows[0]
    by_id = {row[0]: row for row in rows[1:] if row}
    out_rows = [header]
    missing = []
    for skill_id in STARTING_KIT_SKILL_IDS:
        row = by_id.get(str(skill_id))
        if row is None:
            missing.append(skill_id)
            continue
        out_rows.append(row)
    if missing:
        raise MineError(
            "SKILL_CONTEXT is missing starting-kit skill id(s) %s -- the "
            "table changed underneath the starting kit" % missing)
    return _render_tsv(out_rows)


def extract_skill_text_starting_kit(gamedata_tables: Path) -> str:
    path = gamedata_tables / "TEXTDATA_TH__SKILL_TEXT.tsv"
    rows = _read_tsv_rows(path)
    by_id = {row[0]: row for row in rows[1:] if row}
    out_rows = [["n_ID", "s_SKILL_TITLE"]]
    missing = []
    for skill_id in STARTING_KIT_SKILL_IDS:
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
        raise MineError(
            "SKILL_TEXT is missing starting-kit skill id(s) %s" % missing)
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
        "charcreate_class.tsv": extract_charcreate_class(gamedata_tables),
        "skill_context_starting_kit.tsv":
            extract_skill_context_starting_kit(gamedata_tables),
        "skill_text_starting_kit.tsv":
            extract_skill_text_starting_kit(gamedata_tables),
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
        print("CHECK OK: all %d starting-kit tables match a fresh mining"
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
    except MineError as exc:
        print("REFUSED: %s" % exc)
        sys.exit(2)
