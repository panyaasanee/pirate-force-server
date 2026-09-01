"""LANE-A door-priority build: the Bg0004 (Slave Market Island) placement
roster.

The load-bearing tests here are the shape checks (84 known + 32 unresolved =
116, no placement index used twice), the two documented data discrepancies
(name/template_ids disagreement, the reused "Training Iron Man" n_id 917 gap
also seen in bg0001), and ASCII-only display strings -- this table backs an
UNVERIFIED crosswalk (no owner in-game confirmation exists yet for this
scene, unlike bg0001/bg0002), and these tests are what keeps that qualifier
honest against a future silent edit.
"""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import scene4_slave_market_tables as tables


class KnownPlacementsShapeTests(unittest.TestCase):
    def test_the_counts_add_up_to_every_row_in_the_source_file(self):
        self.assertEqual(len(tables.KNOWN_PLACEMENTS), tables.KNOWN_COUNT)
        self.assertEqual(len(tables.UNRESOLVED_PLACEMENTS), tables.UNRESOLVED_COUNT)
        self.assertEqual(
            tables.KNOWN_COUNT + tables.UNRESOLVED_COUNT,
            tables.TOTAL_PLACEMENT_COUNT,
        )
        self.assertEqual(tables.KNOWN_COUNT, 84)
        self.assertEqual(tables.UNRESOLVED_COUNT, 32)
        self.assertEqual(tables.TOTAL_PLACEMENT_COUNT, 116)

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
        self.assertEqual(by_index[1].n_id, 67)
        self.assertEqual(by_index[1].display_name, "Columbus")
        self.assertEqual(by_index[7].n_id, 73)
        self.assertEqual(by_index[7].display_name, "Angelina")
        self.assertEqual(by_index[7].title, "Princess Slave")

    def test_no_known_row_has_an_empty_name_or_preset(self):
        for placement in tables.load_known_placements():
            self.assertTrue(placement.display_name)
            self.assertTrue(placement.visual_preset)

    def test_ascii_only(self):
        for placement in tables.load_known_placements():
            self.assertTrue(placement.display_name.isascii())
            self.assertTrue(placement.title.isascii())
            self.assertTrue(placement.visual_preset.isascii())

    def test_actor_identity_matches_the_project_wide_formula(self):
        for placement in tables.load_known_placements():
            self.assertEqual(
                placement.actor_identity, 0x2000 + placement.placement_index + 1,
            )


class NameTemplateIdMismatchTests(unittest.TestCase):
    """Docstring step 1: two placements' own name text disagrees with the
    authoritative ``template_ids`` column.  Both resolve via template_ids,
    not the name text -- this test is what keeps that choice from silently
    reverting.
    """

    def test_both_mismatches_are_recorded(self):
        mismatches = tables.name_template_id_mismatches()
        self.assertEqual(len(mismatches), 2)
        indices = {m[0] for m in mismatches}
        self.assertEqual(indices, {82, 83})

    def test_the_mismatched_rows_resolved_via_template_ids_not_the_name_text(self):
        by_index = {p.placement_index: p for p in tables.load_known_placements()}
        # Mismatch row 82 named "Mob_Set_34 08" but template_ids=45.
        self.assertEqual(by_index[82].n_id, 519)  # CLINE(4,45).n_LEADER_BK1
        self.assertEqual(by_index[82].display_name, "Jet cat thieves No.3")
        # Mismatch row 83 named "Mob_Set_34 09" but template_ids=46.
        self.assertEqual(by_index[83].n_id, 246)  # CLINE(4,46).n_LEADER_BK1
        self.assertEqual(by_index[83].display_name, "Jet cat thieves No.4")


class UnresolvedPlacementReasonTests(unittest.TestCase):
    def test_placement_zero_has_no_mobs_row(self):
        unresolved = {u.placement_index: u for u in tables.load_unresolved_placements()}
        self.assertIn(0, unresolved)
        self.assertEqual(unresolved[0].reason, "no_mobs_row_for_n_id_66")

    def test_the_reused_training_iron_man_n_id_917_gap_is_25_placements(self):
        # The SAME n_id world_port_royal_identity.py already names as having
        # a MOBS row but no MOBS_TIP row in bg0001 (Mob-Set 98/103 there;
        # Mob-Set 107 here) -- directly relevant to the still-open RE-155
        # ticket, recorded not fixed (see module docstring step 4).
        unresolved = tables.load_unresolved_placements()
        n917 = [u for u in unresolved if "917" in u.reason]
        self.assertEqual(len(n917), 25)
        for u in n917:
            self.assertEqual(u.set_number, 107)

    def test_the_six_pathfinding_helper_markers_are_unresolved_not_placed(self):
        unresolved = tables.load_unresolved_placements()
        helpers = [u for u in unresolved if "1001" in u.reason]
        self.assertEqual(len(helpers), 6)

    def test_known_n_ids_and_unresolved_n_id_66_do_not_overlap(self):
        known_n_ids = {p.n_id for p in tables.load_known_placements()}
        self.assertNotIn(66, known_n_ids)


class RefusalTests(unittest.TestCase):
    def test_a_shape_drifted_known_row_is_refused(self):
        original = tables.KNOWN_PLACEMENTS
        try:
            tables.KNOWN_PLACEMENTS = original + [(999, 1, 1)]
            with self.assertRaises(tables.Scene4TableError):
                tables.load_known_placements()
        finally:
            tables.KNOWN_PLACEMENTS = original

    def test_a_duplicate_placement_index_is_refused(self):
        original = tables.KNOWN_PLACEMENTS
        original_count = tables.KNOWN_COUNT
        try:
            tables.KNOWN_PLACEMENTS = original + [original[0]]
            tables.KNOWN_COUNT = original_count + 1
            with self.assertRaises(tables.Scene4TableError):
                tables.load_known_placements()
        finally:
            tables.KNOWN_PLACEMENTS = original
            tables.KNOWN_COUNT = original_count

    def test_an_empty_display_name_is_refused_not_shipped(self):
        # Unlike bg0001's own convention (an empty-named row still ships),
        # this module follows scene2_prison_exile_tables.py's rule: refuse
        # into UNRESOLVED rather than send a nameless actor.
        original = tables.KNOWN_PLACEMENTS
        original_count = tables.KNOWN_COUNT
        try:
            bad_row = (999, 1, 917, 0.0, 0.0, 0.0, 'INVISIBLE', False,
                       '', '', 1, 1, 0, 0, 0, 100, 1, 0, 0, 0)
            tables.KNOWN_PLACEMENTS = original + [bad_row]
            tables.KNOWN_COUNT = original_count + 1
            with self.assertRaises(tables.Scene4TableError):
                tables.load_known_placements()
        finally:
            tables.KNOWN_PLACEMENTS = original
            tables.KNOWN_COUNT = original_count


if __name__ == "__main__":
    unittest.main()
