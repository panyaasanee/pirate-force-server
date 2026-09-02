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
into a throwaway migration directory -- one that drops the foreign key, one
that drops a CHECK constraint, one that adds a collation, one that destroys a
trigger, one that backfills the existing rows, one that cascade-deletes every
child row, one that loses an index, one that forgets a birth default -- and
requires of each that a guard REFUSED it, that the message NAMES the guard the
test is about, and that the database still holds its pre-009 table, columns,
indexes and DDL text.  Seven guards; every one of them has a mutant that names
it, and `test_every_guard_in_the_file_has_a_mutant_in_this_class` is what keeps
that true when a guard is added or removed.

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
import re
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

#: A veteran with a DISTINCT value in every one of the 21 typed columns.  Not
#: decoration: guard C in the migration compares each column with `IS NOT`, so
#: a column that is NULL in every fixture row can only ever be compared NULL
#: to NULL and the guard's line for it never really runs.  Built from the
#: typed-column table so a column added by a later migration joins it
#: automatically instead of being silently unmeasured.
def _veteran_full():
    values = {}
    for index, (column, spec) in enumerate(sorted(typed.TYPED_COLUMNS.items())):
        if column in VETERAN:
            values[column] = VETERAN[column]
        elif spec.kind == "f32":
            values[column] = 250.0 + index
        else:
            values[column] = 11 + index
    return values


VETERAN_FULL = _veteran_full()


def _build_wire(selector):
    return b"wire-%d" % selector, b"avatar", 0x30000001 + selector, 0


def _build_wire_second_account(selector):
    return b"wire-b-%d" % selector, b"avatar", 0x40000001 + selector, 0


def _build_wire_third_account(selector):
    return b"wire-c-%d" % selector, b"avatar", 0x50000001 + selector, 0


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


def _ddl(path, table="characters"):
    """The table's own stored DDL text -- the thing `pragma_table_info` is a
    lossy projection of, and the only place a CHECK constraint, a REFERENCES
    clause or a COLLATE can be seen at all."""
    db = sqlite3.connect(str(path))
    try:
        return db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,)).fetchone()[0]
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
        # EVERY typed column, with a value distinct from every other column's.
        # A `pf-adversary` pass measured what the three-column version cost:
        # with the other eighteen NULL in every fixture row, guard C's
        # `IS NOT` comparison for them only ever compared NULL to NULL, and a
        # rebuild that dropped `speed_walk` out of the copy COMMITTED.
        store.write_typed_attributes(veteran.id, dict(VETERAN_FULL))
        db = sqlite3.connect(str(self.path))
        try:
            # Two more columns guard C names that no store method writes.
            db.execute("UPDATE characters SET avatar_typed_json=?, "
                       "identity_hi=? WHERE id=?",
                       ('{"lane":"db"}', 7, veteran.id))
            db.commit()
        finally:
            db.close()
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

    def test_a_row_born_before_009_keeps_what_it_was_born_with(self):
        """Named rather than hidden: 009 does not reach backwards.

        A DEFAULT governs INSERTs, and this file deliberately runs no UPDATE,
        so a character created before 009 keeps exactly the columns it was
        born with and gains nothing.  WHICH columns those are depends on when
        it was born, and the window narrowed while this file was being
        written: chief's insertion point (`COO-DECISION 20260902_0444`,
        commit `b9e11059`) now writes the three vitals at creation, so a
        character born after THAT has the three and lacks only `speed_walk`.
        A character born before it -- which is every character on the owner's
        database created between the boot that applied 007/008 and the boot
        that applies the plug -- still holds NULL in all four.  Both halves
        are measured below, and the window is reported to COO in this round's
        letter rather than closed here: `COO-DECISION 20260902_1607` approved
        a DEFAULT, and a backfill is a different decision with its own price.
        """
        store = self._store_at_008()
        _, _, veteran, rookie, _, _ = self._populate(store)
        born_with = store.read_typed_attributes(rookie.id)
        self.assertNotIn("speed_walk", born_with,
                         "008 seeds a cohort; a character born after it has "
                         "no speed and this test would be measuring nothing")

        # The other half of the window: a row that predates chief's plug too.
        pre_plug = self._create(store, self.__dict__.setdefault(
            "_account_c", store.ensure_account("account-c")),
            "Ancient", "ancient", _build_wire_third_account, 11.0)
        birth_state.clear_birth_defaults_to_pre_009(self.path, [pre_plug.id])
        self.assertEqual(store.read_typed_attributes(pre_plug.id), {})

        self._store_at_009().migrate()
        after = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(after.read_typed_attributes(rookie.id), born_with)
        self.assertEqual(after.read_typed_attributes(pre_plug.id), {},
                         "009 backfilled a row; it is a DEFAULT, not an "
                         "UPDATE, and the guard in the file should have "
                         "refused the commit")
        self.assertEqual(
            after.read_typed_attributes(veteran.id),
            birth_state.with_birth(born_with, **VETERAN_FULL))

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
        held = store.read_typed_attributes(veteran.id)
        self._store_at_009().migrate()
        after = SQLiteStore(self.path, MIGRATIONS)
        again = self._create(after, account_a, "Veteran", "veteran", x=1.0)
        self.assertEqual(again.id, veteran.id)
        self.assertEqual(after.read_typed_attributes(veteran.id), held)


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
    """One mutant per guard, and each one has to NAME the guard that caught it.

    WHY THE NAME IS ASSERTED AND NOT JUST THE REFUSAL.  The first version of
    this class asserted `assertRaises(Exception)` and called that "six guards,
    six mutants".  A `pf-adversary` pass took it apart:

      * the "guard 6" mutant dropped `id` from the INSERT column list but not
        from the SELECT list, which is an ARITY ERROR -- `table
        characters_rebuild has 35 values for 34 columns`.  It was refused with
        every guard deleted from the file.  That guard had never fired once;
      * two mutants were "caught" by `_mutated_dir`'s own `assertIn`, because
        they changed the exact substring a DIFFERENT test searches for.  Move
        the same defect one column over and the whole suite went green;
      * one mutant was caught by two guards, so one of the two was decoration;
      * and six wrong rebuilds a reader would call catastrophic -- a lost
        `REFERENCES accounts(id)`, three lost CHECK constraints, an added
        COLLATE, a widened range -- were caught by NOTHING, because
        `pragma_table_info` cannot see any of them.

    Every guard now carries a NAMED constraint, so SQLite's message says which
    one refused, and `_refused` requires the expected name.  A mutant caught by
    a SQL error, or by the wrong guard, is a failure here.
    """

    def _refused(self, replacements, expect_guard):
        """Apply a mutant of 009 to a populated 008 database and require that
        the named guard is what stopped it, with the database untouched."""
        store = self._store_at_008()
        self._populate(store)
        before = _all_rows(self.path)
        before_columns = _table_info(self.path)
        before_indexes = _indexes(self.path)
        before_ddl = _ddl(self.path)
        mutant = self._mutated_dir(replacements)
        with self.assertRaises(Exception) as caught:
            SQLiteStore(self.path, mutant).migrate()
        message = str(caught.exception)
        self.assertIn(
            "CHECK constraint failed", message,
            "the mutant was refused by something that is not a guard -- a SQL "
            "error refuses just as loudly and proves nothing: %s" % message)
        self.assertIn(
            expect_guard, message,
            "a guard refused the mutant, but not the one this test is about")
        self.assertEqual(_applied(self.path)[-1], 8,
                         "the ledger recorded a migration that failed")
        self.assertEqual(_all_rows(self.path), before)
        self.assertEqual(_table_info(self.path), before_columns)
        self.assertEqual(_indexes(self.path), before_indexes)
        self.assertEqual(_ddl(self.path), before_ddl)
        return message

    # -- guard A: the whole table declaration.  Every mutant below was
    # -- measured COMMITTING, with every test green, against the version of
    # -- this file that graded the rebuild by `pragma_table_info` alone.
    def test_the_ddl_guard_catches_a_lost_foreign_key(self):
        """The worst of the six: `characters.account_id` stops referencing
        `accounts`, and the orphan half of guard G becomes permanently vacuous
        for this table, in every future migration."""
        self._refused(
            [("    account_id INTEGER NOT NULL REFERENCES accounts(id),\n",
              "    account_id INTEGER NOT NULL,\n")],
            "guard_the_table_declaration_is_unchanged")

    def test_the_ddl_guard_catches_a_dropped_check_constraint(self):
        """`migrations/006` says in writing that a value the encoder could not
        survive cannot be stored in the first place.  Dropping the CHECK makes
        that sentence false, permanently, and the checksum ledger seals it."""
        self._refused(
            [("    cash INTEGER\n"
              "        CHECK(cash IS NULL OR (typeof(cash)='integer' AND cash BETWEEN 0 AND 9223372036854775807)),\n",
              "    cash INTEGER,\n")],
            "guard_the_table_declaration_is_unchanged")

    def test_the_ddl_guard_catches_a_widened_check_range(self):
        self._refused(
            [("stat_str BETWEEN 0 AND 65535",
              "stat_str BETWEEN 0 AND 4294967295")],
            "guard_the_table_declaration_is_unchanged")

    def test_the_ddl_guard_catches_an_added_collation(self):
        """`name_key` is the column the active-name index is built on; giving
        it NOCASE changes what "the same name" means without changing a single
        thing `pragma_table_info` reports."""
        self._refused(
            [("    name_key TEXT NOT NULL DEFAULT '',\n",
              "    name_key TEXT NOT NULL DEFAULT '' COLLATE NOCASE,\n")],
            "guard_the_table_declaration_is_unchanged")

    def test_the_other_objects_guard_catches_a_trigger_destroyed_by_the_rebuild(self):
        """A rebuild drops every trigger on the table it replaces, silently.
        No migration in this repository creates one today -- but the owner's
        canonical database is not in this repository, so "there is no trigger
        on her characters" is an assumption, and this guard is the one nobody
        has to make it."""
        store = self._store_at_008()
        self._populate(store)
        db = sqlite3.connect(str(self.path))
        try:
            db.execute(
                "CREATE TRIGGER characters_audit AFTER UPDATE ON characters "
                "BEGIN SELECT 1; END")
            db.commit()
        finally:
            db.close()
        before = _all_rows(self.path)
        with self.assertRaises(Exception) as caught:
            SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertIn("guard_every_other_object_is_unchanged",
                      str(caught.exception))
        self.assertEqual(_applied(self.path)[-1], 8)
        self.assertEqual(_all_rows(self.path), before)
        db = sqlite3.connect(str(self.path))
        try:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM sqlite_master "
                           "WHERE type='trigger'").fetchone()[0], 1,
                "the trigger was destroyed even though the migration rolled "
                "back")
        finally:
            db.close()

    def test_the_rows_guard_catches_a_backfill_of_the_existing_rows(self):
        """The UPDATE that looks helpful and is the owner's banned overwrite:
        every character in the database reset to the birth numbers."""
        self._refused(
            [("DROP TABLE characters;\nALTER TABLE characters_rebuild",
              "DROP TABLE characters;\n"
              "UPDATE characters_rebuild SET level=1, hp_current=100, "
              "hp_max=100, speed_walk=400.0;\n"
              "ALTER TABLE characters_rebuild")],
            "guard_no_row_changed_in_any_column")

    def test_the_rows_guard_catches_a_row_that_did_not_come_across(self):
        self._refused(
            [("    FROM characters;\n\nDROP TABLE characters;",
              "    FROM characters WHERE deleted_at IS NULL;\n\n"
              "DROP TABLE characters;")],
            "guard_no_row_changed_in_any_column")

    def test_the_rows_guard_catches_a_column_dropped_from_the_copy(self):
        """The slip guard C could not see until `_populate` began writing a
        distinct value into all 21 typed columns: with every typed column NULL
        in every fixture row, a column left out of the copy compares NULL to
        NULL and passes.  A `pf-adversary` pass measured exactly that on
        `speed_walk`."""
        self._refused(
            [("     stat_per,experience,cash,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per\n"
              "    FROM characters;",
              "     stat_per,experience,NULL,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per\n"
              "    FROM characters;")],
            "guard_no_row_changed_in_any_column")

    def test_the_columns_guard_catches_a_column_that_lost_its_not_null(self):
        self._refused([("    name TEXT NOT NULL,\n", "    name TEXT,\n")],
                      "guard_the_column_list_is_unchanged")

    def test_the_defaults_guard_catches_a_default_written_with_the_wrong_number(self):
        self._refused([("hp_max INTEGER DEFAULT 100",
                        "hp_max INTEGER DEFAULT 150")],
                      "guard_exactly_the_four_defaults_were_added")

    def test_the_columns_guard_catches_a_default_on_an_unadjudicated_column(self):
        """The guessed zero, arriving as a kindness.  Caught by the COLUMNS
        guard, which runs first: it compares `dflt_value` for every column
        outside the four this file is allowed to touch."""
        self._refused([("    mp_current INTEGER\n",
                        "    mp_current INTEGER DEFAULT 0\n")],
                      "guard_the_column_list_is_unchanged")

    def test_the_defaults_guard_catches_a_birth_default_that_never_landed(self):
        """The mutant only the defaults guard can catch: the columns guard
        deliberately EXCLUDES the four birth columns from its `dflt_value`
        comparison (they are the four this file changes), so a rebuild that
        simply forgets one of them walks straight past it -- and past every
        test that only creates characters, because three of the four are
        written by chief's insertion point anyway.  `speed_walk` is the one
        nothing else supplies."""
        self._refused([("    speed_walk REAL DEFAULT 400.0\n",
                        "    speed_walk REAL\n")],
                      "guard_exactly_the_four_defaults_were_added")

    def test_the_indexes_guard_catches_a_lost_uniqueness_index(self):
        """Without `characters_active_selector` two live characters share a
        slot; this is the risk the proposing letter called the highest one."""
        self._refused(
            [("CREATE UNIQUE INDEX characters_active_selector ON characters"
              "(account_id, selector) WHERE deleted_at IS NULL;\n", "")],
            "guard_every_index_came_back")

    def test_the_indexes_guard_catches_an_index_that_lost_its_partial_clause(self):
        """A whole-table UNIQUE where a partial one was: soft-deleted slots
        stop being reusable and `004` is silently undone."""
        self._refused(
            [("CREATE UNIQUE INDEX characters_active_identity ON characters"
              "(identity_lo, identity_hi) WHERE deleted_at IS NULL;",
              "CREATE UNIQUE INDEX characters_active_identity ON characters"
              "(identity_lo, identity_hi);")],
            "guard_every_index_came_back")

    def test_the_children_guard_catches_a_rebuild_that_deleted_every_child_row(self):
        """`PRAGMA foreign_keys=OFF` is the line that prevents this, and a
        `pf-adversary` pass measured what the old orphan-only guard did when
        that line was flipped: `DROP TABLE characters` cascade-deleted every
        position, backpack and item row, and the orphan count came back ZERO
        -- because nothing was orphaned, nothing was left.  Counting the
        survivors is the guard the header always claimed to have."""
        self._refused(
            [("PRAGMA foreign_keys=OFF;", "PRAGMA foreign_keys=ON;")],
            "guard_the_child_rows_all_survived")

    def test_the_children_guard_still_catches_an_orphan(self):
        """The other direction, which counting cannot see: every child row is
        still there and points at a parent that is not."""
        self._refused(
            [("DROP TABLE characters;\nALTER TABLE characters_rebuild",
              "DROP TABLE characters;\n"
              "UPDATE characters_rebuild SET id = id + 100000;\n"
              "ALTER TABLE characters_rebuild")],
            "guard_")

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

    def test_every_guard_in_the_file_has_a_mutant_in_this_class(self):
        """The bookkeeping that stops a guard being added with no mutant, and
        stops one being deleted with its mutant left behind testing nothing.
        Both were real: a `pf-adversary` pass found a guard here that had
        never fired once."""
        declared = set(re.findall(r"CONSTRAINT (guard_[a-z_]+) CHECK",
                                  NINE.read_text(encoding="utf-8")))
        self.assertEqual(len(declared), 7)
        source = Path(__file__).read_text(encoding="utf-8")
        for name in sorted(declared):
            with self.subTest(guard=name):
                self.assertIn(
                    '"%s"' % name, source,
                    "this guard has no mutant in this class that names it")


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
