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

    def test_matches_the_gates_modules_own_refused_measurement(self):
        # Two independent readers of the same roster must agree, or one of
        # them is wrong -- neither is a literal the other one copied.
        self.assertEqual(
            proposal.full_roster_template_ids(),
            gates.templates_without_a_death_ruling())

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

    def test_is_empty_at_head(self):
        self.assertEqual(proposal.overlaps_with_registered_rulings(), frozenset())

    def test_is_measured_against_the_real_dict_not_a_copy(self):
        # Corrupt a candidate id into a fake registered ruling and confirm
        # the function notices -- proves it reads mob_death.WIDENING_RULINGS
        # live rather than a value cached at import time.
        fake_name = "TEST-ONLY-fake-ruling-does-not-authorise-anything"
        self.assertNotIn(fake_name, mob_death.WIDENING_RULINGS)
        mob_death.WIDENING_RULINGS[fake_name] = frozenset({343})
        try:
            self.assertEqual(
                proposal.overlaps_with_registered_rulings(), frozenset({343}))
        finally:
            del mob_death.WIDENING_RULINGS[fake_name]
        # And it is really gone again afterwards.
        self.assertEqual(proposal.overlaps_with_registered_rulings(), frozenset())


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

    def test_the_gate_studied_is_still_exactly_as_closed_as_before(self):
        self.assertEqual(
            gates.templates_without_a_death_ruling(),
            (343, 345, 348, 350, 353, 355, 924))


if __name__ == "__main__":
    unittest.main()
