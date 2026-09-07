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
import tempfile
import unittest
from pathlib import Path

from pirateforce_foundation.lua_api import spec
from pirateforce_foundation.lua_api.vendored import VendoredDataError

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

    @staticmethod
    def _redigest(text: str) -> str:
        """Put a MATCHING ``# body_sha256:`` line on a corrupt copy.

        Without this every test below would measure the digest guard and
        nothing else: the digest is checked first, on purpose, so a copy
        that was edited without recomputing it is refused before its rows
        are ever read.  The shape these tests exist for is the OTHER one --
        a re-vendor whose tooling recomputed the digest over already-wrong
        content -- which is the only shape the row-level refusals can
        catch.  ``test_a_stale_digest_is_refused_before_the_rows_are_read``
        (below) is the one test that deliberately skips this helper.
        """
        from pirateforce_foundation.lua_api import spec

        lines = [line for line in text.splitlines()
                 if not line.startswith(spec.BODY_DIGEST_PREFIX)]
        digest = spec.body_digest("\n".join(lines) + "\n")
        return "\n".join([spec.BODY_DIGEST_PREFIX + digest] + lines) + "\n"

    @staticmethod
    def _body_lines(text: str) -> list:
        """The header and rows, without the comment block above them."""
        return [line for line in text.splitlines()
                if not line.startswith("#")]

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

        good = self._body_lines(spec._SPEC_PATH.read_text(encoding="ascii"))
        # Swap the two count columns in the header only: every row still
        # parses as six integers-and-strings, so ONLY the header check can
        # catch this. That is exactly the case `-O` used to let through.
        header = good[0].split("\t")
        header[2], header[3] = header[3], header[2]
        corrupt = self._redigest("\n".join(["\t".join(header)] + good[1:]))
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

        good = self._body_lines(spec._SPEC_PATH.read_text(encoding="ascii"))
        corrupt = self._redigest("\n".join(good[:3] + ["Quest\tOops"] + good[3:]))
        done = self._load_under(corrupt, optimised=True)
        self.assertIn("REFUSED", done.stdout, done.stderr)
        # Line 5 of the corrupt copy, not line 4 of its body: the digest
        # line the helper prepends is line 1, and the message must name the
        # line an editor jumps to.
        self.assertIn("line 5", done.stdout)

    def test_a_non_integer_count_names_its_line_number(self):
        from pirateforce_foundation.lua_api import spec

        good = self._body_lines(spec._SPEC_PATH.read_text(encoding="ascii"))
        cells = good[1].split("\t")
        cells[2] = "many"
        corrupt = self._redigest(
            "\n".join([good[0], "\t".join(cells)] + good[2:]))
        done = self._load_under(corrupt, optimised=True)
        self.assertIn("REFUSED", done.stdout, done.stderr)
        self.assertIn("non-integer count in call_count", done.stdout)

    def test_an_empty_file_is_refused_rather_than_index_erroring(self):
        done = self._load_under("", optimised=True)
        self.assertIn("REFUSED", done.stdout, done.stderr)
        self.assertIn("is empty", done.stdout)

    def test_a_header_with_no_rows_is_refused(self):
        from pirateforce_foundation.lua_api import spec

        header = self._body_lines(
            spec._SPEC_PATH.read_text(encoding="ascii"))[0]
        done = self._load_under(self._redigest(header), optimised=True)
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


class ACorruptCensusIsRefusedNotSilentlyLostTests(unittest.TestCase):
    """pf-adversary D2 (round `oghyca`): what the loader USED to accept.

    Every shape below parsed happily before round `5qtaqy`, and each one
    silently removed a name from the census.  A name missing from the
    census is not a missing feature -- `ApiNamespaceStub.__getitem__` hands
    an unlisted name `STUB_DEFAULT`, the integer 0, so the script's own
    `Player.RemoveItem(...)` becomes "attempt to call a number value" and
    is logged as `LUA_SCRIPT <quest file> ERR` -- a defect of OURS billed to
    a shipped quest file.  Measured with one trailing space in one cell:
    189 such lines over 122 innocent files, and 18/18 green here.

    These call `_load` directly rather than through a child interpreter:
    the `-O` question is about `assert` statements, which
    `test_the_loader_contains_no_bare_assert` pins for the whole function,
    and these refusals are `raise` statements `-O` does not touch.
    """

    def setUp(self):
        from pirateforce_foundation.lua_api import spec

        self.spec = spec
        self.tmp = tempfile.mkdtemp(prefix="pf_api_spec_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.good = [line for line in
                     spec._SPEC_PATH.read_text(encoding="ascii").splitlines()
                     if not line.startswith("#")]

    def _refusal_for(self, body_lines, redigest=True):
        """Write a corrupt copy, load it, return the refusal message."""
        text = "\n".join(body_lines) + "\n"
        if redigest:
            text = (self.spec.BODY_DIGEST_PREFIX
                    + self.spec.body_digest(text) + "\n" + text)
        else:
            text = (self.spec.BODY_DIGEST_PREFIX + "0" * 64 + "\n" + text)
        target = Path(self.tmp) / "api_spec.tsv"
        target.write_text(text, encoding="ascii")
        with self.assertRaises(VendoredDataError) as caught:
            self.spec._load(target)
        return str(caught.exception)

    def _row_with(self, index, cell, value):
        rows = list(self.good)
        cells = rows[index].split("\t")
        cells[cell] = value
        rows[index] = "\t".join(cells)
        return rows

    def test_a_trailing_space_in_a_method_name_is_refused(self):
        # THE measured one: invisible in a diff, and the reason 122 innocent
        # quest files were blamed for it.
        message = self._refusal_for(self._row_with(1, 1, "AddMeritExp "))
        self.assertIn("method that is not an identifier", message)
        self.assertIn("'AddMeritExp '", message)

    def test_an_empty_namespace_cell_is_refused(self):
        message = self._refusal_for(self._row_with(1, 0, ""))
        self.assertIn("namespace that is not an identifier", message)

    def test_a_method_name_no_script_could_index_is_refused(self):
        for spelling in ("Add Merit", "2AddMerit", "Add-Merit"):
            with self.subTest(spelling=spelling):
                message = self._refusal_for(self._row_with(1, 1, spelling))
                self.assertIn("method that is not an identifier", message)

    def test_the_three_count_spellings_int_would_have_accepted(self):
        # `int()` accepts all three; no counting tool produces any of them.
        for spelling in ("3_67", "+367", "  367  "):
            with self.subTest(spelling=spelling):
                message = self._refusal_for(self._row_with(1, 2, spelling))
                self.assertIn("non-integer count in call_count", message)

    def test_a_duplicate_qualified_name_is_refused_naming_both_lines(self):
        # This is what made API_FUNCTIONS 160 while BY_QUALIFIED_NAME was
        # 159: the second row overwrote the first in the lookup and nothing
        # said so.
        rows = list(self.good)
        rows.append(rows[1])
        message = self._refusal_for(rows)
        self.assertIn("repeats the qualified name", message)
        self.assertIn("Guild.AddMeritExp", message)
        self.assertIn("first seen on line 3", message)

    def test_an_arity_range_that_runs_backwards_is_refused(self):
        rows = self._row_with(1, 4, "3")
        cells = rows[1].split("\t")
        cells[5] = "1"
        rows[1] = "\t".join(cells)
        message = self._refusal_for(rows)
        self.assertIn("arity_min 3 greater than arity_max 1", message)

    def test_a_stale_digest_is_refused_before_the_rows_are_read(self):
        # The one guard that needs no imagination about what corruption
        # looks like: any byte of the body changed without recomputing.
        message = self._refusal_for(self.good, redigest=False)
        self.assertIn("body digest mismatch", message)

    def test_a_file_with_no_digest_header_at_all_is_refused(self):
        target = Path(self.tmp) / "api_spec.tsv"
        target.write_text("\n".join(self.good) + "\n", encoding="ascii")
        with self.assertRaises(VendoredDataError) as caught:
            self.spec._load(target)
        self.assertIn("has no # body_sha256:", str(caught.exception))

    def test_the_real_vendored_file_carries_a_matching_digest(self):
        text = self.spec._SPEC_PATH.read_text(encoding="ascii")
        declared = [line for line in text.splitlines()
                    if line.startswith(self.spec.BODY_DIGEST_PREFIX)]
        self.assertEqual(len(declared), 1, "exactly one digest header")
        self.assertEqual(
            declared[0][len(self.spec.BODY_DIGEST_PREFIX):].strip(),
            self.spec.body_digest(text),
            "re-vendor without recomputing the digest: see the file's own "
            "header for the command")

    def test_the_unchanged_census_still_loads_and_still_has_160_rows(self):
        # The control: every refusal above must leave the real file alone.
        self.assertEqual(len(self.spec._load(self.spec._SPEC_PATH)), 160)


class StarImportPublishesTheCensusNamesTests(unittest.TestCase):
    """pf-adversary (round `oghyca`): `import *` read `__dict__`, not
    `__dir__`, so it published this module's imports and none of its
    census names."""

    def test_star_import_hands_out_the_four_lazy_names(self):
        namespace = {}
        exec("from pirateforce_foundation.lua_api.spec import *", namespace)
        for name in ("API_FUNCTIONS", "NAMESPACES", "NAMESPACE_METHODS",
                     "BY_QUALIFIED_NAME"):
            self.assertIn(name, namespace)
        self.assertEqual(len(namespace["API_FUNCTIONS"]), 160)

    def test_star_import_does_not_hand_out_this_module_s_imports(self):
        namespace = {}
        exec("from pirateforce_foundation.lua_api.spec import *", namespace)
        for name in ("Path", "threading", "dataclass"):
            self.assertNotIn(name, namespace)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
