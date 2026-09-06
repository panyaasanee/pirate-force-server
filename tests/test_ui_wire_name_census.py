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
shape of the ``gate-windows`` single-repo runner): **9** of this file's then-10
tests FAILED outright instead of skipping -- the tenth passes because it calls
no cross-repo input at all. That 9 is PR #961's reported ``pytest_subset``
"9 failed" exactly.

CORRECTION (round `d1b231`, pf-adversary, re-measured both shapes): the
paragraph above previously said "10 of this file's then-10 tests FAILED" and
then named the passing tenth in the same sentence -- the parenthetical refuted
the headline inside one sentence, and the wrong figure had been carried into
``docs/PYTEST_SKIP_PINS.json``'s note as well. Measured with the guards
stripped on a sibling-less checkout: the then-10 file gives 9 failed / 1
passed, today's file gives 10 failed / 1 passed. Both are corrected here and in
the pin.

CORRECTION 2 (same round, same pass): the sentence above used to end "with no
OS-path-separator mechanism involved at all", while
``WindowsPathSafetyTests``'s own docstring 90 lines below called the separator
bug "the actual cause of PR #961". One file, two opposite answers. The
reconciled statement: the MISSING GUARD is what produced #961's 9 failures --
the separator bug could not have caused them, because those tests never got far
enough to compare an evidence string. The separator bug is nonetheless real,
was proven separately by mutation, and would have produced its own Windows-only
`CENSUS DRIFT` later. ``WindowsPathSafetyTests``'s docstring is corrected to say
that instead.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
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

    def test_rerun_is_deterministic(self):
        # The cache MUST be cleared between the two builds. Before round
        # `d1b231` this test called build_rows() twice in a row, and
        # _CENSUS_INPUT_CACHE made the second call reuse the first call's
        # (names, source_hits, name_only_sources) tuple -- so it compared a
        # cached result against itself and could not fail for the reason it
        # names. Proven by pf-adversary: with _iter_py_files' sorted(...)
        # replaced by random.shuffle, this test still passed on its own.
        # With the clears below the same mutant makes it fail.
        census._CENSUS_INPUT_CACHE.clear()
        try:
            first = census.render_tsv(census.build_rows())
            census._CENSUS_INPUT_CACHE.clear()
            second = census.render_tsv(census.build_rows())
        finally:
            census._CENSUS_INPUT_CACHE.clear()
        self.assertEqual(first, second)


class IsClientReqRuleTests(unittest.TestCase):
    """Pure-function tests over string literals -- NO sibling checkout needed,
    so this class is deliberately NOT guarded and DOES run on `gate-windows`.

    Split out of ``BuildRowsTests`` in round `d1b231` (pf-adversary): the
    guard added in round `on8hbb` is applied at class granularity, so this
    test -- measured as the one test of the file that passes with no
    ``../pf_bridge`` sibling present -- was being skipped on the only CI this
    project runs pytest on. It is the ONLY test that ground-truths the
    ``is_client_req`` rule against the wire-naming convention rather than
    against itself (``test_is_client_req_flag_matches_the_helper_function``
    checks the rule against the rule), and it exists because round `9dezrf`'s
    ``name.endswith("Req")`` rule missed every ``...ReqVital[_REGION]`` name
    while that self-consistent test passed anyway. Skipping it on CI left that
    regression uncovered everywhere automated."""

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


class SourceHitPathSafetyTests(unittest.TestCase):
    """The Windows-only hazards of this tool, pinned WITHOUT the sibling
    checkout so they actually run on `gate-windows` -- the only CI here that
    runs pytest, and one that checks out this repo alone.

    ``WindowsPathSafetyTests`` below covers the same ``as_posix()`` line
    through the real catalog, so it is guarded and skips on that runner. That
    left PR #961's regression protection running nowhere automated
    (pf-adversary, round `d1b231`). These two tests drive the same code paths
    over a synthetic tree in a temp directory, with ``census.ROOT`` patched to
    it, so they need nothing outside this repo."""

    def test_evidence_uses_posix_separators_under_a_windows_style_relative_to(self):
        real_relative_to = pathlib.Path.relative_to

        def fake_relative_to(self, *args, **kwargs):
            # What real Windows returns: a WindowsPath, whose str() renders
            # backslashes.
            return pathlib.PureWindowsPath(
                str(real_relative_to(self, *args, **kwargs))
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "src" / "pirateforce_foundation"
            pkg.mkdir(parents=True)
            module = pkg / "ui_probe_wire.py"
            module.write_text("SOME_VITAL_ID = 1\n", encoding="utf-8")
            with mock.patch.object(census, "ROOT", root), mock.patch.object(
                pathlib.Path, "relative_to", fake_relative_to
            ):
                hits = census._build_source_hits({"SOME_VITAL_ID"}, [module])

        self.assertIn("SOME_VITAL_ID", hits)
        self.assertEqual(
            hits["SOME_VITAL_ID"],
            "src/pirateforce_foundation/ui_probe_wire.py:1",
            "evidence must be a posix path even when relative_to() returns a "
            "Windows-flavoured path -- str(relpath) instead of "
            "relpath.as_posix() is what closed PR #961 once already",
        )

    def test_sort_py_files_ignores_windows_path_comparison_semantics(self):
        # Fed PureWindowsPath objects, which carry Windows comparison
        # semantics on any host: PurePath.__lt__ compares _str_normcase, and
        # for the Windows flavour that is str(path).lower() -- backslash
        # separators AND case-folded. This is the test that actually bites on
        # Linux: with `sorted(files)` instead of the posix key, the two pairs
        # below come back in the other order right here.
        given = [
            pathlib.PureWindowsPath(p) for p in (
                "src/pf/bootstrap.py",
                "src/pf/Ui_shim.py",
                "src/pf/gm2_probe.py",
                "src/pf/gm/inner.py",
            )
        ]
        self.assertEqual(
            [p.as_posix() for p in census.sort_py_files(given)],
            [
                "src/pf/Ui_shim.py",   # 'U' 0x55 < 'b' 0x62 by byte;
                "src/pf/bootstrap.py",  # case-folded on Windows it is after
                "src/pf/gm/inner.py",   # '/' 0x2F < '2' 0x32 by byte;
                "src/pf/gm2_probe.py",  # as '\\' 0x5C it would be after
            ],
        )

    def test_py_file_order_does_not_depend_on_path_object_comparison(self):
        # The exact two shapes pf-adversary measured diverging: a capitalised
        # basename (Windows PurePath comparison case-folds) and a `gm/` package
        # against a `gm2_*` sibling ('/' 0x2F < '2' 0x32 by byte, but '2' 0x32
        # < '\\' 0x5C once separators are backslashes).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "gm").mkdir()
            for relative in (
                "Ui_shim.py", "bootstrap.py", "gm/inner.py", "gm2_probe.py",
            ):
                (root / relative).write_text("", encoding="utf-8")
            # Case-insensitive rglob on Windows would otherwise scan this one
            # while Linux ignores it.
            (root / "SHOUTING.PY").write_text("", encoding="utf-8")
            got = [
                p.relative_to(root).as_posix()
                for p in census._iter_py_files(root)
            ]

        self.assertEqual(
            got,
            ["Ui_shim.py", "bootstrap.py", "gm/inner.py", "gm2_probe.py"],
            "byte order of the posix path, identical on every OS -- sorting "
            "Path objects instead gives a different order on Windows, and "
            "_build_source_hits records the FIRST hit per name, so that order "
            "decides evidence values",
        )


@UI_WIRE_CENSUS_INPUTS.skip_unless_present()
class WindowsPathSafetyTests(unittest.TestCase):
    """Regression test for a Windows-only hazard found while diagnosing PR
    #961 -- NOT for #961's own 9 failures, which the missing precondition
    guard produced (see this module's docstring, CORRECTION 2; those tests
    errored long before any evidence string was compared). On real Windows, `Path.relative_to(...)` returns a
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
