"""The skip census is itself a gate check, so it gets the same treatment.

Actions run #3 (2026-08-20) went red on four tests that reached for evidence a
fresh clone cannot have.  The repair was a declared skip; the danger a declared
skip introduces is that a real test drifts into the skip pile and the suite
still prints a number that looks healthy.  ``tools/pf_pytest_precondition_
census.py`` exists to make that impossible, and a rule nobody has watched
reject something is not a rule - so most of this file is the census refusing
things.

Every test here is pure standard library and reads no artifact from outside the
repository: the census is driven with an explicit artifact map, so ONE run of
this file proves both machines - Panya's bridge, where everything is present,
and a fresh clone in CI, where nothing is.  That is the whole point.  A test
that could only ever check the machine it happens to be running on is the bug
this milestone is about.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import pf_preconditions as pre  # noqa: E402

TOOL = ROOT / "tools" / "pf_pytest_precondition_census.py"
PINS = ROOT / "docs" / "PYTEST_SKIP_PINS.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("_pf_skip_census", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def skip_line(module, line, reason):
    return "SKIPPED [1] %s:%d: %s" % (module, line, reason)


ALL_PRESENT = {key: True for key in pre.REGISTRY}
NONE_PRESENT = {key: False for key in pre.REGISTRY}


class ArtifactsExistTests(unittest.TestCase):
    def test_the_tool_and_the_pin_file_both_ship(self):
        for path in (TOOL, PINS):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), path)

    def test_the_tool_is_pure_ascii_and_pure_stdlib(self):
        source = TOOL.read_bytes()
        self.assertTrue(
            all(byte < 128 for byte in source),
            "the census tool carries a byte the bridge console cannot encode",
        )
        text = source.decode("ascii")
        for banned in ("capstone", "pefile", "numpy", "yaml", "requests",
                       "pytest"):
            self.assertNotIn("import " + banned, text)

    def test_the_registry_is_pure_ascii_too(self):
        source = (ROOT / "tests" / "pf_preconditions.py").read_bytes()
        self.assertTrue(all(byte < 128 for byte in source))


class RegistryTests(unittest.TestCase):
    def test_every_reason_carries_its_own_machine_readable_key(self):
        for key, precondition in sorted(pre.REGISTRY.items()):
            with self.subTest(key=key):
                self.assertEqual(pre.key_of(precondition.reason), key)
                self.assertIn(pre.TOKEN_PREFIX, precondition.reason)

    def test_a_reason_without_a_token_has_no_key(self):
        self.assertIsNone(pre.key_of("runtime.py now carries the branch"))
        self.assertIsNone(pre.key_of("[precondition without a bracket"))

    def test_a_precondition_needs_a_single_word_key_and_a_path(self):
        with self.assertRaises(ValueError):
            pre.Precondition("two words", [ROOT], "x", "y")
        with self.assertRaises(ValueError):
            pre.Precondition("empty", [], "x", "y")

    def test_presence_is_recomputed_and_never_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "appears-later.txt"
            probe = pre.Precondition("probe", [target], "a file", "a test")
            self.assertFalse(probe.present)
            self.assertEqual(probe.missing, (target,))
            target.write_text("here now", encoding="ascii")
            self.assertTrue(probe.present)
            self.assertEqual(probe.missing, ())

    def test_the_login_capture_path_matches_the_audit_tool_exactly(self):
        """Two files name the same capture; neither may move alone."""
        spec = importlib.util.spec_from_file_location(
            "_pf_mp_audit",
            ROOT / "tools" / "pf_multiplayer_readiness_audit.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            module.LOGIN_REQ_CAPTURE, pre.LOGIN_REQ_CAPTURE_RELPATH,
        )


class PinFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads(PINS.read_text(encoding="utf-8"))

    def test_every_pinned_key_is_in_the_registry(self):
        for entry in self.pins["preconditions"]:
            with self.subTest(key=entry["key"]):
                self.assertIn(entry["key"], pre.REGISTRY)

    def test_every_pinned_module_exists_and_is_named_once(self):
        seen = set()
        for entry in self.pins["preconditions"]:
            pair = (entry["key"], entry["module"])
            with self.subTest(pair=pair):
                self.assertTrue((ROOT / entry["module"]).is_file())
                self.assertNotIn(pair, seen)
                seen.add(pair)
        design = set()
        for entry in self.pins["design_skips"]:
            pair = (entry["reason"], entry["module"])
            with self.subTest(pair=pair):
                self.assertTrue((ROOT / entry["module"]).is_file())
                self.assertNotIn(pair, design)
                design.add(pair)

    def test_every_pinned_count_is_a_positive_integer(self):
        for entry in self.pins["preconditions"] + self.pins["design_skips"]:
            with self.subTest(entry=entry.get("key") or entry.get("reason")):
                self.assertIsInstance(entry["count"], int)
                self.assertGreater(entry["count"], 0)

    def test_each_pinned_module_really_names_its_precondition(self):
        """The pin file cannot claim a guard the module does not have."""
        for entry in self.pins["preconditions"]:
            with self.subTest(module=entry["module"]):
                source = (ROOT / entry["module"]).read_text(encoding="utf-8")
                self.assertIn("pf_preconditions", source)
                constant = entry["key"].upper()
                self.assertTrue(
                    constant in source or constant + "_PRECONDITION" in source,
                    "%s pins precondition %r but never names it"
                    % (entry["module"], entry["key"]),
                )

    def test_the_pinned_test_names_exist_in_their_modules(self):
        for entry in self.pins["preconditions"]:
            source = (ROOT / entry["module"]).read_text(encoding="utf-8")
            for dotted in entry["tests"]:
                name = dotted.split("::")[-1]
                with self.subTest(test=name):
                    self.assertIn("def %s(" % name, source)


class CensusVerdictTests(unittest.TestCase):
    """Drive the census over both machines from one place."""

    @classmethod
    def setUpClass(cls):
        cls.module = load_tool()
        cls.pins = json.loads(PINS.read_text(encoding="utf-8"))

    def run_census(self, lines, excluded=(), present=None):
        return self.module.census(
            "\n".join(lines), list(excluded), self.pins, present,
        )[0]

    # -- the two machines, both green -------------------------------------
    def fresh_clone_transcript(self):
        lines = []
        for entry in self.pins["preconditions"]:
            reason = pre.REGISTRY[entry["key"]].reason
            for i in range(entry["count"]):
                lines.append(skip_line(entry["module"], 100 + i, reason))
        for entry in self.pins["design_skips"]:
            for i in range(entry["count"]):
                lines.append(skip_line(entry["module"], 200 + i,
                                       entry["reason"]))
        return lines

    def test_the_bridge_is_green_with_no_precondition_skips_at_all(self):
        lines = [
            skip_line(entry["module"], 200, entry["reason"])
            for entry in self.pins["design_skips"]
            for _ in range(entry["count"])
        ]
        self.assertEqual(self.run_census(lines, present=ALL_PRESENT), [])

    def test_a_fresh_clone_is_green_with_exactly_the_pinned_skips(self):
        self.assertEqual(
            self.run_census(self.fresh_clone_transcript(),
                            present=NONE_PRESENT),
            [],
        )

    def test_an_excluded_module_is_expected_to_skip_nothing(self):
        excluded = [e["module"] for e in self.pins["design_skips"]]
        lines = [
            line for line in self.fresh_clone_transcript()
            if not any(line.startswith("SKIPPED [1] " + m) for m in excluded)
        ]
        self.assertEqual(
            self.run_census(lines, excluded=excluded, present=NONE_PRESENT),
            [],
        )

    # -- and now the refusals ---------------------------------------------
    def test_one_extra_skip_is_red(self):
        lines = self.fresh_clone_transcript()
        entry = self.pins["preconditions"][0]
        lines.append(skip_line(entry["module"], 999,
                               pre.REGISTRY[entry["key"]].reason))
        problems = self.run_census(lines, present=NONE_PRESENT)
        self.assertTrue(any("PIN DRIFT" in p for p in problems), problems)

    def test_one_missing_skip_is_red_too(self):
        """Drift downwards is the dangerous direction: a test disappeared."""
        lines = self.fresh_clone_transcript()[1:]
        problems = self.run_census(lines, present=NONE_PRESENT)
        self.assertTrue(any("PIN DRIFT" in p for p in problems), problems)

    def test_a_precondition_skip_on_a_machine_that_has_the_artifact_is_red(self):
        lines = self.fresh_clone_transcript()
        problems = self.run_census(lines, present=ALL_PRESENT)
        self.assertTrue(any("PIN DRIFT" in p for p in problems), problems)

    def test_an_undeclared_skip_is_red(self):
        lines = self.fresh_clone_transcript()
        lines.append(skip_line("tests/test_arena.py", 12,
                               "no particular reason"))
        problems = self.run_census(lines, present=NONE_PRESENT)
        self.assertTrue(
            any("UNDECLARED SKIP" in p for p in problems), problems)

    def test_a_token_for_an_unregistered_key_is_red(self):
        lines = self.fresh_clone_transcript()
        lines.append(skip_line("tests/test_arena.py", 13,
                               "[precondition:moon_phase] not waxing"))
        problems = self.run_census(lines, present=NONE_PRESENT)
        self.assertTrue(
            any("unknown precondition key" in p for p in problems), problems)

    def test_a_declared_but_unpinned_precondition_skip_is_red(self):
        lines = self.fresh_clone_transcript()
        lines.append(skip_line("tests/test_arena.py", 14,
                               pre.CLIENT_IMAGE.reason))
        problems = self.run_census(lines, present=NONE_PRESENT)
        self.assertTrue(any("UNPINNED" in p for p in problems), problems)

    def test_a_module_level_skip_without_a_line_number_still_parses(self):
        parsed = self.module.parse(
            "SKIPPED [4] tests/test_x.py: " + pre.CLIENT_IMAGE.reason)
        self.assertEqual(parsed, [("tests/test_x.py", 4,
                                   pre.CLIENT_IMAGE.reason)])

    def test_windows_path_separators_are_the_same_module(self):
        parsed = self.module.parse(
            "SKIPPED [1] tests\\test_x.py:3: " + pre.CLIENT_IMAGE.reason)
        self.assertEqual(parsed[0][0], "tests/test_x.py")

    def test_a_reason_truncated_by_a_narrow_console_still_matches_its_pin(self):
        """pytest cuts summary lines to the console width; the pin must survive."""
        entry = self.pins["design_skips"][0]
        for cut in (len(entry["reason"]) - 8, len(entry["reason"]) - 1):
            with self.subTest(cut=cut):
                lines = [skip_line(entry["module"], 200,
                                   entry["reason"][:cut] + "...")
                         for _ in range(entry["count"])]
                self.assertEqual(
                    self.run_census(lines, present=ALL_PRESENT), [],
                )

    def test_tolerance_runs_one_way_only(self):
        """A pin must not be satisfied by a reason that says MORE than it."""
        self.assertTrue(self.module.same_reason("abc de", "abc def"))
        self.assertTrue(self.module.same_reason("abc def", "abc def"))
        self.assertFalse(self.module.same_reason("abc defg", "abc def"))
        self.assertFalse(self.module.same_reason("   ", "abc def"))

    def test_a_truncated_reason_from_the_wrong_module_is_still_undeclared(self):
        entry = self.pins["design_skips"][0]
        lines = [skip_line("tests/test_arena.py", 7,
                           entry["reason"][:12] + "...")]
        problems = self.run_census(lines, present=ALL_PRESENT)
        self.assertTrue(
            any("UNDECLARED SKIP" in p for p in problems), problems)

    def test_lines_that_are_not_skips_are_ignored(self):
        self.assertEqual(self.module.parse(
            "1860 passed, 1 skipped\nSKIPPED some prose\n"), [])


class ToolRunsTests(unittest.TestCase):
    """Exit codes are a contract; run the real process to prove them."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(TOOL), *args], capture_output=True,
        )

    def test_it_aborts_with_two_when_given_no_transcript(self):
        completed = self._run()
        self.assertEqual(completed.returncode, 2)
        self.assertIn(b"CENSUS ABORT", completed.stdout)

    def test_it_aborts_with_two_when_the_report_is_missing(self):
        completed = self._run("--report", "no-such-transcript.txt")
        self.assertEqual(completed.returncode, 2)

    def test_it_reads_a_transcript_from_stdin_and_prints_pure_ascii(self):
        completed = subprocess.run(
            [sys.executable, str(TOOL), "-"],
            input=b"nothing was skipped here\n", capture_output=True,
        )
        self.assertIn(completed.returncode, (0, 1))
        self.assertTrue(all(byte < 128 for byte in completed.stdout))
        completed.stdout.decode("ascii")

    def test_a_transcript_with_a_planted_undeclared_skip_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "transcript.txt"
            report.write_text(
                skip_line("tests/test_arena.py", 5, "because I said so") + "\n",
                encoding="ascii",
            )
            completed = self._run("--report", str(report))
        self.assertEqual(completed.returncode, 1)
        self.assertIn(b"UNDECLARED SKIP", completed.stdout)
        self.assertIn(b"RESULT: FAIL", completed.stdout)

    def test_the_json_mode_is_machine_readable_and_agrees_with_the_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "transcript.txt"
            report.write_text(
                skip_line("tests/test_arena.py", 5, "because I said so") + "\n",
                encoding="ascii",
            )
            completed = self._run("--report", str(report), "--json")
        payload = json.loads(completed.stdout.decode("ascii"))
        self.assertEqual(payload["result"], "FAIL")
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(sorted(payload["artifacts"]), sorted(pre.REGISTRY))


if __name__ == "__main__":
    unittest.main()
