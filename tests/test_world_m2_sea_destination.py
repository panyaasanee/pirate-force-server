"""Tests for ``world_m2_sea_destination`` - the M2 destination pin.

The module ships no wire bytes, so what is worth testing is the two things
it CAN get wrong: keying the CLINE table the way the shipped scene-14 module
keys it, and claiming a door is open when nothing behind it is pinned.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg0015_identity
from pirateforce_foundation import world_m2_sea_destination as sea


class DestinationTests(unittest.TestCase):
    def test_the_destination_is_scene_126_and_the_vehicle_is_scene_17(self):
        self.assertEqual(sea.DESTINATION_SCENE_N_ID, 126)
        self.assertEqual(sea.DESTINATION_SCENE_MODEL_ID, "Bg3001")
        self.assertEqual(sea.VEHICLE_SCENE_N_ID, 17)
        self.assertEqual(sea.VEHICLE_SCENE_MODEL_ID, "Bg1001")

    def test_the_quest_this_lane_already_sends_is_the_one_that_names_it(self):
        from pirateforce_foundation import columbus_quest_dispatch
        self.assertEqual(
            sea.DESTINATION_QUEST_ID, columbus_quest_dispatch.COLUMBUS_QUEST_ID,
            "the destination is pinned off the quest this server already "
            "sends as conversation entry one - if they drift, the pin is "
            "about a quest nobody sends",
        )

    def test_the_option_target_column_is_controlled_by_a_second_row(self):
        # n_VARI_2 is read as a scene id.  The control is the OTHER option on
        # the same screen: row 3205's n_VARI_2 is 1, and scene 1 is Port
        # Royal, which is what 3205's own title says.  Without that second
        # row, "n_VARI_2 17 means scene 17" would be a one-row coincidence.
        self.assertEqual(sea.OPTION_TARGET_SCENE_N_ID[3205], 1)
        self.assertEqual(
            sea.OPTION_TARGET_SCENE_N_ID[sea.DESTINATION_QUEST_ID],
            sea.VEHICLE_SCENE_N_ID,
            "option 1's own script parameter names the ship, not the sea map "
            "its title advertises - that split IS this module's finding",
        )

    def test_the_module_does_not_claim_the_advertised_name_is_the_target(self):
        self.assertNotEqual(
            sea.OPTION_TARGET_SCENE_N_ID[sea.DESTINATION_QUEST_ID],
            sea.DESTINATION_SCENE_N_ID,
            "if these ever become equal the docstring's whole ship-vs-sea-map "
            "reading has to be rewritten, not quietly kept",
        )

    def test_the_door_is_shut_and_says_why(self):
        self.assertFalse(sea.destination_ready())
        self.assertIn("no pinned spawn position", sea.refusal_reason())

    def test_the_console_line_is_ascii_and_names_the_state(self):
        line = sea.console_line()
        line.encode("ascii")  # raises if a non-ASCII character ever creeps in
        line.encode("cp874")  # the bridge console's own encoding
        self.assertIn("M2_SEA_DESTINATION", line)
        self.assertIn("scene=126", line)
        self.assertIn("state=REFUSED", line)


class CrosswalkKeyRuleTests(unittest.TestCase):
    def test_the_key_is_a_column_not_a_row_id_or_a_position(self):
        self.assertEqual(
            sea.cline_key(14, 111),
            (("n_CLINE_TYPE", 14), ("n_CREATURE_TYPE", 111)),
        )

    def test_the_rule_covers_every_set_number_scene_14_actually_ships(self):
        # This is the test that caught the ordinal misreading: scene 14 ships
        # Mob-Set 111 out of a block of 51 rows, so any rule that treats the
        # set number as a position into the block refuses a placement that is
        # on the wire today.
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

    def test_the_scene_126_counts_account_for_every_placement(self):
        self.assertEqual(
            sea.RESOLVING_PLACEMENT_COUNT
            + sea.MULTI_SET_PLACEMENT_COUNT
            + sea.EMPTY_LEADER_PLACEMENT_COUNT,
            sea.PLACEMENT_COUNT,
        )
        self.assertLess(
            sea.RESOLVING_PLACEMENT_COUNT, sea.PLACEMENT_COUNT,
            "the drops are the point: a module that claimed 38 of 38 would "
            "be hiding the 53|54 shape nothing here can read yet",
        )


if __name__ == "__main__":
    unittest.main()
