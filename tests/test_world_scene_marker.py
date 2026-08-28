"""LANE-A M2: the MARKER crosswalk, and scene 14's arrival point.

The load-bearing tests here are the ones that would go red if the crosswalk
were quietly replaced by the shortcut that looks identical on the 12 scenes
where it happens to agree:

* ``test_the_marker_id_is_not_the_scene_id`` - scene 130 names marker 1000.
  A round that indexes MARKER by scene id passes every other test in this file
  and puts one map's arrival point in another map.
* ``test_a_scene_with_no_marker_answers_none_rather_than_guessing`` - 258 of
  the client's 271 scenes have no authored arrival point, scene 17 among them,
  and None is the table's answer rather than a hole in the reader.
* ``test_the_volcano_island_login_lands_on_the_marker_and_says_so`` - the
  whole point of the round, driven through the real entry path: a character
  row naming scene 14 used to refuse the login outright.
"""

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_entry
from pirateforce_foundation import world_scene_marker
from pirateforce_foundation import world_scene_travel
from pirateforce_foundation.model import Position
from pirateforce_foundation.world_scene_marker import (
    MarkerArrival,
    SceneMarkerError,
    arrival_point,
    console_line,
    scenes_with_an_arrival_point,
)

VOLCANO_SCENE_ID = 14
SEA_SCENE_ID = 17
# The scene-1 row of the same table, kept as a value rather than a lookup so a
# test that reads the module under test cannot agree with itself.
PORT_ROYAL_MARKER = (-10322, -755, 671)
# What this runtime actually stands a fresh character on at home - NOT the
# marker, and the gap is the module's own stated non-corroboration.
V135_HOME_SPAWN = (-9239.95703125, -2830.045166015625, 223.29209899902344)


class MarkerTableTests(unittest.TestCase):

    def test_the_marker_id_is_not_the_scene_id(self):
        scene_130 = arrival_point(130)
        self.assertIsNotNone(scene_130)
        self.assertEqual(scene_130.marker_n_id, 1000)
        self.assertNotEqual(scene_130.marker_n_id, scene_130.scene_n_id)

    def test_every_pinned_marker_points_back_at_the_scene_that_names_it(self):
        for scene_id in scenes_with_an_arrival_point():
            arrival = arrival_point(scene_id)
            self.assertEqual(arrival.marker_row_scene, arrival.scene_n_id)

    def test_no_two_scenes_share_one_marker_row(self):
        marker_ids = [
            arrival_point(scene_id).marker_n_id
            for scene_id in scenes_with_an_arrival_point()
        ]
        self.assertEqual(len(marker_ids), len(set(marker_ids)))

    def test_the_thirteen_scenes_are_the_measured_thirteen(self):
        self.assertEqual(
            scenes_with_an_arrival_point(),
            (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 130),
        )
        self.assertEqual(
            len(scenes_with_an_arrival_point()),
            world_scene_marker.SCENES_WITH_A_MARKER,
        )

    def test_a_scene_with_no_marker_answers_none_rather_than_guessing(self):
        self.assertIsNone(arrival_point(SEA_SCENE_ID))
        self.assertIsNone(arrival_point(278))
        self.assertIsNone(arrival_point(126))

    def test_a_scene_id_that_is_not_an_int_is_refused_not_answered(self):
        for bad in ("14", 14.0, None, True):
            with self.assertRaises(SceneMarkerError):
                arrival_point(bad)

    def test_the_coordinates_are_read_as_signed(self):
        # Read unsigned, scene 1's n_X is 4294956974.  Any future round that
        # drops the two's-complement step gets a point 4.29 billion units out,
        # and this is the row that catches it first.
        self.assertEqual(
            (arrival_point(1).x, arrival_point(1).y, arrival_point(1).z),
            PORT_ROYAL_MARKER,
        )

    def test_home_is_the_non_corroboration_the_module_admits_to(self):
        # If these two ever coincide, the module's docstring is wrong and the
        # claim "one scene agrees exactly and one differs" has to be rewritten
        # rather than quietly kept.
        marker = arrival_point(1)
        self.assertNotEqual(
            (float(marker.x), float(marker.y), float(marker.z)),
            V135_HOME_SPAWN,
        )

    def test_the_console_line_is_ascii_and_names_its_source(self):
        line = console_line(arrival_point(VOLCANO_SCENE_ID))
        self.assertTrue(line.isascii())
        self.assertIn("SCENE_MARKER scene=14 marker=14", line)
        self.assertIn("source=CLIENT_MARKER_TABLE", line)

    def test_the_console_line_refuses_anything_but_an_arrival(self):
        with self.assertRaises(SceneMarkerError):
            console_line((14, 14, 0, 0, 0, 0))

    def test_the_reverification_command_names_both_pinned_hashes(self):
        formula = world_scene_marker.reverify_on_the_bridge()
        self.assertIn(world_scene_marker.MARKER_TSV_SHA256, formula)
        self.assertIn(world_scene_marker.SCENE_NAME_TSV_SHA256, formula)
        self.assertTrue(formula.isascii())


class Scene14RegistryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.registry = world_scene_travel.load_scene_registry()
        cls.target = world_scene_travel.destination(
            VOLCANO_SCENE_ID, cls.registry)

    def test_the_pinned_spawn_is_the_marker_and_not_a_placement(self):
        self.assertEqual(
            world_scene_travel.spawn_position(self.target),
            arrival_point(VOLCANO_SCENE_ID).xyz,
        )
        self.assertIn("CLIENT_MARKER_TABLE", self.target.spawn_provenance)

    def test_the_scene_has_no_pinned_ground_on_purpose(self):
        # With ground pinned from this scene's 91 placements the box would be
        # 40312 x 46416 units and a Port Royal row would be KEPT - see the
        # registry nonclaim.  None is what makes the relocation below fire.
        self.assertIsNone(self.target.ground_extent)

    def test_login_is_allowed_and_persistence_is_not(self):
        self.assertTrue(self.target.login_entry_allowed)
        self.assertFalse(self.target.persist_position_allowed)
        self.assertFalse(
            world_scene_travel.is_position_persist_allowed(
                VOLCANO_SCENE_ID, self.registry)
        )

    def test_the_volcano_island_login_lands_on_the_marker_and_says_so(self):
        lines = []
        entry = world_scene_entry.resolve_entry(
            Position(VOLCANO_SCENE_ID, 0, *V135_HOME_SPAWN, 0.0),
            registry=self.registry,
            emit=lines.append,
        )
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            arrival_point(VOLCANO_SCENE_ID).xyz,
        )
        self.assertTrue(entry.relocated)
        self.assertEqual(
            entry.relocation_reason,
            world_scene_entry.RELOCATED_NO_GROUND_EVIDENCE,
        )
        self.assertTrue(any(line.startswith("WORLD_SCENE ") for line in lines))
        self.assertTrue(
            any(line.startswith("WORLD_SCENE_RELOCATED ") for line in lines))
        for line in lines:
            self.assertTrue(line.isascii())

    def test_the_teleport_and_the_position_cannot_name_two_places(self):
        entry = world_scene_entry.resolve_entry(
            Position(VOLCANO_SCENE_ID, 0, *V135_HOME_SPAWN, 0.0),
            registry=self.registry,
            emit=lambda line: None,
        )
        scene_id, _seq, x, y, z = entry.teleport_fields
        self.assertEqual(scene_id, VOLCANO_SCENE_ID)
        self.assertEqual(
            (x, y, z),
            (entry.position.x, entry.position.y, entry.position.z),
        )

    def test_the_scene_now_reports_the_roster_it_has_had_all_along(self):
        # Before this round the console line read population=none for a scene
        # world_population_bg0015 has composed 81 actors for since round
        # 02k3w5.  This is a report; nothing here sends the roster.
        self.assertEqual(
            world_scene_travel.population_source(VOLCANO_SCENE_ID),
            "bg0015_roster",
        )
        self.assertIn(
            "population=bg0015_roster",
            world_scene_travel.entry_console_line(self.target),
        )

    def test_the_home_census_still_refuses_this_scene(self):
        # The report above must never become a licence: the bg0001 census
        # builder refuses scene 14 whatever any table says.
        from pirateforce_foundation import world_population
        with self.assertRaises(ValueError):
            world_population.build_world_population(
                None, (0.0, 0.0, 0.0), 3, scene_id=VOLCANO_SCENE_ID,
            )


if __name__ == "__main__":
    unittest.main()
