"""LANE-B: lane_hooks/lane_b_mob_ai_tick.py -- the option-(b) wrapper around
mob_ai_scheduler.tick_session, and the exact call site it names for a future
runtime.py round (round iok5z1, 2026-08-31).

Three load-bearing tests in this file.

``test_maybe_tick_passes_through_the_same_register_and_results`` is the
whole contract: this file changes nothing about tick_session's own outcome,
only what prints.

``test_only_a_phase_transition_prints_a_row_line`` pins the console-spam
guard named in the module's own docstring: a register full of rows that did
not change phase must not flood stdout on every TargetPos a moving player
sends.

``test_nothing_in_runtime_py_calls_maybe_tick_yet`` is this round's own
honest half, the same discipline test_mob_ai_scheduler.py's sibling test
already uses: nothing calls this today, and this test fails the day that
stops being true without the module docstring's "WHAT THE PLAYER WILL SEE
DIFFERENTLY" section being updated to match.
"""
from __future__ import annotations

import ast
import contextlib
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    field_mob_tables_bg0002, field_mobs, mob_aggro, mob_ai_control,
    mob_combat,
)
from pirateforce_foundation.lane_hooks import lane_b_mob_ai_tick  # noqa: E402

SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
PLAYER = 0x750059
BG0002_OFFENSIVE_PLACEMENT = 92  # Orc Chief, ai_wander=11 (offensive)


class MaybeTickTests(unittest.TestCase):
    def setUp(self):
        bg0002_roster = field_mobs._parse_hostile_placements(
            field_mob_tables_bg0002)
        self.bg0002_by_placement = {
            m.placement_index: m for m in bg0002_roster}
        self.register = mob_ai_control.open_register(bg0002_roster)
        self.ledger = mob_combat.open_ledger(bg0002_roster)

        dummy_roster = field_mobs.load_roster()  # bg0001: four dummies
        self.dummy_register = mob_ai_control.open_register(dummy_roster)
        self.dummy_ledger = mob_combat.open_ledger(dummy_roster)

    def test_production_allowed_is_true_with_no_flag(self):
        self.assertIs(lane_b_mob_ai_tick.production_allowed, True)

    def test_maybe_tick_passes_through_the_same_register_and_results(self):
        mob = self.bg0002_by_placement[BG0002_OFFENSIVE_PLACEMENT]
        with redirect_stdout(io.StringIO()):
            wrapped_register, wrapped_results = lane_b_mob_ai_tick.maybe_tick(
                self.register, self.ledger, PLAYER,
                (mob.x + 100.0, mob.y, mob.z))
        from pirateforce_foundation.mob_ai_scheduler import tick_session
        direct_register, direct_results = tick_session(
            self.register, self.ledger, PLAYER, (mob.x + 100.0, mob.y, mob.z))
        self.assertEqual(
            wrapped_register.identities(), direct_register.identities())
        for identity in wrapped_register.identities():
            self.assertEqual(
                wrapped_register.state_of(identity).phase,
                direct_register.state_of(identity).phase)
        self.assertEqual(len(wrapped_results), len(direct_results))
        self.assertEqual(
            [r.after_phase for r in wrapped_results],
            [r.after_phase for r in direct_results])

    def test_only_a_phase_transition_prints_a_row_line(self):
        mob = self.bg0002_by_placement[BG0002_OFFENSIVE_PLACEMENT]
        buf = io.StringIO()
        with redirect_stdout(buf):
            _register, results = lane_b_mob_ai_tick.maybe_tick(
                self.register, self.ledger, PLAYER,
                (mob.x + 100.0, mob.y, mob.z))
        lines = [
            line for line in buf.getvalue().splitlines()
            if line.startswith("LANE_B_MOB_AI_TICK")
        ]
        transitioned = [
            r for r in results if r.before_phase != r.after_phase]
        # Measured: placement 92 (Orc Chief) is one of a five-mob offensive
        # group at this position, so more than one row acquires -- the
        # count this test pins is "one line per row that actually changed",
        # not a fixed number of mobs.  17 rows total in this register (this
        # project's largest per-session roster); the rest stay idle->idle
        # and must print nothing.
        self.assertTrue(0 < len(transitioned) < len(results))
        self.assertEqual(len(lines), len(transitioned))
        self.assertIn("idle->aggro", lines[0])
        self.assertIn("0x%X" % mob.actor_identity, "\n".join(lines))

    def test_a_no_op_pass_prints_no_row_lines(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            lane_b_mob_ai_tick.maybe_tick(
                self.dummy_register, self.dummy_ledger, PLAYER,
                (0.0, 0.0, 0.0))
        lines = [
            line for line in buf.getvalue().splitlines()
            if line.startswith("LANE_B_MOB_AI_TICK")
        ]
        self.assertEqual(lines, [])

    def test_the_fired_token_lands_on_stderr_not_stdout(self):
        # Same reason as every other lane_hooks direct-call consumer
        # (announce_direct_fire's own docstring): a --json tool's stdout
        # contract must stay pure JSON even once a future runtime.py round
        # wires this in.
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out):
            with contextlib.redirect_stderr(err):
                lane_b_mob_ai_tick.maybe_tick(
                    self.dummy_register, self.dummy_ledger, PLAYER,
                    (0.0, 0.0, 0.0))
        self.assertIn("LANE_HOOK_FIRED", err.getvalue())
        self.assertNotIn("LANE_HOOK_FIRED", out.getvalue())

    def test_a_mismatched_ledger_still_raises_not_swallowed(self):
        dummy_roster = field_mobs.load_roster()
        dummy_ledger = mob_combat.open_ledger(dummy_roster)
        with self.assertRaises(mob_combat.MobCombatContractError):
            lane_b_mob_ai_tick.maybe_tick(
                self.register, dummy_ledger, PLAYER, (0.0, 0.0, 0.0))


class WiringLineTests(unittest.TestCase):
    def test_the_wiring_line_names_dispatch_and_the_target_pos_vital(self):
        line = lane_b_mob_ai_tick.LANE_B_MOB_AI_TICK_WIRING
        self.assertIn("runtime.py dispatch", line)
        self.assertIn("TARGET_POS_VITAL", line)
        self.assertIn("identity_hi", line)
        self.assertIn("identity_lo", line)
        self.assertIn("lane_b_mob_ai_tick.maybe_tick", line)

    def test_runtime_py_now_calls_maybe_tick_per_coo_decision_0145(self):
        # WAS test_nothing_in_runtime_py_calls_maybe_tick_yet (pinned
        # NotIn), until COO-DECISION 20260901_0145 ordered lane B to paste
        # LANE_B_MOB_AI_TICK_WIRING into runtime.py's dispatch() this round.
        # Flipped rather than deleted -- the history is that this file was
        # readiness-only from round iok5z1 until this round.
        runtime_source = (SRC_ROOT / "runtime.py").read_text(
            encoding="utf-8")
        self.assertIn("lane_b_mob_ai_tick", runtime_source)
        self.assertIn(
            "lane_b_mob_ai_tick.maybe_tick(", runtime_source,
            "the wiring must call maybe_tick(), not just import the module")

    def test_this_module_and_runtime_py_are_the_only_importers_in_src(self):
        # WAS test_this_module_is_the_only_importer_of_itself_in_src
        # (asserted the importer list was empty). COO-DECISION 20260901_0145
        # named runtime.py as the one call site this round wires -- a SECOND
        # importer beyond that would still be a second, undocumented call
        # site this round did not review, so the guard stays, just widened
        # by exactly one named file.
        importers = []
        for path in SRC_ROOT.rglob("*.py"):
            if path.name == "lane_b_mob_ai_tick.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
            names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] + [
                        alias.name for alias in node.names]
                if any("lane_b_mob_ai_tick" in name for name in names):
                    importers.append(str(path.relative_to(SRC_ROOT)))
        self.assertEqual(sorted(set(importers)), ["runtime.py"])


if __name__ == "__main__":
    unittest.main()
