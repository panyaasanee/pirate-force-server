"""LANE-CS: class registry, pinned to the committed client table."""
from __future__ import annotations

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
