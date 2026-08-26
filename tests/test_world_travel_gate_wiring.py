"""LANE-A M2: the three things that stood between the door and the wiring.

``CORE-REQUEST-004`` asked the chief for one call at ``runtime.py:3949`` and
then handed him three questions lane A had left open, any one of which is a
good reason not to make the call:

1. a bare ``TravelGateSet()`` in ``PersistentGameSessionState.__init__``
   parses three JSON files on every login and raises on a bad pin - on the
   login path of every player, so a broken pin means NOBODY CAN LOG IN;
2. the opt-in lanes (arena, ground loot, nameprop, field mobs) also run in
   scene 1, so an attended round of any of them can walk into the gate and be
   carried off mid-experiment, leaving a durable row pointing at scene 278;
3. ``foundation.checkpoint`` can throw, and the departure line was printed
   before the caller ever tried the write - so a failed write left a console
   claiming a player had travelled and a database saying they had not.

This file is the evidence that all three are answered, and the last class in
it runs the chief's patch itself against a scripted walk, so the code in the
letter is code that has been executed rather than code that has been read.

NOTHING HERE BOOTS A SERVER OR TOUCHES A CLIENT.  The runtime in the last
class is a double with three methods, and it proves the SHAPE of the call,
not that scene 278 renders.  GT-081 is still the only thing that can say a
player saw anything.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel, world_travel_gate
from pirateforce_foundation.model import Position
from pirateforce_foundation.population import SCENE_SEQUENCE
from pirateforce_foundation.world_travel_gate import (
    TravelDeparture,
    TravelGateRefused,
    TravelGateSet,
    load_travel_gates,
    preload,
    preloaded,
    forget_preload,
    scenario_stand_down,
)

DEPARTURE_GATE = "port_royal_columbus_departure"
RETURN_GATE = "test_stage_landing_return"
ATTENDED_SPAWN = (-8553.947265625, -2579.68896484375, 186.0)


def _sink():
    lines = []
    return lines, lines.append


def _home(x, y, z, scene_id=1) -> Position:
    return Position(scene_id, SCENE_SEQUENCE, x, y, z, 0.0)


class _NoDisk:
    """Make every loader in the module explode, then watch nothing explode."""

    def __enter__(self):
        def refuse(*args, **kwargs):
            raise AssertionError("the login path read a file")

        self._gates = world_travel_gate.load_travel_gates
        self._registry = world_scene_travel.load_scene_registry
        world_travel_gate.load_travel_gates = refuse
        world_scene_travel.load_scene_registry = refuse
        return self

    def __exit__(self, *exc):
        world_travel_gate.load_travel_gates = self._gates
        world_scene_travel.load_scene_registry = self._registry
        return False


class PreloadTests(unittest.TestCase):
    """Question 1: a bad pin must stop a boot, not stop every login."""

    def tearDown(self):
        forget_preload()

    def test_preload_parses_the_same_pins_the_loader_does(self):
        pins = preload()
        gates, settings = load_travel_gates()
        self.assertEqual(pins.gates, gates)
        self.assertEqual(pins.settings, settings)
        self.assertIs(preloaded(), pins)
        self.assertIn("world_travel_gates_001.json", pins.source)

    def test_the_login_path_reads_no_file_at_all(self):
        preload()
        with _NoDisk():
            lines, emit = _sink()
            gate_set = TravelGateSet.from_preloaded(emit=emit)
        self.assertFalse(gate_set.is_inert)
        self.assertEqual(len(gate_set.gates), 2)
        self.assertEqual(lines, [])

    def test_a_broken_pin_refuses_at_preload_where_one_operator_is_watching(self):
        raw = json.loads(Path(world_travel_gate.GATE_REGISTRY_PATH).read_text(
            encoding="ascii"))
        raw["gates"][0]["fire_radius_units"] = -1.0
        # A temporary directory, not the repository: a test that leaves a
        # broken pin lying in the tree is a test that breaks the next round.
        with tempfile.TemporaryDirectory() as scratch:
            broken = Path(scratch) / "world_travel_gates_001.json"
            broken.write_text(json.dumps(raw), encoding="ascii")
            with self.assertRaises(TravelGateRefused):
                preload(broken)

    def test_without_a_preload_the_session_is_inert_and_says_so(self):
        """The failure mode is 'the world has no doors', never 'no login'."""
        forget_preload()
        with _NoDisk():
            lines, emit = _sink()
            gate_set = TravelGateSet.from_preloaded(emit=emit)
            self.assertTrue(gate_set.is_inert)
            self.assertEqual(gate_set.inert_reason, "not_preloaded")
            self.assertEqual(len(lines), 1)
            self.assertTrue(lines[0].startswith("WORLD_TRAVEL_INERT"))
            self.assertIn("reason=not_preloaded", lines[0])
            self.assertIsNone(gate_set.observe(_home(*ATTENDED_SPAWN)))

    def test_preload_again_replaces_the_parse(self):
        first = preload()
        second = preload()
        self.assertIsNot(first, second)
        self.assertIs(preloaded(), second)


class StandDownTests(unittest.TestCase):
    """Question 2: the guard lane A could not write as a list, as a rule."""

    def setUp(self):
        self.settings = load_travel_gates()[1]

    def _walk_into_the_gate(self, gate_set):
        centre = {g.name: g for g in gate_set.gates}[DEPARTURE_GATE].centre \
            if gate_set.gates else (0.0, 0.0, 0.0)
        gate_set.observe(_home(*ATTENDED_SPAWN))
        found = None
        for _ in range(self.settings.dwell_reports + 2):
            got = gate_set.observe(_home(*centre))
            if got is not None and found is None:
                got.confirmed_fields()
                found = got
        return found

    def test_an_inert_set_does_not_open_a_door_however_long_you_stand(self):
        lines, emit = _sink()
        gate_set = TravelGateSet(emit=emit, inert_reason="scenario_selected_arena_scenario")
        self.assertIsNone(self._walk_into_the_gate(gate_set))
        self.assertEqual(gate_set.departures, 0)
        self.assertEqual(len(lines), 1, "one line at stand-down, none per report")
        self.assertIn("effect=no_door_opens_in_this_session", lines[0])

    def test_standing_down_mid_transit_prints_the_row_to_put_back(self):
        """The set is about to stop reporting the only copy of that row."""
        lines, emit = _sink()
        gate_set = TravelGateSet(emit=emit)
        departure = self._walk_into_the_gate(gate_set)
        self.assertIsInstance(departure, TravelDeparture)
        self.assertTrue(gate_set.in_transit)
        gate_set.stand_down("operator_stopped_the_lane")
        stranded = [
            line for line in lines if line.startswith("WORLD_TRAVEL_STRANDED")]
        self.assertEqual(len(stranded), 1)
        self.assertIn("restore_row=(1,0,", stranded[0])
        self.assertFalse(gate_set.in_transit)
        self.assertTrue(gate_set.is_inert)

    def test_standing_down_kills_a_crossing_the_caller_is_still_holding(self):
        """Otherwise a door opens after the lane was shut.

        The caller takes a crossing, the lane stands down before the caller
        gets to the confirm, and the crossing's staged apply() would still
        commit and still print - on a set that is inert.
        """
        lines, emit = _sink()
        gate_set = TravelGateSet(emit=emit)
        centre = {g.name: g for g in gate_set.gates}[DEPARTURE_GATE].centre
        gate_set.observe(_home(*ATTENDED_SPAWN))
        crossing = None
        for _ in range(self.settings.dwell_reports + 1):
            crossing = crossing or gate_set.observe(_home(*centre))
        self.assertIsInstance(crossing, TravelDeparture)
        gate_set.stand_down("operator_stopped_the_lane")
        self.assertTrue(crossing.abandoned)
        with self.assertRaises(TravelGateRefused):
            crossing.confirmed_fields()
        self.assertEqual(gate_set.departures, 0)
        self.assertFalse(any(
            line.startswith("WORLD_TRAVEL_DEPART ") for line in lines))
        self.assertTrue(any(
            "reason=stood_down_before_confirm" in line for line in lines))

    def test_standing_down_twice_says_it_once(self):
        lines, emit = _sink()
        gate_set = TravelGateSet(emit=emit)
        gate_set.stand_down("first")
        gate_set.stand_down("second")
        inert = [line for line in lines if line.startswith("WORLD_TRAVEL_INERT")]
        self.assertEqual(len(inert), 1)
        self.assertIn("reason=first", inert[0])
        self.assertEqual(gate_set.inert_reason, "first")

    def test_a_stand_down_cannot_be_undone(self):
        gate_set = TravelGateSet(emit=lambda line: None)
        gate_set.stand_down("done")
        self.assertFalse(hasattr(gate_set, "resume"))

    def test_an_empty_reason_is_refused(self):
        with self.assertRaises(ValueError):
            TravelGateSet(emit=lambda line: None, inert_reason="")
        gate_set = TravelGateSet(emit=lambda line: None)
        with self.assertRaises(ValueError):
            gate_set.stand_down("")


class ScenarioScanTests(unittest.TestCase):
    """Question 2: the guard, after the adversary pass rewrote what it takes.

    The first version scanned an object's ``vars()``.  The adversary pass of
    round e7q6yy measured four shapes where that returns ``None`` while a lane
    IS selected - a class attribute, a ``property``, an inherited default, and
    any object defining ``items()`` - and a guard whose miss opens every door
    is worse than no guard.  The object form is gone.  What replaced it is
    better than either: ``runtime.make_state_class`` already builds
    ``active_lanes`` at :334-382, the frozenset of the names of every lane the
    boot selected, at the top of the factory where the call goes.
    """

    def test_the_runtimes_own_active_lanes_is_what_this_takes(self):
        self.assertIsNone(scenario_stand_down(frozenset()))
        reason = scenario_stand_down(frozenset({"arena_scenario"}))
        self.assertEqual(reason, "scenario_selected_arena_scenario")

    def test_two_selected_lanes_are_both_named_and_the_order_is_stable(self):
        reason = scenario_stand_down(
            {"pickup_listener_hypothesis_scenario",
             "ground_loot_hypothesis_scenario"})
        self.assertEqual(
            reason,
            "scenario_selected_ground_loot_hypothesis_scenario,"
            "pickup_listener_hypothesis_scenario",
        )

    def test_the_factory_keywords_still_work_as_a_mapping(self):
        """``scenario_stand_down(locals())`` for a caller without the set."""
        def make_state_class(legacy, scenario=None, scene_load_scenario=None,
                             arena_scenario=None, session_factory=None):
            return scenario_stand_down(locals())

        self.assertIsNone(make_state_class("legacy"))
        self.assertIn(
            "arena_scenario", make_state_class("legacy", arena_scenario="v2"))

    def test_the_bare_name_scenario_counts_because_the_arena_uses_it(self):
        """The lane the guard was asked for is passed as ``scenario``."""
        reason = scenario_stand_down({"scenario": "arena_v2"})
        self.assertEqual(reason, "scenario_selected_scenario")
        self.assertIsNone(scenario_stand_down({"scenario": None}))

    def test_a_lane_this_module_has_never_heard_of_shuts_them_too(self):
        self.assertIn(
            "a_lane_invented_next_month_scenario",
            scenario_stand_down({"a_lane_invented_next_month_scenario": "on"}),
        )
        self.assertIn(
            "a_lane_invented_next_month_scenario",
            scenario_stand_down(frozenset({"a_lane_invented_next_month_scenario"})),
        )

    def test_an_object_is_refused_and_not_scanned(self):
        """The four shapes the old scan missed, and it missed them OPEN."""

        class ClassAttribute:
            arena_scenario = "arena_v2"

        class WithProperty:
            @property
            def arena_scenario(self):
                return "arena_v2"

        class Base:
            arena_scenario = "arena_v2"

        class Inherited(Base):
            pass

        class HasItems:
            def __init__(self):
                self.arena_scenario = "arena_v2"

            def items(self):
                return [("a sword", 1)]

        for label, owner in (
            ("class attribute", ClassAttribute()),
            ("property", WithProperty()),
            ("inherited default", Inherited()),
            ("object with items()", HasItems()),
            ("an int", 7),
        ):
            with self.subTest(label):
                self.assertEqual(
                    scenario_stand_down(owner), "scenario_scan_unreadable")

    def test_names_that_are_not_strings_shut_the_doors(self):
        self.assertEqual(
            scenario_stand_down({7: "arena_v2"}), "scenario_scan_unreadable")
        self.assertEqual(
            scenario_stand_down({7, 8}), "scenario_scan_unreadable")

    def test_none_means_the_caller_said_nothing_is_selected(self):
        self.assertIsNone(scenario_stand_down(None))

    def test_every_reason_is_ascii(self):
        scenario_stand_down(frozenset({"arena_scenario"})).encode("ascii")
        scenario_stand_down(7).encode("ascii")


class TwoPhaseCrossingTests(unittest.TestCase):
    """Question 3: the console must not be able to outrun the database."""

    def setUp(self):
        self.settings = load_travel_gates()[1]
        self.lines, emit = _sink()
        self.set = TravelGateSet(emit=emit)
        self.centre = {g.name: g for g in self.set.gates}[DEPARTURE_GATE].centre
        self.set.observe(_home(*ATTENDED_SPAWN))
        self.departure = None
        for _ in range(self.settings.dwell_reports + 1):
            self.departure = self.departure or self.set.observe(
                _home(*self.centre))

    def _depart_lines(self):
        return [
            line for line in self.lines
            if line.startswith("WORLD_TRAVEL_DEPART ")
        ]

    def test_a_crossing_arrives_with_nothing_committed(self):
        self.assertIsInstance(self.departure, TravelDeparture)
        self.assertFalse(self.departure.confirmed)
        self.assertEqual(self.set.departures, 0)
        self.assertFalse(self.set.in_transit)
        self.assertIsNone(self.set.left_from(1))
        self.assertEqual(self._depart_lines(), [])

    def test_confirming_commits_it_and_prints_it_once(self):
        fields = self.departure.confirmed_fields()
        self.assertEqual(fields, self.departure.teleport_fields)
        self.assertTrue(self.departure.confirmed)
        self.assertEqual(self.set.departures, 1)
        self.assertTrue(self.set.in_transit)
        self.assertEqual(len(self._depart_lines()), 1)

    def test_confirming_twice_is_refused_rather_than_counted_twice(self):
        self.departure.confirmed_fields()
        with self.assertRaises(TravelGateRefused) as caught:
            self.departure.confirmed_fields()
        self.assertEqual(caught.exception.reason, "already_confirmed")
        self.assertEqual(self.set.departures, 1)

    def test_a_write_that_failed_leaves_no_line_and_no_transit(self):
        """The chief's own example: checkpoint throws on a stale lease."""
        self.departure.abandon("checkpoint_raised_StaleLease")
        self.assertTrue(self.departure.abandoned)
        self.assertEqual(self._depart_lines(), [])
        self.assertEqual(self.set.departures, 0)
        self.assertFalse(self.set.in_transit)
        abandoned = [
            line for line in self.lines
            if line.startswith("WORLD_TRAVEL_DEPART_ABANDONED")
        ]
        self.assertEqual(len(abandoned), 1)
        self.assertIn("reason=checkpoint_raised_StaleLease", abandoned[0])
        self.assertIn("arrival_row_offered=(278,0,", abandoned[0])
        # It says what it knows and nothing about the database: the caller
        # persists BEFORE it confirms, so a confirm that dies after a
        # successful write would make any claim about the row false.
        self.assertIn("no_teleport_sent=true", abandoned[0])
        self.assertIn("whether_the_caller_wrote_that_row=unknown", abandoned[0])
        self.assertNotIn("row_not_written", abandoned[0])

    def test_an_abandoned_crossing_cannot_then_be_sent(self):
        self.departure.abandon("checkpoint_raised_StaleLease")
        with self.assertRaises(TravelGateRefused) as caught:
            self.departure.confirmed_fields()
        self.assertEqual(caught.exception.reason, "already_abandoned")

    def test_a_caller_that_just_drops_it_is_told_on_the_next_report(self):
        self.assertIsNone(self.set.observe(_home(*self.centre)))
        self.assertTrue(any(
            "reason=not_confirmed_before_next_report" in line
            for line in self.lines))
        self.assertEqual(self.set.departures, 0)

    def test_an_abandoned_crossing_makes_the_player_stand_still_again(self):
        """Otherwise a failing database prints one line per report forever."""
        self.departure.abandon("checkpoint_raised_StaleLease")
        for _ in range(self.settings.dwell_reports - 1):
            self.assertIsNone(self.set.observe(_home(*self.centre)))
        again = self.set.observe(_home(*self.centre))
        self.assertIsInstance(again, TravelDeparture)


class TheChiefsPatchTests(unittest.TestCase):
    """Run the code from CORE-REQUEST-004 v2, exactly as the letter has it.

    A runtime double, three methods, and a scripted walk.  What this proves is
    the shape of the call and the order of the two writes; what it cannot
    prove is anything about a client.
    """

    def setUp(self):
        self.settings = load_travel_gates()[1]
        forget_preload()
        preload()
        self.addCleanup(forget_preload)

    class _Character:
        """``foundation.selected`` is a CHARACTER, and that nearly shipped.

        The first version of this double made ``selected`` a ``Position``,
        which made the wire below read ``foundation.selected`` and pass.  The
        real object is a character: ``session.checkpoint`` does
        ``self.selected = replace(self.selected, position=position)``
        (session.py:162-166) and ``runtime.py:3187-3192`` reads
        ``selected.position.scene_id``.  ``observe`` refuses a non-Position
        with a ``ValueError``, which nothing at :3646 catches, so a double
        that disagreed with the real object in the one field the patch reads
        would have "proved" a patch that killed every connection on its first
        position report.  The letter always said ``.position``; this double
        did not, and it was the double that claimed to be evidence.
        """

        def __init__(self, position):
            self.position = position

    class _Foundation:
        def __init__(self, position, fail=False):
            self.selected = TheChiefsPatchTests._Character(position)
            self.rows = []
            self.fail = fail

        def checkpoint(self, position):
            if self.fail:
                raise RuntimeError("lease is stale")
            self.rows.append(position)
            self.selected = TheChiefsPatchTests._Character(position)

    def _wire(self, foundation, gate_set, lines):
        """THE PATCH.  Keep this identical to the letter."""
        def on_position_report(row):
            actions = []
            foundation.checkpoint(row)              # _checkpoint_exact_target
            departure = gate_set.observe(foundation.selected.position)
            if departure is not None:
                foundation.checkpoint(departure.arrival)
                tp_pc, tp_frame = (
                    "pc", departure.confirmed_fields())
                actions = actions + [(
                    departure.action_label, tp_pc, tp_frame, 0.70)]
                lines.append(
                    "world_travel_departed_scene_"
                    f"{departure.gate.to_scene_id}")
            return actions
        return on_position_report

    def test_the_double_agrees_with_the_real_objects_it_stands_for(self):
        """The check that would have caught the double, run against the tree.

        A double is evidence only while it agrees with the thing it replaces
        in the fields the code under test reads.  This reads the real
        modules.
        """
        import inspect
        from pirateforce_foundation import session as real_session
        source = inspect.getsource(real_session.FoundationSession.checkpoint)
        self.assertIn("replace(self.selected, position=position)", source)
        foundation = self._Foundation(_home(*ATTENDED_SPAWN))
        self.assertFalse(isinstance(foundation.selected, Position))
        self.assertIsInstance(foundation.selected.position, Position)

    def test_the_whole_loop_out_of_town_and_back(self):
        console, emit = _sink()
        events = []
        gate_set = TravelGateSet.from_preloaded(emit=emit)
        centre = {g.name: g for g in gate_set.gates}[DEPARTURE_GATE].centre
        foundation = self._Foundation(_home(*ATTENDED_SPAWN))
        report = self._wire(foundation, gate_set, events)

        # 1. walk to the door and stop.
        report(_home(*ATTENDED_SPAWN))
        out = []
        for _ in range(self.settings.dwell_reports + 1):
            out = out or report(_home(*centre))
        self.assertEqual(len(out), 1)
        label, _, fields, delay = out[0]
        self.assertEqual(label, "WORLD_TRAVEL_DEPARTURE_TO_SCENE278_TELEPORT")
        self.assertIn("TELEPORT", label, "the grace window keys on this word")
        self.assertEqual(fields[0], 278)
        self.assertEqual(events, ["world_travel_departed_scene_278"])
        self.assertEqual(foundation.selected.position.scene_id, 278)

        # 2. the client lands somewhere nobody predicted.
        landing = Position(278, SCENE_SEQUENCE, -13200.0, 22800.0, -2492.0, 0.0)
        self.assertEqual(report(landing), [])
        self.assertEqual(
            gate_set.measured_centre(RETURN_GATE),
            (-13200.0, 22800.0, -2492.0))

        # 3. walk out of the landing zone, then come back and stop.
        self.assertEqual(
            report(Position(278, SCENE_SEQUENCE, -11500.0, 22800.0, -2492.0, 0.0)),
            [])
        back = []
        for _ in range(self.settings.dwell_reports + 1):
            back = back or report(
                Position(278, SCENE_SEQUENCE, -13100.0, 22800.0, -2492.0, 0.0))
        self.assertEqual(len(back), 1)
        self.assertEqual(back[0][0], "WORLD_TRAVEL_RETURN_TO_SCENE1_TELEPORT")
        self.assertEqual(back[0][2][0], 1)
        # and home is the row they were standing on when they left, not a pin.
        self.assertAlmostEqual(back[0][2][2], centre[0])
        self.assertEqual(events[-1], "world_travel_departed_scene_1")
        self.assertEqual(len(gate_set.gates), 2)

    def test_a_checkpoint_that_throws_sends_nothing_and_claims_nothing(self):
        console, emit = _sink()
        events = []
        gate_set = TravelGateSet.from_preloaded(emit=emit)
        centre = {g.name: g for g in gate_set.gates}[DEPARTURE_GATE].centre
        foundation = self._Foundation(_home(*ATTENDED_SPAWN))
        report = self._wire(foundation, gate_set, events)
        report(_home(*ATTENDED_SPAWN))
        foundation.fail = True
        with self.assertRaises(RuntimeError):
            for _ in range(self.settings.dwell_reports + 2):
                report(_home(*centre))
        self.assertEqual(events, [])
        self.assertEqual(gate_set.departures, 0)
        self.assertFalse(gate_set.in_transit)
        self.assertFalse(any(
            line.startswith("WORLD_TRAVEL_DEPART ") for line in console))

    def test_an_opt_in_lane_walks_through_the_same_zone_untouched(self):
        """An attended arena round is what this protects."""
        console, emit = _sink()
        events = []
        # Exactly what runtime.make_state_class:334-382 would hand over.
        active_lanes = frozenset({"scenario"})
        gate_set = TravelGateSet.from_preloaded(
            emit=emit, inert_reason=scenario_stand_down(active_lanes))
        centre = {g.name: g for g in gate_set.gates}[DEPARTURE_GATE].centre \
            if gate_set.gates else (0.0, 0.0, 0.0)
        foundation = self._Foundation(_home(*ATTENDED_SPAWN))
        report = self._wire(foundation, gate_set, events)
        report(_home(*ATTENDED_SPAWN))
        for _ in range(self.settings.dwell_reports + 8):
            self.assertEqual(report(_home(*centre)), [])
        self.assertEqual(events, [])
        self.assertEqual(foundation.selected.position.scene_id, 1)
        self.assertEqual(
            [line for line in console if line.startswith("WORLD_TRAVEL_INERT")],
            console,
            "an inert lane says one thing and then keeps quiet",
        )


if __name__ == "__main__":
    unittest.main()
