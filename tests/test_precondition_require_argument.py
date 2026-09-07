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

Exactly ONE pull request has died of this shape: #990.  #966 was closed for an
unpinned skip COUNT produced by the ``@X.skip_unless_present()`` decorator, and
the ``bg0008`` / ``bg0010`` rows in ``docs/PYTEST_SKIP_PINS.json`` are shipped
modules that carried no pin - neither contains a ``require`` call at all.  What
the four share is the asymmetric environment, not this defect.  (The "three
pull requests" reading was R384's own error, refuted by pf-adversary and
corrected in round lafdux / R385.)  No lane can catch it from inside its own
round.

Two fences, and they are deliberately different in kind:

  1. ``a_test_instance`` checks the ARGUMENT before ``present`` is consulted,
     so the mistake fails identically on every machine (the tests below).
  2. an AST sweep of the repository refuses ``.require(<arg>)`` written
     LITERALLY inside a ``setUpClass`` or ``setUpModule`` body, so the line
     does not get committed at all, and it reads the file even on modules the
     gate ``--ignore``s, where fence 1 never runs.  MEASURED LIMIT
     (pf-adversary, round 1w9f0q): it does NOT follow a helper called from
     ``setUpClass``, an alias or ``getattr(X, "require")(cls)``, or pytest's
     ``setup_class`` / ``setup_module``.  Fence 1 is what catches those,
     because it judges the argument at the moment of the call.

Neither fence needs a precondition of its own: both read only files that are
in the repository, so they run on every machine, which is the entire point.
"""
from __future__ import annotations

import ast
import inspect
import tempfile
import unittest
from pathlib import Path

import pf_preconditions
from pf_preconditions import a_test_instance

ROOT = Path(__file__).resolve().parents[1]

# Directories swept for the forbidden call.  MEASURED (pf-adversary, round
# 1w9f0q): no file under ``tools`` defines a TestCase today, so sweeping it
# buys no catch right now - the earlier "a test helper lives there" reason was
# wrong.  It stays as a forward guard, because a helper that lands there later
# would be imported by tests and swept by nothing else, and the cost is
# reading files that already have to parse.
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


def swept_files(root: Path = ROOT, dirs=SWEPT_DIRS):
    for name in dirs:
        directory = root / name
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.py")):
            yield path


def sweep_repository(root: Path = ROOT, dirs=SWEPT_DIRS):
    """Return ``(offenders, unparseable)`` over every swept file.

    ``root`` / ``dirs`` default to this repository and exist so a test can
    walk the WHOLE function over a tree it built itself.  Without that, the
    only caller sweeps a repository where every file parses, and both
    ``except`` branches below are dead code (pf-adversary, round 1w9f0q:
    swapping them for ``ZeroDivisionError`` left the suite green).

    A file that does not parse is reported by NAME rather than raised as a
    bare ``SyntaxError`` from inside a sweep: ``tests/fixtures/`` exists and a
    lane may one day commit a deliberately-broken sample there, and an
    exception with no filename in front of it reads as "this fence is broken"
    when it means "that file does not parse".
    """
    offenders = []
    unparseable = []
    for path in swept_files(root, dirs):
        label = path.relative_to(root).as_posix()
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
                self.assertIn("FakeCase", message)
                # Pin the SENTENCE, not a token: "setUp" also occurs in
                # the unconditional half of the message, so asserting it
                # survived deleting the whole remedy (pf-adversary A2).
                self.assertIn("into setUp or into the test method", message)
                # D2 (pf-adversary, round 1w9f0q): the guard used to tell
                # every caller to decorate the class - including the two
                # preconditions that deliberately have no decorator, where
                # following the advice raises AttributeError at import, which
                # is worse than the symptom the guard replaced.  Grade the
                # RECOMMENDATION against the object, so a fifth precondition
                # class is graded the day it lands.
                offers = hasattr(instance, "skip_unless_present")
                if offers:
                    self.assertIn("skip_unless_present() above", message)
                else:
                    self.assertNotIn("skip_unless_present() above", message)

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
        case = FakeCase("not_a_test")
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

    def test_the_sweep_function_reports_files_it_cannot_read_or_parse(self):
        # Drives sweep_repository() itself over a tree with one file that does
        # not parse and one that is not UTF-8, so both except branches are
        # walked by a test instead of being asserted about in pieces.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "broken.py").write_text("def (:\n",
                                                      encoding="utf-8")
            (root / "tests" / "not_utf8.py").write_bytes(b"# \xff\xfe\n")
            # Sorts AFTER both unreadable files on purpose: without it,
            # turning the loop's `continue` into `break` left the whole new
            # suite green while the fence reported zero offenders with one
            # sitting in the tree (pf-adversary A4, round lafdux).
            (root / "tests" / "zz_offender.py").write_text(
                "import unittest\n"
                "class T(unittest.TestCase):\n"
                "    @classmethod\n"
                "    def setUpClass(cls):\n"
                "        SOMETHING.require(cls)\n", encoding="utf-8")
            offenders, unparseable = sweep_repository(root, ("tests",))
        self.assertEqual([(label, scope) for label, _, scope in offenders],
                         [("tests/zz_offender.py", "setUpClass")])
        self.assertEqual(sorted(label for label, _ in unparseable),
                         ["tests/broken.py", "tests/not_utf8.py"])

    def test_the_sweep_function_finds_an_offender_written_to_disk(self):
        # The repository sweep asserts an EMPTY list, so it cannot show that
        # the walk-and-collect half works.  This one can.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "bad.py").write_text(
                "import unittest\n"
                "class T(unittest.TestCase):\n"
                "    @classmethod\n"
                "    def setUpClass(cls):\n"
                "        SOMETHING.require(cls)\n", encoding="utf-8")
            offenders, unparseable = sweep_repository(root, ("tests",))
        self.assertEqual(unparseable, [])
        self.assertEqual([(label, scope) for label, _, scope in offenders],
                         [("tests/bad.py", "setUpClass")])

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
            "require(<arg>) inside %s is the #990 shape (the gate log numbers "
            "are in tests/test_name_colour_sweep.py): it is silent on a "
            "machine that has the precondition and raises TypeError on one "
            "that does not. Move the call into setUp / the test method where a "
            "real case exists, or - if this precondition has one - decorate "
            "the class with @<PRECONDITION>.skip_unless_present().\n  %s"
            % (" or ".join(FORBIDDEN_SCOPES), "\n  ".join(lines))
        )


class FakeCase(unittest.TestCase):
    """A real TestCase subclass, used both as a class and as an instance.

    There is deliberately NO ``runTest`` and no ``test*`` method: with one,
    ``unittest`` falls back to it and banks a permanently-green test that
    asserts nothing (``--collect-only`` counted it, pf-adversary round
    1w9f0q - which is how "13 tests" in R384 was really 12 and one ghost).
    ``__test__ = False`` alone does NOT fix that: it is a pytest convention
    and appears nowhere in ``unittest/loader.py``, so a raising ``runTest``
    turns the green ghost into a RED one under
    ``python -m unittest discover -s tests`` - a red in a file the lane
    running it never touched, which is the exact shape this file exists to
    prevent (pf-adversary A1, round lafdux).  With no such method, BOTH
    runners collect nothing from this class.
    """

    __test__ = False

    def not_a_test(self):
        raise AssertionError(
            "FakeCase is a fixture for the guard tests, not a test itself")


if __name__ == "__main__":
    unittest.main()
