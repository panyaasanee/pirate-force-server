"""LANE-DB: `migrations/009_character_birth_defaults.sql`, and the pin it
retires.

WHAT `009` IS.  `SQLiteStore.create_character` names its INSERT columns
explicitly and the typed columns are not among them; `006` added them with no
DEFAULT; `007` and `008` seed the rows that EXIST when they run and the
checksum ledger stops them ever running again.  So on a FRESH INSTALL every
character born afterwards held NULL in all four, forever -- a character with
no HP cannot be damaged, cannot be healed, and composes with a named gap
instead of a number.  `009` gives those four columns a DEFAULT, which closes
the hole for every character born from now on without touching one existing
row.

WHOSE DECISION, AND WHICH TWO IT REPLACES.  `COO-DECISION 20260902_0443`
point 2 forbade the DEFAULT and `COO-DECISION 20260902_1546` refused the table
rebuild it needs.  The project owner overruled both in person on 2026-09-02
(relayed as `COO-DECISION 20260902_1607`), fixed the four numbers -- `level=1`,
`hp_current=100`, `hp_max=100`, `speed_walk=400.0` -- and forbade changing
them.  The same letter keeps the other seventeen columns NULL: guessing an
unknown field as zero is the owner's own ban (`COO-DECISION 20260901_1059`).

WHAT THIS FILE IS.  It is the file `COO-DECISION 20260902_1607` asks for in
one sentence -- "the order to write a pin stands, but its job changes: from a
pin that points at the hole to a test that proves `009` really closed it" --
and it is the retirement of `tests/test_persistence_birth_hole_pin.py`, whose
own header predicted this exact collision and named the fix ("retire this
file and let `pf_birth_state` be amended, not argue with it here").  The
population that file built is kept, because it was not built for decoration:
a `pf-adversary` pass drove SEVEN wrong plugs through a one-character version
of it, including an `UPDATE` with no `WHERE` clause at all, and found THREE
more that left it fully green.  Every one of those shapes is still separated
here:

  * a VETERAN whose vitals are written before anything else is created -- the
    row a migration that touched existing rows would stomp;
  * a SECOND character on the same account at selector 1;
  * a RETRY create with the second character's own fingerprint -- the
    retransmitted-create-packet branch;
  * a THIRD character at selector 0 of a SECOND account;
  * a LOGIN after all of it.

WHAT IT ADDS THAT THE PIN COULD NOT, all three named by
`COO-DECISION 20260902_1607` as conditions the round may not push without:

  1. that a backup FILE really appears before `009` is applied -- not that a
     function was called (`TheOwnerKeepsACopyBefore009Tests`);
  2. that the boot path the owner's machine really uses is one that migrates
     (measured in the round file, not here: it is a fact about the bridge's
     boot scripts, not about this repository's python);
  3. that every index, constraint and uniqueness rule comes back, compared
     BEFORE against AFTER automatically rather than by eye
     (`TheSchemaComesBackWholeTests`), plus the same rules exercised
     behaviourally, because a matching `sqlite_master` row is a claim about
     text and a refused INSERT is a claim about the database.

AND ONE THING NOBODY ASKED FOR, because a rebuild is the one migration shape
that can lose a whole table: `TheGuardsInsideTheMigrationFireTests` breaks the
migration on purpose, in a copy of the file in a temporary directory, and
measures that the guards inside it abort the upgrade and leave the database
untouched.  Guards nobody has ever seen fire are decoration.
"""
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402
from pirateforce_foundation import persistence_backup  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

import pf_birth_state as birth_state  # noqa: E402

MIGRATIONS = ROOT / "migrations"
VERSION = 9
MIGRATION_009 = next(MIGRATIONS.glob("009_*.sql"))

#: What a veteran holds before any of the newborns exist.  A migration that
#: reached an existing row would turn these into the birth values, which is
#: the damage the retry-branch scenario in
#: `tests/test_persistence_vitals_seed_007.py` measured for real.
VETERAN = {"level": 9, "hp_current": 480, "hp_max": 500}

#: The four columns `009` defaults, and the seventeen it must leave alone.
DEFAULTED = ("level", "hp_current", "hp_max", "speed_walk")


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


def _build_wire_second_account(selector):
    """A second account's selectors also start at zero, and
    `004_character_soft_delete_reuse.sql` puts a partial UNIQUE index on
    `(identity_lo, identity_hi)`."""
    return b"wire", b"avatar", 0x40000001 + selector, 0


def _migrations_through(version, destination):
    """A migrations directory holding `001..version` and nothing after it.

    Chosen by VERSION NUMBER rather than by name so this keeps meaning what it
    says the day `010` exists.
    """
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
        if int(path.name[:3]) <= version:
            shutil.copy2(path, destination / path.name)
    return destination


def _raw(path):
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    return db


def _table_sql(path, name):
    db = _raw(path)
    try:
        row = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (name,)).fetchone()
    finally:
        db.close()
    return None if row is None else row["sql"]


def _indexes(path, table):
    db = _raw(path)
    try:
        return {row["name"]: row["sql"] for row in db.execute(
            "SELECT name,sql FROM sqlite_master "
            "WHERE type='index' AND tbl_name=?", (table,))}
    finally:
        db.close()


def _columns(path, table):
    db = _raw(path)
    try:
        return {row["name"]: (row["cid"], row["type"], row["notnull"],
                              row["dflt_value"], row["pk"])
                for row in db.execute("PRAGMA table_info(%s)" % table)}
    finally:
        db.close()


def _applied(path):
    db = _raw(path)
    try:
        return sorted(int(row[0]) for row in
                      db.execute("SELECT version FROM schema_migrations"))
    finally:
        db.close()


class _FreshInstall(unittest.TestCase):
    """A server booting on a machine that has never held a character."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "fresh_install.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()

    def _create(self, account_id, name, tag, build, x):
        return self.store.create_character(
            account_id, name, name.casefold(), "fingerprint-%s" % tag,
            build, Position(3, 0, x, 2.0, 3.0, heading=0.0))


class TheBirthHoleIsClosedTests(_FreshInstall):
    """The pin, inverted: every shape it could not tell apart, now graded."""

    def test_009_is_really_in_this_database(self):
        """The guard against a vacuously green file.

        A fixture that stopped before `009` would report whatever it liked
        about newborns and keep passing.  Measured on the database the rest of
        this class uses, not on a second one.
        """
        self.assertIn(VERSION, _applied(self.path))
        columns = _columns(self.path, "characters")
        for column in DEFAULTED:
            with self.subTest(column=column):
                self.assertIn(column, columns)
                self.assertIsNotNone(
                    columns[column][3], "%s has no DEFAULT" % column)

    def test_every_character_born_on_a_fresh_install_holds_the_birth_state(self):
        """THE RETIRED PIN'S POPULATION, graded the other way round."""
        account_a = self.store.ensure_account("account-a")
        veteran = self._create(account_a, "Veteran", "veteran", _build_wire, 1.0)
        veteran_birth = birth_state.measure_birth_typed_state(
            self.store, veteran.id)
        self.store.write_typed_attributes(veteran.id, dict(VETERAN))

        second = self._create(account_a, "Rookie", "rookie", _build_wire, 4.0)
        again = self._create(account_a, "Rookie", "rookie", _build_wire, 4.0)
        self.assertEqual(
            again.id, second.id,
            "the retry branch made a second row instead of returning the "
            "existing one; this test's retry coverage is not measuring what "
            "it claims to")

        account_b = self.store.ensure_account("account-b")
        third = self._create(account_b, "Stranger", "stranger",
                             _build_wire_second_account, 7.0)

        # EVERY newborn, not only the first: a `pf-adversary` pass measured
        # that checking one row lets a shape through that is right for the
        # account's first character and wrong for every character after it.
        expected = birth_state.defaulted_birth()
        births = [veteran_birth] + birth_state.measure_every_birth(
            self.store, [second.id, third.id])
        for index, state in enumerate(births):
            with self.subTest(character=index):
                self.assertEqual(state, expected)

        # the veteran, who is the reason a rebuild needs guards at all
        self.assertEqual(
            self.store.read_typed_attributes(veteran.id),
            birth_state.with_birth(veteran_birth, **VETERAN),
            "creating characters changed an EXISTING character's vitals")

        # login is not a birth: selecting a character writes nothing
        session = self.store.open_session(account_b)
        self.store.select_character(session, third.selector)
        self.assertEqual(self.store.read_typed_attributes(third.id), expected,
                         "logging in changed a character's vitals")

    def test_a_newborn_can_be_damaged_and_healed_without_being_seeded_first(self):
        """The sentence the hole made false, said as behaviour.

        Before `009` a character born on a fresh install was refused by both
        doors -- `VitalsError`, unseeded -- and no call site could take its HP
        down or put it back.  This is what closing the hole BUYS, and it is
        measured through the store's own doors rather than by reading columns.
        """
        account = self.store.ensure_account("playable")
        character = self._create(account, "Playable", "playable",
                                 _build_wire, 1.0)
        birth = birth_state.measure_birth_typed_state(self.store, character.id)
        self.assertEqual(birth, birth_state.defaulted_birth())
        resolution = self.store.read_character_vitals(character.id)
        self.assertTrue(resolution.complete, [g.reason for g in resolution.gaps])
        state = resolution.require()
        self.assertEqual(state.hp_current, state.hp_max)

        hurt = self.store.apply_hp_damage(character.id, 30)
        self.assertEqual(hurt.hp_after, state.hp_max - 30)
        healed = self.store.restore_hp_to_full(character.id)
        self.assertEqual(healed.hp_after, state.hp_max)
        with _raw(self.path) as db:
            stored = db.execute(
                "SELECT hp_current FROM characters WHERE id=?",
                (character.id,)).fetchone()[0]
        self.assertEqual(stored, state.hp_max)

    def test_the_census_says_every_row_is_seeded_and_raw_sql_agrees(self):
        """The census, graded against raw SQL over the same file rather than
        against a number typed here -- a hardcoded expectation can only be
        right in one of the states this file has to tell apart."""
        account = self.store.ensure_account("census")
        ids = [self._create(account, "C%d" % n, "census-%d" % n,
                            _build_wire, float(n)).id for n in range(3)]
        columns = list(vitals.VITAL_COLUMNS)
        parts = ["COUNT(*)", "SUM(deleted_at IS NULL)"]
        for column in columns:
            parts.append("SUM(%s IS NOT NULL)" % column)
            parts.append("SUM(%s IS NOT NULL AND deleted_at IS NULL)" % column)
        with _raw(self.path) as db:
            row = db.execute(
                "SELECT %s FROM characters" % ",".join(parts)).fetchone()
        counted = {"characters_any": row[0], "characters_live": row[1]}
        for index, column in enumerate(columns):
            counted["%s_seeded_any" % column] = row[2 + index * 2]
            counted["%s_seeded_live" % column] = row[3 + index * 2]
        counted = {key: (0 if value is None else int(value))
                   for key, value in counted.items()}
        census = self.store.vitals_seeding_census()
        self.assertEqual({key: census[key] for key in counted}, counted,
                         "vitals_seeding_census disagrees with the rows on disk")
        self.assertEqual(counted["characters_any"], len(ids))
        for column in columns:
            with self.subTest(column=column):
                self.assertEqual(counted["%s_seeded_any" % column], len(ids))

    def test_the_seventeen_unadjudicated_columns_are_still_absent(self):
        """The half of `COO-DECISION 20260902_1607` that is a REFUSAL.

        A DEFAULT of 0 on `class_id`, `experience`, `cash`, the five stats or
        the five bonuses would turn every honest gap into a confident wrong
        number for every character created afterwards.  Read RAW as well as
        through the store, so the reader being graded does not supply the
        evidence.
        """
        account = self.store.ensure_account("gaps")
        character = self._create(account, "Gappy", "gappy", _build_wire, 1.0)
        unborn = birth_state.columns_no_birth_carries()
        self.assertEqual(len(unborn), 17, unborn)
        with _raw(self.path) as db:
            row = db.execute(
                "SELECT %s FROM characters WHERE id=?" % ",".join(unborn),
                (character.id,)).fetchone()
        for column in unborn:
            with self.subTest(column=column):
                self.assertIsNone(row[column])
                self.assertNotIn(column, self.store.read_typed_attributes(
                    character.id))
        # and they arrive at the gate as NAMED gaps, never as zeros
        values = {typed.TYPED_COLUMNS[c].x: v for c, v in
                  self.store.read_typed_attributes(character.id).items()}
        gaps = {gap.x: gap for gap in compose.block_gaps(values)}
        for column in unborn:
            with self.subTest(column=column):
                gap = gaps[typed.TYPED_COLUMNS[column].x]
                self.assertEqual(gap.reason, compose.REASON_NO_TYPED_VALUE)

    def test_the_four_numbers_are_the_ones_the_owner_fixed(self):
        """The DEFAULTS in the schema are the numbers `007`/`008` used.

        Read off `PRAGMA table_info` -- what SQLite really installed -- and
        compared with the modules that own the numbers, never with a literal
        written here.  `COO-DECISION 20260902_1607`: the numbers cannot be
        changed, and this is the assertion that notices if they are.
        """
        columns = _columns(self.path, "characters")
        declared = {column: columns[column][3] for column in DEFAULTED}
        expected = dict(birth_state.defaulted_birth())
        self.assertEqual(sorted(expected), sorted(DEFAULTED))
        for column, text in declared.items():
            with self.subTest(column=column):
                self.assertEqual(float(text), float(expected[column]))
        # and a newborn really receives them
        account = self.store.ensure_account("numbers")
        character = self._create(account, "Numbers", "numbers",
                                 _build_wire, 1.0)
        self.assertEqual(
            self.store.read_typed_attributes(character.id), expected)
        # The vitals half is reached through `pf_birth_state` and not by
        # calling the ordered birth function of `COO-DECISION 20260902_0443`
        # point 1 directly.  That point keeps the function to one call site,
        # `NewCharacterVitalsTests` in `tests/test_persistence_vitals.py`
        # enforces it with a scan over every python tree, and the scan reads
        # TEXT -- so this file does not spell the name even in a comment,
        # rather than joining that test's allowlist and costing it a little
        # of its reach.  The walk speed is compared against the module that
        # measured it.
        self.assertEqual(
            {c: expected[c] for c in vitals.VITAL_COLUMNS},
            birth_state.seeded_birth())
        self.assertEqual(expected["speed_walk"],
                         compose.CLIENT_CONSTRUCTION_DEFAULTS[7].value)


class _StoppedAt008(unittest.TestCase):
    """A real database that stopped at `008`, with real rows in it -- the
    shape the owner's machine is in the moment before `009` runs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "state.sqlite3"
        self.through_008 = _migrations_through(8, self.root / "through_008")
        store = SQLiteStore(self.path, self.through_008)
        store.migrate()
        self.account_id = store.ensure_account("pre-009")
        self.veteran = store.create_character(
            self.account_id, "Veteran", "veteran", "fingerprint-veteran",
            _build_wire, Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        store.write_typed_attributes(self.veteran.id, dict(VETERAN))
        self.rookie = store.create_character(
            self.account_id, "Rookie", "rookie", "fingerprint-rookie",
            _build_wire, Position(3, 0, 4.0, 5.0, 6.0, heading=0.0))
        # What the rookie was BORN holding on a pre-009 database, measured
        # through the gate that refuses any state this lane does not accept.
        # NOT written down as `{}` here: `COO-DECISION 20260902_1607` keeps
        # chief's birth-write plug (`COO-DECISION 20260902_0444`) alive at
        # R306, and the day it lands a rookie born on this pre-009 database
        # holds the three vitals.  A literal `{}` would then go red inside
        # HIS pull request, in THIS lane's file, accusing a correct line --
        # which is the exact shape `tests/pf_birth_state.py` exists to stop
        # this lane from laying in another lane's corridor.  A `pf-adversary`
        # pass installed that plug and measured the red before it shipped.
        self.rookie_birth = birth_state.measure_birth_typed_state(
            store, self.rookie.id)
        self.doomed = store.create_character(
            self.account_id, "Doomed", "doomed", "fingerprint-doomed",
            _build_wire, Position(3, 0, 7.0, 8.0, 9.0, heading=0.0))
        session = store.open_session(self.account_id)
        store.soft_delete_character(session, self.doomed.selector)
        store.close_session(session)
        self.assertEqual(_applied(self.path), list(range(1, 9)))

    def _rows(self, path=None):
        with _raw(path or self.path) as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM characters ORDER BY id")]

    def _everything_else(self, path=None):
        """Every row of every table except `characters` and the ledger."""
        out = {}
        with _raw(path or self.path) as db:
            names = [row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            for name in names:
                if name in ("characters", "schema_migrations"):
                    continue
                out[name] = [tuple(row) for row in db.execute(
                    "SELECT * FROM %s" % name)]
        return out


class TheOwnerKeepsACopyBefore009Tests(_StoppedAt008):
    """`COO-DECISION 20260902_1607` condition 1, and the owner's own rule
    behind it (`COO-DECISION 20260901_1112` point 3).

    The condition is explicit about what will not do: "prove it with a test
    that a backup FILE really appears -- not a test that the code calls the
    function".  So nothing here patches `snapshot_database` and asserts it was
    called.  A file is looked for on disk, opened, and read back.
    """

    def test_a_snapshot_file_exists_and_it_predates_009(self):
        backups = self.root / "db_backups"
        snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
            backups_root=backups)
        self.assertIsNotNone(snapshot, "no snapshot was taken before 009")
        snapshot = Path(snapshot)
        self.assertTrue(snapshot.is_file(), snapshot)
        self.assertGreater(snapshot.stat().st_size, 0)
        # it is not the live database under another name
        self.assertNotEqual(snapshot.resolve(), self.path.resolve())

        # RESTORED AND READ, not just stat'd: a zero-byte file passes an
        # existence check and loses the world.
        restored = self.root / "restored.sqlite3"
        shutil.copy2(snapshot, restored)
        self.assertEqual(_applied(restored), list(range(1, 9)),
                         "the snapshot was taken AFTER 009 was applied")
        self.assertIsNone(_columns(restored, "characters")["level"][3],
                          "the snapshot already carries 009's DEFAULT")
        self.assertEqual(self._rows(restored), self._rows_before_009,
                         "the snapshot does not hold the pre-009 rows")
        # and the live database really did move on.  `assertIn`, not
        # `assertEqual(..., list(range(1, 10)))`: the day `010` exists the
        # equality would be a claim about how many migrations the repository
        # has, which is not what this class measures.  A `pf-adversary` pass
        # dropped an empty `010` into the directory and turned this red.
        self.assertIn(VERSION, _applied(self.path))
        self.assertNotIn(VERSION, _applied(restored))

    def setUp(self):
        super().setUp()
        self._rows_before_009 = self._rows()

    def test_a_snapshot_that_cannot_be_taken_stops_009_entirely(self):
        """Fail-safe direction: a boot that cannot protect the owner's only
        copy of the world must not go on to rebuild her table."""
        backups = self.root / "db_backups"
        with mock.patch.object(
                persistence_backup, "snapshot_database",
                side_effect=persistence_backup.BackupError("disk went away")):
            with self.assertRaises(persistence_backup.BackupError):
                SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
                    backups_root=backups)
        self.assertEqual(_applied(self.path), list(range(1, 9)))
        self.assertIsNone(_columns(self.path, "characters")["level"][3])
        self.assertEqual(self._rows(), self._rows_before_009)

    def test_009_is_what_makes_the_snapshot_due(self):
        take, reason = persistence_backup.should_snapshot(self.path, MIGRATIONS)
        self.assertTrue(take, reason)
        self.assertIn("009", reason)
        self.assertIn(
            VERSION,
            persistence_backup.pending_versions(self.path, MIGRATIONS))


class TheSchemaComesBackWholeTests(_StoppedAt008):
    """`COO-DECISION 20260902_1607` condition 3, which the letter says it will
    read before any other: index, constraint and soft-delete uniqueness all
    survive the rebuild, proven by comparing the schema BEFORE with the schema
    AFTER automatically rather than by eye."""

    def _upgrade(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()

    def test_every_index_comes_back_by_name_and_by_its_exact_sql(self):
        before = _indexes(self.path, "characters")
        self.assertEqual(sorted(before), [
            "characters_active_identity", "characters_active_name_lookup",
            "characters_active_selector", "characters_create_fingerprint"])
        self._upgrade()
        self.assertEqual(_indexes(self.path, "characters"), before)

    def test_every_column_comes_back_and_only_the_four_gained_a_default(self):
        before = _columns(self.path, "characters")
        self._upgrade()
        after = _columns(self.path, "characters")
        self.assertEqual(sorted(before), sorted(after))
        for column, spec in before.items():
            with self.subTest(column=column):
                cid, type_, notnull, default, pk = spec
                acid, atype, anotnull, adefault, apk = after[column]
                self.assertEqual((cid, type_, notnull, pk),
                                 (acid, atype, anotnull, apk))
                if column in DEFAULTED:
                    self.assertIsNone(default)
                    self.assertIsNotNone(adefault)
                else:
                    self.assertEqual(default, adefault,
                                     "a column outside the four moved")

    def test_the_table_definition_differs_only_by_those_four_defaults(self):
        """The whole `CREATE TABLE` text, compared after removing exactly the
        four DEFAULT clauses `009` is allowed to add.  A CHECK constraint
        quietly dropped in the rebuild shows up here and nowhere else."""
        before = _table_sql(self.path, "characters")
        self._upgrade()
        after = _table_sql(self.path, "characters")
        stripped = after
        for column, spec in _columns(self.path, "characters").items():
            if column in DEFAULTED:
                stripped = stripped.replace(" DEFAULT %s" % spec[3], "", 1)
        # Whitespace around punctuation is normalised because SQLite writes
        # the two texts differently for reasons that carry no meaning: a
        # column added by `ALTER TABLE` arrives as `DEFAULT '' , level ...`,
        # a column written into a `CREATE TABLE` as `DEFAULT '', level ...`.
        # Nothing else is normalised, so a dropped CHECK still shows.
        def normalise(text):
            text = text.replace('"characters"', "characters")
            text = re.sub(r"\s*([(),])\s*", r"\1", text)
            return " ".join(text.split())

        self.maxDiff = None
        self.assertEqual(normalise(stripped), normalise(before))

    def test_the_uniqueness_rules_still_refuse_what_they_refused(self):
        """The behavioural half.  A matching `sqlite_master` row is a claim
        about text; a refused INSERT is a claim about the database."""
        self._upgrade()
        with _raw(self.path) as db:
            for column, value in (("selector", self.veteran.selector),
                                  ("identity_lo", self.veteran.identity_lo)):
                with self.subTest(rule=column):
                    with self.assertRaises(sqlite3.IntegrityError):
                        db.execute(
                            "INSERT INTO characters(account_id,selector,name,"
                            "name_key,create_fingerprint,actor_wire,"
                            "avatar_wire,identity_lo,identity_hi,created_at,"
                            "updated_at) SELECT account_id,%s,'Clash','clash',"
                            "'fingerprint-clash',actor_wire,avatar_wire,%s,"
                            "identity_hi,created_at,updated_at FROM characters "
                            "WHERE id=?"
                            % (self.veteran.selector if column == "selector"
                               else 200,
                               self.veteran.identity_lo if column == "identity_lo"
                               else 999999),
                            (self.veteran.id,))
                    db.rollback()

    def test_a_soft_deleted_slot_can_still_be_recreated_in_place(self):
        """`004`'s whole reason for existing, exercised after `009` rebuilt the
        table it installed those partial indexes on."""
        self._upgrade()
        store = SQLiteStore(self.path, MIGRATIONS)
        reborn = store.create_character(
            self.account_id, "Doomed", "doomed", "fingerprint-doomed-again",
            _build_wire, Position(3, 0, 7.0, 8.0, 9.0, heading=0.0))
        self.assertEqual(reborn.selector, self.doomed.selector)
        self.assertNotEqual(reborn.id, self.doomed.id)
        self.assertEqual(store.read_typed_attributes(reborn.id),
                         birth_state.defaulted_birth())

    def test_the_foreign_key_to_accounts_still_bites(self):
        self._upgrade()
        with _raw(self.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO characters(account_id,selector,name,name_key,"
                    "create_fingerprint,actor_wire,avatar_wire,identity_lo,"
                    "identity_hi,created_at,updated_at) SELECT 999999,77,"
                    "'Orphan','orphan','fingerprint-orphan',actor_wire,"
                    "avatar_wire,777777,identity_hi,created_at,updated_at "
                    "FROM characters WHERE id=?", (self.veteran.id,))
            db.rollback()
            self.assertEqual(
                [], db.execute("PRAGMA foreign_key_check").fetchall())

    def test_the_type_checks_added_by_006_still_refuse_a_wrong_type(self):
        self._upgrade()
        with _raw(self.path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE characters SET level='nine' WHERE id=?",
                           (self.veteran.id,))
            db.rollback()
            # NOT an integer: a REAL-affinity column converts `4` to `4.0`
            # and `typeof` then says 'real', so that spelling would assert
            # nothing.  A string is what the CHECK really refuses.
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE characters SET speed_walk='fast' WHERE id=?",
                           (self.veteran.id,))
            db.rollback()


class NotOneExistingRowMovesTests(_StoppedAt008):
    """A DEFAULT applies to future INSERTs only, and this is the file that
    proves `009` did nothing else -- the property the migration's own G2 guard
    also enforces, measured here from outside it."""

    def test_every_row_survives_the_rebuild_byte_for_byte(self):
        """Every row of `characters`, and every row of every other table.

        The other tables are compared over the tables that existed BEFORE the
        upgrade rather than by whole-dictionary equality: a later migration
        that ADDS a table is not this test's business, and a `pf-adversary`
        pass showed the strict version going red on an empty probe `010`.
        A table that DISAPPEARS is still caught, by the membership assertion.
        """
        before = self._rows()
        others = self._everything_else()
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(self._rows(), before)
        after = self._everything_else()
        for name, rows in others.items():
            with self.subTest(table=name):
                self.assertIn(name, after, "a table disappeared")
                self.assertEqual(after[name], rows)

    def test_the_veteran_keeps_its_own_numbers_and_does_not_get_the_defaults(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()
        store = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(store.read_typed_attributes(self.veteran.id), VETERAN)

    def test_a_row_born_before_009_is_not_reached_by_the_default(self):
        """The gap this file does NOT close, said out loud rather than left to
        be discovered: a DEFAULT applies to future INSERTs and cannot reach
        backwards, so a character created between `007` and `009` comes out of
        the upgrade holding exactly what it was born holding.  Only a backfill
        could change that, and `COO-DECISION 20260902_1607` approved the
        DEFAULT alone -- so the state is pinned here and reported to COO
        rather than fixed on this lane's own authority.

        Phrased as "unchanged by `009`" rather than as "empty", so it stays
        true, and stays a measurement, in both worlds: today the rookie holds
        nothing and the vitals doors refuse it; the day chief's plug lands it
        holds the three and they resolve.  Either way `009` must not have
        touched it.
        """
        SQLiteStore(self.path, MIGRATIONS).migrate()
        store = SQLiteStore(self.path, MIGRATIONS)
        after = store.read_typed_attributes(self.rookie.id)
        self.assertEqual(after, self.rookie_birth,
                         "009 reached a row that already existed")
        self.assertNotEqual(
            after, birth_state.defaulted_birth(),
            "a row born before 009 came out holding 009's defaults; the "
            "DEFAULT reached backwards, which is not what a DEFAULT does")
        resolution = store.read_character_vitals(self.rookie.id)
        if not self.rookie_birth:
            with self.assertRaises(vitals.VitalsError):
                resolution.require()
        else:
            self.assertTrue(resolution.complete,
                            [gap.reason for gap in resolution.gaps])

    def test_the_soft_deleted_row_is_still_there_and_still_deleted(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()
        with _raw(self.path) as db:
            row = db.execute(
                "SELECT deleted_at FROM characters WHERE id=?",
                (self.doomed.id,)).fetchone()
        self.assertIsNotNone(row, "the rebuild dropped a soft-deleted row")
        self.assertIsNotNone(row["deleted_at"])

    def test_running_the_boot_twice_changes_nothing_more(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()
        after_first = self._rows()
        ledger = _applied(self.path)
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(self._rows(), after_first)
        self.assertEqual(_applied(self.path), ledger)

    def test_nothing_outside_this_table_changes_shape(self):
        """Every other schema object, byte for byte in `sqlite_master`.

        `_indexes` and `_columns` above are scoped to `characters`, and the
        row comparison is about rows.  A `pf-adversary` pass used the gap:
        a rebuild that also ran `DROP INDEX sessions_one_active_character`
        (`002`, one live session per character) passed every guard the
        migration had AND this whole file.  `G6` inside the migration now
        refuses it too; this is the same sentence measured from OUTSIDE the
        migration, because `G6`'s own "before" picture is taken by the
        migration itself.
        """
        def schema():
            with _raw(self.path) as db:
                return {(row["type"], row["name"]): row["sql"]
                        for row in db.execute(
                            "SELECT type,name,tbl_name,sql FROM sqlite_master "
                            "WHERE name NOT LIKE 'sqlite_%' "
                            "AND tbl_name<>'characters'")}

        before = schema()
        self.assertTrue(before)
        SQLiteStore(self.path, MIGRATIONS).migrate()
        after = schema()
        for key, sql in before.items():
            with self.subTest(object=key):
                self.assertIn(key, after, "a schema object disappeared")
                self.assertEqual(after[key], sql)

    def test_no_scratch_table_of_this_migration_is_left_behind(self):
        """The guards build tables to hold the BEFORE picture.  A leftover
        `_pf_mig009_rows_before` would be a second copy of every character in
        the owner's live database, forever."""
        SQLiteStore(self.path, MIGRATIONS).migrate()
        with _raw(self.path) as db:
            left = [row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE name LIKE '_pf_mig%'")]
        self.assertEqual(left, [])


class TheGuardsInsideTheMigrationFireTests(_StoppedAt008):
    """The guards abort the upgrade, measured by breaking the file on purpose.

    A copy of the migration in a temporary directory, never the repository's
    own file.  Each mutation is a real regression somebody could write, and
    each must leave the database exactly where it started: no `009` in the
    ledger, no DEFAULT on the columns, and every row still there -- which is
    what makes "the next boot retries from the pre-migration state" true.
    """

    def _staged(self, mutate):
        staged = _migrations_through(
            8, self.root / ("staged_%d" % id(mutate)))
        text = MIGRATION_009.read_text(encoding="utf-8")
        broken = mutate(text)
        self.assertNotEqual(broken, text, "the mutation changed nothing")
        (staged / MIGRATION_009.name).write_text(broken, encoding="utf-8")
        return staged

    def _refuses(self, mutate):
        """The mutation is refused BY A GUARD, and by nothing else.

        `assertRaises(Exception)` alone would pass on a mutation that broke
        the SQL syntax, which measures the SQL parser rather than the guards
        this class is about.  The exception type and message are pinned to the
        `CHECK(ok=1)` the guards are built out of.
        """
        before = self._rows()
        staged = self._staged(mutate)
        with self.assertRaises(sqlite3.IntegrityError) as caught:
            SQLiteStore(self.path, staged).migrate()
        self.assertIn("CHECK constraint failed", str(caught.exception))
        self.assertEqual(_applied(self.path), list(range(1, 9)))
        self.assertIsNone(_columns(self.path, "characters")["level"][3])
        self.assertEqual(self._rows(), before)
        return caught.exception

    def test_a_rebuild_that_loses_a_unique_index_is_refused(self):
        self._refuses(lambda text: text.replace(
            "CREATE UNIQUE INDEX characters_active_selector ON characters"
            "(account_id, selector) WHERE deleted_at IS NULL;\n", ""))

    def test_a_rebuild_that_loses_rows_is_refused(self):
        self._refuses(lambda text: text.replace(
            "    SELECT id,account_id,selector,name,actor_wire",
            "    SELECT id,account_id,selector,name,actor_wire", 1).replace(
                "bonus_per FROM characters;",
                "bonus_per FROM characters WHERE id<0;", 1))

    def test_a_rebuild_that_stamps_an_existing_row_is_refused(self):
        """The `UPDATE` with no `WHERE` -- the exact shape a `pf-adversary`
        pass drove through the pin this file replaces."""
        self._refuses(lambda text: text.replace(
            "CREATE TABLE _pf_mig009_guard(ok INTEGER NOT NULL CHECK(ok=1));",
            "UPDATE characters SET level=1,hp_current=100,hp_max=100;\n"
            "CREATE TABLE _pf_mig009_guard(ok INTEGER NOT NULL CHECK(ok=1));",
            1))

    def test_a_rebuild_that_defaults_a_column_nobody_adjudicated_is_refused(self):
        """`class_id INTEGER DEFAULT 0` is the owner's banned guess arriving
        as a schema change.  The G3 guard names the four columns that may gain
        a default, so a fifth is refused by the migration itself."""
        self._refuses(lambda text: text.replace(
            "    class_id INTEGER\n", "    class_id INTEGER DEFAULT 0\n", 1))

    def test_a_rebuild_that_changes_one_of_the_four_numbers_is_refused(self):
        """`COO-DECISION 20260902_1607`: the numbers cannot be changed.  A
        `hp_max DEFAULT 150` is refused before it can reach a database."""
        self._refuses(lambda text: text.replace(
            "    hp_max INTEGER DEFAULT 100\n",
            "    hp_max INTEGER DEFAULT 150\n", 1))


if __name__ == "__main__":
    unittest.main()
