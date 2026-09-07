"""The vendored 160-name API census matches the LANE-Q charter's own numbers.

prompts/LANE-Q.md (pf_bridge) states the census by hand: 160 names across 8
namespaces, Player 73 / Quest 25 / Trigger 17 / Party 11 / Mob 10 /
Instance 9 / Guild 8 / Scene 7, 12,653 call sites total.  This module reads
those numbers from ``lua_api/api_spec.tsv`` (see that file's own docstring
for provenance) instead of typing them a second time, so a re-vendor that
silently drops or duplicates a row fails here on every machine, no sibling
checkout required.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pirateforce_foundation.lua_api import spec

CHARTER_NAMESPACE_COUNTS = {
    "Player": 73,
    "Quest": 25,
    "Trigger": 17,
    "Party": 11,
    "Mob": 10,
    "Instance": 9,
    "Guild": 8,
    "Scene": 7,
}


class ApiSpecMatchesTheCharterTests(unittest.TestCase):
    def test_total_function_count_is_160(self):
        self.assertEqual(len(spec.API_FUNCTIONS), 160)

    def test_eight_namespaces_named_by_the_charter(self):
        self.assertEqual(set(spec.NAMESPACES), set(CHARTER_NAMESPACE_COUNTS))

    def test_each_namespace_method_count_matches_the_charter(self):
        for namespace, expected in CHARTER_NAMESPACE_COUNTS.items():
            with self.subTest(namespace=namespace):
                self.assertEqual(
                    len(spec.NAMESPACE_METHODS[namespace]), expected,
                    "namespace %r drifted from the charter's %d" % (namespace, expected),
                )

    def test_total_call_sites_is_12653(self):
        total = sum(fn.call_count for fn in spec.API_FUNCTIONS)
        self.assertEqual(total, 12653)

    def test_no_duplicate_qualified_names(self):
        names = [fn.qualified_name for fn in spec.API_FUNCTIONS]
        self.assertEqual(len(names), len(set(names)))

    def test_by_qualified_name_lookup_agrees_with_the_tuple(self):
        self.assertEqual(len(spec.BY_QUALIFIED_NAME), len(spec.API_FUNCTIONS))
        for fn in spec.API_FUNCTIONS:
            self.assertIs(spec.BY_QUALIFIED_NAME[fn.qualified_name], fn)

    def test_the_twenty_busiest_names_named_in_the_charter_are_present(self):
        # A sample from PF_LUA_API_SPEC.md's own "20 most-called" table -
        # not the whole 20, just enough that a rename or drop is caught.
        for qualified, expected_calls in (
            ("Player.MobAppear", 3532),
            ("Player.AddItem", 1430),
            ("Quest.RewardItemSelect", 1335),
            ("Mob.ShowAnimation", 716),
            ("Trigger.NextStatus", 353),
            ("Trigger.GetTriggerStatus", 134),
        ):
            with self.subTest(qualified=qualified):
                fn = spec.BY_QUALIFIED_NAME[qualified]
                self.assertEqual(fn.call_count, expected_calls)

    def test_vendored_tsv_is_ascii_only(self):
        # Bridge console is code page 874; this file must never carry a byte
        # that breaks it.
        raw = Path(spec._SPEC_PATH).read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:
            self.fail("api_spec.tsv is not ASCII-only: %s" % exc)


class BrokenVendoredCensusIsRefusedByNameTests(unittest.TestCase):
    """Every way api_spec.tsv can be broken raises spec.ApiSpecError.

    Not a style preference: script_host._host_side_error_types() classifies
    a failure as OURS by asking whether it is a VendoredDataError, and
    ApiSpecError is the only subclass this module raises.  A shape that
    escapes as a bare ValueError/OSError/AssertionError instead -- which is
    what this loader did before round oghyca -- is logged against whichever
    quest script happened to be loading, which is the defect
    lua_api/vendored.py exists to prevent.
    """

    HEADER = "namespace\tmethod\tcall_count\tfile_count\tarity_min\tarity_max"
    GOOD_ROW = "Quest\tSetFlag\t12\t7\t2\t2"

    def _load_from(self, text):
        root = Path(tempfile.mkdtemp(prefix="pf_api_spec_"))
        self.addCleanup(shutil.rmtree, root, True)
        path = root / "api_spec.tsv"
        if text is not None:
            path.write_text(text, encoding="ascii")
        real = spec._SPEC_PATH
        spec._SPEC_PATH = path
        spec._CACHE.clear()
        self.addCleanup(spec._CACHE.clear)
        self.addCleanup(setattr, spec, "_SPEC_PATH", real)
        return spec._tables

    def test_a_missing_file_is_refused(self):
        load = self._load_from(None)
        with self.assertRaises(spec.ApiSpecError):
            load()

    def test_an_empty_file_is_refused(self):
        load = self._load_from("")
        with self.assertRaises(spec.ApiSpecError):
            load()

    def test_a_header_with_no_rows_is_refused(self):
        load = self._load_from(self.HEADER + "\n")
        with self.assertRaises(spec.ApiSpecError):
            load()

    def test_a_drifted_header_is_refused(self):
        load = self._load_from(
            self.HEADER.replace("arity_max", "arity_maximum") + "\n"
            + self.GOOD_ROW + "\n")
        with self.assertRaises(spec.ApiSpecError):
            load()

    def test_a_ragged_row_is_refused_rather_than_unpacked(self):
        # The old shape let this out as ValueError("not enough values to
        # unpack"), naming neither the file nor the line.
        load = self._load_from(
            self.HEADER + "\n" + "Quest\tSetFlag\t12\t7\t2\n")
        with self.assertRaises(spec.ApiSpecError) as caught:
            load()
        self.assertIn("line 2", str(caught.exception))

    def test_a_non_integer_count_is_refused_naming_the_column_and_line(self):
        load = self._load_from(
            self.HEADER + "\n" + "Quest\tSetFlag\ttwelve\t7\t2\t2\n")
        with self.assertRaises(spec.ApiSpecError) as caught:
            load()
        self.assertIn("call_count", str(caught.exception))
        self.assertIn("line 2", str(caught.exception))

    def test_a_good_file_still_parses_and_caches_one_object(self):
        load = self._load_from(self.HEADER + "\n" + self.GOOD_ROW + "\n")
        first, second = load(), load()
        self.assertIs(first, second)
        self.assertEqual(
            [fn.qualified_name for fn in first["API_FUNCTIONS"]],
            ["Quest.SetFlag"])
        self.assertEqual(first["NAMESPACES"], ("Quest",))


class TheCensusIsNotReadAtImportTimeTests(unittest.TestCase):
    """script_host must import even when the vendored census is broken.

    Before round oghyca the parse ran at spec's own import, so a corrupt
    file raised out of `import pirateforce_foundation.script_host` itself:
    every fail-closed sweep in that module was dead before its own
    try/except could run, and the escaping exception was not a type
    _host_side_error_types() would have recognised (pf-adversary finding
    13).  Run in a child interpreter because import is once per process --
    this module has already imported both by the time any test here runs.
    """

    def test_script_host_imports_with_a_broken_census_and_fails_only_on_use(self):
        src = str(Path(__file__).resolve().parents[1] / "src")
        code = (
            "import sys, pathlib\n"
            "sys.path.insert(0, %r)\n"
            "from pirateforce_foundation.lua_api import spec\n"
            "spec._SPEC_PATH = pathlib.Path('no_such_api_spec.tsv')\n"
            "spec._CACHE.clear()\n"
            "import pirateforce_foundation.script_host as sh\n"
            "print('IMPORTED')\n"
            "try:\n"
            "    sh.lua_api_spec.NAMESPACE_METHODS\n"
            "except spec.ApiSpecError as exc:\n"
            "    print('LAZY', type(exc).__name__)\n"
            % src)
        done = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.split(), ["IMPORTED", "LAZY", "ApiSpecError"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
