"""The vendored 160-name API census matches the LANE-Q charter's own numbers.

prompts/LANE-Q.md (pf_bridge) states the census by hand: 160 names across 8
namespaces, Player 73 / Quest 25 / Trigger 17 / Party 11 / Mob 10 /
Instance 9 / Guild 8 / Scene 7, 12,653 call sites total.  This module reads
those numbers from ``lua_api/api_spec.tsv`` (see that file's own docstring
for provenance) instead of typing them a second time, so a re-vendor that
silently drops or duplicates a row fails here on every machine, no sibling
checkout required.
"""
import unittest
from pathlib import Path

from pirateforce_foundation.lua_api import spec

CHARTER_NAMESPACE_COUNTS = {
    "Player": 73,
    "Quest": 25,
    "Trigger": 17,
    "Party": 11,
    "Mob": 10,
    "Instance": 9,
    "Guild": 8,
    "Scene": 7,
}


class ApiSpecMatchesTheCharterTests(unittest.TestCase):
    def test_total_function_count_is_160(self):
        self.assertEqual(len(spec.API_FUNCTIONS), 160)

    def test_eight_namespaces_named_by_the_charter(self):
        self.assertEqual(set(spec.NAMESPACES), set(CHARTER_NAMESPACE_COUNTS))

    def test_each_namespace_method_count_matches_the_charter(self):
        for namespace, expected in CHARTER_NAMESPACE_COUNTS.items():
            with self.subTest(namespace=namespace):
                self.assertEqual(
                    len(spec.NAMESPACE_METHODS[namespace]), expected,
                    "namespace %r drifted from the charter's %d" % (namespace, expected),
                )

    def test_total_call_sites_is_12653(self):
        total = sum(fn.call_count for fn in spec.API_FUNCTIONS)
        self.assertEqual(total, 12653)

    def test_no_duplicate_qualified_names(self):
        names = [fn.qualified_name for fn in spec.API_FUNCTIONS]
        self.assertEqual(len(names), len(set(names)))

    def test_by_qualified_name_lookup_agrees_with_the_tuple(self):
        self.assertEqual(len(spec.BY_QUALIFIED_NAME), len(spec.API_FUNCTIONS))
        for fn in spec.API_FUNCTIONS:
            self.assertIs(spec.BY_QUALIFIED_NAME[fn.qualified_name], fn)

    def test_the_twenty_busiest_names_named_in_the_charter_are_present(self):
        # A sample from PF_LUA_API_SPEC.md's own "20 most-called" table -
        # not the whole 20, just enough that a rename or drop is caught.
        for qualified, expected_calls in (
            ("Player.MobAppear", 3532),
            ("Player.AddItem", 1430),
            ("Quest.RewardItemSelect", 1335),
            ("Mob.ShowAnimation", 716),
            ("Trigger.NextStatus", 353),
            ("Trigger.GetTriggerStatus", 134),
        ):
            with self.subTest(qualified=qualified):
                fn = spec.BY_QUALIFIED_NAME[qualified]
                self.assertEqual(fn.call_count, expected_calls)

    def test_vendored_tsv_is_ascii_only(self):
        # Bridge console is code page 874; this file must never carry a byte
        # that breaks it.
        raw = Path(spec._SPEC_PATH).read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail("api_spec.tsv is not ASCII-only: %s" % exc)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
