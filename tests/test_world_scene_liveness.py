"""LANE-A BUILD-002 / M2: the character who was left where the client parked.

The load-bearing tests in this file are the five that decide whether this
module helps a player or hurts one:

* ``test_a_row_in_an_unopened_scene_is_sent_home`` - the whole point.  Without
  it a character whose client parked at status 2 is sent back to the same
  scene on every login, forever, and only a person with database access can
  free them.
* ``test_a_scene_the_client_settled_in_is_honoured_afterwards`` - the other
  half.  A guard that never lets go turns a working destination into a scene
  nobody can stay in, which would take away what M2 just added.
* ``test_a_home_row_is_honoured_by_a_ledger_that_knows_nothing`` - the loop.
  Sending a character home FROM home, or refusing to believe in scene 1,
  would be a login that never settles anywhere.
* ``test_only_a_settle_line_teaches_the_ledger`` - the mutant.  Three other
  lines from the same module carry ``scene_id=``, and one of them,
  ``WORLD_TRAVEL_STRANDED``, is emitted in exactly the case this module exists
  to catch.  A lenient parser learns 278 from the strand line and then honours
  the row that stranded them.
* ``test_the_parser_is_pinned_to_the_real_gate`` - the drift.  The line is a
  console string with no schema, so the test drives a real crossing and feeds
  this parser what the real module actually emitted.
"""

import sys
from pathlib import Path
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
    DECISION_HONOUR,
    DECISION_SEND_HOME,
    REASON_HOME_ROW,
    REASON_HOME_UNAVAILABLE,
    REASON_NO_EVIDENCE,
    REASON_OBSERVED_BEFORE_THIS_PROCESS,
    REASON_OBSERVED_THIS_PROCESS,
    REASON_UNREADABLE_ROW,
    SceneLivenessLedger,
    decide,
    liveness_console_line,
    liveness_report,
)

STAGE = world_scene_travel.TEST_STAGE_SCENE_ID          # 278
HOME = world_scene_travel.HOME_SCENE_ID                 # 1
DEPARTURE_GATE = "port_royal_columbus_departure"

# Where an attended run actually found the character on 2026-08-23 (GT-045).
ATTENDED_SPAWN = (-8553.947265625, -2579.68896484375, 186.0)

# Nine shapes that are not a Position, plus the awkward ones this project has
# actually been bitten by: a message that is not ASCII, one with a carriage
# return, and an object whose __str__ raises.
class _Exploding:
    def __str__(self):
        raise RuntimeError("this object refuses to be printed")


JUNK = (
    None, 0, 1, -1, 278, 1.5, True, False, "", "278",
    b"278", (), (1, 0, 0.0, 0.0, 0.0), [1], {"scene_id": 1},
    object(), _Exploding(), float("nan"),
    "ห้อง", "line\rwith\rreturns",
)


def _row(scene_id, x=-13270.0, y=22794.0, z=-2492.7) -> Position:
    return Position(scene_id, SCENE_SEQUENCE, x, y, z, 0.0)


def _stage_row() -> Position:
    return _row(STAGE)


class LedgerSeedTests(unittest.TestCase):
    def test_the_module_is_not_a_scenario(self):
        self.assertIs(world_scene_liveness.test_only, False)
        self.assertIs(world_scene_liveness.production_allowed, True)

    def test_the_seed_is_exactly_the_two_scenes_this_project_has_rendered(self):
        ledger = SceneLivenessLedger.seeded()
        self.assertEqual(
            ledger.observed_ids, tuple(sorted(
                world_scene_travel.MEASURED_SCENE_IDS)))
        self.assertEqual(ledger.observed_ids, (1, 2))
        for fact in ledger.facts():
            with self.subTest(fact.scene_id):
                self.assertFalse(fact.from_this_process)
                self.assertTrue(fact.evidence.strip())

    def test_the_stage_is_not_seeded(self):
        """278 is the scene the door leads to and no client has opened it.

        If this ever goes green the guard has been defeated by a seed, which
        is the failure the module docstring names as worse than no guard.
        """
        ledger = SceneLivenessLedger.seeded()
        self.assertFalse(ledger.knows(STAGE))
        self.assertIsNone(ledger.fact(STAGE))

    def test_the_way_home_is_resolved_once_at_seed_time(self):
        ledger = SceneLivenessLedger.seeded()
        self.assertEqual(ledger.home, world_scene_travel.home_return_position())
        self.assertEqual(ledger.home.scene_id, HOME)

    def test_an_empty_ledger_knows_nothing(self):
        ledger = SceneLivenessLedger.empty()
        self.assertEqual(ledger.observed_ids, ())
        self.assertIsNone(ledger.home)


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.ledger = SceneLivenessLedger.seeded()

    def test_a_row_in_an_unopened_scene_is_sent_home(self):
        decision = decide(_stage_row(), self.ledger)
        self.assertEqual(decision.decision, DECISION_SEND_HOME)
        self.assertEqual(decision.reason, REASON_NO_EVIDENCE)
        self.assertTrue(decision.sends_home)
        self.assertTrue(decision.rewrites_the_row)
        self.assertEqual(decision.position, self.ledger.home)
        self.assertEqual(decision.stored.scene_id, STAGE)
        self.assertIsNone(decision.fact)

    def test_a_scene_the_client_settled_in_is_honoured_afterwards(self):
        self.ledger.observe_alive(STAGE, "a tester stood in it")
        decision = decide(_stage_row(), self.ledger)
        self.assertEqual(decision.decision, DECISION_HONOUR)
        self.assertEqual(decision.reason, REASON_OBSERVED_THIS_PROCESS)
        self.assertFalse(decision.rewrites_the_row)
        self.assertEqual(decision.position, decision.stored)

    def test_an_inherited_fact_says_so_rather_than_claiming_this_boot_saw_it(self):
        decision = decide(_row(2, 26905.0, 21185.0, 1680.0), self.ledger)
        self.assertEqual(decision.decision, DECISION_HONOUR)
        self.assertEqual(decision.reason, REASON_OBSERVED_BEFORE_THIS_PROCESS)
        self.assertFalse(decision.fact.from_this_process)

    def test_a_home_row_is_honoured_by_a_ledger_that_knows_nothing(self):
        for ledger in (SceneLivenessLedger.seeded(),
                       SceneLivenessLedger.empty()):
            with self.subTest(ledger.observed_ids):
                decision = decide(_row(HOME, *ATTENDED_SPAWN), ledger)
                self.assertEqual(decision.decision, DECISION_HONOUR)
                self.assertEqual(decision.reason, REASON_HOME_ROW)
                self.assertFalse(decision.rewrites_the_row)

    def test_the_row_that_comes_back_is_the_row_that_went_in(self):
        """An honoured row is returned untouched - same object, same heading.

        A module that rebuilt the row would quietly drop the heading and the
        scene_seq, and the caller would never see it happen.
        """
        row = Position(STAGE, 7, 1.0, 2.0, 3.0, 4.5)
        self.ledger.observe_alive(STAGE, "settled")
        decision = decide(row, self.ledger)
        self.assertIs(decision.position, row)
        self.assertEqual(decision.position.heading, 4.5)
        self.assertEqual(decision.position.scene_seq, 7)

    def test_with_no_way_home_the_row_stands_and_the_reason_says_why(self):
        ledger = SceneLivenessLedger.empty()
        decision = decide(_stage_row(), ledger, registry=object())
        self.assertEqual(decision.decision, DECISION_HONOUR)
        self.assertEqual(decision.reason, REASON_HOME_UNAVAILABLE)
        self.assertFalse(decision.rewrites_the_row)

    def test_decide_never_raises(self):
        ledger = SceneLivenessLedger.seeded()
        for bad in JUNK:
            with self.subTest(repr(type(bad))):
                decision = decide(bad, ledger)
                self.assertEqual(decision.decision, DECISION_HONOUR)
                self.assertEqual(decision.reason, REASON_UNREADABLE_ROW)
        for bad in JUNK:
            with self.subTest("ledger=" + repr(type(bad))):
                decision = decide(_stage_row(), bad)
                self.assertEqual(decision.reason, REASON_UNREADABLE_ROW)

    def test_a_scene_id_outside_the_wire_field_is_not_decided_about(self):
        """scene_id is a u16 on the wire.  A row outside it is unreadable, not
        an unopened scene: sending such a character home would hide a row that
        store.save_position should never have accepted.
        """
        for scene_id in (-1, 0x10000, 999999):
            with self.subTest(scene_id):
                decision = decide(_row(scene_id), self.ledger)
                self.assertEqual(decision.reason, REASON_UNREADABLE_ROW)
                self.assertFalse(decision.rewrites_the_row)

    def test_scene_zero_is_decided_about_and_sent_home(self):
        """0 is inside the u16 field and is the id RE-077 measured as the miss
        branch - the client parks at status 2 and never reports.  It is the
        strongest case for the guard, not an unreadable row.
        """
        decision = decide(_row(0), self.ledger)
        self.assertEqual(decision.decision, DECISION_SEND_HOME)
        self.assertEqual(decision.reason, REASON_NO_EVIDENCE)


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.ledger = SceneLivenessLedger.seeded()

    def test_the_first_evidence_is_the_evidence(self):
        self.assertTrue(self.ledger.observe_alive(STAGE, "first"))
        self.assertFalse(self.ledger.observe_alive(STAGE, "second"))
        self.assertEqual(self.ledger.fact(STAGE).evidence, "first")

    def test_a_seed_never_overwrites_an_earned_fact(self):
        self.ledger.observe_alive(STAGE, "earned here")
        self.assertFalse(self.ledger.seed_observed(STAGE, "from storage"))
        self.assertTrue(self.ledger.fact(STAGE).from_this_process)

    def test_a_seeded_fact_is_not_claimed_as_this_boot(self):
        ledger = SceneLivenessLedger.seeded()
        self.assertTrue(ledger.seed_observed(STAGE, "an earlier process saw it"))
        self.assertFalse(ledger.fact(STAGE).from_this_process)
        self.assertEqual(
            decide(_stage_row(), ledger).reason,
            REASON_OBSERVED_BEFORE_THIS_PROCESS)

    def test_the_structured_entry_point_refuses_a_bad_observation(self):
        for bad in (None, "278", -1, 0x10000, 1.5, True, b"1", object()):
            with self.subTest(repr(bad)):
                with self.assertRaises(ValueError):
                    self.ledger.observe_alive(bad, "evidence")
        for bad in (None, "", "   ", 1, b"x", object()):
            with self.subTest("evidence=" + repr(bad)):
                with self.assertRaises(ValueError):
                    self.ledger.observe_alive(STAGE, bad)
        for bad in (None, "278", -1, 0x10000):
            with self.subTest("seed=" + repr(bad)):
                with self.assertRaises(ValueError):
                    self.ledger.seed_observed(bad, "evidence")
        with self.assertRaises(ValueError):
            self.ledger.seed_observed(STAGE, "  ")
        self.assertFalse(self.ledger.knows(STAGE))

    def test_the_console_reader_never_raises(self):
        for bad in JUNK:
            with self.subTest(repr(type(bad))):
                self.assertIsNone(self.ledger.observe_console_line(bad))
        self.assertEqual(self.ledger.observed_ids, (1, 2))

    def test_only_a_settle_line_teaches_the_ledger(self):
        """THE MUTANT.  Every other line that carries a scene id is refused.

        WORLD_TRAVEL_STRANDED is the one emitted when a crossing never
        completes - the exact case this module exists for.  A parser that
        learned from it would honour the row that stranded the player.
        """
        refused = (
            "WORLD_TRAVEL_STRANDED scene_id=278 reports=30 home=(1,2,3)",
            "WORLD_TRAVEL_DISCONTINUITY scene_id=278 step=9000.000",
            "WORLD_TRAVEL_DEPART scene_id=278 to=(1,2,3)",
            "WORLD_TRAVEL_SETTLE scene_id=278",
            "prefixed WORLD_TRAVEL_SETTLED scene_id=278",
            "WORLD_TRAVEL_SETTLED at=(1,2,3) scene_id=278",
            "WORLD_TRAVEL_SETTLED scene_id=",
            "WORLD_TRAVEL_SETTLED scene_id=abc",
            "WORLD_TRAVEL_SETTLED scene_id=-1",
            "WORLD_TRAVEL_SETTLED scene_id=278.0",
            "WORLD_TRAVEL_SETTLED scene_id=99999",
            "WORLD_TRAVEL_SETTLED scene_id=２７８",
            "WORLD_TRAVEL_SETTLEDscene_id=278",
        )
        for line in refused:
            with self.subTest(line):
                self.assertIsNone(self.ledger.observe_console_line(line))
        self.assertFalse(self.ledger.knows(STAGE))

    def test_a_settle_line_is_read_once_and_kept(self):
        line = ("WORLD_TRAVEL_SETTLED scene_id=278 at=(1.000,2.000,3.000) "
                "jump=9000.000 reports=2")
        self.assertEqual(self.ledger.observe_console_line(line), STAGE)
        self.assertIn(line, self.ledger.fact(STAGE).evidence)
        self.assertTrue(self.ledger.fact(STAGE).from_this_process)
        # A second settle in the same scene is not a second fact.
        self.assertEqual(self.ledger.observe_console_line(
            line.replace("reports=2", "reports=9")), STAGE)
        self.assertIn("reports=2", self.ledger.fact(STAGE).evidence)


class RealGateTests(unittest.TestCase):
    """The parser against the module that actually writes the line."""

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
        return [self.ledger.observe_console_line(line) for line in self.lines]

    def test_the_parser_is_pinned_to_the_real_gate(self):
        """A real crossing that settles teaches the ledger scene 278."""
        self.set.observe(Position(STAGE, SCENE_SEQUENCE, -13200.0, 22800.0,
                                  -2492.0, 0.0))
        self.assertTrue(any(
            line.startswith(world_scene_liveness.SETTLED_PREFIX)
            for line in self.lines))
        learned = [item for item in self._feed() if item is not None]
        self.assertEqual(learned, [STAGE])
        self.assertTrue(self.ledger.knows(STAGE))
        self.assertEqual(
            decide(_stage_row(), self.ledger).decision, DECISION_HONOUR)

    def test_a_crossing_that_never_settles_teaches_the_ledger_nothing(self):
        """THE CASE THIS MODULE EXISTS FOR, end to end.

        The player walks out of the door, the destination never loads, the
        gate strands them - and the next login walks them home.
        """
        for index in range(1, self.settings.report_budget + 1):
            self.set.observe(Position(
                STAGE, SCENE_SEQUENCE,
                self.centre[0] + index * 538.44, self.centre[1],
                self.centre[2], 0.0))
        self.assertTrue(any(
            line.startswith("WORLD_TRAVEL_STRANDED") for line in self.lines))
        self.assertFalse(any(
            line.startswith(world_scene_liveness.SETTLED_PREFIX)
            for line in self.lines))
        self.assertEqual([item for item in self._feed() if item is not None], [])
        decision = decide(_stage_row(), self.ledger)
        self.assertEqual(decision.decision, DECISION_SEND_HOME)
        self.assertEqual(decision.position, self.ledger.home)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.ledger = SceneLivenessLedger.seeded()

    def test_a_line_is_printed_on_both_branches(self):
        sent = liveness_console_line(decide(_stage_row(), self.ledger))
        self.assertIn("decision=send_home", sent)
        self.assertIn("home_scene=1", sent)
        kept = liveness_console_line(
            decide(_row(HOME, *ATTENDED_SPAWN), self.ledger))
        self.assertIn("decision=honour", kept)
        self.assertNotIn("home_scene=", kept)
        for line in (sent, kept):
            with self.subTest(line):
                self.assertTrue(line.startswith("WORLD_SCENE_LIVENESS "))
                self.assertTrue(line.isascii())
                self.assertNotIn("\n", line)
                self.assertNotIn("\r", line)

    def test_an_unreadable_row_still_prints_a_line(self):
        line = liveness_console_line(decide(None, self.ledger))
        self.assertIn("stored_scene=none", line)
        self.assertIn("stored_at=unreadable", line)

    def test_the_report_carries_both_rows(self):
        report = liveness_report(decide(_stage_row(), self.ledger))
        self.assertIs(report["sends_home"], True)
        self.assertEqual(report["stored_scene_id"], STAGE)
        self.assertEqual(report["used_scene_id"], HOME)
        self.assertIsNone(report["evidence"])
        self.assertIn("WORLD_SCENE_LIVENESS", report["console_line"])

    def test_the_reporters_refuse_anything_that_is_not_a_decision(self):
        for bad in JUNK:
            with self.subTest(repr(type(bad))):
                with self.assertRaises(ValueError):
                    liveness_console_line(bad)
                with self.assertRaises(ValueError):
                    liveness_report(bad)


class StaticTests(unittest.TestCase):
    def test_this_module_writes_nothing(self):
        """It hands back rows; the caller owns every write.

        Read off the parse tree rather than the text: an earlier version of
        this test scanned the source for the word "socket" and went red on the
        docstring sentence that PROMISES there is no socket.  A prose scan
        cannot tell a promise from a violation of it.
        """
        import ast
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "world_scene_liveness.py").read_text(encoding="ascii")
        tree = ast.parse(source)
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

    def test_the_source_is_ascii(self):
        """The bridge console is cp874 and this project has been bitten."""
        path = (ROOT / "src" / "pirateforce_foundation"
                / "world_scene_liveness.py")
        path.read_text(encoding="ascii")


if __name__ == "__main__":
    unittest.main()
