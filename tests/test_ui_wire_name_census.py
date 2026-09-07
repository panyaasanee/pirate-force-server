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

import io
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
# Re-pinned round `fvp9ke` 2026-09-07 to 161/159/7 for two independent moves
# (`ShowMessageVital` 0x36D2 NAME-ONLY -> SOURCE when LANE-Q's message wire
# landed; `GuildStorageOpenVital` 0x5CAD and `GuildStorageResultVital` 0x70D0
# UNTOUCHED -> NAME-ONLY because that round's own `docs/UI_LANE.md` Stall row
# names them and that doc is one of the tool's four NAME-ONLY sources).
# NOTE, and do not let a later round misread it: naming a vital in the plan is
# NOT progress toward it working. See UI_WIRE_COVERAGE.md's movement log.
#
# Re-pinned again round `mg3nr4` 2026-09-07 to 160/160/7. ONE row moved back:
# `ShowMessageVital` (0x36D2) SOURCE -> NAME-ONLY, because LANE-Q moved that
# name into a full-line comment in `lua_api/message.py` (line 122 on main),
# and this tool deliberately does not count full-line comments. Measured, not
# assumed: `--emit` on the merged tree rewrites exactly that one artifact row
# and nothing else.
# This is NOT a regression of anyone's code. It is a name leaving the tier on
# a documentation edit, which is the same class of movement as the two
# GuildStorage rows above. `#987` pinned 161 from a tree derived BEFORE `#988`
# landed, so main carried a red pin + `CENSUS DRIFT` from the moment `#987`
# merged until this commit (COO-DECISION `20260907_0546` item 5: if it merged
# already, fixing the pin is the next round's first job -- this is it).
#
# Re-pinned a SECOND time in round `mg3nr4` to 30/286/11, in the same commit
# as the change that caused it: the tool stopped counting a name that appears
# only inside a docstring (COO-DECISION `20260907_0546`). 130 rows moved,
# 126 of them `ui_*_wire.py` modules that spell the wire name in their
# docstring frame table and name the class something shorter in the code.
# The drop is a measurement fix, not a regression -- full reasoning in
# docs/UI_WIRE_COVERAGE.md's movement log, open question to COO in
# `pf_bridge/notes_to_chief/20260907_0624_LANE-UI-ASK-COO-docstring-rule-drops-n327-from-160-to-30.md`.
EXPECT_TOTAL = 327
EXPECT_SOURCE = 30
EXPECT_NAME_ONLY = 286
EXPECT_UNTOUCHED = 11


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

    def test_source_tier_evidence_is_a_real_path_with_no_line_number(self):
        # Was `test_source_tier_evidence_is_a_real_path_and_line` until round
        # `o50gly`, which removed the line number from the artifact because it
        # made main go red on other lanes' unrelated edits -- see
        # `_build_source_hits`. The path half is asserted exactly as before;
        # the new half is that the line number is GONE, so that a future
        # re-introduction is a red test rather than a fresh drift treadmill.
        rows = census.build_rows()
        checked = 0
        for row in rows:
            if row["tier"] != "SOURCE":
                continue
            self.assertNotIn(":", row["evidence"], row["evidence"])
            self.assertTrue((ROOT / row["evidence"]).is_file(), row["evidence"])
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
            "src/pirateforce_foundation/ui_probe_wire.py",
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


# ---------------------------------------------------------------------------
# D7 (pf-adversary, round `d1b231`): every test above this line is gated by
# ``@UI_WIRE_CENSUS_INPUTS.skip_unless_present()``, so on a checkout WITHOUT a
# sibling ``pf_bridge`` -- which is exactly what ``gate-windows`` builds --
# they all skip and NOTHING in this file runs. The consequence measured that
# round: the two ``return 1`` exit paths of ``main()`` (artifact absent,
# artifact stale) and the ``return 2`` CensusError path have never been
# executed by any test on any machine, on any OS. A `CENSUS DRIFT` that
# silently returned 0 would have shipped green.
#
# The class below closes that hole and is deliberately NOT decorated: it feeds
# ``main()`` a fixed row list through ``build_rows`` and a temp-dir artifact
# path, so it depends on no file outside this repo and runs on the gate.
# Mocking ``build_rows`` is the point, not a shortcut -- what is under test is
# main()'s CONTRACT (which exit code and which stderr token for which state of
# the artifact file), not the census derivation, which the gated classes above
# already cover.
_FAKE_ROWS = [
    {
        "id": "0x1001",
        "name": "Community_ThrowLetterInABottle",
        "family": "Community",
        "is_client_req": "1",
        "tier": "SOURCE",
        "evidence": "src/pirateforce_foundation/ui_community_social_wire.py",
    },
    {
        "id": "0x1002",
        "name": "Pets_Feed",
        "family": "Pets",
        "is_client_req": "0",
        "tier": "UNTOUCHED",
        "evidence": "-",
    },
]


class MainExitCodeTests(unittest.TestCase):
    """The non-zero exit paths of ``main()``, with no sibling checkout."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.artifact = Path(self._tmp.name) / "census.tsv"
        patcher = mock.patch.object(census, "build_rows", return_value=list(_FAKE_ROWS))
        self.build_rows = patcher.start()
        self.addCleanup(patcher.stop)

    def _run(self, *extra):
        return census.main(["--artifact", str(self.artifact), *extra])

    def test_missing_artifact_exits_1_and_names_the_file(self):
        self.assertFalse(self.artifact.exists())
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            code = self._run()
        self.assertEqual(code, 1)
        self.assertIn("CENSUS DRIFT", err.getvalue())
        self.assertIn("does not exist", err.getvalue())
        self.assertIn(str(self.artifact), err.getvalue())

    def test_stale_artifact_exits_1_and_says_rerun_with_emit(self):
        # One byte of drift is enough: a single tier flipped in the committed
        # copy, which is the real-world shape (someone edits the artifact by
        # hand, or forgets --emit after a source change moves a name's tier).
        stale = census.render_tsv(_FAKE_ROWS).replace("UNTOUCHED", "SOURCE   ")
        self.artifact.write_text(stale, encoding="utf-8", newline="")
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            code = self._run()
        self.assertEqual(code, 1)
        self.assertIn("CENSUS DRIFT", err.getvalue())
        self.assertIn("does not match a fresh re-derive", err.getvalue())

    def test_artifact_missing_its_trailing_newline_is_drift_not_a_pass(self):
        # render_tsv() ends with "\n". An artifact committed without it is a
        # different byte stream and must fail, or the `--emit` output and the
        # committed file could disagree forever.
        rendered = census.render_tsv(_FAKE_ROWS)
        self.artifact.write_text(rendered.rstrip("\n"), encoding="utf-8", newline="")
        with mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(self._run(), 1)

    def test_matching_artifact_exits_0(self):
        self.artifact.write_text(census.render_tsv(_FAKE_ROWS), encoding="utf-8", newline="")
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            code = self._run()
        self.assertEqual(code, 0)
        self.assertIn("PASS", out.getvalue())

    def test_emit_writes_the_artifact_and_then_passes(self):
        self.assertFalse(self.artifact.exists())
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            code = self._run("--emit")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.artifact.read_text(encoding="utf-8"), census.render_tsv(_FAKE_ROWS)
        )

    def test_emit_writes_lf_not_crlf_under_windows_newline_translation(self):
        # The `newline=""` in main() is load-bearing: without it Python's text
        # mode writes "\r\n" on Windows, read_text()'s own universal-newline
        # translation hides that on read so THIS tool still passes, and every
        # other tool reading the artifact byte-for-byte sees a different file.
        #
        # Reading the bytes back on Linux CANNOT catch that -- text mode here
        # writes "\n" whether or not `newline=""` is passed, so the assertion
        # would hold against a mutant that deleted it (measured this round:
        # deleting `newline=""` left the whole file green). So emulate what
        # Windows text mode actually does -- translate "\n" to os.linesep when
        # the caller did NOT pin `newline` -- and then check the bytes. This
        # goes red on that mutant on any OS.
        real_write_text = pathlib.Path.write_text

        def windows_write_text(self, data, encoding=None, errors=None, newline=None):
            if newline is None:
                data = data.replace("\n", "\r\n")
            self.write_bytes(data.encode(encoding or "utf-8", errors or "strict"))
            return len(data)

        with mock.patch.object(pathlib.Path, "write_text", windows_write_text):
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                self._run("--emit")
        self.assertIs(pathlib.Path.write_text, real_write_text)
        raw = self.artifact.read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertTrue(raw.endswith(b"\n"))

    def test_census_error_exits_2_not_1(self):
        # A missing INPUT is a different failure from a stale artifact, and
        # the caller (the gate) is entitled to tell them apart.
        self.build_rows.side_effect = census.CensusError("boom")
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            code = self._run()
        self.assertEqual(code, 2)
        self.assertIn("CENSUS ERROR", err.getvalue())
        self.assertNotIn("CENSUS DRIFT", err.getvalue())

    def test_summary_exits_0_and_does_not_create_the_artifact(self):
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            code = self._run("--summary")
        self.assertEqual(code, 0)
        self.assertFalse(self.artifact.exists())
        self.assertIn("Community", out.getvalue())


class CoverageDocMatchesCommittedArtifactTests(unittest.TestCase):
    """`docs/UI_WIRE_COVERAGE.md` says "regenerate; do not hand-edit these
    numbers" -- but until this round nothing checked that anyone obeyed it,
    so the page could sit stale against its own artifact indefinitely (it
    did, for one name, at the start of round `fvp9ke`).

    Deliberately NOT gated on the sibling `pf_bridge` checkout: it reads the
    COMMITTED artifact in this repo instead of re-deriving, so it runs on
    `gate-windows` where the gated classes above all skip.
    """

    def setUp(self):
        self.artifact = census.DEFAULT_ARTIFACT
        self.doc = ROOT / "docs" / "UI_WIRE_COVERAGE.md"

    def _counts(self):
        rows = census.parse_tsv(self.artifact.read_text(encoding="utf-8"))
        total, by_tier, _ = census.summarize(rows)
        return total, by_tier

    def test_headline_numbers_match_the_artifact(self):
        total, by_tier = self._counts()
        text = self.doc.read_text(encoding="utf-8")
        self.assertIn(
            f"n/327 known (SOURCE) = {by_tier['SOURCE']}/{total}", text
        )
        self.assertIn(
            f"NAME-ONLY = {by_tier['NAME-ONLY']}  UNTOUCHED = {by_tier['UNTOUCHED']}",
            text,
        )

    def test_scoreboard_line_matches_the_artifact(self):
        total, by_tier = self._counts()
        text = self.doc.read_text(encoding="utf-8")
        self.assertIn(
            f"wire-names known n/327: {by_tier['SOURCE']}/{total}", text
        )

    def test_the_prose_numbers_in_the_non_claims_match_the_artifact(self):
        # pf-adversary D4 (round `mg3nr4`): the two tests above bound the
        # headline and the scoreboard, and NOTHING bound the three other
        # absolute numbers on the page. Measured: rewriting non-claim 1's
        # count to 999 or non-claim 3's to 4242 left the whole file green.
        # Not hypothetical -- round `fvp9ke` moved UNTOUCHED 9 -> 7 and left
        # non-claim 3 reading "some of the 9" for a whole round.
        total, by_tier = self._counts()
        text = self.doc.read_text(encoding="utf-8")
        self.assertIn(f"any of the {by_tier['SOURCE']} `SOURCE` names", text)
        self.assertIn(f"some of the {by_tier['UNTOUCHED']} may already", text)

    def test_the_plan_page_quotes_the_same_number(self):
        # `docs/UI_LANE.md` repeats the headline for readers who never open
        # the coverage page. It had no binding at all (same finding).
        #
        # 🔴 Note for whoever edits that file: it is ALSO one of the four
        # NAME-ONLY sources the census reads, so writing or deleting a vital
        # NAME there moves tiers. Only digits are bound here, and digits are
        # not vital names, so this assertion cannot feed itself.
        total, by_tier = self._counts()
        text = (ROOT / "docs" / "UI_LANE.md").read_text(encoding="utf-8")
        self.assertIn(f"Current: **{by_tier['SOURCE']}/{total}**", text)

    def test_artifact_row_count_is_the_whole_catalog(self):
        total, _ = self._counts()
        self.assertEqual(total, EXPECT_TOTAL)


class ProseStringNamesAreNotSourceTests(unittest.TestCase):
    """A vital name that appears ONLY inside a docstring is prose, not a
    reference -- COO-DECISION `pf_bridge/notes_to_chief/
    20260907_0546_COO-DECISION-q0454-census-tool-skips-docstrings-LANE-UI.md`,
    on LANE-Q's `0454` alert.

    Why this matters more than a rounding error: before this rule, a lane
    writing the HONEST note "this module does not build ``XxxVital``" pushed
    n/327 UP by one with nothing wired. The metric moved in the opposite
    direction from the thing it measures, and an inflated value reads as
    progress on the encyclopedia page.

    Unguarded on purpose: these drive ``_build_source_hits`` and
    ``docstring_line_numbers`` over a synthetic tree in a temp directory, so
    they need no `pf_bridge` sibling and therefore actually run on
    `gate-windows`, the only CI that runs pytest here."""

    NAME = "Community_ProbeOnlyVital"

    def _hits(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "src" / "pirateforce_foundation"
            pkg.mkdir(parents=True)
            module = pkg / "ui_probe_wire.py"
            module.write_text(source, encoding="utf-8")
            with mock.patch.object(census, "ROOT", root):
                return census._build_source_hits({self.NAME}, [module])

    def test_name_only_in_a_module_docstring_is_not_a_source_hit(self):
        hits = self._hits(f'"""Table of frames:\n\n    {self.NAME}  0x0001\n"""\n\nX = 1\n')
        self.assertEqual(
            hits,
            {},
            "a wire name that exists only in the module docstring must not "
            "count as SOURCE; this is the exact shape of every ui_*_wire.py "
            "docstring frame table",
        )

    def test_name_only_in_a_function_or_class_docstring_is_not_a_source_hit(self):
        self.assertEqual(
            self._hits(f'class Fields:\n    """See {self.NAME} rows."""\n\n    n = 1\n'),
            {},
        )
        self.assertEqual(
            self._hits(f'def build():\n    """Encodes {self.NAME}."""\n    return 1\n'),
            {},
        )

    def test_the_same_name_in_real_code_is_still_a_source_hit(self):
        # The other half of the mutant: the rule must remove docstring prose
        # WITHOUT removing genuine references, or it would zero the census.
        hits = self._hits(f'"""Doc."""\n\nWIRE_NAME = "{self.NAME}"\n')
        self.assertEqual(
            hits[self.NAME], "src/pirateforce_foundation/ui_probe_wire.py"
        )

    def test_a_second_bare_string_is_prose_too_not_only_the_first(self):
        # THE D1 BYPASS, pinned shut (round `mg3nr4`, pf-adversary). The
        # first version of this rule matched Python's own docstring
        # definition -- first statement only -- so prepending one extra
        # one-line docstring above a module's prose block demoted that block
        # to a "not a docstring" and made it count as code again. Measured
        # on that version: doing it to every ui_*_wire.py moved n/327 from
        # 30 to 149 with no wire code touched, and a lint rule asking for a
        # one-line summary would have done it by accident. An earlier draft
        # of this very test asserted the OPPOSITE and pinned the hole open.
        self.assertEqual(self._hits(f'"""Summary."""\n"{self.NAME}"\n'), {})
        self.assertEqual(self._hits(f'X = 1\n"{self.NAME}"\n'), {})

    def test_a_string_bound_to_a_name_or_passed_as_an_argument_is_code(self):
        # The other side of the same knife: exclude bare STATEMENTS, never
        # string values. Over-excluding here would zero the census.
        self.assertEqual(
            self._hits(f'"""Doc."""\n\nWIRE_NAME = "{self.NAME}"\n')[self.NAME],
            "src/pirateforce_foundation/ui_probe_wire.py",
        )
        self.assertEqual(
            self._hits(f'"""Doc."""\n\nregister("{self.NAME}")\n')[self.NAME],
            "src/pirateforce_foundation/ui_probe_wire.py",
        )
        self.assertEqual(
            self._hits(f'"""Doc."""\n\nNAMES = ["{self.NAME}"]\n')[self.NAME],
            "src/pirateforce_foundation/ui_probe_wire.py",
        )

    def test_a_method_docstring_inside_a_class_is_prose(self):
        # pf-adversary D2: the earlier witnesses used a TOP-LEVEL class and a
        # TOP-LEVEL def, so `for node in ast.walk(tree)` and a top-level-only
        # scan were indistinguishable. Measured that round: the top-level
        # mutant left all of these green while the live census moved 30 -> 36,
        # and the only test that caught it is guarded and skips on
        # gate-windows. Six runtime.py METHOD docstrings were the difference.
        self.assertEqual(
            self._hits(
                "class Handler:\n"
                "    def run(self):\n"
                f'        """Handles {self.NAME}."""\n'
                "        return 1\n"
            ),
            {},
        )

    def test_an_async_method_docstring_is_prose(self):
        # pf-adversary D3: the async branch of the first version was never
        # measured (no `async def` exists in src/). Under the bare-statement
        # rule there is no per-node-type branch left to go untested, and this
        # witness keeps it that way if one is ever reintroduced.
        self.assertEqual(
            self._hits(
                "class Handler:\n"
                "    async def run(self):\n"
                f'        """Handles {self.NAME}."""\n'
                "        return 1\n"
            ),
            {},
        )

    def test_a_form_feed_does_not_shift_the_excluded_line_numbers(self):
        # pf-adversary D6: str.splitlines() breaks on FF/VT/FS/GS/RS/NEL/
        # U+2028/U+2029 and ast does not, so one form feed inside a docstring
        # shifted every later line number and INVERTED the exclusion -- real
        # code skipped, docstring prose counted. Latent (0 such characters in
        # the tree today), fixed by splitting on "\n" only.
        source = (
            '"""line one\x0cline two\n"""\n'
            "def f():\n"
            f'    """Mentions {self.NAME}."""\n'
            "    return 1\n"
        )
        self.assertEqual(self._hits(source), {})

    def test_a_utf8_bom_does_not_disable_the_rule(self):
        # pf-adversary D7: ast.parse raises on a leading BOM, which would
        # drop that file back to comment-skip-only and start counting its
        # docstrings again. This repo syncs from a Windows/PowerShell bridge
        # whose default output encoding writes one.
        self.assertEqual(self._hits(f'\ufeff"""Mentions {self.NAME}."""\nX = 1\n'), {})

    def test_no_file_in_the_tree_falls_back_to_the_unparseable_path(self):
        # The fallback is deliberately permissive, so it must not be a silent
        # skip: a file in this list has its prose counted as code, which moves
        # the census with nothing to point at. Reads only this repo, so it
        # runs on gate-windows.
        bad = census.unparseable_py_files(census._iter_py_files(census.SRC_DIR))
        self.assertEqual(
            [p.name for p in bad],
            [],
            "these files did not parse, so their docstrings are being counted "
            "as code -- fix the file or the census number is wrong",
        )

    def test_a_reference_after_a_multi_line_docstring_keeps_its_own_line_number(self):
        # Off-by-one guard: the exclusion covers lineno..end_lineno of the
        # docstring literal and must not eat the line after its closing
        # quotes.
        source = f'"""line one\nline two\nline three\n"""\nWIRE = "{self.NAME}"\n'
        hits = self._hits(source)
        self.assertEqual(
            hits[self.NAME], "src/pirateforce_foundation/ui_probe_wire.py"
        )

    def test_a_file_that_does_not_parse_falls_back_to_comment_skipping_only(self):
        # Fallback is the tool's PREVIOUS behaviour, which can only
        # over-count. A parse error must never make a name silently vanish
        # from the census, because that would look like a lane's module
        # disappearing.
        hits = self._hits(f'def broken(\nWIRE = "{self.NAME}"\n')
        self.assertEqual(
            hits[self.NAME], "src/pirateforce_foundation/ui_probe_wire.py"
        )
        self.assertEqual(census.prose_string_line_numbers("def broken(\n"), frozenset())

    def test_full_line_comments_are_still_skipped_as_well(self):
        self.assertEqual(self._hits(f"# {self.NAME} is not built here\nX = 1\n"), {})

    def test_prose_string_line_numbers_reports_the_whole_literal_span(self):
        self.assertEqual(
            census.prose_string_line_numbers('"""a\nb\nc"""\nX = 1\n'), frozenset({1, 2, 3})
        )


class EvidenceIsInsensitiveToUnrelatedEditsTests(unittest.TestCase):
    """Round `o50gly`. The committed artifact used to carry `file:line` for
    every SOURCE row, so ANY lane adding lines above a cited hit rewrote this
    lane's artifact and turned `test_committed_artifact_matches_a_fresh_
    rederive` red on main with no census-relevant change anywhere.

    That is not hypothetical: it is how main was red at the start of this
    round. On `6b5b6b8`, LANE-GM's growth of `gm/command_capture.py` moved
    `GM_RunGMCommandVital` from line 750 to 800 and `Activity_CheatCodeVital`
    from 803 to 853 -- same file, same tier, same 30/286/11 counts -- and the
    drift test failed. The files this census cites most (`runtime.py`, 9 rows;
    the `gm/` catalogs; `delete_actor.py`) belong to OTHER lanes, so the red
    recurs on their schedule and only this lane can clear it.

    Unguarded on purpose, like the class above: it drives
    ``_build_source_hits`` over a synthetic tree in a temp directory, so it
    needs no ``pf_bridge`` sibling and actually runs on `gate-windows`."""

    NAME = "Community_ProbeOnlyVital"

    def _hits(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "src" / "pirateforce_foundation"
            pkg.mkdir(parents=True)
            module = pkg / "ui_probe_wire.py"
            module.write_text(source, encoding="utf-8")
            with mock.patch.object(census, "ROOT", root):
                return census._build_source_hits({self.NAME}, [module])

    def test_padding_above_the_hit_does_not_change_the_evidence(self):
        # The exact shape of the main-red: unrelated code grows above the
        # cited name. Evidence must be byte-identical, or the artifact drifts
        # for a reason that has nothing to do with the census.
        near = self._hits(f'WIRE = "{self.NAME}"\n')
        far = self._hits("X = 1\n" * 50 + f'WIRE = "{self.NAME}"\n')
        self.assertEqual(near, far)
        self.assertEqual(near[self.NAME], "src/pirateforce_foundation/ui_probe_wire.py")

    def test_padding_above_the_hit_does_not_change_a_rendered_row(self):
        # Same property one layer up, at the artifact text the drift test
        # compares -- so a future change that re-introduces a line number
        # anywhere between the hit and the TSV is red here too.
        def render(source):
            hits = self._hits(source)
            return census.render_tsv(
                [
                    {
                        "id": "0x0001",
                        "name": self.NAME,
                        "family": "Community_",
                        "is_client_req": "0",
                        "tier": "SOURCE",
                        "evidence": hits[self.NAME],
                    }
                ]
            )

        self.assertEqual(
            render(f'WIRE = "{self.NAME}"\n'),
            render('"""Docstring that grew."""\n\n' + "X = 1\n" * 30 + f'WIRE = "{self.NAME}"\n'),
        )

    def test_a_move_to_a_DIFFERENT_file_still_changes_the_evidence(self):
        # The other half: dropping the line number must not make evidence
        # blind. A name that moves between files is a real census change and
        # still has to rewrite the artifact.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "src" / "pirateforce_foundation"
            pkg.mkdir(parents=True)
            first = pkg / "ui_probe_wire.py"
            second = pkg / "ui_other_wire.py"
            first.write_text("X = 1\n", encoding="utf-8")
            second.write_text(f'WIRE = "{self.NAME}"\n', encoding="utf-8")
            with mock.patch.object(census, "ROOT", root):
                hits = census._build_source_hits({self.NAME}, [first, second])
        self.assertEqual(hits[self.NAME], "src/pirateforce_foundation/ui_other_wire.py")


if __name__ == "__main__":
    unittest.main()
