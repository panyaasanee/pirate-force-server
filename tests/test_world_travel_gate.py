"""LANE-A BUILD-002 second half: the door out of town.

The load-bearing tests in this file are the four that keep the module honest
about the ways this mechanism can hurt a player rather than help one:

* ``test_landing_inside_a_gate_does_not_fire_it`` - the ping-pong. Without the
  disarm-on-switch rule a player bounces between two scenes forever, at
  walking speed, and every bounce rewrites their durable row.
* ``test_a_transit_never_settles_and_says_so`` - the strand. A destination
  that never loads leaves a row pointing at it, and the only recovery is the
  console line, so the console line has to exist.
* ``test_the_return_row_is_the_row_the_player_left_that_scene_on`` - one
  memory slot answered "where did they leave scene 1" with the row they left
  scene 278 on as soon as anybody made the round trip twice.
* ``test_a_gate_to_an_unpinned_scene_is_refused_at_load`` - RE-077 proved the
  client parks at status 2 with no fallback and no way for the server to know.
  A bad destination must never be discovered while a player is walking.
"""

import json
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel, world_travel_gate
from pirateforce_foundation.model import Position
from pirateforce_foundation.population import SCENE_SEQUENCE
from pirateforce_foundation.world_travel_gate import (
    ARRIVAL_DESTINATION_SPAWN,
    ARRIVAL_REMEMBERED_HOME,
    GATE_REGISTRY_PATH,
    ROLE_DEPARTURE,
    ROLE_RETURN,
    TravelDeparture,
    TravelGate,
    TravelGateRefused,
    TravelGateSet,
    TravelGateSettings,
    departure_report,
    load_travel_gates,
    production_allowed,
    test_only,
)

DEPARTURE_GATE = "port_royal_columbus_departure"
RETURN_GATE = "test_stage_landing_return"

# Where an attended run actually found the character on 2026-08-23 (GT-045),
# pinned in scenarios/world_scene_density_001.json.  Not the v141 constant:
# the login position comes from the DB row.
ATTENDED_SPAWN = (-8553.947265625, -2579.68896484375, 186.0)
V141_LOGIN_ANCHOR = (-9239.95703125, -2780.045166015625, 223.29209899902344)


def _raw() -> dict:
    return json.loads(Path(GATE_REGISTRY_PATH).read_text(encoding="ascii"))


def _sink():
    lines = []
    return lines, lines.append


def _set(**kwargs) -> tuple[TravelGateSet, list]:
    lines, emit = _sink()
    return TravelGateSet(emit=emit, **kwargs), lines


def _home(x, y, z, scene_id=1) -> Position:
    return Position(scene_id, SCENE_SEQUENCE, x, y, z, 0.0)


class TravelGatePinTests(unittest.TestCase):
    def setUp(self):
        self.gates, self.settings = load_travel_gates()
        self.by_name = {gate.name: gate for gate in self.gates}

    def test_the_pin_is_not_a_scenario(self):
        raw = _raw()
        self.assertIs(raw["test_only"], False)
        self.assertIs(raw["production_allowed"], True)
        self.assertEqual(raw["selection"], "none_default_behaviour_no_scenario_flag")
        self.assertIs(test_only, False)
        self.assertIs(production_allowed, True)

    def test_both_doors_are_pinned_and_they_are_a_pair(self):
        self.assertEqual(
            sorted(self.by_name), sorted([DEPARTURE_GATE, RETURN_GATE]))
        out = self.by_name[DEPARTURE_GATE]
        back = self.by_name[RETURN_GATE]
        self.assertEqual(out.role, ROLE_DEPARTURE)
        self.assertEqual(back.role, ROLE_RETURN)
        # The way back leads to the scene the way out left.
        self.assertEqual(back.to_scene_id, out.from_scene_id)
        self.assertEqual(back.from_scene_id, out.to_scene_id)

    def test_the_departure_gate_stands_on_a_census_actor(self):
        gate = self.by_name[DEPARTURE_GATE]
        self.assertIsNotNone(gate.centre)
        self.assertFalse(gate.centre_is_measured_at_runtime)
        self.assertIn("Columbus", gate.centre_provenance)
        self.assertIn("index 65", gate.centre_provenance)

    def test_the_landmark_is_declared_conditional_while_the_census_is_not_wired(self):
        """Columbus is one of the 115, and the default boot still sends three.

        The census wiring lives in PR #41, which had not merged.  A pin that
        promised a visible person would be promising something no tester can
        see, so the pin says so and this keeps it saying so.
        """
        gate = self.by_name[DEPARTURE_GATE]
        self.assertIn("#41", gate.centre_provenance)
        self.assertIn("not one of the three", gate.centre_provenance)
        self.assertTrue(any(
            "PR #41" in claim for claim in _raw()["nonclaims"]))

    def test_the_landmark_name_is_declared_non_unique(self):
        """Three census rows are called Columbus - 35, 65 and 140.

        The old pin said "walk to Columbus names exactly one place".  It names
        three, and the test that was supposed to prove uniqueness measured the
        distance to the nearest other ACTOR rather than checking the NAME.
        """
        gate = self.by_name[DEPARTURE_GATE]
        self.assertIn("35, 65 and 140", gate.centre_provenance)
        self.assertIn("never by name", gate.centre_provenance)
        import ast
        source = (ROOT / "current" / "pf_login_game_server_v141.py").read_text(
            encoding="utf-8", errors="replace")
        head = source.index("PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS = [")
        tail = source.index("\n]", head)
        rows = ast.literal_eval(
            source[head + len("PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS = "):tail + 2])
        columbus = sorted(row[0] for row in rows if row[6] == "Columbus")
        self.assertEqual(columbus, [35, 65, 140])

    def test_the_gate_centre_is_a_real_row_of_the_frozen_census(self):
        """Re-derived from v141's own table, not copied from a letter."""
        import ast
        source = (ROOT / "current" / "pf_login_game_server_v141.py").read_text(
            encoding="utf-8", errors="replace")
        head = source.index("PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS = [")
        tail = source.index("\n]", head)
        rows = ast.literal_eval(
            source[head + len("PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS = "):tail + 2])
        self.assertEqual(len(rows), 115)
        row = [item for item in rows if item[0] == 65][0]
        gate = self.by_name[DEPARTURE_GATE]
        self.assertEqual(row[6], "Columbus")
        self.assertEqual((row[2], row[3], row[4]), gate.centre)
        # And no OTHER census member is inside the zone, or "walk to Columbus"
        # would name two places.
        inside = [
            item for item in rows
            if item[0] != 65
            and math.hypot(item[2] - gate.centre[0], item[3] - gate.centre[1])
            <= gate.fire_radius
        ]
        self.assertEqual(inside, [])

    def test_the_departure_gate_cannot_fire_where_a_player_logs_in(self):
        """The single most damaging failure would be a gate at the spawn.

        A player who logs in inside the zone would be shipped out of town
        before touching the keyboard, which is exactly the 'waking up
        elsewhere' that COO-DECISION 0150 ruled is NOT travel.
        """
        gate = self.by_name[DEPARTURE_GATE]
        for label, point in (
            ("attended spawn", ATTENDED_SPAWN),
            ("v141 login anchor", V141_LOGIN_ANCHOR),
        ):
            with self.subTest(label):
                horizontal = math.hypot(
                    point[0] - gate.centre[0], point[1] - gate.centre[1])
                self.assertGreater(horizontal, gate.fire_radius)
                # And beyond the ARM radius too, so the gate is already armed
                # by the first report of the session rather than needing a
                # walk out and back before it can ever be used.
                self.assertGreater(horizontal, gate.arm_radius)

    def test_the_radii_have_hysteresis(self):
        for gate in self.gates:
            with self.subTest(gate.name):
                self.assertGreater(gate.arm_radius, gate.fire_radius)

    def test_the_fire_radius_covers_more_than_two_measured_steps(self):
        """Recomputed from the replay table, not quoted from a docstring.

        The prose in move_authority_hypothesis.py says 400-500 units per
        report.  The 29 rows of reports/move_cadence001_smoke/replay_output.txt
        say the largest horizontal step is 538.44, between frames 226 and 227,
        over all 29 reported positions and not only the 19 that wrote a row -
        this gate sees every report, so the dedup skips count.
        A straight crossing of the zone is 2 x fire_radius long, and this pins
        that it is at least two of the LARGEST real steps, so shrinking the
        radius has to argue with the measurement rather than with the prose.
        """
        largest_measured_step = 538.44
        gate = self.by_name[DEPARTURE_GATE]
        self.assertGreaterEqual(
            2.0 * gate.fire_radius, 2.0 * largest_measured_step)
        pinned = _raw()["the_measured_facts_the_radii_come_from"][
            "step_units_recomputed_from_the_replay_this_round"]
        self.assertEqual(pinned["largest_horizontal_step"], largest_measured_step)
        self.assertEqual(pinned["steps_measured"], 28)

    def test_the_replay_table_still_says_what_the_pin_says_it_says(self):
        """The pin's numbers are re-derived here, from the committed table.

        A pinned measurement nobody recomputes is a number that drifts in
        silence.  This is the recompute, and it runs on every gate machine.
        """
        import math
        import re
        rows = []
        path = ROOT / "reports" / "move_cadence001_smoke" / "replay_output.txt"
        pattern = re.compile(
            r"\s*(\d+)\s+(\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+"
            r"(\d+\.\d+)\s+(\d+\.\d+)\s+(\d)\s+([W.])"
        )
        # The replay report is not ASCII - it carries a plus-minus sign in its
        # tolerance lines.  The rows this reads are digits either way.
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            found = pattern.match(line)
            if found:
                rows.append((float(found.group(3)), float(found.group(4))))
        self.assertEqual(len(rows), 29)
        steps = [
            math.hypot(b[0] - a[0], b[1] - a[1])
            for a, b in zip(rows, rows[1:])
        ]
        pinned = _raw()["the_measured_facts_the_radii_come_from"][
            "step_units_recomputed_from_the_replay_this_round"]
        self.assertEqual(len(steps), pinned["steps_measured"])
        self.assertAlmostEqual(
            max(steps), pinned["largest_horizontal_step"], places=2)
        self.assertAlmostEqual(
            sorted(steps)[len(steps) // 2], pinned["median_horizontal_step"],
            places=1)
        self.assertEqual(
            sum(1 for step in steps if step > 0.0),
            pinned["steps_that_moved_at_all"])

    def test_the_return_gate_refuses_to_pin_a_centre(self):
        """V112: the teleport vec3 does not position the avatar.

        So the server cannot know where a player lands, and a pinned return
        centre would be a door placed where nobody is standing.
        """
        gate = self.by_name[RETURN_GATE]
        self.assertIsNone(gate.centre)
        self.assertTrue(gate.centre_is_measured_at_runtime)
        self.assertIsNone(gate.vertical_band)
        raw_gate = [g for g in _raw()["gates"] if g["name"] == RETURN_GATE][0]
        self.assertIn("V112", raw_gate["why_this_centre_cannot_be_pinned"])

    def test_the_settle_budget_matches_one_authentic_walk(self):
        self.assertEqual(self.settings.jump_units, 2000.0)
        self.assertGreaterEqual(self.settings.report_budget, 29)

    def test_the_stage_is_never_called_a_white_map(self):
        """COO-DECISION 20260826_0246 section 1.2 - in EVERY file this lane owns.

        The first version of this test read two JSON blobs, allowed one free
        use of each forbidden phrase, and never checked the positive half of
        the order.  The adversary pass of round 4fhdxv showed one affirmative
        "white map" would have passed it green.  This one scans every file the
        lane owns and allows the phrases only on a line that is stating the
        prohibition, quoting the owner's own request, or disclaiming.
        """
        banned = ("white" + " map", "effect" + "-free", "effect" + " free")
        allowed_on_a_line_that_says = (
            "forbid", "no claim that", "the owner asked for",
            "requires it be called",
        )
        owned = [
            Path(GATE_REGISTRY_PATH),
            Path(world_scene_travel.REGISTRY_PATH),
            ROOT / "src" / "pirateforce_foundation" / "world_travel_gate.py",
            ROOT / "src" / "pirateforce_foundation" / "world_scene_travel.py",
            ROOT / "src" / "pirateforce_foundation" / "world_scene_entry.py",
            ROOT / "tests" / "test_world_scene_travel.py",
        ]
        for path in owned:
            text = path.read_text(encoding="utf-8", errors="replace")
            kept = [
                line.lower() for line in text.splitlines()
                if not any(
                    marker in line.lower()
                    for marker in allowed_on_a_line_that_says
                )
            ]
            body = "\n".join(kept)
            for word in banned:
                with self.subTest("{0}:{1}".format(path.name, word)):
                    self.assertNotIn(word, body)

    def test_the_stage_is_called_what_the_order_says_to_call_it(self):
        """The positive half of 0246: green screen, fog and environment on."""
        registry_raw = Path(
            world_scene_travel.REGISTRY_PATH).read_text(encoding="ascii")
        stage = [
            row for row in json.loads(registry_raw)["destinations"]
            if row["n_id"] == 997
        ][0]
        blob = json.dumps(stage).lower()
        for required in ("green screen", "fog", "environment"):
            with self.subTest(required):
                self.assertIn(required, blob)

    def test_the_stage_name_field_is_a_name_and_not_a_policy_notice(self):
        """Every other row carries a name; a consumer renders this field."""
        registry_raw = Path(
            world_scene_travel.REGISTRY_PATH).read_text(encoding="ascii")
        for row in json.loads(registry_raw)["destinations"]:
            with self.subTest(row["n_id"]):
                self.assertLessEqual(len(row["scene_name_ascii"]), 40)

    def test_both_files_are_ascii(self):
        for path in (GATE_REGISTRY_PATH, world_scene_travel.REGISTRY_PATH):
            with self.subTest(str(path)):
                Path(path).read_text(encoding="ascii")


class TravelGateLoadRefusalTests(unittest.TestCase):
    """Every refusal here is one that would otherwise land on a walking player."""

    def setUp(self):
        self.raw = _raw()
        self.tmp = Path(self.enterContext(__import__(
            "tempfile").TemporaryDirectory()))

    def _write(self, data) -> Path:
        path = self.tmp / "gates.json"
        path.write_text(json.dumps(data), encoding="ascii")
        return path

    def _load(self, mutate):
        data = json.loads(json.dumps(self.raw))
        mutate(data)
        return load_travel_gates(self._write(data))

    def _refusal(self, mutate) -> TravelGateRefused:
        with self.assertRaises(TravelGateRefused) as caught:
            self._load(mutate)
        return caught.exception

    def test_the_unmodified_pin_still_loads_from_a_copy(self):
        gates, settings = self._load(lambda data: None)
        self.assertEqual(len(gates), 2)
        self.assertEqual(settings.jump_units, 2000.0)

    def test_a_gate_to_an_unpinned_scene_is_refused_at_load(self):
        def mutate(data):
            data["gates"][0]["to_scene_id"] = 60000
        error = self._refusal(mutate)
        self.assertEqual(error.reason, "destination_not_pinned")
        self.assertIn("RE-077", str(error))

    def test_a_destination_with_no_spawn_is_refused(self):
        scenes = world_scene_travel.load_scene_registry()
        spawnless = world_scene_travel.SceneRegistry(tuple(
            item if item.n_id != 278 else
            world_scene_travel.SceneDestination(
                **{**item.__dict__, "spawn": None, "spawn_provenance": None})
            for item in scenes.destinations
        ))
        with self.assertRaises(TravelGateRefused) as caught:
            load_travel_gates(GATE_REGISTRY_PATH, registry=spawnless)
        self.assertEqual(caught.exception.reason, "destination_has_no_spawn")

    def test_an_arm_radius_inside_the_fire_radius_is_refused(self):
        def mutate(data):
            data["gates"][0]["arm_radius_units"] = 100.0
        self.assertIn("arm radius", str(self._refusal(mutate)))

    def test_an_arm_radius_equal_to_the_fire_radius_is_refused(self):
        """M5 from the adversary pass: the boundary case was untested.

        arm == fire is exactly the flapping the refusal message describes - a
        player on the line re-arms and re-fires on alternating reports.
        """
        def mutate(data):
            data["gates"][0]["arm_radius_units"] = (
                data["gates"][0]["fire_radius_units"])
        self.assertIn("arm radius", str(self._refusal(mutate)))

    def test_a_zero_fire_radius_is_refused(self):
        def mutate(data):
            data["gates"][0]["fire_radius_units"] = 0.0
        self.assertIn("fire radius", str(self._refusal(mutate)))

    def test_a_duplicate_gate_name_is_refused(self):
        def mutate(data):
            twin = json.loads(json.dumps(data["gates"][1]))
            twin["from_scene_id"] = 2
            data["gates"].append(twin)
        self.assertIn("pinned twice", str(self._refusal(mutate)))

    def test_an_unknown_role_is_refused(self):
        def mutate(data):
            data["gates"][0]["role"] = "shortcut"
        self.assertIn("unknown role", str(self._refusal(mutate)))

    def test_an_unknown_arrival_mode_is_refused(self):
        def mutate(data):
            data["gates"][0]["arrival"] = "wherever"
        self.assertIn("unknown arrival mode", str(self._refusal(mutate)))

    def test_a_departure_gate_may_not_measure_its_centre_at_runtime(self):
        def mutate(data):
            data["gates"][0]["centre"] = None
        self.assertIn("only a return gate", str(self._refusal(mutate)))

    def test_an_incomplete_centre_is_refused(self):
        def mutate(data):
            del data["gates"][0]["centre"]["z"]
        self.assertIn("centre is incomplete", str(self._refusal(mutate)))

    def test_a_negative_vertical_band_is_refused(self):
        def mutate(data):
            data["gates"][0]["vertical_band_units"] = -1.0
        self.assertIn("vertical band", str(self._refusal(mutate)))

    def test_a_dwell_of_one_report_is_refused(self):
        """One report inside is a tripwire, and the tripwire is the defect."""
        def mutate(data):
            data["dwell"]["reports"] = 1
        self.assertIn("dwell reports", str(self._refusal(mutate)))

    def test_a_missing_dwell_block_is_refused(self):
        def mutate(data):
            del data["dwell"]
        self.assertIn("incomplete or has unknown fields", str(self._refusal(mutate)))

    def test_a_gate_that_leads_to_its_own_scene_is_refused(self):
        def mutate(data):
            data["gates"][0]["to_scene_id"] = data["gates"][0]["from_scene_id"]
        self.assertIn("leads to the scene", str(self._refusal(mutate)))

    def test_two_gates_in_one_scene_are_refused(self):
        def mutate(data):
            twin = json.loads(json.dumps(data["gates"][0]))
            twin["name"] = "second_door"
            data["gates"].append(twin)
        self.assertIn("already has a gate", str(self._refusal(mutate)))

    def test_an_arrival_within_one_jump_of_the_door_is_refused(self):
        """The settle test reads the size of the jump, not a scene id.

        An arrival that close is indistinguishable from an ordinary step, so
        the transit would never settle and the return gate would never anchor.
        """
        def mutate(data):
            data["settle"]["jump_units"] = 100000.0
        error = self._refusal(mutate)
        self.assertEqual(error.reason, "settle_would_never_fire")

    def test_an_unknown_field_is_refused_rather_than_ignored(self):
        def mutate(data):
            data["gates"][0]["shortcut"] = True
        self.assertIn("unknown fields", str(self._refusal(mutate)))

    def test_a_broken_file_surfaces_as_a_broken_file(self):
        """N-6 from round qumhmf, applied here before anybody can repeat it.

        A JSON error laundered into "there is no gate" is a lie a reader
        cannot see through.
        """
        path = self.tmp / "gates.json"
        path.write_text("{ this is not json", encoding="ascii")
        with self.assertRaises(json.JSONDecodeError):
            load_travel_gates(path)

    def test_a_missing_file_surfaces_as_a_missing_file(self):
        with self.assertRaises(OSError):
            load_travel_gates(self.tmp / "absent.json")


class TravelGateCrossingTests(unittest.TestCase):
    def setUp(self):
        self.gates, self.settings = load_travel_gates()
        self.by_name = {gate.name: gate for gate in self.gates}
        self.out = self.by_name[DEPARTURE_GATE]
        self.centre = self.out.centre

    def _armed_set(self):
        gate_set, lines = _set()
        gate_set.observe(_home(*ATTENDED_SPAWN))
        self.assertTrue(gate_set.is_armed(DEPARTURE_GATE))
        return gate_set, lines

    def _stand(self, gate_set, point, times=None):
        """Stand still at one point, report by report, and return the fire."""
        times = self.settings.dwell_reports + 1 if times is None else times
        result = None
        for _ in range(times):
            got = gate_set.observe(_home(*point))
            result = result or got
        return result

    def test_the_first_report_arms_and_does_not_fire(self):
        gate_set, lines = _set()
        self.assertIsNone(gate_set.observe(_home(*ATTENDED_SPAWN)))
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("WORLD_TRAVEL_ARMED"))
        self.assertIn("gate=" + DEPARTURE_GATE, lines[0])

    def test_standing_in_the_zone_departs(self):
        gate_set, lines = self._armed_set()
        crossing = (self.centre[0] + 100.0, self.centre[1], self.centre[2])
        departure = self._stand(gate_set, crossing)
        self.assertIsInstance(departure, TravelDeparture)
        self.assertEqual(departure.gate.name, DEPARTURE_GATE)
        self.assertEqual(
            departure.teleport_fields,
            (278, 0, -13270.0576171875, 22794.2734375, -2492.7685546875),
        )
        self.assertEqual(departure.arrival.scene_id, 278)
        self.assertEqual(departure.left_from, _home(*crossing))
        self.assertIn("TELEPORT", departure.action_label)
        self.assertTrue(any(
            line.startswith("WORLD_TRAVEL_DEPART ") for line in lines))

    def test_walking_through_the_zone_does_not_depart(self):
        """THE TRAPDOOR TEST.  Remove the dwell rule and this goes red.

        The gate sits 1592.99 units from the position an attended run found
        the character on, so 993 of those units are walking - and that walk is
        the one GT-078 asks the owner to take to count NPCs.  A player who
        crosses the zone on the way somewhere else must come out the other
        side still in Port Royal.
        """
        gate_set, _ = self._armed_set()
        # Straight through the middle at the LARGEST step measured in the one
        # authentic walk, then out the far side.
        step = 538.44
        start_x = self.centre[0] - 1400.0
        fired = []
        for index in range(6):
            row = _home(start_x + index * step, self.centre[1], self.centre[2])
            got = gate_set.observe(row)
            if got is not None:
                fired.append(got)
        self.assertEqual(fired, [])
        self.assertEqual(gate_set.departures, 0)
        # And at the median step, which spends far longer inside.
        gate_set, _ = self._armed_set()
        step = 139.26
        start_x = self.centre[0] - 1400.0
        for index in range(22):
            got = gate_set.observe(
                _home(start_x + index * step, self.centre[1], self.centre[2]))
            self.assertIsNone(got)
        self.assertEqual(gate_set.departures, 0)

    def test_a_dwell_that_is_interrupted_starts_again(self):
        gate_set, _ = self._armed_set()
        point = (self.centre[0] + 50.0, self.centre[1], self.centre[2])
        gate_set.observe(_home(*point))
        gate_set.observe(_home(*point))
        self.assertEqual(gate_set.dwell(DEPARTURE_GATE), 1)
        # One step, however small, is movement.
        moved = (point[0] + self.settings.still_units + 0.5, point[1], point[2])
        self.assertIsNone(gate_set.observe(_home(*moved)))
        self.assertEqual(gate_set.dwell(DEPARTURE_GATE), 0)
        self.assertEqual(gate_set.departures, 0)

    def test_the_dwell_counter_is_reported_while_it_counts(self):
        gate_set, lines = self._armed_set()
        point = (self.centre[0], self.centre[1], self.centre[2])
        gate_set.observe(_home(*point))
        gate_set.observe(_home(*point))
        dwell_lines = [
            line for line in lines if line.startswith("WORLD_TRAVEL_DWELL")]
        self.assertTrue(dwell_lines)
        self.assertIn(
            "still_reports=1/{0}".format(self.settings.dwell_reports),
            dwell_lines[0])

    def test_the_action_label_carries_teleport_for_the_move_gate(self):
        """runtime.py:_move_authority_note_server_moves keys on the substring.

        Without it, the gate's own teleport makes the next honest client
        reading look like a lie and the durable row freezes for the session.
        """
        gate_set, _ = self._armed_set()
        departure = self._stand(gate_set, self.centre)
        self.assertIn("TELEPORT", departure.action_label)

    def test_an_unarmed_gate_does_not_fire_however_long_you_stand(self):
        gate_set, _ = _set()
        self.assertIsNone(self._stand(gate_set, self.centre, times=10))
        self.assertEqual(gate_set.departures, 0)

    def test_standing_just_outside_the_zone_does_not_fire(self):
        gate_set, _ = self._armed_set()
        outside = (
            self.centre[0] + self.out.fire_radius + 1.0,
            self.centre[1], self.centre[2],
        )
        self.assertIsNone(self._stand(gate_set, outside, times=10))
        self.assertEqual(gate_set.dwell(DEPARTURE_GATE), 0)

    def test_the_fire_radius_boundary_is_inclusive_and_pinned(self):
        gate_set, _ = self._armed_set()
        on_the_line = (
            self.centre[0] + self.out.fire_radius,
            self.centre[1], self.centre[2],
        )
        self.assertIsInstance(
            self._stand(gate_set, on_the_line), TravelDeparture)

    def test_distance_is_measured_in_x_and_y_and_not_in_x_and_z(self):
        """M1 from the adversary pass: _horizontal's y axis was untested.

        A gate that measured the wrong plane would fire on a player standing
        5000 units north of the door, and every other test moved in x.
        """
        gate_set, _ = self._armed_set()
        due_north = (
            self.centre[0],
            self.centre[1] + self.out.fire_radius + 100.0,
            self.centre[2],
        )
        self.assertIsNone(self._stand(gate_set, due_north, times=10))
        self.assertEqual(gate_set.departures, 0)
        # And a player who is inside in x and y fires even with z untouched,
        # which is what separates the y test above from a z test.
        inside_north = (
            self.centre[0], self.centre[1] + 100.0, self.centre[2])
        self.assertIsInstance(
            self._stand(gate_set, inside_north), TravelDeparture)

    def test_height_is_checked_where_there_is_ground_evidence(self):
        gate_set, _ = self._armed_set()
        overhead = (
            self.centre[0], self.centre[1],
            self.centre[2] + self.out.vertical_band + 1.0,
        )
        self.assertIsNone(self._stand(gate_set, overhead, times=10))
        self.assertEqual(gate_set.departures, 0)

    def test_the_vertical_band_is_the_pinned_move_authority_number(self):
        """M4 from the adversary pass: the band was self-referential.

        Reading the band off the loaded gate and adding one can never fail for
        a wrong value.  This pins the value itself, and to the module the
        project already argued about it in.
        """
        from pirateforce_foundation import move_authority_hypothesis
        policy = move_authority_hypothesis._SPEED_GATE_POLICY
        self.assertEqual(self.out.vertical_band, 400.0)
        self.assertEqual(
            self.out.vertical_band, policy.max_vertical_step_units)
        self.assertEqual(self.settings.jump_units, policy.max_step_units)

    def test_a_report_in_another_scene_does_not_touch_this_gate(self):
        gate_set, _ = self._armed_set()
        for _ in range(10):
            self.assertIsNone(gate_set.observe(
                Position(2, SCENE_SEQUENCE, *self.centre, 0.0)))
        self.assertEqual(gate_set.departures, 0)

    def test_a_nonfinite_row_is_refused_by_name_and_does_not_raise(self):
        gate_set, lines = self._armed_set()
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(bad):
                self.assertIsNone(gate_set.observe(
                    _home(bad, self.centre[1], self.centre[2])))
        self.assertEqual(
            sum(line.startswith("WORLD_TRAVEL_REFUSED") for line in lines), 3)
        self.assertEqual(gate_set.departures, 0)

    def test_observe_refuses_anything_that_is_not_a_row(self):
        gate_set, _ = _set()
        for bad in ((1, 0, 0.0, 0.0, 0.0), None, "1,0,0,0,0", 278):
            with self.subTest(repr(bad)):
                with self.assertRaises(ValueError):
                    gate_set.observe(bad)

    def test_the_census_is_not_offered_to_the_test_stage(self):
        gate_set, _ = self._armed_set()
        departure = self._stand(gate_set, self.centre)
        self.assertIsNone(departure.population_source)
        self.assertIn("population_source=None", departure.console_line)


class TravelTransitTests(unittest.TestCase):
    def setUp(self):
        self.gates, self.settings = load_travel_gates()
        self.by_name = {gate.name: gate for gate in self.gates}
        self.centre = self.by_name[DEPARTURE_GATE].centre
        self.set, self.lines = _set()
        self.set.observe(_home(*ATTENDED_SPAWN))
        self.departure = None
        for _ in range(self.settings.dwell_reports + 1):
            self.departure = self.departure or self.set.observe(
                _home(*self.centre))
        self.assertIsNotNone(self.departure)

    def _report(self, x, y, z, scene_id=278):
        return self.set.observe(Position(scene_id, SCENE_SEQUENCE, x, y, z, 0.0))

    def _walk_away(self, steps, size=538.44):
        """Keep walking in the old scene at the largest measured real step."""
        for index in range(1, steps + 1):
            self._report(
                self.centre[0] + index * size, self.centre[1], self.centre[2])

    def test_old_scene_reports_during_the_load_are_ignored(self):
        self._walk_away(3)
        self.assertTrue(self.set.in_transit)
        self.assertEqual(self.set.departures, 1)

    def test_walking_away_at_the_measured_cadence_never_settles(self):
        """THE PING-PONG TEST.  The settle test is a STEP, not a displacement.

        The adversary pass of round 4fhdxv walked one straight line at 538.44
        units per report against a settle test that measured distance from the
        crossing row, and produced six durable-row rewrites in 48 reports.  A
        cumulative test cannot tell "walked a long way in the old scene" from
        "arrived in the new one".
        """
        self._walk_away(self.settings.report_budget)
        self.assertEqual(self.set.departures, 1)
        self.assertIsNone(self.set.measured_centre(RETURN_GATE))
        stranded = [
            line for line in self.lines
            if line.startswith("WORLD_TRAVEL_STRANDED")
        ]
        self.assertEqual(len(stranded), 1)

    def test_the_arrival_jump_settles_and_anchors_the_way_back(self):
        self.assertIsNone(self._report(-13200.0, 22800.0, -2492.0))
        self.assertFalse(self.set.in_transit)
        self.assertEqual(
            self.set.measured_centre(RETURN_GATE), (-13200.0, 22800.0, -2492.0))
        self.assertTrue(any(
            line.startswith("WORLD_TRAVEL_RETURN_ANCHORED ")
            for line in self.lines))
        self.assertTrue(any(
            line.startswith("WORLD_TRAVEL_SETTLED") for line in self.lines))

    def test_landing_inside_a_gate_does_not_fire_it(self):
        """Delete the disarm-on-switch rule and this goes red."""
        self._report(-13200.0, 22800.0, -2492.0)
        for _ in range(8):
            self.assertIsNone(self._report(-13200.0, 22800.0, -2492.0))
        self.assertEqual(self.set.departures, 1)
        self.assertFalse(self.set.is_armed(RETURN_GATE))

    def test_a_straggler_frame_cannot_arm_the_way_home(self):
        """The report that carries the pre-switch position, re-stamped.

        TargetPosVital has no scene identity of its own, so the runtime stamps
        every reading with the scene the SERVER believes in.  One late frame
        from before the switch therefore arrives looking like a position in
        the new scene, thousands of units from the landing - which is exactly
        the shape that arms a gate.
        """
        self._report(-13200.0, 22800.0, -2492.0)
        straggler = self._report(
            self.centre[0], self.centre[1], self.centre[2])
        self.assertIsNone(straggler)
        self.assertFalse(self.set.is_armed(RETURN_GATE))
        self.assertTrue(any(
            line.startswith("WORLD_TRAVEL_DISCONTINUITY")
            for line in self.lines))
        # And the honest report that follows it is a discontinuity too, so it
        # cannot arm either.  Two frames of caution, not one.
        self.assertIsNone(self._report(-13200.0, 22800.0, -2492.0))
        self.assertFalse(self.set.is_armed(RETURN_GATE))
        self.assertEqual(self.set.departures, 1)

    def test_the_way_back_needs_a_walk_out_and_a_stop(self):
        self._report(-13200.0, 22800.0, -2492.0)
        self.assertIsNone(self._report(-11500.0, 22800.0, -2492.0))
        self.assertTrue(self.set.is_armed(RETURN_GATE))
        back = None
        for _ in range(self.settings.dwell_reports + 1):
            back = back or self._report(-13100.0, 22800.0, -2492.0)
        self.assertIsInstance(back, TravelDeparture)
        self.assertEqual(back.gate.name, RETURN_GATE)
        self.assertEqual(back.arrival.scene_id, 1)

    def test_the_return_row_is_the_row_the_player_left_that_scene_on(self):
        self._report(-13200.0, 22800.0, -2492.0)
        self._report(-11500.0, 22800.0, -2492.0)
        back = None
        for _ in range(self.settings.dwell_reports + 1):
            back = back or self._report(-13100.0, 22800.0, -2492.0)
        self.assertEqual(back.arrival.x, self.centre[0])
        self.assertEqual(back.arrival.y, self.centre[1])
        self.assertIn("arrival_source=remembered_row", back.console_line)
        self.assertEqual(self.set.left_from(1).scene_id, 1)
        self.assertEqual(self.set.left_from(278).scene_id, 278)

    def test_a_relogged_player_is_given_a_way_home_under_its_own_name(self):
        """The character whose row already said 278 when the session opened.

        Their travelling happened in a process that is gone.  Without this the
        durable row walls them into the scene with no door, on every login,
        forever.  It is a GUESS, and it logs under a different event name than
        a landing this session watched arrive, so a reader can tell them apart.
        """
        gate_set, lines = _set()
        first = Position(278, SCENE_SEQUENCE, -13200.0, 22800.0, -2492.0, 0.0)
        self.assertIsNone(gate_set.observe(first))
        self.assertEqual(
            gate_set.measured_centre(RETURN_GATE), (-13200.0, 22800.0, -2492.0))
        unverified = [
            line for line in lines
            if line.startswith("WORLD_TRAVEL_RETURN_ANCHORED_UNVERIFIED")
        ]
        self.assertEqual(len(unverified), 1)
        self.assertIn("no_jump_was_observed=true", unverified[0])
        self.assertFalse(any(
            line.startswith("WORLD_TRAVEL_RETURN_ANCHORED ") for line in lines))
        gate_set.observe(
            Position(278, SCENE_SEQUENCE, -11500.0, 22800.0, -2492.0, 0.0))
        back = None
        for _ in range(self.settings.dwell_reports + 1):
            back = back or gate_set.observe(
                Position(278, SCENE_SEQUENCE, -13100.0, 22800.0, -2492.0, 0.0))
        self.assertIsInstance(back, TravelDeparture)
        self.assertEqual(back.arrival, world_scene_travel.home_return_position())
        self.assertIn("arrival_source=pinned_home_row_no_memory", back.console_line)

    def test_a_strand_does_not_anchor_the_way_home_on_the_old_scene(self):
        """After a strand the client never loaded, so its reports are lies."""
        self._walk_away(self.settings.report_budget + 2)
        self.assertFalse(self.set.in_transit)
        self.assertEqual(self.set.departures, 1)
        self.assertIsNone(self.set.measured_centre(RETURN_GATE))
        self._report(self.centre[0] + 5.0, self.centre[1], self.centre[2])
        self.assertIsNone(self.set.measured_centre(RETURN_GATE))

    def test_a_transit_never_settles_and_says_so(self):
        self._walk_away(self.settings.report_budget)
        stranded = [
            line for line in self.lines
            if line.startswith("WORLD_TRAVEL_STRANDED")
        ]
        self.assertEqual(len(stranded), 1)
        # The line has to carry the row to put back, or it is not a recovery.
        self.assertIn("restore_row=(1,0,", stranded[0])
        self.assertIn("restore_row_is_remembered=True", stranded[0])
        self.assertFalse(self.set.in_transit)

    def test_the_strand_line_is_said_once_and_not_every_report(self):
        self._walk_away(self.settings.report_budget * 3)
        self.assertEqual(
            sum(line.startswith("WORLD_TRAVEL_STRANDED") for line in self.lines),
            1,
        )

    def test_a_round_trip_leaves_the_player_standing_in_a_closed_door(self):
        self._report(-13200.0, 22800.0, -2492.0)
        self._report(-11500.0, 22800.0, -2492.0)
        for _ in range(self.settings.dwell_reports + 1):
            self._report(-13100.0, 22800.0, -2492.0)
        # Home again, and the arrival row is the gate's own doorstep.
        self.set.observe(
            Position(1, SCENE_SEQUENCE, -13100.0, 22800.0, -2492.0, 0.0))
        for _ in range(8):
            self.assertIsNone(self.set.observe(_home(*self.centre)))
        self.assertEqual(self.set.departures, 2)

    def test_a_second_departure_re_measures_the_landing(self):
        """A landing measured on trip one must not be reused on trip two."""
        self._report(-13200.0, 22800.0, -2492.0)
        self._report(-11500.0, 22800.0, -2492.0)
        for _ in range(self.settings.dwell_reports + 1):
            self._report(-13100.0, 22800.0, -2492.0)
        self.set.observe(_home(*ATTENDED_SPAWN))
        self.assertEqual(
            self.set.measured_centre(RETURN_GATE), (-13200.0, 22800.0, -2492.0))
        self.assertIsNone(self.set.observe(_home(*ATTENDED_SPAWN)))
        second = None
        for _ in range(self.settings.dwell_reports + 1):
            second = second or self.set.observe(_home(*self.centre))
        self.assertIsInstance(second, TravelDeparture)
        self.assertEqual(self.set.departures, 3)
        self.assertIsNone(self.set.measured_centre(RETURN_GATE))


class TravelReportTests(unittest.TestCase):
    def setUp(self):
        self.set, self.lines = _set()
        gates = {gate.name: gate for gate in self.set.gates}
        self.settings = load_travel_gates()[1]
        self.centre = gates[DEPARTURE_GATE].centre
        self.set.observe(_home(*ATTENDED_SPAWN))
        self.departure = None
        for _ in range(self.settings.dwell_reports + 1):
            self.departure = self.departure or self.set.observe(
                _home(*self.centre))

    def test_the_report_carries_the_two_nonclaims_a_reader_forgets(self):
        report = departure_report(self.departure)
        self.assertIs(report["avatar_position_is_not_set_by_this_teleport"], True)
        self.assertEqual(report["remote_actors_after_switch"], "unknown_RE077_T5")

    def test_the_report_says_the_stage_has_no_authored_entry(self):
        report = departure_report(self.departure)
        self.assertIs(report["destination_has_authored_entry"], False)
        self.assertIs(report["destination_persists_characters"], False)
        self.assertIs(report["destination_sent_before"], False)

    def test_the_console_line_carries_the_row_to_restore(self):
        line = self.departure.console_line
        self.assertIn("row_before=(1,0,", line)
        self.assertIn("arrival_row=(278,0,", line)
        self.assertIn("model=Bg1177", line)
        self.assertIn("V112", line)
        self.assertIn("unknown_RE077_T5", line)

    def test_the_report_refuses_anything_that_is_not_a_departure(self):
        for bad in (None, {}, "departure", self.departure.gate):
            with self.subTest(repr(bad)[:24]):
                with self.assertRaises(ValueError):
                    departure_report(bad)

    def test_every_console_line_is_ascii(self):
        for line in self.lines:
            with self.subTest(line[:40]):
                line.encode("ascii")


class TravelGateWritesNothingTests(unittest.TestCase):
    """A pure module that quietly wrote a file would be a lane nobody audited."""

    def test_the_module_opens_nothing_but_its_own_pin(self):
        import ast
        source = Path(
            ROOT / "src" / "pirateforce_foundation" / "world_travel_gate.py"
        ).read_text(encoding="ascii")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = None
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                self.assertNotIn(name, ("write_text", "write_bytes", "open"))
                if name == "print":
                    self.fail("print is the caller's choice, not this module's")
                for keyword in node.keywords:
                    self.assertNotEqual(keyword.arg, "file")

    def test_a_full_round_trip_creates_no_files(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            before = sorted(Path(tmp).iterdir())
            gate_set, _ = _set()
            gates = {gate.name: gate for gate in gate_set.gates}
            centre = gates[DEPARTURE_GATE].centre
            gate_set.observe(_home(*ATTENDED_SPAWN))
            gate_set.observe(_home(*centre))
            gate_set.observe(Position(278, SCENE_SEQUENCE, 980.0, 1010.0, -30.0, 0.0))
            gate_set.observe(Position(278, SCENE_SEQUENCE, 3000.0, 1010.0, -30.0, 0.0))
            gate_set.observe(Position(278, SCENE_SEQUENCE, 1100.0, 1010.0, -30.0, 0.0))
            self.assertEqual(sorted(Path(tmp).iterdir()), before)


class TravelGateEmitContractTests(unittest.TestCase):
    def test_a_console_that_raises_does_not_leave_a_half_crossed_player(self):
        """The lines go out before the state moves, on purpose.

        If the emit raises, nothing has been recorded as having happened, so
        the next report re-tries the same crossing rather than leaving a
        player in a transit nobody can see.
        """
        def angry(_line):
            raise RuntimeError("console is gone")

        gate_set = TravelGateSet(emit=angry)
        gates = {gate.name: gate for gate in gate_set.gates}
        centre = gates[DEPARTURE_GATE].centre
        with self.assertRaises(RuntimeError):
            gate_set.observe(_home(*ATTENDED_SPAWN))
        self.assertFalse(gate_set.is_armed(DEPARTURE_GATE))
        self.assertFalse(gate_set.in_transit)
        self.assertEqual(gate_set.departures, 0)

    def test_a_console_that_raises_at_the_fire_leaves_no_hidden_transit(self):
        """M2 from the adversary pass: only the ARM emit was covered.

        With the emit moved after the state commit, a raising console leaves
        departures=1, a transit latch set, every gate disarmed and no teleport
        sent - a player frozen in an invisible transit for 30 reports, which
        is the exact failure the comment in _fire claims to prevent.
        """
        lines = []
        settings = load_travel_gates()[1]

        def angry(line):
            lines.append(line)
            if line.startswith("WORLD_TRAVEL_DEPART "):
                raise RuntimeError("console is gone")

        gate_set = TravelGateSet(emit=angry)
        gates = {gate.name: gate for gate in gate_set.gates}
        centre = gates[DEPARTURE_GATE].centre
        gate_set.observe(_home(*ATTENDED_SPAWN))
        with self.assertRaises(RuntimeError):
            for _ in range(settings.dwell_reports + 1):
                gate_set.observe(_home(*centre))
        self.assertEqual(gate_set.departures, 0)
        self.assertFalse(gate_set.in_transit)
        self.assertIsNone(gate_set.left_from(1))
        self.assertTrue(gate_set.is_armed(DEPARTURE_GATE))

    def test_emit_must_be_callable(self):
        with self.assertRaises(ValueError):
            TravelGateSet(emit="print")

    def test_is_armed_refuses_a_gate_that_does_not_exist(self):
        gate_set, _ = _set()
        with self.assertRaises(TravelGateRefused):
            gate_set.is_armed("back_door")


if __name__ == "__main__":
    unittest.main()
