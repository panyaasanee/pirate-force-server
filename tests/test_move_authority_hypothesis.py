"""MOVE-AUTHORITY-002 (HYP-PF-030) -- the movement-authority policy, offline.

This file proves the pure half of the lane: the refusal ladder, its ORDER, the
scenario file's role as a permission token rather than a source of values, and
the containment of the module inside the tree.  It drives no dispatcher, opens
no database and needs no artifact of any kind --
``tests/test_move_authority_dispatch.py`` drives the real dispatcher.

What the ladder means is stated once, here, so a later reader does not have to
infer it from the assertions: the gate decides whether a REPORTED position may
be PERSISTED.  It never composes a byte, so a refusal is a write that does not
happen, not a message the client receives.

NOT proven here, and not provable on any machine without a person at a screen:
what a real client does when the position it reported is not persisted.  No
client has ever been run against this lane.  That is the attended half and it
is queued, not run.
"""
from __future__ import annotations

import ast
import dataclasses
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import move_authority_hypothesis as mah  # noqa: E402


SCENARIO_PATH = ROOT / "scenarios" / "move_authority_hypothesis_speed_gate.json"
MODULE_PATH = ROOT / "src" / "pirateforce_foundation" / "move_authority_hypothesis.py"


class MoveAuthorityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.scenario = mah.load_move_authority_hypothesis_scenario(SCENARIO_PATH)
        self.policy = self.scenario.policy
        self.origin = (0.0, 0.0, 0.0)

    def report(self, x=0.0, y=0.0, z=0.0, heading=0.0, moving=1):
        """The parser's own tuple shape: index 4 is its constant zero."""
        return (x, y, z, heading, 0, moving)

    # ----- the accept rungs -------------------------------------------------

    def test_the_first_report_of_a_session_anchors(self):
        verdict = mah.evaluate_move_report(
            None, self.report(9999.0, 9999.0), None, self.policy,
        )
        self.assertTrue(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_ANCHOR)
        self.assertIsNone(verdict.speed)

    def test_the_grace_window_accepts_before_anything_is_measured(self):
        verdict = mah.evaluate_move_report(
            self.origin, self.report(500000.0, 500000.0), 0.001, self.policy,
            grace=True,
        )
        self.assertTrue(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_TELEPORT_GRACE)

    def test_a_report_that_did_not_move_needs_no_clock(self):
        verdict = mah.evaluate_move_report(
            self.origin, self.report(0.0, 0.0, 0.0, 3.0, moving=0),
            None, self.policy,
        )
        self.assertTrue(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_STATIONARY)

    def test_a_walk_inside_every_budget_is_accepted(self):
        verdict = mah.evaluate_move_report(
            self.origin, self.report(300.0, 400.0), 1.0, self.policy,
        )
        self.assertTrue(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_WITHIN_BUDGET)
        self.assertAlmostEqual(verdict.horizontal, 500.0)
        self.assertAlmostEqual(verdict.speed, 500.0)

    def test_the_tolerance_ratio_is_applied_and_is_not_decoration(self):
        ceiling = self.policy.max_speed_units_per_second
        ratio = self.policy.speed_tolerance_ratio
        self.assertGreater(ratio, 0.0)
        just_over_the_raw_ceiling = ceiling * (1.0 + ratio / 2.0)
        verdict = mah.evaluate_move_report(
            self.origin, self.report(just_over_the_raw_ceiling, 0.0),
            1.0, self.policy,
        )
        self.assertTrue(verdict.accepted, verdict)
        over_the_tolerated_ceiling = ceiling * (1.0 + ratio) + 1.0
        verdict = mah.evaluate_move_report(
            self.origin, self.report(over_the_tolerated_ceiling, 0.0),
            1.0, self.policy,
        )
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_SPEED_OVER_BUDGET)

    # ----- the refusal rungs ------------------------------------------------

    def test_a_speed_over_the_budget_is_refused_and_shows_its_work(self):
        verdict = mah.evaluate_move_report(
            self.origin, self.report(1900.0, 0.0), 1.0, self.policy,
        )
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_SPEED_OVER_BUDGET)
        self.assertAlmostEqual(verdict.horizontal, 1900.0)
        self.assertAlmostEqual(verdict.speed, 1900.0)

    def test_one_step_over_the_step_budget_is_refused_without_a_clock(self):
        verdict = mah.evaluate_move_report(
            self.origin,
            self.report(self.policy.max_step_units + 1.0, 0.0),
            10_000.0, self.policy,
        )
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_STEP_OVER_BUDGET)

    def test_a_vertical_jump_over_the_budget_is_refused(self):
        verdict = mah.evaluate_move_report(
            self.origin,
            self.report(1.0, 0.0, self.policy.max_vertical_step_units + 1.0),
            1.0, self.policy,
        )
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_VERTICAL_OVER_BUDGET)

    def test_standing_still_while_moving_is_refused_when_the_knob_is_on(self):
        """The rung is implemented, tested, and OFF in the shipped profile.

        Why it ships off is proved against the authentic walk further down;
        here the rung is exercised on a profile that turns it on, so the
        behaviour stays covered and a future profile can rely on it.
        """
        self.assertIs(self.policy.enforce_moving_flag, False)
        strict = dataclasses.replace(self.policy, enforce_moving_flag=True)
        verdict = mah.evaluate_move_report(
            self.origin, self.report(10.0, 0.0, moving=0), 1.0, strict,
        )
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_MOVING_FLAG_INCONSISTENT)
        # ... and the shipped profile accepts the very same reading.
        shipped = mah.evaluate_move_report(
            self.origin, self.report(10.0, 0.0, moving=0), 1.0, self.policy,
        )
        self.assertTrue(shipped.accepted)
        self.assertEqual(shipped.reason, mah.REASON_WITHIN_BUDGET)

    def test_a_missing_or_backwards_clock_refuses_rather_than_dividing(self):
        for elapsed in (None, -1.0, float("nan")):
            with self.subTest(elapsed=elapsed):
                verdict = mah.evaluate_move_report(
                    self.origin, self.report(10.0, 0.0), elapsed, self.policy,
                )
                self.assertFalse(verdict.accepted)
                self.assertEqual(
                    verdict.reason, mah.REASON_NONPOSITIVE_ELAPSED,
                )

    def test_a_clock_too_coarse_to_divide_by_accepts_instead_of_dividing(self):
        """Two readings inside one tick are ordinary, not suspicious.

        Dividing by a granularity manufactures a speed, and that false speed
        would be a false refusal on an ordinary walk -- which is exactly what
        the authentic walk further down catches.
        """
        floor = self.policy.min_measurable_elapsed_seconds
        self.assertGreater(floor, 0.0)
        for elapsed in (0.0, floor / 2.0):
            with self.subTest(elapsed=elapsed):
                verdict = mah.evaluate_move_report(
                    self.origin, self.report(10.0, 0.0), elapsed, self.policy,
                )
                self.assertTrue(verdict.accepted)
                self.assertEqual(verdict.reason, mah.REASON_CLOCK_TOO_COARSE)
                self.assertIsNone(verdict.speed)
        # At the floor the speed rung is live again.
        verdict = mah.evaluate_move_report(
            self.origin, self.report(10.0, 0.0), floor, self.policy,
        )
        self.assertEqual(verdict.reason, mah.REASON_WITHIN_BUDGET)
        # The clock-free budgets still apply below the floor.
        verdict = mah.evaluate_move_report(
            self.origin,
            self.report(self.policy.max_step_units + 1.0, 0.0),
            0.0, self.policy,
        )
        self.assertEqual(verdict.reason, mah.REASON_STEP_OVER_BUDGET)

    def test_a_non_finite_coordinate_is_refused_independently_of_the_parser(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(bad=bad):
                verdict = mah.evaluate_move_report(
                    self.origin, self.report(bad, 0.0), 1.0, self.policy,
                )
                self.assertFalse(verdict.accepted)
                self.assertEqual(
                    verdict.reason, mah.REASON_NONFINITE_COMPONENT,
                )

    def test_every_malformed_argument_refuses_by_the_same_name(self):
        cases = {
            "policy_is_not_a_policy": (
                self.origin, self.report(1.0), 1.0, object(),
            ),
            "report_is_too_short": (
                self.origin, (1.0, 2.0, 3.0), 1.0, self.policy,
            ),
            "report_is_not_a_sequence": (
                self.origin, "0,0,0,0,0,1", 1.0, self.policy,
            ),
            "moving_is_a_bool": (
                self.origin, (1.0, 0.0, 0.0, 0.0, 0, True), 1.0, self.policy,
            ),
            "moving_is_a_string": (
                self.origin, (1.0, 0.0, 0.0, 0.0, 0, "1"), 1.0, self.policy,
            ),
            "previous_is_the_wrong_length": (
                (0.0, 0.0), self.report(1.0), 1.0, self.policy,
            ),
            "previous_is_not_finite": (
                (float("nan"), 0.0, 0.0), self.report(1.0), 1.0, self.policy,
            ),
        }
        for name, args in cases.items():
            with self.subTest(name=name):
                verdict = mah.evaluate_move_report(*args)
                self.assertFalse(verdict.accepted)
                self.assertEqual(verdict.reason, mah.REASON_MALFORMED_REPORT)

    def test_vertical_speed_is_unbounded_and_the_nonclaims_say_so(self):
        """A known gap, pinned so it cannot quietly become a claim.

        Only horizontal displacement is divided by elapsed time.  A climb just
        inside the per-reading vertical budget is admitted at any rate.
        """
        previous = self.origin
        climb = self.policy.max_vertical_step_units - 1.0
        for step in range(1, 6):
            verdict = mah.evaluate_move_report(
                previous, self.report(0.0, 0.0, climb * step, moving=0),
                1.0, self.policy,
            )
            self.assertTrue(verdict.accepted)
            self.assertEqual(verdict.reason, mah.REASON_WITHIN_BUDGET)
            self.assertEqual(verdict.speed, 0.0)
            previous = (0.0, 0.0, climb * step)
        self.assertGreater(previous[2], self.policy.max_vertical_step_units * 4)
        self.assertIn("VERTICAL SPEED IS NOT BOUNDED", MODULE_PATH.read_text(
            encoding="utf-8"))

    # ----- the ORDER of the ladder, which is part of the design --------------

    def test_a_non_finite_coordinate_outranks_the_grace_window(self):
        verdict = mah.evaluate_move_report(
            self.origin, self.report(float("nan"), 0.0), 1.0, self.policy,
            grace=True,
        )
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason, mah.REASON_NONFINITE_COMPONENT)

    def test_the_moving_flag_outranks_both_distance_budgets(self):
        strict = dataclasses.replace(self.policy, enforce_moving_flag=True)
        verdict = mah.evaluate_move_report(
            self.origin,
            self.report(
                self.policy.max_step_units * 10.0,
                0.0,
                self.policy.max_vertical_step_units * 10.0,
                moving=0,
            ),
            1.0, strict,
        )
        self.assertEqual(verdict.reason, mah.REASON_MOVING_FLAG_INCONSISTENT)

    def test_the_vertical_budget_outranks_the_step_budget(self):
        verdict = mah.evaluate_move_report(
            self.origin,
            self.report(
                self.policy.max_step_units * 10.0,
                0.0,
                self.policy.max_vertical_step_units + 1.0,
            ),
            1.0, self.policy,
        )
        self.assertEqual(verdict.reason, mah.REASON_VERTICAL_OVER_BUDGET)

    def test_every_clock_free_refusal_outranks_the_clock(self):
        """A verdict reachable without a clock must never need one."""
        verdict = mah.evaluate_move_report(
            self.origin,
            self.report(self.policy.max_step_units + 1.0, 0.0),
            None, self.policy,
        )
        self.assertEqual(verdict.reason, mah.REASON_STEP_OVER_BUDGET)

    def test_the_reason_of_every_verdict_is_one_of_the_two_declared_sets(self):
        samples = [
            (None, self.report(1.0), None),
            (self.origin, self.report(0.0, 0.0, 0.0, 0.0, 0), None),
            (self.origin, self.report(1.0), 1.0),
            (self.origin, self.report(9e9), 1.0),
            (self.origin, self.report(10.0, 0.0, moving=0), 1.0),
            (self.origin, self.report(10.0), None),
            (self.origin, self.report(float("inf")), 1.0),
            (self.origin, (1.0,), 1.0),
        ]
        for previous, report, elapsed in samples:
            with self.subTest(report=report):
                verdict = mah.evaluate_move_report(
                    previous, report, elapsed, self.policy,
                )
                pool = (
                    mah.ACCEPT_REASONS if verdict.accepted
                    else mah.REFUSAL_REASONS
                )
                self.assertIn(verdict.reason, pool)
                self.assertIs(verdict.checkpoint_allowed, verdict.accepted)

    def test_the_same_inputs_always_produce_the_same_verdict(self):
        args = (self.origin, self.report(700.0, 700.0), 1.5, self.policy)
        first = mah.evaluate_move_report(*args)
        for _ in range(50):
            self.assertEqual(mah.evaluate_move_report(*args), first)


class MoveAuthorityScenarioTests(unittest.TestCase):
    """The scenario file is a permission token, never a source of values."""

    def setUp(self):
        self.body = SCENARIO_PATH.read_text(encoding="utf-8")
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        path = Path(self.tmp.name) / "scenario.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_the_shipped_file_loads_and_yields_the_frozen_profile(self):
        loaded = mah.load_move_authority_hypothesis_scenario(SCENARIO_PATH)
        self.assertIs(loaded, mah._SPEED_GATE)
        self.assertEqual(loaded.hypothesis_id, "HYP-PF-030")

    def test_the_shipped_file_declares_itself_test_only(self):
        import json
        data = json.loads(self.body)
        self.assertIs(data["test_only"], True)
        self.assertIs(data["production_allowed"], False)
        self.assertEqual(data["hypothesis_id"], "HYP-PF-030")
        self.assertEqual(
            data["entry"]["corrective_frame_policy"], "never_emitted",
        )
        self.assertIn("original_server_movement_policy", data["nonclaims"])
        self.assertIn("corrective_reposition_wire_shape", data["nonclaims"])
        self.assertIn("client_observable_acceptance", data["nonclaims"])
        self.assertIn("production_baseline_behavior", data["nonclaims"])

    def test_a_tampered_budget_is_refused_rather_than_obeyed(self):
        tampered = self.body.replace('"max_speed_units_per_second": 1200.0',
                                     '"max_speed_units_per_second": 999999.0')
        self.assertNotEqual(tampered, self.body)
        with self.assertRaises(ValueError) as caught:
            mah.load_move_authority_hypothesis_scenario(self._write(tampered))
        self.assertIn("exceeds_allowlist", str(caught.exception))

    def test_an_int_where_a_float_is_expected_is_refused(self):
        tampered = self.body.replace('"max_step_units": 2000.0',
                                     '"max_step_units": 2000')
        with self.assertRaises(ValueError):
            mah.load_move_authority_hypothesis_scenario(self._write(tampered))

    def test_flipping_production_allowed_is_refused(self):
        tampered = self.body.replace('"production_allowed": false',
                                     '"production_allowed": true')
        with self.assertRaises(ValueError):
            mah.load_move_authority_hypothesis_scenario(self._write(tampered))

    def test_an_extra_or_a_missing_key_is_refused(self):
        extra = self.body.replace('{\n  "schema": 1,',
                                  '{\n  "extra": 1,\n  "schema": 1,')
        with self.assertRaises(ValueError):
            mah.load_move_authority_hypothesis_scenario(self._write(extra))
        missing = self.body.replace('  "schema": 1,\n', '')
        with self.assertRaises(ValueError):
            mah.load_move_authority_hypothesis_scenario(self._write(missing))

    def test_an_unknown_id_is_refused_by_name(self):
        tampered = self.body.replace(
            '"id": "move_authority_hypothesis_speed_gate"',
            '"id": "move_authority_hypothesis_something_else"',
        )
        with self.assertRaises(ValueError) as caught:
            mah.load_move_authority_hypothesis_scenario(self._write(tampered))
        self.assertIn("unknown_id", str(caught.exception))

    def test_an_unreadable_file_is_refused_by_name(self):
        with self.assertRaises(ValueError) as caught:
            mah.load_move_authority_hypothesis_scenario(
                Path(self.tmp.name) / "absent.json"
            )
        self.assertIn("unreadable", str(caught.exception))
        with self.assertRaises(ValueError):
            mah.load_move_authority_hypothesis_scenario(self._write("{ not json"))

    def test_a_value_equal_lookalike_profile_is_refused(self):
        lookalike = mah.MoveAuthorityScenario(
            mah._SPEED_GATE.scenario_id,
            mah._SPEED_GATE.hypothesis_id,
            dataclasses.replace(mah._SPEED_GATE.policy),
        )
        self.assertEqual(lookalike, mah._SPEED_GATE)
        with self.assertRaises(ValueError) as caught:
            mah.require_move_authority_hypothesis_scenario(lookalike)
        self.assertIn("not_allowlisted", str(caught.exception))
        self.assertIs(
            mah.require_move_authority_hypothesis_scenario(mah._SPEED_GATE),
            mah._SPEED_GATE,
        )


class MoveAuthorityContainmentTests(unittest.TestCase):
    """The module stays pure, stays annotated once, and stays where it is."""

    def setUp(self):
        self.source = MODULE_PATH.read_text(encoding="utf-8")

    def test_the_module_is_ascii_and_survives_the_bridge_console_encoding(self):
        self.source.encode("ascii")
        self.source.encode("cp874")

    def test_the_module_opens_no_database_and_no_socket(self):
        for banned in (
            "sqlite3", "SQLiteStore", "INSERT ", "UPDATE ", "DELETE FROM",
            "import socket", "socket.socket", "connect(",
        ):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, self.source)

    def test_the_module_imports_only_the_standard_library_it_declares(self):
        tree = ast.parse(self.source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertEqual(
            imported, {"__future__", "dataclasses", "json", "math", "pathlib",
                       "typing"},
        )

    def test_the_module_composes_no_bytes_at_all(self):
        """The one rule this lane must never break: it may refuse, not reply."""
        for banned in ("u8tag", "u16tag", "u32tag", "f32tag", "make_", "pack("):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, self.source)

    def test_the_module_carries_exactly_one_ledger_marker(self):
        self.assertEqual(
            self.source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-030 active"), 1,
        )

    def test_production_is_disallowed_everywhere(self):
        self.assertIs(mah.production_allowed, False)
        self.assertIn("production_allowed = False", self.source)

    def test_the_header_carries_the_evidence_tags_and_the_nonclaims(self):
        for tag in ("[PROVEN]", "[STATIC]", "[OUR DESIGN]", "NONCLAIMS"):
            with self.subTest(tag=tag):
                self.assertIn(tag, self.source)

    def test_the_header_refuses_the_mob_speed_columns_as_a_source(self):
        """The one number a reader might be tempted to borrow, refused in text."""
        self.assertIn("n_SPEED_WALK", self.source)
        self.assertIn("NOT the source of any threshold here", self.source)

    def test_exactly_two_foundation_modules_mention_the_lane(self):
        src = ROOT / "src" / "pirateforce_foundation"
        mentions = sorted(
            path.name for path in src.glob("*.py")
            if path != MODULE_PATH
            and "move_authority" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(mentions, ["app.py", "runtime.py"])
        for absent in ("connection.py", "scenario.py", "session.py", "store.py"):
            with self.subTest(absent=absent):
                self.assertNotIn(
                    "move_authority",
                    (src / absent).read_text(encoding="utf-8"),
                )


REPLAY_TABLE = ROOT / "reports" / "move_cadence001_smoke" / "replay_output.txt"
# The heartbeat worker of the pinned server sends every 2.0 s, which is the
# in-band clock MOVE-CADENCE-001 used to time that walk.  It is the only clock
# the committed table carries, and its granularity is part of what this test
# proves the ladder survives.
HEARTBEAT_SECONDS = 2.0
_ROW = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+"
    r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+([01])\s+([W.])\s*$"
)


def _authentic_walk():
    """The 29 readings of the one authentic walk this project holds.

    Source: ``reports/move_cadence001_smoke/replay_output.txt``, the committed
    stdout of MOVE-CADENCE-001's headless replay of the GT-005 boot1 capture.
    The capture itself does not exist on this machine and is not needed: the
    per-reading table is committed, and that table is the evidence.
    """
    rows = []
    for line in REPLAY_TABLE.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(line)
        if match:
            ordinal, heartbeat, x, y, z, heading, moving, write = match.groups()
            rows.append((
                int(ordinal), int(heartbeat), float(x), float(y), float(z),
                float(heading), int(moving), write,
            ))
    return rows


def _replay(policy):
    """Drive the ladder over the authentic walk and tally the verdicts."""
    previous = None
    previous_heartbeat = None
    tally = {}
    measured = {"step": 0.0, "speed": 0.0, "vertical": 0.0}
    for _ordinal, heartbeat, x, y, z, heading, moving, _write in _authentic_walk():
        elapsed = (
            None if previous_heartbeat is None
            else (heartbeat - previous_heartbeat) * HEARTBEAT_SECONDS
        )
        verdict = mah.evaluate_move_report(
            previous, (x, y, z, heading, 0, moving), elapsed, policy,
        )
        tally[verdict.reason] = tally.get(verdict.reason, 0) + 1
        measured["step"] = max(measured["step"], verdict.horizontal)
        measured["vertical"] = max(measured["vertical"], verdict.vertical)
        if verdict.speed is not None:
            measured["speed"] = max(measured["speed"], verdict.speed)
        if verdict.accepted:
            previous = (x, y, z)
            previous_heartbeat = heartbeat
    return tally, measured


class MoveAuthorityAgainstTheOneAuthenticWalkTests(unittest.TestCase):
    """The budgets, measured against a real walk instead of invented inputs.

    Every other test in this file feeds the ladder numbers chosen to exercise
    it.  This one feeds it the only authentic movement trace the project holds,
    and it is the test that set two of the shipped budgets: it is why
    ``enforce_moving_flag`` ships FALSE and why an elapsed below the measurable
    floor is an accept rather than a division.
    """

    def setUp(self):
        self.policy = mah.load_move_authority_hypothesis_scenario(
            SCENARIO_PATH
        ).policy

    def test_the_committed_table_is_the_walk_the_report_describes(self):
        rows = _authentic_walk()
        self.assertEqual(len(rows), 29)
        self.assertEqual(sum(1 for row in rows if row[7] == "W"), 19)
        self.assertEqual(sum(1 for row in rows if row[6] == 1), 5)

    def test_the_shipped_budgets_refuse_nothing_in_a_real_walk(self):
        tally, _ = _replay(self.policy)
        refused = {
            reason: count for reason, count in tally.items()
            if reason in mah.REFUSAL_REASONS
        }
        self.assertEqual(refused, {}, tally)
        self.assertEqual(
            tally,
            {
                mah.REASON_ANCHOR: 1,
                mah.REASON_WITHIN_BUDGET: 17,
                mah.REASON_CLOCK_TOO_COARSE: 1,
                mah.REASON_STATIONARY: 10,
            },
        )

    def test_the_one_clock_too_coarse_reading_is_real_and_not_contrived(self):
        """Two readings share heartbeat 43 in the authentic table."""
        heartbeats = [row[1] for row in _authentic_walk()]
        self.assertEqual(len(heartbeats), len(set(heartbeats)) + 1)
        tally, _ = _replay(self.policy)
        self.assertEqual(tally[mah.REASON_CLOCK_TOO_COARSE], 1)

    def test_enforcing_the_moving_flag_would_refuse_most_of_a_real_walk(self):
        """The measurement that decided the shipped default.

        The client set ``moving`` on five of twenty-nine readings while moving
        through nineteen distinct positions, so the flag is not a statement
        about whether the player is walking.
        """
        tally, _ = _replay(dataclasses.replace(
            self.policy, enforce_moving_flag=True,
        ))
        self.assertEqual(tally.get(mah.REASON_MOVING_FLAG_INCONSISTENT), 23)
        self.assertEqual(tally.get(mah.REASON_WITHIN_BUDGET), 5)
        self.assertIs(self.policy.enforce_moving_flag, False)

    def test_the_budgets_keep_real_headroom_over_a_real_walk(self):
        _, measured = _replay(self.policy)
        self.assertAlmostEqual(measured["step"], 538.4, delta=0.5)
        self.assertAlmostEqual(measured["speed"], 269.2, delta=0.5)
        self.assertAlmostEqual(measured["vertical"], 8.0, delta=0.5)
        self.assertGreater(self.policy.max_step_units, measured["step"] * 3)
        self.assertGreater(
            self.policy.max_speed_units_per_second, measured["speed"] * 4,
        )
        self.assertGreater(
            self.policy.max_vertical_step_units, measured["vertical"] * 10,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
