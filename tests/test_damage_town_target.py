"""LANE-CS: the R322C pin -- the first damage number watched on the lane's
standard test dummy.

Read `src/pirateforce_foundation/damage_town_target.py`'s docstring first; it
carries the provenance for every observed number asserted here.
"""

import ast
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import damage_town_target
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_combat
from pirateforce_foundation import runtime


MODULE_PATH = (pathlib.Path(damage_town_target.__file__)).resolve()


class TownTargetIsTheShippedDummy(unittest.TestCase):

    def test_the_row_is_the_named_practice_dummy(self):
        mob = damage_town_target.town_target_mob()
        self.assertEqual(mob.template_id, field_mobs.TOWN_TARGET_N_ID)
        self.assertEqual(mob.display_name, field_mobs.TOWN_TARGET_NAME)
        self.assertEqual(mob.level, field_mobs.TOWN_TARGET_LEVEL)
        self.assertEqual(mob.max_hp, field_mobs.TOWN_TARGET_MAX_HP)

    def test_all_four_shipped_dummies_share_one_defender_shape(self):
        rows = [mob for mob in field_mobs.load_roster()
                if mob.template_id == field_mobs.TOWN_TARGET_N_ID]
        self.assertGreater(len(rows), 0)
        self.assertEqual(
            {mob_combat.mob_defender(mob) for mob in rows},
            {damage_town_target.town_target_defender()},
        )

    def test_the_defender_record_is_the_one_production_builds(self):
        mob = damage_town_target.town_target_mob()
        self.assertEqual(
            damage_town_target.town_target_defender(),
            mob_combat.mob_defender(mob),
        )


class TheNumberTheOwnerSaw(unittest.TestCase):
    """R322C, GT-274 PASS, OBSERVER_CONFIRMED 2026-09-07T01:48+07:00."""

    def test_one_hit_from_the_production_attacker_is_the_watched_891(self):
        # The attacker is NOT re-typed here: it is the record runtime hands
        # every player today, so if that constant is ever pointed at the real
        # character this pin is what notices.
        self.assertEqual(
            damage_town_target.on_screen_damage(
                runtime.MOB_COMBAT_DEFAULT_ATTACKER),
            damage_town_target.R322C_OBSERVED_DAMAGE_PER_HIT,
        )

    def test_the_four_hit_hp_ladder_matches_the_console_trace(self):
        self.assertEqual(
            damage_town_target.hp_after_hits(
                runtime.MOB_COMBAT_DEFAULT_ATTACKER,
                damage_town_target.R322C_OBSERVED_HP_BEFORE,
                damage_town_target.R322C_OBSERVED_HITS,
            ),
            damage_town_target.R322C_OBSERVED_HP_AFTER,
        )

    def test_the_watched_number_is_nowhere_near_the_min_hit_floor(self):
        # A pin that silently sits on the clamp would keep passing after the
        # formula collapsed, so the pin states it is off the floor.
        self.assertGreater(
            damage_town_target.R322C_OBSERVED_DAMAGE_PER_HIT,
            mob_combat.MIN_HIT,
        )
        self.assertLess(
            damage_town_target.R322C_OBSERVED_DAMAGE_PER_HIT,
            field_mobs.TOWN_TARGET_MAX_HP,
        )

    def test_hits_and_hp_refuse_nonsense_by_name(self):
        for bad in (-1, True, 1.0, "4"):
            with self.assertRaises(damage_town_target.TownTargetDamageError):
                damage_town_target.hp_after_hits(
                    runtime.MOB_COMBAT_DEFAULT_ATTACKER, 100, bad)
            with self.assertRaises(damage_town_target.TownTargetDamageError):
                damage_town_target.hp_after_hits(
                    runtime.MOB_COMBAT_DEFAULT_ATTACKER, bad, 1)

    def test_the_ladder_floors_at_zero_rather_than_going_negative(self):
        self.assertEqual(
            damage_town_target.hp_after_hits(
                runtime.MOB_COMBAT_DEFAULT_ATTACKER, 10, 1000),
            0,
        )


class TheClassCannotEnterTheNumber(unittest.TestCase):
    """GT-274 saw the pose change with the class and the number not.

    The pose half is LANE-B's `combat_pose` and is asserted in its own tests.
    What is asserted here is the other half, structurally: there is no class
    term and no skill term anywhere in the record the formula reads, so a
    round that believes it made damage class-dependent without touching
    `Combatant` has believed something this test can refute.
    """

    def test_the_combatant_record_carries_no_class_or_skill_field(self):
        fields = set(mob_combat.Combatant.__dataclass_fields__)
        self.assertEqual(fields, {"level", "ability_str", "ability_con"})

    def test_two_attackers_differing_only_in_nothing_but_class_cannot_exist(self):
        # Stated as construction rather than prose: the record cannot even be
        # built with a class, which is why the number cannot depend on one.
        with self.assertRaises(TypeError):
            mob_combat.Combatant(
                level=1, ability_str=1, ability_con=0, class_id=2)


class ThisModuleAddsNoArithmeticOfItsOwn(unittest.TestCase):

    FORMULA_NAMES = (
        "ATK_BASE", "K_ATK_STR", "K_ATK_LV",
        "DEF_BASE", "K_DEF_CON", "K_DEF_LV",
        "MOB_ABILITY_CON", "MIN_HIT",
    )

    def test_it_defines_none_of_the_formula_constants(self):
        tree = ast.parse(MODULE_PATH.read_text(encoding="ascii"))
        assigned = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for name in self.FORMULA_NAMES:
            self.assertNotIn(name, assigned, "%s re-typed here" % name)

    def test_the_only_module_level_numbers_are_the_four_observations(self):
        tree = ast.parse(MODULE_PATH.read_text(encoding="ascii"))
        observed = {}
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(
                        node.value, ast.Constant):
                    observed[target.id] = node.value.value
        self.assertEqual(
            observed,
            {
                "R322C_OBSERVED_DAMAGE_PER_HIT": 891,
                "R322C_OBSERVED_HITS": 4,
                "R322C_OBSERVED_HP_BEFORE": 192779,
                "R322C_OBSERVED_HP_AFTER": 189215,
            },
        )


if __name__ == "__main__":
    unittest.main()
