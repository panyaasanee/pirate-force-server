"""`world_m2_sailing_result_key`: the SAILING_RESULT key RE-265 found the
client's contact tick requires at record `+0x14`, derived from the client's
own table via a committed, hash-pinned copy.

LANE-A, COO-DECISION 20260905_1947 item 2, answering RE-265.
COO-DECISION 20260905_2349 item 1 (GT-233 v3, option (ข)): the two-candidate
scheme discriminates a COLUMN (n_ID vs n_AREA), not a row -- see
`ColumnDiscriminatingKeysTests`.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import (  # noqa: E402
    world_m2_sailing_result_key as key,
)
from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402


class CommittedCopyTests(unittest.TestCase):
    def test_the_copy_verifies_against_its_own_pin(self):
        rows = key.load_copy()
        self.assertEqual(len(rows), 18)

    def test_every_row_is_area_126_and_event_2(self):
        for row in key.load_copy():
            with self.subTest(n_ID=row["n_ID"]):
                self.assertEqual(row["n_AREA"], str(key.SAILING_RESULT_AREA))
                self.assertEqual(row["n_EVENT"], str(key.SAILING_RESULT_EVENT))

    def test_a_tampered_copy_is_refused_not_silently_trusted(self):
        # D2, pf-adversary round `tk4hr7`: the first version of this test
        # wrote the forged bytes over the TRACKED artifact itself and
        # restored it in `finally` -- a process killed mid-test left a
        # modified file under `src/` that `import runtime` then failed on
        # for every round after, until someone noticed and ran `git
        # checkout --`.  Same fix as
        # `test_world_marker_copy.py`'s `test_editing_the_copy_without_
        # moving_the_pin_is_refused`: point `COPY_PATH` at a temp file
        # instead of touching the committed one at all.
        real = key.COPY_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as work:
            forged = Path(work) / "world_sailing_result_area126.tsv"
            forged.write_bytes(real + b"\n")
            original = key.COPY_PATH
            key.COPY_PATH = forged
            try:
                with self.assertRaises(key.SailingResultCopyError):
                    key.load_copy()
            finally:
                key.COPY_PATH = original


class AreaIdsTests(unittest.TestCase):
    def test_area_126_ids_match_the_committed_copy(self):
        rows = key.load_copy()
        self.assertEqual(
            key.area_126_sailing_result_ids(),
            tuple(int(row["n_ID"]) for row in rows),
        )

    def test_eighteen_rows_no_more_no_less_today(self):
        # A pinned count, same discipline as `world_marker_copy`'s totals
        # block: a table update that adds or removes an area-126 row must
        # move this number in the same diff, not silently.
        self.assertEqual(len(key.area_126_sailing_result_ids()), 18)

    def test_ids_are_unique(self):
        ids = key.area_126_sailing_result_ids()
        self.assertEqual(len(ids), len(set(ids)))

    def test_not_bound_at_module_scope(self):
        # D1, pf-adversary round `tk4hr7`: this must be a function, not a
        # module-level tuple bound at import time -- see the module
        # docstring's "WHY THE ROWS ARE LOADED LAZILY".
        self.assertFalse(hasattr(key, "AREA_126_SAILING_RESULT_IDS"))
        self.assertTrue(callable(key.area_126_sailing_result_ids))


class ProvisionalKeyTests(unittest.TestCase):
    def test_the_provisional_key_is_a_real_row_id(self):
        self.assertIn(
            key.provisional_area_126_key(), key.area_126_sailing_result_ids()
        )

    def test_the_provisional_key_is_deterministic(self):
        self.assertEqual(
            key.provisional_area_126_key(), key.provisional_area_126_key()
        )

    def test_the_provisional_key_is_the_lowest_id_not_a_guess(self):
        self.assertEqual(
            key.provisional_area_126_key(),
            min(key.area_126_sailing_result_ids()),
        )

    def test_the_provisional_key_is_never_zero(self):
        # Zero is the value RE-265 measured as the null-lookup gate: the
        # whole point of this module is that this is not that value.
        self.assertNotEqual(key.provisional_area_126_key(), 0)


class NAreaKeyTests(unittest.TestCase):
    def test_n_area_key_is_the_area_itself(self):
        self.assertEqual(key.n_area_key(), 126)
        self.assertEqual(key.n_area_key(), key.SAILING_RESULT_AREA)

    def test_n_area_key_is_not_one_of_the_row_ids(self):
        # The whole point of testing "n_AREA" as a column hypothesis is
        # that it is a DIFFERENT number from every "n_ID" candidate.
        self.assertNotIn(key.n_area_key(), key.area_126_sailing_result_ids())


class ColumnDiscriminatingKeysTests(unittest.TestCase):
    """`column_discriminating_keys(n)` -- COO-DECISION `20260905_2349` item
    1, GT-233 v3 option (ข): the two GT-233 records must test DIFFERENT
    COLUMN hypotheses (n_ID vs n_AREA), not two rows of the same column --
    see the function's own docstring for why the row-discriminating design
    this replaces could never come back positive if the client keys its
    store by `n_AREA` instead."""

    def test_two_keys_are_n_id_then_n_area(self):
        keys = key.column_discriminating_keys(2)
        self.assertEqual(keys, (key.provisional_area_126_key(),
                                 key.n_area_key()))

    def test_two_keys_are_distinct(self):
        keys = key.column_discriminating_keys(2)
        self.assertEqual(len(keys), 2)
        self.assertEqual(len(set(keys)), 2)

    def test_d8_neither_key_collides_with_either_docks_0x12(self):
        # D8, pf-adversary round `tk4hr7`: the retired scheme's two lowest
        # n_IDs (1, 2) put island 3's key exactly equal to island 2's
        # `+0x12` (survey_id 2). Neither new candidate may equal 2 or 3
        # (the two docks' `+0x12` values), or a resolved lookup could be
        # misread as evidence about the wrong field.
        for value in key.column_discriminating_keys(2):
            self.assertNotIn(value, (2, 3))

    def test_one_key_is_the_n_id_hypothesis_alone(self):
        self.assertEqual(
            key.column_discriminating_keys(1), (key.provisional_area_126_key(),)
        )

    def test_zero_keys_is_the_empty_tuple(self):
        self.assertEqual(key.column_discriminating_keys(0), ())

    def test_more_than_two_is_rejected(self):
        # Only two named hypotheses exist (n_ID, n_AREA); this function
        # does not generalise to "N distinct candidates" the way the
        # row-discriminating design it replaces did.
        with self.assertRaises(ValueError):
            key.column_discriminating_keys(3)

    def test_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            key.column_discriminating_keys(-1)

    def test_row_discriminating_function_is_gone(self):
        # The design it replaced gave every count a DISTINCT n_ID -- keeping
        # both names around would let a caller pick the wrong one silently.
        self.assertFalse(hasattr(key, "provisional_area_126_keys"))


class CurateReDerivationTests(unittest.TestCase):
    """`@BRIDGE_GAMEDATA.skip_unless_present()`: on a machine with
    `pf_bridge` beside this repository, re-curate straight from the bridge
    source and compare bytes against the committed copy -- the second half
    of the lock, same shape as `world_marker_copy`'s own re-derive test.
    """

    @BRIDGE_GAMEDATA.skip_unless_present()
    def test_the_committed_copy_matches_a_fresh_curate_from_the_bridge(self):
        bridge_root = ROOT.parent / "pf_bridge"
        tables_dir = bridge_root / "gamedata" / "tables"
        curated = key.curate(tables_dir)
        committed = key.COPY_PATH.read_text(encoding="utf-8")
        self.assertEqual(curated, committed)


if __name__ == "__main__":
    unittest.main()
