"""`world_m2_sailing_result_key`: the SAILING_RESULT key RE-265 found the
client's contact tick requires at record `+0x14`, derived from the client's
own table via a committed, hash-pinned copy.

LANE-A, COO-DECISION 20260905_1947 item 2, answering RE-265.
"""
from __future__ import annotations

import sys
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
        real = key.COPY_PATH.read_bytes()
        try:
            key.COPY_PATH.write_bytes(real + b"\n")
            with self.assertRaises(key.SailingResultCopyError):
                key.load_copy()
        finally:
            key.COPY_PATH.write_bytes(real)


class AreaIdsTests(unittest.TestCase):
    def test_area_126_ids_match_the_committed_copy(self):
        rows = key.load_copy()
        self.assertEqual(
            key.AREA_126_SAILING_RESULT_IDS,
            tuple(int(row["n_ID"]) for row in rows),
        )

    def test_eighteen_rows_no_more_no_less_today(self):
        # A pinned count, same discipline as `world_marker_copy`'s totals
        # block: a table update that adds or removes an area-126 row must
        # move this number in the same diff, not silently.
        self.assertEqual(len(key.AREA_126_SAILING_RESULT_IDS), 18)

    def test_ids_are_unique(self):
        ids = key.AREA_126_SAILING_RESULT_IDS
        self.assertEqual(len(ids), len(set(ids)))


class ProvisionalKeyTests(unittest.TestCase):
    def test_the_provisional_key_is_a_real_row_id(self):
        self.assertIn(
            key.provisional_area_126_key(), key.AREA_126_SAILING_RESULT_IDS
        )

    def test_the_provisional_key_is_deterministic(self):
        self.assertEqual(
            key.provisional_area_126_key(), key.provisional_area_126_key()
        )

    def test_the_provisional_key_is_the_lowest_id_not_a_guess(self):
        self.assertEqual(
            key.provisional_area_126_key(),
            min(key.AREA_126_SAILING_RESULT_IDS),
        )

    def test_the_provisional_key_is_never_zero(self):
        # Zero is the value RE-265 measured as the null-lookup gate: the
        # whole point of this module is that this is not that value.
        self.assertNotEqual(key.provisional_area_126_key(), 0)


class ProvisionalKeysPluralTests(unittest.TestCase):
    """`provisional_area_126_keys(n)` -- pf-adversary, round `wjprxa`, D1:
    the two GT-233 records must get DISTINCT candidates, not one value
    repeated."""

    def test_keys_are_distinct_and_real(self):
        keys = key.provisional_area_126_keys(2)
        self.assertEqual(len(keys), 2)
        self.assertEqual(len(set(keys)), 2)
        for value in keys:
            self.assertIn(value, key.AREA_126_SAILING_RESULT_IDS)

    def test_keys_are_the_lowest_ids_in_ascending_order(self):
        self.assertEqual(
            key.provisional_area_126_keys(3),
            tuple(sorted(key.AREA_126_SAILING_RESULT_IDS)[:3]),
        )

    def test_zero_keys_is_the_empty_tuple(self):
        self.assertEqual(key.provisional_area_126_keys(0), ())

    def test_the_single_key_function_is_the_first_of_the_plural_one(self):
        self.assertEqual(
            key.provisional_area_126_key(),
            key.provisional_area_126_keys(1)[0],
        )

    def test_asking_for_more_than_exist_refuses_rather_than_repeats(self):
        too_many = len(key.AREA_126_SAILING_RESULT_IDS) + 1
        with self.assertRaises(key.SailingResultCopyError):
            key.provisional_area_126_keys(too_many)

    def test_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            key.provisional_area_126_keys(-1)


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
