"""LANE-DB: what `migrations/017_character_experience_skill_points_birth_
defaults.sql` changes, and what a rebuild of the owner's `characters` table
must be proved not to have done.

WHAT 017 IS.  A rebuild of `characters` that attaches `DEFAULT 0` to
`experience` and to `skill_points`, and changes nothing else -- not a value on
a row, not another column's default, not an index, not a child row.  It is the
half `016` could not carry: `016` wrote 0 over the NULL every EXISTING row
held, and its own header records that a character born AFTERWARDS still holds
NULL in both columns and is still refused by `store.grant_experience` and
`store.spend_skill_points`.  This file is where "a character created today can
be paid by a quest" stops being a claim.

WHY THE TWO HALVES SHIP TOGETHER.  A fifth and sixth birth column used to turn
39 tests red at one shared fixture, because `tests/pf_birth_state.py` named
the accepted birth states as literal dicts.  `PANYA-DECISION 20260908_1218`
point 3 ordered both: this migration, and that pin rewritten to MEASURE the
birth state from the schema.  `tests/test_birth_state_is_derived_from_the_
schema.py` grades the pin; this file grades the migration.

THE TWO SENTENCES THIS FILE EXISTS TO SEPARATE.  "A newborn now starts at 0"
and "nobody who already existed was touched".  A rebuild can make the first
true and the second false in a way no per-column pragma check can see, so the
rows are compared value by value, NULL-safely, before and after -- and the
fixture deliberately contains a row holding a real 0, a row holding a real
number, and a soft-deleted tombstone, because a mutant that rewrites every
row to 0 is invisible against a table where every row is 0 already.

WHAT THIS FILE DOES NOT CLAIM.  It does not claim a player has seen a quest
pay out -- nothing here boots a client.  It claims the checkable half: that
after 017 a character created by `store.create_character` holds 0 in both
columns rather than NULL, that the two doors stop refusing it for being
unmeasured, and that the owner's existing rows come through the rebuild
unchanged in every column, with every index, child row and other object
intact.
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

from pirateforce_foundation import persistence_experience as experience_rule  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
SEVENTEEN = MIGRATIONS / "017_character_experience_skill_points_birth_defaults.sql"

#: The two columns 017 gives a default.  Read once, so a test cannot pass by
#: agreeing with itself about a different pair than the SQL uses.
DEFAULTED_COLUMNS = ("experience", "skill_points")

#: The default value, as `pragma_table_info` reports it (a text literal).
DEFAULT_LITERAL = "0"

#: The version this file grades, derived from the migration's filename so a
#: renumbering cannot leave this file grading a version that no longer exists.
SEVENTEEN_VERSION = int(SEVENTEEN.name[:3])

#: Same derivation as `016`'s file, and for the same reason: a fixture whose
#: experience already reaches the next level's threshold is refused by
#: `grant_experience` for a reason this file is not about.
VETERAN_EXPERIENCE = experience_rule.threshold_for_next_level(1) // 2


def _sql(path, query, args=()):
    db = sqlite3.connect(str(path))
    try:
        return [tuple(row) for row in db.execute(query, args)]
    finally:
        db.close()


def _table_info(path, table="characters"):
    return _sql(
        path,
        'SELECT cid,name,type,"notnull",dflt_value,pk FROM pragma_table_info(?)',
        (table,),
    )


def _indexes(path, table="characters"):
    return sorted(
        _sql(
            path,
            "SELECT name,sql FROM sqlite_master WHERE type='index' AND tbl_name=?",
            (table,),
        )
    )


def _ddl(path, table="characters"):
    return _sql(
        path,
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )[0][0]


def _squeeze(text):
    for ch in (" ", "\n", "\t", "\r"):
        text = text.replace(ch, "")
    return text


def _build_wire(selector):
    return b"wire-%d" % selector, b"avatar", 0x60000001 + selector, 0


def _build_wire_second(selector):
    return b"wire-b-%d" % selector, b"avatar", 0x70000001 + selector, 0


class _Base(unittest.TestCase):
    """A database built by the REAL migration directory, stopped at 016, so
    "before 017" is the state the owner's database is actually in rather than
    a hand-written table that resembles it.

    Both trees are pinned by NUMBER rather than by "whatever `migrations/`
    holds today", the lesson `009`'s file learned when a `010` landed beside
    it: a tree that means "up to here" has to say where here is.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "state.sqlite3"
        self.upto_016 = self._tree("migrations_016", SEVENTEEN_VERSION - 1)
        self.upto_017 = self._tree("migrations_017", SEVENTEEN_VERSION)

    def _tree(self, name, last):
        directory = self.root / name
        directory.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) <= last:
                shutil.copy(path, directory / path.name)
        return directory

    def _store_at_016(self):
        store = SQLiteStore(self.path, self.upto_016)
        store.migrate()
        return store

    def _store_at_017(self):
        return SQLiteStore(self.path, self.upto_017)

    def _create(self, store, account_id, name, tag, build=_build_wire, x=1.0):
        return store.create_character(
            account_id,
            name,
            name.casefold(),
            "fingerprint-%s" % tag,
            build,
            Position(3, 0, x, 2.0, 3.0, heading=0.0),
        )

    def _populate(self, store):
        """Four characters covering every case the guards must distinguish:
        one holding the 0 that `016` backfilled, one holding a real number, one
        holding a NULL that nothing has reached, and a soft-deleted tombstone.

        The NULL is built deliberately rather than inherited.  After `016` no
        row in a migrated database holds NULL in these columns, so without this
        the file could not tell "017 left a NULL alone" (which is what guard 1
        requires: 017 is NOT a backfill) from "there was no NULL to leave".
        """
        account = store.ensure_account("account-a")
        rookie = self._create(store, account, "Rookie", "rookie", x=1.0)
        veteran = self._create(store, account, "Veteran", "veteran", x=4.0)
        untouched = self._create(store, account, "Untouched", "untouched", x=7.0)
        other = store.ensure_account("account-b")
        ghost = self._create(store, other, "Ghost", "ghost", _build_wire_second, 9.0)
        db = sqlite3.connect(str(self.path))
        try:
            db.execute(
                "UPDATE characters SET experience=?, skill_points=? WHERE id=?",
                (VETERAN_EXPERIENCE, 7, veteran.id),
            )
            db.execute(
                "UPDATE characters SET experience=NULL, skill_points=NULL "
                "WHERE id=?",
                (untouched.id,),
            )
            db.commit()
        finally:
            db.close()
        session = store.open_session(other)
        store.soft_delete_character(session, ghost.selector)
        store.close_session(session)
        return {
            "rookie": rookie.id,
            "veteran": veteran.id,
            "untouched": untouched.id,
            "ghost": ghost.id,
        }

    def _row(self, character_id):
        return _sql(
            self.path,
            "SELECT experience,skill_points,deleted_at,level,hp_current,"
            "hp_max,speed_walk,name,selector,identity_lo FROM characters "
            "WHERE id=?",
            (character_id,),
        )[0]


class WhatSeventeenChangesTests(_Base):
    """The schema half: two defaults appear, and only those two."""

    def test_the_two_columns_gain_a_default_of_zero(self):
        store = self._store_at_016()
        before = {row[1]: row[4] for row in _table_info(self.path)}
        for column in DEFAULTED_COLUMNS:
            self.assertIsNone(
                before[column],
                "%s already carried a default before 017; this file would "
                "then be changing one rather than adding one" % column,
            )
        self._store_at_017().migrate()
        after = {row[1]: row[4] for row in _table_info(self.path)}
        for column in DEFAULTED_COLUMNS:
            self.assertEqual(after[column], DEFAULT_LITERAL)
        del store

    def test_no_other_column_gained_or_lost_a_default(self):
        self._store_at_016()
        before = {row[1]: row[4] for row in _table_info(self.path)}
        self._store_at_017().migrate()
        after = {row[1]: row[4] for row in _table_info(self.path)}
        moved = sorted(
            name for name in after if after[name] != before.get(name)
        )
        self.assertEqual(moved, sorted(DEFAULTED_COLUMNS))

    def test_identity_hi_keeps_the_default_zero_it_has_carried_since_004(self):
        """The trap this file's guard 6 is written around.  `identity_hi`
        already reads `DEFAULT 0`, so a text guard that subtracted the string
        `DEFAULT0` blindly would delete this one from both sides and go green
        over its loss -- and a character whose `identity_hi` arrived NULL
        would break the UNIQUE index that keeps two characters from sharing
        an identity."""
        self._store_at_016()
        self._store_at_017().migrate()
        after = {row[1]: row[4] for row in _table_info(self.path)}
        self.assertEqual(after["identity_hi"], "0")

    def test_the_column_list_is_otherwise_identical(self):
        self._store_at_016()
        before = [row[:4] + row[5:] for row in _table_info(self.path)]
        self._store_at_017().migrate()
        after = [row[:4] + row[5:] for row in _table_info(self.path)]
        self.assertEqual(after, before)

    def test_the_stored_ddl_differs_only_by_the_two_default_clauses(self):
        """The whole declaration, graded on its text: a dropped CHECK, a lost
        `REFERENCES`, an added `COLLATE`, a widened range and a renamed
        constraint are all invisible to `pragma_table_info` and all visible
        here.  `009`'s header records six such rebuilds committing green
        through a pragma-only draft."""
        self._store_at_016()
        before = _squeeze(_ddl(self.path))
        self._store_at_017().migrate()
        after = _squeeze(_ddl(self.path))
        self.assertNotEqual(after, before, "017 changed nothing at all")
        undone = after.replace(
            "experienceINTEGERDEFAULT0", "experienceINTEGER"
        ).replace("skill_pointsINTEGERDEFAULT0", "skill_pointsINTEGER")
        self.assertEqual(undone, before)

    def test_every_index_came_back_byte_identical(self):
        self._store_at_016()
        before = _indexes(self.path)
        self._store_at_017().migrate()
        self.assertEqual(_indexes(self.path), before)
        self.assertEqual(len(before), 4, "the four indexes of 004")

    def test_no_scratch_table_of_this_migration_survives(self):
        self._store_at_016()
        self._store_at_017().migrate()
        left = _sql(
            self.path,
            "SELECT name FROM sqlite_master WHERE name LIKE '\\_pf\\_mig017\\_%' "
            "ESCAPE '\\'",
        )
        self.assertEqual(left, [])

    def test_this_file_adds_no_object_to_the_database_at_all(self):
        self._store_at_016()
        before = sorted(
            _sql(
                self.path,
                "SELECT type,name,tbl_name,sql FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' AND name<>'characters'",
            )
        )
        self._store_at_017().migrate()
        after = sorted(
            _sql(
                self.path,
                "SELECT type,name,tbl_name,sql FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' AND name<>'characters'",
            )
        )
        self.assertEqual(after, before)


class WhatSeventeenLeavesAloneTests(_Base):
    """The row half.  017 is not a backfill and the rows are where that is
    either true or a sentence in a comment."""

    def test_every_existing_row_comes_through_unchanged(self):
        store = self._store_at_016()
        ids = self._populate(store)
        before = {name: self._row(cid) for name, cid in ids.items()}
        self._store_at_017().migrate()
        after = {name: self._row(cid) for name, cid in ids.items()}
        self.assertEqual(after, before)

    def test_a_null_left_by_hand_is_still_null_afterwards(self):
        """A DEFAULT applies to an INSERT that omits the column; it does not
        reach a row that already exists.  This is the difference between 017
        and 016 stated on a row rather than in a header."""
        store = self._store_at_016()
        ids = self._populate(store)
        self._store_at_017().migrate()
        experience, skill_points = self._row(ids["untouched"])[:2]
        self.assertIsNone(experience)
        self.assertIsNone(skill_points)

    def test_the_veterans_numbers_survive(self):
        store = self._store_at_016()
        ids = self._populate(store)
        self._store_at_017().migrate()
        self.assertEqual(
            self._row(ids["veteran"])[:2], (VETERAN_EXPERIENCE, 7)
        )

    def test_the_soft_deleted_tombstone_survives(self):
        """A rebuild that lost `deleted_at` would resurrect a deleted
        character into its account's selector list, and the account would
        then hold a character its owner deleted."""
        store = self._store_at_016()
        ids = self._populate(store)
        before = self._row(ids["ghost"])[2]
        self.assertIsNotNone(before, "the fixture failed to soft-delete")
        self._store_at_017().migrate()
        self.assertEqual(self._row(ids["ghost"])[2], before)

    def test_the_child_rows_survive(self):
        store = self._store_at_016()
        self._populate(store)
        tables = (
            "character_positions",
            "character_backpacks",
            "character_backpack_items",
            "character_skills",
            "character_home_marker",
            "character_equipment",
            "sessions",
        )
        before = {
            table: _sql(self.path, "SELECT COUNT(*) FROM %s" % table)[0][0]
            for table in tables
        }
        self.assertTrue(
            before["character_positions"] and before["character_backpacks"],
            "the fixture produced no child rows, so their survival is vacuous",
        )
        self._store_at_017().migrate()
        after = {
            table: _sql(self.path, "SELECT COUNT(*) FROM %s" % table)[0][0]
            for table in tables
        }
        self.assertEqual(after, before)
        self.assertEqual(
            _sql(self.path, "SELECT COUNT(*) FROM pragma_foreign_key_check()"),
            [(0,)],
        )

    def test_an_empty_table_migrates_cleanly(self):
        self._store_at_016()
        self._store_at_017().migrate()
        self.assertEqual(
            _sql(self.path, "SELECT COUNT(*) FROM characters"), [(0,)]
        )

    def test_running_the_whole_directory_twice_changes_nothing(self):
        store = self._store_at_016()
        ids = self._populate(store)
        self._store_at_017().migrate()
        ddl, rows = _ddl(self.path), {n: self._row(c) for n, c in ids.items()}
        self._store_at_017().migrate()
        self.assertEqual(_ddl(self.path), ddl)
        self.assertEqual({n: self._row(c) for n, c in ids.items()}, rows)


class TheDoorThatRefusedEveryNewbornTests(_Base):
    """The reason the file exists, measured on a character created AFTER it.

    `016` opened the two doors for everybody who already existed.  These are
    the tests that say the door is open for somebody created today -- which is
    the sentence `016`'s own header says it could not make.
    """

    def _newborn_after_017(self):
        store = self._store_at_016()
        migrated = self._store_at_017()
        migrated.migrate()
        account = migrated.ensure_account("account-new")
        character = self._create(migrated, account, "Newborn", "newborn", x=2.0)
        del store
        return migrated, character

    def test_a_character_created_after_017_is_born_holding_zero(self):
        _, character = self._newborn_after_017()
        self.assertEqual(self._row(character.id)[:2], (0, 0))

    def test_grant_experience_does_not_refuse_a_newborn_as_unmeasured(self):
        store, character = self._newborn_after_017()
        store.grant_experience(character.id, 1)
        self.assertEqual(self._row(character.id)[0], 1)

    def test_spend_skill_points_refuses_for_affordability_not_for_silence(self):
        """The distinction that matters: before 017 a newborn was refused
        because nobody had ever measured the column.  Afterwards it is refused
        because it has 0 points and cannot afford 1 -- a different exception,
        and one a player can act on by earning points."""
        store, character = self._newborn_after_017()
        with self.assertRaises(Exception) as caught:
            store.spend_skill_points(character.id, 1)
        self.assertNotIn("Unmeasured", type(caught.exception).__name__)

    def test_a_character_created_before_017_is_unaffected_by_it(self):
        store = self._store_at_016()
        ids = self._populate(store)
        before = self._row(ids["rookie"])
        self._store_at_017().migrate()
        self.assertEqual(self._row(ids["rookie"]), before)


class TheGuardsInTheFileReallyFireTests(_Base):
    """A guard that has never failed is a guess.

    Each mutant below is a deliberately wrong version of 017, written into a
    throwaway migration directory.  Each must be REFUSED, the refusal must
    NAME the guard the test is about, and the database must still hold its
    pre-017 table -- a mutant caught by a SQL error rather than by a guard, or
    caught by the WRONG guard, is a failure here rather than a green tick.
    """

    def _guard_names(self):
        text = SEVENTEEN.read_text(encoding="utf-8")
        return [chunk.split()[0] for chunk in text.split("CONSTRAINT ")[1:]]

    def _mutated_dir(self, replacements):
        mutant_root = self.root / ("mutant_%d" % len(list(self.root.iterdir())))
        mutant_root.mkdir()
        for path in sorted(self.upto_016.glob("[0-9][0-9][0-9]_*.sql")):
            shutil.copy(path, mutant_root / path.name)
        # newline="" on both halves: `read_text`/`write_text` translate line
        # endings and the Windows gate grades bytes.
        with SEVENTEEN.open(encoding="utf-8", newline="") as handle:
            text = handle.read()
        for old, new in replacements:
            self.assertIn(old, text, "the mutation target left the file")
            text = text.replace(old, new, 1)
        with (mutant_root / SEVENTEEN.name).open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            handle.write(text)
        return mutant_root

    def _refuses(self, guard, replacements):
        store = self._store_at_016()
        ids = self._populate(store)
        before_ddl = _ddl(self.path)
        before_rows = {name: self._row(cid) for name, cid in ids.items()}
        mutant = SQLiteStore(self.path, self._mutated_dir(replacements))
        with self.assertRaises(sqlite3.IntegrityError) as caught:
            mutant.migrate()
        self.assertIn(guard, str(caught.exception))
        self.assertEqual(_ddl(self.path), before_ddl, "the table was left mutated")
        self.assertEqual(
            {name: self._row(cid) for name, cid in ids.items()},
            before_rows,
            "the rows were left mutated",
        )
        self.assertEqual(
            _sql(
                self.path,
                "SELECT COUNT(*) FROM schema_migrations WHERE version=?",
                (SEVENTEEN_VERSION,),
            ),
            [(0,)],
            "the mutant's ledger row committed, so nothing was rolled back "
            "and the guard did not refuse the file at all",
        )
        return guard

    def test_a_rebuild_that_backfills_while_it_rebuilds_is_refused(self):
        """The failure that would make 017 a backfill in disguise: the copy
        writes `COALESCE(experience,0)` and every NULL a player still holds
        silently becomes a number nobody measured for them."""
        self._refuses(
            "guard_no_row_changed_in_any_column",
            [
                (
                    "     stat_per,experience,cash,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per\n"
                    "    FROM characters;",
                    "     stat_per,COALESCE(experience,0),cash,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per\n"
                    "    FROM characters;",
                ),
            ],
        )

    def test_a_rebuild_that_drops_the_soft_delete_tombstone_is_refused(self):
        self._refuses(
            "guard_no_row_changed_in_any_column",
            [("created_at,updated_at,deleted_at,name_key,\n"
              "     create_fingerprint,level,hp_current,hp_max,mp_current,mp_max,speed_walk,\n"
              "     class_id,skill_points,unspent_points,stat_str,stat_con,stat_dex,stat_int,\n"
              "     stat_per,experience,cash,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per\n"
              "    FROM characters;",
              "created_at,updated_at,NULL,name_key,\n"
              "     create_fingerprint,level,hp_current,hp_max,mp_current,mp_max,speed_walk,\n"
              "     class_id,skill_points,unspent_points,stat_str,stat_con,stat_dex,stat_int,\n"
              "     stat_per,experience,cash,bonus_str,bonus_con,bonus_dex,bonus_int,bonus_per\n"
              "    FROM characters;")],
        )

    def test_a_rebuild_that_moves_another_columns_default_is_refused(self):
        """`identity_hi` loses the `DEFAULT 0` it has carried since `004`.
        Guard 6 subtracts this file's own two defaults BY COLUMN NAME for
        exactly this reason; a blind `replace('DEFAULT0','')` would have gone
        green here."""
        self._refuses(
            "guard_the_column_list_is_unchanged",
            [("    identity_hi INTEGER NOT NULL DEFAULT 0,",
              "    identity_hi INTEGER NOT NULL,")],
        )

    def test_a_rebuild_that_defaults_a_third_column_is_refused(self):
        """`cash` is one of the seventeen typed columns nobody has adjudicated
        a birth value for.  A file that quietly gives it one is inventing a
        number for every character created afterwards.

        THE COLUMN-LIST GUARD IS THE ONE THAT FIRES, not the defaults guard,
        and that is the ordering this file wants: guard 2 allows a default to
        move only on the two columns 017 names, so a third column is refused
        by the guard whose message names the column list.  Guard 3 is what
        catches the case guard 2 deliberately lets through -- one of THOSE two
        columns getting a number other than 0, which
        `test_a_rebuild_that_defaults_one_of_the_two_to_something_else_is_
        refused` is."""
        self._refuses(
            "guard_the_column_list_is_unchanged",
            [("    cash INTEGER\n        CHECK(cash IS NULL OR (typeof(cash)='integer'",
              "    cash INTEGER DEFAULT 0\n        CHECK(cash IS NULL OR (typeof(cash)='integer'")],
        )

    def test_a_rebuild_that_defaults_one_of_the_two_to_something_else_is_refused(self):
        self._refuses(
            "guard_exactly_the_two_defaults_were_added",
            [("    skill_points INTEGER DEFAULT 0",
              "    skill_points INTEGER DEFAULT 2")],
        )

    def test_a_rebuild_that_forgets_an_index_is_refused(self):
        self._refuses(
            "guard_every_index_came_back",
            [("CREATE UNIQUE INDEX characters_active_selector ON characters(account_id, selector) WHERE deleted_at IS NULL;\n", "")],
        )

    def test_a_rebuild_that_recreates_an_index_without_its_predicate_is_refused(self):
        """A partial index rebuilt as a total one: every soft-deleted row keeps
        holding its selector, so an account that deleted a character can never
        create another in that slot."""
        self._refuses(
            "guard_every_index_came_back",
            [("CREATE UNIQUE INDEX characters_active_selector ON characters(account_id, selector) WHERE deleted_at IS NULL;",
              "CREATE UNIQUE INDEX characters_active_selector ON characters(account_id, selector);")],
        )

    def test_a_rebuild_that_leaves_the_foreign_keys_on_is_refused(self):
        """The catastrophe this shape is capable of, and the one mutant that
        was a live defect in this file before it was measured.  With the
        `PRAGMA foreign_keys=OFF` line gone, `DROP TABLE characters` performs
        its implicit `DELETE FROM`, the ON DELETE CASCADE on
        `character_positions` and `character_backpacks` fires, and the
        grandchild rows in `character_backpack_items` go with them -- while
        the rebuilt table still holds every character row and NOTHING IS
        ORPHANED afterwards, because nothing is left to be orphaned.  That is
        why guard 5 counts survivors instead of asking for orphans."""
        self._refuses(
            "guard_the_child_rows_all_survived",
            [("COMMIT;\nPRAGMA foreign_keys=OFF;\nBEGIN IMMEDIATE;\n",
              "COMMIT;\nBEGIN IMMEDIATE;\n")],
        )

    def test_a_rebuild_that_drops_a_check_constraint_is_refused(self):
        """Invisible to `pragma_table_info` in every column.  `009` records
        three of these committing green through a pragma-only draft."""
        self._refuses(
            "guard_the_table_declaration_is_unchanged",
            [("    cash INTEGER\n        CHECK(cash IS NULL OR (typeof(cash)='integer' AND cash BETWEEN 0 AND 9223372036854775807)),",
              "    cash INTEGER,")],
        )

    def test_a_rebuild_that_drops_the_foreign_key_to_accounts_is_refused(self):
        """The worst of `009`'s six, because it also makes every future orphan
        check on `characters` permanently vacuous."""
        self._refuses(
            "guard_the_table_declaration_is_unchanged",
            [("    account_id INTEGER NOT NULL REFERENCES accounts(id),",
              "    account_id INTEGER NOT NULL,")],
        )

    def test_a_rebuild_that_leaves_a_stray_object_behind_is_refused(self):
        self._refuses(
            "guard_every_other_object_is_unchanged",
            [("CREATE UNIQUE INDEX characters_active_identity ON characters(identity_lo, identity_hi) WHERE deleted_at IS NULL;",
              "CREATE UNIQUE INDEX characters_active_identity ON characters(identity_lo, identity_hi) WHERE deleted_at IS NULL;\n"
              "CREATE TABLE characters_leftover(x);")],
        )

    def test_every_guard_in_the_file_has_a_mutant_in_this_class(self):
        """What keeps the list above honest when a guard is added or removed.
        The name must appear as the FIRST ARGUMENT of a `self._refuses(` call,
        not merely somewhere in this file: `pf-adversary` (round `ywpicw`,
        D11) defeated the whole-source version of this scan in one line, by
        adding a guard to the SQL and writing its name into a Python comment
        here."""
        source = Path(__file__).read_text(encoding="utf-8")
        exercised = set(
            re.findall(r"self\._refuses\(\s*\n?\s*\"([a-z_]+)\"", source)
        )
        self.assertTrue(exercised, "the scan found no mutant call at all")
        names = self._guard_names()
        self.assertEqual(
            [n for n in names if n not in exercised],
            [],
            "guards with no `self._refuses` mutant naming them",
        )
        self.assertEqual(
            sorted(exercised - set(names)),
            [],
            "mutants naming a guard the migration no longer has",
        )
        self.assertEqual(
            len(names),
            len(set(names)),
            "two guards share a constraint name; SQLite would report the "
            "wrong one and a mutant test would pass for the wrong reason",
        )


class TheChildrenGuardCannotFallBehindTests(_Base):
    """A guard that names child tables by hand goes stale the day another lane
    adds one, and it goes stale SILENTLY.  So the list is derived from the
    schema here and compared with the file."""

    def test_the_children_guard_names_every_table_that_references_characters(self):
        self._store_at_016()
        db = sqlite3.connect(str(self.path))
        try:
            tables = [
                row[0]
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                )
            ]
            children = sorted(
                table
                for table in tables
                if any(
                    row[2] == "characters"
                    for row in db.execute("PRAGMA foreign_key_list(%s)" % table)
                )
            )
        finally:
            db.close()
        self.assertTrue(children, "no child table found; the query is wrong")
        text = SEVENTEEN.read_text(encoding="utf-8")
        guard = text.split("CONSTRAINT guard_the_child_rows_all_survived")[1]
        guard = guard.split("THEN 1 ELSE 0 END;")[0]
        missing = [table for table in children if table not in guard]
        self.assertEqual(
            missing,
            [],
            "these tables reference `characters` and would be cascade-deleted "
            "without the guard noticing",
        )

    def test_a_grandchild_table_is_covered_too(self):
        """`character_backpack_items` hangs off `character_backpacks`, not off
        `characters`, so the derivation above cannot see it and the guard has
        to name it explicitly."""
        self.assertIn(
            "character_backpack_items", SEVENTEEN.read_text(encoding="utf-8")
        )

    def test_the_rebuild_copies_every_column_the_table_has(self):
        """A column added by a future migration and forgotten in the copy list
        would arrive NULL on every row.  The copy list is compared with the
        table's real column list rather than read by eye."""
        self._store_at_016()
        columns = [row[1] for row in _table_info(self.path)]
        text = SEVENTEEN.read_text(encoding="utf-8")
        body = text.split("INSERT INTO characters_rebuild")[1].split(
            "FROM characters;"
        )[0]
        missing = [name for name in columns if name not in body]
        self.assertEqual(missing, [], "columns the rebuild would leave NULL")


class TheFileItselfTests(unittest.TestCase):
    def test_the_migration_is_pure_ascii(self):
        SEVENTEEN.read_bytes().decode("ascii")

    def test_the_file_is_the_next_free_number(self):
        numbers = sorted(
            int(path.name[:3])
            for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")
        )
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        self.assertEqual(numbers[-1], SEVENTEEN_VERSION)

    def test_the_decision_that_ordered_this_file_is_named_in_it(self):
        """`016` was cut down to a backfill on the authority of a decision
        naming four birth columns; this file exists because the owner reopened
        that herself.  A reader on the owner's machine has to be able to find
        which decision, without leaving the file."""
        text = SEVENTEEN.read_text(encoding="utf-8")
        self.assertIn("20260908_1218", text)
        self.assertIn("20260902_1607", text)

    def test_the_file_says_which_of_the_two_zeroes_is_measured(self):
        """The honesty this lane is held to: `experience = 0` is measured from
        a shipped table, `skill_points = 0` is the owner's instruction and
        nothing else.  A header that blurred the two would send the next round
        looking for evidence that does not exist."""
        text = SEVENTEEN.read_text(encoding="utf-8")
        self.assertIn("standard_status.tsv", text)
        self.assertIn("NOT MEASURED", text)


if __name__ == "__main__":
    unittest.main()
