"""LANE-DB / M4: `migrations/008_character_speed_walk_seed.sql` puts the
client's own construction default into `characters.speed_walk`, and does
nothing else to anything.

WHAT THIS FILE IS THE EVIDENCE FOR.  `COO-DECISION 20260901_1447` point 2
forbade seeding this one column: 150.0 and 400.0 were two candidates and
"both numbers are equally a guess without" an RE.  `RE-194` decoded the
client's constructor chain and closed it -- `BasicAttr::ctor` stores 400.0f
into `+0x54` at VA `0x00464AF2`, unconditionally, for players and NPCs
alike -- and `COO-DECISION 20260902_0742` lifted the ban and approved this
file, in the shape of 007: `WHERE speed_walk IS NULL`, a required header
label, an automatic pre-apply snapshot, and a paired test file.  This is that
file.

WHAT IT PROVES, in the order the proofs matter:

1. **The migration cannot have destroyed anything.**  It is parsed statement
   by statement -- exactly one `UPDATE`, no INSERT, DELETE, DROP, CREATE or
   ALTER -- and then run for real against a database holding characters in
   four different states, whose every other column is compared afterwards.
2. **It is narrow.**  A row already holding a speed keeps it, whatever wrote
   it and whatever it is; a row holding NULL gets exactly the client's
   number; no other typed column is touched; and a value written after it
   runs is never re-seeded.
3. **The number is not a second constant.**  It is re-derived here from
   `persistence_attr_compose._CLIENT_DEFAULT_ROWS`' x=7 row -- value AND the
   VA the migration's header cites -- and cross-checked against
   `player_wire.PLAYER_LOGIN_MOVEMENT_SPEED`, so the migration and the two
   places this repository already records that fact cannot drift apart.
4. **It is reversible.**  The real `migrate_with_backup` runs over the real
   `migrations/` directory and the pre-008 database is restored out of the
   snapshot it leaves.

WHAT THIS FILE DOES NOT PROVE, so nobody reads more into it.  Nothing here is
client-observable: no frame is composed and nothing is sent.  That is not an
accident of scope, it is the decision -- `COO-DECISION 20260902_0742` point 4
says no code may read `speed_walk` off a row and put it on the wire on the
strength of this migration, and `NothingSendsTheSeededSpeedTests` below is the
control that says so out loud rather than leaving it to be assumed.  And 008
seeds a COHORT, not a database: the characters that exist when it runs, and no
others, ever.
"""
import contextlib
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import player_wire  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
import pf_lane_db_birth  # noqa: E402  (the birth-state door)

MIGRATIONS = ROOT / "migrations"
MIGRATION_008 = MIGRATIONS / "008_character_speed_walk_seed.sql"

#: The label `COO-DECISION 20260902_0742` point 2 requires in the header, in
#: the ASCII spelling the file uses (the decision wrote em dashes; every line
#: this repository ships is read under a cp874 console).
REQUIRED_HEADER_TAG = (
    "MEASURED from client BasicAttr constructor (RE-194) -- VA 0x00464AF2 "
    "-- STORE ONLY, not a send value"
)

#: The one column 008 may write.
SEEDED_COLUMN = "speed_walk"


def _build_wire(selector):
    return b"wire", b"avatar", 0x20000001 + selector, 0


@contextlib.contextmanager
def raw_rows(path):
    """A raw sqlite connection that is committed AND CLOSED.

    Same helper and same reason as `raw_rows` in
    `tests/test_persistence_vitals_seed_007.py`: `with sqlite3.connect(...)`
    commits on exit and does NOT close, which costs nothing on Linux and
    fails the whole suite on Windows out of `TemporaryDirectory` cleanup.
    """
    db = sqlite3.connect(path)
    try:
        yield db
        db.commit()
    finally:
        db.close()


def _statements(sql: str) -> list[str]:
    body = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )
    return [" ".join(s.split()) for s in body.split(";") if s.strip()]


def _client_default_speed():
    """400.0, re-derived from the table this repository already keeps.

    NOT a literal of this file's own.  `_CLIENT_DEFAULT_ROWS` is where
    `persistence_attr_compose` records the client construction defaults, each
    with the VA that writes it; the migration header cites the same VA.  If
    either side is ever edited alone, the tests below stop agreeing.
    """
    rows = [row for row in compose._CLIENT_DEFAULT_ROWS if row[0] == 7]
    assert len(rows) == 1, rows
    return rows[0][1], rows[0][2]


class HeaderTagTests(unittest.TestCase):
    """Point 2 of COO-DECISION 20260902_0742."""

    def setUp(self):
        self.sql = MIGRATION_008.read_text(encoding="utf-8")

    def test_the_header_carries_the_decision_s_label(self):
        self.assertIn(REQUIRED_HEADER_TAG, self.sql)

    def test_the_label_is_in_the_header_not_buried_after_a_statement(self):
        """A label a reader has to scroll past the SQL to find is not a
        header.  Measured position: before the first statement."""
        offset, first_statement = 0, None
        for line in self.sql.splitlines(keepends=True):
            if line.upper().startswith("UPDATE"):
                first_statement = offset
                break
            offset += len(line)
        self.assertIsNotNone(first_statement, "the migration has no statement")
        self.assertLess(self.sql.index(REQUIRED_HEADER_TAG), first_statement)

    def test_the_label_keeps_the_half_that_limits_it(self):
        """The decision's point 2 says the second clause "must be there".

        `STORE ONLY, not a send value` is the half that stops this file from
        being read as permission to send a speed -- which is point 4, and
        which RE-194's own nonclaims are the reason for.  Pinned separately
        from the whole-label test above so that shortening the label to its
        flattering half is a named failure.
        """
        self.assertIn("STORE ONLY, not a send value", self.sql)

    def test_the_header_names_the_re_that_lifted_the_ban(self):
        self.assertIn("RE-194", self.sql)
        self.assertIn("20260902_0742", self.sql)

    def test_the_file_is_ascii(self):
        """Every line this repository ships is read under a cp874 console at
        least once (`gate-windows.yml`), and a migration is read by the BOOT
        that applies it -- a traceback out of `executescript` quotes it.  007
        has this test; 008 did not until a `pf-adversary` pass named the gap,
        and the decision's own words are "the same shape as 007, exactly"."""
        MIGRATION_008.read_bytes().decode("ascii")

    def test_the_two_new_test_files_of_this_round_are_ascii_too(self):
        """The migration is not the only new file a cp874 console meets."""
        for name in ("test_persistence_speed_seed_008.py", "pf_lane_db_birth.py"):
            with self.subTest(name=name):
                (ROOT / "tests" / name).read_bytes().decode("ascii")

    def test_the_header_states_the_cohort_limitation(self):
        """The limitation a reader must not have to run a test to discover."""
        self.assertIn("COHORT, NOT A", self.sql)
        self.assertIn("create_character", self.sql)


class MigrationShapeTests(unittest.TestCase):
    """What the file is allowed to contain, read out of the file."""

    def setUp(self):
        self.statements = _statements(MIGRATION_008.read_text(encoding="utf-8"))

    def test_there_is_exactly_one_statement_and_it_is_an_update(self):
        self.assertEqual(len(self.statements), 1, self.statements)
        self.assertTrue(self.statements[0].upper().startswith("UPDATE "))

    def test_nothing_inserts_deletes_drops_creates_or_alters(self):
        """The verbs this file must never contain.

        Matched on WORD BOUNDARIES and against 007's FULL list, both because
        a `pf-adversary` pass measured that the shorter, substring version
        re-introduced a defect its sibling file documents having fixed: a
        future author adding the safest possible narrowing, `AND deleted_at
        IS NULL`, would turn this red on `DELETE` and be told they were
        destroying something.  The extra verbs matter too -- `SQLiteStore.
        migrate` wraps every migration in `BEGIN IMMEDIATE; ... COMMIT;`, so a
        stray `COMMIT` here would end that transaction early.
        """
        for verb in ("DELETE", "DROP", "INSERT", "REPLACE", "ALTER",
                     "CREATE", "PRAGMA", "ATTACH", "VACUUM", "BEGIN",
                     "COMMIT", "ROLLBACK"):
            for statement in self.statements:
                self.assertIsNone(
                    re.search(r"\b%s\b" % verb, statement.upper()),
                    "%s in %s" % (verb, statement),
                )

    def test_the_verb_scan_does_not_fire_on_a_column_name(self):
        """The control for the boundary rule above."""
        harmless = "UPDATE CHARACTERS SET SPEED_WALK = 400.0 WHERE DELETED_AT IS NULL"
        self.assertIn("DELETE", harmless)
        self.assertIsNone(re.search(r"\bDELETE\b", harmless))

    def test_the_only_column_written_is_speed_walk(self):
        statement = self.statements[0]
        assignments = re.findall(r"SET\s+(.*?)\s+WHERE", statement, re.I)
        self.assertEqual(len(assignments), 1, statement)
        written = {a.split("=")[0].strip() for a in assignments[0].split(",")}
        self.assertEqual(written, {SEEDED_COLUMN})

    def test_the_predicate_is_the_one_the_decision_ordered(self):
        """Point 1: `WHERE speed_walk IS NULL`, so a stored value is safe."""
        self.assertRegex(
            self.statements[0], r"(?i)WHERE\s+speed_walk\s+IS\s+NULL\s*$")

    def test_updated_at_is_not_touched(self):
        self.assertNotIn("updated_at", self.statements[0])

    def test_the_seeded_value_is_the_client_construction_default(self):
        """The number in the file, re-derived rather than repeated.

        This is what stops 008 from becoming a third home for 400.0 that can
        drift away from the two that already exist.
        """
        value, address = _client_default_speed()
        self.assertEqual(value, 400.0)
        self.assertIn(address, MIGRATION_008.read_text(encoding="utf-8"))
        written = re.search(
            r"(?i)SET\s+speed_walk\s*=\s*([0-9.]+)", self.statements[0])
        self.assertIsNotNone(written, self.statements[0])
        self.assertEqual(float(written.group(1)), value)

    def test_the_value_also_matches_what_player_wire_records(self):
        """A second, independent in-repository record of the same fact."""
        value, _ = _client_default_speed()
        self.assertEqual(player_wire.PLAYER_LOGIN_MOVEMENT_SPEED, value)

    def test_the_column_accepts_the_value_its_own_check_constrains(self):
        """008 writes through SQL, so what guards it is 006's CHECK, not
        `persistence_typed_attrs.validate`.  Both are asked anyway."""
        value, _ = _client_default_speed()
        self.assertEqual(typed.validate(SEEDED_COLUMN, value), value)


class _MigratedWorkspace(unittest.TestCase):
    """Run 001..007, put real rows in, THEN run the full directory."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.older = self.root / "migrations_upto_007"
        self.older.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) < 8:
                shutil.copy2(path, self.older / path.name)
        self.path = self.root / "state.sqlite3"

    def _rows(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute("SELECT * FROM characters ORDER BY id").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            db.close()

    def _make(self, names):
        """Create characters on the pre-008 schema; return their ids."""
        store = SQLiteStore(self.path, self.older)
        store.migrate()
        account_id = store.ensure_account("speed-seed-008")
        home = Position(3, 0, 11.0, 22.0, 33.0, heading=1.5)
        ids = []
        for name in names:
            character = store.create_character(
                account_id, name, name.lower(),
                "fingerprint-008-%s" % name.lower(), _build_wire, home,
            )
            # 007 has already run in this workspace, so these rows have vitals
            # legitimately.  What has to stay out of the measurement is a
            # BIRTH-written set (`COO-DECISION 20260902_0444`), which arrives
            # with no migration behind it -- and `clear_birth_vitals` refuses
            # any birth but the two this lane accepts before clearing.
            pf_lane_db_birth.clear_birth_vitals(store, character.id)
            ids.append(character.id)
        return ids

    def _apply_008(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()

    def _applied_versions(self):
        db = sqlite3.connect(self.path)
        try:
            return {int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations")}
        finally:
            db.close()

    def _set(self, character_id, **columns):
        with raw_rows(self.path) as db:
            for column, value in columns.items():
                db.execute(
                    "UPDATE characters SET %s=? WHERE id=?" % column,
                    (value, character_id),
                )


class MigrationIsNarrowTests(_MigratedWorkspace):
    """Point 1 of COO-DECISION 20260902_0742, measured on real rows."""

    def test_a_row_holding_nothing_gets_the_client_default(self):
        ids = self._make(["SpeedOne"])
        before = self._rows()[0]
        self.assertIsNone(before[SEEDED_COLUMN])
        self._apply_008()
        after = self._rows()[0]
        value, _ = _client_default_speed()
        self.assertEqual(after[SEEDED_COLUMN], value)
        self.assertIn(8, self._applied_versions())
        for column in before:
            if column != SEEDED_COLUMN:
                self.assertEqual(after[column], before[column], column)
        self.assertEqual(len(ids), 1)

    def test_a_row_that_already_holds_a_speed_keeps_it(self):
        """Including a speed nothing in this repository would have chosen.

        150.0 is used on purpose: it is the number RE-194 placed one
        lifecycle layer later, and if 008 ever "corrected" a stored 150.0 to
        400.0 it would be overwriting a value somebody else adjudicated.
        """
        ids = self._make(["Veteran", "Slow"])
        self._set(ids[0], speed_walk=150.0)
        self._set(ids[1], speed_walk=0.5)
        self._apply_008()
        rows = self._rows()
        self.assertEqual(rows[0][SEEDED_COLUMN], 150.0)
        self.assertEqual(rows[1][SEEDED_COLUMN], 0.5)

    def test_every_other_typed_column_is_left_exactly_as_it_was(self):
        ids = self._make(["Mixed"])
        self._set(ids[0], level=9, hp_current=40, hp_max=80, cash=1234)
        before = self._rows()[0]
        self._apply_008()
        after = self._rows()[0]
        for column in typed.TYPED_COLUMNS:
            if column != SEEDED_COLUMN:
                self.assertEqual(after[column], before[column], column)

    def test_soft_deleted_rows_are_seeded_like_live_ones(self):
        """004 keeps a deleted character's row forever; leaving a hole in it
        would make an undelete produce a character with no speed.

        The delete goes through `SQLiteStore.soft_delete_character` and not
        through a raw `UPDATE ... SET deleted_at`, so what 008 meets is the
        state the server really leaves behind -- guards, `updated_at` stamp
        and all -- rather than a state this test invented.  A LIVE character
        stands beside it so the assertion is that BOTH are seeded, which a
        migration carrying a stray `WHERE deleted_at IS NULL` would fail.
        """
        store = SQLiteStore(self.path, self.older)
        ids = self._make(["Gone", "Here"])
        rows = {row["id"]: row for row in self._rows()}
        sid = store.open_session(store.ensure_account("speed-seed-008"))
        store.soft_delete_character(sid, rows[ids[0]]["selector"])

        after_delete = {row["id"]: row for row in self._rows()}
        self.assertIsNotNone(after_delete[ids[0]]["deleted_at"])
        self.assertIsNone(after_delete[ids[1]]["deleted_at"])

        self._apply_008()
        value, _ = _client_default_speed()
        seeded = {row["id"]: row for row in self._rows()}
        self.assertEqual(seeded[ids[0]][SEEDED_COLUMN], value)
        self.assertEqual(seeded[ids[1]][SEEDED_COLUMN], value)

    def test_a_value_written_after_the_migration_is_not_re_seeded(self):
        ids = self._make(["Later"])
        self._apply_008()
        self._set(ids[0], speed_walk=222.5)
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(self._rows()[0][SEEDED_COLUMN], 222.5)

    def test_008_is_recorded_in_the_ledger_and_re_running_is_a_no_op(self):
        self._make(["Ledger"])
        self._apply_008()
        first = self._rows()[0]
        self.assertIn(8, self._applied_versions())
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(self._rows()[0], first)

    def test_an_empty_table_survives_the_migration(self):
        """A fresh install: 008 runs against no rows at all and succeeds,
        which is also the state in which it seeds nothing."""
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertIn(8, self._applied_versions())
        self.assertEqual(self._rows(), [])

    def test_the_statement_is_idempotent_on_its_own_rows(self):
        """The ledger is what stops a second apply; the statement would be
        harmless anyway, and that is the property a reader assumes."""
        self._make(["Twice"])
        self._apply_008()
        first = self._rows()[0]
        with raw_rows(self.path) as db:
            db.executescript(
                _statements(MIGRATION_008.read_text(encoding="utf-8"))[0] + ";")
        self.assertEqual(self._rows()[0], first)


class OneBootFrom006To008Tests(unittest.TestCase):
    """007 and 008 applied to the SAME populated database in ONE boot.

    *** WHY THIS CLASS EXISTS.  The owner's canonical database is at 006.  The
    next server boot it sees will apply 007 AND 008 in a single `migrate()`,
    against rows that already exist -- and until a `pf-adversary` pass said so,
    nothing in this repository executed that path.  `_MigratedWorkspace` here
    builds through 007 first, so 007 and 008 are always two boots; and the
    edit this round made to `test_persistence_vitals_seed_007._apply_007`
    (stopping it at a through-007 prefix, which it needed for its own reason)
    removed the only place the combined run happened by accident.

    A limitation removed by accident is still removed, so it is put back on
    purpose, here, where the class name says what it covers.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.at_006 = self.root / "migrations_upto_006"
        self.at_006.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) <= 6:
                shutil.copy2(path, self.at_006 / path.name)
        self.path = self.root / "state.sqlite3"

    def test_a_populated_006_database_reaches_008_in_one_migrate(self):
        store = SQLiteStore(self.path, self.at_006)
        store.migrate()
        account_id = store.ensure_account("one-boot")
        home = Position(3, 0, 11.0, 22.0, 33.0, heading=1.5)
        ids = []
        for name in ("Alpha", "Beta"):
            character = store.create_character(
                account_id, name, name.lower(), "fingerprint-one-boot-%s" % name,
                _build_wire, home)
            pf_lane_db_birth.clear_birth_vitals(store, character.id)
            ids.append(character.id)
        # One row is a veteran already: the combined run must complete the
        # empty row and leave the held values alone, in the same boot.
        with raw_rows(self.path) as db:
            db.execute(
                "UPDATE characters SET level=?,hp_current=?,hp_max=?,speed_walk=? "
                "WHERE id=?", (9, 480, 500, 150.0, ids[1]))

        upgraded = SQLiteStore(self.path, MIGRATIONS)
        snapshot = upgraded.migrate_with_backup(backups_root=self.root / "backups")
        self.assertIsNotNone(snapshot)

        value, _ = _client_default_speed()
        rows = {}
        with raw_rows(self.path) as db:
            db.row_factory = sqlite3.Row
            for row in db.execute(
                    "SELECT id,level,hp_current,hp_max,speed_walk FROM characters"):
                rows[row["id"]] = {k: row[k] for k in row.keys()}
            versions = {int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations")}
        self.assertEqual(versions, set(range(1, 9)))
        self.assertEqual(
            rows[ids[0]],
            {"id": ids[0], "level": 1, "hp_current": 100, "hp_max": 100,
             "speed_walk": value},
        )
        self.assertEqual(
            rows[ids[1]],
            {"id": ids[1], "level": 9, "hp_current": 480, "hp_max": 500,
             "speed_walk": 150.0},
        )

    def test_the_snapshot_of_that_one_boot_restores_the_006_database(self):
        """One snapshot covers BOTH migrations, because a boot takes one."""
        store = SQLiteStore(self.path, self.at_006)
        store.migrate()
        account_id = store.ensure_account("one-boot")
        character = store.create_character(
            account_id, "Solo", "solo", "fingerprint-one-boot-solo",
            _build_wire, Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        pf_lane_db_birth.clear_birth_vitals(store, character.id)

        snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
            backups_root=self.root / "backups")
        restored = self.root / "restored.sqlite3"
        shutil.copy2(Path(snapshot), restored)
        db = sqlite3.connect(restored)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute("SELECT * FROM characters WHERE id=?",
                             (character.id,)).fetchone()
            versions = {int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations")}
        finally:
            db.close()
        self.assertEqual(versions, set(range(1, 7)))
        for column in ("level", "hp_current", "hp_max", SEEDED_COLUMN):
            self.assertIsNone(row[column], column)


class SeedsACohortNotADatabaseTests(_MigratedWorkspace):
    """The limitation 008 inherits from 007, measured rather than asserted."""

    def test_a_character_created_after_008_has_no_speed(self):
        self._make(["Before"])
        self._apply_008()
        store = SQLiteStore(self.path, MIGRATIONS)
        newborn = store.create_character(
            store.ensure_account("speed-seed-008"), "After", "after",
            "fingerprint-008-after", _build_wire,
            Position(3, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        value, _ = _client_default_speed()
        rows = {row["id"]: row for row in self._rows()}
        self.assertEqual(rows[newborn.id][SEEDED_COLUMN], None)
        self.assertNotEqual(rows[newborn.id][SEEDED_COLUMN], value)

    def test_the_birth_plug_is_not_allowed_to_seed_this_column(self):
        """`COO-DECISION 20260902_0443` answered the birth question for the
        three VITAL columns and deliberately not for this one.

        `pf_lane_db_birth.observed_birth_vitals` refuses any birth state but
        the two this lane accepts, and the birth-value function in
        `persistence_vitals` is graded elsewhere for having exactly three
        keys.  Its name is deliberately not spelled here: a scan in
        `tests/test_persistence_vitals.py` counts every file that mentions it
        so that a SECOND source of birth values cannot appear unnoticed, and
        a mention in prose would cost that scan a false positive
        (`COO-DECISION 20260902_0445` point 5: write around a guard, do not
        widen it).  What is pinned HERE is the
        consequence for 008: whatever a birth writes, it is not a speed.
        """
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        newborn = store.create_character(
            store.ensure_account("speed-seed-008"), "Newborn", "newborn",
            "fingerprint-008-newborn", _build_wire,
            Position(3, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        pf_lane_db_birth.observed_birth_vitals(store, newborn.id)
        with raw_rows(self.path) as db:
            speed = db.execute(
                "SELECT speed_walk FROM characters WHERE id=?",
                (newborn.id,)).fetchone()[0]
        self.assertIsNone(speed)


class TheOneBehaviourChangeThisMigrationMakesTests(_MigratedWorkspace):
    """008 is a store, not a send -- but it is not invisible to the server.

    Disclosed as a class of its own rather than as a line in a header, because
    a `pf-adversary` pass found this and the first draft of the header did not
    mention it.
    """

    def test_a_pre_existing_character_starts_reporting_a_speed_to_its_readers(self):
        """The behaviour change 008 really does make, measured at this lane's
        own layer instead of asserted in the header.

        `read_typed_attributes` is the input every reader of this column takes,
        `/speed`'s undo included.  Before 008 it OMITS `speed_walk` for an
        existing character (the column is NULL, and this API never renders a
        NULL as a value -- that is the owner's rule); after 008 it returns
        400.0.  `_speed_undo`'s own docstring names the NULL case as the one
        it cannot revert, so this is where its behaviour changes, and the
        migration header says so out loud.

        What is NOT claimed here: anything about the console word a GM sees.
        That is `/speed`'s layer and `COO-DECISION 20260902_0345`'s decision;
        this test measures only the input that layer reads.
        """
        ids = self._make(["Reader"])
        store = SQLiteStore(self.path, MIGRATIONS)
        self.assertNotIn(SEEDED_COLUMN, store.read_typed_attributes(ids[0]))
        self._apply_008()
        value, _ = _client_default_speed()
        self.assertEqual(
            store.read_typed_attributes(ids[0])[SEEDED_COLUMN], value)


class NothingSendsTheSeededSpeedTests(unittest.TestCase):
    """Point 4 of COO-DECISION 20260902_0742, as a control rather than a
    promise in a comment.

    The decision is explicit: no code may read `speed_walk` off a row and put
    it on the wire on the strength of this migration.  Whether the server
    sends a speed at all belongs to GM-B / `/speed` and to `COO-DECISION
    20260902_0345`.  So what this class watches is the MIGRATION's reach --
    that 008 landing does not, by itself, change what any client receives.
    """

    def test_the_login_frame_still_carries_its_own_literal(self):
        """`player_wire` sends a speed from a module constant today.  008 does
        not redirect it at a row, and this is what says so.

        If a later round wires the login frame to the column -- which is a
        real thing to want -- this test is where that shows up, and the letter
        that authorises it is what should edit this test.
        """
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "player_wire.py").read_text(encoding="utf-8")
        self.assertIn("PLAYER_LOGIN_MOVEMENT_SPEED = 400.0", source)

    def test_the_repository_s_only_reader_of_this_column_is_the_one_already_adjudicated(self):
        """Point 4 says "no code", so the scan is the whole tree, not one file.

        A `pf-adversary` pass measured the hole in the first version: it read
        `player_wire.py` alone, so a new `gm/speed_send.py` doing
        `read_typed_attributes(cid)["speed_walk"] -> encode_field -> frame`
        would have left it green while doing precisely what point 4 forbids.

        What this asserts is a CENSUS, not an absence: `speed_walk` already
        has one reader outside this lane -- `/speed`'s undo path in
        `gm/chat_command_action.py`, which belongs to `COO-DECISION
        20260902_0345` and predates 008 -- and pretending otherwise would be a
        lie the next author trips over.  So the known readers are named, and
        the day a file that is NOT on this list starts reading the column,
        this goes red with its name.

        The scan is narrowed to files that touch a CHARACTER ROW, because nine
        `field_mob_*` / `mob_*` modules carry the same two words as a MOBS
        gamedata template field (`n_SPEED_WALK`, the row RE-194 traced to the
        NPC's later wire write).  Those are a different table and a different
        object; flagging them would make this test noise that the next author
        silences, which is worse than not having it.
        """
        # Reading `speed_walk` is only point 4's business when it is being
        # read OFF A CHARACTER ROW, so a file qualifies only if it also names
        # one of the doors into that row.
        row_access = ("read_typed_attributes", "write_typed_attributes",
                      "TYPED_COLUMNS", "FROM characters", "UPDATE characters")
        known = {
            "src/pirateforce_foundation/persistence_typed_attrs.py",
            "src/pirateforce_foundation/persistence_vitals.py",
            # `/speed`, whose read of this column is GM-B's decision and not
            # this migration's: `COO-DECISION 20260902_0345`.
            "src/pirateforce_foundation/gm/chat_command_action.py",
        }
        found = []
        for path in sorted((ROOT / "src").rglob("*.py")):
            relative = str(path.relative_to(ROOT)).replace("\\", "/")
            if relative in known:
                continue
            source = path.read_text(encoding="utf-8", errors="replace")
            if not re.search(r"\bspeed_walk\b", source):
                continue
            if any(door in source for door in row_access):
                found.append(relative)
        self.assertEqual(
            [], found,
            "%r reads or writes `speed_walk`.  COO-DECISION 20260902_0742 "
            "point 4: no code may take this column off a row onto the wire on "
            "the strength of migration 008.  If a decision authorised it, that "
            "decision is what should add the file to `known` above." % (found,),
        )


class BootSnapshotProtects008Tests(_MigratedWorkspace):
    """The owner's rule for a row-touching migration (COO-DECISION
    20260901_1112 point 3), measured against THIS file."""

    def test_a_snapshot_is_due_while_008_is_the_pending_file(self):
        from pirateforce_foundation import persistence_backup

        self._make(["Snapshot"])
        take, reason = persistence_backup.should_snapshot(self.path, MIGRATIONS)
        self.assertTrue(take, reason)
        self.assertIn("008", reason)

    def test_a_snapshot_that_dies_in_its_prologue_still_aborts_the_boot(self):
        """The half of "reversible" that says the migration does NOT run
        behind a failed snapshot.

        007 has this test and 008 did not until a `pf-adversary` pass named
        the gap.  It is the more important half: a snapshot that exists is
        only useful afterwards, while a migration that runs WITHOUT one is
        the owner's forbidden state ("cannot be undone, no backup") arriving
        by accident.  `app.py` catches `BackupError` and nothing else, so a
        raw `OSError` here would become a traceback and exit 1 instead of
        exit 13 and "your database has NOT been changed".
        """
        from pirateforce_foundation import persistence_backup
        from unittest import mock

        self._make(["Prologue"])
        with mock.patch.object(
                persistence_backup, "_sha256_file",
                side_effect=OSError("disk went away mid-snapshot")):
            with self.assertRaises(persistence_backup.BackupError) as caught:
                SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
                    backups_root=self.root / "backups")
        self.assertIn("disk went away mid-snapshot", str(caught.exception))
        self.assertIsNone(self._rows()[0][SEEDED_COLUMN])
        self.assertNotIn(8, self._applied_versions())

    def test_the_snapshot_taken_at_boot_restores_the_pre_008_database(self):
        ids = self._make(["Restore"])
        backups = self.root / "backups"
        snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
            backups_root=backups)
        self.assertIsNotNone(snapshot)
        value, _ = _client_default_speed()
        self.assertEqual(self._rows()[0][SEEDED_COLUMN], value)

        copy = Path(snapshot)
        self.assertEqual(copy.name, self.path.name)
        restored = self.root / "restored.sqlite3"
        shutil.copy2(copy, restored)
        db = sqlite3.connect(restored)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                "SELECT * FROM characters WHERE id=?", (ids[0],)).fetchone()
            versions = {int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations")}
        finally:
            db.close()
        self.assertNotIn(8, versions)
        self.assertIsNone(row[SEEDED_COLUMN])


class TheGateMovesByExactlyOneFieldTests(_MigratedWorkspace):
    """What 008 buys the attribute block, and what it does not.

    Seeding one column closes exactly one gap, and the count is ASSERTED
    below rather than written here.  The first version of this docstring said
    "twenty-one fields still gap"; a `pf-adversary` pass measured 54 and was
    right -- 21 is the number of typed COLUMNS other than `speed_walk`, a
    different denominator entirely, and nothing in the class checked either
    number.  A free-floating count in a docstring is exactly the sentence a
    round file quotes, which is why the class that exists to stop a number
    being rounded is the worst place to keep one.
    """

    def test_the_seeded_row_closes_the_speed_gap_and_no_other(self):
        ids = self._make(["Gate"])
        store = SQLiteStore(self.path, MIGRATIONS)
        before = {typed.TYPED_COLUMNS[c].x: v
                  for c, v in store.read_typed_attributes(ids[0]).items()}
        before_gaps = {g.x for g in compose.block_gaps(before)}
        self.assertIn(7, before_gaps)

        self._apply_008()
        after = {typed.TYPED_COLUMNS[c].x: v
                 for c, v in store.read_typed_attributes(ids[0]).items()}
        after_gaps = {g.x for g in compose.block_gaps(after)}
        self.assertNotIn(7, after_gaps)
        self.assertEqual(before_gaps - after_gaps, {7})
        value, _ = _client_default_speed()
        self.assertEqual(after[7], value)
        # The count, measured instead of narrated.  One field closed, and the
        # arithmetic between the two states is the whole claim.
        self.assertEqual(len(after_gaps), len(before_gaps) - 1)
        self.assertEqual(len(after_gaps), 54)

    def test_a_full_block_still_cannot_be_composed(self):
        ids = self._make(["StillClosed"])
        self._apply_008()
        store = SQLiteStore(self.path, MIGRATIONS)
        values = {typed.TYPED_COLUMNS[c].x: v
                  for c, v in store.read_typed_attributes(ids[0]).items()}
        with self.assertRaises(compose.AttrComposeError):
            compose.compose_full_block(values)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
