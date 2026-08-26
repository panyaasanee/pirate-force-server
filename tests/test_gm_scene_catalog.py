"""GM-004: the GM scene-name catalog, generated from TEXTDATA_TH__SCENE_NAME_TIP.

Cross-checked against pf_bridge/notes_to_chief/20260826_1630_PANYA-ORDER-...:
Port Royal=1, Prison Exile Island=2, Spice Paradise Island=3, Slave Market
Island=4.  That letter counted "331 scenes"; the shipped table has 330 DATA
rows (the letter's count included the header row) -- reported back to chief
rather than silently carried as 331.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

from pirateforce_foundation.gm import scene_catalog  # noqa: E402


class TestGmSceneCatalog(unittest.TestCase):
    def test_row_count_matches_the_pinned_constant(self):
        self.assertEqual(len(scene_catalog.SCENE_CATALOG), scene_catalog.ROW_COUNT)

    def test_row_count_is_330_not_the_letters_331(self):
        self.assertEqual(scene_catalog.ROW_COUNT, 330)

    def test_the_four_names_the_opening_letter_cross_checked(self):
        expected = {
            1: "Port Royal",
            2: "Prison Exile Island",
            3: "Spice Paradise Island",
            4: "Slave Market Island",
        }
        for scene_id, name in expected.items():
            self.assertEqual(scene_catalog.SCENE_CATALOG[scene_id][0], name)
            self.assertEqual(scene_catalog.gm_scene_name(scene_id), name)

    def test_unknown_scene_id_returns_none(self):
        self.assertNotIn(-1, scene_catalog.SCENE_CATALOG)
        self.assertIsNone(scene_catalog.gm_scene_name(-1))

    def test_every_scene_id_is_a_positive_int(self):
        for scene_id in scene_catalog.SCENE_CATALOG:
            self.assertIsInstance(scene_id, int)
            self.assertGreater(scene_id, 0)

    def test_module_source_is_pure_ascii(self):
        path = ROOT / "src" / "pirateforce_foundation" / "gm" / "scene_catalog.py"
        path.read_text(encoding="ascii")  # raises on any non-ASCII byte

    @BRIDGE_GAMEDATA.skip_unless_present()
    def test_the_generator_reproduces_the_shipped_table_when_it_can_run(self):
        import subprocess

        gamedata = ROOT.parent / "pf_bridge" / "gamedata"
        finished = subprocess.run(
            [sys.executable, str(ROOT / "tools/pf_mine_gm_scene_catalog.py"),
             "--check", "--gamedata", str(gamedata)],
            capture_output=True, text=True)
        self.assertEqual(
            finished.returncode, 0,
            "the shipped catalog is not what a fresh mining produces:\n%s%s"
            % (finished.stdout, finished.stderr))
        self.assertIn("CHECK OK", finished.stdout)


if __name__ == "__main__":
    unittest.main()
