"""LANE-A's own half of chief's quest/shop code-name guard.

WHY THIS FILE EXISTS
--------------------
`tests/test_npc_interaction_wire.py`'s `QuestAndShopStateGuardTests` scans
`glob("*.py")` at the TOP LEVEL of `src/pirateforce_foundation/` only -- it
says so itself, and pins the gap with
`test_the_unscanned_subpackages_are_named_and_counted`.  Chief measured the
subpackages out-of-gate in round `t7bsfx`/R342 and wrote to each lane with
its own hits (`pf_bridge/notes_to_chief/20260904_2016_FROM-CHIEF-TO-LANE-A-
quest-shop-guard-recursive-hitlist-two-modules.md`, ADDRESSEE: LANE-A):
two modules, three symbols, deadline 2026-09-05 03:21, at which point chief
flips that glob to recursive and anything left is RED IN THIS LANE'S ZONE,
not chief's.

Two of the three are renamed in the same round as this file
(`vendor_trigger_idx` / `mission_actor_idx` in `lane_a_choose_npc_scene1`).
The third is the imported module name `columbus_quest_dispatch` and cannot
be renamed from here at all -- any import binds that token as code -- so it
is named below as this lane's one expected hit and requested from chief as
a per-symbol exemption (the same shape chief already granted
`world_m2_columbus_trigger_readiness.py`, which imports the same module for
the same kind of pass-through read).

THE RULE THIS ENFORCES, AND WHAT IT DOES NOT SAY.  It borrows chief's
helpers rather than re-implementing them, deliberately: a private copy of
the matcher would drift from the gate's copy and this test would go on
passing while the gate went red.  A green run here says "no LANE-A hook
module binds a quest/shop code name that this lane has not read", exactly
the sentence chief's top-level guard makes about top-level modules.  It
says nothing about behaviour: this lane implements no quest and no shop,
and no word list could prove that either way.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_npc_interaction_wire import guard_hits_in_module  # noqa: E402

LANE_HOOKS = ROOT / "src" / "pirateforce_foundation" / "lane_hooks"

# Every LANE-A hook module, by prefix -- computed, never a hardcoded list, so
# a hook added next round is scanned without anyone remembering to edit this.
LANE_A_PREFIX = "lane_a_"

# The one hit this lane expects, per module.  An imported module name that
# this lane reads ONE integer out of (`COLUMBUS_PLACEMENT_INDEX`, in
# `_scenes_where_columbus_collides`), and which the guard's own exemption
# table already allows under exactly this reasoning for two other files.
EXPECTED_HITS = {
    "lane_a_choose_npc_roster_scenes.py": {"columbus_quest_dispatch"},
}


class LaneAHookModulesAreGuardClean(unittest.TestCase):
    def test_no_lane_a_hook_binds_an_unread_quest_or_shop_code_name(self):
        modules = sorted(
            path for path in LANE_HOOKS.glob(f"{LANE_A_PREFIX}*.py")
        )
        self.assertTrue(modules, "no LANE-A hook modules found to scan")
        for path in modules:
            with self.subTest(module=path.name):
                found = set()
                for symbols in guard_hits_in_module(
                    path.read_text(encoding="utf-8")
                ).values():
                    found |= symbols
                self.assertEqual(
                    sorted(found - EXPECTED_HITS.get(path.name, set())),
                    [],
                    "a quest/shop code name nobody has read -- rename it "
                    "(chief's rule: an exemption is never granted to make a "
                    "red run green)",
                )

    def test_every_expected_hit_is_still_a_real_name_in_that_module(self):
        """The mirror image, so this file cannot rot into a wish list.

        An expected hit that no longer matches anything is a stale allowance,
        and the next real one would slip in behind it.
        """
        for name, expected in EXPECTED_HITS.items():
            path = LANE_HOOKS / name
            with self.subTest(module=name):
                self.assertTrue(path.exists(), "expected hit names a dead module")
                live = set()
                for symbols in guard_hits_in_module(
                    path.read_text(encoding="utf-8")
                ).values():
                    live |= symbols
                self.assertEqual(
                    sorted(expected - live),
                    [],
                    "expected hit no longer matches any code name here",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
