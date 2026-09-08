"""LANE-DB: the quest-state persistence doors -- write, then read them back.

WHAT THIS FILE IS THE EVIDENCE FOR.  `pf_bridge/NOW.md` carries the owner's
order `PANYA 20260908_1520` ("quest-flag store first"), routed to this lane
by `pf_bridge/notes_to_chief/20260908_1642_COO-DECISION-quest-flags-schema-
comes-before-the-bulk-skill-rows-LANE-DB.md`.  That decision measured, and
LANE-Q re-measured in `pf_bridge/notes_to_chief/20260908_1647_LANE-Q-TO-
LANE-DB-the-quest-state-doors-are-not-on-main.md`, that the five doors this
lane DECLARED in `pf_bridge/notes_to_chief/20260905_2212_LANE-DB-TO-LANE-Q-
quest-state-doors-declared-and-opened-this-round.md` never reached `main`:
no migration mentioning quest, no `set_quest_flag` in `store.py`.  This
file is the evidence they exist now, on `migrations/
019_character_quest_state.sql`.

WHY 019 AND NOT THE 014 THE CONTRACT RESERVED.  `014` on `main` today is
`014_character_skills_learned_source.sql` and `015`..`018` are taken as
well.  The number is the ONLY thing that moves; every name, signature,
refusal and return shape below is the contract's, verbatim, because the COO
decision forbids redesigning it and LANE-Q's `lua_api/quest_state_store.
StoreBackedQuestStateStore` already calls these names.

WHAT THIS FILE DOES NOT CLAIM.  It does not claim any player's quest
progress survives a logout on the owner's machine today -- nothing calls
these doors yet.  LANE-Q's adapter is written but not wired to a
dispatcher (its own nonclaim, `1647` point 4), and this lane's charter
(`COO-DECISION 20260901_1100`) does not touch `runtime.py`.  This is the
wire/DB layer of evidence only; there is no client-observable layer in this
round and none is claimed.
"""
from __future__ import annotations

import inspect
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position               # noqa: E402
from pirateforce_foundation.persistence_quest_state import (    # noqa: E402
    QuestCounterRow,
    QuestFlagRow,
)
from pirateforce_foundation.store import (                      # noqa: E402
    SQLiteStore,
    WriteLockTimeout,
)

MIGRATIONS = ROOT / "migrations"
NINETEEN = MIGRATIONS / "019_character_quest_state.sql"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


def _raw(path, sql, args=()):
    """Rows read through a connection of this test's own, never through the
    store's accessors -- so a door that returns a plausible object without
    writing a row cannot pass by agreeing with itself."""
    db = sqlite3.connect(str(path))
    try:
        return [tuple(row) for row in db.execute(sql, args)]
    finally:
        db.close()


def _rewrite_trigger(path):
    """Make the stored value differ from the argument, behind the door's
    back, so an echoing door and an honest one report different numbers."""
    db = sqlite3.connect(str(path))
    try:
        db.execute(
            "CREATE TRIGGER quest_counter_rewrite AFTER INSERT ON "
            "character_quest_counter BEGIN UPDATE character_quest_counter "
            "SET counter_value=4242 WHERE character_id=NEW.character_id "
            "AND quest_id=NEW.quest_id AND counter_name=NEW.counter_name; END"
        )
        db.commit()
    finally:
        db.close()


def _soft_delete(path, character_id):
    """Mark a character soft-deleted through this test's own connection.

    `SQLiteStore.soft_delete_character` is keyed by (session id, selector),
    which would drag a whole login into a persistence test; the doors under
    test read `characters.deleted_at IS NULL` and nothing else, so this
    writes exactly that fact."""
    db = sqlite3.connect(str(path))
    try:
        db.execute(
            "UPDATE characters SET deleted_at=? WHERE id=?",
            ("2026-09-08T00:00:00+00:00", character_id),
        )
        db.commit()
    finally:
        db.close()


def _table_info(path, table):
    return _raw(
        path,
        "SELECT cid,name,type,\"notnull\",dflt_value,pk "
        "FROM pragma_table_info(?)",
        (table,),
    )


class _Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "quest_state_test.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 0.0, 0.0, 0.0, heading=0.0)
        self.account_id = self.store.ensure_account("quest-state-tests")
        self.character_id = self._make_character("a")

    def _make_character(self, tag):
        return self.store.create_character(
            self.account_id, f"QS{tag}", f"qs{tag}",
            f"fingerprint-qs-{tag}", _build_wire, self.home,
        ).id


class MigrationShapeTests(unittest.TestCase):
    """The file itself: two bare CREATE TABLEs, nothing else."""

    def setUp(self):
        self.sql = NINETEEN.read_text(encoding="utf-8")
        self.code_only = "\n".join(
            line for line in self.sql.splitlines()
            if not line.strip().startswith("--")
        )
        self.statements = [
            s.strip() for s in self.code_only.split(";") if s.strip()
        ]

    def test_the_file_is_ascii(self):
        """`AGENTS.md`: everything that can reach the bridge console is
        ASCII -- cp874 kills the tooling on anything else.  `016` and `017`
        pin their own files; `018` forgot to (adversary finding D11) and
        this one does not."""
        NINETEEN.read_bytes().decode("ascii")

    def test_two_statements_both_create_table_no_default(self):
        self.assertEqual(len(self.statements), 2)
        for statement in self.statements:
            self.assertTrue(statement.upper().startswith("CREATE TABLE"))
            self.assertNotIn("DEFAULT", statement.upper())

    def test_nothing_is_updated_or_rebuilt_so_no_backup_is_owed(self):
        """`COO-DECISION 20260901_1112` point 3 demands an automatic
        pre-apply snapshot only for a migration that touches EXISTING rows.
        This one writes none, which is a property of the file, not a
        promise in its prose -- so the test reads the file."""
        upper = self.code_only.upper()
        for forbidden in ("UPDATE ", "INSERT ", "DROP ", "ALTER "):
            self.assertNotIn(forbidden, upper)

    def test_both_tables_name_the_two_new_tables_only(self):
        self.assertIn("CREATE TABLE character_quest_flag", self.statements[0])
        self.assertIn(
            "CREATE TABLE character_quest_counter", self.statements[1]
        )

    def test_the_number_is_the_next_free_one(self):
        """`prompts/LANE-DB.md`: a colliding number makes the owner's
        database refuse to boot on a checksum mismatch.  Derived from the
        directory, not typed twice."""
        numbers = sorted(
            int(p.name[:3]) for p in MIGRATIONS.glob("*.sql")
            if p.name[:3].isdigit()
        )
        self.assertEqual(numbers, list(range(1, max(numbers) + 1)))
        self.assertEqual(numbers.count(19), 1)
        # NOT `max(numbers) == 19`.  PAYS pf-adversary D4 (round `6vv9mi`):
        # that assertion says "this file claimed a free number", and it
        # stops being able to say it the moment ANY lane lands `020` -- at
        # which point this file goes red for a reason with nothing to do
        # with quest state.  `tests/test_migration_016_experience_skill_
        # points_backfill.py:780` deleted the same assertion for the same
        # reason and wrote down why; repeating the mistake it removed would
        # be worse than never having read it.  What survives is the two
        # claims that stay true forever: the directory is a gapless run,
        # and exactly one file is numbered 19.


class AppliedSchemaTests(unittest.TestCase):
    """The schema as SQLite actually built it, not as the file reads."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "shape.sqlite3"
        SQLiteStore(self.path, MIGRATIONS).migrate()

    def test_flag_columns_and_composite_primary_key(self):
        columns = {row[1]: row for row in _table_info(
            self.path, "character_quest_flag")}
        self.assertEqual(
            set(columns),
            {"character_id", "quest_id", "flag_value", "updated_at"},
        )
        for name in columns:
            self.assertEqual(columns[name][3], 1, name)  # every column NOT NULL
        self.assertEqual(columns["character_id"][5], 1)  # pk position 1
        self.assertEqual(columns["quest_id"][5], 2)      # pk position 2
        self.assertEqual(columns["flag_value"][5], 0)
        self.assertEqual(columns["updated_at"][5], 0)

    def test_counter_columns_and_three_part_primary_key(self):
        columns = {row[1]: row for row in _table_info(
            self.path, "character_quest_counter")}
        self.assertEqual(
            set(columns),
            {
                "character_id", "quest_id", "counter_name",
                "counter_value", "updated_at",
            },
        )
        self.assertEqual(columns["character_id"][5], 1)
        self.assertEqual(columns["quest_id"][5], 2)
        self.assertEqual(columns["counter_name"][5], 3)
        self.assertEqual(columns["counter_value"][5], 0)

    def test_both_tables_carry_the_foreign_key_to_characters(self):
        """Adversary finding D1 on round `fw2hs6`: a test named after a
        foreign key can pass BECAUSE the foreign key is gone --
        `pragma_foreign_key_check` returns zero rows on a table that has
        none.  So this reads `pragma_foreign_key_list` instead, which is
        empty exactly when the constraint is missing."""
        for table in ("character_quest_flag", "character_quest_counter"):
            keys = _raw(
                self.path,
                "SELECT \"table\",\"from\",\"to\",on_delete "
                "FROM pragma_foreign_key_list(?)",
                (table,),
            )
            self.assertEqual(
                keys, [("characters", "character_id", "id", "CASCADE")], table
            )

    def test_every_counter_column_is_not_null(self):
        """PAYS pf-adversary D3 (round `6vv9mi`): the flag table's test
        looped `notnull==1` over every column, the counter table's checked
        only PK positions -- so dropping NOT NULL from `counter_value` and
        `updated_at` survived every mutant."""
        columns = {row[1]: row for row in _table_info(
            self.path, "character_quest_counter")}
        # PAYS pf-adversary D6 (round `euskyd`): `PRAGMA table_info` on a
        # table that does not exist returns zero rows, so the loop below
        # used to assert NOTHING and report PASS if the table were ever
        # renamed away -- the same "green because it never got there"
        # shape this test was written to close.  The set is checked first.
        self.assertEqual(
            set(columns),
            {"character_id", "quest_id", "counter_name", "counter_value",
             "updated_at"},
        )
        for name in columns:
            self.assertEqual(columns[name][3], 1, name)

    def test_the_counter_tables_u16_check_is_in_the_schema_too(self):
        """PAYS pf-adversary D3: the u16 CHECK was measured on the flag
        table only, so deleting it from the counter table went unnoticed --
        and the migration's stated reason for it ("a second writer cannot
        put a row here that the wire could never carry") was unproven for
        half the schema."""
        db = sqlite3.connect(str(self.path))
        try:
            for bad in (65536, -1):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(
                        "INSERT INTO character_quest_counter "
                        "VALUES (1,?,'m',0,'t')", (bad,)
                    )
        finally:
            db.close()

    def test_the_u16_check_is_in_the_schema_not_only_in_python(self):
        """A second writer (a repair script, a later migration) must not be
        able to store a quest id the wire could never carry."""
        db = sqlite3.connect(str(self.path))
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO character_quest_flag VALUES (1,65536,1,'t')"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO character_quest_flag VALUES (1,-1,1,'t')"
                )
        finally:
            db.close()

    def test_the_counter_name_length_check_is_in_the_schema_too(self):
        db = sqlite3.connect(str(self.path))
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO character_quest_counter VALUES (1,1,'',0,'t')"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO character_quest_counter VALUES "
                    "(1,1,?,0,'t')", ("x" * 129,)
                )
        finally:
            db.close()

    def test_a_fresh_migrate_leaves_both_tables_empty(self):
        """No backfill: a character born before `019` gets no guessed quest
        progress."""
        for table in ("character_quest_flag", "character_quest_counter"):
            self.assertEqual(
                _raw(self.path, f"SELECT COUNT(*) FROM {table}"), [(0,)]
            )


class QuestFlagDoorTests(_Workspace):
    def test_set_then_get_round_trips_the_value(self):
        written = self.store.set_quest_flag(self.character_id, 3020, 7)
        self.assertIsInstance(written, QuestFlagRow)
        self.assertEqual(written.character_id, self.character_id)
        self.assertEqual(written.quest_id, 3020)
        self.assertEqual(written.flag_value, 7)
        read = self.store.get_quest_flag(self.character_id, 3020)
        self.assertEqual(read, written)

    def test_the_row_is_in_the_table_not_only_in_the_return(self):
        self.store.set_quest_flag(self.character_id, 3020, 7)
        self.assertEqual(
            _raw(
                self.path,
                "SELECT character_id,quest_id,flag_value "
                "FROM character_quest_flag",
            ),
            [(self.character_id, 3020, 7)],
        )

    def test_setting_twice_moves_the_value_and_makes_no_second_row(self):
        """`q_kill5.lua` sets `Quest.Active` and later `Quest.Finish` on the
        same quest -- an UPSERT, not an append."""
        self.store.set_quest_flag(self.character_id, 3020, 1)
        second = self.store.set_quest_flag(self.character_id, 3020, 9)
        self.assertEqual(second.flag_value, 9)
        self.assertEqual(
            _raw(self.path, "SELECT COUNT(*) FROM character_quest_flag"),
            [(1,)],
        )

    def test_the_return_is_read_back_not_echoed(self):
        """`2212`'s explicit requirement, and LANE-Q has a test that fails
        if this door echoes.  Proved by making the stored value differ from
        the argument behind the door's back: a trigger rewrites the row, so
        an echoing door would report 7 and an honest one 4242."""
        db = sqlite3.connect(str(self.path))
        try:
            db.execute(
                "CREATE TRIGGER quest_flag_rewrite AFTER INSERT ON "
                "character_quest_flag BEGIN UPDATE character_quest_flag "
                "SET flag_value=4242 WHERE character_id=NEW.character_id "
                "AND quest_id=NEW.quest_id; END"
            )
            db.commit()
        finally:
            db.close()
        written = self.store.set_quest_flag(self.character_id, 3020, 7)
        self.assertEqual(written.flag_value, 4242)

    def test_a_quest_never_set_reads_none_not_zero(self):
        self.assertIsNone(self.store.get_quest_flag(self.character_id, 3020))

    def test_two_quests_of_one_character_do_not_collide(self):
        self.store.set_quest_flag(self.character_id, 3020, 1)
        self.store.set_quest_flag(self.character_id, 3021, 2)
        self.assertEqual(
            self.store.get_quest_flag(self.character_id, 3020).flag_value, 1
        )
        self.assertEqual(
            self.store.get_quest_flag(self.character_id, 3021).flag_value, 2
        )

    def test_two_characters_do_not_see_each_others_flags(self):
        other = self._make_character("b")
        self.store.set_quest_flag(self.character_id, 3020, 1)
        self.store.set_quest_flag(other, 3020, 5)
        self.assertEqual(
            self.store.get_quest_flag(self.character_id, 3020).flag_value, 1
        )
        self.assertEqual(self.store.get_quest_flag(other, 3020).flag_value, 5)

    def test_a_missing_character_is_refused(self):
        with self.assertRaises(KeyError):
            self.store.set_quest_flag(999999, 3020, 1)
        self.assertEqual(
            _raw(self.path, "SELECT COUNT(*) FROM character_quest_flag"),
            [(0,)],
        )

    def test_a_soft_deleted_character_is_refused(self):
        _soft_delete(self.path, self.character_id)
        with self.assertRaises(KeyError):
            self.store.set_quest_flag(self.character_id, 3020, 1)

    def test_the_read_side_refuses_a_missing_character_too(self):
        """PAYS pf-adversary D9 (round `6vv9mi`).  `2212` writes two
        separate clauses -- "no such / soft-deleted character -> KeyError"
        and "no row (never set) -> None" -- and scopes only the second to
        the write side.  Answering `None` for a character that does not
        exist would collapse "no such character" into "no progress", which
        is the one distinction the caller cannot recover afterwards."""
        with self.assertRaises(KeyError):
            self.store.get_quest_flag(999999, 3020)

    def test_the_read_side_refuses_a_soft_deleted_character_too(self):
        self.store.set_quest_flag(self.character_id, 3020, 1)
        _soft_delete(self.path, self.character_id)
        with self.assertRaises(KeyError):
            self.store.get_quest_flag(self.character_id, 3020)

    def test_a_character_id_sqlite_cannot_hold_is_refused(self):
        """PAYS pf-adversary D6: this was the one number without a bound,
        so it reached `sqlite3` and raised `OverflowError` from inside the
        open transaction -- outside the exception family LANE-Q's adapter
        catches, so it escaped into the Lua call stack."""
        for door in (
            lambda: self.store.set_quest_flag(2 ** 70, 3020, 1),
            lambda: self.store.get_quest_flag(2 ** 70, 3020),
            lambda: self.store.set_quest_counter(2 ** 70, 3020, "m", 1),
            lambda: self.store.increment_quest_counter(2 ** 70, 3020, "m"),
            lambda: self.store.get_quest_counter(2 ** 70, 3020, "m"),
        ):
            with self.assertRaises(ValueError):
                door()

    def test_setting_the_same_value_twice_still_moves_updated_at(self):
        """`updated_at` is the only evidence that a script touched a quest
        at all when the flag it wrote equals the flag already there."""
        first = self.store.set_quest_flag(self.character_id, 3020, 1)
        second = self.store.set_quest_flag(self.character_id, 3020, 1)
        self.assertNotEqual(second.updated_at, first.updated_at)

    def test_the_read_back_matches_the_quest_exactly_not_a_range(self):
        """A read-back that matched `quest_id>=?` would return quest 3020's
        row for a write to 3019 the moment both exist."""
        self.store.set_quest_flag(self.character_id, 3019, 11)
        row = self.store.set_quest_flag(self.character_id, 3020, 22)
        self.assertEqual((row.quest_id, row.flag_value), (3020, 22))

    def test_a_quest_id_outside_u16_is_refused_on_both_sides(self):
        for bad in (-1, 0x10000):
            with self.assertRaises(ValueError):
                self.store.set_quest_flag(self.character_id, bad, 1)
            with self.assertRaises(ValueError):
                self.store.get_quest_flag(self.character_id, bad)

    def test_the_u16_edges_themselves_are_accepted(self):
        for edge in (0, 0xFFFF):
            self.assertEqual(
                self.store.set_quest_flag(
                    self.character_id, edge, 1).quest_id, edge
            )

    def test_bools_are_refused_everywhere_an_int_is_expected(self):
        with self.assertRaises(TypeError):
            self.store.set_quest_flag(True, 3020, 1)
        with self.assertRaises(TypeError):
            self.store.set_quest_flag(self.character_id, True, 1)
        with self.assertRaises(TypeError):
            self.store.set_quest_flag(self.character_id, 3020, True)
        with self.assertRaises(TypeError):
            self.store.get_quest_flag(self.character_id, False)

    def test_a_flag_value_sqlite_cannot_hold_is_refused_before_the_write(self):
        with self.assertRaises(ValueError):
            self.store.set_quest_flag(self.character_id, 3020, 2 ** 63)
        self.assertEqual(
            _raw(self.path, "SELECT COUNT(*) FROM character_quest_flag"),
            [(0,)],
        )

    def test_negative_flag_values_are_stored_as_given(self):
        """`2212`: no enum, no range beyond the storage's own -- the DB does
        not know what the number means and must not narrow it."""
        row = self.store.set_quest_flag(self.character_id, 3020, -5)
        self.assertEqual(row.flag_value, -5)


class QuestCounterDoorTests(_Workspace):
    def test_set_then_get_round_trips(self):
        written = self.store.set_quest_counter(
            self.character_id, 3020, "mob_517", 3)
        self.assertIsInstance(written, QuestCounterRow)
        self.assertEqual(written.counter_name, "mob_517")
        self.assertEqual(written.counter_value, 3)
        self.assertEqual(
            self.store.get_quest_counter(self.character_id, 3020, "mob_517"),
            written,
        )

    def test_set_is_absolute_not_additive(self):
        self.store.set_quest_counter(self.character_id, 3020, "mob_517", 3)
        again = self.store.set_quest_counter(
            self.character_id, 3020, "mob_517", 1)
        self.assertEqual(again.counter_value, 1)

    def test_two_counters_in_one_quest_are_two_rows(self):
        """`gamedata/lua/Quest/q_kill5.lua` tracks two mobs at once inside
        one quest -- the case the name is part of the key for."""
        self.store.set_quest_counter(self.character_id, 3020, "mob_517", 3)
        self.store.set_quest_counter(self.character_id, 3020, "mob_518", 8)
        self.assertEqual(
            self.store.get_quest_counter(
                self.character_id, 3020, "mob_517").counter_value, 3
        )
        self.assertEqual(
            self.store.get_quest_counter(
                self.character_id, 3020, "mob_518").counter_value, 8
        )
        self.assertEqual(
            _raw(self.path, "SELECT COUNT(*) FROM character_quest_counter"),
            [(2,)],
        )

    def test_a_counter_never_set_reads_none(self):
        self.assertIsNone(
            self.store.get_quest_counter(self.character_id, 3020, "mob_517")
        )

    def test_increment_from_nothing_starts_at_delta(self):
        row = self.store.increment_quest_counter(
            self.character_id, 3020, "mob_517")
        self.assertEqual(row.counter_value, 1)

    def test_increment_adds_to_what_is_there(self):
        self.store.set_quest_counter(self.character_id, 3020, "mob_517", 4)
        row = self.store.increment_quest_counter(
            self.character_id, 3020, "mob_517", 2)
        self.assertEqual(row.counter_value, 6)
        self.assertEqual(
            _raw(self.path, "SELECT COUNT(*) FROM character_quest_counter"),
            [(1,)],
        )

    def test_five_increments_land_five(self):
        for _ in range(5):
            self.store.increment_quest_counter(
                self.character_id, 3020, "mob_517")
        self.assertEqual(
            self.store.get_quest_counter(
                self.character_id, 3020, "mob_517").counter_value, 5
        )

    def test_a_negative_delta_is_allowed(self):
        self.store.set_quest_counter(self.character_id, 3020, "mob_517", 4)
        row = self.store.increment_quest_counter(
            self.character_id, 3020, "mob_517", -3)
        self.assertEqual(row.counter_value, 1)

    def test_a_total_sqlite_cannot_hold_is_refused_and_writes_nothing(self):
        self.store.set_quest_counter(
            self.character_id, 3020, "mob_517", 2 ** 63 - 1)
        with self.assertRaises(ValueError):
            self.store.increment_quest_counter(
                self.character_id, 3020, "mob_517", 1)
        self.assertEqual(
            self.store.get_quest_counter(
                self.character_id, 3020, "mob_517").counter_value,
            2 ** 63 - 1,
        )

    def test_an_empty_counter_name_is_refused(self):
        for door in (
            lambda: self.store.set_quest_counter(
                self.character_id, 3020, "", 1),
            lambda: self.store.increment_quest_counter(
                self.character_id, 3020, ""),
            lambda: self.store.get_quest_counter(self.character_id, 3020, ""),
        ):
            with self.assertRaises(ValueError):
                door()

    def test_a_counter_name_past_128_characters_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.set_quest_counter(
                self.character_id, 3020, "x" * 129, 1)
        self.assertEqual(
            self.store.set_quest_counter(
                self.character_id, 3020, "x" * 128, 1).counter_value, 1
        )

    def test_a_non_string_counter_name_is_refused(self):
        with self.assertRaises(TypeError):
            self.store.set_quest_counter(self.character_id, 3020, 517, 1)

    def test_a_missing_character_is_refused_by_both_write_doors(self):
        with self.assertRaises(KeyError):
            self.store.set_quest_counter(999999, 3020, "mob_517", 1)
        with self.assertRaises(KeyError):
            self.store.increment_quest_counter(999999, 3020, "mob_517")
        self.assertEqual(
            _raw(self.path, "SELECT COUNT(*) FROM character_quest_counter"),
            [(0,)],
        )

    def test_a_soft_deleted_character_is_refused(self):
        _soft_delete(self.path, self.character_id)
        with self.assertRaises(KeyError):
            self.store.increment_quest_counter(
                self.character_id, 3020, "mob_517")

    def test_the_read_side_refuses_a_missing_character_too(self):
        with self.assertRaises(KeyError):
            self.store.get_quest_counter(999999, 3020, "mob_517")

    def test_set_quest_counter_returns_what_the_table_holds_not_its_argument(
            self):
        """PAYS pf-adversary D2 (round `6vv9mi`): only the FLAG door had
        this test, so a counter door that echoed its arguments survived
        every mutant.  Same method as the flag door's: a trigger rewrites
        the row behind the door's back, so an echoing door reports 3 and an
        honest one reports 4242."""
        _rewrite_trigger(self.path)
        written = self.store.set_quest_counter(
            self.character_id, 3020, "mob_517", 3)
        self.assertEqual(written.counter_value, 4242)

    def test_increment_returns_what_the_table_holds_not_its_own_sum(self):
        _rewrite_trigger(self.path)
        row = self.store.increment_quest_counter(
            self.character_id, 3020, "mob_517", 3)
        self.assertEqual(row.counter_value, 4242)

    def test_incrementing_by_zero_still_moves_updated_at(self):
        first = self.store.increment_quest_counter(
            self.character_id, 3020, "mob_517", 5)
        second = self.store.increment_quest_counter(
            self.character_id, 3020, "mob_517", 0)
        self.assertEqual(second.counter_value, 5)
        self.assertNotEqual(second.updated_at, first.updated_at)

    def test_the_read_matches_the_name_exactly_not_a_range(self):
        """A read that matched `counter_name>=?` would answer one tracker
        with another tracker's count."""
        self.store.set_quest_counter(self.character_id, 3020, "mob_517", 3)
        self.store.set_quest_counter(self.character_id, 3020, "mob_518", 8)
        self.assertEqual(
            self.store.get_quest_counter(
                self.character_id, 3020, "mob_517").counter_value, 3
        )


class TheRowsSurviveARelogTests(_Workspace):
    """"Survives relog" reduces, at the storage layer, to "a brand new
    `SQLiteStore` over the same file reads the same row" -- the same claim
    every other typed column in this schema makes, and no more."""

    def test_a_flag_and_a_counter_are_both_still_there_after_a_reopen(self):
        self.store.set_quest_flag(self.character_id, 3020, 2)
        self.store.increment_quest_counter(
            self.character_id, 3020, "mob_517", 3)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        reopened.migrate()
        self.assertEqual(
            reopened.get_quest_flag(self.character_id, 3020).flag_value, 2
        )
        self.assertEqual(
            reopened.get_quest_counter(
                self.character_id, 3020, "mob_517").counter_value, 3
        )

    def test_a_second_migrate_does_not_re_apply_019(self):
        versions = _raw(
            self.path, "SELECT version FROM schema_migrations ORDER BY version"
        )
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(
            _raw(
                self.path,
                "SELECT version FROM schema_migrations ORDER BY version",
            ),
            versions,
        )
        self.assertIn((19,), versions)


class TheContractIsTheOneLaneQCallsTests(unittest.TestCase):
    """`20260908_1642` forbids redesigning `2212`, and LANE-Q's adapter
    calls these five names with these argument names.  Read off the class,
    so renaming a parameter is red here rather than at LANE-Q's boot."""

    EXPECTED = {
        "set_quest_flag": ["self", "character_id", "quest_id", "flag_value"],
        "get_quest_flag": ["self", "character_id", "quest_id"],
        "set_quest_counter": [
            "self", "character_id", "quest_id", "counter_name",
            "counter_value",
        ],
        "get_quest_counter": [
            "self", "character_id", "quest_id", "counter_name",
        ],
        "increment_quest_counter": [
            "self", "character_id", "quest_id", "counter_name", "delta",
        ],
    }

    def test_every_declared_door_exists_with_the_declared_parameters(self):
        for name, parameters in self.EXPECTED.items():
            door = getattr(SQLiteStore, name, None)
            self.assertIsNotNone(door, name)
            self.assertEqual(
                list(inspect.signature(door).parameters), parameters, name
            )

    def test_delta_defaults_to_one(self):
        delta = inspect.signature(
            SQLiteStore.increment_quest_counter
        ).parameters["delta"]
        self.assertEqual(delta.default, 1)


class TheWriteLockIsReportedAsOursTests(_Workspace):
    """`2212`: a lock clash raises `WriteLockTimeout`, not a raw
    `sqlite3.OperationalError` -- so LANE-Q's adapter can tell "somebody
    else is writing" apart from "this database is broken".  Provoked the
    way the sibling doors' tests provoke it (`tests/test_persistence_
    character_skills_gm_grant_018.py`): `BEGIN IMMEDIATE` is made to raise
    once, because a real second writer would need a second process to hold
    the lock past `connect()`'s own busy timeout."""

    def _refusing_connect(self):
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
        return lambda *a, **k: _RaisesOnFirstBeginImmediate(
            real_connect(*a, **k)
        )

    def _assert_timeout(self, door):
        with mock.patch("sqlite3.connect", side_effect=self._refusing_connect()):
            with self.assertRaises(WriteLockTimeout):
                door()
        self.assertEqual(
            _raw(self.path, "SELECT COUNT(*) FROM character_quest_flag"),
            [(0,)],
        )
        self.assertEqual(
            _raw(self.path, "SELECT COUNT(*) FROM character_quest_counter"),
            [(0,)],
        )

    def test_set_quest_flag_raises_our_own_timeout(self):
        self._assert_timeout(
            lambda: self.store.set_quest_flag(self.character_id, 3020, 1)
        )

    def test_set_quest_counter_raises_our_own_timeout(self):
        self._assert_timeout(
            lambda: self.store.set_quest_counter(
                self.character_id, 3020, "mob_517", 1)
        )

    def test_increment_quest_counter_raises_our_own_timeout(self):
        self._assert_timeout(
            lambda: self.store.increment_quest_counter(
                self.character_id, 3020, "mob_517")
        )

    def test_an_operational_error_that_is_not_a_lock_is_not_disguised(self):
        """The `_LOCKED` check exists so a genuinely broken database does
        not come back wearing this lane's own exception."""
        class _RaisesSomethingElse:
            def __init__(self, real):
                object.__setattr__(self, "_real", real)
                object.__setattr__(self, "_raised", False)

            def execute(self, sql, *args, **kwargs):
                if sql == "BEGIN IMMEDIATE" and not self._raised:
                    object.__setattr__(self, "_raised", True)
                    raise sqlite3.OperationalError("disk I/O error")
                return self._real.execute(sql, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self._real, name)

            def __setattr__(self, name, value):
                setattr(self._real, name, value)

        real_connect = sqlite3.connect
        with mock.patch(
            "sqlite3.connect",
            side_effect=lambda *a, **k: _RaisesSomethingElse(
                real_connect(*a, **k)
            ),
        ):
            with self.assertRaises(sqlite3.OperationalError) as caught:
                self.store.set_quest_flag(self.character_id, 3020, 1)
        self.assertNotIsInstance(caught.exception, WriteLockTimeout)


if __name__ == "__main__":
    unittest.main()
