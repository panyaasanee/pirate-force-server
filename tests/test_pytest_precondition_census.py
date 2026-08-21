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
import unittest.mock
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


class HistoricalGitObjectTests(unittest.TestCase):
    """The two preconditions whose artifact lives INSIDE git.

    The machine-independence rule of this file applies here and bites harder:
    whether THIS clone holds commit 5c200e2 is exactly what differs between a
    cloud round and the gate, so nothing below asserts ``present`` for a
    REGISTERED entry.  Every test builds the repository it reasons about - a
    plain one, a shallow one, a broken one - so one run proves every machine.

    The class under test is a state machine rather than a boolean because an
    adversarial pass proved a boolean lets ``.git`` deleted read as a suite full
    of declared skips, graded PASS by a census asking the same broken oracle.
    Most of what follows is therefore about the states that MUST NOT skip.
    """

    NOWHERE = "0" * 40 + "^{commit}"

    def git(self, args, cwd=None, check=True):
        try:
            return subprocess.run(
                ["git"] + args, cwd=None if cwd is None else str(cwd),
                check=check, capture_output=True, text=True,
            )
        except OSError as error:
            self.fail(
                "git is not runnable on this machine (%s).  These tests build "
                "real repositories on purpose; there is no version of them "
                "that is meaningful without git." % (error,)
            )

    def make_repo(self, where, commits=1):
        """A real repository with ``commits`` commits."""
        self.git(["init", "-q", str(where)])
        for index in range(commits):
            self.git(
                ["-c", "user.name=census test",
                 "-c", "user.email=census@example.invalid",
                 "-c", "commit.gpgsign=false",
                 "-c", "core.hooksPath=" + str(Path(where) / "no-hooks-here"),
                 "commit", "-q", "--allow-empty", "-m", "commit %d" % index],
                cwd=where,
            )
        return Path(where)

    def probe(self, root, revisions=("HEAD^{commit}",), key="probe"):
        return pre.HistoricalGitObject(
            key, list(revisions), "a commit", "a test", root=root, timeout=30,
        )

    def assert_require_refuses_to_skip(self, probe, expected_in_message=""):
        """`require` must FAIL here, and must not skip its way out.

        Written this way on purpose: `assertRaises(self.failureException)`
        around a call that might raise SkipTest lets a mutation escape by
        turning the negative control itself into a skipped test.  Round 118
        measured exactly that - letting a BROKEN state skip survived until this
        helper existed.
        """
        try:
            probe.require(self)
        except unittest.SkipTest as skipped:
            raise self.failureException(
                "require() SKIPPED for a state that must fail: %s" % skipped)
        except self.failureException as failure:
            if expected_in_message:
                self.assertIn(expected_in_message, str(failure))
            return
        raise self.failureException(
            "require() accepted a state it must have refused")

    # -- construction -------------------------------------------------------

    def test_a_historical_object_needs_a_single_word_key_and_a_revision(self):
        with self.assertRaises(ValueError):
            pre.HistoricalGitObject("two words", ["HEAD"], "x", "y")
        with self.assertRaises(ValueError):
            pre.HistoricalGitObject("empty", [], "x", "y")
        with self.assertRaises(ValueError):
            pre.HistoricalGitObject("blank", [""], "x", "y")

    # -- the four states ----------------------------------------------------

    def test_a_repository_that_has_the_object_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_repo(Path(tmp) / "repo")
            probe = self.probe(root)
            self.assertEqual(probe.state()[0], pre.HistoricalGitObject.PRESENT)
            self.assertTrue(probe.present)
            self.assertEqual(probe.missing, ())

    def test_reachability_is_recomputed_and_never_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.git(["init", "-q", str(root)])
            probe = self.probe(root)
            self.assertFalse(probe.present)
            self.assertEqual(probe.missing, ("HEAD^{commit}",))
            self.make_repo(root, commits=1)
            self.assertTrue(probe.present)
            self.assertEqual(probe.missing, ())

    def test_a_shallow_clone_missing_the_object_is_a_declared_skip(self):
        """The whole point of the class, on a shallow clone built here."""
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_repo(Path(tmp) / "source", commits=3)
            first = self.git(
                ["rev-list", "--max-parents=0", "HEAD"], cwd=source
            ).stdout.strip()
            clone = Path(tmp) / "shallow"
            self.git(["clone", "-q", "--depth", "1", "--no-local",
                      Path(source).as_uri(), str(clone)])
            probe = self.probe(clone, revisions=[first + "^{commit}"])
            state, detail = probe.state()
            self.assertEqual(state, pre.HistoricalGitObject.SHALLOW)
            self.assertIn("shallow", detail)
            self.assertFalse(probe.present)
            with self.assertRaises(unittest.SkipTest) as caught:
                probe.require(self)
            self.assertEqual(pre.key_of(str(caught.exception)), "probe")
            self.assertIn("shallow", str(caught.exception))

    def test_a_complete_clone_missing_the_object_FAILS_and_never_skips(self):
        """A typo in a pinned SHA must not disable a test everywhere."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_repo(Path(tmp) / "repo")
            probe = self.probe(root, revisions=[self.NOWHERE])
            state, detail = probe.state()
            self.assertEqual(state, pre.HistoricalGitObject.BROKEN)
            self.assertIn("revision is wrong", detail)
            self.assert_require_refuses_to_skip(
                probe, "NOT because of clone depth")

    def test_a_directory_that_is_not_a_repository_FAILS_and_never_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = self.probe(Path(tmp))
            state, detail = probe.state()
            self.assertEqual(state, pre.HistoricalGitObject.BROKEN)
            self.assertIn("not a git work tree", detail)
            self.assert_require_refuses_to_skip(probe)

    def test_git_missing_from_the_machine_FAILS_and_never_skips(self):
        """No git is a broken machine, not missing evidence.

        The first draft answered "absent" here and published a reason that
        blamed clone depth, on a machine where the prescribed remedy - git
        fetch --unshallow - cannot even be typed.
        """
        probe = self.probe(ROOT)

        def no_git(*args, **kwargs):
            raise OSError(2, "no such file or directory: git")

        with unittest.mock.patch.object(pre.subprocess, "run", no_git):
            state, detail = probe.state()
            self.assertEqual(state, pre.HistoricalGitObject.BROKEN)
            self.assertIn("not runnable", detail)
            self.assertNotIn("shallow", detail)
            self.assert_require_refuses_to_skip(probe)

    def test_git_hanging_FAILS_and_never_skips(self):
        probe = self.probe(ROOT)

        def timed_out(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="git", timeout=probe.timeout)

        with unittest.mock.patch.object(pre.subprocess, "run", timed_out):
            state, detail = probe.state()
            self.assertEqual(state, pre.HistoricalGitObject.BROKEN)
            self.assertIn("did not answer", detail)

    # -- aggregation --------------------------------------------------------

    def test_every_named_revision_must_be_present_not_merely_one(self):
        """`all`, not `any`: naming a second object must be able to fail."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_repo(Path(tmp) / "repo")
            both = self.probe(root, revisions=["HEAD^{commit}", self.NOWHERE])
            self.assertFalse(both.present)
            self.assertEqual(both.missing, (self.NOWHERE,))
            self.assertEqual(both.state()[0], pre.HistoricalGitObject.BROKEN)

    # -- the registered entries --------------------------------------------

    def test_every_registered_entry_names_a_commit_and_the_object_read(self):
        """A commit-only probe reports PRESENT on a partial clone and lies."""
        for entry in (pre.ORIGINAL_SCHEMA_HISTORY, pre.AUDIT_HEAD_HISTORY):
            with self.subTest(key=entry.key):
                commits = [r for r in entry.revisions if r.endswith("^{commit}")]
                objects = [r for r in entry.revisions if ":" in r]
                self.assertEqual(len(commits), 1, entry.revisions)
                self.assertTrue(objects, entry.revisions)

    def test_the_two_history_keys_stay_separate(self):
        self.assertNotEqual(pre.ORIGINAL_SCHEMA_COMMIT, pre.AUDIT_HEAD_COMMIT)
        self.assertNotEqual(
            pre.ORIGINAL_SCHEMA_HISTORY.key, pre.AUDIT_HEAD_HISTORY.key)
        self.assertEqual(
            set(pre.ORIGINAL_SCHEMA_HISTORY.revisions)
            & set(pre.AUDIT_HEAD_HISTORY.revisions),
            set(),
        )

    def test_the_audit_head_commit_matches_the_audit_tool_exactly(self):
        """Two files name the same commit; neither may move alone."""
        spec = importlib.util.spec_from_file_location(
            "_pf_mp_audit_head",
            ROOT / "tools" / "pf_multiplayer_readiness_audit.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.HEAD_COMMIT, pre.AUDIT_HEAD_COMMIT)

    def test_the_guarded_test_reads_the_object_the_registry_names(self):
        """The test module and the registry cannot name different objects."""
        source = (ROOT / "tests" / "test_foundation.py").read_text(
            encoding="utf-8")
        self.assertIn("ORIGINAL_SCHEMA_COMMIT", source)
        for quote in ('"', "'"):
            self.assertNotIn(
                quote + pre.ORIGINAL_SCHEMA_COMMIT + ":", source,
                "test_foundation.py hard-codes the object the registry already "
                "names; the two can drift apart",
            )
        self.assertIn(
            "migrations/001_initial.sql", pre.ORIGINAL_SCHEMA_BLOB)
        self.assertIn(
            pre.ORIGINAL_SCHEMA_COMMIT, pre.ORIGINAL_SCHEMA_HISTORY.reason)
        self.assertIn(pre.AUDIT_HEAD_COMMIT, pre.AUDIT_HEAD_HISTORY.reason)

    def test_a_skip_reason_carries_the_token_and_the_measured_cause(self):
        reason = pre.ORIGINAL_SCHEMA_HISTORY.skip_reason("a measured cause")
        self.assertEqual(
            pre.key_of(reason), pre.ORIGINAL_SCHEMA_HISTORY.key)
        self.assertIn("a measured cause", reason)


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

    def test_every_pinned_count_matches_the_number_of_names_pinned(self):
        """A count and its list cannot disagree in silence."""
        for entry in self.pins["preconditions"]:
            with self.subTest(key=entry["key"]):
                self.assertEqual(entry["count"], len(entry["tests"]))

    def test_each_pinned_module_guards_exactly_its_pinned_count(self):
        """Deleting a guard, or guarding with the wrong key, goes red HERE.

        It has to be here, because for a key whose artifact is PRESENT the
        census expects zero skips - so on the gate and on the bridge the pinned
        count is never compared against a real run at all.  Round 118 measured
        that hole by deleting the guard lines: the suite stayed green.  The
        source is the only witness those machines have.
        """
        for entry in self.pins["preconditions"]:
            source = (ROOT / entry["module"]).read_text(encoding="utf-8")
            constant = entry["key"].upper()
            uses = sum(
                source.count("%s.%s(" % (name, verb))
                for name in (constant, constant + "_PRECONDITION")
                for verb in ("require", "skip_unless_present")
            )
            with self.subTest(key=entry["key"], module=entry["module"]):
                self.assertEqual(
                    uses, entry["count"],
                    "%s pins %d skip(s) for %r but the module uses that guard "
                    "%d time(s)"
                    % (entry["module"], entry["count"], entry["key"], uses),
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
