"""LANE-DB: `/speed` gets a place to be REMEMBERED, addressed the way `gm/`
can actually address it.

WHAT THIS FILE IS THE EVIDENCE FOR.  `/speed` on `main` today composes a
frame and writes nothing (`NOW.md` GM-B: the speed column is on `main` but the value does not
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
import math
import os
import sqlite3
import struct
import sys
import tempfile
import unittest
from pathlib import Path

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
        self.assertEqual(value.value, 7)
        self.assertNotIsInstance(value.value, bool)

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
        declared = {
            name for name in dir(speed_id)
            if name.startswith("REASON_") and name != "REASONS"
        }
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

    def test_the_short_method_returns_exactly_the_block_of_the_long_one(self):
        """They cannot drift: one delegates to the other.  Pinned anyway --
        a future 'optimisation' that reimplements the short one is the shape
        this catches.
        """
        block = self.store.write_speed_by_identity(
            IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, 500.0
        )
        self.assertEqual(block, {7: 500.0})
        self.assertIsNone(
            self.store.write_speed_by_identity(999999, IDENTITY_HI, 500.0)
        )
        self.assertIsNone(
            self.store.write_speed_by_identity(
                IDENTITY_LO_FOR_SELECTOR_0, IDENTITY_HI, "fast"
            )
        )


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
        self.assertEqual(self.raw_row(), before, "the refused write rolled back")

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
        self.assertEqual(self.raw_row(), before, "the refused write rolled back")

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
        """Two predicates, not one.  Removing EITHER alone must be visible:
        the guard is the error message, the predicate is what makes the write
        impossible.  Same reasoning as `write_typed_attributes`, where an
        adversary pass landed a write on a soft-deleted row by deleting the
        guard while every test stayed green.
        """
        self.assertEqual(self.code.count("deleted_at IS NULL"), 3,
                         "the lookup, the UPDATE and the read-back each "
                         "carry it; a count of 2 means one was dropped")

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
        head = ast.unparse(ast.Module(
            body=[n for n in self.func.body if n.lineno < block.lineno],
            type_ignores=[],
        ))
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


if __name__ == "__main__":
    unittest.main()
