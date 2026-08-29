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
    tree = ast.parse(path.read_text(encoding="utf-8"))
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


class StubProjector:
    """Records what the session handed the client, if it got that far."""

    def __init__(self):
        self.started_with = []

    def start_game(self, selected, *, backpack):
        self.started_with.append((selected, backpack))
        return b"start-game-frame"


class StubLifecycle:
    """The two calls ``select_and_start`` makes before gate 2, and no more."""

    def __init__(self, backpack):
        self._backpack = backpack
        self.store = None

    def login(self, login_name):
        return 1, "session-1", []

    def select(self, session_id, selector):
        return ("character", selector)

    def backpack(self, session_id, selected):
        return self._backpack


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
        # mob_pickup.py joined runtime.py in round 4gqnwm: its WIRING
        # string used to instruct the chief that persistence was
        # blocked at gate 2, which stopped being true when gate 2
        # became this predicate.  Correcting that instruction means
        # naming the predicate.  Prose and a constant only -- the
        # import check above still holds mob_pickup to zero.
        mentions_allowed = {"runtime.py", "mob_pickup.py"}
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
        # ~~1~~ -> 2 in round 4gqnwm.  The count is pinned so an exemption
        # cannot be added quietly; raising it is meant to be a visible edit,
        # and this one is: mob_pickup's WIRING string carried an instruction
        # that gate 2 blocks persistence, which STORE-INSERT-001 made false,
        # and correcting an instruction about a predicate means naming it.
        self.assertEqual(len(mentions_allowed), 2)

    def test_nothing_outside_the_package_calls_it_either(self):
        """The repo-wide half of the deleted guard: tools/, current/, entrypoints."""
        tracked = subprocess.run(
            ["git", "grep", "-l", "bag_admission", "--", "."],
            cwd=ROOT, capture_output=True, text=True,
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
            # bag_admission's outcome, like the two above it; not a caller
            # reaching for the predicate from outside the package.
            #
            # THIS ENTRY WAS ADDED AFTER THE FACT, AND THAT IS THE LESSON.
            # `git grep` searches the INDEX, so while the new file was
            # untracked this check could not see it and the whole suite ran
            # green; the failure appeared only at `git add`.  A new test file
            # that imports bag_admission must be staged before its own suite
            # run is worth anything.
            "tests/test_store_acquired_item_insert.py",
            # Added by chief, round 4gqnwm.  test_mob_pickup's "wall"
            # test asserted a decommissioned predicate and stayed
            # green through the gate-2 widening it promised to fail
            # on; it now re-derives the wall against the gate IN
            # FORCE, which means reading this predicate.  A test OF
            # the gate's outcome, not a caller of it.
            "tests/test_mob_pickup.py",
            "src/pirateforce_foundation/mob_pickup.py",
            "docs/FUNCTIONAL_COVERAGE.json",
        }
        elsewhere = sorted(
            set(line for line in tracked.stdout.split("\n") if line) - allowed
        )
        self.assertEqual(elsewhere, [], elsewhere)


if __name__ == "__main__":
    unittest.main()
