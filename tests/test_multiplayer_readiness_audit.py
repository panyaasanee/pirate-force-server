"""Pin MULTIPLAYER-READINESS-AUDIT-001's numbers to the tree they were counted from.

The audit report exists to give the project owner numbers instead of opinions,
so its numbers must not be hand-typed.  These tests take the ``AUDIT_COUNTS``
fenced block out of

``reports/PF_MULTIPLAYER_READINESS_AUDIT001_SINGLE_PLAYER_ASSUMPTIONS_20260818.md``

and compare it to a live run of ``tools/pf_multiplayer_readiness_audit.py``.
If a site moves file, disappears, or is duplicated, the verifier itself exits
nonzero and the first test fails.  If a site survives but a count in the report
disagrees with the tree, the comparison tests fail.

Two comparison rules, on purpose:

  * EXACT for everything the audit reasons from -- site counts, the
    immutable/mutable split, the frame anchor split, the per-package file and
    site counts, and the pinned impact sets (which are explicit, named test
    files, so a concurrent lane adding new test files never moves them).
  * ``>=`` for the whole-suite totals and the two import-closure totals, which
    are "how big is the suite today" measurements.  The report records the
    HEAD 5cc0eda value; the suite may grow under a concurrent lane, and it may
    not shrink silently.

Re-pinning when a number legitimately moves: run
``py -3 tools/pf_multiplayer_readiness_audit.py --json`` and update the
``AUDIT_COUNTS`` block in the report in the same change.

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
        for key in (
            "checkpoint_calls_at_try_depth_zero",
            "game_listener_try_blocks_without_except",
            "login_req_capture_guard",
        ):
            with self.subTest(key=key):
                self.assertEqual(self.report[key], self.tool[key])


class SuiteSizeTests(unittest.TestCase):
    """Suite-size measurements: may grow under a concurrent lane, may not shrink."""

    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool().build()
        cls.report = report_counts()

    def test_the_suite_has_not_shrunk_since_the_audit_was_counted(self):
        pairs = (
            ("tests_total_files_at_head", self.tool["tests_total_files"]),
            ("tests_total_functions_at_head", self.tool["tests_total_functions"]),
            ("package_a_closure_test_files_at_head", self.tool["impact_a_closure"]["files"]),
            ("package_a_closure_test_functions_at_head",
             self.tool["impact_a_closure"]["functions"]),
            ("package_b_closure_test_files_at_head", self.tool["impact_b_closure"]["files"]),
            ("package_b_closure_test_functions_at_head",
             self.tool["impact_b_closure"]["functions"]),
        )
        for key, live in pairs:
            with self.subTest(key=key):
                self.assertGreaterEqual(live, self.report[key])

    def test_the_closures_are_a_strict_subset_of_the_suite(self):
        total = self.tool["tests_total_files"]
        for key in ("impact_a_closure", "impact_b_closure"):
            with self.subTest(key=key):
                self.assertLessEqual(self.tool[key]["files"], total)
                self.assertGreater(self.tool[key]["files"], 0)

    def test_package_a_touches_more_of_the_suite_than_package_b(self):
        """The audit's central cost comparison, re-derived rather than asserted."""
        self.assertGreater(
            self.tool["impact_a_closure"]["functions"],
            self.tool["impact_b_closure"]["functions"],
        )
        self.assertGreater(
            self.tool["impact_a_pinned"]["functions"],
            self.tool["impact_b_pinned"]["functions"],
        )


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
