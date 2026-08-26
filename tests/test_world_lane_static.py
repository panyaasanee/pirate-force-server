"""LANE-A: the check that would have caught ``_refused_line`` on the day.

``world_travel_gate._fire`` called ``_refused_line`` from the day the adversary
pass of round 4fhdxv asked for those two refusals, and the function was never
written.  Both branches raised ``NameError`` inside ``observe`` - the one method
whose contract is that it never raises on a report, because a raise there does
not refuse a departure, it kills the connection's frame handling.  It survived a
full adversary pass and 80 tests because every test walked a player whose
durable row carried ``scene_seq`` 0, and 0 is the value that skips the guard.

The tests that catch it now are the right tests and they exist.  This one
catches the SHAPE of it - a name that is called and never defined - without
needing anybody to think of the walk that reaches it first.

SCOPE: LANE-A's own modules only, ``world_*.py``.  The same sweep was run over
all 58 modules of the package in round e7q6yy and came back clean, so this is
the only lane that has ever carried one; but a check that fails another lane's
round is not this lane's to install, and it was offered to the chief instead.
"""

import ast
import builtins
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PACKAGE = ROOT / "src" / "pirateforce_foundation"
_MODULE_GLOBALS = {"__file__", "__name__", "__doc__", "__package__", "__spec__"}


def _undefined_names(path: Path) -> list[str]:
    """Names loaded in this module that nothing in it ever binds.

    Deliberately simple: it does not resolve wildcard imports (this package has
    none) and it treats any binding anywhere in the file as visible, so it
    cannot flag a name that is merely used before assignment.  That makes it
    blind to some real bugs and incapable of a false positive on a working
    module, which is the trade a gate on every lane module has to make.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defined = set(dir(builtins)) | set(_MODULE_GLOBALS)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            defined.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                defined.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.arg):
            defined.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            defined.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            defined.update(node.names)
    used = {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    return sorted(used - defined)


class WorldLaneStaticTests(unittest.TestCase):
    def setUp(self):
        self.modules = sorted(PACKAGE.glob("world_*.py"))
        self.assertTrue(self.modules, "lane A has modules")

    def test_no_lane_module_calls_a_name_nothing_defines(self):
        for path in self.modules:
            with self.subTest(path.name):
                self.assertEqual(_undefined_names(path), [])

    def test_the_checker_actually_catches_the_bug_it_was_written_for(self):
        """A guard nobody has watched refuse anything is not a guard.

        This reproduces the exact shape of the defect - a helper called from a
        refusal branch and never written - in a temporary file, so the check
        above is known to be capable of failing.
        """
        sample = ROOT / "tests" / "_undefined_name_sample.py"
        sample.write_text(
            "def _fire(row):\n"
            "    if row < 0:\n"
            "        return _refused_line(row)\n"
            "    return row\n",
            encoding="utf-8",
        )
        try:
            self.assertEqual(_undefined_names(sample), ["_refused_line"])
        finally:
            sample.unlink()


if __name__ == "__main__":
    unittest.main()
