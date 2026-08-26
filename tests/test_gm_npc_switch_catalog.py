"""GM-003 support: NPC GM-switch catalog, pinned to the committed client table."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import npc_switch_catalog


class GmNpcSwitchCatalogTests(unittest.TestCase):
    def test_known_gm_switch_npc_ids_from_the_owner_order_letter(self):
        # notes_to_chief 20260826_1630 section 2: CONSTDATA_TH__MOBS.n_GM_SWITCH=1
        # rows are 855, 871, 882, 897, 902, 8180, 8181 (7 rows)
        expected_ids = {855, 871, 882, 897, 902, 8180, 8181}
        self.assertEqual(set(npc_switch_catalog.NPC_ID_TO_NAME.keys()), expected_ids)

    def test_gm_switch_npc_count_matches_the_committed_table(self):
        self.assertEqual(npc_switch_catalog.GM_SWITCH_NPC_COUNT, 7)

    def test_npc_gm_name_known_id(self):
        self.assertEqual(npc_switch_catalog.npc_gm_name(855), "傑克")

    def test_npc_gm_name_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            npc_switch_catalog.npc_gm_name(1)

    def test_is_gm_switchable_npc(self):
        self.assertTrue(npc_switch_catalog.is_gm_switchable_npc(855))
        self.assertFalse(npc_switch_catalog.is_gm_switchable_npc(1))
        self.assertFalse(npc_switch_catalog.is_gm_switchable_npc(0))

    def test_8180_and_8181_are_distinct_ids_sharing_one_name(self):
        # the source table has two n_ID rows (8180, 8181) both named "水燈" --
        # confirm the catalog keeps them as two separate ids, not collapsed
        self.assertEqual(npc_switch_catalog.npc_gm_name(8180), "水燈")
        self.assertEqual(npc_switch_catalog.npc_gm_name(8181), "水燈")
        self.assertNotEqual(8180, 8181)

    def test_data_file_sha256_matches_pin(self):
        data_path = ROOT / "src" / "pirateforce_foundation" / "gm" / "data" / "gm_npc_switch.tsv"
        actual = hashlib.sha256(data_path.read_bytes()).hexdigest()
        self.assertEqual(actual, npc_switch_catalog.SOURCE_SHA256)


if __name__ == "__main__":
    unittest.main()
