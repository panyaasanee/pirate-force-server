"""LANE-A / M2: the sea-scene cast measurement, pinned.

What these tests defend is the FINDING, not the phrasing: the eight ship
scenes the Columbus options target name no creature line, the four ocean
panels they advertise do, and the two halves of M2 point at different
scenes.  A round that changes any of those has changed something real and
should have to say so in a diff.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch  # noqa: E402
from pirateforce_foundation import world_m2_sea_destination  # noqa: E402
from pirateforce_foundation import world_m2_sea_scene_cast as cast  # noqa: E402
from pirateforce_foundation import world_m2_survey_plan  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402


class MeasuredRowsTests(unittest.TestCase):

    def test_every_ship_destination_names_no_creature_line(self):
        """Eight of eight, and each one named rather than counted."""
        for scene_id in cast.SHIP_DESTINATION_SCENE_IDS:
            with self.subTest(scene_id=scene_id):
                row = cast.cast_capacity(scene_id)
                self.assertEqual(row.scene_type, cast.SCENE_TYPE_SHIP)
                self.assertEqual(row.cline_type, cast.NO_CLINE_TYPE)
                self.assertEqual(row.cline_rows, 0)
                self.assertFalse(row.can_carry_a_cast)
                self.assertEqual(row.verdict, cast.VERDICT_NO_CAST_POSSIBLE)

    def test_the_measured_sets_are_the_columbus_routes_own_two_columns(self):
        """Neither set is a list this file made up.  ``COLUMBUS_ROUTES``
        rows are (MOBS n_ID, home scene, row id, target scene, advertised
        ocean scene); the ship set must be column 4 exactly and the panel
        set column 5 exactly, so a route added or retargeted next door
        fails here instead of quietly going unmeasured."""
        routes = world_m2_sea_destination.COLUMBUS_ROUTES
        self.assertEqual(
            set(cast.SHIP_DESTINATION_SCENE_IDS),
            {row[3] for row in routes},
        )
        self.assertEqual(
            set(cast.OCEAN_PANEL_SCENE_IDS),
            {row[4] for row in routes},
        )
        # And row 3021's own target -- the one door a player can walk
        # through today -- is in the ship set, not the panel set.
        self.assertIn(
            world_m2_sea_destination.OPTION_TARGET_SCENE_N_ID[3021],
            cast.SHIP_DESTINATION_SCENE_IDS,
        )

    def test_every_ocean_panel_names_a_creature_line_with_rows(self):
        for scene_id in cast.OCEAN_PANEL_SCENE_IDS:
            with self.subTest(scene_id=scene_id):
                row = cast.cast_capacity(scene_id)
                self.assertEqual(row.scene_type, cast.SCENE_TYPE_OCEAN_PANEL)
                self.assertNotEqual(row.cline_type, cast.NO_CLINE_TYPE)
                self.assertGreater(row.cline_rows, 0)
                self.assertTrue(row.can_carry_a_cast)

    def test_the_ocean_panel_this_project_already_composes_says_so(self):
        """Scene 126 has a roster on main; the verdict must reflect the live
        table, not a frozen guess about it."""
        row = cast.cast_capacity(126)
        self.assertEqual(row.verdict, cast.VERDICT_CAST_POSSIBLE_COMPOSED)
        self.assertEqual(
            row.composer_source, world_scene_travel.CENSUS_SOURCES[126],
        )

    def test_a_panel_with_no_roster_registered_says_not_composed(self):
        for scene_id in (127, 304, 305):
            with self.subTest(scene_id=scene_id):
                self.assertNotIn(scene_id, world_scene_travel.CENSUS_SOURCES)
                self.assertEqual(
                    cast.cast_capacity(scene_id).verdict,
                    cast.VERDICT_CAST_POSSIBLE_NOT_COMPOSED,
                )

    def test_cline_type_sentinel_is_the_all_ones_u32(self):
        self.assertEqual(cast.NO_CLINE_TYPE, 0xFFFFFFFF)
        self.assertEqual(cast.NO_CLINE_TYPE, 4294967295)


class HalvesTests(unittest.TestCase):

    def test_the_two_scene_ids_are_read_from_their_owners(self):
        """This module must not carry its own copy of either number."""
        self.assertEqual(
            cast.DOOR_SCENE_ID,
            world_m2_sea_destination.DESTINATION_SCENE_N_ID,
        )
        self.assertEqual(
            cast.TRIAL_SCENE_ID, world_m2_survey_plan.XYZ_FRAME_SCENE_ID,
        )

    def test_the_halves_disagree_today_and_the_door_is_the_one_with_no_cast(
        self,
    ):
        self.assertFalse(cast.halves_agree())
        self.assertFalse(
            cast.cast_capacity(cast.DOOR_SCENE_ID).can_carry_a_cast
        )
        self.assertTrue(
            cast.cast_capacity(cast.TRIAL_SCENE_ID).can_carry_a_cast
        )

    def test_the_eight_of_eight_answer_is_derived_not_asserted(self):
        self.assertTrue(cast.every_ship_destination_refuses_a_cast())


class ConsoleLineTests(unittest.TestCase):

    def test_line_is_ascii_and_greppable(self):
        line = cast.sea_scene_cast_console_line()
        line.encode("ascii")
        self.assertTrue(line.startswith("M2_SEA_CAST "))
        self.assertIn("halves_agree=NO", line)
        self.assertIn("ship_destinations_refusing_a_cast=8/8", line)
        self.assertIn("door_verdict=NO_CAST_POSSIBLE_NO_CLINE_TYPE", line)
        self.assertIn("trial_composer=bg3001_roster", line)
        self.assertEqual(line, line.strip())
        self.assertNotIn("\n", line)

    def test_safe_wrapper_never_raises_and_names_the_failure(self):
        original = cast.cast_capacity
        try:
            def boom(_scene_id):
                raise RuntimeError("measured failure")
            cast.cast_capacity = boom
            line = cast.sea_scene_cast_console_line_safe()
        finally:
            cast.cast_capacity = original
        self.assertEqual(
            line, "M2_SEA_CAST unmeasured reason=RuntimeError",
        )

    def test_unmeasured_scene_reports_rather_than_raising(self):
        row = cast.cast_capacity(4242)
        self.assertEqual(row.verdict, cast.VERDICT_NOT_MEASURED)
        self.assertFalse(row.can_carry_a_cast)

    def test_a_composer_table_that_will_not_answer_degrades_to_none(self):
        original = world_scene_travel.CENSUS_SOURCES
        try:
            class Hostile:
                def get(self, _key):
                    raise RuntimeError("no table today")
            world_scene_travel.CENSUS_SOURCES = Hostile()
            row = cast.cast_capacity(126)
        finally:
            world_scene_travel.CENSUS_SOURCES = original
        self.assertIsNone(row.composer_source)
        self.assertEqual(row.verdict, cast.VERDICT_CAST_POSSIBLE_NOT_COMPOSED)


class DispatchReportTests(unittest.TestCase):
    """The line has to actually reach the default path, last."""

    def test_the_crossing_prints_it_and_prints_it_last(self):
        lines = []
        columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append,
        )
        printed = [line for line in lines if isinstance(line, str)]
        self.assertTrue(
            printed[-1].startswith("M2_SEA_CAST "),
            f"last emitted line was {printed[-1]!r}",
        )
        self.assertEqual(
            1, sum(1 for line in printed if line.startswith("M2_SEA_CAST ")),
        )


if __name__ == "__main__":
    unittest.main()
