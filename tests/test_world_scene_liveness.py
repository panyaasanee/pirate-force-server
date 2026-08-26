"""LANE-A BUILD-002 / M2: what is known about a row that names another scene.

THIS FILE EXISTS IN THE SHAPE THE ADVERSARIAL PASS LEFT IT.  The module was
written to REWRITE a stranded character's row at login and the adversary
proved, by running both branches against the real gate, that it must not.  The
load-bearing tests are therefore the ones that keep the retraction true:

* ``test_the_default_never_rewrites_a_row`` - the retraction itself.  The
  settle line's scene id is written by the SERVER, so a rewrite acts on a
  coordinate delta wearing a scene id, and in one of two unmeasured branches
  it yanks a player who arrived safely back to town at every login.
* ``test_a_settle_at_the_departure_scene_is_refused_for_the_destination`` -
  the false learn, driven through the REAL gate.  A client still standing in
  Port Royal produces a settle labelled 278 the moment one report jumps.
  Without the cross-check the ledger trusts 278 on Port Royal coordinates.
* ``test_a_crossing_that_strands_records_nothing`` - the starved ledger.  If
  an arrival does not move the coordinates, nothing ever settles.
* ``test_only_the_settle_line_can_teach_the_ledger`` - the mutant, with the
  refusal list RE-DERIVED from world_travel_gate by AST rather than typed out.
  Eight of its lines carry a scene_id= field and one of them is emitted in
  exactly the case this module cares about.
* ``test_the_parser_is_pinned_to_the_real_gate`` - the drift.  The line is a
  console string with no schema, so the test feeds this parser what the real
  module actually emitted.
"""

import ast
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    world_scene_liveness,
    world_scene_travel,
    world_travel_gate,
)
from pirateforce_foundation.model import Position
from pirateforce_foundation.population import SCENE_SEQUENCE
from pirateforce_foundation.world_scene_liveness import (
    CROSS_CHECK_RADIUS_UNITS,
    DECISION_FLAG,
    DECISION_HONOUR,
    DECISION_SEND_HOME,
    REASON_HOME_ROW,
    REASON_HOME_UNAVAILABLE,
    REASON_NO_RECORD,
    REASON_RECORDED_BEFORE_THIS_PROCESS,
    REASON_RECORDED_THIS_PROCESS,
    REASON_STOOD_DOWN,
    REASON_UNREADABLE_LEDGER,
    REASON_UNREADABLE_ROW,
    SETTLED_PREFIX,
    SceneLivenessLedger,
    decide,
    liveness_console_line,
    liveness_report,
)

MODULE_PATH = ROOT / "src" / "pirateforce_foundation" / "world_scene_liveness.py"
GATE_PATH = ROOT / "src" / "pirateforce_foundation" / "world_travel_gate.py"

STAGE = world_scene_travel.TEST_STAGE_SCENE_ID          # 278
HOME = world_scene_travel.HOME_SCENE_ID                 # 1
DEPARTURE_GATE = "port_royal_columbus_departure"

# Where an attended run actually found the character on 2026-08-23 (GT-045).
ATTENDED_SPAWN = (-8553.947265625, -2579.68896484375, 186.0)


class _Exploding:
    def __str__(self):
        raise RuntimeError("this object refuses to be printed")


class _Row(Position):
    """A Position subclass.  tests/test_world_travel_gate.py builds these, so
    an exact-type gate here would switch the module off for a shape that is
    already in the tree."""


JUNK = (
    None, 0, 1, -1, 278, 1.5, True, False, "", "278",
    b"278", (), (1, 0, 0.0, 0.0, 0.0), [1], {"scene_id": 1},
    object(), _Exploding(), float("nan"),
    "hong", "line\rwith\rreturns",
)


def _row(scene_id, x=-13270.0, y=22794.0, z=-2492.7) -> Position:
    return Position(scene_id, SCENE_SEQUENCE, x, y, z, 0.0)


def _stage_row() -> Position:
    return _row(STAGE)


def _settle_line(scene_id, x, y, z, jump=9000.0, reports=2) -> str:
    """Built by the real producer, never typed out by hand."""
    return world_travel_gate._settled_line(
        Position(scene_id, SCENE_SEQUENCE, x, y, z, 0.0), jump, reports)


class LedgerSeedTests(unittest.TestCase):
    def test_the_module_is_not_a_scenario(self):
        self.assertIs(world_scene_liveness.test_only, False)
        self.assertIs(world_scene_liveness.production_allowed, True)

    def test_the_seed_is_exactly_the_ids_this_tree_already_pins(self):
        ledger = SceneLivenessLedger.seeded()
        self.assertEqual(
            ledger.observed_ids,
            tuple(sorted(world_scene_travel.MEASURED_SCENE_IDS)))
        self.assertEqual(ledger.observed_ids, (1, 2))
        for fact in ledger.facts():
            with self.subTest(fact.scene_id):
                self.assertFalse(fact.from_this_process)
                self.assertFalse(fact.cross_checked)
                self.assertTrue(fact.evidence.strip())

    def test_the_scene_two_evidence_still_matches_the_ledger_it_cites(self):
        """M10: the shipped evidence text was completely unpinned, so it could
        be rewritten to cite a line that does not exist and nothing noticed."""
        fact = SceneLivenessLedger.seeded().fact(2)
        self.assertIn("SCENE-001", fact.evidence)
        rows = [
            line for line in
            (ROOT / "docs" / "EXPERIMENT_LEDGER.md").read_text(
                encoding="utf-8").splitlines()
            if line.startswith("| SCENE-001 ")
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn(
            "the client loaded and rendered Prison Exile Island", rows[0])

    def test_the_stage_is_not_seeded(self):
        """278 is the scene the door leads to and no client has opened it.

        If this ever goes green the guard has been defeated by a seed, which
        the module docstring names as worse than no guard.
        """
        ledger = SceneLivenessLedger.seeded()
        self.assertFalse(ledger.knows(STAGE))
        self.assertIsNone(ledger.fact(STAGE))

    def test_the_way_home_is_the_registry_row_not_a_second_copy(self):
        """Re-derived from the pin, not compared against the same call."""
        import json
        raw = json.loads(
            Path(world_scene_travel.REGISTRY_PATH).read_text(encoding="ascii"))
        pinned = [
            item for item in raw["destinations"] if item["n_id"] == HOME][0]
        home = SceneLivenessLedger.seeded().home
        self.assertEqual(home.scene_id, HOME)
        self.assertEqual(
            [home.x, home.y, home.z],
            [pinned["spawn"]["x"], pinned["spawn"]["y"], pinned["spawn"]["z"]])

    def test_an_empty_ledger_knows_nothing(self):
        ledger = SceneLivenessLedger.empty()
        self.assertEqual(ledger.observed_ids, ())
        self.assertIsNone(ledger.home)
        self.assertIsNone(ledger.registry)

    def test_a_true_is_not_scene_one(self):
        """bool is an int subclass; the exact-type gate is what excludes it."""
        ledger = SceneLivenessLedger.seeded()
        self.assertIsNone(ledger.fact(True))
        self.assertFalse(ledger.knows(True))
        with self.assertRaises(ValueError):
            ledger.observe_arrival(True, "evidence")


class PreloadTests(unittest.TestCase):
    def tearDown(self):
        SceneLivenessLedger.forget_preloaded()

    def test_from_preloaded_hands_back_the_one_that_was_built(self):
        built = SceneLivenessLedger.preload()
        self.assertIs(SceneLivenessLedger.from_preloaded(), built)

    def test_without_a_preload_the_session_gets_a_ledger_that_stands_down(self):
        """The failure mode of finding nothing must be doing nothing.

        An empty ledger would flag every character in the game; an inert one
        flags none and names the reason in the console line.
        """
        SceneLivenessLedger.forget_preloaded()
        inert = SceneLivenessLedger.from_preloaded()
        self.assertEqual(inert.stood_down, "preload_was_never_called")
        decision = decide(_stage_row(), inert)
        self.assertEqual(decision.decision, DECISION_HONOUR)
        self.assertEqual(decision.reason, REASON_STOOD_DOWN)
        self.assertIn("stood_down=preload_was_never_called",
                      liveness_console_line(decision, inert))

    def test_a_stand_down_reason_is_always_printable(self):
        ledger = SceneLivenessLedger.seeded()
        for bad in (None, "", _Exploding(), "arena\rlane", "lane hong 1",
                    object(), 12):
            with self.subTest(repr(type(bad))):
                reason = ledger.stand_down(bad)
                self.assertTrue(reason.isascii())
                self.assertNotIn(" ", reason)
                self.assertNotIn("\r", reason)
                self.assertTrue(reason)

    def test_standing_down_beats_every_other_branch(self):
        ledger = SceneLivenessLedger.seeded()
        ledger.stand_down("an_opt_in_scenario_is_active")
        for row in (_stage_row(), _row(HOME), None, _row(2)):
            with self.subTest(repr(row)):
                decision = decide(row, ledger, rewrite=True)
                self.assertEqual(decision.decision, DECISION_HONOUR)
                self.assertEqual(decision.reason, REASON_STOOD_DOWN)
                self.assertFalse(decision.rewrites_the_row)


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.ledger = SceneLivenessLedger.seeded()

    def test_the_default_never_rewrites_a_row(self):
        """THE RETRACTION.  The adversarial pass of the round that built this
        module proved the evidence cannot tell "the scene opened" from "the
        coordinates moved", in both directions, against the real gate.  So the
        default reports and does not act, and the row that comes back is the
        row that went in.
        """
        import inspect
        self.assertIs(
            inspect.signature(decide).parameters["rewrite"].default, False)
        row = _stage_row()
        decision = decide(row, self.ledger)
        self.assertEqual(decision.decision, DECISION_FLAG)
        self.assertEqual(decision.reason, REASON_NO_RECORD)
        self.assertFalse(decision.rewrites_the_row)
        self.assertFalse(decision.sends_home)
        self.assertIs(decision.position, row)
        self.assertEqual(decision.home_if_asked, self.ledger.home)

    def test_the_rewrite_is_reachable_and_says_what_it_would_do(self):
        decision = decide(_stage_row(), self.ledger, rewrite=True)
        self.assertEqual(decision.decision, DECISION_SEND_HOME)
        self.assertTrue(decision.rewrites_the_row)
        self.assertTrue(decision.sends_home)
        self.assertEqual(decision.position, self.ledger.home)
        self.assertEqual(decision.stored.scene_id, STAGE)

    def test_a_recorded_arrival_is_honoured_afterwards(self):
        self.ledger.observe_arrival(STAGE, "a tester stood in it")
        for rewrite in (False, True):
            with self.subTest(rewrite=rewrite):
                decision = decide(_stage_row(), self.ledger, rewrite=rewrite)
                self.assertEqual(decision.decision, DECISION_HONOUR)
                self.assertEqual(decision.reason, REASON_RECORDED_THIS_PROCESS)
                self.assertFalse(decision.rewrites_the_row)

    def test_an_inherited_fact_says_so_rather_than_claiming_this_boot_saw_it(self):
        decision = decide(_row(2, 26905.0, 21185.0, 1680.0), self.ledger)
        self.assertEqual(decision.decision, DECISION_HONOUR)
        self.assertEqual(decision.reason, REASON_RECORDED_BEFORE_THIS_PROCESS)
        self.assertFalse(decision.fact.from_this_process)

    def test_a_home_row_is_honoured_by_a_ledger_that_knows_nothing(self):
        for ledger in (SceneLivenessLedger.seeded(),
                       SceneLivenessLedger.empty()):
            with self.subTest(ledger.observed_ids):
                decision = decide(
                    _row(HOME, *ATTENDED_SPAWN), ledger, rewrite=True)
                self.assertEqual(decision.decision, DECISION_HONOUR)
                self.assertEqual(decision.reason, REASON_HOME_ROW)
                self.assertFalse(decision.rewrites_the_row)

    def test_the_row_that_comes_back_is_the_row_that_went_in(self):
        """A module that rebuilt the row would drop the heading and the
        scene_seq, and the caller would never see it happen."""
        row = Position(STAGE, 7, 1.0, 2.0, 3.0, 4.5)
        self.ledger.observe_arrival(STAGE, "recorded")
        decision = decide(row, self.ledger)
        self.assertIs(decision.position, row)
        self.assertEqual(decision.position.heading, 4.5)
        self.assertEqual(decision.position.scene_seq, 7)

    def test_a_position_subclass_is_still_a_row(self):
        """M5 / D7: an exact-type gate switched the module off in silence for
        a shape tests/test_world_travel_gate.py already builds."""
        row = _Row(STAGE, SCENE_SEQUENCE, 1.0, 2.0, 3.0, 0.0)
        decision = decide(row, self.ledger)
        self.assertEqual(decision.decision, DECISION_FLAG)
        self.assertEqual(decision.scene_id, STAGE)
        self.assertIs(decision.stored, row)

    def test_a_broken_ledger_says_the_ledger_is_broken(self):
        """M15 / D6: this branch used to return position=None while the class
        docstring promised position is always the row to use, and it blamed
        the row for a fault in the wiring."""
        row = _stage_row()
        for bad in JUNK:
            with self.subTest(repr(type(bad))):
                decision = decide(row, bad)
                self.assertEqual(decision.decision, DECISION_HONOUR)
                self.assertEqual(decision.reason, REASON_UNREADABLE_LEDGER)
                self.assertIs(decision.position, row)
                self.assertIs(decision.stored, row)
                self.assertEqual(decision.scene_id, STAGE)
                self.assertFalse(decision.rewrites_the_row)

    def test_decide_never_raises(self):
        for bad in JUNK:
            with self.subTest(repr(type(bad))):
                decision = decide(bad, self.ledger, rewrite=True)
                self.assertEqual(decision.decision, DECISION_HONOUR)
                self.assertEqual(decision.reason, REASON_UNREADABLE_ROW)
                self.assertIsNone(decision.position)

    def test_a_scene_id_outside_the_wire_field_is_not_decided_about(self):
        """scene_id is a u16 on the wire.  A row outside it is unreadable, not
        an unrecorded scene: acting on it would hide a row that
        store.save_position should never have accepted."""
        for scene_id in (-1, 0x10000, 999999):
            with self.subTest(scene_id):
                decision = decide(_row(scene_id), self.ledger, rewrite=True)
                self.assertEqual(decision.reason, REASON_UNREADABLE_ROW)
                self.assertFalse(decision.rewrites_the_row)

    def test_scene_zero_is_decided_about(self):
        """0 is inside the u16 field and is the id RE-077 traced to the
        table-miss branch, so it is the strongest case for a flag, not an
        unreadable row."""
        decision = decide(_row(0), self.ledger)
        self.assertEqual(decision.decision, DECISION_FLAG)
        self.assertEqual(decision.reason, REASON_NO_RECORD)

    def test_with_no_way_home_the_row_stands_and_the_reason_says_why(self):
        decision = decide(_stage_row(), SceneLivenessLedger.empty(),
                          rewrite=True)
        self.assertEqual(decision.decision, DECISION_HONOUR)
        self.assertEqual(decision.reason, REASON_HOME_UNAVAILABLE)
        self.assertFalse(decision.rewrites_the_row)


class CrossCheckTests(unittest.TestCase):
    """D1a: the false learn, and the arithmetic that refuses it."""

    def setUp(self):
        self.registry = world_scene_travel.load_scene_registry()
        self.ledger = SceneLivenessLedger.seeded(self.registry)

    def test_the_radius_cannot_reach_from_one_pinned_spawn_to_the_other(self):
        """Re-derived from the registry, so the constant cannot drift past the
        separation it depends on."""
        home = self.registry[HOME].spawn
        stage = self.registry[STAGE].spawn
        separation = math.hypot(home[0] - stage[0], home[1] - stage[1])
        self.assertGreater(separation, 2 * CROSS_CHECK_RADIUS_UNITS)
        extent = self.registry[STAGE].ground_extent
        self.assertLess(max(extent), CROSS_CHECK_RADIUS_UNITS)

    def test_a_settle_at_the_destination_is_recorded_and_marked_checked(self):
        spawn = self.registry[STAGE].spawn
        line = _settle_line(STAGE, spawn[0] + 70.0, spawn[1] - 6.0, spawn[2])
        self.assertEqual(self.ledger.observe_console_line(line), STAGE)
        self.assertTrue(self.ledger.fact(STAGE).cross_checked)
        self.assertEqual(self.ledger.refused_by_cross_check, 0)

    def test_a_settle_at_the_departure_scene_is_refused_for_the_destination(self):
        """THE FALSE LEARN.  A client that never loaded 278 and is still
        standing in Port Royal produces this line as soon as one report jumps
        further than jump_units - the gate lists the causes itself."""
        home = self.registry[HOME].spawn
        line = _settle_line(STAGE, home[0] - 1721.0, home[1] + 267.0, 207.549)
        self.assertIsNone(self.ledger.observe_console_line(line))
        self.assertFalse(self.ledger.knows(STAGE))
        self.assertEqual(self.ledger.refused_by_cross_check, 1)
        self.assertEqual(self.ledger.settle_lines_seen, 1)

    def test_with_no_registry_the_fact_is_kept_but_marked_unchecked(self):
        ledger = SceneLivenessLedger.empty()
        home = self.registry[HOME].spawn
        line = _settle_line(STAGE, home[0], home[1], home[2])
        self.assertEqual(ledger.observe_console_line(line), STAGE)
        self.assertFalse(ledger.fact(STAGE).cross_checked)

    def test_a_registry_that_cannot_answer_never_raises(self):
        class _Angry:
            def __getitem__(self, key):
                raise RuntimeError("no")

        for registry in (_Angry(), object(), {}, 5):
            with self.subTest(repr(type(registry))):
                ledger = SceneLivenessLedger({}, None, registry)
                self.assertEqual(
                    ledger.observe_console_line(
                        _settle_line(STAGE, 1.0, 2.0, 3.0)), STAGE)
                self.assertFalse(ledger.fact(STAGE).cross_checked)

    def test_a_scene_the_registry_does_not_pin_is_kept_unchecked(self):
        line = _settle_line(4242, 1.0, 2.0, 3.0)
        self.assertEqual(self.ledger.observe_console_line(line), 4242)
        self.assertFalse(self.ledger.fact(4242).cross_checked)

    def test_an_unreadable_at_field_is_not_a_refusal(self):
        for broken in ("at=(nan,2.000,3.000)", "at=(1.000,2.000)",
                       "at=(inf,2.000,3.000)", "at=(a,b,c)"):
            with self.subTest(broken):
                ledger = SceneLivenessLedger.seeded(self.registry)
                line = _settle_line(STAGE, 1.0, 2.0, 3.0)
                head = line.index(" at=(")
                tail = line.index(")", head) + 1
                line = line[:head] + " " + broken + line[tail:]
                self.assertEqual(ledger.observe_console_line(line), STAGE)
                self.assertFalse(ledger.fact(STAGE).cross_checked)


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.ledger = SceneLivenessLedger.seeded()

    def test_the_first_evidence_is_the_evidence(self):
        self.assertTrue(self.ledger.observe_arrival(STAGE, "  first  "))
        self.assertFalse(self.ledger.observe_arrival(STAGE, "second"))
        self.assertEqual(self.ledger.fact(STAGE).evidence, "first")

    def test_a_seed_never_overwrites_a_recorded_fact(self):
        self.ledger.observe_arrival(STAGE, "recorded here")
        self.assertFalse(self.ledger.seed_observed(STAGE, "from storage"))
        self.assertTrue(self.ledger.fact(STAGE).from_this_process)

    def test_a_seeded_fact_is_not_claimed_as_this_boot(self):
        ledger = SceneLivenessLedger.seeded()
        self.assertTrue(ledger.seed_observed(STAGE, " an earlier process "))
        self.assertFalse(ledger.fact(STAGE).from_this_process)
        self.assertEqual(ledger.fact(STAGE).evidence, "an earlier process")
        self.assertEqual(
            decide(_stage_row(), ledger).reason,
            REASON_RECORDED_BEFORE_THIS_PROCESS)

    def test_the_structured_entry_point_refuses_a_bad_observation(self):
        for bad in (None, "278", -1, 0x10000, 1.5, True, b"1", object()):
            with self.subTest(repr(bad)):
                with self.assertRaises(ValueError):
                    self.ledger.observe_arrival(bad, "evidence")
                with self.assertRaises(ValueError):
                    self.ledger.seed_observed(bad, "evidence")
        for bad in (None, "", "   ", 1, b"x", object()):
            with self.subTest("evidence=" + repr(bad)):
                with self.assertRaises(ValueError):
                    self.ledger.observe_arrival(STAGE, bad)
                with self.assertRaises(ValueError):
                    self.ledger.seed_observed(STAGE, bad)
        self.assertFalse(self.ledger.knows(STAGE))

    def test_the_console_reader_never_raises(self):
        for bad in JUNK:
            with self.subTest(repr(type(bad))):
                self.assertIsNone(self.ledger.observe_console_line(bad))
        self.assertEqual(self.ledger.observed_ids, (1, 2))

    def test_a_str_subclass_is_still_a_line(self):
        """A logging wrapper is a str subclass; an exact-type gate would make
        the ledger silently unteachable behind one."""
        class _Wrapped(str):
            pass

        line = _Wrapped(_settle_line(STAGE, -13270.0, 22794.0, -2492.7))
        self.assertEqual(
            SceneLivenessLedger.empty().observe_console_line(line), STAGE)

    def test_only_the_settle_line_can_teach_the_ledger(self):
        """THE MUTANT, with the list re-derived from the producer.

        The earlier version of this test typed out three lines by hand, said
        there were three, and included one that carries no scene_id= field at
        all.  This walks world_travel_gate's own source instead.
        """
        gate_source = GATE_PATH.read_text(encoding="ascii")
        literals = [
            node.value for node in ast.walk(ast.parse(gate_source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and node.value.startswith("WORLD_TRAVEL_")
        ]
        settles = [item for item in literals
                   if item.startswith(SETTLED_PREFIX)]
        self.assertEqual(len(settles), 1, literals)
        others = [item for item in literals
                  if not item.startswith(SETTLED_PREFIX)]
        carrying = [item for item in others if "scene_id=" in item]
        self.assertGreaterEqual(len(carrying), 5)
        self.assertTrue(any(
            item.startswith("WORLD_TRAVEL_STRANDED") for item in carrying))
        for template in others:
            with self.subTest(template.split(" ")[0]):
                line = template.replace("{0}", str(STAGE)).replace(
                    "{1}", "1.0").replace("{2}", "2.0").replace("{3}", "3.0")
                self.assertIsNone(self.ledger.observe_console_line(line))
        self.assertFalse(self.ledger.knows(STAGE))

    def test_the_parser_refuses_everything_that_is_not_the_field(self):
        for line in (
            "prefixed " + _settle_line(STAGE, 1.0, 2.0, 3.0),
            "WORLD_TRAVEL_SETTLED at=(1,2,3) scene_id=278",
            "WORLD_TRAVEL_SETTLED scene_id=",
            "WORLD_TRAVEL_SETTLED scene_id=abc",
            "WORLD_TRAVEL_SETTLED scene_id=-1",
            "WORLD_TRAVEL_SETTLED scene_id=278.0",
            "WORLD_TRAVEL_SETTLED scene_id=99999",
            "WORLD_TRAVEL_SETTLED scene_id=２７８",
            "WORLD_TRAVEL_SETTLED  scene_id=278",
            "WORLD_TRAVEL_SETTLEDscene_id=278",
            "WORLD_TRAVEL_SETTLED scene_id=" + "9" * 5000,
            # The prefix has to be AT the start, not anywhere in the line.
            # Twenty-one characters of anything, then a readable field, then
            # the prefix further along: a substring check would learn 278 from
            # this and a startswith check refuses it.  Contrived on purpose -
            # it is the whole class of input the weaker check admits.
            "A" * len(SETTLED_PREFIX)
            + "scene_id=278 at=(-13270.058,22794.273,-2492.769) "
            + SETTLED_PREFIX,
        ):
            with self.subTest(line[:48]):
                self.assertIsNone(self.ledger.observe_console_line(line))
        self.assertFalse(self.ledger.knows(STAGE))

    def test_a_settle_line_is_read_once_and_kept(self):
        line = _settle_line(STAGE, -13270.0, 22794.0, -2492.7, reports=2)
        ledger = SceneLivenessLedger.empty()
        self.assertEqual(ledger.observe_console_line(line), STAGE)
        self.assertIn(line, ledger.fact(STAGE).evidence)
        self.assertTrue(ledger.fact(STAGE).from_this_process)
        again = _settle_line(STAGE, -13270.0, 22794.0, -2492.7, reports=9)
        self.assertEqual(ledger.observe_console_line(again), STAGE)
        self.assertIn("reports=2", ledger.fact(STAGE).evidence)

    def test_the_counters_make_a_half_wiring_visible(self):
        """D4: a ledger consulted at login but never fed from the emit hook is
        otherwise indistinguishable from an honest empty one."""
        ledger = SceneLivenessLedger.seeded()
        self.assertEqual(
            (ledger.lines_seen, ledger.settle_lines_seen), (0, 0))
        line = liveness_console_line(decide(_stage_row(), ledger), ledger)
        self.assertIn("lines_seen=0 settles=0 refused=0 recorded=1+2", line)
        ledger.observe_console_line("WORLD_TRAVEL_ARMED scene_id=1")
        ledger.observe_console_line(_settle_line(STAGE, 1.0, 2.0, 3.0))
        self.assertEqual(
            (ledger.lines_seen, ledger.settle_lines_seen), (2, 1))


class RealGateTests(unittest.TestCase):
    """The parser and the cross-check against the module that writes the line."""

    def setUp(self):
        self.gates, self.settings = world_travel_gate.load_travel_gates()
        by_name = {gate.name: gate for gate in self.gates}
        self.centre = by_name[DEPARTURE_GATE].centre
        self.lines = []
        self.set = world_travel_gate.TravelGateSet(emit=self.lines.append)
        self.ledger = SceneLivenessLedger.seeded()
        self.set.observe(Position(HOME, SCENE_SEQUENCE, *ATTENDED_SPAWN, 0.0))
        departure = None
        for _ in range(self.settings.dwell_reports + 1):
            got = self.set.observe(
                Position(HOME, SCENE_SEQUENCE, *self.centre, 0.0))
            if got is not None and departure is None:
                got.confirmed_fields()
                departure = got
        self.assertIsNotNone(departure)

    def _feed(self):
        return [item for item in
                (self.ledger.observe_console_line(line) for line in self.lines)
                if item is not None]

    def test_the_parser_is_pinned_to_the_real_gate(self):
        """A real crossing that settles at the destination records scene 278."""
        self.set.observe(Position(STAGE, SCENE_SEQUENCE, -13200.0, 22800.0,
                                  -2492.0, 0.0))
        self.assertTrue(any(
            line.startswith(SETTLED_PREFIX) for line in self.lines))
        self.assertEqual(self._feed(), [STAGE])
        self.assertTrue(self.ledger.fact(STAGE).cross_checked)
        self.assertEqual(
            decide(_stage_row(), self.ledger).decision, DECISION_HONOUR)

    def test_a_jump_in_the_departure_scene_settles_and_is_still_refused(self):
        """D1a END TO END.  The client never loaded 278 and is standing in
        Port Royal; one report jumps further than jump_units - which the gate
        itself says can come from a straggler frame or somebody else's
        teleport - and the gate calls it an arrival.  Without the cross-check
        the ledger would trust 278 on Port Royal coordinates and honour every
        stranded character straight back into the scene that stranded them.
        """
        self.set.observe(Position(
            STAGE, SCENE_SEQUENCE,
            self.centre[0] - 4000.0, self.centre[1], self.centre[2], 0.0))
        settled = [line for line in self.lines
                   if line.startswith(SETTLED_PREFIX)]
        self.assertEqual(len(settled), 1)
        self.assertIn("scene_id=278", settled[0])
        self.assertEqual(self._feed(), [])
        self.assertFalse(self.ledger.knows(STAGE))
        self.assertEqual(self.ledger.refused_by_cross_check, 1)
        self.assertEqual(
            decide(_stage_row(), self.ledger).decision, DECISION_FLAG)

    def test_a_crossing_that_strands_records_nothing(self):
        """D1b.  A client that keeps reporting ordinary walking steps never
        settles, whether it is still in the old scene or standing in the new
        one with its coordinates unchanged - which is what
        avatar_position_is_not_set_by_this_teleport=V112 would mean across a
        boundary.  The gate strands it either way, and the two are
        indistinguishable from here.

        NOTE WHAT THIS TEST IS NOT.  The case the module was built for - a
        client parked at status 2 - cannot be driven through the gate at all:
        it sends nothing, so the gate emits no line, the report budget is
        never reached, and there is nothing for this parser to be fed.  That
        case has no server-side signal today and this file does not pretend
        to cover it.
        """
        for index in range(1, self.settings.report_budget + 1):
            self.set.observe(Position(
                STAGE, SCENE_SEQUENCE,
                self.centre[0] + index * 538.44, self.centre[1],
                self.centre[2], 0.0))
        self.assertTrue(any(
            line.startswith("WORLD_TRAVEL_STRANDED") for line in self.lines))
        self.assertFalse(any(
            line.startswith(SETTLED_PREFIX) for line in self.lines))
        self.assertEqual(self._feed(), [])
        decision = decide(_stage_row(), self.ledger)
        self.assertEqual(decision.decision, DECISION_FLAG)
        self.assertEqual(decision.home_if_asked, self.ledger.home)
        self.assertIs(decision.position, decision.stored)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.ledger = SceneLivenessLedger.seeded()

    def test_a_line_is_printed_on_every_branch(self):
        flagged = liveness_console_line(decide(_stage_row(), self.ledger))
        self.assertIn("decision=flag_no_arrival_recorded", flagged)
        self.assertIn("home_if_asked_scene=1", flagged)
        sent = liveness_console_line(
            decide(_stage_row(), self.ledger, rewrite=True))
        self.assertIn("decision=send_home", sent)
        self.assertIn("home_scene=1", sent)
        self.assertNotIn("home_if_asked", sent)
        kept = liveness_console_line(
            decide(_row(HOME, *ATTENDED_SPAWN), self.ledger))
        self.assertIn("decision=honour", kept)
        # reason=home_row is not a home coordinate field; the honoured branch
        # offers no way home because it is not proposing one.
        self.assertNotIn("home_at=", kept)
        self.assertNotIn("home_scene=", kept)
        for line in (flagged, sent, kept):
            with self.subTest(line[:40]):
                self.assertTrue(line.startswith("WORLD_SCENE_LIVENESS "))
                self.assertTrue(line.isascii())
                self.assertNotIn("\n", line)
                self.assertNotIn("\r", line)

    def test_an_unchecked_recorded_fact_says_so_in_the_line(self):
        ledger = SceneLivenessLedger.empty()
        ledger.observe_arrival(STAGE, "recorded with nothing to check against")
        line = liveness_console_line(decide(_stage_row(), ledger))
        self.assertIn("evidence=this_process_unchecked", line)
        ledger2 = SceneLivenessLedger.empty()
        ledger2.observe_arrival(STAGE, "checked", cross_checked=True)
        self.assertIn(
            "evidence=this_process ",
            liveness_console_line(decide(_stage_row(), ledger2)) + " ")

    def test_an_unreadable_row_still_prints_a_line(self):
        line = liveness_console_line(decide(None, self.ledger))
        self.assertIn("stored_scene=none", line)
        self.assertIn("stored_at=unreadable", line)

    def test_the_report_carries_both_rows(self):
        report = liveness_report(decide(_stage_row(), self.ledger), self.ledger)
        self.assertIs(report["sends_home"], False)
        self.assertIs(report["rewrites_the_row"], False)
        self.assertEqual(report["stored_scene_id"], STAGE)
        self.assertEqual(report["used_scene_id"], STAGE)
        self.assertEqual(report["used_position"],
                         [report["stored_position"][0],
                          report["stored_position"][1],
                          report["stored_position"][2]])
        self.assertEqual(report["home_if_asked"][0], self.ledger.home.x)
        self.assertIsNone(report["evidence"])
        self.assertIn("lines_seen=0", report["console_line"])
        written = liveness_report(
            decide(_stage_row(), self.ledger, rewrite=True))
        self.assertIs(written["rewrites_the_row"], True)
        self.assertEqual(written["used_scene_id"], HOME)

    def test_the_reporters_refuse_anything_that_is_not_a_decision(self):
        for bad in JUNK:
            with self.subTest(repr(type(bad))):
                with self.assertRaises(ValueError):
                    liveness_console_line(bad)
                with self.assertRaises(ValueError):
                    liveness_report(bad)


class StaticTests(unittest.TestCase):
    def test_this_module_writes_nothing(self):
        """Read off the parse tree rather than the text: a prose scan cannot
        tell a promise that there is no socket from a socket."""
        tree = ast.parse(MODULE_PATH.read_text(encoding="ascii"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add("." * node.level + (node.module or ""))
                imported.update(
                    "." * node.level + (node.module or "") + "." + alias.name
                    for alias in node.names)
        self.assertEqual(
            imported,
            {
                "__future__", "__future__.annotations",
                "dataclasses", "dataclasses.dataclass",
                "typing", "typing.Any",
                ".", "..world_scene_travel", ".model", ".model.Position",
            },
        )
        called = {
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        for forbidden in ("open", "exec", "eval", "compile", "__import__",
                          "print"):
            with self.subTest(forbidden):
                self.assertNotIn(forbidden, called)

    def test_the_retraction_is_still_in_the_file(self):
        """The default was changed because of a proven defect.  If somebody
        flips it back, the paragraph explaining why has to go with it, and
        this is what makes that deliberate rather than quiet.
        """
        source = MODULE_PATH.read_text(encoding="ascii")
        self.assertIn("WHY THIS DOES NOT REWRITE ANYTHING", source)
        self.assertIn("the scene the server believes the player is in", source)

    def test_the_source_is_ascii(self):
        """The bridge console is cp874 and this project has been bitten."""
        MODULE_PATH.read_text(encoding="ascii")


if __name__ == "__main__":
    unittest.main()
