"""LANE-DB: the read-only door LANE-B asked for, next to
`write_speed_by_identity`.

WHY THIS FILE EXISTS.  `pf_bridge/notes_to_chief/20260905_1353_LANE-B-
CORE-REQUEST-store-read-for-a-characters-class-id.md` asked for a reader that
never guesses: `migrations/006` added `characters.class_id`,
`lifecycle.persist_class_id_from_starting_gear` writes it and
`persistence_class_id_backfill` writes it retroactively, but nothing in this
tree ever read it back.  This file grades
`SQLiteStore.read_class_id_by_identity` against that letter: `None` means
"no honest value" (no row, an ambiguous identity, an unmigrated schema, or a
column that is genuinely still NULL), never a guessed class.

WHAT IT PROVES (wire/DB layer only, against a real migrated database):

1. A `class_id` written through the REAL production writer,
   `write_typed_attributes`, comes back unchanged -- not just a value poked
   in with a raw `UPDATE` (see `ReadsTheRowTests`, which now round-trips
   through both, on purpose: the two are not interchangeable evidence, and a
   corpus that only ever went through the raw helper would leave the actual
   writer path unexercised while a docstring nearby claimed otherwise).
2. A NULL column (every character 006 does not seed) comes back `None`, not
   `0` and not any other number.
3. Every identity refusal `write_speed_by_identity` has -- unknown pair, bad
   hi with a good lo, a soft-deleted character, `True` mistaken for the
   character whose identity is `1`, out-of-range/non-numeric parts, two
   active rows sharing an identity (built by hand, same as that door's own
   test) -- is `None` here too, from the SAME `_require_identity_part` guard
   and the SAME `deleted_at IS NULL` predicate.
4. The lookup is the ACTIVE row when an identity is reused after a soft
   delete, exactly like the write door's own `TheLookupIsTheACTIVERowTests`.
5. A database that predates migration 006 (no `class_id` column at all) is a
   refusal, not a crash -- the same guard `list_character_ids_missing_class_id`
   and `read_typed_attributes` already carry.
6. Nothing here raises across the boundary -- INCLUDING a `self.connect()`
   or a read inside it that fails outright (a corrupted file, a locked
   database), not only a bad identity argument.  A `pf-adversary` pass
   caught an earlier draft that wrapped only the identity-part guard in
   `try/except`, leaving the `with self.connect()` block free to raise
   `sqlite3.DatabaseError` straight across this door's boundary while its
   sibling `write_speed_by_identity` correctly reported `None` for the same
   corrupted file (`DatabaseCannotBeReachedTests`).

WHAT IT DOES NOT PROVE.  Nothing client-observable: no frame is composed
and no attack pose changes because of it.  Every database in this file is
built in a `TemporaryDirectory`; the owner's canonical database is never
opened.  This file does not pin "nothing calls this door" -- the day LANE-B
wires it, a pin here would turn that lane's PR red for doing the thing the
door exists for.
"""

import contextlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.store import Position, SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"

#: Not `0` -- so a test that forgets to check for the difference between "the
#: seeded value" and "a class id that just happens to be zero" cannot pass by
#: accident.
CLASS_ID = 3


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


def _build_wire_identity_one(selector):
    """The character an unguarded `identity_lo=True` would find."""
    return b"wire", b"avatar", 1, 0


@contextlib.contextmanager
def raw(path):
    """A raw connection that is committed AND CLOSED -- same wart and same
    reason as `tests/test_store_speed_by_identity.py`'s own `raw`: a bare
    `with sqlite3.connect(...)` commits without closing, which is free on
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
        self.account_id = self.store.ensure_account("classid")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "ClassChar", "classchar",
            "fingerprint-classid", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)
        self.identity = (self.character.identity_lo, self.character.identity_hi)

    def _read(self, *args):
        return self.store.read_class_id_by_identity(*args)

    def _set_class_id(self, character_id, class_id):
        with raw(self.path) as db:
            db.execute(
                "UPDATE characters SET class_id=? WHERE id=?",
                (class_id, character_id),
            )


class ReadsTheRowTests(_StoreCase):
    def test_a_seeded_class_id_comes_back(self):
        self._set_class_id(self.character.id, CLASS_ID)
        self.assertEqual(self._read(*self.identity), CLASS_ID)

    def test_a_class_id_written_through_the_real_writer_comes_back_unchanged(self):
        # Not `_set_class_id` (a raw `UPDATE`): `write_typed_attributes` is
        # the production door this column is actually written through, and
        # it is a DIFFERENT code path (validates, takes `BEGIN IMMEDIATE`,
        # reads back inside its own transaction) than the raw helper every
        # other test in this file uses to seed the row.
        self.store.write_typed_attributes(
            self.character.id, {"class_id": CLASS_ID})
        self.assertEqual(self._read(*self.identity), CLASS_ID)

    def test_it_is_an_int_not_whatever_sqlite_handed_back(self):
        self._set_class_id(self.character.id, CLASS_ID)
        self.assertIs(type(self._read(*self.identity)), int)

    def test_it_reads_only_the_character_it_was_asked_for(self):
        other = self.store.create_character(
            self.account_id, "OtherChar", "otherchar",
            "fingerprint-other", _build_wire, self.home,
        )
        self._set_class_id(self.character.id, CLASS_ID)
        self._set_class_id(other.id, CLASS_ID + 1)
        self.assertEqual(self._read(*self.identity), CLASS_ID)

    def test_zero_is_a_class_id_and_is_returned(self):
        self._set_class_id(self.character.id, 0)
        self.assertEqual(self._read(*self.identity), 0)


class NullColumnIsNoneTests(_StoreCase):
    def test_an_unseeded_column_is_none_not_zero(self):
        # `migrations/006` gives `class_id` no default: a freshly created
        # character is NULL here until something writes it.
        self.assertIsNone(self._read(*self.identity))

    def test_it_stays_none_after_a_reopen(self):
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertIsNone(
            reopened.read_class_id_by_identity(*self.identity))


class RefusesTheIdentityTests(_StoreCase):
    def test_an_identity_nobody_holds(self):
        self.assertIsNone(self._read(0x7FFFFFFF, 0))

    def test_the_right_lo_with_the_wrong_hi(self):
        self.assertIsNone(self._read(self.identity[0], 1))

    def test_a_soft_deleted_character(self):
        gone = self.store.create_character(
            self.account_id, "GoneChar", "gonechar",
            "fingerprint-gone", _build_wire, self.home,
        )
        self._set_class_id(gone.id, CLASS_ID)
        self.store.soft_delete_character(self.sid, gone.selector)
        self.assertIsNone(
            self._read(gone.identity_lo, gone.identity_hi))

    def test_a_bool_is_not_the_character_whose_identity_is_one(self):
        one = self.store.create_character(
            self.account_id, "IdentityOne", "identityone",
            "fingerprint-one", _build_wire_identity_one, self.home,
        )
        self.assertEqual((one.identity_lo, one.identity_hi), (1, 0))
        self._set_class_id(one.id, CLASS_ID)
        self.assertIsNone(self._read(True, False))

    def test_a_float_that_compares_equal_to_the_identity(self):
        self._set_class_id(self.character.id, CLASS_ID)
        self.assertIsNone(self._read(float(self.identity[0]), 0.0))

    def test_out_of_range_and_negative_and_non_numeric(self):
        for lo in (-1, 0x100000000, "1", None, 1.5):
            with self.subTest(lo=lo):
                self.assertIsNone(self._read(lo, 0))


class TheLookupIsTheACTIVERowTests(_StoreCase):
    """Same fixture shape as `write_speed_by_identity`'s own -- an identity
    reused after a soft delete must resolve to the LIVE row, not the dead
    one, even when the dead row still carries a `class_id`.
    """

    def setUp(self):
        super().setUp()
        self._set_class_id(self.character.id, CLASS_ID)
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

    def test_the_read_resolves_to_the_live_row(self):
        # The live row has no class_id yet (a fresh character): the dead
        # row's CLASS_ID must not leak through.
        self.assertIsNone(self._read(*self.identity))
        self._set_class_id(self.reborn.id, CLASS_ID + 1)
        self.assertEqual(self._read(*self.identity), CLASS_ID + 1)


class TwoActiveRowsAreRefusedTests(_StoreCase):
    """`migrations/004`'s partial unique index makes this state
    unreachable through the public API -- built by hand, same as
    `write_speed_by_identity`'s own `TwoActiveRowsAreRefusedTests`.
    """

    def setUp(self):
        super().setUp()
        self.twin = self.store.create_character(
            self.account_id, "TwinChar", "twinchar",
            "fingerprint-twin", _build_wire, self.home,
        )
        self._set_class_id(self.character.id, CLASS_ID)
        self._set_class_id(self.twin.id, CLASS_ID + 1)
        with raw(self.path) as db:
            db.execute("DROP INDEX characters_active_identity")
            db.execute(
                "UPDATE characters SET identity_lo=?,identity_hi=? WHERE id=?",
                (*self.identity, self.twin.id),
            )

    def test_it_refuses_instead_of_picking_one(self):
        self.assertIsNone(self._read(*self.identity))


class SchemaMissingTheColumnIsARefusalTests(_StoreCase):
    def test_a_database_that_predates_migration_006_is_a_refusal(self):
        # Same shape `list_character_ids_missing_class_id` and
        # `read_typed_attributes` are already guarded against
        # (`pf_bridge/notes_to_chief/20260905_0233_...boot-crash-class-id-
        # backfill.md`): a column that does not exist has no honest value.
        with raw(self.path) as db:
            db.execute("ALTER TABLE characters RENAME COLUMN class_id TO gone")
        self.assertIsNone(self._read(*self.identity))


class DatabaseCannotBeReachedTests(_StoreCase):
    """The gap a `pf-adversary` pass found in an earlier draft: only the
    identity-part guard sat inside `try/except`, so anything `self.
    connect()` or the read itself raised -- a locked or corrupted database --
    crossed this door's boundary uncaught, while `write_speed_by_identity`
    (whose whole body is one `try`) correctly reports `None` for the exact
    same failure.  Reproduced concretely against a real, un-mocked
    `SQLiteStore` rather than assumed: writing garbage bytes over the
    database file on disk.
    """

    def test_a_corrupted_database_file_is_none_not_a_raise(self):
        self._set_class_id(self.character.id, CLASS_ID)
        with open(self.path, "r+b") as f:
            f.write(b"garbage-not-a-sqlite-file-header" * 4)
        # The sibling door reports the same failure as `None` -- this
        # asserts the two doors agree, not just that this one survives.
        self.assertIsNone(
            self.store.write_speed_by_identity(*self.identity, 5.0))
        self.assertIsNone(self._read(*self.identity))


class ItDoesNotRaiseTests(_StoreCase):
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
            (hostile, 0),
            (0, hostile),
            (2 ** 128, 0),
            ([], {}),
            (None, None),
        ):
            with self.subTest(args=repr(args)):
                try:
                    returned = self._read(*args)
                except Exception as exc:  # pragma: no cover - the failure IS the report
                    self.fail(f"the door raised {exc!r}")
                self.assertIsNone(returned)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
