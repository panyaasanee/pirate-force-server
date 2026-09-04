"""LANE-CS: starting-skill-kit catalog, pinned to the committed client tables."""
from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402
from pirateforce_foundation import class_catalog, skill_catalog  # noqa: E402


class SkillCatalogTests(unittest.TestCase):
    def test_the_eight_starting_kit_skill_ids(self):
        self.assertEqual(skill_catalog.SKILL_COUNT, 8)
        self.assertEqual(
            skill_catalog.STARTING_KIT_SKILL_IDS,
            (99, 110, 111, 40000, 41000, 42000, 43000, 44000))

    def test_titles_from_textdata_th_skill_text(self):
        self.assertEqual(skill_catalog.skill_title(99), "Normal Attack")
        self.assertEqual(skill_catalog.skill_title(110), "Strive Jump")
        self.assertEqual(skill_catalog.skill_title(111), "VIP Strive Jump")
        self.assertEqual(
            skill_catalog.skill_title(40000), "Gladiator Basic Training")
        self.assertEqual(
            skill_catalog.skill_title(41000), "Sharpshooter Basic Training")
        self.assertEqual(
            skill_catalog.skill_title(42000), "Stormherald Basic Training")
        self.assertEqual(
            skill_catalog.skill_title(43000), "Imperial Knights Basic Training")
        self.assertEqual(
            skill_catalog.skill_title(44000), "Light Priest Basic Training")

    def test_basic_training_title_differs_from_the_charcreate_icon_name(self):
        # Real, measured discrepancy (not a bug this catalog introduces):
        # CHARCREATE_CLASS's own s_ICON says "Sniper" for class id 4, but
        # SKILL_TEXT's title for that class's Basic Training skill (41000)
        # says "Sharpshooter" -- the two tables use different flavor names
        # for the same class.  Both are carried, undecided which is
        # "the" name; see class_catalog.py's module docstring nonclaims.
        sniper_class_name = class_catalog.class_name(4)
        sniper_basic_training_title = skill_catalog.skill_title(41000)
        self.assertEqual(sniper_class_name, "Sniper")
        self.assertEqual(sniper_basic_training_title, "Sharpshooter Basic Training")
        self.assertNotIn(sniper_class_name, sniper_basic_training_title)

    def test_every_class_starting_skill_id_resolves_in_this_catalog(self):
        # Cross-module consistency: class_catalog only names ids this module
        # is supposed to cover.
        for class_id in class_catalog.CLASS_IDS:
            for skill_id in class_catalog.starting_skill_ids(class_id):
                with self.subTest(class_id=class_id, skill_id=skill_id):
                    self.assertTrue(skill_catalog.is_known_skill_id(skill_id))
                    skill_catalog.skill_title(skill_id)
                    skill_catalog.skill_raw_context(skill_id)

    def test_level_learn_is_one_for_every_starting_kit_skill(self):
        for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                self.assertEqual(skill_catalog.level_learn(skill_id), 1)

    def test_cooldown_seconds_matches_the_raw_column_per_skill(self):
        # Real values from the committed table (not invented): the basic
        # attack (99) and the two movement skills (110/111) each carry a
        # non-zero n_CD, every Basic Training carries 0.
        expected = {
            99: 25, 110: 1, 111: 1,
            40000: 0, 41000: 0, 42000: 0, 43000: 0, 44000: 0,
        }
        for skill_id, cd in expected.items():
            with self.subTest(skill_id=skill_id):
                self.assertEqual(skill_catalog.cooldown_seconds(skill_id), cd)
                self.assertEqual(
                    skill_catalog.cooldown_seconds(skill_id),
                    int(skill_catalog.skill_raw_context(skill_id)["n_CD"]))

    def test_stamina_cost_matches_the_raw_column_per_skill(self):
        # Real values from the committed table: only Strive Jump (110) costs
        # stamina among these 8 -- the basic attack (99) costs 0.
        expected = {
            99: 0, 110: 22, 111: 0,
            40000: 0, 41000: 0, 42000: 0, 43000: 0, 44000: 0,
        }
        for skill_id, cost in expected.items():
            with self.subTest(skill_id=skill_id):
                self.assertEqual(skill_catalog.stamina_cost(skill_id), cost)
                self.assertEqual(
                    skill_catalog.stamina_cost(skill_id),
                    int(skill_catalog.skill_raw_context(skill_id)["n_STAMINA_COST"]))

    def test_basic_training_skill_ids_is_exactly_the_five_known_ids(self):
        # pf-adversary this round: the title-suffix derivation
        # (skill_catalog._BASIC_TRAINING_SKILL_IDS, built from
        # `.endswith(" Basic Training")`) is correct against today's table,
        # but nothing pinned the DERIVED tuple itself -- a future table
        # change that adds a spurious id whose title happens to end in
        # " Basic Training" would silently widen own_class_bit()'s domain
        # with no test catching it at the derivation site (it would only
        # surface indirectly, if at all, through the unrelated 8-id-count
        # pin in test_the_eight_starting_kit_skill_ids). Pin it directly.
        self.assertEqual(
            skill_catalog._BASIC_TRAINING_SKILL_IDS,
            (40000, 41000, 42000, 43000, 44000))

    def test_own_class_bit_matches_the_raw_n_isclass_column(self):
        # Real values from the committed table (not invented): each Basic
        # Training skill's n_ISCLASS is its own bit, distinct per class.
        expected = {40000: 1, 41000: 4, 42000: 16, 43000: 2, 44000: 32}
        for skill_id, bit in expected.items():
            with self.subTest(skill_id=skill_id):
                self.assertEqual(skill_catalog.own_class_bit(skill_id), bit)
                self.assertEqual(
                    skill_catalog.own_class_bit(skill_id),
                    int(skill_catalog.skill_raw_context(skill_id)["n_ISCLASS"]))

    def test_own_class_bit_equals_the_class_id_that_grants_it(self):
        # Cross-check between two INDEPENDENTLY committed tables
        # (SKILL_CONTEXT via skill_catalog, CHARCREATE_CLASS via
        # class_catalog): each Basic Training row's own n_ISCLASS bit must
        # equal the class_id of the class that names it a starting skill.
        # Derived from class_catalog, not a hand-typed skill-id list -- if
        # the client ever ships a 6th selectable class or renumbers one of
        # the 5, this goes red instead of silently pinning stale bits.
        checked = 0
        for class_id in class_catalog.CLASS_IDS:
            for skill_id in class_catalog.starting_skill_ids(class_id):
                if not skill_catalog.skill_title(skill_id).endswith(
                    " Basic Training"
                ):
                    continue
                with self.subTest(class_id=class_id, skill_id=skill_id):
                    self.assertEqual(
                        skill_catalog.own_class_bit(skill_id), class_id)
                checked += 1
        self.assertEqual(
            checked, 5,
            "expected exactly 5 Basic Training rows across all classes -- "
            "got %d, re-check class_catalog.CLASS_IDS / starting_skill_ids "
            "before trusting this cross-check" % checked)

    def test_own_class_bit_refuses_the_three_non_basic_training_ids(self):
        # 99/110/111's raw n_ISCLASS (63/0/0) has no established meaning --
        # see the module docstring. Refusing beats guessing.
        for skill_id in (99, 110, 111):
            with self.subTest(skill_id=skill_id):
                with self.assertRaises(skill_catalog.SkillCatalogError):
                    skill_catalog.own_class_bit(skill_id)

    def test_own_class_bit_raises_key_error_for_an_unknown_id(self):
        with self.assertRaises(KeyError):
            skill_catalog.own_class_bit(123456)

    def test_no_accessor_exists_for_n_target_yet(self):
        # n_TARGET has no RE'd unit or direction (module docstring, this
        # round) -- guards against a future edit quietly adding a named
        # accessor for it, the same trap test_raw_context_exposes_no_invented_
        # type_field pins for the type column.
        #
        # AST-shaped, not name-based (pf-adversary this round: a first draft
        # only checked four guessed function names -- hasattr(skill_catalog,
        # "target"/"target_field"/"range"/"target_mode") -- and a mutation
        # test proved a differently-named accessor such as target_type()
        # sailed straight past it while this test kept reporting green).
        # Instead this walks the module's AST for the string literal
        # "n_TARGET" and requires it to appear in exactly the one place the
        # module is allowed to name it: the ``_CONTEXT_COLUMNS`` raw-column
        # allowlist tuple.  A future accessor of any name that indexes
        # ``skill_raw_context(...)["n_TARGET"]`` -- or the raw dict directly
        # -- adds a second occurrence of that literal and turns this red,
        # regardless of what the function is called.
        source = (
            ROOT / "src/pirateforce_foundation/skill_catalog.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        occurrences = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and node.value == "n_TARGET"
        ]
        self.assertEqual(
            len(occurrences), 1,
            "the string literal \"n_TARGET\" appears %d times in "
            "skill_catalog.py, expected exactly 1 (inside _CONTEXT_COLUMNS) "
            "-- a new occurrence means something now reads/exposes n_TARGET "
            "by name; re-check it isn't an invented-meaning accessor before "
            "widening this count" % len(occurrences))

    def test_raw_context_exposes_no_invented_type_field(self):
        # Guards against a future edit quietly adding a
        # basic/attack/AOE/buff/heal/passive classification that the
        # underlying table does not actually carry (pf-adversary, round
        # iazmrv, finding 4).
        context = skill_catalog.skill_raw_context(99)
        for forbidden in ("type", "skill_type", "category", "n_MP", "mp_cost"):
            self.assertNotIn(forbidden, context)

    def test_unknown_skill_id_raises(self):
        with self.assertRaises(KeyError):
            skill_catalog.skill_title(123456)
        with self.assertRaises(KeyError):
            skill_catalog.skill_raw_context(123456)

    def test_is_known_skill_id(self):
        self.assertTrue(skill_catalog.is_known_skill_id(99))
        self.assertFalse(skill_catalog.is_known_skill_id(45000))  # Voodooist lead, not carried

    def test_the_committed_copies_match_their_own_pins(self):
        context_raw = (
            ROOT / "src/pirateforce_foundation/data/skill_context_starting_kit.tsv"
        ).read_bytes()
        text_raw = (
            ROOT / "src/pirateforce_foundation/data/skill_text_starting_kit.tsv"
        ).read_bytes()
        self.assertEqual(
            hashlib.sha256(context_raw).hexdigest(),
            skill_catalog.CONTEXT_SOURCE_SHA256)
        self.assertEqual(
            hashlib.sha256(text_raw).hexdigest(),
            skill_catalog.TEXT_SOURCE_SHA256)

    @BRIDGE_GAMEDATA.skip_unless_present()
    def test_the_generator_reproduces_the_shipped_tables_when_it_can_run(self):
        """Real drift detection against ../pf_bridge, not just a self-hash
        (pf-adversary, round iazmrv -- same rationale as
        test_class_catalog.py's matching test)."""
        gamedata = ROOT.parent / "pf_bridge" / "gamedata"
        finished = subprocess.run(
            [sys.executable,
             str(ROOT / "tools/pf_class_skill_starting_kit_extract.py"),
             "--check", "--gamedata", str(gamedata)],
            capture_output=True, text=True)
        self.assertEqual(
            finished.returncode, 0,
            "the shipped skill catalog tables are not what a fresh mining "
            "produces:\n%s%s" % (finished.stdout, finished.stderr))


class NPassiveIsNotATypeColumnTests(unittest.TestCase):
    """Round 6o11t1: pf-static-re and pf-adversary independently falsified
    the shortcut of reading ``n_PASSIVE`` as the basic/attack/AOE/buff/heal/
    passive taxonomy (see skill_catalog.py's module docstring for the full
    evidence).  This class pins the counter-example inside our own 8 known
    ids so a future round that quietly reintroduces the shortcut -- or a
    table update that erases the counter-example -- goes red here instead of
    only in an investigation report nobody re-reads."""

    def test_the_literal_basic_attack_shares_its_value_with_a_movement_skill(self):
        # Skill 99 "Normal Attack" is the one skill in this catalog that is
        # unambiguously a basic attack.  If n_PASSIVE distinguished
        # basic-attack from other kinds, it would not equal the value of a
        # pure movement skill (110 "Strive Jump").
        normal_attack = int(skill_catalog.skill_raw_context(99)["n_PASSIVE"])
        strive_jump = int(skill_catalog.skill_raw_context(110)["n_PASSIVE"])
        vip_strive_jump = int(skill_catalog.skill_raw_context(111)["n_PASSIVE"])
        self.assertEqual(normal_attack, 2)
        self.assertEqual(strive_jump, 2)
        self.assertEqual(vip_strive_jump, 2)
        self.assertEqual(
            normal_attack, strive_jump,
            "n_PASSIVE no longer collides Normal Attack with Strive Jump -- "
            "the counter-example this test exists to pin has changed; "
            "re-investigate before trusting n_PASSIVE as a type column "
            "again, do not just delete this assertion")

    def test_the_five_basic_trainings_sit_at_a_different_single_value(self):
        basic_training_ids = (40000, 41000, 42000, 43000, 44000)
        values = {
            skill_id: int(skill_catalog.skill_raw_context(skill_id)["n_PASSIVE"])
            for skill_id in basic_training_ids
        }
        self.assertEqual(set(values.values()), {1})
        # And that single value is NOT "nothing is ever actively cast" --
        # table-wide, 97/118 rows at n_PASSIVE=1 carry a non-blank
        # s_CAST_CONDITION (pf-static-re, round 6o11t1).  We only assert the
        # local half we can pin without re-scanning the whole table: none of
        # our 8 ids' s_CAST_CONDITION values are consistent with n_PASSIVE=1
        # meaning "distinct from n_PASSIVE=2" in any cast-behavior sense --
        # both 99 (n_PASSIVE=2) and the Basic Trainings (n_PASSIVE=1) can
        # have any cast-condition shape; the Basic Trainings just happen to
        # be blank here.
        for skill_id in basic_training_ids:
            with self.subTest(skill_id=skill_id):
                context = skill_catalog.skill_raw_context(skill_id)
                self.assertEqual(context["s_CAST_CONDITION"], "")
                self.assertEqual(context["s_CAST_BEHAVIOR"], "")

    def test_n_passive_alone_cannot_separate_our_known_attack_from_our_known_movement(self):
        # The direct statement of the trap: grouping our 8 known ids by
        # n_PASSIVE puts the basic attack in the same bucket as a movement
        # skill, and separates it from every Basic Training -- the opposite
        # of what a basic/attack/AOE/buff/heal/passive column should do.
        by_value: dict[int, list[int]] = {}
        for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS:
            value = int(skill_catalog.skill_raw_context(skill_id)["n_PASSIVE"])
            by_value.setdefault(value, []).append(skill_id)
        self.assertIn(99, by_value[2])
        self.assertIn(110, by_value[2])
        self.assertNotIn(99, by_value.get(1, []))


if __name__ == "__main__":
    unittest.main()
