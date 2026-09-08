"""LANE-DB: `character_skills.source` widened to admit `'gm_grant'`, plus
the `grant_gm_skills` bulk write door.

`pf_bridge/NOW.md` / `PANYA 20260908_1455` (restated by `1541`): a skill
practice ground for GM ACCOUNTS ONLY -- `/skill all` grants every skill
regardless of `n_LEVEL_LEARN`.  This lane's half of that order is the row
that survives the relog: `migrations/018_character_skills_gm_grant_
source.sql` widens the `source` CHECK, and `SQLiteStore.grant_gm_skills` is
the first and only writer of the new value.

NOTHING HERE IS CLIENT-OBSERVABLE YET.  The GM command that would call this
door is LANE-GM's (`NOW.md`: "LANE-GM first job = 1455: `/job` + `/skill
all` + a refusal test"), and no caller in `runtime.py` or `gm/` reaches
this method this round.  What these tests measure is the DATABASE half: the
rows land, they land once, they land with the right provenance, and they
are still there after the store is torn down and reopened.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position       # noqa: E402
from pirateforce_foundation.store import (               # noqa: E402
    SQLiteStore,
    WriteLockTimeout,
)

MIGRATIONS = ROOT / "migrations"
EIGHTEEN = MIGRATIONS / "018_character_skills_gm_grant_source.sql"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
_next_identity = iter(range(0x2000A000, 0x2000B000))


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


def _raw_rows(path):
    db = sqlite3.connect(str(path))
    try:
        return [
            tuple(row)
            for row in db.execute(
                "SELECT id,character_id,skill_id,source,granted_at "
                "FROM character_skills ORDER BY id"
            )
        ]
    finally:
        db.close()


class _StoreFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()

    def _make_character(self, login="gmacct01", name="Gm01"):
        account_id = self.store.ensure_account(login)
        self.sid = self.store.open_session(account_id)
        return self.store.create_character(
            account_id, name, name.casefold(), "fp-" + login,
            _build_wire, _HOME,
        )

    def _sources(self, character_id):
        db = sqlite3.connect(str(self.path))
        try:
            return {
                (int(r[0]), str(r[1]))
                for r in db.execute(
                    "SELECT skill_id,source FROM character_skills "
                    "WHERE character_id=?",
                    (character_id,),
                )
            }
        finally:
            db.close()


class TheMigrationItselfTests(_StoreFixture):
    def test_018_is_on_disk_with_no_duplicate_version_number(self):
        self.assertTrue(EIGHTEEN.exists(), EIGHTEEN)
        versions = sorted(
            int(p.name[:3]) for p in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")
        )
        self.assertIn(18, versions)
        self.assertEqual(len(versions), len(set(versions)))

    def test_the_ledger_records_version_18(self):
        db = sqlite3.connect(str(self.path))
        try:
            versions = {
                int(r[0])
                for r in db.execute("SELECT version FROM schema_migrations")
            }
        finally:
            db.close()
        self.assertIn(18, versions)

    def test_the_check_now_admits_three_sources_and_no_more(self):
        db = sqlite3.connect(str(self.path))
        try:
            ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='character_skills'"
            ).fetchone()[0]
        finally:
            db.close()
        for value in ("'starting_kit'", "'learned'", "'gm_grant'"):
            self.assertIn(value, ddl)

    def test_a_fourth_unrecognised_source_is_still_refused(self):
        character = self._make_character()
        db = sqlite3.connect(str(self.path))
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO character_skills"
                    "(character_id,skill_id,source,granted_at)"
                    " VALUES (?,99,'trainer',?)",
                    (character.id, "2026-01-01T00:00:00+00:00"),
                )
        finally:
            db.close()

    def test_the_columns_unique_constraint_and_index_are_unchanged(self):
        db = sqlite3.connect(str(self.path))
        try:
            columns = {
                str(r[1])
                for r in db.execute(
                    "SELECT cid,name FROM pragma_table_info('character_skills')"
                )
            }
            ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='character_skills'"
            ).fetchone()[0]
            indexes = {
                str(r[0])
                for r in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND tbl_name='character_skills' AND sql IS NOT NULL"
                )
            }
        finally:
            db.close()
        self.assertEqual(
            columns,
            {"id", "character_id", "skill_id", "source", "granted_at"},
        )
        self.assertIn("UNIQUE(character_id,skill_id)", ddl.replace(" ", ""))
        self.assertEqual(indexes, {"character_skills_by_character"})


class TheRebuildPreservesExistingRowsTests(unittest.TestCase):
    """A `017` tree with real rows in it -> reopen against the full tree
    (which applies `018`) -> every row must cross byte-for-byte."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "state.sqlite3"
        self.upto_017 = self.root / "migrations_017"
        self.upto_017.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) <= 17:
                shutil.copy(path, self.upto_017 / path.name)

    def test_rows_of_both_older_sources_survive_the_018_rebuild(self):
        store = SQLiteStore(self.path, self.upto_017)
        store.migrate()
        account_id = store.ensure_account("pre018")
        character = store.create_character(
            account_id, "Pre018", "pre018", "fp-pre018",
            _build_wire, _HOME,
        )
        store.grant_starting_skills(character.id, (99, 210))
        store.grant_learned_skill(character.id, 311)
        before = _raw_rows(self.path)
        self.assertEqual(len(before), 3)
        self.assertEqual(
            {row[3] for row in before}, {"starting_kit", "learned"}
        )

        reopened = SQLiteStore(self.path, MIGRATIONS)
        reopened.migrate()
        self.assertEqual(_raw_rows(self.path), before)
        self.assertEqual(
            reopened.list_character_skills(character.id), (99, 210, 311)
        )

    def test_foreign_key_integrity_holds_after_the_rebuild(self):
        store = SQLiteStore(self.path, self.upto_017)
        store.migrate()
        account_id = store.ensure_account("fk018")
        character = store.create_character(
            account_id, "Fk018", "fk018", "fp-fk018", _build_wire, _HOME,
        )
        store.grant_starting_skills(character.id, (99,))
        SQLiteStore(self.path, MIGRATIONS).migrate()
        db = sqlite3.connect(str(self.path))
        try:
            db.execute("PRAGMA foreign_keys=ON")
            violations = list(
                db.execute(
                    "SELECT * FROM pragma_foreign_key_check('character_skills')"
                )
            )
        finally:
            db.close()
        self.assertEqual(violations, [])

    def test_a_second_boot_does_not_rebuild_again(self):
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        db = sqlite3.connect(str(self.path))
        try:
            first = db.execute(
                "SELECT applied_at,checksum FROM schema_migrations "
                "WHERE version=18"
            ).fetchone()
        finally:
            db.close()
        SQLiteStore(self.path, MIGRATIONS).migrate()
        db = sqlite3.connect(str(self.path))
        try:
            second = db.execute(
                "SELECT applied_at,checksum FROM schema_migrations "
                "WHERE version=18"
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(tuple(first), tuple(second))


class TheGmGrantDoorTests(_StoreFixture):
    def test_many_ids_land_in_one_call(self):
        character = self._make_character()
        ids = tuple(range(1000, 1300))
        self.assertEqual(
            self.store.grant_gm_skills(character.id, ids), ids
        )
        self.assertEqual(
            self.store.list_character_skills(character.id), ids
        )

    def test_every_row_this_door_writes_says_gm_grant(self):
        character = self._make_character()
        self.store.grant_gm_skills(character.id, (7, 8))
        self.assertEqual(
            self._sources(character.id),
            {(7, "gm_grant"), (8, "gm_grant")},
        )

    def test_a_second_identical_grant_writes_nothing_and_raises_nothing(self):
        character = self._make_character()
        self.store.grant_gm_skills(character.id, (7, 8, 9))
        before = _raw_rows(self.path)
        self.assertEqual(
            self.store.grant_gm_skills(character.id, (7, 8, 9)), (7, 8, 9)
        )
        self.assertEqual(_raw_rows(self.path), before)

    def test_an_overlapping_grant_adds_only_what_is_missing(self):
        character = self._make_character()
        self.store.grant_gm_skills(character.id, (7, 8))
        self.assertEqual(
            self.store.grant_gm_skills(character.id, (8, 9)), (7, 8, 9)
        )
        self.assertEqual(len(_raw_rows(self.path)), 3)

    def test_a_skill_already_owned_keeps_the_provenance_it_had(self):
        """The row the character was BORN with does not become a GM grant
        because an operator ran `/skill all` over it."""
        character = self._make_character()
        self.store.grant_starting_skills(character.id, (99,))
        self.store.grant_learned_skill(character.id, 210)
        self.store.grant_gm_skills(character.id, (99, 210, 311))
        self.assertEqual(
            self._sources(character.id),
            {(99, "starting_kit"), (210, "learned"), (311, "gm_grant")},
        )

    def test_a_duplicate_id_inside_one_call_is_folded_not_refused(self):
        character = self._make_character()
        self.assertEqual(
            self.store.grant_gm_skills(character.id, (7, 7, 8, 7)), (7, 8)
        )
        self.assertEqual(len(_raw_rows(self.path)), 2)

    def test_the_grant_survives_a_relog(self):
        character = self._make_character()
        self.store.grant_gm_skills(character.id, (7, 8, 9))
        self.store.close_session(self.sid)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(
            reopened.list_character_skills(character.id), (7, 8, 9)
        )

    def test_two_characters_do_not_see_each_others_grants(self):
        first = self._make_character()
        second = self._make_character(login="gmacct02", name="Gm02")
        self.store.grant_gm_skills(first.id, (7, 8))
        self.store.grant_gm_skills(second.id, (9,))
        self.assertEqual(self.store.list_character_skills(first.id), (7, 8))
        self.assertEqual(self.store.list_character_skills(second.id), (9,))


class TheGmGrantDoorRefusesTests(_StoreFixture):
    def _assert_nothing_written(self):
        self.assertEqual(_raw_rows(self.path), [])

    def test_an_empty_sequence_is_refused(self):
        character = self._make_character()
        for empty in ((), []):
            with self.assertRaises(ValueError):
                self.store.grant_gm_skills(character.id, empty)
        self._assert_nothing_written()

    def test_a_non_sequence_is_refused(self):
        character = self._make_character()
        for bad in ("789", b"789", 7, None, {7: 8}, {7, 8}):
            with self.assertRaises(TypeError):
                self.store.grant_gm_skills(character.id, bad)
        self._assert_nothing_written()

    def test_a_bool_character_id_is_refused(self):
        with self.assertRaises(TypeError):
            self.store.grant_gm_skills(True, (7,))
        self._assert_nothing_written()

    def test_a_bool_or_float_skill_id_is_refused(self):
        character = self._make_character()
        for bad in (True, 7.0, "7", None):
            with self.assertRaises(TypeError):
                self.store.grant_gm_skills(character.id, (bad,))
        self._assert_nothing_written()

    def test_an_id_outside_the_u32_range_is_refused(self):
        character = self._make_character()
        for bad in (-1, 0x100000000):
            with self.assertRaises(ValueError):
                self.store.grant_gm_skills(character.id, (bad,))
        self._assert_nothing_written()

    def test_one_bad_id_refuses_the_whole_batch(self):
        """All-or-nothing: the valid ids in front of the bad one are not
        written, because every id is checked before the transaction opens."""
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.grant_gm_skills(character.id, (7, 8, -1, 9))
        self._assert_nothing_written()

    def test_an_unknown_character_is_refused(self):
        with self.assertRaises(KeyError):
            self.store.grant_gm_skills(9_999_999, (7,))
        self._assert_nothing_written()

    def test_a_soft_deleted_character_is_refused(self):
        character = self._make_character()
        self.store.soft_delete_character(self.sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.grant_gm_skills(character.id, (7,))
        self._assert_nothing_written()

    def test_a_locked_database_raises_write_lock_timeout(self):
        """The same shim `test_persistence_character_skills_learned_014.py`
        uses against `grant_learned_skill`, for the same reason: a raw
        `sqlite3.OperationalError` out of a write door is a leak."""
        from unittest import mock

        character = self._make_character()

        class _RaisesOnFirstBeginImmediate:
            def __init__(self, real):
                object.__setattr__(self, "_real", real)
                object.__setattr__(self, "_raised", False)

            def execute(self, sql, *args, **kwargs):
                if sql == "BEGIN IMMEDIATE" and not self._raised:
                    object.__setattr__(self, "_raised", True)
                    raise sqlite3.OperationalError("database is locked")
                return self._real.execute(sql, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self._real, name)

            def __setattr__(self, name, value):
                setattr(self._real, name, value)

        real_connect = sqlite3.connect

        def flaky_connect(*args, **kwargs):
            return _RaisesOnFirstBeginImmediate(real_connect(*args, **kwargs))

        with mock.patch("sqlite3.connect", side_effect=flaky_connect):
            with self.assertRaises(WriteLockTimeout):
                self.store.grant_gm_skills(character.id, (7, 8))
        self._assert_nothing_written()


class TheSiblingDoorsAreUntouchedTests(_StoreFixture):
    """This lane may ADD a method to `store.py` but must never change the
    behaviour of one already there.  These are the two the new door sits
    between, measured after `018` rather than before it."""

    def test_grant_starting_skills_still_writes_starting_kit(self):
        character = self._make_character()
        self.assertEqual(
            self.store.grant_starting_skills(character.id, (99, 210)),
            (99, 210),
        )
        self.assertEqual(
            self._sources(character.id),
            {(99, "starting_kit"), (210, "starting_kit")},
        )

    def test_grant_learned_skill_still_writes_learned(self):
        character = self._make_character()
        self.assertEqual(
            self.store.grant_learned_skill(character.id, 311), (311,)
        )
        self.assertEqual(self._sources(character.id), {(311, "learned")})

    def test_both_siblings_still_refuse_an_empty_or_bad_argument(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.grant_starting_skills(character.id, ())
        with self.assertRaises(ValueError):
            self.store.grant_learned_skill(character.id, -1)
        self.assertEqual(_raw_rows(self.path), [])


if __name__ == "__main__":
    unittest.main()
