#!/usr/bin/env python3
"""LOOT-ROLL-001: offline verifier for the server-side loot roller (Door 2).

WHAT THIS PROVES, and where the proof stops
-------------------------------------------
That the loot roller is an honest reading of the committed round-100 fact pack
and that its output is reproducible from an INDEPENDENT re-derivation.  This
file does not ask the module what to expect: sections A, B and C re-implement
the id-decoding rule, the three roll primitives, the quality selection and the
whole roll ORDER from the raw JSON excerpt with their own code, and only then
compare the resulting text to what the module produced.  A symmetrical bug
would have to be written twice, in two different shapes, to survive.

It proves NOTHING about a client, a wire, or a database.  Nothing in this lane
has ever touched any of the three.  The roller is OUR reconstruction from
client-shipped data; the original server's roll order and RNG are unrecoverable
forever.  Doors 3 and 4 of the loot loop (a ground object appearing, and a
player picking it up) have no known wire path, so a roll result cannot reach a
player today.

DISCIPLINE
----------
Pure stdlib.  No server process, no socket, no database, no client, no
GameClient window, no repository write.  ASCII only, on purpose: the gate
console is code page 874.

Usage:
    py -3 tools/verify_loot_roller.py

Exit 0 = every guard held.  Exit 1 = at least one drifted, with the list.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
FIXTURE = ROOT / "tests" / "golden" / "loot_roll_tables_r100.json"
MODULE_PATH = SRC_ROOT / "loot_roll.py"

from pirateforce_foundation import loot_roll as module  # noqa: E402

# ---------------------------------------------------------------------------
# This reader's OWN constants, written as literals so section A can measure the
# module against THEM rather than against itself.  Fact pack section 5.
# ---------------------------------------------------------------------------
SCALE = 100000
OWN_DROP_SET_PREFIXES = {
    "DROPS_NORMAL": 27,
    "DROPS_SPECIALLY": 28,
    "DROPS_EQUIPMENT": 54,
    "DROPS_QUEST": 87,
}
OWN_ITEM_PREFIXES = {
    22: "EQUIPMENT_BASE",
    24: "ITEM_CONSUMABLES",
    25: "ITEM_QUEST",
    26: "ITEM_MISC",
}
OWN_QUALITY_ORDER = ("WHITE", "GREEN", "BLUE", "PURPLE", "ORANGE")
OWN_QUALITY_COLUMNS = (
    "n_WEIGHT_W", "n_WEIGHT_G", "n_WEIGHT_B", "n_WEIGHT_P", "n_WEIGHT_O",
)
PINNED_MOB = 900001
PINNED_SEED = 332
CROSS_CHECK_CASES = (
    (900001, 332), (900001, 20260820), (900002, 20260820), (900003, 1),
    (900004, 5), (900005, 5), (900006, 9), (900007, 4), (900008, 7),
    (900009, 3), (900010, 12),
)

guards = 0
failures = []


def check(label, condition, detail=""):
    global guards
    guards += 1
    if condition:
        print("  ok   %s" % label)
        return True
    failures.append(label)
    print("  FAIL %s%s" % (label, (" -- " + detail) if detail else ""))
    return False


# ---------------------------------------------------------------------------
# The verifier's own decoding, primitives and roll.  Nothing below imports a
# helper from the module it is checking.
# ---------------------------------------------------------------------------
def own_split(raw):
    return raw // SCALE, raw % SCALE


def own_decode_drop_set(raw, table, rows):
    """Return (low, reason).  reason is None when the id resolves."""
    if type(raw) is not int or type(raw) is bool:
        return None, "not_an_int"
    if raw == 0:
        return None, "zero"
    if raw < 0:
        return None, "negative"
    prefix, low = own_split(raw)
    if prefix != OWN_DROP_SET_PREFIXES[table]:
        return None, "wrong_prefix"
    if low == 0:
        return None, "zero"
    if rows is not None and low not in rows:
        return None, "absent_row"
    return low, None


def own_decode_item(raw):
    if type(raw) is not int or raw <= 0:
        return None, None, "not_an_item"
    prefix, low = own_split(raw)
    if prefix not in OWN_ITEM_PREFIXES:
        return None, None, "unknown_prefix"
    if low == 0:
        return None, None, "zero"
    return OWN_ITEM_PREFIXES[prefix], low, None


def own_rate_hits(rate, draw):
    return draw < rate / 100.0


def own_quantity(low, high, draw):
    span = high - low + 1
    value = low + int(draw * span)
    return max(low, min(high, value))


def own_weighted(weights, draw):
    total = sum(weights)
    if total <= 0:
        return None
    target = draw * total
    running = 0
    for index, weight in enumerate(weights):
        running += weight
        if running > target:
            return index
    return len(weights) - 1


def own_quality(quality_rows, rank, level, draw):
    """Return (name, refused, unpublished_band)."""
    for row in sorted(quality_rows, key=lambda entry: entry["n_ID"]):
        if row["n_MOB_RANK"] != rank:
            continue
        if row["band_published"]:
            if not row["n_MOB_LEVELMIN"] <= level <= row["n_MOB_LEVELMAX"]:
                continue
        weights = [row[column] for column in OWN_QUALITY_COLUMNS]
        index = own_weighted(weights, draw)
        if index is None:
            return None, "weights", not row["band_published"]
        return OWN_QUALITY_ORDER[index], None, not row["band_published"]
    return None, "no_row", False


def own_roll_lines(document, mob_row, seed):
    """The whole roll, re-derived, rendered in the module's pinned line form."""
    tables = document["tables"]
    normal_rows = {row["n_ID"]: row for row in tables["DROPS_NORMAL"]}
    equipment_rows = {row["n_ID"]: row for row in tables["DROPS_EQUIPMENT"]}
    specially_rows = {row["n_ID"]: row for row in tables["DROPS_SPECIALLY"]}
    quality_rows = tables["E_DROPS_QUALITY"]
    rng = random.Random(seed)
    rank = mob_row["n_RANK"]
    level = mob_row["n_LEVEL_MIN"]
    drops = []
    misses = []
    refusals = []
    padding = 0

    def drop_line(source, slot, item, table_name, quantity, quality, money, tags):
        return (
            "drop|%s|slot=%d|item=%s|table=%s|qty=%d|quality=%s|money=%s|tags=%s"
            % (source, slot, item, table_name, quantity, quality, money,
               ",".join(tags) if tags else "-")
        )

    low, reason = own_decode_drop_set(
        mob_row["n_DROPS_NORMAL"], "DROPS_NORMAL", normal_rows,
    )
    if reason is not None:
        refusals.append("refuse|DROPS_NORMAL|%s" % _reason_name(reason))
    else:
        for index, slot in enumerate(normal_rows[low]["slots"]):
            item_id = slot["n_ITEM"]
            rate = float(slot["f_RATE"])
            if item_id == 0 and rate == 0.0 and slot["n_MIN"] == 0 \
                    and slot["n_MAX"] == 0:
                padding += 1
                continue
            if not own_rate_hits(rate, rng.random()):
                misses.append(
                    "miss|DROPS_NORMAL|slot=%d|rate=%s" % (index, repr(rate))
                )
                continue
            quantity = own_quantity(slot["n_MIN"], slot["n_MAX"], rng.random())
            if item_id == 0:
                drops.append(drop_line(
                    "DROPS_NORMAL", index, "MONEY", "-", quantity, "-", "yes",
                    ["inference_money_slot_is_item_id_zero_with_a_nonzero_rate"],
                ))
                continue
            table_name, _low_item, item_reason = own_decode_item(item_id)
            if item_reason is not None:
                refusals.append(
                    "refuse|DROPS_NORMAL|%s" % _reason_name(item_reason)
                )
                continue
            drops.append(drop_line(
                "DROPS_NORMAL", index, str(item_id), table_name, quantity,
                "-", "no", [],
            ))

    for table_name, rows, raw_key, with_quality in (
        ("DROPS_EQUIPMENT", equipment_rows, "n_DROPS_EQUIPMENT", True),
        ("DROPS_SPECIALLY", specially_rows, "n_DROPS_SPECIALLY", False),
    ):
        low, reason = own_decode_drop_set(mob_row[raw_key], table_name, rows)
        if reason is not None:
            refusals.append("refuse|%s|%s" % (table_name, _reason_name(reason)))
            continue
        row = rows[low]
        rate = float(row["f_DROPS_RATE"])
        if not own_rate_hits(rate, rng.random()):
            misses.append("miss|%s|slot=-1|rate=%s" % (table_name, repr(rate)))
            continue
        count = own_quantity(row["n_NUMBER_MIN"], row["n_NUMBER_MAX"], rng.random())
        weights = [entry["n_WEIGHT"] for entry in row["entries"]]
        for pick in range(count):
            chosen = own_weighted(weights, rng.random())
            if chosen is None:
                refusals.append(
                    "refuse|%s|loot_roll_refused_weight_total_not_positive"
                    % table_name
                )
                continue
            entry = row["entries"][chosen]
            quality = "-"
            tags = []
            if with_quality:
                name, quality_reason, unpublished = own_quality(
                    quality_rows, rank, level, rng.random(),
                )
                if quality_reason == "no_row":
                    refusals.append(
                        "refuse|E_DROPS_QUALITY|"
                        "loot_roll_refused_no_quality_row_for_rank_and_level"
                    )
                elif quality_reason == "weights":
                    refusals.append(
                        "refuse|E_DROPS_QUALITY|"
                        "loot_roll_refused_weight_total_not_positive"
                    )
                if name is not None:
                    quality = name
                if unpublished:
                    tags.append(
                        "inference_quality_row_level_band_not_published_"
                        "treated_as_unbounded"
                    )
            item_table, _item_low, item_reason = own_decode_item(entry["n_ITEM"])
            if item_reason is not None:
                refusals.append(
                    "refuse|%s|%s" % (table_name, _reason_name(item_reason))
                )
                continue
            drops.append(drop_line(
                table_name, pick, str(entry["n_ITEM"]), item_table, 1,
                quality, "no", tags,
            ))

    if mob_row["n_DROPS_QUEST"] == 0:
        refusals.append("refuse|DROPS_QUEST|loot_roll_refused_drop_set_id_zero")
    else:
        refusals.append(
            "refuse|DROPS_QUEST|loot_roll_refused_quest_drops_not_implemented"
        )

    head = "mob=%d level=%d rank=%d padding_slots=%d" % (
        mob_row["n_ID"], level, rank, padding,
    )
    return tuple([head] + drops + misses + refusals)


def _reason_name(reason):
    return {
        "zero": "loot_roll_refused_drop_set_id_zero",
        "negative": "loot_roll_refused_id_not_a_positive_int",
        "not_an_int": "loot_roll_refused_id_not_a_positive_int",
        "wrong_prefix": "loot_roll_refused_wrong_table_prefix",
        "absent_row": "loot_roll_refused_row_absent_from_the_loaded_table",
        "unknown_prefix": "loot_roll_refused_unknown_item_category_prefix",
        "not_an_item": "loot_roll_refused_drop_set_id_zero",
    }[reason]


def main():
    print("LOOT-ROLL-001 verifier: the server-side loot roller (Door 2)")
    print("fixture: %s" % FIXTURE.relative_to(ROOT).as_posix())
    print()

    if not FIXTURE.is_file():
        print("FAIL: the excerpt is missing")
        return 1
    raw_text = FIXTURE.read_text(encoding="utf-8")
    document = json.loads(raw_text)
    tables = document["tables"]

    print("A. the id-encoding rule, re-derived over EVERY id in the excerpt")
    normal_rows = {row["n_ID"]: row for row in tables["DROPS_NORMAL"]}
    equipment_rows = {row["n_ID"]: row for row in tables["DROPS_EQUIPMENT"]}
    specially_rows = {row["n_ID"]: row for row in tables["DROPS_SPECIALLY"]}

    item_ids = []
    for row in tables["DROPS_NORMAL"]:
        item_ids.extend(slot["n_ITEM"] for slot in row["slots"])
    for key in ("DROPS_EQUIPMENT", "DROPS_SPECIALLY"):
        for row in tables[key]:
            item_ids.extend(entry["n_ITEM"] for entry in row["entries"])

    bad_item = []
    for raw in item_ids:
        if raw == 0:
            continue  # the money slot reading, judged by the caller
        table_name, low, reason = own_decode_item(raw)
        module_view = module.decode_item_id(raw)
        if reason is None:
            if not module_view.ok or module_view.table != table_name \
                    or module_view.low != low:
                bad_item.append(raw)
        elif module_view.ok:
            bad_item.append(raw)
    check("every item id in the excerpt decodes the same way in both readers",
          not bad_item, str(bad_item))
    check("the excerpt carries at least one id per published item prefix",
          {own_split(raw)[0] for raw in item_ids if raw} >= {22, 24, 26},
          str(sorted({own_split(raw)[0] for raw in item_ids if raw})))

    bad_set = []
    absent = []
    for row in tables["MOBS"]:
        for key, table_name, rows in (
            ("n_DROPS_NORMAL", "DROPS_NORMAL", normal_rows),
            ("n_DROPS_EQUIPMENT", "DROPS_EQUIPMENT", equipment_rows),
            ("n_DROPS_SPECIALLY", "DROPS_SPECIALLY", specially_rows),
            ("n_DROPS_QUEST", "DROPS_QUEST", None),
        ):
            raw = row[key]
            low, reason = own_decode_drop_set(raw, table_name, rows)
            module_view = module.decode_drop_set_id(
                raw, table_name,
                None if rows is None else module.load_loot_tables(FIXTURE),
            )
            if table_name == "DROPS_QUEST":
                continue
            if reason is None:
                if not module_view.ok or module_view.low != low:
                    bad_set.append((row["n_ID"], key, raw))
            else:
                if module_view.ok:
                    bad_set.append((row["n_ID"], key, raw))
                absent.append((row["n_ID"], key, reason))
    check("every drop-set reference decodes the same way in both readers",
          not bad_set, str(bad_set))
    check("the excerpt exercises the zero, wrong-prefix and absent-row refusals",
          {reason for _mob, _key, reason in absent}
          >= {"zero", "wrong_prefix", "absent_row"},
          str(sorted({reason for _m, _k, reason in absent})))
    check("the module's prefix tables are the fact pack's",
          dict(module.DROP_SET_PREFIXES) == OWN_DROP_SET_PREFIXES
          and dict(module.ITEM_TABLE_PREFIXES) == OWN_ITEM_PREFIXES)
    check("the rule is prefix*100000 + row id in both readers",
          all(own_split(raw) == module.split_prefixed_id(raw)
              for raw in (2701001, 5400001, 2801553, 2200201, 8700035, 1, 0)))

    print()
    print("B. the primitives, re-derived at their boundaries")
    check("0 percent never fires and 100 percent always fires",
          not own_rate_hits(0.0, 0.0) and own_rate_hits(100.0, 1.0 - 1e-12)
          and not module.rate_succeeds(0.0, 0.0)
          and module.rate_succeeds(100.0, 1.0 - 1e-12))
    check("the 0.5 percent threshold is 0.005 and the entry AT it fails",
          own_rate_hits(0.5, 0.005 - 1e-9) and not own_rate_hits(0.5, 0.005)
          and module.rate_succeeds(0.5, 0.005 - 1e-9)
          and not module.rate_succeeds(0.5, 0.005))
    quantity_rows = [
        (3, 7, draw) for draw in (0.0, 0.2, 0.4, 0.6, 0.8, 0.999999)
    ]
    check("the quantity mapping agrees over its whole span",
          all(own_quantity(low, high, draw)
              == module.uniform_quantity(low, high, draw)
              for low, high, draw in quantity_rows))
    check("the quantity mapping never leaves the span",
          {own_quantity(3, 7, step / 997.0) for step in range(997)}
          == {3, 4, 5, 6, 7})
    published_specially = [15, 40, 45]
    check("the published DROPS_SPECIALLY row 1 boundaries are 0.15 and 0.55",
          [own_weighted(published_specially, draw)
           for draw in (0.0, 0.1499, 0.15, 0.5499, 0.55, 0.999999)]
          == [0, 0, 1, 1, 2, 2])
    check("both weighted walks agree on every boundary of that row",
          all(own_weighted(published_specially, step / 1009.0)
              == module.weighted_pick(published_specially, step / 1009.0)
              for step in range(1009)))
    check("a zero weight total refuses in both readers",
          own_weighted([0, 0], 0.5) is None
          and module.weighted_pick([0, 0], 0.5) is None)

    print()
    print("C. E_DROPS_QUALITY, normalized by the ACTUAL sum")
    quality_rows = tables["E_DROPS_QUALITY"]
    check("the excerpt carries all 26 published quality rows",
          len(quality_rows) == 26, str(len(quality_rows)))
    row_1201 = [row for row in quality_rows if row["n_ID"] == 1201]
    weights_1201 = [row_1201[0][column] for column in OWN_QUALITY_COLUMNS]
    check("row 1201 is rank 4096 with weights G700 B299 P1",
          row_1201[0]["n_MOB_RANK"] == 4096 and weights_1201 == [0, 700, 299, 1, 0])
    check("row 1201 sums to 1000, NOT to 100",
          sum(weights_1201) == 1000, str(sum(weights_1201)))
    boundary_cases = (
        (0.0, "GREEN"), (0.6999, "GREEN"), (0.7, "BLUE"), (0.9989, "BLUE"),
        (0.999, "PURPLE"), (0.999999, "PURPLE"),
    )
    loaded = module.load_loot_tables(FIXTURE)
    mismatched = []
    for draw, expected in boundary_cases:
        own_name = own_quality(quality_rows, 4096, 64, draw)[0]
        module_name = module.select_quality(loaded, 4096, 64, draw)[0]
        if own_name != expected or module_name != expected:
            mismatched.append((draw, own_name, module_name, expected))
    check("the 1201 boundaries walk 700/1000 and 999/1000 in both readers",
          not mismatched, str(mismatched))
    check("a rank with no quality row refuses in both readers",
          own_quality(quality_rows, 0, 27, 0.5)[1] == "no_row"
          and module.select_quality(loaded, 0, 27, 0.5)[1].reason
          == "loot_roll_refused_no_quality_row_for_rank_and_level")
    sums = {row["n_ID"]: sum(row[c] for c in OWN_QUALITY_COLUMNS)
            for row in quality_rows}
    check("exactly one published quality row is not normalized to 100",
          sorted(row_id for row_id, total in sums.items() if total != 100)
          == [1201], str(sums))

    print()
    print("D. full deterministic rolls, re-derived and compared line for line")
    mob_rows = {row["n_ID"]: row for row in tables["MOBS"]}
    drift = []
    for mob_id, seed in CROSS_CHECK_CASES:
        own_lines = own_roll_lines(document, mob_rows[mob_id], seed)
        result = module.roll_mob_loot(
            loaded, loaded.mobs[mob_id], random.Random(seed),
        )
        module_lines = module.describe_loot_roll(result)
        if own_lines != module_lines:
            drift.append((mob_id, seed, own_lines, module_lines))
    check("every cross-checked roll matches the independent re-derivation",
          not drift,
          "" if not drift else "first drift: mob %d seed %d\n  own:    %s\n"
          "  module: %s" % (drift[0][0], drift[0][1], drift[0][2], drift[0][3]))
    pinned = own_roll_lines(document, mob_rows[PINNED_MOB], PINNED_SEED)
    check("the pinned roll (mob %d, seed %d) carries a money drop, an item "
          "drop, a graded equipment drop and the quest refusal" % (
              PINNED_MOB, PINNED_SEED),
          any("money=yes" in line for line in pinned)
          and any("ITEM_CONSUMABLES" in line for line in pinned)
          and any("quality=WHITE" in line for line in pinned)
          and any("quest_drops_not_implemented" in line for line in pinned),
          "\n  ".join(pinned))
    repeat = module.describe_loot_roll(module.roll_mob_loot(
        loaded, loaded.mobs[PINNED_MOB], random.Random(PINNED_SEED),
    ))
    check("re-seeding reproduces the roll inside this process",
          repeat == pinned)

    print()
    print("E. containment: pure logic, unreachable from dispatch")
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    check("the module imports stdlib only, nothing cross-layer",
          imported == {"__future__", "dataclasses", "json", "pathlib",
                       "random", "types", "typing"}, str(sorted(imported)))
    check("no other module in src references the lane",
          [path.name for path in sorted(SRC_ROOT.glob("*.py"))
           if path.name != "loot_roll.py"
           and "loot_roll" in path.read_text(encoding="utf-8")] == [])
    check("the lane declares itself unreachable from production dispatch",
          module.production_allowed is False
          and module.LOOT_ROLL_DISPATCH_REACHABLE is False)
    check("the module and the excerpt are ASCII (cp874 console safe)",
          _is_ascii(source) and _is_ascii(raw_text))
    check("the excerpt names the fact pack and says it is only an excerpt",
          "FACTPACK_R100_CONSTDATA_MONSTER_LOOT.md"
          in document["provenance"]["factpack"]
          and "267 rows" in document["provenance"]["the_real_tables_are_far_larger"])
    check("the excerpt carries no DROPS_QUEST table at all",
          "DROPS_QUEST" not in tables)
    check("every excerpt row declares whether it was published or composed",
          all(row.get("source") in ("factpack_r100_section_5",
                                    "composed_for_test")
              for rows in tables.values() for row in rows))
    check("every MOBS row in the excerpt is marked composed-for-test",
          all(row["source"] == "composed_for_test" for row in tables["MOBS"]))

    print()
    print("guards run: %d" % guards)
    if failures:
        print("RESULT: FAIL - %d guard(s) drifted: %s"
              % (len(failures), failures))
        return 1
    print("RESULT: PASS - the roller reproduces an independent re-derivation of "
          "the fact pack's drop model line for line, decodes every id in the "
          "excerpt the same way, normalizes E_DROPS_QUALITY row 1201 by its "
          "actual sum of 1000, refuses DROPS_QUEST by name, and claims nothing "
          "about a client, a wire or a database")
    return 0


def _is_ascii(text):
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
