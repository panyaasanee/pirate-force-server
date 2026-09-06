"""The derivation behind the bridge-guarded job, and the job's own shape.

COO work order `0445` item 3.  The job in
``.github/workflows/bridge-guarded-tests.yml`` is only as honest as the list
it runs: an empty or short list produces a green run over nothing, which is
indistinguishable from the hole the job exists to close.  So the derivation
is tested here, and two properties of the workflow file are pinned - that it
does not impersonate the gate, and that it starts report-only.
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import pf_preconditions  # noqa: E402
from tools import pf_bridge_guarded_tests as guarded  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "bridge-guarded-tests.yml"


class _FakePrecondition:
    def __init__(self, paths):
        self.paths = tuple(Path(p) for p in paths)


class _FakeComposite:
    def __init__(self, parts):
        self.parts = tuple(parts)


class DerivationTests(unittest.TestCase):

    def test_a_precondition_inside_the_bridge_is_named(self):
        module = type(sys)("fake")
        module.IN_BRIDGE = _FakePrecondition(["/home/user/pf_bridge/gamedata"])
        self.assertEqual(
            ["IN_BRIDGE"], guarded.bridge_precondition_names(module))

    def test_a_precondition_outside_the_bridge_is_not_named(self):
        module = type(sys)("fake")
        module.IN_REPO = _FakePrecondition(["/home/user/pirate-force-server/x"])
        self.assertEqual([], guarded.bridge_precondition_names(module))

    def test_one_bridge_path_among_several_is_enough(self):
        # A test guarded by this skips on a machine without the bridge even
        # though most of what it needs is in the repo.
        module = type(sys)("fake")
        module.MIXED = _FakePrecondition(
            ["/home/user/pirate-force-server/x", "/home/user/pf_bridge/y"])
        self.assertEqual(["MIXED"], guarded.bridge_precondition_names(module))

    def test_the_walk_recurses_into_composite_parts(self):
        # AllOfThese holds `parts`, not `paths`; test_script_lua_corpus.py
        # reaches the bridge's Lua corpus only through one of them.
        module = type(sys)("fake")
        module.COMPOSITE = _FakeComposite(
            [_FakePrecondition(["/home/user/pf_bridge/gamedata/lua"])])
        self.assertEqual(
            ["COMPOSITE"], guarded.bridge_precondition_names(module))

    def test_a_cycle_in_the_parts_graph_terminates(self):
        module = type(sys)("fake")
        left = _FakeComposite([])
        right = _FakeComposite([left])
        left.parts = (right,)
        module.LOOP = left
        self.assertEqual([], guarded.bridge_precondition_names(module))

    def test_a_directory_merely_NAMED_pf_bridge_deeper_still_counts(self):
        # The match is on a path COMPONENT, so a nested checkout counts and a
        # lookalike filename does not.
        module = type(sys)("fake")
        module.NESTED = _FakePrecondition(["/srv/x/pf_bridge/notes_to_chief"])
        module.LOOKALIKE = _FakePrecondition(["/srv/x/pf_bridge_backup.tar"])
        self.assertEqual(["NESTED"], guarded.bridge_precondition_names(module))

    def test_lowercase_module_attributes_are_ignored(self):
        module = type(sys)("fake")
        module.helper = _FakePrecondition(["/home/user/pf_bridge/x"])
        self.assertEqual([], guarded.bridge_precondition_names(module))


class FileScanTests(unittest.TestCase):

    def _scan(self, body, names=("BRIDGE_SIBLING",)):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test_sample.py"
            path.write_text(body, encoding="utf-8")
            return guarded.guarded_test_files(list(names), Path(tmp))

    def test_a_file_naming_the_precondition_is_found(self):
        self.assertEqual(1, len(self._scan("x = BRIDGE_SIBLING.present\n")))

    def test_a_longer_identifier_is_not_a_hit(self):
        self.assertEqual(
            [], self._scan("x = BRIDGE_SIBLING_TWO.present\n"))

    def test_a_prefixed_identifier_is_not_a_hit(self):
        self.assertEqual([], self._scan("x = MY_BRIDGE_SIBLING\n"))

    def test_files_not_named_test_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "helper.py").write_text(
                "BRIDGE_SIBLING\n", encoding="utf-8")
            self.assertEqual(
                [], guarded.guarded_test_files(["BRIDGE_SIBLING"], Path(tmp)))

    def test_no_names_means_no_files_rather_than_every_file(self):
        # An empty name list must never compile into a regex that matches
        # everything -- that would hand pytest the whole suite and call it
        # "the guarded set".
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "test_x.py").write_text("anything\n", encoding="utf-8")
            self.assertEqual([], guarded.guarded_test_files([], Path(tmp)))


class LiveDerivationTests(unittest.TestCase):

    def test_the_live_registry_yields_bridge_preconditions(self):
        names = guarded.bridge_precondition_names(pf_preconditions)
        self.assertIn("BRIDGE_SIBLING", names)
        self.assertGreaterEqual(len(names), 6, names)

    def test_the_live_derivation_names_real_files(self):
        files = guarded.guarded_test_files(
            guarded.bridge_precondition_names(pf_preconditions))
        self.assertTrue(files)
        found = {p.name for p in files}
        for expected in ("test_mob_death_widening_schema_gate.py",
                         "test_script_lua_corpus.py",
                         "test_world_scene_folder_on_the_bridge.py"):
            self.assertIn(expected, found)

    def test_every_derived_file_exists_and_is_a_test_module(self):
        for path in guarded.guarded_test_files(
                guarded.bridge_precondition_names(pf_preconditions)):
            self.assertTrue(path.is_file(), path)
            self.assertTrue(path.name.startswith("test_"), path)

    def test_main_prints_repo_relative_posix_paths(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = guarded.main([])
        self.assertEqual(0, rc)
        lines = [line for line in buf.getvalue().splitlines() if line]
        self.assertTrue(lines)
        for line in lines:
            self.assertTrue(line.startswith("tests/"), line)
            self.assertNotIn("\\", line)

    def test_an_empty_derivation_exits_2_and_never_0(self):
        # The contract the workflow leans on: no files is a tool failure, so
        # `set -e` stops before pytest is handed an empty argument list and
        # reports success over zero tests.
        import io
        import contextlib
        with tempfile.TemporaryDirectory() as tmp:
            original = guarded.guarded_test_files
            guarded.guarded_test_files = lambda names, *a, **k: []
            try:
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    with contextlib.redirect_stdout(io.StringIO()):
                        rc = guarded.main([])
            finally:
                guarded.guarded_test_files = original
            self.assertEqual(2, rc)
            self.assertIn("FATAL", err.getvalue())
            self.assertEqual([], list(Path(tmp).iterdir()))


class WorkflowShapeTests(unittest.TestCase):
    """Two properties of the job file that a later edit must not lose."""

    def setUp(self):
        self.assertTrue(WORKFLOW.is_file(), WORKFLOW)
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_the_job_is_not_called_gate(self):
        # merge-claude-pr.yml reads the conclusion of the job named `gate`.
        # A job here with that name inside a workflow named differently would
        # not be read today -- but the name is the only thing standing between
        # this report-only job and being mistaken for the verdict.
        import yaml
        data = yaml.safe_load(self.text)
        self.assertNotIn("gate", data["jobs"])
        self.assertEqual(["bridge-guarded"], list(data["jobs"]))

    def test_it_starts_report_only(self):
        import yaml
        data = yaml.safe_load(self.text)
        self.assertEqual(
            "0", str(data["env"]["PF_BRIDGE_GUARDED_BLOCKING"]),
            "COO 0445 item 3: one green round first, then block")

    def test_no_duplicate_yaml_keys(self):
        # GitHub rejects a whole file with a duplicate key; yaml.safe_load
        # accepts it silently.
        import yaml

        class _NoDup(yaml.SafeLoader):
            pass

        def _construct(loader, node, deep=False):
            seen = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node, deep=deep)
                if key in seen:
                    raise AssertionError("duplicate key %r" % (key,))
                seen[key] = loader.construct_object(value_node, deep=deep)
            return seen

        _NoDup.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct)
        yaml.load(self.text, _NoDup)

    def test_the_file_is_ascii(self):
        WORKFLOW.read_bytes().decode("ascii")

    # NOT a test: `bash -n` on every `run:` block.  It is run by hand in the
    # round that touches this file (5/5 blocks clean in R383), and it is not
    # here because the gate PINS SKIP COUNTS - a test that skips when bash is
    # absent and runs when it is present is a machine-dependent skip, which is
    # what closed PR #503.  A proper OptionalPackage-style precondition would
    # need a static count that is right on every machine at once, and there is
    # no such number.  Recorded so the next reader knows this was decided, not
    # forgotten.


if __name__ == "__main__":
    unittest.main()
