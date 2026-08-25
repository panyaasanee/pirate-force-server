"""LANE-A BUILD-001: the bg0001 census staircase.

The load-bearing test in this file is the first one.  Rung 3 must be BYTE-
IDENTICAL to what the runtime already sends today; if it is not, then a failing
higher rung could be blamed on the encoder instead of on the actor count, and
the whole staircase stops measuring anything.

The second load-bearing test is ``test_the_census_is_thin_everywhere``.  It
pins the measured fact that this table is map-wide and sparse, which is the
reason this module refuses to promise a crowded screen.  If the table ever
becomes dense, that promise can change - loudly, here, not quietly in prose.
"""

import json
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_population
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import (
    AUTHORITATIVE_COUNT,
    build_port_royal_initial_population,
)
from pirateforce_foundation.world_population import (
    CENSUS_COUNT,
    DEFAULT_ACTOR_COUNT,
    INITIAL_REAPPLY_MS,
    SHIPPED_ISOLATED_INDICES,
    STAIRCASE_RUNGS,
    build_staircase,
    build_world_population,
    census_order,
    effective_actor_count,
    nesting_break,
    production_allowed,
    staircase_report,
    test_only,
)


class WorldPopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.anchor = (
            cls.legacy.V134_PLAYER_X,
            cls.legacy.V134_PLAYER_Y,
            cls.legacy.V134_PLAYER_Z,
        )
        cls.spawn = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )
        cls.far = (
            cls.legacy.V112_PLAYER_X,
            cls.legacy.V112_PLAYER_Y,
            cls.legacy.V112_PLAYER_Z,
        )

    # --- the control -----------------------------------------------------

    def test_rung_three_is_byte_identical_to_the_shipped_default(self) -> None:
        shipped_pc, shipped_frame, shipped_rows = (
            self.legacy.make_v112_monster_shop_population_state()
        )
        rung = build_world_population(self.legacy, self.anchor, 3)
        self.assertEqual(rung.pc, shipped_pc)
        self.assertEqual(rung.frame, shipped_frame)
        self.assertEqual(rung.indices, tuple(row[0] for row in shipped_rows))
        self.assertEqual(rung.indices, SHIPPED_ISOLATED_INDICES)
        # The v141 self-test pins this same frame at 504/517 (v141:6104-6107).
        self.assertEqual((rung.pc_bytes, rung.frame_bytes), (504, 517))

    def test_the_control_rung_is_anchor_invariant(self) -> None:
        """Which is what makes it a control - and also its only limitation."""
        first = build_world_population(self.legacy, self.anchor, 3)
        for other in (self.spawn, self.far, (0.0, 0.0, 0.0)):
            self.assertEqual(build_world_population(self.legacy, other, 3).pc, first.pc)

    # --- the honesty pin -------------------------------------------------

    def test_the_census_is_thin_everywhere(self) -> None:
        """Sending 115 does not crowd a view; this is why the module says so."""
        placements = census_order(self.legacy, self.spawn)
        x, y, z = self.spawn
        distances = sorted(
            ((item.x - x) ** 2 + (item.y - y) ** 2 + (item.z - z) ** 2) ** 0.5
            for item in placements
        )
        self.assertLessEqual(sum(1 for d in distances if d < 2000.0), 2)
        self.assertGreater(distances[AUTHORITATIVE_COUNT - 1], 10000.0)
        self.assertGreater(distances[-1], 35000.0)

    # --- the staircase ---------------------------------------------------

    def test_every_rung_is_a_prefix_of_the_next(self) -> None:
        built = build_staircase(self.legacy, self.anchor)
        self.assertEqual(tuple(item.actor_count for item in built), STAIRCASE_RUNGS)
        for lower, higher in zip(built, built[1:]):
            self.assertEqual(higher.indices[: lower.actor_count], lower.indices)
            self.assertGreater(higher.frame_bytes, lower.frame_bytes)
        self.assertIsNone(nesting_break(built))

    def test_nesting_break_catches_rungs_built_at_different_anchors(self) -> None:
        """The real threat: one boot per rung means one anchor per rung."""
        low = build_world_population(self.legacy, self.anchor, 20)
        high_same = build_world_population(self.legacy, self.anchor, 60)
        self.assertIsNone(nesting_break((low, high_same)))

        # An anchor on the far side of the table: at ~30,000 units away its
        # nearest-60 no longer contains the first anchor's nearest-20.
        elsewhere = (21694.0703125, -5071.00048828125, 0.0)
        high_elsewhere = build_world_population(self.legacy, elsewhere, 60)
        dropped = nesting_break((low, high_elsewhere))
        self.assertIsNotNone(dropped)
        self.assertTrue(set(dropped) <= set(low.indices))
        self.assertTrue(set(dropped).isdisjoint(set(high_elsewhere.indices)))

    def test_nesting_break_refuses_input_it_cannot_read(self) -> None:
        low = build_world_population(self.legacy, self.anchor, 20)
        high = build_world_population(self.legacy, self.anchor, 60)
        for bad in ((), [low, high], None):
            with self.assertRaises(ValueError):
                nesting_break(bad)
        with self.assertRaises(ValueError):
            nesting_break((high, low))

    def test_top_rung_is_the_whole_census_without_repeats(self) -> None:
        top = build_world_population(self.legacy, self.anchor, CENSUS_COUNT)
        self.assertEqual(top.actor_count, CENSUS_COUNT)
        self.assertEqual(len(set(top.indices)), CENSUS_COUNT)

    def test_top_rung_differs_from_the_frozen_golden_115_by_p30_alone(self) -> None:
        """v141:1441 already builds a 115-member snapshot; this one is that one.

        Set equality would be a tautology - both read the same sha256-pinned
        table.  The falsifiable part is the byte delta: the census frame must
        exceed the golden frame by exactly P30's BasicAttr name and nothing
        else, since the HP override reuses tags of identical width.
        """
        _label, golden_pc, _frame, chosen = (
            self.legacy.make_v62_port_royal_population_snapshot(*self.anchor)
        )
        top = build_world_population(self.legacy, self.anchor, CENSUS_COUNT)
        self.assertEqual(set(top.indices), {row[0] for row in chosen})
        name_tag = self.legacy.wstr_tag(self.legacy.V119_P30_TARGET_NAME)
        self.assertEqual(top.pc_bytes - len(golden_pc), len(name_tag))
        self.assertNotIn(name_tag, golden_pc)
        self.assertEqual(top.pc.count(name_tag), 1)

    def test_identities_follow_the_frozen_actor_identity_rule(self) -> None:
        top = build_world_population(self.legacy, self.anchor, CENSUS_COUNT)
        self.assertEqual(
            top.actor_identities,
            tuple(0x2000 + index + 1 for index in top.indices),
        )

    def test_build_is_deterministic(self) -> None:
        first = build_world_population(self.legacy, self.anchor, 60)
        second = build_world_population(self.legacy, self.anchor, 60)
        self.assertEqual(first.pc, second.pc)
        self.assertEqual(first.indices, second.indices)

    def test_order_is_pinned_first_then_nearest_first(self) -> None:
        placements = census_order(self.legacy, self.anchor)
        self.assertEqual(
            tuple(item.placement_index for item in placements[:3]),
            SHIPPED_ISOLATED_INDICES,
        )
        x, y, z = self.anchor
        distances = [
            (item.x - x) ** 2 + (item.y - y) ** 2 + (item.z - z) ** 2
            for item in placements[3:]
        ]
        self.assertEqual(distances, sorted(distances))

    def test_rung_twenty_membership_coincides_with_v94_at_this_anchor(self) -> None:
        """A weak coincidence, recorded as one - not a second control.

        At the V134 anchor the pinned three happen to fall inside V94's
        nearest-20, so the SETS match.  The frames do not, the orders do not,
        and at other anchors the sets do not either.  No client has accepted
        this frame.
        """
        v94 = build_port_royal_initial_population(self.legacy, self.anchor)
        rung = build_world_population(self.legacy, self.anchor, AUTHORITATIVE_COUNT)
        self.assertEqual(set(rung.indices), set(v94.current_indices))
        self.assertNotEqual(rung.pc, v94.pc)
        self.assertNotEqual(rung.indices, v94.current_indices)

    # --- the default this lane exists to ship ----------------------------

    def test_module_declares_itself_a_shipping_lane(self) -> None:
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        self.assertEqual(DEFAULT_ACTOR_COUNT, CENSUS_COUNT)

    def test_recording_a_measured_ceiling_actually_changes_what_callers_send(
        self,
    ) -> None:
        """The whole point of the constant: editing it must change behaviour."""
        original = world_population.MEASURED_CLIENT_ACTOR_CEILING
        try:
            self.assertEqual(effective_actor_count(), CENSUS_COUNT)
            world_population.MEASURED_CLIENT_ACTOR_CEILING = 20
            self.assertEqual(effective_actor_count(), 20)
            world_population.MEASURED_CLIENT_ACTOR_CEILING = CENSUS_COUNT
            self.assertEqual(effective_actor_count(), CENSUS_COUNT)
        finally:
            world_population.MEASURED_CLIENT_ACTOR_CEILING = original
        self.assertEqual(effective_actor_count(), CENSUS_COUNT)

    def test_effective_count_validates_an_explicit_ceiling(self) -> None:
        self.assertEqual(effective_actor_count(None), CENSUS_COUNT)
        self.assertEqual(effective_actor_count(60), 60)
        for bad in (0, -1, CENSUS_COUNT + 1, "60", 60.0, True):
            with self.assertRaises(ValueError):
                effective_actor_count(bad)

    def test_report_pins_sizes_and_membership(self) -> None:
        report = staircase_report(self.legacy, self.anchor)
        self.assertEqual(report["census_count"], CENSUS_COUNT)
        self.assertEqual(report["initial_reapply_ms"], INITIAL_REAPPLY_MS)
        counts = [rung["actor_count"] for rung in report["rungs"]]
        self.assertEqual(counts, list(STAIRCASE_RUNGS))
        for rung in report["rungs"]:
            self.assertEqual(len(rung["indices"]), rung["actor_count"])
        sizes = [rung["frame_bytes"] for rung in report["rungs"]]
        self.assertEqual(sizes, sorted(sizes))

    def test_pin_file_still_describes_what_the_module_builds(self) -> None:
        """The scenario file is a PIN, not a switch: no flag reads it.

        Both anchors are pinned on purpose - the documented V134 anchor and the
        anchor a new character actually spawns at - so a tester comparing an
        observed frame to the pin is comparing against a position that exists.
        """
        pinned = json.loads(
            (ROOT / "scenarios" / "world_population_full_001.json")
            .read_text(encoding="ascii")
        )
        self.assertTrue(pinned["production_allowed"])
        self.assertFalse(pinned["test_only"])
        population = pinned["population"]
        self.assertEqual(population["default_actor_count"], CENSUS_COUNT)
        self.assertEqual(population["source_count"], CENSUS_COUNT)
        self.assertEqual(population["initial_reapply_ms"], INITIAL_REAPPLY_MS)
        self.assertEqual(
            population["control_rung_indices"], list(SHIPPED_ISOLATED_INDICES)
        )
        from pirateforce_foundation.population import PORT_ROYAL_SOURCE_SHA256

        self.assertEqual(population["source_sha256"], PORT_ROYAL_SOURCE_SHA256)

        anchors = pinned["staircase"]["reference_anchors"]
        self.assertEqual(len(anchors), 2)
        expected_anchors = {
            "v141_V134_PLAYER_XYZ": self.anchor,
            "v141_V135_PLAYER_XYZ_new_character_spawn": self.spawn,
        }
        for block in anchors:
            xyz = expected_anchors[block["label"]]
            self.assertEqual((block["x"], block["y"], block["z"]), xyz)
            report = staircase_report(self.legacy, xyz)
            self.assertEqual(
                [
                    {
                        "actor_count": rung["actor_count"],
                        "pc_bytes": rung["pc_bytes"],
                        "frame_bytes": rung["frame_bytes"],
                        "indices": rung["indices"],
                    }
                    for rung in report["rungs"]
                ],
                block["rungs"],
            )

    def test_pin_file_cannot_be_loaded_as_a_population_scenario(self) -> None:
        """It declares production_allowed; the loader only accepts test_only."""
        from pirateforce_foundation.population_scenario import (
            load_population_scenario,
        )

        with self.assertRaises(ValueError):
            load_population_scenario(
                ROOT / "scenarios" / "world_population_full_001.json"
            )

    # --- refusals --------------------------------------------------------

    def test_actor_count_is_bounded_by_the_census(self) -> None:
        for bad in (0, -1, CENSUS_COUNT + 1, 3.0, "3", None, True):
            with self.assertRaises(ValueError):
                build_world_population(self.legacy, self.anchor, bad)

    def test_anchor_must_be_an_exact_finite_triple(self) -> None:
        for bad in (
            None, (), (0.0, 0.0), (0.0, 0.0, 0.0, 0.0), [0.0, 0.0, 0.0],
            (0.0, 0.0, float("nan")), (0.0, 0.0, float("inf")),
            (0.0, 0.0, "0"), (0.0, 0.0, 1e39),
        ):
            with self.assertRaises(ValueError):
                build_world_population(self.legacy, bad, 3)

    def test_rungs_must_be_a_strictly_increasing_tuple_of_counts(self) -> None:
        for bad in (
            (), [3, 20], (20, 3), (3, 3), (3, 20, 20),
            (3, "20"), (3, None), (3, 3.0), (0, 20), (3, CENSUS_COUNT + 1),
        ):
            with self.assertRaises(ValueError):
                build_staircase(self.legacy, self.anchor, bad)

    def test_control_rung_refuses_to_measure_a_drifted_default(self) -> None:
        """If the shipped isolated set changes, rung 3 stops being the control."""
        drifted = types.SimpleNamespace(
            **{
                name: getattr(self.legacy, name)
                for name in (
                    "NPC_ATTR", "MOVEMENT_ATTR", "GSCN_RUNTIME_PROTOCOL_RES",
                    "V94_LOCAL_LIMIT", "V94_REFRESH_DISTANCE",
                    "PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS",
                    "make_npc_attr", "make_remote_movement_attr",
                    "make_remote_actor_entry", "make_runtime_remote_actors",
                    "V112_MONSTER_INDEX", "V117_P30_EXACT_HP",
                    "V119_P30_TARGET_NAME",
                )
            }
        )
        drifted.V112_TEST_INDICES = (0, 30, 92)
        with self.assertRaises(ValueError):
            census_order(drifted, self.anchor)
        drifted.V112_TEST_INDICES = self.legacy.V112_TEST_INDICES
        drifted.V112_MONSTER_INDEX = 31
        with self.assertRaises(ValueError):
            census_order(drifted, self.anchor)


if __name__ == "__main__":
    unittest.main()
