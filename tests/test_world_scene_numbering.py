"""Pin the identity-namespace rule and its fail-closed edge.

The rule under test is the one thing ``GT-078`` cost an attended round to
learn: a Mob-Set number is a global ``MOBS.n_ID`` only in a scene whose set
numbering is SPARSE.  ``bg0001`` is dense, so its numbers are per-scene
ordinals, so the 115 identities Port Royal ships today are a category error
rather than an unconfirmed guess.

Three separate things are watched here, because each can rot without the
others:

1. the frozen measurement itself (aggregates and per-scene rows), so that a
   gamedata re-export which changes the corpus turns this red instead of
   quietly moving the rule;
2. the classifier's arithmetic, including the inputs that are not small
   scenes but broken parses;
3. the fail-closed direction of every consumer - ``identity_is_provable``,
   ``assert_identity_claim`` and both console emitters - since a guard that
   fails open is worse than no guard, and the boot line is the only place a
   human sees this verdict.

Nonclaims: nothing here claims to know a ``bg0001`` identity, that the ten
predicted town scenes are classified correctly, or that any wire byte changed.
"""

from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_numbering as wsn


class FrozenMeasurementTest(unittest.TestCase):
    """The numbers the rule was read off, pinned as numbers."""

    def test_corpus_aggregates_are_pinned(self):
        self.assertEqual(wsn.SCENE_FILES_WITH_SETS, 266)
        self.assertEqual(wsn.DENSE_SCENE_COUNT, 202)
        self.assertEqual(wsn.SPARSE_SCENE_COUNT, 64)
        self.assertEqual(
            wsn.DENSE_SCENE_COUNT + wsn.SPARSE_SCENE_COUNT,
            wsn.SCENE_FILES_WITH_SETS,
            "dense + sparse must exhaust the measured corpus",
        )

    def test_census_rows_are_well_formed_and_unique(self):
        seen = set()
        for scene, rows, sets_, max_set, family in wsn.FROZEN_SCENE_SET_CENSUS:
            self.assertNotIn(scene, seen, f"{scene} listed twice")
            seen.add(scene)
            self.assertGreaterEqual(sets_, 20, f"{scene} below the >=20 cut")
            self.assertGreaterEqual(rows, sets_, f"{scene} has fewer rows than sets")
            self.assertGreaterEqual(max_set, sets_, f"{scene} max below count")
            self.assertTrue(family, f"{scene} has no set-name family")

    def test_bg0001_is_the_only_dense_large_town(self):
        """The whole rule rests on this asymmetry, so state it as a test."""
        towns = [
            row for row in wsn.FROZEN_SCENE_SET_CENSUS
            if re.fullmatch(r"[Bb]g00\d\d", row[0]) and row[2] >= 30
        ]
        dense = sorted(row[0] for row in towns if row[3] == row[2])
        self.assertEqual(
            dense, ["Bg0020", "bg0001"],
            "dense large scenes changed; the bg0001 asymmetry must be re-argued",
        )
        # bg0001 is dense at 113 of a ~115 slot space; Bg0020 is a 30/30
        # scene, far from the 102-115 band the town files occupy.
        bg0001 = dict((r[0], r) for r in wsn.FROZEN_SCENE_SET_CENSUS)["bg0001"]
        self.assertEqual((bg0001[2], bg0001[3]), (113, 113))

    def test_the_two_owner_verdicts_are_the_evidence_and_are_disjoint(self):
        self.assertEqual(wsn.OWNER_CONFIRMED_GLOBAL_NID, ("Bg0002",))
        self.assertEqual(wsn.OWNER_REJECTED_LOCAL_ORDINAL, ("bg0001",))
        self.assertFalse(
            set(wsn.OWNER_CONFIRMED_GLOBAL_NID)
            & set(wsn.OWNER_REJECTED_LOCAL_ORDINAL))

    def test_the_two_evidence_scenes_classify_the_way_they_were_observed(self):
        self.assertEqual(
            wsn.classify_scene("Bg0002"), wsn.NAMESPACE_GLOBAL_NID)
        self.assertEqual(
            wsn.classify_scene("bg0001"), wsn.NAMESPACE_LOCAL_ORDINAL)


class ClassifierTest(unittest.TestCase):

    def test_dense_reads_as_ordinal_and_sparse_as_global(self):
        self.assertEqual(
            wsn.classify_counts(113, 113), wsn.NAMESPACE_LOCAL_ORDINAL)
        self.assertEqual(
            wsn.classify_counts(45, 104), wsn.NAMESPACE_GLOBAL_NID)

    def test_a_single_set_scene_is_dense_not_a_special_case(self):
        self.assertEqual(
            wsn.classify_counts(1, 1), wsn.NAMESPACE_LOCAL_ORDINAL)

    def test_impossible_and_malformed_shapes_raise(self):
        for bad in ((0, 5), (5, 0), (-1, 3), (6, 5)):
            with self.assertRaises(ValueError, msg=f"{bad} should raise"):
                wsn.classify_counts(*bad)
        for bad in (("113", 113), (113, 113.0), (True, 5)):
            with self.assertRaises(ValueError, msg=f"{bad} should raise"):
                wsn.classify_counts(*bad)

    def test_an_unmeasured_scene_is_unknown_not_an_exception(self):
        self.assertEqual(
            wsn.classify_scene("Bg9999"), wsn.NAMESPACE_UNKNOWN)

    def test_scene_id_mapping_is_explicit_and_closed(self):
        self.assertEqual(wsn.scene_file_for_scene_id(1), "bg0001")
        self.assertEqual(wsn.scene_file_for_scene_id(2), "Bg0002")
        self.assertIsNone(wsn.scene_file_for_scene_id(278))
        with self.assertRaises(ValueError):
            wsn.scene_file_for_scene_id("1")


class FailClosedTest(unittest.TestCase):
    """Every consumer must answer 'no' when it does not know."""

    def test_port_royal_identity_is_refused(self):
        self.assertFalse(wsn.identity_is_provable("bg0001"))
        self.assertIn("GT-078", wsn.identity_block_reason("bg0001"))
        with self.assertRaises(ValueError) as caught:
            wsn.assert_identity_claim("bg0001")
        self.assertIn("bg0001", str(caught.exception))

    def test_the_owner_confirmed_scene_is_the_only_thing_allowed(self):
        self.assertTrue(wsn.identity_is_provable("Bg0002"))
        self.assertIsNone(wsn.identity_block_reason("Bg0002"))
        wsn.assert_identity_claim("Bg0002")  # must not raise

    def test_sparse_but_unconfirmed_is_still_refused(self):
        """bg0003 is sparse, so the rule predicts its numbers are n_IDs - and
        no owner has looked at it, so shipping on that prediction is exactly
        the move that produced GT-078."""
        self.assertEqual(
            wsn.classify_scene("bg0003"), wsn.NAMESPACE_GLOBAL_NID)
        self.assertFalse(wsn.identity_is_provable("bg0003"))
        self.assertEqual(
            wsn.identity_block_reason("bg0003"),
            "sparse_but_not_owner_confirmed")
        with self.assertRaises(ValueError):
            wsn.assert_identity_claim("bg0003")

    def test_an_unmeasured_scene_is_refused_with_its_own_reason(self):
        self.assertFalse(wsn.identity_is_provable("Bg9999"))
        self.assertEqual(
            wsn.identity_block_reason("Bg9999"), "scene_not_in_frozen_census")

    def test_no_scene_in_the_census_is_provable_by_accident(self):
        provable = [
            row[0] for row in wsn.FROZEN_SCENE_SET_CENSUS
            if wsn.identity_is_provable(row[0])
        ]
        self.assertEqual(provable, ["Bg0002"])


class ConsoleTest(unittest.TestCase):

    def _assert_ascii(self, line):
        line.encode("ascii")  # raises if a non-ASCII byte crept in
        self.assertNotIn("\n", line)

    def test_port_royal_line_carries_verdict_and_raw_numbers(self):
        line = wsn.numbering_console_line("bg0001")
        self._assert_ascii(line)
        self.assertTrue(line.startswith("WORLD_IDENTITY_NAMESPACE "))
        self.assertIn("scene=bg0001", line)
        self.assertIn("kind=local_ordinal", line)
        self.assertIn("sets=113", line)
        self.assertIn("max=113", line)
        self.assertIn("identity_provable=0", line)

    def test_prison_island_line_reports_provable(self):
        line = wsn.numbering_console_line("Bg0002")
        self._assert_ascii(line)
        self.assertIn("kind=global_nid", line)
        self.assertIn("identity_provable=1", line)
        self.assertIn("reason=-", line)

    def test_unmeasured_scene_still_emits_a_line(self):
        line = wsn.numbering_console_line("Bg9999")
        self._assert_ascii(line)
        self.assertIn("kind=unknown", line)
        self.assertIn("sets=?", line)
        self.assertIn("identity_provable=0", line)

    def test_suffix_resolves_scene_ids_and_never_fails_open(self):
        self.assertEqual(
            wsn.numbering_console_suffix(1),
            wsn.numbering_console_line("bg0001"))
        unmapped = wsn.numbering_console_suffix(278)
        self._assert_ascii(unmapped)
        self.assertIn("identity_provable=0", unmapped)
        self.assertIn("scene_id_278_not_mapped", unmapped)


class CensusLineIntegrationTest(unittest.TestCase):
    """The boot line must carry the verdict, without breaking its readers."""

    @classmethod
    def setUpClass(cls):
        from pirateforce_foundation.legacy_bridge import load_legacy
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_census_line_appends_the_namespace_token(self):
        from pirateforce_foundation import world_population

        # Build the line through the real function on a real generation, so
        # this cannot pass against a hand-made string.
        gen = world_population.build_world_population(
            self.legacy, (0.0, 0.0, 0.0), 3, scene_id=1)
        line = world_population.census_console_line(gen)
        line.encode("ascii")
        self.assertTrue(
            line.startswith("WORLD_CENSUS "),
            "existing readers match on this prefix and must keep working",
        )
        self.assertIn("WORLD_IDENTITY_NAMESPACE ", line)
        self.assertIn("scene=bg0001", line)
        self.assertIn("identity_provable=0", line)


if __name__ == "__main__":
    unittest.main()
