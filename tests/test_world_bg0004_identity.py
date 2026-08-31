"""LANE-A: Bg0004's crosswalk, and the controls that make it believable.

Same discipline as ``tests/test_world_bg0015_identity.py``, applied to this
scene:

* It does not re-derive the table from the client tables.  Those five files
  (plus the scene's own placements TSV) live in the pf_bridge clone, not in
  this repository, so a test here cannot open them; ``SOURCE_SHA256`` is
  recorded provenance for a bridge-side re-mine, and this file says so rather
  than pretending to check it.
* It does not claim any of these actors has been SEEN.  Nobody has been in
  this scene (registry ``status: never_sent_to_any_client_by_this_project``).
  Everything below is wire/DB-layer and table-layer evidence.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg0004_identity as identity  # noqa: E402


class Bg0004TableShape(unittest.TestCase):
    def test_the_scene_is_the_one_the_module_says_it_is(self) -> None:
        self.assertEqual(identity.SCENE_N_ID, 4)
        self.assertEqual(identity.SCENE_MODEL_ID, "BG0004")
        # A direct SCENE_NAME selector (one of RE-128's 19), not one of its
        # 240 instance scenes.
        self.assertEqual(identity.SCENE_CLINE_TYPE, 4)
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 45)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(len(identity._RESOLVED_ROWS), 48)
        self.assertEqual(len(identity.UNRESOLVED), 7)
        self.assertEqual(identity.PLACEMENT_COUNT, 116)
        self.assertEqual(len(identity.shippable_placements()), 109)
        self.assertEqual(len(identity.unshippable_placements()), 7)

    def test_control_1_scene_sets_and_the_table_keys_are_the_same_55(
        self,
    ) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertEqual(len(table_sets), 55)
        self.assertEqual(scene_sets, table_sets)
        # The 101..108 half really is there, and 109..114 (unused by any
        # placement) are NOT in this table on purpose: a literal 1..N key
        # block could not have produced the 101..108 tail.
        self.assertTrue({101, 108} <= table_sets)
        self.assertFalse({109, 110, 111, 112, 113, 114} & table_sets)

    def test_control_3_no_row_ships_its_own_set_number(self) -> None:
        self.assertTrue(identity.no_set_number_is_shipped_as_identity())
        for template_id, row in identity.IDENTITIES.items():
            self.assertNotEqual(template_id, row.mobs_n_id)

    def test_every_shipped_row_is_ascii_and_carries_a_body(self) -> None:
        for row in identity.IDENTITIES.values():
            with self.subTest(set=row.template_id):
                self.assertTrue(row.outfit.isascii() and row.outfit)
                self.assertTrue(row.name.isascii())
                self.assertTrue(row.title.isascii())
                self.assertNotIn(";", row.outfit)
                self.assertGreaterEqual(row.max_hp, 1)

    def test_only_set_107_ships_with_an_empty_name(self) -> None:
        # The one row that ships with no name plate, and the reason (leader
        # 917, INVISIBLE outfit, no MOBS_TIP row) is the exact shape
        # world_port_royal_identity already ships for the same leader id.
        empty_named = [row.template_id for row in identity.IDENTITIES.values()
                       if not row.name]
        self.assertEqual(empty_named, [107])
        self.assertEqual(identity.IDENTITIES[107].mobs_n_id, 917)
        self.assertEqual(identity.IDENTITIES[107].outfit, "INVISIBLE")

    def test_set_107_accounts_for_25_of_the_109_shippable_placements(
        self,
    ) -> None:
        placements = [p for p in identity.shippable_placements()
                      if p.template_id == 107]
        self.assertEqual(len(placements), 25)

    def test_the_seven_dropped_placements_each_name_a_reason(self) -> None:
        rows = identity.unshippable_placements()
        self.assertEqual(
            sorted(row["template_id"] for row in rows),
            [1, 101, 102, 103, 104, 105, 106])
        for row in rows:
            with self.subTest(placement=row["placement_index"]):
                self.assertTrue(row["reason"])
                self.assertTrue(row["reason"].isascii())
        # Set 1's leader (66, "Port transportation") is a real MOBS_TIP name
        # with no MOBS row at all -- a different reason from the other six,
        # which HAVE a MOBS row but no s_OUTFIT.
        by_template = {row["template_id"]: row for row in rows}
        self.assertIn("no CONSTDATA MOBS row", by_template[1]["reason"])
        self.assertEqual(by_template[1]["leader_n_id"], 66)
        for template_id in (101, 102, 103, 104, 105, 106):
            self.assertIn("no s_OUTFIT", by_template[template_id]["reason"])
            self.assertGreater(by_template[template_id]["leader_n_id"], 0)

    def test_identity_for_never_substitutes(self) -> None:
        for template_id in identity.UNRESOLVED:
            self.assertIsNone(identity.identity_for(template_id))
        self.assertEqual(identity.identity_for(38).name, "Orc Chief")
        self.assertEqual(identity.identity_for(38).mobs_n_id, 103)
        # Every value carries its own CLINE row locator, so a second party
        # can open CONSTDATA_TH__CLINE.tsv at that row and check the pairing
        # this module claims.
        self.assertEqual(identity.identity_for(38).cline_row_id, 1637)
        for row in identity.IDENTITIES.values():
            self.assertGreater(row.cline_row_id, 0)

    def test_multi_variant_outfits_ship_their_first_variant(self) -> None:
        self.assertEqual(len(identity.MULTI_VARIANT_OUTFITS), 9)
        by_n_id = {row.mobs_n_id: row for row in identity.IDENTITIES.values()}
        for n_id, whole in identity.MULTI_VARIANT_OUTFITS.items():
            with self.subTest(n_id=n_id):
                self.assertIn(";", whole)
                self.assertEqual(by_n_id[n_id].outfit, whole.split(";")[0])
        affected = [p for p in identity.shippable_placements()
                    if p.n_id in identity.MULTI_VARIANT_OUTFITS]
        # Measured, not estimated: template 30 alone recurs 9 times (the
        # "Dragon Gladiator" family), so this is nearly 40% of the 109
        # shippable placements, bigger than a corner case.
        self.assertEqual(len(affected), 44)

    def test_the_two_anomalous_placements_follow_template_ids_not_the_name_column(
        self,
    ) -> None:
        # Placements 82/83's free-text name column says "Mob_Set_34 08/09"
        # but the machine-parsed template column says 45/46 -- this module
        # follows the machine-parsed column.  See the module docstring.
        placements = {p.placement_index: p
                      for p in identity.shippable_placements()}
        self.assertEqual(placements[82].template_id, 45)
        self.assertEqual(placements[82].display_name, "Jet cat thieves No.3")
        self.assertEqual(placements[83].template_id, 46)
        self.assertEqual(placements[83].display_name, "Jet cat thieves No.4")
        # Neither is Mob-Set 34 ("Moor Slime"), which the name column implies.
        self.assertNotEqual(placements[82].n_id, identity.IDENTITIES[34].mobs_n_id)
        self.assertNotEqual(placements[83].n_id, identity.IDENTITIES[34].mobs_n_id)

    def test_the_extra_triple_is_named_and_not_shipped(self) -> None:
        index, template_id, _x, _y, _z, distance = identity.EXTRA_TRIPLE_NOT_SHIPPED
        self.assertEqual(index, 83)
        self.assertEqual(template_id, 46)
        self.assertGreater(distance, 0)
        shipped_count = sum(
            1 for p in identity.shippable_placements()
            if p.placement_index == index)
        # Exactly one actor ships for placement 83 -- the primary point, not
        # a second one from the extra triple.
        self.assertEqual(shipped_count, 1)

    def test_actor_identities_are_unique_across_the_roster(self) -> None:
        ids = [p.actor_identity for p in identity.shippable_placements()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_self_check_refuses_a_drifted_table(self) -> None:
        original = identity._RESOLVED_ROWS
        try:
            identity._RESOLVED_ROWS = original[:-1]
            with self.assertRaises(identity.Bg0004IdentityError):
                identity._self_check()
        finally:
            identity._RESOLVED_ROWS = original
        identity._self_check()

    def test_no_lane_b_hostile_roster_module_exists_for_this_scene_yet(
        self,
    ) -> None:
        # Unlike Bg0015 (which collides with a committed field_mob_tables_
        # bg0015.py for the same scene), no such sibling exists here yet: a
        # 0-hit glob this round, re-checked here so a future addition is
        # something a red test notices instead of a silent
        # actor_identity == 0x2000 + index + 1 collision (the shape
        # world_bg0015_identity.COLLIDING_PLACEMENTS documents for scene 14).
        hits = list(
            (ROOT / "src" / "pirateforce_foundation").glob(
                "field_mob_tables_bg0004*"))
        self.assertEqual(hits, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
