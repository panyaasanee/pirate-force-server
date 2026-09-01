"""LANE-DB-BACKUP-001: a boot that is about to migrate a real database copies
it first, the copy is a database that opens, and the original is not touched.

WHAT THIS FILE IS THE EVIDENCE FOR.  ``COO-DECISION 2026-09-01T11:12+07:00``
(``pf_bridge/notes_to_chief/20260901_1112_COO-DECISION-amend-lane-db-canonical-
db-via-migrations.md``, point 3) makes an automatic pre-migration copy of the
``.db`` file a precondition for ANY migration of this lane's that touches
existing rows.  Before this round no boot copied the database at any point:
``SQLiteStore.migrate`` applied whatever new ``migrations/NNN_*.sql`` it found
straight onto the owner's only copy of the live world.  (The narrow claim is
"automatically, at boot".  Nine ``tools/*_headless_replay.py`` scripts do
``shutil.copyfile`` a database for their own scratch runs, and
``tests/pf_preconditions.py``'s ``BACKUPS_TREE`` names a machine-local
``backups/`` tree of hand-made snapshots -- neither runs at the moment a
migration is applied.)  This file is the evidence that the new, separate
``SQLiteStore.migrate_with_backup`` closes that gap, and that the old
``migrate`` is byte-for-byte the same code path it was.

THE DATABASES HERE ARE REAL.  Every database in this file is built by the real
``SQLiteStore`` running the repository's real ``migrations/`` directory in a
temporary directory, and every read-back opens the produced snapshot with a
fresh ``sqlite3`` connection.  Nothing is hand-assembled, and nothing here can
reach ``state/pirateforce.sqlite3`` -- every path is built under
``tempfile.TemporaryDirectory()`` (round 41's rule).

WHY SEVERAL OF THESE TESTS EXIST AT ALL.  They are pf-adversary findings from
this lane's first round, each one measured before it was fixed:
``test_snapshot_leaves_the_source_database_byte_identical`` (the copy used to
open the live database read-WRITE and, on close, checkpoint and DELETE the hot
``-wal`` it claimed to preserve), ``test_a_failed_snapshot_is_left_marked
_incomplete`` (a half-written directory used to be named exactly like a good
backup), ``test_verification_rejects_a_corrupt_snapshot`` (the integrity check
was asserted against a constant the code always wrote, so deleting the check
entirely kept the suite green) and ``test_repeated_boots_against_an_unchanged
_database_reuse_one_snapshot`` (ten retries of a failing migration used to make
ten full copies of the live world).

WHAT THIS FILE DOES NOT PROVE.  No boot path calls ``migrate_with_backup``
yet -- ``app.py`` (chief's zone, not this lane's) still calls ``migrate``, and
CORE-REQUEST-DB-001 asks for that one-line insertion point.  So this is
wire/DB evidence only: nothing here is client-observable, and nothing here
proves the owner's own canonical database was ever protected on a real boot.
It also proves nothing about restoring: this lane's module only ever creates
snapshots, and a restore is a human act (see the manifest's ``restore_hint``).
"""
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_backup  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"


class PreMigrationBackupTest(unittest.TestCase):
    # ---- helpers ----------------------------------------------------------

    def _store(self, tmp, name="pirateforce.sqlite3", migrations=MIGRATIONS):
        return SQLiteStore(Path(tmp) / "state" / name, migrations)

    def _migrated_store(self, tmp):
        store = self._store(tmp)
        Path(store.path).parent.mkdir(parents=True, exist_ok=True)
        store.migrate()
        return store

    def _migrations_plus(self, tmp, version, sql, name="extra"):
        """The real migrations directory plus one more file -- the only way to
        make a real database have something genuinely pending."""
        later = Path(tmp) / ("migrations_%s" % name)
        later.mkdir()
        for path in sorted(MIGRATIONS.glob(persistence_backup.MIGRATION_GLOB)):
            (later / path.name).write_bytes(path.read_bytes())
        (later / ("%03d_lane_db_probe.sql" % version)).write_text(sql, encoding="utf-8")
        return later

    def _hot_wal(self, path):
        """An open connection with a committed row that SQLite cannot
        checkpoint away while the connection lives -- the state a boot finds
        after a server was killed, and the state the naive implementation used
        to destroy."""
        holder = sqlite3.connect(str(path))
        holder.execute("PRAGMA journal_mode=WAL")
        holder.execute(
            "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
            ("committed_into_the_wal", "2026-09-01T12:00:00Z"),
        )
        holder.commit()
        return holder

    @staticmethod
    def _state(path):
        """Every byte SQLite keeps that CARRIES DATA for this database.

        ``-shm`` is excluded on purpose: it is a derived WAL index that SQLite
        rebuilds whenever any reader attaches, so it moves under a read-only
        probe as well.  Its continued EXISTENCE is asserted separately -- the
        defect this test guards is the old implementation DELETING the
        sidecars, not SQLite refreshing an index."""
        out = {}
        for name in (path.name, path.name + "-wal"):
            sidecar = path.with_name(name)
            out[name] = sidecar.read_bytes() if sidecar.exists() else None
        return out

    # ---- the decision -----------------------------------------------------

    def test_fresh_database_file_is_not_snapshotted(self):
        """A database that does not exist yet has nothing to lose, so a first
        boot must not leave an empty snapshot folder behind."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            Path(store.path).parent.mkdir(parents=True, exist_ok=True)
            take, reason = persistence_backup.should_snapshot(store.path, MIGRATIONS)
            self.assertFalse(take, reason)
            self.assertIn("fresh database", reason)
            self.assertIsNone(store.migrate_with_backup())
            self.assertFalse(
                (Path(store.path).parent / persistence_backup.DEFAULT_BACKUP_DIRNAME).exists()
            )

    def test_already_migrated_database_is_not_snapshotted(self):
        """Every server boot calls migrate.  If an up-to-date database were
        snapshotted anyway, one long-running bridge would fill its own disk
        with identical copies of a database nothing was about to change."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            take, reason = persistence_backup.should_snapshot(store.path, MIGRATIONS)
            self.assertFalse(take, reason)
            self.assertEqual([], persistence_backup.pending_versions(store.path, MIGRATIONS))
            self.assertIsNone(store.migrate_with_backup())

    def test_pending_migration_on_an_existing_database_is_snapshotted(self):
        """The case the owner's rule is actually about: a database with rows in
        it meets a migration file it has never seen."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            account_id = store.ensure_account("panya")
            later = self._migrations_plus(
                tmp, 900, "CREATE TABLE lane_db_probe(id INTEGER PRIMARY KEY);\n"
            )
            store_later = SQLiteStore(store.path, later)

            take, reason = persistence_backup.should_snapshot(store.path, later)
            self.assertTrue(take, reason)
            self.assertEqual([900], persistence_backup.pending_versions(store.path, later))

            snapshot = store_later.migrate_with_backup()
            self.assertIsNotNone(snapshot)
            self.assertTrue(snapshot.exists())

            # the live database really did get the migration ...
            with store_later.connect() as db:
                db.execute("SELECT id FROM lane_db_probe").fetchall()
            # ... and the snapshot is the state from BEFORE it, with the row
            # that existed at that moment still in it.
            copy = sqlite3.connect(str(snapshot))
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    copy.execute("SELECT id FROM lane_db_probe").fetchall()
                accounts = copy.execute("SELECT id, login_name FROM accounts").fetchall()
                versions = {
                    int(r[0]) for r in copy.execute("SELECT version FROM schema_migrations")
                }
            finally:
                copy.close()
            self.assertEqual([(account_id, "panya")], accounts)
            self.assertNotIn(900, versions)

    def test_unreadable_ledger_is_snapshotted_rather_than_skipped(self):
        """Fail-safe direction: a database this server cannot read the ledger
        of is the LEAST safe one to migrate unprotected, so 'unknown' must
        mean 'copy it', never 'assume it is up to date'."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state" / "not_a_database.sqlite3"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"this is not a sqlite database at all")
            self.assertIsNone(persistence_backup.applied_versions(path))
            self.assertIsNone(persistence_backup.pending_versions(path, MIGRATIONS))
            take, reason = persistence_backup.should_snapshot(path, MIGRATIONS)
            self.assertTrue(take, reason)
            self.assertIn("unreadable", reason)

    def test_in_memory_database_migrates_without_a_snapshot(self):
        """Tests and headless replays use ``:memory:``; there is no file to
        copy and asking for one must not break them."""
        store = SQLiteStore(":memory:", MIGRATIONS)
        take, reason = persistence_backup.should_snapshot(":memory:", MIGRATIONS)
        self.assertFalse(take, reason)
        self.assertIsNone(store.migrate_with_backup())

    # ---- the ledger-rewrite hole ------------------------------------------

    def _downgrade_ledger_to_pre_checksum(self, path):
        """Rebuild ``schema_migrations`` in the exact shape
        ``migrations/001_initial.sql:2`` creates it -- ``(version, applied_at)``,
        no checksum column -- which is what a database created by an older
        build of this server still has today."""
        db = sqlite3.connect(str(path))
        try:
            db.execute(
                "CREATE TABLE ledger_old(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            db.execute("INSERT INTO ledger_old SELECT version, applied_at FROM schema_migrations")
            db.execute("DROP TABLE schema_migrations")
            db.execute("ALTER TABLE ledger_old RENAME TO schema_migrations")
            db.commit()
            return [str(r[1]) for r in db.execute("PRAGMA table_info(schema_migrations)")]
        finally:
            db.close()

    def test_ledger_checksum_upgrade_is_snapshotted_even_with_no_pending_file(self):
        """The one row-touching write that ``pending_versions`` cannot see.

        ``migrate()`` upgrades a pre-checksum ledger in place -- ALTER TABLE
        plus one UPDATE per applied row -- while every migration FILE is
        already applied.  A long-lived database (the owner's canonical one is
        exactly that shape of candidate) would otherwise have met that write
        with no snapshot at all."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            store.ensure_account("panya")
            columns = self._downgrade_ledger_to_pre_checksum(store.path)
            self.assertEqual(["version", "applied_at"], columns)

            self.assertEqual([], persistence_backup.pending_versions(store.path, MIGRATIONS))
            self.assertTrue(persistence_backup.ledger_rewrite_pending(store.path))
            take, reason = persistence_backup.should_snapshot(store.path, MIGRATIONS)
            self.assertTrue(take, reason)
            self.assertIn("rewritten in place", reason)

            snapshot = store.migrate_with_backup()
            self.assertIsNotNone(snapshot)

            live = sqlite3.connect(str(store.path))
            try:
                live_columns = [str(r[1]) for r in live.execute("PRAGMA table_info(schema_migrations)")]
                stamped = live.execute(
                    "SELECT count(*) FROM schema_migrations WHERE checksum IS NOT NULL"
                ).fetchone()[0]
            finally:
                live.close()
            self.assertIn("checksum", live_columns)
            self.assertGreater(stamped, 0)

            copy = sqlite3.connect(str(snapshot))
            try:
                copy_columns = [str(r[1]) for r in copy.execute("PRAGMA table_info(schema_migrations)")]
            finally:
                copy.close()
            self.assertEqual(["version", "applied_at"], copy_columns)

    def test_ledger_rewrite_pending_is_false_for_a_current_database(self):
        """The guard must not turn every ordinary boot into a snapshot."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            self.assertFalse(persistence_backup.ledger_rewrite_pending(store.path))
            self.assertIsNone(store.migrate_with_backup())

    def test_ledger_rewrite_pending_is_false_when_there_is_no_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(
                persistence_backup.ledger_rewrite_pending(Path(tmp) / "absent.sqlite3")
            )

    def test_ledger_rewrite_pending_fails_safe_on_a_database_it_cannot_read(self):
        """Its own docstring promises 'anything that cannot be read reports
        True'.  Without this test that direction can be inverted silently."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "junk.sqlite3"
            path.write_bytes(b"not a database")
            self.assertTrue(persistence_backup.ledger_rewrite_pending(path))

    def test_ledger_rewrite_pending_is_true_with_no_ledger_table_at_all(self):
        """A real database that this server has never migrated: migrate() is
        about to create the ledger and stamp it, in a file that already holds
        rows."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "foreign.sqlite3"
            db = sqlite3.connect(str(path))
            db.execute("CREATE TABLE somebody_elses(id INTEGER PRIMARY KEY)")
            db.commit()
            db.close()
            self.assertTrue(persistence_backup.ledger_rewrite_pending(path))

    # ---- the copy ---------------------------------------------------------

    def test_snapshot_leaves_the_source_database_byte_identical(self):
        """pf-adversary, round 1, defect 1 -- the worst one found.

        The first implementation opened the live database READ-WRITE to copy
        it.  On close, as the last connection, SQLite checkpointed the hot WAL
        into the main file and DELETED ``-wal`` and ``-shm``: the module whose
        docstring said it 'only ever creates' performed the one irreversible
        act on the owner's file, before anything had been verified, and
        destroyed the very originals its manifest promised to preserve."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            path = Path(store.path)
            holder = self._hot_wal(path)
            try:
                before = self._state(path)
                self.assertIsNotNone(before[path.name + "-wal"])
                self.assertTrue(before[path.name + "-wal"], "precondition: -wal is not empty")

                persistence_backup.snapshot_database(path, Path(tmp) / "backups")

                after = self._state(path)
                shm_survived = path.with_name(path.name + "-shm").exists()
            finally:
                holder.close()
            self.assertEqual(before, after)
            self.assertTrue(shm_survived, "the snapshot must not delete -shm either")

    def test_snapshot_leaves_a_crashed_servers_wal_alone(self):
        """The same defect as above, in the state it actually bites.

        The test above keeps a connection open, which is itself what stops
        SQLite from checkpointing -- so it passes even against an
        implementation that opens the source read-WRITE.  The real case has NO
        live connection: a server was killed with a committed transaction still
        only in ``-wal``.  There, a read-write handle checkpoints and DELETES
        the sidecars the moment it closes.  A child process that commits and
        then calls ``os._exit`` is the only honest way to produce that state."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            path = Path(store.path)
            script = (
                "import os, sqlite3\n"
                "db = sqlite3.connect(%r)\n"
                "db.execute('PRAGMA journal_mode=WAL')\n"
                "db.execute(\"INSERT INTO accounts(login_name,created_at) "
                "VALUES ('killed_mid_flight','t')\")\n"
                "db.commit()\n"
                "os._exit(0)\n" % str(path)
            )
            subprocess.run([sys.executable, "-c", script], check=True)

            wal = path.with_name(path.name + "-wal")
            self.assertTrue(wal.exists(), "precondition: the crash left a -wal")
            self.assertGreater(wal.stat().st_size, 0, "precondition: -wal is hot")
            wal_before = wal.read_bytes()
            main_before = path.read_bytes()

            persistence_backup.snapshot_database(path, Path(tmp) / "backups")

            self.assertTrue(wal.exists(), "the snapshot deleted the crashed server's -wal")
            self.assertEqual(wal_before, wal.read_bytes())
            self.assertEqual(main_before, path.read_bytes())

    def test_snapshot_captures_a_committed_wal_transaction(self):
        """The reason this module does not use ``shutil.copy``: with WAL on
        (``SQLiteStore.connect`` sets it for every file database), a committed
        row can still live only in the ``-wal`` file, and a snapshot that
        opened clean while quietly missing the newest accounts would be worse
        than no snapshot at all.

        The snapshot is moved to an empty directory before it is opened.
        Opening it where it lies would prove nothing -- the raw ``-wal`` is
        kept in the snapshot's ``raw_originals/`` for forensics, and if it sat
        beside the database SQLite would recover the transaction out of THAT,
        so a plain ``shutil.copy`` of the main file would look just as good.
        (Measured both ways: with a sidecar beside it this assertion passes
        against a ``shutil.copy`` implementation; isolated, it does not.)"""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            path = Path(store.path)
            holder = self._hot_wal(path)
            try:
                snapshot = persistence_backup.snapshot_database(
                    path, Path(tmp) / "backups", reason="test"
                )
            finally:
                holder.close()

            self.assertFalse(snapshot.with_name(snapshot.name + "-wal").exists())
            alone = Path(tmp) / "isolated" / snapshot.name
            alone.parent.mkdir()
            alone.write_bytes(snapshot.read_bytes())

            copy = sqlite3.connect(str(alone))
            try:
                names = [r[0] for r in copy.execute("SELECT login_name FROM accounts")]
            finally:
                copy.close()
            self.assertIn("committed_into_the_wal", names)

    def test_raw_originals_are_preserved_beside_but_not_beneath_the_snapshot(self):
        """The forensic copies go in their own subdirectory, byte for byte,
        and never next to the snapshot database where SQLite would read
        them."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            path = Path(store.path)
            holder = self._hot_wal(path)
            try:
                wal_bytes = path.with_name(path.name + "-wal").read_bytes()
                snapshot = persistence_backup.snapshot_database(path, Path(tmp) / "backups")
            finally:
                holder.close()
            raw = snapshot.parent / persistence_backup.RAW_SUBDIR
            self.assertTrue(raw.is_dir())
            self.assertEqual(wal_bytes, (raw / (path.name + "-wal")).read_bytes())
            manifest = json.loads((snapshot.parent / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertIn(path.name + "-wal", manifest["raw_originals"])
            self.assertNotIn(
                path.name + "-wal", [p.name for p in snapshot.parent.iterdir()]
            )

    # ---- verification is real ---------------------------------------------

    def test_verification_rejects_a_corrupt_snapshot(self):
        """pf-adversary, round 1, defect 7: the manifest asserted
        ``integrity_check == "ok"`` against a string the code wrote
        unconditionally, so deleting the check entirely left the suite green.
        This drives the failure branch on a real damaged file."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            with store.connect() as db:
                db.execute("CREATE TABLE bulk(id INTEGER PRIMARY KEY, filler TEXT)")
                db.executemany(
                    "INSERT INTO bulk(filler) VALUES(?)", [("y" * 400,)] * 400
                )
            broken = Path(tmp) / "broken.sqlite3"
            raw = bytearray(Path(store.path).read_bytes())
            page = int.from_bytes(raw[16:18], "big") or 65536
            self.assertGreater(len(raw) // page, 4, "precondition: a multi-page database")
            # Page 1 (the schema) is left intact so the file still opens as a
            # database; a page deep inside the data is destroyed.
            offset = page * (len(raw) // page - 2)
            raw[offset:offset + page] = b"\x00" * page
            broken.write_bytes(bytes(raw))

            with self.assertRaises(persistence_backup.BackupError):
                persistence_backup._verify_snapshot(broken)

    def test_verification_refuses_a_snapshot_sqlite_reports_as_not_ok(self):
        """The other half of the same guard.  Damage severe enough to make
        SQLite raise is easy to produce; damage it merely REPORTS on (a bad
        index entry, a freelist inconsistency) is not, and without this the
        `!= "ok"` comparison can be deleted with the suite still green."""
        verdicts = ["row 3 missing from index characters_active_name_lookup"]

        class _FakeCursor:
            def __init__(self, rows):
                self._rows = rows

            def fetchone(self):
                return self._rows[0]

            def __iter__(self):
                return iter(self._rows)

        class _FakeConnection:
            def execute(self, sql, *args):
                if "integrity_check" in sql:
                    return _FakeCursor([(verdicts[0],)])
                raise AssertionError("nothing may run after a failed check: %r" % sql)

            def close(self):
                self.closed = True

        fake = _FakeConnection()
        with mock.patch.object(
            persistence_backup, "_read_only_connection", return_value=fake
        ):
            with self.assertRaises(persistence_backup.BackupError) as caught:
                persistence_backup._verify_snapshot(Path("unused.sqlite3"))
        self.assertIn(verdicts[0], str(caught.exception))
        self.assertTrue(getattr(fake, "closed", False), "the connection must be closed")

    def test_manifest_verification_reports_the_snapshot_it_actually_read(self):
        """A hardcoded verification block would not know these numbers."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            snapshot = persistence_backup.snapshot_database(
                store.path, Path(tmp) / "backups", reason="because", pending=[900]
            )
            manifest = json.loads((snapshot.parent / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual("pf.lane_db.premigration_snapshot.v1", manifest["kind"])
            self.assertEqual(str(Path(store.path).resolve()), manifest["source_database"])
            self.assertEqual("because", manifest["reason"])
            self.assertEqual([900], manifest["pending_versions"])
            self.assertEqual("ok", manifest["verification"]["integrity_check"])
            self.assertEqual(snapshot.stat().st_size, manifest["verification"]["bytes"])
            self.assertEqual(
                persistence_backup._sha256_file(snapshot),
                manifest["verification"]["sha256"],
            )
            self.assertEqual(
                persistence_backup.migration_versions(MIGRATIONS),
                manifest["verification"]["schema_migrations_in_snapshot"],
            )

    # ---- failure is visible -----------------------------------------------

    def test_a_failed_snapshot_is_left_marked_incomplete(self):
        """pf-adversary, round 1, defect 3.

        A snapshot that dies halfway used to leave a directory named exactly
        like a good one, holding a 0-byte file named exactly like the live
        database.  The owner, told the server would not start, could open
        ``db_backups/``, see the newest folder, and copy that file back over
        the world -- producing the loss the whole rule exists to forbid."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = Path(tmp) / "backups"
            boom = OSError("simulated disk full")
            with mock.patch.object(
                persistence_backup, "_copy_consistent", side_effect=boom
            ):
                with self.assertRaises(persistence_backup.BackupError):
                    persistence_backup.snapshot_database(store.path, root, stamp="FIXED")
            leftovers = sorted(p.name for p in root.iterdir())
            self.assertEqual(1, len(leftovers))
            self.assertTrue(
                leftovers[0].endswith(persistence_backup.INCOMPLETE_SUFFIX), leftovers
            )
            self.assertFalse((root / leftovers[0] / "MANIFEST.json").exists())

    def test_an_incomplete_directory_is_never_reused_as_a_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = Path(tmp) / "backups"
            with mock.patch.object(
                persistence_backup, "_copy_consistent", side_effect=OSError("boom")
            ):
                with self.assertRaises(persistence_backup.BackupError):
                    persistence_backup.snapshot_database(store.path, root)
            good = persistence_backup.snapshot_database(store.path, root)
            self.assertFalse(good.parent.name.endswith(persistence_backup.INCOMPLETE_SUFFIX))
            self.assertTrue((good.parent / "MANIFEST.json").is_file())

    def test_every_failure_is_a_backup_error_including_mkdir(self):
        """pf-adversary, round 1, defect 4: ``mkdir`` sat outside the guarded
        block, so a permission or ENOSPC error escaped as a raw ``OSError`` and
        a boot wrapper written as ``except BackupError:`` would miss it."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            with mock.patch.object(
                Path, "mkdir", side_effect=PermissionError("read-only filesystem")
            ):
                with self.assertRaises(persistence_backup.BackupError):
                    persistence_backup.snapshot_database(store.path, Path(tmp) / "backups")

    def test_low_free_space_refuses_before_copying_anything(self):
        """pf-adversary, round 1, defect 5, second half: better a boot that
        refuses and says why than a copy that runs the disk out halfway."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = Path(tmp) / "backups"
            usage = mock.Mock(free=1)
            with mock.patch.object(persistence_backup.shutil, "disk_usage", return_value=usage):
                with self.assertRaises(persistence_backup.BackupError) as caught:
                    persistence_backup.snapshot_database(store.path, root)
            self.assertIn("free", str(caught.exception))
            self.assertFalse(root.exists(), "nothing may be created before the check")

    # ---- growth -----------------------------------------------------------

    def test_repeated_boots_against_an_unchanged_database_reuse_one_snapshot(self):
        """pf-adversary, round 1, defect 5, first half.

        A migration of this lane's own with one bad statement fails on every
        boot, and ``pending_versions`` keeps reporting it pending.  The owner
        re-runs the bridge to read the error; without this, each attempt copied
        the whole live world again -- measured at ten copies for ten runs."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            store.ensure_account("panya")
            later = self._migrations_plus(tmp, 901, "SELECT bad_function_that_does_not_exist();\n")
            broken = SQLiteStore(store.path, later)
            root = Path(tmp) / "backups"

            first = None
            for _ in range(5):
                with self.assertRaises(sqlite3.OperationalError):
                    broken.migrate_with_backup(backups_root=root)
                produced = sorted(p for p in root.iterdir() if p.is_dir())
                if first is None:
                    first = produced[0]
                self.assertEqual([first], produced)

    def test_a_changed_database_gets_its_own_new_snapshot(self):
        """The reuse above must key on the bytes, not on the path: once the
        world moves, the next boot's snapshot is a different one."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = Path(tmp) / "backups"
            first = persistence_backup.snapshot_database(store.path, root)
            again = persistence_backup.snapshot_database(store.path, root)
            self.assertEqual(first, again)

            store.ensure_account("someone_new")
            third = persistence_backup.snapshot_database(store.path, root)
            self.assertNotEqual(first.parent, third.parent)
            copy = sqlite3.connect(str(third))
            try:
                names = [r[0] for r in copy.execute("SELECT login_name FROM accounts")]
            finally:
                copy.close()
            self.assertIn("someone_new", names)

    def test_a_damaged_old_snapshot_is_not_handed_back_as_a_backup(self):
        """pf-adversary, round 1, defect 4 -- the worst one found.

        Reuse used to be gated on ``candidate.is_file()`` alone, so a snapshot
        truncated since the day it was made (bad sector, interrupted copy,
        0-byte artifact of a full disk) was handed straight back to a boot,
        which then migrated the owner's live rows believing it was protected,
        while the manifest beside the dead file still said
        ``"integrity_check": "ok"``.  A backup nobody has opened is a claim,
        and that has to hold on the day it is NEEDED, not only the day it was
        made."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = Path(tmp) / "backups"
            first = persistence_backup.snapshot_database(store.path, root)
            self.assertEqual(first, persistence_backup.snapshot_database(store.path, root))

            first.write_bytes(b"")  # the snapshot rots where it lies

            second = persistence_backup.snapshot_database(store.path, root)
            self.assertNotEqual(first, second)
            self.assertTrue(first.exists(), "a damaged snapshot is still never deleted")
            copy = sqlite3.connect(str(second))
            try:
                copy.execute("SELECT version FROM schema_migrations").fetchall()
            finally:
                copy.close()

    def test_a_manifest_cannot_point_the_reuse_gate_at_another_file(self):
        """The snapshot's name is read off a file on disk.  A manifest saying
        ``../../pirateforce.sqlite3`` must not be able to hand the LIVE
        database back as its own backup."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = Path(tmp) / "backups"
            first = persistence_backup.snapshot_database(store.path, root)

            # A byte-identical decoy OUTSIDE the backups root, so that the
            # re-verification in _snapshot_is_still_good would happily accept
            # it -- the ONLY thing standing between the boot and a "backup"
            # somewhere nobody manages is the name check itself.
            escape = Path(tmp) / "escape"
            escape.mkdir()
            decoy = escape / first.name
            decoy.write_bytes(first.read_bytes())

            manifest_path = first.parent / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["snapshot_database"] = "../../escape/" + first.name
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            second = persistence_backup.snapshot_database(store.path, root)
            self.assertNotEqual(decoy.resolve(), second.resolve())
            self.assertNotEqual(Path(store.path).resolve(), second.resolve())
            self.assertEqual(root.resolve(), second.parent.parent.resolve())

    def test_a_database_not_yet_in_wal_mode_is_snapshotted(self):
        """pf-adversary, round 1, defect 2: ``SQLiteStore.connect`` runs
        ``PRAGMA journal_mode=WAL`` unconditionally (``store.py:36``), so
        merely opening a rollback-journal database rewrites its header.  A
        plain-file restore, a ``.dump``/``.restore`` round trip or a copy from
        a third-party tool arrives in exactly that state with a complete
        ledger, and used to be migrated with no snapshot at all."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            db = sqlite3.connect(str(store.path))
            try:
                db.execute("PRAGMA journal_mode=DELETE")
                db.commit()
            finally:
                db.close()

            self.assertTrue(persistence_backup.journal_mode_rewrite_pending(store.path))
            self.assertEqual([], persistence_backup.pending_versions(store.path, MIGRATIONS))
            take, reason = persistence_backup.should_snapshot(store.path, MIGRATIONS)
            self.assertTrue(take, reason)
            self.assertIn("journal_mode", reason)
            self.assertIsNotNone(store.migrate_with_backup())

    def test_journal_mode_rewrite_pending_is_false_for_a_wal_database(self):
        """The guard must not make every ordinary boot snapshot."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            self.assertFalse(persistence_backup.journal_mode_rewrite_pending(store.path))
            self.assertIsNone(store.migrate_with_backup())

    def test_a_locked_database_fails_in_bounded_time_instead_of_hanging(self):
        """pf-adversary, round 1, defect 8B.

        ``sqlite3.Connection.backup`` retries ``SQLITE_BUSY`` on a 0.25s sleep
        with NO deadline and ignores ``busy_timeout``, so without the bounded
        read probe in ``_copy_consistent`` a second boot against a running
        bridge blocks for as long as the other process holds the lock -- with
        no log line, no progress callback and no timeout, the bridge simply
        appears frozen at startup.  Measured: with the probe removed the copy
        waited out a 20-second lock and then succeeded; with it, the boot fails
        in about five seconds and says why."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            path = Path(store.path)
            db = sqlite3.connect(str(path))
            try:
                db.execute("PRAGMA journal_mode=DELETE")
                db.commit()
            finally:
                db.close()

            ready = Path(tmp) / "locked.flag"
            script = (
                "import sqlite3, time, pathlib\n"
                "db = sqlite3.connect(%r)\n"
                "db.execute('PRAGMA journal_mode=DELETE')\n"
                "db.execute('BEGIN EXCLUSIVE')\n"
                "db.execute('CREATE TABLE holding_the_lock(id INTEGER)')\n"
                "pathlib.Path(%r).write_text('x')\n"
                "time.sleep(30)\n" % (str(path), str(ready))
            )
            holder = subprocess.Popen([sys.executable, "-c", script])
            try:
                deadline = time.monotonic() + 20
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(ready.exists(), "precondition: the lock was taken")

                started = time.monotonic()
                with self.assertRaises(persistence_backup.BackupError) as caught:
                    persistence_backup.snapshot_database(path, Path(tmp) / "backups")
                elapsed = time.monotonic() - started
            finally:
                holder.kill()
                holder.wait()
            self.assertIn("locked", str(caught.exception).lower())
            self.assertLess(
                elapsed, 15,
                "a locked database must fail in bounded time, not wait out the lock",
            )

    def test_the_free_space_refusal_names_what_is_safe_to_delete(self):
        """pf-adversary, round 1, defect 3: this module never prunes, so
        enough failed boots push the free-space check under its threshold and
        the server refuses to start for good.  The refusal has to tell a human
        which directories are dead weight, or it is a dead end."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = Path(tmp) / "backups"
            with mock.patch.object(
                persistence_backup, "_copy_consistent", side_effect=OSError("boom")
            ):
                with self.assertRaises(persistence_backup.BackupError):
                    persistence_backup.snapshot_database(store.path, root, stamp="DEADONE")
            usage = mock.Mock(free=1)
            with mock.patch.object(persistence_backup.shutil, "disk_usage", return_value=usage):
                with self.assertRaises(persistence_backup.BackupError) as caught:
                    persistence_backup.snapshot_database(store.path, root)
            message = str(caught.exception)
            self.assertIn("SAFE TO DELETE", message)
            self.assertIn("DEADONE", message)

    def test_the_restore_hint_says_to_move_the_live_wal_aside_first(self):
        """pf-adversary, round 1, defect 5: following the old hint literally
        produced a half-restore.  A stopped server leaves a hot ``-wal`` beside
        the database; SQLite replays it onto whatever file is put there, so the
        post-snapshot rows come back and ``PRAGMA integrity_check`` still says
        ``ok``.  'The file is self-contained' is true of the FILE and false of
        the PROCEDURE, and the module only ships the procedure."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            snapshot = persistence_backup.snapshot_database(store.path, Path(tmp) / "backups")
            hint = json.loads(
                (snapshot.parent / "MANIFEST.json").read_text(encoding="utf-8")
            )["restore_hint"]
            self.assertIn(Path(store.path).name + "-wal", hint)
            self.assertIn(Path(store.path).name + "-shm", hint)
            self.assertIn("NOT OPTIONAL", hint)
            self.assertLess(
                hint.index("-wal"), hint.index(snapshot.parent.name),
                "the sidecar step must come BEFORE the copy step in the text",
            )

    def test_snapshot_refuses_to_overwrite_an_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = Path(tmp) / "backups"
            persistence_backup.snapshot_database(store.path, root, stamp="FIXED")
            store.ensure_account("moves_the_bytes")  # defeat the reuse path
            with self.assertRaises(persistence_backup.BackupError):
                persistence_backup.snapshot_database(store.path, root, stamp="FIXED")

    # ---- input safety -----------------------------------------------------

    def test_snapshot_of_a_missing_database_is_an_error_not_an_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(persistence_backup.BackupError):
                persistence_backup.snapshot_database(
                    Path(tmp) / "nothing.sqlite3", Path(tmp) / "backups"
                )

    def test_label_and_stamp_cannot_escape_the_backups_root(self):
        """pf-adversary, round 1, defect 10: ``label`` was validated and
        ``stamp`` was interpolated into the directory name unchecked."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = Path(tmp) / "backups"
            for kwargs in (
                {"stamp": "../../escaped"},
                {"stamp": ".."},
                {"label": "../x"},
                {"label": "two words"},
                {"label": ""},
                {"label": 'colon:star*'},
            ):
                with self.assertRaises(persistence_backup.BackupError, msg=kwargs):
                    persistence_backup.snapshot_database(store.path, root, **kwargs)
            self.assertFalse(root.exists())

    def test_default_backups_root_sits_beside_the_database(self):
        """Never derived from the repository root: a replay tool pointed at a
        scratch database must not be able to write into the bridge's own
        backup history."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            root = persistence_backup.default_backups_root(store.path)
            self.assertEqual(Path(store.path).resolve().parent, root.parent)
            snapshot = persistence_backup.snapshot_database(store.path)
            self.assertEqual(root, snapshot.parent.parent)

    # ---- the guarantee about the OLD method --------------------------------

    def test_plain_migrate_still_takes_no_snapshot(self):
        """LANE-DB charter: a new method is allowed, changing an existing
        one's behaviour is not.  Every caller that still says ``migrate()``
        must get exactly what it got before this round."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            store.ensure_account("panya")
            later = self._migrations_plus(
                tmp, 902, "CREATE TABLE lane_db_probe_two(id INTEGER PRIMARY KEY);\n"
            )
            SQLiteStore(store.path, later).migrate()
            self.assertFalse(
                (Path(store.path).parent / persistence_backup.DEFAULT_BACKUP_DIRNAME).exists()
            )

    def test_migration_versions_matches_the_runner_glob(self):
        """This module answers 'is anything pending?' about the same files the
        runner is about to apply -- if the two globs drifted apart, a real
        pending migration could be invisible here and get no backup."""
        self.assertEqual(
            [int(p.name[:3]) for p in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))],
            persistence_backup.migration_versions(MIGRATIONS),
        )
        self.assertTrue(persistence_backup.migration_versions(MIGRATIONS))


if __name__ == "__main__":
    unittest.main()
