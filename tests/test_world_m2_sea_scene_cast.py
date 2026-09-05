"""LANE-A / M2: the creature-line source enumeration, pinned against things
outside the module.

MOST OF THIS FILE EXISTS BECAUSE ITS OWN FIRST DRAFT SCORED 2 KILLS OUT OF
29 MUTATIONS.  pf-adversary's finding was that every assertion compared the
module's constants against themselves, so mutating a pinned row, a digest,
a scene type, or the body of a derived predicate to `return True` all
survived.  Every test below is therefore anchored on something the module
does not own:

* the pinned rows and digests are written out again HERE, literally, so a
  row edited on one side and not the other fails;
* scene 126's resolved count is cross-checked against
  `world_population_bg3001.ROSTER_COUNT`, a roster this lane composed by a
  completely different route -- 37 has to come out of both or one of them
  is wrong;
* the target and panel sets are cross-checked against
  `world_m2_sea_destination.COLUMBUS_ROUTES`' own columns;
* the [CONTESTED] tag is cross-checked against the SOURCE TEXT of the
  module the number is imported from, so dropping the tag next door fails
  here;
* the derived predicates are driven with injected rows, so a body replaced
  by a constant dies.

The whole console line is asserted as one string, because the earlier
version checked only the `M2_SEA_CAST ` prefix and deleting any field from
the line survived.
"""

from __future__ import annotations

import datetime
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch  # noqa: E402
from pirateforce_foundation import world_m2_sea_destination  # noqa: E402
from pirateforce_foundation import world_m2_sea_scene_cast as cast  # noqa: E402
from pirateforce_foundation import world_m2_survey_plan  # noqa: E402
from pirateforce_foundation import world_population_bg3001  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402

# The measurement, written out a second time on purpose.  scene id ->
# (model, n_SCENE_TYPE, direct n_CLINE_TYPE, INSTANCE types, SAILING types,
#  placements, resolved, best type).  Re-derivable with
# tools/pf_scene_cast_sources_extract.py against the digests below.
EXPECTED = {
    17: ("Bg1001", 4, 0xFFFFFFFF, (801, 814, 816), (), 8, 7, 801),
    18: ("Bg1002", 4, 0xFFFFFFFF, (803, 805, 818), (), 8, 8, 818),
    19: ("Bg1003", 4, 0xFFFFFFFF, (821,), (), 8, 8, 821),
    20: ("Bg1004", 4, 0xFFFFFFFF, (809, 823), (), 10, 10, 809),
    21: ("Bg1005", 4, 0xFFFFFFFF, (811, 825), (), 13, 13, 811),
    39: ("Bg1023", 4, 0xFFFFFFFF, (519,), (), 11, 11, 519),
    40: ("Bg1024", 4, 0xFFFFFFFF, (520,), (), 37, 35, 520),
    41: ("Bg1025", 4, 0xFFFFFFFF, (521,), (), 10, 10, 521),
    126: ("Bg3001", 8, 3001, (), (8000,), 38, 37, 3001),
}

EXPECTED_SOURCE_DIGESTS = {
    "gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv":
        "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b",
    "gamedata/tables/CONSTDATA_TH__INSTANCE.tsv":
        "e3b54a192b886284f30cdf94922d3ee2f5907f4db6c8ab24a6850318d21558f4",
    "gamedata/tables/CONSTDATA_TH__SAILING_RESULT.tsv":
        "9a047da026c12c2909e9c2725a19e49713161c5d9e10c108e386157446323d2c",
}

EXPECTED_CONSOLE_LINE = (
    "M2_SEA_CAST door=17 door_contested=YES"
    " door_verdict=CAST_RESOLVES_PARTIALLY door_source=INSTANCE"
    " door_cast=7/8 door_composer=none"
    " trial=126 trial_verdict=CAST_RESOLVES_PARTIALLY trial_source=SCENE_NAME"
    " trial_cast=37/38 trial_composer=bg3001_roster"
    " halves_agree=NO targets_resolving=8/8"
    " targets_buildable_unbuilt=17,18,19,20,21,39,40,41 sources_checked=3"
)


class PinnedMeasurementTests(unittest.TestCase):

    def test_every_pinned_row_matches_the_second_copy(self):
        self.assertEqual(set(cast._MEASURED_ROWS), set(EXPECTED))
        for scene_id, expected in sorted(EXPECTED.items()):
            with self.subTest(scene_id=scene_id):
                row = cast.cast_capacity(scene_id)
                self.assertEqual(
                    (row.model_id, row.scene_type, row.direct_cline_type,
                     row.instance_cline_types, row.sailing_cline_types,
                     row.placements, row.resolved, row.best_cline_type),
                    expected,
                )

    def test_the_three_sources_are_named_with_their_keys_and_digests(self):
        by_name = {
            name: (key, sha) for name, key, sha in cast.CREATURE_LINE_SOURCES
        }
        self.assertEqual(set(by_name), set(EXPECTED_SOURCE_DIGESTS))
        self.assertEqual(
            by_name["gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv"][0], "n_ID")
        self.assertEqual(
            by_name["gamedata/tables/CONSTDATA_TH__INSTANCE.tsv"][0],
            "n_SCENE_ID")
        self.assertEqual(
            by_name["gamedata/tables/CONSTDATA_TH__SAILING_RESULT.tsv"][0],
            "n_AREA")
        for name, expected_sha in EXPECTED_SOURCE_DIGESTS.items():
            with self.subTest(table=name):
                self.assertEqual(by_name[name][1], expected_sha)

    def test_the_join_tables_carry_their_own_digests(self):
        self.assertEqual(
            cast.CLINE_TABLE_SHA256,
            "aa4a55b8db882eb965d0b7e186cd7bc7b5a81da8f057fee24586a27c94b2dc40",
        )
        self.assertEqual(
            cast.MOBS_TABLE_SHA256,
            "3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b",
        )

    def test_scene_126s_count_agrees_with_the_roster_this_lane_composed(self):
        """The one row with a second, independent producer.  37 comes out of
        the shipped roster module and out of this measurement, by different
        routes; if they ever disagree one of them is wrong."""
        row = cast.cast_capacity(126)
        self.assertEqual(row.resolved, world_population_bg3001.ROSTER_COUNT)
        self.assertEqual(row.placements,
                         world_population_bg3001.PLACEMENT_COUNT)

    def test_measured_at_is_a_real_timestamp(self):
        parsed = datetime.datetime.fromisoformat(cast.MEASURED_AT)
        self.assertIsNotNone(parsed.tzinfo)

    def test_the_sentinel_is_the_all_ones_u32(self):
        self.assertEqual(cast.NO_DIRECT_CLINE_TYPE, 0xFFFFFFFF)
        self.assertEqual(cast.NO_DIRECT_CLINE_TYPE, 4294967295)


class TheCorrectionTests(unittest.TestCase):
    """The claims that replaced this round's refuted first draft."""

    def test_all_eight_columbus_targets_resolve_a_cast(self):
        self.assertEqual(
            cast.targets_with_a_resolvable_cast(),
            cast.COLUMBUS_TARGET_SCENE_IDS,
        )
        self.assertEqual(len(cast.COLUMBUS_TARGET_SCENE_IDS), 8)

    def test_every_target_answers_through_instance_not_its_own_row(self):
        """The whole correction in one assertion: the door scenes carry the
        sentinel in SCENE_NAME and are answered by INSTANCE."""
        for scene_id in cast.COLUMBUS_TARGET_SCENE_IDS:
            with self.subTest(scene_id=scene_id):
                row = cast.cast_capacity(scene_id)
                self.assertEqual(row.direct_cline_type,
                                 cast.NO_DIRECT_CLINE_TYPE)
                self.assertEqual(row.answering_source, cast.SOURCE_INSTANCE)
                self.assertTrue(row.a_cast_resolves)

    def test_two_targets_resolve_more_completely_than_scene_126_does(self):
        """21 at 13/13 and 39 at 11/11 against 126 at 37/38 -- the sentence
        the first draft's conclusion could not survive."""
        panel = cast.cast_capacity(126)
        self.assertLess(panel.resolved, panel.placements)
        for scene_id in (21, 39):
            with self.subTest(scene_id=scene_id):
                row = cast.cast_capacity(scene_id)
                self.assertEqual(row.resolved, row.placements)
                self.assertEqual(row.verdict, cast.VERDICT_CAST_RESOLVES)

    def test_three_of_the_targets_are_islands_by_the_tables_own_name(self):
        for scene_id in (39, 40, 41):
            with self.subTest(scene_id=scene_id):
                self.assertIn("island",
                              cast.cast_capacity(scene_id).name_gloss)
        for scene_id in (17, 18, 19, 20, 21):
            with self.subTest(scene_id=scene_id):
                self.assertIn("ship",
                              cast.cast_capacity(scene_id).name_gloss)

    def test_none_of_the_eight_has_a_roster_yet(self):
        self.assertEqual(
            cast.targets_with_no_roster_yet(),
            cast.COLUMBUS_TARGET_SCENE_IDS,
        )
        for scene_id in cast.COLUMBUS_TARGET_SCENE_IDS:
            self.assertNotIn(scene_id, world_scene_travel.CENSUS_SOURCES)


class AnchoredOnTheirOwnersTests(unittest.TestCase):

    def test_the_two_scene_ids_are_read_from_their_owners(self):
        self.assertEqual(
            cast.DOOR_SCENE_ID,
            world_m2_sea_destination.DESTINATION_SCENE_N_ID,
        )
        self.assertEqual(
            cast.TRIAL_SCENE_ID, world_m2_survey_plan.XYZ_FRAME_SCENE_ID,
        )

    def test_the_target_and_panel_sets_are_the_routes_own_two_columns(self):
        routes = world_m2_sea_destination.COLUMBUS_ROUTES
        self.assertEqual(set(cast.COLUMBUS_TARGET_SCENE_IDS),
                         {row[3] for row in routes})
        self.assertEqual(set(cast.ADVERTISED_PANEL_SCENE_IDS),
                         {row[4] for row in routes})

    def test_the_contested_tag_still_exists_where_the_number_lives(self):
        """If the source module ever stops calling its own constant
        [CONTESTED], this module's tag is a lie and this test says so."""
        source = Path(
            world_m2_sea_destination.__file__
        ).read_text(encoding="utf-8")
        self.assertIn("[CONTESTED]", source)
        self.assertIn("MARKER[17].n_SCENE", source)
        self.assertTrue(cast.DOOR_SCENE_ID_IS_CONTESTED)
        self.assertEqual(cast.DOOR_RIVAL_READING_SCENE_ID, 126)

    def test_under_the_rival_reading_the_two_halves_would_agree(self):
        self.assertEqual(cast.DOOR_RIVAL_READING_SCENE_ID,
                         cast.TRIAL_SCENE_ID)


class DerivedNotAssertedTests(unittest.TestCase):
    """Drive the predicates with injected rows, so a body replaced by a
    constant dies."""

    def _with_rows(self, rows):
        original = dict(cast._MEASURED_ROWS)
        cast._MEASURED_ROWS.clear()
        cast._MEASURED_ROWS.update(rows)
        self.addCleanup(lambda: (cast._MEASURED_ROWS.clear(),
                                 cast._MEASURED_ROWS.update(original)))

    def test_a_target_whose_cast_stops_resolving_drops_out(self):
        rows = dict(cast._MEASURED_ROWS)
        model, gloss, stype, direct, inst, sail, plc, _res, best = rows[17]
        rows[17] = (model, gloss, stype, direct, inst, sail, plc, 0, best)
        self._with_rows(rows)
        self.assertNotIn(17, cast.targets_with_a_resolvable_cast())
        self.assertEqual(cast.cast_capacity(17).verdict,
                         cast.VERDICT_NO_SOURCE_ANSWERS)

    def test_a_target_that_gains_a_roster_drops_out_of_the_unbuilt_list(self):
        original = dict(world_scene_travel.CENSUS_SOURCES)
        world_scene_travel.CENSUS_SOURCES[17] = "bg1001_roster"
        self.addCleanup(
            lambda: (world_scene_travel.CENSUS_SOURCES.clear(),
                     world_scene_travel.CENSUS_SOURCES.update(original)))
        self.assertIn(17, cast.targets_with_a_resolvable_cast())
        self.assertNotIn(17, cast.targets_with_no_roster_yet())

    def test_halves_agree_answers_yes_when_the_two_ids_match(self):
        original = cast.DOOR_SCENE_ID
        try:
            cast.DOOR_SCENE_ID = cast.TRIAL_SCENE_ID
            self.assertTrue(cast.halves_agree())
        finally:
            cast.DOOR_SCENE_ID = original
        self.assertFalse(cast.halves_agree())

    def test_a_full_resolution_reads_differently_from_a_partial_one(self):
        rows = dict(cast._MEASURED_ROWS)
        model, gloss, stype, direct, inst, sail, plc, _res, best = rows[17]
        rows[17] = (model, gloss, stype, direct, inst, sail, plc, plc, best)
        self._with_rows(rows)
        self.assertEqual(cast.cast_capacity(17).verdict,
                         cast.VERDICT_CAST_RESOLVES)

    def test_a_scene_with_no_source_at_all_is_not_called_unmeasured(self):
        rows = dict(cast._MEASURED_ROWS)
        rows[555] = ("Bg0555", "invented", 4, cast.NO_DIRECT_CLINE_TYPE,
                     (), (), 4, 0, -1)
        self._with_rows(rows)
        row = cast.cast_capacity(555)
        self.assertIsNone(row.answering_source)
        self.assertEqual(row.verdict, cast.VERDICT_NO_SOURCE_ANSWERS)
        self.assertNotEqual(row.verdict, cast.VERDICT_NOT_MEASURED)

    def test_an_unmeasured_scene_is_not_called_castless(self):
        row = cast.cast_capacity(4242)
        self.assertEqual(row.verdict, cast.VERDICT_NOT_MEASURED)
        self.assertNotEqual(row.verdict, cast.VERDICT_NO_SOURCE_ANSWERS)


class ConsoleLineTests(unittest.TestCase):

    def test_the_whole_line_is_pinned_not_just_its_prefix(self):
        line = cast.sea_scene_cast_console_line()
        line.encode("ascii")
        self.assertEqual(line, EXPECTED_CONSOLE_LINE)

    def test_safe_wrapper_never_raises_and_names_the_failure(self):
        original = cast.cast_capacity
        try:
            def boom(_scene_id):
                raise RuntimeError("measured failure")
            cast.cast_capacity = boom
            line = cast.sea_scene_cast_console_line_safe()
        finally:
            cast.cast_capacity = original
        self.assertEqual(line, "M2_SEA_CAST unmeasured reason=RuntimeError")

    def test_a_composer_table_that_will_not_answer_degrades_to_none(self):
        original = world_scene_travel.CENSUS_SOURCES

        class Hostile:
            def get(self, _key):
                raise RuntimeError("no table today")

        try:
            world_scene_travel.CENSUS_SOURCES = Hostile()
            row = cast.cast_capacity(126)
        finally:
            world_scene_travel.CENSUS_SOURCES = original
        self.assertIsNone(row.composer_source)


class DispatchReportTests(unittest.TestCase):
    """The line has to actually reach the default path, last, and whole."""

    def test_the_crossing_prints_the_whole_line_last(self):
        lines = []
        columbus_quest_dispatch.dispatch_columbus_quest3021(emit=lines.append)
        printed = [line for line in lines if isinstance(line, str)]
        self.assertEqual(printed[-1], EXPECTED_CONSOLE_LINE)
        self.assertEqual(
            1, sum(1 for line in printed if line.startswith("M2_SEA_CAST ")),
        )


if __name__ == "__main__":
    unittest.main()
