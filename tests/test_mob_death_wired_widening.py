"""LANE-B / round j0u64p: one kill site, every scene the server ships.

WHAT THIS FILE IS ABOUT, IN ONE SENTENCE.  ``runtime.py`` reaches
``mob_death.kill()`` from ONE call site for every monster that dies, and that
call site passes ONE owner ruling by name -- bg0001's.  The server now ships a
second scene.  Measured before a line of this round was written: all 17 Bg0002
monsters were refused a death by that single string, so a player fighting one
in Prison Exile takes it to 0 HP and it never falls.

``test_every_shipped_mob_dies_through_one_widened_value`` is the load-bearing
test here.  It walks the REAL rosters of every live scene, kills each row
through the single value ``wired_widening_rulings()`` produces, and requires
all of them to die.  On the tree this round started from it fails 17 times.

The other tests exist because the fix is a widening of a GATE, and a widened
gate is exactly where this project has been bitten before (pf-adversary, round
67jejl: an unregistered ruling name used to authorise a kill).  So they attack
the widening rather than demonstrate it: a mistranscribed name riding along
beside a correct one, an empty sequence, two rulings whose halves would
authorise a mob neither covers on its own.
"""

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs, mob_death
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_combat import Combatant, open_ledger, strike
from pirateforce_foundation.mob_death import (
    DeathRegister,
    MobDeathContractError,
    kill,
    wired_widening_rulings,
)


PERFORMER = 0x750059
LETHAL = Combatant(level=1000, ability_str=100000, ability_con=0)

WIDENED_916_RULING = (
    "COO-DECISION widen-death-scope-916-training-iron-man "
    "2026-08-27T09:55+07:00 (ref PANYA-DECISION 2026-08-27T09:50+07:00 "
    "section 3, supersedes COO 0954)"
)
WIDENED_BG0001_RULING = "COO-RULING-20260827-1350 widen-death-scope-bg0001"
WIDENED_BG0002_RULING = (
    "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
    "widen-death-scope-bg0002"
)
# The value ``runtime.py``'s kill site passes TODAY, quoted here so the
# before/after measurement below is against the real call site and not against
# a convenient stand-in.
RUNTIME_CALL_SITE_VALUE_BEFORE_THIS_ROUND = WIDENED_BG0001_RULING


class WiredWideningTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def lethal_outcome(self, mob):
        """A killing blow on ``mob`` through a one-mob ledger.

        Every subject in this file is loaded from its own scene's roster, and
        the default ledger only knows bg0001's, so each mob gets a ledger
        opened on itself -- the same shape test_mob_death.killing_outcome_solo
        uses for its off-roster subjects.
        """
        return strike(
            self.legacy, None, open_ledger((mob,)), None, mob, PERFORMER,
            LETHAL).outcome

    def shipped_mobs(self):
        for scene in field_mobs.live_scenes():
            for mob in field_mobs.load_roster(scene=scene):
                yield scene, mob

    # -- the measurement -------------------------------------------------

    def test_every_shipped_mob_dies_through_one_widened_value(self):
        # THE round's claim, stated as the thing a player would notice: every
        # monster this server ships, in every scene it ships, falls when it is
        # beaten -- through ONE value, because there is only one kill site.
        wired = wired_widening_rulings()
        shipped = list(self.shipped_mobs())
        # Guard the guard: a roster that silently emptied would make the loop
        # below vacuously green, which is the failure mode round 149wbp's own
        # note warns about ("a loop that runs zero times is always green").
        self.assertGreaterEqual(len(shipped), 21, "the shipped rosters shrank")
        self.assertGreaterEqual(
            len(field_mobs.live_scenes()), 2,
            "this test is about more than one scene reaching one kill site")
        for scene, mob in shipped:
            with self.subTest(scene=scene, identity=hex(mob.actor_identity)):
                step = kill(
                    self.legacy, mob, self.lethal_outcome(mob),
                    DeathRegister(), widened=wired)
                # is_dead is asked WITH the mob's own scene.  Its scene
                # argument defaults to bg0001, so an assertion that omits it
                # reads False for every Bg0002 corpse and would have turned
                # the whole point of this test into a puzzle.
                self.assertTrue(
                    step.register.is_dead(mob.actor_identity, mob.scene))

    def test_the_single_string_in_use_today_cannot_kill_the_second_scene(self):
        # The before half of the measurement, kept as a test rather than
        # written up in the round note, so the day someone widens the bg0001
        # ruling's own template set to "fix" this by another route, this file
        # says so.  Nothing here asserts the refusal is DESIRABLE -- it
        # asserts the single-string call site is INSUFFICIENT, which is the
        # fact that made this round necessary.
        bg0002 = field_mobs.load_roster(scene=field_mobs.BG0002_SCENE)
        self.assertTrue(bg0002)
        for mob in bg0002:
            with self.subTest(identity=hex(mob.actor_identity)):
                with self.assertRaises(MobDeathContractError) as caught:
                    kill(
                        self.legacy, mob, self.lethal_outcome(mob),
                        DeathRegister(),
                        widened=RUNTIME_CALL_SITE_VALUE_BEFORE_THIS_ROUND)
                self.assertEqual(
                    caught.exception.reason,
                    mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)

    # -- the derivation --------------------------------------------------

    def test_the_wired_value_is_derived_from_the_world_not_typed_in(self):
        # Every name it returns is a registered ruling...
        wired = wired_widening_rulings()
        for name in wired:
            self.assertIn(name, mob_death.WIDENING_RULINGS)
        # ...and every name is there BECAUSE some shipped row needs it: drop
        # the rows a ruling covers and the ruling leaves the value.  This is
        # what "derived" has to mean to be worth the word; a hardcoded tuple
        # would pass the assertion above and fail this one.
        for name in wired:
            covered = [
                mob for _scene, mob in self.shipped_mobs()
                if name in mob_death._rulings_covering(mob)
            ]
            self.assertTrue(
                covered,
                "%r is in the wired value but covers nothing the world "
                "ships" % (name,))

    def test_a_ruling_that_covers_nothing_shipped_is_not_wired_in(self):
        # The diagnostic Mountain Deer letter (template 27) is a real
        # registered ruling whose bodies mob_diag_multi_object places
        # directly; no roster carries template 27.  It must NOT be handed to
        # the kill site: the wired value is what the world needs, not a
        # catalogue of every letter the project has received.
        diag = (
            "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
            "diag-mountain-deer-template-27"
        )
        self.assertIn(diag, mob_death.WIDENING_RULINGS)
        self.assertNotIn(
            27, {mob.template_id for _scene, mob in self.shipped_mobs()})
        self.assertNotIn(diag, wired_widening_rulings())

    def test_the_derivation_and_the_gate_agree_on_every_shipped_mob(self):
        # _rulings_covering() is a SECOND expression of the two questions
        # kill() asks, because kill() has to walk the rulings itself to say
        # which letter declined.  Two expressions of one rule drift; this
        # holds them to the same answer by execution, over every shipped row
        # crossed with every registered ruling, instead of trusting a comment.
        for _scene, mob in self.shipped_mobs():
            outcome = self.lethal_outcome(mob)
            covering = mob_death._rulings_covering(mob)
            for name in mob_death.WIDENING_RULINGS:
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

    def test_live_scenes_is_the_list_load_roster_actually_obeys(self):
        # wired_widening_rulings walks live_scenes(); if that list and the
        # scenes load_roster accepts ever diverge, the wired value would be
        # derived from a world the server does not run.
        for scene in field_mobs.live_scenes():
            self.assertTrue(field_mobs.load_roster(scene=scene))
        with self.assertRaises(field_mobs.FieldMobContractError):
            field_mobs.load_roster(scene="no-such-scene")

    def test_the_coverage_report_names_a_monster_no_ruling_covers(self):
        # G-OBS.  Round szdkgs shipped four unkillable dummies and the suite
        # stayed green, so "nothing covers this row" has to reach a console,
        # by identity, not wait for a tester to stand in front of it.
        # DERIVED, not typed in: the counts come from the roster itself, so a
        # roster edit changes what this test expects instead of failing it for
        # a reason that has nothing to do with what it is guarding.
        bg0002_size = len(field_mobs.load_roster(scene=field_mobs.BG0002_SCENE))
        self.assertGreater(bg0002_size, 0)
        healthy = mob_death.describe_wired_widening_coverage()
        self.assertFalse([ln for ln in healthy if "UNKILLABLE" in ln])
        self.assertTrue([
            ln for ln in healthy
            if "%d of %d" % (bg0002_size, bg0002_size) in ln])
        previous = dict(mob_death.WIDENING_RULINGS)
        try:
            mob_death.WIDENING_RULINGS.pop(WIDENED_BG0002_RULING)
            broken = mob_death.describe_wired_widening_coverage()
        finally:
            mob_death.WIDENING_RULINGS.clear()
            mob_death.WIDENING_RULINGS.update(previous)
        named = [ln for ln in broken if "UNKILLABLE" in ln]
        self.assertEqual(len(named), bg0002_size)
        self.assertTrue([
            ln for ln in broken if "0 of %d" % (bg0002_size,) in ln])
        # the report is restored with the dict, so a later test in this file
        # is not reading a mutated module
        self.assertEqual(mob_death.describe_wired_widening_coverage(), healthy)

    # -- the gate is not loosened ----------------------------------------

    def test_one_bad_name_beside_a_good_one_is_refused_not_rescued(self):
        # The defect this round could most easily have introduced.  A caller
        # assembling a list by hand mistranscribes one ruling; the correct
        # name beside it kills the mob anyway and nobody ever learns the
        # second letter was never really quoted.  pf-adversary round 67jejl
        # found the single-string version of exactly this.
        mob = field_mobs.load_roster(scene=field_mobs.BG0002_SCENE)[0]
        paraphrase = "PANYA-DECISION 2026-08-27 widen-death-scope-bg0002"
        self.assertNotIn(paraphrase, mob_death.WIDENING_RULINGS)
        for value in (
            (WIDENED_BG0002_RULING, paraphrase),
            (paraphrase, WIDENED_BG0002_RULING),
        ):
            with self.subTest(order=value.index(paraphrase)):
                with self.assertRaises(MobDeathContractError) as caught:
                    kill(
                        self.legacy, mob, self.lethal_outcome(mob),
                        DeathRegister(), widened=value)
                self.assertEqual(
                    caught.exception.reason,
                    mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)
                self.assertIn("recognises", caught.exception.detail)

    def test_two_rulings_do_not_assemble_an_authorisation_neither_gives(self):
        # The reverse-direction hazard, in its new multi-name shape.  Ruling A
        # (bg0001) covers template 916 in scene bg0001.  Ruling B (Bg0002)
        # covers template 31 in scene Bg0002.  A mob carrying template 916 in
        # scene Bg0002 matches A's template and B's scene -- and must still be
        # refused, because no single letter covers it.  A gate that tested
        # "some ruling's templates" and "some ruling's scenes" separately
        # would authorise this and would look correct in review.
        bg0001 = field_mobs.load_roster()[0]
        self.assertEqual(bg0001.template_id, 916)
        smuggled = field_mobs.FieldMob(
            placement_index=9101,
            template_id=bg0001.template_id,
            x=bg0001.x, y=bg0001.y, z=bg0001.z,
            visual_preset=bg0001.visual_preset,
            display_name="916 BODY WEARING THE OTHER SCENE",
            level=bg0001.level, rank=bg0001.rank,
            ai_wander=bg0001.ai_wander, ai_combat=bg0001.ai_combat,
            speed_walk=bg0001.speed_walk, max_hp=bg0001.max_hp,
            drops_normal=0, drops_equipment=0, drops_specially=0,
            scene=field_mobs.BG0002_SCENE,
        )
        with self.assertRaises(MobDeathContractError) as caught:
            kill(
                self.legacy, smuggled, self.lethal_outcome(smuggled),
                DeathRegister(),
                widened=(WIDENED_BG0001_RULING, WIDENED_BG0002_RULING))
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)
        # and the refusal says BOTH why each letter declined, not just the
        # last one tried -- a caller holding three letters needs to know which
        # of them it thought applied.
        self.assertIn(WIDENED_BG0001_RULING, caught.exception.detail)
        self.assertIn(WIDENED_BG0002_RULING, caught.exception.detail)

    def test_an_empty_or_malformed_widened_authorises_nothing(self):
        mob = field_mobs.load_roster(scene=field_mobs.BG0002_SCENE)[0]
        outcome = self.lethal_outcome(mob)
        for value in ((), [], None, "", "   ", (WIDENED_BG0002_RULING, ""),
                      (WIDENED_BG0002_RULING, None), 916,
                      {WIDENED_BG0002_RULING}):
            with self.subTest(value=repr(value)):
                with self.assertRaises(MobDeathContractError) as caught:
                    kill(
                        self.legacy, mob, outcome, DeathRegister(),
                        widened=value)
                self.assertEqual(
                    caught.exception.reason,
                    mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)

    def test_a_ruling_string_is_not_iterated_into_its_characters(self):
        # str is a sequence.  A normaliser that forgot to special-case it
        # would turn the real ruling into 60-odd one-character "rulings", none
        # registered, and the refusal a caller read back would name a letter
        # of the alphabet instead of the letter they quoted.  The positive
        # path proves it: a bare string still kills what it always killed.
        mob = field_mobs.load_roster()[0]
        step = kill(
            self.legacy, mob, self.lethal_outcome(mob), DeathRegister(),
            widened=WIDENED_916_RULING)
        self.assertTrue(step.register.is_dead(mob.actor_identity))
        # and a single-element sequence carrying the same name is the same
        # authorisation, not a different one
        again = kill(
            self.legacy, mob, self.lethal_outcome(mob), DeathRegister(),
            widened=(WIDENED_916_RULING,))
        self.assertEqual(again.dead_frame, step.dead_frame)


if __name__ == "__main__":
    unittest.main()
