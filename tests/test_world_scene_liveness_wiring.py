"""CORE-REQUEST wiring: world_scene_liveness on the REAL dispatcher.

notes_to_chief/20260826_1010_LANE-A-URGENT-the-door-out-of-town-may-never-
see-anyone-arrive.md item 4-2 asked the chief for three report-only calls:
preload the ledger at server start, fan the travel gate's own console lines
into it, and call decide()/liveness_console_line() at login right after
CORE-REQUEST-003's own resolve_entry() call. ``rewrite`` was never passed as
True on either side of that letter, and this file does not pass it either --
that stays a separate, owner-ruled step (RB7) until somebody measures whether
a cross-scene arrival produces a coordinate jump.

tests/test_world_scene_liveness.py proves the module offline. This file
drives make_state_class headless -- no server process, no socket, no client
-- and proves the part that was missing: that a real login on the real
factory actually reaches decide() and actually prints the line, that an
opt-in lane stands the ledger down the same way CORE-REQUEST-004 already
requires for the travel gate, and that the travel gate's own emit hook is
the one feeding this ledger's line counter (not a second, silent parse of
the same lines).

NOT proven here: whether a client crossing a scene boundary produces a
coordinate jump. That is RB7, attended, unanswered.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    world_scene_liveness, world_scene_travel, world_travel_gate,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.population import SCENE_SEQUENCE
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore
from pirateforce_foundation.world_travel_gate import forget_preload, preload

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class LivenessReachesTheRealBootTests(unittest.TestCase):
    """Boots through ``runtime.make_state_class`` itself, not a double."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        forget_preload()
        preload()
        self.addCleanup(forget_preload)
        world_scene_liveness.SceneLivenessLedger.forget_preloaded()
        self.addCleanup(world_scene_liveness.SceneLivenessLedger.forget_preloaded)

    def tearDown(self):
        self.tmp.cleanup()

    def _real_state(self, token, capture=True, **kwargs):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector, **kwargs,
        )
        buf = io.StringIO()
        ctx = contextlib.redirect_stdout(buf) if capture else contextlib.nullcontext()
        with ctx:
            state = state_type(token)
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc(token)
            ))
            state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
            character = self.store.list_characters(
                state.foundation.account_id
            )[-1]
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        return state, buf.getvalue()

    def test_a_default_boot_prints_a_liveness_line_at_the_first_login(self):
        """A fresh character spawns at scene 1 -- HOME_SCENE_ID -- so the
        console line names the home_row branch, never the flag branch."""
        state, out = self._real_state("tok-liveness-default")
        lines = [
            line for line in out.splitlines()
            if line.startswith("WORLD_SCENE_LIVENESS ")
        ]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("decision=honour", lines[0])
        self.assertIn("reason=home_row", lines[0])
        self.assertIsInstance(
            state.scene_liveness_ledger, world_scene_liveness.SceneLivenessLedger,
        )
        self.assertIsNone(state.scene_liveness_ledger.stood_down)

    def test_the_ledger_is_the_one_process_wide_preload_not_a_fresh_copy(self):
        state, _out = self._real_state("tok-liveness-shared")
        preloaded = world_scene_liveness.SceneLivenessLedger.from_preloaded()
        self.assertIs(state.scene_liveness_ledger, preloaded)

    def test_an_opt_in_lane_stands_the_ledger_down_same_predicate_as_004(self):
        """``scenario`` (the arena lane) is one of the 26 active_lanes names
        CORE-REQUEST-004 section 3 point 2 already listed -- this ledger
        must go inert under the exact same guard, not a second copy of it."""
        reason = world_travel_gate.scenario_stand_down(frozenset({"scenario"}))
        state, out = self._real_state(
            "tok-liveness-arena", scenario="test_arena_lane",
        )
        self.assertEqual(state.scene_liveness_ledger.stood_down, reason)
        lines = [
            line for line in out.splitlines()
            if line.startswith("WORLD_SCENE_LIVENESS ")
        ]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("reason=stood_down", lines[0])
        self.assertIn("stood_down=" + reason, lines[0])

    def test_the_default_boots_inert_line_still_reaches_this_ledgers_counter(self):
        """The gate is inert by default (debug flag off) and prints exactly
        one WORLD_TRAVEL_INERT line at session construction. If the fan-out
        in runtime.py ever reverts to a bare ``emit=print`` (dropping the
        ledger from the call), this line count goes back to zero and this
        test catches it without needing the debug-only gate turned on.

        NOTE what this does NOT prove: that a WORLD_TRAVEL_SETTLED line
        (the only kind observe_console_line ever turns into a fact) reaches
        the ledger. In this project's one production configuration the gate
        never leaves DEBUG_LANE_DISABLED_REASON, so it never emits anything
        but this one INERT line and WORLD_SCENE_LIVENESS's `settles` counter
        stays 0 forever, by design and not by a wiring gap -- pf-adversary
        review of round kdx85r. See the test right below this one for the
        settle path itself, and the module docstring's stand-down section
        for what an operator should read into settles=0 in production."""
        state, out = self._real_state("tok-liveness-emit-fanout")
        self.assertTrue(
            any(line.startswith("WORLD_TRAVEL_INERT") for line in out.splitlines()),
            "the gate itself must still have printed its own inert line",
        )
        self.assertGreaterEqual(state.scene_liveness_ledger.lines_seen, 1)
        self.assertEqual(state.scene_liveness_ledger.settle_lines_seen, 0)

    def test_a_real_gate_crossing_reaches_the_ledger_through_the_production_closure(
        self,
    ):
        """pf-adversary review of round kdx85r: the test above only proves
        lines_seen counts the one WORLD_TRAVEL_INERT line every session
        prints, which would pass identically even if
        observe_console_line's SETTLED_PREFIX parsing were completely
        broken. This drives a REAL gate crossing through
        ``state.world_travel_gates`` -- the exact TravelGateSet instance
        runtime.py constructs with the ``_travel_gate_emit`` closure under
        review -- and proves the resulting WORLD_TRAVEL_SETTLED line
        actually lands in ``state.scene_liveness_ledger`` and changes what
        a later decide() answers for a character stored in that scene.
        Debug is explicitly enabled: production never reaches this path
        (see the test above), so this is the one boot configuration where
        a settle line can be produced at all to prove the fan-out works.
        """
        state, _out = self._real_state(
            "tok-liveness-real-crossing", travel_gate_debug_enabled=True,
        )
        self.assertFalse(state.world_travel_gates.is_inert)
        gates, settings = world_travel_gate.load_travel_gates()
        centre = {gate.name: gate for gate in gates}[
            "port_royal_columbus_departure"
        ].centre
        home = world_scene_travel.HOME_SCENE_ID
        stage = world_scene_travel.TEST_STAGE_SCENE_ID
        spawn = (-8553.947265625, -2579.68896484375, 186.0)
        state.world_travel_gates.observe(
            Position(home, SCENE_SEQUENCE, *spawn, 0.0))
        departure = None
        for _ in range(settings.dwell_reports + 1):
            got = state.world_travel_gates.observe(
                Position(home, SCENE_SEQUENCE, *centre, 0.0))
            if got is not None and departure is None:
                got.confirmed_fields()
                departure = got
        self.assertIsNotNone(departure, "the walk-in did not produce a crossing")
        self.assertEqual(state.scene_liveness_ledger.settle_lines_seen, 0)
        self.assertFalse(state.scene_liveness_ledger.knows(stage))

        # A real client landing near the measured spawn for scene 278 -- the
        # exact coordinates tests/test_world_scene_liveness.py's own
        # RealGateTests uses, so this exercises the same cross-check radius
        # a real crossing would, not a coordinate picked to make the test
        # pass.
        landing = Position(stage, SCENE_SEQUENCE, -13200.0, 22800.0, -2492.0, 0.0)
        state.world_travel_gates.observe(landing)

        self.assertGreaterEqual(state.scene_liveness_ledger.settle_lines_seen, 1)
        self.assertTrue(state.scene_liveness_ledger.knows(stage))
        fact = state.scene_liveness_ledger.fact(stage)
        self.assertTrue(fact.from_this_process)
        self.assertTrue(fact.cross_checked)

        verdict = world_scene_liveness.decide(landing, state.scene_liveness_ledger)
        self.assertEqual(verdict.decision, world_scene_liveness.DECISION_HONOUR)
        self.assertEqual(
            verdict.reason, world_scene_liveness.REASON_RECORDED_THIS_PROCESS,
        )

    def test_rewrite_is_never_requested_by_the_wiring(self):
        """A static guard against the one regression that would matter: the
        wiring passing rewrite=True before RB7 answers the coordinate-jump
        question the letter raises."""
        import inspect
        from pirateforce_foundation import runtime as runtime_module
        source = inspect.getsource(runtime_module)
        self.assertIn("world_scene_liveness.decide(", source)
        self.assertNotIn("rewrite=True", source)


if __name__ == "__main__":
    unittest.main()
