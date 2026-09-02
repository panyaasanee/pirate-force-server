"""LANE-DB: what `migrations/009_character_birth_defaults.sql` closed, and the
price it was allowed to charge for closing it.

WHAT 009 IS.  Four columns of `characters` gain a DEFAULT -- `level = 1`,
`hp_current = 100`, `hp_max = 100`, `speed_walk = 400.0` -- so a character
born on a fresh install holds numbers instead of NULL.  SQLite can only
attach a default at CREATE TABLE or ADD COLUMN time, so the file rebuilds the
table, which puts it in the one category the owner has a standing rule about
(`COO-DECISION 20260901_1112` point 3: a migration that touches existing rows
must land with an automatic pre-apply snapshot).  `COO-DECISION 20260902_1607`
approved it after the owner overruled the two earlier refusals herself, and
attached five conditions.  This file is where three of them are measured:
the snapshot really happening (not merely being called), the index and
constraint set surviving the rebuild proved by an automatic before/after
comparison rather than by eye, and the numbers being the ones `007` and `008`
already used rather than four new inventions.

WHY THE ASSERTIONS ARE NOT WRITTEN AS LITERALS WHERE THEY COULD BE DERIVED.
A number typed into a test is only right for the database it was typed for.
The schema comparison below reads `PRAGMA table_info` from a database built
by the REAL migration directory at 008 and compares it against the same
pragma after 009, in Python, independently of the guards inside the SQL file
-- so a guard that was written wrong cannot also grade itself.  The birth
values are compared against `pf_birth_state.default_birth()`, which derives
the three vitals from `persistence_vitals` and the speed from
`persistence_attr_compose.CLIENT_CONSTRUCTION_DEFAULTS[7]` -- the two modules
that own those numbers -- so a default that drifts from either is red here
even if the database is internally consistent.  It goes through the helper
rather than calling the birth-value function in `persistence_vitals` itself
because that function is deliberately held to one call site and a short
allow-list (`NewCharacterVitalsTests` in tests/test_persistence_vitals.py).

WHY IT ALSO MUTATES THE MIGRATION.  A guard that has never failed is a guess.
`TheGuardsInTheFileReallyFireTests` writes deliberately wrong versions of 009
into a throwaway migration directory -- one that drops an index, one that
backfills the existing rows, one that gives a seventeenth column a default,
one that loses a column's NOT NULL -- and asserts each is REFUSED and that the
database it was refused on still holds its pre-009 table.  Six guards, six
mutants that only that guard catches.

WHAT THIS FILE DOES NOT CLAIM.  It does not claim the four numbers are the
original game's; that is `NEW_CHARACTER_VITALS_LABEL`'s and RE-194's business
and neither is re-argued here.  It does not claim every character in an
existing database ends up with vitals: 009 is a DEFAULT and not a backfill, so
a character born in the window between the boot that applied 008 and the boot
that applies 009 still holds NULL, which is measured below by
`test_a_row_born_before_009_keeps_its_nulls` and reported to COO rather than
quietly fixed here.  And it does not reach the `--scene-load-scenario` boot
shape, which does not migrate at all.
"""
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

import pf_birth_state as birth_state  # noqa: E402

MIGRATIONS = ROOT / "migrations"
NINE = MIGRATIONS / "009_character_birth_defaults.sql"

#: The four columns 009 gives a default, and the three that had one before it
#: (from `001_initial.sql` and `004_character_soft_delete_reuse.sql`).
BIRTH_COLUMNS = ("level", "hp_current", "hp_max", "speed_walk")
PRE_EXISTING_DEFAULT_COLUMNS = ("identity_hi", "name_key", "create_fingerprint")

VETERAN = {"level": 9, "hp_current": 480, "hp_max": 500}


def _build_wire(selector):
    return b"wire-%d" % selector, b"avatar", 0x30000001 + selector, 0


def _build_wire_second_account(selector):
    return b"wire-b-%d" % selector, b"avatar", 0x40000001 + selector, 0


def _table_info(path, table="characters"):
    db = sqlite3.connect(str(path))
    try:
        return [tuple(row) for row in db.execute(
            "SELECT cid,name,type,\"notnull\",dflt_value,pk "
            "FROM pragma_table_info(?)", (table,))]
    finally:
        db.close()


def _indexes(path, table="characters"):
    db = sqlite3.connect(str(path))
    try:
        return sorted(
            (str(row[0]), row[1]) for row in db.execute(
                "SELECT name,sql FROM sqlite_master "
                "WHERE type='index' AND tbl_name=?", (table,)))
    finally:
        db.close()


def _all_rows(path):
    db = sqlite3.connect(str(path))
    try:
        return [tuple(row) for row in db.execute(
            "SELECT * FROM characters ORDER BY id")]
    finally:
        db.close()


def _applied(path):
    db = sqlite3.connect(str(path))
    try:
        return sorted(int(row[0]) for row in db.execute(
            "SELECT version FROM schema_migrations"))
    finally:
        db.close()


class _PreNineFixture(unittest.TestCase):
    """A database that stopped at 008, built by the REAL migration files.

    Copying the files rather than writing a schema by hand is the point: the
    checksum ledger the runner keeps is over the file bytes, so a hand-built
    schema would apply 009 against a table this repository never actually
    ships, and the before/after comparison would be graded against fiction.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "state.sqlite3"
        self.upto_008 = self.root / "migrations_008"
        self.upto_008.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) <= 8:
                shutil.copy(path, self.upto_008 / path.name)

    def _store_at_008(self):
        store = SQLiteStore(self.path, self.upto_008)
        store.migrate()
        return store

    def _store_at_009(self):
        return SQLiteStore(self.path, MIGRATIONS)

    def _mutated_dir(self, replacements):
        mutant_root = self.root / ("mutant_%d" % len(list(self.root.iterdir())))
        mutant_root.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            shutil.copy(path, mutant_root / path.name)
        text = NINE.read_text(encoding="utf-8")
        for old, new in replacements:
            self.assertIn(old, text, "the mutation target left the file")
            text = text.replace(old, new, 1)
        (mutant_root / NINE.name).write_text(text, encoding="utf-8")
        return mutant_root

    def _create(self, store, account_id, name, tag, build=_build_wire, x=1.0):
        return store.create_character(
            account_id, name, name.casefold(), "fingerprint-%s" % tag,
            build, Position(3, 0, x, 2.0, 3.0, heading=0.0))

    def _populate(self, store):
        """A veteran with real vitals, a rookie with none, on two accounts."""
        account_a = store.ensure_account("account-a")
        veteran = self._create(store, account_a, "Veteran", "veteran", x=1.0)
        store.write_typed_attributes(veteran.id, dict(VETERAN))
        rookie = self._create(store, account_a, "Rookie", "rookie", x=4.0)
        account_b = store.ensure_account("account-b")
        stranger = self._create(store, account_b, "Stranger", "stranger",
                                _build_wire_second_account, 7.0)
        deleted = self._create(store, account_b, "Ghost", "ghost",
                               _build_wire_second_account, 9.0)
        session = store.open_session(account_b)
        store.soft_delete_character(session, deleted.selector)
        store.close_session(session)
        return account_a, account_b, veteran, rookie, stranger, deleted


class ANewbornHoldsTheFourNumbersTests(_PreNineFixture):

    def test_a_character_born_on_a_fresh_install_holds_the_birth_defaults(self):
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        account = store.ensure_account("account-a")
        born = self._create(store, account, "Newborn", "newborn")
        self.assertEqual(
            store.read_typed_attributes(born.id),
            {"level": 1, "hp_current": 100, "hp_max": 100,
             "speed_walk": 400.0},
            "a character born on a fresh install after 009 must hold exactly "
            "the four adjudicated birth values and nothing else")

    def test_the_other_seventeen_typed_columns_are_still_absent(self):
        """The owner's rule, still standing: an unmeasured field is NULL.

        Not "zero", and not "absent from this assertion" -- the compose gate
        must still refuse a block for them by name, or 009 has traded the
        birth hole for the guessed zero `COO-DECISION 20260901_1059` forbids.
        """
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        account = store.ensure_account("account-a")
        born = self._create(store, account, "Newborn", "newborn")
        held = store.read_typed_attributes(born.id)
        unseeded = sorted(set(typed.TYPED_COLUMNS) - set(BIRTH_COLUMNS))
        self.assertEqual(len(unseeded), 17)
        for column in unseeded:
            with self.subTest(column=column):
                self.assertNotIn(column, held)
        db = sqlite3.connect(str(self.path))
        try:
            row = db.execute(
                "SELECT %s FROM characters WHERE id=?"
                % ",".join(unseeded), (born.id,)).fetchone()
        finally:
            db.close()
        self.assertEqual(list(row), [None] * 17,
                         "an unmeasured column holds NULL, never a zero")

    def test_the_numbers_are_the_ones_007_and_008_already_used(self):
        """Condition: the four values may not be new inventions.

        Read out of the SCHEMA (`dflt_value`) and compared against the two
        modules that own the numbers, so a default that drifts from them is
        red here even though the database would be perfectly consistent.
        """
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        defaults = {name: dflt for _, name, _, _, dflt, _
                    in _table_info(self.path)}
        # `pf_birth_state.default_birth()` and not the birth-value function
        # itself: `NewCharacterVitalsTests.test_only_the_ordered_call_site_
        # may_call_it` in tests/test_persistence_vitals.py holds that function
        # to ONE call site plus a short allow-list, and a new test file
        # calling it directly would spend that budget for nothing -- the
        # helper derives the three vitals from that same function and the
        # speed from `CLIENT_CONSTRUCTION_DEFAULTS[7]`, so the chain from the
        # schema back to the two owning modules is unbroken either way.
        owned = birth_state.default_birth()
        self.assertEqual(sorted(owned), sorted(BIRTH_COLUMNS))
        for column, value in owned.items():
            with self.subTest(column=column):
                self.assertEqual(float(defaults[column]), float(value))
        self.assertEqual(
            float(defaults["speed_walk"]),
            compose.CLIENT_CONSTRUCTION_DEFAULTS[7].value,
            "speed_walk's default must be the client's own construction "
            "default for BasicAttr+0x54, the number 008 seeded")
        self.assertIn("UPDATE characters SET speed_walk = 400.0",
                      (MIGRATIONS / "008_character_speed_walk_seed.sql")
                      .read_text(encoding="utf-8"))

    def test_the_typed_write_door_still_refuses_what_it_refused_before(self):
        """The CHECKs came back: the rebuild is not a way past them."""
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        account = store.ensure_account("account-a")
        born = self._create(store, account, "Newborn", "newborn")
        db = sqlite3.connect(str(self.path))
        try:
            for column, value in (("level", -1), ("level", 70000),
                                  ("hp_current", "eighty"),
                                  ("speed_walk", "fast"),
                                  ("stat_str", -5)):
                with self.subTest(column=column, value=value):
                    with self.assertRaises(sqlite3.IntegrityError):
                        db.execute("UPDATE characters SET %s=? WHERE id=?"
                                   % column, (value, born.id))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE characters SET selector=300 WHERE id=?",
                           (born.id,))
        finally:
            db.rollback()
            db.close()


class ExistingRowsSurviveTheRebuildTests(_PreNineFixture):

    def test_every_column_of_every_row_is_byte_identical(self):
        store = self._store_at_008()
        self._populate(store)
        before = _all_rows(self.path)
        self.assertEqual(len(before), 4)
        self._store_at_009().migrate()
        self.assertEqual(_applied(self.path)[-1], 9)
        self.assertEqual(_all_rows(self.path), before,
                         "009 is a DEFAULT, not a backfill: no existing row "
                         "may change in any column")

    def test_a_row_born_before_009_keeps_its_nulls(self):
        """Named rather than hidden: 009 does not reach backwards.

        A character created between the boot that applied 008 and the boot
        that applies 009 holds NULL in all four columns, and still does after
        009 -- a DEFAULT governs INSERTs, and this file deliberately runs no
        UPDATE.  That window is reported to COO in this round's letter; it is
        not closed here, because `COO-DECISION 20260902_1607` approved a
        default and a backfill is a different decision with a different price.
        """
        store = self._store_at_008()
        _, _, veteran, rookie, _, _ = self._populate(store)
        self._store_at_009().migrate()
        after = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(after.read_typed_attributes(rookie.id), {})
        self.assertEqual(after.read_typed_attributes(veteran.id), VETERAN)

    def test_the_children_of_a_dropped_parent_are_still_there(self):
        """The rebuild drops `characters` with foreign_keys OFF for a reason.

        With the pragma left ON, dropping the parent cascades into
        `character_positions` and the backpack tables and the owner loses a
        world without a single error message.
        """
        store = self._store_at_008()
        _, _, veteran, _, _, _ = self._populate(store)
        db = sqlite3.connect(str(self.path))
        try:
            before = (
                db.execute("SELECT COUNT(*) FROM character_positions").fetchone()[0],
                db.execute("SELECT COUNT(*) FROM character_backpacks").fetchone()[0],
                db.execute("SELECT COUNT(*) FROM character_backpack_items").fetchone()[0],
            )
        finally:
            db.close()
        self.assertGreater(before[0], 0)
        self.assertGreater(before[1], 0)
        self._store_at_009().migrate()
        db = sqlite3.connect(str(self.path))
        try:
            after = (
                db.execute("SELECT COUNT(*) FROM character_positions").fetchone()[0],
                db.execute("SELECT COUNT(*) FROM character_backpacks").fetchone()[0],
                db.execute("SELECT COUNT(*) FROM character_backpack_items").fetchone()[0],
            )
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM pragma_foreign_key_check()")
                  .fetchone()[0], 0)
        finally:
            db.close()
        self.assertEqual(after, before)
        self.assertEqual(
            SQLiteStore(self.path, MIGRATIONS).get_character(veteran.id).id,
            veteran.id)

    def test_a_soft_deleted_slot_can_still_be_reused_after_the_rebuild(self):
        """The partial unique indexes are what make this work at all."""
        store = self._store_at_008()
        account_a, account_b, _, _, _, deleted = self._populate(store)
        self._store_at_009().migrate()
        after = SQLiteStore(self.path, MIGRATIONS)
        replacement = self._create(after, account_b, "Ghost", "ghost-again",
                                   _build_wire_second_account, 9.0)
        self.assertEqual(replacement.selector, deleted.selector)
        self.assertNotEqual(replacement.id, deleted.id)

    def test_the_retry_branch_still_returns_the_first_row_untouched(self):
        """The property a DEFAULT has and an INSERT-site write does not.

        A retransmitted create packet returns before the INSERT, so a DEFAULT
        cannot fire on it -- the shape that turns a `level 9, 480/500`
        veteran into `1, 100/100` under a wrongly written plug.
        """
        store = self._store_at_008()
        account_a, _, veteran, _, _, _ = self._populate(store)
        self._store_at_009().migrate()
        after = SQLiteStore(self.path, MIGRATIONS)
        again = self._create(after, account_a, "Veteran", "veteran", x=1.0)
        self.assertEqual(again.id, veteran.id)
        self.assertEqual(after.read_typed_attributes(veteran.id), VETERAN)


class TheSchemaIsTheSameSchemaTests(_PreNineFixture):

    def test_columns_are_identical_except_for_the_four_new_defaults(self):
        """`COO-DECISION 20260902_1607` point 3, measured in Python.

        Deliberately NOT the same code path as the guard inside the SQL file:
        a guard cannot be the only witness for itself.
        """
        self._store_at_008()
        before = _table_info(self.path)
        self._store_at_009().migrate()
        after = _table_info(self.path)
        self.assertEqual(len(after), len(before))
        self.assertEqual(len(after), 35)
        for old, new in zip(before, after):
            with self.subTest(column=old[1]):
                self.assertEqual(new[:4], old[:4],
                                 "cid, name, type or NOT NULL changed")
                self.assertEqual(new[5], old[5], "primary key changed")
                if new[1] in BIRTH_COLUMNS:
                    self.assertIsNone(old[4])
                    self.assertIsNotNone(new[4])
                else:
                    self.assertEqual(new[4], old[4],
                                     "a column that was not part of this "
                                     "change gained or lost a default")

    def test_exactly_seven_columns_carry_a_default_afterwards(self):
        self._store_at_008()
        before = {name for _, name, _, _, dflt, _ in _table_info(self.path)
                  if dflt is not None}
        self.assertEqual(before, set(PRE_EXISTING_DEFAULT_COLUMNS))
        self._store_at_009().migrate()
        after = {name for _, name, _, _, dflt, _ in _table_info(self.path)
                 if dflt is not None}
        self.assertEqual(after, set(PRE_EXISTING_DEFAULT_COLUMNS) | set(BIRTH_COLUMNS))

    def test_every_index_came_back_with_the_same_text(self):
        self._store_at_008()
        before = _indexes(self.path)
        self.assertEqual(
            [name for name, _ in before],
            ["characters_active_identity", "characters_active_name_lookup",
             "characters_active_selector", "characters_create_fingerprint"])
        self._store_at_009().migrate()
        self.assertEqual(_indexes(self.path), before)

    def test_the_rest_of_the_database_did_not_move(self):
        """Only `characters` is rebuilt; the other tables and their indexes
        are not in this file's business and must not change."""
        store = self._store_at_008()
        self._populate(store)
        db = sqlite3.connect(str(self.path))
        try:
            before = sorted(
                (str(r[0]), str(r[1]), r[2]) for r in db.execute(
                    "SELECT type,name,sql FROM sqlite_master "
                    "WHERE tbl_name<>'characters'"))
        finally:
            db.close()
        self._store_at_009().migrate()
        db = sqlite3.connect(str(self.path))
        try:
            after = sorted(
                (str(r[0]), str(r[1]), r[2]) for r in db.execute(
                    "SELECT type,name,sql FROM sqlite_master "
                    "WHERE tbl_name<>'characters' AND name<>'schema_migrations'"))
            after = [row for row in after if row[1] != "schema_migrations"]
            before = [row for row in before if row[1] != "schema_migrations"]
        finally:
            db.close()
        self.assertEqual(after, before)

    def test_no_scratch_table_of_this_migration_survives(self):
        self._store_at_008()
        self._store_at_009().migrate()
        db = sqlite3.connect(str(self.path))
        try:
            left = [str(row[0]) for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE name LIKE '\\_pf\\_mig009\\_%' ESCAPE '\\' "
                "   OR name='characters_rebuild'")]
        finally:
            db.close()
        self.assertEqual(left, [])


class TheSnapshotReallyHappensTests(_PreNineFixture):

    def test_a_real_backup_file_exists_before_009_is_applied(self):
        """`COO-DECISION 20260902_1607` point 1, in its own words: confirm
        with a test that a backup FILE really appears -- not that the code
        calls a function."""
        store = self._store_at_008()
        self._populate(store)
        before = _all_rows(self.path)
        backups = self.root / "backups"
        snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
            backups_root=backups)
        self.assertIsNotNone(
            snapshot, "009 was pending, so a snapshot was owed and none was "
                      "taken")
        snapshot = Path(snapshot)
        self.assertTrue(snapshot.is_file())
        self.assertGreater(snapshot.stat().st_size, 0)
        self.assertTrue((snapshot.parent / "MANIFEST.json").is_file())
        self.assertEqual(_applied(self.path)[-1], 9)

        # The copy is the world as it was BEFORE the rebuild: same rows, and
        # a `characters` table that still has no defaults on the four.
        self.assertEqual(_all_rows(snapshot), before)
        self.assertEqual(_applied(snapshot)[-1], 8)
        snapshot_defaults = {name for _, name, _, _, dflt, _
                             in _table_info(snapshot) if dflt is not None}
        self.assertEqual(snapshot_defaults, set(PRE_EXISTING_DEFAULT_COLUMNS))

    def test_a_boot_that_cannot_take_the_snapshot_does_not_migrate(self):
        """Fail-closed: no copy, no rebuild.  The database must still be at
        008 afterwards, not half-way through a table rebuild."""
        from pirateforce_foundation.persistence_backup import BackupError

        store = self._store_at_008()
        self._populate(store)
        before = _all_rows(self.path)
        blocked = self.root / "blocked"
        blocked.write_text("not a directory", encoding="utf-8")
        with self.assertRaises(BackupError):
            SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
                backups_root=blocked)
        self.assertEqual(_applied(self.path)[-1], 8)
        self.assertEqual(_all_rows(self.path), before)
        defaults = {name for _, name, _, _, dflt, _ in _table_info(self.path)
                    if dflt is not None}
        self.assertEqual(defaults, set(PRE_EXISTING_DEFAULT_COLUMNS))


class TheGuardsInTheFileReallyFireTests(_PreNineFixture):
    """Six guards, and one mutant each that only that guard catches.

    Every mutant is a wrong rebuild that a reader could plausibly write, and
    every assertion is the same pair: the migration is REFUSED, and the
    database it was refused on still holds its pre-009 table with its rows
    intact.  A guard whose mutant applies cleanly is decoration.
    """

    def _refused(self, replacements):
        store = self._store_at_008()
        self._populate(store)
        before = _all_rows(self.path)
        before_columns = _table_info(self.path)
        before_indexes = _indexes(self.path)
        mutant = self._mutated_dir(replacements)
        with self.assertRaises(Exception) as caught:
            SQLiteStore(self.path, mutant).migrate()
        self.assertEqual(_applied(self.path)[-1], 8,
                         "the ledger recorded a migration that failed")
        self.assertEqual(_all_rows(self.path), before)
        self.assertEqual(_table_info(self.path), before_columns)
        self.assertEqual(_indexes(self.path), before_indexes)
        return caught.exception

    def test_guard_1_catches_a_backfill_of_the_existing_rows(self):
        """The UPDATE that looks helpful and is the owner's banned overwrite:
        every character in the database reset to the birth numbers."""
        self._refused([(
            "DROP TABLE characters;\nALTER TABLE characters_rebuild",
            "DROP TABLE characters;\n"
            "UPDATE characters_rebuild SET level=1, hp_current=100, "
            "hp_max=100, speed_walk=400.0;\n"
            "ALTER TABLE characters_rebuild")])

    def test_guard_1_catches_a_row_that_did_not_come_across(self):
        self._refused([(
            "    FROM characters;\n\nDROP TABLE characters;",
            "    FROM characters WHERE deleted_at IS NULL;\n\n"
            "DROP TABLE characters;")])

    def test_guard_2_catches_a_column_that_lost_its_not_null(self):
        self._refused([("    name TEXT NOT NULL,\n", "    name TEXT,\n")])

    def test_guard_3_catches_a_default_written_with_the_wrong_number(self):
        self._refused([("hp_max INTEGER DEFAULT 100",
                        "hp_max INTEGER DEFAULT 150")])

    def test_guard_4_catches_a_default_on_an_unadjudicated_column(self):
        """The guessed zero, arriving as a kindness."""
        self._refused([("    mp_current INTEGER\n",
                        "    mp_current INTEGER DEFAULT 0\n")])

    def test_guard_5_catches_a_lost_uniqueness_index(self):
        """Without `characters_active_selector` two live characters share a
        slot; this is the risk the proposing letter called the highest one."""
        self._refused([(
            "CREATE UNIQUE INDEX characters_active_selector ON characters"
            "(account_id, selector) WHERE deleted_at IS NULL;\n", "")])

    def test_guard_5_catches_an_index_that_lost_its_partial_clause(self):
        """A whole-table UNIQUE where a partial one was: soft-deleted slots
        stop being reusable and `004` is silently undone."""
        self._refused([(
            "CREATE UNIQUE INDEX characters_active_identity ON characters"
            "(identity_lo, identity_hi) WHERE deleted_at IS NULL;",
            "CREATE UNIQUE INDEX characters_active_identity ON characters"
            "(identity_lo, identity_hi);")])

    def test_guard_6_catches_a_rebuild_that_orphaned_the_children(self):
        """`id` renumbered by dropping it from the copy: every position and
        backpack row now points at a parent that does not exist."""
        self._refused([(
            "INSERT INTO characters_rebuild\n    (id,account_id",
            "INSERT INTO characters_rebuild\n    (account_id")])

    def test_the_mutation_harness_is_not_vacuous(self):
        """The unmutated file, through the same harness, APPLIES.

        Without this, every test above would pass against a harness that
        refuses everything -- including a copy of 009 with nothing wrong.
        """
        store = self._store_at_008()
        self._populate(store)
        before = _all_rows(self.path)
        unmutated = self._mutated_dir([])
        self.assertEqual(
            (unmutated / NINE.name).read_bytes(), NINE.read_bytes())
        SQLiteStore(self.path, unmutated).migrate()
        self.assertEqual(_applied(self.path)[-1], 9)
        self.assertEqual(_all_rows(self.path), before)


class TheLedgerStillGovernsThisFileTests(_PreNineFixture):

    def test_an_edited_009_is_refused_on_a_database_that_applied_it(self):
        """Why the round file says "the bytes of an applied file are frozen":
        the owner's canonical database refuses to boot against a changed one,
        with a message naming the file."""
        self._store_at_008()
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(_applied(self.path)[-1], 9)
        edited = self._mutated_dir([("-- 009_character_birth_defaults.sql",
                                     "-- 009 (edited after it was applied)")])
        with self.assertRaises(RuntimeError) as caught:
            SQLiteStore(self.path, edited).migrate()
        self.assertIn("checksum mismatch", str(caught.exception))
        self.assertIn(NINE.name, str(caught.exception))

    def test_applying_twice_changes_nothing(self):
        store = self._store_at_008()
        self._populate(store)
        SQLiteStore(self.path, MIGRATIONS).migrate()
        rows = _all_rows(self.path)
        columns = _table_info(self.path)
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(_all_rows(self.path), rows)
        self.assertEqual(_table_info(self.path), columns)
        self.assertEqual(_applied(self.path).count(9), 1)


if __name__ == "__main__":
    unittest.main()
