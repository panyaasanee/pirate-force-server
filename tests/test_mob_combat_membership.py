"""RE-157 Job 2 predicate, offline.  Pins ``mob_combat_membership.admits()``'s
fail-closed contract before any ``runtime.py`` call site exists -- see that
module's own CORE-REQUEST for the still-unwired call.  No socket, no client,
no ``legacy_bridge`` load: the predicate is pure, so this file drives it
directly, the same way ``tests/test_mob_combat.py`` drives
``mob_combat.check_attack_cadence`` before its own wiring test exists.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    mob_combat_membership as membership,
)


class MobCombatMembershipTests(unittest.TestCase):
    # ----- fail closed on a missing record ---------------------------------

    def test_no_membership_ever_committed_refuses(self):
        self.assertFalse(membership.admits(
            None, scene_id=2, actor_identity=0x2058, generation=1,
        ))

    # ----- the one admitting shape ------------------------------------------

    def test_exact_match_on_scene_actor_and_generation_admits(self):
        record = membership.build_membership(2, (0x2058, 0x2051), 7)
        self.assertTrue(membership.admits(
            record, scene_id=2, actor_identity=0x2058, generation=7,
        ))

    # ----- each field refuses independently ---------------------------------

    def test_scene_mismatch_refuses(self):
        record = membership.build_membership(2, (0x2058,), 7)
        self.assertFalse(membership.admits(
            record, scene_id=14, actor_identity=0x2058, generation=7,
        ))

    def test_generation_mismatch_refuses_even_for_a_once_announced_actor(
        self,
    ):
        record = membership.build_membership(2, (0x2058,), 7)
        self.assertFalse(membership.admits(
            record, scene_id=2, actor_identity=0x2058, generation=8,
        ))

    def test_actor_never_announced_refuses(self):
        record = membership.build_membership(2, (0x2058,), 7)
        self.assertFalse(membership.admits(
            record, scene_id=2, actor_identity=0x2051, generation=7,
        ))

    def test_empty_announced_set_refuses_everything(self):
        record = membership.build_membership(2, (), 7)
        self.assertFalse(membership.admits(
            record, scene_id=2, actor_identity=0x2058, generation=7,
        ))

    # ----- record construction is a real freeze, not a view -----------------

    def test_a_mutable_source_iterable_cannot_change_a_built_record(self):
        source = [0x2058]
        record = membership.build_membership(2, source, 7)
        source.append(0x2051)  # must not leak into `record` after the fact
        self.assertFalse(membership.admits(
            record, scene_id=2, actor_identity=0x2051, generation=7,
        ))

    def test_duplicate_identities_in_the_source_collapse_but_still_admit(
        self,
    ):
        record = membership.build_membership(2, (0x2058, 0x2058, 0x2051), 7)
        self.assertEqual(len(record.actor_identities), 2)
        self.assertTrue(membership.admits(
            record, scene_id=2, actor_identity=0x2058, generation=7,
        ))

    def test_generation_may_be_any_equality_comparable_value(self):
        # RE-157's two named commit points are two different mechanisms
        # (home vs. lane census); this module promises only `==`, not int.
        record = membership.build_membership(2, (0x2058,), "gen-abc")
        self.assertTrue(membership.admits(
            record, scene_id=2, actor_identity=0x2058, generation="gen-abc",
        ))
        self.assertFalse(membership.admits(
            record, scene_id=2, actor_identity=0x2058, generation="gen-xyz",
        ))


if __name__ == "__main__":
    unittest.main()
