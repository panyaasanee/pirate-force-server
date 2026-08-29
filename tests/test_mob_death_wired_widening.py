"""LANE-B / round j0u64p: one kill site, the right letter for every scene.

WHAT THIS FILE IS ABOUT.  ``runtime.py``'s ROSTER kill site -- the
``mob_death.kill()`` call in the ``else`` branch at ~4168, which every field
monster dies through -- hardcodes ONE ruling string, bg0001's.  The server
ships a second scene, so that literal is the wrong letter for 17 of the 21
monsters it ships, and the day a third scene lands it is the wrong letter
again.  ``mob_death.ruling_for(mob)`` answers what a literal cannot.

There is a SECOND kill site (the diagnostic branch, through
``diag_multi_object_wiring.death_dispatch``), which carries its own ruling on
its own stated design position and is no business of this round's.  "One call
site" was the first draft's phrasing and it was wrong.

WHAT THIS ROUND IS NOT, stated first because its first draft got it wrong and
pf-adversary broke it by execution:

  * The death gate was NOT broken.  ``kill()`` already authorised every
    monster the server ships -- the Bg0002 letter has been registered since
    round y7koj9 and covers all 17 of that scene's rows, each under its own
    correct string.  What holds "kill() is untouched" is the diff plus a full
    old-vs-new behavioural differential;
    ``test_the_gate_still_takes_one_string_and_nothing_else`` narrows it to
    every container shape a caller might reach for.
  * A Bg0002 monster does NOT "reach 0 HP and keep standing".  It is refused
    two layers earlier, at ``mob_combat``'s ``target_not_in_ledger``, because
    ``runtime.py:3911`` loads only bg0001's roster -- so no hit lands on it at
    all.  ``test_the_first_wall_is_in_mob_combat_not_in_this_module`` pins that, so
    this file cannot be read as claiming a symptom it never saw.

The load-bearing test is ``test_every_shipped_mob_dies_under_the_letter_
ruling_for_names``: walk the REAL rosters of every live scene, kill each row
under the letter this module names for it, and require all of them to die.
"""

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs, mob_combat, mob_death
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_combat import Combatant, open_ledger, strike
from pirateforce_foundation.mob_death import (
    DeathRegister,
    MobDeathContractError,
    kill,
    ruling_for,
    rulings_covering,
)


PERFORMER = 0x750059
LETHAL = Combatant(level=1000, ability_str=100000, ability_con=0)

# The value runtime.py's kill site passes TODAY, quoted so the measurement
# below is against the real call site and not a convenient stand-in.
RUNTIME_CALL_SITE_LITERAL = "COO-RULING-20260827-1350 widen-death-scope-bg0001"


class RulingForTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def lethal_outcome(self, mob):
        """A killing blow on ``mob`` through a ledger opened on itself.

        The default ledger only knows bg0001's roster, so every subject here
        gets a one-mob ledger -- the same shape test_mob_death's own
        killing_outcome_solo uses for its off-roster subjects.
        """
        return strike(
            self.legacy, None, open_ledger((mob,)), None, mob, PERFORMER,
            LETHAL).outcome

    def stand_in(self, *, template_id, scene, placement_index=9401,
                 display_name="STAND-IN"):
        """A FieldMob built to reach a branch no shipped row reaches.

        Every field except the three under test is copied from a real shipped
        row, so a stand-in cannot pass or fail for a reason this file is not
        about.
        """
        real = field_mobs.load_roster()[0]
        return field_mobs.FieldMob(
            placement_index=placement_index,
            template_id=template_id,
            x=real.x, y=real.y, z=real.z,
            visual_preset=real.visual_preset,
            display_name=display_name,
            level=real.level, rank=real.rank, ai_wander=real.ai_wander,
            ai_combat=real.ai_combat, speed_walk=real.speed_walk,
            max_hp=real.max_hp, drops_normal=0, drops_equipment=0,
            drops_specially=0, scene=scene,
        )

    def shipped(self):
        rows = [
            (scene, mob)
            for scene in field_mobs.live_scenes()
            for mob in field_mobs.load_roster(scene=scene)
        ]
        # NON-VACUITY, and it guards every loop in this file rather than one
        # of them (pf-adversary, this round: three tests here stayed green
        # with every owner letter revoked, because their loops ran zero
        # times).  A floor, not a pin: rosters are allowed to grow.
        self.assertGreaterEqual(len(rows), 21, "the shipped rosters shrank")
        self.assertGreaterEqual(len(field_mobs.live_scenes()), 2)
        self.assertGreaterEqual(len(mob_death.WIDENING_RULINGS), 4)
        return rows

    # -- what the round delivers -----------------------------------------

    def test_every_shipped_mob_dies_under_the_letter_ruling_for_names(self):
        for scene, mob in self.shipped():
            with self.subTest(scene=scene, identity=hex(mob.actor_identity)):
                step = kill(
                    self.legacy, mob, self.lethal_outcome(mob),
                    DeathRegister(), widened=ruling_for(mob))
                # is_dead is asked WITH the mob's own scene; its default is
                # bg0001, so omitting it reads False for every Bg0002 corpse.
                self.assertTrue(
                    step.register.is_dead(mob.actor_identity, mob.scene))

    def test_the_literal_the_call_site_hardcodes_is_the_wrong_letter(self):
        # The honest before-measurement.  NOT "these monsters cannot die" --
        # each of them dies under its own letter, as the test above shows.
        # What is measured here is that ONE hardcoded literal cannot be the
        # right letter for a world with more than one scene.
        # A mob the literal does not COVER is refused outright.  A mob it
        # covers is killed by it -- bg0001's four dummies are covered by both
        # bg0001 letters, so the literal works for them and only the letter a
        # kill travels UNDER differs.  Both halves are asserted, because
        # "17 of 21 are refused" and "the literal is wrong for all of them"
        # are different claims and only the first one is true.
        refused = killed = 0
        for scene, mob in self.shipped():
            covered = RUNTIME_CALL_SITE_LITERAL in rulings_covering(mob)
            with self.subTest(scene=scene, identity=hex(mob.actor_identity)):
                if covered:
                    killed += 1
                    step = kill(
                        self.legacy, mob, self.lethal_outcome(mob),
                        DeathRegister(), widened=RUNTIME_CALL_SITE_LITERAL)
                    self.assertTrue(
                        step.register.is_dead(mob.actor_identity, mob.scene))
                    continue
                refused += 1
                with self.assertRaises(MobDeathContractError) as caught:
                    kill(
                        self.legacy, mob, self.lethal_outcome(mob),
                        DeathRegister(), widened=RUNTIME_CALL_SITE_LITERAL)
                self.assertEqual(
                    caught.exception.reason,
                    mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)
        # Floors with a reason rather than bare numbers, so a roster edit does
        # not fail this test for something it is not about.
        self.assertGreaterEqual(
            refused, 17,
            "the hardcoded literal is supposed to be the wrong letter for at "
            "least Bg0002's whole roster")
        self.assertGreaterEqual(
            killed, 4,
            "the literal still has to work for the scene it names, or this "
            "round would be describing a regression instead of a hardcode")

    def test_the_gate_still_takes_one_string_and_nothing_else(self):
        # This round deliberately did NOT widen kill().  Its first draft did
        # -- it taught widened= to accept a sequence of names -- and
        # pf-adversary showed the gate had never been the constraint.
        #
        # WHAT ESTABLISHES "kill() is untouched" IS THE DIFF AND A FULL
        # OLD-VS-NEW DIFFERENTIAL, not this test (pf-adversary, this round:
        # the first version passed one tuple, so the same widening re-landed
        # as a frozenset would have gone straight past it).  What this test
        # does is narrower and worth having on its own terms: every container
        # shape a caller might reach for is refused, and the refusal is still
        # the one that names the sequencing ruling.
        _scene, mob = self.shipped()[0]
        name = ruling_for(mob)
        self.assertIsInstance(name, str)
        outcome = self.lethal_outcome(mob)
        for value in (
            (name,), [name], {name}, frozenset({name}), iter([name]),
            (n for n in (name,)), {name: 1}, [[name]], bytes(name, "ascii"),
        ):
            with self.subTest(shape=type(value).__name__):
                with self.assertRaises(MobDeathContractError) as caught:
                    kill(
                        self.legacy, mob, outcome, DeathRegister(),
                        widened=value)
                self.assertEqual(
                    caught.exception.reason,
                    mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)
                self.assertIn(
                    mob_death.SANCTIONING_RULING, caught.exception.detail)
        # and the bare string it has always taken still works
        step = kill(
            self.legacy, mob, outcome, DeathRegister(), widened=name)
        self.assertTrue(step.register.is_dead(mob.actor_identity, mob.scene))

    def test_the_first_wall_is_in_mob_combat_not_in_this_module(self):
        # Why this round changes nothing a player sees, pinned so no reader of
        # this file mistakes a mob_death fact for a client-observable one.  A
        # Bg0002 monster never reaches 0 HP: runtime.py loads bg0001's roster,
        # so mob_combat refuses the target before mob_death is ever consulted.
        bg0002 = field_mobs.load_roster(scene=field_mobs.BG0002_SCENE)
        self.assertTrue(bg0002)
        runtime_roster = field_mobs.load_roster()   # runtime.py:3911, verbatim
        runtime_ledger = open_ledger()              # runtime.py:1119, verbatim
        for mob in bg0002:
            with self.subTest(identity=hex(mob.actor_identity)):
                self.assertNotIn(mob.actor_identity,
                                 {m.actor_identity for m in runtime_roster})
                with self.assertRaises(mob_combat.MobCombatContractError) as c:
                    strike(
                        self.legacy, None, runtime_ledger, None, mob,
                        PERFORMER, LETHAL)
                self.assertEqual(
                    c.exception.reason, mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    # -- the derivation ---------------------------------------------------

    def test_ruling_for_is_derived_and_every_answer_is_a_real_letter(self):
        for scene, mob in self.shipped():
            with self.subTest(scene=scene, identity=hex(mob.actor_identity)):
                name = ruling_for(mob)
                self.assertIn(name, mob_death.WIDENING_RULINGS)
                # derived, not typed in: the letter it names must be one that
                # genuinely covers this mob on both axes
                self.assertIn(name, rulings_covering(mob))

    def test_the_narrower_letter_wins_and_it_is_the_one_the_pin_uses(self):
        # bg0001's dummies are covered by TWO letters.  A kill travels under
        # exactly one, and the rule (smallest covered set, ties by sorted
        # name) has to reproduce the answer the tree already gave in
        # PIN_WIDENING_RULING rather than invent a second one.
        bg0001 = field_mobs.load_roster()
        self.assertTrue(bg0001)
        for mob in bg0001:
            with self.subTest(identity=hex(mob.actor_identity)):
                self.assertGreaterEqual(
                    len(rulings_covering(mob)), 2,
                    "this test is about a mob two letters cover")
                self.assertEqual(ruling_for(mob), mob_death.PIN_WIDENING_RULING)

    def test_the_tie_break_is_the_rule_it_claims_to_be(self):
        # pf-adversary, this round: "the narrower letter wins" was decorative.
        # bg0001's two letters BOTH carry frozenset({916}) at HEAD, so the len
        # term separated nothing, and two mutants survived -- dropping len
        # entirely, and reversing it so the WIDER letter wins.  The rule is
        # therefore exercised on registered stand-in letters, where the two
        # terms can be told apart, and both terms are pinned separately.
        bg0001 = field_mobs.load_roster()[0]
        previous = dict(mob_death.WIDENING_RULINGS)
        try:
            # (1) a WIDER letter, whose name sorts FIRST, must still lose --
            #     this fails under sorted(covering)[0] and under a reversed
            #     len term alike.
            mob_death.WIDENING_RULINGS["AAA test-only wide letter"] = (
                frozenset({916, 31, 34, 35}))
            self.assertEqual(
                ruling_for(bg0001), mob_death.PIN_WIDENING_RULING,
                "a wider letter sorting first took the kill: the len term is "
                "not deciding")
            # (2) an EQUALLY narrow letter whose name sorts first must win --
            #     that is the tie-break, and it is the term that actually
            #     decides at HEAD.
            mob_death.WIDENING_RULINGS["AAA test-only narrow letter"] = (
                frozenset({916}))
            self.assertEqual(
                ruling_for(bg0001), "AAA test-only narrow letter")
        finally:
            mob_death.WIDENING_RULINGS.clear()
            mob_death.WIDENING_RULINGS.update(previous)
        self.assertEqual(ruling_for(bg0001), mob_death.PIN_WIDENING_RULING)

    def test_a_monster_no_letter_covers_is_refused_not_given_some_letter(self):
        # Fail-closed.  The tempting bug is to return the first registered
        # ruling, or None, and let kill() sort it out -- None is the
        # SANCTIONED path, so that would hand a free kill to a monster nobody
        # authorised.
        bg0001 = field_mobs.load_roster()[0]
        stranger = field_mobs.FieldMob(
            placement_index=9401,
            template_id=4242,
            x=bg0001.x, y=bg0001.y, z=bg0001.z,
            visual_preset=bg0001.visual_preset,
            display_name="TEMPLATE NO LETTER NAMES",
            level=bg0001.level, rank=bg0001.rank,
            ai_wander=bg0001.ai_wander, ai_combat=bg0001.ai_combat,
            speed_walk=bg0001.speed_walk, max_hp=bg0001.max_hp,
            drops_normal=0, drops_equipment=0, drops_specially=0,
            scene=bg0001.scene,
        )
        self.assertNotIn(
            4242,
            {t for s in mob_death.WIDENING_RULINGS.values() for t in s})
        self.assertEqual(rulings_covering(stranger), ())
        with self.assertRaises(MobDeathContractError) as caught:
            ruling_for(stranger)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)
        self.assertIn("4242", caught.exception.detail)

    def test_the_sanctioned_target_needs_no_letter_and_is_told_so(self):
        # widened=ruling_for(mob) has to be the correct argument for EVERY
        # mob, so a caller never needs a special case.  For the sanctioned
        # first target in its own scene, kill() wants None, and that is what
        # this returns -- and the kill goes through with it.
        bg0001 = field_mobs.load_roster()[0]
        sanctioned = field_mobs.FieldMob(
            placement_index=mob_death.SANCTIONED_FIRST_TARGET_IDENTITY
            - 0x2000 - 1,
            template_id=4242,
            x=bg0001.x, y=bg0001.y, z=bg0001.z,
            visual_preset=bg0001.visual_preset,
            display_name="THE SANCTIONED FIRST TARGET",
            level=bg0001.level, rank=bg0001.rank,
            ai_wander=bg0001.ai_wander, ai_combat=bg0001.ai_combat,
            speed_walk=bg0001.speed_walk, max_hp=bg0001.max_hp,
            drops_normal=0, drops_equipment=0, drops_specially=0,
            scene=mob_death.SANCTIONED_FIRST_TARGET_SCENE,
        )
        self.assertEqual(
            sanctioned.actor_identity,
            mob_death.SANCTIONED_FIRST_TARGET_IDENTITY)
        # no letter covers its template; the bypass is what admits it
        self.assertEqual(rulings_covering(sanctioned), ())
        self.assertIsNone(ruling_for(sanctioned))
        step = kill(
            self.legacy, sanctioned, self.lethal_outcome(sanctioned),
            DeathRegister(), widened=ruling_for(sanctioned))
        self.assertTrue(
            step.register.is_dead(
                sanctioned.actor_identity, sanctioned.scene))

    def test_the_derivation_and_the_gate_agree_on_every_shipped_mob(self):
        # rulings_covering() is a SECOND expression of the two questions
        # kill() asks, because kill() has to walk the rulings itself to say
        # which letter declined.  Two expressions of one rule drift; this
        # holds them to the same answer by execution.  The sanctioned
        # identity is EXCLUDED BY NAME, not by luck: kill() admits it with no
        # letter at all, so the two would legitimately disagree there.
        checked = 0
        for scene, mob in self.shipped():
            if (mob.actor_identity
                    == mob_death.SANCTIONED_FIRST_TARGET_IDENTITY
                    and mob.scene == mob_death.SANCTIONED_FIRST_TARGET_SCENE):
                continue
            outcome = self.lethal_outcome(mob)
            covering = rulings_covering(mob)
            for name in mob_death.WIDENING_RULINGS:
                checked += 1
                with self.subTest(
                        identity=hex(mob.actor_identity), ruling=name[:40]):
                    try:
                        kill(
                            self.legacy, mob, outcome, DeathRegister(),
                            widened=name)
                    except MobDeathContractError:
                        gate_says_yes = False
                    else:
                        gate_says_yes = True
                    self.assertEqual(gate_says_yes, name in covering)
        self.assertGreaterEqual(checked, 21 * 4)

    def test_live_scenes_is_the_list_load_roster_actually_obeys(self):
        # SET EQUALITY against the registry itself, not "everything it returns
        # loads" (pf-adversary, this round: the weaker version let a
        # registered scene be DROPPED from live_scenes() with the whole file
        # still green -- and describe_widening_coverage would then omit that
        # scene's entire roster, unkillable rows included, with a scope line
        # giving the wrong reason for the omission).
        scenes = field_mobs.live_scenes()
        self.assertEqual(
            set(scenes), set(field_mobs._SCENE_TABLE_MODULES),
            "live_scenes() has drifted from the registry load_roster obeys")
        self.assertEqual(scenes, tuple(sorted(scenes)))
        self.assertGreaterEqual(len(scenes), 2)
        for scene in scenes:
            self.assertTrue(field_mobs.load_roster(scene=scene))
        with self.assertRaises(field_mobs.FieldMobContractError):
            field_mobs.load_roster(scene="no-such-scene")

    def test_the_scene_axis_of_rulings_covering_is_actually_exercised(self):
        # pf-adversary, this round: the scene branch of rulings_covering never
        # fires on the live rosters -- no shipped row's template appears in a
        # letter tied to a different scene -- so deleting that branch left the
        # whole file green.  The crossing over shipped rows cannot reach it,
        # so it is reached HERE, on constructed rows, and both directions are
        # asserted: covered when the scene matches, dropped when it does not.
        bg2_letter = (
            "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
            "widen-death-scope-bg0002"
        )
        self.assertEqual(
            mob_death.WIDENING_RULING_SCENES[bg2_letter],
            field_mobs.BG0002_SCENE)
        template = sorted(mob_death.WIDENING_RULINGS[bg2_letter])[0]
        for scene, expected in (
            (field_mobs.BG0002_SCENE, True),
            (field_mobs.load_roster()[0].scene, False),
            ("some-third-scene", False),
        ):
            with self.subTest(scene=scene):
                mob = self.stand_in(template_id=template, scene=scene)
                self.assertEqual(bg2_letter in rulings_covering(mob), expected)
                # and the gate itself agrees, which is the whole point of
                # having a second expression of the rule at all
                try:
                    kill(
                        self.legacy, mob, self.lethal_outcome(mob),
                        DeathRegister(), widened=bg2_letter)
                except MobDeathContractError:
                    gate_says_yes = False
                else:
                    gate_says_yes = True
                self.assertEqual(gate_says_yes, expected)

    # -- the report -------------------------------------------------------

    def test_the_coverage_report_names_a_monster_no_letter_covers(self):
        # G-OBS.  Round szdkgs shipped four unkillable dummies and the suite
        # stayed green, so "nothing covers this row" has to be sayable by
        # identity.  Counts are DERIVED from the roster, so a roster edit
        # changes what this expects instead of failing it for the wrong
        # reason.
        bg0002 = len(field_mobs.load_roster(scene=field_mobs.BG0002_SCENE))
        self.assertGreater(bg0002, 0)
        healthy = mob_death.describe_widening_coverage()
        self.assertFalse([ln for ln in healthy if "UNKILLABLE" in ln])
        self.assertTrue([
            ln for ln in healthy
            if "scene=%s letter_covers=%d of %d" % (
                field_mobs.BG0002_SCENE, bg0002, bg0002) in ln])
        # the scope line: this report covers live scenes and says so, rather
        # than reading as "there is nothing else"
        self.assertTrue([ln for ln in healthy if "scope=live_scenes(" in ln])
        previous = dict(mob_death.WIDENING_RULINGS)
        try:
            mob_death.WIDENING_RULINGS.pop(
                "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
                "widen-death-scope-bg0002")
            broken = mob_death.describe_widening_coverage()
        finally:
            # clear+update, not rebinding: any module that did
            # ``from mob_death import WIDENING_RULINGS`` holds this same dict
            mob_death.WIDENING_RULINGS.clear()
            mob_death.WIDENING_RULINGS.update(previous)
        self.assertEqual(
            len([ln for ln in broken if "UNKILLABLE" in ln]), bg0002)
        self.assertTrue([
            ln for ln in broken
            if "scene=%s letter_covers=0 of %d" % (
                field_mobs.BG0002_SCENE, bg0002) in ln])
        self.assertEqual(mob_death.describe_widening_coverage(), healthy)

    def test_the_report_encodes_to_the_console_this_project_actually_has(self):
        # G-OBS again: the bridge console is cp874.  A line that cannot be
        # encoded is a line nobody reads, and a display_name mined from the
        # game tables is not this lane's choice of characters.
        #
        # THE HEALTHY REPORT IS NOT THE TEST (pf-adversary, this round): the
        # only line that interpolates a display_name is the UNKILLABLE one,
        # which the healthy report never emits -- so the first version of this
        # test stayed green with an un-encodable name planted in a shipped
        # row, and the report would have died mid-emission in exactly the
        # state it exists for.  Both states are encoded here, and the
        # un-encodable-name case is the one that matters.
        for line in mob_death.describe_widening_coverage():
            line.encode("cp874")
        previous = dict(mob_death.WIDENING_RULINGS)
        try:
            mob_death.WIDENING_RULINGS.clear()
            broken = mob_death.describe_widening_coverage()
        finally:
            mob_death.WIDENING_RULINGS.clear()
            mob_death.WIDENING_RULINGS.update(previous)
        named = [ln for ln in broken if "UNKILLABLE" in ln]
        self.assertGreaterEqual(len(named), 21)
        for line in broken:
            line.encode("cp874")


if __name__ == "__main__":
    unittest.main()
