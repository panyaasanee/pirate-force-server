"""LANE-CS: class registry, pinned to the committed client table."""
from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402
from pirateforce_foundation import class_catalog  # noqa: E402


class ClassCatalogTests(unittest.TestCase):
    def test_the_five_selectable_classes_from_charcreate_class(self):
        self.assertEqual(class_catalog.CLASS_COUNT, 5)
        self.assertEqual(class_catalog.CLASS_IDS, (1, 2, 4, 16, 32))
        self.assertEqual(
            class_catalog.CLASS_ID_TO_NAME,
            {
                1: "Gladiator",
                2: "Paladin",
                4: "Sniper",
                16: "Necromancer",
                32: "Sorcerer",
            },
        )

    def test_starting_skill_ids_match_s_skill_1_through_4(self):
        # gamedata/tables/CONSTDATA_TH__CHARCREATE_CLASS.tsv: 99/110/111 are
        # shared by every class; the class-specific "Basic Training" skill is
        # s_SKILL_2 in every row.
        self.assertEqual(
            class_catalog.starting_skill_ids(1), (111, 40000, 99, 110))
        self.assertEqual(
            class_catalog.starting_skill_ids(2), (111, 43000, 99, 110))
        self.assertEqual(
            class_catalog.starting_skill_ids(4), (111, 41000, 99, 110))
        self.assertEqual(
            class_catalog.starting_skill_ids(16), (111, 42000, 99, 110))
        self.assertEqual(
            class_catalog.starting_skill_ids(32), (111, 44000, 99, 110))

    def test_every_class_shares_the_same_three_universal_starting_skills(self):
        for class_id in class_catalog.CLASS_IDS:
            skills = class_catalog.starting_skill_ids(class_id)
            self.assertEqual((skills[0], skills[2], skills[3]), (111, 99, 110))

    def test_class_specific_basic_training_ids_are_all_distinct(self):
        basic_training_ids = {
            class_catalog.starting_skill_ids(class_id)[1]
            for class_id in class_catalog.CLASS_IDS
        }
        self.assertEqual(len(basic_training_ids), 5)

    def test_starting_dress_sets_all_three_looks_per_class(self):
        # gamedata/tables/CONSTDATA_TH__CHARCREATE_CLASS.tsv:
        # (n_DRESS_HAT, n_DRESS_CHEST[_2/_3], n_DRESS_LEGGINGS[_2/_3]).
        self.assertEqual(
            class_catalog.starting_dress_sets(1),
            ((0, 2300026, 2300027), (0, 2300032, 2300033), (0, 2300122, 2300123)))
        self.assertEqual(
            class_catalog.starting_dress_sets(2),
            ((0, 2300038, 2300039), (0, 2300044, 2300045), (0, 2300116, 2300117)))
        self.assertEqual(
            class_catalog.starting_dress_sets(4),
            ((0, 2300002, 2300003), (0, 2300011, 2300012), (0, 2300098, 2300099)))
        self.assertEqual(
            class_catalog.starting_dress_sets(16),
            ((0, 2300083, 2300084), (0, 2300071, 2300072), (0, 2300110, 2300111)))
        self.assertEqual(
            class_catalog.starting_dress_sets(32),
            ((0, 2300014, 2300015), (0, 2300023, 2300024), (0, 2300065, 2300066)))

    def test_source_table_has_no_per_look_hat_columns(self):
        # pf-adversary (round covering COO-DECISION 20260904_0548 item 2):
        # a test that only re-checks the *loaded* dress-set tuples for a
        # shared hat value is tautological -- class_catalog.py's loader
        # computes one _hat per row and reuses it for all three tuples by
        # construction, so it can never independently catch the source
        # table growing n_DRESS_HAT_2/_3.  Read the raw header instead: if
        # upstream ever adds per-look hat columns, this goes red and
        # starting_dress_sets' "hat is shared" claim (and the docstring
        # justifying it) needs re-deriving, not silently staying stale.
        with (ROOT / "src/pirateforce_foundation/data/charcreate_class.tsv").open(
            "r", encoding="ascii", newline=""
        ) as handle:
            header = next(csv.reader(handle, delimiter="\t"))
        self.assertIn("n_DRESS_HAT", header)
        self.assertNotIn("n_DRESS_HAT_2", header)
        self.assertNotIn("n_DRESS_HAT_3", header)

    def test_starting_dress_sets_hat_is_shared_across_all_three_looks(self):
        # Given the source-table fact above, the loader must actually reuse
        # that one hat value rather than, say, silently zeroing looks #2/#3.
        for class_id in class_catalog.CLASS_IDS:
            hats = {look[0] for look in class_catalog.starting_dress_sets(class_id)}
            self.assertEqual(len(hats), 1)

    def test_starting_dress_sets_chest_and_leggings_distinct_across_looks(self):
        # The 3 looks are meant to be visually distinct picks; a repeated
        # chest/leggings pair across looks would mean two "looks" are really
        # the same item and the table changed shape underneath this reader.
        for class_id in class_catalog.CLASS_IDS:
            chest_leggings_pairs = {
                look[1:] for look in class_catalog.starting_dress_sets(class_id)
            }
            self.assertEqual(len(chest_leggings_pairs), 3)

    def test_starting_dress_sets_unknown_class_id_raises(self):
        with self.assertRaises(KeyError):
            class_catalog.starting_dress_sets(999)

    def test_unknown_class_id_raises(self):
        with self.assertRaises(KeyError):
            class_catalog.class_name(999)
        with self.assertRaises(KeyError):
            class_catalog.starting_skill_ids(999)

    def test_is_known_class_id(self):
        self.assertTrue(class_catalog.is_known_class_id(1))
        self.assertFalse(class_catalog.is_known_class_id(8))  # bit unused by any row

    def test_voodooist_is_not_a_sixth_class(self):
        # SKILL_CONTEXT row 45000 (icon ICON_Class_Voodooist_s) exists but
        # CHARCREATE_CLASS ships no n_ID=8 row -- not selectable at creation.
        self.assertNotIn(8, class_catalog.CLASS_IDS)

    def test_the_committed_copy_matches_its_own_pin(self):
        # Exercises the SOURCE_SHA256 guard path without corrupting the real
        # file: re-imports would already have failed at collection time if
        # the pin were wrong, so this pins the pin itself against silent
        # edits to the constant.
        raw = (ROOT / "src/pirateforce_foundation/data/charcreate_class.tsv").read_bytes()
        import hashlib

        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), class_catalog.SOURCE_SHA256)

    @BRIDGE_GAMEDATA.skip_unless_present()
    def test_the_generator_reproduces_the_shipped_table_when_it_can_run(self):
        """Real drift detection, not just a self-hash.

        pf-adversary (round iazmrv) measured that a bare SOURCE_SHA256 pin
        "only catches an accidental hand-edit to the frozen copy; it is
        structurally blind to the upstream table changing."  This test closes
        that gap the same way tests/test_mob_loot.py does for
        pf_mine_scene_drop_tables.py: re-run the extractor against the live
        pf_bridge sibling and fail if the committed file is stale.
        """
        gamedata = ROOT.parent / "pf_bridge" / "gamedata"
        finished = subprocess.run(
            [sys.executable,
             str(ROOT / "tools/pf_class_skill_starting_kit_extract.py"),
             "--check", "--gamedata", str(gamedata)],
            capture_output=True, text=True)
        self.assertEqual(
            finished.returncode, 0,
            "the shipped class catalog table is not what a fresh mining "
            "produces:\n%s%s" % (finished.stdout, finished.stderr))


if __name__ == "__main__":
    unittest.main()
