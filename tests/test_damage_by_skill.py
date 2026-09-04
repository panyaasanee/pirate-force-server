"""LANE-CS: tests for ``damage_by_skill``, the first skill-id-gated damage
module in this lane's own territory.

``TheFormulaIsImportedNotCopiedTests`` is the one that matters most: it
proves by identity (``is``), not by equal value, that this module holds no
fourth copy of the formula -- a value-equality check would still pass the
day somebody pastes the six constants in here "for convenience" and they
happen to still match, right up until one of the three existing copies is
edited and this one is not.

``ResolveSkillDamageTests`` exercises the gate against the project's
standard test subject, Training Iron Man (``template_id`` 916): skill 99
("Normal Attack") must produce the exact number ``mob_combat.resolve_damage``
would, and every other starting-kit skill id must be refused by name, not
silently treated as zero damage.
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import damage_by_skill, field_mobs, mob_combat, skill_catalog


TRAINING_IRON_MAN_TEMPLATE_ID = 916

_FORMULA_CONSTANT_NAMES = (
    "ATK_BASE", "K_ATK_STR", "K_ATK_LV",
    "DEF_BASE", "K_DEF_CON", "K_DEF_LV", "MIN_HIT",
)


class TheFormulaIsImportedNotCopiedTests(unittest.TestCase):

    def test_resolve_damage_is_the_same_function_object(self):
        self.assertIs(damage_by_skill.resolve_damage, mob_combat.resolve_damage)

    def test_combatant_is_the_same_class_object(self):
        self.assertIs(damage_by_skill.Combatant, mob_combat.Combatant)

    def test_no_formula_constant_is_assigned_in_this_module(self):
        """AST check, not just "it works today": a future edit that pastes
        ``ATK_BASE = 100`` etc. back into this file would still pass the
        identity tests above (the import line would just become unused) --
        this is what actually catches a fourth copy being reintroduced."""
        source = (ROOT / "src/pirateforce_foundation/damage_by_skill.py").read_text(
            encoding="utf-8")
        tree = ast.parse(source)
        assigned = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    assigned.add(target.id)
        collision = assigned.intersection(_FORMULA_CONSTANT_NAMES)
        self.assertEqual(
            collision, set(),
            "damage_by_skill.py assigns %r itself -- the formula must be "
            "imported from mob_combat, never re-declared here" % (collision,))


class ResolveSkillDamageTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        roster = field_mobs.load_roster()
        cls.training_iron_man = next(
            mob for mob in roster
            if mob.template_id == TRAINING_IRON_MAN_TEMPLATE_ID)
        cls.defender = mob_combat.mob_defender(cls.training_iron_man)
        cls.attacker = damage_by_skill.Combatant(
            level=27, ability_str=132, ability_con=10)

    def test_normal_attack_matches_the_bare_formula_against_916(self):
        expected = mob_combat.resolve_damage(self.attacker, self.defender)
        got = damage_by_skill.resolve_skill_damage(
            99, self.attacker, self.defender)
        self.assertEqual(got, expected)

    def test_normal_attack_is_classified(self):
        self.assertTrue(damage_by_skill.is_classified_attack_skill(99))

    def test_every_other_starting_kit_skill_is_refused_not_guessed(self):
        others = [
            skill_id for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS
            if skill_id != 99
        ]
        self.assertTrue(others, "the starting-kit catalog only has skill 99?")
        for skill_id in others:
            self.assertFalse(damage_by_skill.is_classified_attack_skill(skill_id))
            with self.assertRaises(damage_by_skill.DamageBySkillError):
                damage_by_skill.resolve_skill_damage(
                    skill_id, self.attacker, self.defender)

    def test_a_skill_id_outside_the_catalog_is_refused_as_unknown(self):
        unknown_skill_id = 12345
        self.assertFalse(skill_catalog.is_known_skill_id(unknown_skill_id))
        with self.assertRaises(damage_by_skill.DamageBySkillError) as ctx:
            damage_by_skill.resolve_skill_damage(
                unknown_skill_id, self.attacker, self.defender)
        self.assertIn("not in the starting-kit catalog", str(ctx.exception))

    def test_unknown_and_unclassified_are_distinguishable_messages(self):
        # skill 110 ("Strive Jump") is a KNOWN but unclassified id; its
        # refusal message must not read like the "unknown id" case above.
        with self.assertRaises(damage_by_skill.DamageBySkillError) as ctx:
            damage_by_skill.resolve_skill_damage(
                110, self.attacker, self.defender)
        self.assertIn("not yet classified", str(ctx.exception))
        self.assertNotIn("not in the starting-kit catalog", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
