"""LANE-CS: starting-skill-kit catalog, pinned to the committed client tables."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402
from pirateforce_foundation import class_catalog, skill_catalog  # noqa: E402


class SkillCatalogTests(unittest.TestCase):
    def test_the_eight_starting_kit_skill_ids(self):
        self.assertEqual(skill_catalog.SKILL_COUNT, 8)
        self.assertEqual(
            skill_catalog.STARTING_KIT_SKILL_IDS,
            (99, 110, 111, 40000, 41000, 42000, 43000, 44000))

    def test_titles_from_textdata_th_skill_text(self):
        self.assertEqual(skill_catalog.skill_title(99), "Normal Attack")
        self.assertEqual(skill_catalog.skill_title(110), "Strive Jump")
        self.assertEqual(skill_catalog.skill_title(111), "VIP Strive Jump")
        self.assertEqual(
            skill_catalog.skill_title(40000), "Gladiator Basic Training")
        self.assertEqual(
            skill_catalog.skill_title(41000), "Sharpshooter Basic Training")
        self.assertEqual(
            skill_catalog.skill_title(42000), "Stormherald Basic Training")
        self.assertEqual(
            skill_catalog.skill_title(43000), "Imperial Knights Basic Training")
        self.assertEqual(
            skill_catalog.skill_title(44000), "Light Priest Basic Training")

    def test_basic_training_title_differs_from_the_charcreate_icon_name(self):
        # Real, measured discrepancy (not a bug this catalog introduces):
        # CHARCREATE_CLASS's own s_ICON says "Sniper" for class id 4, but
        # SKILL_TEXT's title for that class's Basic Training skill (41000)
        # says "Sharpshooter" -- the two tables use different flavor names
        # for the same class.  Both are carried, undecided which is
        # "the" name; see class_catalog.py's module docstring nonclaims.
        sniper_class_name = class_catalog.class_name(4)
        sniper_basic_training_title = skill_catalog.skill_title(41000)
        self.assertEqual(sniper_class_name, "Sniper")
        self.assertEqual(sniper_basic_training_title, "Sharpshooter Basic Training")
        self.assertNotIn(sniper_class_name, sniper_basic_training_title)

    def test_every_class_starting_skill_id_resolves_in_this_catalog(self):
        # Cross-module consistency: class_catalog only names ids this module
        # is supposed to cover.
        for class_id in class_catalog.CLASS_IDS:
            for skill_id in class_catalog.starting_skill_ids(class_id):
                with self.subTest(class_id=class_id, skill_id=skill_id):
                    self.assertTrue(skill_catalog.is_known_skill_id(skill_id))
                    skill_catalog.skill_title(skill_id)
                    skill_catalog.skill_raw_context(skill_id)

    def test_level_learn_is_one_for_every_starting_kit_skill(self):
        for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                self.assertEqual(skill_catalog.level_learn(skill_id), 1)

    def test_raw_context_exposes_no_invented_type_field(self):
        # Guards against a future edit quietly adding a
        # basic/attack/AOE/buff/heal/passive classification that the
        # underlying table does not actually carry (pf-adversary, round
        # iazmrv, finding 4).
        context = skill_catalog.skill_raw_context(99)
        for forbidden in ("type", "skill_type", "category", "n_MP", "mp_cost"):
            self.assertNotIn(forbidden, context)

    def test_unknown_skill_id_raises(self):
        with self.assertRaises(KeyError):
            skill_catalog.skill_title(123456)
        with self.assertRaises(KeyError):
            skill_catalog.skill_raw_context(123456)

    def test_is_known_skill_id(self):
        self.assertTrue(skill_catalog.is_known_skill_id(99))
        self.assertFalse(skill_catalog.is_known_skill_id(45000))  # Voodooist lead, not carried

    def test_the_committed_copies_match_their_own_pins(self):
        context_raw = (
            ROOT / "src/pirateforce_foundation/data/skill_context_starting_kit.tsv"
        ).read_bytes()
        text_raw = (
            ROOT / "src/pirateforce_foundation/data/skill_text_starting_kit.tsv"
        ).read_bytes()
        self.assertEqual(
            hashlib.sha256(context_raw).hexdigest(),
            skill_catalog.CONTEXT_SOURCE_SHA256)
        self.assertEqual(
            hashlib.sha256(text_raw).hexdigest(),
            skill_catalog.TEXT_SOURCE_SHA256)

    @BRIDGE_GAMEDATA.skip_unless_present()
    def test_the_generator_reproduces_the_shipped_tables_when_it_can_run(self):
        """Real drift detection against ../pf_bridge, not just a self-hash
        (pf-adversary, round iazmrv -- same rationale as
        test_class_catalog.py's matching test)."""
        gamedata = ROOT.parent / "pf_bridge" / "gamedata"
        finished = subprocess.run(
            [sys.executable,
             str(ROOT / "tools/pf_class_skill_starting_kit_extract.py"),
             "--check", "--gamedata", str(gamedata)],
            capture_output=True, text=True)
        self.assertEqual(
            finished.returncode, 0,
            "the shipped skill catalog tables are not what a fresh mining "
            "produces:\n%s%s" % (finished.stdout, finished.stderr))


if __name__ == "__main__":
    unittest.main()
