"""Tests for tools/pf_ui_wire_name_census.py -- PANYA `2032` job 2 (LANE-UI).

Pins the numbers this round's SCOREBOARD line and docs/UI_WIRE_COVERAGE.md
quote, the same way tests/test_names_fold003_thunk_census.py pins its own
tool's counts in a second, independent place. If the source tree changes in a
way that moves a name across tiers, this file is meant to go red so the next
round updates the pinned numbers and the committed artifact together instead
of the page silently going stale.

Needs the sibling ``pf_bridge`` checkout (for the master catalog tsv and the
two ``external/`` registries) the same way every other cross-repo census test
in this suite does -- see tools/pf_vital_names.py's own DEFAULT_TSV. SKIPs
loudly, with the missing path in the message, if that checkout is absent.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from tools import pf_ui_wire_name_census as census

ROOT = Path(__file__).resolve().parents[1]

# Pinned this round (`9dezrf`) against DEFAULT_TSV as committed today. A tier
# move for any name changes at least one of these four numbers.
EXPECT_TOTAL = 327
EXPECT_SOURCE = 161
EXPECT_NAME_ONLY = 157
EXPECT_UNTOUCHED = 9


def _bridge_missing_reason():
    if not census.DEFAULT_TSV.exists():
        return f"sibling pf_bridge checkout not found: {census.DEFAULT_TSV}"
    return None


@unittest.skipIf(_bridge_missing_reason(), _bridge_missing_reason() or "")
class BuildRowsTests(unittest.TestCase):
    def test_row_count_matches_the_master_catalog(self):
        rows = census.build_rows()
        self.assertEqual(len(rows), EXPECT_TOTAL)

    def test_pinned_tier_counts(self):
        rows = census.build_rows()
        total, by_tier, _by_family = census.summarize(rows)
        self.assertEqual(total, EXPECT_TOTAL)
        self.assertEqual(by_tier["SOURCE"], EXPECT_SOURCE)
        self.assertEqual(by_tier["NAME-ONLY"], EXPECT_NAME_ONLY)
        self.assertEqual(by_tier["UNTOUCHED"], EXPECT_UNTOUCHED)

    def test_every_row_has_one_of_the_three_tiers(self):
        rows = census.build_rows()
        for row in rows:
            self.assertIn(row["tier"], ("SOURCE", "NAME-ONLY", "UNTOUCHED"))

    def test_source_tier_evidence_is_a_real_path_and_line(self):
        rows = census.build_rows()
        checked = 0
        for row in rows:
            if row["tier"] != "SOURCE":
                continue
            path_part, _, line_part = row["evidence"].rpartition(":")
            self.assertTrue(line_part.isdigit(), row["evidence"])
            self.assertTrue((ROOT / path_part).is_file(), row["evidence"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_untouched_rows_have_no_evidence(self):
        rows = census.build_rows()
        for row in rows:
            if row["tier"] == "UNTOUCHED":
                self.assertEqual(row["evidence"], "-")

    def test_is_client_req_flag_matches_the_req_suffix(self):
        rows = census.build_rows()
        for row in rows:
            self.assertEqual(row["is_client_req"], "1" if row["name"].endswith("Req") else "0")

    def test_rerun_is_deterministic(self):
        first = census.render_tsv(census.build_rows())
        second = census.render_tsv(census.build_rows())
        self.assertEqual(first, second)


@unittest.skipIf(_bridge_missing_reason(), _bridge_missing_reason() or "")
class CommittedArtifactTests(unittest.TestCase):
    def test_committed_artifact_matches_a_fresh_rederive(self):
        self.assertEqual(census.main(["--tsv", str(census.DEFAULT_TSV)]), 0)

    def test_committed_artifact_round_trips_through_parse_tsv(self):
        rendered = census.render_tsv(census.build_rows())
        parsed = census.parse_tsv(rendered)
        self.assertEqual(census.render_tsv(parsed), rendered)


if __name__ == "__main__":
    unittest.main()
