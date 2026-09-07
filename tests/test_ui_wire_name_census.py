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


@UI_WIRE_CENSUS_INPUTS.skip_unless_present()
class WhereAgreesWithTheArtifactOnTheRealTreeTests(unittest.TestCase):
    """The same invariant as ``WhereAndCensusCannotDisagreeTests``, but over
    all 327 real names and the real `src/` tree instead of a fixture.

    Guarded (needs the sibling catalog), so it does NOT run on
    `gate-windows` -- that is why the unguarded class above exists and why it
    varies file count, depth and name-set size by hand. This one is the
    ground truth the fixture is modelled on: if a future change makes them
    disagree only at scale, this catches it here even though the gate cannot.
    Round `8btjto`, pf-adversary D-A on `#1013` (the check the reviewer ran
    by hand and got 0 conflicts from)."""

    def test_every_source_row_is_the_file_where_answers(self):
        rows = census.build_rows()
        checked = 0
        for row in rows:
            if row["tier"] != "SOURCE":
                continue
            location = census.source_hit_location(row["name"])
            self.assertIsNotNone(
                location,
                f"{row['name']} is a SOURCE row but --where finds nothing",
            )
            self.assertEqual(
                row["evidence"],
                location[0],
                f"--where sends a reader to a different file from the "
                f"artifact for {row['name']}",
            )
            checked += 1
        self.assertEqual(checked, EXPECT_SOURCE)

    def test_no_non_source_name_gets_an_answer(self):
        # The other half of the agreement: a name the artifact does NOT call
        # SOURCE must have no counted occurrence for `--where` either.
        #
        # A miss makes `source_hit_location` walk and parse the WHOLE tree,
        # so this samples rather than looping over all 297 non-SOURCE names:
        # the full sweep ran for minutes, and a test nobody waits for is a
        # test nobody runs. The one-pass equivalent over EVERY name is the
        # assertion below, which costs a single walk.
        rows = census.build_rows()
        misses = [row["name"] for row in rows if row["tier"] != "SOURCE"]
        self.assertEqual(len(misses), EXPECT_NAME_ONLY + EXPECT_UNTOUCHED)
        for name in misses[:5] + misses[-5:]:
            with self.subTest(name=name):
                self.assertIsNone(census.source_hit_location(name))

    def test_the_source_tier_is_exactly_the_set_with_a_counted_hit(self):
        # One walk, every name: the tier assignment and the hit map must
        # partition the catalog the same way.
        rows = census.build_rows()
        names = {row["name"] for row in rows}
        hits = census._build_source_hits(
            names, census._iter_py_files(census.SRC_DIR)
        )
        self.assertEqual(
            {row["name"] for row in rows if row["tier"] == "SOURCE"},
            set(hits),
        )

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

    def _assert_page_has(self, needle, text, page):
        """``assertIn``, minus unittest's habit of pasting the WHOLE container
        into the failure message.

        pf-adversary D-I on `#1013`: the day one of these pages drifts -- the
        day this class exists for -- the failure message would carry every
        byte of a Markdown file that contains U+1F534, and the bridge console
        is cp874. The test would then die with `UnicodeEncodeError` INSTEAD of
        showing the drift, on exactly the run that matters. The page names and
        the needle are ASCII, so this message always prints."""

        self.assertTrue(
            needle in text,
            "docs/%s does not contain %r -- regenerate the page from the "
            "committed artifact (do not hand-edit the numbers)" % (page, needle),
        )

    def _counts(self):
        rows = census.parse_tsv(self.artifact.read_text(encoding="utf-8"))
        total, by_tier, _ = census.summarize(rows)
        return total, by_tier

    def test_headline_numbers_match_the_artifact(self):
        total, by_tier = self._counts()
        text = self.doc.read_text(encoding="utf-8")
        self._assert_page_has(
            f"n/327 known (SOURCE) = {by_tier['SOURCE']}/{total}",
            text,
            "UI_WIRE_COVERAGE.md",
        )
        self._assert_page_has(
            f"NAME-ONLY = {by_tier['NAME-ONLY']}  UNTOUCHED = {by_tier['UNTOUCHED']}",
            text,
            "UI_WIRE_COVERAGE.md",
        )

    def test_scoreboard_line_matches_the_artifact(self):
        total, by_tier = self._counts()
        text = self.doc.read_text(encoding="utf-8")
        self._assert_page_has(
            f"wire-names known n/327: {by_tier['SOURCE']}/{total}",
            text,
            "UI_WIRE_COVERAGE.md",
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
        self._assert_page_has(
            f"any of the {by_tier['SOURCE']} `SOURCE` names",
            text,
            "UI_WIRE_COVERAGE.md",
        )
        self._assert_page_has(
            f"some of the {by_tier['UNTOUCHED']} may already",
            text,
            "UI_WIRE_COVERAGE.md",
        )

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
        self._assert_page_has(
            f"Current: **{by_tier['SOURCE']}/{total}**", text, "UI_LANE.md"
        )

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

    # NOT a `ui_*` filename, and the padded shapes below are >100 lines
    # (pf-adversary D1 on `#1005`, round `jx6r5p`). The first version of this
    # class built every synthetic file as `ui_probe_wire.py` at <=52 lines --
    # but ZERO of the 30 real SOURCE rows live in a `ui_*` file, and the two
    # rows this whole change was built on sit past line 800 of an 857-line
    # file. So four measured mutants of `_build_source_hits` that re-introduce
    # the line number CONDITIONALLY (only for `ui_`-prefixed filenames, only
    # for files under ~100 lines, only below line 60, only outside
    # `src/.../ui_`) passed this class 34/34 in the `gate-windows` shape,
    # where the two tests that DO catch them are both skipped for want of a
    # `pf_bridge` sibling. The fixture, not the assertion, was the hole.
    DEFAULT_MODULE = "runtime.py"
    PAD = "X = 1\n" * 150

    def _hits(self, source, module_name=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "src" / "pirateforce_foundation"
            pkg.mkdir(parents=True)
            module = pkg / (module_name or self.DEFAULT_MODULE)
            module.write_text(source, encoding="utf-8")
            with mock.patch.object(census, "ROOT", root):
                return census._build_source_hits({self.NAME}, [module])

    def test_no_file_shape_re_introduces_a_line_number(self):
        # One assertion over the cross product the old fixture could not see:
        # `ui_`-prefixed and not, short and long, hit at line 1 and hit past
        # line 150. Each of the four conditional mutants above is red here on
        # `gate-windows`, with no sibling checkout.
        for module_name in ("runtime.py", "ui_probe_wire.py", "delete_actor.py"):
            for label, source in (
                ("short", f'WIRE = "{self.NAME}"\n'),
                ("long", self.PAD + f'WIRE = "{self.NAME}"\n'),
            ):
                with self.subTest(module=module_name, shape=label):
                    evidence = self._hits(source, module_name)[self.NAME]
                    self.assertEqual(
                        evidence, f"src/pirateforce_foundation/{module_name}"
                    )
                    self.assertNotIn(":", evidence)

    def test_padding_above_the_hit_does_not_change_the_evidence(self):
        # The exact shape of the main-red: unrelated code grows above the
        # cited name. Evidence must be byte-identical, or the artifact drifts
        # for a reason that has nothing to do with the census.
        near = self._hits(f'WIRE = "{self.NAME}"\n')
        far = self._hits(self.PAD + f'WIRE = "{self.NAME}"\n')
        self.assertEqual(near, far)
        self.assertEqual(near[self.NAME], "src/pirateforce_foundation/runtime.py")

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
            render('"""Docstring that grew."""\n\n' + self.PAD + f'WIRE = "{self.NAME}"\n'),
        )

    def test_a_move_to_a_DIFFERENT_file_still_changes_the_evidence(self):
        # The other half: dropping the line number must not make evidence
        # blind. A name that moves between files is a real census change and
        # still has to rewrite the artifact.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "src" / "pirateforce_foundation"
            pkg.mkdir(parents=True)
            first = pkg / "delete_actor.py"
            second = pkg / "runtime.py"
            first.write_text(self.PAD, encoding="utf-8")
            second.write_text(self.PAD + f'WIRE = "{self.NAME}"\n', encoding="utf-8")
            with mock.patch.object(census, "ROOT", root):
                hits = census._build_source_hits({self.NAME}, [first, second])
        self.assertEqual(hits[self.NAME], "src/pirateforce_foundation/runtime.py")


class SourceHitLocationTests(unittest.TestCase):
    """``--where`` / ``source_hit_location()`` -- the supported way to recover
    the line number the artifact stopped carrying in round `o50gly`.

    Round `o50gly` deleted the line number from `evidence` and offered
    ``grep -n "<name>" <file>`` in exchange, in three places (the commit
    message, this tool's own comment, and `docs/UI_WIRE_COVERAGE.md`).
    pf-adversary D2 on `#1005` measured that trade as wrong, and this lane
    re-measured it on `82a3b54` before accepting: grep reports docstring
    bodies and full-line comments, which the census does not count, so grep's
    FIRST hit is a different line from the counted one on 18 of the 30 SOURCE
    rows -- including both rows whose drift motivated the change, because
    `gm/command_capture.py` spells `GM_RunGMCommandVital` and
    `Activity_CheatCodeVital` in its module docstring at lines 3 and 4. The
    documented recovery handed back exactly the prose hit rounds `9dezrf` and
    `mg3nr4` were spent excluding.

    Unguarded on purpose, like the two classes above: a synthetic tree in a
    temp directory, no `pf_bridge` sibling, so this runs on `gate-windows`."""

    NAME = "Community_ProbeOnlyVital"

    # The real shape, not a toy: a module docstring frame table naming the
    # vital near the top, and the code that actually references it far below.
    DOCSTRING_LINE = 3
    PROSE_HEAD = f'"""Frames handled here:\n\n    {NAME}  0x0001  5 fields\n"""\n'
    PAD = "X = 1\n" * 150

    def _tree(self, source, module_name="gm_command_capture.py"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        pkg = root / "src" / "pirateforce_foundation"
        pkg.mkdir(parents=True)
        module = pkg / module_name
        module.write_text(source, encoding="utf-8")
        return root, module

    @staticmethod
    def _first_textual_line(module, name):
        """What ``grep -n`` would answer: the first line containing the name,
        counted by nobody's rule but the reader's."""
        for lineno, line in enumerate(
            module.read_text(encoding="utf-8").split("\n"), start=1
        ):
            if name in line:
                return lineno
        return None

    def test_where_returns_the_counted_line_not_the_first_textual_line(self):
        source = self.PROSE_HEAD + self.PAD + f'WIRE = "{self.NAME}"\n'
        root, module = self._tree(source)
        with mock.patch.object(census, "ROOT", root):
            location = census.source_hit_location(self.NAME, [module])
        self.assertIsNotNone(location)
        relpath, lineno = location
        self.assertEqual(relpath, "src/pirateforce_foundation/gm_command_capture.py")
        # The line the census counted: the assignment under the padding.
        self.assertEqual(lineno, len(self.PROSE_HEAD.split("\n")) - 1 + 150 + 1)
        # ... and it is NOT what grep would have said. If these two ever
        # agree on this fixture the test has stopped testing anything.
        grep_line = self._first_textual_line(module, self.NAME)
        self.assertEqual(grep_line, self.DOCSTRING_LINE)
        self.assertNotEqual(grep_line, lineno)

    def test_where_names_the_same_file_the_artifact_names(self):
        # The recovery command must not be able to point at a different file
        # from the one the evidence column carries; they share
        # `code_token_lines` and the file order for exactly this reason.
        source = self.PROSE_HEAD + self.PAD + f'WIRE = "{self.NAME}"\n'
        root, module = self._tree(source)
        with mock.patch.object(census, "ROOT", root):
            hits = census._build_source_hits({self.NAME}, [module])
            location = census.source_hit_location(self.NAME, [module])
        self.assertEqual(hits[self.NAME], location[0])

    def test_where_skips_a_docstring_only_name_entirely(self):
        root, module = self._tree(self.PROSE_HEAD + "X = 1\n")
        with mock.patch.object(census, "ROOT", root):
            self.assertIsNone(census.source_hit_location(self.NAME, [module]))

    def test_where_skips_a_full_line_comment_only_name_entirely(self):
        root, module = self._tree(f"# see {self.NAME} for the layout\nX = 1\n")
        with mock.patch.object(census, "ROOT", root):
            self.assertIsNone(census.source_hit_location(self.NAME, [module]))

    def test_where_takes_the_first_file_in_census_order(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        pkg = root / "src" / "pirateforce_foundation"
        pkg.mkdir(parents=True)
        first = pkg / "a_wire.py"
        second = pkg / "z_wire.py"
        first.write_text(self.PAD + f'WIRE = "{self.NAME}"\n', encoding="utf-8")
        second.write_text(f'WIRE = "{self.NAME}"\n', encoding="utf-8")
        with mock.patch.object(census, "ROOT", root):
            location = census.source_hit_location(self.NAME, [first, second])
        self.assertEqual(location, ("src/pirateforce_foundation/a_wire.py", 151))


class CensusFileTextsTests(unittest.TestCase):
    """``census_file_texts`` -- the ONE place this census spells a path and
    reads a file. Round `8btjto` (pf-adversary D-A/D-H on `#1013`).

    Before this generator existed, ``_build_source_hits`` and
    ``source_hit_location`` each carried their own copy of those five lines
    and nothing compared the copies: three one-line mutants in the second copy
    sent ``--where`` to a DIFFERENT file from the one the artifact names, with
    this whole test file still green. D-H measured the other half -- the
    ``OSError`` skip and ``errors="replace"`` had never been executed by any
    test at all (deleting both kept the suite green). Both run here.

    Unguarded: synthetic tree in a temp directory, no `pf_bridge` sibling, so
    this runs on `gate-windows`."""

    def _root(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_relpath_is_posix_spelled_under_a_windows_style_relative_to(self):
        # Kills `str(path.relative_to(ROOT))`, which is PR #961's backslash
        # bug -- it reappeared verbatim inside `source_hit_location` and no
        # test noticed, because all three #961 regression tests point at
        # `_build_source_hits`. There is now one function to point at.
        real_relative_to = pathlib.Path.relative_to

        def fake_relative_to(self, *args, **kwargs):
            return pathlib.PureWindowsPath(
                str(real_relative_to(self, *args, **kwargs))
            )

        root = self._root()
        pkg = root / "src" / "pirateforce_foundation" / "gm"
        pkg.mkdir(parents=True)
        module = pkg / "command_capture.py"
        module.write_text("X = 1\n", encoding="utf-8")
        with mock.patch.object(census, "ROOT", root), mock.patch.object(
            pathlib.Path, "relative_to", fake_relative_to
        ):
            got = list(census.census_file_texts([module]))
        self.assertEqual(
            got[0][0], "src/pirateforce_foundation/gm/command_capture.py"
        )
        self.assertNotIn("\\", got[0][0])

    def test_an_unreadable_file_is_skipped_instead_of_killing_the_census(self):
        # D-H: `except OSError: continue` had never run.
        root = self._root()
        pkg = root / "src" / "pirateforce_foundation"
        pkg.mkdir(parents=True)
        good = pkg / "b_good.py"
        good.write_text('WIRE = "Channel_ProbeVital"\n', encoding="utf-8")

        class _Unreadable:
            def relative_to(self, _other):
                return pathlib.PurePosixPath("src/pirateforce_foundation/a_bad.py")

            def read_text(self, **_kwargs):
                raise OSError(13, "Permission denied")

        files = [_Unreadable(), good]
        with mock.patch.object(census, "ROOT", root):
            seen = [relpath for relpath, _ in census.census_file_texts(files)]
            hits = census._build_source_hits({"Channel_ProbeVital"}, files)
            location = census.source_hit_location("Channel_ProbeVital", files)
        self.assertEqual(seen, ["src/pirateforce_foundation/b_good.py"])
        # ... and the census still counts every file it CAN read.
        self.assertEqual(hits["Channel_ProbeVital"],
                         "src/pirateforce_foundation/b_good.py")
        self.assertEqual(location[0], "src/pirateforce_foundation/b_good.py")

    def test_an_undecodable_byte_does_not_hide_the_rest_of_the_file(self):
        # D-H: `errors="replace"` had never run either. Without it this raises
        # UnicodeDecodeError and the name on line 2 is never counted.
        root = self._root()
        pkg = root / "src" / "pirateforce_foundation"
        pkg.mkdir(parents=True)
        module = pkg / "runtime.py"
        module.write_bytes(b'BAD = "\xff\xfe"\nWIRE = "Pets_ProbeVital"\n')
        with mock.patch.object(census, "ROOT", root):
            location = census.source_hit_location("Pets_ProbeVital", [module])
        self.assertEqual(location, ("src/pirateforce_foundation/runtime.py", 2))

    def test_the_given_order_is_preserved_not_re_sorted(self):
        # The ordering policy belongs to `sort_py_files`; this generator must
        # not add a second, quieter one.
        root = self._root()
        pkg = root / "src" / "pirateforce_foundation"
        pkg.mkdir(parents=True)
        names = ["z.py", "a.py", "m.py"]
        for name in names:
            (pkg / name).write_text("X = 1\n", encoding="utf-8")
        with mock.patch.object(census, "ROOT", root):
            got = [relpath for relpath, _ in
                   census.census_file_texts([pkg / n for n in names])]
        self.assertEqual([p.rsplit("/", 1)[1] for p in got], names)


class WhereAndCensusCannotDisagreeTests(unittest.TestCase):
    r"""``--where`` and the artifact's `evidence` column must name the SAME
    file -- checked on a tree shaped like the real one. Round `8btjto`,
    pf-adversary D-A/D-B on `#1013`, and D8 of the `#1005` report.

    The two tests round `jx6r5p` wrote for this invariant could not fail: one
    fed a single file and a single name (no order to get wrong, no name to be
    a substring of another), the other fed two files that were already in
    census order. D-B measured the same monoculture across the whole unguarded
    half of this file -- 1-2 files, a one-name set, never a subpackage, and
    always the one vital name `Community_ProbeOnlyVital` -- while the real
    call site passes several hundred files and 327 names, and 7 of the 30
    SOURCE rows live under `gm/`.

    [MEASURED round `cpgueb`, re-derived, one command:
      awk -F'\t' '$5=="SOURCE" && $6 ~ /\/gm\//' \
        reports/PF_UI_WIRE_NAME_CENSUS_20260906.tsv | wc -l
    -> 7 (gmui_catalog.py 4 + command_capture.py 2 + teleport_wire.py 1).
    Round `8btjto` wrote 4 here and at the fixture below, which is the row
    count of the single busiest gm/ FILE, not of the package -- and that
    number was the argument that the fixture resembles the real tree
    (pf-adversary D5 on `#1017`).]

    Every axis that was fixed is varied here:

    * SEVEN files, not one or two;
    * a subpackage (`gm/`) and a sub-subpackage (`gm/deep/`) -- no fixture had
      ever built one, though `gm/command_capture.py` is the file whose drift
      started this line of work;
    * NINE names across six prefixes, not one `Community_` name;
    * two names where one is a strict prefix of the other, spelled in
      different files (breaks a `name in token` substring test);
    * a file whose BASENAME order differs from its posix PATH order
      (`b_wire.py` before `gm/a_wire.py`) (breaks a re-sort on `p.name`);
    * a docstring-only name and a comment-only spelling, so the exclusions are
      live on this fixture rather than dormant.

    Unguarded: temp tree, no sibling, runs on `gate-windows`."""

    NAMES = [
        "Channel_ProbeVital",
        "Channel_ProbeVitalEx",
        "Community_ProbeOnlyVital",
        "Pets_FeedProbeVital",
        "GM_RunProbeVital",
        "Activity_CheatProbeVital",
        "NavigationEx_ProbeVital",
        "ShowProbeMessageVital",
        "Equipment_UnusedProbeVital",
    ]

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        pkg = self.root / "src" / "pirateforce_foundation"
        (pkg / "gm" / "deep").mkdir(parents=True)

        def write(rel, text):
            (pkg / rel).write_text(text, encoding="utf-8")

        # `Channel_ProbeVitalEx` is spelled in the FIRST file in census order
        # and `Channel_ProbeVital` only in a later one, so a substring
        # membership test answers the first file for BOTH -- and disagrees
        # with the artifact on the shorter name.
        write("a_first.py", 'WIRE = "Channel_ProbeVitalEx"\n')
        # `Equipment_UnusedProbeVital` appears only in this module docstring.
        write(
            "b_wire.py",
            '"""Frames: Equipment_UnusedProbeVital 0x0001."""\n'
            + "X = 1\n" * 3
            + 'WIRE = "Pets_FeedProbeVital"\n'
            + 'ALSO = "ShowProbeMessageVital"\n',
        )
        # basename `a_wire.py` sorts BEFORE `b_wire.py`; the posix path
        # `.../gm/a_wire.py` sorts AFTER it. `Pets_FeedProbeVital` is in both.
        write("gm/a_wire.py", 'WIRE = "Pets_FeedProbeVital"\n')
        write(
            "gm/command_capture.py",
            '"""Handles GM_RunProbeVital and Activity_CheatProbeVital."""\n'
            + "\n"
            + "# GM_RunProbeVital is named in a full-line comment too.\n"
            + "X = 1\n" * 20
            + 'WIRE = "GM_RunProbeVital"\n'
            + 'CHEAT = "Activity_CheatProbeVital"\n',
        )
        write("gm/deep/nested.py", 'WIRE = "NavigationEx_ProbeVital"\n')
        write(
            "m_wire.py",
            'WIRE = "Channel_ProbeVital"\nZ = "Community_ProbeOnlyVital"\n',
        )
        write(
            "z_last.py",
            'WIRE = "Channel_ProbeVital"\nY = "NavigationEx_ProbeVital"\n',
        )

        self.files = census._iter_py_files(pkg)
        self.assertEqual(len(self.files), 7)

    def _hits(self):
        with mock.patch.object(census, "ROOT", self.root):
            return census._build_source_hits(set(self.NAMES), self.files)

    def _where(self, name):
        with mock.patch.object(census, "ROOT", self.root):
            return census.source_hit_location(name, self.files)

    def test_every_name_gets_the_same_file_from_both_paths(self):
        # The invariant the artifact's reader depends on, over the whole name
        # set rather than over one name in one file.
        hits = self._hits()
        for name in self.NAMES:
            with self.subTest(name=name):
                location = self._where(name)
                if name in hits:
                    self.assertIsNotNone(location)
                    self.assertEqual(hits[name], location[0])
                else:
                    self.assertIsNone(location)

    def test_a_prefix_name_is_not_answered_by_the_longer_name_containing_it(self):
        # Kills `if any(name in t for t in tokens)`.
        self.assertEqual(
            self._where("Channel_ProbeVital")[0],
            "src/pirateforce_foundation/m_wire.py",
        )
        self.assertEqual(
            self._where("Channel_ProbeVitalEx")[0],
            "src/pirateforce_foundation/a_first.py",
        )

    def test_file_order_is_the_posix_path_not_the_basename(self):
        # Kills a re-sort on `p.name` in either function: by basename,
        # `gm/a_wire.py` would come first.
        self.assertEqual(
            self._where("Pets_FeedProbeVital")[0],
            "src/pirateforce_foundation/b_wire.py",
        )
        self.assertEqual(
            self._hits()["Pets_FeedProbeVital"],
            "src/pirateforce_foundation/b_wire.py",
        )

    def test_first_hit_wins_and_a_later_file_never_overwrites_it(self):
        # D8 of the `#1005` report: the "first hit wins" policy had no pin
        # outside the guarded class, and a "last hit wins" mutant passed the
        # whole file. `Channel_ProbeVital` is in `m_wire.py` and `z_last.py`;
        # `NavigationEx_ProbeVital` is in `gm/deep/nested.py` and `z_last.py`.
        self.assertEqual(
            self._hits()["Channel_ProbeVital"],
            "src/pirateforce_foundation/m_wire.py",
        )
        self.assertEqual(
            self._hits()["NavigationEx_ProbeVital"],
            "src/pirateforce_foundation/gm/deep/nested.py",
        )
        self.assertEqual(
            self._where("NavigationEx_ProbeVital")[0],
            "src/pirateforce_foundation/gm/deep/nested.py",
        )

    def test_a_subpackage_path_keeps_its_separators(self):
        # 7 of the 30 real SOURCE rows live under `gm/` (re-derived round
        # `cpgueb`; the class docstring carries the command), but no fixture had
        # ever built a subpackage, so `relpath.count("/") <= 2` mutants
        # survived the whole file.
        for name, expected in (
            ("GM_RunProbeVital",
             "src/pirateforce_foundation/gm/command_capture.py"),
            ("NavigationEx_ProbeVital",
             "src/pirateforce_foundation/gm/deep/nested.py"),
        ):
            with self.subTest(name=name):
                self.assertEqual(self._where(name)[0], expected)
                self.assertEqual(self._hits()[name], expected)

    def test_the_exclusions_are_live_on_this_fixture_not_dormant(self):
        # If these stop being excluded, the agreement above stops meaning what
        # it says -- the two functions would agree on a prose hit.
        self.assertIsNone(self._where("Equipment_UnusedProbeVital"))
        self.assertNotIn("Equipment_UnusedProbeVital", self._hits())
        # `GM_RunProbeVital` is spelled in the module docstring (line 1) and
        # again in a full-line comment (line 3); the line that counts is the
        # assignment after 20 lines of padding -- 1 docstring + 1 blank + 1
        # comment + 20 padding = line 24.
        self.assertEqual(self._where("GM_RunProbeVital")[1], 24)

class MainWhereFlagTests(unittest.TestCase):
    """``main(["--where", NAME])``'s contract: exit 0 and one `path:line` line
    on stdout, or exit 1 and a named reason on stderr -- and neither path may
    touch the master catalog, so a reader with no `pf_bridge` sibling can run
    it. Unguarded, runs on `gate-windows`."""

    NAME = "Community_ProbeOnlyVital"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.pkg = self.root / "src" / "pirateforce_foundation"
        self.pkg.mkdir(parents=True)
        # build_rows would need the sibling catalog; if --where ever starts
        # calling it, this raises and the test says so.
        patcher = mock.patch.object(
            census, "build_rows", side_effect=AssertionError("--where must not build rows")
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _run(self, name):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(census, "ROOT", self.root), mock.patch.object(
            census, "SRC_DIR", self.pkg
        ), mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = census.main(["--where", name])
        return code, out.getvalue(), err.getvalue()

    def test_a_counted_name_exits_0_and_prints_path_and_line(self):
        (self.pkg / "runtime.py").write_text(
            "X = 1\n" * 40 + f'WIRE = "{self.NAME}"\n', encoding="utf-8"
        )
        code, out, _ = self._run(self.NAME)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "src/pirateforce_foundation/runtime.py:41")

    def test_a_prose_only_name_exits_1_and_says_why(self):
        (self.pkg / "runtime.py").write_text(
            f'"""Handles {self.NAME}."""\n\nX = 1\n', encoding="utf-8"
        )
        code, out, err = self._run(self.NAME)
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("NOT A SOURCE ROW", err)
        self.assertIn(self.NAME, err)

    def test_an_unknown_name_exits_1_rather_than_pretending(self):
        (self.pkg / "runtime.py").write_text("X = 1\n", encoding="utf-8")
        code, _, err = self._run("Community_NoSuchVital")
        self.assertEqual(code, 1)
        self.assertIn("NOT A SOURCE ROW", err)

    def test_stdout_is_exactly_one_line_and_stderr_is_empty(self):
        # pf-adversary D-G on `#1013`: the "one line on stdout" contract was
        # only ever asserted through `out.strip()`, so a mutant printing a
        # leading blank line, or an extra line on stderr, passed the whole
        # file -- while a consumer written the documented way,
        # `LINE=$(... --where X)`, gets a leading newline.
        (self.pkg / "runtime.py").write_text(
            "X = 1\n" * 40 + f'WIRE = "{self.NAME}"\n', encoding="utf-8"
        )
        code, out, err = self._run(self.NAME)
        self.assertEqual(code, 0)
        self.assertEqual(out, "src/pirateforce_foundation/runtime.py:41\n")
        self.assertEqual(err, "")

    def test_an_empty_name_exits_1_and_never_asks_for_the_sibling(self):
        # pf-adversary D-F on `#1013`: `if args.where:` sent `--where ""`
        # through to the full census, which exits 2 with
        # `CENSUS ERROR ... needs a sibling pf_bridge` -- the one thing this
        # mode promises it never needs. `build_rows` is mocked to raise in
        # setUp, so reaching it at all fails loudly here.
        (self.pkg / "runtime.py").write_text("X = 1\n", encoding="utf-8")
        code, out, err = self._run("")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("NOT A SOURCE ROW", err)
        self.assertNotIn("CENSUS ERROR", err)

    def test_the_failure_message_does_not_diagnose_a_cause_it_did_not_measure(self):
        # pf-adversary D-D on `#1013`: for a MISSPELLED name -- the commonest
        # reason a reader sees this message -- the old wording stated as fact
        # that the docstring/comment rule excluded it. No token matched
        # anywhere and no exclusion ever fired, so that sentence was false.
        # The message may offer both possibilities; it may not pick one.
        (self.pkg / "runtime.py").write_text(
            f'WIRE = "{self.NAME}"\n', encoding="utf-8"
        )
        _code, _out, err = self._run("Community_ProbeOnlyVitalTypo")
        self.assertIn("no occurrence that this census counts", err)
        self.assertIn("spelled nowhere", err)
        self.assertIn("or every occurrence is in a docstring", err)
        # The tool cannot know which, and must say so rather than assert one.
        self.assertIn("cannot tell you which", err)


class MainWhereAllFlagTests(unittest.TestCase):
    """``main(["--where-all", NAME])``'s contract, and the half of ``--where``'s
    contract that COO-DECISION `20260907_1141` item (c) added: the extra line
    goes to STDERR so stdout stays exactly one line.

    Unguarded, runs on `gate-windows` -- it reads only a temp tree, never the
    master catalog. ``build_rows`` is mocked to raise for the same reason
    ``MainWhereFlagTests`` mocks it: a reader with no `pf_bridge` sibling is
    exactly who runs these modes."""

    NAME = "Community_ProbeOnlyVital"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.pkg = self.root / "src" / "pirateforce_foundation"
        (self.pkg / "gm").mkdir(parents=True)
        patcher = mock.patch.object(
            census,
            "build_rows",
            side_effect=AssertionError("--where-all must not build rows"),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(census, "ROOT", self.root), mock.patch.object(
            census, "SRC_DIR", self.pkg
        ), mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = census.main(argv)
        return code, out.getvalue(), err.getvalue()

    def _three_files(self):
        # Census file order is byte order on the posix relpath, so:
        #   gm/a_wire.py < gm/b_wire.py < z_wire.py
        # The name sits at a DIFFERENT line in each file, so a mutant that
        # reported one file's line for another is visible.
        (self.pkg / "gm" / "a_wire.py").write_text(
            "X = 1\n" * 4 + f'WIRE = "{self.NAME}"\n', encoding="utf-8"
        )
        (self.pkg / "gm" / "b_wire.py").write_text(
            "X = 1\n" * 9 + f'WIRE = "{self.NAME}"\n', encoding="utf-8"
        )
        (self.pkg / "z_wire.py").write_text(
            "X = 1\n" * 14 + f'WIRE = "{self.NAME}"\n', encoding="utf-8"
        )

    def test_every_counted_file_is_printed_in_census_order(self):
        self._three_files()
        code, out, err = self._run(["--where-all", self.NAME])
        self.assertEqual(code, 0)
        self.assertEqual(
            out,
            "src/pirateforce_foundation/gm/a_wire.py:5\n"
            "src/pirateforce_foundation/gm/b_wire.py:10\n"
            "src/pirateforce_foundation/z_wire.py:15\n",
        )
        self.assertEqual(err, "")

    def test_the_first_line_is_exactly_what_where_prints(self):
        # The whole point of the shared generator: --where is --where-all's
        # first line, not a second implementation of "which file first".
        self._three_files()
        _c, all_out, _e = self._run(["--where-all", self.NAME])
        _c, one_out, _e = self._run(["--where", self.NAME])
        self.assertEqual(one_out, all_out.splitlines(True)[0])

    def test_where_keeps_one_stdout_line_and_counts_the_rest_on_stderr(self):
        self._three_files()
        code, out, err = self._run(["--where", self.NAME])
        self.assertEqual(code, 0)
        self.assertEqual(out, "src/pirateforce_foundation/gm/a_wire.py:5\n")
        self.assertEqual(err, f"+2 more files, use --where-all {self.NAME}\n")

    def test_a_single_file_name_still_gets_a_silent_stderr(self):
        # The stderr line must be a fact about THIS name, not decoration:
        # a mutant printing it unconditionally says "+0 more files".
        (self.pkg / "z_wire.py").write_text(
            f'WIRE = "{self.NAME}"\n', encoding="utf-8"
        )
        code, out, err = self._run(["--where", self.NAME])
        self.assertEqual(code, 0)
        self.assertEqual(out, "src/pirateforce_foundation/z_wire.py:1\n")
        self.assertEqual(err, "")

    def test_only_the_first_hit_inside_one_file_is_reported(self):
        # One line per FILE. The artifact's evidence is a file, and this mode
        # exists to name the files the artifact cannot.
        (self.pkg / "z_wire.py").write_text(
            f'A = "{self.NAME}"\nB = "{self.NAME}"\nC = "{self.NAME}"\n',
            encoding="utf-8",
        )
        _code, out, _err = self._run(["--where-all", self.NAME])
        self.assertEqual(out, "src/pirateforce_foundation/z_wire.py:1\n")

    def test_prose_only_files_are_left_out_of_the_list(self):
        # --where-all inherits the census's two exclusions; it does not become
        # a grep just because it prints more than one line.
        (self.pkg / "gm" / "a_wire.py").write_text(
            f'"""Handles {self.NAME}."""\nX = 1\n', encoding="utf-8"
        )
        (self.pkg / "gm" / "b_wire.py").write_text(
            f"# {self.NAME} is handled elsewhere\nX = 1\n", encoding="utf-8"
        )
        (self.pkg / "z_wire.py").write_text(
            f'WIRE = "{self.NAME}"\n', encoding="utf-8"
        )
        _code, out, _err = self._run(["--where-all", self.NAME])
        self.assertEqual(out, "src/pirateforce_foundation/z_wire.py:1\n")

    def test_no_counted_hit_exits_1_with_the_same_named_reason(self):
        (self.pkg / "z_wire.py").write_text("X = 1\n", encoding="utf-8")
        code, out, err = self._run(["--where-all", self.NAME])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("NOT A SOURCE ROW", err)
        self.assertIn(self.NAME, err)

    def test_both_flags_at_once_is_refused_rather_than_guessed(self):
        self._three_files()
        code, out, err = self._run(["--where", self.NAME, "--where-all", self.NAME])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("pass one", err)


class MultiFileCountIsRederivedTests(unittest.TestCase):
    """The `11` in ``_iter_py_files``'s docstring is re-derived here, not quoted.

    Round `8btjto` shipped `46` in that docstring with the words "the 46
    re-derives"; it was wrong under every definition this file has, and
    LANE-UI's ASK-COO of `1101` priced its whole question on it
    (pf-adversary D6 on `#1017`). A number a docstring asserts and nothing
    re-runs is how that happened, so it is re-run here.

    GUARDED, and this is a real cost: it walks the 327-name master catalog,
    which lives in the `pf_bridge` sibling, so `gate-windows` -- the only CI
    that runs pytest -- never executes it. What the gate DOES cover is the
    mechanism underneath: ``MainWhereAllFlagTests`` and
    ``WhereAndCensusCannotDisagreeTests`` pin the walk, the ordering and the
    one-line-per-file rule over temp trees with no sibling. What the gate
    cannot cover is the VALUE 11, because the value is a property of the real
    tree plus the real catalog."""

    def test_the_docstring_number_matches_a_fresh_rederive(self):
        UI_WIRE_CENSUS_INPUTS.require(self)
        files = census._iter_py_files(census.SRC_DIR)
        names = [name for _wid, name in census.load_names()]
        multi_names = census.multi_file_counted_names(names, files)
        self.assertEqual(
            len(multi_names),
            11,
            "the count of catalog names counted in more than one file moved; "
            "update BOTH this number and the two docstrings that state it "
            "(_iter_py_files and the --where-all usage block)",
        )
        doc = census._iter_py_files.__doc__
        self.assertIn(
            f"{len(multi_names)} of the catalog names are COUNTED in more "
            "than one file",
            doc,
        )
        # The number this replaced. It may still be NAMED in the paragraph
        # that explains the correction, but never again as a count.
        self.assertNotIn("46 of the", doc)

    def test_the_one_pass_count_agrees_with_two_other_derivations(self):
        # Two independent cross-checks, because pf-adversary D10 on `#1017`
        # faulted round `8btjto`'s "one-pass equivalent" test for being
        # f(x) == f(x) -- it called the same function twice with the same
        # arguments and a mutant that dropped a name passed.
        #
        # (1) a derivation written HERE out of the two primitives
        #     (`census_file_texts` + `code_token_lines`), which shares no
        #     bookkeeping with `multi_file_counted_names` -- one pass, so it
        #     costs about a second;
        # (2) the per-name walk that actually backs `--where-all`, run on the
        #     flagged names only, so a name flagged multi-file that `--where`
        #     would report a single file for is caught. Running (2) over all
        #     327 is minutes, which is why (1) carries the completeness half.
        UI_WIRE_CENSUS_INPUTS.require(self)
        files = census._iter_py_files(census.SRC_DIR)
        names = [name for _wid, name in census.load_names()]
        one_pass = census.multi_file_counted_names(names, files)

        wanted = set(names)
        files_per_name = {}
        for relpath, text in census.census_file_texts(files):
            here = set()
            for _lineno, tokens in census.code_token_lines(text):
                here.update(tok for tok in tokens if tok in wanted)
            for name in here:
                files_per_name.setdefault(name, set()).add(relpath)
        expected = [n for n in names if len(files_per_name.get(n, ())) > 1]
        self.assertEqual(one_pass, expected)

        for name in one_pass:
            self.assertGreater(
                len(census.source_hit_locations(name, files)),
                1,
                f"{name}: the one-pass count says multi-file, the per-name "
                "walk behind --where-all does not",
            )


class ArtifactPassedAsCatalogIsRefused(unittest.TestCase):
    """`--tsv <the artifact>` must name the mistake, not print CENSUS DRIFT.

    THE FAILURE THIS PINS, MEASURED (round `8y18nc`, 2026-09-07).  Before the
    guard in ``load_names``, running

        python3 tools/pf_ui_wire_name_census.py \
            --tsv reports/PF_UI_WIRE_NAME_CENSUS_20260906.tsv

    read this tool's OWN emitted artifact as if it were the master catalog
    -- the artifact's first line is ``id<TAB>name<TAB>family...`` and every
    line under it also carries a hex id and a Vital name, so the parser
    accepted all of it -- derived a 328-row census off that, compared it
    against the committed artifact and printed ``CENSUS DRIFT ... does not
    match a fresh re-derive``.

    That output is a false alarm about the artifact, and it was read as a
    true one twice: LANE-GM reported the artifact stale on main
    (``pf_bridge/notes_to_chief/20260907_1929_LANE-GM-TO-COO-ui-wire-name-
    census-artifact-is-stale-on-main.md``) and COO re-ran the same command,
    got the same line, and ordered LANE-UI to re-emit
    (``20260907_2050_COO-DECISION-gm1929-...``).  The artifact was never
    stale: ``--emit`` with the real defaults on the same commit rewrites it
    byte-for-byte (``git diff`` empty), which the sibling test below is what
    already covers.

    So this is not a usability nicety.  A measuring tool that answers a
    question nobody asked, in the words of the question they did ask, spends
    other lanes' rounds; two are already spent.  It refuses instead.
    """

    def test_artifact_as_tsv_raises_census_error_naming_both_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "PF_UI_WIRE_NAME_CENSUS_FAKE.tsv"
            artifact.write_text(
                "id\tname\tfamily\tis_client_req\ttier\tevidence\n"
                "0x0AEA\tWinemaking_UpdateLearnedFormulaVital\t"
                "Winemaking_\t0\tNAME-ONLY\t-\n",
                encoding="utf-8",
            )
            with self.assertRaises(census.CensusError) as caught:
                census.load_names(artifact)
        message = str(caught.exception)
        # Both flag names, because the reader who hit this typed one of them
        # meaning the other; a message that says only "wrong file" leaves
        # them to guess which way round it goes.
        self.assertIn("--tsv", message)
        self.assertIn("--artifact", message)

    def test_main_exits_2_and_prints_no_drift_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "PF_UI_WIRE_NAME_CENSUS_FAKE.tsv"
            artifact.write_text(
                "id\tname\tfamily\tis_client_req\ttier\tevidence\n"
                "0x0AEA\tWinemaking_UpdateLearnedFormulaVital\t"
                "Winemaking_\t0\tNAME-ONLY\t-\n",
                encoding="utf-8",
            )
            err = io.StringIO()
            with mock.patch.object(sys, "stderr", err):
                code = census.main(["--tsv", str(artifact)])
        self.assertEqual(code, 2)
        # The exact string two lanes acted on. It must not appear for a
        # wrong INPUT file -- that is the whole regression.
        self.assertNotIn("CENSUS DRIFT", err.getvalue())
        self.assertIn("CENSUS ERROR", err.getvalue())

    def test_the_real_catalog_still_loads(self):
        """The guard must not fire on the file it is guarding for."""
        UI_WIRE_CENSUS_INPUTS.require(self)
        rows = census.load_names()
        self.assertGreater(len(rows), 300)

    def test_a_catalog_whose_header_comment_is_gone_is_not_accused(self):
        """The round `8y18nc` guard was too wide, measured (D3/D5).

        That guard refused any catalog whose first PARSED row was the pair
        ("id", "name"), and its comment claimed the real catalog could never
        present one because "its two leading lines are `#` comments".  The
        catalog has FOUR `#` lines and the fourth of them IS `# id<TAB>name`,
        so removing two comment characters -- an edit no rule forbids --
        made the tool accuse the real catalog and refuse to run at all.
        The header this tool emits has SIX columns; that is what is checked
        now, and a two-column id/name header is not it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            catalog = Path(tmp) / "catalog.tsv"
            catalog.write_text(
                "# a comment\n"
                "id\tname\n"
                "0x0AEA\tWinemaking_UpdateLearnedFormulaVital\n",
                encoding="utf-8",
            )
            rows = census.load_names(catalog)
        self.assertIn(
            ("0x0AEA", "Winemaking_UpdateLearnedFormulaVital"), rows,
        )

    def test_first_uncommented_line_skips_comments_and_blanks(self):
        self.assertEqual(
            census.first_uncommented_line("# one\n\n# two\nreal\nlater"),
            "real",
        )
        self.assertEqual(census.first_uncommented_line("# only\n"), "")


class EmitRefusesToOverwriteWhatIsNotItsArtifact(unittest.TestCase):
    """`--emit --artifact <catalog>` destroyed the catalog and said PASS.

    Measured (pf-adversary D2 of round `8y18nc`, re-measured this round on a
    copy): md5 173f662e -> 9f211939, exit 0, the 327-name master catalog
    replaced by a 328-line census.  The guard added in round `8y18nc` closed
    the door a lane walks through by mistake in ONE direction (`--tsv
    <artifact>`) and its own error message pointed at this one.
    """

    def _catalog(self, tmp: str) -> Path:
        catalog = Path(tmp) / "VITAL_REGISTRY.tsv"
        catalog.write_text(
            "# master catalog\n"
            "# id\tname\n"
            "0x0AEA\tWinemaking_UpdateLearnedFormulaVital\n",
            encoding="utf-8",
        )
        return catalog

    def test_emit_over_a_catalog_writes_nothing_and_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = self._catalog(tmp)
            before = catalog.read_bytes()
            err = io.StringIO()
            with mock.patch.object(sys, "stderr", err):
                code = census.main([
                    "--emit", "--tsv", str(catalog),
                    "--artifact", str(catalog),
                ])
            after = catalog.read_bytes()
        self.assertEqual(code, 2)
        self.assertEqual(before, after)
        self.assertIn("refusing to write", err.getvalue())

    def test_a_first_emit_into_a_path_that_does_not_exist_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = self._catalog(tmp)
            artifact = Path(tmp) / "fresh_artifact.tsv"
            out = io.StringIO()
            with mock.patch.object(sys, "stdout", out):
                code = census.main([
                    "--emit", "--tsv", str(catalog),
                    "--artifact", str(artifact),
                ])
            self.assertTrue(artifact.exists())
            first = census.first_uncommented_line(
                artifact.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(first, census.ARTIFACT_HEADER)

    def test_emit_says_whether_rows_moved_before_the_trivial_compare(self):
        """D4: the compare after a write is equal by construction."""
        with tempfile.TemporaryDirectory() as tmp:
            catalog = self._catalog(tmp)
            artifact = Path(tmp) / "artifact.tsv"
            out = io.StringIO()
            with mock.patch.object(sys, "stdout", out):
                census.main([
                    "--emit", "--tsv", str(catalog),
                    "--artifact", str(artifact),
                ])
                first_run = out.getvalue()
                census.main([
                    "--emit", "--tsv", str(catalog),
                    "--artifact", str(artifact),
                ])
                second_run = out.getvalue()[len(first_run):]
        self.assertNotIn("CENSUS EMIT", first_run)  # nothing existed yet
        self.assertIn("CENSUS EMIT: no change", second_run)


class EveryFlagExplainsItself(unittest.TestCase):
    """D6: neither flag had a `help=`, and two lanes swapped them."""

    def test_help_names_input_and_output_for_the_two_path_flags(self):
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            with self.assertRaises(SystemExit):
                census.main(["--help"])
        text = out.getvalue()
        self.assertIn("--tsv", text)
        self.assertIn("--artifact", text)
        self.assertIn("INPUT", text)
        self.assertIn("OUTPUT", text)
        self.assertIn("OVERWRITTEN", text)


if __name__ == "__main__":
    unittest.main()
