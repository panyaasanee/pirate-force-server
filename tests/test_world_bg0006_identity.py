"""LANE-A: Bg0006's crosswalk, and the controls that make it believable.

Same discipline as ``tests/test_world_bg0004_identity.py``,
``tests/test_world_bg0005_identity.py`` and
``tests/test_world_bg0010_identity.py``, applied to this scene:

* It does not re-derive the table from the client tables.  Those five files
  (plus the scene's own placements TSV) live in the pf_bridge clone, not in
  this repository, so a test here cannot open them; ``SOURCE_SHA256`` is
  recorded provenance for a bridge-side re-mine, and this file says so rather
  than pretending to check it.
* It does not claim any of these actors has been SEEN.  Nobody has been in
  this scene (registry ``status: never_sent_to_any_client_by_this_project``
  as of this module's own construction round).  Everything below is
  wire/DB-layer and table-layer evidence.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg0006_identity as identity  # noqa: E402


class Bg0006TableShape(unittest.TestCase):
    def test_the_scene_is_the_one_the_module_says_it_is(self) -> None:
        self.assertEqual(identity.SCENE_N_ID, 6)
        self.assertEqual(identity.SCENE_MODEL_ID, "Bg0006")
        # A direct SCENE_NAME selector (one of RE-128's 19), not one of its
        # 240 instance scenes.
        self.assertEqual(identity.SCENE_CLINE_TYPE, 6)
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 70)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(len(identity._RESOLVED_ROWS), 38)
        self.assertEqual(len(identity.UNRESOLVED), 14)
        self.assertEqual(identity.PLACEMENT_COUNT, 80)
        self.assertEqual(len(identity.shippable_placements()), 66)
        self.assertEqual(len(identity.unshippable_placements()), 14)

    def test_control_1_scene_sets_and_the_table_keys_are_the_same_52(
        self,
    ) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertEqual(len(table_sets), 52)
        self.assertEqual(scene_sets, table_sets)
        # This scene uses CLINE type 6's entire key range, the same shape
        # bg0005's own crosswalk carries (unlike bg0004's 61-of-62 and
        # bg0010's 40-of-41).
        self.assertTrue({1, 38, 101, 114} <= table_sets)

    def test_control_3_no_row_ships_its_own_set_number(self) -> None:
        self.assertTrue(identity.no_set_number_is_shipped_as_identity())
        for template_id, row in identity.IDENTITIES.items():
            self.assertNotEqual(template_id, row.mobs_n_id)

    def test_every_shipped_row_is_ascii_and_carries_a_body(self) -> None:
        for row in identity.IDENTITIES.values():
            with self.subTest(set=row.template_id):
                self.assertTrue(row.outfit.isascii() and row.outfit)
                self.assertTrue(row.name.isascii() and row.name)
                self.assertTrue(row.title.isascii())
                self.assertNotIn(";", row.outfit)
                self.assertGreaterEqual(row.max_hp, 1)

    def test_every_shipped_row_is_cp874_encodable(self) -> None:
        # The specific control this scene's own crosswalk needed and no
        # sibling did: three resolved-in-MOBS rows (sets 111-113) had to be
        # dropped because their MOBS_TIP.s_NAME is CJK script, which cp874
        # cannot encode. This checks the SHIPPED table never lets one back
        # in.
        for row in identity.IDENTITIES.values():
            with self.subTest(set=row.template_id):
                row.name.encode("cp874")
                row.title.encode("cp874")
                row.outfit.encode("cp874")

    def test_no_invisible_marker_shape_recurs_in_this_scene(self) -> None:
        # Unlike bg0004's set 107 (leader 917, INVISIBLE, empty name), every
        # resolved row here carries a real MOBS_TIP name -- checked, not
        # assumed.
        empty_named = [row.template_id for row in identity.IDENTITIES.values()
                       if not row.name]
        self.assertEqual(empty_named, [])

    def test_the_fourteen_dropped_placements_split_into_three_reasons(
        self,
    ) -> None:
        rows = identity.unshippable_placements()
        self.assertEqual(
            sorted(row["template_id"] for row in rows),
            [1, 101, 102, 103, 104, 105, 106, 107, 108, 109, 111, 112, 113,
             114])
        for row in rows:
            with self.subTest(placement=row["placement_index"]):
                self.assertTrue(row["reason"])
                self.assertTrue(row["reason"].isascii())
        by_template = {row["template_id"]: row for row in rows}
        # Sets 1 and 114: CLINE carries a real leader but MOBS has no row
        # for it at all -- two occurrences of the failure mode bg0005's set
        # 1 needed only once.
        for template_id in (1, 114):
            self.assertIn("no row", by_template[template_id]["reason"])
            self.assertGreater(by_template[template_id]["leader_n_id"], 0)
        for template_id in (101, 102, 103, 104, 105, 106, 107, 108, 109):
            self.assertIn("no s_OUTFIT", by_template[template_id]["reason"])
            self.assertGreater(by_template[template_id]["leader_n_id"], 0)
        # Sets 111-113: the new failure mode this scene needed, a
        # non-ASCII MOBS_TIP name cp874 cannot ship -- not "no row" and not
        # "no s_OUTFIT", a third distinct reason string.
        for template_id in (111, 112, 113):
            self.assertIn("non-ASCII", by_template[template_id]["reason"])
            self.assertGreater(by_template[template_id]["leader_n_id"], 0)

    def test_no_extraction_unresolved_sentinel_in_this_scene(self) -> None:
        # No row's template_ids column is the literal UNRESOLVED, and no
        # placement carries a sentinel -1 template id.
        sentinel_rows = [row for row in identity._PLACEMENT_ROWS
                          if row[1] == -1]
        self.assertEqual(sentinel_rows, [])

    def test_identity_for_never_substitutes(self) -> None:
        for template_id in identity.UNRESOLVED:
            self.assertIsNone(identity.identity_for(template_id))
        self.assertEqual(identity.identity_for(2).name, "Columbus")
        self.assertEqual(identity.identity_for(2).mobs_n_id, 196)
        # Every value carries its own CLINE row locator, so a second party
        # can open CONSTDATA_TH__CLINE.tsv at that row and check the
        # pairing this module claims.
        self.assertEqual(identity.identity_for(2).cline_row_id, 2001)
        for row in identity.IDENTITIES.values():
            self.assertGreater(row.cline_row_id, 0)

    def test_multi_variant_outfits_ship_their_first_variant(self) -> None:
        self.assertEqual(len(identity.MULTI_VARIANT_OUTFITS), 10)
        by_n_id = {row.mobs_n_id: row for row in identity.IDENTITIES.values()}
        for n_id, whole in identity.MULTI_VARIANT_OUTFITS.items():
            with self.subTest(n_id=n_id):
                self.assertIn(";", whole)
                self.assertEqual(by_n_id[n_id].outfit, whole.split(";")[0])
        affected = [p for p in identity.shippable_placements()
                    if p.n_id in identity.MULTI_VARIANT_OUTFITS]
        # Measured, not estimated: 36 of 66 shippable placements.
        self.assertEqual(len(affected), 36)

    def test_no_name_column_disagreement_in_this_scene(self) -> None:
        for index, template_id, _mm, _x, _y, _z in identity._PLACEMENT_ROWS:
            self.assertIsInstance(template_id, int)
            self.assertGreater(template_id, 0)

    def test_actor_identities_are_unique_across_the_roster(self) -> None:
        ids = [p.actor_identity for p in identity.shippable_placements()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_self_check_refuses_a_drifted_table(self) -> None:
        original = identity._RESOLVED_ROWS
        try:
            identity._RESOLVED_ROWS = original[:-1]
            with self.assertRaises(identity.Bg0006IdentityError):
                identity._self_check()
        finally:
            identity._RESOLVED_ROWS = original
        identity._self_check()

    def test_no_lane_b_hostile_roster_module_exists_for_this_scene_yet(
        self,
    ) -> None:
        hits = list(
            (ROOT / "src" / "pirateforce_foundation").glob(
                "field_mob_tables_bg0006*"))
        self.assertEqual(hits, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
