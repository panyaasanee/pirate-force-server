"""LANE-B: tests for
src/pirateforce_foundation/mob_death_bg0015_ruling_proposal.py.

What this file proves, and what it deliberately does not claim:

* The 7-template set this module reports is the SAME set
  ``mob_combat_bg0015_gates.templates_without_a_death_ruling()`` already
  measures as refused -- cross-checked by execution, not asserted once from
  a literal and trusted to stay true.
* Exactly one of the seven (Carlos, 924) is distinguishable from the other
  six by outfit prefix WITHIN Bg0015's own roster -- derived from the raw
  ``HOSTILE_PLACEMENTS`` rows independently of the FieldMob-typed path the
  module itself reads, so an agreement between the two is a real check, not
  the same code path counted twice.
* The three options are pairwise consistent (C subset of B subset of A, A
  minus B is exactly {Carlos}).
* This module registers NOTHING: ``mob_death.WIDENING_RULINGS`` is unchanged
  after every function in it has been called, and the gate it studies stays
  exactly as closed as it was before this file existed.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pirateforce_foundation import field_mob_hostile_bg0015
from pirateforce_foundation import field_mob_tables_bg0015
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_combat_bg0015_gates as gates
from pirateforce_foundation import mob_death
from pirateforce_foundation import mob_death_bg0015_ruling_proposal as proposal


class FullRosterTemplateIdsTests(unittest.TestCase):

    def test_matched_the_gates_modules_own_refused_measurement_before_any_ruling(
            self):
        # ~~the two are the same tuple~~ WITHDRAWN round n3wqrt-successor:
        # they were the same tuple only because zero of the seven had a
        # ruling yet, which made "every candidate" and "every refused
        # candidate" coincide by accident of timing, not by definition.
        # COO-RULING-20260901-1046 (mob_death.py) now rules six, so the two
        # readers correctly diverge -- this function still names the FULL
        # candidate set, gates.templates_without_a_death_ruling() now names
        # a strict subset of it (just Carlos). What is still true, and is
        # what this test now proves: the candidates a ruling COULD cover
        # and the candidates STILL refused always differ by exactly the
        # templates some ruling actually covers -- no candidate appears or
        # vanishes on either side unaccounted for.
        full = frozenset(proposal.full_roster_template_ids())
        refused = frozenset(gates.templates_without_a_death_ruling())
        self.assertTrue(refused <= full)
        self.assertEqual(
            full - refused, frozenset(proposal.option_b_roster_minus_carlos()))

    def test_is_exactly_the_seven_templates_named_in_the_COO_letter(self):
        self.assertEqual(
            proposal.full_roster_template_ids(),
            (343, 345, 348, 350, 353, 355, 924))

    def test_is_ascending_with_no_duplicate(self):
        ids = proposal.full_roster_template_ids()
        self.assertEqual(ids, tuple(sorted(set(ids))))


class PlayerBodyTemplateIdsTests(unittest.TestCase):

    def test_is_exactly_carlos(self):
        self.assertEqual(
            proposal.player_body_template_ids(),
            (proposal.CARLOS_TEMPLATE_ID,))
        self.assertEqual(proposal.CARLOS_TEMPLATE_ID, 924)

    def test_matches_an_independent_read_of_the_raw_table_rows(self):
        # Read HOSTILE_PLACEMENTS' own tuples directly (index 5 is the
        # outfit column) rather than through field_mob_hostile_bg0015's
        # FieldMob-typed path the module under test reads -- an agreement
        # here is a real cross-check, not the same code counted twice.
        by_template: dict[int, set[str]] = {}
        for row in field_mob_tables_bg0015.HOSTILE_PLACEMENTS:
            by_template.setdefault(row[1], set()).add(row[5])
        for template_id, outfits in by_template.items():
            self.assertEqual(
                len(outfits), 1,
                "template %d ships more than one outfit: %r" % (
                    template_id, outfits))
        player_bodies = tuple(sorted(
            template_id for template_id, outfits in by_template.items()
            if next(iter(outfits)).startswith("P_")))
        self.assertEqual(player_bodies, proposal.player_body_template_ids())

    def test_the_other_six_are_all_monster_model_M0_prefixed(self):
        carlos = frozenset(proposal.player_body_template_ids())
        by_template: dict[int, str] = {
            row[1]: row[5] for row in field_mob_tables_bg0015.HOSTILE_PLACEMENTS
        }
        for template_id in proposal.full_roster_template_ids():
            if template_id in carlos:
                continue
            self.assertTrue(
                by_template[template_id].startswith("M0"),
                "template %d (%r) was expected to be a monster-model "
                "outfit" % (template_id, by_template[template_id]))

    def test_this_is_a_roster_scoped_fact_not_a_general_rule(self):
        # This project already ships a killable P_-prefixed body elsewhere
        # (Navy soldiers, scene2_prison_exile_tables) -- this module's own
        # docstring says so, and this test pins that the claim being made
        # here is narrower than "P_ means protected".  Nothing to assert
        # beyond the docstring existing would be circular; what matters is
        # that no function in this module claims the general rule. Grepping
        # the module source for an over-broad claim is the honest way to
        # pin a NEGATIVE ("this module never says the general version").
        source = Path(
            SRC / "pirateforce_foundation"
            / "mob_death_bg0015_ruling_proposal.py").read_text(
                encoding="ascii")
        flattened = " ".join(source.split())
        self.assertIn("NOT OFFERED AS A GENERAL RULE", flattened)


class TemplateOutfitFailsClosedTests(unittest.TestCase):
    """Acceptance criterion: two placements of one template id disagreeing
    on outfit must RAISE, never silently pick one, in
    :func:`player_body_template_ids` (the only public caller of the
    private ``_template_outfits`` helper)."""

    def _stand_in(self, template_id, visual_preset, placement_index):
        return field_mobs.FieldMob(
            placement_index=placement_index, template_id=template_id,
            x=0.0, y=0.0, z=0.0, visual_preset=visual_preset,
            display_name="STAND-IN", level=1, rank=1, ai_wander=1,
            ai_combat=1, speed_walk=100, max_hp=1, drops_normal=0,
            drops_equipment=0, drops_specially=0,
            scene=field_mob_tables_bg0015.SCENE,
        )

    def test_disagreeing_outfits_for_one_template_raise(self):
        conflicting = (
            self._stand_in(9001, "M020_000_000_N", 9001),
            self._stand_in(9001, "P_MALE_033_000_CARLOS", 9002),
        )
        original = field_mob_hostile_bg0015.scene14_hostile_roster
        field_mob_hostile_bg0015.scene14_hostile_roster = lambda: conflicting
        try:
            with self.assertRaises(proposal.MobDeathBg0015ProposalError):
                proposal.player_body_template_ids()
        finally:
            field_mob_hostile_bg0015.scene14_hostile_roster = original
        # And the real roster (no stub) is unaffected afterwards.
        self.assertEqual(proposal.player_body_template_ids(), (924,))


class OverlapsWithRegisteredRulingsTests(unittest.TestCase):

    def test_is_the_six_option_b_covers_now(self):
        # ~~is empty at HEAD~~ WITHDRAWN round n3wqrt-successor:
        # COO-RULING-20260901-1046 (mob_death.py) now covers exactly
        # option_b_roster_minus_carlos()'s six ids, so the intersection with
        # Bg0015's seven candidates is that same six, not empty.
        self.assertEqual(
            proposal.overlaps_with_registered_rulings(),
            frozenset(proposal.option_b_roster_minus_carlos()))

    def test_is_measured_against_the_real_dict_not_a_copy(self):
        # Corrupt a candidate id into a fake registered ruling and confirm
        # the function notices -- proves it reads mob_death.WIDENING_RULINGS
        # live rather than a value cached at import time.  345 is a real
        # option-B id already covered by COO-RULING-20260901-1046, so it is
        # a poor choice for "the fake ruling changed the answer" -- 924
        # (Carlos) is the one candidate no registered ruling covers today,
        # so adding a fake ruling for it is the only choice that proves the
        # function re-reads the live dict rather than a cached baseline.
        fake_name = "TEST-ONLY-fake-ruling-does-not-authorise-anything"
        self.assertNotIn(fake_name, mob_death.WIDENING_RULINGS)
        baseline = proposal.overlaps_with_registered_rulings()
        self.assertNotIn(924, baseline)
        mob_death.WIDENING_RULINGS[fake_name] = frozenset({924})
        try:
            self.assertEqual(
                proposal.overlaps_with_registered_rulings(),
                baseline | frozenset({924}))
        finally:
            del mob_death.WIDENING_RULINGS[fake_name]
        # And it is really back to baseline afterwards.
        self.assertEqual(
            proposal.overlaps_with_registered_rulings(), baseline)


class OptionsTests(unittest.TestCase):

    def test_option_a_is_the_full_seven(self):
        self.assertEqual(
            proposal.option_a_full_roster(),
            proposal.full_roster_template_ids())

    def test_option_b_excludes_only_carlos(self):
        self.assertEqual(
            proposal.option_b_roster_minus_carlos(),
            (343, 345, 348, 350, 353, 355))
        self.assertNotIn(
            proposal.CARLOS_TEMPLATE_ID,
            proposal.option_b_roster_minus_carlos())

    def test_option_b_is_option_a_minus_exactly_carlos(self):
        a = frozenset(proposal.option_a_full_roster())
        b = frozenset(proposal.option_b_roster_minus_carlos())
        self.assertEqual(a - b, frozenset({proposal.CARLOS_TEMPLATE_ID}))
        self.assertTrue(b <= a)

    def test_option_c_is_empty(self):
        self.assertEqual(proposal.option_c_defer_the_whole_roster(), ())

    def test_options_nest_c_within_b_within_a(self):
        c = frozenset(proposal.option_c_defer_the_whole_roster())
        b = frozenset(proposal.option_b_roster_minus_carlos())
        a = frozenset(proposal.option_a_full_roster())
        self.assertTrue(c <= b <= a)


class RegisteredRulingMatchesOptionBTests(unittest.TestCase):
    """The COO answered this module's own three options with OPTION B
    (notes_to_chief/20260901_1046_COO-DECISION-...); this class proves the
    ruling ``mob_death.py`` now carries is that answer, re-derived from the
    same roster this module reads rather than trusted as two hand-typed
    literals agreeing by luck -- the discipline every other ruling in
    ``mob_death.WIDENING_RULINGS`` is already held to
    (``test_the_bg0002_ruling_covers_exactly_the_real_bg0002_rosters_
    templates`` in ``tests/test_mob_death.py`` is the sibling of this one)."""

    RULING_NAME = "COO-RULING-20260901-1046"

    def test_ruling_is_registered(self):
        self.assertIn(self.RULING_NAME, mob_death.WIDENING_RULINGS)

    def test_covered_templates_equal_option_b_exactly(self):
        self.assertEqual(
            mob_death.WIDENING_RULINGS[self.RULING_NAME],
            frozenset(proposal.option_b_roster_minus_carlos()))

    def test_carlos_is_not_a_member(self):
        self.assertNotIn(
            proposal.CARLOS_TEMPLATE_ID,
            mob_death.WIDENING_RULINGS[self.RULING_NAME])

    def test_ruling_is_tied_to_bg0015s_own_scene(self):
        self.assertEqual(
            mob_death.WIDENING_RULING_SCENES[self.RULING_NAME],
            field_mob_tables_bg0015.SCENE)

    def test_ruling_for_answers_this_name_for_all_six_real_rows(self):
        carlos = proposal.CARLOS_TEMPLATE_ID
        six = frozenset(proposal.option_b_roster_minus_carlos())
        seen_templates = set()
        for mob in field_mob_hostile_bg0015.scene14_hostile_roster():
            if mob.template_id == carlos:
                continue
            self.assertIn(
                mob.template_id, six,
                "a Bg0015 row outside option B's six ids and outside "
                "Carlos exists -- the roster changed under this test")
            self.assertEqual(mob_death.ruling_for(mob), self.RULING_NAME)
            seen_templates.add(mob.template_id)
        self.assertEqual(seen_templates, six)

    def test_registering_bg0015_gate_1_is_untouched_by_this_ruling(self):
        # The COO letter's own words: registering a ruling and opening
        # gate 1 (field_mobs._SCENE_TABLE_MODULES) are two separate
        # matters. Confirm the second one really did not move.
        self.assertFalse(gates.roster_gate_open())


class DoesNotRegisterAnythingTests(unittest.TestCase):
    """Acceptance criterion this round: importing/calling this module must
    not move the gate it is only allowed to measure."""

    def test_widening_rulings_unchanged_after_every_function_runs(self):
        before = {
            name: frozenset(templates)
            for name, templates in mob_death.WIDENING_RULINGS.items()
        }
        proposal.full_roster_template_ids()
        proposal.player_body_template_ids()
        proposal.overlaps_with_registered_rulings()
        proposal.option_a_full_roster()
        proposal.option_b_roster_minus_carlos()
        proposal.option_c_defer_the_whole_roster()
        after = {
            name: frozenset(templates)
            for name, templates in mob_death.WIDENING_RULINGS.items()
        }
        self.assertEqual(before, after)

    def test_the_gate_this_module_studies_is_unmoved_by_this_module(self):
        # Renamed from "...is_still_exactly_as_closed_as_before" (round
        # n3wqrt-successor): the gate DID move, but not because of this
        # module -- mob_death.py registering COO-RULING-20260901-1046 moved
        # it, and this test's job is only to confirm THIS FILE (pure
        # derivation, asserted unmoved above) is not what did it. Pinned to
        # today's real answer, six ruled and Carlos refused, re-derived
        # rather than the pre-ruling seven this test used to hand-copy.
        self.assertEqual(gates.templates_without_a_death_ruling(), (924,))
        self.assertEqual(
            frozenset(proposal.full_roster_template_ids())
            - frozenset(gates.templates_without_a_death_ruling()),
            frozenset(proposal.option_b_roster_minus_carlos()))


if __name__ == "__main__":
    unittest.main()
