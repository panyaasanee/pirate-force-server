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
import contextlib
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
from pirateforce_foundation import world_population
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
    describe_roster_override_coverage,
    dying_frames,
    full_roster_override,
    hostile_census_frames,
    kill,
    live_roster,
    pin_document,
    production_allowed,
    repopulation_entries,
    repopulation_frames,
    roster_override_coverage,
    test_only,
)


PERFORMER = 0x750059
# Strong enough to reach zero in one hit, so a test does not have to loop the
# ladder to get to the thing it is testing.
LETHAL = Combatant(level=1000, ability_str=100000, ability_con=0)
# DELIBERATELY UNREGISTERED.  kill() fails closed on any widened= string
# that is not an exact key in mob_death.WIDENING_RULINGS (pf-adversary,
# round 67jejl: an unrecognised string used to be treated as pre-fix-legal,
# which is exactly the gap a mistranscribed real ruling string would walk
# through unnoticed) - so this constant now proves REFUSAL, not
# authorisation.  A test that needs SOME registered ruling to widen an
# arbitrary roster mob (because it is testing the compare-and-swap /
# generation machinery, not the scope gate) uses
# ``self.registered_widening(...)`` below instead.
WIDENED = "test-only: this assertion is not about the target scope"
# The exact ruling string COO-DECISION 20260827_0955 gives as the value of
# widened= for Training Iron Man (MOBS.n_ID 916).  Kept as one constant so a
# test that is ABOUT this ruling and a test that only needs SOME registered
# ruling both quote the same source rather than two hand-typed copies.
WIDENED_916_RULING = (
    "COO-DECISION widen-death-scope-916-training-iron-man "
    "2026-08-27T09:55+07:00 (ref PANYA-DECISION 2026-08-27T09:50+07:00 "
    "section 3, supersedes COO 0954)"
)
# The exact ruling string COO-DECISION 2026-08-27T13:50+07:00 gives as the
# value of widened= to authorise all 13 real bg0001 field mobs (stage two,
# see notes_to_chief/20260827_1350_COO-DECISION-widen-death-scope-bg0001-
# full-roster-approved.md). Chief is told to hardcode this exact string as
# widened= on runtime.py's mob_death.kill() call site -- pf-adversary, this
# round: the letter's own cited line number is already stale; as of this
# round that call site passes no widened= argument at all, so do not trust
# a hardcoded line number here (see the matching note on WIDENING_RULINGS
# in mob_death.py).
WIDENED_BG0001_RULING = "COO-RULING-20260827-1350 widen-death-scope-bg0001"


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

    @contextlib.contextmanager
    def registered_widening(self, ruling, template_ids):
        """Temporarily register a test-only ruling in WIDENING_RULINGS.

        kill() fails closed on any widened= string that is not an exact key
        in mob_death.WIDENING_RULINGS.  A test that is about the
        compare-and-swap / generation machinery rather than the scope gate
        itself needs SOME registered ruling to widen an arbitrary roster
        mob, so it registers one here for the duration of the ``with``
        block and the module is restored after, exactly as this file
        already does for ``mob_death._compose_body`` elsewhere.
        """
        previous = dict(mob_death.WIDENING_RULINGS)
        mob_death.WIDENING_RULINGS[ruling] = frozenset(template_ids)
        try:
            yield ruling
        finally:
            mob_death.WIDENING_RULINGS.clear()
            mob_death.WIDENING_RULINGS.update(previous)

    def training_iron_man_stand_in(self):
        """A TEST-ONLY FieldMob for Training Iron Man, MOBS.n_ID 916.

        Built from the real CONSTDATA_TH__MOBS row 916 (model M016, outfit
        M016_000_000_N, level 100/100, rank 0, n_AI_WANDER 21, n_AI_COMBAT 0,
        no drops).  See
        test_simultaneous_death_of_0x201f_and_916_training_iron_man for the
        full provenance note on why max_hp=100 and placement_index=9001 are
        both stand-ins, not captured or wire values.
        """
        return field_mobs.FieldMob(
            placement_index=9001,
            template_id=916,
            x=0.0, y=0.0, z=0.0,
            visual_preset="M016_000_000_N",
            display_name="Training Iron Man",
            level=100,
            rank=0,
            ai_wander=21,
            ai_combat=0,
            speed_walk=150,
            max_hp=100,
            drops_normal=0,
            drops_equipment=0,
            drops_specially=0,
        )

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

    def test_the_death_frame_is_a_one_entry_generation_open_risk_not_a_fix(self):
        # Same open risk as mob_combat's twin test, same citation: see the
        # docstring on mob_death.death_frames.  This does not close the
        # question, it pins the current shape - one corpse entry, not zero,
        # not the roster - so a future change to it is a deliberate, tested
        # decision instead of an accident nobody notices.
        body = corpse_npc_attr(
            self.legacy, self.mob, death_timer=DEAD_TIMER_SECONDS)
        one_entry = self.legacy.make_remote_actor_entry(
            mob_death.NPC_STYLE_ACTOR_TYPE, self.mob.actor_identity,
            [(mob_death.NPC_ATTR_ID, body)])
        pc, _ = dead_frames(self.legacy, self.mob)
        self.assertEqual(
            pc, self.legacy.make_runtime_remote_actors([one_entry])[0])

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
        # widened= because this test is about the compare-and-swap, not about
        # the owner's target scope; the scope gate has its own test below.
        # A registered ruling because kill() now fails closed on anything
        # else (pf-adversary, round 67jejl).
        with self.registered_widening(WIDENED, {other.template_id}):
            b = kill(
                self.legacy, other, second.outcome, stored, widened=WIDENED)
            stored = mob_death.commit_death(stored, a)
            with self.assertRaises(MobDeathContractError) as caught:
                mob_death.commit_death(stored, b)
            self.assertEqual(
                caught.exception.reason, mob_death.REFUSE_REGISTER_STALE)
            # the loser re-reads and re-runs, and now both deaths are
            # recorded
            redone = kill(
                self.legacy, other, second.outcome, stored, widened=WIDENED)
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

    def test_full_roster_override_covers_every_identity_untouched_or_not(self):
        # BUILD-004's still-open gap, in one assertion: corpse_override only
        # names identities that changed from the census default, so a field
        # mob nobody has hit is simply absent from it and ships nameless and
        # neutral.  full_roster_override must not have that gap -- every
        # roster identity is a key, including the twelve nobody has touched.
        override = full_roster_override(self.legacy, self.roster, DeathRegister())
        self.assertEqual(
            sorted(override), sorted(m.actor_identity for m in self.roster))
        for mob in self.roster:
            self.assertEqual(
                override[mob.actor_identity],
                field_mobs.hostile_actor_entry(self.legacy, mob))

    def test_full_roster_override_agrees_with_corpse_override_where_it_applies(
            self):
        # A caller with an existing corpse_override call site can rename the
        # call and change nothing else: for every identity corpse_override
        # DOES name, the two functions must return byte-identical entries.
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        narrow = mob_death.corpse_override(
            self.legacy, self.roster, death.register)
        wide = full_roster_override(self.legacy, self.roster, death.register)
        self.assertEqual(set(wide), set(m.actor_identity for m in self.roster))
        for identity, entry in narrow.items():
            self.assertEqual(wide[identity], entry)
        # and the identities corpse_override left out are exactly the ones
        # nobody has touched, now present at their full-HP hostile body
        untouched = [
            m for m in self.roster if m.actor_identity not in narrow]
        self.assertTrue(untouched)
        for mob in untouched:
            self.assertEqual(
                wide[mob.actor_identity],
                field_mobs.hostile_actor_entry(self.legacy, mob))

    def test_full_roster_override_reflects_ledger_damage(self):
        # The wounded-but-alive case: full_roster_override must read the
        # same ledger balance corpse_override already reads, not silently
        # fall back to max_hp for a damaged survivor.
        weak = Combatant(level=7, ability_str=132, ability_con=0)
        other = [m for m in self.roster if m.placement_index != 30][0]
        hurt = strike(
            self.legacy, None, open_ledger(), None, other, PERFORMER, weak)
        override = full_roster_override(
            self.legacy, self.roster, DeathRegister(), ledger=hurt.ledger)
        balance = mob_death._balance_in(hurt.ledger, other.actor_identity)
        self.assertLess(balance, other.max_hp)
        self.assertEqual(
            override[other.actor_identity],
            field_mobs.hostile_actor_entry(
                self.legacy, other, current_hp=balance))
        # nobody else was touched, so they still carry their ceiling HP
        untouched = [m for m in self.roster if m is not other]
        for mob in untouched:
            self.assertEqual(
                override[mob.actor_identity],
                field_mobs.hostile_actor_entry(self.legacy, mob))

    # -- GT-084 console-coverage helper ------------------------------------

    def test_roster_override_coverage_reports_matched_and_missing(self):
        override = {0x201F: b"a", 0x2001: b"b", 0x2099: b"c"}
        coverage = roster_override_coverage(override, [0x201F, 0x2001, 0x9999])
        self.assertEqual(coverage["matched"], (0x2001, 0x201F))
        self.assertEqual(coverage["missing"], (0x2099,))
        self.assertEqual(coverage["matched_count"], 2)
        self.assertEqual(coverage["total"], 3)

    def test_roster_override_coverage_all_matched_reports_no_missing(self):
        override = {0x201F: b"a", 0x2001: b"b"}
        coverage = roster_override_coverage(override, [0x201F, 0x2001, 0x30])
        self.assertEqual(coverage["missing"], ())
        self.assertEqual(coverage["matched_count"], coverage["total"])

    def test_roster_override_coverage_refuses_non_dict_override(self):
        with self.assertRaises(MobDeathContractError) as caught:
            roster_override_coverage([(0x201F, b"a")], [0x201F])
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_TYPE_NOT_TYPED_RECORD)

    def test_roster_override_coverage_refuses_a_non_int_key(self):
        with self.assertRaises(MobDeathContractError) as caught:
            roster_override_coverage({"0x201F": b"a"}, [0x201F])
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_OVERRIDE_ENTRY_NOT_INT_BYTES)

    def test_roster_override_coverage_refuses_a_bool_key(self):
        # bool is a subclass of int; True/False must not pass as identities.
        with self.assertRaises(MobDeathContractError) as caught:
            roster_override_coverage({True: b"a"}, [1])
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_OVERRIDE_ENTRY_NOT_INT_BYTES)

    def test_roster_override_coverage_refuses_a_non_bytes_value(self):
        with self.assertRaises(MobDeathContractError) as caught:
            roster_override_coverage({0x201F: "a"}, [0x201F])
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_OVERRIDE_ENTRY_NOT_INT_BYTES)

    def test_describe_roster_override_coverage_is_ascii_console_lines(self):
        lines = describe_roster_override_coverage(
            {0x201F: b"a", 0x2099: b"c"}, [0x201F])
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line.encode("ascii").decode("ascii"), line)
        self.assertIn("matched=1/2", line)
        self.assertIn("missing=0x2099", line)

    def test_describe_roster_override_coverage_all_matched_says_none(self):
        lines = describe_roster_override_coverage({0x201F: b"a"}, [0x201F])
        self.assertIn("missing=none", lines[0])

    def test_full_roster_override_lands_on_every_identity_in_the_real_115_census(
            self):
        # GT-084 (2026-08-27, attended) could not tell from the console
        # whether full_roster_override's splice reached the wire at all.
        # This proves it at the wire/DB layer, independent of the console
        # question: build the SAME 115-actor census
        # tests/test_world_census_wiring.py proves the real dispatcher sends
        # on a flagless default boot (same anchor, same scene_id), apply
        # full_roster_override exactly as runtime.py's call site does, and
        # measure coverage against the result -- not against an assumption
        # about what the census SHOULD contain.
        generation = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0), scene_id=1,
        )
        self.assertEqual(generation.actor_count, 115)
        override = full_roster_override(
            self.legacy, self.roster, DeathRegister())
        coverage = roster_override_coverage(
            override, generation.actor_identities)
        self.assertEqual(coverage["missing"], ())
        self.assertEqual(coverage["matched_count"], len(self.roster))

    # -- hostile_census_frames: the world-wipe fix (round `sifsfg`) --------
    #
    # chief's escalation (pf_bridge/notes_to_chief/20260827_0920_CHIEF-
    # URGENT-combat-death-frames-confirmed-world-wipe-unconditional-on-
    # flagless-path.md) reports RE-092 confirmed mob_combat.bar_frames and
    # this module's own death_frames each send a ONE-entry collection that
    # replaces (not merges) the client's whole remote-actor registry.  These
    # tests prove the fix composes a REAL full census correctly -- not a
    # smaller stand-in -- and prove it by wire-layer equivalence to the
    # existing one-entry functions, not by assumption.
    #
    # pf-adversary (round sifsfg) found, by actually running it, that omitting
    # ledger= here silently re-sends every living-but-damaged monster at its
    # ceiling HP -- hostile_census_frames now refuses ledger=None by name
    # (REFUSE_CENSUS_FRAME_WITHOUT_A_LEDGER), and every test below that wants
    # a successful call threads a real ledger through, the same way a real
    # hit/death call site would.

    REAL_CENSUS_ANCHOR = (10.0, 20.0, 30.0)

    def _real_generation_offsets(self, generation):
        """identity -> (start, length) inside generation.pc, header-relative."""
        offsets = {}
        offset = world_population.WIRE_HEADER_BYTES
        for identity, length in zip(
                generation.actor_identities, generation.entry_bytes):
            offsets[identity] = (offset, length)
            offset += length
        return offsets

    def test_hostile_census_frames_matches_independent_recomposition(self):
        # This recomposes the same inputs through the SAME public functions a
        # caller outside this module would use (build_world_population +
        # full_roster_override + apply_identity_override), and only then
        # compares.  pf-adversary (round sifsfg) mutated apply_identity_override
        # itself (made it ignore the override dict) and reran this suite: this
        # specific test still PASSED, because "expected" is recomposed through
        # the SAME apply_identity_override the code under test also calls, so
        # a bug there cancels on both sides.  So the claim this test actually
        # supports is narrower than "not tautological with the
        # implementation": it proves hostile_census_frames wires the right
        # arguments to the right sub-calls (build_world_population,
        # full_roster_override, apply_identity_override), NOT that
        # apply_identity_override itself is correct -- the per-identity check
        # below closes that second gap by comparing against
        # full_roster_override's raw dict directly, without going through
        # apply_identity_override on either side.
        register = DeathRegister()
        ledger = open_ledger()
        override = full_roster_override(
            self.legacy, self.roster, register, ledger=ledger)
        expected_generation = world_population.apply_identity_override(
            self.legacy,
            world_population.build_world_population(
                self.legacy, self.REAL_CENSUS_ANCHOR, 115, scene_id=1),
            override,
        )
        pc, frame = hostile_census_frames(
            self.legacy, self.REAL_CENSUS_ANCHOR, 115, self.roster, register,
            ledger=ledger)
        self.assertEqual(pc, expected_generation.pc)
        self.assertEqual(frame, expected_generation.frame)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        # Independent of apply_identity_override: walk the composed pc's
        # entries using ONLY the plain generation's own identity/length list
        # (never touched by apply_identity_override) and full_roster_override's
        # raw dict -- an overridden identity's byte length usually differs
        # from the plain default's (hostile bodies carry five more faction
        # bytes), so this recomputes each entry's true length from the raw
        # dict itself rather than trusting apply_identity_override's returned
        # entry_bytes.  This is exactly the check that would have caught the
        # mutation the adversary tried: if apply_identity_override ignored
        # the override dict, ``pc`` at these offsets would still hold the
        # plain body, not ``override[identity]``, and this loop would fail
        # even though the recomposition-equality assertions above would not.
        plain_generation = world_population.build_world_population(
            self.legacy, self.REAL_CENSUS_ANCHOR, 115, scene_id=1)
        offset = world_population.WIRE_HEADER_BYTES
        for identity, plain_length in zip(
                plain_generation.actor_identities,
                plain_generation.entry_bytes):
            entry = override.get(identity)
            length = plain_length if entry is None else len(entry)
            if entry is not None:
                self.assertEqual(pc[offset:offset + length], entry)
            offset += length
        self.assertEqual(offset, len(pc))

    def test_hostile_census_frames_carries_all_115_actors_not_fewer(self):
        pc, frame = hostile_census_frames(
            self.legacy, self.REAL_CENSUS_ANCHOR, 115, self.roster,
            DeathRegister(), ledger=open_ledger())
        count = int.from_bytes(
            pc[world_population.WIRE_COUNT_TAG_OFFSET + 1:
               world_population.WIRE_COUNT_TAG_OFFSET + 3],
            "little",
        )
        self.assertEqual(count, 115)

    def test_hostile_census_frames_gives_an_untouched_roster_member_the_hostile_body_not_the_plain_default(
            self):
        # This is the reason full_roster_override, not corpse_override, is
        # the right input here: a monster nobody has hit yet must still show
        # its hostile body, not build_world_population's plain HP-100 default.
        plain_generation = world_population.build_world_population(
            self.legacy, self.REAL_CENSUS_ANCHOR, 115, scene_id=1)
        pc, _ = hostile_census_frames(
            self.legacy, self.REAL_CENSUS_ANCHOR, 115, self.roster,
            DeathRegister(), ledger=open_ledger())
        offsets = self._real_generation_offsets(plain_generation)
        untouched = next(
            m for m in self.roster if m.actor_identity != self.mob.actor_identity)
        start, length = offsets[untouched.actor_identity]
        plain_entry = plain_generation.pc[start:start + length]
        composed_entry = pc[start:start + length]
        self.assertNotEqual(plain_entry, composed_entry)

    def test_hostile_census_frames_embeds_the_exact_dead_body_death_frames_sends_alone(
            self):
        # RE-DERIVED equivalence: the body byte-for-byte inside the full
        # census must be the SAME bytes death_frames would have sent alone --
        # this is "reuse the encoder over a wider input", not a second one.
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        register = death.register
        # death.dead_pc IS mob_death.death_frames' one-entry output for this
        # corpse (dead_frames -> death_frames; see mob_death.kill).
        solo_entry = death.dead_pc[world_population.WIRE_HEADER_BYTES:]
        composed_pc, composed_frame = hostile_census_frames(
            self.legacy, self.REAL_CENSUS_ANCHOR, 115, self.roster, register,
            ledger=step.ledger)
        self.assertEqual(composed_frame, self.legacy.frame_pc(composed_pc))
        base_generation = world_population.build_world_population(
            self.legacy, self.REAL_CENSUS_ANCHOR, 115, scene_id=1)
        offsets = self._real_generation_offsets(base_generation)
        start, _length = offsets[self.mob.actor_identity]
        composed_entry = composed_pc[start:start + len(solo_entry)]
        self.assertEqual(composed_entry, solo_entry)

    def test_hostile_census_frames_refuses_the_same_way_full_roster_override_does(
            self):
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        living = live_roster(self.roster, death.register)
        with self.assertRaises(MobDeathContractError) as caught:
            hostile_census_frames(
                self.legacy, self.REAL_CENSUS_ANCHOR, 115, living,
                death.register, ledger=step.ledger)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER)

    def test_hostile_census_frames_refuses_a_missing_ledger_by_name(self):
        # pf-adversary (round sifsfg), verified by actual execution: damaged
        # a mob to 3828/3857 HP via a real strike()+ledger, then called
        # hostile_census_frames with ledger omitted (the function's own
        # default) -- the composed frame carried the mob's FULL-HP body, not
        # its true damaged HP.  Since this function exists to be composed on
        # EVERY hit/death frame, and a hit/death frame cannot exist without
        # strike() already requiring a typed ledger, omitting it here is
        # never a legitimate call -- it now refuses instead of silently
        # healing every damaged-but-alive monster on the wire.
        with self.assertRaises(MobDeathContractError) as caught:
            hostile_census_frames(
                self.legacy, self.REAL_CENSUS_ANCHOR, 115, self.roster,
                DeathRegister())
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_CENSUS_FRAME_WITHOUT_A_LEDGER)

    def test_hostile_census_frames_carries_the_true_damaged_hp_not_the_ceiling(
            self):
        # The exact regression pf-adversary reproduced by execution, pinned
        # so it cannot come back silently: strike self.mob for LESS than a
        # kill, thread the resulting ledger through, and require the
        # composed census to carry the TRUE current HP for that identity --
        # not build_world_population's plain default, and not the ceiling
        # full_roster_override(ledger=None) would have sent.
        weak = Combatant(level=7, ability_str=132, ability_con=0)
        step = strike(
            self.legacy, None, open_ledger(), None, self.mob, PERFORMER, weak)
        damaged_hp = step.outcome.hp_after
        self.assertLess(damaged_hp, self.mob.max_hp)
        self.assertGreater(damaged_hp, 0)
        pc, frame = hostile_census_frames(
            self.legacy, self.REAL_CENSUS_ANCHOR, 115, self.roster,
            DeathRegister(), ledger=step.ledger)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        expected_damaged_entry = field_mobs.hostile_actor_entry(
            self.legacy, self.mob, current_hp=damaged_hp)
        ceiling_entry = field_mobs.hostile_actor_entry(
            self.legacy, self.mob, current_hp=self.mob.max_hp)
        plain_generation = world_population.build_world_population(
            self.legacy, self.REAL_CENSUS_ANCHOR, 115, scene_id=1)
        offsets = self._real_generation_offsets(plain_generation)
        start, _length = offsets[self.mob.actor_identity]
        composed_entry = pc[start:start + len(expected_damaged_entry)]
        self.assertEqual(composed_entry, expected_damaged_entry)
        self.assertNotEqual(composed_entry, ceiling_entry)

    def test_full_roster_override_refuses_the_same_way_repopulation_does(self):
        # It is a thin wrapper over repopulation_entries and must not swallow
        # or soften that function's own refusals.
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        living = live_roster(self.roster, death.register)
        with self.assertRaises(MobDeathContractError) as caught:
            full_roster_override(self.legacy, living, death.register)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER)

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

    def test_a_target_outside_the_owners_scope_is_refused(self):
        # The constant used to appear only in prose, a pin and a console line.
        # Reporting is not a gate: the owner's ruling sequences the work
        # (0x201F first, then real table mobs, not both in one round), so the
        # module holds that scope where a wiring line cannot walk past it.
        other = [m for m in self.roster if m.placement_index != 30][0]
        outcome = self.killing_outcome(other).outcome
        with self.assertRaises(MobDeathContractError) as caught:
            kill(self.legacy, other, outcome, DeathRegister())
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)
        self.assertIn(mob_death.SANCTIONING_RULING, caught.exception.detail)
        # the sanctioned target needs nothing passed at all
        sanctioned = self.killing_outcome()
        self.assertEqual(
            self.mob.actor_identity, mob_death.SANCTIONED_FIRST_TARGET_IDENTITY)
        kill(self.legacy, self.mob, sanctioned.outcome, DeathRegister())
        # and a caller holding a REGISTERED later ruling that names this
        # mob's template gets a kill
        with self.registered_widening(WIDENED, {other.template_id}):
            step = kill(self.legacy, other, outcome, DeathRegister(),
                        widened=WIDENED)
        self.assertTrue(step.register.is_dead(other.actor_identity))
        # pf-adversary (round 67jejl): an UNREGISTERED string used to be
        # treated as pre-fix-legal here too - "just needs to be non-empty" -
        # which is exactly what a paraphrase or a mistranscription of a real
        # ruling would produce.  kill() now fails closed on it, the same as
        # on an empty one, so WIDENED (never registered in this test) must
        # now be refused rather than accepted.
        for unauthorised in ("", "   ", None, 7, WIDENED, "close but not it"):
            with self.assertRaises(MobDeathContractError) as caught:
                kill(self.legacy, other, outcome, DeathRegister(),
                     widened=unauthorised)
            self.assertEqual(
                caught.exception.reason,
                mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)

    def test_a_register_identity_with_no_roster_row_is_refused(self):
        # live_roster() is exported from this same module and is exactly what
        # a caller reaches for when the sentence is "build the census from the
        # living" - and doing that used to return an EMPTY override, standing
        # every corpse back up with no refusal anywhere.
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        living = live_roster(self.roster, death.register)
        with self.assertRaises(MobDeathContractError) as caught:
            repopulation_entries(self.legacy, living, death.register)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER)
        self.assertIn("0x201F", caught.exception.detail)
        with self.assertRaises(MobDeathContractError):
            mob_death.corpse_override(self.legacy, living, death.register)

    def test_a_commit_cannot_drop_rows_from_a_same_length_lineage(self):
        # generation == len(records) for every register built through this
        # API, so two registers holding the same NUMBER of dead monsters carry
        # the same generation while holding different monsters.  The counter
        # says "nothing happened since"; it cannot say "nothing was lost".
        other = [m for m in self.roster if m.placement_index != 30][0]
        third = [m for m in self.roster if m.placement_index not in
                 (30, other.placement_index)][0]
        # A registered ruling because kill() now fails closed on anything
        # else (pf-adversary, round 67jejl); this test is about the
        # commit-death lineage, not the scope gate.
        with self.registered_widening(
                WIDENED, {other.template_id, third.template_id}):
            lineage_a = mob_death.commit_death(
                DeathRegister(),
                kill(self.legacy, other, self.killing_outcome(other).outcome,
                     DeathRegister(), widened=WIDENED))
            lineage_b = mob_death.commit_death(
                DeathRegister(),
                kill(self.legacy, third, self.killing_outcome(third).outcome,
                     DeathRegister(), widened=WIDENED))
        self.assertEqual(lineage_a.generation, lineage_b.generation)
        self.assertNotEqual(lineage_a.identities(), lineage_b.identities())
        stranger = kill(
            self.legacy, self.mob, self.killing_outcome().outcome, lineage_b)
        with self.assertRaises(MobDeathContractError) as caught:
            mob_death.commit_death(lineage_a, stranger)
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_REGISTER_STALE)
        self.assertIn("drop", caught.exception.detail)

    def test_the_read_back_catches_a_timer_in_the_wrong_place(self):
        # The runtime guard, not the test's byte comparison.  A composer that
        # appends the f32 after the faction field passes both the equality and
        # the length check; only reading the field back out of the composed
        # bytes catches it.
        real = mob_death._compose_body

        def misplaced(legacy, mob, *, death_timer, **kwargs):
            body = real(legacy, mob, death_timer=None, **kwargs)
            if death_timer is None:
                return body
            tail = (
                bytes(legacy.u8tag(0x0B, 0x01 | 0x04))
                + bytes(legacy.u16tag(0x12, mob.template_id))
                + bytes(legacy.wstr_tag(mob.visual_preset))
            )
            at = len(body) - len(tail)
            mask_at = 11 + 1
            mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
            return (
                body[:mask_at]
                + int(mask | mob_death.BASIC_BIT_DEATH_TIMER).to_bytes(
                    2, "little")
                + body[mask_at + 2:at]
                + bytes(legacy.f32tag(death_timer))
                + body[at:]
            )

        mob_death._compose_body = misplaced
        try:
            with self.assertRaises(MobDeathContractError) as caught:
                corpse_npc_attr(
                    self.legacy, self.mob, death_timer=DEAD_TIMER_SECONDS)
        finally:
            mob_death._compose_body = real
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_COMPOSED_BYTES_OFF_PIN)

    def test_a_hand_built_step_gets_the_same_polarity_gate(self):
        step = self.killing_outcome()
        death = kill(self.legacy, self.mob, step.outcome, DeathRegister())
        for dying, dead in ((0.0, 0.0), (-1.0, 0.0), (20.0, 1.0)):
            with self.assertRaises(MobDeathContractError) as caught:
                DeathStep(
                    death.record, death.dying_pc, death.dying_frame,
                    death.dead_pc, death.dead_frame, death.register,
                    death.hold_ms, 0, dying, dead)
            self.assertEqual(
                caught.exception.reason,
                mob_death.REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE)
        with self.assertRaises(MobDeathContractError):
            DeathStep(
                death.record, death.dying_pc, death.dying_frame,
                death.dead_pc, death.dead_frame, death.register,
                death.hold_ms, -1, DYING_TIMER_SECONDS, DEAD_TIMER_SECONDS)

    def test_the_timers_on_the_step_are_the_timers_in_the_frames(self):
        # The step reads its timers off a field instead of a constant, which
        # is only an improvement if the field agrees with the bytes.  Decoded
        # out of the composed body, at the offset the module computes.
        import struct as _struct
        step = self.killing_outcome()
        for dying, dead in ((DYING_TIMER_SECONDS, DEAD_TIMER_SECONDS),
                            (3.5, -1.0)):
            death = kill(
                self.legacy, self.mob, step.outcome, DeathRegister(),
                dying_timer=dying, dead_timer=dead)
            for timer, frame in ((death.dying_timer, death.dying_frame),
                                 (death.dead_timer, death.dead_frame)):
                body = corpse_npc_attr(
                    self.legacy, self.mob, death_timer=timer)
                timerless = mob_death._compose_body(
                    self.legacy, self.mob, current_hp=0, death_timer=None,
                    faction=field_mobs.FIELD_MOB_FACTION,
                    scene_id=1, scene_sequence=0, with_name=True)
                cut = mob_death._timer_offset(
                    self.legacy, self.mob, timerless, 0, True)
                self.assertEqual(
                    _struct.unpack("<f", body[cut + 1:cut + 5])[0], timer)
                self.assertIn(body, frame)

    def test_the_wiring_line_still_says_pass_the_ledger(self):
        # A repair in this round rewrote the wiring line and dropped ledger=,
        # which put back the silent healing the same round had just closed.
        self.assertIn("ledger=ledger", mob_death.MOB_DEATH_WIRING)
        self.assertIn("PASS THE LEDGER", mob_death.MOB_DEATH_WIRING)
        committed = json.loads(
            (ROOT / "scenarios/combat_death_001.json").read_bytes()
            .decode("ascii"))
        self.assertIn("ledger=ledger", committed["wiring"])

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
        # [NOTE, round B_20260827_1637, 2026-08-27, comment only - no new
        # assertion, per this round's charter] MOB_DEATH_NONCLAIMS gained an
        # appended [STALE]/[MEASURED] update on the "named and hostile"
        # entries this round: GT-084-R2 (attended, OBSERVER_CONFIRMED
        # 2026-08-27T15:52-15:55+07:00) observed that body for the first
        # time at zero HP and it froze instead of falling like GT-022/GT-025.
        # Not asserted here on purpose - the update is prose, not a new
        # invariant, and this test already covers that the tuple keeps
        # growing (assertGreaterEqual above) without shrinking below what it
        # already promised.
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
        self.assertIn("[COO-CONFIRMED PROVISIONAL", source)
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

    def test_simultaneous_death_of_0x201f_and_916_training_iron_man(self):
        # notes_to_chief/20260827_0955_COO-DECISION-widen-death-scope-...:
        # the owner named ONE additional identity to widen kill() past
        # 0x201F -- Training Iron Man, MOBS.n_ID 916 (CONSTDATA_TH__MOBS row:
        # s_ID_MODEL_CLASS M016, outfit M016_000_000_N, level 100/100, rank
        # 0, n_AI_WANDER 21, n_AI_COMBAT 0 -- a dummy that never fights back
        # and drops nothing) -- and asked this lane for exactly one thing
        # before chief writes the widened= line at runtime.py:3925: a test
        # that kills the sanctioned target and this new one IN THE SAME
        # TICK, so widening the scope does not also open a dead_timer
        # collision or a register race between the two identities.  Short,
        # not a block: see COO-DECISION 0955, "not a long block, just a
        # mistake-preventing test".
        #
        # [ASSUMPTION OF LANE B -- FLAG FOR COO/chief CONFIRMATION, two
        # parts]
        # (1) CONSTDATA_TH__MOBS carries no HP column for ANY row.  This
        #     fixture's max_hp=100 leans on RE-071's own result (a named
        #     actor with a RESIDENT 100/100 HP pair renders correctly
        #     regardless of the "true" number, because BasicAttr::CopyTo
        #     copies without reading the mask) rather than a captured wire
        #     value -- nobody has captured Training Iron Man's real max HP.
        # (2) FieldMob.actor_identity is DERIVED as 0x2000 + placement_index
        #     + 1 -- the field-mob WIRE-identity space this lane's 13-mob
        #     roster lives in -- and MOBS n_ID 916 is a TEMPLATE id, a
        #     different number space entirely.  This fixture's
        #     actor_identity is a TEST-ONLY stand-in placement (index 9001,
        #     chosen outside the loaded roster so it cannot collide with a
        #     real placement), NOT the real wire identity chief will assign
        #     Training Iron Man's city placement -- that assignment is
        #     chief's call at runtime.py:3925 and outside this lane's write
        #     zone.  What this test actually proves does not depend on the
        #     real number: kill() / commit_death() / DeathRegister do not
        #     collide when the widened target's template_id is 916 and it
        #     dies in the same tick as the sanctioned target.
        training_iron_man = self.training_iron_man_stand_in()
        self.assertNotIn(
            training_iron_man.actor_identity,
            [m.actor_identity for m in self.roster])
        widened_ruling = WIDENED_916_RULING
        sanctioned_outcome = self.killing_outcome().outcome
        tim_ledger = open_ledger(roster=(training_iron_man,))
        tim_step = strike(
            self.legacy, None, tim_ledger, None, training_iron_man,
            PERFORMER, LETHAL)
        widened_outcome = tim_step.outcome
        self.assertTrue(widened_outcome.death_due)
        self.assertEqual(widened_outcome.hp_after, HP_WHEN_DEAD)

        # "the same tick": both kills computed from the SAME generation-0
        # register, exactly the shape test_two_kills_in_one_tick pins.
        stored = DeathRegister()
        a = kill(self.legacy, self.mob, sanctioned_outcome, stored)
        b = kill(
            self.legacy, training_iron_man, widened_outcome, stored,
            widened=widened_ruling)
        stored = mob_death.commit_death(stored, a)
        with self.assertRaises(MobDeathContractError) as caught:
            mob_death.commit_death(stored, b)
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_REGISTER_STALE)

        # the loser re-reads and re-runs -- same outcome, current register --
        # and both deaths land with nothing lost and nothing shared.
        redone = kill(
            self.legacy, training_iron_man, widened_outcome, stored,
            widened=widened_ruling)
        stored = mob_death.commit_death(stored, redone)
        self.assertEqual(
            stored.identities(),
            tuple(sorted((
                self.mob.actor_identity, training_iron_man.actor_identity))))
        self.assertEqual(stored.generation, 2)

        # NO DEAD_TIMER COLLISION: each step's frames are keyed to its own
        # identity, so the sanctioned kill's bytes must not double as the
        # widened kill's bytes, and both must still carry the right side of
        # the timer gate.
        self.assertNotEqual(a.dead_frame, redone.dead_frame)
        self.assertNotEqual(a.dying_frame, redone.dying_frame)
        for step in (a, redone):
            self.assertEqual(step.dying_timer, DYING_TIMER_SECONDS)
            self.assertEqual(step.dead_timer, DEAD_TIMER_SECONDS)
            self.assertEqual(step.hold_ms, mob_death.DEATH_TASK_HOLD_MS)
        self.assertTrue(stored.is_dead(self.mob.actor_identity))
        self.assertTrue(stored.is_dead(training_iron_man.actor_identity))
        self.assertEqual(
            stored.record_of(training_iron_man.actor_identity).max_hp, 100)

    def test_the_916_ruling_does_not_widen_the_other_roster_identities(self):
        # pf-adversary (round 67jejl), reviewing the test above, found a real
        # hole this project's own scar tissue warns about: kill()'s scope
        # gate only checked that ``widened`` was a non-empty string, not
        # WHICH mob it was being used for.  runtime.py:3925 reaches
        # mob_death.kill() from ONE call site for every roster identity that
        # dies -- so the literal one-line wiring COO-DECISION 0955's own
        # text asks chief to write (hardcode that ruling's widened= string)
        # would, without WIDENING_RULINGS, have authorised a kill on any of
        # the OTHER twelve roster mobs too -- including Tornado Eagle
        # (self.mob, this fixture's own SANCTIONED_FIRST_TARGET_IDENTITY
        # 0x201F is fine on its own, needs no widened= at all) and its
        # neighbours, which the SAME ruling calls still-misplaced Prison
        # Exile data.  This is the guard mob_death.WIDENING_RULINGS closes:
        # the real, correctly-quoted 916 ruling string must still be refused
        # for a mob whose template_id is not 916.
        other = [
            m for m in self.roster
            if m.actor_identity != mob_death.SANCTIONED_FIRST_TARGET_IDENTITY
        ][0]
        self.assertNotEqual(other.template_id, 916)
        outcome = self.killing_outcome(other).outcome
        with self.assertRaises(MobDeathContractError) as caught:
            kill(self.legacy, other, outcome, DeathRegister(),
                 widened=WIDENED_916_RULING)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)
        self.assertIn("916", caught.exception.detail)
        self.assertIn(str(other.template_id), caught.exception.detail)
        # A SECOND adversarial pass (same round) broke the first version of
        # this guard by execution: a PARAPHRASE of the real 916 string -
        # not a reuse of it, a drift from transcribing it out of a
        # notes_to_chief letter by hand - walked straight through, because
        # an unrecognised widened= string was treated as pre-fix-legal
        # ("just needs to be non-empty").  kill() now fails closed on the
        # ruling name itself: neither a generic ad hoc string (WIDENED) nor
        # a near-miss of the real one authorises anything, unregistered.
        for unrecognised in (WIDENED, "COO-DECISION widen-death-scope-916"):
            with self.assertRaises(MobDeathContractError) as caught:
                kill(self.legacy, other, outcome, DeathRegister(),
                     widened=unrecognised)
            self.assertEqual(
                caught.exception.reason,
                mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)
        # a widened= string IS still usable for a mob it was never about,
        # but only once a caller REGISTERS it for that mob's template -
        # the compare-and-swap tests above do exactly this.
        with self.registered_widening(WIDENED, {other.template_id}):
            step = kill(self.legacy, other, outcome, DeathRegister(),
                        widened=WIDENED)
        self.assertTrue(step.register.is_dead(other.actor_identity))
        # and the real ruling still authorises the identity it actually
        # names.
        tim_ledger = open_ledger(roster=(self.training_iron_man_stand_in(),))
        tim = self.training_iron_man_stand_in()
        tim_step = strike(
            self.legacy, None, tim_ledger, None, tim, PERFORMER, LETHAL)
        widened_step = kill(
            self.legacy, tim, tim_step.outcome, DeathRegister(),
            widened=WIDENED_916_RULING)
        self.assertTrue(widened_step.register.is_dead(tim.actor_identity))

    def test_the_bg0001_ruling_authorises_every_real_roster_mob(self):
        # COO-DECISION 2026-08-27T13:50+07:00 (stage two): every one of the
        # 13 real bg0001 field mobs, not just SANCTIONED_FIRST_TARGET_
        # IDENTITY, can now die with widened=WIDENED_BG0001_RULING. This
        # loops the REAL roster (field_mobs.load_roster()), not a hand-typed
        # subset, so a future roster edit that adds/removes a mob is
        # exercised by this test automatically rather than silently going
        # unwidened or over-widened.
        self.assertEqual(len(self.roster), 13)
        for mob in self.roster:
            outcome = self.killing_outcome(mob).outcome
            step = kill(
                self.legacy, mob, outcome, DeathRegister(),
                widened=WIDENED_BG0001_RULING)
            self.assertTrue(step.register.is_dead(mob.actor_identity))

    def test_the_bg0001_ruling_covers_exactly_the_real_rosters_templates(self):
        # pf-adversary (round 67jejl) shape, re-applied to the new ruling:
        # the covered_templates set this module pins for
        # WIDENED_BG0001_RULING must be RE-DERIVABLE from the real roster,
        # not a hand-copied literal that can drift silently out of sync with
        # field_mobs.load_roster() the moment the roster changes.
        self.assertEqual(
            mob_death.WIDENING_RULINGS[WIDENED_BG0001_RULING],
            frozenset(m.template_id for m in self.roster))

    def test_the_bg0001_ruling_still_refuses_a_template_outside_the_roster(
            self):
        # The same over-widening hole pf-adversary proved for the 916 ruling
        # applies here: WIDENED_BG0001_RULING must authorise ONLY the 13 real
        # bg0001 templates, not "any" mob a caller happens to pass it for.
        # Training Iron Man (MOBS.n_ID 916) is not one of bg0001's field-mob
        # templates, so it is the same off-roster stand-in the 916 tests
        # above already use, reused here for the opposite direction.
        tim = self.training_iron_man_stand_in()
        self.assertNotIn(
            tim.template_id,
            mob_death.WIDENING_RULINGS[WIDENED_BG0001_RULING])
        tim_ledger = open_ledger(roster=(tim,))
        tim_step = strike(
            self.legacy, None, tim_ledger, None, tim, PERFORMER, LETHAL)
        with self.assertRaises(MobDeathContractError) as caught:
            kill(self.legacy, tim, tim_step.outcome, DeathRegister(),
                 widened=WIDENED_BG0001_RULING)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)


if __name__ == "__main__":
    unittest.main()
