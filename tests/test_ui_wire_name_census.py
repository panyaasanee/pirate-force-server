"""Tests for tools/pf_ui_wire_name_census.py -- PANYA `2032` job 2 (LANE-UI).

Pins the numbers this round's SCOREBOARD line and docs/UI_WIRE_COVERAGE.md
quote, the same way tests/test_names_fold003_thunk_census.py pins its own
tool's counts in a second, independent place. If the source tree changes in a
way that moves a name across tiers, this file is meant to go red so the next
round updates the pinned numbers and the committed artifact together instead
of the page silently going stale.

Needs the sibling ``pf_bridge`` checkout (for the master catalog tsv and the
two ``external/`` registries) the same way every other cross-repo census test
in this suite does. Guarded with ``UI_WIRE_CENSUS_INPUTS``
(``tests/pf_preconditions.py``), named for the exact three files this tool
reads (not the too-broad ``EXTERNAL_RE_TABLES``/``BRIDGE_SIBLING`` keys --
see that precondition's own docstring for why).

CORRECTION (round `on8hbb`, pf-adversary, measured): this file previously
claimed "No skip guard: ... every sibling-repo census test in this suite
assumes the checkout is there rather than adding a new pinned skip for it",
citing tests/test_field_mob_tables_bg0002.py's bare ``ROOT.parent /
"pf_bridge"`` path construction as precedent. That citation was false --
that file has its own ``BRIDGE_GAMEDATA.skip_unless_present()`` guard two
lines below the path literal it cited. A guard used to exist here too (a
``unittest.skipIf`` deleted in round `9dezrf` on the same false citation).
Reproduced directly on a checkout with no ``../pf_bridge`` sibling (the exact
shape of the ``gate-windows`` single-repo runner): 10 of this file's then-10
tests FAILED outright instead of skipping -- this is PR #961's reported
``pytest_subset`` "9 failed" (one of the ten tests does not call
``build_rows()``), with no OS-path-separator mechanism involved at all.
"""
from __future__ import annotations

import pathlib
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools import pf_ui_wire_name_census as census  # noqa: E402
from pf_preconditions import UI_WIRE_CENSUS_INPUTS  # noqa: E402

# Pinned this round (`9dezrf`, after pf-adversary's comment-line-exclusion
# fix) against DEFAULT_TSV as committed today. A tier move for any name
# changes at least one of these four numbers.
EXPECT_TOTAL = 327
EXPECT_SOURCE = 160
EXPECT_NAME_ONLY = 158
EXPECT_UNTOUCHED = 9


@UI_WIRE_CENSUS_INPUTS.skip_unless_present()
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

    def test_is_client_req_flag_matches_the_helper_function(self):
        # Checked against census.is_client_req(), not re-derived inline --
        # a test that re-states the production rule tests the rule against
        # itself and cannot catch the rule being wrong (pf-adversary, round
        # `9dezrf`: the original `name.endswith("Req")` rule passed this
        # exact shape of test while missing every `...ReqVital[_REGION]` name).
        rows = census.build_rows()
        for row in rows:
            expected = "1" if census.is_client_req(row["name"]) else "0"
            self.assertEqual(row["is_client_req"], expected)

    def test_is_client_req_matches_both_wire_naming_conventions(self):
        # Ground-truthed against this repo's own evidence, not the rule under
        # test: trace_path.py's docstring calls CTracePathReqVital inbound
        # (the client sends it) in so many words.
        self.assertTrue(census.is_client_req("CTracePathReqVital"))
        self.assertTrue(census.is_client_req("ItemOperateVitalReq"))
        self.assertTrue(census.is_client_req("CHitParadeReqVital_JP"))
        # "Request" is a different PascalCase word than the "Req" abbreviation
        # the wire-naming convention actually uses -- must NOT be flagged.
        self.assertFalse(census.is_client_req("Community_RequestBeFriendVital"))
        self.assertFalse(census.is_client_req("Community_RequestSoulMateMatchVital"))

    def test_rerun_is_deterministic(self):
        first = census.render_tsv(census.build_rows())
        second = census.render_tsv(census.build_rows())
        self.assertEqual(first, second)


@UI_WIRE_CENSUS_INPUTS.skip_unless_present()
class WindowsPathSafetyTests(unittest.TestCase):
    """Regression test for the actual cause of PR #961's Windows-only
    `pytest_subset` failures (COO-DECISION 20260907_0148, LANE-UI round
    `on8hbb`): on real Windows, `Path.relative_to(...)` returns a
    `WindowsPath`, whose `str()` renders backslashes
    (`src\\pirateforce_foundation\\x.py`) instead of the forward slashes
    baked into the committed artifact (generated on Linux). This test
    cannot run on real Windows here, so it simulates the same shape of
    return value with `PureWindowsPath` instead, and would fail if
    `_build_source_hits` ever goes back to `str(relpath)` instead of
    `relpath.as_posix()`."""

    def test_source_hit_evidence_uses_posix_separators_even_under_a_windows_style_relative_to(self):
        real_relative_to = pathlib.Path.relative_to

        def fake_relative_to(self, *args, **kwargs):
            result = real_relative_to(self, *args, **kwargs)
            return pathlib.PureWindowsPath(str(result))

        census._CENSUS_INPUT_CACHE.clear()
        try:
            with mock.patch.object(pathlib.Path, "relative_to", fake_relative_to):
                rows = census.build_rows()
        finally:
            # Leave no mocked-path-derived entries cached for later tests.
            census._CENSUS_INPUT_CACHE.clear()

        checked = 0
        for row in rows:
            if row["tier"] != "SOURCE":
                continue
            self.assertNotIn("\\", row["evidence"], row["evidence"])
            checked += 1
        self.assertGreater(checked, 0)


@UI_WIRE_CENSUS_INPUTS.skip_unless_present()
class CommittedArtifactTests(unittest.TestCase):
    def test_committed_artifact_matches_a_fresh_rederive(self):
        self.assertEqual(census.main(["--tsv", str(census.DEFAULT_TSV)]), 0)

    def test_committed_artifact_round_trips_through_parse_tsv(self):
        rendered = census.render_tsv(census.build_rows())
        parsed = census.parse_tsv(rendered)
        self.assertEqual(census.render_tsv(parsed), rendered)


if __name__ == "__main__":
    unittest.main()
