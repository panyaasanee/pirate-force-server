"""LANE-B / MOB-AGGRO-001: the promotion, the mined profile, the controller.

The load-bearing tests in this file are these five.

``test_the_threat_fold_hands_over_the_negative_wire_number`` is the one that
matters most, and it is the one bug in this round that would have raised
nothing anywhere.  ``mob_aggro.apply_damage_threat`` adds threat only for a
NEGATIVE value and returns the state unchanged, silently, for a positive one.
``HitOutcome.damage`` is positive and ``HitOutcome.damage_wire`` is its
negative.  A controller that hands over the wrong one builds a monster that is
hit, loses HP, repaints its bar and never once decides it has an enemy.

``test_ten_of_thirteen_bg0001_monsters_never_INITIATE`` is the sentence
of this round a reader can check against the shipped table by eye, and it is
the reason the profile grew an ``offensive`` flag instead of just a radius: a
zero radius alone still admits a player standing exactly on the monster.

``test_the_profile_of_every_roster_row_is_buildable`` is what stops the
promotion from being decorative.  Before this round the profile contract
refused a zero aggro radius and required the attack range inside it, and BOTH
rules refuse ten of the thirteen real monsters.  A contract written against an
imagined roster is not a contract.

``test_two_players_hitting_two_monsters_in_one_tick_do_not_erase_each_other``
pins the compare-and-swap.  Without it both folds read the same register, both
return a register with one row changed, and the second store erases the first
monster's threat with nothing raised.

``test_the_mined_rows_and_the_roster_were_mined_from_the_same_mobs_table``
pins the one control that can be checked with no bridge clone present: the two
generated modules must record the same MOBS digest, or they describe different
data and every profile in this file is a join across two versions.
"""

import ast
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    field_mob_ai_tables, field_mob_tables, field_mobs, mob_aggro,
    mob_ai_control, mob_death,
)
from pirateforce_foundation.mob_ai_control import (  # noqa: E402
    MobAiControlError, MobAiRegister, MobAiRow, MobAiStep, commit_step,
    damage_step, death_step, open_register, profile_of, tick_step,
)
from pirateforce_foundation.mob_combat import (  # noqa: E402
    Combatant, HitOutcome, open_ledger, strike,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

MODULE_SOURCE_PATH = ROOT / "src/pirateforce_foundation/mob_ai_control.py"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
PLAYER = 0x750059
SECOND_PLAYER = 0x750060

# The two mined values, written out so this file states them rather than
# reading them back out of the module it is testing.
AI_WANDER_OFFENSIVE_ROW = 11
AI_WANDER_PASSIVE_ROW = 16
# Round szdkgs: the practice dummy's wander row, mined for the first time.
AI_WANDER_DUMMY_ROW = 21
MINED_AGGRO_RADIUS = 1200
OFFENSIVE_PLACEMENTS = (58, 63, 132)


def outcome(target, damage, hp_before, max_hp, attacker=PLAYER,
            no_room=False, clamped_by=0):
    hp_after = hp_before - damage
    return HitOutcome(
        attacker_identity=attacker,
        target_identity=target,
        damage=damage,
        damage_wire=-damage,
        flags=0x0001 if damage else 0x0000,
        hp_before=hp_before,
        hp_after=hp_after,
        max_hp=max_hp,
        clamped_by=clamped_by,
        at_floor=hp_after == 0,
        death_due=hp_after == 0,
        no_room=no_room,
    )


class MinedRowTests(unittest.TestCase):
    """What is in the table, and that it is the table the roster used."""

    def setUp(self):
        self.roster = field_mobs.load_roster()

    def test_the_mined_rows_and_the_roster_were_mined_from_the_same_mobs_table(self):
        self.assertEqual(
            field_mob_ai_tables.SOURCE_DIGESTS["mobs"],
            field_mob_tables.SOURCE_DIGESTS["mobs"],
            "the AI rows and the roster describe different MOBS tables: "
            "regenerate one of them")
        self.assertEqual(field_mob_ai_tables.SCENE, field_mob_tables.SCENE)

    def test_every_roster_row_resolves_to_exactly_one_row_of_each_ai_table(self):
        for mob in self.roster:
            with self.subTest(placement=mob.placement_index):
                self.assertIn(mob.ai_wander, field_mob_ai_tables.AI_WANDER_ROWS)
                if mob.ai_combat:
                    self.assertIn(
                        mob.ai_combat, field_mob_ai_tables.AI_COMBAT_ROWS)
                else:
                    # n_AI_COMBAT 0 is the table saying THIS ACTOR HAS NO
                    # COMBAT AI (round szdkgs's practice dummy), not a
                    # dangling key: there is no row to find and the join
                    # returns None rather than inventing one.
                    self.assertIsNone(mob_ai_control.ai_rows_of(mob)[1])

    def test_the_links_table_agrees_with_the_roster(self):
        derived = sorted(
            (mob.placement_index, mob.ai_wander, mob.ai_combat)
            for mob in self.roster
        )
        self.assertEqual(sorted(field_mob_ai_tables.PLACEMENT_AI_LINKS),
                         derived)

    def test_the_two_wander_rows_are_the_ones_this_round_read(self):
        rows = field_mob_ai_tables.AI_WANDER_ROWS
        # ~~two rows~~ three from round szdkgs: the practice dummy points at
        # AI_WANDER 21, mined here for the first time.
        self.assertEqual(sorted(rows), [AI_WANDER_OFFENSIVE_ROW,
                                        AI_WANDER_PASSIVE_ROW,
                                        AI_WANDER_DUMMY_ROW])
        _script, _faction, offensive, aggro = rows[AI_WANDER_OFFENSIVE_ROW]
        self.assertEqual((offensive, aggro), (1, MINED_AGGRO_RADIUS))
        _script, _faction, offensive, aggro = rows[AI_WANDER_PASSIVE_ROW]
        self.assertEqual((offensive, aggro), (0, 0))
        # !! The dummy's row CONTRADICTS its own MOBS row and that is the
        # measurement, not a defect of the mining: n_OFFESIVE 1 with
        # n_AGGRO 3000, on an actor whose n_AI_COMBAT is 0.  profile_of
        # resolves the contradiction downward (cannot initiate) and says so
        # at the branch; here we pin what the TABLE says, unresolved.
        _script, _faction, offensive, aggro = rows[AI_WANDER_DUMMY_ROW]
        self.assertEqual((offensive, aggro), (1, 3000))

    def test_no_wander_row_is_offensive_with_no_radius(self):
        # THE ONE DIRECTION THE TABLE SUPPORTS.  An earlier version of this
        # test asserted the biconditional - offensive if and only if a radius -
        # which EIGHT of the 73 shipped rows break (24, 40, 41, 46, 103, 110,
        # 9000, 9001 are non-offensive while carrying 500 to 5000).  It passed
        # only because it iterated the two rows bg0001 happens to use.  What
        # has no reading is the other direction: "charges, from nowhere".
        for identity, row in field_mob_ai_tables.AI_WANDER_ROWS.items():
            with self.subTest(row=identity):
                offensive, aggro = row[2], row[3]
                self.assertFalse(offensive and not aggro)

    def test_the_combat_rows_are_carried_verbatim_and_parsed_by_nobody(self):
        # "Nothing parses them" is a claim about CODE, so it is tested against
        # the code and not against the file's characters: the anchor comment
        # legitimately quotes DISTANCE_ENEMY<(275), and a substring search
        # would either pass vacuously or fail on prose.
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(".split(", source)
        self.assertNotIn("import re", source)
        tree = ast.parse(source)
        readers = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Attribute) and \
                            inner.attr == "AI_COMBAT_ROWS":
                        readers.append(node.name)
        # Exactly one function may touch the combat rows, and all it does is
        # assert the key exists.
        self.assertEqual(sorted(set(readers)), ["ai_rows_of"])
        for identity, row in field_mob_ai_tables.AI_COMBAT_ROWS.items():
            with self.subTest(row=identity):
                conditions, actions = row
                # An OBSERVATION about the nine rows this roster uses, not a
                # law of the table: six of the 276 shipped rows have
                # mismatched lengths and eight do not end with the default.
                # The generator RECORDS the answer per row rather than
                # refusing, and this pins that record against the rows.
                self.assertEqual(
                    field_mob_ai_tables.AI_COMBAT_PARALLEL[identity],
                    len(conditions.split("\\n")) == len(actions.split("\\n")))
                self.assertIs(
                    field_mob_ai_tables.AI_COMBAT_PARALLEL[identity], True)
                self.assertTrue(conditions.endswith("GO(0)"))

    def test_the_generated_module_is_ascii_and_cp874_safe(self):
        raw = (SRC_ROOT / "field_mob_ai_tables.py").read_text(encoding="utf-8")
        raw.encode("ascii")
        raw.encode("cp874")


class ProfileJoinTests(unittest.TestCase):
    """Two values mined, three ours, and every roster row buildable."""

    def setUp(self):
        self.roster = field_mobs.load_roster()
        self.by_placement = {m.placement_index: m for m in self.roster}

    def test_the_profile_of_every_roster_row_is_buildable(self):
        # Before this round the profile refused a zero aggro radius AND
        # required attack_range <= aggro_radius.  Either rule alone refuses
        # every passive monster in the roster, which is ten of thirteen.
        for mob in self.roster:
            with self.subTest(placement=mob.placement_index):
                built = profile_of(mob)
                self.assertIsInstance(built, mob_aggro.MobAiProfile)

    def test_ten_of_thirteen_bg0001_monsters_never_INITIATE(self):
        # Named for what the flag actually says.  The earlier name said "never
        # charge anybody", which overstates it: all ten passive placements
        # point at AI_COMBAT rows whose s_ACTION column is nothing but CHASE
        # lines.  They chase what hit them; they do not start it.
        offensive = [
            mob.placement_index for mob in self.roster
            if profile_of(mob).offensive
        ]
        self.assertEqual(tuple(offensive), OFFENSIVE_PLACEMENTS)
        self.assertEqual(len(self.roster) - len(offensive), 10)
        identities = mob_ai_control.offensive_identities(self.roster)
        self.assertEqual(
            identities,
            tuple(self.by_placement[p].actor_identity
                  for p in OFFENSIVE_PLACEMENTS))

    def test_the_two_mined_values_come_from_the_monsters_own_row(self):
        charging = profile_of(self.by_placement[58])
        passive = profile_of(self.by_placement[30])
        self.assertEqual(charging.aggro_radius, float(MINED_AGGRO_RADIUS))
        self.assertIs(charging.offensive, True)
        self.assertEqual(passive.aggro_radius, 0.0)
        self.assertIs(passive.offensive, False)

    def test_the_home_radius_is_the_monsters_own_walk_speed(self):
        for mob in self.roster:
            with self.subTest(placement=mob.placement_index):
                self.assertEqual(profile_of(mob).home_radius,
                                 float(mob.speed_walk))

    def test_the_three_invented_numbers_are_tagged_and_pinned(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        # COO-DECISION 2026-08-26T11:41+07:00 confirmed all four numbers, so
        # the live tag is CONFIRMED now; the old AWAITING-COO tag survives
        # exactly once, in the header's own past-tense account of that letter.
        self.assertEqual(
            source.count(
                "[LANE-B ASSUMPTION - CONFIRMED BY COO 2026-08-26T11:41+07:00]"
            ),
            5,
        )
        self.assertEqual(source.count("[LANE-B ASSUMPTION - AWAITING COO]"), 1)
        self.assertEqual(mob_ai_control.LEASH_RADIUS, 3000.0)
        self.assertEqual(mob_ai_control.MELEE_ATTACK_RANGE, 275.0)
        self.assertEqual(mob_ai_control.ATTACK_CADENCE_TICKS, 1)
        self.assertEqual(len(mob_ai_control.LANE_B_ASSUMPTIONS), 4)
        # The leash anchor is arithmetic, so it is checked rather than trusted.
        self.assertEqual(mob_ai_control.LEASH_RADIUS,
                         MINED_AGGRO_RADIUS * 2.5)
        # THE ATTACK RANGE HAS NO ANCHOR AND MUST NOT GROW ONE BACK.  The
        # first draft cited "the smallest DISTANCE_ENEMY< band"; that citation
        # was withdrawn because reading a skill-selection band as a melee reach
        # is the move this lane's own generator calls "an invention wearing a
        # table's clothes", and because "smallest" was a pin nothing could
        # re-derive without the parse the lane forbade itself.
        self.assertEqual(mob_ai_control.MELEE_ATTACK_RANGE_ANCHOR,
                         "NONE - a bare choice by lane B, see the comment")
        self.assertIn("WITHDRAWN",
                      mob_ai_control.MELEE_ATTACK_RANGE_WITHDRAWN_ANCHOR)
        self.assertNotIn("DISTANCE_ENEMY",
                         " ".join(mob_ai_control.LANE_B_ASSUMPTIONS))

    def test_a_monster_whose_ai_row_is_missing_is_refused_by_name(self):
        mob = self.by_placement[30]
        stranger = field_mobs.FieldMob(
            *(mob.placement_index, mob.template_id, mob.x, mob.y, mob.z,
              mob.visual_preset, mob.display_name, mob.level, mob.rank,
              9999, mob.ai_combat, mob.speed_walk, mob.max_hp,
              mob.drops_normal, mob.drops_equipment, mob.drops_specially))
        with self.assertRaises(MobAiControlError) as caught:
            profile_of(stranger)
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_AI_ROW_MISSING)


class RegisterTests(unittest.TestCase):
    def setUp(self):
        self.roster = field_mobs.load_roster()
        self.register = open_register(self.roster)

    def test_the_register_opens_one_idle_row_per_monster_at_its_placement(self):
        self.assertEqual(len(self.register.rows), len(self.roster))
        self.assertEqual(self.register.generation, 0)
        for mob in self.roster:
            state = self.register.state_of(mob.actor_identity)
            self.assertEqual(state.phase, mob_aggro.PHASE_IDLE)
            self.assertEqual(state.threat, ())
            self.assertEqual(state.leash_origin, (mob.x, mob.y, mob.z))

    def test_the_register_is_sorted_unique_and_never_mutated(self):
        identities = self.register.identities()
        self.assertEqual(list(identities), sorted(identities))
        self.assertEqual(len(set(identities)), len(identities))
        rows = self.register.rows
        with self.assertRaises(MobAiControlError) as caught:
            MobAiRegister(tuple(reversed(rows)))
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_REGISTER_NOT_SORTED)
        with self.assertRaises(MobAiControlError) as caught:
            MobAiRegister((rows[0], rows[0]))
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_DUPLICATE_REGISTER_IDENTITY)
        # the original is untouched by either attempt
        self.assertEqual(self.register.rows, rows)

    def test_opening_a_register_builds_every_profile_up_front(self):
        # An earlier draft validated only that the AI ROW existed, so a roster
        # whose mined radius contradicted one of this lane's invented numbers
        # opened cleanly and raised at the FIRST TICK - with a mob_aggro reason
        # that is not in this module's vocabulary.  Ten of the 73 shipped
        # AI_WANDER rows carry a radius above the old flat leash constant.
        for aggro in (5000, 8000):
            with self.subTest(aggro=aggro):
                self.assertGreater(
                    mob_ai_control.leash_radius_for(aggro), float(aggro))
        mob = self.roster[0]
        broken = field_mobs.FieldMob(
            *(mob.placement_index, mob.template_id, mob.x, mob.y, mob.z,
              mob.visual_preset, mob.display_name, mob.level, mob.rank,
              4242, mob.ai_combat, mob.speed_walk, mob.max_hp,
              mob.drops_normal, mob.drops_equipment, mob.drops_specially))
        with self.assertRaises(MobAiControlError) as caught:
            open_register((broken,))
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_AI_ROW_MISSING)
        self.assertIn(mob_ai_control.REFUSE_PROFILE_UNBUILDABLE,
                      mob_ai_control.MOB_AI_CONTROL_REFUSAL_REASONS)

    def test_an_untracked_identity_is_refused_by_name(self):
        with self.assertRaises(MobAiControlError) as caught:
            self.register.state_of(0x7FFF)
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_NOT_TRACKED)

    def test_a_typed_row_is_required_everywhere(self):
        for bad in ({"identity": 1}, None, 7):
            with self.subTest(bad=bad):
                with self.assertRaises(MobAiControlError) as caught:
                    MobAiRegister((bad,))
                self.assertEqual(caught.exception.reason,
                                 mob_ai_control.REFUSE_TYPE_NOT_TYPED_RECORD)
        with self.assertRaises(MobAiControlError) as caught:
            MobAiRow(1, "idle")
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_TYPE_NOT_TYPED_RECORD)


class ThreatFoldTests(unittest.TestCase):
    def setUp(self):
        self.roster = field_mobs.load_roster()
        self.register = open_register(self.roster)
        self.mob = self.roster[0]

    def test_the_threat_fold_hands_over_the_negative_wire_number(self):
        hit = outcome(self.mob.actor_identity, 964, self.mob.max_hp,
                      self.mob.max_hp)
        step = damage_step(self.register, hit)
        self.assertTrue(step.moved)
        self.assertEqual(step.after.threat, ((PLAYER, 964),))
        # The proof that it is the WIRE number and not the arithmetic one: the
        # positive value folds nothing, silently, and that is the bug.
        self.assertEqual(
            mob_aggro.apply_damage_threat(
                self.register.state_of(self.mob.actor_identity),
                PLAYER, hit.damage).threat,
            ())

    def test_threat_accumulates_across_hits_and_across_attackers(self):
        register = self.register
        for damage, attacker in ((100, PLAYER), (50, PLAYER),
                                 (70, SECOND_PLAYER)):
            step = damage_step(
                register,
                outcome(self.mob.actor_identity, damage, self.mob.max_hp,
                        self.mob.max_hp, attacker=attacker))
            register = commit_step(register, step)
        self.assertEqual(
            dict(register.state_of(self.mob.actor_identity).threat),
            {PLAYER: 150, SECOND_PLAYER: 70})
        self.assertEqual(register.generation, 3)

    def test_a_hit_that_moved_no_hp_folds_nothing_and_says_so(self):
        hit = outcome(self.mob.actor_identity, 0, 0, self.mob.max_hp,
                      no_room=True, clamped_by=964)
        step = damage_step(self.register, hit)
        self.assertFalse(step.moved)
        self.assertEqual(step.after.threat, ())
        self.assertIs(commit_step(self.register, step), self.register)

    def test_a_damage_step_needs_a_typed_outcome_and_a_typed_register(self):
        hit = outcome(self.mob.actor_identity, 10, self.mob.max_hp,
                      self.mob.max_hp)
        with self.assertRaises(MobAiControlError) as caught:
            damage_step(self.register, {"damage": 10})
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_TYPE_NOT_TYPED_RECORD)
        with self.assertRaises(MobAiControlError) as caught:
            damage_step(None, hit)
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_TYPE_NOT_TYPED_RECORD)


class DeathTests(unittest.TestCase):
    def setUp(self):
        self.roster = field_mobs.load_roster()
        self.register = open_register(self.roster)
        self.mob = self.roster[0]

    def killing(self):
        return outcome(self.mob.actor_identity, self.mob.max_hp,
                       self.mob.max_hp, self.mob.max_hp)

    def test_a_kill_retires_the_row_and_clears_the_table(self):
        pulled = commit_step(
            self.register,
            damage_step(self.register,
                        outcome(self.mob.actor_identity, 100, self.mob.max_hp,
                                self.mob.max_hp)))
        step = death_step(pulled, self.killing())
        retired = commit_step(pulled, step)
        state = retired.state_of(self.mob.actor_identity)
        self.assertEqual(state.phase, mob_aggro.PHASE_DEAD)
        self.assertEqual(state.threat, ())
        self.assertIsNone(state.target_identity)
        # and the leash origin survives, because a rebuild needs it
        self.assertEqual(state.leash_origin,
                         (self.mob.x, self.mob.y, self.mob.z))

    def test_a_dead_row_absorbs_no_further_threat(self):
        retired = commit_step(self.register,
                              death_step(self.register, self.killing()))
        step = damage_step(
            retired,
            outcome(self.mob.actor_identity, 0, 0, self.mob.max_hp,
                    no_room=True, clamped_by=10))
        self.assertFalse(step.moved)
        self.assertEqual(step.after.threat, ())

    def test_an_outcome_that_is_not_a_kill_is_refused_by_name(self):
        for hit in (
            outcome(self.mob.actor_identity, 1, self.mob.max_hp,
                    self.mob.max_hp),
            outcome(self.mob.actor_identity, 0, 0, self.mob.max_hp,
                    no_room=True, clamped_by=964),
        ):
            with self.subTest(no_room=hit.no_room):
                with self.assertRaises(MobAiControlError) as caught:
                    death_step(self.register, hit)
                self.assertEqual(caught.exception.reason,
                                 mob_ai_control.REFUSE_OUTCOME_IS_NOT_A_KILL)


class CompareAndSwapTests(unittest.TestCase):
    def setUp(self):
        self.roster = field_mobs.load_roster()
        self.register = open_register(self.roster)

    def test_two_players_hitting_two_monsters_in_one_tick_do_not_erase_each_other(self):
        first, second = self.roster[0], self.roster[1]
        left = damage_step(
            self.register,
            outcome(first.actor_identity, 100, first.max_hp, first.max_hp))
        right = damage_step(
            self.register,
            outcome(second.actor_identity, 200, second.max_hp, second.max_hp,
                    attacker=SECOND_PLAYER))
        stored = commit_step(self.register, left)
        with self.assertRaises(MobAiControlError) as caught:
            commit_step(stored, right)
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_REGISTER_STALE)
        # the retry, from a re-read register, keeps both
        redone = damage_step(
            stored,
            outcome(second.actor_identity, 200, second.max_hp, second.max_hp,
                    attacker=SECOND_PLAYER))
        both = commit_step(stored, redone)
        self.assertEqual(both.state_of(first.actor_identity).threat,
                         ((PLAYER, 100),))
        self.assertEqual(both.state_of(second.actor_identity).threat,
                         ((SECOND_PLAYER, 200),))

    def test_a_rebuild_of_the_same_roster_is_not_committed_over(self):
        # THE HOLE THE IDENTITY-SET GUARD COULD NOT SEE.  A rebuild is a second
        # open_register over the SAME monsters: same identity set, same
        # generation 0.  A step computed before the rebuild used to commit onto
        # it and discard the whole rebuild, silently.  The epoch is the
        # driver's obligation and the only thing that can tell them apart.
        before = open_register(self.roster, epoch=0)
        step = damage_step(
            before,
            outcome(self.roster[0].actor_identity, 100, self.roster[0].max_hp,
                    self.roster[0].max_hp))
        rebuilt = open_register(self.roster, epoch=1)
        self.assertEqual(set(before.identities()), set(rebuilt.identities()))
        self.assertEqual(before.generation, rebuilt.generation)
        with self.assertRaises(MobAiControlError) as caught:
            commit_step(rebuilt, step)
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_REGISTER_EPOCH_MISMATCH)
        # recomputed against the rebuild, it commits
        redone = damage_step(
            rebuilt,
            outcome(self.roster[0].actor_identity, 100, self.roster[0].max_hp,
                    self.roster[0].max_hp))
        self.assertEqual(commit_step(rebuilt, redone).epoch, 1)

    def test_a_step_from_another_lineage_of_the_same_length_is_refused(self):
        # A generation is a counter, not a value: two registers that have taken
        # the same NUMBER of steps carry the same generation while tracking
        # DIFFERENT monsters.  The earlier version of this test compared a
        # 3-row register against a 13-row one, so it only ever exercised a size
        # difference - replacing the identity-set guard with a length check
        # left it green.  These two are the same length and the same epoch.
        left = open_register(self.roster[:3])
        right = open_register(self.roster[1:4])
        self.assertEqual(len(left.rows), len(right.rows))
        self.assertEqual(left.epoch, right.epoch)
        self.assertNotEqual(set(left.identities()), set(right.identities()))
        shared = self.roster[1]
        stray = damage_step(
            left, outcome(shared.actor_identity, 5, shared.max_hp,
                          shared.max_hp))
        with self.assertRaises(MobAiControlError) as caught:
            commit_step(right, stray)
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_REGISTER_STALE)


class ReconcileTests(unittest.TestCase):
    """The repair for the wedge the prescribed order permits."""

    def setUp(self):
        from pirateforce_foundation import field_mobs as fm
        self.roster = fm.load_roster()
        self.register = open_register(self.roster)
        self.mob = self.roster[0]

    class FakeDeaths:
        def __init__(self, dead):
            self.dead = set(dead)

        def is_dead(self, identity):
            return identity in self.dead

        def identities(self):
            return tuple(sorted(self.dead))

    def test_a_row_the_death_register_calls_a_corpse_is_retired(self):
        # The wedge, reproduced: a driver that gives up on a refused
        # death_step has a monster that is a corpse in the death register and
        # IDLE with live threat here, with the HitOutcome already dropped.
        pulled = commit_step(
            self.register,
            damage_step(self.register,
                        outcome(self.mob.actor_identity, 100, self.mob.max_hp,
                                self.mob.max_hp)))
        self.assertEqual(pulled.state_of(self.mob.actor_identity).phase,
                         mob_aggro.PHASE_IDLE)
        # ...and the repair needs only the two registers.
        step = mob_ai_control.reconcile(
            pulled, self.FakeDeaths([self.mob.actor_identity]))
        repaired = commit_step(pulled, step)
        state = repaired.state_of(self.mob.actor_identity)
        self.assertEqual(state.phase, mob_aggro.PHASE_DEAD)
        self.assertEqual(state.threat, ())
        self.assertEqual(state.leash_origin,
                         (self.mob.x, self.mob.y, self.mob.z))

    def test_reconciling_a_register_that_already_agrees_moves_nothing(self):
        step = mob_ai_control.reconcile(self.register, self.FakeDeaths([]))
        self.assertFalse(step.moved)
        self.assertIs(commit_step(self.register, step), self.register)

    def test_reconcile_retires_every_corpse_in_one_committable_step(self):
        dead = [m.actor_identity for m in self.roster[:3]]
        step = mob_ai_control.reconcile(self.register, self.FakeDeaths(dead))
        repaired = commit_step(self.register, step)
        for identity in dead:
            self.assertEqual(repaired.state_of(identity).phase,
                             mob_aggro.PHASE_DEAD)
        for row in self.roster[3:]:
            self.assertEqual(
                repaired.state_of(row.actor_identity).phase,
                mob_aggro.PHASE_IDLE)

    def test_a_death_handle_missing_a_predicate_is_refused_by_name(self):
        for bad in (object(), None, {"is_dead": True}):
            with self.subTest(bad=type(bad).__name__):
                with self.assertRaises(MobAiControlError) as caught:
                    mob_ai_control.reconcile(self.register, bad)
                self.assertEqual(
                    caught.exception.reason,
                    mob_ai_control.REFUSE_DEATH_HANDLE_INCOMPLETE)

    def test_the_wiring_line_names_the_repair_and_both_retry_loops(self):
        line = mob_ai_control.MOB_AI_CONTROL_WIRING
        self.assertIn("reconcile", line)
        self.assertIn("AND LOOP ON REFUSE_REGISTER_STALE", line)
        self.assertIn("is_tracked", line)
        self.assertIn("epoch", line)


class ReconcileAgainstARealDeathRegisterTests(unittest.TestCase):
    """The same repair, but against ``mob_death.DeathRegister`` itself.

    Every ``ReconcileTests`` case above proves the repair against
    ``FakeDeaths``, a hand-written stand-in for the death-register handle
    ``reconcile()`` documents ("is_dead" and "identities", nothing else).
    That proves this module's OWN logic, but not that the handle it was
    designed for actually satisfies the contract - ``mob_death.DeathRegister``
    could drift (a rename, a different truthiness for an untracked identity)
    and every existing test here would stay green because none of them ever
    import ``mob_death``.  These tests import it and drive a REAL kill
    through ``mob_combat.strike`` -> ``mob_death.kill`` ->
    ``mob_death.commit_death``, exactly the order ``runtime.py`` uses, then
    hand the resulting real register to ``reconcile()`` with no Fake anywhere
    in the chain.

    The target has to be ``mob_death.SANCTIONED_FIRST_TARGET_IDENTITY``
    (placement 30, ``0x201F``, Tornado Eagle) rather than an arbitrary roster
    row: ``mob_death.kill()`` refuses every OTHER identity by name
    (``REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE``) until the roster-wide
    death gate is unlocked, and this test does not ask for that widening -
    it only needs ONE real corpse to prove the two registers agree.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = field_mobs.load_roster()
        cls.mob = [
            m for m in cls.roster
            if m.actor_identity == mob_death.SANCTIONED_FIRST_TARGET_IDENTITY
        ][0]

    def setUp(self):
        self.ai_register = open_register(self.roster)

    def _real_kill(self):
        """Drive one real, lethal hit all the way to a committed corpse."""
        combat_step = strike(
            self.legacy, None, open_ledger(), None, self.mob, PLAYER,
            Combatant(level=1000, ability_str=100000, ability_con=0),
        )
        self.assertTrue(combat_step.outcome.death_due)
        death_register = mob_death.DeathRegister()
        death_step_result = mob_death.kill(
            self.legacy, self.mob, combat_step.outcome, death_register)
        return mob_death.commit_death(death_register, death_step_result)

    def test_reconcile_retires_the_row_a_real_death_register_calls_dead(self):
        death_register = self._real_kill()
        self.assertTrue(death_register.is_dead(self.mob.actor_identity))
        # The AI side never ran its own death_step -- the exact wedge
        # reconcile() exists to repair (module header, section "THE ORDER").
        self.assertEqual(
            self.ai_register.state_of(self.mob.actor_identity).phase,
            mob_aggro.PHASE_IDLE)
        step = mob_ai_control.reconcile(self.ai_register, death_register)
        repaired = commit_step(self.ai_register, step)
        state = repaired.state_of(self.mob.actor_identity)
        self.assertEqual(state.phase, mob_aggro.PHASE_DEAD)
        self.assertEqual(state.threat, ())
        self.assertIsNone(state.target_identity)

    def test_reconcile_against_a_real_register_leaves_every_other_row_alone(self):
        death_register = self._real_kill()
        step = mob_ai_control.reconcile(self.ai_register, death_register)
        repaired = commit_step(self.ai_register, step)
        # The target row must actually be retired here too -- otherwise a
        # reconcile() that touches nobody would pass this test vacuously
        # (pf-adversary caught exactly this: "untouched" excluded the one
        # row this test exists to police).
        self.assertEqual(
            repaired.state_of(self.mob.actor_identity).phase,
            mob_aggro.PHASE_DEAD)
        untouched = [
            mob.actor_identity for mob in self.roster
            if mob.actor_identity != self.mob.actor_identity
        ]
        self.assertEqual(len(untouched), len(self.roster) - 1)
        for identity in untouched:
            self.assertEqual(
                repaired.state_of(identity).phase, mob_aggro.PHASE_IDLE)

    def test_reconciling_twice_against_the_same_real_register_is_idempotent(self):
        death_register = self._real_kill()
        once = commit_step(
            self.ai_register,
            mob_ai_control.reconcile(self.ai_register, death_register))
        # Idempotency is only a meaningful claim about a repair that
        # actually happened -- pf-adversary caught that a reconcile()
        # inverted to retire the WRONG row (or nobody at all) still passed
        # this test, because it never checked the first call was correct
        # before checking the second call was a no-op.
        self.assertEqual(
            once.state_of(self.mob.actor_identity).phase,
            mob_aggro.PHASE_DEAD)
        step = mob_ai_control.reconcile(once, death_register)
        self.assertFalse(step.moved)
        self.assertIs(commit_step(once, step), once)


class TickTests(unittest.TestCase):
    def setUp(self):
        self.roster = field_mobs.load_roster()
        self.by_placement = {m.placement_index: m for m in self.roster}
        self.register = open_register(self.roster)

    def observe(self, mob, players, hp=None):
        return mob_aggro.MobObservation(
            position=(mob.x, mob.y, mob.z),
            hp=mob.max_hp if hp is None else hp,
            players=tuple(players),
        )

    def player_at(self, mob, offset, identity=PLAYER):
        return mob_aggro.PlayerObservation(
            identity=identity,
            position=(mob.x + offset, mob.y, mob.z),
            alive=True,
        )

    def test_a_passive_monster_does_not_acquire_a_player_standing_on_it(self):
        mob = self.by_placement[30]
        step = tick_step(self.register, mob.actor_identity,
                         self.observe(mob, [self.player_at(mob, 0.0)]))
        self.assertEqual(step.after.phase, mob_aggro.PHASE_IDLE)
        self.assertEqual(step.after.threat, ())
        self.assertEqual(step.intent.kind, mob_aggro.INTENT_NONE)

    def test_a_charging_monster_acquires_inside_its_mined_radius(self):
        mob = self.by_placement[58]
        inside = tick_step(self.register, mob.actor_identity,
                           self.observe(mob, [self.player_at(
                               mob, float(MINED_AGGRO_RADIUS))]))
        self.assertEqual(inside.after.phase, mob_aggro.PHASE_AGGRO)
        self.assertEqual(inside.after.target_identity, PLAYER)
        outside = tick_step(self.register, mob.actor_identity,
                            self.observe(mob, [self.player_at(
                                mob, float(MINED_AGGRO_RADIUS) + 1.0)]))
        self.assertEqual(outside.after.phase, mob_aggro.PHASE_IDLE)
        self.assertEqual(outside.after.threat, ())

    def test_a_passive_monster_that_is_hit_answers(self):
        # The whole point of separating the flag from the radius: a monster
        # that acquires nobody by proximity still fights back.
        mob = self.by_placement[30]
        pulled = commit_step(
            self.register,
            damage_step(self.register,
                        outcome(mob.actor_identity, 964, mob.max_hp,
                                mob.max_hp)))
        step = tick_step(pulled, mob.actor_identity,
                         self.observe(mob, [self.player_at(mob, 100.0)]))
        self.assertEqual(step.after.phase, mob_aggro.PHASE_AGGRO)
        self.assertEqual(step.after.target_identity, PLAYER)
        # and inside the chosen melee reach the decision is an attack, which
        # this project still cannot deliver
        self.assertEqual(step.intent.kind,
                         mob_aggro.INTENT_ATTACK_UNDELIVERABLE)
        self.assertIs(mob_aggro.ATTACK_INTENT_DELIVERABLE, False)

    def test_a_tick_cannot_be_pointed_at_the_wrong_monsters_state(self):
        # A MobObservation carries no identity, so a signature taking the
        # roster row and the observation as two arguments would let a driver
        # pair them wrongly and never raise.  The register holds the row, the
        # tick takes an identity, and there is nothing left to pair.
        import inspect
        names = list(inspect.signature(tick_step).parameters)
        self.assertEqual(names, ["register", "actor_identity", "observation"])
        with self.assertRaises(MobAiControlError) as caught:
            tick_step(self.register, 0x7FFF,
                      self.observe(self.by_placement[30], []))
        self.assertEqual(caught.exception.reason,
                         mob_ai_control.REFUSE_NOT_TRACKED)

    def test_a_tick_is_deterministic_and_mutates_nothing(self):
        mob = self.by_placement[58]
        observation = self.observe(mob, [self.player_at(mob, 500.0)])
        first = tick_step(self.register, mob.actor_identity, observation)
        second = tick_step(self.register, mob.actor_identity, observation)
        self.assertEqual(first.after, second.after)
        self.assertEqual(first.intent, second.intent)
        self.assertEqual(self.register.generation, 0)


class DescribeAndPinTests(unittest.TestCase):
    def setUp(self):
        self.roster = field_mobs.load_roster()
        self.register = open_register(self.roster)
        self.mob = self.roster[0]

    def test_the_rendering_is_ascii_and_cp874_safe(self):
        step = damage_step(
            self.register,
            outcome(self.mob.actor_identity, 964, self.mob.max_hp,
                    self.mob.max_hp))
        for line in mob_ai_control.describe_step(step):
            line.encode("ascii")
            line.encode("cp874")
        self.assertTrue(any("threat|identity=%d" % PLAYER in line
                            for line in mob_ai_control.describe_step(step)))

    def test_a_dropped_fold_is_said_out_loud(self):
        retired = commit_step(
            self.register,
            death_step(self.register,
                       outcome(self.mob.actor_identity, self.mob.max_hp,
                               self.mob.max_hp, self.mob.max_hp)))
        step = damage_step(
            retired,
            outcome(self.mob.actor_identity, 0, 0, self.mob.max_hp,
                    no_room=True, clamped_by=5))
        lines = mob_ai_control.describe_step(step)
        self.assertTrue(any("threat NOT recorded" in line for line in lines))

    def test_the_committed_pin_is_what_the_code_computes(self):
        committed = json.loads(
            (ROOT / "scenarios/combat_aggro_001.json").read_bytes()
            .decode("ascii"))
        self.assertEqual(committed, mob_ai_control.pin_document(self.roster))

    def test_the_pin_is_regenerable_and_says_by_what(self):
        # The pin stores all four invented numbers, once per monster.  A COO
        # letter that calls a rollback "one constant and one test line" is
        # wrong unless something rewrites this file.
        self.assertTrue(
            (ROOT / "tools/pf_write_mob_ai_pin.py").is_file(),
            "the pin generator is missing; the rollback claim is false again")
        committed = json.loads(
            (ROOT / "scenarios/combat_aggro_001.json").read_bytes()
            .decode("ascii"))
        self.assertEqual(committed["regenerated_by"],
                         mob_ai_control.PIN_REGENERATION_COMMAND)
        self.assertIn("pf_write_mob_ai_pin.py",
                      mob_ai_control.PIN_REGENERATION_COMMAND)

    def test_the_pin_carries_the_markers_its_siblings_carry(self):
        committed = json.loads(
            (ROOT / "scenarios/combat_aggro_001.json").read_bytes()
            .decode("ascii"))
        self.assertEqual(committed["schema"], 1)
        self.assertIs(committed["not_a_scenario"], True)
        self.assertIs(committed["test_only"], False)

    def test_the_pin_says_what_is_mined_and_what_is_ours(self):
        pin = mob_ai_control.pin_document(self.roster)
        self.assertEqual(tuple(pin["mined_values"]),
                         ("aggro_radius", "offensive"))
        self.assertEqual(len(pin["lane_b_assumptions"]), 4)
        self.assertIs(pin["attack_intent_deliverable"], False)
        self.assertIs(pin["mob_aggro_dispatch_reachable"], False)
        self.assertIs(pin["mob_aggro_production_allowed"], True)


class ContainmentTests(unittest.TestCase):
    """No flag, no clock, no wire, no database - and nothing dispatches it."""

    def setUp(self):
        self.source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_the_module_is_ascii_and_cp874_safe(self):
        self.source.encode("ascii")
        self.source.encode("cp874")

    def test_the_module_has_no_flag_no_scenario_id_and_no_unlock(self):
        self.assertIs(mob_ai_control.production_allowed, True)
        # No gate of any shape: no scenario id constant, no unlock object, no
        # dispatch kwarg.  The word "scenario" appears twice in prose (the pin
        # this lane writes, and the sentence saying there is no scenario id),
        # so the check is on CODE, not on the file's characters.
        assignments = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                assignments.add(node.id)
        for banned in ("SCENARIO_ID", "SCENARIO", "UNLOCK", "scenario_id",
                       "unlock"):
            self.assertNotIn(banned, assignments)
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                argnames = [a.arg for a in node.args.args
                            + node.args.kwonlyargs]
                for bad in ("scenario", "unlock", "enable", "enabled"):
                    self.assertNotIn(bad, argnames, node.name)

    def test_the_module_never_imports_a_clock_randomness_a_socket_or_a_db(self):
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        for banned in ("random", "time", "datetime", "secrets", "socket",
                       "sqlite3", "os", "pathlib"):
            self.assertNotIn(banned, imported)

    def test_the_module_has_no_import_time_side_effects(self):
        allowed = (
            ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
            ast.ClassDef, ast.FunctionDef,
        )
        for node in self.tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value,
                                                         ast.Constant):
                continue
            self.assertIsInstance(node, allowed)

    def test_it_imports_the_promoted_lane_by_name_not_as_a_handle(self):
        # The whole point of the promotion: the edge is an import a scan can
        # see, not an argument it cannot.
        modules = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                modules.add(node.module or "")
                modules.update(alias.name for alias in node.names)
        self.assertIn("mob_aggro", modules)
        self.assertIs(mob_aggro.production_allowed, True)
        self.assertEqual(mob_aggro.MOB_AGGRO_IMPORTER, "mob_ai_control")

    def test_exactly_runtime_dispatches_this_lane_now(self):
        # CORE-REQUEST-007 wired this module into runtime.py.  This used to
        # be a tripwire asserting the OPPOSITE (nothing imports it); now that
        # the chief has written the call, the tripwire is on the other side:
        # exactly ONE file imports it, and it is the one MOB_AI_CONTROL_
        # WIRING named.  A second importer, or app.py picking it up directly,
        # would mean the request was answered twice or in the wrong file.
        importers = []
        for path in sorted(SRC_ROOT.glob("*.py")):
            if path.name == "mob_ai_control.py":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] + [
                        alias.name for alias in node.names]
                if any("mob_ai_control" in name for name in names):
                    importers.append(path.name)
        self.assertEqual(sorted(set(importers)), ["runtime.py"],
                         "exactly runtime.py should import this lane")
        app_body = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("mob_ai_control", app_body,
                         "runtime.py owns this wiring, not app.py")
        self.assertIn("runtime.py", mob_ai_control.MOB_AI_CONTROL_WIRING)
        self.assertIn("CORE-REQUEST-007",
                      mob_ai_control.MOB_AI_CONTROL_NONCLAIMS[0])

    def test_the_wiring_line_orders_the_two_commits(self):
        line = mob_ai_control.MOB_AI_CONTROL_WIRING
        self.assertLess(line.index("mob_combat.commit_step"),
                        line.index("damage_step"))
        self.assertLess(line.index("mob_death.commit_death"),
                        line.index("death_step"))
        self.assertIn("do NOT re-run mob_combat.strike", line)

    def test_the_promotion_ruling_is_cited_where_a_reader_lands(self):
        self.assertIn("COO-DECISION 2026-08-26T04:02+07:00",
                      mob_ai_control.MOB_AI_CONTROL_PROMOTION_RULING)
        aggro_source = (SRC_ROOT / "mob_aggro.py").read_text(encoding="utf-8")
        self.assertIn("COO-DECISION 2026-08-26T04:02+07:00", aggro_source)


if __name__ == "__main__":
    unittest.main()
