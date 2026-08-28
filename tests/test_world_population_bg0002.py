"""LANE-A M1-P: the Bg0002 (Prison Exile Island) census composer.

The load-bearing tests here are the ones that keep BUILD-001's own rule
alive for a second scene: assembled must equal the wire count, the roster
must refuse anywhere but scene 2, and a shortfall must never quietly become
"115/115"-style (or here, "97/97"-style) noise.
"""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import scene2_prison_exile_tables as tables
from pirateforce_foundation import world_population_bg0002 as wp2
from pirateforce_foundation.legacy_bridge import load_legacy


class WorldPopulationBg0002Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.anchor = (
            tables.SCENE2_REGISTRY_SPAWN_X, tables.SCENE2_REGISTRY_SPAWN_Y, 1680.0,
        )

    def test_the_full_roster_assembles_and_the_wire_count_agrees(self):
        generation = wp2.build_bg0002_population(
            self.legacy, self.anchor, scene_id=wp2.SCENE2_N_ID,
            count_source=wp2.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(generation.actor_count, tables.KNOWN_COUNT)
        report = wp2.dispatch_report(generation)
        self.assertEqual(report["assembled_count"], tables.KNOWN_COUNT)
        self.assertEqual(report["wire_actor_count"], tables.KNOWN_COUNT)
        self.assertTrue(report["counts_agree"])
        self.assertTrue(report["bodies_intact"])
        self.assertIsNone(report["shortfall_reason"])

    def test_the_console_line_is_ascii_and_names_the_roster_count(self):
        generation = wp2.build_bg0002_population(
            self.legacy, self.anchor, scene_id=wp2.SCENE2_N_ID,
            count_source=wp2.COUNT_SOURCE_FULL_ROSTER,
        )
        line = wp2.census_console_line(generation)
        line.encode("ascii")
        self.assertIn("assembled=97/97", line)
        self.assertIn("unresolved=9", line)

    def test_actor_lines_carry_the_real_mined_name_and_position(self):
        generation = wp2.build_bg0002_population(
            self.legacy, self.anchor, scene_id=wp2.SCENE2_N_ID,
            count_source=wp2.COUNT_SOURCE_FULL_ROSTER,
        )
        lines = wp2.actor_lines(generation)
        self.assertEqual(len(lines), tables.KNOWN_COUNT)
        joined = "\n".join(lines)
        self.assertIn("Navy Transfer", joined)
        self.assertIn("Veronica", joined)
        for line in lines:
            line.encode("ascii")

    def test_refuses_any_scene_but_two(self):
        with self.assertRaises(wp2.Bg0002CensusError):
            wp2.build_bg0002_population(self.legacy, self.anchor, scene_id=1)
        with self.assertRaises(wp2.Bg0002CensusError):
            wp2.build_bg0002_population(self.legacy, self.anchor, scene_id=278)

    def test_a_smaller_count_still_reports_the_real_shortfall_reason(self):
        generation = wp2.build_bg0002_population(
            self.legacy, self.anchor, 10, scene_id=wp2.SCENE2_N_ID,
            count_source=wp2.COUNT_SOURCE_CALLER,
        )
        report = wp2.dispatch_report(generation)
        self.assertEqual(report["assembled_count"], 10)
        self.assertEqual(report["shortfall_reason"], "caller_requested=10")

    def test_nearest_first_ordering_puts_the_anchor_adjacent_actor_first(self):
        # Anchored at the pinned scene-2 spawn (near the dock), Navy Transfer
        # (placement 0) is the nearest known placement to it.
        generation = wp2.build_bg0002_population(
            self.legacy, self.anchor, 1, scene_id=wp2.SCENE2_N_ID,
        )
        self.assertEqual(generation.placement_indices, (0,))
        self.assertEqual(generation.display_names, ("Navy Transfer",))

    def test_scene_and_census_lines_include_the_world_scene_line(self):
        lines = wp2.scene_and_census_console_lines(self.legacy, self.anchor)
        self.assertTrue(lines[0].startswith("WORLD_SCENE scene_id=2"))
        self.assertIn("model=BG0002", lines[0])
        self.assertTrue(lines[1].startswith("WORLD_CENSUS assembled=97/97"))
        self.assertEqual(len(lines), 2 + tables.KNOWN_COUNT)
        for line in lines:
            line.encode("ascii")

    def test_the_census_line_carries_the_identity_guard_refusal_for_scene_two(self):
        """Scene 2 is the scene actually shipping a roster on an unconfirmed
        premise, so its own boot has to say so.  Asserting on the refusal
        (not merely on the token's presence) is what makes this test go red
        if anyone ever flips scene 2 to provable without owning the change.
        """
        from pirateforce_foundation import world_scene_numbering

        generation = wp2.build_bg0002_population(
            self.legacy, self.anchor, scene_id=wp2.SCENE2_N_ID,
            count_source=wp2.COUNT_SOURCE_FULL_ROSTER,
        )
        line = wp2.census_console_line(generation)
        line.encode("ascii")
        self.assertIn("WORLD_IDENTITY_GUARD", line)
        self.assertIn("identity_provable=0", line)
        self.assertIn(world_scene_numbering.IDENTITY_REFUSED, line)
        # The verdict must be about scene 2, not whatever scene the guard
        # module happens to list first.
        self.assertIn("Bg0002", line)

    def test_the_census_line_still_starts_with_the_prefix_readers_match_on(self):
        """The token was appended rather than spliced in.  Every existing
        reader keys off the ``WORLD_CENSUS `` prefix and the fields before
        the separator, so those must survive this round unchanged.
        """
        generation = wp2.build_bg0002_population(
            self.legacy, self.anchor, scene_id=wp2.SCENE2_N_ID,
            count_source=wp2.COUNT_SOURCE_FULL_ROSTER,
        )
        line = wp2.census_console_line(generation)
        self.assertTrue(line.startswith("WORLD_CENSUS assembled=97/97"))
        head = line.split(" | ")[0]
        self.assertIn("unresolved=9", head)
        self.assertNotIn("WORLD_IDENTITY_GUARD", head)

    def test_the_guard_token_names_the_scene_the_generation_was_built_for(self):
        """Round o8cy9q's adversary finding, ported to scene 2: a token that
        reads a module constant reports that constant even when the census in
        hand belongs to another scene.  Carrying scene_id on the generation is
        what prevents it, so a generation relabelled to scene 1 must produce
        bg0001's verdict - not Bg0002's.
        """
        import dataclasses

        generation = wp2.build_bg0002_population(
            self.legacy, self.anchor, scene_id=wp2.SCENE2_N_ID,
            count_source=wp2.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(generation.scene_id, wp2.SCENE2_N_ID)
        relabelled = dataclasses.replace(generation, scene_id=1)
        self.assertIn("bg0001", wp2.census_console_line(relabelled))

    def test_wire_constants_are_carried_from_world_population_not_redefined(self):
        from pirateforce_foundation import world_population
        self.assertIs(wp2.WIRE_HEADER_BYTES, world_population.WIRE_HEADER_BYTES)
        self.assertIs(wp2.COLLECTION_TAG, world_population.COLLECTION_TAG)
        self.assertIs(wp2.INITIAL_REAPPLY_MS, world_population.INITIAL_REAPPLY_MS)

    def test_heading_cycles_the_same_four_values_bg0001_sends_not_a_constant(self):
        from pirateforce_foundation import world_population

        seen_headings = {}

        class HeadingSpyLegacy:
            def __getattr__(self, name):
                return getattr(WorldPopulationBg0002Tests.legacy, name)

            def make_remote_movement_attr(self, actor_identity, x, y, z,
                                           heading, mask=None):
                seen_headings[actor_identity] = heading
                return WorldPopulationBg0002Tests.legacy.make_remote_movement_attr(
                    actor_identity, x, y, z, heading, mask=mask,
                )

        generation = wp2.build_bg0002_population(
            HeadingSpyLegacy(), self.anchor, scene_id=wp2.SCENE2_N_ID,
            count_source=wp2.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(len(seen_headings), tables.KNOWN_COUNT)
        # Not every actor facing the same way (the bug M1-P found in-game).
        self.assertGreater(len(set(seen_headings.values())), 1)
        # And exactly bg0001's own four-way cycle, keyed the same way
        # (placement_index & 3), not an independently invented set.
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
                return getattr(WorldPopulationBg0002Tests.legacy, name)

            def make_remote_actor_entry(self, *args, **kwargs):
                return b""

        with self.assertRaises(wp2.Bg0002CensusError):
            wp2.build_bg0002_population(
                BrokenLegacy(), self.anchor, 1, scene_id=wp2.SCENE2_N_ID,
            )


if __name__ == "__main__":
    unittest.main()
