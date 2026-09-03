"""CORE-REQUEST-007 -- MOB-AI-CONTROL-001 on the REAL dispatcher.

``tests/test_mob_ai_control.py`` proves ``damage_step``/``death_step``/
``commit_step`` offline.  This file drives ``make_state_class`` headless --
same harness as ``tests/test_mob_combat_dispatch.py`` -- and proves the part
that was missing before this round: nothing in ``src/`` called this module,
so a hit that landed through ``_dispatch_mob_combat`` never touched a threat
table and a killed mob never retired its AI row.

  * a DEFAULT boot opens an AI register with one idle row per roster mob,
    same identities as the combat ledger, generation 0;
  * a hit that does not kill folds threat into the target's row (MOB_AI_
    CONTROL_WIRING step (1)), called AFTER mob_combat.commit_step, as the
    module docstring requires;
  * a killing blow retires the row to ``mob_aggro.PHASE_DEAD`` (step (2)),
    called AFTER mob_death.commit_death;
  * a target that is not a field-mob identity never reaches either lane --
    the combat dispatch itself refuses the frame first -- so the AI register
    is untouched.

NOT proven here: the tick loop (mob_ai_control.tick_step) is explicitly not
part of MOB_AI_CONTROL_WIRING and is not wired by this round either -- see
the module docstring and CORE-REQUEST-007's own letter.
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

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_aggro  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_ai_scheduler  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# ~~CONTROL_TARGET = mob_death.SANCTIONED_FIRST_TARGET_IDENTITY  # 0x201F,
# P30~~  ROUND 8ftmbx: bg0001 placement 30 is a townsman under the RE-128
# crosswalk and COO-DECISION 2026-08-29T00:41+07:00 withdrew it from what this
# lane ships, so the identity this end-to-end test drives is the roster's own
# control row -- the practice dummy the same ruling approved as the thing a
# player can hit.  The scope lock itself is untouched: runtime.py's kill site
# passes COO-RULING-20260827-1350, which covers this template.
CONTROL_TARGET = 0x2000 + field_mobs.CONTROL_PLACEMENT_INDEX + 1


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class MobAiControlDispatchTests(unittest.TestCase):
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
        self.roster = field_mobs.load_roster()
        self.control_mob = next(
            m for m in self.roster if m.actor_identity == CONTROL_TARGET
        )

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness, same shape as test_mob_combat_dispatch.py -----------

    def _state(self, token, **kwargs):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector, **kwargs,
        )
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
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    def _performer(self, state):
        selected = state.foundation.selected
        return (
            ((selected.identity_hi & 0xFFFFFFFF) << 32)
            | (selected.identity_lo & 0xFFFFFFFF)
        )

    def _action_vital_pc(
        self, target_identity, *, action_code=0,
        heading=0.0, x=0.0, y=0.0, z=0.0,
    ):
        legacy = self.legacy
        body = (
            legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, target_identity)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, action_code)
            + legacy.u32tag(0x19, 0)
            + legacy.f32tag(heading) + legacy.f32tag(x)
            + legacy.f32tag(y) + legacy.f32tag(z)
            + legacy.u8tag(0x0B, 0)
            + legacy.u16tag(0x12, 0)
            + legacy.u8tag(0x0B, 0)
        )
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.ACTION_VITAL)
            + legacy.u8tag(0x0B, 0)
            + body
        )

    def _attack(self, state, target_identity, **kwargs):
        # RE-157 job 2 harness note: seed the announced-actor membership
        # the new mob_combat_membership guard requires -- see the
        # identical note in tests/test_mob_combat_dispatch.py.
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (target_identity,),
                state.mob_combat_announced_membership_generation,
            )
        )
        return state.dispatch(self.legacy.parse_outer(
            self._action_vital_pc(target_identity, **kwargs)
        ))

    def _set_balance(self, state, identity, current_hp):
        row = state.mob_combat_ledger.balance_of(identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, current_hp)
        )

    # ----- construction ---------------------------------------------------

    def test_a_default_boot_opens_an_idle_ai_register(self):
        state = self._state("ai_init")
        self.assertEqual(
            state.mob_ai_register.identities(),
            tuple(sorted(m.actor_identity for m in self.roster)),
        )
        self.assertEqual(state.mob_ai_register.generation, 0)
        self.assertEqual(state.mob_ai_register.epoch, 0)
        for row in state.mob_ai_register.rows:
            self.assertEqual(row.state.phase, mob_aggro.PHASE_IDLE)

    # ----- a hit that does not kill ----------------------------------------

    def test_a_hit_that_does_not_kill_folds_threat_after_the_ledger_commits(
        self,
    ):
        state = self._state("ai_hit")
        self._attack(state, CONTROL_TARGET)
        self.assertNotIn(
            "mob_ai_control_damage_target_not_tracked_skipped", state.events,
        )
        self.assertGreater(state.mob_ai_register.generation, 0)
        after = state.mob_ai_register.state_of(CONTROL_TARGET)
        self.assertNotEqual(after.phase, mob_aggro.PHASE_DEAD)
        performer = self._performer(state)
        self.assertTrue(
            any(identity == performer for identity, _threat in after.threat)
        )

    # ----- a killing blow ---------------------------------------------------

    def test_a_killing_blow_retires_the_ai_row_after_death_commits(self):
        state = self._state("ai_kill")
        self._set_balance(state, CONTROL_TARGET, 500)
        self._attack(state, CONTROL_TARGET)
        self.assertTrue(state.mob_death_register.is_dead(CONTROL_TARGET))
        row = state.mob_ai_register.state_of(CONTROL_TARGET)
        self.assertEqual(row.phase, mob_aggro.PHASE_DEAD)
        self.assertEqual(row.threat, ())
        self.assertIsNone(row.target_identity)

    # ----- a target that is not a field mob --------------------------------

    def test_a_target_that_is_not_a_field_mob_leaves_the_register_untouched(
        self,
    ):
        state = self._state("ai_not_a_mob")
        performer = self._performer(state)
        outsider = performer + 1
        actions = self._attack(state, outsider)
        self.assertEqual(actions, [])
        self.assertEqual(state.mob_ai_register.generation, 0)

    # ----- REFUSE_REGISTER_STALE retries, does not lose the fold -----------

    def test_a_stale_register_refusal_retries_and_folds_exactly_once(self):
        state = self._state("ai_stale")
        real_commit_step = mob_ai_control.commit_step
        calls = {"n": 0}

        def flaky_commit_step(current, step):
            calls["n"] += 1
            if calls["n"] == 1:
                raise mob_ai_control.MobAiControlError(
                    mob_ai_control.REFUSE_REGISTER_STALE, "test-induced",
                )
            return real_commit_step(current, step)

        mob_ai_control.commit_step = flaky_commit_step
        try:
            self._attack(state, CONTROL_TARGET)
        finally:
            mob_ai_control.commit_step = real_commit_step
        self.assertEqual(calls["n"], 2)
        self.assertEqual(state.mob_ai_register.generation, 1)

    # ----- D7: the TICK actually runs, watched rather than inferred -------

    def _target_pos_pc(self, xyz, heading=0.0, moving=0, derived=0):
        # Same builder tests/test_mob_ai_tick_gate_wiring.py uses, and for
        # the same reason: a real TargetPos frame through the real parser,
        # never a synthesised call into the hook.
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + b"".join(legacy.f32tag(value) for value in (*xyz, heading))
            + legacy.u8tag(0x0B, moving)
            + legacy.u8tag(0x0B, derived)
        )

    def test_a_target_pos_frame_really_runs_the_tick_not_only_the_gate(self):
        # D7, THE DEBT tests/test_mob_aggro.py NAMES IN ITS OWN CARD:
        # "the behavioural half belongs beside
        # tests/test_mob_ai_control_dispatch.py ... until a card there shows
        # tick_step running on a frame, the shipped pin must not carry a
        # reachability claim nobody executed."  This is that card, and it
        # deliberately reads NO console token: a token proves a branch was
        # ENTERED, and what is owed is proof that the decision loop RAN.
        #
        # THE SHAPE, and why it is a hit first and a step second.  bg0001's
        # roster is four non-offensive dummies, so walking past one moves
        # nothing -- which is why this card cannot be written by walking.  A
        # hit folds threat through damage_step and, MEASURED HERE RATHER
        # THAN ASSUMED, leaves the row in PHASE_IDLE: the fold writes the
        # threat table, it does not decide a phase.  Deciding is the tick's
        # job, and one TargetPos frame is where it happens -- idle -> aggro,
        # with the threat the hit left, in the register the SESSION kept.
        # Delete the call site, discard the register it returns, or close
        # the gate, and the row is still idle and this card goes red.
        state = self._state("ai_tick_behaviour")
        self._attack(state, CONTROL_TARGET)
        after_hit = state.mob_ai_register.state_of(CONTROL_TARGET)
        self.assertEqual(after_hit.phase, mob_aggro.PHASE_IDLE)
        performer = self._performer(state)
        self.assertEqual(
            [identity for identity, _threat in after_hit.threat], [performer])
        generation_after_hit = state.mob_ai_register.generation

        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(self._target_pos_pc(
                (self.control_mob.x, self.control_mob.y, self.control_mob.z))))

        after_step = state.mob_ai_register.state_of(CONTROL_TARGET)
        self.assertEqual(
            after_step.phase, mob_aggro.PHASE_AGGRO,
            "the tick gate answers True and a TargetPos frame arrived, but "
            "the row this player hit is still idle: maybe_tick did not run, "
            "or the register it returned was discarded")
        self.assertEqual(after_step.target_identity, performer)
        self.assertGreater(
            state.mob_ai_register.generation, generation_after_hit,
            "the session kept a register the tick did not write")

    def test_the_tick_does_not_run_on_a_frame_that_is_not_a_target_pos(self):
        # The control for the card above.  pf-adversary MEASURED THE FIRST
        # DRAFT OF THIS CARD VACUOUS and it was right: it sent two ACTION
        # frames and never a TargetPos, so `state.last_target_pos` was None
        # and dispatch's SECOND conjunct short-circuited.  The mutant it
        # claims to catch -- the nested-id guard widened to "any frame" --
        # left it green, because the branch was never entered for a reason
        # this card was not testing.
        #
        # FIXED BY GIVING THE SESSION A REMEMBERED POSITION FIRST: one real
        # TargetPos frame (which ticks, and whose bump is recorded), then an
        # ACTION frame, which must NOT tick.  Now every guard except the
        # nested-id one is satisfied when the ACTION frame arrives, so the
        # nested-id guard is the only thing that can hold the tick back and
        # the mutant has nowhere to hide.
        state = self._state("ai_tick_control")
        self._attack(state, CONTROL_TARGET)
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(self._target_pos_pc(
                (self.control_mob.x, self.control_mob.y, self.control_mob.z))))
        self.assertIsNotNone(
            state.last_target_pos,
            "the TargetPos frame must leave a remembered position, or the "
            "ACTION frame below is refused by a guard that is not the one "
            "under test -- the exact hole pf-adversary measured")
        after_tick = state.mob_ai_register.state_of(CONTROL_TARGET)
        self.assertEqual(after_tick.phase, mob_aggro.PHASE_AGGRO)

        # COUNTED, NOT INFERRED FROM STATE.  A second tick on the ACTION
        # frame would recompute the same aggro state from the same
        # observation -- tick_step is pure -- so no register field can tell
        # the two apart.  What CAN is whether the driver was entered at all,
        # so the real tick_session is wrapped (never replaced: it still runs
        # and the register it returns is still what the session keeps, the
        # same shape test_a_stale_register_refusal_retries_and_folds_exactly_
        # once already uses on commit_step).
        from pirateforce_foundation.lane_hooks import lane_b_mob_ai_tick
        real_tick_session = mob_ai_scheduler.tick_session
        calls = {"n": 0}

        def counting_tick_session(*args, **kwargs):
            calls["n"] += 1
            return real_tick_session(*args, **kwargs)

        mob_ai_scheduler.tick_session = counting_tick_session
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self._attack(state, CONTROL_TARGET)
                self.assertEqual(
                    calls["n"], 0,
                    "an ACTION frame ran the aggro tick: the call site is "
                    "not guarded on TARGET_POS_VITAL any more")
                # and the positive control, in the same session and the same
                # patch, so a zero above cannot be the wrapper not being
                # installed:
                state.dispatch(self.legacy.parse_outer(self._target_pos_pc(
                    (self.control_mob.x, self.control_mob.y,
                     self.control_mob.z))))
            self.assertEqual(calls["n"], 1)
        finally:
            mob_ai_scheduler.tick_session = real_tick_session


if __name__ == "__main__":
    unittest.main()
