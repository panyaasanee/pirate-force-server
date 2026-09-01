#!/usr/bin/env python3
"""LANE-B: mine the DROP SETS of one scene's hostile roster out of game data.

WHAT THIS TOOL IS FOR.  ``field_drop_tables.py`` is a GENERATED module, the
loot sibling of ``field_mob_tables.py``.  This is its generator.  It reads the
committed tables on the bridge clone, carries ONLY the drop sets the roster
actually references, resolves every item id those sets name, and writes an
ASCII-only Python module the server can import with no bridge present.

    gamedata/tables/CONSTDATA_TH__DROPS_NORMAL.tsv       per-slot rate rolls
    gamedata/tables/CONSTDATA_TH__DROPS_EQUIPMENT.tsv    one rate + weights
    gamedata/tables/CONSTDATA_TH__DROPS_SPECIALLY.tsv    one rate + weights
    gamedata/tables/CONSTDATA_TH__{EQUIPMENT_BASE,ITEM_*}.tsv   item rows
    gamedata/tables/TEXTDATA_TH__{EQUIPMENT_BASE,ITEM_*}_TIP.tsv   names

THE ID RULE IS NOT INVENTED HERE.  ``FACTPACK_R100_CONSTDATA_MONSTER_LOOT.md``
section 5 pins ``MOBS.n_DROPS_* = prefix * 100000 + n_ID`` and verifies it on
the full data (27 DROPS_NORMAL 62/62, 28 DROPS_SPECIALLY 107/107, 54
DROPS_EQUIPMENT 36/36).  Item ids inside those sets use the same scheme keyed
on the item-category table (22 EQUIPMENT_BASE, 24 ITEM_CONSUMABLES, 25
ITEM_QUEST, 26 ITEM_MISC).  This tool re-runs that rule on the roster's sets
and refuses to write anything if one set or one item id fails to resolve.

DROPS_QUEST IS REFUSED BY NAME, exactly as the round-100 fact pack and
``loot_roll.py`` refuse it: 2478 distinct DROPS_QUEST sets are referenced by
mobs and only 311 exist client-side, so ~87 pct of that model is absent and any
DROPS_QUEST row this tool wrote would be invention.  That table is not read,
not carried and not rolled.  A roster row that names one is carried WITHOUT it,
and the count is printed.

THE FOUR CONTROLS IT REFUSES ON.  Every one of them is a fact some other,
independently written artifact already pinned, so a table swap or a column
rename cannot pass quietly:

  1. ``EQUIPMENT_BASE`` 423 is named "Red leaves Hammer" in its TIP table --
     the exact string an attended observer read off the ground on 2026-08-25
     (``ground_loot_hypothesis`` docstring, GT-045 job 1135).
  2. That same row has ``n_DROPMODEL_TYPE`` NONZERO, and ``ITEM_MISC`` 1
     ("Adventure Key", the low part of 2600001) has it ZERO.  ~~"and the
     attended difference between the runs is explained by this column"~~ IS
     STRUCK, and struck rather than deleted because the first version of this
     tool shipped it: GT-045 CLOSED-ANSWERED (chief R163, 2026-08-25) measured
     a NAME LABEL and NO MODEL for 2200423, i.e. n_DROPMODEL_TYPE = 1 is NOT
     enough to draw a model.  NARROWED (Codex GDL-IMG-017, IMAGE layer,
     static): the column DOES directly select the NIF file path (item_id ->
     n_DROPMODEL_TYPE 0..12 -> a token -> .\Data\GC\F\<token>.nif), so it is
     not true that the column "explains nothing about drawing" -- what it
     still does NOT do is prove the selected model is ever rendered or
     geometry-visible on screen, which is exactly the gap GT-045 measured
     open.
     It stays as a CONTROL on the TABLES ONLY -- two rows whose values differ,
     so a swapped or re-versioned data set fails here -- and the generated
     module says on every row that it is not a claim.
  3. ``ITEM_CONSUMABLES`` 901 resolves -- the low part of 2400901, the item
     the canonical smoke backpack holds at identity 2 (RE-060 via
     ``item_operate_res_hypothesis``).
  4. The roster module and this tool agree on the scene: the sets carried are
     exactly the ones ``field_mob_tables.HOSTILE_PLACEMENTS`` names.

WHAT THIS TOOL DOES NOT DO.  It does not roll anything (that is
``mob_loot.roll_drops``), it does not decide what a rate means, it does not
normalize a weight, and it does not drop a slot whose rate is zero -- a zero
rate is DATA and it is carried, so the roller's own refusal can be tested
against a real row rather than a composed one.  It writes a table; the reading
of the table lives in exactly one place.

ASCII ONLY, ON PURPOSE.  Lesson 86: one character with no code page 874
mapping raises UnicodeEncodeError inside ``print()`` on the bridge console and
kills a tool mid-report.  Every name written into the generated module is
escaped to pure ASCII and the non-ASCII count is printed in its header.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
import sys


# prefix -> (table file stem, the column layout the roller expects)
DROP_SET_TABLES = {
    27: "DROPS_NORMAL",
    28: "DROPS_SPECIALLY",
    54: "DROPS_EQUIPMENT",
}
# item table code -> (const table stem, text table stem)
ITEM_TABLES = {
    22: ("EQUIPMENT_BASE", "EQUIPMENT_BASE_TIP"),
    24: ("ITEM_CONSUMABLES", "ITEM_CONSUMABLES_TIP"),
    25: ("ITEM_QUEST", "ITEM_QUEST_TIP"),
    26: ("ITEM_MISC", "ITEM_MISC_TIP"),
}
# Slot counts are DERIVED from each header at mining time (see _column_count).
# They are recorded here only as the values seen at HEAD, so a change shows up
# in a diff rather than in silence.
NORMAL_SLOTS_AT_HEAD = 30
EQUIPMENT_ENTRIES_AT_HEAD = 20
SPECIALLY_ENTRIES_AT_HEAD = 30
ID_SCALE = 100000

CONTROL_EQUIPMENT_ID = 423
CONTROL_EQUIPMENT_NAME = "Red leaves Hammer"
CONTROL_MISC_ID = 1
CONTROL_CONSUMABLE_ID = 901
CONTROL_SCENE = "bg0001"


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
            raise MineError("duplicate key %s in %s" % (_safe(value), path))
        keyed[value] = row
    return keyed


def _safe(value: object) -> str:
    """A cell as pure-ASCII text, for an error message.

    ``repr`` does NOT escape non-ASCII in Python 3, and the CONSTDATA name
    columns are CJK, so printing a bad cell through %r kills the tool with a
    UnicodeEncodeError on a code page 874 console -- exactly when the table is
    broken and the operator needs to read the refusal (lesson 86).  The
    docstring promised ASCII output and only the GENERATED module had it.
    """
    text = "" if value is None else str(value)
    return text.encode("unicode_escape").decode("ascii")


def _cell(row: dict, column: str, where: str) -> str:
    """The raw cell, refusing a MISSING COLUMN rather than reading it as 0.

    ``row.get(column)`` returning None is indistinguishable from an empty
    cell, so a renamed column used to mine as a zero: rename n_MAX_1 and every
    slot silently becomes an inverted span the roller then refuses at run time,
    with no refusal here and no change in any digest's meaning.
    """
    if column not in row:
        raise MineError(
            "%s: the source table has no column %s; it was renamed or the "
            "layout changed, and this tool will not mine a missing column as "
            "zero" % (where, column))
    return (row.get(column) or "").strip()


def _int(row: dict, column: str, where: str) -> int:
    raw = _cell(row, column, where)
    if raw == "":
        return 0
    try:
        return int(raw)
    except ValueError:
        raise MineError(
            "%s: %s is not an integer (%s)" % (where, column, _safe(raw)))


def _float(row: dict, column: str, where: str) -> float:
    raw = _cell(row, column, where)
    if raw == "":
        return 0.0
    try:
        return float(raw)
    except ValueError:
        raise MineError(
            "%s: %s is not a number (%s)" % (where, column, _safe(raw)))


def _column_count(table: dict, prefix: str) -> int:
    """How many ``<prefix><n>`` columns the header actually has.

    DERIVED, not hardcoded: the slot counts used to be constants that happened
    to match at HEAD, so a 31st slot column would have been truncated in
    silence.
    """
    row = next(iter(table.values()))
    count = 0
    while "%s%d" % (prefix, count + 1) in row:
        count += 1
    if count == 0:
        raise MineError("no %s1 column in the source table" % prefix)
    return count


def _ascii(text: str) -> tuple[str, bool]:
    """Return (pure-ASCII text, whether anything had to be escaped)."""
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        escaped = text.encode("unicode_escape").decode("ascii")
        return escaped, True
    return text, False


class Sources:
    def __init__(self, gamedata: Path) -> None:
        self.gamedata = gamedata
        self.paths: dict[str, Path] = {}
        self.tables: dict[str, dict[str, dict]] = {}
        for stem in DROP_SET_TABLES.values():
            self._load("CONSTDATA_TH__%s" % stem)
        for const_stem, text_stem in ITEM_TABLES.values():
            self._load("CONSTDATA_TH__%s" % const_stem)
            self._load("TEXTDATA_TH__%s" % text_stem)

    def load_mobs(self) -> dict[str, dict]:
        """MOBS itself, read ONLY to count the DROPS_QUEST sets refused here."""
        self._load("CONSTDATA_TH__MOBS")
        return self.tables["CONSTDATA_TH__MOBS"]

    def _load(self, stem: str) -> None:
        path = self.gamedata / "tables" / ("%s.tsv" % stem)
        self.paths[stem] = path
        self.tables[stem] = _key(_read_tsv(path), "n_ID", path)

    def digests(self) -> dict[str, str]:
        return {stem: _digest(path) for stem, path in sorted(self.paths.items())}


def _split_id(full_id: int, where: str) -> tuple[int, int]:
    if full_id <= 0:
        raise MineError("%s: id must be positive, got %d" % (where, full_id))
    return full_id // ID_SCALE, full_id % ID_SCALE


def resolve_item(sources: Sources, full_id: int, where: str) -> dict:
    """One item id -> its table code, low id, ASCII name and drop-model type."""
    table_code, low = _split_id(full_id, where)
    if table_code not in ITEM_TABLES:
        raise MineError(
            "%s: item id %d names table %d, which is not one of %s"
            % (where, full_id, table_code, sorted(ITEM_TABLES)))
    const_stem, text_stem = ITEM_TABLES[table_code]
    const_row = sources.tables["CONSTDATA_TH__%s" % const_stem].get(str(low))
    if const_row is None:
        raise MineError(
            "%s: item id %d has no row %d in %s"
            % (where, full_id, low, const_stem))
    text_row = sources.tables["TEXTDATA_TH__%s" % text_stem].get(str(low))
    raw_name = (text_row or {}).get("s_NAME") or ""
    name, escaped = _ascii(raw_name.strip())
    return {
        "item_id": full_id,
        "table_code": table_code,
        "table": const_stem,
        "low_id": low,
        "name": name,
        "name_escaped": escaped,
        "drop_model_type": _int(const_row, "n_DROPMODEL_TYPE", where),
    }


def resolve_normal(sources: Sources, set_id: int) -> dict:
    prefix, low = _split_id(set_id, "DROPS_NORMAL set %d" % set_id)
    if prefix != 27:
        raise MineError(
            "drops_normal %d has prefix %d, expected 27" % (set_id, prefix))
    row = sources.tables["CONSTDATA_TH__DROPS_NORMAL"].get(str(low))
    if row is None:
        raise MineError("DROPS_NORMAL has no row %d (set %d)" % (low, set_id))
    slots = []
    table = sources.tables["CONSTDATA_TH__DROPS_NORMAL"]
    for index in range(1, _column_count(table, "n_ITEM_") + 1):
        where = "DROPS_NORMAL %d slot %d" % (low, index)
        item = _int(row, "n_ITEM_%d" % index, where)
        rate = _float(row, "f_RATE_%d" % index, where)
        low_qty = _int(row, "n_MIN_%d" % index, where)
        high_qty = _int(row, "n_MAX_%d" % index, where)
        if item == 0 and rate == 0.0 and low_qty == 0 and high_qty == 0:
            continue
        if not 0.0 <= rate <= 100.0:
            raise MineError(
                "%s: rate %r is outside 0..100; the roller reads these as "
                "percentages and this tool will not ship a row it would have "
                "to guess about" % (where, rate))
        if low_qty > high_qty:
            raise MineError(
                "%s: quantity span %d..%d is inverted"
                % (where, low_qty, high_qty))
        slots.append((index, item, rate, low_qty, high_qty))
    return {"set_id": set_id, "low_id": low, "slots": tuple(slots)}


def resolve_weighted(sources: Sources, set_id: int, kind: str) -> dict:
    prefix, low = _split_id(set_id, "%s set %d" % (kind, set_id))
    expected = 54 if kind == "DROPS_EQUIPMENT" else 28
    if prefix != expected:
        raise MineError(
            "%s %d has prefix %d, expected %d" % (kind, set_id, prefix, expected))
    row = sources.tables["CONSTDATA_TH__%s" % kind].get(str(low))
    if row is None:
        raise MineError("%s has no row %d (set %d)" % (kind, low, set_id))
    count = _column_count(sources.tables["CONSTDATA_TH__%s" % kind], "n_ITEM_")
    where = "%s %d" % (kind, low)
    rate = _float(row, "f_DROPS_RATE", where)
    if not 0.0 <= rate <= 100.0:
        raise MineError(
            "%s: rate %r is outside 0..100" % (where, rate))
    number_min = _int(row, "n_NUMBER_MIN", where)
    number_max = _int(row, "n_NUMBER_MAX", where)
    if number_min > number_max:
        raise MineError(
            "%s: number span %d..%d is inverted"
            % (where, number_min, number_max))
    entries = []
    for index in range(1, count + 1):
        item = _int(row, "n_ITEM_%d" % index, where)
        weight = _int(row, "n_WEIGHT_%d" % index, where)
        if item == 0 and weight == 0:
            continue
        entries.append((index, item, weight))
    return {
        "set_id": set_id,
        "low_id": low,
        "rate": rate,
        "number_min": number_min,
        "number_max": number_max,
        "entries": tuple(entries),
    }


def check_controls(sources: Sources) -> dict:
    equipment = resolve_item(
        sources, 22 * ID_SCALE + CONTROL_EQUIPMENT_ID, "control 1")
    if equipment["name"] != CONTROL_EQUIPMENT_NAME:
        raise MineError(
            "control 1 broke: EQUIPMENT_BASE %d is named %r, the attended run "
            "read %r off the ground"
            % (CONTROL_EQUIPMENT_ID, equipment["name"], CONTROL_EQUIPMENT_NAME))
    if equipment["drop_model_type"] == 0:
        raise MineError(
            "control 2 broke: EQUIPMENT_BASE %d no longer has a nonzero drop "
            "model type; this is a fingerprint of the TABLES, not a claim "
            "about drawing (GT-045 measured no model for this very row)"
            % CONTROL_EQUIPMENT_ID)
    misc = resolve_item(sources, 26 * ID_SCALE + CONTROL_MISC_ID, "control 2")
    if misc["drop_model_type"] != 0:
        raise MineError(
            "control 2 broke: ITEM_MISC %d no longer has drop model type 0; "
            "the two control rows must keep differing in this column"
            % (CONTROL_MISC_ID,))
    consumable = resolve_item(
        sources, 24 * ID_SCALE + CONTROL_CONSUMABLE_ID, "control 3")
    return {
        "equipment_control": equipment,
        "misc_control": misc,
        "consumable_control": consumable,
    }


def mine(sources: Sources, roster: list) -> dict:
    normal: dict[int, dict] = {}
    equipment: dict[int, dict] = {}
    specially: dict[int, dict] = {}
    items: dict[int, dict] = {}
    money_slots = 0
    referenced_by: dict[int, list[int]] = {}
    for mob in roster:
        template_id = mob[1]
        for set_id, bucket, kind in (
            (mob[13], normal, "DROPS_NORMAL"),
            (mob[14], equipment, "DROPS_EQUIPMENT"),
            (mob[15], specially, "DROPS_SPECIALLY"),
        ):
            if set_id == 0:
                continue
            referenced_by.setdefault(set_id, [])
            if template_id not in referenced_by[set_id]:
                referenced_by[set_id].append(template_id)
            if kind == "DROPS_NORMAL":
                resolved = resolve_normal(sources, set_id)
            else:
                resolved = resolve_weighted(sources, set_id, kind)
            # THE DUPLICATE CHECK, and it is here because pf-adversary (round
            # 8ftmbx, D8) caught this tool CLAIMING one that did not exist.
            # The first draft of the union just did `if set_id in bucket:
            # continue` -- first writer wins, in silence -- while a comment in
            # main() told the reader that _render proved the union was
            # collision-free.  It proved nothing.  Two scenes CAN name the
            # same drop-set id, and if they ever resolved it differently this
            # tool would have shipped whichever one it read first.  They
            # cannot today (a set id is resolved from the global tables and
            # carries no scene), and that is now asserted rather than assumed.
            if set_id in bucket:
                if bucket[set_id] != resolved:
                    raise MineError(
                        "%s set %d resolves differently for two scenes in "
                        "this union; a drop-set id was assumed to mean the "
                        "same thing everywhere and does not" % (kind, set_id))
                continue
            bucket[set_id] = resolved
    for entry in normal.values():
        for index, item, rate, low_qty, high_qty in entry["slots"]:
            if item == 0:
                money_slots += 1
                continue
            if item not in items:
                items[item] = resolve_item(
                    sources, item,
                    "DROPS_NORMAL %d slot %d" % (entry["low_id"], index))
    for bucket, kind in ((equipment, "DROPS_EQUIPMENT"),
                         (specially, "DROPS_SPECIALLY")):
        for entry in bucket.values():
            for index, item, weight in entry["entries"]:
                if item == 0:
                    money_slots += 1
                    continue
                if item not in items:
                    items[item] = resolve_item(
                        sources, item,
                        "%s %d entry %d" % (kind, entry["low_id"], index))
    return {
        "normal": normal,
        "equipment": equipment,
        "specially": specially,
        "items": items,
        "money_slots": money_slots,
        "referenced_by": referenced_by,
    }


def _render(mined: dict, digests: dict, scenes: tuple, quest_sets: int) -> str:
    escaped = sum(1 for row in mined["items"].values() if row["name_escaped"])
    lines = []
    add = lines.append
    add('"""GENERATED - do not hand-edit.  LANE-B drop sets for one scene.')
    add("")
    add("Written by ``tools/pf_mine_scene_drop_tables.py`` from the committed game")
    add("data on the bridge clone.  Regenerate rather than patch; the generator")
    add("carries the id rule, the four controls it refuses on, and the reasons.")
    add("")
    add("Every value below is copied from a table.  Nothing here was composed, no")
    add("rate was rounded, no weight was normalized and no zero-rate slot was")
    add("dropped: a zero rate is data, and the roller's refusal is tested against")
    add("a real row because of it.")
    add("")
    add("DROPS_QUEST IS ABSENT ON PURPOSE.  Only 311 of the 2478 DROPS_QUEST")
    add("sets the mobs reference exist client-side, so ~87 pct of that model is")
    add("missing and any DROPS_QUEST row written here would be invention.")
    add("%d roster row(s) name one; they are carried without it." % quest_sets)
    add("")
    add("``drop_model_type`` is copied for information and is NOT a claim.  In")
    add("particular a nonzero value is NOT SUFFICIENT to make an item model")
    add("appear: GT-045 (CLOSED-ANSWERED 2026-08-25) put ids 2200423 and")
    add("2200003 on a real client's wire -- BOTH carry 1 -- and measured a name")
    add("label, brown dust and no model under the label that was seen.  Neither")
    add("of those ids is in the table below; no id in this file has ever been on")
    add("a client's wire.  The column is carried as a fingerprint of the tables")
    add("and as the pair this tool's control 2 compares; nothing more.")
    add("")
    add("SOURCES AND THEIR DIGESTS AT MINING TIME")
    for stem, digest in digests.items():
        add("    %-34s %s" % (stem, digest))
    add('"""')
    add("")
    add("from __future__ import annotations")
    add("")
    add("")
    add("# The scenes whose shipped rosters were mined into this module.  The")
    add("# tables below are their UNION: a drop-set id and an item id mean the")
    add("# same thing in every scene, so this is a superset of each scene's own")
    add("# table and never a merge of disagreeing rows.")
    add("SCENES = %r" % (scenes,))
    add("# ~~SCENE~~, kept as the first mined scene so an existing reader does")
    add("# not break; SCENES is what this module is actually about now.")
    add("SCENE = %r" % scenes[0])
    add("SOURCE_DIGESTS = {")
    for stem, digest in digests.items():
        add("    %r: %r," % (stem, digest))
    add("}")
    add("NON_ASCII_NAMES_ESCAPED = %d" % escaped)
    add("MONEY_SLOTS_IN_CARRIED_SETS = %d" % mined["money_slots"])
    add("")
    add("# set id -> ((slot_index, item_id, rate_percent, qty_min, qty_max), ...)")
    add("# Per-slot INDEPENDENT percentage rates, in table order.  item_id 0 is")
    add("# the money slot [INFERENCE, round-100 fact pack]: it has no item row.")
    add("DROPS_NORMAL = {")
    for set_id in sorted(mined["normal"]):
        entry = mined["normal"][set_id]
        add("    %d: (" % set_id)
        for index, item, rate, low_qty, high_qty in entry["slots"]:
            add("        (%d, %d, %r, %d, %d)," % (index, item, rate, low_qty, high_qty))
        add("    ),")
    add("}")
    add("")
    add("# set id -> (rate_percent, number_min, number_max,")
    add("#            ((entry_index, item_id, weight), ...))")
    add("# ONE roll at rate_percent, then a weighted pick among the entries.")
    for name, key in (("DROPS_EQUIPMENT", "equipment"),
                      ("DROPS_SPECIALLY", "specially")):
        add("%s = {" % name)
        for set_id in sorted(mined[key]):
            entry = mined[key][set_id]
            add("    %d: (%r, %d, %d, (" % (
                set_id, entry["rate"], entry["number_min"], entry["number_max"]))
            for index, item, weight in entry["entries"]:
                add("        (%d, %d, %d)," % (index, item, weight))
            add("    )),")
        add("}")
        add("")
    add("# item id -> (table_code, low_id, display_name, drop_model_type)")
    add("ITEMS = {")
    for item_id in sorted(mined["items"]):
        row = mined["items"][item_id]
        add("    %d: (%d, %d, %r, %d)," % (
            item_id, row["table_code"], row["low_id"], row["name"],
            row["drop_model_type"]))
    add("}")
    add("")
    add("# set id -> the MOBS template ids that reference it, in roster order")
    add("REFERENCED_BY = {")
    for set_id in sorted(mined["referenced_by"]):
        add("    %d: %r," % (set_id, tuple(mined["referenced_by"][set_id])))
    add("}")
    return "\n".join(lines) + "\n"


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--gamedata", type=Path,
        default=here.parent / "pf_bridge" / "gamedata",
        help="the bridge clone's gamedata directory")
    parser.add_argument(
        "--roster", type=Path, default=here / "src",
        help="directory holding pirateforce_foundation/field_mob_tables.py")
    parser.add_argument(
        "--out", type=Path,
        default=here / "src" / "pirateforce_foundation" / "field_drop_tables.py")
    parser.add_argument(
        "--scene", action="append", default=None,
        help="scene to mine; repeat to mine the UNION of several scenes' "
             "rosters (default: every scene this lane ships a roster for)")
    parser.add_argument(
        "--check", action="store_true",
        help="compose and compare against --out; write nothing")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(args.roster))
    from pirateforce_foundation import field_mob_tables
    from pirateforce_foundation import field_mob_tables_bg0002

    # ROUND 8ftmbx: THE UNION OF THE SCENES THIS LANE SHIPS, NOT ONE OF THEM.
    # Until this round the tool mined bg0001 alone, and that was fine while
    # bg0001 had thirteen monsters with drop sets.  COO-DECISION
    # 2026-08-29T00:41+07:00 withdrew nine of those rows and the four that
    # remain are practice dummies with n_DROPS_NORMAL 0 -- so a bg0001-only
    # mining now produces an EMPTY table, and every loot set the server can
    # actually roll (Bg0002's, the scene the owner confirmed by sight) would
    # be missing from the one module mob_loot imports.  The keys are global to
    # the game data on both sides (a drop-set id and an item id mean the same
    # thing in every scene), so a union is a superset rather than a merge of
    # disagreeing rows -- and `mine()` REFUSES BY NAME if that ever stops
    # being true, which is what makes this a claim rather than a hope.
    # (pf-adversary, D8: an earlier draft of this comment cited a duplicate
    # check in _render that did not exist, and the real behaviour was
    # first-writer-wins in silence.  The check exists now, in mine().)
    roster_modules = (field_mob_tables, field_mob_tables_bg0002)
    by_scene = {module.SCENE: module for module in roster_modules}
    scenes = args.scene if args.scene else [
        module.SCENE for module in roster_modules]
    unknown = [scene for scene in scenes if scene not in by_scene]
    if unknown:
        raise MineError(
            "control 4 broke: no roster module ships scene(s) %r; this lane "
            "has %r" % (unknown, sorted(by_scene)))
    sources = Sources(args.gamedata)
    controls = check_controls(sources)
    # Round szdkgs: every row the scene module SHIPS, not only the ones its
    # hostility predicate selected.  bg0001's HOSTILE_PLACEMENTS is empty
    # under the crosswalk (a town has no monsters) while its four town targets
    # are still shipped, and a drop table mined from the empty list would
    # silently drop every loot set this lane already sends.
    roster = []
    for scene in scenes:
        module = by_scene[scene]
        roster.extend(getattr(
            module, "SHIPPED_PLACEMENTS", module.HOSTILE_PLACEMENTS))
    mined = mine(sources, roster)
    mobs = sources.load_mobs()
    quest_sets = 0
    for mob in roster:
        row = mobs.get(str(mob[1]))
        if row is None:
            raise MineError(
                "roster template %d has no MOBS row; the roster module and this "
                "tool are reading different data" % mob[1])
        if _int(row, "n_DROPS_QUEST", "MOBS %d" % mob[1]) != 0:
            quest_sets += 1
    # D9 (pf-adversary, round 8ftmbx): `--scene bg0001` alone used to write a
    # module with every table empty and exit 0.  bg0001 ships four practice
    # dummies with n_DROPS_* zero in all three columns, so that is exactly the
    # command a reader who thinks this tool is "about bg0001" would run -- and
    # it would delete every loot set the server can roll, with a success
    # message.  The roster generator refuses an empty result by name; so does
    # this one now.
    if not (mined["normal"] or mined["equipment"] or mined["specially"]):
        raise MineError(
            "scene(s) %s name no drop set at all, so this would write an "
            "EMPTY table over the one the server rolls from.  bg0001 alone "
            "does this: its roster is four n_ID 916 practice dummies with "
            "n_DROPS_NORMAL/EQUIPMENT/SPECIALLY all zero.  Mine the union "
            "(no --scene at all) or name a scene that has monsters."
            % ", ".join(scenes))
    rendered = _render(mined, sources.digests(), tuple(scenes), quest_sets)

    print("scenes               %s" % ", ".join(scenes))
    print("roster rows          %d" % len(roster))
    print("drops_normal sets    %d" % len(mined["normal"]))
    print("drops_equipment sets %d" % len(mined["equipment"]))
    print("drops_specially sets %d" % len(mined["specially"]))
    print("distinct item ids    %d" % len(mined["items"]))
    print("money slots carried  %d" % mined["money_slots"])
    print("control 1 name       %s" % controls["equipment_control"]["name"])
    print("control 2 model      %d vs %d" % (
        controls["equipment_control"]["drop_model_type"],
        controls["misc_control"]["drop_model_type"]))
    print("control 3 consumable %s" % controls["consumable_control"]["name"])

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
    args.out.write_text(rendered, encoding="ascii")
    print("wrote %s (%d bytes)" % (args.out, len(rendered)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except MineError as exc:
        print("REFUSED: %s" % exc)
        sys.exit(2)
