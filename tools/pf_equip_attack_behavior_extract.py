#!/usr/bin/env python3
"""LANE-B: attack-behavior crosswalk extractor (production attack pose).

WHAT THIS TOOL IS FOR.  ``combat_pose.py`` answers one production question --
"which BEHAVIOR id goes at ActionVital ``+0x30`` for the character that just
swung?" -- and it must answer it from committed client tables, never from a
typed-in constant.  This is that module's generator.  It reads three tables
off the bridge clone and writes the two local ASCII copies the module loads
with no pf_bridge sibling present.

    gamedata/tables/CONSTDATA_TH__EQUIP_VALUE.tsv       17 equipment KINDS
    gamedata/tables/CONSTDATA_TH__EQUIPMENT_BASE.tsv    974 equipment ITEMS
    gamedata/tables/CONSTDATA_TH__CHARCREATE_CLASS.tsv  5 selectable classes

WHY THIS TOOL EXISTS AT ALL.  ``pose_trial.py`` carries a hand-typed
``ATTACK_BEHAVIOR_BY_EQUIP_TYPE`` under a comment stating, in capitals, that
the table "CANNOT BE RE-DERIVED INSIDE THIS REPOSITORY" and inviting whoever
lands the source tables to "replace this comment with a test that re-derives
the six rows".  pf-adversary had measured the hole it names (D3: changing 280
to 281 left the whole suite green).  The premise was wrong in one word --
``CONSTDATA_TH__EQUIP_VALUE.tsv`` is not tracked in THIS repository, but it
IS tracked in ``pf_bridge/gamedata/tables/``, which is where every other
committed table in ``src/pirateforce_foundation/data/`` came from.  So the
six rows are derivable, this tool derives them, and
``tests/test_combat_pose.py`` is the test that comment asked for.

THE TWO OUTPUTS, AND WHAT EACH ONE IS.

``equip_value_attack_behavior.tsv`` -- all 17 rows of EQUIP_VALUE, three
columns (``n_ID``, ``n_EQUIPTYPE``, ``n_ATTACK_SKILL``).  ``s_NAME`` is
dropped, not translated: the names are CJK and this repository's committed
data copies are read with ``encoding="ascii"`` (a non-ASCII byte on the
bridge's cp874 console kills the tool reading it).  EQUIP_VALUE is a KIND
table, not an item table: 17 rows, one per ``n_EQUIPTYPE`` bit (1, 2, 4, 8,
... 65536), each carrying the ``n_ATTACK_SKILL`` that ``RE-110``'s crosswalk
(``EQUIP_VALUE.n_EQUIPTYPE -> n_ATTACK_SKILL -> BEHAVIOR.n_ID``, chief
[PROVEN] 2026-09-04 14:05) resolves to a BEHAVIOR id.  Six of the 17 carry a
non-zero one; the other eleven (shield, armour, jewellery) carry 0, which is
this table saying "this kind does not swing" and is preserved as 0 rather
than dropped.

``creation_gear_by_class.tsv`` -- one row per selectable class, five columns
(``n_CLASS_ID``, ``n_SLOT_RHAND``, ``n_EQUIPMENT_BASE_ID``, ``n_EQUIPTYPE``,
``n_CONDITION_CLASS``).  This is the half that is DERIVED rather than copied,
so the derivation is spelled out here and re-checked three independent ways
below, because one of the three is what a reader would otherwise have to take
on trust:

  1. ``CHARCREATE_CLASS.n_SLOT_RHAND`` holds a value like ``2200002`` for
     class 1.  No committed table has a row with that id -- grepping all of
     ``gamedata/tables`` for ``2200002`` returns CHARCREATE_CLASS and nothing
     else.  Subtracting the ``2200000`` weapon-key base leaves ``2``, which
     IS an ``EQUIPMENT_BASE`` row.  That subtraction is the derivation, and
     on its own it would be a guess.

  2. CHECK A -- every one of the five decoded rows exists in EQUIPMENT_BASE.

  3. CHECK B -- every one of the five decoded rows is named with the
     character-creation prefix, and those rows are the ONLY rows in the
     entire 974-row table that carry it.  The prefix is CJK, so it is
     compared as a code point tuple (``_CREATION_PREFIX``) and never written
     to an output file.

  4. CHECK C -- the decoded row's own ``n_CONDITION_CLASS`` bitmask contains
     the bit of the class whose slot pointed at it, for all five.
     ``n_CONDITION_CLASS`` is EQUIPMENT_BASE's own answer to "which classes
     may equip this", so this is the table agreeing with the decode from the
     other direction, with no arithmetic in common.

  A tool that only did (1) would ship a plausible number.  A tool that fails
  any of A/B/C refuses and writes nothing -- see ``MineError``: there is no
  partial output.

  WHAT A/B/C DO AND DO NOT PIN, measured by pf-adversary rather than argued.
  They kill the OFFSET family outright: brute-forcing ``WEAPON_SLOT_KEY_BASE``
  over ``2199980..2200020`` leaves exactly one survivor, the correct 2200000.
  They do NOT pin a decode that lands on the wrong creation row, because the
  three checks only narrow the answer to ``{row exists} and {creation-named}
  and {CONDITION_CLASS & class_id}``, and that set has more than one member
  for two classes: base 2 and base 3 both carry ``n_CONDITION_CLASS = 3``, so
  class 1 and class 2 are mutually indistinguishable under all three, and
  class 2 additionally cannot be told from its own off-hand shield (base 4,
  mask 2).  Fed a ``CHARCREATE_CLASS`` with those two right hands SWAPPED,
  this tool writes a file, exit 0 -- Gladiator swinging the mace and Paladin
  the sword, all three checks satisfied.  So "three independent checks" is
  true and is not the same sentence as "the decode is pinned".  What actually
  holds the two apart is ``tests/test_combat_pose.py``'s spelled-out
  per-class expectations, plus the class-name agreement (Gladiator/sword,
  Sniper/gunshot) which is prose in a docstring and not a check anywhere.

WHAT THIS TOOL DOES NOT CLAIM.  That the class's starting right-hand weapon
is what the player is holding NOW.  Nothing in this repository persists an
equipped-item change yet (there is no equipped-weapon column in
``migrations/`` -- ``combat_pose.py``'s own header says so and says what
would have to land to make it a live read).  What it mines is the weapon the
class STARTS with, which for every character this server has ever created is
also the weapon it still holds.  The moment an inventory swap can happen,
this crosswalk needs an item-level read in front of it, and ``combat_pose``
names that as the seam.

The off-hand is deliberately not mined: class 2's ``n_SLOT_LHAND`` decodes to
the shield, whose ``n_ATTACK_SKILL`` is 0, and a hand that does not swing has
no pose to choose.  Class 1's ``n_SLOT_LHAND`` is the same id as its right
hand and the other three classes' is ``0``.
"""
import argparse
import csv
from pathlib import Path
import sys


# The base every CHARCREATE_CLASS hand-slot value in this snapshot sits on.
# See derivation step (1) in the module docstring, and checks A/B/C for why
# this is not left as an assumption.
WEAPON_SLOT_KEY_BASE = 2200000

# ``EQUIPMENT_BASE.s_NAME``'s character-creation prefix, as code points so
# this source file stays ASCII.  Renders as the three CJK characters meaning
# "for character creation".
_CREATION_PREFIX = "".join(chr(cp) for cp in (0x5275, 0x89D2, 0x7528))

EQUIP_VALUE_COLUMNS = ("n_ID", "n_EQUIPTYPE", "n_ATTACK_SKILL")
CREATION_GEAR_COLUMNS = (
    "n_CLASS_ID", "n_SLOT_RHAND", "n_EQUIPMENT_BASE_ID", "n_EQUIPTYPE",
    "n_CONDITION_CLASS",
)

EXPECTED_EQUIP_VALUE_ROWS = 17
EXPECTED_CLASS_ROWS = 5


class MineError(RuntimeError):
    """Any refusal.  There is no partial output: the tool writes or it does not."""


def _read_tsv_dicts(path: Path) -> list:
    if not path.is_file():
        raise MineError("missing source table: %s" % path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise MineError("empty source table: %s" % path)
    return rows


def _render_tsv(header: tuple, rows: list) -> str:
    lines = ["\t".join(header)]
    lines.extend("\t".join(str(cell) for cell in row) for row in rows)
    return "\n".join(lines) + "\n"


def extract_equip_value(gamedata_tables: Path) -> str:
    path = gamedata_tables / "CONSTDATA_TH__EQUIP_VALUE.tsv"
    rows = _read_tsv_dicts(path)
    if len(rows) != EXPECTED_EQUIP_VALUE_ROWS:
        raise MineError(
            "CONSTDATA_TH__EQUIP_VALUE.tsv has %d data row(s), expected %d -- "
            "the equipment-kind roster changed; re-read the crosswalk by hand "
            "before trusting a mechanical re-mine"
            % (len(rows), EXPECTED_EQUIP_VALUE_ROWS))
    seen_types = set()
    out = []
    for row in rows:
        equip_type = int(row["n_EQUIPTYPE"])
        if equip_type in seen_types:
            raise MineError(
                "EQUIP_VALUE carries n_EQUIPTYPE %d twice -- the table stopped "
                "being one row per kind, which is the property every lookup "
                "keyed on n_EQUIPTYPE depends on" % equip_type)
        seen_types.add(equip_type)
        out.append((
            int(row["n_ID"]), equip_type, int(row["n_ATTACK_SKILL"]),
        ))
    return _render_tsv(EQUIP_VALUE_COLUMNS, out)


def extract_creation_gear_by_class(gamedata_tables: Path) -> str:
    classes = _read_tsv_dicts(
        gamedata_tables / "CONSTDATA_TH__CHARCREATE_CLASS.tsv")
    if len(classes) != EXPECTED_CLASS_ROWS:
        raise MineError(
            "CONSTDATA_TH__CHARCREATE_CLASS.tsv has %d data row(s), expected "
            "%d -- the selectable class roster changed"
            % (len(classes), EXPECTED_CLASS_ROWS))
    base_rows = _read_tsv_dicts(
        gamedata_tables / "CONSTDATA_TH__EQUIPMENT_BASE.tsv")
    by_base_id = {}
    for row in base_rows:
        base_id = row["n_ID"]
        if base_id in by_base_id:
            raise MineError(
                "EQUIPMENT_BASE carries n_ID %s twice -- the decode below "
                "resolves a slot value to one row and cannot pick" % base_id)
        by_base_id[base_id] = row

    # CHECK B's denominator, computed BEFORE the decode so the two cannot be
    # made to agree by construction.
    creation_named = {
        row["n_ID"] for row in base_rows
        if row["s_NAME"].startswith(_CREATION_PREFIX)
    }

    out = []
    decoded_ids = set()
    for row in classes:
        class_id = int(row["n_ID"])
        slot_rhand = int(row["n_SLOT_RHAND"])
        if slot_rhand <= WEAPON_SLOT_KEY_BASE:
            raise MineError(
                "class %d n_SLOT_RHAND is %d, which is not above the %d "
                "weapon-key base this decode subtracts -- the slot encoding "
                "changed and must be re-read, not extrapolated"
                % (class_id, slot_rhand, WEAPON_SLOT_KEY_BASE))
        base_id = slot_rhand - WEAPON_SLOT_KEY_BASE
        # CHECK A.
        base_row = by_base_id.get(str(base_id))
        if base_row is None:
            raise MineError(
                "class %d n_SLOT_RHAND %d decodes to EQUIPMENT_BASE id %d, "
                "which has no row -- the %d base is wrong for this snapshot"
                % (class_id, slot_rhand, base_id, WEAPON_SLOT_KEY_BASE))
        # CHECK B.
        if str(base_id) not in creation_named:
            raise MineError(
                "class %d decodes to EQUIPMENT_BASE id %d, which is not one "
                "of the %d character-creation rows -- the decode landed on "
                "some other item"
                % (class_id, base_id, len(creation_named)))
        # CHECK C.
        condition_class = int(base_row["n_CONDITION_CLASS"])
        if not condition_class & class_id:
            raise MineError(
                "class %d decodes to EQUIPMENT_BASE id %d whose "
                "n_CONDITION_CLASS is %d and does not carry class %d's bit -- "
                "the table disagrees with the decode"
                % (class_id, base_id, condition_class, class_id))
        decoded_ids.add(str(base_id))
        out.append((
            class_id, slot_rhand, base_id, int(base_row["n_EQUIPTYPE"]),
            condition_class,
        ))

    # CHECK B, the other direction: every right hand decoded into the
    # creation-named set, and that set is not wildly larger than the hands
    # that reached it.  The off-hand shield is the one creation row no right
    # hand points at, and it is named here rather than allowed silently.
    unreached = creation_named - decoded_ids
    if len(unreached) > 1:
        raise MineError(
            "%d character-creation rows are not the right hand of any class "
            "(%s) -- expected at most the off-hand shield; the table gained "
            "creation gear this decode does not account for"
            % (len(unreached), sorted(unreached, key=int)))
    return _render_tsv(CREATION_GEAR_COLUMNS, out)


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
            extract_equip_value(gamedata_tables),
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
            if out_path.read_text(encoding="ascii") != text:
                mismatched.append("%s differs from a fresh mining" % out_path)
        if mismatched:
            print("CHECK FAILED:")
            for line in mismatched:
                print("  %s" % line)
            return 1
        print("CHECK OK: all %d attack-behavior tables match a fresh mining"
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
