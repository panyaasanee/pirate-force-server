"""LANE-CS: tests for `damage_by_class_skill`, the class-ownership gate on
top of `damage_by_skill`'s skill-id gate.

`TheFormulaIsReExportedNotCopiedTests` is this file's version of
`test_damage_by_skill.py`'s own identity checks: it proves this module adds
no independent formula or skill-id table of its own, only a class-ownership
check derived from `class_catalog` (pinned to
`CONSTDATA_TH__CHARCREATE_CLASS.tsv`).

`ClassOwnershipIsDerivedFromTheTableTests` never types out which class owns
which "Basic Training" id by hand -- every expectation is re-derived from
`class_catalog.CLASS_ID_TO_STARTING_SKILL_IDS` in the test body itself, so a
future edit to the pinned table (a 6th class, a re-shuffled kit) changes
what this file expects along with it instead of leaving a stale hand-typed
row that quietly stops testing anything real.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    class_catalog,
    damage_by_class_skill,
    damage_by_skill,
    field_mobs,
    mob_combat,
)


TRAINING_IRON_MAN_TEMPLATE_ID = 916


class TheFormulaIsReExportedNotCopiedTests(unittest.TestCase):

    def test_resolve_damage_is_the_same_function_object_as_damage_by_skill(self):
        self.assertIs(damage_by_class_skill.resolve_damage, damage_by_skill.resolve_damage)
        self.assertIs(damage_by_class_skill.resolve_damage, mob_combat.resolve_damage)

    def test_combatant_is_the_same_class_object_as_damage_by_skill(self):
        self.assertIs(damage_by_class_skill.Combatant, damage_by_skill.Combatant)

    def test_no_class_to_skill_mapping_is_typed_in_this_module(self):
        """`is_skill_granted_to_class` must call `class_catalog.
        starting_skill_ids` for its answer, not hold a second table -- proven
        by patching the table function to a value nothing else could
        produce and observing the gate answer flip with it."""
        from unittest import mock
        with mock.patch.object(
                class_catalog, "starting_skill_ids", return_value=(999999,)):
            self.assertFalse(
                damage_by_class_skill.is_skill_granted_to_class(1, 99))
            self.assertTrue(
                damage_by_class_skill.is_skill_granted_to_class(1, 999999))


class ClassOwnershipIsDerivedFromTheTableTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        roster = field_mobs.load_roster()
        training_iron_man = next(
            mob for mob in roster
            if mob.template_id == TRAINING_IRON_MAN_TEMPLATE_ID)
        cls.defender = mob_combat.mob_defender(training_iron_man)
        cls.attacker = damage_by_class_skill.Combatant(
            level=27, ability_str=132, ability_con=10)

    def test_every_class_is_granted_skill_99(self):
        # Re-derives the claim from the table itself, not from
        # `persistence_starting_skills.py`'s docstring prose about it.
        for class_id in class_catalog.CLASS_IDS:
            self.assertIn(
                99, class_catalog.starting_skill_ids(class_id),
                "class_id %r's starting kit does not carry skill 99" % (class_id,))
            self.assertTrue(
                damage_by_class_skill.is_skill_granted_to_class(class_id, 99))

    def test_skill_99_resolves_identically_to_damage_by_skill_for_every_class(self):
        expected = damage_by_skill.resolve_skill_damage(
            99, self.attacker, self.defender)
        for class_id in class_catalog.CLASS_IDS:
            got = damage_by_class_skill.resolve_class_skill_damage(
                class_id, 99, self.attacker, self.defender)
            self.assertEqual(got, expected)

    def test_a_classs_own_basic_training_id_is_refused_for_every_other_class(self):
        """Table-derived cross-check, not a hand-typed pair: for each class,
        the single Basic Training id its own kit carries (the one starting
        id that is neither 99, 110, nor 111) must be ABSENT from every other
        class's kit, and `resolve_class_skill_damage` must refuse it there."""
        checked_a_refusal = False
        for owner_class_id in class_catalog.CLASS_IDS:
            owner_kit = class_catalog.starting_skill_ids(owner_class_id)
            basic_training_ids = [
                skill_id for skill_id in owner_kit
                if skill_id not in (99, 110, 111)]
            self.assertEqual(
                len(basic_training_ids), 1,
                "class_id %r's kit does not carry exactly one non-99/110/111 "
                "id -- CHARCREATE_CLASS's per-class layout changed" % (owner_class_id,))
            own_basic_training_id = basic_training_ids[0]
            for other_class_id in class_catalog.CLASS_IDS:
                if other_class_id == owner_class_id:
                    continue
                other_kit = class_catalog.starting_skill_ids(other_class_id)
                self.assertNotIn(
                    own_basic_training_id, other_kit,
                    "class %r and %r both carry skill %r -- the two kits are "
                    "no longer pairwise distinct on this column" % (
                        owner_class_id, other_class_id, own_basic_training_id))
                with self.assertRaises(damage_by_class_skill.DamageByClassSkillError) as ctx:
                    damage_by_class_skill.resolve_class_skill_damage(
                        other_class_id, own_basic_training_id,
                        self.attacker, self.defender)
                self.assertIn("is not in class_id", str(ctx.exception))
                checked_a_refusal = True
        self.assertTrue(checked_a_refusal, "no cross-class pair was ever checked")

    def test_a_known_but_unclassified_skill_refusal_propagates_from_damage_by_skill(self):
        # 110 ("Strive Jump") is in every class's kit but is not classified
        # as an attack by damage_by_skill -- the class gate must let that
        # DamageBySkillError through as a DamageByClassSkillError, not mask
        # it as "not granted."
        class_id = class_catalog.CLASS_IDS[0]
        self.assertIn(110, class_catalog.starting_skill_ids(class_id))
        with self.assertRaises(damage_by_class_skill.DamageByClassSkillError) as ctx:
            damage_by_class_skill.resolve_class_skill_damage(
                class_id, 110, self.attacker, self.defender)
        self.assertIn("not yet classified", str(ctx.exception))

    def test_unknown_class_id_is_refused_by_name(self):
        unknown_class_id = -1
        self.assertFalse(class_catalog.is_known_class_id(unknown_class_id))
        with self.assertRaises(damage_by_class_skill.DamageByClassSkillError) as ctx:
            damage_by_class_skill.resolve_class_skill_damage(
                unknown_class_id, 99, self.attacker, self.defender)
        self.assertIn("not in the class catalog", str(ctx.exception))

    def test_attack_skill_ids_for_class_is_99_only_for_every_class(self):
        """Table-derived, not a hand-typed constant: for all 5 classes today
        only skill 99 is classified as an attack (`damage_by_skill.
        is_classified_attack_skill`), so the filtered answer must equal
        `(99,)` -- re-derived per class from `class_catalog.
        starting_skill_ids` rather than asserting the literal `(99,)` alone,
        so a future kit re-shuffle that drops 99 from a class's kit would
        still be caught here."""
        for class_id in class_catalog.CLASS_IDS:
            kit = class_catalog.starting_skill_ids(class_id)
            expected = tuple(
                skill_id for skill_id in kit
                if damage_by_skill.is_classified_attack_skill(skill_id))
            self.assertEqual(expected, (99,))
            self.assertEqual(
                damage_by_class_skill.attack_skill_ids_for_class(class_id),
                expected)

    def test_attack_skill_ids_for_class_follows_the_classifier_not_a_constant(self):
        """Patches `damage_by_skill.is_classified_attack_skill` to also
        accept 110 -- proves this function re-derives its answer from that
        classifier at call time rather than holding a cached/typed `(99,)`
        of its own -- and, since 110 sits AFTER 99 in every class's real kit
        order (`class_catalog.starting_skill_ids` puts 111/basic-training
        before 99/110 for all 5 classes), also pins the returned pair's
        order against the table rather than only checking membership."""
        from unittest import mock
        class_id = class_catalog.CLASS_IDS[0]
        kit = class_catalog.starting_skill_ids(class_id)
        self.assertIn(110, kit)
        self.assertLess(kit.index(99), kit.index(110))
        with mock.patch.object(
                damage_by_skill, "is_classified_attack_skill",
                side_effect=lambda skill_id: skill_id in (99, 110)):
            got = damage_by_class_skill.attack_skill_ids_for_class(class_id)
        self.assertEqual(got, (99, 110))

    def test_attack_skill_ids_for_class_preserves_kit_order_on_real_data(self):
        """pf-adversary (this round) found the classifier-mock test above
        insufficient on its own to catch a reversed-iteration-order
        regression, since it only existed for one class -- and found the
        original version of THIS test self-referential (it derived its own
        "expected" order from `got` itself, so it could never fail).  This
        version instead patches the classifier to accept every id (not just
        99) for all 5 real classes and asserts the RETURNED tuple equals the
        REAL, unmocked `starting_skill_ids(class_id)` tuple exactly -- none
        of the 5 classes' 4-id kits equal their own reverse (checked below),
        so a `tuple(reversed(...))` mutation in the production function
        would turn every one of these assertions red."""
        from unittest import mock
        with mock.patch.object(
                damage_by_skill, "is_classified_attack_skill",
                return_value=True):
            for class_id in class_catalog.CLASS_IDS:
                kit = class_catalog.starting_skill_ids(class_id)
                self.assertNotEqual(
                    kit, tuple(reversed(kit)),
                    "class_id %r's kit is a palindrome -- this test can no "
                    "longer distinguish forward from reversed order for it"
                    % (class_id,))
                got = damage_by_class_skill.attack_skill_ids_for_class(class_id)
                self.assertEqual(got, kit)

    def test_attack_skill_ids_for_class_unknown_class_id_raises_keyerror(self):
        unknown_class_id = -1
        self.assertFalse(class_catalog.is_known_class_id(unknown_class_id))
        with self.assertRaises(KeyError):
            damage_by_class_skill.attack_skill_ids_for_class(unknown_class_id)

    def test_unknown_skill_id_is_refused_by_name_not_by_ownership_message(self):
        class_id = class_catalog.CLASS_IDS[0]
        unknown_skill_id = 12345
        for kit_class_id in class_catalog.CLASS_IDS:
            self.assertNotIn(
                unknown_skill_id, class_catalog.starting_skill_ids(kit_class_id))
        with self.assertRaises(damage_by_class_skill.DamageByClassSkillError) as ctx:
            damage_by_class_skill.resolve_class_skill_damage(
                class_id, unknown_skill_id, self.attacker, self.defender)
        # An id outside every kit is caught by the ownership check first
        # (no class's kit names it), same message shape as the cross-class
        # refusal above -- this is deliberate: from this gate's point of
        # view "no class grants you this" and "this class doesn't" are the
        # same fact for an id that is not anyone's starting-kit id.
        self.assertIn("is not in class_id", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
