"""LANE-A: Bg0011's crosswalk, and the controls that make it believable.

Same discipline as ``tests/test_world_bg0003_identity.py``,
``tests/test_world_bg0004_identity.py``, ``tests/test_world_bg0005_identity.py``,
``tests/test_world_bg0006_identity.py``, ``tests/test_world_bg0007_identity.py``,
``tests/test_world_bg0008_identity.py``, ``tests/test_world_bg0009_identity.py``
and ``tests/test_world_bg0010_identity.py``, applied to this scene:

* It does not re-derive the table from the client tables.  Those five files
  (plus the scene's own placements TSV) live in the pf_bridge clone, not in
  this repository, so a test here cannot open them; ``SOURCE_SHA256`` is
  recorded provenance for a bridge-side re-mine, and this file says so rather
  than pretending to check it.
* It does not claim any of these actors has been SEEN.  Nobody has been in
  this scene (registry ``status`` records it opened this round with no
  attended visit yet).  Everything below is wire/DB-layer and table-layer
  evidence.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg0011_identity as identity  # noqa: E402


class Bg0011TableShape(unittest.TestCase):
    def test_the_scene_is_the_one_the_module_says_it_is(self) -> None:
        self.assertEqual(identity.SCENE_N_ID, 11)
        self.assertEqual(identity.SCENE_MODEL_ID, "Bg0011")
        # A direct SCENE_NAME selector (one of RE-128's 19), not one of its
        # 240 instance scenes.
        self.assertEqual(identity.SCENE_CLINE_TYPE, 11)
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 95)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(len(identity._RESOLVED_ROWS), 26)
        self.assertEqual(len(identity.UNRESOLVED), 5)
        self.assertEqual(identity.PLACEMENT_COUNT, 56)
        self.assertEqual(len(identity.shippable_placements()), 51)
        self.assertEqual(len(identity.unshippable_placements()), 5)

    def test_control_1_scene_sets_and_the_table_keys_are_the_same_31(
        self,
    ) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertEqual(len(table_sets), 31)
        self.assertEqual(scene_sets, table_sets)
        # This scene uses a SUBSET of CLINE type 11's own 32-row key range
        # (31 of 32), the same "subset, not exact" shape bg0004's 55-of-61,
        # bg0009's 44-of-48 and bg0010's 40-of-41 own crosswalks carry
        # (unlike scenes 5's, 6's, 7's and 8's own EXACT-match crosswalks).
        # See the module docstring for the one CLINE key (106) this scene
        # never touches - it carries a real leader anyway.
        self.assertTrue({1, 26, 101, 105} <= table_sets)
        self.assertFalse({106} & table_sets)

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
        # This scene needed no CJK-name drop among the 26 SHIPPED rows
        # (the one CJK name this round found, on MOBS row 9061, belongs to
        # the untouched CLINE key 106 and never reaches a placement) - the
        # check is still run rather than assumed from that absence.
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

    def test_the_five_dropped_placements_are_one_failure_shape(
        self,
    ) -> None:
        rows = identity.unshippable_placements()
        self.assertEqual(
            sorted(row["template_id"] for row in rows),
            [101, 102, 103, 104, 105])
        for row in rows:
            with self.subTest(placement=row["placement_index"]):
                self.assertTrue(row["reason"])
                self.assertTrue(row["reason"].isascii())
                self.assertIn("no s_OUTFIT", row["reason"])
                self.assertGreater(row["leader_n_id"], 0)
        # Unlike bg0009's two distinct failure shapes (a "MOBS has no row
        # at all" set plus five "no s_OUTFIT" sets), this scene needed only
        # the one shape - every Mob-Set number 1-26 this scene's placements
        # use resolves to a real CONSTDATA MOBS row.
        by_template = {row["template_id"]: row for row in rows}
        self.assertEqual(len(by_template), 5)

    def test_no_extraction_unresolved_sentinel_in_this_scene(self) -> None:
        # No row's template_ids column is the literal UNRESOLVED, and no
        # placement carries a sentinel -1 template id.
        sentinel_rows = [row for row in identity._PLACEMENT_ROWS
                          if row[1] == -1]
        self.assertEqual(sentinel_rows, [])

    def test_identity_for_never_substitutes(self) -> None:
        for template_id in identity.UNRESOLVED:
            self.assertIsNone(identity.identity_for(template_id))
        self.assertEqual(identity.identity_for(1).name, "Balas")
        self.assertEqual(identity.identity_for(1).mobs_n_id, 675)
        # Every value carries its own CLINE row locator, so a second party
        # can open CONSTDATA_TH__CLINE.tsv at that row and check the
        # pairing this module claims.
        self.assertEqual(identity.identity_for(1).cline_row_id, 3000)
        for row in identity.IDENTITIES.values():
            self.assertGreater(row.cline_row_id, 0)

    def test_multi_variant_outfits_ship_their_first_variant(self) -> None:
        self.assertEqual(len(identity.MULTI_VARIANT_OUTFITS), 7)
        by_n_id = {row.mobs_n_id: row for row in identity.IDENTITIES.values()}
        for n_id, whole in identity.MULTI_VARIANT_OUTFITS.items():
            with self.subTest(n_id=n_id):
                self.assertIn(";", whole)
                self.assertEqual(by_n_id[n_id].outfit, whole.split(";")[0])
        affected = [p for p in identity.shippable_placements()
                    if p.n_id in identity.MULTI_VARIANT_OUTFITS]
        # Measured, not estimated: 27 of 51 shippable placements.
        self.assertEqual(len(affected), 27)
        # UNLIKE bg0003's nine-variant outlier, every one of this scene's
        # seven multi-variant sets lists exactly two variants.
        for whole in identity.MULTI_VARIANT_OUTFITS.values():
            self.assertEqual(whole.count(";"), 1)

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
            with self.assertRaises(identity.Bg0011IdentityError):
                identity._self_check()
        finally:
            identity._RESOLVED_ROWS = original
        identity._self_check()

    def test_no_lane_b_hostile_roster_module_exists_for_this_scene_yet(
        self,
    ) -> None:
        hits = list(
            (ROOT / "src" / "pirateforce_foundation").glob(
                "field_mob_tables_bg0011*"))
        self.assertEqual(hits, [])

    def test_the_untouched_cline_key_would_have_failed_to_resolve_anyway(
        self,
    ) -> None:
        # Measured this round, not assumed: CLINE type 11's own key 106
        # carries a real, non-zero leader (9061) that no placement in this
        # scene points at, and that leader's own MOBS row would have been
        # dropped on TWO axes even if a placement had used it (empty
        # s_OUTFIT and a non-cp874 CJK name) - see the module docstring.
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertNotIn(106, table_sets)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
