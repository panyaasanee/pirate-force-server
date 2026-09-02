"""LANE-DB: the door LANE-GM asked for, and the one property that makes it
usable -- `None` means the row did not change.

WHY THIS FILE EXISTS.  `/speed` composes a frame today and writes no row
(`pf_bridge/notes_to_chief/20260901_2213`), so a speed survives exactly as
long as the session does.  LANE-GM asked this lane for the store half in
`20260902_0017_LANE-GM-TO-LANE-DB-request-speed-persistence-method.md`, with
a shape it had to have: the identity pair as the key (that lane holds no row
id), no exception across the boundary, and the value handed back read from
the row rather than echoed from the caller.  This file grades
`SQLiteStore.write_speed_by_identity` against that letter.

WHAT IT PROVES (wire/DB layer only, against a real migrated database):

1. **A refused call writes nothing.**  Every refusal path -- a bad identity,
   a bad value, a lost write, a read-back that disagrees, a locked database
   -- comes back `None` with the row byte-for-byte as it was, `updated_at`
   included.  Two of those paths are driven by SQL triggers rather than by
   argument, because they cannot be reached from the outside.
2. **`True` is not the character whose identity is 1.**  SQLite binds a bool
   as an integer; the door refuses it before the lookup, and the test builds
   the character that would otherwise be written.
3. **What comes back is the row's number.**  `400.1` is stored, read back and
   returned as the f32 the client will see, and it survives a reopen of the
   database from a new `SQLiteStore`.
4. **It does not raise.**  A hostile-input sweep asserts the door returns
   `None` rather than propagating anything.

WHAT IT DOES NOT PROVE.  Nothing here is client-observable: no frame is
composed, nothing is sent, and no player moves faster because of it.  Every
database in this file is built in a `TemporaryDirectory`; the owner's
canonical database is never opened.  `COO-DECISION 20260902_2147` stands --
neither `/speed` lock is released by a store method with no caller -- and
this file deliberately does NOT pin "nothing calls this door", for the reason
`SQLiteStore.read_character_vitals_or_none`'s docstring gives: the day the
asking lane wires it, a pin would turn that lane's PR red for doing the thing
the door exists for.

WHY EVERY NUMBER HERE AVOIDS `400.0`.  `migrations/009` gives `speed_walk`
the DEFAULT `400.0`, which is also the constant the composer hardcodes
(`COO-DECISION 20260903_0054`), so a test written with `400.0` passes just as
well against a door that was deleted.  No assertion in this file uses it as
the written value.
"""

import contextlib
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_typed_attrs as typed_attrs  # noqa: E402,E501
from pirateforce_foundation import store as store_module  # noqa: E402
from pirateforce_foundation.store import Position, SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"

#: Not `400.0`, and not the default of any column -- see the module docstring.
SPEED = 512.5

#: A value SQLite stores exactly as handed over but which is NOT the double
#: the caller typed: `validate` rounds it to float32 first.
SPEED_ROUNDED_BY_F32 = 400.1


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


def _build_wire_identity_one(selector):
    """The character an unguarded `identity_lo=True` would find and write."""
    return b"wire", b"avatar", 1, 0


@contextlib.contextmanager
def raw(path):
    """A raw connection that is committed AND CLOSED.

    Same wart and same reason as `tests/test_persistence_vitals_heal.py`: a
    bare `with sqlite3.connect(...)` commits without closing, which is free on
    Linux and takes the Windows gate red at `TemporaryDirectory` cleanup.
    """
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


class _StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 10.0, 20.0, 30.0, heading=0.0)
        self.account_id = self.store.ensure_account("speed")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "SpeedChar", "speedchar",
            "fingerprint-speed", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)
        self.identity = (self.character.identity_lo, self.character.identity_hi)

    def _row(self, character_id=None):
        """`speed_walk` AND `updated_at`: a refusal must move neither."""
        with raw(self.path) as db:
            return db.execute(
                "SELECT speed_walk,updated_at FROM characters WHERE id=?",
                (self.character.id if character_id is None else character_id,),
            ).fetchone()

    def _write(self, *args):
        return self.store.write_speed_by_identity(*args)


class WritesTheRowTests(_StoreCase):
    """The successful call, measured on disk rather than in the return."""

    def test_it_returns_the_wire_field_index_and_the_value(self):
        self.assertEqual(self._write(*self.identity, SPEED), {7: SPEED})

    def test_the_key_is_derived_from_the_column_table_not_typed_here(self):
        self.assertEqual(
            typed_attrs.TYPED_COLUMNS["speed_walk"].x,
            store_module.SPEED_WALK_FIELD_X,
        )

    def test_the_value_is_on_disk_after_the_call(self):
        before = self._row()
        self._write(*self.identity, SPEED)
        after = self._row()
        self.assertEqual(after["speed_walk"], SPEED)
        self.assertNotEqual(after["updated_at"], before["updated_at"])

    def test_it_survives_reopening_the_database(self):
        self._write(*self.identity, SPEED)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(
            reopened.read_typed_attributes(self.character.id)["speed_walk"],
            SPEED,
        )

    def test_what_comes_back_is_the_rows_f32_not_the_callers_double(self):
        returned = self._write(*self.identity, SPEED_ROUNDED_BY_F32)
        rounded = typed_attrs.as_f32(SPEED_ROUNDED_BY_F32)
        self.assertNotEqual(rounded, SPEED_ROUNDED_BY_F32)
        self.assertEqual(returned, {7: rounded})
        self.assertEqual(self._row()["speed_walk"], rounded)

    def test_a_second_call_overwrites_the_first(self):
        self._write(*self.identity, SPEED)
        self.assertEqual(self._write(*self.identity, 700.0), {7: 700.0})
        self.assertEqual(self._row()["speed_walk"], 700.0)

    def test_zero_is_a_value_and_is_accepted(self):
        # Stated rather than assumed: `0.0` is not an absence on this wire
        # (`tests/test_npc_gait_wire.py` pins that), so the door stores it.
        # What is refused is a nonzero number that BECOMES zero as an f32 --
        # `RefusesTheValueTests` covers that one.
        self.assertEqual(self._write(*self.identity, 0.0), {7: 0.0})
        self.assertEqual(self._row()["speed_walk"], 0.0)

    def test_it_writes_only_the_character_it_was_asked_for(self):
        other = self.store.create_character(
            self.account_id, "OtherChar", "otherchar",
            "fingerprint-other", _build_wire, self.home,
        )
        before = self._row(other.id)
        self._write(*self.identity, SPEED)
        self.assertEqual(dict(self._row(other.id)), dict(before))


class _RefusalCase(_StoreCase):
    """A refusal is `None` AND an untouched row -- asserted together."""

    def assertRefused(self, *args):
        before = dict(self._row())
        self.assertIsNone(self._write(*args))
        self.assertEqual(dict(self._row()), before)


class RefusesTheIdentityTests(_RefusalCase):
    def test_an_identity_nobody_holds(self):
        self.assertRefused(0x7FFFFFFF, 0, SPEED)

    def test_the_right_lo_with_the_wrong_hi(self):
        self.assertRefused(self.identity[0], 1, SPEED)

    def test_a_soft_deleted_character(self):
        # A second character, because `soft_delete_character` refuses one an
        # open session has selected -- and this lane may not change it.
        gone = self.store.create_character(
            self.account_id, "GoneChar", "gonechar",
            "fingerprint-gone", _build_wire, self.home,
        )
        self.store.soft_delete_character(self.sid, gone.selector)
        before = dict(self._row(gone.id))
        self.assertIsNone(
            self._write(gone.identity_lo, gone.identity_hi, SPEED))
        self.assertEqual(dict(self._row(gone.id)), before)

    def test_a_bool_is_not_the_character_whose_identity_is_one(self):
        one = self.store.create_character(
            self.account_id, "IdentityOne", "identityone",
            "fingerprint-one", _build_wire_identity_one, self.home,
        )
        self.assertEqual((one.identity_lo, one.identity_hi), (1, 0))
        before = dict(self._row(one.id))
        self.assertIsNone(self._write(True, False, SPEED))
        self.assertEqual(dict(self._row(one.id)), before)

    def test_a_float_that_compares_equal_to_the_identity(self):
        self.assertRefused(float(self.identity[0]), 0.0, SPEED)

    def test_out_of_range_and_negative_and_non_numeric(self):
        for lo in (-1, 0x100000000, "1", None, 1.5):
            with self.subTest(lo=lo):
                self.assertRefused(lo, 0, SPEED)


class TheLookupIsTheACTIVERowTests(_StoreCase):
    """`migrations/004` frees the identity slot when a character is soft
    deleted, so the SAME pair can be held by a dead row and a live one at
    once.  These two tests are what make the `deleted_at IS NULL` in the
    LOOKUP load-bearing rather than decorative: the UPDATE carries the same
    predicate, so dropping it from the SELECT alone leaves every refusal test
    green while the door stops working for a REUSED identity.
    """

    def setUp(self):
        super().setUp()
        # `soft_delete_character` refuses a character an OPEN session has
        # selected, and there is no deselect door; the session is closed and
        # a second one opened instead.  Neither method is touched by this
        # lane -- both are used exactly as they are.
        self.store.close_session(self.sid)
        self.sid = self.store.open_session(self.account_id)
        self.store.soft_delete_character(self.sid, self.character.selector)
        self.reborn = self.store.create_character(
            self.account_id, "RebornChar", "rebornchar",
            "fingerprint-reborn", _build_wire, self.home,
        )

    def test_the_dead_row_and_the_live_one_really_share_the_identity(self):
        self.assertEqual(
            (self.reborn.identity_lo, self.reborn.identity_hi), self.identity)
        self.assertNotEqual(self.reborn.id, self.character.id)

    def test_the_write_lands_on_the_live_row_and_not_the_dead_one(self):
        dead_before = dict(self._row(self.character.id))
        self.assertEqual(self._write(*self.identity, SPEED), {7: SPEED})
        self.assertEqual(self._row(self.reborn.id)["speed_walk"], SPEED)
        self.assertEqual(dict(self._row(self.character.id)), dead_before)


class ADictMeansAWriteLandedTests(_StoreCase):
    """The other half of "`None` means nothing was written": a call that
    returns a number must have written one.  The trap is a row that ALREADY
    holds the value -- there the read-back agrees with the caller and only
    the row count knows the UPDATE never happened.
    """

    def test_a_write_that_lands_nowhere_is_not_reported_as_a_write(self):
        self.assertEqual(self._write(*self.identity, SPEED), {7: SPEED})
        with raw(self.path) as db:
            db.execute(
                "CREATE TRIGGER refuse_second BEFORE UPDATE OF speed_walk "
                "ON characters BEGIN SELECT RAISE(IGNORE); END"
            )
        before = dict(self._row())
        self.assertIsNone(self._write(*self.identity, SPEED))
        self.assertEqual(dict(self._row()), before)


class RefusesTheValueTests(_RefusalCase):
    def test_every_value_the_wire_encoder_could_not_carry(self):
        for speed in (
            True, False, None, "512.5", b"512.5", object(),
            float("nan"), float("inf"), float("-inf"),
            1e300, -1e300,
            1e-300,  # nonzero, but exactly 0.0 as an f32
        ):
            with self.subTest(speed=speed):
                self.assertRefused(*self.identity, speed)

    def test_the_refusal_is_the_same_one_validate_makes(self):
        # The door owns no range of its own: it borrows the column's.  If
        # this drifts, the door has grown a private opinion about the value.
        with self.assertRaises(typed_attrs.TypedAttrError):
            typed_attrs.validate("speed_walk", 1e-300)


class TheTransactionRollsBackTests(_RefusalCase):
    """The two branches that cannot be reached by argument, driven by
    triggers -- and both of them prove the same sentence: the row is
    unchanged, INCLUDING the write the trigger itself made."""

    def test_a_write_that_matches_no_row_is_refused(self):
        with raw(self.path) as db:
            db.execute(
                "CREATE TRIGGER refuse_speed BEFORE UPDATE OF speed_walk "
                "ON characters BEGIN SELECT RAISE(IGNORE); END"
            )
        self.assertRefused(*self.identity, SPEED)

    def test_a_read_back_that_disagrees_is_refused_and_rolled_back(self):
        with raw(self.path) as db:
            db.execute(
                "CREATE TRIGGER rewrite_speed AFTER UPDATE OF speed_walk "
                "ON characters BEGIN UPDATE characters SET speed_walk=1.25 "
                "WHERE id=NEW.id AND speed_walk<>1.25; END"
            )
        before = dict(self._row())
        self.assertIsNone(self._write(*self.identity, SPEED))
        after = dict(self._row())
        self.assertEqual(after, before)
        self.assertNotEqual(after["speed_walk"], 1.25)

    def test_a_row_that_is_gone_at_read_back_is_refused(self):
        # An unselected character: `sessions.selected_character_id` has no
        # ON DELETE rule, so the trigger below could not delete a selected
        # one without tripping the foreign key first, which is a different
        # branch than the one this test is for.
        victim = self.store.create_character(
            self.account_id, "VictimChar", "victimchar",
            "fingerprint-victim", _build_wire, self.home,
        )
        with raw(self.path) as db:
            db.execute(
                "CREATE TRIGGER vanish_row AFTER UPDATE OF speed_walk "
                "ON characters BEGIN DELETE FROM characters WHERE id=NEW.id; END"
            )
        before = dict(self._row(victim.id))
        self.assertIsNone(
            self._write(victim.identity_lo, victim.identity_hi, SPEED))
        with raw(self.path) as db:
            still = db.execute(
                "SELECT speed_walk,updated_at FROM characters WHERE id=?",
                (victim.id,),
            ).fetchone()
        self.assertIsNotNone(still, "the delete was rolled back with the write")
        self.assertEqual(dict(still), before)


class ALockedDatabaseIsARefusalTests(_StoreCase):
    """A database another writer holds is `None`, not a raise and not a wait
    long enough to stall a strictly serial server
    (`pf_bridge/FINDINGS_R18_SERVER_IS_STRICTLY_SERIAL.md`).

    It costs the `busy_timeout` of one attempt (5 s) and that is why there is
    exactly one test here rather than one per branch.
    """

    def test_it_returns_none_and_writes_nothing(self):
        holding = threading.Event()
        released = threading.Event()

        def hold():
            # Opened INSIDE the thread: a sqlite3 connection may only be used
            # by the thread that made it.
            holder = sqlite3.connect(self.path)
            try:
                holder.execute("BEGIN EXCLUSIVE")
                holder.execute(
                    "UPDATE characters SET updated_at=updated_at WHERE id=?",
                    (self.character.id,),
                )
                holding.set()
                released.wait(30)
                holder.rollback()
            finally:
                holder.close()

        thread = threading.Thread(target=hold)
        thread.start()
        try:
            self.assertTrue(holding.wait(10), "the lock was never taken")
            self.assertIsNone(
                self.store.write_speed_by_identity(*self.identity, SPEED))
        finally:
            released.set()
            thread.join(30)
        with raw(self.path) as db:
            row = db.execute(
                "SELECT speed_walk FROM characters WHERE id=?",
                (self.character.id,),
            ).fetchone()
        self.assertNotEqual(row["speed_walk"], SPEED)


class ItDoesNotRaiseTests(_StoreCase):
    """The letter's own requirement: nothing crosses back into `gm/`."""

    def test_no_input_in_this_sweep_raises(self):
        class Hostile:
            def __eq__(self, other):
                raise RuntimeError("comparison")

            def __index__(self):
                raise RuntimeError("index")

            def __float__(self):
                raise RuntimeError("float")

        hostile = Hostile()
        for args in (
            (hostile, 0, SPEED),
            (0, hostile, SPEED),
            (self.identity[0], self.identity[1], hostile),
            (2 ** 128, 0, SPEED),
            ([], {}, set()),
            (None, None, None),
        ):
            with self.subTest(args=repr(args)):
                try:
                    self.assertIsNone(self._write(*args))
                except Exception as exc:  # pragma: no cover - the failure IS the report
                    self.fail(f"the door raised {exc!r}")

    def test_a_database_whose_column_is_gone_is_a_refusal_not_a_raise(self):
        # Schema drift is indistinguishable from a refusal at this door, by
        # design and said out loud in its docstring: a caller that needs the
        # reason must use `write_typed_attributes`, which raises.
        with raw(self.path) as db:
            db.execute("ALTER TABLE characters RENAME COLUMN speed_walk TO gone")
        self.assertIsNone(self._write(*self.identity, SPEED))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
