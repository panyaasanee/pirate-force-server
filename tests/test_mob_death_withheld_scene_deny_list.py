"""LANE-B / round 2fpnex: the deny-list, and the tripwire a 13th scene trips.

Three COO rulings meet in this file, all of them about the same question --
what a scene has to have before a kill in it is authorised -- now that
``mob_death`` mints permits from a rule instead of from eleven hand-typed
letters.

D3, COO-DECISION 2026-09-06T22:41+07:00 (``pf_bridge`` notes_to_chief/
20260906_2241_COO-DECISION-b2131-*.md), option (a): new scenes enter the
derived permit automatically EXCEPT scenes named in a short per-scene
deny-list declared in the code, each row citing the letter that deferred it.
Today that is one row, ``Bg3001`` <- COO-DECISION 2026-09-06T17:45.  COO's
own instruction was to keep round ``mf71tm``'s word for the state
(``ROSTER_SHIPPED_KILL_NOT_YET_GRANTED``) rather than invent a new one, and
to make ``ruling_for`` refuse those scenes with the message it already uses.

THE POINT OF MOVING IT INTO THE CODE.  On branch ``mf71tm`` that set lives in
``tests/test_mob_scene_registration_contract.py`` -- a test reads it, and
nothing else does.  That proves the set's contents; it does not stop a kill,
because ``kill()`` never reads it.  Under the derived permit the difference
stops being academic: the moment that branch registers ``Bg3001`` in
``field_mobs``, ``derive_rule_widened_templates()`` would mint it a permit on
the next import with nobody typing anything.  So the assertions below are
written the hard way round -- not "the set still says Bg3001", but "with the
row present a kill is refused, and with the row removed the SAME kill
succeeds".  A deny-list that cannot be shown to be the reason for a refusal
is not a deny-list.

D1's 13th-scene tripwire, COO-DECISION 2026-09-06T23:45+07:00 item 2: the
authority order is SIGNED LETTER > DERIVED PERMIT > TABLE ROW, and a table
row alone grants nothing.  A scene may enter only two ways: a signed letter,
or the columns plus its own ``PREDICATE_CENSUS``.  So a thirteenth scene that
arrives with neither must turn this file red rather than quietly become
killable.

D2, same letter item 3: every derived permit is checked BOTH ways -- that
``rulings_covering`` names it, and that ``kill()`` refuses that permit's own
templates when they are presented in another scene.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402

from pf_preconditions import BRIDGE_SIBLING  # noqa: E402


def stand_in(*, template_id, scene, placement_index=9411,
             display_name="STAND-IN"):
    """A FieldMob in a scene no shipped row is in.

    Every field but the three under test is copied off a real shipped row, so
    a stand-in cannot pass or fail for a reason this file is not about --
    same construction ``tests/test_mob_death_wired_widening.py`` uses.
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


class Bg3001IsNotKillableYetTests(unittest.TestCase):
    """D3.  The one row on the deny-list today, measured as load-bearing."""

    WITHHELD_SCENE = "Bg3001"

    def a_withheld_mob(self):
        """A monster in the deferred scene, carrying a template a SIGNED
        letter already covers elsewhere.

        Deliberately the hardest case for the deny-list rather than the
        easiest: an unknown template would be refused by the scope check even
        with the deny-list deleted, and would therefore prove nothing about
        the deny-list at all.
        """
        signed = sorted(
            set(mob_death.WIDENING_RULINGS)
            - set(mob_death.RULE_DERIVED_RULING_FOR_SCENE.values())
        )
        self.assertTrue(signed, "no signed letter is registered any more")
        for name in signed:
            for template in sorted(mob_death.WIDENING_RULINGS[name]):
                return stand_in(
                    template_id=template, scene=self.WITHHELD_SCENE)
        self.fail("every signed letter covers an empty template set")

    def test_the_deferred_scene_is_covered_by_no_ruling_at_all(self):
        mob = self.a_withheld_mob()
        self.assertEqual(
            mob_death.rulings_covering(mob), (),
            "a scene whose kill grant is DEFERRED is covered by a ruling",
        )

    def test_ruling_for_refuses_the_deferred_scene_with_the_owner_sentence(
            self):
        mob = self.a_withheld_mob()
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.ruling_for(mob)
        self.assertIn("ask the owner", str(caught.exception))

    def test_kill_refuses_the_deferred_scene_under_a_named_signed_letter(self):
        """The route a test-only deny-list cannot close.

        ``kill`` does not consult ``rulings_covering``; it looks the ONE name
        it was handed up directly.  So a caller holding a signed letter's own
        name is exactly the caller a set read only by a test would not stop.
        """
        mob = self.a_withheld_mob()
        signed = sorted(
            set(mob_death.WIDENING_RULINGS)
            - set(mob_death.RULE_DERIVED_RULING_FOR_SCENE.values())
        )[0]
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.kill(None, mob, None, None, widened=signed)
        message = str(caught.exception)
        self.assertIn("DEFERRED", message)
        self.assertIn("ask the owner", message)

    def test_removing_the_row_is_what_changes_the_answer(self):
        """The deny-list is the REASON, not a bystander.

        Measured on a scene that IS registered, because ``Bg3001`` is not:
        with no permit of its own, a Bg3001 stand-in is refused by the scope
        check whether the deny-list exists or not, so it cannot show the
        deny-list doing anything.  A registered scene's own shipped monster
        can: covered today, uncovered the moment its scene joins the list,
        covered again when it leaves.  That is the property ``Bg3001`` will
        have the day ``mf71tm`` registers it.
        """
        scene = field_mobs.live_scenes()[0]
        mob = field_mobs.load_roster(scene=scene)[0]
        self.assertNotEqual(
            mob_death.rulings_covering(mob), (),
            "scene %r's own first monster is covered by no ruling even "
            "before the deny-list is touched" % (scene,),
        )
        with mock.patch.dict(
                mob_death.WITHHELD_SCENE_LETTERS,
                {scene: "TEST-ONLY, never a real grant"}):
            self.assertEqual(
                mob_death.rulings_covering(mob), (),
                "a scene on the deny-list is still covered by a ruling",
            )
            with self.assertRaises(mob_death.MobDeathContractError) as caught:
                mob_death.kill(None, mob, None, None,
                               widened=mob_death.WIDENING_RULINGS
                               and sorted(mob_death.WIDENING_RULINGS)[0])
            self.assertIn("DEFERRED", str(caught.exception))
        self.assertNotEqual(
            mob_death.rulings_covering(mob), (),
            "the deny-list row did not come back out again",
        )

    def test_a_deferred_scene_is_minted_no_derived_permit(self):
        derived = mob_death.derive_rule_widened_templates()
        overlap = sorted(set(derived) & set(mob_death.WITHHELD_SCENE_LETTERS))
        self.assertEqual(
            overlap, [],
            "the derivation minted a permit for a scene whose kill grant is "
            "DEFERRED",
        )

    def test_the_derivation_skip_is_load_bearing_on_a_live_scene(self):
        """Anti-vacuity for the test above.

        ``Bg3001`` is not registered on this tree, so the overlap above is
        empty whether the skip works or not.  Putting a scene that IS
        registered on the deny-list and watching its permit disappear is what
        proves the skip runs.
        """
        live = field_mobs.live_scenes()
        self.assertTrue(live, "no live scene to measure the skip against")
        victim = live[0]
        self.assertIn(victim, mob_death.derive_rule_widened_templates())
        with mock.patch.dict(
                mob_death.WITHHELD_SCENE_LETTERS,
                {victim: "TEST-ONLY, never a real grant"}):
            self.assertNotIn(
                victim, mob_death.derive_rule_widened_templates(),
                "a scene on the deny-list was still minted a derived permit",
            )

    def test_every_deny_list_row_cites_a_letter_that_exists(self):
        """A row's citation is checkable, or the row is an assertion.

        Same lookup shape ``tests/test_mob_death_widening_schema_gate.py``
        uses for ruling keys: the stamp in the citation must name a real file
        in ``pf_bridge/notes_to_chief``.
        """
        import os
        import re
        env = os.environ.get("PF_BRIDGE_DIR")
        if env and Path(env).is_dir():
            pf_bridge_dir = Path(env)
        else:
            BRIDGE_SIBLING.require(self)
            pf_bridge_dir = BRIDGE_SIBLING.paths[0]
        notes = pf_bridge_dir / "notes_to_chief"
        self.assertTrue(mob_death.WITHHELD_SCENE_LETTERS, "deny-list is empty")
        for scene, citation in mob_death.WITHHELD_SCENE_LETTERS.items():
            with self.subTest(scene=scene):
                found = re.search(
                    r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})\+07:00",
                    citation)
                self.assertIsNotNone(
                    found, "row %r cites no dated letter" % (scene,))
                year, month, day, hour, minute = found.groups()
                stamp = "%s%s%s_%s%s" % (year, month, day, hour, minute)
                self.assertTrue(
                    any(entry.name.startswith(stamp)
                        and "COO-DECISION" in entry.name
                        for entry in notes.iterdir()),
                    "row %r cites %s and no such COO-DECISION letter is "
                    "filed" % (scene, stamp),
                )


class ThirteenthSceneTripwireTests(unittest.TestCase):
    """D1 item 2.  A table row alone does not grant a kill.

    COO-DECISION 2026-09-06T23:45+07:00: authority runs SIGNED LETTER >
    DERIVED PERMIT > TABLE ROW, and a scene enters one of exactly two ways --
    a signed letter, or the MOBS columns PLUS its own ``PREDICATE_CENSUS``.
    A thirteenth scene registered with neither must turn this red instead of
    becoming killable because somebody added a module to a dict.
    """

    def signed_scenes(self):
        derived = set(mob_death.RULE_DERIVED_RULING_FOR_SCENE.values())
        return {
            scene
            for name, scene in mob_death.WIDENING_RULING_SCENES.items()
            if name not in derived
        }

    def census_of(self, scene):
        """The scene's own ``PREDICATE_CENSUS``, or ``None``.

        Reaches ``field_mobs._SCENE_TABLE_MODULES`` on purpose and with its
        eyes open: that private dict IS the registry this tripwire is about --
        the question asked here is "what happens when somebody adds a row to
        it", so reading a public projection of it instead would measure the
        projection.
        """
        module = field_mobs._SCENE_TABLE_MODULES.get(scene)
        return getattr(module, "PREDICATE_CENSUS", None)

    def test_every_registered_scene_entered_by_a_letter_or_by_a_census(self):
        signed = self.signed_scenes()
        self.assertTrue(
            field_mobs.live_scenes(), "no registered scene to walk")
        undocumented = []
        for scene in field_mobs.live_scenes():
            if mob_death.scene_kill_is_withheld(scene) is not None:
                continue
            if scene in signed:
                continue
            if self.census_of(scene):
                continue
            undocumented.append(scene)
        self.assertEqual(
            undocumented, [],
            "scene(s) %r are registered and killable with NO signed COO "
            "letter and NO PREDICATE_CENSUS of their own -- under "
            "COO-DECISION 2026-09-06T23:45 item 2 a table row alone does not "
            "grant a kill.  Either the scene gets a letter, or its table "
            "gets its census, or it goes on WITHHELD_SCENE_LETTERS with the "
            "letter that defers it" % (undocumented,),
        )

    def test_the_tripwire_fires_on_a_thirteenth_scene(self):
        """Anti-vacuity, and the case the ruling is actually about.

        Every scene registered TODAY carries a signed letter, so the
        assertion above passes on this tree no matter whether it is wired to
        anything.  The thirteenth scene is therefore simulated exactly as it
        would arrive -- a new key in the registry ``live_scenes()`` reads,
        with no letter written for it and no table module (hence no
        ``PREDICATE_CENSUS``) behind it -- and the tripwire must go red.
        """
        thirteenth = "Bg9999"
        self.assertNotIn(thirteenth, field_mobs.live_scenes())
        self.assertIsNone(self.census_of(thirteenth))
        with mock.patch.object(
                field_mobs, "live_scenes",
                return_value=field_mobs.live_scenes() + (thirteenth,)):
            with self.assertRaises(AssertionError) as caught:
                self.test_every_registered_scene_entered_by_a_letter_or_by_a_census()
        self.assertIn(thirteenth, str(caught.exception))

    def test_a_thirteenth_scene_that_is_deferred_does_not_trip_it(self):
        """The deny-list is the OTHER honest answer for a new scene.

        A scene with no letter is allowed to be registered while its grant is
        pending -- that is what ``Bg3001`` is -- so the tripwire must accept
        a deny-listed scene and reject only the silent one.  Without this,
        the only way to land a new roster would be to mint it a permit.
        """
        thirteenth = "Bg9999"
        with mock.patch.object(
                field_mobs, "live_scenes",
                return_value=field_mobs.live_scenes() + (thirteenth,)):
            with mock.patch.dict(
                    mob_death.WITHHELD_SCENE_LETTERS,
                    {thirteenth: "TEST-ONLY, never a real grant"}):
                self.test_every_registered_scene_entered_by_a_letter_or_by_a_census()


class DerivedPermitCrossSceneTests(unittest.TestCase):
    """D2.  Every derived permit, both ways, by execution."""

    def test_every_derived_permit_is_named_by_rulings_covering(self):
        checked = 0
        for scene, name in mob_death.RULE_DERIVED_RULING_FOR_SCENE.items():
            for mob in field_mobs.load_roster(scene=scene):
                with self.subTest(scene=scene, template=mob.template_id):
                    self.assertIn(name, mob_death.rulings_covering(mob))
                checked += 1
        self.assertGreaterEqual(
            checked, 16,
            "the derived permits cover almost nothing, so this loop is "
            "vacuous",
        )

    def test_a_derived_permit_does_not_authorise_its_templates_elsewhere(
            self):
        """The scene axis, on the permit the rule mints rather than a letter.

        A permit tied to scene X presented for a mob in scene Y must be
        refused -- otherwise deriving permits per scene bought nothing over
        the one scene-tie-less key the existing contract test already
        refuses.
        """
        scenes = sorted(mob_death.RULE_DERIVED_RULING_FOR_SCENE)
        self.assertGreaterEqual(
            len(scenes), 2, "fewer than two derived permits to cross")
        crossed = 0
        for scene in scenes:
            name = mob_death.RULE_DERIVED_RULING_FOR_SCENE[scene]
            other = next(
                s for s in scenes
                if s != scene
                and mob_death.scene_kill_is_withheld(s) is None
            )
            for template in sorted(mob_death.WIDENING_RULINGS[name]):
                mob = stand_in(template_id=template, scene=other)
                with self.subTest(permit=scene, presented_in=other,
                                  template=template):
                    with self.assertRaises(mob_death.MobDeathContractError):
                        mob_death.kill(None, mob, None, None, widened=name)
                crossed += 1
        self.assertGreater(crossed, 0, "no permit was crossed")


if __name__ == "__main__":
    unittest.main()
