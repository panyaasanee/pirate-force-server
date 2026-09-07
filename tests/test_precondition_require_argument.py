"""``require(cls)`` must die on every machine, and no lane may write it again.

WHY THIS FILE EXISTS (chief round 1w9f0q / R384, COO work order 0641 item 1).

``pf_preconditions`` offers two ways to guard a test that needs evidence a
fresh clone does not carry: the decorator ``@X.skip_unless_present()`` on a
class or method, and the imperative ``X.require(self)`` inside a test body.
The imperative form needs a live ``unittest.TestCase`` because a skip is
raised THROUGH the case.  ``setUpClass(cls)`` has no instance, so
``X.require(cls)`` is wrong - and wrong in the worst possible way:

  * ``require`` only touches its argument when the precondition is ABSENT;
  * a cloud round always has the bridge checked out beside it, so the
    precondition is PRESENT and the line is silent where it was written;
  * on the Windows gate, which checks out this repository alone, the same
    line reaches ``cls.skipTest(reason)`` - an unbound call missing its
    ``self`` - and raises ``TypeError`` inside ``setUpClass``, erroring
    every test in the class.

Three pull requests have been closed by that shape already: #966, #990, and
the ``bg0008`` / ``bg0010`` rows ``docs/PYTEST_SKIP_PINS.json`` recorded
against itself.  No lane can catch it from inside its own round.

Two fences, and they are deliberately different in kind:

  1. ``a_test_instance`` checks the ARGUMENT before ``present`` is consulted,
     so the mistake fails identically on every machine (the tests below).
  2. an AST sweep of the repository refuses ``.require(<arg>)`` anywhere
     inside a ``setUpClass`` or ``setUpModule`` body, so the mistake does not
     get written at all - including through a helper this file cannot type
     check, and including on a machine where fence 1 would stay quiet.

Neither fence needs a precondition of its own: both read only files that are
in the repository, so they run on every machine, which is the entire point.
"""
from __future__ import annotations

import ast
import inspect
import unittest
from pathlib import Path

import pf_preconditions
from pf_preconditions import a_test_instance

ROOT = Path(__file__).resolve().parents[1]

# Directories swept for the forbidden call.  ``tools`` is included because a
# test helper that lives there is imported by tests and would be swept by
# nothing else.
SWEPT_DIRS = ("tests", "tools")

FORBIDDEN_SCOPES = ("setUpClass", "setUpModule")


# ---------------------------------------------------------------------------
# The sweep, as a function so a test can feed it a source string it wrote
# itself.  A scanner nobody has ever seen catch anything is not a fence.
# ---------------------------------------------------------------------------

def class_scoped_require_calls(source: str, label: str):
    """Every ``.require(<arg>)`` written inside a class/module setup body.

    Zero-argument ``.require()`` is a DIFFERENT api in this repository -
    the persistence lane's own resolution object has a ``require()`` that
    returns a value and takes nothing - so only calls that pass an argument are
    reported.  That keeps the
    sweep honest instead of loud.
    """
    found = []
    tree = ast.parse(source, filename=label)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in FORBIDDEN_SCOPES:
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            if not isinstance(sub.func, ast.Attribute):
                continue
            if sub.func.attr != "require":
                continue
            if not (sub.args or sub.keywords):
                continue
            found.append((label, sub.lineno, node.name))
    return found


def swept_files():
    for name in SWEPT_DIRS:
        directory = ROOT / name
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.py")):
            yield path


def sweep_repository():
    """Return ``(offenders, unparseable)`` over every swept file.

    A file that does not parse is reported by NAME rather than raised as a
    bare ``SyntaxError`` from inside a sweep: ``tests/fixtures/`` exists and a
    lane may one day commit a deliberately-broken sample there, and an
    exception with no filename in front of it reads as "this fence is broken"
    when it means "that file does not parse".
    """
    offenders = []
    unparseable = []
    for path in swept_files():
        label = path.relative_to(ROOT).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            unparseable.append((label, str(exc)))
            continue
        try:
            offenders.extend(class_scoped_require_calls(source, label))
        except SyntaxError as exc:
            unparseable.append((label, str(exc)))
    return offenders, unparseable


class ArgumentGuardTests(unittest.TestCase):
    """Fence 1: the argument is judged before the precondition is."""

    def test_every_require_in_the_module_rejects_a_class(self):
        # Derived from the module, not typed out, so a fifth precondition
        # class added later is covered the day it lands rather than the day
        # somebody remembers this file.
        classes = [
            value for value in vars(pf_preconditions).values()
            if inspect.isclass(value) and "require" in vars(value)
        ]
        self.assertGreaterEqual(len(classes), 4, classes)
        for cls in classes:
            with self.subTest(precondition_class=cls.__name__):
                instance = self._some_instance_of(cls)
                with self.assertRaises(TypeError) as caught:
                    instance.require(FakeCase)
                message = str(caught.exception)
                self.assertIn("INSTANCE", message)
                self.assertIn("skip_unless_present", message)
                self.assertIn("FakeCase", message)

    def test_a_present_precondition_still_rejects_a_class(self):
        # The whole defect is that the absent branch is the only one that
        # looked at the argument.  Pick a precondition that IS present here -
        # the repository's own tests directory - and prove the guard fires
        # anyway.  Without this, the fix would only move the crash, not the
        # machine it happens on.
        present = pf_preconditions.Precondition(
            "self_evident", [ROOT / "tests"], "the tests directory",
            "it is committed, so this precondition is true everywhere")
        self.assertTrue(present.present)
        with self.assertRaises(TypeError):
            present.require(FakeCase)

    def test_an_instance_is_accepted_and_returned(self):
        case = FakeCase("runTest")
        self.assertIs(a_test_instance(case, "any_key"), case)

    def test_a_non_case_argument_is_refused_too(self):
        with self.assertRaises(TypeError) as caught:
            a_test_instance(object(), "any_key")
        self.assertIn("any_key", str(caught.exception))

    def test_the_guard_names_the_precondition_key(self):
        with self.assertRaises(TypeError) as caught:
            pf_preconditions.CLIENT_IMAGE.require(FakeCase)
        self.assertIn("client_image", str(caught.exception))

    def _some_instance_of(self, cls):
        name = cls.__name__
        for value in vars(pf_preconditions).values():
            if type(value) is cls:
                return value
        self.fail("no registry entry of type %s to test with" % name)


class SweepTests(unittest.TestCase):
    """Fence 2: the call is not written in a class/module setup at all."""

    def test_no_repository_file_calls_require_in_a_class_setup(self):
        offenders, unparseable = sweep_repository()
        self.assertEqual(unparseable, [], self._unparseable(unparseable))
        self.assertEqual(offenders, [], self._explain(offenders))

    def test_the_sweep_actually_catches_the_shape_it_forbids(self):
        offending = (
            "import unittest\n"
            "from pf_preconditions import BRIDGE_GAMEDATA\n"
            "class T(unittest.TestCase):\n"
            "    @classmethod\n"
            "    def setUpClass(cls):\n"
            "        BRIDGE_GAMEDATA.require(cls)\n"
        )
        found = class_scoped_require_calls(offending, "<synthetic>")
        self.assertEqual([(label, scope) for label, _, scope in found],
                         [("<synthetic>", "setUpClass")])

    def test_setupmodule_is_swept_as_well_as_setupclass(self):
        offending = (
            "from pf_preconditions import BRIDGE_GAMEDATA\n"
            "def setUpModule():\n"
            "    BRIDGE_GAMEDATA.require(None)\n"
        )
        self.assertEqual(len(class_scoped_require_calls(offending, "<m>")), 1)

    def test_a_correct_require_in_setup_or_a_test_is_left_alone(self):
        fine = (
            "import unittest\n"
            "from pf_preconditions import BRIDGE_GAMEDATA\n"
            "class T(unittest.TestCase):\n"
            "    def setUp(self):\n"
            "        BRIDGE_GAMEDATA.require(self)\n"
            "    def test_x(self):\n"
            "        BRIDGE_GAMEDATA.require(self)\n"
        )
        self.assertEqual(class_scoped_require_calls(fine, "<fine>"), [])

    def test_the_zero_argument_require_api_is_not_a_false_positive(self):
        # The persistence lane has an unrelated method of the same name that
        # takes nothing and returns a value (a resolution object's own
        # require()).  Sweeping that would make this fence noisy in the wrong
        # place, and a noisy fence gets turned off.  Its identifier is
        # deliberately NOT written out here: tests/test_persistence_vitals.py
        # greps the whole tree for its call sites to prove that lane is still
        # wired to nothing, and naming it in a comment is enough to go red.
        other = (
            "def setUpModule():\n"
            "    resolution.require()\n"
        )
        self.assertEqual(class_scoped_require_calls(other, "<other>"), [])

    def test_the_sweep_reads_a_real_and_non_empty_set_of_files(self):
        # A sweep over zero files passes for the wrong reason.  Deliberately a
        # FLOOR and not a pinned count: this fence must not need editing every
        # time a lane adds or archives a test file, or it becomes the thing
        # people delete.  Both swept directories must actually contribute.
        files = [p.relative_to(ROOT).parts[0] for p in swept_files()]
        self.assertGreater(len(files), 100, len(files))
        for name in SWEPT_DIRS:
            with self.subTest(directory=name):
                self.assertIn(name, files)
        self.assertIn(Path(__file__).resolve(),
                      [p.resolve() for p in swept_files()])

    def test_a_file_that_does_not_parse_is_named_not_raised(self):
        # Proves the report path exists; the sweep over the real repository
        # asserts the list is empty, which cannot exercise this branch.
        with self.assertRaises(SyntaxError):
            class_scoped_require_calls("def (:\n", "<broken>")
        message = self._unparseable([("tests/fixtures/x.py", "invalid syntax")])
        self.assertIn("tests/fixtures/x.py", message)

    def _unparseable(self, rows):
        return (
            "these files could not be read or parsed, so the require() sweep "
            "could not grade them - fix the file, or move it out of %s if it is "
            "a deliberately broken fixture:\n  %s"
            % (" / ".join(SWEPT_DIRS),
               "\n  ".join("%s: %s" % row for row in rows))
        )

    def _explain(self, offenders):
        lines = ["%s:%d inside %s" % row for row in offenders]
        return (
            "require(<arg>) inside %s is the #966 / #990 / bg0008 shape: it is "
            "silent on a machine that has the precondition and raises TypeError "
            "on one that does not. Decorate the class with "
            "@<PRECONDITION>.skip_unless_present() instead, or move the call "
            "into setUp / the test method where a real case exists.\n  %s"
            % (" or ".join(FORBIDDEN_SCOPES), "\n  ".join(lines))
        )


class FakeCase(unittest.TestCase):
    """A real TestCase subclass, used both as a class and as an instance."""

    def runTest(self):  # pragma: no cover - never executed as a test
        pass


if __name__ == "__main__":
    unittest.main()
