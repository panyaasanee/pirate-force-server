"""LANE-DB: the `RE-305` precondition probe keeps saying what it says.

`tools/pf_backpack_attr_headless_replay.py` produces the `HEADLESS_PROOF:`
token `COO-DECISION 20260907_2148` requires for `RE-305`: the StartGame
reply the server sends carries a BackpackAttr, and that bag holds the
template the attended tester is told to drag.  A token that quietly stops
being true is worse than no token, because `ka1-A` re-runs it before the
boot and cuts the ticket when it does not match (`PANYA-ORDER
20260907_0159`).  This file is what turns that drift red HERE, in the
suite, instead of on the owner's machine at boot time.

WHAT IT DOES NOT DO.  It does not assert the four template ids as
literals.  The starting bag is `inventory.INITIAL_BACKPACK`, which is not
this lane's to freeze, and a hard-coded list here would go red for the
RIGHT reason (the bag changed) with the WRONG message (this test's own
numbers).  What is pinned is the PROPERTY the ticket depends on: the bag
the login loads is the bag the frame carries, and the class-1 right hand
named by `CHARCREATE_CLASS.n_SLOT_RHAND` is in it.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import pf_backpack_attr_headless_replay as probe  # noqa: E402

def _class_one_right_hand() -> int:
    """`class_id 1 -> n_SLOT_RHAND`, taken from the ONE crosswalk this lane
    already builds (`persistence_class_id.CLASS_PRESETS`, under
    `class_catalog.SOURCE_SHA256`) rather than from a second read of a
    gamedata table.  `lane_hooks/lane_db_item_operate_op5.py` derives the
    same column the same way and says why: a duplicated predicate is a
    predicate that will drift (pf-adversary `D7`, round `5vzis0`).
    """
    from pirateforce_foundation.persistence_class_id import CLASS_PRESETS

    return {row[0]: row[3] for row in CLASS_PRESETS}[1]


class BackpackAttrProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = probe.run()

    def test_the_composed_bag_is_actually_in_the_frame_the_client_parses(self):
        """The sentence "the server SENDS them", checked rather than
        argued: a composer that can build the bytes proves nothing until
        the bytes are inside the StartGame reply."""
        self.assertTrue(self.result["in_start_game_frame"])
        self.assertEqual(self.result["occurrences_in_start_game_frame"], 1)

    def test_the_byte_walk_agrees_with_the_rows_the_login_loaded(self):
        """The walker in the probe does not import the composer's helpers,
        so this is two independent readings of the same bytes agreeing --
        not the composer agreeing with itself."""
        self.assertTrue(self.result["walk_agrees_with_rows"])
        self.assertEqual(
            self.result["templates_walked_from_the_wire"],
            self.result["templates_in_the_loaded_rows"],
        )
        self.assertTrue(self.result["templates_walked_from_the_wire"])

    def test_nothing_in_the_starting_bag_is_worn_yet(self):
        """`RE-280`: `ItemAttr+0x39 == 0xFF` is "not worn".  The attended
        tester is asked to DRAG an item onto a slot, so a starting bag
        where something is already worn would change what the ticket
        measures.  0xFF across the bag is the precondition, and it is read
        off the wire rather than assumed."""
        self.assertEqual(
            set(self.result["worn_bytes_raw_u8_39"]), {0xFF}
        )

    def test_the_class_one_right_hand_is_in_the_bag(self):
        """The item `RE-305` step (a) tells the tester to drag.  No skip
        and no bridge file: the number comes from this repository's own
        `CLASS_PRESETS`, so the cloud clone and the bridge measure the
        same thing."""
        self.assertIn(
            _class_one_right_hand(),
            self.result["templates_walked_from_the_wire"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
