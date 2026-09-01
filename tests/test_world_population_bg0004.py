"""LANE-A door-priority build: the Bg0004 (Slave Market Island) census
composer.

Same load-bearing shape ``test_world_population_bg0002.py`` already pins for
its own scene: assembled must equal the wire count, the roster must refuse
anywhere but scene 4, and a shortfall must never quietly become "84/84"-style
noise.
"""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import scene4_slave_market_tables as tables
from pirateforce_foundation import world_population_bg0004 as wp4
from pirateforce_foundation.legacy_bridge import load_legacy


class WorldPopulationBg0004Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        # scenarios/world_scene_registry_001.json's own pinned scene-4 spawn
        # (MARKER[4], round ga91m5).  Copied as a plain number, same
        # pure-data-module discipline test_world_population_bg0002.py uses.
        cls.anchor = (-19076.0, 17634.0, 1440.0)

    def test_the_full_roster_assembles_and_the_wire_count_agrees(self):
        generation = wp4.build_bg0004_population(
            self.legacy, self.anchor, scene_id=wp4.SCENE4_N_ID,
            count_source=wp4.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(generation.actor_count, tables.KNOWN_COUNT)
        report = wp4.dispatch_report(generation)
        self.assertEqual(report["assembled_count"], tables.KNOWN_COUNT)
        self.assertEqual(report["wire_actor_count"], tables.KNOWN_COUNT)
        self.assertTrue(report["counts_agree"])
        self.assertTrue(report["bodies_intact"])
        self.assertIsNone(report["shortfall_reason"])

    def test_the_console_line_is_ascii_and_names_the_roster_count(self):
        generation = wp4.build_bg0004_population(
            self.legacy, self.anchor, scene_id=wp4.SCENE4_N_ID,
            count_source=wp4.COUNT_SOURCE_FULL_ROSTER,
        )
        line = wp4.census_console_line(generation)
        line.encode("ascii")
        self.assertIn("assembled=84/84", line)
        self.assertIn("unresolved=32", line)

    def test_actor_lines_carry_the_real_crosswalked_name_and_position(self):
        generation = wp4.build_bg0004_population(
            self.legacy, self.anchor, scene_id=wp4.SCENE4_N_ID,
            count_source=wp4.COUNT_SOURCE_FULL_ROSTER,
        )
        lines = wp4.actor_lines(generation)
        self.assertEqual(len(lines), tables.KNOWN_COUNT)
        joined = "\n".join(lines)
        self.assertIn("Columbus", joined)
        self.assertIn("Angelina", joined)
        for line in lines:
            line.encode("ascii")

    def test_refuses_any_scene_but_four(self):
        with self.assertRaises(wp4.Bg0004CensusError):
            wp4.build_bg0004_population(self.legacy, self.anchor, scene_id=1)
        with self.assertRaises(wp4.Bg0004CensusError):
            wp4.build_bg0004_population(self.legacy, self.anchor, scene_id=2)

    def test_a_smaller_count_still_reports_the_real_shortfall_reason(self):
        generation = wp4.build_bg0004_population(
            self.legacy, self.anchor, 10, scene_id=wp4.SCENE4_N_ID,
            count_source=wp4.COUNT_SOURCE_CALLER,
        )
        report = wp4.dispatch_report(generation)
        self.assertEqual(report["assembled_count"], 10)
        self.assertEqual(report["shortfall_reason"], "caller_requested=10")

    def test_nearest_first_ordering_puts_the_anchor_adjacent_actor_first(self):
        # Anchored at the pinned scene-4 spawn, placement 81 (Salahuddin) is
        # the nearest known placement to it (measured, not assumed).
        generation = wp4.build_bg0004_population(
            self.legacy, self.anchor, 1, scene_id=wp4.SCENE4_N_ID,
        )
        self.assertEqual(generation.placement_indices, (81,))
        self.assertEqual(generation.display_names, ("Salahuddin",))

    def test_scene_and_census_lines_include_the_world_scene_line(self):
        lines = wp4.scene_and_census_console_lines(self.legacy, self.anchor)
        self.assertTrue(lines[0].startswith("WORLD_SCENE scene_id=4"))
        self.assertIn("model=BG0004", lines[0])
        self.assertTrue(lines[1].startswith("WORLD_CENSUS assembled=84/84"))
        self.assertEqual(len(lines), 2 + tables.KNOWN_COUNT)
        for line in lines:
            line.encode("ascii")

    def test_wire_constants_are_carried_from_world_population_not_redefined(self):
        from pirateforce_foundation import world_population
        self.assertIs(wp4.WIRE_HEADER_BYTES, world_population.WIRE_HEADER_BYTES)
        self.assertIs(wp4.COLLECTION_TAG, world_population.COLLECTION_TAG)
        self.assertIs(wp4.INITIAL_REAPPLY_MS, world_population.INITIAL_REAPPLY_MS)

    def test_heading_cycles_the_same_four_values_bg0001_sends_not_a_constant(self):
        from pirateforce_foundation import world_population

        seen_headings = {}

        class HeadingSpyLegacy:
            def __getattr__(self, name):
                return getattr(WorldPopulationBg0004Tests.legacy, name)

            def make_remote_movement_attr(self, actor_identity, x, y, z,
                                           heading, mask=None):
                seen_headings[actor_identity] = heading
                return WorldPopulationBg0004Tests.legacy.make_remote_movement_attr(
                    actor_identity, x, y, z, heading, mask=mask,
                )

        generation = wp4.build_bg0004_population(
            HeadingSpyLegacy(), self.anchor, scene_id=wp4.SCENE4_N_ID,
            count_source=wp4.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(len(seen_headings), tables.KNOWN_COUNT)
        self.assertGreater(len(set(seen_headings.values())), 1)
        placements = {p.placement_index: p for p in tables.load_known_placements()}
        for index in generation.placement_indices:
            placement = placements[index]
            expected = world_population.HEADINGS[placement.placement_index & 3]
            self.assertEqual(
                seen_headings[placement.actor_identity], expected,
            )

    def test_an_empty_actor_entry_would_be_refused(self):
        class BrokenLegacy:
            def __getattr__(self, name):
                return getattr(WorldPopulationBg0004Tests.legacy, name)

            def make_remote_actor_entry(self, *args, **kwargs):
                return b""

        with self.assertRaises(wp4.Bg0004CensusError):
            wp4.build_bg0004_population(
                BrokenLegacy(), self.anchor, 1, scene_id=wp4.SCENE4_N_ID,
            )


if __name__ == "__main__":
    unittest.main()
