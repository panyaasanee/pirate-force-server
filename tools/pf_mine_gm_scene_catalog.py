#!/usr/bin/env python3
"""LANE-GM: mine the GM scene-name catalog out of the client's own text table.

WHAT THIS TOOL IS FOR.  ``gm/scene_catalog.py`` is a GENERATED module.  This
is its generator.  It reads exactly one committed table on the bridge clone,

    gamedata/tables/TEXTDATA_TH__SCENE_NAME_TIP.tsv

carries every row verbatim (n_ID, s_SCENE_NAME, s_GM_SCENE_NAME with
leading/trailing whitespace stripped -- the source pads both string columns),
and writes an ASCII-only Python module the server can import with no bridge
present.

WHY THIS TABLE.  It is the "แมพ GM" (GM scene map) PANYA-ORDER
(pf_bridge/notes_to_chief/20260826_1630_...) asked Lane GM to find: the exact
scene-id -> name pairing a GM sees when picking a warp destination.  The
2026-08-26 16:30 letter that opened this lane counted "331 scenes"; a fresh
count of the shipped table is 330 data rows (the letter's count included the
header row).  This tool prints the row count on every run so that drift is
visible rather than repeated by hand a second time.

THE ONE CONTROL IT REFUSES ON.  n_ID 1/2/3/4 must resolve to Port Royal /
Prison Exile Island / Spice Paradise Island / Slave Market Island -- the four
names the opening letter already cross-checked by hand.  A table swap or a
column rename that still parses but no longer carries those four names fails
here rather than shipping a silently wrong catalog.

Regenerate rather than hand-edit ``gm/scene_catalog.py``; run with --check in
CI to prove the committed module still matches a fresh mining of the table.
"""
import argparse
import csv
import hashlib
import sys
from pathlib import Path

CONTROL_ROWS = {
    "1": "Port Royal",
    "2": "Prison Exile Island",
    "3": "Spice Paradise Island",
    "4": "Slave Market Island",
}

SOURCE_RELPATH = "tables/TEXTDATA_TH__SCENE_NAME_TIP.tsv"


class MineError(Exception):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mine(gamedata: Path):
    source = gamedata / SOURCE_RELPATH
    if not source.is_file():
        raise MineError("missing %s" % source)
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["n_ID", "s_SCENE_NAME", "s_GM_SCENE_NAME"]:
            raise MineError(
                "unexpected columns %r; the generator and the table have "
                "drifted" % (reader.fieldnames,))
        rows = list(reader)
    catalog = {}
    for row in rows:
        scene_id = int(row["n_ID"].strip())
        if scene_id in catalog:
            raise MineError("duplicate n_ID %d" % scene_id)
        catalog[scene_id] = (
            row["s_SCENE_NAME"].strip(),
            row["s_GM_SCENE_NAME"].strip(),
        )
    for raw_id, expected_name in CONTROL_ROWS.items():
        scene_id = int(raw_id)
        if scene_id not in catalog or catalog[scene_id][0] != expected_name:
            # ascii(), not %r: the console this prints to is cp874, and a
            # corrupted source table is exactly the case where catalog[scene_id]
            # could carry a non-cp874 character this report must not crash on.
            raise MineError(
                "control broke: n_ID %d is %s, expected %s"
                % (scene_id, ascii(catalog.get(scene_id)), ascii(expected_name)))
    return catalog, _sha256(source), len(rows)


def _render(catalog, source_sha256: str, row_count: int) -> str:
    lines = [
        '"""GENERATED - do not hand-edit.  LANE-GM scene-id -> GM scene name catalog.',
        "",
        "Written by ``tools/pf_mine_gm_scene_catalog.py`` from the committed",
        "TEXTDATA_TH__SCENE_NAME_TIP.tsv on the bridge clone.  Regenerate rather",
        "than patch.",
        "",
        "This is the client's own GM-facing scene name list, nothing more: it",
        "answers \"what does a GM see this scene called\" and \"what is its scene",
        "id\".  It is NOT a claim that every id is reachable, populated, or",
        "currently correct in any other table -- it is a name lookup only.",
        "",
        "SOURCE AND ITS DIGEST AT MINING TIME",
        "    TEXTDATA_TH__SCENE_NAME_TIP  %s" % source_sha256,
        "    row count (excluding header)  %d" % row_count,
        '"""',
        "",
        "SOURCE_SHA256 = %r" % source_sha256,
        "ROW_COUNT = %d" % row_count,
        "",
        "# scene_id -> (s_SCENE_NAME, s_GM_SCENE_NAME), both stripped of the",
        "# source table's padding whitespace.",
        "SCENE_CATALOG = {",
    ]
    for scene_id in sorted(catalog):
        name, gm_name = catalog[scene_id]
        lines.append(
            "    %d: (%s, %s)," % (scene_id, ascii(name), ascii(gm_name)))
    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("def gm_scene_name(scene_id: int) -> str | None:")
    lines.append('    """The GM-facing scene name, or None if scene_id is not in the table."""')
    lines.append("    row = SCENE_CATALOG.get(scene_id)")
    lines.append("    return row[1] if row is not None else None")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--gamedata", type=Path,
        default=here.parent / "pf_bridge" / "gamedata",
        help="the bridge clone's gamedata directory")
    parser.add_argument(
        "--out", type=Path,
        default=here / "src" / "pirateforce_foundation" / "gm" / "scene_catalog.py")
    parser.add_argument(
        "--check", action="store_true",
        help="compose and compare against --out; write nothing")
    args = parser.parse_args(argv)

    catalog, source_sha256, row_count = mine(args.gamedata)
    rendered = _render(catalog, source_sha256, row_count)

    print("rows                 %d" % row_count)
    print("source sha256        %s" % source_sha256)
    print("control ids ok       1 2 3 4")

    if args.check:
        if not args.out.is_file():
            print("CHECK FAILED: %s does not exist" % args.out)
            return 1
        current = args.out.read_text(encoding="ascii")
        if current != rendered:
            print("CHECK FAILED: %s differs from a fresh mining" % args.out)
            return 1
        print("CHECK OK: %s matches a fresh mining" % args.out)
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(rendered, encoding="ascii")
    print("wrote %s (%d bytes)" % (args.out, len(rendered)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except MineError as exc:
        print("REFUSED: %s" % exc)
        sys.exit(1)
