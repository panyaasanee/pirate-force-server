#!/usr/bin/env python3
"""LANE-B: attack-pose crosswalk data extractor.

WHAT THIS TOOL IS FOR.  ``combat_pose.py`` is a committed data module the
server imports with no pf_bridge sibling present.  This is its generator: it
reads the committed client tables on the bridge clone and writes the two
local TSV copies that module loads.

    gamedata/tables/CONSTDATA_TH__EQUIP_VALUE.tsv       n_EQUIPTYPE -> the
                                                         BEHAVIOR id that
                                                         kind swings with
    gamedata/tables/CONSTDATA_TH__CHARCREATE_CLASS.tsv  n_SLOT_RHAND, the
                                                         weapon key each of
                                                         the five selectable
                                                         classes starts with
    gamedata/tables/CONSTDATA_TH__EQUIPMENT_BASE.tsv    resolves that key to
                                                         an n_EQUIPTYPE

THE THREE-WAY CHECK (``combat_pose.py``'s module header calls these legs
(1)-(3)).  ``n_SLOT_RHAND`` is not an ``EQUIPMENT_BASE`` id by itself -- it is
that id plus ``WEAPON_KEY_BASE`` (2200000) -- and nothing commits that offset
in writing anywhere else, so this tool refuses to trust one subtraction on
its own.  Three independent checks must all agree before a row is written:

  A. the decoded id (``n_SLOT_RHAND - WEAPON_KEY_BASE``) exists as a row in
     ``EQUIPMENT_BASE``.
  B. that row is one of the SIX rows ``EQUIPMENT_BASE`` itself marks as
     character-creation stock -- ``s_NAME`` starting with the client's own
     "創角用" (character-creation-use) prefix -- and those six are the ONLY
     six of that shape in the 974-row table.  Computed independently of the
     decode (the prefix scan does not look at ``n_SLOT_RHAND`` at all), so
     the two cannot agree by construction.  (Five of the six are claimed by
     the five classes' right hands; the sixth, id 4, "創角用盾" -- a
     creation-stock SHIELD -- is not, and this tool does not claim it either;
     see ``combat_pose.py``'s module header on the left-hand seam.)
  C. the row's own ``n_CONDITION_CLASS`` bitmask carries the bit of the class
     that pointed at it (``condition_class & class_id == class_id``) --
     ``EQUIPMENT_BASE`` answering "who may equip this" from a third
     direction with no arithmetic in common with A or B.

A class whose ``n_SLOT_RHAND`` fails any of the three is refused, not
guessed: see ``MineError`` below.  There is no partial output.

SCOPE.  Five selectable classes only (``CHARCREATE_CLASS`` ships exactly
five: 1/2/4/16/32).  Extending the crosswalk past the class's STARTING
right-hand weapon (an equipped-item read overriding it) is the seam
``combat_pose.py``'s module header names and this tool does not attempt.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


# CONSTDATA_TH__EQUIPMENT_BASE.s_NAME's own marker for a character-creation
# stock item, in the client's original encoding.  Kept as one named constant
# rather than inlined so a future reader does not mistake it for noise.
_CREATION_STOCK_NAME_PREFIX = "創角用"  # "創角用"

# CONSTDATA_TH__CHARCREATE_CLASS.n_SLOT_RHAND is an EQUIPMENT_BASE id plus
# this offset.  Not committed anywhere else -- RE-110, chief [PROVEN]
# 2026-09-04.
WEAPON_KEY_BASE = 2200000


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


def _render_tsv(header: list, data_rows: list) -> str:
    return "\n".join(
        "\t".join(row) for row in ([header] + data_rows)) + "\n"


def extract_equip_value_attack_behavior(gamedata_tables: Path) -> str:
    """``n_ID``/``n_EQUIPTYPE``/``n_ATTACK_SKILL`` off every equip kind.

    All rows are carried, including the eleven whose ``n_ATTACK_SKILL`` is 0
    -- ``combat_pose.py``'s own loader is the one that decides 0 means "does
    not swing" and drops those from its dict; this tool mines the table, it
    does not pre-filter it.
    """
    path = gamedata_tables / "CONSTDATA_TH__EQUIP_VALUE.tsv"
    rows = _read_tsv_rows(path)
    header = rows[0]
    wanted = ("n_ID", "n_EQUIPTYPE", "n_ATTACK_SKILL")
    try:
        indexes = [header.index(name) for name in wanted]
    except ValueError as exc:
        raise MineError(
            "CONSTDATA_TH__EQUIP_VALUE.tsv is missing an expected column "
            "(need %s, have %s)" % (wanted, header)) from exc
    data_rows = [[row[i] for i in indexes] for row in rows[1:] if row]
    if not data_rows:
        raise MineError("CONSTDATA_TH__EQUIP_VALUE.tsv has no data rows")
    return _render_tsv(list(wanted), data_rows)


def _character_creation_stock_ids(gamedata_tables: Path) -> dict:
    """``{EQUIPMENT_BASE id: row}`` for the six character-creation rows.

    Independent of ``n_SLOT_RHAND`` on purpose (check B): this scans
    ``s_NAME`` alone, so a decode bug in the offset subtraction cannot make
    this set agree with it by construction.
    """
    path = gamedata_tables / "CONSTDATA_TH__EQUIPMENT_BASE.tsv"
    rows = _read_tsv_rows(path)
    header = rows[0]
    id_index = header.index("n_ID")
    name_index = header.index("s_NAME")
    stock = {}
    for row in rows[1:]:
        if not row:
            continue
        if row[name_index].startswith(_CREATION_STOCK_NAME_PREFIX):
            stock[row[id_index]] = row
    if len(stock) != 6:
        raise MineError(
            "CONSTDATA_TH__EQUIPMENT_BASE.tsv has %d character-creation-"
            "stock row(s) (s_NAME prefix %r), expected exactly 6 -- the "
            "client table changed shape underneath this tool's check B"
            % (len(stock), _CREATION_STOCK_NAME_PREFIX))
    return stock, header


def extract_creation_gear_by_class(gamedata_tables: Path) -> str:
    charcreate_path = (
        gamedata_tables / "CONSTDATA_TH__CHARCREATE_CLASS.tsv")
    charcreate_rows = _read_tsv_rows(charcreate_path)
    charcreate_header = charcreate_rows[0]
    class_id_index = charcreate_header.index("n_ID")
    slot_rhand_index = charcreate_header.index("n_SLOT_RHAND")

    stock, base_header = _character_creation_stock_ids(gamedata_tables)
    base_id_index = base_header.index("n_ID")
    equiptype_index = base_header.index("n_EQUIPTYPE")
    condition_class_index = base_header.index("n_CONDITION_CLASS")
    base_by_id = {}
    for row in _read_tsv_rows(
            gamedata_tables / "CONSTDATA_TH__EQUIPMENT_BASE.tsv")[1:]:
        if row:
            base_by_id[row[base_id_index]] = row

    out_rows = []
    for row in charcreate_rows[1:]:
        if not row:
            continue
        class_id = int(row[class_id_index])
        slot_rhand = int(row[slot_rhand_index])
        decoded_id = str(slot_rhand - WEAPON_KEY_BASE)

        # Check A: the decoded id exists as an EQUIPMENT_BASE row at all.
        base_row = base_by_id.get(decoded_id)
        if base_row is None:
            raise MineError(
                "class %d's n_SLOT_RHAND %d decodes to EQUIPMENT_BASE id "
                "%s, which does not exist (check A failed)"
                % (class_id, slot_rhand, decoded_id))

        # Check B: it is one of the six character-creation-stock rows.
        if decoded_id not in stock:
            raise MineError(
                "class %d's decoded EQUIPMENT_BASE id %s is not one of the "
                "six character-creation-stock rows (check B failed)"
                % (class_id, decoded_id))

        # Check C: the row's own class-condition bitmask carries this
        # class's bit.
        condition_class = int(base_row[condition_class_index])
        if (condition_class & class_id) != class_id:
            raise MineError(
                "class %d's decoded EQUIPMENT_BASE id %s has "
                "n_CONDITION_CLASS %d, which does not carry bit %d "
                "(check C failed)"
                % (class_id, decoded_id, condition_class, class_id))

        equip_type = base_row[equiptype_index]
        out_rows.append([
            str(class_id), str(slot_rhand), decoded_id, equip_type,
            str(condition_class),
        ])

    if not out_rows:
        raise MineError(
            "CONSTDATA_TH__CHARCREATE_CLASS.tsv has no data rows")
    return _render_tsv(
        ["n_CLASS_ID", "n_SLOT_RHAND", "n_EQUIPMENT_BASE_ID", "n_EQUIPTYPE",
         "n_CONDITION_CLASS"],
        out_rows)


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
        "equip_value_attack_behavior.tsv":
            extract_equip_value_attack_behavior(gamedata_tables),
        "creation_gear_by_class.tsv":
            extract_creation_gear_by_class(gamedata_tables),
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
        print("CHECK OK: both attack-pose tables match a fresh mining")
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
