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
        """Assertion 2: COO-DECISION 1648 item 2's "equals the old table"."""
        already_permitted: set[int] = set()
        for templates in _hand_typed_rulings().values():
            already_permitted |= set(templates)

        derived_for_ratified: set[int] = set()
        for scene in RATIFIED_SCENES_AT_SWITCH:
            self.assertIn(
                scene, field_mobs.live_scenes(),
                "a scene ratified at the switch has been de-registered; "
                "this pin describes a tree that no longer exists and the "
                "round that removed the scene owes it an update",
            )
            for mob in field_mobs.load_roster(scene=scene):
                derived_for_ratified.add(mob.template_id)

        self.assertEqual(
            sorted(derived_for_ratified - already_permitted), [],
            "the rule-derived permit authorises killing template(s) in an "
            "ALREADY-RATIFIED scene that no hand-typed COO letter covers -- "
            "that is a widening of a scene COO already ruled on, not the "
            "automatic admission of a new one",
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
        proof wanted here is that the withheld placement's template does not
        arrive in the derived set through some OTHER placement -- which is
        the way a template-keyed permit could quietly dissolve a
        placement-keyed exception.
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
        # Template 924 (Bg0015 placement 87, withheld pending ticket 924/529)
        # named explicitly, because it is the one item 4 turns on.
        self.assertNotIn(
            924, derived,
            "template 924 has entered the rule-derived permit; "
            "COO-DECISION 2026-09-06T16:48+07:00 item 4 keeps it withheld "
            "until ticket 924/529 answers",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
