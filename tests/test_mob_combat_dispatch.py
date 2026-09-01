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

import contextlib
import dataclasses
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import (  # noqa: E402
    make_state_class, _apply_mob_death_census_override,
)
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
        self.control_mob = next(
            m for m in self.roster if m.actor_identity == CONTROL_TARGET
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
        # RE-157 job 2 harness note: seed the announced-actor membership
        # the new mob_combat_membership guard (runtime.py's
        # ``_dispatch_mob_combat``) now requires before a field-mob target
        # can spend cadence or mutate the ledger.  This file deliberately
        # isolates combat/death wiring from real census composition
        # (test_mob_combat_census_wiring.py owns proving the
        # arrival-census-then-combat sequence itself), so the announcement
        # is seeded directly here rather than by driving a real census
        # dispatch first, which would change what these tests measure.  A
        # harmless no-op for a target that never resolves to a field-mob
        # identity (test_a_target_that_is_not_a_field_mob_sends_nothing):
        # the guard only ever consults this membership once the STATIC
        # roster has already said the target is a field mob.
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

    def _arrive(self, state):
        """Send the real arrival TargetPos BEFORE any attack, exactly the
        production order (login -> StartGame -> TargetPos -> census) instead
        of the after-the-attack ordering the two ``test_world_census_*``
        tests above use to isolate the NEXT census. This is what sets
        ``population_refresh_anchor``/``world_census_actor_count`` on
        ``state`` for real, the same two attributes CORE-REQUEST-008's
        ``MOB_COMBAT_BAR``/``MOB_DEATH_*`` recompose reads at
        ``runtime.py``'s combat dispatch site.
        """
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
        state.dispatch(self.legacy.parse_outer(pc))
        return anchor

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
        actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertEqual([delay for *_r, delay in actions], [0.0, 0.0])
        for _label, pc, frame, _delay in actions:
            self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(state.mob_combat_hit_count, 1)
        self.assertEqual(state.mob_combat_kill_count, 0)
        balance = state.mob_combat_ledger.balance_of(CONTROL_TARGET)
        self.assertEqual(
            balance.current_hp,
            self.control_mob.max_hp - mob_combat.resolve_damage(
                mob_combat.pin_attacker(), mob_combat.mob_defender(self.control_mob),
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
        self._set_balance(state, CONTROL_TARGET, 500)
        actions = self._attack(state, CONTROL_TARGET)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        # CORE-REQUEST-007 (MOB-LOOT-001): a killing blow on the sanctioned
        # target now also rolls loot (mob_loot.roll_drops against a real,
        # unseeded random.Random per session) and may append zero or more
        # MOB_LOOT_DROP frames after the death frames above.  This file
        # proves combat/death ordering, not loot -- see
        # tests/test_mob_loot.py for the roll/encode contract -- so trailing
        # entries are only checked for label, never asserted absent.
        self.assertTrue(all(label == "MOB_LOOT_DROP" for label in labels[3:]))
        delays = [delay for *_r, delay in actions]
        self.assertEqual(delays[0], 0.0)
        self.assertEqual(delays[1], 0.0)
        self.assertEqual(delays[2], mob_death.DEATH_TASK_HOLD_MS / 1000.0)
        for _label, pc, frame, _delay in actions:
            self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(
            state.mob_combat_ledger.balance_of(CONTROL_TARGET).current_hp,
            0,
        )
        self.assertTrue(state.mob_death_register.is_dead(CONTROL_TARGET))
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

        before = state.mob_combat_ledger.balance_of(CONTROL_TARGET).current_hp
        with mock.patch.object(
            mob_combat, "commit_step", side_effect=flaky_commit_step,
        ):
            actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        after = state.mob_combat_ledger.balance_of(CONTROL_TARGET).current_hp
        expected_damage = mob_combat.resolve_damage(
            mob_combat.pin_attacker(), mob_combat.mob_defender(self.control_mob),
        )
        # Exactly one hit's worth of damage landed, not two: the retry must
        # not re-apply the arithmetic a second time.
        self.assertEqual(before - after, expected_damage)
        self.assertEqual(state.mob_combat_hit_count, 1)
        self.assertEqual(state.mob_combat_ledger.generation, 1)

    # ----- a hit on an already-dead identity sends nothing -------------------

    def test_a_hit_on_an_already_dead_mob_sends_nothing(self):
        state = self._state("mc_corpse")
        self._set_balance(state, CONTROL_TARGET, 0)
        actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(actions, [])
        # The ledger still moves generation (a real hit was processed and
        # committed), but the balance stays at the floor and nothing is
        # queued for the wire -- mob_combat's own no_room path.
        self.assertEqual(
            state.mob_combat_ledger.balance_of(CONTROL_TARGET).current_hp,
            0,
        )
        self.assertEqual(state.mob_combat_hit_count, 1)
        # No second kill was attempted: the register is untouched by this
        # dispatch (CombatStep.death_due is False for a no_room outcome).
        self.assertEqual(state.mob_death_register.records, ())

    # ----- the sanctioned-scope gate is respected, not bypassed -------------

    def test_a_killing_blow_on_a_bg0001_roster_identity_now_finishes_a_kill(self):
        """COO-RULING-20260827-1350 widened mob_death.kill()'s scope to the
        10 template ids field_mob_tables.py's bg0001 roster carries (see
        mob_death.WIDENING_RULINGS) and this wiring now passes that ruling's
        exact name on every kill -- so any roster identity finishes a real
        kill, not only 0x201F/P30.  This replaces the old test of the same
        name minus "now": that test's premise ("this wiring passes no
        widened=") is exactly what the ruling made false, on purpose.
        """
        state = self._state("mc_widened_roster")
        other = next(
            m for m in self.roster if m.actor_identity != CONTROL_TARGET
        )
        self._set_balance(state, other.actor_identity, 1)
        actions = self._attack(state, other.actor_identity)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        self.assertTrue(all(label == "MOB_LOOT_DROP" for label in labels[3:]))
        self.assertTrue(state.mob_death_register.is_dead(other.actor_identity))
        self.assertEqual(
            state.mob_combat_ledger.balance_of(other.actor_identity).current_hp,
            0,
        )
        self.assertEqual(state.mob_combat_kill_count, 1)

    def test_a_killing_blow_on_a_template_no_ruling_names_still_finishes_no_kill(
        self,
    ):
        """The gate mob_death.kill() enforces is per-template_id, not "any
        roster member" -- proves it still holds end-to-end for a template no
        WIDENING_RULINGS entry names, so a future roster addition cannot walk
        through this wiring's hardcoded widened= string by accident.  A
        synthetic mob (template_id 1, which is neither 0x201F, 916, nor any
        of the 10 bg0001 ids the current ruling names) is added to the roster
        this state boots from, standing in for that future addition.
        """
        # Copy every field the AI/combat tables validate (ai_wander,
        # ai_combat, speed_walk, visual_preset) from a real, mined roster
        # mob -- only placement_index, template_id and display_name change.
        # A hand-picked ai_wander/ai_combat pair not in the mined
        # field_mob_ai_tables rows would refuse at boot for a reason
        # unrelated to what this test proves.
        outsider_mob = dataclasses.replace(
            self.control_mob,
            placement_index=9999,
            template_id=1,
            display_name="Unruled Test Mob",
        )
        with mock.patch.object(
            field_mobs, "load_roster",
            return_value=self.roster + (outsider_mob,),
        ):
            state = self._state("mc_unruled_template")
            self._set_balance(state, outsider_mob.actor_identity, 1)
            actions = self._attack(state, outsider_mob.actor_identity)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions], ["MOB_COMBAT_ANNOUNCE"],
        )
        self.assertTrue(any(
            event.startswith(
                "mob_death_refused_target_outside_the_sanctioned_scope"
            )
            for event in state.events
        ))
        self.assertFalse(
            state.mob_death_register.is_dead(outsider_mob.actor_identity)
        )
        self.assertEqual(
            state.mob_combat_ledger.balance_of(
                outsider_mob.actor_identity
            ).current_hp,
            0,
        )
        self.assertEqual(state.mob_combat_kill_count, 0)

    # ----- the world census reflects a hit that wounds but does not kill ----

    def test_world_census_after_a_non_lethal_hit_reflects_reduced_hp(self):
        """Closes the gap CHIEF_CONTINUATION.md's R182 entry names: nobody had
        driven "wounded, not dead, and the NEXT census reflects the lower HP"
        through the real dispatch -> compose path.  ``repopulation_entries``
        (see mob_death.py) already reads ``ledger.balance_of(...).current_hp``
        live on every call and ``runtime.py``'s census-compose site already
        passes the SAME ``self.mob_combat_ledger`` a hit just committed into
        -- this only proves that wiring end to end, it changes no production
        code.
        """
        state = self._state("mc_census_wound", world_census_actor_count=None)
        actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        balance = state.mob_combat_ledger.balance_of(CONTROL_TARGET)
        self.assertGreater(balance.current_hp, 0)
        self.assertLess(balance.current_hp, self.control_mob.max_hp)
        self.assertFalse(state.mob_death_register.is_dead(CONTROL_TARGET))
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
        wounded_entry = field_mobs.hostile_actor_entry(
            self.legacy, self.control_mob, current_hp=balance.current_hp,
        )
        full_hp_entry = field_mobs.hostile_actor_entry(
            self.legacy, self.control_mob, current_hp=self.control_mob.max_hp,
        )
        dead_entry = mob_death.death_actor_entry(
            self.legacy, self.control_mob, death_timer=mob_death.DEAD_TIMER_SECONDS,
        )
        # The next census composition ships the SAME identity at the SAME
        # reduced HP the ledger holds after the hit -- not the ceiling
        # world_population would have sent by default, and not a corpse.
        self.assertIn(wounded_entry, census[0][1])
        self.assertNotIn(full_hp_entry, census[0][1])
        self.assertNotIn(dead_entry, census[0][1])
        self.assertEqual(census[0][2], self.legacy.frame_pc(census[0][1]))

    # ----- the world census does not resurrect or heal a committed kill -----

    def test_world_census_override_reflects_a_committed_kill(self):
        state = self._state("mc_census", world_census_actor_count=None)
        self._set_balance(state, CONTROL_TARGET, 500)
        actions = self._attack(state, CONTROL_TARGET)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        # See the identical note in
        # test_a_killing_blow_sends_announce_then_death_frames_in_order:
        # CORE-REQUEST-007 (MOB-LOOT-001) may append MOB_LOOT_DROP frames
        # after the death frames; this test proves world-census behavior,
        # not loot.
        self.assertTrue(all(label == "MOB_LOOT_DROP" for label in labels[3:]))
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
            self.legacy, self.control_mob, death_timer=mob_death.DEAD_TIMER_SECONDS,
        )
        self.assertIn(expected_corpse_entry, census[0][1])
        default_generation = world_population.build_world_population(
            self.legacy, anchor, scene_id=1,
        )
        # A raw, un-overridden generation is the wrong baseline now that
        # runtime.py splices mob_death.full_roster_override into EVERY boot
        # (CORE-REQUEST-007's corpse_override -> full_roster_override swap):
        # that override touches all 13 roster identities unconditionally, so
        # census[0][1] would differ from default_generation.pc whether or not
        # this kill ever happened.  The baseline that still isolates "did
        # THIS kill change the wire" is the SAME override, applied against an
        # empty register/no ledger -- i.e. what the override would have
        # produced with no kill committed at all.
        no_kill_override = mob_death.full_roster_override(
            self.legacy, self.roster, mob_death.DeathRegister(),
        )
        no_kill_generation = _apply_mob_death_census_override(
            self.legacy, default_generation, no_kill_override,
        )
        self.assertNotEqual(census[0][1], no_kill_generation.pc)
        self.assertEqual(census[0][2], self.legacy.frame_pc(census[0][1]))

    # ----- PANYA-ORDER 2026-08-27 12:30 section 3: the world-wipe fix,   ----
    # ----- proven on the REAL production sequence and the REAL 115-actor ---
    # ----- census, not the after-the-attack ordering above that never    ---
    # ----- reaches the recompose branch at all (population_refresh_anchor
    # ----- is still None when those two tests attack).                  ----

    def test_a_hit_after_real_arrival_recomposes_the_bar_frame_over_115(self):
        """The order this test drives is login -> StartGame -> TargetPos
        (arrival census, sets population_refresh_anchor/world_census_actor_
        count for real) -> attack -- the actual sequence a live client
        produces, and the one CHIEF-REPLY 2026-08-27T13:30+07:00's WIRED v2
        audit measured live on the bridge (``combat_first_hit`` row). The
        two ``test_world_census_*`` tests above deliberately attack BEFORE
        any TargetPos, which lands in the ``mob_combat_bar_census_compose_
        skipped_no_population_anchor`` branch and never exercises the
        recompose this test is the missing proof for.
        """
        state = self._state("mc_real_arrival_bar")
        anchor = self._arrive(state)
        # Was 115.  SUPERSEDED 2026-08-28 (LANE-A, RE-128): the arrival census
        # assembles 108 of the 115 frozen placements, because seven of them
        # have a Mob-Set number that resolves to no CONSTDATA MOBS row and so
        # have no shippable identity.  The recompose is still over the WHOLE
        # census this boot built, which is what this test is about.
        self.assertEqual(state.world_census_actor_count, 108)
        self.assertEqual(state.population_refresh_anchor, anchor)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        printed = buf.getvalue()
        # ROUND z096sw: the line now carries a MEASUREMENT beside the input.
        # ``actor_count`` is unchanged (session state, read before the
        # compose); ``wire_actors`` is read back off the composed
        # collection's own header.  Asserted as one substring so a future
        # edit cannot drop the measurement and leave the token matching.
        self.assertIn(
            "MOB_COMBAT_BAR_CENSUS_RECOMPOSE "
            f"actor_count={state.world_census_actor_count} "
            f"wire_actors={state.world_census_actor_count} "
            f"target=0x{CONTROL_TARGET:X}",
            printed,
        )
        self.assertFalse(any(
            event.startswith("mob_combat_bar_census_compose_skipped_")
            or event.startswith("mob_combat_bar_census_compose_refused_")
            for event in state.events
        ))
        bar_pc, bar_frame, _delay = next(
            (pc, frame, delay) for label, pc, frame, delay in actions
            if label == "MOB_COMBAT_BAR"
        )
        balance = state.mob_combat_ledger.balance_of(CONTROL_TARGET)
        expected_pc, expected_frame = mob_death.hostile_census_frames(
            self.legacy, anchor, state.world_census_actor_count, self.roster,
            mob_death.DeathRegister(), ledger=state.mob_combat_ledger,
        )
        # If this ever regressed back to the one-entry frame, this equality
        # would fail (the one-entry frame is a strict subset of the 108-actor
        # collection below) -- that is the world-wipe RE-092/CORE-REQUEST-008
        # exists to prevent, proven here on the real dispatch path instead of
        # by calling the encoder directly the way mob_death.py's own offline
        # tests do.
        self.assertEqual(bar_pc, expected_pc)
        self.assertEqual(bar_frame, expected_frame)
        wounded_entry = field_mobs.hostile_actor_entry(
            self.legacy, self.control_mob, current_hp=balance.current_hp,
        )
        self.assertIn(wounded_entry, bar_pc)

    def test_a_kill_after_real_arrival_recomposes_dying_and_dead_over_115(self):
        """Same real-sequence proof as the hit test above, for the death
        half of CORE-REQUEST-008 (``combat_death`` row of the same WIRED v2
        audit).
        """
        state = self._state("mc_real_arrival_death")
        anchor = self._arrive(state)
        # Was 115; see the hit test above for why the arrival census is 108.
        self.assertEqual(state.world_census_actor_count, 108)
        self._set_balance(state, CONTROL_TARGET, 500)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = self._attack(state, CONTROL_TARGET)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        # CORE-REQUEST-007 (MOB-LOOT-001) may append MOB_LOOT_DROP frames
        # after the death frames; this test proves census-recompose behavior,
        # not loot -- same carve-out as the two pre-existing census tests.
        self.assertTrue(all(label == "MOB_LOOT_DROP" for label in labels[3:]))
        printed = buf.getvalue()
        # ROUND z096sw: both death frames are measured, on their own lines.
        # The DYING line is new; the DEAD line keeps the token every
        # existing grep already uses.
        self.assertIn(
            "MOB_DEATH_FRAMES_CENSUS_RECOMPOSE_DYING "
            f"actor_count={state.world_census_actor_count} "
            f"wire_actors={state.world_census_actor_count} "
            f"target=0x{CONTROL_TARGET:X}",
            printed,
        )
        self.assertIn(
            "MOB_DEATH_FRAMES_CENSUS_RECOMPOSE "
            f"actor_count={state.world_census_actor_count} "
            f"wire_actors={state.world_census_actor_count} "
            f"target=0x{CONTROL_TARGET:X}",
            printed,
        )
        self.assertFalse(any(
            event.startswith("mob_death_frames_census_compose_skipped_")
            or event.startswith("mob_death_frames_census_compose_refused_")
            for event in state.events
        ))
        dying_pc, _dying_frame, _d1 = next(
            (pc, frame, delay) for label, pc, frame, delay in actions
            if label == "MOB_DEATH_DYING"
        )
        dead_pc, _dead_frame, _d2 = next(
            (pc, frame, delay) for label, pc, frame, delay in actions
            if label == "MOB_DEATH_DEAD"
        )
        expected_dying_pc, _ = mob_death.hostile_census_frames(
            self.legacy, anchor, state.world_census_actor_count, self.roster,
            state.mob_death_register, ledger=state.mob_combat_ledger,
            dead_timer=mob_death.DYING_TIMER_SECONDS,
        )
        expected_dead_pc, _ = mob_death.hostile_census_frames(
            self.legacy, anchor, state.world_census_actor_count, self.roster,
            state.mob_death_register, ledger=state.mob_combat_ledger,
        )
        self.assertEqual(dying_pc, expected_dying_pc)
        self.assertEqual(dead_pc, expected_dead_pc)
        corpse_entry = mob_death.death_actor_entry(
            self.legacy, self.control_mob, death_timer=mob_death.DEAD_TIMER_SECONDS,
        )
        self.assertIn(corpse_entry, dead_pc)


if __name__ == "__main__":
    unittest.main()
