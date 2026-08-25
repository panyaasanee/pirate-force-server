"""LANE-B / MOB-DEATH-001: the half where the monster actually dies.

The load-bearing tests in this file are these five.

``test_the_corpse_body_is_the_live_body_plus_one_tagged_float`` is the one that
matters most.  This module composes a BasicAttr body by hand because the death
timer lands in the MIDDLE of the block, and the only thing that keeps a
hand-written composer honest is that its timerless projection reproduces
``field_mobs.hostile_npc_attr`` byte for byte - the body this project already
ships and whose bar movement GT-035 watched.  This test pins that equality and
the exact five-byte delta.

``test_the_timer_polarity_is_the_one_the_client_reads`` guards the single fact
the probe lane says is most likely to be got backwards: ``timer > 0`` is DYING
and ``timer <= 0`` is DEAD.  A module with these swapped composes two frames
that look right and kill nothing.

``test_the_constants_are_the_proven_ones`` pins every wire constant and every
static VA against ``runtimeres_death_hypothesis``, the scenario-gated lane that
derived them.  This module re-declares them because a flagless build cannot
reach a probe lane, so the copy has to be checked rather than trusted.

``test_the_two_frames_reproduce_the_probe_lane_bytes`` goes further than
constants: it composes the probe lane's own actor for a body with no name and
no faction and requires this module's encoder to produce the SAME BYTES the
probe lane's encoder produces, with and without the timer.

``test_a_reapply_does_not_resurrect_the_dead`` pins the hazard this lane
closes.  field_mobs re-sends the whole collection after model readiness and on
every later rebuild; every one of those sends carries a live body for every
roster row, so without this filter a monster killed between two of them stands
back up at full HP with no hit, no frame and no error anywhere.
"""

import ast
import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    field_mobs,
    mob_combat,
    mob_death,
    runtimeres_death_hypothesis,
)
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_combat import Combatant, open_ledger, strike
from pirateforce_foundation.mob_death import (
    DEAD_TIMER_SECONDS,
    DYING_TIMER_SECONDS,
    HP_WHEN_DEAD,
    DeathRecord,
    DeathRegister,
    DeathStep,
    MobDeathContractError,
    basic_mask_of,
    corpse_npc_attr,
    dead_frames,
    describe_death,
    dying_frames,
    kill,
    live_roster,
    pin_document,
    production_allowed,
    repopulation_entries,
    repopulation_frames,
    test_only,
)


PERFORMER = 0x750059
# Strong enough to reach zero in one hit, so a test does not have to loop the
# ladder to get to the thing it is testing.
LETHAL = Combatant(level=1000, ability_str=100000, ability_con=0)


class MobDeathTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = field_mobs.load_roster()
        cls.mob = [m for m in cls.roster if m.placement_index == 30][0]

    def killing_outcome(self, mob=None):
        target = self.mob if mob is None else mob
        step = strike(
            self.legacy, None, open_ledger(), None, target, PERFORMER, LETHAL)
        return step

    # -- the body ---------------------------------------------------------

    def test_the_corpse_body_is_the_live_body_plus_one_tagged_float(self):
        live = field_mobs.hostile_npc_attr(
            self.legacy, self.mob, current_hp=self.mob.max_hp)
        corpse = corpse_npc_attr(
            self.legacy, self.mob, death_timer=DEAD_TIMER_SECONDS)
        self.assertEqual(len(corpse), len(live) + 5)
        live_mask = basic_mask_of(self.legacy, live, self.mob.actor_identity)
        corpse_mask = basic_mask_of(
            self.legacy, corpse, self.mob.actor_identity)
        self.assertEqual(live_mask, 0x070D)
        self.assertEqual(corpse_mask, live_mask | 0x0080)
        self.assertEqual(corpse_mask, 0x078D)
        # The five bytes are the tagged f32 and they sit in EXACTLY one place:
        # after max HP, before the scene id.  Built as an insertion at a
        # computed offset rather than searched for, so this cannot pass by
        # finding the same five bytes somewhere else in the body.
        timer_bytes = bytes(self.legacy.f32tag(DEAD_TIMER_SECONDS))
        self.assertEqual(len(timer_bytes), 5)
        self.assertEqual(timer_bytes[0], mob_death.DEATH_TIMER_TAG)
        prefix = (
            bytes(self.legacy.u8tag(0x0B, 1))
            + bytes(self.legacy.qwordtag(0x32, self.mob.actor_identity))
            + bytes(self.legacy.u16tag(0x12, live_mask))
            + bytes(self.legacy.wstr_tag(self.mob.display_name))
            + bytes(self.legacy.u32tag(0x14, self.mob.max_hp))   # current hp
            + bytes(self.legacy.u32tag(0x14, self.mob.max_hp))   # max hp
        )
        self.assertTrue(live.startswith(prefix))
        cut = len(prefix)
        dead_prefix = (
            bytes(self.legacy.u8tag(0x0B, 1))
            + bytes(self.legacy.qwordtag(0x32, self.mob.actor_identity))
            + bytes(self.legacy.u16tag(0x12, corpse_mask))
            + bytes(self.legacy.wstr_tag(self.mob.display_name))
            + bytes(self.legacy.u32tag(0x14, 0))                 # current hp
            + bytes(self.legacy.u32tag(0x14, self.mob.max_hp))   # max hp
        )
        self.assertEqual(len(dead_prefix), cut)
        self.assertEqual(
            corpse, dead_prefix + timer_bytes + live[cut:])

    def test_the_hp_and_the_timer_are_refused_apart(self):
        # bit 0x0080 on a body that still has HP is a lethal field no gate
        # reads: both predicates require +0x44 == 0 before they look at +0x58
        with self.assertRaises(MobDeathContractError) as caught:
            corpse_npc_attr(
                self.legacy, self.mob, death_timer=0.0, current_hp=100)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_LIVE_HP_WITH_A_DEATH_TIMER)
        # and the live lane refuses the other half of the same mistake
        with self.assertRaises(mob_combat.MobCombatContractError) as combat:
            mob_combat.bar_frames(self.legacy, self.mob, 0)
        self.assertEqual(
            combat.exception.reason,
            mob_combat.REFUSE_BAR_FRAME_FOR_A_DEAD_BODY)

    def test_the_composer_fails_closed_if_the_live_projection_drifts(self):
        # D-CLOSED.  The degradation check is the whole reason to believe the
        # widened encoder: break the frozen body it degrades to and NO bytes
        # come back, rather than a guessed body going on the wire.
        real = field_mobs.hostile_npc_attr

        def drifted(*args, **kwargs):
            return real(*args, **kwargs) + b"\x00"

        field_mobs.hostile_npc_attr = drifted
        try:
            with self.assertRaises(MobDeathContractError) as caught:
                corpse_npc_attr(
                    self.legacy, self.mob, death_timer=DEAD_TIMER_SECONDS)
        finally:
            field_mobs.hostile_npc_attr = real
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_BODY_OFF_THE_LIVE_PROJECTION)
        # and the real one still composes, so the swap really was the cause
        self.assertTrue(corpse_npc_attr(
            self.legacy, self.mob, death_timer=DEAD_TIMER_SECONDS))

    # -- the gate ---------------------------------------------------------

    def test_the_timer_polarity_is_the_one_the_client_reads(self):
        self.assertGreater(DYING_TIMER_SECONDS, 0.0)
        self.assertLessEqual(DEAD_TIMER_SECONDS, 0.0)
        with self.assertRaises(MobDeathContractError) as caught:
            dying_frames(self.legacy, self.mob, death_timer=0.0)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE)
        with self.assertRaises(MobDeathContractError) as caught:
            dead_frames(self.legacy, self.mob, death_timer=1.0)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE)
        # and the two frames differ by exactly the four bytes of the float
        dying = dying_frames(self.legacy, self.mob)[1]
        dead = dead_frames(self.legacy, self.mob)[1]
        self.assertEqual(len(dying), len(dead))
        self.assertEqual(
            sum(1 for a, b in zip(dying, dead) if a != b),
            sum(1 for a, b in zip(
                bytes(self.legacy.f32tag(DYING_TIMER_SECONDS)),
                bytes(self.legacy.f32tag(DEAD_TIMER_SECONDS))) if a != b),
        )

    def test_the_constants_are_the_proven_ones(self):
        probe = runtimeres_death_hypothesis
        pairs = (
            (mob_death.BASIC_BIT_CURRENT_HP, probe.BASIC_BIT_CURRENT_HP),
            (mob_death.BASIC_BIT_MAX_HP, probe.BASIC_BIT_MAX_HP),
            (mob_death.BASIC_BIT_DEATH_TIMER, probe.BASIC_BIT_DEATH_TIMER),
            (mob_death.BASIC_BIT_SCENE_ID, probe.BASIC_BIT_SCENE_ID),
            (mob_death.BASIC_BIT_SCENE_SEQ, probe.BASIC_BIT_SCENE_SEQ),
            (mob_death.DEATH_TIMER_TAG, probe.DEATH_TIMER_TAG),
            (mob_death.DEATH_TIMER_WIDTH, probe.DEATH_TIMER_WIDTH),
            (mob_death.DEATH_TIMER_OBJECT_OFFSET, probe.DEATH_TIMER_OFFSET),
            (mob_death.DYING_PREDICATE_VA, probe.DYING_LATCH_PREDICATE_VA),
            (mob_death.DEATH_PREDICATE_VA, probe.DEATH_TASK_PREDICATE_VA),
            (mob_death.DYING_TIMER_SECONDS, probe.DYING_LATCH_TIMER_SECONDS),
            (mob_death.DEAD_TIMER_SECONDS, probe.DEATH_TASK_TIMER_SECONDS),
            (mob_death.HP_WHEN_DEAD, probe.RUNTIMERES_DEATH_HP_ZERO),
            (mob_death.NPC_BIT_TEMPLATE, probe.NPC_BIT_TEMPLATE),
            (mob_death.NPC_BIT_VISUAL_PRESET, probe.NPC_BIT_VISUAL_PRESET),
        )
        for mine, theirs in pairs:
            self.assertEqual(mine, theirs)
        # the faction bit is the OTHER lane's, and it is pinned there
        self.assertEqual(
            mob_death.BASIC_BIT_FACTION, field_mobs.BASIC_BIT_FACTION)
        self.assertEqual(mob_death.BASIC_BIT_NAME, field_mobs.BASIC_BIT_NAME)
        # and the floor mob_combat now stops at IS the HP this lane sends
        self.assertEqual(mob_combat.HP_FLOOR, HP_WHEN_DEAD)

    def test_the_two_frames_reproduce_the_probe_lane_bytes(self):
        # Constants agreeing is not the same as bytes agreeing.  Composed for
        # the probe lane's own actor - no name, no faction - this module's
        # encoder must produce what that lane's encoder produces, both with
        # the timer and without it.
        probe = runtimeres_death_hypothesis
        actor = probe.resolve_probe(self.legacy)
        unlock = probe._UNLOCK
        stand_in = field_mobs.FieldMob(
            placement_index=actor.placement_index,
            template_id=actor.template_id,
            x=actor.x, y=actor.y, z=actor.z,
            visual_preset=actor.visual_preset,
            display_name="",
            level=1, rank=1, ai_wander=0, ai_combat=0, speed_walk=100,
            max_hp=probe.RUNTIMERES_DEATH_HP_MAX,
            drops_normal=0, drops_equipment=0, drops_specially=0,
        )
        self.assertEqual(stand_in.actor_identity, actor.actor_identity)
        # the probe lane's body carries no faction field, so the comparison is
        # made against THEIR bytes with the faction spliced in exactly the way
        # field_mobs splices it: bit 0x0400 set, the tagged u32 at the end of
        # the BasicAttr block.  A drift in either lane breaks this.
        tail = (
            bytes(self.legacy.u8tag(0x0B, 0x01 | 0x04))
            + bytes(self.legacy.u16tag(0x12, actor.template_id))
            + bytes(self.legacy.wstr_tag(actor.visual_preset))
        )
        mask_at = 11 + 1
        for timer in (DYING_TIMER_SECONDS, DEAD_TIMER_SECONDS):
            theirs = probe.encode_death_capable_npc_attr(
                self.legacy, actor, current_hp=probe.RUNTIMERES_DEATH_HP_ZERO,
                max_hp=probe.RUNTIMERES_DEATH_HP_MAX,
                death_timer=timer, lethal=unlock,
            )
            self.assertTrue(theirs.endswith(tail))
            splice_at = len(theirs) - len(tail)
            theirs_mask = int.from_bytes(theirs[mask_at:mask_at + 2], "little")
            self.assertEqual(theirs_mask, 0x038C)
            expected = (
                theirs[:mask_at]
                + int(theirs_mask | field_mobs.BASIC_BIT_FACTION).to_bytes(
                    2, "little")
                + theirs[mask_at + 2:splice_at]
                + bytes(self.legacy.u32tag(
                    0x14, field_mobs.FIELD_MOB_FACTION))
                + theirs[splice_at:]
            )
            ours = corpse_npc_attr(
                self.legacy, stand_in, death_timer=timer,
                scene_id=actor.scene_id, scene_sequence=actor.scene_sequence,
                with_name=False,
            )
            self.assertEqual(ours, expected)
            self.assertEqual(
                basic_mask_of(self.legacy, ours, actor.actor_identity),
                0x078C)

    # -- the kill ---------------------------------------------------------

    def test_a_kill_needs_an_outcome_that_actually_killed(self):
        weak = Combatant(level=7, ability_str=132, ability_con=0)
        step = strike(
            self.legacy, None, open_ledger(), None, self.mob, PERFORMER, weak)
        self.assertFalse(step.outcome.death_due)
        with self.assertRaises(MobDeathContractError) as caught:
            kill(self.legacy, self.mob, step.outcome, DeathRegister())
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_OUTCOME_IS_NOT_A_KILL)

    def test_a_kill_refuses_an_outcome_about_another_monster(self):
        other = [m for m in self.roster if m.placement_index != 30][0]
        step = self.killing_outcome()
        with self.assertRaises(MobDeathContractError) as caught:
            kill(self.legacy, other, step.outcome, DeathRegister())
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER)

    def test_a_kill_refuses_an_outcome_from_another_ceiling(self):
        # The announced number came from one ceiling and the body would be
        # composed against another, which is how a client ends up watching a
        # monster die at a bar it never had.
        step = self.killing_outcome()
        wrong_ceiling = field_mobs.FieldMob(
            **{**self.mob.__dict__, "max_hp": self.mob.max_hp + 1})
        with self.assertRaises(MobDeathContractError) as caught:
            kill(self.legacy, wrong_ceiling, step.outcome, DeathRegister())
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_OUTCOME_DISAGREES_WITH_ROSTER)

    def test_a_second_kill_on_the_same_corpse_is_refused(self):
        step = self.killing_outcome()
        first = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        with self.assertRaises(MobDeathContractError) as caught:
            kill(self.legacy, self.mob, step.outcome, first.register)
        self.assertEqual(caught.exception.reason, mob_death.REFUSE_ALREADY_DEAD)

    def test_the_killing_blow_hands_over_instead_of_repainting_a_bar(self):
        step = self.killing_outcome()
        self.assertEqual(step.outcome.hp_after, HP_WHEN_DEAD)
        self.assertTrue(step.death_due)
        self.assertEqual(step.frames, (step.announce_frame,))
        self.assertEqual(step.bar_frame, b"")
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        self.assertEqual(death.frames, (death.dying_frame, death.dead_frame))
        self.assertEqual(
            death.schedule,
            ((0, death.dying_frame), (death.hold_ms, death.dead_frame)))
        self.assertEqual(death.record.killer_identity, PERFORMER)
        self.assertEqual(death.record.actor_identity, self.mob.actor_identity)
        self.assertTrue(death.register.is_dead(self.mob.actor_identity))

    def test_a_hit_on_a_corpse_stays_silent(self):
        step = self.killing_outcome()
        again = strike(
            self.legacy, None, step.ledger, None, self.mob, PERFORMER, LETHAL)
        self.assertTrue(again.outcome.no_room)
        self.assertEqual(again.frames, ())
        self.assertFalse(again.death_due)
        self.assertTrue(
            any("already dead" in line
                for line in mob_combat.describe_step(again)))

    def test_a_hit_on_something_already_dead_is_not_a_kill(self):
        # THE ONE THE ADVERSARIAL REVIEW EXECUTED.  A no_room outcome carries
        # death_due=True (it IS at the floor), and commit_step accepts the
        # step because the ledger did not move - so a wiring line reading
        # outcome.death_due would send a SECOND pair of lethal frames at a
        # body already on the ground.
        step = self.killing_outcome()
        again = strike(
            self.legacy, None, step.ledger, None, self.mob, PERFORMER, LETHAL)
        self.assertTrue(again.outcome.no_room)
        self.assertTrue(again.outcome.death_due)   # the trap
        self.assertFalse(again.death_due)          # the property that is safe
        with self.assertRaises(MobDeathContractError) as caught:
            kill(self.legacy, self.mob, again.outcome, DeathRegister())
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_OUTCOME_IS_NOT_A_KILL)
        self.assertIn("already dead", caught.exception.detail)

    def test_an_outcome_that_moved_nothing_cannot_kill(self):
        # With HP_FLOOR at 0 an outcome with hp_before == hp_after == 0 became
        # CONSTRUCTIBLE for the first time this round, and the first draft of
        # kill() accepted it and composed both lethal frames for a monster
        # nobody hit.
        untouched = mob_combat.HitOutcome(
            PERFORMER, self.mob.actor_identity, 0, 0, mob_combat.FLAGS_MISS,
            0, 0, self.mob.max_hp, 0, True, True, False)
        with self.assertRaises(MobDeathContractError) as caught:
            kill(self.legacy, self.mob, untouched, DeathRegister())
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_OUTCOME_IS_NOT_A_KILL)
        self.assertIn("moved nothing", caught.exception.detail)

    def test_a_timer_that_underflows_to_zero_cannot_pass_as_dying(self):
        # struct.pack("<f", 1e-46) is four zero bytes, so a "strictly
        # positive" dying timer under ~1.4e-45 goes on the wire as 0.0 and
        # composes a DEAD frame that passed a DYING check.  The gate reads the
        # f32 round trip now, not the Python double.
        for underflow in (1e-46, 1e-50, 1e-300):
            self.assertGreater(underflow, 0.0)
            self.assertEqual(mob_death.as_wire_float(underflow), 0.0)
            with self.assertRaises(MobDeathContractError) as caught:
                dying_frames(self.legacy, self.mob, death_timer=underflow)
            self.assertEqual(
                caught.exception.reason,
                mob_death.REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE)
            with self.assertRaises(MobDeathContractError):
                kill(self.legacy, self.mob, self.killing_outcome().outcome,
                     DeathRegister(), dying_timer=underflow)
        # and the smallest value that DOES survive the round trip is allowed
        self.assertGreater(mob_death.as_wire_float(1e-44), 0.0)
        dying_frames(self.legacy, self.mob, death_timer=1e-44)

    def test_a_step_whose_frames_are_identical_is_refused(self):
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        with self.assertRaises(MobDeathContractError) as caught:
            DeathStep(
                death.record, death.dead_pc, death.dead_frame,
                death.dead_pc, death.dead_frame, death.register,
                death.hold_ms, 0, DYING_TIMER_SECONDS, DEAD_TIMER_SECONDS)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE)

    def test_two_kills_in_one_tick_cannot_lose_one_of_them(self):
        # DeathRegister had no generation in the first draft: two players
        # killing two DIFFERENT monsters both read the empty register, both
        # returned a register of one, and whichever was stored second erased
        # the other kill - silently, and the erased monster stands back up at
        # full HP on the next rebuild.
        other = [m for m in self.roster if m.placement_index != 30][0]
        first = self.killing_outcome()
        second = self.killing_outcome(other)
        stored = DeathRegister()
        a = kill(self.legacy, self.mob, first.outcome, stored)
        b = kill(self.legacy, other, second.outcome, stored)
        stored = mob_death.commit_death(stored, a)
        with self.assertRaises(MobDeathContractError) as caught:
            mob_death.commit_death(stored, b)
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_REGISTER_STALE)
        # the loser re-reads and re-runs, and now both deaths are recorded
        redone = kill(self.legacy, other, second.outcome, stored)
        stored = mob_death.commit_death(stored, redone)
        self.assertEqual(
            stored.identities(),
            tuple(sorted((self.mob.actor_identity, other.actor_identity))))
        self.assertEqual(stored.generation, 2)

    def test_the_census_override_names_only_what_changed(self):
        # repopulation_entries builds a collection of THIS lane's thirteen
        # monsters, but field_mobs says the correct wiring is the OVERRIDE and
        # not a second collection - and the census that actually ships
        # (world_population) rebuilds every placement at full HP.
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        override = mob_death.corpse_override(
            self.legacy, self.roster, death.register)
        self.assertEqual(list(override), [self.mob.actor_identity])
        self.assertEqual(
            override[self.mob.actor_identity],
            mob_death.death_actor_entry(
                self.legacy, self.mob, death_timer=DEAD_TIMER_SECONDS))
        # with a ledger, the living wounded are in it too, and nobody else is
        weak = Combatant(level=7, ability_str=132, ability_con=0)
        hurt = strike(
            self.legacy, None, step.ledger, None,
            [m for m in self.roster if m.placement_index != 30][0],
            PERFORMER, weak)
        wider = mob_death.corpse_override(
            self.legacy, self.roster, death.register, ledger=hurt.ledger)
        self.assertEqual(
            sorted(wider),
            sorted((self.mob.actor_identity,
                    hurt.outcome.target_identity)))

    def test_repopulation_frames_can_take_the_safe_path(self):
        # The convenience wrapper had no ledger parameter at all, so the
        # module's own whole-scene helper could not express the safe call.
        weak = Combatant(level=7, ability_str=132, ability_con=0)
        step = strike(
            self.legacy, None, open_ledger(), None, self.mob, PERFORMER, weak)
        safe_pc, _ = mob_death.repopulation_frames(
            self.legacy, self.roster, DeathRegister(), ledger=step.ledger)
        healed_pc, _ = mob_death.repopulation_frames(
            self.legacy, self.roster, DeathRegister())
        self.assertNotEqual(safe_pc, healed_pc)
        entries = repopulation_entries(
            self.legacy, self.roster, DeathRegister(), ledger=step.ledger)
        self.assertEqual(
            safe_pc, self.legacy.make_runtime_remote_actors(entries)[0])

    def test_a_ledger_from_another_roster_refuses_in_this_lane_s_name(self):
        # mob_combat's refusal is the right refusal in the wrong module's
        # name, and a caller catching MobDeathContractError would have missed
        # it entirely.
        stranger = mob_combat.CombatLedger(
            (mob_combat.MobBalance(0x9001, 10, 10),))
        with self.assertRaises(MobDeathContractError) as caught:
            repopulation_entries(
                self.legacy, self.roster, DeathRegister(), ledger=stranger)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_LEDGER_DISAGREES_WITH_REGISTER)

    def test_the_console_prints_the_timers_that_were_sent(self):
        # Not the module constants: a line that prints 20.0 for a frame
        # carrying something else is a diagnostic that lies exactly when it
        # is needed.
        step = self.killing_outcome()
        death = kill(
            self.legacy, self.mob, step.outcome, DeathRegister(),
            dying_timer=3.5, dead_timer=-1.0)
        joined = "\n".join(describe_death(death))
        self.assertIn("3.5", joined)
        self.assertIn("-1.0", joined)
        self.assertNotIn("20.0", joined)

    def test_the_step_cannot_carry_a_register_that_forgot_the_kill(self):
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        with self.assertRaises(MobDeathContractError) as caught:
            DeathStep(
                death.record, death.dying_pc, death.dying_frame,
                death.dead_pc, death.dead_frame, DeathRegister(),
                death.hold_ms,
            )
        self.assertEqual(caught.exception.reason, mob_death.REFUSE_NOT_DEAD)

    # -- the register -----------------------------------------------------

    def test_the_register_is_sorted_unique_and_never_mutated(self):
        first = DeathRegister()
        rows = tuple(
            DeathRecord(m.actor_identity, PERFORMER, m.max_hp)
            for m in self.roster[:3]
        )
        second = first
        for row in rows:
            second = second.with_death(row)
        self.assertEqual(first.records, ())
        self.assertEqual(
            second.identities(), tuple(sorted(r.actor_identity for r in rows)))
        with self.assertRaises(MobDeathContractError) as caught:
            DeathRegister(tuple(reversed(second.records)))
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_REGISTER_NOT_SORTED)
        with self.assertRaises(MobDeathContractError) as caught:
            DeathRegister((rows[0], rows[0]))
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_DUPLICATE_REGISTER_IDENTITY)
        # two registers built from the same kills compare equal
        third = DeathRegister()
        for row in reversed(rows):
            third = third.with_death(row)
        self.assertEqual(second, third)

    def test_a_reapply_does_not_resurrect_the_dead(self):
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        entries = repopulation_entries(self.legacy, self.roster, death.register)
        self.assertEqual(len(entries), len(self.roster))
        live_entry = field_mobs.hostile_actor_entry(self.legacy, self.mob)
        index = [m.actor_identity for m in self.roster].index(
            self.mob.actor_identity)
        self.assertNotEqual(entries[index], live_entry)
        self.assertEqual(
            entries[index],
            mob_death.death_actor_entry(
                self.legacy, self.mob, death_timer=DEAD_TIMER_SECONDS))
        # everybody else is sent exactly as field_mobs would send them
        for position, mob in enumerate(self.roster):
            if mob.actor_identity == self.mob.actor_identity:
                continue
            self.assertEqual(
                entries[position],
                field_mobs.hostile_actor_entry(self.legacy, mob))
        pc, frame = repopulation_frames(
            self.legacy, self.roster, death.register)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(
            live_roster(self.roster, death.register),
            tuple(m for m in self.roster
                  if m.actor_identity != self.mob.actor_identity),
        )

    def test_a_reapply_does_not_heal_the_wounded_either(self):
        # The other half of the same hazard, and the one that has no frame of
        # its own to announce it: a monster at a third of its bar is re-sent
        # at its ceiling by field_mobs, so the drop the player just watched is
        # undone silently on the next re-apply.
        weak = Combatant(level=7, ability_str=132, ability_con=0)
        step = strike(
            self.legacy, None, open_ledger(), None, self.mob, PERFORMER, weak)
        self.assertLess(step.outcome.hp_after, self.mob.max_hp)
        index = [m.actor_identity for m in self.roster].index(
            self.mob.actor_identity)
        healed = repopulation_entries(
            self.legacy, self.roster, DeathRegister())
        remembered = repopulation_entries(
            self.legacy, self.roster, DeathRegister(), ledger=step.ledger)
        self.assertEqual(
            healed[index],
            field_mobs.hostile_actor_entry(self.legacy, self.mob))
        self.assertEqual(
            remembered[index],
            field_mobs.hostile_actor_entry(
                self.legacy, self.mob, current_hp=step.outcome.hp_after))
        self.assertNotEqual(healed[index], remembered[index])
        # everybody untouched is byte-identical either way
        for position, mob in enumerate(self.roster):
            if mob.actor_identity == self.mob.actor_identity:
                continue
            self.assertEqual(healed[position], remembered[position])

    def test_a_ledger_that_killed_without_a_kill_is_refused(self):
        # Dead in the arithmetic, alive in the register: sending a live body
        # resurrects it and sending a corpse claims a kill nobody committed,
        # so neither is composed.
        step = self.killing_outcome()
        with self.assertRaises(MobDeathContractError) as caught:
            repopulation_entries(
                self.legacy, self.roster, DeathRegister(), ledger=step.ledger)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_LEDGER_DISAGREES_WITH_REGISTER)
        # and with the kill committed it composes the corpse instead
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        entries = repopulation_entries(
            self.legacy, self.roster, death.register, ledger=step.ledger)
        index = [m.actor_identity for m in self.roster].index(
            self.mob.actor_identity)
        self.assertEqual(
            entries[index],
            mob_death.death_actor_entry(
                self.legacy, self.mob, death_timer=DEAD_TIMER_SECONDS))

    def test_a_corpse_that_is_still_standing_in_the_ledger_is_refused(self):
        # The mirror of the case above: dead in the register, alive in the
        # arithmetic.  Both directions of the same desync are named.
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        with self.assertRaises(MobDeathContractError) as caught:
            repopulation_entries(
                self.legacy, self.roster, death.register, ledger=open_ledger())
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_LEDGER_DISAGREES_WITH_REGISTER)

    def test_a_register_built_from_another_roster_is_refused(self):
        wrong = DeathRegister((
            DeathRecord(self.mob.actor_identity, PERFORMER,
                        self.mob.max_hp + 1),
        ))
        with self.assertRaises(MobDeathContractError) as caught:
            repopulation_entries(self.legacy, self.roster, wrong)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER)

    # -- the lane's own rules ---------------------------------------------

    def test_this_lane_needs_no_flag(self):
        # Read out of the SYNTAX, not out of the text: the prose in this
        # module's own docstring says the words "scenario" and "unlock" while
        # explaining that it has neither, and a text scan cannot tell the
        # difference between describing a gate and having one.
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_death.py").read_text(
                encoding="utf-8"))
        named = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                named.add(node.id.lower())
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                named.add(node.name.lower())
            elif isinstance(node, ast.arg):
                named.add(node.arg.lower())
            elif isinstance(node, ast.Attribute):
                named.add(node.attr.lower())
        for forbidden in ("scenario", "unlock", "kwarg", "flag", "profile",
                          "allowlist", "hypothesis"):
            offenders = sorted(n for n in named if forbidden in n)
            self.assertEqual(offenders, [], forbidden)

    def test_this_lane_imports_no_probe_lane(self):
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_death.py").read_text(
                encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.lstrip("."))
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
        for probe in ("runtimeres_death_hypothesis", "hostile_hp_link_hypothesis",
                      "damage_model_hypothesis", "mob_aggro", "npc_hp_link_hypothesis"):
            self.assertNotIn(probe, imported)
        self.assertIn("field_mobs", imported)
        self.assertIn("mob_combat", imported)

    def test_every_named_refusal_reason_can_actually_happen(self):
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_death.py").read_text(
                encoding="utf-8"))
        raised = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise):
                continue
            call = node.exc
            if (isinstance(call, ast.Call)
                    and getattr(call.func, "id", "") == "MobDeathContractError"
                    and call.args
                    and isinstance(call.args[0], ast.Name)):
                raised.add(getattr(mob_death, call.args[0].id))
        self.assertEqual(
            sorted(raised),
            sorted(mob_death.MOB_DEATH_REFUSAL_REASONS),
            "a refusal is declared and never raised, or raised and never "
            "declared")

    def test_nothing_is_installed_by_importing_this_module(self):
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_death.py").read_text(
                encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        for forbidden in ("socket", "sqlite3", "random", "time", "datetime",
                          "threading", "asyncio", "os", "subprocess"):
            self.assertNotIn(forbidden, imported)
        # and no module-level statement does anything but declare
        for node in tree.body:
            self.assertIsInstance(
                node,
                (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
                 ast.FunctionDef, ast.ClassDef, ast.Expr),
            )
            if isinstance(node, ast.Expr):
                self.assertIsInstance(node.value, ast.Constant)

    def test_the_module_says_what_it_does_not_claim(self):
        self.assertGreaterEqual(len(mob_death.MOB_DEATH_NONCLAIMS), 6)
        joined = " ".join(mob_death.MOB_DEATH_NONCLAIMS)
        # the three the archive forced this round to write down: the animation
        # nobody has seen, the frame whose effect nobody has seen, and the
        # hold nobody has measured
        self.assertIn("_F_DIE_000", joined)
        self.assertIn("GT-025", joined)
        self.assertIn("runtime.py", joined)
        self.assertIn("hold", joined)
        self.assertNotIn("corpse is", joined)
        # the two nonclaims the first half retired are recorded, not deleted
        retired = dict(mob_combat.MOB_COMBAT_RETIRED_NONCLAIMS)
        self.assertEqual(len(retired), 2)
        for claim, reason in retired.items():
            self.assertIn("7ptoku", reason)
            self.assertNotIn(claim, mob_combat.MOB_COMBAT_NONCLAIMS)

    def test_the_wiring_line_names_every_step_the_caller_owes(self):
        for owed in ("mob_death.kill", "commit_death", "dying_frame",
                     "dead_frame", "hold_ms", "corpse_override", "register"):
            self.assertIn(owed, mob_death.MOB_DEATH_WIRING)
        self.assertIn("mob_death", mob_combat.MOB_COMBAT_WIRING)
        # The wiring line must name the CombatStep property and warn off the
        # outcome attribute of the same name: an adversarial review of this
        # round found the first version naming outcome.death_due, which is
        # also True for a hit on a monster that is already dead.
        self.assertIn("step.death_due", mob_death.MOB_DEATH_WIRING)
        self.assertIn("NOT step.outcome.death_due", mob_death.MOB_DEATH_WIRING)

    def test_the_hold_is_declared_as_ours_and_not_as_a_measurement(self):
        self.assertEqual(mob_death.DEATH_TASK_HOLD_MS, 700)
        source = (
            ROOT / "src/pirateforce_foundation/mob_death.py"
        ).read_text(encoding="utf-8")
        self.assertIn("[LANE-B ASSUMPTION", source)
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        self.assertTrue(
            any("unmeasured" in line for line in describe_death(death)))

    def test_the_committed_pin_is_what_the_code_produces(self):
        path = ROOT / "scenarios/combat_death_001.json"
        raw = path.read_bytes()
        self.assertTrue(raw.decode("utf-8").isascii())
        committed = json.loads(raw.decode("ascii"))
        pinned_mob = [
            m for m in self.roster
            if m.placement_index == mob_death.PIN_PLACEMENT_INDEX
        ][0]
        self.assertEqual(committed, pin_document(self.legacy, pinned_mob))
        self.assertTrue(committed["production_allowed"])
        self.assertFalse(committed["test_only"])
        self.assertTrue(committed["not_a_scenario"])
        self.assertEqual(
            committed["selection"], "none_default_behaviour_no_scenario_flag")
        self.assertEqual(committed["hp_when_dead"], 0)
        self.assertEqual(committed["basic_mask_corpse"], "0x078D")
        self.assertTrue(committed["hold_ms_is_ours"])
        self.assertGreaterEqual(len(committed["nonclaims"]), 6)

    def test_the_console_lines_name_the_chain(self):
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        lines = describe_death(death)
        joined = "\n".join(lines)
        self.assertIn("0x443990", joined)
        self.assertIn("CActorTask_Dead", joined)
        self.assertIn("0x201F", joined)


if __name__ == "__main__":
    unittest.main()
