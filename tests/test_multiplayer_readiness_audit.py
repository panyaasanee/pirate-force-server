"""Pin MULTIPLAYER-READINESS-AUDIT-001's numbers to the tree they were counted from.

The audit report exists to give the project owner numbers instead of opinions,
so its numbers must not be hand-typed.  These tests take the ``AUDIT_COUNTS``
fenced block out of

``reports/PF_MULTIPLAYER_READINESS_AUDIT001_SINGLE_PLAYER_ASSUMPTIONS_20260818.md``

and compare it to a live run of ``tools/pf_multiplayer_readiness_audit.py``.
If a site moves file, disappears, or is duplicated, the verifier itself exits
nonzero and the first test fails.  If a site survives but a count in the report
disagrees with the tree, the comparison tests fail.

One comparison rule since round 84: **exact, for every number in the block.**

That used to be two rules.  The whole-suite totals and the two import-closure
totals were compared with ``>=`` ("a suite may grow under a concurrent lane; it
may not shrink silently"), and that is how ``tests_total_files_at_head: 61``
sat in a published report while the tree grew to 77 - the comparison was green
the entire time because 77 >= 61.  A ``>=`` guard over a number that only ever
goes up is not a guard.

Those six numbers are *historical*: they describe commit ``5cc0eda``, not the
tree in front of you.  The tool now pins them as constants next to that commit
and re-derives them from it with ``git ls-tree``/``git cat-file`` on every run,
so the pin is falsifiable; these tests compare the report to the pin exactly.
The live suite size is still measured, under ``tests_total_files_today`` /
``tests_total_functions_today``, and is deliberately NOT in the report block.

Re-pinning when a number legitimately moves: run
``py -3 tools/pf_multiplayer_readiness_audit.py --json`` and update the
``AUDIT_COUNTS`` block in the report in the same change.  The ``*_at_head``
numbers are NOT in that category - they describe a commit that cannot change,
so if one of them is wrong the report needs an erratum, not a re-pin.

These tests import nothing from ``src/``, open no socket and touch no database.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from pf_preconditions import AUDIT_HEAD_HISTORY, LOGIN_REQ_CAPTURE  # noqa: E402
TOOL = ROOT / "tools" / "pf_multiplayer_readiness_audit.py"
REPORT = (
    ROOT / "reports"
    / "PF_MULTIPLAYER_READINESS_AUDIT001_SINGLE_PLAYER_ASSUMPTIONS_20260818.md"
)
MANIFEST = REPORT.with_suffix(".manifest")

AUDIT_COUNTS_BLOCK = re.compile(r"```json AUDIT_COUNTS\n(?P<body>.*?)\n```", re.S)


def load_tool():
    spec = importlib.util.spec_from_file_location("pf_mp_readiness_audit", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def report_counts() -> dict:
    match = AUDIT_COUNTS_BLOCK.search(REPORT.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError("the report has no ```json AUDIT_COUNTS block")
    return json.loads(match.group("body"))


class ArtifactsExistTests(unittest.TestCase):
    """The three files of this milestone must ship together."""

    def test_report_tool_and_manifest_all_exist(self):
        for path in (REPORT, MANIFEST, TOOL):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), path)

    def test_the_report_carries_a_machine_readable_counts_block(self):
        counts = report_counts()
        self.assertIsInstance(counts, dict)
        self.assertEqual(counts["measured_at_head"], "5cc0eda")


class VerifierRunsCleanTests(unittest.TestCase):
    """The scan itself is the primary guard; everything else compares to it."""

    def test_the_verifier_exits_zero_as_a_subprocess(self):
        # The tool re-derives a suite size from commit 5cc0eda and fails the
        # historical pin when git cannot hand it over, which is the right
        # answer for the tool and the wrong one for a test that never got to
        # run.  Measured 2026-08-21 on a depth-1 clone.
        AUDIT_HEAD_HISTORY.require(self)
        completed = subprocess.run(
            [sys.executable, str(TOOL)],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        self.assertEqual(
            completed.returncode, 0,
            f"verifier drifted:\n{completed.stdout}\n{completed.stderr}",
        )
        self.assertIn("all multiplayer-readiness audit guards reproduced", completed.stdout)

    def test_the_json_mode_is_valid_json_and_hides_private_keys(self):
        # Same reason as above: --json exits non-zero without the commit.
        AUDIT_HEAD_HISTORY.require(self)
        completed = subprocess.run(
            [sys.executable, str(TOOL), "--json"],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertFalse([key for key in payload if key.startswith("_")])

    def test_two_runs_produce_identical_output(self):
        """Deterministic, as the task requires: no timestamps, no ordering drift."""
        runs = [
            subprocess.run(
                [sys.executable, str(TOOL), "--json"],
                cwd=str(ROOT), capture_output=True, text=True,
            ).stdout
            for _ in range(2)
        ]
        self.assertEqual(runs[0], runs[1])


class ExactCountTests(unittest.TestCase):
    """Every number the audit reasons from, compared exactly."""

    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool().build()
        cls.report = report_counts()

    def test_assumption_site_total_and_layer_split_match(self):
        self.assertEqual(
            self.report["assumption_sites_total"], self.tool["assumption_sites_total"],
        )
        self.assertEqual(
            self.report["assumption_sites_by_layer"],
            self.tool["assumption_sites_by_layer"],
        )
        self.assertEqual(
            sum(self.report["assumption_sites_by_layer"].values()),
            self.report["assumption_sites_total"],
        )

    def test_the_immutable_split_matches_and_still_adds_up(self):
        """18 of 40 sitting in frozen v141 is the load-bearing architectural fact."""
        self.assertEqual(
            self.report["assumption_sites_immutable"],
            self.tool["assumption_sites_immutable"],
        )
        self.assertEqual(
            self.report["assumption_sites_mutable"],
            self.tool["assumption_sites_mutable"],
        )
        self.assertEqual(
            self.report["assumption_sites_immutable"]
            + self.report["assumption_sites_mutable"],
            self.report["assumption_sites_total"],
        )

    def test_every_immutable_site_really_lives_in_the_frozen_module(self):
        frozen = "current/pf_login_game_server_v141.py"
        counted = self.tool["assumption_sites_per_path"].get(frozen, 0)
        self.assertEqual(counted, self.tool["assumption_sites_immutable"])

    def test_ready_site_total_matches(self):
        self.assertEqual(
            self.report["ready_sites_total"], self.tool["ready_sites_total"],
        )

    def test_frame_anchor_split_matches_and_adds_up(self):
        for key in ("frames_total", "frames_anchored", "frames_partial", "frames_guess"):
            with self.subTest(key=key):
                self.assertEqual(self.report[key], self.tool[key])
        self.assertEqual(
            self.report["frames_anchored"]
            + self.report["frames_partial"]
            + self.report["frames_guess"],
            self.report["frames_total"],
        )

    def test_package_file_and_site_counts_match(self):
        for key in (
            "package_a_files_touched", "package_a_files_new", "package_a_sites_covered",
            "package_b_files_touched", "package_b_files_new", "package_b_sites_covered",
        ):
            with self.subTest(key=key):
                self.assertEqual(self.report[key], self.tool[key])

    def test_pinned_impact_sets_match(self):
        self.assertEqual(
            self.report["package_a_pinned_test_files"],
            self.tool["impact_a_pinned"]["files"],
        )
        self.assertEqual(
            self.report["package_a_pinned_test_functions"],
            self.tool["impact_a_pinned"]["functions"],
        )
        self.assertEqual(
            self.report["package_b_pinned_test_files"],
            self.tool["impact_b_pinned"]["files"],
        )
        self.assertEqual(
            self.report["package_b_pinned_test_functions"],
            self.tool["impact_b_pinned"]["functions"],
        )

    def test_pinned_impact_functions_equal_the_sum_of_their_named_files(self):
        for key in ("impact_a_pinned", "impact_b_pinned"):
            with self.subTest(key=key):
                block = self.tool[key]
                self.assertEqual(sum(block["per_file"].values()), block["functions"])
                self.assertEqual(len(block["per_file"]), block["files"])

    def test_interlock_facts_match(self):
        """The two facts the tool re-derives from tracked source alone.

        ``login_req_capture_guard`` used to be a third key here.  It is not a
        fact about tracked source: it is a fact about an untracked capture, so
        on a fresh clone the tool honestly answered "skipped (untracked capture
        absent)" while the pinned report still said "reproduced", and Actions
        run #3 went red on the difference.  It now has two tests of its own
        below, one for each machine, and NEITHER of them is weaker than this
        line was.
        """
        for key in (
            "checkpoint_calls_at_try_depth_zero",
            "game_listener_try_blocks_without_except",
        ):
            with self.subTest(key=key):
                self.assertEqual(self.report[key], self.tool[key])

    @LOGIN_REQ_CAPTURE.skip_unless_present()
    def test_the_login_capture_guard_reproduces_where_the_capture_exists(self):
        """On the bridge: exactly the assertion that used to live above."""
        self.assertEqual(
            self.report["login_req_capture_guard"],
            self.tool["login_req_capture_guard"],
        )
        self.assertEqual(self.tool["login_req_capture_guard"], "reproduced")

    def test_the_login_capture_guard_states_which_machine_it_is_on(self):
        """Runs everywhere, and is an assertion on both machines.

        Where the capture exists the tool must say ``reproduced`` - anything
        else (``drifted``, ``missing id``, ``unreadable``) is a real failure
        and is caught here as well as above.  Where it does not exist the tool
        must say exactly ``skipped (untracked capture absent)`` and nothing
        else, and the report's pin must still read ``reproduced``, because the
        pin records what the bridge measured, not what this machine can see.
        """
        answer = self.tool["login_req_capture_guard"]
        if LOGIN_REQ_CAPTURE.present:
            self.assertEqual(answer, "reproduced")
        else:
            self.assertEqual(answer, "skipped (untracked capture absent)")
            self.assertEqual(self.report["login_req_capture_guard"], "reproduced")


class HistoricalSuiteSizeTests(unittest.TestCase):
    """The six historical numbers, compared exactly and re-derived from the commit."""

    @classmethod
    def setUpClass(cls):
        cls.module = load_tool()
        cls.tool = cls.module.build()
        cls.report = report_counts()

    def test_the_report_and_the_pin_agree_exactly(self):
        for key in sorted(self.module.AT_HEAD):
            with self.subTest(key=key):
                self.assertEqual(self.report[key], self.tool[key])

    def test_the_pin_is_re_derived_from_the_commit_it_names(self):
        # The whole point: this is what makes "61 test files" falsifiable.
        # It is also the one test here that cannot even be attempted without
        # the commit itself, so it says so rather than failing.
        AUDIT_HEAD_HISTORY.require(self)
        self.assertEqual(self.tool["historical_pin"],
                         "reproduced from " + self.module.HEAD_COMMIT)
        self.assertEqual(self.report["measured_at_head"],
                         self.module.HEAD_COMMIT)
        self.assertEqual(self.module._counts_at_head(self.module.HEAD_COMMIT),
                         dict(self.module.AT_HEAD))

    def test_the_live_suite_size_is_reported_but_not_published(self):
        # It is measured (a shrinking suite is still worth seeing) and it is
        # deliberately absent from the report's machine-readable block.
        self.assertGreater(self.tool["tests_total_files_today"], 0)
        self.assertNotIn("tests_total_files_today", self.report)
        self.assertNotIn("tests_total_functions_today", self.report)

    def test_the_closures_are_a_strict_subset_of_the_suite(self):
        total = self.tool["tests_total_files_today"]
        for key in ("impact_a_closure", "impact_b_closure"):
            with self.subTest(key=key):
                self.assertLessEqual(self.tool[key]["files"], total)
                self.assertGreater(self.tool[key]["files"], 0)

    def test_package_a_touches_more_of_the_suite_than_package_b(self):
        """The audit's central cost comparison, re-derived rather than asserted.

        The DURABLE form of the claim is the PINNED one: over the audit's own
        pinned test sets, package A (transport/session) touches more test
        functions than package B (world/visibility).  That is the finding the
        1 -> 2 -> 3 sequencing rested on and it does not move -- it is asserted
        strictly below and re-derived from the audit's HEAD commit by
        ``test_the_pin_is_re_derived_from_the_commit_it_names``.

        The LIVE closure is a different measurement and it is ALLOWED to move
        as we write code, exactly like ``tests_total_files_today``.  Round 96
        (HYP-PF-025, multiplayer chunk 2) added the package-B visibility lane
        and its tests -- ``test_remote_player_hypothesis.py`` reaches
        ``population.load_port_royal_placements`` and so joins package B's
        blast radius, which is correct: it WOULD re-run if that module changed.
        So the live package-B closure has caught up to and passed package A.
        That is what DOING package-B work looks like, not a regression, so the
        live ordering is measured and checked for sanity (both closures real
        and positive) but no longer pinned to a direction.  Pinning a live
        ordering that our own roadmap is designed to invert would be a guard
        that fails on success.
        """
        # The durable, load-bearing claim -- unchanged.
        self.assertGreater(
            self.tool["impact_a_pinned"]["functions"],
            self.tool["impact_b_pinned"]["functions"],
        )
        # The live closures are both real; their ordering is no longer pinned
        # now that package-B development (chunk 2) has begun.
        self.assertGreater(self.tool["impact_a_closure"]["functions"], 0)
        self.assertGreater(self.tool["impact_b_closure"]["functions"], 0)


class GuardWouldNoticeTests(unittest.TestCase):
    """A guard that cannot fail is not a guard."""

    def test_a_missing_site_makes_the_scan_fail(self):
        module = load_tool()
        original = module.ASSUMPTION_SITES
        module._failures.clear()
        try:
            module.ASSUMPTION_SITES = original + (
                ("ZZ9", "transport", module.V141,
                 r"this_marker_does_not_exist_anywhere", 1, "synthetic"),
            )
            module.build()
            self.assertTrue(module._failures)
        finally:
            module.ASSUMPTION_SITES = original
            module._failures.clear()

    def test_a_wrong_occurrence_count_makes_the_scan_fail(self):
        module = load_tool()
        original = module.ASSUMPTION_SITES
        module._failures.clear()
        try:
            module.ASSUMPTION_SITES = original + (
                ("ZZ8", "transport", module.V141, r"s\.listen\(4\)", 99, "synthetic"),
            )
            module.build()
            self.assertTrue(module._failures)
        finally:
            module.ASSUMPTION_SITES = original
            module._failures.clear()

    def test_a_stale_historical_pin_makes_the_scan_fail(self):
        """The defect SCAN-DEBT-001 closed: a rotted number that stayed green."""
        module = load_tool()
        original = dict(module.AT_HEAD)
        module._failures.clear()
        try:
            module.AT_HEAD["tests_total_files_at_head"] = original[
                "tests_total_files_at_head"] + 1
            module.build()
            self.assertTrue(
                [f for f in module._failures if "historical pin" in f],
                module._failures)
        finally:
            module.AT_HEAD.clear()
            module.AT_HEAD.update(original)
            module._failures.clear()

    def test_an_unreachable_history_makes_the_scan_fail_rather_than_skip(self):
        """A historical claim in a checkout that cannot see its history is red."""
        module = load_tool()
        original = module.HEAD_COMMIT
        module._failures.clear()
        try:
            module.HEAD_COMMIT = "0000000000000000000000000000000000000000"
            with self.assertRaises(module.HistoryUnavailable):
                module._counts_at_head(module.HEAD_COMMIT)
            module.build()
            self.assertTrue(
                [f for f in module._failures if "historical pin" in f],
                module._failures)
        finally:
            module.HEAD_COMMIT = original
            module._failures.clear()

    def test_a_missing_frame_evidence_path_makes_the_scan_fail(self):
        module = load_tool()
        original = module.FRAMES
        module._failures.clear()
        try:
            module.FRAMES = original + (
                ("ZZ7", "synthetic", "-", module.GUESS,
                 "reports/THIS_REPORT_DOES_NOT_EXIST.md", "synthetic"),
            )
            module.build()
            self.assertTrue(module._failures)
        finally:
            module.FRAMES = original
            module._failures.clear()


class ReportShapeTests(unittest.TestCase):
    """The report must keep the properties the audit brief demanded."""

    @classmethod
    def setUpClass(cls):
        cls.text = REPORT.read_text(encoding="utf-8")
        cls.tool = load_tool()

    def test_every_assumption_and_ready_site_id_is_cited_in_the_report(self):
        ids = [row[0] for row in self.tool.ASSUMPTION_SITES]
        ids += [row[0] for row in self.tool.READY_SITES]
        ids += [row[0] for row in self.tool.FRAMES]
        missing = [site for site in ids if site not in self.text]
        self.assertEqual(missing, [], f"report does not cite: {missing}")

    def test_the_report_states_the_head_its_line_numbers_come_from(self):
        self.assertIn("5cc0eda", self.text)

    def test_the_report_keeps_an_explicit_nonclaims_section(self):
        self.assertIn("Nonclaims", self.text)

    def test_the_report_records_what_it_could_not_answer(self):
        self.assertIn("could not answer", self.text)


if __name__ == "__main__":
    unittest.main()
