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


# The exact `action_u32_30` values GT-243 captured (attended, reproduced
# twice each) -- pf_bridge/notes_to_chief/20260906_0155_KA1A-R320-RESULTS-
# group2-GT266-257-255-230-243-RE235-237-261.md section "GT-243".
_GT243_WIELD_Z_ACTION_U32_30 = 0x0000EA7E
_GT243_SKILL_110_ACTION_U32_30 = 0x0000006E  # 110 decimal


class CandidateSkillIdFromActionFieldsTests(unittest.TestCase):
    """`candidate_skill_id_from_action_fields` has zero callers today (see
    the module docstring's GT-243 update) -- these tests pin its behavior
    against the exact bytes GT-243 measured, not invented fixtures, so a
    future caller inherits a function already proven against the one real
    capture that exists rather than one only ever exercised with made-up
    numbers."""

    def test_wield_z_with_no_weapon_returns_none(self):
        fields = {"action_u32_30": _GT243_WIELD_Z_ACTION_U32_30}
        got = damage_by_skill.candidate_skill_id_from_action_fields(
            fields, wield_action_code=_GT243_WIELD_Z_ACTION_U32_30)
        self.assertIsNone(got)

    def test_skill_110_hotbar_click_returns_110(self):
        fields = {"action_u32_30": _GT243_SKILL_110_ACTION_U32_30}
        got = damage_by_skill.candidate_skill_id_from_action_fields(
            fields, wield_action_code=_GT243_WIELD_Z_ACTION_U32_30)
        self.assertEqual(got, 110)

    def test_wield_action_code_has_no_default_hardcoding_it(self):
        """Guards the "no second copy of 0xEA7E" claim in the docstring:
        `wield_action_code` must stay a REQUIRED parameter with no default
        -- a default of `0xEA7E` would be exactly the second copy of the
        frozen v141 constant this function is designed to avoid, and would
        still pass every other test above (they always pass it explicitly)."""
        import inspect
        sig = inspect.signature(
            damage_by_skill.candidate_skill_id_from_action_fields)
        self.assertIs(
            sig.parameters["wield_action_code"].default, inspect.Parameter.empty)

    def test_only_the_action_u32_30_key_is_required(self):
        """A minimal fields dict (just the one key this function reads)
        must work -- proves this does not accidentally require the rest of
        the `ActionVital` shape `action_ack.py`'s stricter gate needs."""
        fields = {"action_u32_30": 12345}
        got = damage_by_skill.candidate_skill_id_from_action_fields(
            fields, wield_action_code=_GT243_WIELD_Z_ACTION_U32_30)
        self.assertEqual(got, 12345)

    def test_missing_key_raises_rather_than_guessing(self):
        with self.assertRaises(KeyError):
            damage_by_skill.candidate_skill_id_from_action_fields(
                {}, wield_action_code=_GT243_WIELD_Z_ACTION_U32_30)

    def test_exported_in_dunder_all(self):
        self.assertIn(
            "candidate_skill_id_from_action_fields", damage_by_skill.__all__)


class CandidateSkillIdIsAKnownSkillTests(unittest.TestCase):
    """`candidate_skill_id_is_a_known_skill` (round `sar0vq`) -- pinned
    against the real GT-243 hex (skill 110, a real starting-kit id) and a
    synthetic value chosen to sit outside the 8-id catalog, not invented
    "plausible" numbers."""

    def test_gt243_skill_110_is_a_known_skill(self):
        candidate = damage_by_skill.candidate_skill_id_from_action_fields(
            {"action_u32_30": _GT243_SKILL_110_ACTION_U32_30},
            wield_action_code=_GT243_WIELD_Z_ACTION_U32_30)
        self.assertTrue(
            damage_by_skill.candidate_skill_id_is_a_known_skill(candidate))

    def test_a_value_outside_the_8_id_catalog_is_not_a_known_skill(self):
        outside_catalog = max(skill_catalog.STARTING_KIT_SKILL_IDS) + 1
        self.assertNotIn(outside_catalog, skill_catalog.STARTING_KIT_SKILL_IDS)
        self.assertFalse(
            damage_by_skill.candidate_skill_id_is_a_known_skill(outside_catalog))

    def test_every_starting_kit_id_is_a_known_skill(self):
        """Every one of the 8 real ids must read True -- this is a catalog
        membership check, not the (already refused-by-name-elsewhere)
        attack-vs-not-attack classification."""
        for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                self.assertTrue(
                    damage_by_skill.candidate_skill_id_is_a_known_skill(skill_id))

    def test_delegates_to_skill_catalog_is_known_skill_id(self):
        """Not a second copy of the catalog membership rule -- proven by
        mocking the real accessor and checking it is actually called."""
        with mock.patch.object(
            skill_catalog, "is_known_skill_id", return_value=True
        ) as mocked:
            result = damage_by_skill.candidate_skill_id_is_a_known_skill(99)
        mocked.assert_called_once_with(99)
        self.assertTrue(result)

    def test_exported_in_dunder_all(self):
        self.assertIn(
            "candidate_skill_id_is_a_known_skill", damage_by_skill.__all__)


if __name__ == "__main__":
    unittest.main()
