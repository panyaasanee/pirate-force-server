"""The vendored 160-name API census matches the LANE-Q charter's own numbers.

prompts/LANE-Q.md (pf_bridge) states the census by hand: 160 names across 8
namespaces, Player 73 / Quest 25 / Trigger 17 / Party 11 / Mob 10 /
Instance 9 / Guild 8 / Scene 7, 12,653 call sites total.  This module reads
those numbers from ``lua_api/api_spec.tsv`` (see that file's own docstring
for provenance) instead of typing them a second time, so a re-vendor that
silently drops or duplicates a row fails here on every machine, no sibling
checkout required.
"""
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


class TheCensusIsNotReadAtImportTimeTests(unittest.TestCase):
    """`import script_host` must survive a corrupt census (finding 13).

    The refusals above are only half the fix.  Until round `oghyca` the
    parse ran at spec's own import, so every one of them raised out of
    `import pirateforce_foundation.script_host` itself: that module's
    fail-closed sweeps were dead before their own try/except could run, and
    `_host_side_error_types()` -- the thing that keeps a defect of ours off
    an innocent quest file's name -- never got to see the one mirror every
    ScriptHost construction reads.  The end-to-end half (the LUA_HOST line
    and the host_failed bucket) is in tests/test_script_lua_corpus.py,
    which needs the Lua runtime; this test needs none.

    A child interpreter because import happens once per process: this
    module has already imported both by the time any test here runs.
    """

    def test_script_host_imports_with_a_broken_census_and_fails_only_on_use(self):
        # Same locals-only style as the -O tests below: this module's own
        # header keeps its import list to what every test needs.
        import subprocess
        import sys

        src_root = Path(spec.__file__).resolve().parents[2]
        code = (
            "import sys, pathlib\n"
            "sys.path.insert(0, %r)\n"
            "from pirateforce_foundation.lua_api import spec, vendored\n"
            "spec._SPEC_PATH = pathlib.Path('no_such_api_spec.tsv')\n"
            "spec._CACHE.clear()\n"
            "import pirateforce_foundation.script_host as sh\n"
            "print('IMPORTED')\n"
            "try:\n"
            "    sh.lua_api_spec.NAMESPACE_METHODS\n"
            "except vendored.VendoredDataError:\n"
            "    print('LAZY')\n"
            % str(src_root))
        done = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.split(), ["IMPORTED", "LAZY"])

    def test_every_public_name_still_reads_as_a_plain_attribute(self):
        # PEP 562 resolution is an implementation detail; call sites (and
        # dir(), which the census tooling walks) must not have to know.
        for name in spec._LAZY_NAMES:
            self.assertIn(name, dir(spec))
            self.assertIsNotNone(getattr(spec, name))
        with self.assertRaises(AttributeError):
            spec.API_FUNCTIONS_TYPO

    def test_the_tables_are_parsed_once_and_shared(self):
        self.assertIs(spec.API_FUNCTIONS, spec.API_FUNCTIONS)
        self.assertIs(spec.BY_QUALIFIED_NAME["Quest.SetFlag"],
                      spec.BY_QUALIFIED_NAME["Quest.SetFlag"])


class LoaderRefusesInsteadOfAssertingTests(unittest.TestCase):
    """pf-adversary D13 (round `wn088m`): `python -O` deleted the header guard.

    `_load` used a bare `assert` to check `api_spec.tsv`'s header. `python -O`
    strips `assert` statements outright, so under `-O` a re-vendor that
    reordered the columns would have been parsed happily -- `call_count` and
    `file_count` swapped across all 160 rows, no error anywhere. The guard did
    not merely weaken under `-O`, it ceased to exist.

    These run the loader against corrupt copies in a CHILD interpreter under
    `-O`, because that is the only way to prove the statement survives
    optimisation: asserting it in-process proves nothing about a flag this
    process was not started with.

    THE CHILD COPIES NOTHING. The first version of these tests staged the
    whole `src/` tree per test so the child would import a package with a
    corrupt TSV in it. That is 21 MB copied six times -- 126 MB on the
    Windows gate, followed by an `rmtree` over a tree the child had just
    written `__pycache__` into -- and the gate went RED at `pytest_subset`
    with no FAILED line. `_load` takes a path now, so the child imports the
    real, valid package and calls `_load(corrupt_file)`.
    """

    def _load_under(self, contents: str, optimised: bool):
        """Run `spec._load(<a corrupt copy>)` in a child interpreter."""
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        from pirateforce_foundation.lua_api import spec

        src_root = Path(spec.__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "api_spec.tsv"
            target.write_text(contents, encoding="ascii")
            argv = [sys.executable]
            if optimised:
                argv.append("-O")
            # The exception is caught by TYPE NAME as well as by its
            # `RuntimeError` base: importing `lua_api.vendored` to name the
            # class would run `lua_api/__init__`, and this test has no
            # interest in what that does.
            argv += ["-c", (
                "import sys, pathlib\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "from pirateforce_foundation.lua_api import spec\n"
                "try:\n"
                "    rows = spec._load(pathlib.Path(sys.argv[2]))\n"
                "except Exception as exc:\n"
                "    if type(exc).__name__ != 'VendoredDataError':\n"
                "        raise\n"
                "    if not isinstance(exc, RuntimeError):\n"
                "        raise\n"
                "    print('REFUSED', exc)\n"
                "else:\n"
                "    print('ACCEPTED', len(rows))\n"
            ), str(src_root), str(target)]
            done = subprocess.run(argv, capture_output=True, text=True,
                                  timeout=120)
        return done

    def test_a_reordered_header_is_refused_even_under_dash_O(self):
        from pirateforce_foundation.lua_api import spec

        good = spec._SPEC_PATH.read_text(encoding="ascii").splitlines()
        # Swap the two count columns in the header only: every row still
        # parses as six integers-and-strings, so ONLY the header check can
        # catch this. That is exactly the case `-O` used to let through.
        header = good[0].split("\t")
        header[2], header[3] = header[3], header[2]
        corrupt = "\n".join(["\t".join(header)] + good[1:]) + "\n"
        for optimised in (False, True):
            with self.subTest(optimised=optimised):
                done = self._load_under(corrupt, optimised)
                self.assertIn("REFUSED", done.stdout,
                              "python -O must not delete the header guard: "
                              "%r / %r" % (done.stdout, done.stderr))
                self.assertIn("header drifted", done.stdout)

    def test_the_unmodified_spec_still_loads_under_dash_O(self):
        from pirateforce_foundation.lua_api import spec

        good = spec._SPEC_PATH.read_text(encoding="ascii")
        done = self._load_under(good, optimised=True)
        self.assertIn("ACCEPTED %d" % len(spec.API_FUNCTIONS), done.stdout,
                      done.stderr)

    def test_a_short_row_names_its_line_number(self):
        from pirateforce_foundation.lua_api import spec

        good = spec._SPEC_PATH.read_text(encoding="ascii").splitlines()
        corrupt = "\n".join(good[:3] + ["Quest\tOops"] + good[3:]) + "\n"
        done = self._load_under(corrupt, optimised=True)
        self.assertIn("REFUSED", done.stdout, done.stderr)
        self.assertIn("line 4", done.stdout)

    def test_a_non_integer_count_names_its_line_number(self):
        from pirateforce_foundation.lua_api import spec

        good = spec._SPEC_PATH.read_text(encoding="ascii").splitlines()
        cells = good[1].split("\t")
        cells[2] = "many"
        corrupt = "\n".join([good[0], "\t".join(cells)] + good[2:]) + "\n"
        done = self._load_under(corrupt, optimised=True)
        self.assertIn("REFUSED", done.stdout, done.stderr)
        self.assertIn("non-integer count", done.stdout)

    def test_an_empty_file_is_refused_rather_than_index_erroring(self):
        done = self._load_under("", optimised=True)
        self.assertIn("REFUSED", done.stdout, done.stderr)
        self.assertIn("is empty", done.stdout)

    def test_a_header_with_no_rows_is_refused(self):
        from pirateforce_foundation.lua_api import spec

        header = spec._SPEC_PATH.read_text(encoding="ascii").splitlines()[0]
        done = self._load_under(header + "\n", optimised=True)
        self.assertIn("REFUSED", done.stdout, done.stderr)
        self.assertIn("no rows", done.stdout)

    def test_the_loader_contains_no_bare_assert(self):
        """A second, weaker signal -- the behavioural tests above are the pin.

        Kept because it is the one that names the DEFECT rather than a
        symptom, and pf-adversary D3 (round `wn088m`) taught this lane that a
        string count alone is not a pin: it is here underneath the subprocess
        tests, not instead of them.
        """
        import ast
        import inspect
        from pirateforce_foundation.lua_api import spec

        tree = ast.parse(inspect.getsource(spec._load))
        self.assertEqual(
            [node for node in ast.walk(tree) if isinstance(node, ast.Assert)],
            [], "python -O deletes assert statements; _load must raise")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
