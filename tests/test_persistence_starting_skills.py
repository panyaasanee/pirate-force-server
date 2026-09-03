"""LANE-DB: `persistence_starting_skills.resolve_starting_skill_ids`.

`PANYA-DECISION 20260904_0328` piece 5 (`COO-ORDER 20260904_0329` item 5).
This file measures the resolver only -- it does not touch a database and
does not claim a skill reaches a character; that is
`tests/test_persistence_character_skills_011.py` (the write/read door) and,
beyond this PR, whichever hookup chief grants threads the two together at
character creation, the same shape piece 1's `persistence_class_id.
resolve_class_id` went through.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import class_catalog                  # noqa: E402
from pirateforce_foundation.persistence_starting_skills import (  # noqa: E402
    resolve_starting_skill_ids,
)


class TheResolverAgreesWithClassCatalogTests(unittest.TestCase):
    """This module resolves LANE-CS's own catalog; it must never disagree
    with it, and a test importing both is what makes that checkable rather
    than assumed."""

    def test_every_known_class_id_resolves_to_class_catalogs_own_tuple(self):
        for class_id in class_catalog.CLASS_IDS:
            with self.subTest(class_id=class_id):
                self.assertEqual(
                    resolve_starting_skill_ids(class_id),
                    class_catalog.starting_skill_ids(class_id),
                )

    def test_the_result_is_exactly_four_ids_for_every_known_class(self):
        for class_id in class_catalog.CLASS_IDS:
            with self.subTest(class_id=class_id):
                self.assertEqual(len(resolve_starting_skill_ids(class_id)), 4)

    def test_skill_99_normal_attack_is_the_third_id_for_every_class(self):
        """Pinned against the committed table, not assumed by this module's
        code: `CHARCREATE_CLASS.s_SKILL_3` is skill id 99 ("Normal Attack",
        the basic attack) for all five rows, but nothing in
        `resolve_starting_skill_ids` special-cases position 3 or the value
        99 -- if a future table edit moved it, this test is what would go
        red, not a silent behaviour change."""
        for class_id in class_catalog.CLASS_IDS:
            with self.subTest(class_id=class_id):
                self.assertEqual(resolve_starting_skill_ids(class_id)[2], 99)

    def test_five_known_classes_all_start_with_a_basic_attack(self):
        self.assertEqual(class_catalog.CLASS_COUNT, 5)
        for class_id in class_catalog.CLASS_IDS:
            self.assertIn(99, resolve_starting_skill_ids(class_id))


class AnUnknownClassResolvesToNoneNeverAGuessTests(unittest.TestCase):

    def test_a_class_id_not_in_the_catalog_resolves_to_none(self):
        unknown = max(class_catalog.CLASS_IDS) + 1
        self.assertNotIn(unknown, class_catalog.CLASS_IDS)
        self.assertIsNone(resolve_starting_skill_ids(unknown))

    def test_zero_and_a_large_u32_both_resolve_to_none(self):
        for candidate in (0, 0xFFFFFFFF):
            with self.subTest(candidate=candidate):
                self.assertIsNone(resolve_starting_skill_ids(candidate))

    def test_a_negative_class_id_resolves_to_none_not_an_error(self):
        self.assertIsNone(resolve_starting_skill_ids(-1))


class TheDoorRefusesBadInputTypesTests(unittest.TestCase):

    def test_a_bool_class_id_is_refused_not_coerced_to_0_or_1(self):
        """`True is 1` and `False is 0` in python; silently resolving on a
        bool would resolve class 1's kit for a caller that meant to pass a
        real class id and had a bug -- `persistence_typed_attrs.validate`
        refuses the same shape for the same reason."""
        for bad in (True, False):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    resolve_starting_skill_ids(bad)

    def test_a_non_int_class_id_is_refused(self):
        for bad in ("1", 1.0, None, [1], {1: 1}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    resolve_starting_skill_ids(bad)


if __name__ == "__main__":
    unittest.main()
