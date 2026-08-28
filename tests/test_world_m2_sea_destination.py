"""Tests for ``world_m2_sea_destination``.

The module ships no wire bytes, so what is worth testing is what it can get
wrong: naming the wrong scene as the destination (which its own first draft
did), drifting from the module that actually sends the option, keying the
CLINE table the way the shipped scene-14 module keys it, and claiming a door
is open when nothing behind it is pinned.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch
from pirateforce_foundation import world_bg0015_identity
from pirateforce_foundation import world_m2_sea_destination as sea


class DestinationTests(unittest.TestCase):
    def test_the_target_is_the_ship_scene_the_row_itself_names(self):
        self.assertEqual(sea.DESTINATION_SCENE_N_ID, 17)
        self.assertEqual(sea.DESTINATION_SCENE_MODEL_ID, "Bg1001")
        self.assertEqual(
            sea.OPTION_TARGET_SCENE_N_ID[sea.DESTINATION_QUEST_ID], 17,
        )

    def test_it_does_not_drift_from_the_module_that_sends_the_option(self):
        # The defect this test exists for: two modules in src/ asserting
        # different destinations for the same option, with nothing failing.
        self.assertEqual(
            sea.DESTINATION_QUEST_ID, columbus_quest_dispatch.COLUMBUS_QUEST_ID,
        )
        self.assertEqual(
            sea.DESTINATION_SCENE_N_ID,
            columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID,
            "the dispatch lane and this pin must name ONE destination for "
            "this option; if they differ the tree contradicts itself in a "
            "console line an operator has to choose between",
        )

    def test_the_advertised_ocean_is_not_the_destination(self):
        self.assertEqual(sea.ADVERTISED_OCEAN_SCENE_N_ID, 126)
        self.assertNotEqual(
            sea.ADVERTISED_OCEAN_SCENE_N_ID, sea.DESTINATION_SCENE_N_ID,
            "reading the advertised name as a route is the error this "
            "module was rewritten to record, not to repeat",
        )

    def test_three_islands_advertise_one_ocean_and_go_three_ways(self):
        # The asymmetry that refutes "126 is the destination": if it were,
        # 3021/3022/3023 would be indistinguishable.
        rising_sun = [r for r in sea.COLUMBUS_ROUTES if r[4] == 126]
        self.assertEqual(len(rising_sun), 3)
        self.assertEqual(len({r[3] for r in rising_sun}), 3)
        self.assertEqual(len({r[2] for r in rising_sun}), 3)

    def test_port_royals_columbus_routes_the_way_the_dispatch_lane_sends(self):
        home, row, target, ocean = sea.route_for(156)
        self.assertEqual(home, 1)
        self.assertEqual(row, columbus_quest_dispatch.COLUMBUS_QUEST_ID)
        self.assertEqual(target, columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID)
        self.assertEqual(ocean, 126)

    def test_an_unknown_columbus_is_refused_not_guessed(self):
        self.assertIsNone(sea.route_for(999999))

    def test_the_door_is_shut_and_the_reason_is_the_measured_one(self):
        self.assertFalse(sea.destination_ready())
        reason = sea.refusal_reason()
        self.assertIn("no pinned arrival position", reason)
        self.assertIn("RE-103", reason)
        self.assertNotIn(
            "not in the cloud clone", reason,
            "the .npc digest IS in this tree; that was the wrong reason and "
            "it would send a later round to ask for a file it already has",
        )

    def test_the_console_line_is_ascii_and_names_both_scenes(self):
        line = sea.console_line()
        line.encode("ascii")   # raises if a non-ASCII character creeps in
        line.encode("cp874")   # the bridge console's own encoding
        self.assertIn("target_scene=17", line)
        self.assertIn("advertises_ocean=126", line)
        self.assertIn("state=REFUSED", line)


class CrosswalkKeyRuleTests(unittest.TestCase):
    def test_the_key_is_a_column_not_a_row_id_or_a_position(self):
        self.assertEqual(
            sea.cline_key(14, 111),
            (("n_CLINE_TYPE", 14), ("n_CREATURE_TYPE", 111)),
        )

    def test_the_rule_covers_every_set_number_scene_14_actually_ships(self):
        # The test that caught the ordinal misreading: scene 14 ships Mob-Set
        # 111 out of a block of 51 rows, so a rule that treats the set number
        # as a position into the block refuses a placement on the wire today.
        for placement in world_bg0015_identity.shippable_placements():
            sea.cline_key(14, placement.template_id)

    def test_scene_14_really_does_ship_a_set_past_its_block_length(self):
        highest = max(
            p.template_id
            for p in world_bg0015_identity.shippable_placements()
        )
        _base, count, _lowest, _highest = sea.CLINE_BLOCKS[14]
        self.assertGreater(
            highest, count,
            "if scene 14 ever stops shipping a set number past its block "
            "length, this module's warning has lost its only witness",
        )

    def test_a_set_number_outside_the_measured_key_range_is_refused(self):
        with self.assertRaises(sea.SeaDestinationError):
            sea.cline_key(14, 116)   # keys measured 1..115
        with self.assertRaises(sea.SeaDestinationError):
            sea.cline_key(3001, 57)  # keys measured 1..56
        with self.assertRaises(sea.SeaDestinationError):
            sea.cline_key(14, 0)

    def test_an_unmeasured_cline_type_is_refused(self):
        with self.assertRaises(sea.SeaDestinationError):
            sea.cline_key(3002, 1)


class FeasibilityCountTests(unittest.TestCase):
    def test_the_two_variant_rows_are_resolving_rows_not_a_drop(self):
        # The corrected count.  An earlier draft reported 31 of 38 by
        # treating these six as unresolvable; both of their legs resolve.
        self.assertEqual(sea.RESOLVING_PLACEMENT_COUNT, 37)
        self.assertLessEqual(
            sea.TWO_VARIANT_PLACEMENT_COUNT, sea.RESOLVING_PLACEMENT_COUNT,
        )
        self.assertEqual(
            sea.RESOLVING_PLACEMENT_COUNT + sea.EMPTY_LEADER_PLACEMENT_COUNT,
            sea.PLACEMENT_COUNT,
        )

    def test_the_two_variant_shape_is_not_claimed_to_be_rare(self):
        placements, scenes = sea.TWO_VARIANT_SHAPE_TREE_WIDE
        self.assertGreater(placements, sea.PLACEMENT_COUNT)
        self.assertGreater(scenes, 1)


if __name__ == "__main__":
    unittest.main()
