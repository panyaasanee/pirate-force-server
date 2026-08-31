"""LANE-A BUILD-002 door 1: Bg0004's crosswalk, and the controls under it.

Mirrors ``test_world_bg0015_identity.py``'s split: this file does not
re-derive the table from the client's own tables (they live in the pf_bridge
clone, not here -- ``SOURCE_SHA256`` is recorded provenance for a bridge-side
re-mine) and it does not claim any of these 84 actors has been SEEN.  Nobody
has stood in this scene.  Everything below is wire/DB-layer and table-layer
evidence.
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
        # A direct SCENE_NAME selector (read straight off the table, not
        # inferred by key-set matching the way an INSTANCE-branch scene
        # would need) -- the whole reason this door could be built without
        # any RE work first.
        self.assertEqual(identity.SCENE_CLINE_TYPE, 4)
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 45)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(len(identity._RESOLVED_ROWS), 47)
        self.assertEqual(len(identity.UNRESOLVED), 14)
        self.assertEqual(identity.PLACEMENT_COUNT, 116)
        self.assertEqual(len(identity.shippable_placements()), 84)
        self.assertEqual(len(identity.unshippable_placements()), 32)

    def test_every_placement_mobset_number_is_covered_by_cline_type_4(
        self,
    ) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        # A SUBSET, not an exact match (six CLINE keys -- 109..114 -- are
        # never placed in this scene) -- the docstring's "SUBSET CHECK",
        # asserted rather than described.
        self.assertTrue(scene_sets.issubset(table_sets))
        self.assertEqual(table_sets - scene_sets, {109, 110, 111, 112, 113, 114})
        self.assertEqual(len(scene_sets), 55)
        self.assertEqual(len(table_sets), 61)

    def test_control_3_no_row_ships_its_own_set_number(self) -> None:
        self.assertTrue(identity.no_set_number_is_shipped_as_identity())
        for mobset_key, row in identity.IDENTITIES.items():
            self.assertNotEqual(mobset_key, row.mobs_n_id)

    def test_every_shipped_row_is_ascii_and_carries_a_body(self) -> None:
        for row in identity.IDENTITIES.values():
            with self.subTest(set=row.mobset_key):
                self.assertTrue(row.outfit.isascii() and row.outfit)
                self.assertTrue(row.name.isascii() and row.name)
                self.assertNotIn(";", row.outfit)
                self.assertGreaterEqual(row.max_hp, 1)

    def test_the_thirtytwo_dropped_placements_each_name_a_reason(self) -> None:
        rows = identity.unshippable_placements()
        self.assertEqual(len(rows), 32)
        # Set 107 alone costs 25 of the 32 -- the dense unresolved cluster
        # the docstring names.
        self.assertEqual(
            sum(1 for row in rows if row["mobset_key"] == 107), 25)
        for row in rows:
            with self.subTest(placement=row["placement_index"]):
                self.assertTrue(row["reason"])
                self.assertTrue(row["reason"].isascii())
                self.assertGreaterEqual(row["leader_n_id"], 0)

    def test_identity_for_never_substitutes(self) -> None:
        for mobset_key in identity.UNRESOLVED:
            self.assertIsNone(identity.identity_for(mobset_key))
        self.assertEqual(identity.identity_for(38).name, "Orc Chief ")
        self.assertEqual(identity.identity_for(38).mobs_n_id, 103)
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

    def test_the_two_name_template_id_disagreements_ship_the_template_id(
        self,
    ) -> None:
        # Placements 82/83 name "Mob_Set_34" but their template_ids column
        # (the authoritative field) says 45/46 -- both ship under 45/46.
        self.assertEqual(
            identity.NAME_TEMPLATE_ID_DISAGREEMENT, {82: (34, 45), 83: (34, 46)})
        by_index = {p.placement_index: p for p in identity.shippable_placements()}
        self.assertEqual(by_index[82].mobset_key, 45)
        self.assertEqual(by_index[83].mobset_key, 46)
        self.assertNotEqual(by_index[82].mobset_key, 34)

    def test_the_trailing_space_name_ships_verbatim(self) -> None:
        # A real byte in the source data, not a parsing artifact -- see the
        # module docstring.  Not stripped: CHARTER-02 forbids an invented
        # transform nobody has checked against the client.
        self.assertEqual(identity.IDENTITIES[38].name, "Orc Chief ")
        self.assertTrue(identity.IDENTITIES[38].name.endswith(" "))

    def test_the_map_prop_rows_are_recorded_rather_than_quietly_shipped(
        self,
    ) -> None:
        self.assertEqual(sorted(identity.MAP_PROP_LEADERS), [234, 235, 236])
        shipped = {p.n_id for p in identity.shippable_placements()}
        for leader in identity.MAP_PROP_LEADERS:
            self.assertIn(leader, shipped)

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

    def test_subset_candidate_types_include_two_broad_blocks(self) -> None:
        # Recorded so a reader does not mistake the subset check for a
        # uniqueness proof: types 1 and 9998 are broad enough to also
        # contain this scene's 55 keys.  The type-4 claim itself rests on
        # the direct SCENE_NAME column read, not on this check.
        self.assertEqual(identity.SUBSET_CANDIDATE_CLINE_TYPES, (1, 4, 9998))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
