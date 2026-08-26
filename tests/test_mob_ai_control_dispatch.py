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

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_aggro  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
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
        self.p30 = next(
            m for m in self.roster if m.actor_identity == SANCTIONED_TARGET
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
        self._attack(state, SANCTIONED_TARGET)
        self.assertNotIn(
            "mob_ai_control_damage_target_not_tracked_skipped", state.events,
        )
        self.assertGreater(state.mob_ai_register.generation, 0)
        after = state.mob_ai_register.state_of(SANCTIONED_TARGET)
        self.assertNotEqual(after.phase, mob_aggro.PHASE_DEAD)
        performer = self._performer(state)
        self.assertTrue(
            any(identity == performer for identity, _threat in after.threat)
        )

    # ----- a killing blow ---------------------------------------------------

    def test_a_killing_blow_retires_the_ai_row_after_death_commits(self):
        state = self._state("ai_kill")
        self._set_balance(state, SANCTIONED_TARGET, 500)
        self._attack(state, SANCTIONED_TARGET)
        self.assertTrue(state.mob_death_register.is_dead(SANCTIONED_TARGET))
        row = state.mob_ai_register.state_of(SANCTIONED_TARGET)
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
            self._attack(state, SANCTIONED_TARGET)
        finally:
            mob_ai_control.commit_step = real_commit_step
        self.assertEqual(calls["n"], 2)
        self.assertEqual(state.mob_ai_register.generation, 1)


if __name__ == "__main__":
    unittest.main()
