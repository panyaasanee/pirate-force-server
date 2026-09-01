"""Gate 2 is wired to ``bag_admission.may_enter_world`` -- COO-DECISION
20260829_0441.

The predicate itself is enumerated in ``tests/test_bag_admission.py`` (both
goldens x every item x every slot, through the three real ``inventory``
mutators).  This file asserts the ONE thing that file no longer can, now that
its anti-wiring guard is gone: that
``session.FoundationSession.select_and_start`` -- the production character
select path -- actually asks that predicate, that the answer changes what the
player gets, and that the refusal prints the token an operator needs.

The bags are NOT assembled here.  The admitted one is the return value of the
real ``mob_pickup.place_in_bag``; the refused ones are the return values of
the real ``inventory`` mutators and the shipped ``HYPOTHESIZED_V111_SLOT2``
constant.  A test that hand-built the bag it then admits would prove that the
predicate agrees with this file's idea of a pickup, not that a pickup gets in.

WHAT THIS DOES NOT PROVE.  The bag reaches ``select_and_start`` through a
lifecycle stub, so this file pins the GATE and not the round trip.
~~because nothing writes an acquired row to the database yet -- ``store.py``
has no INSERT and does not advance ``next_item_identity``~~ -- that ticket
(``STORE-INSERT-001``) LANDED in round 4gqnwm, and the round trip through a
real store now has its own file,
``tests/test_store_acquired_item_insert.py``.  What is still missing for M5
is the call site (``GT-124``): ``runtime.py`` does not call
``mob_pickup.dispatch_pickup_request``, so no line here or there should be
quoted as evidence that a PLAYER can pick anything up.
"""
from pathlib import Path
import ast
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    bag_admission, mob_loot, mob_pickup,
)
from pirateforce_foundation.inventory import (  # noqa: E402
    HYPOTHESIZED_V111_SLOT2_BACKPACK,
    INITIAL_BACKPACK,
    move_known_item_to_free_slot,
)
from pirateforce_foundation.session import FoundationSession  # noqa: E402

ITEM = 2400046  # the roster's most common drop, as tests/test_mob_pickup.py uses
MOB = 0x2068
KILLER = 0x750059


def a_drop():
    return mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE, ITEM, 1,
        mob_loot.as_wire_float(10.0),
        mob_loot.as_wire_float(20.0),
        mob_loot.as_wire_float(30.0),
        MOB, KILLER,
    )


def _imports_bag_admission(path):
    """True when this module actually imports ``bag_admission``.

    Both spellings the package uses: ``from . import bag_admission`` and
    ``from .bag_admission import ...`` (and the absolute forms of each).
    """
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").endswith("bag_admission"):
                return True
            if any(alias.name == "bag_admission" for alias in node.names):
                return True
        elif isinstance(node, ast.Import):
            if any(
                alias.name.split(".")[-1] == "bag_admission"
                for alias in node.names
            ):
                return True
    return False


#: ROUND 78zy6l, after pf-adversary.  ``.txt`` WAS in this set for one draft
#: and is struck: the argument written for it ("prose") was never made -- and
#: in this repository a ``.txt`` is not inert prose at all, it is
#: ``docs/.round_claim_*.txt`` (a round lock) and ``pf_pytest_excluded.txt``
#: (a gate artifact).  Only markdown is cleared by rule.
#: Suffixes of files that cannot call anything.  ROUND 78zy6l (LANE-B).
#: The repo-wide scan at the bottom of this file greps the WHOLE tracked
#: tree for the module's name, so a round file or a letter that merely
#: MENTIONS the gate turned the Windows gate red and cost the whole round:
#: run 33522539202 on pull request #511, whose only change was a new test
#: file for inventory.py that named two sibling test files in its
#: docstring.  Markdown is not executed by anything in this repository (no
#: doctest runner, no literate step -- grepped for one before this line was
#: written), so prose is cleared by rule here instead of by another
#: after-the-fact allowlist entry every time somebody writes the name down.
PROSE_SUFFIXES = frozenset({".md"})

#: Every suffix python actually runs on Windows.  ``.pyw`` is a real entry
#: point and ``.pyi`` is read by tooling; matching only ``".py"`` sent both
#: down the "not python" branch, whose reason text tells the next reviewer
#: to allowlist them -- the wrong action for a file the helper can read.
PYTHON_SUFFIXES = frozenset({".py", ".pyw", ".pyi"})

#: ROUND 78zy6l, after pf-adversary.  Names whose presence anywhere in a
#: file means a STRING in that file can still become a lookup.  The first
#: draft trusted a docstring unconditionally, and pf-adversary measured the
#: hole in one move: make the module docstring BE the module path and hand
#: ``__doc__`` to ``import_module``.  The token never appears as an
#: identifier and never appears outside a docstring, and the file reaches
#: the gate.  So a docstring is prose only in a file that has no machinery
#: to turn a string into a module; a file that has that machinery has to
#: earn an allowlist entry even for prose.  The cost is a false positive on
#: a file that uses ``getattr`` for ordinary work AND names the predicate in
#: prose; that fails closed and is one allowlist line, which is the side to
#: be wrong on.
DYNAMIC_LOOKUP_NAMES = frozenset({
    "__doc__", "__import__", "import_module", "importlib", "exec", "eval",
    "getattr", "modules", "load_module", "spec_from_file_location",
})


def _names_bag_admission_as_code(path):
    """The reason a python file outside the package is a CALLER, or None.

    ROUND 78zy6l.  Returns ``None`` when every occurrence of the token in
    the file is text -- a docstring, a comment -- and a short reason string
    when the file actually reaches the predicate.  The two rules are the
    ones the package-level mention scan above already argued for and
    already hardened against pf-adversary, applied to a file outside the
    package:

      * the token appears in the AST as an IDENTIFIER (an import, an
        attribute hop, an argument, a definition), or
      * the token appears in a STRING and the file also carries machinery
        that can turn a string into a module (:data:`DYNAMIC_LOOKUP_NAMES`)
        -- ``import_module``, ``getattr``, ``sys.modules``, ``exec``, or
        ``__doc__``.

    TWO DRAFTS WERE MEASURED WRONG BY pf-adversary BEFORE THIS ONE, and both
    scars are why the rule reads as it does:

      1. "a string reaching a call or a subscript" walks past
         ``NAME = "pirateforce_foundation.bag_admission"`` bound first and
         imported three lines later.
      2. "any string that is not a docstring" walks past a file whose
         module docstring IS the module path, imported with
         ``import_module(__doc__)`` -- and it also turned an assertion
         MESSAGE naming a sibling test file into a red gate, which is the
         exact failure (pull request #511) this helper exists to end.

    A file with no such machinery cannot reach the predicate through text,
    so its prose -- docstring, assertion message, a list of filenames, a
    ``help=`` string -- is prose.  A comment is not in the AST at all.
    """
    try:
        # utf-8-sig, not utf-8: a BOM (Notepad, Windows PowerShell 5
        # ``Set-Content -Encoding utf8``) is invisible to python's own
        # importer and would otherwise be reported here as "unparseable".
        source = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return "unreadable (%s)" % (exc.__class__.__name__,)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # NO SILENT PASS.  A file this helper cannot parse has not been
        # shown to be prose, so it stays flagged and a human reads it.
        return "unparseable python"
    if _imports_bag_admission(path):
        return "imports bag_admission"
    machinery = None
    for node in ast.walk(tree):
        identifiers = {
            getattr(node, "id", None),
            getattr(node, "attr", None),
            getattr(node, "arg", None),
            getattr(node, "name", None),
        }
        if "bag_admission" in identifiers:
            return "names bag_admission as an identifier, not as prose"
        if machinery is None:
            found = identifiers & DYNAMIC_LOOKUP_NAMES
            if found:
                machinery = sorted(found)[0]
    if machinery is None:
        return None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "bag_admission" in node.value
        ):
            return (
                "carries the module's name in a string, in a file that also "
                "uses %r -- a string is a lookup away from the gate there"
                % (machinery,)
            )
    return None


def _classify_repo_wide_hits(root, hits, allowed):
    """Every grep hit that still has to be explained, with its reason.

    ROUND 78zy6l.  Split out of the test below because pf-adversary
    measured that the two lines which ACT on a hit had never executed once:
    three mutants (clear every python file; put every suffix in
    ``PROSE_SUFFIXES``; grep for a token that does not exist) all left the
    file green.  A helper can be driven with planted files; the live scan
    cannot.
    """
    elsewhere = []
    for line in hits:
        if line in allowed:
            continue
        suffix = Path(line).suffix.lower()
        if suffix in PROSE_SUFFIXES:
            continue
        if suffix in PYTHON_SUFFIXES:
            reason = _names_bag_admission_as_code(root / line)
            if reason is None:
                continue
            elsewhere.append("%s: %s" % (line, reason))
            continue
        elsewhere.append(
            "%s: not python and not prose, and not on the allowlist" % (line,)
        )
    return sorted(elsewhere)


def _repo_wide_hits(root):
    """Every tracked file naming the predicate, or a loud failure.

    ``-z`` and ``core.quotePath=false`` because the default quotes a path
    with a non-ASCII byte (``"docs/caf\\303\\251_x.py"``), and a quoted path
    then misses its own suffix and is reported as a data file.  The return
    code is checked because ``git grep`` outside a repository exits 128 with
    an empty stdout, which the old code read as "nothing calls it".
    """
    tracked = subprocess.run(
        ["git", "-c", "core.quotePath=false", "grep", "-lz",
         "bag_admission", "--", "."],
        cwd=root, capture_output=True, text=True,
    )
    if tracked.returncode not in (0, 1):
        raise AssertionError(
            "git grep failed (exit %s) -- an empty result from a broken "
            "grep is not evidence that nothing calls the predicate: %s"
            % (tracked.returncode, tracked.stderr.strip())
        )
    return [line for line in tracked.stdout.split("\0") if line]


class StubProjector:
    """Records what the session handed the client, if it got that far."""

    def __init__(self):
        self.started_with = []

    def start_game(self, selected, *, backpack):
        self.started_with.append((selected, backpack))
        return b"start-game-frame"


class StubLifecycle:
    """The three calls ``select_and_start`` makes before gate 2, and no
    more: ``select``, ``backpack``, and the counter read."""

    def __init__(self, backpack):
        self._backpack = backpack

    def login(self, login_name):
        return 1, "session-1", []

    def select(self, session_id, selector):
        return ("character", selector)

    def backpack(self, session_id, selected):
        return self._backpack

    def backpack_issued_through(self, session_id, selected):
        # Route 1 (COO-DECISION 20260829_0848) threads the identity counter
        # into gate 2.  The honest stub value is the bag's own highest
        # identity -- the counter as the real store would hold it after
        # everything this bag carries was issued -- so these tests keep
        # measuring the SHAPE rule, not the ceiling (the ceiling's tests
        # live in tests/test_bag_admission.py::CounterCeilingTests).
        try:
            return max(item.identity for item in self._backpack.items)
        except (TypeError, AttributeError, ValueError):
            # A malformed value has no honest counter; gate 2 refuses it on
            # shape whatever this number is.
            return 0


def enter(backpack, *, allow_hypothesized_item_move=False):
    """Run the real gate.  Returns ``(session, stderr_text, error_or_None)``."""
    projector = StubProjector()
    session = FoundationSession(
        StubLifecycle(backpack), projector, "gate2-user",
        allow_hypothesized_item_move=allow_hypothesized_item_move,
    )
    captured, error = io.StringIO(), None
    with redirect_stderr(captured):
        try:
            session.select_and_start(0)
        except PermissionError as exc:
            error = exc
    return session, captured.getvalue(), error


class Gate2ThreadsTheRealCounter(unittest.TestCase):
    """The gate acts on the number the STORE holds, not on a constant.

    Route 1 (COO-DECISION 20260829_0848): ``session.select_and_start`` reads
    ``store.backpack_issued_through`` and threads it into
    ``may_enter_world``.  GATE-WALK (COO letter 0742): the branch walked is
    ``_classify_against``'s ceiling refusal, reached through the REAL
    session call.  Mutation kill: hardcode the threaded value in
    ``session.py``, or stop reading the store there, and the refusal below
    becomes an admission.
    """

    def test_a_counter_below_the_acquired_row_refuses_the_relog(self):
        acquired, item = mob_pickup.place_in_bag(INITIAL_BACKPACK, a_drop())
        lifecycle = StubLifecycle(acquired)
        # The store says it never issued this row's identity: the counter
        # still stands at the golden's seed.
        seed = max(row.identity for row in INITIAL_BACKPACK.items)
        self.assertGreater(item.identity, seed)
        lifecycle.backpack_issued_through = lambda sid, sel: seed
        session = FoundationSession(
            lifecycle, StubProjector(), "gate2-user",
            allow_hypothesized_item_move=False,
        )
        captured, error = io.StringIO(), None
        with redirect_stderr(captured):
            try:
                session.select_and_start(0)
            except PermissionError as exc:
                error = exc
        self.assertIsNotNone(
            error,
            "gate 2 admitted a row the store says it never issued -- the "
            "session is not threading the real counter",
        )
        self.assertEqual(len(session.projector.started_with), 0)
        self.assertIn(
            "reason=" + bag_admission.REASON_ACQUIRED_IDENTITY_NOT_ISSUED,
            captured.getvalue(),
            "the console line must name the counter refusal the gate made",
        )


class Gate2AdmitsAnAcquiredRow(unittest.TestCase):
    def test_a_bag_a_real_pickup_produced_enters_the_world(self):
        acquired, _item = mob_pickup.place_in_bag(INITIAL_BACKPACK, a_drop())
        self.assertGreater(len(acquired.items), len(INITIAL_BACKPACK.items))

        session, stderr, error = enter(acquired)

        self.assertIsNone(error, "gate 2 refused a bag mob_pickup produced")
        self.assertEqual(session.backpack, acquired)
        self.assertEqual(len(session.projector.started_with), 1)
        # The refusal token is for refusals.  An admitted bag printing one
        # would train an operator to ignore the line that matters.
        self.assertNotIn("BAG_ADMISSION", stderr, stderr)

    def test_a_golden_bag_still_enters_the_world(self):
        session, stderr, error = enter(INITIAL_BACKPACK)

        self.assertIsNone(error)
        self.assertEqual(session.backpack, INITIAL_BACKPACK)
        self.assertNotIn("BAG_ADMISSION", stderr, stderr)


class Gate2StillRefusesTheGovernedFamily(unittest.TestCase):
    def test_the_shipped_hyp_pf_008_post_state_is_still_refused(self):
        _session, stderr, error = enter(HYPOTHESIZED_V111_SLOT2_BACKPACK)

        self.assertIsInstance(error, PermissionError)
        self.assertIn("HYP-PF-008", str(error))
        # The whole point of the printed line: the operator sees WHICH
        # refusal this was, beside a message that names one hypothesis.
        self.assertIn("BAG_ADMISSION", stderr, stderr)
        self.assertIn("verdict=", stderr)

    def test_a_moved_item_from_the_real_mutator_is_still_refused(self):
        item = INITIAL_BACKPACK.items[0]
        moved, _identity = move_known_item_to_free_slot(
            INITIAL_BACKPACK, item.identity, 7,
        )

        _session, stderr, error = enter(moved)

        self.assertIsInstance(error, PermissionError)
        self.assertIn("BAG_ADMISSION", stderr, stderr)

    def test_the_opt_in_still_admits_the_governed_state(self):
        session, _stderr, error = enter(
            HYPOTHESIZED_V111_SLOT2_BACKPACK,
            allow_hypothesized_item_move=True,
        )

        self.assertIsNone(error, "the HYP-PF-008 opt-in lane regressed")
        self.assertEqual(session.backpack, HYPOTHESIZED_V111_SLOT2_BACKPACK)

    def test_a_malformed_bag_is_refused_even_with_the_opt_in_on(self):
        """The one deliberate difference from the pre-wiring condition.

        The old second term was a bare ``or allow_hypothesized_item_move``,
        so with the opt-in on gate 2 admitted a value that is not a Backpack
        at all.  Gate 1 raises on such a value first in production, so this
        is unreachable there -- which is exactly why it needs a test here.
        """
        _session, stderr, error = enter(
            "not a backpack", allow_hypothesized_item_move=True,
        )

        self.assertIsInstance(error, PermissionError)
        self.assertIn(
            f"verdict={bag_admission.VERDICT_MALFORMED}", stderr, stderr,
        )
        self.assertIn(
            f"reason={bag_admission.REASON_MALFORMED}", stderr, stderr,
        )


class TheConsoleLineIsAsciiOnly(unittest.TestCase):
    """The bridge console is cp874.  A non-ASCII byte kills the report."""

    def test_every_refusal_line_encodes_as_ascii(self):
        for label, bag in (
            ("hyp-008", HYPOTHESIZED_V111_SLOT2_BACKPACK),
            ("malformed", object()),
        ):
            with self.subTest(label):
                _session, stderr, error = enter(bag)
                self.assertIsInstance(error, PermissionError)
                # Assert the line is THERE before asserting it is ASCII.  ""
                # encodes as ASCII, so without this the test is green about a
                # line that was never emitted -- measured: it survived the
                # mutant that deletes the print entirely.
                self.assertIn("BAG_ADMISSION", stderr, stderr)
                stderr.encode("ascii")


class TheDiagnosticNeverAltersDispatch(unittest.TestCase):
    """A refusal must leave this method as a PermissionError, always.

    pf-adversary measured three degraded stderr states.  TWO of them changed
    what leaves this method, and the wrapper closes both: a closed stream
    raised ValueError (which runtime.py then reports as
    BACKPACK_LOAD_REFUSED -- the misattribution the line exists to prevent),
    and a stream whose write raises BrokenPipeError escaped both of
    runtime.py's handlers and unwound the listener thread in silence.

    The third, ``sys.stderr is None`` (pythonw, no console), never raised:
    ``print(file=None)`` writes to stdout instead.  So the test below cannot
    kill a mutant that removes the wrapper, and it is kept only as the
    statement that this state still raises PermissionError.  The token
    landing in the run's .out.txt rather than .err.txt on such a boot is a
    KNOWN, UNFIXED misroute -- the durable fix is an event beside the print,
    which this round did not do.
    """

    def _refuse_with_stderr(self, stream):
        session = FoundationSession(
            StubLifecycle(HYPOTHESIZED_V111_SLOT2_BACKPACK),
            StubProjector(), "gate2-user",
        )
        saved = sys.stderr
        sys.stderr = stream
        try:
            with self.assertRaises(PermissionError):
                session.select_and_start(0)
        finally:
            sys.stderr = saved

    def test_a_closed_stderr_still_raises_permission_error(self):
        closed = io.StringIO()
        closed.close()
        self._refuse_with_stderr(closed)

    def test_stderr_set_to_none_still_raises_permission_error(self):
        self._refuse_with_stderr(None)

    def test_a_stream_that_raises_on_write_still_raises_permission_error(self):
        class Hostile:
            def write(self, _text):
                raise BrokenPipeError("downstream is gone")

            def flush(self):
                raise BrokenPipeError("downstream is gone")

        self._refuse_with_stderr(Hostile())


class OnlyTheCharacterSelectPathAsksThisPredicate(unittest.TestCase):
    """The property the deleted anti-wiring guard used to carry.

    That test asserted the caller set was EMPTY; wiring makes that false.
    What is not false, and what nothing else pins, is that the caller set is
    KNOWN.  Without this, a later round can put may_enter_world inside gate 1
    (store._load_backpack) or gate 3 (inventory.make_backpack_attr) with the
    whole suite green, quietly turning a loud structural raise into a quiet
    refusal and staling every gate table in the tree again.
    """

    def test_session_py_is_the_only_module_in_the_package_that_calls_it(self):
        root = Path(bag_admission.__file__).parent
        # rglob, not glob: gm/ and lane_hooks/ are where a lane registration
        # would most plausibly live, and the non-recursive form never opens
        # them.  The count pin keeps this scan honest -- a glob that silently
        # stopped matching would otherwise report an empty caller list as a
        # clean one.
        package = sorted(
            path for path in root.rglob("*.py")
            if path.name != "bag_admission.py"
            and "__pycache__" not in path.parts
        )
        self.assertGreater(len(package), 90, len(package))
        # BOTH ROUTES, and the substring scan is the load-bearing one.  The
        # first draft of this test kept only the AST/import check, and
        # pf-adversary defeated it twice in minutes -- once with
        # importlib.import_module inside inventory.make_backpack_attr, once by
        # hopping through session's own module attribute -- both green.  That
        # is the same trade tests/test_loot_roll.py::
        # test_the_lane_is_not_reachable_from_production_dispatch already made
        # and already undid: the scan comes back, with named and counted
        # exemptions for the files whose PROSE mentions the module, and the
        # AST check stays as a second route to the same fact.
        mentions_allowed = {
            "runtime.py",  # a comment naming the gate, no call
            # Added by LANE-B, round 149wbp, on chief's R222 letter item 3.
            # mob_pickup.py's THE WALL section and its
            # GOVERNED_BAG_ALLOWLIST_* constants named gate 2 as
            # is_unmoved_baseline and shipped that as report DATA; the
            # correction has to name the predicate that replaced it or it
            # is not a correction.  Prose and a constant string only --
            # mob_pickup.py imports nothing from bag_admission and calls
            # nothing in it, which the importers assertion above still
            # proves independently.
            "mob_pickup.py",
        }
        # AN EXEMPTION IS FOR PROSE, AND HERE THAT IS ENFORCED, NOT TRUSTED.
        # Naming a file in ``mentions_allowed`` used to switch the substring
        # scan off for it entirely -- so a caller could hide in an exempted
        # file exactly the way pf-adversary got in before, and this round's
        # own adversary pass did: a ``_sneaky_gate`` in mob_pickup.py doing
        # ``importlib.import_module("...bag_admission").may_enter_world(bag)``
        # is invisible to the import AST check by construction, and the
        # exemption made it invisible to the scan too.  So an exempted file's
        # mentions must all be INERT: the token may appear in a docstring, a
        # comment or a string constant, never as code -- no Name, no
        # attribute base, and no dynamic-import machinery anywhere in it.
        # THE FIRST DRAFT OF THIS LOOP WAS DEFEATED, AND THE ATTACK IS THE
        # REASON IT IS SHAPED THIS WAY.  It rejected ``bag_admission`` as a
        # bare Name, as an Attribute BASE, and import_module/__import__
        # calls.  pf-adversary walked through all three with
        # ``session.bag_admission.may_enter_world(bag, ...)`` -- a real new
        # production caller of the gate-2 predicate, full suite green -- and
        # ``sys.modules[...]`` and ``getattr(session, "bag_admission")``
        # walk through the same gap.  So the test is now: the token may not
        # appear ANYWHERE in an exempted file's AST, at any depth, in any
        # form.  Prose, comments and string constants are what an exemption
        # is for; they are not in the AST as identifiers.
        for name in sorted(mentions_allowed):
            path = root / name
            # NO SILENT SKIP.  The first draft continued past a missing
            # file, so renaming an exempted module would have evaporated its
            # enforcement with nothing going red.
            self.assertTrue(
                path.exists(),
                f"{name} is exempted from the mention scan but does not "
                "exist -- remove the exemption or fix the name",
            )
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                identifiers = {
                    getattr(node, "id", None),
                    getattr(node, "attr", None),
                    getattr(node, "arg", None),
                    getattr(node, "name", None),
                }
                self.assertNotIn(
                    "bag_admission", identifiers,
                    f"{name} names bag_admission as CODE, not prose -- an "
                    "exemption from the mention scan is for text, and this "
                    "is the attribute-hop route the scan exists to catch",
                )
                # THE STRING ROUTE.  An identifier check alone still leaves
                # ``import_module("...bag_admission")``,
                # ``getattr(session, "bag_admission")`` and
                # ``sys.modules["...bag_admission"]``, where the token is a
                # string constant, not a name.  Banning those CALLS by name
                # was the first attempt and it was too wide -- mob_pickup.py
                # uses ``getattr`` for ordinary work -- so what is banned is
                # the token reaching a call or a subscript, whoever the
                # callee is.  A docstring or a comment, which is what an
                # exemption is for, reaches neither.
                if isinstance(node, (ast.Call, ast.Subscript)):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Constant) and isinstance(
                            child.value, str
                        ):
                            self.assertNotIn(
                                "bag_admission", child.value,
                                f"{name} passes the module's name into a "
                                "call or a subscript -- a dynamic lookup "
                                "that would reach the gate unseen",
                            )
        importers = sorted(
            str(path.relative_to(root)) for path in package
            if _imports_bag_admission(path)
        )
        mentioners = sorted(
            str(path.relative_to(root)) for path in package
            if "bag_admission" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(
            importers, ["session.py"],
            "the set of modules that import bag_admission changed.  Gate 2 is "
            "the only gate this predicate was reviewed for; adding it to "
            "another gate needs its own review and its own round.",
        )
        self.assertEqual(
            sorted(set(mentioners) - mentions_allowed), ["session.py"],
            "a module names bag_admission without importing it -- either a "
            "runtime lookup that dodges the import check (importlib, an "
            "attribute hop through another module), or new prose that needs "
            "a named exemption on the line above.",
        )
        self.assertEqual(len(mentions_allowed), 2)

    def test_nothing_outside_the_package_calls_it_either(self):
        """The repo-wide half of the deleted guard: tools/, current/, entrypoints."""
        hits = _repo_wide_hits(ROOT)
        # A LOWER BOUND, not decoration.  pf-adversary changed the grep
        # pattern to a token that appears nowhere and the file stayed
        # green: an empty scan proves nothing and must not read as proof.
        self.assertGreaterEqual(
            len(hits), 8,
            "the repo-wide grep found almost nothing -- the pattern, the "
            "working directory or the index is wrong, not the repository",
        )
        allowed = {
            "src/pirateforce_foundation/bag_admission.py",
            "src/pirateforce_foundation/session.py",
            "src/pirateforce_foundation/runtime.py",
            "tests/test_bag_admission.py",
            "tests/test_gate2_bag_admission_wiring.py",
            # Added by LANE-B, round ua236k.  COO-DECISION 20260829_0441
            # item 2 ordered the interim rule's expiry written into the
            # module; this file is the test that makes that expiry fail a
            # run instead of reading the same forever.  It is a test OF
            # bag_admission, which is what this allowlist is for -- not a
            # caller reaching for the predicate from outside the package.
            "tests/test_bag_admission_expiry.py",
            # Added by chief, round 4gqnwm (STORE-INSERT-001).  The store now
            # writes a picked-up row, and the one thing that write has to be
            # true for is that the bag it produces GETS THROUGH GATE 2 after a
            # relog -- so that file reads the verdict from this predicate
            # rather than asserting its own idea of admissibility.  A test OF
            # bag_admission's outcome; not a caller reaching for the predicate
            # from outside the package.
            #
            # THIS ENTRY WAS ADDED AFTER THE FACT, AND THAT IS THE LESSON.
            # `git grep` searches the INDEX, so while the new file was
            # untracked this check could not see it and the whole suite ran
            # green; the failure appeared only at `git add`.  A new test file
            # that imports bag_admission must be staged before its own suite
            # run is worth anything.
            "tests/test_store_acquired_item_insert.py",
            # Added by LANE-B, round 149wbp (chief's R222 letter item 3).
            # mob_pickup.py names the predicate that replaced
            # is_unmoved_baseline in its corrected THE WALL prose and in
            # GOVERNED_BAG_ALLOWLIST_OWNER; test_mob_pickup.py asserts the
            # gate itself rather than a module constant that was True by
            # assignment.  ~~"Neither is a new caller from outside the
            # package"~~ IS STRUCK AS FALSE OF ONE OF THE TWO (pf-adversary):
            # tests/test_mob_pickup.py DOES import bag_admission and DOES
            # call may_enter_world, deliberately -- that is the one
            # assertion in its wall test that can actually fire.  It is a
            # TEST calling the predicate, which is what this allowlist is
            # for; it is not production reaching the gate from a second
            # place.  mob_pickup.py itself has no import of it at all, and
            # the inert-mention loop above now proves that at AST level
            # rather than asserting it here.
            "src/pirateforce_foundation/mob_pickup.py",
            "tests/test_mob_pickup.py",
            # The pin document mob_pickup.pin_document GENERATES; it carries
            # nonclaim 9's text verbatim, so it names the predicate for the
            # same reason the module does.  Regenerated, never hand-edited.
            "scenarios/combat_pickup_001.json",
            "docs/FUNCTIONAL_COVERAGE.json",
            # Added by LANE-B, round uq2lxw.  mob_pickup_persist joins the
            # pickup path to the store's write, and the one thing that write
            # has to be true for is the same one STORE-INSERT-001's file
            # names above: the bag it produces GETS THROUGH GATE 2 after a
            # relog.  So the test reads the verdict from this predicate
            # instead of asserting its own idea of admissibility.  A test OF
            # bag_admission's outcome; the production module
            # (mob_pickup_persist.py) does not import it and is not listed.
            #
            # AND THIS ENTRY IS THE SCAR ABOVE, REPEATED IN THE ROUND THAT
            # WAS WARNED BY IT.  The paragraph two entries up says `git grep`
            # searches the INDEX, so an untracked new test file is invisible
            # here and the suite runs green until `git add`.  That is exactly
            # what happened: round uq2lxw measured 4483 green with this file
            # untracked, committed it, and HEAD was red.  Staged first, then
            # measured, from now on.
            "tests/test_mob_pickup_persist.py",
        }
        # ROUND 78zy6l.  Everything past the allowlist used to be a failure
        # by itself, which made the check fire on files that cannot call
        # anything (a round file naming the gate in prose) and on python
        # files whose only mention is a docstring.  That cost two rounds --
        # the scar two entries up, and pull request #511, closed red for a
        # docstring.  What is asked now is what the test's own name claims:
        # does anything outside the package CALL it.  Prose is cleared by
        # suffix, a python file by the AST rules this file already uses on
        # the package itself; a real caller still has to earn an allowlist
        # entry above, with its reason written next to it.
        elsewhere = _classify_repo_wide_hits(ROOT, hits, allowed)
        self.assertEqual(elsewhere, [], elsewhere)


class ProseIsNotACallerButEveryDynamicRouteStillIs(unittest.TestCase):
    """ROUND 78zy6l.  Pins the rule the repo-wide scan now applies.

    The scan above is only as good as the line it draws between a file that
    NAMES the predicate and a file that REACHES it.  Each test here writes a
    real python file and asks the helper, so the line is measured rather
    than asserted about; the last one asks it about a file that actually
    ships in this repository.
    """

    MODULE = "bag_admission"

    def verdict(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subject.py"
            path.write_text(source, encoding="utf-8")
            return _names_bag_admission_as_code(path)

    def test_a_docstring_and_a_comment_are_not_a_caller(self):
        source = (
            '"""Prose that names %s the way a round file does."""\n'
            "# and a comment that names %s too\n"
            "VALUE = 1\n" % (self.MODULE, self.MODULE)
        )
        self.assertIsNone(self.verdict(source))

    def test_prose_outside_a_docstring_is_still_prose(self):
        """THE PULL REQUEST #511 CLASS, and a draft of this closed it wrong.

        Naming a sibling test file in an assertion message, a list of paths
        or a ``help=`` string is what a test file does.  A draft that
        cleared only docstrings turned every one of those red -- the same
        lost round, moved one line over.
        """
        source = (
            "import unittest\n"
            "DOCS = [\"tests/test_%s.py\"]\n"
            "class T(unittest.TestCase):\n"
            "    def test_x(self):\n"
            '        self.assertEqual(1, 1, "see tests/test_%s.py")\n'
            % (self.MODULE, self.MODULE)
        )
        self.assertIsNone(self.verdict(source))

    def test_a_module_docstring_handed_to_import_module_is_a_caller(self):
        """pf-adversary's own payload against the draft before this one."""
        source = (
            '"""pirateforce_foundation.%s"""\n'
            "import importlib\n"
            "_GATE = importlib.import_module(__doc__)\n" % (self.MODULE,)
        )
        self.assertIsNotNone(self.verdict(source))

    def test_a_docstring_payload_reached_by_exec_is_a_caller(self):
        source = (
            '"""from pirateforce_foundation import %s"""\n'
            "exec(__doc__)\n" % (self.MODULE,)
        )
        self.assertIsNotNone(self.verdict(source))

    def test_a_class_docstring_payload_is_a_caller(self):
        source = (
            "import importlib\n"
            "class Gate:\n"
            '    """pirateforce_foundation.%s"""\n'
            "GATE = importlib.import_module(Gate.__doc__)\n" % (self.MODULE,)
        )
        self.assertIsNotNone(self.verdict(source))

    def test_a_bom_does_not_turn_prose_into_unparseable(self):
        """Windows writes BOMs; python imports such a file without blinking."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subject.py"
            path.write_text(
                '"""prose naming %s."""\nVALUE = 1\n' % (self.MODULE,),
                encoding="utf-8-sig",
            )
            self.assertIsNone(_names_bag_admission_as_code(path))

    def test_an_import_is_a_caller(self):
        source = "from pirateforce_foundation import %s\n" % (self.MODULE,)
        self.assertIsNotNone(self.verdict(source))

    def test_an_attribute_hop_is_a_caller(self):
        source = (
            "import pirateforce_foundation as pf\n"
            "pf.%s.may_enter_world(None)\n" % (self.MODULE,)
        )
        self.assertIsNotNone(self.verdict(source))

    def test_a_dynamic_import_by_string_is_a_caller(self):
        source = (
            "import importlib\n"
            'importlib.import_module("pirateforce_foundation.%s")\n'
            % (self.MODULE,)
        )
        self.assertIsNotNone(self.verdict(source))

    def test_a_sys_modules_subscript_by_string_is_a_caller(self):
        source = (
            "import sys\n"
            'sys.modules["pirateforce_foundation.%s"]\n' % (self.MODULE,)
        )
        self.assertIsNotNone(self.verdict(source))

    def test_a_getattr_by_string_is_a_caller(self):
        source = (
            "import pirateforce_foundation as pf\n"
            'getattr(pf, "%s")\n' % (self.MODULE,)
        )
        self.assertIsNotNone(self.verdict(source))

    def test_a_name_bound_for_a_later_dynamic_import_is_a_caller(self):
        """The route a call/subscript-only check walks straight past."""
        source = (
            "import importlib\n"
            'MODULE = "pirateforce_foundation.%s"\n'
            "importlib.import_module(MODULE)\n" % (self.MODULE,)
        )
        self.assertIsNotNone(self.verdict(source))

    def test_a_docstring_in_a_function_or_a_class_is_still_prose(self):
        source = (
            "class C:\n"
            '    """names %s in a class docstring."""\n'
            "    def m(self):\n"
            '        """and %s in a method docstring."""\n'
            "        return 1\n" % (self.MODULE, self.MODULE)
        )
        self.assertIsNone(self.verdict(source))

    def test_an_unparseable_file_is_not_cleared_as_prose(self):
        source = '"""names %s."""\ndef (\n' % (self.MODULE,)
        self.assertEqual(self.verdict(source), "unparseable python")

    def test_the_file_this_rule_was_written_for_is_prose_by_it(self):
        """tests/test_inventory.py -- the file pull request #511 died on.

        It names two sibling test files whose NAMES carry the module's name;
        it does not import, call or subscript anything of the predicate's.
        If a later round makes it a real caller, this goes red and that
        round owes the allowlist an entry with a reason.
        """
        subject = ROOT / "tests" / "test_inventory.py"
        self.assertTrue(subject.exists(), "tests/test_inventory.py is gone")
        # NO assertIn ON THE FILE'S TEXT.  A draft required the mention to
        # still be there, so an editorial tidy of an unrelated file's prose
        # turned THIS gate red, and the failure printed all 458 lines to a
        # cp874 console.  The claim is about the verdict, not the prose.
        self.assertIsNone(_names_bag_admission_as_code(subject))


class TheRepoWideScanItselfActsOnWhatItFinds(unittest.TestCase):
    """ROUND 78zy6l, after pf-adversary.

    The scan's two acting lines had never executed in any run: with the
    real repository green, the loop always fell through.  pf-adversary
    proved it with three mutants that all stayed green -- clear every
    python file, put every suffix in the prose set, grep for a token that
    does not exist.  These tests plant files and drive the classifier, so
    each of those mutants now has a test that dies with it.
    """

    def planted(self, files):
        """A fake repo root: {relative path: text}.  Returns (root, hits)."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name, text in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return root, sorted(files)

    def test_a_planted_python_caller_is_reported_not_swallowed(self):
        root, hits = self.planted({
            "tools/reach.py":
                "from pirateforce_foundation import bag_admission\n"
                "bag_admission.may_enter_world(None)\n",
        })
        elsewhere = _classify_repo_wide_hits(root, hits, set())
        self.assertEqual(len(elsewhere), 1, elsewhere)
        self.assertIn("tools/reach.py", elsewhere[0])

    def test_a_planted_markdown_file_is_cleared(self):
        root, hits = self.planted({
            "rounds/B_round.md": "round file naming bag_admission in prose\n",
        })
        self.assertEqual(_classify_repo_wide_hits(root, hits, set()), [])

    def test_a_planted_data_file_is_reported_not_cleared(self):
        root, hits = self.planted({
            "tools/wrapper.ps1": "py -3 -c \"import bag_admission\"\n",
        })
        elsewhere = _classify_repo_wide_hits(root, hits, set())
        self.assertEqual(len(elsewhere), 1, elsewhere)
        self.assertIn("tools/wrapper.ps1", elsewhere[0])

    def test_an_allowlisted_caller_is_cleared_and_only_it(self):
        root, hits = self.planted({
            "tools/reach.py":
                "from pirateforce_foundation import bag_admission\n",
            "tools/other.py":
                "from pirateforce_foundation import bag_admission\n",
        })
        elsewhere = _classify_repo_wide_hits(root, hits, {"tools/reach.py"})
        self.assertEqual(len(elsewhere), 1, elsewhere)
        self.assertIn("tools/other.py", elsewhere[0])

    def test_a_pyw_entry_point_is_read_as_python_not_as_a_data_file(self):
        root, hits = self.planted({
            "tools/entry.pyw":
                "from pirateforce_foundation import bag_admission\n",
        })
        elsewhere = _classify_repo_wide_hits(root, hits, set())
        self.assertEqual(len(elsewhere), 1, elsewhere)
        self.assertIn("imports bag_admission", elsewhere[0])

    def test_the_grep_refuses_to_report_nothing_when_git_is_not_there(self):
        """An empty result from a failed grep is not an all-clear."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with self.assertRaises(AssertionError):
            _repo_wide_hits(Path(tmp.name))

    def test_the_live_repository_still_answers_the_grep(self):
        self.assertGreaterEqual(len(_repo_wide_hits(ROOT)), 8)


if __name__ == "__main__":
    unittest.main()
