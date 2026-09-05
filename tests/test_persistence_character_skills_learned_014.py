"""LANE-DB: `character_skills.source` widened to admit `'learned'`, plus
the `grant_learned_skill` write door.

`pf_bridge/notes_to_chief/
20260905_2119_LANE-CS-CORE-REQUEST-character-skills-learned-source-to-
lane-db.md`: LANE-CS's `skill_grant_wiring.learn_and_grant_skill` has
nowhere to write a skill a character LEARNS.
`migrations/014_character_skills_learned_source.sql` rebuilds
`character_skills` to admit the new value; `SQLiteStore.
grant_learned_skill` (this file's other half) is the first and only writer
of it.  There is no production caller of either yet (LANE-CS's own module
is Protocol-typed against a shape, not wired to this concrete store) -- so
nothing in this file is client-observable.
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
FOURTEEN = MIGRATIONS / "014_character_skills_learned_source.sql"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
_next_identity = iter(range(0x20002000, 0x20003000))


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


def _table_info(path):
    db = sqlite3.connect(str(path))
    try:
        return [
            tuple(row)
            for row in db.execute(
                "SELECT cid,name,type,\"notnull\",dflt_value,pk "
                "FROM pragma_table_info('character_skills')"
            )
        ]
    finally:
        db.close()


class _StoreFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()

    def _make_character(self, login="acct01", name="Test01"):
        account_id = self.store.ensure_account(login)
        self.sid = self.store.open_session(account_id)
        return self.store.create_character(
            account_id, name, name.casefold(), "fp-" + login,
            _build_wire, _HOME,
        )


class TheMigrationItselfTests(_StoreFixture):
    def test_014_is_on_disk_with_no_duplicate_version_number(self):
        self.assertTrue(FOURTEEN.exists(), FOURTEEN)
        versions = sorted(
            int(p.name[:3]) for p in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")
        )
        self.assertIn(14, versions)
        self.assertEqual(len(versions), len(set(versions)))

    def test_the_ledger_records_version_14(self):
        db = sqlite3.connect(str(self.path))
        try:
            versions = {
                int(r[0]) for r in db.execute("SELECT version FROM schema_migrations")
            }
        finally:
            db.close()
        self.assertIn(14, versions)

    def test_the_check_now_admits_starting_kit_and_learned_only(self):
        db = sqlite3.connect(str(self.path))
        try:
            ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='character_skills'"
            ).fetchone()[0]
        finally:
            db.close()
        self.assertIn("'starting_kit'", ddl)
        self.assertIn("'learned'", ddl)

    def test_a_third_unrecognised_source_is_still_refused(self):
        db = sqlite3.connect(str(self.path))
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO character_skills"
                    "(character_id,skill_id,source,granted_at)"
                    " VALUES (1,99,'trainer',?)",
                    ("2026-01-01T00:00:00+00:00",),
                )
        finally:
            db.close()

    def test_the_unique_constraint_and_columns_are_unchanged(self):
        columns = {row[1] for row in _table_info(self.path)}
        self.assertEqual(
            columns,
            {"id", "character_id", "skill_id", "source", "granted_at"},
        )
        db = sqlite3.connect(str(self.path))
        try:
            ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='character_skills'"
            ).fetchone()[0]
        finally:
            db.close()
        self.assertIn("UNIQUE(character_id,skill_id)", ddl.replace(" ", ""))


class TheRebuildPreservesExistingRowsTests(unittest.TestCase):
    """013-only tree -> grant a starting-kit skill -> reopen against the
    full tree (which applies 014) -> the row must survive byte-for-byte
    except for whatever the rebuild recipe itself cannot avoid touching
    (nothing, here -- `id`/`granted_at`/`source` all round-trip)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "state.sqlite3"
        self.upto_013 = self.root / "migrations_013"
        self.upto_013.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) <= 13:
                shutil.copy(path, self.upto_013 / path.name)

    def test_a_starting_kit_row_survives_the_014_rebuild_unchanged(self):
        store = SQLiteStore(self.path, self.upto_013)
        store.migrate()
        account_id = store.ensure_account("pre014")
        character = store.create_character(
            account_id, "Pre014", "pre014", "fp-pre014",
            _build_wire, _HOME,
        )
        store.grant_starting_skills(character.id, (99,))
        before = _raw_rows(self.path)
        self.assertEqual(len(before), 1)

        reopened = SQLiteStore(self.path, MIGRATIONS)
        reopened.migrate()
        after = _raw_rows(self.path)
        self.assertEqual(before, after)
        self.assertEqual(
            reopened.list_character_skills(character.id), (99,)
        )

    def test_foreign_key_integrity_holds_after_the_rebuild(self):
        store = SQLiteStore(self.path, self.upto_013)
        store.migrate()
        account_id = store.ensure_account("fk014")
        character = store.create_character(
            account_id, "Fk014", "fk014", "fp-fk014", _build_wire, _HOME,
        )
        store.grant_starting_skills(character.id, (99,))
        SQLiteStore(self.path, MIGRATIONS).migrate()
        db = sqlite3.connect(str(self.path))
        try:
            db.execute("PRAGMA foreign_keys=ON")
            violations = db.execute(
                "SELECT * FROM pragma_foreign_key_check('character_skills')"
            ).fetchall()
        finally:
            db.close()
        self.assertEqual(violations, [])


class GrantLearnedSkillWritesAndReadsBackTests(_StoreFixture):
    def test_a_first_call_creates_a_learned_row(self):
        character = self._make_character()
        result = self.store.grant_learned_skill(character.id, 210)
        self.assertEqual(result, (210,))
        raw = _raw_rows(self.path)
        self.assertEqual(len(raw), 1)
        _id, character_id, skill_id, source, granted_at = raw[0]
        self.assertEqual(character_id, character.id)
        self.assertEqual(skill_id, 210)
        self.assertEqual(source, "learned")
        self.assertTrue(granted_at)

    def test_a_learned_grant_alongside_a_starting_kit_grant_coexist(self):
        character = self._make_character()
        self.store.grant_starting_skills(character.id, (99,))
        result = self.store.grant_learned_skill(character.id, 210)
        self.assertEqual(result, (99, 210))
        raw = {row[2]: row[3] for row in _raw_rows(self.path)}
        self.assertEqual(raw[99], "starting_kit")
        self.assertEqual(raw[210], "learned")

    def test_re_granting_the_same_learned_skill_is_idempotent(self):
        character = self._make_character()
        first = self.store.grant_learned_skill(character.id, 210)
        second = self.store.grant_learned_skill(character.id, 210)
        self.assertEqual(first, second)
        self.assertEqual(len(_raw_rows(self.path)), 1)

    def test_learning_a_skill_already_owned_as_starting_kit_is_a_no_op(self):
        """The shared `UNIQUE(character_id, skill_id)` constraint, not one
        scoped per `source`: a skill already granted -- however it was
        granted -- is already granted."""
        character = self._make_character()
        self.store.grant_starting_skills(character.id, (99,))
        result = self.store.grant_learned_skill(character.id, 99)
        self.assertEqual(result, (99,))
        raw = _raw_rows(self.path)
        self.assertEqual(len(raw), 1)
        self.assertEqual(raw[0][3], "starting_kit")  # source unchanged

    def test_two_characters_do_not_see_each_others_learned_skills(self):
        first = self._make_character("acct-first", "First1")
        second = self._make_character("acct-secnd", "Secnd1")
        self.store.grant_learned_skill(first.id, 210)
        self.assertEqual(self.store.list_character_skills(second.id), ())
        self.assertEqual(self.store.list_character_skills(first.id), (210,))

    def test_the_row_survives_a_brand_new_store_against_the_same_file(self):
        character = self._make_character()
        self.store.grant_learned_skill(character.id, 210)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(reopened.list_character_skills(character.id), (210,))


class GrantLearnedSkillRefusesBadInputBeforeWritingTests(_StoreFixture):
    def _assert_nothing_written(self):
        self.assertEqual(_raw_rows(self.path), [])

    def test_an_unknown_character_id_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.store.grant_learned_skill(999999, 210)
        self._assert_nothing_written()

    def test_a_soft_deleted_character_is_treated_as_unknown(self):
        character = self._make_character()
        self.store.soft_delete_character(self.sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.grant_learned_skill(character.id, 210)

    def test_a_bool_character_id_is_refused_not_coerced(self):
        for bad in (True, False):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    self.store.grant_learned_skill(bad, 210)
        self._assert_nothing_written()

    def test_a_bool_skill_id_is_refused_not_coerced(self):
        character = self._make_character()
        with self.assertRaises(TypeError):
            self.store.grant_learned_skill(character.id, True)
        self._assert_nothing_written()

    def test_a_skill_id_outside_u32_is_refused(self):
        character = self._make_character()
        for bad in (-1, 0x100000000):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.store.grant_learned_skill(character.id, bad)
        self._assert_nothing_written()

    def test_write_lock_timeout_replaces_a_raw_operational_error(self):
        # Same deterministic technique `test_store_skill_points.py::
        # test_write_lock_timeout_replaces_a_raw_operational_error` uses.
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
                self.store.grant_learned_skill(character.id, 210)
        self._assert_nothing_written()


if __name__ == "__main__":
    unittest.main()
