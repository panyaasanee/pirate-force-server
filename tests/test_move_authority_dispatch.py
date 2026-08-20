"""MOVE-AUTHORITY-DISPATCH (HYP-PF-030) -- the gate on the real dispatcher.

``tests/test_move_authority_hypothesis.py`` proves the policy offline.  This
file drives the REAL ``make_state_class`` path behind the opt-in
``scenarios/move_authority_hypothesis_speed_gate.json`` and proves the DB layer
end to end, headless -- no server process, no socket, no client:

  * the FIRST reading of a connection is measured against the authoritative
    character row, not accepted because the connection is young, and
    reconnecting does not re-arm anything beyond the one grace reading the
    server's own scene-entry teleport grants;
  * a REFUSED reading leaves the row exactly as it was, with a named no-write
    event, and never becomes the baseline the next reading is measured against;
  * an admitted reading is recorded ONLY AFTER the durable write survived: a
    checkpoint that raises leaves no admitted event, no counter and no moved
    baseline behind;
  * a server-initiated teleport reopens the grace window, so the frozen
    dispatcher moving the player itself cannot freeze the durable row for the
    rest of the session;
  * the gate changes no ACTION for the frame in hand: the gated and ungated
    sessions return the same action list, because a refusal is a write that
    does not happen and never a reply.  It DOES change the position bytes of
    the next login's StartGame, which is proven here rather than claimed away;
  * containment: with the scenario absent no lane event appears and the write
    path is the frozen one MOVE-AUTHORITY-001 characterized;
  * the lane is refused alongside every other scenario mode, and the offline
    verifier is actually executed.

NOT proven here: anything a client can see while it is playing.  A client whose
reported position is quietly not persisted may keep walking, may snap back on
the next server projection, or may not care at all -- undecidable without a
person at a screen, and queued as an attended test, not run.
"""
from __future__ import annotations

import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation import move_authority_hypothesis as mah  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "move_authority_hypothesis_speed_gate.json"
VERIFIER_PATH = ROOT / "tools" / "verify_move_authority_gate.py"
EVENT_PREFIX = "move_authority_hypothesis_"
GRACE_REOPENED_EVENT = (
    "move_authority_hypothesis_grace_reopened_after_server_teleport"
)
# The one action the frozen dispatcher queues on scene entry, and the reason
# the grace window exists at all.
SCENE_ENTRY_TELEPORT_LABEL = "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class _Clock:
    """A hand-cranked monotonic clock: the lane must never read a real one."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class MoveAuthorityDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
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
        self.scenario = mah.load_move_authority_hypothesis_scenario(SCENARIO_PATH)
        self.policy = self.scenario.policy
        self.clock = _Clock()

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ----------------------------------------------------------

    def _state_type(self, *, gated=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            move_authority_hypothesis_scenario=(
                self.scenario if gated else None
            ),
            monotonic_clock=self.clock,
        )

    def _state(self, login, *, gated=True):
        state = self._state_type(gated=gated)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(login)
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(state.foundation.account_id)
        state.selector_under_test = characters[-1].selector
        state.last_start_actions = self._select(state)
        return state

    def _reconnect(self, previous, *, gated=True):
        """A second connection for the same account and character."""
        state = self._state_type(gated=gated)(previous.token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(previous.token)
        ))
        state.selector_under_test = previous.selector_under_test
        state.last_start_actions = self._select(state)
        return state

    def _select(self, state):
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(state.selector_under_test)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        return actions

    def _target_pos_pc(self, x, y, z, heading=0.0, moving=1):
        """The exact singleton shape parse_v141_refresh_target_pos accepts."""
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.f32tag(x) + self.legacy.f32tag(y)
            + self.legacy.f32tag(z) + self.legacy.f32tag(heading)
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, 0)
        )

    def _report(self, state, x, y, z, *, heading=0.0, moving=1, after=1.0):
        self.clock.advance(after)
        return state.dispatch(self.legacy.parse_outer(
            self._target_pos_pc(x, y, z, heading, moving)
        ))

    @staticmethod
    def _f32(value):
        """What a float becomes after one round trip through the wire."""
        return struct.unpack("<f", struct.pack("<f", value))[0]

    def _f32_xyz(self, x, y, z):
        return (self._f32(x), self._f32(y), self._f32(z))

    def _row(self, state):
        character = self.store.get_character(state.foundation.selected.id)
        return (
            character.position.x, character.position.y, character.position.z,
        )

    def _origin(self, state):
        position = state.foundation.selected.position
        return position.x, position.y, position.z

    def _spend_the_grace(self, state):
        """Spend the one grace reading scene entry granted, honestly.

        Every later reading in the test is therefore measured, which is the
        state a session spends all but one of its readings in.
        """
        x, y, z = self._origin(state)
        self.assertEqual(state.move_authority_grace_remaining, 1)
        self._report(state, x, y, z)
        self.assertEqual(state.move_authority_grace_remaining, 0)
        return x, y, z

    def _lane_events(self, state):
        return [e for e in state.events if e.startswith(EVENT_PREFIX)]

    # ----- the first reading is measured, not given away --------------------

    def test_scene_entry_queues_the_teleport_that_opens_the_grace_window(self):
        state = self._state("mad01")
        labels = [action[0] for action in state.last_start_actions]
        self.assertIn(SCENE_ENTRY_TELEPORT_LABEL, labels)
        self.assertIn(GRACE_REOPENED_EVENT, state.events)
        self.assertEqual(
            state.move_authority_grace_remaining,
            self.policy.teleport_grace_reports,
        )

    def test_the_first_measured_reading_is_judged_against_the_row(self):
        """No free write for a young connection: the baseline is the ROW."""
        state = self._state("mad02")
        x, y, z = self._spend_the_grace(state)
        before = self._row(state)
        self._report(state, x + 100_000.0, y, z)
        self.assertIn(f"{EVENT_PREFIX}step_over_budget_no_write", state.events)
        self.assertEqual(self._row(state), before)

    def test_reconnecting_grants_one_grace_reading_and_no_more(self):
        """The residual bypass, pinned as a GAP so it cannot be forgotten.

        Scene entry teleports the player, so one reading per connection is
        admitted without being measured.  A client that lies in exactly that
        window writes an arbitrary position -- bounded at one reading per
        server move, re-armed by reconnecting, and closable only with the
        teleport's destination, which the frozen dispatcher does not publish.
        """
        state = self._state("mad03")
        x, y, z = self._origin(state)
        self._report(state, 999999.0, 888888.0, 777777.0)
        self.assertIn(f"{EVENT_PREFIX}teleport_grace_admitted", state.events)
        self.assertEqual(
            self._row(state), self._f32_xyz(999999.0, 888888.0, 777777.0),
        )
        # ... and the very next reading is measured against that same lie,
        # which is why the honest spawn position is now the one refused.
        row_after_the_lie = self._row(state)
        self._report(state, x, y, z)
        self.assertTrue(
            [e for e in self._lane_events(state) if e.endswith("_no_write")],
            self._lane_events(state),
        )
        self.assertEqual(self._row(state), row_after_the_lie)
        self.assertEqual(state.move_authority_grace_remaining, 0)

    # ----- the accept half --------------------------------------------------

    def test_an_admitted_walk_reaches_the_character_row(self):
        state = self._state("mad04")
        x, y, z = self._spend_the_grace(state)
        self._report(state, x + 300.0, y + 400.0, z)
        self.assertIn(f"{EVENT_PREFIX}within_budget_admitted", state.events)
        self.assertEqual(
            self._row(state), self._f32_xyz(x + 300.0, y + 400.0, z),
        )
        self.assertEqual(state.move_authority_accept_count, 2)
        self.assertEqual(state.move_authority_refusal_count, 0)

    def test_a_reading_that_does_not_move_needs_no_clock(self):
        state = self._state("mad05")
        x, y, z = self._spend_the_grace(state)
        self._report(state, x, y, z, after=0.0)
        self.assertIn(f"{EVENT_PREFIX}stationary_admitted", state.events)
        self.assertEqual(self._row(state), self._f32_xyz(x, y, z))

    def test_two_readings_inside_one_tick_are_admitted_not_divided(self):
        state = self._state("mad06")
        x, y, z = self._spend_the_grace(state)
        self._report(state, x + 100.0, y, z, after=0.0)
        self.assertIn(f"{EVENT_PREFIX}clock_too_coarse_admitted", state.events)
        self.assertEqual(self._row(state), self._f32_xyz(x + 100.0, y, z))

    def test_a_moving_flag_of_zero_does_not_refuse_a_walk(self):
        """The shipped profile does not read the flag; the authentic walk in
        ``tests/test_move_authority_hypothesis.py`` is why."""
        state = self._state("mad07")
        x, y, z = self._spend_the_grace(state)
        self._report(state, x + 200.0, y, z, moving=0)
        self.assertIn(f"{EVENT_PREFIX}within_budget_admitted", state.events)
        self.assertEqual(self._row(state), self._f32_xyz(x + 200.0, y, z))

    # ----- the refusal half -------------------------------------------------

    def test_a_reading_over_the_speed_budget_never_reaches_the_row(self):
        state = self._state("mad08")
        x, y, z = self._spend_the_grace(state)
        before = self._row(state)
        self._report(state, x + 1900.0, y, z, after=1.0)
        self.assertIn(f"{EVENT_PREFIX}speed_over_budget_no_write", state.events)
        self.assertEqual(self._row(state), before)
        self.assertEqual(state.move_authority_refusal_count, 1)
        self.assertFalse(state.move_authority_last_verdict.accepted)

    def test_a_refused_reading_never_becomes_the_next_baseline(self):
        """The whole point of holding the admitted position on the gate."""
        state = self._state("mad09")
        x, y, z = self._spend_the_grace(state)
        self._report(state, x + 100_000.0, y, z)
        self.assertIn(f"{EVENT_PREFIX}step_over_budget_no_write", state.events)
        # Measured from the refused reading this step is tiny; measured from
        # the last ADMITTED position it is another absurd jump.  It must be
        # refused, or the ladder could be climbed one refusal at a time.
        self._report(state, x + 100_050.0, y, z)
        self.assertEqual(state.move_authority_refusal_count, 2)
        self.assertEqual(self._row(state), self._f32_xyz(x, y, z))
        # And a step in budget from the last admitted position is still
        # admitted afterwards: the session is gated, not poisoned.
        self._report(state, x + 200.0, y, z)
        self.assertEqual(self._row(state), self._f32_xyz(x + 200.0, y, z))

    def test_a_vertical_jump_over_the_budget_is_refused(self):
        state = self._state("mad10")
        x, y, z = self._spend_the_grace(state)
        self._report(
            state, x + 1.0, y, z + self.policy.max_vertical_step_units + 1.0,
        )
        self.assertIn(
            f"{EVENT_PREFIX}vertical_over_budget_no_write", state.events,
        )
        self.assertEqual(self._row(state), self._f32_xyz(x, y, z))

    def test_every_reading_leaves_exactly_one_named_event(self):
        state = self._state("mad11")
        x, y, z = self._spend_the_grace(state)
        self._report(state, x + 100.0, y, z)
        self._report(state, x + 100_000.0, y, z)
        self._report(state, x + 200.0, y, z)
        lane = [
            event for event in self._lane_events(state)
            if event != GRACE_REOPENED_EVENT
        ]
        self.assertEqual(len(lane), 4)
        self.assertEqual(
            state.move_authority_accept_count
            + state.move_authority_refusal_count,
            4,
        )

    # ----- the record follows the write, never precedes it ------------------

    def test_a_durable_write_that_raises_records_no_admission(self):
        """A stale or stolen lease is the frozen path's own refusal.

        If the gate recorded the admission first, the event log would say a
        reading was admitted for a row that was never written, the counters
        would disagree with the database, and the baseline would point where no
        row points.
        """
        state = self._state("mad12")
        x, y, z = self._spend_the_grace(state)
        accepted_before = state.move_authority_accept_count
        baseline_before = state.move_authority_last_accepted_xyz
        events_before = len(self._lane_events(state))
        self.store.close_session(state.foundation.session_id)
        with self.assertRaises(PermissionError):
            self._report(state, x + 100.0, y, z)
        self.assertEqual(state.move_authority_accept_count, accepted_before)
        self.assertEqual(
            state.move_authority_last_accepted_xyz, baseline_before,
        )
        self.assertEqual(len(self._lane_events(state)), events_before)

    # ----- the gate replies to nothing, but the NEXT login differs ----------

    def test_the_gate_changes_no_action_for_the_frame_in_hand(self):
        gated = self._state("mad13")
        ungated = self._state("mad14", gated=False)
        x, y, z = self._origin(gated)
        self.assertEqual((x, y, z), self._origin(ungated))
        self._spend_the_grace(gated)
        self._report(ungated, x, y, z)
        far = (x + 100_000.0, y, z)
        gated_actions = self._report(gated, *far)
        ungated_actions = self._report(ungated, *far)
        self.assertEqual(
            [(label, bytes(pc), bytes(frame), delay)
             for label, pc, frame, delay in gated_actions],
            [(label, bytes(pc), bytes(frame), delay)
             for label, pc, frame, delay in ungated_actions],
        )
        self.assertEqual(self._row(gated), self._f32_xyz(x, y, z))
        self.assertEqual(self._row(ungated), self._f32_xyz(*far))

    def test_the_withheld_write_is_visible_in_the_next_logins_start_game(self):
        """Not a client claim -- a bytes claim, decided here.

        The frozen projector composes StartGame from the character row, so a
        write this gate withholds changes what the NEXT connection is sent.
        Whether a player notices is the attended question; that the bytes
        differ is not, and it is proven rather than left to that test.
        """
        gated = self._state("mad15")
        ungated = self._state("mad16", gated=False)
        x, y, z = self._origin(gated)
        self._spend_the_grace(gated)
        self._report(ungated, x, y, z)
        far = (x + 100_000.0, y, z)
        self._report(gated, *far)
        self._report(ungated, *far)
        gated_again = self._reconnect(gated)
        ungated_again = self._reconnect(ungated, gated=False)
        gated_start = bytes(gated_again.last_start_actions[0][1])
        ungated_start = bytes(ungated_again.last_start_actions[0][1])
        self.assertNotEqual(gated_start, ungated_start)
        self.assertIn(struct.pack("<f", self._f32(x)), gated_start)
        self.assertIn(struct.pack("<f", self._f32(far[0])), ungated_start)

    # ----- containment ------------------------------------------------------

    def test_with_the_scenario_absent_the_frozen_write_path_is_unchanged(self):
        state = self._state("mad17", gated=False)
        x, y, z = self._origin(state)
        self._report(state, x + 100_000.0, y, z)
        self.assertEqual(self._row(state), self._f32_xyz(x + 100_000.0, y, z))
        self.assertEqual(self._lane_events(state), [])
        for attribute in (
            "move_authority_accept_count", "move_authority_refusal_count",
            "move_authority_grace_remaining",
        ):
            with self.subTest(attribute=attribute):
                self.assertEqual(getattr(state, attribute), 0)
        self.assertIsNone(state.move_authority_last_accepted_xyz)

    def test_the_durable_write_has_exactly_the_two_callers_it_had_before(self):
        """The gate sits on one caller, so the caller set is part of the lane.

        ``lifecycle.exit`` is the other writer of the same row.  It is dead in
        the server today, and if a future logout lane wakes it up it will
        bypass this gate silently -- so the count is pinned here.
        """
        package = ROOT / "src" / "pirateforce_foundation"
        callers = sorted(
            path.name for path in package.glob("*.py")
            if "store.save_position(" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(callers, ["lifecycle.py"])
        lifecycle = (package / "lifecycle.py").read_text(encoding="utf-8")
        # Two: CharacterLifecycle.checkpoint, which this gate sits in front of,
        # and CharacterLifecycle.exit, which nothing in src/ calls today.
        self.assertEqual(lifecycle.count("self.store.save_position("), 2)
        runtime = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("lifecycle.exit(", runtime)
        self.assertNotIn(".close(candidate", runtime)

    def test_the_lane_is_refused_alongside_every_other_mode(self):
        from pirateforce_foundation.scene_load import load_scene_load_scenario
        other = load_scene_load_scenario(
            ROOT / "scenarios" / "scene2_fighting_fish_soldier.json"
        )
        with self.assertRaises(ValueError) as caught:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                scene_load_scenario=other,
                move_authority_hypothesis_scenario=self.scenario,
            )
        self.assertIn("mutually exclusive", str(caught.exception))

    def test_a_lookalike_profile_cannot_gate_the_dispatcher(self):
        lookalike = mah.MoveAuthorityScenario(
            self.scenario.scenario_id, self.scenario.hypothesis_id,
            self.scenario.policy,
        )
        with self.assertRaises(ValueError) as caught:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                move_authority_hypothesis_scenario=lookalike,
            )
        self.assertIn("not_allowlisted", str(caught.exception))


class MoveAuthorityToolTests(unittest.TestCase):
    """The offline verifier is only evidence if something runs it."""

    def test_the_verifier_runs_green_and_says_how_many_guards(self):
        result = subprocess.run(
            [sys.executable, str(VERIFIER_PATH)],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RESULT: PASS", result.stdout)
        self.assertNotIn("FAIL", result.stdout.replace("RESULT: PASS", ""))
        self.assertTrue(result.stdout.isascii())
        match = re.search(r"guards run: (\d+)", result.stdout)
        self.assertIsNotNone(match, result.stdout)
        self.assertGreaterEqual(int(match.group(1)), 60)

    def test_the_verifier_goes_red_when_the_thing_it_guards_is_wrong(self):
        """A verifier that cannot fail is decoration."""
        source = VERIFIER_PATH.read_text(encoding="utf-8")
        broken = source.replace(
            'guard("scenario hypothesis id", "HYP-PF-030"',
            'guard("scenario hypothesis id", "HYP-PF-999"',
            1,
        )
        self.assertNotEqual(broken, source)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken_verifier.py"
            path.write_text(broken, encoding="utf-8")
            environment = dict(os.environ)
            environment["PF_MOVE_AUTHORITY_ROOT"] = str(ROOT)
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True, text=True, cwd=str(ROOT),
                env=environment,
            )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("RESULT: FAIL", result.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
