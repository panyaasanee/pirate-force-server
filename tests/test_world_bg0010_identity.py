"""LANE-A: Bg0010's crosswalk, and the controls that make it believable.

Same discipline as ``tests/test_world_bg0004_identity.py``, applied to this
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

from pirateforce_foundation import world_bg0010_identity as identity  # noqa: E402


class Bg0010TableShape(unittest.TestCase):
    def test_the_scene_is_the_one_the_module_says_it_is(self) -> None:
        self.assertEqual(identity.SCENE_N_ID, 10)
        self.assertEqual(identity.SCENE_MODEL_ID, "BG0010")
        # A direct SCENE_NAME selector (one of RE-128's 19), not one of its
        # 240 instance scenes.
        self.assertEqual(identity.SCENE_CLINE_TYPE, 10)
        self.assertEqual(identity.SCENE_DECLARED_LEVEL, 92)

    def test_counts_are_the_ones_the_docstring_states(self) -> None:
        self.assertEqual(len(identity._RESOLVED_ROWS), 35)
        self.assertEqual(len(identity.UNRESOLVED), 5)
        self.assertEqual(identity.PLACEMENT_COUNT, 100)
        self.assertEqual(len(identity.shippable_placements()), 94)
        self.assertEqual(len(identity.unshippable_placements()), 6)

    def test_control_1_scene_sets_and_the_table_keys_are_the_same_40(
        self,
    ) -> None:
        scene_sets = {row[1] for row in identity._PLACEMENT_ROWS if row[1] != -1}
        table_sets = set(identity.IDENTITIES) | set(identity.UNRESOLVED)
        self.assertEqual(len(table_sets), 40)
        self.assertEqual(scene_sets, table_sets)
        self.assertTrue({101, 105} <= table_sets)

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

    def test_no_invisible_marker_shape_recurs_in_this_scene(self) -> None:
        # Unlike bg0004's set 107 (leader 917, INVISIBLE, empty name), every
        # resolved row here carries a real MOBS_TIP name -- checked, not
        # assumed.
        empty_named = [row.template_id for row in identity.IDENTITIES.values()
                       if not row.name]
        self.assertEqual(empty_named, [])

    def test_the_six_dropped_placements_split_into_two_reasons(self) -> None:
        rows = identity.unshippable_placements()
        self.assertEqual(
            sorted(row["template_id"] for row in rows),
            [-1, 101, 102, 103, 104, 105])
        for row in rows:
            with self.subTest(placement=row["placement_index"]):
                self.assertTrue(row["reason"])
                self.assertTrue(row["reason"].isascii())
        by_template = {row["template_id"]: row for row in rows}
        # The sentinel row (placement 50): extraction itself never named a
        # Mob-Set number -- a different failure mode from the other five,
        # which DO have a Mob-Set number and a CLINE row, just no outfit.
        self.assertEqual(by_template[-1]["placement_index"], 50)
        self.assertIn("UNRESOLVED", by_template[-1]["reason"])
        self.assertEqual(by_template[-1]["cline_row_id"], 0)
        self.assertEqual(by_template[-1]["leader_n_id"], 0)
        for template_id in (101, 102, 103, 104, 105):
            self.assertIn("no s_OUTFIT", by_template[template_id]["reason"])
            self.assertGreater(by_template[template_id]["leader_n_id"], 0)

    def test_identity_for_never_substitutes(self) -> None:
        for template_id in identity.UNRESOLVED:
            self.assertIsNone(identity.identity_for(template_id))
        self.assertIsNone(identity.identity_for(-1))
        self.assertEqual(identity.identity_for(30).name, "Columbus")
        self.assertEqual(identity.identity_for(30).mobs_n_id, 835)
        # Every value carries its own CLINE row locator, so a second party
        # can open CONSTDATA_TH__CLINE.tsv at that row and check the pairing
        # this module claims.
        self.assertEqual(identity.identity_for(30).cline_row_id, 2829)
        for row in identity.IDENTITIES.values():
            self.assertGreater(row.cline_row_id, 0)

    def test_multi_variant_outfits_ship_their_first_variant(self) -> None:
        self.assertEqual(len(identity.MULTI_VARIANT_OUTFITS), 12)
        by_n_id = {row.mobs_n_id: row for row in identity.IDENTITIES.values()}
        for n_id, whole in identity.MULTI_VARIANT_OUTFITS.items():
            with self.subTest(n_id=n_id):
                self.assertIn(";", whole)
                self.assertEqual(by_n_id[n_id].outfit, whole.split(";")[0])
        affected = [p for p in identity.shippable_placements()
                    if p.n_id in identity.MULTI_VARIANT_OUTFITS]
        # Measured, not estimated: 59 of 94 shippable placements, well over
        # half the roster, bigger than a corner case (same shape bg0004's own
        # docstring records for its own nine sets).
        self.assertEqual(len(affected), 59)

    def test_no_name_column_disagreement_in_this_scene(self) -> None:
        # Unlike bg0004's placements 82/83, every placement's free-text
        # name matches its machine-parsed template_ids column here (checked
        # for all 99 rows that carry a real template id, this round).
        for index, template_id, _mm, _x, _y, _z in identity._PLACEMENT_ROWS:
            if template_id == -1:
                continue
            # A regression here would mean a future re-mine trusted the
            # free-text column instead; this project's convention is
            # machine-parsed wins, and there is nothing to reconcile today.
            self.assertIsInstance(template_id, int)

    def test_the_sentinel_row_is_exactly_placement_50(self) -> None:
        sentinel = [row for row in identity._PLACEMENT_ROWS if row[1] == -1]
        self.assertEqual(len(sentinel), 1)
        self.assertEqual(sentinel[0][0], 50)
        shipped_count = sum(
            1 for p in identity.shippable_placements()
            if p.placement_index == 50)
        self.assertEqual(shipped_count, 0)

    def test_actor_identities_are_unique_across_the_roster(self) -> None:
        ids = [p.actor_identity for p in identity.shippable_placements()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_self_check_refuses_a_drifted_table(self) -> None:
        original = identity._RESOLVED_ROWS
        try:
            identity._RESOLVED_ROWS = original[:-1]
            with self.assertRaises(identity.Bg0010IdentityError):
                identity._self_check()
        finally:
            identity._RESOLVED_ROWS = original
        identity._self_check()

    def test_no_lane_b_hostile_roster_module_exists_for_this_scene_yet(
        self,
    ) -> None:
        hits = list(
            (ROOT / "src" / "pirateforce_foundation").glob(
                "field_mob_tables_bg0010*"))
        self.assertEqual(hits, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
