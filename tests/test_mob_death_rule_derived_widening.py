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
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mob_tables_bg0002  # noqa: E402
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


def _hand_typed_permit_for(scene: str) -> frozenset[int]:
    """What the hand-typed letters authorise killing IN ONE SCENE.

    COO-DECISION 2026-09-07T16:41+07:00 item c.  The predecessor of this
    helper was a single union over every hand-typed letter, taken once and
    reused for all twelve ratified scenes -- so a template a letter permits
    in ONE scene read as "already permitted" in ELEVEN others it was never
    named in.  Bg0002 is the live case: ``field_mob_tables_bg0002.
    UNRESOLVED_PLACEMENTS`` ships template 27 four times, and the only
    hand-typed permit for 27 anywhere is ``PANYA-DECISION 2026-08-27T20:10
    ... diag-mountain-deer-template-27``, tied to **bg0001**.  Under the
    union those four placements are invisible to assertion 2; scene by
    scene they are not.

    The scene tie is read the same way :func:`mob_death.rulings_covering`
    reads it, and for the same reason -- a permit whose name is absent from
    ``WIDENING_RULING_SCENES`` has NO scene tie, and the production path
    lets such a permit cover a row in any scene.  Mirroring that here keeps
    this test measuring the gate rather than a stricter gate of its own; a
    hand-typed permit that loses its tie should show up as a widening in
    ``test_no_hand_typed_permit_is_killable_in_every_scene``, not as a
    silently narrower baseline in assertion 2.
    """
    permitted: set[int] = set()
    for name, templates in _hand_typed_rulings().items():
        required_scene = mob_death.WIDENING_RULING_SCENES.get(name)
        if required_scene is not None and required_scene != scene:
            continue
        permitted |= set(templates)
    return frozenset(permitted)


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

        Measured SCENE BY SCENE (COO-DECISION 2026-09-07T16:41+07:00 item
        c).  "Equals the old table" is a statement about each scene's own
        letter: the old table was twelve per-scene permits, not one pooled
        set, and a kill is refused or allowed in a scene, never in the
        union of all of them.  See :func:`_hand_typed_permit_for` for the
        template the pooled reading loses.
        """
        gained: list[tuple[str, int]] = []
        for scene in RATIFIED_SCENES_AT_SWITCH:
            self.assertIn(
                scene, field_mobs.live_scenes(),
                "a scene ratified at the switch has been de-registered; "
                "this pin describes a tree that no longer exists and the "
                "round that removed the scene owes it an update",
            )
            already_permitted = _hand_typed_permit_for(scene)
            for mob in field_mobs.load_roster(scene=scene):
                if mob.template_id not in already_permitted:
                    gained.append((scene, mob.template_id))

        self.assertEqual(
            sorted(set(gained)), [],
            "the rule-derived permit authorises killing template(s) in an "
            "ALREADY-RATIFIED scene that no hand-typed COO letter covers "
            "FOR THAT SCENE -- that is a widening of a scene COO already "
            "ruled on, not the automatic admission of a new one",
        )

    def test_a_permit_tied_to_one_scene_does_not_excuse_another(self):
        """The pin for COO-DECISION 2026-09-07T16:41+07:00 item c.

        Assertion 2 is only worth its message if its baseline is per-scene,
        and today assertion 2 is green under BOTH readings -- every shipped
        row happens to be covered in its own scene -- so nothing above
        would notice the union coming back.  This holds the difference
        directly, on shipped data rather than a fixture:

        ROUND najn72: THE DAY THIS TEST NAMED ARRIVED, and the witness had
        to move because of it.  ~~template 27 IS in the pooled union / is
        NOT in Bg0002's own permit / has four unresolved placements waiting
        on the owner's tick~~ -- the owner ticked (20260908_0025 item 1),
        the roster flipped 12 -> 52 and Bg0002's own permit now names 27,
        so 27 can no longer tell a per-scene reading from a pooled one.
        The property this test defends is unchanged and the shape of the
        witness is unchanged; only which template plays it moves, to the
        one the same flip freed up:

        * template 103 ("Orc Chief") IS in the pooled union of every
          hand-typed letter -- bg0004's letter names it, and so did
          Bg0002's until this round,
        * template 103 is NOT in Bg0002's own hand-typed permit any more:
          the crosswalk resolves no named body for it in this scene, so
          the ruling dropped it in the same commit that re-mined the
          roster,
        * and it is not a fixture: ``field_mob_tables_bg0002
          .WITHDRAWN_UNDER_THIS_RULE`` carries the five placements that
          used to ship it.

        So assertion 2 under a pooled union would report template 103 as
        already permitted in Bg0002 on the strength of bg0004's letter.
        This test goes red the moment ``_hand_typed_permit_for`` stops
        reading ``WIDENING_RULING_SCENES``.

        This asserts nothing about whether 103 SHOULD be killable in
        Bg0002 -- no row of the scene carries it, which is why it left.
        """
        pooled: set[int] = set()
        for templates in _hand_typed_rulings().values():
            pooled |= set(templates)
        self.assertIn(
            103, pooled,
            "template 103 no longer has a hand-typed permit anywhere, so "
            "this test's whole premise is gone and the round that removed "
            "the permit owes it a replacement witness",
        )
        self.assertNotIn(
            103, _hand_typed_permit_for("Bg0002"),
            "template 103 counts as already-permitted in Bg0002 although "
            "no letter of that scene names it -- the scene-blind union is "
            "back and assertion 2's baseline is pooled again",
        )
        # And the witness is a real withdrawal, not a template nobody ever
        # placed here: the rows that carried it are named in the table.
        from pirateforce_foundation import field_mob_tables_bg0002
        self.assertEqual(
            [row[0] for row in
             field_mob_tables_bg0002.WITHDRAWN_UNDER_THIS_RULE
             if row[1] == 103],
            [92, 93, 94, 95, 96])
        self.assertIn(
            27, _hand_typed_permit_for("bg0001"),
            "template 27 is no longer permitted in bg0001, the one scene "
            "its letter does name -- the scene tie is being read as a "
            "refusal instead of a scope",
        )
        # ROUND najn72: ~~four UNRESOLVED template-27 placements~~ -> four
        # SHIPPED ones.  COO-DECISION 1641 item c counted them while they
        # were waiting on the owner's tick; the tick came (20260908_0025)
        # and the same four placements (36-39) are now real rows of the
        # scene.  The count is what item c pinned and the count is
        # unchanged -- what moved is which list they sit in, so the check
        # follows them rather than reporting zero and calling it a move.
        self.assertEqual(
            [row[1] for row in field_mob_tables_bg0002.UNRESOLVED_PLACEMENTS
             if row[1] == 27],
            [],
            "template 27 is unresolved in Bg0002 again -- the re-mining "
            "that resolved it has been reverted, and the four rows below "
            "no longer ship",
        )
        shipped_27 = [
            row[0] for row in field_mob_tables_bg0002.HOSTILE_PLACEMENTS
            if row[1] == 27
        ]
        self.assertEqual(
            shipped_27, [36, 37, 38, 39],
            "Bg0002 no longer ships exactly the four template-27 "
            "placements COO-DECISION 1641 item c counted; the number this "
            "test was written against has moved",
        )

    def test_assertion_2_asks_the_permit_question_one_scene_at_a_time(self):
        """The other half of item c's pin, on assertion 2 itself.

        ``test_a_permit_tied_to_one_scene_does_not_excuse_another`` holds
        :func:`_hand_typed_permit_for`, but assertion 2 could stop calling
        it and rebuild the pooled union inline -- the two would then alibi
        each other and item c would be un-fixed with both tests green.
        Read structurally, because there is no shipped row that separates
        the two readings today (that is exactly why the bug survived).

        Checks the call's ARGUMENT, not just its name: a
        ``_hand_typed_permit_for(RATIFIED_SCENES_AT_SWITCH[0])`` hoisted
        out of the loop is the pooled reading wearing the right name.
        """
        import ast
        import inspect

        src = inspect.getsource(
            RuleDerivedWideningTests
            .test_ratified_scenes_gain_nothing_from_the_switch)
        tree = ast.parse(textwrap.dedent(src))

        loops = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.For)
            and isinstance(node.target, ast.Name)
            and node.target.id == "scene"
        ]
        self.assertEqual(
            len(loops), 1,
            "assertion 2 no longer walks the ratified scenes in exactly "
            "one `for scene in ...` loop; the structure this pin reads is "
            "gone and the pin owes itself a rewrite",
        )

        per_scene_calls = [
            node for node in ast.walk(loops[0])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_hand_typed_permit_for"
            and [a for a in node.args
                 if isinstance(a, ast.Name) and a.id == "scene"]
        ]
        self.assertEqual(
            len(per_scene_calls), 1,
            "assertion 2 does not ask _hand_typed_permit_for(scene) once "
            "inside its own scene loop -- either the baseline was hoisted "
            "out of the loop (one scene's permit reused for all twelve) or "
            "the pooled union is back inline",
        )

        self.assertNotIn(
            "_hand_typed_rulings", src,
            "assertion 2 reads the hand-typed letters directly again; the "
            "only pooled reading item c forbids is exactly this one",
        )

    def test_no_hand_typed_permit_is_killable_in_every_scene(self):
        """A hand-typed permit with no scene tie is a permit everywhere.

        :func:`mob_death.rulings_covering` treats a missing
        ``WIDENING_RULING_SCENES`` entry as "covers any scene", so an
        untied hand-typed permit would widen all twelve ratified scenes at
        once and would do it while assertion 2 stayed green (the baseline
        mirrors production, so it would widen with it).  There are none
        today; this says so out loud rather than leaving it to be noticed.
        """
        untied = sorted(
            name for name in _hand_typed_rulings()
            if mob_death.WIDENING_RULING_SCENES.get(name) is None
        )
        self.assertEqual(
            untied, [],
            "hand-typed permit(s) carry no scene tie, so kill() accepts "
            "them in EVERY scene: %r" % (untied,),
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

        Measured before the fix, not imagined: all 17 shipped Bg0002 rows
        moved from the PANYA-DECISION 2026-08-27T20:10 letter (4 templates)
        to this round's derived permit (3).  ``ruling_for`` now consults
        derived permits only where no signed letter covers the row at all.
        """
        derived_names = set(mob_death.RULE_DERIVED_RULING_FOR_SCENE.values())
        checked = 0
        for scene in field_mobs.live_scenes():
            for mob in field_mobs.load_roster(scene=scene):
                covering = mob_death.rulings_covering(mob)
                if not covering:
                    continue
                if all(name in derived_names for name in covering):
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
            "no shipped row is covered by both a signed letter and a derived "
            "permit, so this test proves nothing about the partition",
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
