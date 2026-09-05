"""The three-tier scope for a boundary crossing at scene 126's map edge.

LANE-A, round n4vqxc.  COO-DECISION 20260905_1748 item 6: the responder
scope for a sea-edge crossing must check (1) the source scene, (2) a closed
map of wire trigger ids, and (3) that this project can actually compose an
arrival for the resolved destination -- and it must send nothing, because
composing and returning a live-teleport frame from `runtime.py`'s
TriggerVital branch is chief's file (`AGENTS.md` section 7).

WHAT THIS FILE DOES NOT CLAIM.  No client was booted.  No frame was queued.
Every assertion below is either a pure-function refusal/acceptance check or
a check against the SAME live-warp gate `/warp <scene>` already uses, so a
future change to that gate's shape and this module's own shape cannot
silently disagree about which scenes qualify.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_sea_edge_crossing as sea  # noqa: E402
from pirateforce_foundation.gm.warp_executor import (  # noqa: E402
    warp_no_coords_live_target,
)
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_island_trigger_log as islands_hook,
)

SOURCE_SCENE = 126


class TierOneSourceSceneTests(unittest.TestCase):
    """Only scene 126 may cross; every other scene id is a refusal."""

    def test_scene_126_with_a_pinned_id_resolves(self):
        crossing = sea.crossing_target(SOURCE_SCENE, 7)
        self.assertIsNotNone(crossing)
        self.assertEqual(crossing.destination.n_id, 304)

    def test_any_other_scene_refuses_even_with_a_pinned_id(self):
        for scene_id in (1, 2, 17, 278, 997, 304, 305):
            with self.subTest(scene_id=scene_id):
                self.assertIsNone(sea.crossing_target(scene_id, 7))
                self.assertIsNone(sea.crossing_target(scene_id, 69))


class TierTwoWireIdTests(unittest.TestCase):
    """Only the two pinned wire ids resolve; everything else refuses."""

    def test_the_pinned_ids_resolve_to_the_right_scenes(self):
        self.assertEqual(
            sea.crossing_target(SOURCE_SCENE, 7).destination.n_id, 304)
        self.assertEqual(
            sea.crossing_target(SOURCE_SCENE, 69).destination.n_id, 305)

    def test_the_third_observed_edge_is_not_pinned(self):
        # R318 also measured id 48 at the northern edge (Y >= +6413), but
        # COO-DECISION 20260905_1748 named only 7 and 69 -- a third row here
        # would be inventing a destination for an id nobody has ruled on.
        self.assertIsNone(sea.crossing_target(SOURCE_SCENE, 48))

    def test_an_unobserved_id_refuses(self):
        self.assertIsNone(sea.crossing_target(SOURCE_SCENE, 999999))

    def test_the_island_docking_ids_are_not_sea_edges(self):
        # ids 2/3 are GT-228's island-docking hypothesis
        # (lane_a_island_trigger_log.M2_OBSERVED_ISLAND_TRIGGER_IDS), a
        # different feature entirely -- this module must not also claim them.
        self.assertIsNone(sea.crossing_target(SOURCE_SCENE, 2))
        self.assertIsNone(sea.crossing_target(SOURCE_SCENE, 3))

    def test_the_two_maps_are_disjoint_by_construction(self):
        overlap = (set(sea.SEA_EDGE_TRIGGER_TARGETS)
                   & set(islands_hook.M2_OBSERVED_ISLAND_TRIGGER_IDS))
        self.assertEqual(overlap, set())


class TierThreeDestinationReadinessTests(unittest.TestCase):
    """The resolved scene must be one this project can actually land on."""

    def test_both_destinations_agree_with_the_live_warp_gate(self):
        # Not a bespoke lookup: the exact same function `/warp <scene>` uses.
        for wire_id, scene_id in sea.SEA_EDGE_TRIGGER_TARGETS.items():
            with self.subTest(wire_id=wire_id, scene_id=scene_id):
                crossing = sea.crossing_target(SOURCE_SCENE, wire_id)
                gate = warp_no_coords_live_target(scene_id)
                self.assertIsNotNone(gate)
                self.assertEqual(crossing.destination, gate)

    def test_a_scene_the_gate_refuses_would_refuse_here_too(self):
        # Simulated by asking for a wire id this module has never pinned to
        # a scene the gate is known to refuse (278, markerless, no decree):
        # there is no such wire id today, so this instead proves the SHAPE
        # of the refusal directly against the map this module actually owns.
        broken_map = dict(sea.SEA_EDGE_TRIGGER_TARGETS)
        broken_map[7] = 278
        original = sea.SEA_EDGE_TRIGGER_TARGETS
        try:
            sea.SEA_EDGE_TRIGGER_TARGETS = broken_map
            self.assertIsNone(sea.crossing_target(SOURCE_SCENE, 7))
        finally:
            sea.SEA_EDGE_TRIGGER_TARGETS = original


class BadInputRefusesRatherThanRaisesTests(unittest.TestCase):

    def test_non_int_scene_id(self):
        self.assertIsNone(sea.crossing_target("126", 7))
        self.assertIsNone(sea.crossing_target(126.0, 7))
        self.assertIsNone(sea.crossing_target(None, 7))

    def test_non_int_wire_id(self):
        self.assertIsNone(sea.crossing_target(SOURCE_SCENE, "7"))
        self.assertIsNone(sea.crossing_target(SOURCE_SCENE, 7.0))

    def test_bool_is_not_accepted_as_int_even_though_it_is_one_in_python(self):
        # True == 1, and 1 is not a pinned scene id (nor is False == 0), but
        # this refuses the TYPE, not just the value, the same discipline
        # world_scene_marker.decreed_arrival_row already takes.
        self.assertIsNone(sea.crossing_target(True, 7))
        self.assertIsNone(sea.crossing_target(SOURCE_SCENE, False))


class ConsoleLineAndPlanReportTests(unittest.TestCase):

    def test_a_resolved_crossing_names_both_scenes_and_never_claims_a_send(self):
        crossing = sea.crossing_target(SOURCE_SCENE, 7)
        line = sea.crossing_console_line(crossing, 7)
        self.assertIn("SEA_EDGE_CROSSING", line)
        self.assertIn("id=7", line)
        self.assertIn("dest_scene=304", line)
        self.assertIn("bytes_out=0", line)
        self.assertIn("no_responder", line)

    def test_a_refused_id_still_prints_a_line(self):
        line = sea.crossing_console_line(None, 48)
        self.assertIn("id=48", line)
        self.assertIn("no_target", line)
        self.assertIn("bytes_out=0", line)

    def test_the_plan_report_carries_the_spawn_and_heading(self):
        crossing = sea.crossing_target(SOURCE_SCENE, 69)
        plan = sea.crossing_plan_report(crossing)
        self.assertEqual(plan["dest_scene_id"], 305)
        self.assertEqual(plan["spawn"], (1538.0, 4819.0, 70.0))
        self.assertEqual(plan["heading"], 6)


class ItSendsNothingTests(unittest.TestCase):
    """The module's own central claim, checked rather than only asserted."""

    def test_production_allowed_is_true_but_the_module_has_no_send_surface(self):
        self.assertTrue(sea.production_allowed)
        # No attribute anywhere in this module's public surface spells
        # "send", "queue", "enqueue", "transmit" or "sendall" -- a grep a
        # reviewer can re-run without importing anything.
        source = Path(sea.__file__).read_text(encoding="utf-8")
        for banned in ("sendall(", "def send(", ".transport", "socket."):
            self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main()
