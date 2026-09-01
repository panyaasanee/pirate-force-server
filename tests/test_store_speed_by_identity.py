"""LANE-DB: `/speed` gets a place to be REMEMBERED, addressed the way `gm/`
can actually address it.

WHAT THIS FILE IS THE EVIDENCE FOR.  `/speed` on `main` today composes a
frame and writes nothing (`pf_bridge/NOW.md` GM-B: the speed column is on `main` but the value does not
persist), because `gm/` holds `identity_lo`/`identity_hi` off
`session.foundation.selected` and holds no `characters.id` at all, while the
only write path this lane had --
`SQLiteStore.write_typed_attributes_and_compose_sparse` -- takes a
`character_id`.  `LANE-GM`'s letter `20260902_0017` asked this lane to own
that translation and fixed the signature; `COO-DECISION 20260902_0147`
ordered it built this round, DB-first, with the refusal VISIBLE.  This file
measures the result.

THE THREE THINGS IT MEASURES HARDEST, in order of how much they matter:

1. **A refused value writes nothing, and a refusal is never a committed
   write reported as a refusal.**  The whole gate runs before the
   transaction opens, and every refusal case below re-reads the row.
2. **An identity that is not two `int`s cannot reach SQLite.**  SQLite
   compares `7.0` equal to `7`, so a float identity MATCHES A REAL ROW.  The
   control for this is the sharpest test in the file: the float form of a
   live character's own identity must write nothing.
3. **The block the caller gets is the row that landed.**  Read back inside
   the write's own transaction, and a disagreement rolls the write back
   instead of being smoothed over.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable.  No frame
is sent and no call site calls either new method -- `gm/` wires it in a later
round (`COO-DECISION 20260902_0147` sends LANE-GM to do it in its first round
after this method is on `main`),
so `/speed` still does not remember anything in the game.  Nothing here can
see WHICH database file the store points at either, so no green test here
means `COO-ORDER 20260901_1641`'s canonical-database ban was honoured; that
gate lives in `gm/chat_command_action._speed_db_is_canonical`.
"""
import ast
import contextlib
import math
import os
import sqlite3
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402
from pirateforce_foundation import persistence_speed_identity as speed_id  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
STORE_SOURCE = ROOT / "src" / "pirateforce_foundation" / "store.py"

#: The identity `_build_wire` hands `create_character` for selector 0.  Pinned
#: here so a test can build the FLOAT form of a real identity.
IDENTITY_LO_FOR_SELECTOR_0 = 0x20000001
IDENTITY_HI = 0


def _build_wire(selector):
    return b"wire", b"avatar", 0x20000001 + selector, 0


#: Captured at IMPORT time, before any patch.  Read off `SQLiteStore.connect`
#: inside the helper instead, it resolves to the PATCH while the patch is
#: active and recurses until the stack dies -- measured.
_REAL_CONNECT = contextlib.contextmanager(SQLiteStore.connect.__wrapped__)


@contextlib.contextmanager
def _connect_impatient(self):
    """`SQLiteStore.connect` with the busy timeout turned down to nothing.

    `connect()` sets `PRAGMA busy_timeout=5000` and belongs to chief's half
    of `store.py`, so this lane does not change it -- but a test that waits
    five real seconds to prove a lock is answered is a test nobody runs
    twice.  Everything else about the connection is the real thing.
    """
    with _REAL_CONNECT(self) as db:
        db.execute("PRAGMA busy_timeout=0")
        yield db


def open_handles_under(directory):
    """Paths inside `directory` this process still has open, or `None` where
    that cannot be asked (no `/proc`, i.e. not Linux).

    `None` is not "clean" and callers must not read it as clean.  On Windows
    the operating system enforces the same rule by refusing the unlink -- and
    that, not a Linux assertion, is how this defect reached the gate twice in
    this lane's history (PR #495, PR #518).
    """
    if not os.path.isdir("/proc/self/fd"):
        return None
    root = os.path.realpath(directory)
    held = set()
    for fd in os.listdir("/proc/self/fd"):
        try:
            target = os.readlink(os.path.join("/proc/self/fd", fd))
        except OSError:
            continue
        if target.startswith(root + os.sep):
            held.add(target)
    return sorted(held)


class StoreOnATempDatabase(unittest.TestCase):
    """One real SQLite file, one account, one character on selector 0.

    Not `:memory:`: `BEGIN IMMEDIATE`, WAL and the column CHECKs are the
    things under test and a memory database does not exercise the same file
    behaviour.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # AFTER the line above on purpose: cleanups run LIFO, so this one runs
        # BEFORE the directory is removed.  Registered the other way round it
        # would inspect a directory that no longer exists and pass always.
        self.addCleanup(self._assert_no_handle_survives, self.tmp.name)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("speed-by-identity")
        self.character = self.store.create_character(
            self.account_id, "SpeedByIdentity", "speedbyidentity",
            "fingerprint-speed-by-identity", _build_wire, self.home,
        )
        self.assertEqual(self.character.identity_lo, IDENTITY_LO_FOR_SELECTOR_0)
        self.assertEqual(self.character.identity_hi, IDENTITY_HI)

    def _assert_no_handle_survives(self, name):
        held = open_handles_under(name)
        if held is None:  # not Linux: the OS enforces this itself, loudly
            return
        self.assertEqual(
            held,
            [],
            "a handle on the temp directory outlives this test.  On Windows "
            "TemporaryDirectory.cleanup raises WinError 32 here and the gate "
            "goes red.",
        )

    def write(self, speed, *, lo=None, hi=None):
        return self.store.write_speed_by_identity_with_reason(
            IDENTITY_LO_FOR_SELECTOR_0 if lo is None else lo,
            IDENTITY_HI if hi is None else hi,
            speed,
        )

    def stored_speed(self):
        """The speed column of the fixture character, or `None` if unset.

        Read through `read_typed_attributes`, which OMITS a NULL column, so
        "unset" arrives here as absence rather than as a zero.
        """
        state = self.store.read_typed_attributes(self.character.id)
        return state.get(speed_id.speed_column())

    def raw_row(self):
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT * FROM characters WHERE id=?", (self.character.id,)
            ).fetchone()
            return dict(row)
        finally:
            db.close()


class ConstantsPinTests(unittest.TestCase):
    """The field number, the column it names, and the permission agree.

    All three are read from the modules that own them rather than restated,
    so a rename or a widened permission is red HERE and not on a live client.
    """

    def test_the_field_is_x_seven_and_its_column_is_speed_walk(self):
        self.assertEqual(speed_id.SPEED_FIELD_X, 7)
        self.assertEqual(speed_id.speed_column(), "speed_walk")

    def test_the_column_is_the_one_the_typed_table_maps_x_seven_to(self):
        self.assertEqual(
            speed_id.speed_column(), typed.COLUMN_FOR_X[speed_id.SPEED_FIELD_X]
        )

    def test_the_field_is_approved_for_the_sparse_send_path(self):
        self.assertIn(speed_id.SPEED_FIELD_X, compose.SPARSE_APPROVED_FIELDS)

    def test_the_field_number_is_a_literal_not_read_off_the_permission_set(self):
        """A control for the comment that says why, asserted on the SOURCE.

        `SPARSE_APPROVED_FIELDS` is a PERMISSION and COO may widen it.  If
        this module derived its field from that set, the day it becomes
        `{7, 12}` this lane starts writing a different column with nothing
        saying so.

        The first draft of this test widened the set at RUNTIME and asserted
        `SPEED_FIELD_X == 7` -- which is hollow: the constant is computed at
        IMPORT time, so rebinding the set afterwards cannot move it and
        `SPEED_FIELD_X = max(SPARSE_APPROVED_FIELDS)` survived the test
        untouched.  Measured.  The assignment itself is what has to be a
        literal, so that is what is read.
        """
        module = Path(speed_id.__file__)
        tree = ast.parse(module.read_text(encoding="utf-8"))
        assigned = [
            node for node in tree.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "SPEED_FIELD_X"
        ]
        self.assertEqual(len(assigned), 1)
        value = assigned[0].value
        self.assertIsInstance(value, ast.Constant, ast.unparse(value))
        # `assertNotIsInstance(..., bool)` was here and was unreachable
        # after the equality above (`True != 7`).  Measured, removed.
        self.assertEqual(value.value, 7)

    def test_refusals_are_the_reasons_minus_ok(self):
        self.assertEqual(speed_id.REFUSALS, speed_id.REASONS - {speed_id.REASON_OK})
        self.assertNotIn(speed_id.REASON_OK, speed_id.REFUSALS)

    def test_every_reason_the_store_returns_is_a_declared_reason(self):
        """The store may not invent a token the caller has never seen.

        Read out of `store.py`'s SOURCE rather than out of a run: a token on
        a branch no test reaches would otherwise never be checked, and the GM
        would meet it for the first time in a chat window.
        """
        tree = ast.parse(STORE_SOURCE.read_text(encoding="utf-8"))
        used = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr.startswith("REASON_")
        }
        self.assertTrue(used, "no reason token is referenced in store.py at all")
        # `and name != "REASONS"` was here and was a no-op:
        # `"REASONS".startswith("REASON_")` is False.  Measured, removed.
        declared = {n for n in dir(speed_id) if n.startswith("REASON_")}
        self.assertEqual(used - declared, set())
        for name in used:
            self.assertIn(getattr(speed_id, name), speed_id.REASONS)


class GateValueTests(unittest.TestCase):
    """The refusal gate, with no database anywhere near it."""

    def test_a_good_speed_comes_back_as_the_float32_the_wire_carries(self):
        value = speed_id.gate_value(400.1)
        self.assertEqual(value, struct.unpack("<f", struct.pack("<f", 400.1))[0])
        self.assertNotEqual(value, 400.1)

    def test_zero_is_a_value_and_is_not_refused(self):
        """Deliberate, and the opposite of the owner's banned zero.

        The ban (`COO-DECISION 20260901_1059`) is on a zero that was GUESSED
        for a field nobody supplied.  A zero a GM typed is a supplied value,
        and `read_typed_attributes` keeps it (only NULL is omitted), so it
        round-trips as a value rather than as an absence.
        """
        self.assertEqual(speed_id.gate_value(0.0), 0.0)

    def test_a_value_that_underflows_to_zero_on_the_wire_is_refused(self):
        """The guessed zero reached by arithmetic instead of by a lookup."""
        self.assertIsNone(speed_id.gate_value(1e-300))

    def test_the_shapes_that_cannot_survive_the_encoder_are_refused(self):
        for value in ("fast", None, True, False, float("nan"), float("inf"),
                      -float("inf"), 1e39, -1e39, object(), [400.0], {7: 400.0}):
            with self.subTest(value=repr(value)):
                self.assertIsNone(speed_id.gate_value(value))

    def test_an_int_speed_is_accepted_and_stored_as_a_float(self):
        value = speed_id.gate_value(400)
        self.assertEqual(value, 400.0)
        self.assertIsInstance(value, float)

    def test_identity_is_usable_only_for_two_real_ints(self):
        self.assertTrue(speed_id.identity_is_usable(1, 0))
        self.assertTrue(speed_id.identity_is_usable(-1, -1))
        for lo, hi in ((1.0, 0), (1, 0.0), (True, 0), (1, True), ("1", 0),
                       (None, 0), (1, None)):
            with self.subTest(lo=repr(lo), hi=repr(hi)):
                self.assertFalse(speed_id.identity_is_usable(lo, hi))

    def test_a_row_with_no_speed_column_is_absence_not_zero(self):
        self.assertIsNone(speed_id.block_from_stored({}))
        self.assertIsNone(speed_id.block_from_stored({"level": 3}))

    def test_a_row_holding_something_unstorable_composes_nothing(self):
        """This function is importable and a caller can hand it a row it read
        itself, so its refusal arm is reachable -- reached here rather than
        left to be argued about (an adversary line census found it never
        executed).
        """
        for junk in ("fast", float("nan"), float("inf"), 1e39, True, None):
            with self.subTest(junk=repr(junk)):
                self.assertIsNone(
                    speed_id.block_from_stored({speed_id.speed_column(): junk})
                )

    def test_a_row_with_a_speed_composes_the_one_field_block(self):
        self.assertEqual(
            speed_id.block_from_stored({speed_id.speed_column(): 620.0}),
            {7: 620.0},
        )


class WriteSpeedByIdentityTests(StoreOnATempDatabase):
    """The happy path and everything that must not happen around it."""

    def test_a_speed_write_comes_back_as_the_one_field_block(self):
        block, reason = self.write(620.0)
        self.assertEqual(reason, speed_id.REASON_OK)
        self.assertEqual(block, {7: 620.0})

    def test_the_block_value_is_always_a_float(self):
        """The annotation says `dict[int, object]` because
        `compose_sparse_block` does; the VALUE is always a `float`, and the
        reply to LANE-GM tells them they may rely on that.  This is what
        makes that sentence true rather than polite -- including for an int
        the GM typed.
        """
        for typed_in in (620.0, 400, 0.0, 1):
            with self.subTest(typed_in=typed_in):
                block, reason = self.write(typed_in)
                self.assertEqual(reason, speed_id.REASON_OK)
                self.assertIsInstance(block[7], float)
                self.assertNotIsInstance(block[7], bool)

    def test_the_value_survives_a_reopen_of_the_database(self):
        self.write(620.0)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(
            reopened.read_typed_attributes(self.character.id),
            {speed_id.speed_column(): 620.0},
        )

    def test_the_block_and_the_column_are_the_same_float32(self):
        block, reason = self.write(400.1)
        self.assertEqual(reason, speed_id.REASON_OK)
        self.assertEqual(self.stored_speed(), block[7])
        self.assertEqual(block[7], struct.unpack("<f", struct.pack("<f", 400.1))[0])
        self.assertNotEqual(block[7], 400.1)

    def test_zero_is_written_and_reads_back_as_a_value(self):
        block, reason = self.write(0.0)
        self.assertEqual(reason, speed_id.REASON_OK)
        self.assertEqual(block, {7: 0.0})
        # present, and NOT absent: the row really holds a zero
        self.assertIn(speed_id.speed_column(),
                      self.store.read_typed_attributes(self.character.id))
        self.assertEqual(self.stored_speed(), 0.0)

    def test_a_second_write_replaces_rather_than_appends(self):
        self.write(400.0)
        block, reason = self.write(250.0)
        self.assertEqual(reason, speed_id.REASON_OK)
        self.assertEqual(block, {7: 250.0})
        self.assertEqual(self.stored_speed(), 250.0)

    def test_only_the_speed_column_moves(self):
        """Every other byte of the row is compared, not just the typed ones.

        `updated_at` is expected to move and is excluded by name rather than
        by being quietly left out of the comparison.
        """
        before = self.raw_row()
        self.write(333.0)
        after = self.raw_row()
        moved = {k for k in before if before[k] != after[k]}
        self.assertEqual(moved, {speed_id.speed_column(), "updated_at"})
        self.assertNotEqual(before["updated_at"], after["updated_at"])

    def test_no_other_typed_column_is_seeded_by_the_write(self):
        self.write(333.0)
        self.assertEqual(
            self.store.read_typed_attributes(self.character.id),
            {speed_id.speed_column(): 333.0},
        )

    def test_a_write_leaves_an_existing_typed_value_alone(self):
        self.store.write_typed_attributes(self.character.id, {"level": 12})
        self.write(333.0)
        self.assertEqual(
            self.store.read_typed_attributes(self.character.id),
            {"level": 12, speed_id.speed_column(): 333.0},
        )

    def test_the_short_method_agrees_with_the_long_one_on_every_input(self):
        """The two are run SIDE BY SIDE on two identical databases.

        The first version of this test called only the short method and
        checked three literals, while its docstring claimed it caught a
        reimplementation.  An adversary pass replaced the delegating body
        with a hand-rolled one that dropped the read-back, dropped
        `deleted_at IS NULL` from its UPDATE and built the block from the
        caller's own value -- and this file reported `46 passed`.  A test
        that names a mutant it does not catch is worse than no test.

        So: two stores, same migrations, same fixture, same inputs, and BOTH
        answers compared -- the returned block AND the row it left behind.
        """
        other_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(other_tmp.cleanup)
        other_path = Path(other_tmp.name) / "state.sqlite3"
        other = SQLiteStore(other_path, MIGRATIONS)
        other.migrate()
        other_account = other.ensure_account("speed-by-identity")
        twin = other.create_character(
            other_account, "SpeedByIdentity", "speedbyidentity",
            "fingerprint-speed-by-identity", _build_wire, self.home,
        )
        cases = (
            (IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, 500.0),
            (IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, 400.1),
            (IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, 0.0),
            (999999, IDENTITY_HI, 500.0),
            (IDENTITY_LO_FOR_SELECTOR_0, 1, 500.0),
            (IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, "fast"),
            (IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, float("nan")),
            (IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, 1e-300),
            (float(IDENTITY_LO_FOR_SELECTOR_0), IDENTITY_HI, 500.0),
            (2 ** 63, IDENTITY_HI, 500.0),
            (True, False, 500.0),
        )
        for lo, hi, speed in cases:
            with self.subTest(lo=repr(lo), hi=repr(hi), speed=repr(speed)):
                short = self.store.write_speed_by_identity(lo, hi, speed)
                long, _reason = other.write_speed_by_identity_with_reason(
                    lo, hi, speed
                )
                self.assertEqual(short, long)
                # and the two databases were left in the same state
                self.assertEqual(
                    self.store.read_typed_attributes(self.character.id),
                    other.read_typed_attributes(twin.id),
                )

    def test_the_short_method_is_a_delegation_and_nothing_else(self):
        """Read off the SOURCE, because the behavioural test above can only
        compare what a reimplementation CHOSE to get right.

        The body must be exactly: call the reason-carrying method, return its
        block.  Any SQL, any second answer, any extra branch is a second
        implementation of the guarantees this file measures only once.
        """
        tree = ast.parse(STORE_SOURCE.read_text(encoding="utf-8"))
        func = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef)
                    and n.name == "write_speed_by_identity")
        body = [n for n in func.body
                if not (isinstance(n, ast.Expr)
                        and isinstance(n.value, ast.Constant)
                        and isinstance(n.value.value, str))]
        code = ast.unparse(ast.Module(body=body, type_ignores=[]))
        self.assertEqual(len(body), 2, code)
        self.assertIn("self.write_speed_by_identity_with_reason", code)
        for forbidden in ("SELECT", "UPDATE", "connect", "REASON_", "if "):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)


class NothingIsWrittenWhenItIsRefusedTests(StoreOnATempDatabase):
    """Every refusal, and the row after it.

    A refusal that had already committed would be the exact lie
    `COO-DECISION 20260902_0147` forbids, so each test below asserts the
    ANSWER and then re-reads the database.
    """

    def assertNothingLanded(self, before):
        self.assertEqual(self.raw_row(), before)

    def test_an_unknown_identity_is_named_and_writes_nothing(self):
        before = self.raw_row()
        block, reason = self.write(400.0, lo=0x7FFFFFFF)
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_NO_SUCH_CHARACTER)
        # Same honesty as the CHECK arm: this measures that nothing landed,
        # not that `db.rollback()` is why.  On this path nothing had been
        # written to undo, so removing the call keeps every test green
        # (measured).  It is kept as intent, and declared unmeasured.
        self.assertNothingLanded(before)

    def test_the_right_lo_with_the_wrong_hi_is_not_a_match(self):
        """Both halves are part of the key, and this proves the second one is
        really in the WHERE clause -- dropping `identity_hi=?` leaves every
        other test in this file green.
        """
        before = self.raw_row()
        block, reason = self.write(400.0, hi=1)
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_NO_SUCH_CHARACTER)
        self.assertNothingLanded(before)

    def test_a_refused_value_is_named_and_writes_nothing(self):
        for value in ("fast", None, True, float("nan"), float("inf"),
                      1e39, 1e-300, [400.0]):
            with self.subTest(value=repr(value)):
                before = self.raw_row()
                block, reason = self.write(value)
                self.assertIsNone(block)
                self.assertEqual(reason, speed_id.REASON_VALUE_REFUSED)
                self.assertNothingLanded(before)

    def test_a_refused_value_does_not_undo_a_good_earlier_one(self):
        self.write(400.0)
        block, reason = self.write(float("nan"))
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_VALUE_REFUSED)
        self.assertEqual(self.stored_speed(), 400.0)

    def test_a_float_identity_that_equals_a_live_one_writes_nothing(self):
        """THE sharpest control in this file.

        SQLite compares `REAL 536870913.0` EQUAL to `INTEGER 536870913`, so
        without the `type(...) is int` guard this call finds the fixture
        character's own row and writes to it.  Measured: with the guard
        removed, the assertion below on `stored_speed()` is the only one in
        this file that goes red.
        """
        before = self.raw_row()
        block, reason = self.write(
            400.0, lo=float(IDENTITY_LO_FOR_SELECTOR_0), hi=float(IDENTITY_HI)
        )
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_IDENTITY_NOT_AN_INT)
        self.assertIsNone(self.stored_speed())
        self.assertNothingLanded(before)
        # and the premise of the test is real, not assumed
        db = sqlite3.connect(self.path)
        try:
            matched = db.execute(
                "SELECT COUNT(*) FROM characters WHERE identity_lo=?",
                (float(IDENTITY_LO_FOR_SELECTOR_0),),
            ).fetchone()[0]
        finally:
            db.close()
        self.assertEqual(matched, 1, "the float really does match the row")

    def test_a_bool_identity_writes_nothing(self):
        """`True` is an `int` in python and `1` is a plausible identity."""
        before = self.raw_row()
        block, reason = self.write(400.0, lo=True, hi=False)
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_IDENTITY_NOT_AN_INT)
        self.assertNothingLanded(before)

    def test_a_string_identity_writes_nothing(self):
        before = self.raw_row()
        block, reason = self.write(400.0, lo=str(IDENTITY_LO_FOR_SELECTOR_0))
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_IDENTITY_NOT_AN_INT)
        self.assertNothingLanded(before)

    def test_no_refusal_ever_creates_a_row(self):
        db = sqlite3.connect(self.path)
        try:
            before = db.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
        finally:
            db.close()
        self.write(400.0, lo=0x7FFFFFFF)
        self.write("fast")
        self.write(400.0, lo=1.0)
        db = sqlite3.connect(self.path)
        try:
            after = db.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
        finally:
            db.close()
        self.assertEqual(before, after)


class TheTwoLinesBehindTheGateTests(StoreOnATempDatabase):
    """The refusals `gate_value` is supposed to make unreachable.

    They exist because "unreachable" is an argument, not a measurement: the
    python range table and `migrations/006_character_typed_attribute_columns.
    sql`'s CHECKs are two separate transcriptions of the same numbers, and a
    later migration or a later widening can desync them.  Both paths are
    forced here by replacing `gate_value` -- there is no INPUT that reaches
    them today, which is exactly the point.

    Without these two tests both branches are dead source: an adversary pass
    disabled the read-back check entirely and every other test in this file
    stayed green.
    """

    def test_a_value_the_column_check_refuses_is_named_not_raised(self):
        """The SQL CHECK fires and the GM is told WHICH gate said no."""
        before = self.raw_row()
        original = speed_id.gate_value
        try:
            speed_id.gate_value = lambda value: 1e39  # outside the f32 CHECK
            block, reason = self.write(400.0)
        finally:
            speed_id.gate_value = original
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_SCHEMA_REFUSED)
        # WHAT THIS MEASURES: nothing landed.  NOT that `db.rollback()` is
        # what stopped it -- an adversary pass removed that call and this
        # stayed green, because SQLite's default `ON CONFLICT ABORT` had
        # already undone the statement.  The `rollback()` in that arm is
        # unmeasured defence for a future edit that writes before the CHECK
        # fires, and it is declared as such in the round file rather than
        # asserted here.
        self.assertEqual(self.raw_row(), before, "nothing landed")

    def test_a_value_sqlite_turns_into_null_is_caught_by_the_read_back(self):
        """`float('nan')` binds to SQLite as NULL, which the column's
        `speed_walk IS NULL OR ...` CHECK happily accepts -- so the CHECK is
        NOT the last line here, the read-back is.  A NULL speed reaching the
        caller as a block would be the absent-field-rendered-as-a-value the
        owner's rule forbids.
        """
        before = self.raw_row()
        original = speed_id.gate_value
        try:
            speed_id.gate_value = lambda value: float("nan")
            block, reason = self.write(400.0)
        finally:
            speed_id.gate_value = original
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_READBACK_DISAGREES)
        self.assertEqual(self.raw_row(), before, "nothing landed")

    def test_a_block_that_cannot_be_composed_rolls_the_write_back(self):
        """The other half of the same guard: the row landed, but no block can
        be built from it.  Reporting that as a success would hand the caller
        a `None` block under `REASON_OK`; reporting it as done without a
        block would tell the GM a speed was set that nothing can show.  So it
        is rolled back and named.
        """
        before = self.raw_row()
        original = speed_id.block_from_stored
        try:
            speed_id.block_from_stored = lambda stored: None
            block, reason = self.write(400.0)
        finally:
            speed_id.block_from_stored = original
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_READBACK_DISAGREES)
        self.assertEqual(self.raw_row(), before, "the write really rolled back")
        self.assertIsNone(self.stored_speed())


class AnIdentitySqliteCannotBindTests(StoreOnATempDatabase):
    """An `int` too wide for SQLite is refused HERE, not by the driver.

    Measured by an adversary pass against the first draft, which checked the
    TYPE of an identity and not its RANGE: `2**63` walked through the gate,
    through `BEGIN IMMEDIATE`, and died on the parameter bind with
    `OverflowError: Python int too large to convert to SQLite INTEGER`.
    Nothing was written -- and the caller got an exception that is not a
    token, is documented nowhere, is caught nowhere, and reaches a GM's
    screen as the silence `COO-DECISION 20260902_0147` bans.
    """

    def test_an_int_wider_than_sqlite_is_a_token_not_an_overflow(self):
        for lo, hi in ((2 ** 63, IDENTITY_HI), (2 ** 64, IDENTITY_HI),
                       (-(2 ** 63) - 1, IDENTITY_HI),
                       (IDENTITY_LO_FOR_SELECTOR_0, 2 ** 70)):
            with self.subTest(lo=lo, hi=hi):
                before = self.raw_row()
                block, reason = self.write(400.0, lo=lo, hi=hi)
                self.assertIsNone(block)
                self.assertEqual(reason, speed_id.REASON_IDENTITY_NOT_AN_INT)
                self.assertEqual(self.raw_row(), before)

    def test_the_widest_bindable_int_is_still_usable(self):
        """The boundary is not moved inward: these are legal identities that
        simply match no row, and must NOT be reported as a type problem.
        """
        for half in (speed_id.SQLITE_INTEGER_MAX, speed_id.SQLITE_INTEGER_MIN):
            with self.subTest(half=half):
                self.assertTrue(speed_id.identity_is_usable(half, 0))
                block, reason = self.write(400.0, lo=half)
                self.assertIsNone(block)
                self.assertEqual(reason, speed_id.REASON_NO_SUCH_CHARACTER)


class WhenTheDatabaseItselfIsTheProblemTests(StoreOnATempDatabase):
    """`db_unavailable`: an operational failure is ANSWERED, with its own name.

    Neither an exception (which skips `_log_outcome` at
    `gm/chat_command_action.py:1284` and answers the GM with nothing) nor a
    value refusal (which blames the number the GM typed).  Both of those were
    measured on the real caller by an adversary pass; this class is the
    third option existing.
    """

    def test_a_database_that_cannot_be_opened_is_named_not_raised(self):
        missing = SQLiteStore(
            Path(self.tmp.name) / "no" / "such" / "state.sqlite3", MIGRATIONS
        )
        block, reason = missing.write_speed_by_identity_with_reason(
            IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, 400.0
        )
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_DB_UNAVAILABLE)

    def test_a_database_with_no_characters_table_is_named_not_raised(self):
        """An un-migrated file: `no such table` is an `OperationalError` too,
        and it must not surface as `no_such_character` -- the row is not
        missing, the SCHEMA is.
        """
        empty = Path(self.tmp.name) / "empty.sqlite3"
        db = sqlite3.connect(empty)
        try:
            db.execute("CREATE TABLE unrelated(x)")
            db.commit()
        finally:
            db.close()
        store = SQLiteStore(empty, MIGRATIONS)
        block, reason = store.write_speed_by_identity_with_reason(
            IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, 400.0
        )
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_DB_UNAVAILABLE)

    def test_a_locked_database_is_named_not_raised(self):
        """Another connection holds the write lock for longer than the busy
        timeout.  Measured rather than reasoned about -- and it is also what
        makes the five-second stall in the method's docstring a fact.
        """
        holder = sqlite3.connect(self.path)
        try:
            holder.execute("PRAGMA busy_timeout=0")
            holder.execute("BEGIN IMMEDIATE")
            holder.execute(
                "UPDATE characters SET updated_at=? WHERE id=?",
                ("held", self.character.id),
            )
            with mock.patch.object(SQLiteStore, "connect", _connect_impatient):
                block, reason = self.write(400.0)
        finally:
            holder.rollback()
            holder.close()
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_DB_UNAVAILABLE)
        # the holder's transaction was rolled back, so nothing of ours landed
        self.assertIsNone(self.stored_speed())


class ThePremisesThisMethodStandsOnTests(StoreOnATempDatabase):
    """The docstring cites two facts about the schema.  Cited is not pinned.

    An adversary pass measured that `characters_active_identity` was named in
    exactly two places -- migration 004 and a docstring -- with no test
    asserting it exists on the database this method actually opens.  The code
    uses `.fetchone()` with no `LIMIT` and no count check, so if that index
    were ever absent the method would silently pick an arbitrary row.
    """

    def test_the_partial_unique_index_on_a_live_identity_really_exists(self):
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            indexes = {r["name"]: dict(r)
                       for r in db.execute("PRAGMA index_list(characters)")}
            self.assertIn("characters_active_identity", indexes)
            self.assertEqual(indexes["characters_active_identity"]["unique"], 1)
            self.assertEqual(indexes["characters_active_identity"]["partial"], 1)
            columns = [r[2] for r in
                       db.execute("PRAGMA index_info(characters_active_identity)")]
        finally:
            db.close()
        self.assertEqual(columns, ["identity_lo", "identity_hi"])

    def test_two_live_characters_cannot_share_an_identity(self):
        """The property the index is cited FOR, measured end to end rather
        than inferred from the index's flags.
        """
        db = sqlite3.connect(self.path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO characters(account_id,selector,name,name_key,"
                    "create_fingerprint,actor_wire,avatar_wire,identity_lo,"
                    "identity_hi,created_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (self.account_id, 9, "Clone", "clone", "fp-clone",
                     b"w", b"a", IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI,
                     "now", "now"),
                )
        finally:
            db.rollback()
            db.close()


class SoftDeleteAndIdentityReuseTests(StoreOnATempDatabase):
    """`migrations/004` lets a soft-deleted character's identity be REUSED.

    That is the reason the lookup carries `deleted_at IS NULL` and the reason
    the whole method is one `BEGIN IMMEDIATE` transaction: the row a lookup
    identifies must still be the row the write lands on.
    """

    def soft_delete_the_fixture(self):
        sid = self.store.open_session(self.account_id)
        self.store.soft_delete_character(sid, self.character.selector)
        self.store.close_session(sid)

    def test_a_soft_deleted_character_is_no_such_character(self):
        self.soft_delete_the_fixture()
        block, reason = self.write(400.0)
        self.assertIsNone(block)
        self.assertEqual(reason, speed_id.REASON_NO_SUCH_CHARACTER)

    def test_a_soft_deleted_row_is_not_written_through(self):
        """Its column stays NULL -- the write did not reach the dead row."""
        self.soft_delete_the_fixture()
        self.write(400.0)
        db = sqlite3.connect(self.path)
        try:
            value = db.execute(
                f"SELECT {speed_id.speed_column()} FROM characters WHERE id=?",
                (self.character.id,),
            ).fetchone()[0]
        finally:
            db.close()
        self.assertIsNone(value)

    def test_the_live_reuser_of_an_identity_is_the_one_written(self):
        """The identity is reused by a NEW character; the write must land on
        that one and leave the dead row alone.
        """
        self.soft_delete_the_fixture()
        reborn = self.store.create_character(
            self.account_id, "Reborn", "reborn",
            "fingerprint-speed-reborn", _build_wire, self.home,
        )
        self.assertNotEqual(reborn.id, self.character.id)
        self.assertEqual(reborn.identity_lo, self.character.identity_lo)
        self.assertEqual(reborn.identity_hi, self.character.identity_hi)
        block, reason = self.write(777.0)
        self.assertEqual(reason, speed_id.REASON_OK)
        self.assertEqual(block, {7: 777.0})
        self.assertEqual(
            self.store.read_typed_attributes(reborn.id),
            {speed_id.speed_column(): 777.0},
        )
        db = sqlite3.connect(self.path)
        try:
            dead = db.execute(
                f"SELECT {speed_id.speed_column()} FROM characters WHERE id=?",
                (self.character.id,),
            ).fetchone()[0]
        finally:
            db.close()
        self.assertIsNone(dead, "the soft-deleted row must not be touched")


class OneCharacterAtATimeTests(StoreOnATempDatabase):
    def test_writing_one_identity_leaves_every_other_character_alone(self):
        other = self.store.create_character(
            self.account_id, "Other", "other",
            "fingerprint-speed-other", _build_wire, self.home,
        )
        self.assertNotEqual(other.identity_lo, self.character.identity_lo)
        block, reason = self.write(555.0)
        self.assertEqual(reason, speed_id.REASON_OK)
        self.assertEqual(block, {7: 555.0})
        self.assertEqual(self.store.read_typed_attributes(other.id), {})

    def test_each_identity_reaches_its_own_row(self):
        other = self.store.create_character(
            self.account_id, "Other", "other",
            "fingerprint-speed-other", _build_wire, self.home,
        )
        self.write(111.0)
        self.store.write_speed_by_identity_with_reason(
            other.identity_lo, other.identity_hi, 222.0
        )
        self.assertEqual(self.stored_speed(), 111.0)
        self.assertEqual(
            self.store.read_typed_attributes(other.id),
            {speed_id.speed_column(): 222.0},
        )


class TheWriteIsOneTransactionTests(unittest.TestCase):
    """Structural pins on `store.write_speed_by_identity_with_reason`.

    Behaviour cannot show this from a single-threaded test: split the method
    into three transactions and every other test in this file stays green,
    while the window in which `004`'s identity reuse can move the row out
    from under the lookup opens up.  So the shape is asserted from the AST.
    """

    def setUp(self):
        tree = ast.parse(STORE_SOURCE.read_text(encoding="utf-8"))
        self.func = next(
            (n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef)
             and n.name == "write_speed_by_identity_with_reason"),
            None,
        )
        self.assertIsNotNone(self.func, "the method is gone from store.py")
        # THE DOCSTRING IS DROPPED, and this line is why this class is worth
        # anything.  The first draft of it asserted against
        # `ast.unparse(self.func)` whole -- and that method's docstring says
        # the words "BEGIN IMMEDIATE" and "deleted_at IS NULL" out loud, so
        # BOTH assertions passed on PROSE.  Measured: deleting the real
        # `BEGIN IMMEDIATE` statement and the real `deleted_at IS NULL` from
        # the UPDATE left every test in this file green.  A test that grades
        # a docstring is a test that grades nothing.
        self.body = [n for n in self.func.body
                     if not (isinstance(n, ast.Expr)
                             and isinstance(n.value, ast.Constant)
                             and isinstance(n.value.value, str))]
        self.assertEqual(len(self.body), len(self.func.body) - 1,
                         "the docstring was not the first statement")
        self.code = ast.unparse(ast.Module(body=self.body, type_ignores=[]))

    def _with_blocks(self):
        return [n for n in ast.walk(self.func) if isinstance(n, ast.With)]

    def test_there_is_exactly_one_connection_block(self):
        self.assertEqual(len(self._with_blocks()), 1)

    def test_it_opens_an_immediate_transaction(self):
        self.assertIn("BEGIN IMMEDIATE", self.code)

    def test_the_lookup_the_update_and_the_read_back_are_all_inside_it(self):
        block = self._with_blocks()[0]
        inside = ast.unparse(ast.Module(body=block.body, type_ignores=[]))
        self.assertIn("SELECT id FROM characters", inside)
        self.assertIn("UPDATE characters SET", inside)
        self.assertIn("deleted_at IS NULL", inside)

    def test_the_lookup_and_the_update_both_exclude_deleted_rows(self):
        """Two predicates, and BOTH are load-bearing.

        The guard is the error message, the predicate is what makes the write
        impossible -- same reasoning as `write_typed_attributes`, where an
        adversary pass landed a write on a soft-deleted row by deleting the
        guard while every test stayed green.

        This asserted THREE until an adversary pass measured the third: the
        read-back's copy of the predicate was inert (the row is locked by
        this transaction, its `deleted_at` cannot move), so removing it
        changed no behaviour and only this count went red.  A hardcoded count
        that fires for a change with no behaviour behind it is a trap for the
        next round, so the decoration was deleted and the number follows the
        two that mean something.
        """
        self.assertEqual(self.code.count("deleted_at IS NULL"), 2,
                         "the lookup and the UPDATE each carry it; a count "
                         "of 1 means one was dropped")

    def test_only_an_operational_error_becomes_db_unavailable(self):
        """The catch must not be widened to `sqlite3.Error`.

        Measured by an adversary pass: that one-word edit turns a locked
        database into `schema_refused` -- an operational failure laundered
        into a refusal of the value the GM typed, in the method whose whole
        purpose is that a refusal is never mislabelled.  Nothing else in this
        file pins the class, so this is the pin.
        """
        handlers = [n for n in ast.walk(self.func)
                    if isinstance(n, ast.ExceptHandler)]
        caught = {ast.unparse(h.type) for h in handlers if h.type is not None}
        self.assertEqual(caught, {"sqlite3.IntegrityError",
                                  "sqlite3.OperationalError"})

    def test_the_connect_call_is_inside_the_operational_error_guard(self):
        """`unable to open database file` is raised by the CONNECT, not by a
        statement -- so a guard that starts after it would miss the case it
        names.
        """
        guard = next(n for n in ast.walk(self.func)
                     if isinstance(n, ast.Try)
                     and any(h.type is not None
                             and ast.unparse(h.type) == "sqlite3.OperationalError"
                             for h in n.handlers))
        self.assertIn("self.connect()",
                      ast.unparse(ast.Module(body=guard.body, type_ignores=[])))

    def test_there_is_no_unreachable_second_no_such_character_return(self):
        """A `rowcount != 1` branch cannot fire after the lookup found the
        row by id inside the same IMMEDIATE transaction, and an adversary
        line census proved it never executed.  It is gone; this keeps it
        gone, because a token that can be returned from a place it can never
        be returned from is a lie about what the method handles.
        """
        self.assertEqual(self.code.count("REASON_NO_SUCH_CHARACTER"), 1)
        self.assertNotIn("rowcount", self.code)

    def test_nothing_in_it_inserts_or_deletes(self):
        text = self.code.upper()
        for verb in ("INSERT INTO", "DELETE FROM", "DROP ", "CREATE "):
            with self.subTest(verb=verb):
                self.assertNotIn(verb, text)

    def test_the_gate_runs_before_the_connection_is_opened(self):
        """DB-first means the DB is never touched by a value it would refuse.

        Measured on the source: both refusal returns for a bad identity and a
        bad value must appear BEFORE the `with` block starts.
        """
        block = self._with_blocks()[0]
        # `self.body`, NOT `self.func.body`: the docstring is stripped from
        # the former.  An adversary pass measured that this test graded
        # PROSE -- the docstring contains the words "gate_value", so that
        # assertion could not fail while the sentence stood.  The same
        # hollow shape this class was written to prevent, inside this class,
        # three tests after the comment explaining it.
        head = ast.unparse(ast.Module(
            body=[n for n in self.body if n.lineno < block.lineno],
            type_ignores=[],
        ))
        self.assertNotIn("COO-DECISION", head, "the docstring leaked back in")
        self.assertIn("REASON_IDENTITY_NOT_AN_INT", head)
        self.assertIn("REASON_VALUE_REFUSED", head)
        self.assertIn("gate_value", head)


class AsciiOnlyTests(unittest.TestCase):
    """The bridge console is code page 874; a non-ASCII byte in a source file
    of this lane has broken a run before.
    """

    def test_this_lane_s_new_files_are_ascii(self):
        for path in (
            ROOT / "src" / "pirateforce_foundation" / "persistence_speed_identity.py",
            Path(__file__),
        ):
            with self.subTest(path=path.name):
                path.read_bytes().decode("ascii")

    def test_the_two_methods_this_lane_added_to_store_py_are_ascii(self):
        """`store.py` is the third file this round ships and the one that
        gained 147 lines of prose, and the guard above did not cover it --
        found by an adversary pass.

        Scoped to THIS LANE'S TWO METHODS rather than the whole file on
        purpose: `store.py` is shared, `persistence_typed_attrs.py` in the
        same package legitimately contains Thai, and the repository's own
        cp874 tripwire (`tools_bridge/pf_gate_preflight.py`) is what covers
        the file globally.  A whole-file ASCII assertion here would go red on
        another lane's legitimate edit, which is a trap, not a guard.
        """
        source = STORE_SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        lines = source.splitlines(keepends=True)
        found = 0
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef)
                    and node.name.startswith("write_speed_by_identity")):
                found += 1
                segment = "".join(lines[node.lineno - 1:node.end_lineno])
                with self.subTest(method=node.name):
                    segment.encode("ascii")
        self.assertEqual(found, 2, "both methods must be found and checked")


if __name__ == "__main__":
    unittest.main()
