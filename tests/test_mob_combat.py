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

``test_the_bar_frame_is_the_hostile_body_with_a_lower_hp`` pins the wire half
to the shape GT-035 watched move on a real screen: the bar frame differs from
the spawn body only in HP, and carries no movement attribute.

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
    CHIT_RESULT_HEADER_WIRE_SIZE,
    CHIT_RESULT_VITAL_ID,
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
    describe_step,
    encode_hit_entry,
    mob_defender,
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
        cls.mob = [m for m in cls.roster if m.placement_index == 30][0]
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
        self.assertEqual(target, self.mob.actor_identity)
        position = (self.mob.x, self.mob.y, self.mob.z)
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
        with self.assertRaises(MobCombatContractError) as caught:
            bar_frames(self.legacy, self.mob, 0)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_VALUE_OUT_OF_RANGE)

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
        source = (ROOT / "src/pirateforce_foundation/mob_combat.py").read_text(
            encoding="utf-8")
        for line in source.splitlines():
            if line.startswith(("import ", "from ")):
                self.assertNotIn("hypothesis", line)
                self.assertNotIn("mob_aggro", line)

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
        ledger = open_ledger()
        profiles = hostile_hp_link_hypothesis.HOSTILE_HP_LINK_ATTACKER_PROFILES
        pinned = hostile_hp_link_hypothesis.HOSTILE_HP_LINK_DAMAGE_PINNED
        for name, expected_after in (("MOB_WEAK", 2893), ("MOB_STRONG", 771)):
            level, ability_str = profiles[name]
            attacker = Combatant(
                level=level, ability_str=ability_str, ability_con=0)
            damage = resolve_damage(attacker, mob_defender(self.mob))
            ledger, outcome = apply_hit(
                ledger, PERFORMER, self.mob.actor_identity, damage)
            self.assertEqual(outcome.damage_wire, pinned[name])
            self.assertEqual(outcome.hp_after, expected_after)
        self.assertEqual(
            hostile_hp_link_hypothesis.DEFENDER_ABILITY_CON,
            mob_combat.MOB_ABILITY_CON)
        self.assertEqual(
            hostile_hp_link_hypothesis.DEFENDER_LEVEL, self.mob.level)

    def test_the_committed_pin_is_what_the_code_produces(self):
        path = ROOT / "scenarios/combat_first_hit_001.json"
        raw = path.read_bytes()
        self.assertTrue(raw.decode("utf-8").isascii())
        committed = json.loads(raw.decode("ascii"))
        pinned_mob = [
            m for m in self.roster
            if m.placement_index == mob_combat.PIN_PLACEMENT_INDEX
        ][0]
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
        self.assertEqual(pin["target_name"], self.mob.display_name)
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
        self.assertTrue(any("clamped by" in line for line in lines))
        self.assertTrue(any("death due" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
