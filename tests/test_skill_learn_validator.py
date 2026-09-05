"""LANE-CS: `skill_learn_validator.can_afford_to_learn`."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import skill_catalog                # noqa: E402
from pirateforce_foundation.skill_learn_validator import (      # noqa: E402
    SkillLearnValidatorError,
    can_afford_to_learn,
    skill_points_after_learning,
)


class CanAffordToLearnTests(unittest.TestCase):
    def test_smallest_affording_int_balance_affords_every_starting_kit_skill(self):
        # current_skill_points is an int (the wire's own skill_points field
        # is u32, gm/attr_wire.py:438) but costs are floats (99/110/40000..
        # 44000 are 1.0, 111 is ~0.2) -- so "exact balance" for a fractional
        # cost means the smallest int that covers it, math.ceil(cost), not
        # the cost value itself.  Pinned against the table via skill_catalog
        # itself, not a hand-typed cost, so a future table edit moves this
        # test's expectation along with the production accessor it
        # exercises.
        for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                cost = skill_catalog.skill_point_cost_to_learn(skill_id)
                smallest_affording_balance = math.ceil(cost)
                self.assertTrue(
                    can_afford_to_learn(smallest_affording_balance, skill_id)
                )

    def test_one_int_short_of_the_smallest_affording_balance_never_affords(self):
        for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                cost = skill_catalog.skill_point_cost_to_learn(skill_id)
                one_short = math.ceil(cost) - 1
                self.assertFalse(can_afford_to_learn(one_short, skill_id))

    def test_zero_balance_cannot_afford_a_normal_cost_skill(self):
        # skill 99 (Normal Attack) costs 1.0 -- 0 must refuse it.
        self.assertEqual(skill_catalog.skill_point_cost_to_learn(99), 1.0)
        self.assertFalse(can_afford_to_learn(0, 99))

    def test_a_large_surplus_affords_the_cheapest_starting_kit_skill(self):
        # skill 111 (VIP Strive Jump) is the one starting-kit id costing
        # less than 1 point (~0.2, the table's own float32-precision text) --
        # 100 whole points must cover it same as any other id here.
        self.assertLess(skill_catalog.skill_point_cost_to_learn(111), 1.0)
        self.assertTrue(can_afford_to_learn(100, 111))

    def test_unknown_skill_id_raises_key_error_not_a_guessed_bool(self):
        # Conflating "unaffordable" with "unknown skill" would be exactly
        # the invented-meaning mistake skill_catalog.py's own docstring
        # warns against -- this must propagate, not swallow, the lookup
        # failure.
        with self.assertRaises(KeyError):
            can_afford_to_learn(999, skill_id=1)

    def test_negative_balance_refused_not_silently_treated_as_unaffordable(self):
        with self.assertRaises(SkillLearnValidatorError):
            can_afford_to_learn(-1, 99)

    def test_bool_balance_refused_same_as_every_other_int_gate_in_this_project(self):
        with self.assertRaises(TypeError):
            can_afford_to_learn(True, 99)
        with self.assertRaises(TypeError):
            can_afford_to_learn(False, 99)

    def test_non_int_balance_refused(self):
        with self.assertRaises(TypeError):
            can_afford_to_learn("1", 99)
        with self.assertRaises(TypeError):
            can_afford_to_learn(1.0, 99)


class SkillPointsAfterLearningTests(unittest.TestCase):
    """The spend half `can_afford_to_learn`'s docstring names as a caller's
    job -- pure arithmetic, and a refusal (not a guess) on fractional cost."""

    _WHOLE_COST_SKILL_IDS = tuple(
        skill_id for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS
        if skill_catalog.skill_point_cost_to_learn(skill_id).is_integer()
    )
    _FRACTIONAL_COST_SKILL_IDS = tuple(
        skill_id for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS
        if not skill_catalog.skill_point_cost_to_learn(skill_id).is_integer()
    )

    def test_the_catalog_still_has_exactly_one_fractional_cost_id(self):
        # Pins the split this test class's two id groups depend on -- if a
        # future table edit changes which/how-many ids cost a fraction,
        # this fails loudly instead of the two groups quietly drifting.
        self.assertEqual(self._FRACTIONAL_COST_SKILL_IDS, (111,))
        self.assertEqual(len(self._WHOLE_COST_SKILL_IDS), 7)

    def test_exact_balance_spends_to_exactly_zero_for_whole_cost_ids(self):
        for skill_id in self._WHOLE_COST_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                cost = int(skill_catalog.skill_point_cost_to_learn(skill_id))
                self.assertEqual(
                    skill_points_after_learning(cost, skill_id), 0,
                )

    def test_surplus_balance_spends_down_by_exactly_the_cost(self):
        for skill_id in self._WHOLE_COST_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                cost = int(skill_catalog.skill_point_cost_to_learn(skill_id))
                self.assertEqual(
                    skill_points_after_learning(cost + 50, skill_id), 50,
                )

    def test_the_result_is_a_plain_int_never_a_float(self):
        result = skill_points_after_learning(1, 99)
        self.assertIs(type(result), int)

    def test_fractional_cost_id_refuses_rather_than_guessing_a_rounding_rule(self):
        for skill_id in self._FRACTIONAL_COST_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                with self.assertRaises(SkillLearnValidatorError):
                    skill_points_after_learning(100, skill_id)

    def test_fractional_refusal_fires_even_though_the_balance_affords_it(self):
        # Guards against a shortcut implementation that only checks
        # affordability and forgets the separate fractional-cost refusal:
        # 111 costs ~0.2, so a balance of 100 easily affords it, but this
        # must still refuse rather than silently truncating/rounding.
        self.assertTrue(can_afford_to_learn(100, 111))
        with self.assertRaises(SkillLearnValidatorError):
            skill_points_after_learning(100, 111)

    def test_insufficient_balance_refuses_rather_than_returning_negative(self):
        for skill_id in self._WHOLE_COST_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                cost = int(skill_catalog.skill_point_cost_to_learn(skill_id))
                with self.assertRaises(SkillLearnValidatorError):
                    skill_points_after_learning(cost - 1, skill_id)

    def test_unknown_skill_id_raises_key_error_not_a_guessed_result(self):
        with self.assertRaises(KeyError):
            skill_points_after_learning(999, skill_id=1)

    def test_negative_balance_refused_same_as_can_afford_to_learn(self):
        # This does NOT isolate a negative-balance-specific guard inside
        # skill_points_after_learning: every catalog cost is positive, so a
        # negative balance already fails the affordability check this
        # function makes first (pf-adversary verified: with
        # can_afford_to_learn's own negative check removed, this call still
        # raises via the affordability path, not a distinct one here) --
        # the collateral coverage from CanAffordToLearnTests is what
        # actually proves the guard exists.  Pinned anyway so a future
        # refactor that reorders the checks cannot silently start
        # returning a negative balance for THIS function's own inputs.
        with self.assertRaises(SkillLearnValidatorError):
            skill_points_after_learning(-1, 99)

    def test_bool_balance_refused_same_as_can_afford_to_learn(self):
        with self.assertRaises(TypeError):
            skill_points_after_learning(True, 99)
        with self.assertRaises(TypeError):
            skill_points_after_learning(False, 99)

    def test_non_int_balance_refused(self):
        with self.assertRaises(TypeError):
            skill_points_after_learning("1", 99)
        with self.assertRaises(TypeError):
            skill_points_after_learning(1.0, 99)


if __name__ == "__main__":
    unittest.main()
