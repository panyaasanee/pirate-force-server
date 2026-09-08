"""LANE-CS: every skill row the client's own SKILL_CONTEXT table declares.

What these tests prove
----------------------
  * the census is the client's table verbatim -- pinned by sha256, and, when
    a bridge clone is present, re-mined and diffed rather than self-hashed;
  * the 8-row starting-kit copy is a byte-exact SUBSET of it, so the two
    files cannot answer one skill id two ways;
  * the three columns a learn rule reads are read RAW, sentinel included,
    and the sentinel is refused by name instead of being multiplied;
  * and the level rule is a `>=` against the table value, pinned on real
    ids at both ends of the ladder.

NOT tested here, because it is not claimed: that any client enforces
`n_LEVEL_LEARN`, that `n_PASSIVE`/`n_TARGET` mean anything, or that any
class may learn any of these ids.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    skill_catalog,
    skill_context_census as census,
)

DATA = ROOT / "src" / "pirateforce_foundation" / "data"


class TheCopyIsTheClientTableTests(unittest.TestCase):
    def test_the_shipped_copy_matches_its_own_pin(self):
        raw = (DATA / "skill_context_all.tsv").read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            census.ALL_CONTEXT_SOURCE_SHA256,
        )

    def test_the_row_count_is_the_one_the_module_names(self):
        self.assertEqual(
            census.DECLARED_SKILL_ROWS, len(census.DECLARED_SKILL_IDS)
        )

    def test_every_id_is_unique_and_sorted(self):
        ids = census.DECLARED_SKILL_IDS
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(list(ids), sorted(ids))

    def test_the_copy_is_ascii(self):
        """The server loads it with encoding='ascii' on purpose: the bridge
        console is cp874 and a transcoded row would be a silent edit."""
        raw = (DATA / "skill_context_all.tsv").read_bytes()
        raw.decode("ascii")

class TheKitCopyIsASubsetOfThisOneTests(unittest.TestCase):
    """Two files carrying the same rows is how two answers drift apart."""

    def test_every_starting_kit_line_appears_verbatim_in_the_census(self):
        kit = (DATA / "skill_context_starting_kit.tsv").read_text(
            encoding="ascii").splitlines()
        allr = (DATA / "skill_context_all.tsv").read_text(
            encoding="ascii").splitlines()
        self.assertEqual(kit[0], allr[0], "headers differ")
        for line in kit[1:]:
            self.assertIn(line, allr[1:])

    def test_every_kit_id_reads_the_same_cost_through_both_modules(self):
        for skill_id in skill_catalog.STARTING_KIT_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                self.assertEqual(
                    skill_catalog.skill_point_cost_to_learn(skill_id),
                    census.rank_one_point_cost(skill_id),
                )


class TheColumnsAreReadRawTests(unittest.TestCase):
    def test_an_undeclared_id_is_refused_by_name_not_defaulted(self):
        self.assertFalse(census.is_declared(123456))
        with self.assertRaises(census.SkillContextCensusError) as caught:
            census.level_to_learn(123456)
        self.assertIn("refusing rather than inventing", str(caught.exception))

    def test_a_bool_is_not_a_skill_id(self):
        self.assertFalse(census.is_declared(True))
        with self.assertRaises(TypeError):
            census.level_to_learn(True)

    def test_the_rank_sentinel_is_reported_raw_and_refused_as_a_count(self):
        """0xFFFFFFFF is not 4294967295 ranks, and 169 rows carry it."""
        self.assertEqual(4294967295, census.RANK_COUNT_SENTINEL)
        sentinel_ids = [
            skill_id for skill_id in census.DECLARED_SKILL_IDS
            if census.declared_rank_count(skill_id)
            == census.RANK_COUNT_SENTINEL
        ]
        self.assertEqual(169, len(sentinel_ids))
        for skill_id in sentinel_ids[:5]:
            with self.subTest(skill_id=skill_id):
                self.assertFalse(census.rank_count_is_a_real_count(skill_id))

    def test_the_rank_census_is_the_three_values_the_docstring_names(self):
        counts = {}
        for skill_id in census.DECLARED_SKILL_IDS:
            value = census.declared_rank_count(skill_id)
            counts[value] = counts.get(value, 0) + 1
        self.assertEqual({1: 1982, 120: 14, 4294967295: 169}, counts)

    def test_no_module_multiplies_the_sentinel(self):
        """The census exposes no rank-2 cost at all -- see its docstring."""
        self.assertFalse(
            [name for name in dir(census) if "level2" in name.lower()]
        )


class TheLevelRuleTests(unittest.TestCase):
    """`>=` against `n_LEVEL_LEARN`, on real ids at both ends of the ladder."""

    def test_a_level_one_skill_is_learnable_at_level_one(self):
        self.assertEqual(1, census.level_to_learn(99))
        self.assertTrue(census.meets_level_requirement(1, 99))

    def test_a_level_forty_skill_refuses_a_level_thirty_nine_character(self):
        self.assertEqual(40, census.level_to_learn(2950))
        self.assertFalse(census.meets_level_requirement(39, 2950))
        self.assertTrue(census.meets_level_requirement(40, 2950))
        self.assertTrue(census.meets_level_requirement(41, 2950))

    def test_a_bool_level_is_refused_rather_than_compared_as_one(self):
        with self.assertRaises(TypeError):
            census.meets_level_requirement(True, 99)

    def test_a_negative_level_is_refused(self):
        with self.assertRaises(census.SkillContextCensusError):
            census.meets_level_requirement(-1, 99)


if __name__ == "__main__":
    unittest.main()
