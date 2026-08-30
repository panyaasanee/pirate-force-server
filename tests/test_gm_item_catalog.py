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

    def test_item_name_on_a_colliding_id_without_category_raises(self):
        with self.assertRaises(ValueError):
            item_catalog.item_name(1)

    def test_item_name_on_a_colliding_id_with_category_disambiguates(self):
        misc_raw = _read_raw("gm_item_misc.tsv")
        quest_raw = _read_raw("gm_item_quest.tsv")
        self.assertEqual(item_catalog.item_name(1, category="misc"), misc_raw[1][0])
        self.assertEqual(item_catalog.item_name(1, category="quest"), quest_raw[1][0])

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
