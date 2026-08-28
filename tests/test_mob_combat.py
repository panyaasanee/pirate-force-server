"""LANE-B / MOB-COMBAT-001: the damage driver.

The load-bearing tests in this file are these four.

``test_the_formula_constants_are_the_proven_ones`` is the one that matters
most.  This module re-declares the damage formula instead of importing the
scenario-gated lanes that proved it, because a flagless build cannot reach a
probe lane - so the only thing keeping the copy honest is that it is compared,
value by value, against those lanes' own constants.  If someone edits a
constant here, the number a player sees stops being the number three proving
rounds measured, and this test is what says so.

``test_threat_rises_by_the_damage`` guards a silent failure that no exception
would ever announce: ``mob_aggro.apply_damage_threat`` adds threat only for a
NEGATIVE damage value and returns the state unchanged for a positive one.  A
driver that hands it the positive arithmetic value builds a monster that is
hit, bleeds, repaints its bar and never decides it has an enemy.  The first
draft of this module did exactly that.

``test_the_bar_frame_is_the_hostile_body_with_a_lower_hp`` pins the refresh
frame to the field_mobs hostile body at a lower HP, and pins that it carries no
movement attribute - which is how GT-035's own refresh steps were composed.  It
does NOT claim the frame is the one GT-035 watched: that lane's body carries no
faction field, and this one does.  The difference is five bytes and it is
written down in the module, in MOB_COMBAT_NONCLAIMS, and here.

``test_the_floor_holds_and_says_so`` pins the seam the death half attaches to.
"""

import ast
import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    damage_model_hypothesis,
    field_mobs,
    hostile_hp_link_hypothesis,
    mob_aggro,
    mob_combat,
)
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import NPC_ATTR_ID
from pirateforce_foundation.mob_combat import (
    ATTACK_CADENCE_MS_PROVISIONAL,
    CHIT_RESULT_HEADER_WIRE_SIZE,
    CHIT_RESULT_VITAL_ID,
    AttackCadenceLedger,
    CadenceRecord,
    Combatant,
    CombatLedger,
    FLAGS_HIT,
    FLAGS_MISS,
    HIT_ELEMENT_WIRE_SIZE,
    HP_FLOOR,
    MobBalance,
    MobCombatContractError,
    announce_frames,
    apply_hit,
    apply_threat,
    attack_from_observed_action,
    bar_frames,
    check_attack_cadence,
    describe_cadence_rejection,
    describe_step,
    encode_hit_entry,
    mob_defender,
    open_cadence_ledger,
    open_ledger,
    pin_document,
    production_allowed,
    resolve_damage,
    strike,
    test_only,
)


PERFORMER = 0x750059


class MobCombatTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = field_mobs.load_roster()
        cls.mob = [m for m in cls.roster if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX][0]
        cls.attacker = Combatant(level=27, ability_str=132, ability_con=10)

    # -- the arithmetic ---------------------------------------------------

    def test_the_formula_constants_are_the_proven_ones(self):
        for name in ("ATK_BASE", "K_ATK_STR", "K_ATK_LV", "DEF_BASE",
                     "K_DEF_CON", "K_DEF_LV", "MIN_HIT"):
            here = getattr(mob_combat, name)
            self.assertEqual(
                here, getattr(damage_model_hypothesis, name),
                "%s drifted from HYP-PF-024" % name)
            self.assertEqual(
                here, getattr(hostile_hp_link_hypothesis, name),
                "%s drifted from HYP-PF-038" % name)

    def test_the_wire_anchors_are_the_proven_ones(self):
        pairs = (
            ("CHIT_RESULT_VITAL_ID", "CHIT_RESULT_VITAL_ID"),
            ("CHIT_RESULT_VITAL_VERSION", "CHIT_RESULT_VITAL_VERSION"),
            ("CHIT_RESULT_HEADER_WIRE_SIZE", "CHIT_RESULT_HEADER_WIRE_SIZE"),
            ("HIT_ELEMENT_WIRE_SIZE", "HIT_ELEMENT_WIRE_SIZE"),
            ("HIT_COUNT_WIRE_SIZE", "HIT_COUNT_WIRE_SIZE"),
            ("DAMAGE_WIRE_MIN", "DAMAGE_WIRE_MIN"),
            ("DAMAGE_WIRE_MAX", "DAMAGE_WIRE_MAX"),
            ("FLAGS_HIT", "FLAGS_HIT"),
            ("FLAGS_MISS", "FLAGS_MISS"),
        )
        for here, there in pairs:
            self.assertEqual(
                getattr(mob_combat, here),
                getattr(hostile_hp_link_hypothesis, there),
                "%s drifted from HYP-PF-038" % here)

    def test_the_damage_is_recomputed_not_written_down(self):
        defender = mob_defender(self.mob)
        expected = (
            mob_combat.ATK_BASE
            + mob_combat.K_ATK_STR * self.attacker.ability_str
            + mob_combat.K_ATK_LV * self.attacker.level
        ) - (
            mob_combat.DEF_BASE
            + mob_combat.K_DEF_CON * defender.ability_con
            + mob_combat.K_DEF_LV * defender.level
        )
        self.assertEqual(resolve_damage(self.attacker, defender), expected)

    def test_a_hit_never_goes_below_the_minimum(self):
        weakest = Combatant(level=1, ability_str=0, ability_con=0)
        strongest = Combatant(level=1000, ability_str=0, ability_con=100000)
        self.assertEqual(
            resolve_damage(weakest, strongest), mob_combat.MIN_HIT)

    # -- the ledger -------------------------------------------------------

    def test_the_ledger_opens_at_every_ceiling_in_the_roster(self):
        ledger = open_ledger()
        self.assertEqual(len(ledger.balances), len(self.roster))
        for mob in self.roster:
            row = ledger.balance_of(mob.actor_identity)
            self.assertEqual(row.current_hp, mob.max_hp)
            self.assertEqual(row.max_hp, mob.max_hp)
        self.assertEqual(
            list(ledger.identities()), sorted(ledger.identities()))

    def test_the_announced_number_is_the_number_subtracted(self):
        ledger = open_ledger()
        ledger, outcome = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 964)
        self.assertEqual(outcome.damage, 964)
        self.assertEqual(outcome.damage_wire, -964)
        self.assertEqual(outcome.applied, 964)
        self.assertEqual(outcome.hp_before - outcome.hp_after, 964)
        self.assertEqual(
            ledger.balance_of(self.mob.actor_identity).current_hp,
            self.mob.max_hp - 964)

    def test_two_hits_stack_on_the_same_balance(self):
        ledger = open_ledger()
        ledger, _ = apply_hit(ledger, PERFORMER, self.mob.actor_identity, 964)
        ledger, second = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 2122)
        self.assertEqual(second.hp_after, self.mob.max_hp - 964 - 2122)

    def test_the_floor_holds_and_says_so(self):
        ledger = open_ledger()
        ledger, outcome = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, self.mob.max_hp * 2)
        self.assertEqual(outcome.hp_after, HP_FLOOR)
        self.assertEqual(outcome.applied, self.mob.max_hp - HP_FLOOR)
        self.assertEqual(
            outcome.clamped_by, self.mob.max_hp * 2 - outcome.applied)
        self.assertTrue(outcome.at_floor)
        self.assertTrue(outcome.death_due)
        self.assertEqual(outcome.damage_wire, -outcome.applied)
        # and a hit on a monster already at the floor moves nothing at all
        ledger, again = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 500)
        self.assertEqual(again.applied, 0)
        self.assertEqual(again.flags, FLAGS_MISS)
        self.assertEqual(again.damage_wire, 0)
        self.assertTrue(again.death_due)

    def test_the_ledger_is_never_mutated_in_place(self):
        first = open_ledger()
        second, _ = apply_hit(first, PERFORMER, self.mob.actor_identity, 100)
        self.assertEqual(
            first.balance_of(self.mob.actor_identity).current_hp,
            self.mob.max_hp)
        self.assertNotEqual(first, second)

    def test_a_ledger_refuses_a_duplicate_identity(self):
        row = MobBalance(0x2001, 100, 100)
        with self.assertRaises(MobCombatContractError) as caught:
            CombatLedger((row, row))
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_DUPLICATE_LEDGER_IDENTITY)

    def test_the_performer_may_not_be_the_target(self):
        ledger = open_ledger()
        with self.assertRaises(MobCombatContractError) as caught:
            apply_hit(
                ledger, self.mob.actor_identity, self.mob.actor_identity, 10)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_PERFORMER_IS_THE_TARGET)

    def test_an_unopened_target_is_refused_by_name(self):
        with self.assertRaises(MobCombatContractError) as caught:
            apply_hit(open_ledger(), PERFORMER, 0x7FFF, 10)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    # -- the threat seam --------------------------------------------------

    def test_threat_rises_by_the_damage(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        step = strike(
            self.legacy, mob_aggro, ledger, state, self.mob,
            PERFORMER, self.attacker)
        self.assertEqual(
            step.aggro_state.threat, ((PERFORMER, step.outcome.damage),))
        second = strike(
            self.legacy, mob_aggro, step.ledger, step.aggro_state, self.mob,
            PERFORMER, self.attacker)
        self.assertEqual(
            second.aggro_state.threat,
            ((PERFORMER, step.outcome.damage + second.outcome.damage),))

    def test_a_hit_that_moves_nothing_adds_no_threat(self):
        ledger = open_ledger()
        ledger, outcome = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, self.mob.max_hp * 2)
        ledger, nothing = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 500)
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        self.assertIs(apply_threat(mob_aggro, state, nothing), state)

    def test_an_incomplete_aggro_handle_is_refused_by_name(self):
        ledger = open_ledger()
        _, outcome = apply_hit(ledger, PERFORMER, self.mob.actor_identity, 10)
        with self.assertRaises(MobCombatContractError) as caught:
            apply_threat(object(), None, outcome)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_AGGRO_HANDLE_INCOMPLETE)

    # -- the wire ---------------------------------------------------------

    def test_the_announce_frame_carries_the_signed_number(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        step = strike(
            self.legacy, mob_aggro, ledger, state, self.mob,
            PERFORMER, self.attacker)
        entry = encode_hit_entry(
            self.legacy, self.mob.actor_identity, step.outcome.damage_wire,
            (self.mob.x, self.mob.y, self.mob.z), FLAGS_HIT)
        self.assertEqual(len(entry), HIT_ELEMENT_WIRE_SIZE)
        self.assertIn(
            bytes(self.legacy.u32tag(
                mob_combat.TAG_U32,
                step.outcome.damage_wire & 0xFFFFFFFF)),
            entry)
        self.assertIn(entry, step.announce_pc)
        self.assertIn(
            bytes(self.legacy.u16tag(
                mob_combat.TAG_U16, CHIT_RESULT_VITAL_ID)),
            step.announce_pc)
        self.assertEqual(step.announce_frame, self.legacy.frame_pc(
            step.announce_pc))

    def test_the_encoders_are_byte_identical_to_the_proven_lane(self):
        # The whole re-derivation stands or falls here.  This module refuses to
        # import HYP-PF-038 because that lane is scenario-gated and a flagless
        # build cannot reach it - but a re-derivation nobody compares is just a
        # second guess.  A test MAY reach the probe lane, so it does: same
        # target, same position, same damage, same flags, and the bytes must be
        # equal, not merely the same length.  ``_PROFILE`` is that lane's own
        # allowlisted scenario object and its unlock minter takes nothing else.
        unlock = hostile_hp_link_hypothesis.hostile_hp_link_wire_unlock(
            hostile_hp_link_hypothesis._PROFILE)
        target = hostile_hp_link_hypothesis.hostile_hp_link_target_identity()
        # ROUND 8ftmbx: ~~self.mob~~.  The probe lane is pinned to ONE target,
        # bg0001 placement 30, and that row left the shipped roster with
        # COO-DECISION 2026-08-29T00:41+07:00.  The comparison is against
        # THAT lane's bytes, so the subject has to stay that lane's actor;
        # rebuilt from the preserved row rather than looked up in a roster
        # that no longer has it.
        subject = field_mobs.gt035_observed_subject()
        self.assertEqual(target, subject.actor_identity)
        position = (subject.x, subject.y, subject.z)
        for damage_wire, flags in ((-964, FLAGS_HIT), (-2122, FLAGS_HIT),
                                   (0, FLAGS_MISS)):
            mine = encode_hit_entry(
                self.legacy, target, damage_wire, position, flags)
            theirs = hostile_hp_link_hypothesis.\
                encode_hostile_hp_link_hit_entry(
                    self.legacy, target, damage_wire, position,
                    hostile_hp_link_hypothesis.YAW_PINNED, flags, unlock)
            self.assertEqual(mine, theirs)
            self.assertEqual(
                mob_combat.encode_chit_result(self.legacy, PERFORMER, [mine]),
                hostile_hp_link_hypothesis.encode_hostile_hp_link_chit_result(
                    self.legacy, PERFORMER, [theirs], unlock))

    def test_a_positive_damage_number_is_refused_by_name(self):
        with self.assertRaises(MobCombatContractError) as caught:
            encode_hit_entry(
                self.legacy, self.mob.actor_identity, 964,
                (self.mob.x, self.mob.y, self.mob.z), FLAGS_HIT)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_DAMAGE_WIRE_POSITIVE)

    def test_a_miss_and_a_number_may_not_disagree(self):
        with self.assertRaises(MobCombatContractError) as caught:
            encode_hit_entry(
                self.legacy, self.mob.actor_identity, -964,
                (self.mob.x, self.mob.y, self.mob.z), FLAGS_MISS)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_FLAGS_DISAGREE_WITH_DAMAGE)

    def test_the_bar_frame_differs_from_gt035s_by_exactly_the_faction(self):
        # D1.  Stated as a test so nobody has to take the paragraph's word for
        # it: the frame this production driver refreshes is NOT the frame the
        # attended round watched.  It is eight bytes longer (five for
        # faction, three for RE-117's level) and its BasicAttr mask carries
        # bits 0x0400 and 0x0002.
        hp = self.mob.max_hp - 964
        mine = field_mobs.hostile_npc_attr(
            self.legacy, self.mob, current_hp=hp)
        theirs = self.legacy.make_npc_attr(
            self.mob.template_id, self.mob.actor_identity,
            mob_combat.field_mobs.SCENE_ID,
            mob_combat.field_mobs.SCENE_SEQUENCE,
            self.mob.visual_preset, hp, self.mob.max_hp,
            movement_speed=float(self.mob.speed_walk),
            basic_name=self.mob.display_name,
        )
        self.assertEqual(
            len(mine),
            len(theirs)
            + field_mobs.FACTION_SPLICE_BYTES + field_mobs.LEVEL_SPLICE_BYTES)
        self.assertIn(
            bytes(self.legacy.u32tag(
                field_mobs.FACTION_TAG, field_mobs.FIELD_MOB_FACTION)),
            mine)
        self.assertNotIn(
            bytes(self.legacy.u32tag(
                field_mobs.FACTION_TAG, field_mobs.FIELD_MOB_FACTION)),
            theirs)

    def test_the_bar_frame_is_the_hostile_body_with_a_lower_hp(self):
        hp = self.mob.max_hp - 964
        pc, frame = bar_frames(self.legacy, self.mob, hp)
        body = field_mobs.hostile_npc_attr(
            self.legacy, self.mob, current_hp=hp)
        self.assertIn(body, pc)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        # the same monster at full HP differs only by the HP fields, and the
        # refresh carries no movement attribute at all
        full_pc, _ = bar_frames(self.legacy, self.mob, self.mob.max_hp)
        self.assertEqual(len(pc), len(full_pc))
        self.assertNotEqual(pc, full_pc)
        placed_pc, _ = bar_frames(
            self.legacy, self.mob, hp, with_movement=True)
        self.assertGreater(len(placed_pc), len(pc))

    def test_the_bar_frame_refuses_to_go_under_the_floor(self):
        # ~~0 was under the floor~~ - with the floor at 0 it is ON it, and a
        # LIVE body there satisfies neither side of the client's gate, so it
        # is refused by its own name and handed to mob_death.
        with self.assertRaises(MobCombatContractError) as caught:
            bar_frames(self.legacy, self.mob, 0)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_BAR_FRAME_FOR_A_DEAD_BODY)
        self.assertIn("mob_death", caught.exception.detail)
        with self.assertRaises(MobCombatContractError) as caught:
            bar_frames(self.legacy, self.mob, -1)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_VALUE_OUT_OF_RANGE)

    def test_the_bar_frame_is_a_one_entry_generation_open_risk_not_a_fix(self):
        # This test does not close anything - it PINS the shape the docstring
        # above now warns about, so the next round (or chief, or RE) has a
        # red test the moment anyone widens this to a full-roster generation
        # without meaning to, or narrows a fix down to zero entries by
        # mistake.  See the docstring citation: `pirate-force-server#63`
        # wired this onto the unflagged path 2026-08-26 16:49+07:00, and
        # `pf_bridge/notes_to_chief/20260826_1017_RE-082-RESULT-OBJECT-REF-IS-ELEMENT-
        # KEY.md` proved a sibling collection's consumer erases every entry a
        # nonempty generation omits.  Nobody has run that trace against THIS
        # collection's consumer yet, so this lane records the fact - one
        # entry, not zero, not the roster - rather than claiming a fix.
        hp = self.mob.max_hp - 964
        pc, _ = bar_frames(self.legacy, self.mob, hp)
        body = field_mobs.hostile_npc_attr(
            self.legacy, self.mob, current_hp=hp)
        one_entry = self.legacy.make_remote_actor_entry(
            mob_combat.NPC_STYLE_ACTOR_TYPE, self.mob.actor_identity,
            [(mob_combat.NPC_ATTR_ID, body)])
        self.assertEqual(
            pc, self.legacy.make_runtime_remote_actors([one_entry])[0])

    def test_the_two_frames_come_back_in_the_watched_order(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        step = strike(
            self.legacy, mob_aggro, ledger, state, self.mob,
            PERFORMER, self.attacker)
        self.assertEqual(
            step.frames, (step.announce_frame, step.bar_frame))
        self.assertIn(NPC_ATTR_ID.to_bytes(2, "little"), step.bar_pc)

    def test_the_announce_frame_refuses_a_mismatched_mob(self):
        ledger = open_ledger()
        _, outcome = apply_hit(ledger, PERFORMER, self.mob.actor_identity, 10)
        other = [m for m in self.roster if m.actor_identity
                 != self.mob.actor_identity][0]
        with self.assertRaises(MobCombatContractError) as caught:
            announce_frames(self.legacy, PERFORMER, other, outcome)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    # -- the inbound seam -------------------------------------------------

    def test_an_ea7d_action_on_a_monster_drives_a_hit(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        step = attack_from_observed_action(
            self.legacy, mob_aggro, ledger, state,
            {"field_qword_20": self.mob.actor_identity},
            PERFORMER, self.attacker,
        )
        self.assertIsNotNone(step)
        self.assertEqual(step.outcome.target_identity, self.mob.actor_identity)
        self.assertLess(step.outcome.hp_after, self.mob.max_hp)

    def test_an_ea7d_action_on_a_townsperson_is_not_an_error(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        self.assertIsNone(attack_from_observed_action(
            self.legacy, mob_aggro, ledger, state,
            {"field_qword_20": 0x2001}, PERFORMER, self.attacker,
        ))

    def test_malformed_action_fields_are_refused_by_name(self):
        ledger = open_ledger()
        with self.assertRaises(MobCombatContractError) as caught:
            attack_from_observed_action(
                self.legacy, mob_aggro, ledger, None, {}, PERFORMER,
                self.attacker)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_ACTION_FIELDS_MALFORMED)

    # -- what the adversarial review of 2026-08-26 broke -------------------

    def test_an_outcome_cannot_announce_one_number_and_subtract_another(self):
        # D4.  This record used to be the only unvalidated one in the module,
        # and announce_frames / apply_threat / describe_step all took whatever
        # they were handed.  apply_hit is not the only builder: the chief's
        # wiring and the death lane both will be.
        with self.assertRaises(MobCombatContractError) as caught:
            mob_combat.HitOutcome(
                PERFORMER, self.mob.actor_identity, 964, -1, FLAGS_HIT,
                3857, 2893, 3857, 0, False, False)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_OUTCOME_SELF_CONTRADICTORY)
        with self.assertRaises(MobCombatContractError):
            # the balance moved 100 while the hit says 964
            mob_combat.HitOutcome(
                PERFORMER, self.mob.actor_identity, 964, -964, FLAGS_HIT,
                3857, 3757, 3857, 0, False, False)
        with self.assertRaises(MobCombatContractError):
            # at_floor that does not agree with hp_after
            mob_combat.HitOutcome(
                PERFORMER, self.mob.actor_identity, 964, -964, FLAGS_HIT,
                3857, 2893, 3857, 0, True, True)

    def test_two_hits_in_one_tick_cannot_both_be_committed(self):
        # The concurrency case: two players action the same monster before
        # either write lands.  Without a compare-and-swap both announce -964
        # and one subtraction is lost - 1928 announced, 964 subtracted.
        ledger = open_ledger()
        first = strike(
            self.legacy, None, ledger, None, self.mob, PERFORMER,
            self.attacker)
        second = strike(
            self.legacy, None, ledger, None, self.mob, PERFORMER + 1,
            self.attacker)
        self.assertEqual(first.base_generation, second.base_generation)
        stored = mob_combat.commit_step(ledger, first)
        self.assertEqual(stored.generation, ledger.generation + 1)
        with self.assertRaises(MobCombatContractError) as caught:
            mob_combat.commit_step(stored, second)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_LEDGER_STALE)

    def test_a_hit_with_no_room_left_sends_nothing_at_all(self):
        # D5.  The first draft answered a real 964-damage hit on a floored
        # monster with a MISS frame: the wire told the client the player had
        # missed when the formula said otherwise.
        thumping = Combatant(level=1000, ability_str=100000, ability_con=0)
        ledger = open_ledger()
        first = strike(
            self.legacy, None, ledger, None, self.mob, PERFORMER, thumping)
        self.assertEqual(first.outcome.hp_after, HP_FLOOR)
        second = strike(
            self.legacy, None, first.ledger, None, self.mob, PERFORMER,
            thumping)
        self.assertTrue(second.outcome.no_room)
        self.assertEqual(second.frames, ())
        self.assertEqual(second.announce_frame, b"")
        self.assertGreater(second.outcome.clamped_by, 0)
        self.assertTrue(
            any("nothing sent" in line for line in describe_step(second)))

    def test_a_dropped_threat_fold_is_recorded_not_inferred(self):
        # D6.  mob_aggro absorbs damage silently in its return and dead phases
        # - its declared design - so a driver that cannot tell reports a
        # monster as aggroed when it is not.
        ledger = open_ledger()
        returning = mob_aggro.MobAiState(
            phase=mob_aggro.PHASE_RETURN,
            leash_origin=(self.mob.x, self.mob.y, self.mob.z),
            threat=(), target_identity=None, ticks_since_attack=0)
        step = strike(
            self.legacy, mob_aggro, ledger, returning, self.mob, PERFORMER,
            self.attacker)
        self.assertLess(step.outcome.hp_after, self.mob.max_hp)
        self.assertEqual(step.aggro_state.threat, ())
        self.assertFalse(step.threat_recorded)
        self.assertTrue(
            any("threat NOT recorded" in line for line in describe_step(step)))

    def test_the_threat_handle_is_optional_and_that_is_the_wiring(self):
        # D8.  Passing mob_aggro in makes a lane whose production_allowed is
        # False reachable from dispatch through an argument no static scan can
        # see.  The supported production wiring passes None.
        ledger = open_ledger()
        step = strike(
            self.legacy, None, ledger, None, self.mob, PERFORMER,
            self.attacker)
        self.assertFalse(step.threat_recorded)
        self.assertEqual(len(step.frames), 2)
        self.assertIn("None", mob_combat.MOB_COMBAT_WIRING)
        self.assertIn("commit_step", mob_combat.MOB_COMBAT_WIRING)
        self.assertTrue(mob_combat.MOB_COMBAT_THREAT_HANDLE_IS_OPTIONAL)

    def test_a_ledger_row_from_another_roster_is_refused(self):
        # D16.  With a mismatched ceiling the announced number came from the
        # roster row and the bar frame from the ledger row.
        row = MobBalance(self.mob.actor_identity, 100, 100)
        with self.assertRaises(MobCombatContractError) as caught:
            strike(
                self.legacy, None, CombatLedger((row,)), None, self.mob,
                PERFORMER, self.attacker)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_LEDGER_ROW_DISAGREES_WITH_ROSTER)

    def test_a_roster_ledger_desync_is_refused_not_silently_ignored(self):
        # D7.  This used to return None, indistinguishable from the ordinary
        # "the player actioned a townsperson" case, and that line had never
        # executed.
        rows = tuple(
            row for row in open_ledger().balances
            if row.actor_identity != self.mob.actor_identity)
        with self.assertRaises(MobCombatContractError) as caught:
            attack_from_observed_action(
                self.legacy, None, CombatLedger(rows), None,
                {"field_qword_20": self.mob.actor_identity}, PERFORMER,
                self.attacker)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    def test_an_unsorted_ledger_is_refused_not_quietly_re_sorted(self):
        # D12.  The module promises no silent coercion; the sibling
        # mob_aggro.MobAiState refuses this exact shape by name.
        rows = open_ledger().balances
        with self.assertRaises(MobCombatContractError) as caught:
            CombatLedger(tuple(reversed(rows)))
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_LEDGER_NOT_SORTED)

    def test_every_named_refusal_reason_can_actually_happen(self):
        # D11.  Two of the eighteen names could not occur: one was raised
        # nowhere and one sat behind an unreachable branch.  A named refusal
        # that cannot happen is a lie told to whoever counts them.
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_combat.py").read_text(
                encoding="utf-8"))
        raised = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise):
                continue
            call = node.exc
            if (isinstance(call, ast.Call)
                    and getattr(call.func, "id", "") == "MobCombatContractError"
                    and call.args
                    and isinstance(call.args[0], ast.Name)):
                raised.add(getattr(mob_combat, call.args[0].id))
        self.assertEqual(
            sorted(raised),
            sorted(mob_combat.MOB_COMBAT_REFUSAL_REASONS),
            "a refusal is declared and never raised, or raised and never "
            "declared")
        # and the one that used to be unreachable behind a range check
        with self.assertRaises(MobCombatContractError) as caught:
            mob_combat.require_damage_wire(mob_combat.DAMAGE_WIRE_MIN - 1)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_DAMAGE_WIRE_OUT_OF_RANGE)

    # -- the lane's own rules ---------------------------------------------

    def test_this_lane_needs_no_flag(self):
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        # Checked on NAMES rather than on raw text: the pin document says
        # "no_scenario_flag" in a string value, and a substring search would
        # either fail on that or have to be weakened to nothing.  What must not
        # exist is a scenario or unlock SEAM - a constant, a parameter or a
        # function this lane could be gated behind.
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_combat.py").read_text(
                encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.keyword) and node.arg:
                names.add(node.arg)
        for name in sorted(names):
            lowered = name.lower()
            self.assertNotIn(
                "scenario", lowered,
                "a production lane must not carry a scenario seam: %s" % name)
            self.assertNotIn(
                "unlock", lowered,
                "a production lane must not carry an unlock seam: %s" % name)

    def test_this_module_imports_no_probe_lane(self):
        # Walked with ast, not matched on line prefixes.  The first draft used
        # startswith("import ", "from ") and an adversarial review showed three
        # bypasses in one minute: an indented import inside a function, a
        # parenthesised multi-line import, and both together.  A tripwire with
        # a documented bypass is worse than none, because it is quoted.
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_combat.py").read_text(
                encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
                imported.extend(alias.name for alias in node.names)
        for name in imported:
            self.assertNotIn("hypothesis", name)
            self.assertNotIn("mob_aggro", name)
        self.assertIn("field_mobs", imported)

    def test_determinism_two_runs_agree(self):
        def run():
            ledger = open_ledger()
            state = mob_aggro.initial_state(
                (self.mob.x, self.mob.y, self.mob.z))
            step = strike(
                self.legacy, mob_aggro, ledger, state, self.mob,
                PERFORMER, self.attacker)
            return (step.ledger, step.aggro_state, step.outcome,
                    step.announce_frame, step.bar_frame)
        self.assertEqual(run(), run())

    def test_the_driver_reproduces_the_ladder_gt035_watched(self):
        # The strongest control this lane has.  Two observers watched a real
        # client walk this monster's bar 3857 -> 2893 -> 2893 -> 771 in GT-035
        # (2026-08-25).  Those numbers came out of a probe lane pinned to one
        # target; this is a general production driver, and it must land on the
        # SAME two damage numbers for the same two attacker profiles - or the
        # thing the owner boots without a flag is not the thing anybody saw.
        # ROUND 8ftmbx: ~~self.mob~~.  The bar those two observers watched
        # belonged to bg0001 placement 30 as the set-number reading rendered
        # it -- level 27, 3857 HP -- and COO-DECISION 2026-08-29T00:41+07:00
        # withdrew that row from the shipped roster.  The subject here is
        # therefore the actor the ladder was watched ON, rebuilt from the row
        # the generated table preserves for this, not the roster's new control
        # row: 916 is level 100 with 198,125 HP, and running this comparison
        # against it would have "reproduced" numbers nobody ever saw.
        subject = field_mobs.gt035_observed_subject()
        self.assertEqual(subject.max_hp, 3857)
        ledger = open_ledger(roster=(subject,))
        profiles = hostile_hp_link_hypothesis.HOSTILE_HP_LINK_ATTACKER_PROFILES
        pinned = hostile_hp_link_hypothesis.HOSTILE_HP_LINK_DAMAGE_PINNED
        for name, expected_after in (("MOB_WEAK", 2893), ("MOB_STRONG", 771)):
            level, ability_str = profiles[name]
            attacker = Combatant(
                level=level, ability_str=ability_str, ability_con=0)
            damage = resolve_damage(attacker, mob_defender(subject))
            ledger, outcome = apply_hit(
                ledger, PERFORMER, subject.actor_identity, damage)
            self.assertEqual(outcome.damage_wire, pinned[name])
            self.assertEqual(outcome.hp_after, expected_after)
        self.assertEqual(
            hostile_hp_link_hypothesis.DEFENDER_ABILITY_CON,
            mob_combat.MOB_ABILITY_CON)
        self.assertEqual(
            hostile_hp_link_hypothesis.DEFENDER_LEVEL, subject.level)

    def test_the_committed_pin_is_what_the_code_produces(self):
        path = ROOT / "scenarios/combat_first_hit_001.json"
        raw = path.read_bytes()
        self.assertTrue(raw.decode("utf-8").isascii())
        committed = json.loads(raw.decode("ascii"))
        # ROUND 8ftmbx: ~~a roster lookup on PIN_PLACEMENT_INDEX~~.  The row
        # this pin's numbers were watched on is withdrawn from the shipped
        # roster (COO-DECISION 2026-08-29T00:41+07:00), and the pin
        # deliberately did NOT follow the table -- see mob_combat.pin_subject
        # on why moving it to the new control row would have compared today's
        # arithmetic against numbers nobody saw.
        pinned_mob = mob_combat.pin_subject()
        self.assertEqual(
            pinned_mob.placement_index, mob_combat.PIN_PLACEMENT_INDEX)
        self.assertNotIn(
            pinned_mob.placement_index,
            [m.placement_index for m in self.roster],
            "the GT-035 subject is a shipped roster row again: this pin has "
            "to be re-read before it can be trusted")
        self.assertEqual(committed, pin_document(self.legacy, pinned_mob))
        self.assertTrue(committed["production_allowed"])
        self.assertFalse(committed["test_only"])
        self.assertEqual(
            committed["selection"], "none_default_behaviour_no_scenario_flag")
        self.assertEqual(committed["damage_wire"], -964)
        self.assertEqual(committed["hp_after"], 2893)
        self.assertGreaterEqual(len(committed["nonclaims"]), 6)

    def test_the_pin_document_computes_its_numbers(self):
        pin = pin_document(self.legacy, self.mob, self.attacker)
        self.assertEqual(pin["target_name"], ascii(self.mob.display_name))
        self.assertTrue(pin["not_a_scenario"])
        self.assertEqual(
            pin["target_position"], [self.mob.x, self.mob.y, self.mob.z])
        self.assertEqual(pin["target_faction"], field_mobs.FIELD_MOB_FACTION)
        self.assertFalse(pin["threat_recorded"])
        self.assertEqual(pin["max_hp"], self.mob.max_hp)
        self.assertEqual(pin["damage_wire"], -pin["damage"])
        self.assertEqual(pin["hp_after"], pin["max_hp"] - pin["damage"])
        self.assertTrue(pin["production_allowed"])
        self.assertIn("runtime.py", pin["wiring"])

    def test_describe_step_names_the_floor_when_it_bites(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        thumping = Combatant(level=1000, ability_str=100000, ability_con=0)
        step = strike(
            self.legacy, mob_aggro, ledger, state, self.mob,
            PERFORMER, thumping)
        lines = describe_step(step)
        # ~~"clamped by"~~ with the floor at 0 the clamp is overkill, not a
        # monster held one point above death, and the line says so.
        self.assertTrue(any("overkill by" in line for line in lines))
        self.assertTrue(any("death due" in line for line in lines))
        self.assertTrue(any("mob_death.kill" in line for line in lines))

    # -- attack cadence (PANYA-REFERENCE 2026-08-27 16:35, RE-110) ---------
    #
    # These pin the "spam-click = runaway damage" gate ahead of RE-110's
    # real number: a fast-second-attack rejection, an accept once the window
    # elapses, and no cross-performer blocking.  ``ATTACK_CADENCE_MS_
    # PROVISIONAL`` is used throughout rather than a hard-coded literal, so a
    # later round that swaps the constant does not also have to hand-edit
    # every test's arithmetic.

    OTHER_PERFORMER = 0x750060

    def test_the_first_attack_from_a_new_performer_is_accepted(self):
        cadence = open_cadence_ledger()
        check = check_attack_cadence(cadence, PERFORMER, 1_000)
        self.assertTrue(check.accepted)
        self.assertEqual(check.early_by_ms, 0)
        self.assertEqual(
            check.cadence.last_accepted_at(PERFORMER), 1_000)

    def test_a_second_attack_inside_the_window_is_rejected(self):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        too_soon_at = 1_000 + ATTACK_CADENCE_MS_PROVISIONAL - 1
        second = check_attack_cadence(first.cadence, PERFORMER, too_soon_at)
        self.assertFalse(second.accepted)
        self.assertEqual(second.early_by_ms, 1)
        # a rejection must not move the ledger: the window is measured from
        # the last ACCEPTED attack, not from the last attempt.
        self.assertEqual(second.cadence, first.cadence)
        self.assertEqual(second.cadence.last_accepted_at(PERFORMER), 1_000)

    def test_an_attack_exactly_at_the_window_is_accepted(self):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        exactly_at = 1_000 + ATTACK_CADENCE_MS_PROVISIONAL
        second = check_attack_cadence(first.cadence, PERFORMER, exactly_at)
        self.assertTrue(second.accepted)
        self.assertEqual(
            second.cadence.last_accepted_at(PERFORMER), exactly_at)

    def test_an_attack_after_the_window_elapses_is_accepted(self):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        well_after = 1_000 + ATTACK_CADENCE_MS_PROVISIONAL + 5_000
        second = check_attack_cadence(first.cadence, PERFORMER, well_after)
        self.assertTrue(second.accepted)

    def test_a_burst_of_rejects_does_not_slide_its_own_deadline(self):
        # Five rapid clicks after one accepted hit: the fifth is scored
        # against the SAME accepted timestamp as the second, not against the
        # fourth reject.
        cadence = open_cadence_ledger()
        cadence = check_attack_cadence(cadence, PERFORMER, 0).cadence
        early_by_values = []
        for offset in (10, 20, 30, 40, 50):
            check = check_attack_cadence(cadence, PERFORMER, offset)
            self.assertFalse(check.accepted)
            early_by_values.append(check.early_by_ms)
        expected = [
            ATTACK_CADENCE_MS_PROVISIONAL - offset
            for offset in (10, 20, 30, 40, 50)
        ]
        self.assertEqual(early_by_values, expected)

    def test_two_performers_are_not_cross_blocked(self):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        second = check_attack_cadence(
            first.cadence, self.OTHER_PERFORMER, 1_000 + 1)
        self.assertTrue(second.accepted)
        self.assertEqual(
            second.cadence.last_accepted_at(PERFORMER), 1_000)
        self.assertEqual(
            second.cadence.last_accepted_at(self.OTHER_PERFORMER), 1_001)

    def test_clock_skew_fails_closed_not_open(self):
        # A caller-supplied timestamp earlier than this performer's own last
        # accepted one must never be read as "plenty of time has passed".
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 10_000)
        second = check_attack_cadence(first.cadence, PERFORMER, 1)
        self.assertFalse(second.accepted)
        self.assertEqual(second.early_by_ms, ATTACK_CADENCE_MS_PROVISIONAL)

    def test_a_rejection_console_line_names_the_performer_and_the_shortfall(
        self,
    ):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        second = check_attack_cadence(first.cadence, PERFORMER, 1_050)
        lines = describe_cadence_rejection(second)
        self.assertEqual(len(lines), 1)
        self.assertIn("0x%X" % PERFORMER, lines[0])
        self.assertIn("REJECTED", lines[0])
        self.assertIn("%d" % second.early_by_ms, lines[0])
        self.assertIn("RE-110", lines[0])
        self.assertTrue(lines[0].isascii())

    def test_describe_cadence_rejection_refuses_an_accepted_check(self):
        cadence = open_cadence_ledger()
        accepted = check_attack_cadence(cadence, PERFORMER, 1_000)
        with self.assertRaises(MobCombatContractError) as caught:
            describe_cadence_rejection(accepted)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_CADENCE_OUTCOME_SELF_CONTRADICTORY)

    def test_cadence_ledger_refuses_unsorted_rows(self):
        rows = (CadenceRecord(2, 0), CadenceRecord(1, 0))
        with self.assertRaises(MobCombatContractError) as caught:
            AttackCadenceLedger(rows)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_CADENCE_NOT_SORTED)

    def test_cadence_ledger_refuses_duplicate_identity(self):
        rows = (CadenceRecord(1, 0), CadenceRecord(1, 5))
        with self.assertRaises(MobCombatContractError) as caught:
            AttackCadenceLedger(rows)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_DUPLICATE_CADENCE_IDENTITY)

    def test_cadence_ledger_never_shrinks_and_keys_by_performer(self):
        cadence = open_cadence_ledger()
        cadence = check_attack_cadence(cadence, PERFORMER, 0).cadence
        cadence = check_attack_cadence(
            cadence, self.OTHER_PERFORMER, 0).cadence
        self.assertEqual(
            sorted(cadence.identities()),
            sorted((PERFORMER, self.OTHER_PERFORMER)))
        # a second accepted attack from the SAME performer replaces its row
        # rather than growing the ledger.
        cadence = check_attack_cadence(
            cadence, PERFORMER, ATTACK_CADENCE_MS_PROVISIONAL).cadence
        self.assertEqual(len(cadence.identities()), 2)

    def test_this_lane_needs_no_flag_covers_cadence_names_too(self):
        # The existing test_this_lane_needs_no_flag already re-scans the
        # whole module text, so this only pins that the new names are
        # actually present for it to have scanned.
        self.assertIn("check_attack_cadence", dir(mob_combat))
        self.assertIn("ATTACK_CADENCE_MS_PROVISIONAL", dir(mob_combat))


if __name__ == "__main__":
    unittest.main()
