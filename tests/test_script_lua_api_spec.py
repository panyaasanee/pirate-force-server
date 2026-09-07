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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class LoaderRefusesInsteadOfAssertingTests(unittest.TestCase):
    """pf-adversary D13 (round `wn088m`): `python -O` deleted the header guard.

    `_load` used a bare `assert` to check `api_spec.tsv`'s header. `python -O`
    strips `assert` statements outright, so under `-O` a re-vendor that
    reordered the columns would have been parsed happily -- `call_count` and
    `file_count` swapped across all 160 rows, no error anywhere. The guard did
    not merely weaken under `-O`, it ceased to exist.

    These tests run the loader against corrupt copies through a SUBPROCESS
    under `-O`, because that is the only way to prove the statement survives
    optimisation: asserting it in-process proves nothing about a flag this
    process was not started with.
    """

    def _load_under(self, contents: str, optimised: bool):
        """Run `spec._load()` against `contents` in a child interpreter."""
        import shutil
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        from pirateforce_foundation.lua_api import spec

        package_dir = Path(spec.__file__).resolve().parent
        src_root = package_dir.parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "src"
            shutil.copytree(src_root, staged)
            target = (staged / "pirateforce_foundation" / "lua_api"
                      / "api_spec.tsv")
            target.write_text(contents, encoding="ascii")
            argv = [sys.executable]
            if optimised:
                argv.append("-O")
            # The exception is caught by TYPE NAME rather than by importing
            # `vendored` first, because importing anything from `lua_api`
            # runs its `__init__`, which imports `spec` -- so the very import
            # that would name the class is the one that raises. The name and
            # the `RuntimeError` base are both asserted, so this still fails
            # if something else entirely goes wrong.
            argv += ["-c", (
                "import sys; sys.path.insert(0, sys.argv[1])\n"
                "try:\n"
                "    from pirateforce_foundation.lua_api import spec\n"
                "except Exception as exc:\n"
                "    if type(exc).__name__ != 'VendoredDataError':\n"
                "        raise\n"
                "    if not isinstance(exc, RuntimeError):\n"
                "        raise\n"
                "    print('REFUSED', exc)\n"
                "else:\n"
                "    print('ACCEPTED', len(spec.API_FUNCTIONS))\n"
            ), str(staged)]
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
        string count alone is not a pin: it is here underneath four
        subprocess tests, not instead of them.
        """
        import ast
        import inspect
        from pirateforce_foundation.lua_api import spec

        tree = ast.parse(inspect.getsource(spec._load))
        self.assertEqual(
            [node for node in ast.walk(tree) if isinstance(node, ast.Assert)],
            [], "python -O deletes assert statements; _load must raise")
