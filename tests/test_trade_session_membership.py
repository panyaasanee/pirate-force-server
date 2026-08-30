"""RE-157 Job 1 predicate, offline.  Pins ``trade_session_membership.
admits()``'s fail-closed contract before any ``runtime.py`` call site
exists -- see that module's own CORE-REQUEST for the still-unwired call.
No socket, no client, no ``legacy_bridge`` load: the predicate is pure, so
this file drives it directly, the same way
``tests/test_mob_combat_membership.py`` drives its sibling predicate before
its own wiring test exists.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    trade_session_membership as membership,
)


class TradeSessionMembershipTests(unittest.TestCase):
    # ----- fail closed on a missing record ---------------------------------

    def test_no_store_ever_opened_refuses(self):
        self.assertFalse(membership.admits(
            None, scene_id=2, actor_identity=0x3010, generation=1,
        ))

    # ----- the one admitting shape ------------------------------------------

    def test_exact_match_on_scene_actor_and_generation_admits(self):
        session = membership.build_session(2, 0x3010, 7)
        self.assertTrue(membership.admits(
            session, scene_id=2, actor_identity=0x3010, generation=7,
        ))

    # ----- each field refuses independently ---------------------------------

    def test_scene_mismatch_refuses(self):
        session = membership.build_session(2, 0x3010, 7)
        self.assertFalse(membership.admits(
            session, scene_id=14, actor_identity=0x3010, generation=7,
        ))

    def test_generation_mismatch_refuses_even_for_the_owning_actor(self):
        session = membership.build_session(2, 0x3010, 7)
        self.assertFalse(membership.admits(
            session, scene_id=2, actor_identity=0x3010, generation=8,
        ))

    def test_different_actor_than_the_one_that_opened_the_store_refuses(self):
        session = membership.build_session(2, 0x3010, 7)
        self.assertFalse(membership.admits(
            session, scene_id=2, actor_identity=0x3099, generation=7,
        ))

    # ----- a fresh open always replaces, never merges -----------------------

    def test_a_second_build_session_never_admits_the_prior_sessions_actor(
        self,
    ):
        # Pins that the module holds no state of its own: `admits()` only
        # ever sees whatever single record the caller passes in, so a
        # second `build_session()` call cannot leave the first one's actor
        # still admissible through some hidden accumulation.
        stale = membership.build_session(2, 0x3010, 7)
        fresh = membership.build_session(2, 0x3099, 8)
        self.assertFalse(membership.admits(
            fresh, scene_id=2, actor_identity=stale.actor_identity,
            generation=stale.generation,
        ))

    def test_generation_may_be_any_equality_comparable_value(self):
        # RE-157 leaves open whether this shares a generation counter with
        # the mob-combat guard; this module promises only `==`, not int.
        session = membership.build_session(2, 0x3010, "gen-abc")
        self.assertTrue(membership.admits(
            session, scene_id=2, actor_identity=0x3010, generation="gen-abc",
        ))
        self.assertFalse(membership.admits(
            session, scene_id=2, actor_identity=0x3010, generation="gen-xyz",
        ))

    def test_actor_identity_zero_is_a_real_value_not_a_sentinel(self):
        # Guards against a future caller treating 0 as "no actor" and
        # skipping the equality check -- this module never special-cases it.
        session = membership.build_session(2, 0, 7)
        self.assertTrue(membership.admits(
            session, scene_id=2, actor_identity=0, generation=7,
        ))


if __name__ == "__main__":
    unittest.main()
