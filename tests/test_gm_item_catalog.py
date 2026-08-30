"""GM-042 prep: item catalog, pinned to the committed extracted client tables."""
from __future__ import annotations

import csv
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import item_catalog

_DATA_DIR = ROOT / "src" / "pirateforce_foundation" / "gm" / "data"


def _read_raw(category_file: str) -> dict[int, tuple[str, int]]:
    """Read a local data TSV directly (bypassing item_catalog) so tests
    check against the actual file on disk, not hardcoded guesses."""
    path = _DATA_DIR / category_file
    rows: dict[int, tuple[str, int]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        assert header == ["n_ID", "s_NAME", "n_QUATITY_STACK"], header
        for n_id, name, stack in reader:
            rows[int(n_id)] = (name.strip(), int(stack))
    return rows


class GmItemCatalogDataFileTests(unittest.TestCase):
    """Sanity checks on the extracted files themselves (independent of the
    module under test), to catch a bad re-extraction."""

    def test_row_counts_match_the_documented_source_tables(self):
        self.assertEqual(len(_read_raw("gm_item_misc.tsv")), 1646)
        self.assertEqual(len(_read_raw("gm_item_consumable.tsv")), 1260)
        self.assertEqual(len(_read_raw("gm_item_quest.tsv")), 579)


class GmItemCatalogTests(unittest.TestCase):
    def test_data_file_sha256_matches_pin(self):
        for category, filename, expected in (
            ("misc", "gm_item_misc.tsv", item_catalog.SOURCE_SHA256_MISC),
            ("consumable", "gm_item_consumable.tsv", item_catalog.SOURCE_SHA256_CONSUMABLE),
            ("quest", "gm_item_quest.tsv", item_catalog.SOURCE_SHA256_QUEST),
        ):
            with self.subTest(category=category):
                actual = hashlib.sha256((_DATA_DIR / filename).read_bytes()).hexdigest()
                self.assertEqual(actual, expected)

    def test_known_items_from_each_category_read_from_file(self):
        # Sample a handful of ids per category straight from the raw file
        # (not guessed) and confirm the catalog agrees on name + stack.
        misc_raw = _read_raw("gm_item_misc.tsv")
        cons_raw = _read_raw("gm_item_consumable.tsv")
        quest_raw = _read_raw("gm_item_quest.tsv")

        for item_id in sorted(misc_raw)[:1] + sorted(misc_raw)[500:501] + sorted(misc_raw)[-1:]:
            name, stack = misc_raw[item_id]
            with self.subTest(category="misc", item_id=item_id):
                self.assertTrue(item_catalog.is_known_item(item_id, category="misc"))
                self.assertEqual(item_catalog.item_max_stack(item_id, "misc"), stack)
                if len(item_catalog.item_category(item_id)) == 1:
                    self.assertEqual(item_catalog.item_name(item_id), name)
                self.assertEqual(item_catalog.item_name(item_id, category="misc"), name)

        for item_id in sorted(cons_raw)[:1] + sorted(cons_raw)[500:501] + sorted(cons_raw)[-1:]:
            name, stack = cons_raw[item_id]
            with self.subTest(category="consumable", item_id=item_id):
                self.assertTrue(item_catalog.is_known_item(item_id, category="consumable"))
                self.assertEqual(item_catalog.item_max_stack(item_id, "consumable"), stack)
                self.assertEqual(item_catalog.item_name(item_id, category="consumable"), name)

        for item_id in sorted(quest_raw)[:1] + sorted(quest_raw)[300:301] + sorted(quest_raw)[-1:]:
            name, stack = quest_raw[item_id]
            with self.subTest(category="quest", item_id=item_id):
                self.assertTrue(item_catalog.is_known_item(item_id, category="quest"))
                self.assertEqual(item_catalog.item_max_stack(item_id, "quest"), stack)
                self.assertEqual(item_catalog.item_name(item_id, category="quest"), name)

    def test_unknown_item_id_is_not_known(self):
        self.assertFalse(item_catalog.is_known_item(99999999))
        self.assertEqual(item_catalog.item_category(99999999), ())
        with self.assertRaises(KeyError):
            item_catalog.item_name(99999999)

    def test_unknown_item_id_scoped_to_a_category_is_not_known(self):
        self.assertFalse(item_catalog.is_known_item(99999999, category="misc"))
        with self.assertRaises(KeyError):
            item_catalog.item_name(99999999, category="misc")

    def test_item_category_reports_every_matching_category(self):
        # id 1 is "Adventure Key" in misc but "Sky Lantern" in quest --
        # documented id collision, read straight from both raw files.
        misc_raw = _read_raw("gm_item_misc.tsv")
        quest_raw = _read_raw("gm_item_quest.tsv")
        self.assertIn(1, misc_raw)
        self.assertIn(1, quest_raw)
        self.assertNotEqual(misc_raw[1][0], quest_raw[1][0])
        self.assertEqual(item_catalog.item_category(1), ("misc", "quest"))

    def test_module_docstrings_misc_consumable_example_id_matches_the_data(self):
        # The module docstring's "IMPORTANT finding" paragraph illustrates the
        # misc/consumable collision with a specific id and names. An earlier
        # version of that paragraph named id 6 for this pair, which was wrong
        # (id 6 does not exist in misc at all -- pf-adversary caught the
        # off-by-one against id 7, the id that actually holds these two
        # names). Pin the real id here so a future data refresh that moves
        # these names off id 7 fails this test instead of leaving a stale
        # worked example in the docstring for the next reader to trust.
        # id 7 is actually a three-way collision (misc/consumable/quest), not
        # just the misc/consumable pair the docstring illustrates -- the
        # docstring only needs the misc and consumable names to be right.
        misc_raw = _read_raw("gm_item_misc.tsv")
        cons_raw = _read_raw("gm_item_consumable.tsv")
        self.assertIn(7, misc_raw)
        self.assertIn(7, cons_raw)
        self.assertEqual(misc_raw[7][0], "Earth Element")
        self.assertEqual(cons_raw[7][0], "Fruit Wine Jar")
        self.assertIn("misc", item_catalog.item_category(7))
        self.assertIn("consumable", item_catalog.item_category(7))
        self.assertNotIn(6, misc_raw)

    def test_item_name_on_a_colliding_id_without_category_raises(self):
        with self.assertRaises(ValueError):
            item_catalog.item_name(1)

    def test_item_name_on_a_colliding_id_with_category_disambiguates(self):
        misc_raw = _read_raw("gm_item_misc.tsv")
        quest_raw = _read_raw("gm_item_quest.tsv")
        self.assertEqual(item_catalog.item_name(1, category="misc"), misc_raw[1][0])
        self.assertEqual(item_catalog.item_name(1, category="quest"), quest_raw[1][0])

    def test_item_max_stack_unknown_id_in_known_category_raises_named_keyerror(self):
        # Before this round: a raw dict lookup leaked as `KeyError('99999999')`
        # -- indistinguishable by message from a wrong-dict bug. item_name's
        # KeyError already names the id and category; item_max_stack now
        # matches that contract instead of being the one lookup in this
        # module that does not.
        with self.assertRaises(KeyError) as ctx:
            item_catalog.item_max_stack(99999999, category="misc")
        self.assertIn("99999999", str(ctx.exception))
        self.assertIn("misc", str(ctx.exception))

    def test_item_max_stack_unknown_id_message_names_the_category_it_was_checked_against(self):
        # id 1 IS known in "quest" but not in "consumable" -- the message
        # must name the category actually queried (consumable), not the one
        # this id happens to resolve in elsewhere, or a reader debugging a
        # `/item 1 5` typo would be pointed at the wrong table.
        self.assertTrue(item_catalog.is_known_item(1, category="quest"))
        self.assertFalse(item_catalog.is_known_item(1, category="consumable"))
        with self.assertRaises(KeyError) as ctx:
            item_catalog.item_max_stack(1, category="consumable")
        self.assertIn("consumable", str(ctx.exception))

    def test_item_max_stack_known_id_unaffected_by_the_error_message_fix(self):
        # The fix only wraps the KeyError path; a real lookup must still
        # return the plain int it always did, not a wrapped/decorated value.
        misc_raw = _read_raw("gm_item_misc.tsv")
        item_id = next(iter(sorted(misc_raw)))
        _, expected_stack = misc_raw[item_id]
        self.assertEqual(
            item_catalog.item_max_stack(item_id, category="misc"), expected_stack
        )

    def test_unknown_category_string_raises_clean_value_error_not_bare_keyerror(self):
        with self.assertRaises(ValueError):
            item_catalog.is_known_item(1, category="weapon")
        with self.assertRaises(ValueError):
            item_catalog.item_name(1, category="weapon")
        with self.assertRaises(ValueError):
            item_catalog.item_max_stack(1, category="weapon")

    def test_category_item_counts(self):
        self.assertEqual(item_catalog.MISC_ITEM_COUNT, 1646)
        self.assertEqual(item_catalog.CONSUMABLE_ITEM_COUNT, 1260)
        self.assertEqual(item_catalog.QUEST_ITEM_COUNT, 579)


if __name__ == "__main__":
    unittest.main()
