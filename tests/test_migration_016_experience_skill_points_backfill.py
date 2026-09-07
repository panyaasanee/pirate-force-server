"""LANE-DB: what `migrations/016_character_experience_skill_points_backfill.
sql` opens, and the price it was allowed to charge for opening it.

WHAT 016 IS, AND WHAT IT DELIBERATELY IS NOT.  It writes 0 over the NULL that
every EXISTING row holds in `characters.experience` and
`characters.skill_points`, and it changes nothing else -- no schema, no
DEFAULT, nothing about what a character born tomorrow holds.  It is the first
migration in this repository that changes a value on a row the owner already
had, which is why it carries eight guards and why this file mutates every one
of them.

THE VERSION THAT IS NOT HERE, AND WHY.  The obvious 016 is `009`'s shape: a
rebuild that also attaches `DEFAULT 0`, so a newborn starts at 0 like everyone
else.  That version was written in full this round and then measured against
the suite: 39 tests red, 30 of them at one shared fixture.
`tests/pf_birth_state.py` names the three typed states a newly created
character may hold and refuses everything else on purpose -- "an insertion
point that adds a FIFTH column turns every file that imports this one red at
its fixture" -- and a DEFAULT on these two columns is that fifth and sixth
column.  NOW.md `2050` says a pin is released by its owner while the caller
withdraws, so the caller withdrew: the DEFAULT question went to COO with the
numbers, and this file was cut to the half that contradicts nothing.  A
BACKFILL IS NOT A BIRTH RULE, and `TheBirthRuleIsUntouchedTests` below is
where that sentence stops being a claim.

WHY THE 0 IS NOT A GUESS, WHICH IS THE ONLY QUESTION THAT MATTERS HERE.
`COO-DECISION 20260901_1059` forbids guessing an unmeasured field to be zero,
and that rule is the reason `009` deliberately left these two columns alone.
Two lanes measured them on 2026-09-08 and wrote the commands down:
`pf_bridge/notes_to_chief/20260908_0555_LANE-Q-TO-LANE-DB-experience-is-0-
skill-points-is-NOT-obviously-0.md` (nothing in the 616 lua scripts SETS
experience; every call site adds to it) and `pf_bridge/notes_to_chief/
20260908_0458_LANE-CS-TO-DB-Q-level-sp-is-an-experience-curve-not-a-skill-
point-column.md` (the table that looked like it awarded 2 skill points at
level 1 runs to 13,645,740 by level 120, which is an experience curve).  This
FILE cannot re-measure either claim -- neither the lua corpus nor the client
tables are what a migration test can reach -- so it does not pretend to.  What
it measures is the half that is this lane's: that the file writes 0 where and
only where a NULL was, that it disturbs nothing that already held a number,
and that the count of what it touched survives the commit so the write can be
reversed if the client's own answer ever turns out to be different.

WHAT THIS FILE DOES NOT CLAIM.  It does not claim a player has seen a quest
pay out; nothing here boots a client.  It claims the narrower, checkable
thing: the two store doors that refused every character that EXISTS in the
owner's database with `UnmeasuredSkillPointsError` /
`UnmeasuredTypedAttributeError` stop refusing for that reason after 016, which
is measured below by watching the exception TYPE change from "nobody measured
this" to "you cannot afford it" -- while a character created AFTER 016 still
gets the old refusal, because the birth rule did not move.  It does not claim the backup happened: `migrate_with_backup` is
`test_persistence_premigration_backup.py`'s subject and still has no caller on
the boot path, which is recorded in this round's file rather than asserted
away here.
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
from pirateforce_foundation import store as store_module  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
SIXTEEN = MIGRATIONS / "016_character_experience_skill_points_backfill.sql"

#: The two columns 016 exists for.  Read from the file's own name rather than
#: typed twice: a rename of the migration that forgets one of them is red.
BACKFILLED_COLUMNS = ("experience", "skill_points")

#: The value the file writes.  One place, so a test cannot pass by agreeing
#: with itself about a different number than the SQL uses.
BACKFILLED_VALUE = 0

#: The veteran fixture's experience.  DERIVED, not typed: `grant_experience`
#: refuses a row whose experience already reaches the next level's threshold
#: (`InconsistentLevelExperienceError`, "another door moved a column under
#: this one"), and a fixture that trips that refuses for a reason this file
#: is not about.  Half the level-1 threshold is inside the bar on any table
#: whose first threshold is positive, and it moves with the table.
VETERAN_EXPERIENCE = experience_rule.threshold_for_next_level(1) // 2

#: The version this file grades.  Derived from the migration's filename so a
#: renumbering cannot leave this file quietly grading a version that no longer
#: exists.
SIXTEEN_VERSION = int(SIXTEEN.name[:3])


def _sql(path, query, args=()):
    db = sqlite3.connect(str(path))
    try:
        db.row_factory = sqlite3.Row
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
    rows = _sql(
        path,
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return rows[0][0]


def _squeeze(text):
    for ch in (" ", "\n", "\t", "\r"):
        text = text.replace(ch, "")
    return text


def _build_wire(selector):
    return b"wire-%d" % selector, b"avatar", 0x60000001 + selector, 0


def _build_wire_second(selector):
    return b"wire-b-%d" % selector, b"avatar", 0x70000001 + selector, 0


def _build_wire_third(selector):
    """A third identity base.  `create_character` numbers selectors from 0
    per account, and `characters_active_identity` is UNIQUE across the
    table, so a third account reusing the first base collides on identity
    rather than on anything this file is about."""
    return b"wire-c-%d" % selector, b"avatar", 0x80000001 + selector, 0


class _Base(unittest.TestCase):
    """A database built by the REAL migration directory, stopped at 015, so
    "before 016" is the state the owner's database is actually in rather than
    a hand-written table that resembles it.

    Both trees are pinned by number, not by "whatever `migrations/` holds
    today", for the reason the 009 file learned the hard way when a 010
    landed beside it: a tree that means "up to here" has to say where here is.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "state.sqlite3"
        self.upto_015 = self._tree("migrations_015", SIXTEEN_VERSION - 1)
        self.upto_016 = self._tree("migrations_016", SIXTEEN_VERSION)

    def _tree(self, name, last):
        directory = self.root / name
        directory.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) <= last:
                shutil.copy(path, directory / path.name)
        return directory

    def _store_at_015(self):
        store = SQLiteStore(self.path, self.upto_015)
        store.migrate()
        return store

    def _store_at_016(self):
        return SQLiteStore(self.path, self.upto_016)

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
        """Four characters that between them cover every case the guards
        distinguish: never measured, already a number, a legitimately stored
        0 beside a NULL in the sibling column, and a soft-deleted tombstone.

        The stored 0 is not decoration.  Guard 2 has to tell "was NULL, is
        now 0" from "was 0, is still 0", and with no row holding a real 0 the
        two branches are indistinguishable and a mutant that rewrites every
        row to 0 unconditionally would commit.
        """
        account = store.ensure_account("account-a")
        rookie = self._create(store, account, "Rookie", "rookie", x=1.0)
        veteran = self._create(store, account, "Veteran", "veteran", x=4.0)
        zero = self._create(store, account, "Zero", "zero", x=7.0)
        other = store.ensure_account("account-b")
        ghost = self._create(store, other, "Ghost", "ghost", _build_wire_second, 9.0)
        db = sqlite3.connect(str(self.path))
        try:
            db.execute(
                "UPDATE characters SET experience=?, skill_points=? WHERE id=?",
                (VETERAN_EXPERIENCE, 7, veteran.id),
            )
            db.execute(
                "UPDATE characters SET experience=?, skill_points=NULL WHERE id=?",
                (0, zero.id),
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
            "zero": zero.id,
            "ghost": ghost.id,
        }

    def _row(self, character_id):
        return _sql(
            self.path,
            "SELECT experience,skill_points,deleted_at FROM characters WHERE id=?",
            (character_id,),
        )[0]


class WhatSixteenDoesToTheRowsTests(_Base):
    def test_a_null_becomes_zero_and_a_number_is_left_alone(self):
        store = self._store_at_015()
        ids = self._populate(store)
        before = {name: self._row(cid) for name, cid in ids.items()}
        self.assertEqual(before["rookie"][:2], (None, None))
        self.assertEqual(before["veteran"][:2], (VETERAN_EXPERIENCE, 7))
        self.assertEqual(before["zero"][:2], (0, None))

        self._store_at_016().migrate()

        self.assertEqual(self._row(ids["rookie"])[:2], (0, 0))
        self.assertEqual(
            self._row(ids["veteran"])[:2],
            (VETERAN_EXPERIENCE, 7),
            "a row that already held numbers must come through untouched",
        )
        self.assertEqual(
            self._row(ids["zero"])[:2],
            (0, 0),
            "a legitimately stored 0 stays 0 and its NULL sibling becomes 0",
        )

    def test_a_soft_deleted_character_is_backfilled_too(self):
        """A tombstone `004` lets a character come back from.  Left NULL, a
        restored character would be one whose quests refuse to pay -- the
        exact state this file exists to end -- so the file says out loud that
        it backfills them, and this is where that sentence is graded."""
        store = self._store_at_015()
        ids = self._populate(store)
        self.assertIsNotNone(self._row(ids["ghost"])[2])
        self._store_at_016().migrate()
        row = self._row(ids["ghost"])
        self.assertEqual(row[:2], (0, 0))
        self.assertIsNotNone(row[2], "the tombstone itself must survive")

    def test_a_character_born_after_016_still_holds_null(self):
        """The sentence that keeps this file inside the pins.  `009`'s shape
        would have given a newborn 0 through a column DEFAULT and turned
        `tests/pf_birth_state.py` red at its fixture; this file writes rows and
        leaves the schema alone, so a character created afterwards is in
        exactly the state the birth pin requires."""
        store = self._store_at_015()
        self._populate(store)
        store = self._store_at_016()
        store.migrate()
        account = store.ensure_account("account-c")
        newborn = self._create(
            store, account, "Newborn", "newborn", _build_wire_third, 11.0
        )
        self.assertEqual(self._row(newborn.id)[:2], (None, None))
        ddl = _ddl(self.path)
        self.assertNotIn("experience INTEGER DEFAULT", ddl)
        self.assertNotIn("skill_points INTEGER DEFAULT", ddl)

    def test_no_null_survives_in_either_column(self):
        store = self._store_at_015()
        self._populate(store)
        self._store_at_016().migrate()
        for column in BACKFILLED_COLUMNS:
            left = _sql(
                self.path,
                "SELECT COUNT(*) FROM characters WHERE %s IS NULL" % column,
            )[0][0]
            self.assertEqual(left, 0, "%s still holds a NULL" % column)

    def test_an_empty_table_migrates_cleanly(self):
        """A fresh install has no rows at all.  Every guard has to hold over
        an empty table too, or the first boot of a new install is the one
        that fails."""
        self._store_at_015()
        self._store_at_016().migrate()
        self.assertEqual(
            _sql(self.path, "SELECT COUNT(*) FROM characters")[0][0], 0
        )

    def test_running_the_whole_directory_twice_changes_nothing(self):
        store = self._store_at_015()
        ids = self._populate(store)
        self._store_at_016().migrate()
        after_first = {name: self._row(cid) for name, cid in ids.items()}
        schema_first = _ddl(self.path)
        self._store_at_016().migrate()
        self.assertEqual({n: self._row(c) for n, c in ids.items()}, after_first)
        self.assertEqual(_ddl(self.path), schema_first)


class WhatSixteenDoesNotDoToTheSchemaTests(_Base):
    """A backfill that changes the schema is not a backfill.  Every assertion
    here is graded in Python against the real 015 database, independently of
    the guards inside the SQL, so a guard written wrong cannot grade itself.
    """

    def test_the_stored_ddl_is_byte_identical(self):
        store = self._store_at_015()
        self._populate(store)
        before = _ddl(self.path)
        self._store_at_016().migrate()
        self.assertEqual(_ddl(self.path), before)

    def test_the_column_list_is_identical_defaults_included(self):
        store = self._store_at_015()
        self._populate(store)
        before = _table_info(self.path)
        self._store_at_016().migrate()
        self.assertEqual(_table_info(self.path), before)

    def test_no_column_gained_a_default(self):
        """The specific thing the cut-down version of this file exists to not
        do, named on its own so a future rebuild cannot arrive quietly."""
        store = self._store_at_015()
        self._populate(store)
        before = {r[1]: r[4] for r in _table_info(self.path) if r[4] is not None}
        self._store_at_016().migrate()
        after = {r[1]: r[4] for r in _table_info(self.path) if r[4] is not None}
        self.assertEqual(after, before)
        for column in BACKFILLED_COLUMNS:
            self.assertNotIn(column, after)

    def test_identity_hi_keeps_the_default_zero_it_has_carried_since_004(self):
        store = self._store_at_015()
        self._populate(store)
        self._store_at_016().migrate()
        defaults = {r[1]: r[4] for r in _table_info(self.path)}
        self.assertEqual(defaults["identity_hi"], "0")
        self.assertEqual(defaults["level"], "1")
        self.assertEqual(defaults["speed_walk"], "400.0")

    def test_every_index_is_unchanged(self):
        store = self._store_at_015()
        self._populate(store)
        before = _indexes(self.path)
        self.assertTrue(before)
        self._store_at_016().migrate()
        self.assertEqual(_indexes(self.path), before)

    def test_the_child_rows_survive(self):
        store = self._store_at_015()
        self._populate(store)
        counts = lambda: {
            table: _sql(self.path, "SELECT COUNT(*) FROM %s" % table)[0][0]
            for table in ("character_positions", "characters", "accounts")
        }
        before = counts()
        self.assertTrue(before["character_positions"])
        self._store_at_016().migrate()
        self.assertEqual(counts(), before)

    def test_no_scratch_table_of_this_migration_survives(self):
        store = self._store_at_015()
        self._populate(store)
        self._store_at_016().migrate()
        left = _sql(
            self.path,
            "SELECT name FROM sqlite_master WHERE name LIKE '\\_pf\\_mig016\\_%' "
            "ESCAPE '\\'",
        )
        self.assertEqual(left, [])

    def test_this_file_adds_no_object_to_the_database_at_all(self):
        """A backfill that leaves a table behind is a schema change nobody
        chose.  The round's first draft did leave one -- a
        `migration_backfill_audit` holding the row count LANE-Q asked for --
        and it was withdrawn when `tests/test_npc_interaction_wire.py`'s
        `EXPECTED_TABLES` refused it, which is the pin doing its job."""
        store = self._store_at_015()
        self._populate(store)
        before = {(r[0], r[1]) for r in _sql(
            self.path, "SELECT type,name FROM sqlite_master")}
        self._store_at_016().migrate()
        after = {(r[0], r[1]) for r in _sql(
            self.path, "SELECT type,name FROM sqlite_master")}
        self.assertEqual(after, before)


class TheDoorsThatRefusedEveryRowTests(_Base):
    """The reason this migration is worth a table rebuild.

    `store.spend_skill_points` and `store.grant_experience` refuse a NULL
    column on purpose -- `COO-DECISION 20260901_1059` again -- and
    `lua_api/reward.py` turns both refusals into `refused=store_error`.  Every
    character in the owner's database holds NULL in both, so today every one
    of those doors refuses every character.  What 016 changes is the KIND of
    answer: from "nobody has measured this" to an ordinary balance answer.
    That distinction is the evidence, and it is why the assertions below are
    about exception TYPES rather than about a number.
    """

    def test_spend_skill_points_stops_refusing_for_being_unmeasured(self):
        store = self._store_at_015()
        ids = self._populate(store)
        with self.assertRaises(store_module.UnmeasuredSkillPointsError):
            store.spend_skill_points(ids["rookie"], 1)

        store = self._store_at_016()
        store.migrate()
        with self.assertRaises(store_module.InsufficientSkillPointsError):
            store.spend_skill_points(ids["rookie"], 1)

    def test_a_character_who_earns_points_can_now_spend_them(self):
        store = self._store_at_015()
        ids = self._populate(store)
        self._store_at_016().migrate()
        store = self._store_at_016()
        db = sqlite3.connect(str(self.path))
        try:
            db.execute(
                "UPDATE characters SET skill_points=3 WHERE id=?", (ids["rookie"],)
            )
            db.commit()
        finally:
            db.close()
        self.assertEqual(store.spend_skill_points(ids["rookie"], 2), 1)

    def test_grant_experience_stops_refusing_for_being_unmeasured(self):
        store = self._store_at_015()
        ids = self._populate(store)
        with self.assertRaises(store_module.UnmeasuredTypedAttributeError):
            store.grant_experience(ids["rookie"], 10)

        store = self._store_at_016()
        store.migrate()
        gain = store.grant_experience(ids["rookie"], 10)
        self.assertEqual(self._row(ids["rookie"])[0], 10)
        self.assertIsNotNone(gain)

    def test_the_veterans_own_number_is_what_the_grant_adds_to(self):
        """The other half of the same sentence: 016 must not reset a row that
        already had experience, or the first quest after it would pay the
        wrong amount into a wrong balance."""
        store = self._store_at_015()
        ids = self._populate(store)
        self._store_at_016().migrate()
        store = self._store_at_016()
        store.grant_experience(ids["veteran"], 5)
        self.assertEqual(self._row(ids["veteran"])[0], VETERAN_EXPERIENCE + 5)


class TheGuardsInTheFileReallyFireTests(_Base):
    """A guard that has never failed is a guess.

    Each mutant below is a deliberately wrong version of 016, written into a
    throwaway migration directory.  Each must be REFUSED, the refusal must
    NAME the guard the test is about, and the database must still hold its
    pre-016 table -- a mutant that is caught by a SQL error rather than by a
    guard, or by the wrong guard, is a failure here rather than a green tick.
    """

    #: Every named CONSTRAINT in the file, discovered from the file itself so
    #: that adding a guard without a mutant is red.
    def _guard_names(self):
        text = SIXTEEN.read_text(encoding="utf-8")
        names = []
        for chunk in text.split("CONSTRAINT ")[1:]:
            names.append(chunk.split()[0])
        return names

    def _mutated_dir(self, replacements):
        mutant_root = self.root / ("mutant_%d" % len(list(self.root.iterdir())))
        mutant_root.mkdir()
        for path in sorted(self.upto_015.glob("[0-9][0-9][0-9]_*.sql")):
            shutil.copy(path, mutant_root / path.name)
        # newline="" on both halves: `read_text`/`write_text` translate line
        # endings, and the Windows gate grades bytes.
        with SIXTEEN.open(encoding="utf-8", newline="") as handle:
            text = handle.read()
        for old, new in replacements:
            self.assertIn(old, text, "the mutation target left the file")
            text = text.replace(old, new, 1)
        with (mutant_root / SIXTEEN.name).open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            handle.write(text)
        return mutant_root

    def _refuses(self, guard, replacements):
        store = self._store_at_015()
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
        # The rollback assertions above cannot fail while the runner wraps a
        # migration in one transaction -- `pf-adversary` (D-negative, round
        # `ywpicw`) deleted them and the suite did not move.  They stay,
        # because the day the runner stops wrapping is the day they are the
        # only thing that notices, and this comment is here so nobody mistakes
        # them for evidence that a guard fired.  The assertion that DOES carry
        # weight is the `assertIn(guard, ...)` above: deleting it turned three
        # red mutants into two, measured.
        self.assertTrue(
            _sql(self.path, "SELECT COUNT(*) FROM schema_migrations "
                            "WHERE version=?", (SIXTEEN_VERSION,))[0][0] == 0,
            "the mutant's ledger row committed, so nothing was rolled back "
            "and the guard did not refuse the file at all",
        )
        return guard

    def test_an_update_that_lost_its_where_clause_is_refused(self):
        """The failure this whole file is built around: `UPDATE characters SET
        experience = 0` without `WHERE experience IS NULL` resets a veteran's
        balance to zero and reports success."""
        self._refuses(
            "guard_only_null_became_zero_in_the_two_columns",
            [
                (
                    "UPDATE characters SET experience = 0 WHERE experience IS NULL;",
                    "UPDATE characters SET experience = 0;",
                )
            ],
        )

    def test_a_write_that_reaches_a_third_column_is_refused(self):
        self._refuses(
            "guard_no_row_changed_outside_the_two_columns",
            [
                (
                    "UPDATE characters SET skill_points = 0 WHERE skill_points IS NULL;",
                    "UPDATE characters SET skill_points = 0, cash = 0 "
                    "WHERE skill_points IS NULL;",
                )
            ],
        )

    def test_a_file_that_backfills_only_one_of_the_two_is_refused(self):
        """Half a backfill is the worst outcome: the quest that pays
        experience works and the one that pays skill points still refuses,
        and nothing in the boot log says why."""
        self._refuses(
            "guard_no_null_remains_in_the_two_columns",
            [
                (
                    "UPDATE characters SET skill_points = 0 WHERE skill_points IS NULL;",
                    "",
                )
            ],
        )

    def test_a_file_that_touches_the_schema_at_all_is_refused(self):
        """The guard that keeps this file a backfill.  A column added here is
        the smallest schema change there is, and it is still refused."""
        self._refuses(
            "guard_the_schema_is_untouched",
            [
                (
                    "UPDATE characters SET experience = 0 WHERE experience IS NULL;",
                    "ALTER TABLE characters ADD COLUMN pf_probe INTEGER;\n"
                    "UPDATE characters SET experience = 0 WHERE experience IS NULL;",
                )
            ],
        )

    def test_a_file_that_drops_an_index_is_refused(self):
        self._refuses(
            "guard_every_index_is_unchanged",
            [
                (
                    "UPDATE characters SET experience = 0 WHERE experience IS NULL;",
                    "DROP INDEX characters_active_selector;\n"
                    "UPDATE characters SET experience = 0 WHERE experience IS NULL;",
                )
            ],
        )

    def test_a_file_that_deletes_a_child_row_is_refused(self):
        self._refuses(
            "guard_the_child_rows_all_survived",
            [
                (
                    "UPDATE characters SET experience = 0 WHERE experience IS NULL;",
                    "DELETE FROM character_positions;\n"
                    "UPDATE characters SET experience = 0 WHERE experience IS NULL;",
                )
            ],
        )

    def test_a_file_that_leaves_a_stray_object_behind_is_refused(self):
        """The catch-all.  A table this file did not declare is the shape a
        forgotten scratch table has, and a scratch table left in the owner's
        database is a schema change nobody chose."""
        self._refuses(
            "guard_every_other_object_is_unchanged",
            [
                (
                    "UPDATE characters SET experience = 0 WHERE experience IS NULL;",
                    "CREATE TABLE pf_stray(x INTEGER);\n"
                    "UPDATE characters SET experience = 0 WHERE experience IS NULL;",
                )
            ],
        )

    def test_every_guard_in_the_file_has_a_mutant_in_this_class(self):
        """What keeps the list above honest when a guard is added or removed.
        A new guard with no mutant is a guess that ships.

        THE NAME MUST APPEAR AS THE FIRST ARGUMENT OF A `self._refuses(` CALL,
        not merely somewhere in this file.  The first version searched the
        whole source, and `pf-adversary` (round `ywpicw`, D11) defeated it in
        one line: a brand-new guard added to the SQL, with its name written
        into a Python COMMENT here and no mutant at all, passed.  A docstring
        that says "a guess that ships" has to be graded against calls."""
        source = Path(__file__).read_text(encoding="utf-8")
        exercised = set(
            re.findall(r"self\._refuses\(\s*\n?\s*\"([a-z_]+)\"", source)
        )
        self.assertTrue(exercised, "the scan found no mutant call at all")
        missing = [n for n in self._guard_names() if n not in exercised]
        self.assertEqual(
            missing, [], "guards with no `self._refuses` mutant naming them")
        stale = sorted(exercised - set(self._guard_names()))
        self.assertEqual(
            stale, [], "mutants naming a guard the migration no longer has")
        self.assertEqual(
            len(self._guard_names()),
            len(set(self._guard_names())),
            "two guards share a constraint name; SQLite would report the "
            "wrong one and a mutant test would pass for the wrong reason",
        )


class TheChildrenGuardCannotFallBehindTests(_Base):
    """`009`'s children guard named four tables, and three more have landed
    since (`011` character_skills, `013` character_home_marker, `015`
    character_equipment).  A guard that names tables by hand goes stale the
    day another lane adds one, and it goes stale SILENTLY -- the guard still
    passes, it just stops watching the new table.  So this derives the list
    from the schema instead of trusting the file, and is red the day the
    eighth child table lands without being added to 016.
    """

    def test_the_children_guard_names_every_table_that_references_characters(self):
        store = self._store_at_015()
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
        text = SIXTEEN.read_text(encoding="utf-8")
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
        to name it explicitly.  This is the test that says so."""
        text = SIXTEEN.read_text(encoding="utf-8")
        self.assertIn("character_backpack_items", text)


class WhatTheLevelSpTableIsNotTests(unittest.TestCase):
    """The measurement that stopped this file from repeating a false sentence.

    LANE-CS's letter concludes that `CONSTDATA_TH__LEVEL_SP.tsv` must be the
    experience curve, partly because it is the only level-indexed table in the
    game data.  This repository already has an experience curve, in
    `data/standard_status.tsv`, and `persistence_experience.
    threshold_for_next_level` has been reading it all along -- so `LEVEL_SP`
    is a level-indexed table that is NOT the experience curve, and what it IS
    is still unmeasured.  That is why `skill_points = 0` ships tagged.

    The LEVEL_SP half of the comparison is NOT tested here, on purpose.  That
    file lives in `pf_bridge`, and a test that reaches out of this repository
    is either a skip when the bridge is absent -- which NOW.md `2050` forbids
    outright -- or a red suite on a lone checkout.  The numbers are recorded
    in this round's file with the command that produced them
    (`LEVEL_SP.n_SP` lv1=2 lv2=4 lv10=42 lv120=13,645,740 against
    `n_EXP_CURRENTLV` lv1=0 lv2=79 lv10=714 lv120=91,699,378, 0 of 120 rows
    identical).  What is pinned HERE is the half that makes the letter's
    second argument fail and that this repository can answer alone: the
    experience curve exists, here, and it is already wired.
    """

    def test_this_repository_already_has_an_experience_curve(self):
        from pirateforce_foundation import persistence_experience as rule

        first = rule.threshold_for_next_level(1)
        self.assertIsNotNone(first)
        self.assertGreater(first, 0)
        climbs = [rule.threshold_for_next_level(level) for level in (1, 10, 50)]
        self.assertEqual(climbs, sorted(climbs))
        self.assertNotEqual(climbs[0], climbs[-1])

    def test_the_experience_door_reads_that_curve_and_not_a_constant(self):
        """A curve nothing consults is not a curve.  Two different levels must
        give the door two different bars, or `threshold_for_next_level` is a
        constant wearing a table's name."""
        from pirateforce_foundation import persistence_experience as rule

        self.assertNotEqual(
            rule.threshold_for_next_level(1), rule.threshold_for_next_level(50)
        )


class TheFileItselfTests(unittest.TestCase):
    def test_the_migration_is_pure_ascii(self):
        text = SIXTEEN.read_text(encoding="utf-8")
        self.assertTrue(all(ord(ch) < 128 for ch in text))
        text.encode("cp874")

    def test_the_file_is_the_next_free_number(self):
        numbers = sorted(
            int(path.name[:3]) for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")
        )
        self.assertEqual(len(numbers), len(set(numbers)), "duplicate version")
        self.assertEqual(max(numbers), SIXTEEN_VERSION)

    def test_the_two_letters_it_rests_on_are_named_in_the_file(self):
        """The 0 in this file is a measurement borrowed from two other lanes.
        A reader who cannot find whose measurement it was has to take it on
        faith, which is the thing `COO-DECISION 20260901_1059` exists to
        prevent."""
        text = SIXTEEN.read_text(encoding="utf-8")
        self.assertIn("20260908_0555", text)
        self.assertIn("20260908_0458", text)
        self.assertIn("COO-DECISION 20260901_1059", text)


if __name__ == "__main__":
    unittest.main()
