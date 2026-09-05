"""LANE-DB: the starting-skill-kit persistence door -- grant, then read it
back.

`PANYA-DECISION 20260904_0328` piece 5 (`COO-ORDER 20260904_0329` item 5):
today a character's skill window is empty forever, including the basic
attack every class starts with.  `migrations/011_character_skills.sql` plus
`SQLiteStore.grant_starting_skills`/`list_character_skills` are the schema
and write/read halves this file measures.  There is no call site yet -- the
resolver (`persistence_starting_skills.resolve_starting_skill_ids`) and this
door exist; wiring the two together at character creation is chief's, the
same way piece 1's two hookups were -- so nothing in this file is
client-observable.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position       # noqa: E402
from pirateforce_foundation.store import SQLiteStore     # noqa: E402

MIGRATIONS = ROOT / "migrations"
ELEVEN = MIGRATIONS / "011_character_skills.sql"

#: The four starting-kit ids of the Gladiator (`class_catalog.
#: CLASS_ID_TO_STARTING_SKILL_IDS[1]`), typed independently here rather than
#: imported, so a drift between this fixture and that catalog fails this
#: file instead of the two silently agreeing forever.
GLADIATOR_STARTING_SKILLS = (111, 40000, 99, 110)

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)

#: Bumped for every character this file creates, so two characters (even in
#: two different accounts, both at selector 0) never collide on
#: `UNIQUE(identity_lo, identity_hi)` -- `create_character`'s own uniqueness
#: floor, unrelated to anything this file measures.
_next_identity = iter(range(0x20000001, 0x20001000))


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


def _table_info(path, table="character_skills"):
    db = sqlite3.connect(str(path))
    try:
        return [
            tuple(row)
            for row in db.execute(
                "SELECT cid,name,type,\"notnull\",dflt_value,pk "
                "FROM pragma_table_info(?)", (table,),
            )
        ]
    finally:
        db.close()


def _applied(path):
    db = sqlite3.connect(str(path))
    try:
        return sorted(
            int(row[0]) for row in db.execute("SELECT version FROM schema_migrations")
        )
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

    def test_011_is_on_disk_with_no_duplicate_version_number(self):
        # No longer "is the newest version": `012_ground_drops_taken_marker.
        # sql` (LANE-DB, round `p6x3ee`) landed after this file was written --
        # same relaxation `test_persistence_ground_drops_010.py` already made
        # for 010 once 011 passed it. This test's job is that 011 exists and
        # no version number repeats, not which one is newest.
        self.assertTrue(ELEVEN.exists(), ELEVEN)
        versions = sorted(
            int(p.name[:3]) for p in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")
        )
        self.assertIn(11, versions)
        self.assertEqual(len(versions), len(set(versions)))

    def test_the_ledger_records_version_11(self):
        self.assertIn(11, _applied(self.path))

    def test_applying_twice_changes_nothing(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(_applied(self.path).count(11), 1)
        self.assertEqual(_raw_rows(self.path), [])

    def test_an_edited_011_is_refused_on_a_database_that_applied_it(self):
        mutated = Path(self.tmp.name) / "mutated_migrations"
        mutated.mkdir()
        for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"):
            text = path.read_text(encoding="utf-8")
            if path.name == ELEVEN.name:
                text = text.replace(
                    "-- 011_character_skills.sql",
                    "-- 011 (edited after it was applied)",
                )
            (mutated / path.name).write_text(text, encoding="utf-8")
        with self.assertRaises(RuntimeError) as caught:
            SQLiteStore(self.path, mutated).migrate()
        self.assertIn("checksum mismatch", str(caught.exception))

    def test_no_existing_table_or_row_is_touched(self):
        """011 is a bare CREATE TABLE -- not a rebuild, not a backfill."""
        db = sqlite3.connect(str(self.path))
        try:
            after_ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='characters'"
            ).fetchone()[0]
        finally:
            db.close()

        ten_only = Path(self.tmp.name) / "ten_only.sqlite3"
        ten_only_migrations = Path(self.tmp.name) / "ten_only_migrations"
        ten_only_migrations.mkdir()
        for path in sorted(MIGRATIONS.glob("0[0-1][0-9]_*.sql")):
            if int(path.name[:3]) > 10:
                continue
            (ten_only_migrations / path.name).write_text(
                path.read_text(encoding="utf-8"), encoding="utf-8"
            )
        SQLiteStore(ten_only, ten_only_migrations).migrate()
        db = sqlite3.connect(str(ten_only))
        try:
            before_ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='characters'"
            ).fetchone()[0]
        finally:
            db.close()
        self.assertEqual(after_ddl, before_ddl)


class TheTableShapeTests(_StoreFixture):

    def test_the_columns_are_exactly_these(self):
        columns = {row[1] for row in _table_info(self.path)}
        self.assertEqual(
            columns,
            {"id", "character_id", "skill_id", "source", "granted_at"},
        )

    def test_the_unique_constraint_is_on_character_and_skill(self):
        db = sqlite3.connect(str(self.path))
        try:
            ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='character_skills'"
            ).fetchone()[0]
        finally:
            db.close()
        self.assertIn(
            "UNIQUE(character_id,skill_id)", ddl.replace(" ", ""),
        )

    def test_an_unknown_source_value_is_refused_by_the_check(self):
        # 'learned' used to be the unrecognised value this test picked --
        # `migrations/014_character_skills_learned_source.sql` (LANE-DB,
        # round `qul9wo`) widened the CHECK list to admit it, so this test
        # now picks a value that stays outside the list either way, to keep
        # testing "the CHECK still refuses an unrecognised source" rather
        # than a value that quietly stopped being unrecognised.
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


class TheGrantThenReadBackDoorTests(_StoreFixture):

    def test_a_fresh_character_starts_with_no_skills(self):
        character = self._make_character()
        self.assertEqual(self.store.list_character_skills(character.id), ())

    def test_granting_the_starting_kit_round_trips_in_order(self):
        character = self._make_character()
        result = self.store.grant_starting_skills(
            character.id, GLADIATOR_STARTING_SKILLS,
        )
        self.assertEqual(result, GLADIATOR_STARTING_SKILLS)
        self.assertEqual(
            self.store.list_character_skills(character.id),
            GLADIATOR_STARTING_SKILLS,
        )

    def test_the_raw_table_holds_the_source_and_a_timestamp(self):
        character = self._make_character()
        self.store.grant_starting_skills(character.id, (99,))
        raw = _raw_rows(self.path)
        self.assertEqual(len(raw), 1)
        _id, character_id, skill_id, source, granted_at = raw[0]
        self.assertEqual(character_id, character.id)
        self.assertEqual(skill_id, 99)
        self.assertEqual(source, "starting_kit")
        self.assertTrue(granted_at)

    def test_granting_the_same_kit_twice_is_idempotent_not_an_error(self):
        """The create-fingerprint retry shape: the same caller confirming
        the same fact twice must not raise and must not duplicate rows."""
        character = self._make_character()
        first = self.store.grant_starting_skills(
            character.id, GLADIATOR_STARTING_SKILLS,
        )
        second = self.store.grant_starting_skills(
            character.id, GLADIATOR_STARTING_SKILLS,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(_raw_rows(self.path)), 4)

    def test_granting_a_new_skill_later_adds_to_the_existing_set(self):
        character = self._make_character()
        self.store.grant_starting_skills(character.id, (99,))
        result = self.store.grant_starting_skills(character.id, (111,))
        self.assertEqual(result, (99, 111))

    def test_an_overlapping_reordered_regrant_touches_no_existing_row(self):
        """pf-adversary: `INSERT OR REPLACE` in place of `INSERT OR IGNORE`
        (`store.py`'s `grant_starting_skills`) passed every OTHER test in
        this file, because none of them re-granted a set that both repeats
        an existing id AND adds a new one in a different relative order.
        `OR REPLACE` deletes-then-reinserts a colliding row, which gives it
        a NEW `id` and a NEW `granted_at`, and (because SQLite's rowid
        ordering follows insertion, not the caller's argument order) moves
        it to the END of `ORDER BY id` -- silently breaking both the
        "no-op on a repeat" half of this method's own docstring and the
        "ordered by insertion" half.  This test re-grants 99 (already
        present) together with 200 (new) in an order where 99 comes SECOND
        in the call, and pins the untouched row by id and by timestamp, not
        only by its value -- an `id`/`granted_at` change would be invisible
        to a test that only checked `list_character_skills`'s returned
        values.
        """
        character = self._make_character()
        self.store.grant_starting_skills(character.id, (99, 111))
        before = {
            row[2]: row for row in _raw_rows(self.path)
            if row[1] == character.id
        }  # skill_id -> full raw row
        result = self.store.grant_starting_skills(character.id, (200, 99))
        self.assertEqual(result, (99, 111, 200))
        after = {
            row[2]: row for row in _raw_rows(self.path)
            if row[1] == character.id
        }
        for skill_id in (99, 111):
            with self.subTest(skill_id=skill_id):
                self.assertEqual(
                    after[skill_id], before[skill_id],
                    "a re-grant that repeats an existing skill id must not "
                    "touch that row's id or granted_at",
                )
        self.assertNotIn(200, before)
        self.assertIn(200, after)

    def test_two_characters_do_not_see_each_others_skills(self):
        first = self._make_character("acct-first", "First1")
        second = self._make_character("acct-secnd", "Secnd1")
        self.store.grant_starting_skills(first.id, (99,))
        self.assertEqual(self.store.list_character_skills(second.id), ())
        self.assertEqual(self.store.list_character_skills(first.id), (99,))

    def test_the_row_survives_a_brand_new_store_against_the_same_file(self):
        character = self._make_character()
        self.store.grant_starting_skills(character.id, (99,))
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(reopened.list_character_skills(character.id), (99,))


class TheDoorRefusesBadInputBeforeWritingTests(_StoreFixture):

    def _assert_nothing_written(self):
        self.assertEqual(_raw_rows(self.path), [])

    def test_an_unknown_character_id_raises_keyerror_on_grant(self):
        with self.assertRaises(KeyError):
            self.store.grant_starting_skills(999999, (99,))
        self._assert_nothing_written()

    def test_an_unknown_character_id_raises_keyerror_on_list(self):
        with self.assertRaises(KeyError):
            self.store.list_character_skills(999999)

    def test_a_bool_character_id_is_refused_not_coerced(self):
        """pf-adversary: `skill_id` and (in `persistence_starting_skills`)
        `class_id` were already bool-refused in this PR; `character_id` was
        not.  `sqlite3` binds python `True`/`False` as `1`/`0` with no
        complaint, so an uncaught bool here would silently read or write
        character id 1's / 0's row for a caller that passed a bool by
        mistake."""
        for bad in (True, False):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    self.store.grant_starting_skills(bad, (99,))
                with self.assertRaises(TypeError):
                    self.store.list_character_skills(bad)
        self._assert_nothing_written()

    def test_a_soft_deleted_character_is_treated_as_unknown(self):
        character = self._make_character()
        self.store.soft_delete_character(self.sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.grant_starting_skills(character.id, (99,))
        with self.assertRaises(KeyError):
            self.store.list_character_skills(character.id)

    def test_an_empty_sequence_is_refused(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.grant_starting_skills(character.id, ())
        self._assert_nothing_written()

    def test_a_non_sequence_is_refused(self):
        character = self._make_character()
        for bad in (99, "99", None, {99}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    self.store.grant_starting_skills(character.id, bad)
        self._assert_nothing_written()

    def test_a_bool_skill_id_is_refused_not_coerced(self):
        character = self._make_character()
        with self.assertRaises(TypeError):
            self.store.grant_starting_skills(character.id, (True,))
        self._assert_nothing_written()

    def test_a_skill_id_outside_u32_is_refused(self):
        character = self._make_character()
        for bad in (-1, 0x100000000):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.store.grant_starting_skills(character.id, (bad,))
        self._assert_nothing_written()

    def test_one_bad_id_in_a_batch_writes_nothing_of_the_batch(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.grant_starting_skills(character.id, (99, -1))
        self.assertEqual(self.store.list_character_skills(character.id), ())


if __name__ == "__main__":
    unittest.main()
