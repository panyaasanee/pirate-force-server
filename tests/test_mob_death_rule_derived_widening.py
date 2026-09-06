"""LANE-B / round 0wef26: one rule replaces eleven per-scene permits.

COO-DECISION 2026-09-06T16:48+07:00 (``pf_bridge`` notes_to_chief/20260906_
1648_COO-DECISION-ka1a1635-*.md) item 2: once LANE-B has measured the single
MOBS-column rule against the shipped per-scene tables and found no
disagreement, the next round switches -- the tables derive from one rule,
"with a test proving it equals the old table for every ratified scene; new
scenes enter automatically, with no further COO letter".

This file is that test.  It holds four separate things, because "equals the
old table" can be read four ways and only one of them is the one that
matters for a kill:

1.  The dict value is still the RULE's output, not a literal.  If somebody
    later pastes a frozenset over a derived permit's entry in
    ``WIDENING_RULINGS``,
    the rule and the permit have parted company and this goes red.
2.  For the twelve scenes ratified on the tree that introduced this key, the
    derived permit authorises NOTHING the hand-typed per-scene permits did
    not already authorise.  That is item 2's "equals the old table", measured
    on the kill axis rather than the roster axis (the round bvaptp letter,
    ``20260906_1824_LANE-B-TO-COO-mobs-rule-diff-town-vs-ocean.md``, measured
    the roster axis and found 0/106; this is the other half).
    Scoped to a PINNED scene list, deliberately: a thirteenth scene arriving
    later SHOULD widen the derived set, and must not turn this red.
3.  Every monster a registered scene actually ships is killable under the
    derived permit.  This is the property new scenes rely on -- it is what
    "enter automatically, with no further COO letter" means in code.
4.  Withheld and owner-refused placements are NOT reached by it.  Item 4 of
    the same letter keeps the Nina/Carlos withholding alive until ticket
    924/529 answers, and a rule-derived permit is exactly the shape of change
    that could dissolve such an exception without anybody noticing.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402


# The scenes that carried a hand-typed COO permit on the tree this key was
# introduced on (round 0wef26).  PINNED, and pinned as a snapshot rather than
# read from ``live_scenes()``: the whole point of the switch is that
# ``live_scenes()`` grows without a letter, so comparing against it would
# make assertion 2 compare the new arrangement with itself and prove nothing.
RATIFIED_SCENES_AT_SWITCH = (
    "Bg0002", "Bg0003", "Bg0007", "Bg0008", "Bg0009", "Bg0010", "Bg0011",
    "Bg0015", "bg0001", "bg0004", "bg0005", "bg0006",
)


def _hand_typed_rulings() -> dict[str, frozenset[int]]:
    """``WIDENING_RULINGS`` minus the keys this round derived."""
    derived = set(mob_death.RULE_DERIVED_RULING_FOR_SCENE.values())
    return {
        name: templates
        for name, templates in mob_death.WIDENING_RULINGS.items()
        if name not in derived
    }


class RuleDerivedWideningTests(unittest.TestCase):

    def test_the_registered_values_are_still_the_rules_own_output(self):
        """Assertion 1: the permits cannot drift away from the rule."""
        derived = mob_death.derive_rule_widened_templates()
        self.assertEqual(
            sorted(derived), sorted(mob_death.RULE_DERIVED_RULING_FOR_SCENE),
            "the set of scenes the rule derives a permit for is no longer "
            "the set registered at import",
        )
        for scene, templates in derived.items():
            name = mob_death.RULE_DERIVED_RULING_FOR_SCENE[scene]
            self.assertEqual(
                mob_death.WIDENING_RULINGS[name], templates,
                "scene %r's rule-derived permit no longer holds what "
                "derive_rule_widened_templates() returns -- a literal has "
                "been pasted over it and the permit no longer says what the "
                "MOBS columns say" % (scene,),
            )
            self.assertEqual(
                mob_death.WIDENING_RULING_SCENES.get(name), scene,
                "scene %r's rule-derived permit lost its scene tie; a "
                "template-only permit is killable in ANY scene" % (scene,),
            )

    def test_every_derived_permit_name_is_the_function_of_its_scene(self):
        """The name is derived too, so it cannot be typed two ways.

        ``kill`` fails closed on an unrecognised ``widened=`` string, so a
        second spelling of a permit name is a refusal, not a lenience -- the
        reason the name is a function and not a literal.
        """
        for scene, name in mob_death.RULE_DERIVED_RULING_FOR_SCENE.items():
            self.assertEqual(name, mob_death.rule_derived_ruling_name(scene))
            self.assertIn(name, mob_death.WIDENING_RULINGS)

    def test_ratified_scenes_gain_nothing_from_the_switch(self):
        """Assertion 2: COO-DECISION 1648 item 2's "equals the old table".

        PER SCENE, and read off the REGISTERED permit rather than recomputed
        from the roster.  Both halves are pf-adversary's finding on round
        0wef26's branch, and both were real holes in the first shape of this
        test:

        *   It compared the union of every ratified scene's roster against
            the union of ALL hand-typed letters, so a template counted as
            "already permitted" when ANY scene's letter carried it.
            Measured: template 669, which only the Bg0011 letter covers, was
            injected into a different scene's derived permit for each of the
            12 ratified scenes in turn -- green 12 times out of 12, full
            suite unchanged.  A ratified scene's roster growing therefore
            widened that scene's kill permit silently, which is precisely
            what item 2 promises does not happen.
        *   It never read a derived permit at all; it recomputed the rule.  A
            literal pasted over an entry in ``WIDENING_RULINGS`` is what
            ``kill`` actually consults, so that is what this now reads.

        What item 2 promises, stated per scene: the permit derived FOR a
        scene authorises nothing in that scene that the letters tied TO that
        scene did not already authorise.  Measured on this tree: true for
        all twelve, with zero templates of slack in any of them.
        """
        hand_by_scene: dict[str, set[int]] = {}
        for name, templates in _hand_typed_rulings().items():
            scene = mob_death.WIDENING_RULING_SCENES.get(name)
            if scene is None:
                continue
            hand_by_scene.setdefault(scene, set()).update(templates)

        for scene in RATIFIED_SCENES_AT_SWITCH:
            self.assertIn(
                scene, field_mobs.live_scenes(),
                "a scene ratified at the switch has been de-registered; "
                "this pin describes a tree that no longer exists and the "
                "round that removed the scene owes it an update",
            )
            self.assertIn(
                scene, mob_death.RULE_DERIVED_RULING_FOR_SCENE,
                "ratified scene %r ships a roster but has no rule-derived "
                "permit, so the switch item 2 authorised did not happen for "
                "it" % (scene,),
            )
            name = mob_death.RULE_DERIVED_RULING_FOR_SCENE[scene]
            derived_here = set(mob_death.WIDENING_RULINGS[name])
            signed_here = hand_by_scene.get(scene, set())

            # Anti-vacuity, both directions: an empty derived permit or a
            # scene with no signed letter of its own would make the subset
            # below true for a reason that has nothing to do with item 2.
            self.assertTrue(
                derived_here,
                "the derived permit for ratified scene %r is empty, so the "
                "comparison below proves nothing" % (scene,),
            )
            self.assertTrue(
                signed_here,
                "ratified scene %r has no hand-typed letter tied to it, so "
                "there is no 'old table' here to equal" % (scene,),
            )

            self.assertEqual(
                sorted(derived_here - signed_here), [],
                "the permit derived for ALREADY-RATIFIED scene %r "
                "authorises killing template(s) %s that no letter tied to "
                "%r covers -- that is a widening of a scene COO already "
                "ruled on, not the automatic admission of a new one"
                % (scene, sorted(derived_here - signed_here), scene),
            )

    def test_a_signed_letter_outranks_a_derived_permit_on_every_shipped_row(
            self):
        """Assertion 2, on the axis that actually bit.

        COO-DECISION 2026-08-29T08:48+07:00 item 1(b) refuses to let a letter
        written tomorrow move the provenance of a kill already recorded under
        one written yesterday, and enforces it through the AGE term.  A
        derived permit gets past that term without touching it: it can be
        NARROWER than the hand letter (the roster ships fewer templates than
        the letter authorised), and narrower is term (a), which outranks age.

        Measured before the fix, not imagined: all 12 shipped Bg0002 rows
        moved from the PANYA-DECISION 2026-08-27T20:10 letter (4 templates)
        to this round's derived permit (3).  ``ruling_for`` now consults
        derived permits only where no signed letter covers the row at all.

        (Twelve, not the seventeen an earlier telling of this said:
        ``field_mob_tables_bg0002.HOSTILE_PLACEMENTS`` lists 17 placements
        and five of them are owner-refused, so ``load_roster('Bg0002')``
        ships 12.  The seventeen is the table's length, not a count of rows
        any player can meet.)

        The guard at the bottom is the one pf-adversary caught being no
        guard at all: it used to count a row as checked whenever a signed
        letter covered it, which is true of nearly every shipped row and
        stayed true with the whole derivation mutated away to ``{}``.  A row
        only exercises the partition if BOTH kinds of permit cover it.
        """
        derived_names = set(mob_death.RULE_DERIVED_RULING_FOR_SCENE.values())
        checked = 0
        for scene in field_mobs.live_scenes():
            for mob in field_mobs.load_roster(scene=scene):
                covering = mob_death.rulings_covering(mob)
                signed = [n for n in covering if n not in derived_names]
                derived = [n for n in covering if n in derived_names]
                if not (signed and derived):
                    continue
                checked += 1
                self.assertNotIn(
                    mob_death.ruling_for(mob), derived_names,
                    "shipped row 0x%X in %r is recorded under a permit this "
                    "round derived, though a signed letter covers it -- the "
                    "switch moved the provenance of an already-ratified kill"
                    % (mob.actor_identity, scene),
                )
        self.assertGreater(
            checked, 0,
            "no shipped row is covered by BOTH a signed letter and a derived "
            "permit, so this test proves nothing about the partition -- "
            "either the derivation stopped producing permits or the signed "
            "letters stopped covering shipped rows",
        )

    def test_every_registered_scenes_monsters_are_killable_under_the_rule(
            self):
        """Assertion 3: what "new scenes enter automatically" means."""
        uncovered = []
        for scene in field_mobs.live_scenes():
            name = mob_death.RULE_DERIVED_RULING_FOR_SCENE.get(scene)
            for mob in field_mobs.load_roster(scene=scene):
                if name is None or mob.template_id not in (
                        mob_death.WIDENING_RULINGS[name]):
                    uncovered.append((scene, mob.template_id))
        self.assertEqual(
            uncovered, [],
            "a registered scene ships a monster its own rule-derived permit "
            "does not cover, so that scene still needs a per-scene letter "
            "and the switch did not take",
        )

    def test_the_rule_names_the_ruling_for_a_shipped_monster(self):
        """Assertion 3, through the module's own answering path.

        ``rulings_covering`` is what the wired gate and its derivation are
        held to agree on (``tests/test_mob_death_wired_widening.py``), so
        asking it -- rather than only asking the frozenset -- is what proves
        the new key is reachable by a kill and not merely present in a dict.
        """
        for scene in field_mobs.live_scenes():
            roster = field_mobs.load_roster(scene=scene)
            if not roster:
                continue
            mob = roster[0]
            self.assertIn(
                mob_death.RULE_DERIVED_RULING_FOR_SCENE[scene],
                mob_death.rulings_covering(mob),
                "scene %r's first shipped monster (template %d) is not "
                "covered by the rule-derived permit through the module's "
                "own answering path" % (scene, mob.template_id),
            )

    def test_withheld_and_refused_placements_are_not_reached(self):
        """Assertion 4: item 4's exceptions survive the switch.

        Withholding happens in ``field_mobs`` at roster-build time, so the
        proof wanted here is that a withheld or refused placement's template
        does not arrive in the permit that covers ITS OWN scene through some
        other placement -- which is the way a template-keyed permit could
        quietly dissolve a placement-keyed exception.

        Scoped to the scene on purpose, because the global statement is
        FALSE and was written down as true in an earlier telling of this
        (``mob_death``'s comment has been corrected in the same commit):
        template 103 is owner-refused at Bg0002 placements 92-96 and is at
        the same time in bg0004's derived permit, because bg0004 ships it.
        Nothing is wrong with that -- every permit names a scene, so
        bg0004's cannot reach a Bg0002 placement -- but it means the scene
        tie is the whole of what keeps item 4 alive, and that is what this
        measures.

        Both templates item 4 names are pinned by id: 924 (Bg0015 placement
        87) and 529 (Bg0008 placement 69, Nina).  An earlier shape of this
        test named only 924, and a mutant that pushed 529 into every derived
        permit left the file 7/7 green.
        """
        derived: set[int] = set()
        for name in mob_death.RULE_DERIVED_RULING_FOR_SCENE.values():
            derived |= set(mob_death.WIDENING_RULINGS[name])
        checked = 0
        for scene in field_mobs.live_scenes():
            withheld = field_mobs.lane_withheld_placements(scene)
            refused = field_mobs.owner_refused_placements(scene)
            if not withheld and not refused:
                continue
            shipped = {
                mob.placement_index for mob in field_mobs.load_roster(
                    scene=scene)
            }
            for placement in tuple(withheld) + tuple(refused):
                checked += 1
                self.assertNotIn(
                    placement, shipped,
                    "%r placement %d is withheld or owner-refused yet ships "
                    "in the roster" % (scene, placement),
                )
        self.assertGreater(
            checked, 0,
            "no withheld or owner-refused placement was found to check -- "
            "this test would pass vacuously and prove nothing about item 4",
        )
        # The exception, measured in the shape item 4 states it: a template
        # id, at the scene whose placement is the reason it is withheld.
        pinned = 0
        for scene in field_mobs.live_scenes():
            excepted = tuple(field_mobs.lane_withheld_placements(scene))
            excepted += tuple(field_mobs.owner_refused_placements(scene))
            if not excepted:
                continue
            module = field_mobs._SCENE_TABLE_MODULES[scene]
            template_of = {
                row[0]: row[1] for row in module.HOSTILE_PLACEMENTS
            }
            name = mob_death.RULE_DERIVED_RULING_FOR_SCENE.get(scene)
            here = set(mob_death.WIDENING_RULINGS[name]) if name else set()
            for placement in excepted:
                template = template_of.get(placement)
                if template is None:
                    continue
                pinned += 1
                self.assertNotIn(
                    template, here,
                    "template %d is withheld or owner-refused at %r "
                    "placement %d, yet %r's own rule-derived permit "
                    "authorises killing it -- the switch dissolved an "
                    "exception COO-DECISION 2026-09-06T16:48+07:00 item 4 "
                    "keeps alive until ticket 924/529 answers"
                    % (template, scene, placement, scene),
                )
        self.assertGreater(
            pinned, 0,
            "no withheld or owner-refused placement resolved to a template, "
            "so the per-scene half of item 4 was not measured at all",
        )

        # The two templates item 4 turns on, named by id as well, so that
        # renumbering a placement cannot quietly retire the pin above.
        for template, where in ((924, "Bg0015 placement 87"),
                                (529, "Bg0008 placement 69, Nina")):
            self.assertNotIn(
                template, derived,
                "template %d (%s) has entered a rule-derived permit; "
                "COO-DECISION 2026-09-06T16:48+07:00 item 4 keeps it "
                "withheld until ticket 924/529 answers" % (template, where),
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
