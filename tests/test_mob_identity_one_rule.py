"""COO-DECISION 20260909_1312 beat 3: a monster whose identity is NOT
positive registers, drops and fights -- proved BEFORE the allocator flips.

WHY THIS FILE EXISTS AND WHAT IT IS FOR.  PANYA `20260908_1545` ordered the
order: one identity-range rule, in one place, checked green, and only then
does this lane move ``field_mobs.actor_identity`` off
``0x2000 + placement_index + 1``.  The reason is written in the decision
letter and is worth repeating where the code is: on the morning it was
written, four different range rules stood on ``main``, and a monster at
``-2`` would have been DRAWN in the right colour by the client while the
server refused to register it, refused to drop for it, and refused the hit
that killed it -- each module for its own reason, none of them the
client's.  Flipping the allocator first would have shipped exactly that.

So these tests are the gate on beat 4, not a description of today: nothing
in this tree hands out a negative identity yet (``field_mobs.FieldMob``
still derives the positive formula, and this file PINS that too, so the day
it moves this file has to be read).  What they prove is that when it does
move, the paths a player walks -- register, hit, die, drop, pick up -- are
already judging identities by the one rule.

WHAT THIS FILE DOES NOT CLAIM.
  * It does not claim lane A's world registry accepts a negative identity.
    It does not: ``world_scene_registry._require_identity`` refuses < 1, and
    that file is lane A's to change, AFTER M2, per NOW.md and the same COO
    decision.  That wall is real, it is named in this round's round file,
    and it is the reason beat 4 is not in this commit.
  * It does not claim any of this was seen on a screen.  No client has drawn
    a negative-identity monster in this project's history except the six
    R324A sweep rows the owner read on 2026-09-08, and those were composed
    by hand for the sweep, not spawned by the roster.
  * It does not claim the shared rule is the only gate a hit passes.  It is
    the only RANGE gate.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mob_tables
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_aggro
from pirateforce_foundation import mob_combat
from pirateforce_foundation import mob_death
from pirateforce_foundation import mob_identity_sign
from pirateforce_foundation import mob_loot


#: A monster identity from the band this lane will allocate out of, taken
#: from the allocator itself rather than typed: -2 would be a sweep row.
NEGATIVE_MOB = mob_identity_sign.mob_wire_identity(0, 0)

#: A player.  Positive, because the client draws the player colour formula
#: by that sign -- see ``mob_identity_sign`` rule 1.
PLAYER = 0x1234


class TheOneRuleTests(unittest.TestCase):
    """The rule itself, before anything that depends on it."""

    def test_zero_is_refused_by_the_one_rule_because_the_client_will_not_draw_it(self):
        with self.assertRaises(mob_identity_sign.MobIdentitySignError):
            mob_identity_sign.require_targetable_identity(0, "identity")
        with self.assertRaises(mob_identity_sign.MobIdentitySignError):
            mob_identity_sign.require_player_identity(0, "player identity")

    def test_a_negative_identity_is_a_real_actor_and_not_a_player(self):
        self.assertEqual(
            mob_identity_sign.require_targetable_identity(NEGATIVE_MOB),
            NEGATIVE_MOB)
        with self.assertRaises(mob_identity_sign.MobIdentitySignError):
            mob_identity_sign.require_player_identity(NEGATIVE_MOB)

    def test_an_undecoded_wire_value_is_refused_rather_than_read_as_an_actor(self):
        # struct.unpack('<Q', ...) at every inbound parse point in the frozen
        # v141 file hands back this number for NEGATIVE_MOB.  It is not a big
        # actor; the caller owes it a decode_wire_identity() first.
        undecoded = NEGATIVE_MOB + 2 ** 64
        with self.assertRaises(mob_identity_sign.MobIdentitySignError):
            mob_identity_sign.require_targetable_identity(undecoded)
        self.assertEqual(
            mob_identity_sign.decode_wire_identity(undecoded), NEGATIVE_MOB)

    def test_true_is_not_an_identity_of_one(self):
        for value in (True, False):
            with self.assertRaises(mob_identity_sign.MobIdentitySignError):
                mob_identity_sign.require_targetable_identity(value)
            with self.assertRaises(mob_identity_sign.MobIdentitySignError):
                mob_identity_sign.require_player_identity(value)


class ANegativeMonsterCanFightTests(unittest.TestCase):
    """Beat 3, first third: it registers in the combat ledger and takes hits."""

    def setUp(self) -> None:
        self.ledger = mob_combat.CombatLedger(
            (mob_combat.MobBalance(NEGATIVE_MOB, 100, 100),))

    def test_the_ledger_opens_on_a_negative_identity(self):
        self.assertEqual(self.ledger.identities(), (NEGATIVE_MOB,))
        self.assertEqual(self.ledger.balance_of(NEGATIVE_MOB).current_hp, 100)

    def test_a_player_hit_lands_on_a_negative_identity_and_lowers_the_bar(self):
        after, outcome = mob_combat.apply_hit(
            self.ledger, PLAYER, NEGATIVE_MOB, 40)
        self.assertEqual(outcome.hp_before, 100)
        self.assertEqual(outcome.hp_after, 60)
        self.assertEqual(after.balance_of(NEGATIVE_MOB).current_hp, 60)

    def test_a_negative_identity_can_be_killed_and_the_death_is_recorded(self):
        after, outcome = mob_combat.apply_hit(
            self.ledger, PLAYER, NEGATIVE_MOB, 100)
        self.assertEqual(outcome.hp_after, 0)
        self.assertEqual(after.balance_of(NEGATIVE_MOB).current_hp, 0)
        record = mob_death.DeathRecord(NEGATIVE_MOB, PLAYER, 100)
        self.assertEqual(record.actor_identity, NEGATIVE_MOB)

    def test_the_ledger_still_refuses_identity_zero(self):
        with self.assertRaises(mob_combat.MobCombatContractError) as caught:
            mob_combat.CombatLedger((mob_combat.MobBalance(0, 100, 100),))
        self.assertIn("identity_not_positive", str(caught.exception))


class ANegativeMonsterCanDropTests(unittest.TestCase):
    """Beat 3, second third: the ground book holds its drops."""

    def test_a_ground_drop_stands_for_a_negative_identity(self):
        drop = mob_loot.GroundDrop(
            mob_loot.DROP_KEY_BASE, 2400046, 1, 0.0, 0.0, 0.0,
            NEGATIVE_MOB, PLAYER, field_mob_tables.SCENE)
        self.assertEqual(drop.mob_identity, NEGATIVE_MOB)
        ledger = mob_loot.DropLedger(
            (drop,), issued_through=mob_loot.DROP_KEY_BASE + 1)
        self.assertEqual(ledger.drops[0].mob_identity, NEGATIVE_MOB)

    def test_a_drop_still_refuses_identity_zero(self):
        with self.assertRaises(mob_loot.MobLootContractError) as caught:
            mob_loot.GroundDrop(
                mob_loot.DROP_KEY_BASE, 2400046, 1, 0.0, 0.0, 0.0,
                0, PLAYER, field_mob_tables.SCENE)
        self.assertIn("identity_not_positive", str(caught.exception))


class TheAggroTableStillKnowsAPlayerTests(unittest.TestCase):
    """Beat 3, third third, and the half the shared rule must NOT loosen.

    A threat table keyed by attacker holds PLAYERS.  If the widening had been
    applied there too, a monster could have entered its own threat table and
    every leash and target decision would have read it as an attacker.
    """

    def test_a_negative_attacker_is_still_refused_by_the_aggro_lane(self):
        with self.assertRaises(mob_aggro.MobAiContractError) as caught:
            mob_aggro.PlayerObservation(NEGATIVE_MOB, (0.0, 0.0, 0.0), True)
        self.assertIn("identity_not_positive", str(caught.exception))

    def test_a_player_observation_still_stands_on_a_positive_identity(self):
        seen = mob_aggro.PlayerObservation(PLAYER, (0.0, 0.0, 0.0), True)
        self.assertEqual(seen.identity, PLAYER)


class TheAllocatorHasNotMovedYetTests(unittest.TestCase):
    """The pin that makes beat 4 visible when it lands.

    This is deliberately a statement of TODAY, not of the goal: the whole
    point of beats 1-3 is that they are provable while the allocator is
    still positive.  When beat 4 flips ``FieldMob.actor_identity``, this
    test goes red in the same commit that flips it, and whoever writes that
    commit has to come here and say so.
    """

    def test_every_roster_monster_is_still_drawn_by_the_player_formula(self):
        roster = field_mobs.load_roster()
        self.assertTrue(roster)
        for mob in roster:
            self.assertTrue(
                mob_identity_sign.is_player_identity(mob.actor_identity),
                "placement %d is no longer positive: beat 4 has landed, so "
                "update this test and the round file that pins it"
                % mob.placement_index)


if __name__ == "__main__":  # pragma: no cover - parity with the lane's files
    unittest.main()
