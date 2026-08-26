#!/usr/bin/env python3
"""LANE-B: which scenes actually have monsters, across the whole client.

WHY THIS TOOL EXISTS.  BUILD-004 / M3 was written on the assumption that once
a field scene is reachable, ``tools/pf_mine_scene_mob_roster.py`` can be
pointed at it and the same pipeline that shipped Port Royal's 13 monsters
would just work.  Round ``B_20260826_1010`` promoted ``mob_aggro`` to
production; the obvious next step was to run the roster miner against scene
278 (``Bg1177``), the scene ``COO-DECISION`` 0550 confirmed as M2's
destination.  It refuses: 278 has ZERO placements whose MOBS row carries both
a rank and a combat AI.  That is not a bug in the miner - the same predicate
census the miner already prints (``--predicate-census``) reads zero on every
one of the four candidate hostility readings for that scene, not just the
strict one.  Scene 278 is simply empty of monster data.

AND IT IS WORSE THAN EMPTY.  Scene 278's OWN row in
``CONSTDATA_TH__SCENE_NAME.tsv`` names it (Thai) "beach football field
(TEST)", and its own ``TEXTDATA_TH__SCENE_NAME_TIP.tsv`` English string is
"Beach Soccer Field".  This tool reports that fact for scene 278 by name
(:data:`M2_DESTINATION_SCENE`), rather than leaving a reader to infer
anything from an absence, because a zero can always be misread as "not
measured yet" and this is not that: the game's own data says what this scene
is, and it is a QA map, not a field.

WHAT THIS TOOL ANSWERS INSTEAD.  Which of the OTHER scenes on the bridge
clone actually carry hostile monster data, so a field-scene choice can be
made on evidence instead of on which scene happened to get a travel gate
first.  It runs the exact selection rule
``pf_mine_scene_mob_roster.hostile_roster`` uses (rank != 0 AND
ai_combat != 0, on an unambiguous single-template placement) over every scene
folder shipped on the bridge, and reports the ones that are nonzero.

WHAT THIS TOOL DOES NOT DO.  It does not choose a field scene, does not write
``field_mob_tables.py`` for anything but the control it already ships
(bg0001), and does not touch ``scenarios/world_*.json`` - the travel gate
that would need to change is lane A's file.  This is a census, not a switch;
picking the destination is the COO's call, made in the open with this table
in front of them.

THE CONTROL THIS TOOL REFUSES WITHOUT.  bg0001 (Port Royal) must come back
with exactly 13 hostile placements out of 115 unambiguous ones - the same
count ``field_mob_tables.py`` ships and 2994+ tests already hold it to.  If
that drifts, the tables moved under this tool and nothing it prints past that
point can be trusted.

WHY DUPLICATE KEYS ARE A REFUSAL, NOT A LAST-ONE-WINS DICT.  A first draft of
this tool keyed ``MOBS``/``SCENE_NAME_TIP`` rows with a plain dict comprehension
that silently kept whichever row read last on a duplicate ``n_ID``.  Both
tables currently have none, so it produced today's numbers correctly - and
would have kept producing a confident, wrong answer the day either table
gained one, with the bg0001 control (which does not depend on the colliding
row) still passing.  ``_key`` now raises instead, matching
``pf_mine_scene_mob_roster._key``.  The scene registry's ``s_MODLE_ID`` column
is a genuine exception: 44 values in the current table are already
duplicated, so a scene folder can resolve to more than one registry row.
Rather than raise (which would make this tool unusable today) or guess
(last-in-file), an ambiguous resolution is reported as ambiguous - see
:data:`_resolve_scene_registry_row`.

WHY A DUPLICATE PLACEMENT INDEX IS A NAMED SKIP, NOT A SILENT DROP OR A FATAL
RAISE.  The miner raises on a duplicate placement index because it is about
to write a generated module for ONE scene and a silent drop there would ship
wrong data.  This tool walks 265+ scene folders in one run; a scene whose own
placement table is malformed should not abort the whole census, but it must
not be scored as "zero hostiles" either - the earlier draft resolved the
duplicate-index check on the raw index alone, BEFORE the mob/outfit lookup
that decides whether a row counts at all, which meant a garbage row occupying
an index could silently shadow a real hostile row sharing it and drop it from
the count with no error anywhere.  Ordering now matches the miner's
(mob/outfit resolves first); a genuine collision after that is a named skip,
not a count.

ASCII ONLY, on purpose, for the same reason as the rest of this lane's
tooling: the bridge console is code page 874, and one non-ASCII character
printed on it kills the tool mid-report.  ``json.dumps(..., ensure_ascii=True)``
already guarantees this for the JSON this tool writes; there is no second gate
after it because none can ever fire.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


PLACEMENT_COLUMNS = ("index", "template_ids", "x", "y", "z")

# The frozen control this tool refuses to run past if it has drifted.
CONTROL_SCENE = "bg0001"
CONTROL_HOSTILE_COUNT = 13
CONTROL_UNAMBIGUOUS_COUNT = 115

# The scene this tool exists to explain, reported by name and unconditionally
# (not filtered out by "hostile <= 0" the way a candidate would be).
M2_DESTINATION_SCENE = "Bg1177"
M2_DESTINATION_N_ID = 278


class ScanError(RuntimeError):
    """Any refusal.  There is no partial output: the tool writes or it does not."""


class DuplicateIndexError(RuntimeError):
    """One scene's own placement table names the same index twice."""


def _read_tsv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _key(rows: list[dict], column: str, where: str) -> dict[str, dict]:
    """Key rows by a column that must be a real primary key.  Raises on a

    collision rather than keeping one row silently - see the module
    docstring on why a last-one-wins dict here can pass the control check
    while being wrong for every other row.
    """
    keyed: dict[str, dict] = {}
    for row in rows:
        value = (row.get(column) or "").strip()
        if not value:
            continue
        if value in keyed:
            raise ScanError("duplicate key %r in %s" % (value, where))
        keyed[value] = row
    return keyed


def _nonzero(row: dict, column: str) -> bool:
    return (row.get(column) or "").strip() not in ("", "0")


def _scene_census(placements: list[dict], mobs: dict[str, dict]) -> dict[str, int]:
    """Count unambiguous / hostile placements, in the miner's own order:

    resolve template -> MOBS row -> outfit BEFORE deciding an index has been
    seen before, so a row that fails resolution can never shadow a real one
    that happens to share its raw index.  Raises :class:`DuplicateIndexError`
    only for two rows that BOTH survive resolution and collide - a genuine
    data problem in that scene, not a filtering side effect.
    """
    census = {"unambiguous": 0, "hostile": 0}
    seen: set[str] = set()
    for row in placements:
        template_ids = [
            item.strip() for item in (row.get("template_ids") or "").split(",")
            if item.strip()
        ]
        if len(template_ids) != 1:
            continue
        mob = mobs.get(template_ids[0])
        if mob is None:
            continue
        outfit = (mob.get("s_OUTFIT") or "").strip()
        if not outfit or ";" in outfit:
            continue
        index = (row.get("index") or "").strip()
        if not index:
            continue
        if index in seen:
            raise DuplicateIndexError(
                "duplicate placement index %r among resolved rows" % index
            )
        seen.add(index)
        census["unambiguous"] += 1
        if _nonzero(mob, "n_RANK") and _nonzero(mob, "n_AI_COMBAT"):
            census["hostile"] += 1
    return census


def _resolve_scene_registry_row(
    by_model: dict[str, list[dict]], scene: str,
) -> tuple[dict | None, bool]:
    """The registry row for a scene folder, and whether the match was ambiguous.

    ``s_MODLE_ID`` is not a primary key in this table (44 values collide as of
    this tool's writing), so a folder name can map to more than one row.
    Returns ``(None, False)`` when unregistered, ``(row, False)`` when exactly
    one row matches, and ``(first_row, True)`` when more than one does - the
    caller must not treat that row's fields as trustworthy without saying so.
    """
    rows = by_model.get(scene.lower(), [])
    if not rows:
        return None, False
    if len(rows) == 1:
        return rows[0], False
    return rows[0], True


def scan(gamedata: Path) -> dict:
    mobs_path = gamedata / "tables" / "CONSTDATA_TH__MOBS.tsv"
    scene_name_path = gamedata / "tables" / "CONSTDATA_TH__SCENE_NAME.tsv"
    scene_tip_path = gamedata / "tables" / "TEXTDATA_TH__SCENE_NAME_TIP.tsv"
    scene_dir = gamedata / "scene"

    mobs = _key(_read_tsv(mobs_path), "n_ID", str(mobs_path))
    scene_rows = _read_tsv(scene_name_path)
    by_model: dict[str, list[dict]] = {}
    for row in scene_rows:
        model = (row.get("s_MODLE_ID") or "").strip().lower()
        if model:
            by_model.setdefault(model, []).append(row)
    english_names = _key(_read_tsv(scene_tip_path), "n_ID", str(scene_tip_path))

    def _is_bgnull_or_empty(row: dict) -> bool:
        return (row.get("s_IMAGENAME") or "").strip().lower() in ("", "bgnull")

    total_bgnull = sum(1 for row in scene_rows if _is_bgnull_or_empty(row))

    scanned = 0
    skipped_no_file: list[str] = []
    skipped_empty: list[str] = []
    skipped_unreadable: list[str] = []
    skipped_duplicate_index: list[str] = []
    candidates = []
    control_seen = False
    scanned_bgnull = 0

    def registry_fields(scene: str) -> dict:
        row, ambiguous = _resolve_scene_registry_row(by_model, scene)
        n_id = None
        english_name = None
        has_air = None
        if row is not None:
            raw_n_id = (row.get("n_ID") or "").strip()
            n_id = int(raw_n_id) if raw_n_id else None
            has_air = not _is_bgnull_or_empty(row)
            tip = english_names.get(str(n_id)) if n_id is not None else None
            english_name = (tip.get("s_SCENE_NAME") or "").strip() if tip else None
        return {
            "scene_n_id": n_id,
            "english_name": english_name,
            "has_outdoor_air_companion": has_air,
            "registered_in_scene_name_table": row is not None,
            "ambiguous_registry_match": ambiguous,
        }

    for scene_path in sorted(scene_dir.iterdir()):
        if not scene_path.is_dir():
            continue
        scene = scene_path.name
        placement_path = scene_path / ("%s.placements.tsv" % scene)
        if not placement_path.is_file():
            skipped_no_file.append(scene)
            continue
        try:
            placements = _read_tsv(placement_path)
        except Exception as exc:
            skipped_unreadable.append("%s (%s)" % (scene, exc))
            continue
        if not placements:
            skipped_empty.append(scene)
            continue
        scanned += 1
        scene_fields = registry_fields(scene)
        if scene_fields["has_outdoor_air_companion"] is False:
            scanned_bgnull += 1

        try:
            census = _scene_census(placements, mobs)
        except DuplicateIndexError as exc:
            skipped_duplicate_index.append("%s (%s)" % (scene, exc))
            continue

        if scene.lower() == CONTROL_SCENE:
            control_seen = True
            if (
                census["hostile"] != CONTROL_HOSTILE_COUNT
                or census["unambiguous"] != CONTROL_UNAMBIGUOUS_COUNT
            ):
                raise ScanError(
                    "control drift: %s scans as hostile=%d unambiguous=%d, "
                    "not the shipped hostile=%d unambiguous=%d"
                    % (
                        CONTROL_SCENE, census["hostile"], census["unambiguous"],
                        CONTROL_HOSTILE_COUNT, CONTROL_UNAMBIGUOUS_COUNT,
                    )
                )

        if census["hostile"] <= 0:
            continue

        candidates.append({
            "scene_folder": scene,
            "hostile_placements": census["hostile"],
            "unambiguous_placements": census["unambiguous"],
            **scene_fields,
        })

    if not control_seen:
        raise ScanError("control scene %r was never scanned" % CONTROL_SCENE)

    # The scene this tool exists to explain, reported unconditionally and by
    # name - not folded into "candidates" (its hostile count is zero, so the
    # candidate filter would drop it) and not left to be inferred from an
    # absence.
    m2_placement_path = (
        scene_dir / M2_DESTINATION_SCENE
        / ("%s.placements.tsv" % M2_DESTINATION_SCENE)
    )
    m2_census = _scene_census(_read_tsv(m2_placement_path), mobs)
    m2_fields = registry_fields(M2_DESTINATION_SCENE)
    if m2_fields["scene_n_id"] != M2_DESTINATION_N_ID:
        raise ScanError(
            "M2 destination scene drift: %s registry n_ID is %r, not %d"
            % (M2_DESTINATION_SCENE, m2_fields["scene_n_id"], M2_DESTINATION_N_ID)
        )

    candidates.sort(
        key=lambda item: (-item["hostile_placements"], item["scene_folder"])
    )

    return {
        "schema": 1,
        "id": "field_scene_candidates_001",
        "lane": "B_COMBAT",
        "build_order": "BUILD-004 / FIELD-MOBS-001",
        "not_a_scenario": (
            "this file is a census of committed game data, not a switch - no "
            "flag loads it and no loader accepts it"
        ),
        "why_this_exists": (
            "scene 278 (Bg1177), the confirmed M2 travel destination, scans "
            "as zero hostile placements under the exact rule that shipped "
            "Port Royal's 13, and the game's own scene registry names it a "
            "test map (see m2_destination below); this is the evidence for "
            "what a real field scene would be instead"
        ),
        "selection_rule": (
            "a placement counts as hostile when its MOBS row has a single "
            "unambiguous outfit AND n_RANK != 0 AND n_AI_COMBAT != 0 - the "
            "identical rule tools/pf_mine_scene_mob_roster.py uses"
        ),
        "source_digests": {
            "mobs": _digest(mobs_path),
            "scene_name": _digest(scene_name_path),
            "scene_name_tip": _digest(scene_tip_path),
        },
        "control": {
            "scene": CONTROL_SCENE,
            "hostile_placements": CONTROL_HOSTILE_COUNT,
            "unambiguous_placements": CONTROL_UNAMBIGUOUS_COUNT,
        },
        "m2_destination": {
            "scene_folder": M2_DESTINATION_SCENE,
            "hostile_placements": m2_census["hostile"],
            "unambiguous_placements": m2_census["unambiguous"],
            **m2_fields,
        },
        "scenes_scanned": scanned,
        "scenes_scanned_with_bgnull_image_name": scanned_bgnull,
        "scenes_with_bgnull_image_name_in_full_registry": total_bgnull,
        "scenes_skipped": {
            "no_placement_file": sorted(skipped_no_file),
            "empty_placement_file": sorted(skipped_empty),
            "unreadable_placement_file": sorted(skipped_unreadable),
            "duplicate_placement_index": sorted(skipped_duplicate_index),
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
        "nonclaims": [
            "no claim that any candidate scene is reachable by a player - "
            "reachability is a travel-gate question, lane A's file",
            "no claim that a candidate's hostile monsters are placed usefully "
            "(spread out, near a spawn point, etc) - only that the data exists",
            "has_outdoor_air_companion is a naming-convention observation, "
            "not proof of anything: 'BgNull' in a scene's s_IMAGENAME column "
            "is common (%d of %d scanned scenes carry it, %d of all rows in "
            "the full registry table), so this field alone does not single "
            "out scene 278 - see m2_destination for the claim that does "
            "(its own registry name, not an absence)"
            % (scanned_bgnull, scanned, total_bgnull),
            "registered_in_scene_name_table false, or ambiguous_registry_match "
            "true, means this tool could not validate that candidate's name "
            "against the game's own scene registry - it is still counted by "
            "hostile placements, just not vouched for by name",
            "this tool does not decide which scene becomes the field for M3 "
            "- that is lane A's/COO's call against scenarios/world_*.json",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gamedata", required=True, type=Path,
                        help="pf_bridge/gamedata directory on the bridge clone")
    parser.add_argument("--out", type=Path,
                        help="write the JSON report here (default: stdout)")
    args = parser.parse_args(argv)

    try:
        report = scan(args.gamedata)
    except ScanError as exc:
        print("REFUSED: %s" % exc)
        return 1

    text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"

    if args.out:
        args.out.write_text(text, encoding="ascii")
        print("wrote %s (%d candidates, %d scenes scanned)"
              % (args.out, report["candidate_count"], report["scenes_scanned"]))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
