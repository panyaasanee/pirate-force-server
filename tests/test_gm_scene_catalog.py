"""GM-004: scene id -> GM scene name catalog, pinned to the committed client table."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import scene_catalog


class GmSceneCatalogTests(unittest.TestCase):
    def test_known_scene_ids_from_the_owner_order_letter(self):
        # notes_to_chief 20260826_1630: Port Royal=1, Prison Exile Island=2, Spice Paradise Island=3
        self.assertEqual(scene_catalog.gm_scene_name(1), "Port Royal")
        self.assertEqual(scene_catalog.gm_scene_name(2), "Prison Exile Island")
        self.assertEqual(scene_catalog.gm_scene_name(3), "Spice Paradise Island")

    def test_scene_count_matches_the_committed_table(self):
        self.assertEqual(scene_catalog.SCENE_COUNT, 330)

    def test_unknown_scene_id_raises(self):
        with self.assertRaises(KeyError):
            scene_catalog.gm_scene_name(123456)

    def test_is_known_scene_id(self):
        self.assertTrue(scene_catalog.is_known_scene_id(1))
        self.assertFalse(scene_catalog.is_known_scene_id(123456))

    def test_ship_in_the_sea_scene_ids_share_the_client_scene_name_but_not_the_gm_name(self):
        # s_SCENE_NAME repeats "Ship in the Sea" for many ids; s_GM_SCENE_NAME
        # disambiguates each with a Thai label + numbered suffix, e.g. id 17
        # -> "เรือในทะเล 1(17)" -- the two columns answer different questions.
        ship_ids = [
            n_id
            for n_id, name in scene_catalog.SCENE_ID_TO_NAME.items()
            if name == "Ship in the Sea"
        ]
        self.assertIn(17, ship_ids)
        self.assertIn(18, ship_ids)
        self.assertGreaterEqual(len(ship_ids), 7)
        self.assertEqual(scene_catalog.gm_scene_name(17), "เรือในทะเล 1(17)")
        gm_names_for_ship_ids = {scene_catalog.gm_scene_name(n_id) for n_id in ship_ids}
        self.assertGreater(len(gm_names_for_ship_ids), 1)

    def test_scene_ids_named_finds_repeated_gm_names(self):
        # ids 308-327 all carry the literal GM name "Hidden Island"
        ids = scene_catalog.scene_ids_named("Hidden Island")
        self.assertIn(308, ids)
        self.assertIn(327, ids)
        self.assertGreaterEqual(len(ids), 20)

    def test_non_sequential_high_ids_present(self):
        # the table's n_ID column is not contiguous 1..330; 997/999 exist too
        self.assertTrue(scene_catalog.is_known_scene_id(997))
        self.assertTrue(scene_catalog.is_known_scene_id(999))


if __name__ == "__main__":
    unittest.main()
