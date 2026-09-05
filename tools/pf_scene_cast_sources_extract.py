"""Re-derive world_m2_sea_scene_cast._MEASURED_ROWS from committed tables.

WHY THIS EXISTS.  The module freezes its rows because the gate runs with no
``pf_bridge`` beside it, so nothing inside the package can check the pins.
pf-adversary's finding on this round's first draft was that a frozen digest
nothing re-derives is a stale pin the moment the table moves.  This is the
re-derivation: run it wherever ``pf_bridge`` is checked out next to this
repo and it prints, for every scene the module pins, the numbers measured
now and whether they still agree.

    py -3 tools/pf_scene_cast_sources_extract.py
    py -3 tools/pf_scene_cast_sources_extract.py --bridge ../pf_bridge

Exit code 0 when every pinned row and every pinned digest still matches;
1 when any of them has MOVED (the signal to update the module and say so in
a round file); 2 when something could not be checked here at all -- the
tables directory missing, or a scene whose placements file is absent from
this checkout.  2 is NOT a failure and NOT drift; it is this tool saying it
could not answer, which a draft of it reported as nine moved rows and an
instruction to overwrite nine correct measurements with zeros.

THE JOIN THIS PERFORMS is the project's own, not a new one:
``world_m2_sea_destination.CLINE_KEY_COLUMN`` -- for a scene's creature
line type T and a placement's Mob-Set number S,
``CLINE[n_CLINE_TYPE == T and n_CREATURE_TYPE == S] -> n_LEADER_BK1 ->
CONSTDATA_TH__MOBS[n_ID]``.  A placement counts as resolved when that chain
reaches a MOBS row.

TWO READING RULES THIS TOOL APPLIES, STATED BECAUSE NEITHER IS OBVIOUS:

* ARGMAX OVER TIERS.  A scene may have several INSTANCE rows, each with its
  own level band and its own creature-line type.  ``resolved`` is the count
  from the BEST-RESOLVING of them, so it is an upper bound rather than what
  any one arrival is guaranteed.  Only scene 18 currently differs between
  tiers (803/805 give 7/8, 818 gives 8/8); the module's docstring names it.
* SAILING TYPE 0 IS DROPPED.  ``SAILING_RESULT`` rows carry
  ``n_CLINE_TYPE == 0`` for entries that name no block (scene 126's raw set
  is {0, 8000}); 0 is not a type and is filtered.  The INSTANCE branch
  needs no such filter and deliberately has none.

THREE SOURCES OF A CREATURE LINE TYPE, and enumerating them is the whole
point of the round that added this file: SCENE_NAME keyed by n_ID,
INSTANCE keyed by n_SCENE_ID, SAILING_RESULT keyed by n_AREA.  A claim that
a scene can hold no cast is only well formed after all three answer
nothing.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_m2_sea_scene_cast as cast  # noqa: E402


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolves(template_ids: str, block: dict, mobs: dict) -> bool:
    """Does one placement's Mob-Set field reach a MOBS row through ``block``?

    THE ``a|b`` FORM IS WHY THIS IS A FUNCTION AND NOT AN ``in`` TEST.  A
    placement's ``template_ids`` may name TWO Mob-Set numbers separated by
    a pipe -- ``world_bg3001_identity.MULTI_SET_PLACEMENTS`` holds six of
    them for scene 126 alone, and that module resolves such a placement if
    EITHER leg does.  A first draft of this tool matched the whole field as
    one key and reported 31/38 for scene 126 against the 37/38 the shipped
    roster composes; the six it lost were exactly the ``53|54`` rows.  The
    tool's job is to agree with the resolver this project ships, so it
    follows the same rule instead of a simpler one.
    """
    for leg in str(template_ids).split("|"):
        row = block.get(leg.strip())
        if row is None:
            continue
        leader = row.get("n_LEADER_BK1", "0")
        if leader not in ("0", "") and leader in mobs:
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bridge", default=str(ROOT.parent / "pf_bridge"),
        help="path to the pf_bridge checkout holding gamedata/",
    )
    args = parser.parse_args(argv)
    bridge = Path(args.bridge)
    tables = bridge / "gamedata" / "tables"
    if not tables.is_dir():
        print(f"NOT REACHABLE: {tables} - nothing to re-derive here")
        return 2

    disagreements = 0
    unreachable = 0

    # ---- digests -----------------------------------------------------
    pinned = [(name, sha) for name, _key, sha in cast.CREATURE_LINE_SOURCES]
    pinned.append((cast.CLINE_TABLE, cast.CLINE_TABLE_SHA256))
    pinned.append((cast.MOBS_TABLE, cast.MOBS_TABLE_SHA256))
    for name, expected in pinned:
        path = bridge / name
        if not path.is_file():
            print(f"MISSING  {name}")
            disagreements += 1
            continue
        actual = _sha256(path)
        state = "ok  " if actual == expected else "MOVED"
        print(f"digest {state} {name} {actual}")
        if actual != expected:
            disagreements += 1

    # ---- the join ----------------------------------------------------
    scene_rows = {
        row["n_ID"]: row for row in _read(tables / "CONSTDATA_TH__SCENE_NAME.tsv")
        if row["n_ID"].strip().isdigit()
    }
    instance_rows = _read(tables / "CONSTDATA_TH__INSTANCE.tsv")
    sailing_rows = _read(tables / "CONSTDATA_TH__SAILING_RESULT.tsv")
    cline_by_type: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for row in _read(tables / "CONSTDATA_TH__CLINE.tsv"):
        cline_by_type[row["n_CLINE_TYPE"]][row["n_CREATURE_TYPE"]] = row
    mobs = {row["n_ID"]: row for row in _read(tables / "CONSTDATA_TH__MOBS.tsv")}

    for scene_id in sorted(cast._MEASURED_ROWS):
        pinned_row = cast.cast_capacity(scene_id)
        key = str(scene_id)
        scene = scene_rows.get(key)
        if scene is None:
            print(f"scene {scene_id}: MISSING from SCENE_NAME.tsv")
            disagreements += 1
            continue
        direct = int(scene["n_CLINE_TYPE"])
        instance_types = tuple(sorted({
            int(row["n_CLINE_TYPE"]) for row in instance_rows
            if row.get("n_SCENE_ID") == key
        }))
        sailing_types = tuple(sorted({
            int(row["n_CLINE_TYPE"]) for row in sailing_rows
            if row.get("n_AREA") == key and int(row["n_CLINE_TYPE"]) != 0
        }))
        placements_path = (
            bridge / "gamedata" / "scene" / pinned_row.model_id
            / f"{pinned_row.model_id}.placements.tsv"
        )
        placements = resolved = 0
        best = -1
        if not placements_path.is_file():
            # NOT the same as "the table moved", and a draft of this tool
            # conflated them (pf-adversary pass 2, D5): a tables-only or
            # partial pf_bridge checkout made every scene print cast=0/0
            # and the tool then told the operator to overwrite nine
            # correct measurements with zeros.  Say what actually happened
            # and do not count it as drift.
            print(f"scene {scene_id:>4} {pinned_row.model_id:<7} "
                  f"NO PLACEMENTS FILE at {placements_path} - not checked")
            unreachable += 1
            continue
        if placements_path.is_file():
            sets = [row["template_ids"] for row in _read(placements_path)]
            placements = len(sets)
            candidates = instance_types or sailing_types
            if direct != cast.NO_DIRECT_CLINE_TYPE:
                candidates = (direct,) + tuple(candidates)
            for candidate in candidates:
                block = cline_by_type.get(str(candidate), {})
                hits = sum(1 for name in sets if _resolves(name, block, mobs))
                if hits > resolved:
                    resolved, best = hits, candidate
        # EVERY pinned field the tables can answer, not the six a draft of
        # this tool compared (pf-adversary pass 2, D4): model_id,
        # n_SCENE_TYPE and the scene name were taken on trust while this
        # tool had SCENE_NAME.tsv open, and it still printed "every pinned
        # row and digest still agrees".  name_gloss stays out on purpose --
        # it is a human translation, so the MEASURED half (the shipped CJK
        # bytes) is what is compared.
        measured = (
            scene["s_MODLE_ID"],
            scene["s_SCENE_NAME"].encode("utf-8").hex(),
            int(scene["n_SCENE_TYPE"]),
            direct, instance_types, sailing_types, placements, resolved,
            best,
        )
        pinned_tuple = (
            pinned_row.model_id, pinned_row.name_source_hex,
            pinned_row.scene_type,
            pinned_row.direct_cline_type, pinned_row.instance_cline_types,
            pinned_row.sailing_cline_types, pinned_row.placements,
            pinned_row.resolved, pinned_row.best_cline_type,
        )
        agrees = measured == pinned_tuple
        print(
            f"scene {scene_id:>4} {pinned_row.model_id:<7} "
            f"{'ok   ' if agrees else 'MOVED'} "
            f"direct={direct} instance={instance_types} "
            f"sailing={sailing_types} cast={resolved}/{placements} "
            f"best={best}"
        )
        if not agrees:
            print(f"      pinned: {pinned_tuple}")
            print(f"      now   : {measured}")
            disagreements += 1

    if disagreements:
        print(f"\n{disagreements} row(s)/digest(s) MOVED - update the module")
        return 1
    if unreachable:
        print(f"\n{unreachable} scene(s) had no placements file here - "
              "nothing checked for them, and that is not drift")
        return 2
    print("\nevery pinned row and digest still agrees with the tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
