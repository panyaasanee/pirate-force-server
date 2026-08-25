"""LANE-A BUILD-001 / M1: where the town actually is.

The load-bearing test in this file is ``test_the_pin_re_derives_from_the_frozen
_table``.  Every other number this module publishes is only as good as that
one: the pin was written by a script that read two tables in the OTHER
repository, and this repository cannot see those tables.  What it CAN do is
recompute the shipped-census half from v141 and refuse the pin if it drifted.

The second load-bearing test is ``test_the_login_view_is_thinner_than_the_best
_stand_point``.  That comparison is the whole reason this module exists, so it
is computed live from the frozen table on both sides - never read back out of
the pin that asserts it.

The third is ``test_the_unverifiable_list_cannot_grow_in_silence``.  A previous
revision of this module skipped ten pinned numbers without saying so, and a
pin whose headline had been replaced with 99999 still verified clean.  Skips
are now enumerated, and this test pins how many there are.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_density
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import PORT_ROYAL_SOURCE_COUNT
from pirateforce_foundation.world_density import (
    CENSUS_GAP_RECORDS,
    M1_VIEW_RADIUS,
    MEASURED_BANDS,
    SCENE_DISTINCT_COORDINATES,
    SCENE_PLACEMENT_RECORDS,
    SCENE_XYZ_TRIPLES_WRITTEN,
    UNVERIFIABLE_HERE,
    VERDICT_RADIUS,
    attended_measured_spawn,
    census_added_at_the_login_view,
    census_gap,
    census_gap_reasons,
    densest_real_placement,
    densest_stand_point,
    extra_triple_chains,
    gap_rule_separates_both_ways,
    login_anchor,
    m1_console_line,
    neighbours_within,
    radius_sensitivity,
    scene_inventory,
    verify_pin_against_source,
)

PIN = ROOT / "scenarios" / "world_scene_density_001.json"


class WorldDensityTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    # -- the three that carry the module ------------------------------------

    def test_the_pin_re_derives_from_the_frozen_table(self) -> None:
        """If this fails the pin is stale and every number below is a quote."""
        self.assertEqual(verify_pin_against_source(self.legacy)["disagreements"], ())

    def test_the_login_view_is_thinner_than_the_best_stand_point(self) -> None:
        """M1's actual finding, recomputed live on both sides of the compare.

        Reading either count out of the pin would make this test agree with
        the document that asserts the claim, which is not evidence.
        """
        at_login = neighbours_within(self.legacy, login_anchor().xyz, M1_VIEW_RADIUS)
        at_best = neighbours_within(
            self.legacy, densest_stand_point().xyz, M1_VIEW_RADIUS,
        )
        self.assertLess(len(at_login), len(at_best))
        # Pinned so a future table that quietly evens the two out is loud here
        # rather than silently turning the finding into "they are about equal".
        self.assertEqual(len(at_login), 2)
        self.assertEqual(len(at_best), 12)

    def test_the_unverifiable_list_cannot_grow_in_silence(self) -> None:
        """Skips are enumerated, so adding one has to be a deliberate edit."""
        result = verify_pin_against_source(self.legacy)
        self.assertEqual(set(result), {"disagreements", "unverifiable"})
        self.assertEqual(result["unverifiable"], UNVERIFIABLE_HERE)
        self.assertEqual(len(UNVERIFIABLE_HERE), 9)
        for entry in UNVERIFIABLE_HERE:
            self.assertTrue(entry.isascii(), entry)

    # -- what the verifier does and does not catch, demonstrated ------------

    def test_a_tampered_census_count_is_caught(self) -> None:
        """The half this repository owns really does refuse a drifted pin."""
        document = json.loads(PIN.read_text("ascii"))
        document["stand_points"]["login_anchor"]["measured"][
            "within_2000u_shipped_census"
        ] = 99999
        with self._pin(document):
            problems = verify_pin_against_source(self.legacy)["disagreements"]
        self.assertTrue(problems)
        self.assertIn("99999", " ".join(problems))

    def test_a_tampered_all_file_count_is_NOT_caught_and_the_module_admits_it(
        self,
    ) -> None:
        """The honest half of the story, kept as a test so it cannot be forgotten.

        Replacing the all-file band counts with garbage leaves the verifier
        clean, because the table that would refute them is in the other
        repository.  That is exactly why they are named in UNVERIFIABLE_HERE.
        """
        document = json.loads(PIN.read_text("ascii"))
        for key in list(document["stand_points"]["login_anchor"]["measured"]):
            if key.endswith("_all_file_points"):
                document["stand_points"]["login_anchor"]["measured"][key] = 99999
        with self._pin(document):
            result = verify_pin_against_source(self.legacy)
            self.assertEqual(result["disagreements"], ())
            self.assertEqual(login_anchor().file_point_neighbours(), 99999)
        self.assertIn(
            "stand_points.*.measured.within_*u_all_file_points"
            " - needs the placement table",
            UNVERIFIABLE_HERE,
        )

    def test_a_pin_that_lost_a_section_is_refused_not_KeyErrored(self) -> None:
        document = json.loads(PIN.read_text("ascii"))
        document.pop("cross_source_controls")
        with self._pin(document):
            with self.assertRaises(ValueError):
                scene_inventory()

    def test_the_module_refuses_a_pin_that_is_not_its_own_document(self) -> None:
        original = world_density.PIN_PATH
        try:
            world_density.PIN_PATH = ROOT / "scenarios" / "world_population_full_001.json"
            with self.assertRaises(ValueError):
                scene_inventory()
        finally:
            world_density.PIN_PATH = original
        self.assertEqual(verify_pin_against_source(self.legacy)["disagreements"], ())

    def _pin(self, document: dict):
        test = self

        class _Swap:
            def __enter__(self) -> None:
                self.original = world_density.PIN_PATH
                handle = tempfile.NamedTemporaryFile(
                    "w", suffix=".json", delete=False, encoding="ascii",
                )
                json.dump(document, handle, ensure_ascii=True)
                handle.close()
                self.path = Path(handle.name)
                world_density.PIN_PATH = self.path

            def __exit__(self, *_exc) -> None:
                world_density.PIN_PATH = self.original
                self.path.unlink(missing_ok=True)
                test.assertEqual(world_density.PIN_PATH, PIN)

        return _Swap()

    def test_the_position_a_person_actually_starts_at_is_emptier_still(self) -> None:
        """The login anchor is a constant; the DB row is where a tester lands.

        The attended GT-045 run measured the real spawn 715.6 units from
        v141's constant, and at that position NOTHING is inside 500 units.
        Recomputed live, because this is the number a human will check with
        their own eyes.
        """
        spawn = attended_measured_spawn()
        constant = login_anchor()
        offset = sum((a - b) ** 2 for a, b in zip(spawn.xyz, constant.xyz)) ** 0.5
        self.assertGreater(offset, 700.0)
        self.assertLess(offset, 730.0)
        self.assertEqual(len(neighbours_within(self.legacy, spawn.xyz, 500.0)), 0)
        self.assertEqual(
            len(neighbours_within(self.legacy, spawn.xyz, M1_VIEW_RADIUS)), 3)
        line = m1_console_line(self.legacy, spawn.xyz)
        self.assertIn("census_within_500u=0", line)
        self.assertIn("verdict=THIN_VIEW", line)

    # -- the claim that was refuted once, kept honest by a test -------------

    def test_raising_three_to_115_adds_exactly_one_member_at_the_login_view(
        self,
    ) -> None:
        """Not zero.  An earlier draft said zero and its own data refuted it.

        Recomputed live: the census members inside the login view, minus the
        three the server already sends today.
        """
        shipped_today = set(self.legacy.V112_TEST_INDICES)
        near = {
            p.placement_index
            for p in neighbours_within(self.legacy, login_anchor().xyz, M1_VIEW_RADIUS)
        }
        added = sorted(near - shipped_today)
        self.assertEqual(added, [1])
        self.assertEqual(
            [row["placement_index"] for row in census_added_at_the_login_view()], added,
        )
        # And the nearest actor of all is one the server ALREADY sends, which
        # is the part that makes "the census fills the login view" false.
        nearest = neighbours_within(self.legacy, login_anchor().xyz, M1_VIEW_RADIUS)[0]
        self.assertIn(nearest.placement_index, shipped_today)

    def test_the_finding_does_not_depend_on_the_radius_that_was_chosen(self) -> None:
        """2000u was a choice.  The census half has to survive the others too."""
        login = login_anchor().xyz
        best = densest_stand_point().xyz
        for row in radius_sensitivity():
            radius = float(row["radius_units"])
            live_login = len(neighbours_within(self.legacy, login, radius))
            live_best = len(neighbours_within(self.legacy, best, radius))
            self.assertEqual(live_login, row["login_shipped_census"], radius)
            self.assertEqual(live_best, row["densest_shipped_census"], radius)
            self.assertGreaterEqual(live_best, 3 * live_login, radius)

    def test_the_headline_survives_dropping_the_undecided_data(self) -> None:
        """The tiebreak used data of unknown meaning; the census count must not.

        The best point that IS a real placement has to score the same 12, or
        the finding is an artefact of counting patrol waypoints.
        """
        real_xyz, real_count = densest_real_placement()
        live = len(neighbours_within(self.legacy, real_xyz, M1_VIEW_RADIUS))
        self.assertEqual(live, real_count)
        self.assertEqual(live, densest_stand_point().census_neighbours())

    # -- the gap ------------------------------------------------------------

    def test_the_gap_arithmetic_closes_with_nothing_left_over(self) -> None:
        inventory = scene_inventory()
        self.assertEqual(inventory["shipped_census_records"], PORT_ROYAL_SOURCE_COUNT)
        self.assertEqual(inventory["placement_records"], SCENE_PLACEMENT_RECORDS)
        self.assertEqual(inventory["gap_records"], CENSUS_GAP_RECORDS)
        self.assertEqual(
            inventory["shipped_census_records"] + inventory["gap_records"],
            inventory["placement_records"],
        )
        self.assertEqual(
            inventory["placement_records"] + inventory["extra_triples_written"],
            SCENE_XYZ_TRIPLES_WRITTEN,
        )
        self.assertEqual(inventory["triples_written_total"], SCENE_XYZ_TRIPLES_WRITTEN)

    def test_written_triples_are_never_reported_as_distinct_positions(self) -> None:
        """859 is what the file writes; 856 is how many places that is."""
        inventory = scene_inventory()
        self.assertLess(inventory["distinct_coordinates"], inventory["triples_written_total"])
        self.assertEqual(inventory["distinct_coordinates"], SCENE_DISTINCT_COORDINATES)

    def test_every_dropped_row_has_a_measured_reason(self) -> None:
        """The docstring said "semicolon rows".  This checks all 34, not the phrase."""
        allowed = {"multi_outfit_variants_unresolved", "no_mobs_row_for_template_id"}
        rows = census_gap()
        self.assertEqual(len(rows), CENSUS_GAP_RECORDS)
        for row in rows:
            self.assertIn(row["reason"], allowed, row)
            if row["reason"] == "multi_outfit_variants_unresolved":
                self.assertIn(";", row["s_OUTFIT"], row)
        reasons = census_gap_reasons()
        self.assertEqual(sum(reasons.values()), CENSUS_GAP_RECORDS)
        self.assertEqual(set(reasons), allowed)

    def test_the_drop_criterion_is_a_rule_not_a_description(self) -> None:
        """It has to separate the survivors too, or it explains nothing."""
        both = gap_rule_separates_both_ways()
        self.assertEqual(both["dropped_rows_matching_the_rule"], CENSUS_GAP_RECORDS)
        self.assertEqual(both["shipped_rows_with_a_semicolon"], 0)
        self.assertEqual(both["shipped_rows_with_no_MOBS_row"], 0)

    def test_the_gap_claim_is_scoped_to_homes_and_says_so(self) -> None:
        """No dropped row's HOME is in the login view - and that is all it says.

        Their own extra triples get closer, so the pin must not generalise the
        claim to "closing the gap changes nothing here".
        """
        x, y, z = login_anchor().xyz
        for row in census_gap():
            distance2 = (row["x"] - x) ** 2 + (row["y"] - y) ** 2 + (row["z"] - z) ** 2
            self.assertGreater(distance2, M1_VIEW_RADIUS ** 2, row["name"])
        block = json.loads(PIN.read_text("ascii"))["the_gap_of_34"][
            "does_closing_the_gap_help_the_login_view"
        ]
        self.assertGreater(block["but_their_own_extra_triples_reach_further"][
            "within_3000u_3d"], 0)
        self.assertIn("NOT established", block["reading"])

    def test_the_chains_evidence_is_recorded_for_all_eleven(self) -> None:
        """The reason this module stopped calling the triples spawn points."""
        chains = extra_triple_chains()
        self.assertEqual(len(chains), 11)
        self.assertEqual(
            sum(chain["triples"] for chain in chains),
            SCENE_XYZ_TRIPLES_WRITTEN - SCENE_PLACEMENT_RECORDS,
        )
        for chain in chains:
            self.assertLess(chain["home_to_first_point_units"], 500.0, chain["name"])

    # -- the live half ------------------------------------------------------

    def test_neighbours_are_ordered_nearest_first(self) -> None:
        anchor = densest_stand_point().xyz
        found = neighbours_within(self.legacy, anchor, 5000.0)
        distances = [
            (p.x - anchor[0]) ** 2 + (p.y - anchor[1]) ** 2 + (p.z - anchor[2]) ** 2
            for p in found
        ]
        self.assertEqual(distances, sorted(distances))

    def test_a_wider_radius_never_loses_a_member(self) -> None:
        anchor = login_anchor().xyz
        seen: set[int] = set()
        for band in MEASURED_BANDS:
            found = {
                p.placement_index for p in neighbours_within(self.legacy, anchor, band)
            }
            self.assertTrue(seen <= found, band)
            seen = found

    def test_a_radius_past_the_whole_map_returns_the_whole_census(self) -> None:
        found = neighbours_within(self.legacy, login_anchor().xyz, 1_000_000.0)
        self.assertEqual(len(found), PORT_ROYAL_SOURCE_COUNT)

    def test_bad_input_is_refused_rather_than_silently_measured(self) -> None:
        anchor = login_anchor().xyz
        for radius in (0.0, -1.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                neighbours_within(self.legacy, anchor, radius)
        for position in ((0.0, 0.0), [0.0, 0.0, 0.0], (0.0, 0.0, float("nan")),
                         (0.0, 0.0, "0")):
            with self.assertRaises(ValueError):
                neighbours_within(self.legacy, position, 100.0)

    def test_an_unmeasured_band_is_refused_not_interpolated(self) -> None:
        with self.assertRaises(ValueError):
            login_anchor().census_neighbours(1500.0)
        with self.assertRaises(ValueError):
            login_anchor().file_point_neighbours(1500.0)

    # -- the console line ---------------------------------------------------

    def test_the_verdict_is_decided_on_the_nearest_band_not_the_widest(self) -> None:
        """The bug this replaced: an NPC 104 units away scored EMPTY_VIEW.

        Placement 141 has a census neighbour 104 units off but nothing else
        inside 2000u.  Under the old 2000u rule it read empty; under the
        nearest-band rule it reads populated, which is what a pair of eyes
        would say.
        """
        near_pair = None
        for placement in neighbours_within(self.legacy, login_anchor().xyz, 1_000_000.0):
            company = neighbours_within(
                self.legacy, (placement.x, placement.y, placement.z), VERDICT_RADIUS)
            wide = neighbours_within(
                self.legacy, (placement.x, placement.y, placement.z), M1_VIEW_RADIUS)
            if len(company) >= 2 and len(wide) == len(company):
                near_pair = placement
                break
        self.assertIsNotNone(near_pair, "no close pair left in the table to test with")
        line = m1_console_line(
            self.legacy, (near_pair.x, near_pair.y, near_pair.z))
        self.assertIn("verdict=POPULATED_VIEW", line)

    def test_the_console_line_calls_the_login_view_thin(self) -> None:
        line = m1_console_line(self.legacy, login_anchor().xyz)
        self.assertIn("verdict=THIN_VIEW", line)
        self.assertIn("[PROPOSED]", line)
        self.assertIn("pin=best_2000u:12", line)
        self.assertTrue(line.isascii(), line)
        self.assertNotIn("\n", line)

    def test_the_console_line_flips_at_the_best_stand_point(self) -> None:
        line = m1_console_line(self.legacy, densest_stand_point().xyz)
        self.assertIn("verdict=POPULATED_VIEW", line)
        self.assertTrue(line.isascii(), line)

    def test_the_console_line_marks_which_number_came_from_the_pin(self) -> None:
        """Two layers in one line is fine; two layers unlabelled is not."""
        line = m1_console_line(self.legacy, login_anchor().xyz)
        live, _, pinned = line.partition("pin=")
        self.assertNotIn("pin=", live)
        self.assertTrue(pinned.startswith("best_2000u:"))

    # -- the pin as a document ---------------------------------------------

    def test_the_pin_is_ascii_and_declares_itself_not_a_scenario(self) -> None:
        raw = PIN.read_bytes()
        self.assertTrue(raw.isascii())
        self.assertNotIn(b"\r\n", raw)
        document = json.loads(raw.decode("ascii"))
        self.assertEqual(document["lane"], "A_WORLD")
        self.assertFalse(document["test_only"])
        self.assertIn("not_a_scenario", document)
        self.assertIn("nonclaims", document)

    def test_the_pin_still_refuses_to_change_the_owner_ruled_census_count(self) -> None:
        """115 is an owner ruling.  Nothing in this module may move it."""
        self.assertEqual(scene_inventory()["shipped_census_records"], 115)
        self.assertIn(
            "does not change the shipped census count",
            " ".join(json.loads(PIN.read_text("ascii"))["nonclaims"]),
        )

    def test_the_three_cross_source_controls_are_recorded_with_their_results(
        self,
    ) -> None:
        """Including the one that disagrees 115/115, which is the load-bearing one."""
        controls = json.loads(PIN.read_text("ascii"))["cross_source_controls"]
        self.assertEqual(controls["xyz_agree_of_115"], 115)
        self.assertEqual(controls["visual_preset_equals_MOBS_s_OUTFIT_of_115"], 115)
        self.assertEqual(controls["visual_preset_disagreements"], 0)
        self.assertEqual(controls["source_name_agree_of_115"], 0)


if __name__ == "__main__":
    unittest.main()
