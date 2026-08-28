"""LANE-A M1-P: the Bg0002 (Prison Exile Island) placement roster.

The load-bearing tests here are the shape checks (97 known + 9 unresolved =
106, no placement index used twice) and the anchor checks - this table backs
a "strong hypothesis, not yet fact" per PANYA-DECISION 2026-08-27 20:10, and
these tests are what keeps that qualifier honest: if a future edit ever makes
the Veronica or Legend-Jack-cluster anchor stop matching, this is where that
shows up loudly instead of silently in a stale docstring claim.
"""

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import scene2_prison_exile_tables as tables


class KnownPlacementsShapeTests(unittest.TestCase):
    def test_the_counts_add_up_to_every_row_in_the_source_file(self):
        self.assertEqual(len(tables.KNOWN_PLACEMENTS), tables.KNOWN_COUNT)
        self.assertEqual(len(tables.UNRESOLVED_PLACEMENTS), tables.UNRESOLVED_COUNT)
        self.assertEqual(
            tables.KNOWN_COUNT + tables.UNRESOLVED_COUNT,
            tables.TOTAL_PLACEMENT_COUNT,
        )
        self.assertEqual(tables.KNOWN_COUNT, 97)
        self.assertEqual(tables.UNRESOLVED_COUNT, 9)
        self.assertEqual(tables.TOTAL_PLACEMENT_COUNT, 106)

    def test_every_placement_index_is_used_exactly_once(self):
        known = [row[0] for row in tables.KNOWN_PLACEMENTS]
        unresolved = [row[0] for row in tables.UNRESOLVED_PLACEMENTS]
        combined = known + unresolved
        self.assertEqual(len(combined), len(set(combined)))
        self.assertEqual(sorted(combined), list(range(tables.TOTAL_PLACEMENT_COUNT)))

    def test_loading_returns_typed_rows_that_match_the_raw_tuples(self):
        placements = tables.load_known_placements()
        self.assertEqual(len(placements), tables.KNOWN_COUNT)
        by_index = {p.placement_index: p for p in placements}
        self.assertEqual(by_index[0].n_id, 1)
        self.assertEqual(by_index[0].display_name, "Navy Transfer")
        self.assertEqual(by_index[18].n_id, 14)
        self.assertEqual(by_index[18].display_name, "Veronica")
        self.assertEqual(by_index[18].title, "Apprentice Witch")

    def test_no_known_row_has_an_empty_name_or_preset(self):
        for placement in tables.load_known_placements():
            self.assertTrue(placement.display_name)
            self.assertTrue(placement.visual_preset)

    def test_the_unknown_101_104_block_is_recorded_not_placed(self):
        unresolved = tables.load_unresolved_placements()
        block = [u for u in unresolved if 101 <= u.n_id <= 104]
        self.assertEqual(len(block), 8)
        for u in block:
            self.assertEqual(
                u.reason, "n_id_101_104_block_meaning_unknown_owner_says_do_not_place"
            )

    def test_n_id_37_has_no_mobs_row_and_is_unresolved_not_guessed(self):
        unresolved = {u.n_id: u for u in tables.load_unresolved_placements()}
        self.assertIn(37, unresolved)
        self.assertEqual(unresolved[37].reason, "no_mobs_row_for_this_n_id_no_body_data")
        known_n_ids = {p.n_id for p in tables.load_known_placements()}
        self.assertNotIn(37, known_n_ids)

    def test_ascii_only(self):
        for placement in tables.load_known_placements():
            self.assertTrue(placement.display_name.isascii())
            self.assertTrue(placement.title.isascii())
            self.assertTrue(placement.visual_preset.isascii())


class AnchorReportTests(unittest.TestCase):
    def test_the_veronica_anchor_matches_under_the_identity_transform(self):
        report = tables.anchor_report()
        veronica = report["confirmed_numeric"][0]
        self.assertEqual(veronica["name"], "veronica_hud")
        self.assertTrue(veronica["match"])
        # The letter's own reported miss is 227/103; this re-derivation lands
        # within a few units of that, not merely "under the tolerance".
        self.assertLess(veronica["distance"], 260.0)
        # CORRECTED round 5irwkp: the target is negative (HUD read "X:-3,825"
        # under higher zoom, not "X:3,825") - see module docstring CORRECTION.
        self.assertEqual(veronica["target"], [-3825.0, 12447.0])

    def test_the_legend_jack_men_deer_cluster_stays_within_the_pinned_radius(self):
        report = tables.anchor_report()
        cluster = report["confirmed_numeric"][1]
        self.assertEqual(cluster["name"], "legend_jack_men_deer_cluster")
        self.assertTrue(cluster["match"])
        self.assertEqual(len(cluster["pairwise_distances"]), 6)

    def test_the_report_never_claims_all_seven_anchors_confirmed(self):
        report = tables.anchor_report()
        self.assertFalse(report["all_seven_confirmed"])
        self.assertEqual(len(report["not_independently_verified"]), 1)

    def test_the_hud_transform_is_identity_no_sign_flip(self):
        # CORRECTED round 5irwkp: was (-100.0, 200.0) under the old
        # (wrong) "negate X" rule.  See hud_from_placement's docstring.
        self.assertEqual(tables.hud_from_placement(100.0, 200.0), (100.0, 200.0))
        self.assertEqual(tables.hud_from_placement(-100.0, 200.0), (-100.0, 200.0))

    def test_navy_transfer_and_sebastian_are_supportive_same_frame_evidence(self):
        report = tables.anchor_report()
        names = [e["name"] for e in report["supportive_not_tight"]]
        self.assertIn("navy_transfer_near_sebastian_same_frame", names)
        entry = next(
            e for e in report["supportive_not_tight"]
            if e["name"] == "navy_transfer_near_sebastian_same_frame"
        )
        self.assertTrue(entry["match"])
        self.assertAlmostEqual(entry["distance"], 3079.9, places=1)

    def test_sebastian_and_pike_name_title_match_the_photos(self):
        report = tables.anchor_report()
        by_n_id = {e["n_id"]: e for e in report["name_title_confirmed_no_coordinate"]}
        self.assertEqual(len(by_n_id), 2)
        self.assertIn(tables.SEBASTIAN_N_ID, by_n_id)
        self.assertIn(tables.PIKE_N_ID, by_n_id)
        for entry in by_n_id.values():
            self.assertTrue(entry["match"])
            self.assertEqual(entry["table_name"], entry["observed_name"])
            self.assertEqual(entry["table_title"], entry["observed_title"])
        self.assertEqual(by_n_id[tables.SEBASTIAN_N_ID]["observed_name"], "Sebastian")
        self.assertEqual(by_n_id[tables.SEBASTIAN_N_ID]["observed_title"], "Warden")
        self.assertEqual(by_n_id[tables.PIKE_N_ID]["observed_name"], "Pike")
        self.assertEqual(
            by_n_id[tables.PIKE_N_ID]["observed_title"], "Unemployed Sailor"
        )

    def test_the_registry_spawn_constant_matches_the_live_registry_file(self):
        # This module hardcodes the scene-2 spawn rather than importing
        # world_scene_travel (kept a pure data module) - this test is the
        # guard against the two drifting apart in silence.
        registry_path = (
            ROOT / "scenarios" / "world_scene_registry_001.json"
        )
        data = json.loads(registry_path.read_text(encoding="ascii"))
        scene2 = next(d for d in data["destinations"] if d["n_id"] == 2)
        self.assertEqual(scene2["spawn"]["x"], tables.SCENE2_REGISTRY_SPAWN_X)
        self.assertEqual(scene2["spawn"]["y"], tables.SCENE2_REGISTRY_SPAWN_Y)


class SourceDigestTests(unittest.TestCase):
    def test_the_pinned_digests_match_the_bridge_tables_field_mob_tables_already_trusts(self):
        # field_mob_tables.py (lane B, bg0001) already pins the SAME three
        # gamedata tables (mobs/standard_mob/mobs_tip) by digest.  If they
        # ever drift, that module's own test catches it too; this test only
        # confirms this module copied the same value, not a fresh check of
        # the bridge clone (which this repo does not contain).
        from pirateforce_foundation import field_mob_tables
        self.assertEqual(
            tables.SOURCE_DIGESTS["mobs"], field_mob_tables.SOURCE_DIGESTS["mobs"]
        )
        self.assertEqual(
            tables.SOURCE_DIGESTS["standard_mob"],
            field_mob_tables.SOURCE_DIGESTS["standard_mob"],
        )
        self.assertEqual(
            tables.SOURCE_DIGESTS["mobs_tip"],
            field_mob_tables.SOURCE_DIGESTS["mobs_tip"],
        )


class MirageReelRe123GuardTests(unittest.TestCase):
    """RE-123 RESULT (2026-08-28T09:13+07:00) identified the "Mirage reel"
    quest NPC the owner reported missing from Prison Exile as MOBS/TIP
    n_id=230, but closed BUILD_IMPACT_NONE / hard guard: no authoritative XYZ
    and no lifecycle/visibility policy exist in the static corpus, so n_id 230
    must NOT be added to KNOWN_PLACEMENTS (no placement row exists for it in
    Bg0002.placements.tsv) and must NOT borrow Mo Yuzi's (n_id 39) coordinates.
    These tests turn that hard guard into something that goes red instead of
    being a comment someone can miss, exactly as RE-122's guard did for stat
    fabrication.
    """

    MIRAGE_REEL_N_ID = 230

    def test_mirage_reel_n_id_is_not_a_known_placement(self):
        known_n_ids = {row[2] for row in tables.KNOWN_PLACEMENTS}
        self.assertNotIn(self.MIRAGE_REEL_N_ID, known_n_ids)

    def test_mirage_reel_n_id_is_not_an_unresolved_placement_either(self):
        # RE-123 found no placement row (known or unresolved) for 230 at all
        # in Bg0002.placements.tsv -- it is not "unresolved", it is simply
        # absent from the placement table entirely (server-owned quest NPC).
        unresolved_n_ids = {row[1] for row in tables.UNRESOLVED_PLACEMENTS}
        self.assertNotIn(self.MIRAGE_REEL_N_ID, unresolved_n_ids)

    def test_known_placement_loader_rejects_n_id_230_out_of_range(self):
        """Proves the ACTUAL mechanism: n_id-range validation (1..41), not
        the unrelated KNOWN_PLACEMENTS-count-drift check.  Adversary review
        (round z851j4) found the first version of this test only ever
        exercised the count-drift guard, which fires before the per-row
        n_id check is reached and masks it -- reproducible with any
        out-of-range n_id (including 42 or 1), not specific to 230.  This
        version bumps KNOWN_COUNT/TOTAL_PLACEMENT_COUNT to match the
        appended row so the count-drift check does not short-circuit, then
        asserts the raised error message is specifically the n_id
        rejection (not just any Scene2TableError).
        """
        original_known = tables.KNOWN_PLACEMENTS
        original_count = tables.KNOWN_COUNT
        original_total = tables.TOTAL_PLACEMENT_COUNT
        try:
            fake_row = (
                tables.TOTAL_PLACEMENT_COUNT, 1, self.MIRAGE_REEL_N_ID,
                0.0, 0.0, 0.0, 'M015_000_000_SP2', False, 'Mirage reel', '',
                20, 20, 0, 2, 0, 150, 1771, 0, 0, 0,
            )
            tables.KNOWN_PLACEMENTS = original_known + [fake_row]
            tables.KNOWN_COUNT = original_count + 1
            tables.TOTAL_PLACEMENT_COUNT = original_total + 1
            with self.assertRaises(tables.Scene2TableError) as ctx:
                tables.load_known_placements()
            message = str(ctx.exception)
            self.assertIn("n_id", message)
            self.assertIn("[1,41]", message)
        finally:
            tables.KNOWN_PLACEMENTS = original_known
            tables.KNOWN_COUNT = original_count
            tables.TOTAL_PLACEMENT_COUNT = original_total

    def test_loader_rejects_n_id_230_even_when_baited_with_mo_yuzis_coordinates(self):
        """Adversary review (round z851j4) found the original coordinate-
        reuse test looped over KNOWN_PLACEMENTS for an n_id 230 row that
        never exists there (230 cannot be a known row -- see the test
        above), so its assertNotEqual line never executed: a vacuous pass
        that protected nothing beyond the tests above it. This replaces it
        with a real experiment: try to smuggle n_id 230 in using Mo Yuzi's
        (n_id 39) EXACT coordinates as bait -- the specific fabrication
        RE-123's nonclaims section forbids -- and confirm the loader's
        n_id-range guard rejects it anyway, coordinates notwithstanding.
        """
        mo_yuzi_rows = [row for row in tables.KNOWN_PLACEMENTS if row[2] == 39]
        self.assertEqual(len(mo_yuzi_rows), 1)
        mo_yuzi_x, mo_yuzi_y, mo_yuzi_z = mo_yuzi_rows[0][3:6]

        original_known = tables.KNOWN_PLACEMENTS
        original_count = tables.KNOWN_COUNT
        original_total = tables.TOTAL_PLACEMENT_COUNT
        try:
            fake_row = (
                tables.TOTAL_PLACEMENT_COUNT, 1, self.MIRAGE_REEL_N_ID,
                mo_yuzi_x, mo_yuzi_y, mo_yuzi_z, 'M015_000_000_SP2', False,
                'Mirage reel', '', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0,
            )
            tables.KNOWN_PLACEMENTS = original_known + [fake_row]
            tables.KNOWN_COUNT = original_count + 1
            tables.TOTAL_PLACEMENT_COUNT = original_total + 1
            with self.assertRaises(tables.Scene2TableError) as ctx:
                tables.load_known_placements()
            self.assertIn("n_id", str(ctx.exception))
        finally:
            tables.KNOWN_PLACEMENTS = original_known
            tables.KNOWN_COUNT = original_count
            tables.TOTAL_PLACEMENT_COUNT = original_total


class RefusalTests(unittest.TestCase):
    def test_a_shape_drifted_known_row_is_refused(self):
        import dataclasses

        original = tables.KNOWN_PLACEMENTS
        try:
            tables.KNOWN_PLACEMENTS = original + [(999, 1, 1)]
            with self.assertRaises(tables.Scene2TableError):
                tables.load_known_placements()
        finally:
            tables.KNOWN_PLACEMENTS = original

    def test_anchor_report_refuses_if_veronica_row_count_drifts(self):
        original = tables.KNOWN_PLACEMENTS
        try:
            tables.KNOWN_PLACEMENTS = [
                row for row in original if row[2] != tables.VERONICA_N_ID
            ]
            with self.assertRaises(tables.Scene2TableError):
                tables.anchor_report()
        finally:
            tables.KNOWN_PLACEMENTS = original


if __name__ == "__main__":
    unittest.main()
