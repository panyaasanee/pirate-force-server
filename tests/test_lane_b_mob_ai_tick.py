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

~~``test_nothing_in_runtime_py_calls_maybe_tick_yet`` is this round's own
honest half, the same discipline test_mob_ai_scheduler.py's sibling test
already uses: nothing calls this today, and this test fails the day that
stops being true without the module docstring's "WHAT THE PLAYER WILL SEE
DIFFERENTLY" section being updated to match.~~
[STALE as of round `p05wire`, 2026-09-01, COO-DECISION 20260901_0145]
[MEASURED, by reading this file itself]: that day arrived in round
`p05wire`.  The negative test above was flipped (not deleted) to
``test_runtime_py_now_calls_maybe_tick_per_coo_decision_0145``, and the
module docstring's "WHAT THE PLAYER WILL SEE DIFFERENTLY" section was
updated to match in round `3w2mfu` (this correction) -- the promise this
paragraph made to itself, kept one round later than the code that
triggered it.
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

    def test_the_wiring_line_orders_the_attribute_not_a_typed_key(self):
        # ROUND `a7k5gy`, COO-DECISION 2026-09-03T16:47+07:00 item 3 -- THE
        # ROOT CAUSE WAS IN THIS FILE, not in the chief's.  This wiring line
        # ordered the gate call with a hand-typed
        # 'lane_hooks.lane_b_mob_ai_tick', the chief pasted it verbatim into
        # runtime.py:5887 as an order from this file is meant to be pasted, and
        # lane_hooks.__init__ prefixed it into a key that exists nowhere.  The
        # gate answered False on every frame from the day the wiring landed
        # (5ac93b31, 2026-08-31 -- three days, not the eight a draft of this
        # comment borrowed off a neighbouring fact, pf-adversary D4) and the
        # only card watching was a substring search for "maybe_tick(", which
        # stayed green because the CALL was there; the gate above it was not
        # being read.
        #
        # THE GUARD, and why it is shaped like this: a literal in an order is
        # wrong in a way no reader sees, because it is a string in prose and
        # nobody diffs prose against a registry.  MODULE_NAME is the key
        # _discover() actually registers, so it cannot drift from it.  This
        # card therefore requires the ATTRIBUTE and forbids ANY quoted form of
        # the module's name inside the gate order -- not just today's exact
        # spelling, since the next hand-typed key would be a different wrong
        # string, and a card that only knows the last mistake is a card against
        # history.
        line = lane_b_mob_ai_tick.LANE_B_MOB_AI_TICK_WIRING
        opener = "module_production_allowed("
        self.assertIn(opener, line)
        # THE ARGUMENTS ONLY, AND ALL OF THEM.  Two earlier drafts of this
        # card were wrong in opposite directions and pf-adversary measured
        # both (D5):
        #  * the first forbade any quoted word starting "lane" ANYWHERE in the
        #    string.  Over-broad: this same order already quotes
        #    'from .lane_hooks import lane_b_mob_ai_tick' as the import a
        #    future round must add -- prose about a source line, not a key
        #    handed to a resolver -- and any future 'lane_id' dict key or
        #    'lane_b_tick' telemetry string would be accused of the
        #    20260903_1647 defect it has nothing to do with.
        #  * the second read only the FIRST module_production_allowed( in the
        #    order.  Under-broad: an order that gates correctly on
        #    MODULE_NAME and then gates a SECOND lane on a hand-typed key
        #    passed every assertion, the chief pastes it, and the identical
        #    bug ships one module over in a line this card certified.
        # So: every gate the order places, and what may not appear in any of
        # their arguments is a quote.
        arguments = [chunk.split(")", 1)[0]
                     for chunk in line.split(opener)[1:]]
        for argument in arguments:
            for quote in ("'", '"'):
                self.assertNotIn(
                    quote, argument,
                    "the wiring order hands a gate a hand-typed key (%r): "
                    "that is the exact defect COO-DECISION 20260903_1647 "
                    "item 3 ordered removed from this line, and a literal "
                    "here is wrong in a way no reader of prose can see"
                    % (argument,))
        self.assertIn(
            "lane_b_mob_ai_tick.MODULE_NAME", arguments,
            "the wiring order must hand the gate this module's own "
            "MODULE_NAME, so the argument cannot drift from the key "
            "lane_hooks._discover() registered -- it currently orders %r"
            % (arguments,))
        # And the attribute it orders has to EXIST and be the registry key, or
        # the order is a different kind of wrong: runtime.py would raise
        # AttributeError instead of silently answering False.
        self.assertEqual(
            lane_b_mob_ai_tick.MODULE_NAME,
            lane_b_mob_ai_tick.__name__,
            "MODULE_NAME is not this module's own __name__, so it is not the "
            "key lane_hooks registers it under")

    # ~~test_the_gate_answers_true_to_the_name_the_wiring_orders~~ -- WRITTEN
    # AND DELETED IN THE SAME ROUND (`a7k5gy`), by pf-adversary D3, which is
    # the round's own subject caught in the round's own new code.  It asserted
    # module_production_allowed(MODULE_NAME) is True.  But _discover()
    # registers under __name__, the card above already requires MODULE_NAME to
    # EQUAL __name__, and test_production_allowed_is_true_with_no_flag already
    # pins the flag -- so it was a whole test that could only fail after one of
    # those had already failed.  Decoration, and this diff's own prose condemns
    # it twelve lines away: "repeating it here would be a second copy, not a
    # second guard."  The one place that expression earns its keep is inside
    # tests/test_mob_aggro.py::test_the_tick_gate_is_reported_not_assumed,
    # where it is the CONTROL that separates "the argument did not resolve"
    # from "the lane was switched off" -- two states the gate answers
    # identically, on purpose, by its own docstring.

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
