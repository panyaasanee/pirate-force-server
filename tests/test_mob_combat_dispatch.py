"""CORE-REQUEST -- MOB-COMBAT-001 / MOB-DEATH-001 on the REAL dispatcher.

``tests/test_mob_combat.py`` and ``tests/test_mob_death.py`` prove the two
encoders offline.  This file drives ``make_state_class`` headless -- no server
process, no socket, no client -- and proves the part that was missing before
this round: nothing in ``src/`` called either module, so an inbound EA7D
ActionVital reached nowhere near them.

  * a DEFAULT boot, constructed with no flag and no scenario of any kind, now
    answers an inbound EA7D ActionVital whose target resolves to a field-mob
    identity with the mob_combat.strike() -> mob_combat.commit_step() chain,
    and -- on a killing blow -- the mob_death.kill() -> commit_death() chain,
    exactly as MOB_COMBAT_WIRING and MOB_DEATH_WIRING describe;
  * a hit that does not kill sends the announce frame then the bar frame;
  * a killing blow sends the announce frame, then the dying frame, then the
    dead frame after ``mob_death.DEATH_TASK_HOLD_MS`` milliseconds;
  * a REFUSE_LEDGER_STALE refusal from ``commit_step`` is retried and the
    frame set that reaches the wire answers for exactly one hit, never two;
  * a hit on an already-dead identity (0 HP in the ledger) sends nothing;
  * a target that is not a field-mob identity sends nothing and disturbs no
    other lane's dispatch.

NOT proven here, and this is the load-bearing limit both modules already
state: whether a real attack input produces this exact ActionVital shape, and
whether a real client does anything at all with the frames this driver
composes.  No client has ever been shown one byte of either.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SANCTIONED_TARGET = mob_death.SANCTIONED_FIRST_TARGET_IDENTITY  # 0x201F, P30


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class MobCombatDispatchTests(unittest.TestCase):
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
        self.p30 = next(
            m for m in self.roster if m.actor_identity == SANCTIONED_TARGET
        )

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness -----------------------------------------------------

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
        # Skip the one-time bootstrap frames (runtime ack, welcome message,
        # scene music) so an attack frame is the only thing under test.  This
        # file is not about that sequencing -- test_world_census_wiring.py
        # already covers it -- and every one of these lanes is unconditional,
        # so pre-arming them changes nothing this file asserts.
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
        return state.dispatch(self.legacy.parse_outer(
            self._action_vital_pc(target_identity, **kwargs)
        ))

    def _set_balance(self, state, identity, current_hp):
        row = state.mob_combat_ledger.balance_of(identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, current_hp)
        )

    # ----- construction --------------------------------------------------

    def test_a_default_boot_opens_a_ledger_and_an_empty_register(self):
        state = self._state("mc_init")
        self.assertEqual(
            state.mob_combat_ledger.identities(),
            tuple(sorted(m.actor_identity for m in self.roster)),
        )
        for balance in state.mob_combat_ledger.balances:
            self.assertEqual(balance.current_hp, balance.max_hp)
        self.assertEqual(state.mob_death_register.records, ())
        self.assertEqual(state.mob_combat_hit_count, 0)
        self.assertEqual(state.mob_combat_kill_count, 0)

    # ----- a hit that does not kill ---------------------------------------

    def test_a_hit_that_does_not_kill_sends_announce_then_bar(self):
        state = self._state("mc_hit")
        actions = self._attack(state, SANCTIONED_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertEqual([delay for *_r, delay in actions], [0.0, 0.0])
        for _label, pc, frame, _delay in actions:
            self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(state.mob_combat_hit_count, 1)
        self.assertEqual(state.mob_combat_kill_count, 0)
        balance = state.mob_combat_ledger.balance_of(SANCTIONED_TARGET)
        self.assertEqual(
            balance.current_hp,
            self.p30.max_hp - mob_combat.resolve_damage(
                mob_combat.pin_attacker(), mob_combat.mob_defender(self.p30),
            ),
        )
        self.assertGreater(balance.current_hp, 0)
        self.assertEqual(state.mob_death_register.records, ())

    def test_a_target_that_is_not_a_field_mob_sends_nothing(self):
        state = self._state("mc_not_a_mob")
        performer = self._performer(state)
        outsider = performer + 1  # not a roster identity, not the performer
        actions = self._attack(state, outsider)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_a_field_mob_no_reply", state.events,
        )
        self.assertEqual(state.mob_combat_hit_count, 0)

    # ----- a killing blow ---------------------------------------------------

    def test_a_killing_blow_sends_announce_then_death_frames_in_order(self):
        state = self._state("mc_kill")
        # Bring the sanctioned target within one hit of the floor without
        # re-deriving the damage arithmetic here -- that is
        # tests/test_mob_combat.py's job, not this file's.
        self._set_balance(state, SANCTIONED_TARGET, 500)
        actions = self._attack(state, SANCTIONED_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        delays = [delay for *_r, delay in actions]
        self.assertEqual(delays[0], 0.0)
        self.assertEqual(delays[1], 0.0)
        self.assertEqual(delays[2], mob_death.DEATH_TASK_HOLD_MS / 1000.0)
        for _label, pc, frame, _delay in actions:
            self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(
            state.mob_combat_ledger.balance_of(SANCTIONED_TARGET).current_hp,
            0,
        )
        self.assertTrue(state.mob_death_register.is_dead(SANCTIONED_TARGET))
        self.assertEqual(state.mob_combat_hit_count, 1)
        self.assertEqual(state.mob_combat_kill_count, 1)
        # The dying frame carries a strictly-positive timer (the latch); the
        # dead frame carries a timer at or below zero (the gate) -- the
        # polarity mob_death.py calls "the single fact most likely to be got
        # backwards".
        dying_pc = actions[1][1]
        dead_pc = actions[2][1]
        self.assertNotEqual(dying_pc, dead_pc)

    # ----- REFUSE_LEDGER_STALE retries, does not double-send ----------------

    def test_a_stale_ledger_refusal_retries_and_sends_exactly_one_hit(self):
        state = self._state("mc_stale")
        real_commit_step = mob_combat.commit_step
        calls = {"n": 0}

        def flaky_commit_step(current, step):
            calls["n"] += 1
            if calls["n"] == 1:
                raise mob_combat.MobCombatContractError(
                    mob_combat.REFUSE_LEDGER_STALE, "test-induced staleness",
                )
            return real_commit_step(current, step)

        before = state.mob_combat_ledger.balance_of(SANCTIONED_TARGET).current_hp
        with mock.patch.object(
            mob_combat, "commit_step", side_effect=flaky_commit_step,
        ):
            actions = self._attack(state, SANCTIONED_TARGET)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        after = state.mob_combat_ledger.balance_of(SANCTIONED_TARGET).current_hp
        expected_damage = mob_combat.resolve_damage(
            mob_combat.pin_attacker(), mob_combat.mob_defender(self.p30),
        )
        # Exactly one hit's worth of damage landed, not two: the retry must
        # not re-apply the arithmetic a second time.
        self.assertEqual(before - after, expected_damage)
        self.assertEqual(state.mob_combat_hit_count, 1)
        self.assertEqual(state.mob_combat_ledger.generation, 1)

    # ----- a hit on an already-dead identity sends nothing -------------------

    def test_a_hit_on_an_already_dead_mob_sends_nothing(self):
        state = self._state("mc_corpse")
        self._set_balance(state, SANCTIONED_TARGET, 0)
        actions = self._attack(state, SANCTIONED_TARGET)
        self.assertEqual(actions, [])
        # The ledger still moves generation (a real hit was processed and
        # committed), but the balance stays at the floor and nothing is
        # queued for the wire -- mob_combat's own no_room path.
        self.assertEqual(
            state.mob_combat_ledger.balance_of(SANCTIONED_TARGET).current_hp,
            0,
        )
        self.assertEqual(state.mob_combat_hit_count, 1)
        # No second kill was attempted: the register is untouched by this
        # dispatch (CombatStep.death_due is False for a no_room outcome).
        self.assertEqual(state.mob_death_register.records, ())

    # ----- the sanctioned-scope gate is respected, not bypassed -------------

    def test_a_killing_blow_on_an_unsanctioned_identity_finishes_no_kill(self):
        """[PROPOSED] documents the honest degradation, does not paper over it.

        mob_death.kill refuses any identity but 0x201F unless the caller
        passes ``widened=``, and this wiring passes none -- the owner's own
        ruling says the two steps (prove on 0x201F, then widen) must not be
        merged into one round.  A field-mob other than P30 therefore converges
        to 0 HP and stays there with no death frames, exactly like every
        monster did before MOB-DEATH-001 existed.
        """
        state = self._state("mc_unsanctioned")
        other = next(
            m for m in self.roster if m.actor_identity != SANCTIONED_TARGET
        )
        self._set_balance(state, other.actor_identity, 1)
        actions = self._attack(state, other.actor_identity)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions], ["MOB_COMBAT_ANNOUNCE"],
        )
        self.assertTrue(any(
            event.startswith(
                "mob_death_refused_target_outside_the_sanctioned_scope"
            )
            for event in state.events
        ))
        self.assertFalse(state.mob_death_register.is_dead(other.actor_identity))
        self.assertEqual(
            state.mob_combat_ledger.balance_of(other.actor_identity).current_hp,
            0,
        )
        self.assertEqual(state.mob_combat_kill_count, 0)

    # ----- the world census does not resurrect or heal a committed kill -----

    def test_world_census_override_reflects_a_committed_kill(self):
        state = self._state("mc_census", world_census_actor_count=None)
        self._set_balance(state, SANCTIONED_TARGET, 500)
        actions = self._attack(state, SANCTIONED_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        anchor = (
            state.foundation.selected.position.x,
            state.foundation.selected.position.y,
            state.foundation.selected.position.z,
        )
        pc = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + b"".join(self.legacy.f32tag(v) for v in (*anchor, 0.0))
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.u8tag(0x0B, 0)
        )
        census_actions = state.dispatch(self.legacy.parse_outer(pc))
        census = [
            a for a in census_actions if a[0].startswith("WORLD_CENSUS_")
        ]
        self.assertEqual(len(census), 2)
        expected_corpse_entry = mob_death.death_actor_entry(
            self.legacy, self.p30, death_timer=mob_death.DEAD_TIMER_SECONDS,
        )
        self.assertIn(expected_corpse_entry, census[0][1])
        default_generation = world_population.build_world_population(
            self.legacy, anchor, scene_id=1,
        )
        self.assertNotEqual(census[0][1], default_generation.pc)
        self.assertEqual(census[0][2], self.legacy.frame_pc(census[0][1]))


if __name__ == "__main__":
    unittest.main()
