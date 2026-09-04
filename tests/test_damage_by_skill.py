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
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    damage_by_skill,
    damage_model_hypothesis,
    field_mobs,
    hostile_hp_link_hypothesis,
    mob_combat,
    skill_catalog,
)


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

    def test_the_formula_constants_also_match_the_other_two_proven_copies(self):
        """Literal compliance with COO condition (a): a direct cross-check
        against BOTH hypothesis modules, not only identity with mob_combat.
        Redundant with identity today (mob_combat.py's own
        ``test_the_formula_constants_are_the_proven_ones`` already ties those
        two to mob_combat), but this file must not depend on that other
        file's test surviving (pf-adversary this round, D3)."""
        for name in ("ATK_BASE", "K_ATK_STR", "K_ATK_LV", "DEF_BASE",
                     "K_DEF_CON", "K_DEF_LV", "MIN_HIT"):
            here = getattr(mob_combat, name)
            self.assertEqual(here, getattr(damage_model_hypothesis, name))
            self.assertEqual(here, getattr(hostile_hp_link_hypothesis, name))

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
        # The attacker `runtime.py` actually sends today (`MOB_COMBAT_DEFAULT_
        # ATTACKER = mob_combat.pin_attacker()`), as opposed to the arbitrary
        # stand-in above -- see test_normal_attack_against_916_with_the_
        # production_pin_attacker below for why this needs its own case.
        cls.production_attacker = mob_combat.pin_attacker()

    def test_normal_attack_matches_the_bare_formula_against_916(self):
        expected = mob_combat.resolve_damage(self.attacker, self.defender)
        got = damage_by_skill.resolve_skill_damage(
            99, self.attacker, self.defender)
        self.assertEqual(got, expected)

    def test_normal_attack_against_916_with_the_production_pin_attacker(self):
        """The two tests above use ``Combatant(level=27, ability_str=132,
        ability_con=10)``, the same arbitrary stand-in ``test_mob_combat.py``
        uses for its own generic formula checks -- it proves the GATE passes
        an attacker through unchanged, but it is not the attacker a real hit
        would ever carry.  ``runtime.py`` binds exactly one attacker to
        production combat: ``MOB_COMBAT_DEFAULT_ATTACKER = mob_combat.
        pin_attacker()``.  This is the number this module will actually
        return against the house's standard test field (Training Iron Man,
        template 916) the day the still-unanswered CORE-REQUEST (which
        ActionVital field carries the skill id, pf_bridge/notes_to_chief/
        20260904_1041_...) is answered and something calls
        ``resolve_skill_damage(99, ...)`` for real -- so it should already be
        on the record, not left to be discovered the first time that wiring
        lands.

        891 is not invented here: it is re-derived from the same named
        formula constants this test file already cross-checks against both
        hypothesis modules (``TheFormulaIsImportedNotCopiedTests`` above),
        not a bare literal with no path back to them, and it matches
        mob_combat.py's own existing costing comment for this exact
        defender ("level 100, 198125 HP: defence 154 -> 891 dmg ->
        223 hits") word for word -- this test is the first to reach that
        number THROUGH the CS-owned skill-99 gate rather than by calling
        ``mob_combat.resolve_damage``/``strike`` directly.
        """
        expected_attack = (
            mob_combat.ATK_BASE
            + mob_combat.K_ATK_STR * self.production_attacker.ability_str
            + mob_combat.K_ATK_LV * self.production_attacker.level)
        expected_defence = (
            mob_combat.DEF_BASE
            + mob_combat.K_DEF_CON * self.defender.ability_con
            + mob_combat.K_DEF_LV * self.defender.level)
        expected_damage = max(
            mob_combat.MIN_HIT, expected_attack - expected_defence)
        self.assertEqual(expected_damage, 891)

        got = damage_by_skill.resolve_skill_damage(
            99, self.production_attacker, self.defender)
        self.assertEqual(got, expected_damage)
        self.assertEqual(
            got, mob_combat.resolve_damage(
                self.production_attacker, self.defender))

    def test_the_916_dummy_this_pin_uses_is_the_one_hand_verified(self):
        """Guards the assumption ``test_normal_attack_against_916_with_the_
        production_pin_attacker`` depends on but never checks itself:
        ``field_mobs.load_roster()`` carries four separate placement rows
        for template 916 (Training Iron Man has four dummies in Port
        Royal), and ``next(m for m in roster if m.template_id == 916)``
        picks whichever one sorts first.  The hard-pinned 891 above is only
        safe if every one of those rows shares the same level/HP/defence --
        if a future roster edit gave one dummy a different level, this
        picks-the-first-match pattern would go on returning a stale number
        instead of failing loudly."""
        roster = field_mobs.load_roster()
        dummies = [
            mob for mob in roster
            if mob.template_id == TRAINING_IRON_MAN_TEMPLATE_ID]
        self.assertGreaterEqual(
            len(dummies), 2,
            "expected more than one Training Iron Man placement to make "
            "this check meaningful")
        defences = {mob_combat.mob_defender(mob).defence for mob in dummies}
        self.assertEqual(
            defences, {154},
            "the four Training Iron Man placements no longer share one "
            "defence value -- the pinned 891 in the test above only covers "
            "the row `next()` happens to pick")

    def test_normal_attack_is_classified(self):
        self.assertTrue(damage_by_skill.is_classified_attack_skill(99))

    def test_resolve_skill_damage_actually_calls_the_imported_function(self):
        """Not redundant with the identity tests in
        ``TheFormulaIsImportedNotCopiedTests`` (pf-adversary this round, D1,
        reproduced by mutation): a version of ``resolve_skill_damage`` that
        stops calling ``resolve_damage`` and instead inlines the exact same
        arithmetic with numeric literals leaves the (now merely unused)
        import untouched, so the identity tests still pass and the AST
        no-assignment test never fires -- nothing else in this file would
        have noticed a real fourth copy.  Patching the module-level name and
        checking the call goes THROUGH it is the one thing an inlined
        rewrite cannot survive."""
        sentinel = object()
        with mock.patch.object(damage_by_skill, "resolve_damage",
                                return_value=sentinel) as patched:
            got = damage_by_skill.resolve_skill_damage(
                99, self.attacker, self.defender)
        patched.assert_called_once_with(self.attacker, self.defender)
        self.assertIs(got, sentinel)

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
