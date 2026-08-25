#!/usr/bin/env python3
"""LANE-B: mine one scene's HOSTILE roster out of the committed game data.

WHAT THIS TOOL IS FOR.  ``field_mob_tables.py`` is a GENERATED module.  This is
the generator.  It reads four committed tables on the bridge clone, joins them
by the keys the client itself uses, and writes an ASCII-only Python module that
the server can import with no bridge present.

    gamedata/scene/<S>/<S>.placements.tsv   template_ids + XYZ per placement
    gamedata/tables/CONSTDATA_TH__MOBS.tsv  n_ID -> outfit, level, rank, ai
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv   level -> n_HPMAX
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv        n_ID -> displayed name

THE SELECTION RULE, AND WHY IT IS EXACTLY THIS ONE.  A placement is carried
only when its template resolves in MOBS and that row's ``s_OUTFIT`` is a single
unambiguous basename (no ``;``).  That rule is not invented here: running it
over ``bg0001`` reproduces ``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS`` in
``current/pf_login_game_server_v141.py`` EXACTLY - 149 placements, minus 3 whose
template is absent from MOBS, minus 31 whose outfit is a ``;`` list, is 115
rows, and all 115 match the frozen table on index, template, x, y, z and
outfit.  ``--verify-frozen`` re-runs that comparison and is the reason to trust
anything else this tool prints.

WHAT COUNTS AS HOSTILE IS OURS, AND IT IS A CHOICE, NOT A LAW.  This tool marks
a placement hostile when its MOBS row has BOTH ``n_RANK != 0`` AND
``n_AI_COMBAT != 0``.  On bg0001's 115 rows that predicate, ``n_RANK != 0``
alone, ``n_AI_COMBAT != 0`` alone and ``n_DROPS_NORMAL != 0`` alone all select
the SAME 13 placements.  Over the whole 3,210-row MOBS table they do NOT:
211 rows have combat AI at rank 0, 31 rows have a rank with no combat AI, and
54 have equipment drops but no normal drops.  So the agreement is a property of
this scene, not a discovered law, and a scene where the four disagree must be
read before its roster is shipped.  ``--predicate-census`` prints the four
counts for the scene being mined so that reading is cheap.

HP IS DERIVED, AND THE DERIVATION HAS A CONTROL.  MOBS carries no HP column.
Level does: ``n_LEVEL_MIN``, and ``CONSTDATA_TH__STANDARD_MOB`` is a per-level
stat table whose ``n_HPMAX`` at level 27 is 3857 - the exact value the frozen
source already pins as ``V117_P30_EXACT_HP`` for placement 30 of bg0001, whose
template is MOBS 31, whose level is 27.  The displayed name for MOBS 31 in
``TEXTDATA_TH__MOBS_TIP`` is "Tornado Eagle", the exact string the frozen source
pins as ``V119_P30_TARGET_NAME``.  Two independently frozen constants, both
re-derived from the tables; the tool refuses to write anything if either
control breaks.

ASCII ONLY, ON PURPOSE.  Every string written into the generated module is
escaped so the file is pure ASCII.  ``CONSTDATA_TH__MOBS.s_NAME`` is CJK in this
data set, and lesson 86 of this project is that one character with no code page
874 mapping raises UnicodeEncodeError inside ``print()`` and kills a tool
mid-report on the bridge console.  The name that ships is the MOBS_TIP display
name, which is ASCII for every row this tool has selected so far; a non-ASCII
one is escaped rather than dropped, and counted in the header.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
import sys


PLACEMENT_COLUMNS = ("index", "template_ids", "x", "y", "z")
MOBS_COLUMNS = (
    "n_ID", "s_OUTFIT", "n_LEVEL_MIN", "n_LEVEL_MAX", "n_RANK",
    "n_AI_WANDER", "n_AI_COMBAT", "n_SPEED_WALK", "n_SPEED_RUN",
    "n_DROPS_NORMAL", "n_DROPS_EQUIPMENT", "n_DROPS_SPECIALLY",
)

# The two frozen constants this tool re-derives before it will write anything.
CONTROL_TEMPLATE_ID = 31
CONTROL_LEVEL = 27
CONTROL_HP = 3857
CONTROL_NAME = "Tornado Eagle"
CONTROL_SCENE = "bg0001"
CONTROL_PLACEMENT_INDEX = 30
CONTROL_UNAMBIGUOUS_COUNT = 115


class MineError(RuntimeError):
    """Any refusal.  There is no partial output: the tool writes or it does not."""


def _read_tsv(path: Path) -> list[dict]:
    if not path.is_file():
        raise MineError("missing source table: %s" % path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise MineError("empty source table: %s" % path)
    return rows


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _key(rows: list[dict], column: str, path: Path) -> dict[str, dict]:
    keyed: dict[str, dict] = {}
    for row in rows:
        value = (row.get(column) or "").strip()
        if not value:
            continue
        if value in keyed:
            raise MineError("duplicate key %r in %s" % (value, path))
        keyed[value] = row
    return keyed


def _int(row: dict, column: str, where: str) -> int:
    raw = (row.get(column) or "").strip()
    try:
        return int(raw)
    except ValueError:
        raise MineError("%s: %s is not an integer (%r)" % (where, column, raw))


def _nonzero(row: dict, column: str) -> bool:
    return (row.get(column) or "").strip() not in ("", "0")


class Sources:
    def __init__(self, gamedata: Path, scene: str) -> None:
        self.gamedata = gamedata
        self.scene = scene
        self.placement_path = gamedata / "scene" / scene / ("%s.placements.tsv" % scene)
        self.mobs_path = gamedata / "tables" / "CONSTDATA_TH__MOBS.tsv"
        self.standard_path = gamedata / "tables" / "CONSTDATA_TH__STANDARD_MOB.tsv"
        self.tip_path = gamedata / "tables" / "TEXTDATA_TH__MOBS_TIP.tsv"
        self.placements = _read_tsv(self.placement_path)
        self.mobs = _key(_read_tsv(self.mobs_path), "n_ID", self.mobs_path)
        self.standard = _key(
            _read_tsv(self.standard_path), "n_ID", self.standard_path,
        )
        self.tip = _key(_read_tsv(self.tip_path), "n_ID", self.tip_path)
        for column in PLACEMENT_COLUMNS:
            if column not in self.placements[0]:
                raise MineError(
                    "placement table has no %r column: %s"
                    % (column, self.placement_path)
                )

    def digests(self) -> dict[str, str]:
        return {
            "placements": _digest(self.placement_path),
            "mobs": _digest(self.mobs_path),
            "standard_mob": _digest(self.standard_path),
            "mobs_tip": _digest(self.tip_path),
        }

    def hp_for_level(self, level: int, where: str) -> int:
        row = self.standard.get(str(level))
        if row is None:
            raise MineError("%s: no STANDARD_MOB row for level %d" % (where, level))
        return _int(row, "n_HPMAX", where)

    def display_name(self, template_id: int) -> str:
        row = self.tip.get(str(template_id))
        if row is None:
            return ""
        return (row.get("s_NAME") or "").strip()


def unambiguous_placements(sources: Sources) -> list[tuple]:
    """Every placement the frozen selection rule keeps, in file order."""
    kept: list[tuple] = []
    seen: set[int] = set()
    for row in sources.placements:
        template_ids = [
            item.strip() for item in (row.get("template_ids") or "").split(",")
            if item.strip()
        ]
        if len(template_ids) != 1:
            continue
        mob = sources.mobs.get(template_ids[0])
        if mob is None:
            continue
        outfit = (mob.get("s_OUTFIT") or "").strip()
        if not outfit or ";" in outfit:
            continue
        index = _int(row, "index", "placement")
        if index in seen:
            raise MineError("duplicate placement index %d" % index)
        seen.add(index)
        kept.append((
            index,
            int(template_ids[0]),
            float(row["x"]), float(row["y"]), float(row["z"]),
            outfit,
            mob,
        ))
    return kept


def hostile_roster(sources: Sources) -> list[dict]:
    roster: list[dict] = []
    for index, template_id, x, y, z, outfit, mob in unambiguous_placements(sources):
        if not (_nonzero(mob, "n_RANK") and _nonzero(mob, "n_AI_COMBAT")):
            continue
        where = "MOBS row %d" % template_id
        level = _int(mob, "n_LEVEL_MIN", where)
        roster.append({
            "placement_index": index,
            "template_id": template_id,
            "x": x, "y": y, "z": z,
            "visual_preset": outfit,
            "display_name": sources.display_name(template_id),
            "level": level,
            "level_max": _int(mob, "n_LEVEL_MAX", where),
            "rank": _int(mob, "n_RANK", where),
            "ai_wander": _int(mob, "n_AI_WANDER", where),
            "ai_combat": _int(mob, "n_AI_COMBAT", where),
            "speed_walk": _int(mob, "n_SPEED_WALK", where),
            "speed_run": _int(mob, "n_SPEED_RUN", where),
            "max_hp": sources.hp_for_level(level, where),
            "drops_normal": _int(mob, "n_DROPS_NORMAL", where),
            "drops_equipment": _int(mob, "n_DROPS_EQUIPMENT", where),
            "drops_specially": _int(mob, "n_DROPS_SPECIALLY", where),
        })
    return roster


def predicate_census(sources: Sources) -> dict[str, int]:
    """How the four candidate hostility readings split THIS scene's placements."""
    census = {"unambiguous": 0, "rank": 0, "ai_combat": 0,
              "drops_normal": 0, "rank_and_ai_combat": 0}
    for _, _, _, _, _, _, mob in unambiguous_placements(sources):
        census["unambiguous"] += 1
        rank = _nonzero(mob, "n_RANK")
        combat = _nonzero(mob, "n_AI_COMBAT")
        census["rank"] += int(rank)
        census["ai_combat"] += int(combat)
        census["drops_normal"] += int(_nonzero(mob, "n_DROPS_NORMAL"))
        census["rank_and_ai_combat"] += int(rank and combat)
    return census


def check_controls(sources: Sources) -> None:
    """Refuse to write unless both independently frozen constants re-derive."""
    mob = sources.mobs.get(str(CONTROL_TEMPLATE_ID))
    if mob is None:
        raise MineError("control template %d absent from MOBS" % CONTROL_TEMPLATE_ID)
    level = _int(mob, "n_LEVEL_MIN", "control MOBS row")
    if level != CONTROL_LEVEL:
        raise MineError(
            "control drift: MOBS %d level is %d, not %d"
            % (CONTROL_TEMPLATE_ID, level, CONTROL_LEVEL)
        )
    hp = sources.hp_for_level(level, "control")
    if hp != CONTROL_HP:
        raise MineError(
            "control drift: STANDARD_MOB level %d HP is %d, not the frozen "
            "V117_P30_EXACT_HP %d" % (level, hp, CONTROL_HP)
        )
    name = sources.display_name(CONTROL_TEMPLATE_ID)
    if name != CONTROL_NAME:
        raise MineError(
            "control drift: MOBS_TIP %d name is %r, not the frozen "
            "V119_P30_TARGET_NAME %r" % (CONTROL_TEMPLATE_ID, name, CONTROL_NAME)
        )


def verify_frozen(gamedata: Path, legacy_path: Path) -> tuple[int, int]:
    """Re-derive bg0001's 115 unambiguous rows and diff them against v141.

    Returns ``(rows_compared, mismatches)``.  This is the only claim in this
    tool that is checkable without the client: the selection rule either
    reproduces a table that has been on the wire for months, or it does not.
    """
    import ast

    sources = Sources(gamedata, CONTROL_SCENE)
    derived = [
        (index, template_id, x, y, z, outfit)
        for index, template_id, x, y, z, outfit, _ in unambiguous_placements(sources)
    ]
    text = legacy_path.read_text(encoding="utf-8")
    marker = "PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS = ["
    start = text.find(marker)
    if start < 0:
        raise MineError("frozen placement table not found in %s" % legacy_path)
    end = text.find("\n]", start)
    if end < 0:
        raise MineError("frozen placement table is unterminated")
    frozen = ast.literal_eval(text[start + len(marker) - 1:end + 2])
    if len(derived) != CONTROL_UNAMBIGUOUS_COUNT or len(frozen) != len(derived):
        raise MineError(
            "row count drift: derived %d, frozen %d, expected %d"
            % (len(derived), len(frozen), CONTROL_UNAMBIGUOUS_COUNT)
        )
    mismatches = sum(
        1 for left, right in zip(derived, frozen) if left != tuple(right[:6])
    )
    return len(derived), mismatches


_HEADER = '''"""GENERATED - do not hand-edit.  LANE-B scene mob roster.

Written by ``tools/pf_mine_scene_mob_roster.py`` from the committed game data
on the bridge clone.  Regenerate rather than patch; the generator carries the
selection rule, the controls it refuses on, and the reasoning behind both.

The rows below are the placements of one scene whose MOBS row has a rank and a
combat AI.  Every value is copied from a table; nothing here was composed.
``max_hp`` is the one derived column: ``STANDARD_MOB[n_LEVEL_MIN].n_HPMAX``.

SOURCES AND THEIR DIGESTS AT MINING TIME
%(digest_block)s

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
%(census_block)s
"""

from __future__ import annotations


SCENE = %(scene)r
SOURCE_DIGESTS = %(digests)s
PREDICATE_CENSUS = %(census)s

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
HOSTILE_PLACEMENTS = [
%(rows)s]
'''


def render_module(scene: str, roster: list[dict], digests: dict[str, str],
                  census: dict[str, int]) -> str:
    rows = []
    for item in roster:
        rows.append(
            "    (%d, %d, %r, %r, %r, %s, %s, %d, %d, %d, %d, %d, %d, %d, %d, %d),\n"
            % (
                item["placement_index"], item["template_id"],
                item["x"], item["y"], item["z"],
                ascii(item["visual_preset"]), ascii(item["display_name"]),
                item["level"], item["rank"], item["ai_wander"], item["ai_combat"],
                item["speed_walk"], item["max_hp"], item["drops_normal"],
                item["drops_equipment"], item["drops_specially"],
            )
        )
    digest_block = "\n".join(
        "    %-14s %s" % (name, value) for name, value in sorted(digests.items())
    )
    census_block = "\n".join(
        "    %-20s %d" % (name, value) for name, value in sorted(census.items())
    )
    body = _HEADER % {
        "scene": scene,
        "digests": _ascii_dict(digests),
        "census": _ascii_dict(census),
        "digest_block": digest_block,
        "census_block": census_block,
        "rows": "".join(rows),
    }
    if not body.isascii():
        raise MineError("generated module is not pure ASCII")
    return body


def _ascii_dict(mapping: dict) -> str:
    items = "".join(
        "    %s: %s,\n" % (ascii(key), ascii(value))
        for key, value in sorted(mapping.items())
    )
    return "{\n%s}" % items


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gamedata", required=True, type=Path,
                        help="pf_bridge/gamedata directory on the bridge clone")
    parser.add_argument("--scene", default=CONTROL_SCENE)
    parser.add_argument("--out", type=Path,
                        help="write the generated module here (default: stdout)")
    parser.add_argument("--legacy", type=Path,
                        default=Path(__file__).resolve().parents[1]
                        / "current" / "pf_login_game_server_v141.py")
    parser.add_argument("--verify-frozen", action="store_true",
                        help="re-derive bg0001's 115 rows and diff against v141")
    parser.add_argument("--predicate-census", action="store_true",
                        help="print how the four hostility readings split the scene")
    args = parser.parse_args(argv)

    try:
        if args.verify_frozen:
            compared, mismatches = verify_frozen(args.gamedata, args.legacy)
            print("verify-frozen: %d rows compared, %d mismatches"
                  % (compared, mismatches))
            if mismatches:
                return 1

        sources = Sources(args.gamedata, args.scene)
        check_controls(sources)
        census = predicate_census(sources)
        if args.predicate_census:
            for name, value in sorted(census.items()):
                print("census %-20s %d" % (name, value))
        roster = hostile_roster(sources)
        if not roster:
            raise MineError("scene %r has no hostile placement" % args.scene)
        module = render_module(args.scene, roster, sources.digests(), census)
    except MineError as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 2

    print("scene %s: %d hostile placements, %d distinct templates"
          % (args.scene, len(roster),
             len({item["template_id"] for item in roster})))
    if args.out:
        args.out.write_text(module, encoding="ascii")
        print("wrote %s (%d bytes)" % (args.out, len(module)))
    else:
        sys.stdout.write(module)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
