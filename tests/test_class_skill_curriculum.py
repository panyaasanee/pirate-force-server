"""LANE-CS: tests for the per-class curriculum skill catalog.

Three jobs, kept separate on purpose:

1. Pin what the committed tables actually say (counts, ids, titles), so a
   silent table swap goes red here.
2. Re-prove the ``n_PPCLASS == CHARCREATE_CLASS.n_ID`` mapping from the
   shipped copies AND, when the bridge clone is present, from the real
   upstream tables via the extractor's own ``--check``.
3. Keep the ``n_PASSIVE`` shortcut dead.  The tidy 15-row split inside this
   subset is pinned as a CORRELATION with its table-wide counter-evidence
   attached, never as a type decode -- see
   ``NPassiveIsNotATypeColumnTests`` in ``tests/test_skill_catalog.py``
   (round 6o11t1), which this file deliberately does not contradict.
"""
from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402
from pirateforce_foundation import (  # noqa: E402
    class_catalog, class_skill_curriculum, skill_catalog,
)


class CurriculumShapeTests(unittest.TestCase):
    def test_five_classes_and_one_shared_bucket(self):
        self.assertEqual(
            class_skill_curriculum.CURRICULUM_CLASS_IDS, (1, 2, 4, 16, 32))
        self.assertEqual(class_skill_curriculum.SHARED_BUCKET_CODE, 1024)

    def test_the_class_ids_are_exactly_the_charcreate_class_roster(self):
        """The headline claim, stated as one assertion: CURRICULUM's class
        codes are not a second scheme -- they are the same five ids
        class_catalog already reads out of CHARCREATE_CLASS."""
        self.assertEqual(
            set(class_skill_curriculum.CURRICULUM_CLASS_IDS),
            set(class_catalog.CLASS_IDS))

    def test_the_committed_skill_id_count(self):
        self.assertEqual(class_skill_curriculum.SKILL_COUNT, 137)

    def test_per_class_counts(self):
        counts = {
            class_id: len(class_skill_curriculum.curriculum_skill_ids(class_id))
            for class_id in class_skill_curriculum.CURRICULUM_CLASS_IDS
        }
        self.assertEqual(counts, {1: 25, 2: 25, 4: 25, 16: 26, 32: 25})

    def test_the_shared_bucket_holds_eleven_ids_and_is_not_a_class(self):
        shared = class_skill_curriculum.shared_bucket_skill_ids()
        self.assertEqual(len(shared), 11)
        self.assertNotIn(
            class_skill_curriculum.SHARED_BUCKET_CODE,
            class_skill_curriculum.CURRICULUM_CLASS_IDS)
        self.assertNotIn(
            class_skill_curriculum.SHARED_BUCKET_CODE, class_catalog.CLASS_IDS)

    def test_the_shared_bucket_contains_the_three_ids_every_class_starts_with(self):
        """The measurable half of the 1024 reading (the 'means all classes'
        half stays an assumption, see the module docstring)."""
        shared = set(class_skill_curriculum.shared_bucket_skill_ids())
        shared_across_all_classes = set.intersection(*(
            set(class_catalog.CLASS_ID_TO_STARTING_SKILL_IDS[class_id])
            for class_id in class_catalog.CLASS_IDS))
        self.assertEqual(shared_across_all_classes, {99, 110, 111})
        self.assertTrue(shared_across_all_classes <= shared)

    def test_curriculum_skill_ids_never_folds_the_shared_bucket_in(self):
        """A wrong reading of 1024 must not be able to widen a class list."""
        shared = set(class_skill_curriculum.shared_bucket_skill_ids())
        for class_id in class_skill_curriculum.CURRICULUM_CLASS_IDS:
            with self.subTest(class_id=class_id):
                own = set(class_skill_curriculum.curriculum_skill_ids(class_id))
                self.assertEqual(own & shared, set())


class PpclassIsTheCharcreateClassIdTests(unittest.TestCase):
    """The second, independent witness, re-measured from the shipped copies:
    each class's own Basic Training id is a block prefix, and every id
    CURRICULUM files under a class code lands inside that class's own block.
    5 of 5, including the crossed pairs (class 2 -> 43xxx, class 4 ->
    41xxx), so this cannot be satisfied by a mismatched mapping."""

    def _basic_training_id(self, class_id: int) -> int:
        starting = class_catalog.CLASS_ID_TO_STARTING_SKILL_IDS[class_id]
        blocks = [
            skill_id for skill_id in starting
            if skill_id in skill_catalog.STARTING_KIT_SKILL_IDS
            and skill_id >= 40000
        ]
        self.assertEqual(len(blocks), 1, "class %d should own exactly one "
                         "Basic Training id, got %r" % (class_id, blocks))
        return blocks[0]

    def test_the_block_order_is_not_the_class_id_order(self):
        """Guards the witness itself: if the blocks ran in class-id order the
        agreement below would be much weaker evidence."""
        blocks = [self._basic_training_id(class_id)
                  for class_id in sorted(class_catalog.CLASS_IDS)]
        self.assertEqual(blocks, [40000, 43000, 41000, 42000, 44000])
        self.assertNotEqual(blocks, sorted(blocks))

    def test_every_class_bucket_sits_inside_that_classs_own_block(self):
        for class_id in class_skill_curriculum.CURRICULUM_CLASS_IDS:
            with self.subTest(class_id=class_id):
                start = self._basic_training_id(class_id)
                for skill_id in class_skill_curriculum.curriculum_skill_ids(
                        class_id):
                    self.assertTrue(
                        start < skill_id <= start + 999,
                        "class %d has curriculum skill %d outside its own "
                        "Basic Training block %d..%d -- the proof that "
                        "n_PPCLASS == CHARCREATE_CLASS.n_ID has broken; "
                        "re-do it by hand, do not delete this assertion"
                        % (class_id, skill_id, start, start + 999))

    def test_the_shared_bucket_is_disjoint_from_every_class_block(self):
        for class_id in class_skill_curriculum.CURRICULUM_CLASS_IDS:
            start = self._basic_training_id(class_id)
            for skill_id in class_skill_curriculum.shared_bucket_skill_ids():
                with self.subTest(class_id=class_id, skill_id=skill_id):
                    self.assertFalse(start < skill_id <= start + 999)


class AccessorTests(unittest.TestCase):
    def test_titles_come_from_the_client_table(self):
        self.assertEqual(class_skill_curriculum.skill_title(99), "Normal Attack")
        self.assertEqual(
            class_skill_curriculum.skill_title(40001), "Jixi Killing Sword")
        self.assertEqual(
            class_skill_curriculum.skill_title(42026), "Frozen Orb")

    def test_raw_field_accessors(self):
        self.assertEqual(class_skill_curriculum.level_learn(40001), 5)
        self.assertEqual(class_skill_curriculum.cooldown_raw(40001), 4001)
        self.assertEqual(class_skill_curriculum.stamina_cost(40001), 7)

    def test_level_learn_spans_the_whole_committed_range(self):
        levels = [class_skill_curriculum.level_learn(skill_id)
                  for skill_id in class_skill_curriculum.CURRICULUM_SKILL_IDS]
        self.assertEqual((min(levels), max(levels)), (1, 120))

    def test_curriculum_by_level_learn_is_sorted_and_complete(self):
        pairs = class_skill_curriculum.curriculum_by_level_learn(1)
        self.assertEqual(len(pairs), 25)
        self.assertEqual(list(pairs), sorted(pairs))
        self.assertEqual(
            {skill_id for _level, skill_id in pairs},
            set(class_skill_curriculum.curriculum_skill_ids(1)))

    def test_raw_context_is_a_copy_not_the_live_row(self):
        first = class_skill_curriculum.skill_raw_context(40001)
        first["n_CD"] = "999999"
        self.assertEqual(class_skill_curriculum.cooldown_raw(40001), 4001)

    def test_unknown_ids_refuse_rather_than_guess(self):
        with self.assertRaises(class_skill_curriculum.ClassSkillCurriculumError):
            class_skill_curriculum.skill_title(1234567)
        with self.assertRaises(class_skill_curriculum.ClassSkillCurriculumError):
            class_skill_curriculum.curriculum_skill_ids(999)


class NPassiveStaysUndecodedTests(unittest.TestCase):
    """Round 6o11t1 falsified reading ``n_PASSIVE`` as the basic/attack/AOE/
    buff/heal/passive taxonomy.  Inside THIS 137-id subset the column happens
    to split very tidily, which is exactly the shape that tempts a future
    round to promote it to a type decode.  Both halves are pinned here --
    the tidy correlation AND the table-wide counter-evidence that keeps it a
    correlation -- so promoting it requires deleting an assertion that says
    in words why not."""

    def _subset_passive_one(self):
        return [skill_id for skill_id in class_skill_curriculum.CURRICULUM_SKILL_IDS
                if class_skill_curriculum.skill_raw_context(
                    skill_id)["n_PASSIVE"] == "1"]

    def test_the_tidy_subset_correlation_as_a_correlation(self):
        passive_one = self._subset_passive_one()
        self.assertEqual(len(passive_one), 15)
        for skill_id in passive_one:
            with self.subTest(skill_id=skill_id):
                context = class_skill_curriculum.skill_raw_context(skill_id)
                self.assertEqual(context["n_CD"], "0")
                self.assertEqual(context["n_STAMINA_COST"], "0")
                self.assertEqual(context["s_CAST_BEHAVIOR"], "")
                self.assertIn(
                    "Discipline", class_skill_curriculum.skill_title(skill_id))

    def test_the_module_ships_no_passive_accessor(self):
        """The refusal, as an assertion.  If a future round adds one, it goes
        red here and has to read this class's docstring first."""
        for name in dir(class_skill_curriculum):
            self.assertNotIn(
                "passive", name.lower(),
                "class_skill_curriculum exported %r -- n_PASSIVE is not a "
                "decoded type column (see NPassiveIsNotATypeColumnTests in "
                "tests/test_skill_catalog.py and the table-wide "
                "counter-evidence in the sibling test below)" % name)

    @BRIDGE_GAMEDATA.skip_unless_present()
    def test_table_wide_n_passive_one_is_mostly_actively_cast(self):
        """The counter-evidence, re-measured this round from the full table:
        n_PASSIVE=1 cannot mean "never cast" when most such rows cast."""
        gamedata = ROOT.parent / "pf_bridge" / "gamedata" / "tables"
        with (gamedata / "CONSTDATA_TH__SKILL_CONTEXT.tsv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        passive_one = [row for row in rows if row["n_PASSIVE"] == "1"]
        casting = [row for row in passive_one
                   if row["s_CAST_BEHAVIOR"].strip()]
        self.assertEqual(len(passive_one), 118)
        self.assertEqual(len(casting), 97)
        self.assertGreater(
            len(casting), len(passive_one) // 2,
            "most n_PASSIVE=1 rows no longer cast -- the counter-example "
            "that keeps n_PASSIVE undecoded has changed; re-investigate "
            "before treating it as a type column, do not just delete this")
        self.assertEqual(
            sorted({row["n_PASSIVE"] for row in rows}),
            ["0", "1", "2", "3", "4", "5"],
            "n_PASSIVE is a six-valued column, not a boolean")


class CommittedCopiesAreThePinnedOnesTests(unittest.TestCase):
    def test_sha256_of_the_three_shipped_copies(self):
        base = ROOT / "src" / "pirateforce_foundation" / "data"
        for name, expected in (
            ("class_skill_curriculum.tsv",
             class_skill_curriculum.CURRICULUM_SOURCE_SHA256),
            ("skill_context_curriculum.tsv",
             class_skill_curriculum.CONTEXT_SOURCE_SHA256),
            ("skill_text_curriculum.tsv",
             class_skill_curriculum.TEXT_SOURCE_SHA256),
        ):
            with self.subTest(name=name):
                raw = (base / name).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)

    def test_every_shipped_title_is_ascii(self):
        for skill_id in class_skill_curriculum.CURRICULUM_SKILL_IDS:
            with self.subTest(skill_id=skill_id):
                class_skill_curriculum.skill_title(skill_id).encode("ascii")

    @BRIDGE_GAMEDATA.skip_unless_present()
    def test_the_generator_reproduces_the_shipped_tables_when_it_can_run(self):
        """Real drift detection against ../pf_bridge, not just a self-hash --
        same rationale as test_skill_catalog.py's matching test.  The
        extractor also re-runs the whole mapping proof on the upstream
        tables, so this going green means the proof still holds there too."""
        gamedata = ROOT.parent / "pf_bridge" / "gamedata"
        finished = subprocess.run(
            [sys.executable,
             str(ROOT / "tools/pf_class_skill_curriculum_extract.py"),
             "--check", "--gamedata", str(gamedata)],
            capture_output=True, text=True)
        self.assertEqual(
            finished.returncode, 0,
            "the shipped curriculum tables are not what a fresh mining "
            "produces:\n%s%s" % (finished.stdout, finished.stderr))


if __name__ == "__main__":
    unittest.main()
