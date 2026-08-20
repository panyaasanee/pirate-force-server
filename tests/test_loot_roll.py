"""LOOT-ROLL-001 -- the server-side loot roller (Door 2), offline and pure.

What this file proves, and where the proof stops:

  * DETERMINISM: the same excerpt + the same mob + the same seed produce one
    pinned list of ASCII lines, in this process and in a SEPARATE process
    (a subprocess run with an independent hash seed re-derives the same text);
  * every REFUSAL fires by name and nothing is ever silently skipped -- the
    quest table refused by name, a drop-set id of 0, a prefix belonging to a
    different DROPS_* table, a low part absent from the loaded excerpt, an
    unknown item-category prefix, a rank/level with no E_DROPS_QUALITY row,
    and a weighted row whose weights are all zero;
  * the RATE boundaries: 0 pct never drops even at draw 0.0, 100 pct always
    drops even at a draw just below 1.0, and a fractional 0.5 pct drops just
    below the exact threshold 0.005 and refuses AT it;
  * the QUANTITY clamps: draw 0.0 is the minimum, a draw just below 1.0 is the
    maximum, and nothing in between leaves the span;
  * the WEIGHTED-PICK boundaries, enumerated by hand for the published
    DROPS_SPECIALLY row 1 (15/40/45) and for the UNNORMALIZED E_DROPS_QUALITY
    row 1201 (G700 B299 P1, sum 1000, not 100);
  * the MONEY-slot reading (item id 0 with a nonzero rate), carried with its
    [INFERENCE] tag on every money drop;
  * the roll does not mutate its input tables, and the loaded tables are
    read-only mappings of frozen rows;
  * containment: the module imports nothing from the runtime/dispatch layer,
    opens no socket and no database, has no scenario flag, is imported by no
    other module in ``src/``, and is pure ASCII.

NOT proven here: anything about a client, a wire, or a database.  This roller
is OUR reconstruction from client-shipped data; the original server's roll
order and RNG are unrecoverable forever.  Doors 3 and 4 of the loot loop (a
ground object appearing, and pickup) have no known wire path, so a roll result
cannot reach a player.  The fixture is a small documented excerpt of the
shipped tables, not the tables.
"""
from __future__ import annotations

import ast
import copy
import json
import random
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import loot_roll as lr  # noqa: E402

FIXTURE = ROOT / "tests" / "golden" / "loot_roll_tables_r100.json"
MODULE_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "loot_roll.py"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"

# The pinned deterministic roll.  Excerpt + mob 900001 + seed 332, rendered by
# describe_loot_roll.  If any of the roll order, the rate comparison, the
# quantity mapping, the weighted walk or the draw stream moves, this moves.
PINNED_MOB = 900001
PINNED_SEED = 332
PINNED_ROLL = (
    "mob=900001 level=27 rank=1 padding_slots=0",
    "drop|DROPS_NORMAL|slot=0|item=2400046|table=ITEM_CONSUMABLES|qty=1|"
    "quality=-|money=no|tags=-",
    "drop|DROPS_NORMAL|slot=4|item=MONEY|table=-|qty=1|quality=-|money=yes|"
    "tags=inference_money_slot_is_item_id_zero_with_a_nonzero_rate",
    "drop|DROPS_EQUIPMENT|slot=0|item=2200201|table=EQUIPMENT_BASE|qty=1|"
    "quality=WHITE|money=no|tags=-",
    "drop|DROPS_SPECIALLY|slot=0|item=2600042|table=ITEM_MISC|qty=1|quality=-|"
    "money=no|tags=-",
    "drop|DROPS_SPECIALLY|slot=1|item=2600042|table=ITEM_MISC|qty=1|quality=-|"
    "money=no|tags=-",
    "drop|DROPS_SPECIALLY|slot=2|item=2600043|table=ITEM_MISC|qty=1|quality=-|"
    "money=no|tags=-",
    "miss|DROPS_NORMAL|slot=1|rate=15.0",
    "miss|DROPS_NORMAL|slot=2|rate=0.5",
    "miss|DROPS_NORMAL|slot=3|rate=0.5",
    "refuse|DROPS_QUEST|loot_roll_refused_quest_drops_not_implemented",
)


class ScriptedRandom(random.Random):
    """A random.Random whose draws are a fixed list, so a test owns them all.

    The roller takes every stochastic decision through ``rng.random()`` and
    nothing else, which is exactly what makes this possible.
    """

    def __init__(self, draws):
        super().__init__(0)
        self._draws = list(draws)
        self.taken = []

    def random(self):  # noqa: D401 - overriding the one method the roller uses
        if not self._draws:
            raise AssertionError("the scripted rng ran out of draws")
        value = float(self._draws.pop(0))
        self.taken.append(value)
        return value

    @property
    def remaining(self):
        return tuple(self._draws)


def tables():
    return lr.load_loot_tables(FIXTURE)


def roll(mob_id, rng, level=None):
    loaded = tables()
    mob = loaded.mobs[mob_id]
    if level is not None:
        mob = lr.mob_at_level(mob, level)
    return lr.roll_mob_loot(loaded, mob, rng)


class DeterminismTests(unittest.TestCase):
    """Same tables + same mob + same seed = byte-identical, across processes."""

    def test_the_pinned_roll_reproduces_line_for_line(self):
        result = roll(PINNED_MOB, random.Random(PINNED_SEED))
        self.assertEqual(lr.describe_loot_roll(result), PINNED_ROLL)

    def test_repeating_the_seed_in_this_process_repeats_the_roll(self):
        first = lr.describe_loot_roll(roll(PINNED_MOB, random.Random(PINNED_SEED)))
        second = lr.describe_loot_roll(roll(PINNED_MOB, random.Random(PINNED_SEED)))
        self.assertEqual(first, second)

    def test_a_separate_process_re_derives_the_same_bytes(self):
        program = (
            "import sys, random\n"
            "sys.path.insert(0, %r)\n"
            "from pirateforce_foundation import loot_roll as lr\n"
            "t = lr.load_loot_tables(%r)\n"
            "r = lr.roll_mob_loot(t, t.mobs[%d], random.Random(%d))\n"
            "sys.stdout.write(chr(10).join(lr.describe_loot_roll(r)))\n"
            % (str(ROOT / "src"), str(FIXTURE), PINNED_MOB, PINNED_SEED)
        )
        completed = subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(tuple(completed.stdout.split("\n")), PINNED_ROLL)

    def test_a_different_seed_gives_a_different_roll(self):
        # Guard the guard: if the pin held for every seed the pin would be
        # measuring nothing.
        other = lr.describe_loot_roll(roll(PINNED_MOB, random.Random(20260820)))
        self.assertNotEqual(other, PINNED_ROLL)

    def test_the_roller_refuses_anything_but_an_injected_random_instance(self):
        loaded = tables()
        mob = loaded.mobs[PINNED_MOB]
        for bad in (None, 332, [0.5], random):
            with self.subTest(rng=type(bad).__name__):
                with self.assertRaises(ValueError) as raised:
                    lr.roll_mob_loot(loaded, mob, bad)
                self.assertIn("random.Random", str(raised.exception))


class IdDecodingTests(unittest.TestCase):
    """[PROVEN] prefix*100000 + n_ID, decoded totally and fail-closed."""

    def test_the_published_prefixes_are_the_fact_pack_ones(self):
        self.assertEqual(dict(lr.DROP_SET_PREFIXES), {
            "DROPS_NORMAL": 27, "DROPS_SPECIALLY": 28,
            "DROPS_EQUIPMENT": 54, "DROPS_QUEST": 87,
        })
        self.assertEqual(dict(lr.ITEM_TABLE_PREFIXES), {
            22: "EQUIPMENT_BASE", 24: "ITEM_CONSUMABLES",
            25: "ITEM_QUEST", 26: "ITEM_MISC",
        })

    def test_the_fact_pack_worked_examples_decode(self):
        for raw, table, low in (
            (2701001, "DROPS_NORMAL", 1001),
            (2801553, "DROPS_SPECIALLY", 1553),
            (5400001, "DROPS_EQUIPMENT", 1),
        ):
            with self.subTest(raw=raw):
                decoded = lr.decode_drop_set_id(raw, table)
                self.assertTrue(decoded.ok)
                self.assertEqual(decoded.low, low)
        for raw, item_table, low in (
            (2200201, "EQUIPMENT_BASE", 201),
            (2400046, "ITEM_CONSUMABLES", 46),
            (2500021, "ITEM_QUEST", 21),
            (2600041, "ITEM_MISC", 41),
        ):
            with self.subTest(raw=raw):
                decoded = lr.decode_item_id(raw)
                self.assertTrue(decoded.ok)
                self.assertEqual((decoded.table, decoded.low), (item_table, low))

    def test_a_zero_is_a_named_refusal_not_a_silent_skip(self):
        decoded = lr.decode_drop_set_id(0, "DROPS_NORMAL")
        self.assertFalse(decoded.ok)
        self.assertEqual(decoded.reason, lr.REFUSAL_ID_ZERO)

    def test_a_prefix_from_another_drops_table_is_a_named_refusal(self):
        decoded = lr.decode_drop_set_id(2801001, "DROPS_NORMAL")
        self.assertFalse(decoded.ok)
        self.assertEqual(decoded.reason, lr.REFUSAL_WRONG_TABLE_PREFIX)

    def test_a_low_part_absent_from_the_excerpt_is_a_named_refusal(self):
        decoded = lr.decode_drop_set_id(2799999, "DROPS_NORMAL", tables())
        self.assertFalse(decoded.ok)
        self.assertEqual(decoded.reason, lr.REFUSAL_ROW_ABSENT)

    def test_an_unknown_item_category_prefix_is_a_named_refusal(self):
        decoded = lr.decode_item_id(2300005)
        self.assertFalse(decoded.ok)
        self.assertEqual(decoded.reason, lr.REFUSAL_UNKNOWN_ITEM_PREFIX)

    def test_decoding_is_total_and_never_raises(self):
        rng = random.Random(11)
        values = [0, -1, 1, 99999, 2700000, 2 ** 40, 87, 8700001]
        values.extend(rng.randrange(-10 ** 7, 10 ** 7) for _ in range(2000))
        odd = [None, "2701001", 27.0, True, b"27", (), object()]
        loaded = tables()
        for value in values + odd:
            for table in ("DROPS_NORMAL", "DROPS_EQUIPMENT",
                          "DROPS_SPECIALLY", "DROPS_QUEST", "NOT_A_TABLE"):
                decoded = lr.decode_drop_set_id(value, table, loaded)
                self.assertIsInstance(decoded, lr.IdDecode)
                if not decoded.ok:
                    self.assertIn(decoded.reason, lr.LOOT_ROLL_REFUSAL_REASONS)
            item = lr.decode_item_id(value)
            self.assertIsInstance(item, lr.IdDecode)
            if not item.ok:
                self.assertIn(item.reason, lr.LOOT_ROLL_REFUSAL_REASONS)

    def test_a_bool_is_not_an_id(self):
        # True == 1 in Python; an id column that arrived as a bool is a bug,
        # not the row id 1.
        self.assertFalse(lr.decode_item_id(True).ok)
        self.assertFalse(lr.decode_drop_set_id(True, "DROPS_NORMAL").ok)


class QuestRefusalTests(unittest.TestCase):
    """DROPS_QUEST is refused by name.  It is not implemented and will not be."""

    def test_the_roll_refuses_the_quest_table_by_name(self):
        result = roll(PINNED_MOB, random.Random(PINNED_SEED))
        quest = [
            refusal for refusal in result.refusals
            if refusal.source_table == "DROPS_QUEST"
        ]
        self.assertEqual(len(quest), 1)
        self.assertEqual(quest[0].reason, lr.REFUSAL_QUEST_NOT_IMPLEMENTED)
        self.assertIn("311 of 2478", quest[0].detail)

    def test_no_quest_item_can_ever_appear_in_a_roll(self):
        loaded = tables()
        for mob_id in sorted(loaded.mobs):
            for seed in range(12):
                result = lr.roll_mob_loot(
                    loaded, loaded.mobs[mob_id], random.Random(seed),
                )
                for drop in result.drops:
                    self.assertNotEqual(drop.source_table, "DROPS_QUEST")

    def test_the_excerpt_carries_no_quest_table_and_the_loader_refuses_one(self):
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertNotIn("DROPS_QUEST", document["tables"])
        document["tables"]["DROPS_QUEST"] = []
        with self.assertRaises(lr.LootTableError):
            lr.build_loot_tables(document)

    def test_a_mob_with_no_quest_set_still_says_so(self):
        result = roll(900008, random.Random(3))
        reasons = {
            refusal.source_table: refusal.reason for refusal in result.refusals
        }
        self.assertEqual(reasons["DROPS_QUEST"], lr.REFUSAL_ID_ZERO)


class RateBoundaryTests(unittest.TestCase):
    """0 pct never, 100 pct always, and the exact threshold of 0.5 pct."""

    def test_the_primitive_boundaries(self):
        self.assertFalse(lr.rate_succeeds(0.0, 0.0))
        self.assertTrue(lr.rate_succeeds(100.0, 0.99999999))
        self.assertTrue(lr.rate_succeeds(0.5, 0.005 - 1e-9))
        self.assertFalse(lr.rate_succeeds(0.5, 0.005))
        self.assertFalse(lr.rate_succeeds(0.5, 0.005 + 1e-9))

    def test_zero_percent_never_drops_and_hundred_percent_always_drops(self):
        # Row 9003 slot 0 is 0 pct, slot 1 is 100 pct, slot 2 is 0.5 pct.
        rng = ScriptedRandom([0.0, 0.99999999, 0.0, 0.99999999])
        result = roll(900006, rng)
        sources = [(d.source_table, d.slot_index) for d in result.drops]
        self.assertEqual(sources, [("DROPS_NORMAL", 1)])
        self.assertEqual(
            [(m.slot_index, m.rate_percent) for m in result.misses],
            [(0, 0.0), (2, 0.5)],
        )

    def test_a_fractional_rate_drops_just_below_its_threshold(self):
        rng = ScriptedRandom([1.0 - 1e-12, 0.0, 0.0, 0.005 - 1e-9, 0.0])
        result = roll(900006, rng)
        slots = [(d.slot_index, d.quantity) for d in result.drops]
        self.assertEqual(slots, [(1, 1), (2, 3)])

    def test_a_fractional_rate_refuses_exactly_at_its_threshold(self):
        rng = ScriptedRandom([1.0 - 1e-12, 0.0, 0.0, 0.005])
        result = roll(900006, rng)
        self.assertEqual([d.slot_index for d in result.drops], [1])
        self.assertIn((2, 0.5), [(m.slot_index, m.rate_percent) for m in result.misses])
        self.assertEqual(rng.remaining, ())

    def test_a_missed_slot_is_reported_never_silently_dropped(self):
        result = roll(PINNED_MOB, random.Random(PINNED_SEED))
        self.assertTrue(result.misses)
        for miss in result.misses:
            self.assertIn(miss.source_table, lr.LOOT_ROLL_ORDER)
            self.assertTrue(miss.detail)


class QuantityTests(unittest.TestCase):
    """A flat integer span, clamped at both ends."""

    def test_the_primitive_covers_the_span_and_nothing_else(self):
        self.assertEqual(lr.uniform_quantity(3, 7, 0.0), 3)
        self.assertEqual(lr.uniform_quantity(3, 7, 0.19), 3)
        self.assertEqual(lr.uniform_quantity(3, 7, 0.2), 4)
        self.assertEqual(lr.uniform_quantity(3, 7, 0.99999999), 7)
        self.assertEqual(lr.uniform_quantity(3, 7, 1.0), 7)
        self.assertEqual(lr.uniform_quantity(5, 5, 0.5), 5)
        seen = {lr.uniform_quantity(3, 7, i / 1000.0) for i in range(1000)}
        self.assertEqual(seen, {3, 4, 5, 6, 7})

    def test_an_inverted_range_raises_rather_than_inventing_a_quantity(self):
        with self.assertRaises(ValueError):
            lr.uniform_quantity(7, 3, 0.5)

    def test_a_rolled_quantity_stays_inside_the_slot_span(self):
        # Row 9003 slot 2 is min 3, max 7 at 0.5 pct.
        for draw in (0.0, 0.25, 0.5, 0.75, 0.999999):
            with self.subTest(draw=draw):
                rng = ScriptedRandom([1.0, 1.0, 0.0, 0.0, draw])
                result = roll(900006, rng)
                rolled = [d for d in result.drops if d.slot_index == 2]
                self.assertEqual(len(rolled), 1)
                self.assertTrue(3 <= rolled[0].quantity <= 7)

    def test_the_money_slot_spans_its_published_range(self):
        # Published DROPS_NORMAL row 1: money 100 pct 15..25, then 50 pct 5..10,
        # then 20 pct 5..10.
        rng = ScriptedRandom([0.0, 0.0, 0.0, 0.99999999, 0.0, 0.5])
        result = roll(900010, rng)
        self.assertEqual(
            [(d.slot_index, d.quantity) for d in result.drops],
            [(0, 15), (1, 10), (2, 8)],
        )


class WeightedPickTests(unittest.TestCase):
    """An explicit cumulative walk, with every boundary enumerated by hand."""

    def test_the_published_specially_row_boundaries(self):
        weights = [15, 40, 45]  # fact pack DROPS_SPECIALLY row 1
        self.assertEqual(lr.weighted_pick(weights, 0.0), 0)
        self.assertEqual(lr.weighted_pick(weights, 0.1499), 0)
        self.assertEqual(lr.weighted_pick(weights, 0.15), 1)
        self.assertEqual(lr.weighted_pick(weights, 0.5499), 1)
        self.assertEqual(lr.weighted_pick(weights, 0.55), 2)
        self.assertEqual(lr.weighted_pick(weights, 0.99999999), 2)

    def test_a_zero_weight_entry_is_never_picked(self):
        weights = [0, 1, 0]
        for step in range(1000):
            self.assertEqual(lr.weighted_pick(weights, step / 1000.0), 1)

    def test_no_positive_total_refuses_rather_than_picking_entry_zero(self):
        self.assertIsNone(lr.weighted_pick([0, 0], 0.0))
        self.assertIsNone(lr.weighted_pick([], 0.5))

    def test_the_unequal_composed_row_boundary(self):
        weights = [1, 3]  # composed DROPS_EQUIPMENT row 9001, total 4
        self.assertEqual(lr.weighted_pick(weights, 0.2499), 0)
        self.assertEqual(lr.weighted_pick(weights, 0.25), 1)

    def test_the_zero_weight_row_refuses_inside_a_roll_by_name(self):
        result = roll(900009, ScriptedRandom([0.0, 0.0, 0.5]))
        self.assertEqual(
            [d for d in result.drops if d.source_table == "DROPS_EQUIPMENT"], [],
        )
        self.assertIn(
            lr.REFUSAL_WEIGHT_TOTAL_NOT_POSITIVE, result.refusal_reasons(),
        )

    def test_a_multi_pick_is_independent_and_may_repeat_an_entry(self):
        # Composed row 9001 always fires, always picks 2 items.  Both draws
        # land on entry 1, which the pinned reading allows.
        rng = ScriptedRandom([0.0, 0.0, 0.9, 0.0, 0.9, 0.0])
        result = roll(900002, rng)
        picked = [d.item_id for d in result.drops]
        self.assertEqual(picked, [2200401, 2200401])


class QualityTests(unittest.TestCase):
    """E_DROPS_QUALITY by rank + level band, normalized by the ACTUAL sum."""

    def test_the_excerpt_carries_all_twenty_six_published_rows(self):
        loaded = tables()
        self.assertEqual(len(loaded.quality), 26)
        self.assertEqual(
            [row.row_id for row in loaded.quality][:4], [1, 2, 3, 4],
        )

    def test_row_1201_is_not_normalized_to_one_hundred(self):
        loaded = tables()
        row = [entry for entry in loaded.quality if entry.row_id == 1201][0]
        self.assertEqual(row.mob_rank, 4096)
        self.assertEqual(row.weights, (0, 700, 299, 1, 0))
        self.assertEqual(sum(row.weights), 1000)

    def test_row_1201_boundaries_walk_the_actual_sum_not_one_hundred(self):
        loaded = tables()
        # Rank 4096 at level 64 selects row 1201; the boundaries are at
        # 700/1000 and 999/1000, NOT at 700/100.
        cases = (
            (0.0, "GREEN"), (0.6999, "GREEN"), (0.7, "BLUE"),
            (0.9989, "BLUE"), (0.999, "PURPLE"), (0.99999999, "PURPLE"),
        )
        for draw, expected in cases:
            with self.subTest(draw=draw):
                quality, refusal, unpublished = lr.select_quality(
                    loaded, 4096, 64, draw,
                )
                self.assertIsNone(refusal)
                self.assertEqual(quality, expected)
                self.assertTrue(unpublished)
        # Orange carries weight 0 in this row and can never be selected.
        selected = {
            lr.select_quality(loaded, 4096, 64, step / 5000.0)[0]
            for step in range(5000)
        }
        self.assertEqual(selected, {"GREEN", "BLUE", "PURPLE"})

    def test_the_level_band_picks_the_row(self):
        loaded = tables()
        # Rank 1 rows 1..8 partition the level line; row 2 covers 16..30.
        self.assertEqual(lr.select_quality(loaded, 1, 15, 0.99)[0], "GREEN")
        self.assertEqual(lr.select_quality(loaded, 1, 16, 0.0)[0], "WHITE")
        self.assertEqual(lr.select_quality(loaded, 1, 31, 0.6)[0], "GREEN")
        self.assertEqual(lr.select_quality(loaded, 2, 200, 0.999)[0], "BLUE")
        self.assertEqual(lr.select_quality(loaded, 4, 10, 0.5)[0], "BLUE")

    def test_a_rank_with_no_row_refuses_by_name_and_invents_no_quality(self):
        loaded = tables()
        quality, refusal, _ = lr.select_quality(loaded, 0, 27, 0.5)
        self.assertIsNone(quality)
        self.assertEqual(refusal.reason, lr.REFUSAL_NO_QUALITY_ROW)
        result = roll(900003, random.Random(1))
        equipment = [
            d for d in result.drops if d.source_table == "DROPS_EQUIPMENT"
        ]
        self.assertEqual(len(equipment), 1)
        self.assertIsNone(equipment[0].quality)
        self.assertIn(lr.REFUSAL_NO_QUALITY_ROW, result.refusal_reasons())

    def test_an_unpublished_band_is_tagged_wherever_it_is_used(self):
        result = roll(900002, random.Random(20260820))
        equipment = [
            d for d in result.drops if d.source_table == "DROPS_EQUIPMENT"
        ]
        self.assertTrue(equipment)
        for drop in equipment:
            self.assertIn(
                lr.INFERENCE_QUALITY_BAND_UNPUBLISHED, drop.inference_tags,
            )

    def test_quality_is_attached_only_to_equipment_drops(self):
        loaded = tables()
        for seed in range(40):
            result = lr.roll_mob_loot(
                loaded, loaded.mobs[PINNED_MOB], random.Random(seed),
            )
            for drop in result.drops:
                if drop.source_table != "DROPS_EQUIPMENT":
                    self.assertIsNone(drop.quality)


class MoneySlotTests(unittest.TestCase):
    """[INFERENCE] item id 0 with a nonzero rate is the money slot."""

    def test_a_money_slot_is_marked_and_tagged(self):
        rng = ScriptedRandom([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        result = roll(900010, rng)
        self.assertEqual(len(result.drops), 3)
        for drop in result.drops:
            self.assertTrue(drop.is_money)
            self.assertIsNone(drop.item_id)
            self.assertIsNone(drop.item_table)
            self.assertEqual(drop.inference_tags, (lr.INFERENCE_MONEY_SLOT,))

    def test_an_item_drop_is_never_marked_money(self):
        result = roll(PINNED_MOB, random.Random(PINNED_SEED))
        for drop in result.drops:
            if drop.item_id is not None:
                self.assertFalse(drop.is_money)
                self.assertEqual(drop.inference_tags, ())

    def test_a_padding_slot_is_neither_money_nor_a_decision(self):
        # Composed row 9002: slot 0 has an unknown item prefix, slot 1 is
        # padding (item 0, rate 0, min 0, max 0).
        result = roll(900007, ScriptedRandom([0.0, 0.0]))
        self.assertEqual(result.padding_slots, 1)
        self.assertEqual(result.drops, ())
        self.assertIn(lr.REFUSAL_UNKNOWN_ITEM_PREFIX, result.refusal_reasons())


class RefusalSurfaceTests(unittest.TestCase):
    """Every refusal path, by name, from a whole roll."""

    def test_the_reason_strings_are_unique_ascii_and_prefixed(self):
        reasons = lr.LOOT_ROLL_REFUSAL_REASONS
        self.assertEqual(len(set(reasons)), len(reasons))
        for reason in reasons:
            self.assertTrue(reason.startswith("loot_roll_refused_"), reason)
            reason.encode("ascii")

    def test_a_wrong_prefix_in_a_mob_row_refuses_the_whole_set(self):
        result = roll(900004, random.Random(5))
        self.assertIn(lr.REFUSAL_WRONG_TABLE_PREFIX, result.refusal_reasons())
        self.assertEqual(
            [d for d in result.drops if d.source_table == "DROPS_NORMAL"], [],
        )

    def test_an_absent_row_refuses_the_whole_set(self):
        result = roll(900005, random.Random(5))
        self.assertIn(lr.REFUSAL_ROW_ABSENT, result.refusal_reasons())

    def test_a_mob_with_no_sets_at_all_refuses_four_times_and_drops_nothing(self):
        result = roll(900008, random.Random(7))
        self.assertEqual(result.drops, ())
        self.assertEqual(
            [(r.source_table, r.reason) for r in result.refusals],
            [
                ("DROPS_NORMAL", lr.REFUSAL_ID_ZERO),
                ("DROPS_EQUIPMENT", lr.REFUSAL_ID_ZERO),
                ("DROPS_SPECIALLY", lr.REFUSAL_ID_ZERO),
                ("DROPS_QUEST", lr.REFUSAL_ID_ZERO),
            ],
        )

    def test_every_refusal_carries_a_reason_a_table_and_a_detail(self):
        loaded = tables()
        seen = set()
        for mob_id in sorted(loaded.mobs):
            for seed in range(20):
                result = lr.roll_mob_loot(
                    loaded, loaded.mobs[mob_id], random.Random(seed),
                )
                for refusal in result.refusals:
                    self.assertIn(refusal.reason, lr.LOOT_ROLL_REFUSAL_REASONS)
                    self.assertTrue(refusal.source_table)
                    self.assertTrue(refusal.detail)
                    seen.add(refusal.reason)
        self.assertEqual(seen, {
            lr.REFUSAL_ID_ZERO,
            lr.REFUSAL_WRONG_TABLE_PREFIX,
            lr.REFUSAL_ROW_ABSENT,
            lr.REFUSAL_UNKNOWN_ITEM_PREFIX,
            lr.REFUSAL_QUEST_NOT_IMPLEMENTED,
            lr.REFUSAL_NO_QUALITY_ROW,
            lr.REFUSAL_WEIGHT_TOTAL_NOT_POSITIVE,
        })


class TableImmutabilityTests(unittest.TestCase):
    """A roll must not touch the tables it reads."""

    def test_rolling_does_not_mutate_the_loaded_tables(self):
        loaded = tables()
        before = copy.deepcopy({
            "normal": dict(loaded.normal),
            "equipment": dict(loaded.equipment),
            "specially": dict(loaded.specially),
            "quality": loaded.quality,
            "mobs": dict(loaded.mobs),
        })
        for mob_id in sorted(loaded.mobs):
            for seed in range(15):
                lr.roll_mob_loot(
                    loaded, loaded.mobs[mob_id], random.Random(seed),
                )
        after = {
            "normal": dict(loaded.normal),
            "equipment": dict(loaded.equipment),
            "specially": dict(loaded.specially),
            "quality": loaded.quality,
            "mobs": dict(loaded.mobs),
        }
        self.assertEqual(before, after)

    def test_rolling_does_not_mutate_the_source_document(self):
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        pristine = copy.deepcopy(document)
        loaded = lr.build_loot_tables(document)
        for seed in range(10):
            lr.roll_mob_loot(
                loaded, loaded.mobs[PINNED_MOB], random.Random(seed),
            )
        self.assertEqual(document, pristine)

    def test_the_loaded_mappings_reject_assignment(self):
        loaded = tables()
        for mapping in (loaded.normal, loaded.equipment, loaded.specially,
                        loaded.mobs, loaded.provenance):
            with self.subTest(mapping=type(mapping).__name__):
                with self.assertRaises(TypeError):
                    mapping[999999] = None

    def test_the_rows_are_frozen(self):
        loaded = tables()
        with self.assertRaises(Exception):
            loaded.mobs[PINNED_MOB].rank = 9
        with self.assertRaises(Exception):
            loaded.normal[1001].slots[0].rate_percent = 1.0


class FixtureProvenanceTests(unittest.TestCase):
    """The excerpt must say where it came from and what it is not."""

    def setUp(self):
        self.document = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_the_provenance_block_names_the_fact_pack_and_the_const_data(self):
        provenance = self.document["provenance"]
        self.assertIn(
            "FACTPACK_R100_CONSTDATA_MONSTER_LOOT.md", provenance["factpack"],
        )
        self.assertIn("496DFB2E", provenance["const_data_of_record"])
        self.assertIn("267 rows", provenance["the_real_tables_are_far_larger"])
        self.assertIn(
            "do NOT exist on this machine",
            provenance["this_machine_has_no_const_data"],
        )

    def test_every_row_declares_whether_it_was_published_or_composed(self):
        for table, rows in self.document["tables"].items():
            for row in rows:
                with self.subTest(table=table, row=row.get("n_ID")):
                    self.assertIn(
                        row["source"],
                        ("factpack_r100_section_5", "composed_for_test"),
                    )

    def test_no_mobs_row_pretends_to_be_mined(self):
        for row in self.document["tables"]["MOBS"]:
            self.assertEqual(row["source"], "composed_for_test")
            self.assertIn("COMPOSED, NOT MINED", row["note"])

    def test_the_published_rows_are_the_ones_the_fact_pack_prints(self):
        published = {
            table: sorted(
                row["n_ID"] for row in rows
                if row["source"] == "factpack_r100_section_5"
            )
            for table, rows in self.document["tables"].items()
        }
        self.assertEqual(published["DROPS_NORMAL"], [1, 1001])
        self.assertEqual(published["DROPS_EQUIPMENT"], [1])
        self.assertEqual(published["DROPS_SPECIALLY"], [1])
        self.assertEqual(len(published["E_DROPS_QUALITY"]), 26)
        self.assertEqual(published["MOBS"], [])

    def test_the_fixture_is_ascii(self):
        FIXTURE.read_bytes().decode("utf-8").encode("ascii")

    def test_the_loader_refuses_a_row_with_no_declared_source(self):
        document = copy.deepcopy(self.document)
        del document["tables"]["DROPS_NORMAL"][0]["source"]
        with self.assertRaises(lr.LootTableError):
            lr.build_loot_tables(document)

    def test_the_loader_refuses_an_excerpt_with_no_provenance(self):
        document = copy.deepcopy(self.document)
        del document["provenance"]
        with self.assertRaises(lr.LootTableError):
            lr.build_loot_tables(document)

    def test_the_loader_refuses_an_impossible_rate_or_range(self):
        document = copy.deepcopy(self.document)
        document["tables"]["DROPS_NORMAL"][0]["slots"][0]["f_RATE"] = 101.0
        with self.assertRaises(lr.LootTableError):
            lr.build_loot_tables(document)
        document = copy.deepcopy(self.document)
        document["tables"]["DROPS_NORMAL"][0]["slots"][0]["n_MAX"] = 1
        with self.assertRaises(lr.LootTableError):
            lr.build_loot_tables(document)


class ContainmentTests(unittest.TestCase):
    """Pure server logic: no wire, no database, no dispatch, no scenario."""

    def setUp(self):
        self.source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_the_module_is_ascii_and_cp874_safe(self):
        self.source.encode("ascii")
        self.source.encode("cp874")

    def test_the_module_imports_only_stdlib_and_nothing_cross_layer(self):
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        self.assertEqual(imported, {
            "__future__", "dataclasses", "json", "pathlib", "random",
            "types", "typing",
        })
        for banned in ("socket", "sqlite3", "asyncio", "threading"):
            self.assertNotIn(banned, imported)

    def test_the_module_has_no_import_time_side_effects(self):
        allowed = (
            ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
            ast.ClassDef, ast.FunctionDef,
        )
        for node in self.tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                continue  # the module docstring
            self.assertIsInstance(node, allowed)

    def test_the_module_never_calls_the_module_global_random(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                target = node.func
                if isinstance(target.value, ast.Name) and target.value.id == "random":
                    self.fail(
                        "loot_roll called random.%s at module scope; the rng "
                        "must be injected" % target.attr
                    )

    def test_the_lane_is_not_reachable_from_production_dispatch(self):
        self.assertIs(lr.production_allowed, False)
        self.assertIs(lr.LOOT_ROLL_DISPATCH_REACHABLE, False)
        importers = sorted(
            path.name for path in SRC_ROOT.glob("*.py")
            if "loot_roll" in path.read_text(encoding="utf-8")
            and path.name != "loot_roll.py"
        )
        self.assertEqual(importers, [])

    def test_the_module_declares_which_readings_are_ours(self):
        self.assertIn(
            "roll_order_is_normal_then_equipment_then_specially_then_"
            "quest_refusal",
            lr.LOOT_ROLL_CHOSEN_READINGS,
        )
        self.assertIn("[OUR DESIGN]", self.source)
        self.assertIn("[INFERENCE]", self.source)
        self.assertIn("[PROVEN]", self.source)
        self.assertIn("NONCLAIMS", self.source)

    def test_the_rendering_is_ascii_for_every_mob_in_the_excerpt(self):
        loaded = tables()
        for mob_id in sorted(loaded.mobs):
            for seed in range(5):
                result = lr.roll_mob_loot(
                    loaded, loaded.mobs[mob_id], random.Random(seed),
                )
                for line in lr.describe_loot_roll(result):
                    line.encode("ascii")


if __name__ == "__main__":
    unittest.main()
