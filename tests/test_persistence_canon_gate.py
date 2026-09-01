"""LANE-DB-CANON-001: the second-tier gate that tells a legitimate migration
of the owner's canonical database apart from a change nobody can account for.

WHAT THIS FILE IS THE EVIDENCE FOR.  `pf_bridge/CANON_SHA.txt` pins the
SHA-256 of the owner's canonical `state/pirateforce.sqlite3`, and two
PowerShell jobs abort when the file's hash differs
(`staged/175_round109_path_d_ci_status_gate_commit.ps1:117-123`,
`staged/TEMPLATE_teardown_generic.ps1:414-436`).  That gate and this lane's
charter contradict each other: `20260901_1112_COO-DECISION-amend-lane-db-
canonical-db-via-migrations.md` point 1 makes the canonical database the
DESTINATION of this lane's migrations, so the first correct migration of it
changes those bytes and looks exactly like corruption.

`20260901_1447_COO-DECISION-lane-db-m4-unblocked-canon-sha-mechanism-
approved-backuperror-handling.md` point 4 approved the three-verdict answer
(`UNCHANGED` / `EXPLAINED_BY_MIGRATION` / `UNEXPLAINED`), and
`20260901_1515_LANE-DB-REQUEST-chief-staged-canon-gate-spec-and-backuperror-
wrapper.md` section (b.1) is the caller contract this file grades: exit `0`,
exit `20` plus a `NEW_SHA=` line to rotate to, exit `13` to abort, anything
else also to abort.

THE DATABASES HERE ARE REAL.  Every database is built by the real
`SQLiteStore` running the repository's real `migrations/` directory, every
snapshot is taken by the real `SQLiteStore.migrate_with_backup`, and every
corruption is a real byte written into a real SQLite page -- measured to make
`PRAGMA integrity_check` fail while leaving `schema_migrations` readable, so
that the integrity branch is proved LOAD-BEARING rather than merely present.
Nothing is hand-assembled and nothing here can reach
`state/pirateforce.sqlite3`: every path is built under
`tempfile.TemporaryDirectory()`.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable -- no frame
reaches the game client, and a player sees no difference.  Nothing here runs
against the owner's real canonical database (that is the one-off upgrade job
`20260901_1515` section (b.2) asks chief to write; this module has never run
on it).  Nothing here proves the two `staged/*.ps1` jobs call the module
correctly, because `staged/` is outside this lane's write zone and is still
wired to the direct comparison today.  And the gate answers a NARROWER
question than "only migrations changed these bytes": it proves the ledger now
records exactly this repository's migrations, that SQLite still calls the
file intact, and that the pre-change bytes are still recoverable -- a boot
that migrated AND wrote gameplay rows in the same session would still be
called EXPLAINED.  What makes that safe is the third condition, not the
first: the old bytes are on disk and re-verified before any rotation is
authorised.
"""
import contextlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_backup  # noqa: E402
from pirateforce_foundation import persistence_canon_gate as gate  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"

PROBE_SQL = "CREATE TABLE lane_db_canon_probe(id INTEGER PRIMARY KEY);\n"


def open_handles_under(directory):
    """Paths inside `directory` this process still has open, or `None` where
    that cannot be asked (no `/proc`, i.e. not Linux).

    `None` is not "clean" and is not read as clean below.  On Windows the
    question does not need asking: the operating system enforces the same
    rule by refusing the unlink, which is exactly how this defect reached the
    gate the first time.  Deliberately a local copy of the same helper in
    `tests/test_persistence_typed_attr_columns.py` rather than an import
    across test modules -- pytest's import mode makes a cross-module test
    import a property of how the suite was invoked, and this guard has to
    hold under every invocation the gate uses.
    """
    if not os.path.isdir("/proc/self/fd"):
        return None
    root = os.path.realpath(directory)
    held = set()
    for descriptor in os.listdir("/proc/self/fd"):
        try:
            target = os.readlink(os.path.join("/proc/self/fd", descriptor))
        except OSError:
            continue
        if target.startswith(root + os.sep):
            held.add(target)
    return sorted(held)


class CanonGateTestCase(unittest.TestCase):
    """Shared fixtures.  `_migrated` produces the exact situation the gate
    exists for and nothing simpler: a real database at a known sha, a real
    pre-migration snapshot of it, and the same database after a real
    migration moved it off that sha."""

    maxDiff = None

    @contextlib.contextmanager
    def _workspace(self):
        """A temp directory that FAILS the test if a handle on it outlives
        the body.

        THIS IS THE GUARD THAT COST A ROUND ALREADY.  PR #495 of this lane
        died on `pytest_subset exit=1` because a test left a sqlite
        connection open on its own temp directory: on POSIX
        `TemporaryDirectory.cleanup` unlinks the open file and says nothing,
        while on Windows the same handle makes cleanup raise
        `PermissionError: [WinError 32]` and the workflow closes the pull
        request.  Every database in this file is opened by the module under
        test, so a leak here would be the module's, not the test's -- which
        is precisely the leak worth catching.

        Measured before it was written: all tests in this file already leave
        zero handles behind.  It is here so that stays true.
        """
        with tempfile.TemporaryDirectory() as name:
            yield Path(name)
            held = open_handles_under(name)
            if held is not None:  # Linux: ask directly
                self.assertEqual(
                    held,
                    [],
                    "a handle on the temp directory outlives this test.  On "
                    "Windows TemporaryDirectory.cleanup raises WinError 32 "
                    "here and the gate goes red.",
                )

    def _migrations_plus(self, tmp, version=900, sql=PROBE_SQL, name="later"):
        """The real migrations directory plus one more file -- the only way
        to give a real, fully migrated database something genuinely pending
        (copied from `tests/test_persistence_premigration_backup.py`)."""
        later = Path(tmp) / ("migrations_%s" % name)
        later.mkdir()
        for path in sorted(MIGRATIONS.glob(persistence_backup.MIGRATION_GLOB)):
            (later / path.name).write_bytes(path.read_bytes())
        (later / ("%03d_lane_db_canon_probe.sql" % version)).write_text(
            sql, encoding="utf-8"
        )
        return later

    def _migrated(self, tmp):
        """(db path, later migrations dir, sha before, sha after).

        The sha "before" is the value `CANON_SHA.txt` would hold on the
        owner's machine; the sha "after" is what the next `Get-FileHash`
        would report once the boot had migrated.
        """
        db = Path(tmp) / "state" / "pirateforce.sqlite3"
        db.parent.mkdir(parents=True, exist_ok=True)
        SQLiteStore(db, MIGRATIONS).migrate()
        before = persistence_backup._sha256_file(db)
        later = self._migrations_plus(tmp)
        snapshot = SQLiteStore(db, later).migrate_with_backup()
        self.assertIsNotNone(
            snapshot, "the probe migration should have earned a snapshot"
        )
        after = persistence_backup._sha256_file(db)
        self.assertNotEqual(before, after, "the migration did not change the file")
        return db, later, before, after

    def _corrupt_page(self, db, mutate):
        """Write `mutate`'s damage into the file's LAST page.

        Both mutations used below were measured against this repository's own
        schema: they make `PRAGMA integrity_check` fail while leaving
        `schema_migrations` readable, which is the only way to prove the
        integrity condition is what refuses the rotation rather than the
        ledger condition doing it first.
        """
        # Give the file enough pages that the last one holds row data rather
        # than schema, so the ledger survives the damage.
        connection = sqlite3.connect(str(db))
        for index in range(3000):
            connection.execute(
                "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                ("canon_probe_%d" % index, "2026-09-01T00:00:00Z"),
            )
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.close()
        data = bytearray(db.read_bytes())
        page_size = int.from_bytes(data[16:18], "big")
        self.assertEqual(page_size, 4096, "unexpected page size for this schema")
        start = (len(data) // page_size - 1) * page_size
        mutate(data, start)
        db.write_bytes(bytes(data))


class UnchangedTests(CanonGateTestCase):
    def test_a_database_that_still_matches_is_unchanged(self):
        with self._workspace() as tmp:
            db = Path(tmp) / "state" / "pirateforce.sqlite3"
            db.parent.mkdir(parents=True)
            SQLiteStore(db, MIGRATIONS).migrate()
            sha = persistence_backup._sha256_file(db)
            verdict = gate.evaluate(db, MIGRATIONS, sha)
        self.assertEqual(verdict.result, gate.RESULT_UNCHANGED)
        self.assertEqual(verdict.exit_code, 0)
        self.assertIsNone(verdict.new_sha)

    def test_the_uppercase_form_canon_sha_txt_actually_holds_is_accepted(self):
        """`pf_bridge/CANON_SHA.txt` is written by PowerShell's
        `Get-FileHash`, which produces UPPERCASE hex.  A gate that compared
        case-sensitively would call the owner's untouched database
        UNEXPLAINED on its very first run."""
        with self._workspace() as tmp:
            db = Path(tmp) / "state" / "pirateforce.sqlite3"
            db.parent.mkdir(parents=True)
            SQLiteStore(db, MIGRATIONS).migrate()
            sha = persistence_backup._sha256_file(db)
            self.assertEqual(
                gate.evaluate(db, MIGRATIONS, sha.upper()).result,
                gate.RESULT_UNCHANGED,
            )
            self.assertEqual(
                gate.evaluate(db, MIGRATIONS, "  %s\n" % sha.upper()).result,
                gate.RESULT_UNCHANGED,
            )


class HotWalIsSaidOutLoudTests(CanonGateTestCase):
    """`CANON_SHA.txt` fingerprints the MAIN FILE only, because that is what
    `Get-FileHash` hashes.  A committed transaction can live entirely in
    `-wal` while the main file is untouched, so an `UNCHANGED` verdict can be
    true about the file and misleading about the database.

    The verdict is deliberately NOT changed -- being stricter than the jobs
    this gate stands in for would abort attended rounds on a state a killed
    server leaves behind routinely.  What must not happen is that the
    difference goes unsaid.
    """

    def test_unchanged_still_says_zero_but_names_the_hot_wal(self):
        with self._workspace() as tmp:
            db = tmp / "state" / "pirateforce.sqlite3"
            db.parent.mkdir(parents=True)
            SQLiteStore(db, MIGRATIONS).migrate()
            sha = persistence_backup._sha256_file(db)
            holder = sqlite3.connect(str(db))
            try:
                holder.execute("PRAGMA journal_mode=WAL")
                holder.execute(
                    "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                    ("committed_into_the_wal", "2026-09-01T00:00:00Z"),
                )
                holder.commit()
                # The premise: the main file did NOT move, so today's direct
                # comparison would call this untouched.
                self.assertEqual(persistence_backup._sha256_file(db), sha)
                self.assertTrue(db.with_name(db.name + "-wal").stat().st_size > 0)
                verdict = gate.evaluate(db, MIGRATIONS, sha)
            finally:
                holder.close()
        self.assertEqual(verdict.exit_code, 0)
        self.assertTrue(
            any("-wal" in reason for reason in verdict.reasons), verdict.reasons
        )

    def test_a_quiet_database_does_not_get_the_warning(self):
        with self._workspace() as tmp:
            db = tmp / "state" / "pirateforce.sqlite3"
            db.parent.mkdir(parents=True)
            SQLiteStore(db, MIGRATIONS).migrate()
            verdict = gate.evaluate(
                db, MIGRATIONS, persistence_backup._sha256_file(db)
            )
        self.assertEqual(verdict.exit_code, 0)
        self.assertFalse(
            any("NOTE:" in reason for reason in verdict.reasons), verdict.reasons
        )


class ExplainedByMigrationTests(CanonGateTestCase):
    def test_a_real_migration_with_a_real_snapshot_is_explained(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            verdict = gate.evaluate(db, later, before)
            self.assertEqual(verdict.result, gate.RESULT_EXPLAINED, verdict.reasons)
            self.assertEqual(verdict.exit_code, 20)
            self.assertEqual(verdict.new_sha, after)
            self.assertIsNotNone(verdict.snapshot)
            self.assertTrue(Path(verdict.snapshot).is_file())

    def test_the_gate_does_not_touch_the_database_it_judges(self):
        """The gate runs against the owner's only copy of the world.  Its
        own inspection must leave that file byte-identical on every verdict,
        including the two that open it to read the ledger."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            for expectation, label in (
                (after, "UNCHANGED"),
                (before, "EXPLAINED"),
                ("0" * 64, "UNEXPLAINED"),
            ):
                sha_before_call = persistence_backup._sha256_file(db)
                gate.evaluate(db, later, expectation)
                self.assertEqual(
                    persistence_backup._sha256_file(db),
                    sha_before_call,
                    "the gate changed the database on the %s path" % label,
                )


class UnexplainedTests(CanonGateTestCase):
    def test_a_changed_database_with_no_snapshot_is_unexplained(self):
        """Gameplay rows written outside a migration: the ledger still
        matches and the file is intact, but nothing on disk holds the bytes
        `CANON_SHA.txt` names, so the rotation would be irreversible."""
        with self._workspace() as tmp:
            db = Path(tmp) / "state" / "pirateforce.sqlite3"
            db.parent.mkdir(parents=True)
            SQLiteStore(db, MIGRATIONS).migrate()
            before = persistence_backup._sha256_file(db)
            connection = sqlite3.connect(str(db))
            connection.execute(
                "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                ("written_by_gameplay", "2026-09-01T00:00:00Z"),
            )
            connection.commit()
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.close()
            self.assertNotEqual(before, persistence_backup._sha256_file(db))
            verdict = gate.evaluate(db, MIGRATIONS, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertEqual(verdict.exit_code, 13)
        self.assertIsNone(verdict.new_sha)
        self.assertTrue(
            any("snapshot" in reason for reason in verdict.reasons), verdict.reasons
        )

    def test_a_ledger_newer_than_this_repository_is_unexplained(self):
        """The database carries a migration this checkout does not ship --
        the condition `store.migrate` refuses with "database schema is newer
        than this server".  Pointing the gate at the ORIGINAL migrations
        directory after migrating with the extended one reproduces it
        exactly."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            verdict = gate.evaluate(db, MIGRATIONS, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("does not ship" in reason for reason in verdict.reasons),
            verdict.reasons,
        )

    def test_a_migration_on_disk_that_was_never_applied_is_unexplained(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            (later / "901_lane_db_never_applied.sql").write_text(
                "CREATE TABLE lane_db_never_applied(id INTEGER);\n", encoding="utf-8"
            )
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("has not applied" in reason for reason in verdict.reasons),
            verdict.reasons,
        )

    def test_a_migration_file_edited_after_it_was_applied_is_unexplained(self):
        """The ledger stores the SHA-256 of the file it applied
        (`store.py:82-86`), so editing an applied migration is detectable --
        and is the case where the schema in the database is NOT what reading
        `migrations/` would tell you it is."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            probe = later / "900_lane_db_canon_probe.sql"
            probe.write_text(PROBE_SQL + "-- edited after apply\n", encoding="utf-8")
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("checksum" in reason for reason in verdict.reasons), verdict.reasons
        )

    def test_a_ledger_with_no_checksum_column_value_is_unexplained(self):
        """A database mid-way through `store.migrate`'s checksum upgrade
        (`store.py:90-99`) proves nothing about which bytes were applied."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            connection = sqlite3.connect(str(db))
            connection.execute("UPDATE schema_migrations SET checksum=NULL WHERE version=1")
            connection.commit()
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.close()
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("no checksum" in reason for reason in verdict.reasons), verdict.reasons
        )

    def test_a_database_with_no_ledger_at_all_is_unexplained(self):
        with self._workspace() as tmp:
            db = Path(tmp) / "state" / "pirateforce.sqlite3"
            db.parent.mkdir(parents=True)
            connection = sqlite3.connect(str(db))
            connection.execute("CREATE TABLE unrelated(id INTEGER)")
            connection.commit()
            connection.close()
            verdict = gate.evaluate(db, MIGRATIONS, "a" * 64)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("schema_migrations" in reason for reason in verdict.reasons),
            verdict.reasons,
        )

    def test_a_missing_database_is_unexplained_not_a_crash(self):
        with self._workspace() as tmp:
            verdict = gate.evaluate(
                Path(tmp) / "not_here.sqlite3", MIGRATIONS, "b" * 64
            )
        self.assertEqual(verdict.exit_code, 13)

    def test_a_missing_migrations_directory_is_unexplained(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            verdict = gate.evaluate(db, Path(tmp) / "no_such_dir", before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)

    def test_a_garbage_expectation_can_never_be_explained(self):
        """A truncated, empty or hand-edited `CANON_SHA.txt`.  An
        expectation nobody can read must not match anything and must not be
        explainable -- otherwise deleting the file would UNLOCK the gate."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            for spelling in ("", "   ", "not-a-sha", before[:63], before + "0", None):
                verdict = gate.evaluate(db, later, spelling)
                self.assertEqual(verdict.exit_code, 13, repr(spelling))
                self.assertIsNone(verdict.new_sha, repr(spelling))


class IntegrityIsLoadBearingTests(CanonGateTestCase):
    """The two mutations below leave the ledger readable and matching, and
    leave a valid snapshot in place, so the ONLY condition that can refuse
    the rotation is `PRAGMA integrity_check`.  Without them the integrity
    branch could be deleted with every other test still green."""

    def test_a_corrupt_page_header_that_integrity_check_reports_is_unexplained(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            self._corrupt_page(
                db,
                lambda data, start: data.__setitem__(
                    slice(start + 5, start + 7), (10).to_bytes(2, "big")
                ),
            )
            ok, reasons = gate.ledger_matches_migrations(db, later)
            self.assertTrue(ok, reasons)
            snapshot, _ = gate.recoverable_snapshot(db, before)
            self.assertIsNotNone(snapshot)
            self.assertFalse(gate.integrity_ok(db)[0])
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("integrity_check" in reason for reason in verdict.reasons),
            verdict.reasons,
        )

    def test_damage_that_makes_integrity_check_itself_raise_is_unexplained(self):
        """`PRAGMA integrity_check` does not always return a verdict: damage
        bad enough makes SQLite raise instead.  Same outcome required."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            self._corrupt_page(
                db,
                lambda data, start: data.__setitem__(
                    slice(start + 3, start + 5), (999).to_bytes(2, "big")
                ),
            )
            ok, reasons = gate.ledger_matches_migrations(db, later)
            self.assertTrue(ok, reasons)
            self.assertFalse(gate.integrity_ok(db)[0])
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("integrity_check" in reason for reason in verdict.reasons),
            verdict.reasons,
        )


class SnapshotIsLoadBearingTests(CanonGateTestCase):
    """Everything the gate refuses to accept as "the pre-change bytes are
    still recoverable".  Each of these leaves the ledger matching and the
    database intact, so only the snapshot condition can refuse."""

    def _sole_snapshot(self, db):
        root = persistence_backup.default_backups_root(db)
        directories = [
            path
            for path in root.iterdir()
            if path.is_dir() and not path.name.endswith(
                persistence_backup.INCOMPLETE_SUFFIX
            )
        ]
        self.assertEqual(len(directories), 1, directories)
        return directories[0]

    def test_a_truncated_snapshot_is_not_a_backup_any_more(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            directory = self._sole_snapshot(db)
            manifest = json.loads((directory / "MANIFEST.json").read_text("utf-8"))
            (directory / manifest["snapshot_database"]).write_bytes(b"")
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("not a backup" in reason for reason in verdict.reasons),
            verdict.reasons,
        )

    def test_a_snapshot_of_a_different_database_does_not_count(self):
        """A manifest can name any source.  Two databases that once held the
        same bytes are still two databases, and only one of them is the one
        being rotated away."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            directory = self._sole_snapshot(db)
            manifest_path = directory / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            manifest["source_database"] = str(Path(tmp) / "state" / "elsewhere.sqlite3")
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("was taken from" in reason for reason in verdict.reasons),
            verdict.reasons,
        )

    def test_a_manifest_cannot_offer_the_live_database_as_its_own_backup(self):
        """`snapshot_database` is a name read off disk.  A manifest whose
        name escapes its own directory must be refused, not joined."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            directory = self._sole_snapshot(db)
            manifest_path = directory / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            manifest["snapshot_database"] = "../../state/pirateforce.sqlite3"
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            snapshot, reasons = gate.recoverable_snapshot(db, before)
            self.assertIsNone(snapshot, snapshot)
            self.assertEqual(gate.evaluate(db, later, before).exit_code, 13)

    def test_an_unfinished_snapshot_is_not_a_backup(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            directory = self._sole_snapshot(db)
            directory.rename(
                directory.with_name(
                    directory.name + persistence_backup.INCOMPLETE_SUFFIX
                )
            )
            self.assertEqual(gate.evaluate(db, later, before).exit_code, 13)

    def test_a_directory_with_no_manifest_is_not_a_backup(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            (self._sole_snapshot(db) / "MANIFEST.json").unlink()
            self.assertEqual(gate.evaluate(db, later, before).exit_code, 13)

    def test_an_unreadable_manifest_is_not_a_backup(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            (self._sole_snapshot(db) / "MANIFEST.json").write_text(
                "{ this is not json", encoding="utf-8"
            )
            self.assertEqual(gate.evaluate(db, later, before).exit_code, 13)

    def test_no_backups_directory_at_all_is_unexplained(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            verdict = gate.evaluate(
                db, later, before, backups_root=Path(tmp) / "no_such_root"
            )
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)


class NormaliseShaTests(unittest.TestCase):
    """`normalise_sha` is graded directly, not only through the verdict.

    WHY, measured.  Deleting its length check left all 28 verdict tests green:
    a 63- or 65-character string can never equal a 64-character digest, so the
    verdict came out `UNEXPLAINED` either way and the check looked
    load-bearing while proving nothing.  A guard nothing grades is a guard
    that can be deleted by a future edit in silence -- and this one is the
    reason a truncated or hand-edited `CANON_SHA.txt` is REFUSED rather than
    quietly carried into a comparison.
    """

    def test_only_a_real_sha256_survives(self):
        digest = "a1b2c3d4" * 8
        self.assertEqual(len(digest), 64)
        self.assertEqual(gate.normalise_sha(digest), digest)
        self.assertEqual(gate.normalise_sha(digest.upper()), digest)
        self.assertEqual(gate.normalise_sha("  %s\n" % digest), digest)

    def test_everything_that_is_not_a_sha256_becomes_none(self):
        digest = "a1b2c3d4" * 8
        for spelling in (
            "",
            "   ",
            "not-a-sha",
            digest[:63],          # one short
            digest + "0",         # one long
            digest[:63] + "g",    # right length, not hex
            None,
            42,
            b"a" * 64,            # bytes, not str
            ["a" * 64],
        ):
            self.assertIsNone(gate.normalise_sha(spelling), repr(spelling))


class ManifestsAreDataNotInstructionsTests(CanonGateTestCase):
    """A `MANIFEST.json` is a file on disk that this gate reads to decide
    whether the owner's only copy of the world may lose its last recorded
    sha.  Everything in it is therefore treated as a claim to be checked, and
    these are the checks that a verdict test alone did NOT grade."""

    def _sole_snapshot(self, db):
        root = persistence_backup.default_backups_root(db)
        directories = [
            path
            for path in root.iterdir()
            if path.is_dir()
            and not path.name.endswith(persistence_backup.INCOMPLETE_SUFFIX)
        ]
        self.assertEqual(len(directories), 1, directories)
        return directories[0]

    def test_a_snapshot_file_outside_its_own_directory_is_refused(self):
        """THE ONE THAT PRODUCES A FALSE `EXPLAINED` IF THE CHECK IS REMOVED.

        The earlier version of this file pointed `snapshot_database` at
        `../../state/pirateforce.sqlite3` and asserted exit 13 -- but deleting
        the path check kept that test green, because the live database does
        not match the manifest's recorded verification sha and
        `_snapshot_is_still_good` rejected it for an unrelated reason.  The
        test passed for the wrong reason.

        Here the escaping name points at a BYTE-IDENTICAL copy of the real
        snapshot, so every later check succeeds and only the path rule can
        refuse.  Measured: with the rule removed this returns exit 20 --
        authorising a rotation on the strength of a "backup" the manifest
        placed outside the directory that vouches for it.
        """
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            directory = self._sole_snapshot(db)
            manifest_path = directory / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            real = directory / manifest["snapshot_database"]
            stray = directory.parent / "stray_copy.sqlite3"
            stray.write_bytes(real.read_bytes())
            manifest["snapshot_database"] = "../%s" % stray.name
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            snapshot, reasons = gate.recoverable_snapshot(db, before)
            self.assertIsNone(snapshot, "a name that escapes its directory was accepted")
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED, verdict.reasons)
        self.assertNotEqual(verdict.exit_code, 20)

    def test_a_manifest_that_is_valid_json_but_not_an_object_is_refused(self):
        """`json.loads` succeeds on `[]` and on `"x"`.  Without the type
        check the next line raises `AttributeError`, which leaves the gate
        exiting 70 on a merely damaged manifest instead of answering 13."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            for payload in ("[]", '"a string"', "17", "null"):
                (self._sole_snapshot(db) / "MANIFEST.json").write_text(
                    payload, encoding="utf-8"
                )
                verdict = gate.evaluate(db, later, before)
                self.assertEqual(verdict.exit_code, 13, payload)

    def test_the_public_lookup_accepts_the_uppercase_form_canon_sha_txt_holds(self):
        """MEASURED DEFECT, fixed in the same round it was found.  This
        function is public and the canonical-upgrade job is expected to hand
        it the `CANON_SHA.txt` value verbatim -- which PowerShell writes in
        UPPERCASE.  Before the fix it answered "no snapshot holds those
        bytes" for a snapshot sitting right there."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            lower, _ = gate.recoverable_snapshot(db, before)
            upper, _ = gate.recoverable_snapshot(db, before.upper())
            self.assertIsNotNone(lower)
            self.assertEqual(lower, upper)
            self.assertIsNone(gate.recoverable_snapshot(db, "not-a-sha")[0])


class MigrationsDirectoryIsGradedTests(CanonGateTestCase):
    """Two refusals whose VERDICT is `UNEXPLAINED` either way -- what these
    grade is that the gate says the true thing about WHY, because the reason
    line is what a human reads at 2am before deciding whether to disable the
    gate."""

    def test_duplicate_migration_versions_are_named_as_such(self):
        """`store.migrate` raises "duplicate migration version" on this and
        will not run at all, so a gate that authorised a rotation against
        such a directory would be authorising it against a schema no boot
        can produce."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            (later / "900_lane_db_second_file_same_number.sql").write_text(
                "CREATE TABLE lane_db_dupe(id INTEGER);\n", encoding="utf-8"
            )
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("duplicate" in reason for reason in verdict.reasons), verdict.reasons
        )

    def test_an_empty_migrations_directory_is_named_as_such(self):
        """Without its own check this reports "the database records
        migration(s) this repository does not ship", which sends the reader
        hunting for a schema problem that does not exist -- the directory is
        simply the wrong one."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            empty = Path(tmp) / "migrations_empty"
            empty.mkdir()
            verdict = gate.evaluate(db, empty, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED)
        self.assertTrue(
            any("no migration files" in reason for reason in verdict.reasons),
            verdict.reasons,
        )


class TheSnapshotMustBelongToTheChangeUnderJudgementTests(CanonGateTestCase):
    """pf-adversary D1 and D2, both measured against the first version of this
    module, both CRITICAL, both about the same hole: the gate asked "does a
    snapshot naming the pin exist" and never asked whether that snapshot had
    anything to do with the change it was blessing.

    A false `EXPLAINED` is the worst thing this module can produce -- exit 20
    authorises throwing away the last written record of what the owner's only
    copy of the world used to be.
    """

    def _sole_snapshot(self, db):
        root = persistence_backup.default_backups_root(db)
        directories = [
            path
            for path in root.iterdir()
            if path.is_dir()
            and not path.name.endswith(persistence_backup.INCOMPLETE_SUFFIX)
        ]
        self.assertEqual(len(directories), 1, directories)
        return directories[0]

    def test_the_fingerprint_must_name_the_pin_at_all(self):
        """D2: deleting the ONE line that binds a snapshot to `CANON_SHA.txt`
        left 37/37 tests green.  With that line gone any snapshot of this
        database counts, and the whole third condition becomes decoration."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            directory = self._sole_snapshot(db)
            manifest_path = directory / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            # A snapshot that is valid, of this database, and still
            # re-verifies -- but of a moment the pin does not describe.
            manifest["source_fingerprint"]["sha256"] = "b" * 64
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED, verdict.reasons)
        self.assertEqual(verdict.exit_code, 13)

    def test_rows_deleted_after_the_migration_are_not_explained_by_it(self):
        """D1, MEASURED ON THE FIRST VERSION: 200 accounts deleted after a
        correct migration still produced `EXPLAINED_BY_MIGRATION exit 20`,
        with a REASON line asserting the change was explained by a migration
        that had nothing to do with it.

        The rule that catches it is the ledger binding: the ledger a database
        carries now must be exactly the ledger the boot that took the
        surviving snapshot set out to produce.  Deleting rows leaves the
        ledger alone -- so this test is honest about what it grades: it is
        the SECOND migration, taken from a boot whose snapshot is gone, that
        the binding refuses.  The narrower residual (writes inside the same
        boot) is stated in `_schema_came_from_that_boot` and was raised with
        COO; it is not closed here and this test does not pretend it is.
        """
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            self.assertEqual(gate.evaluate(db, later, before).exit_code, 20)

            # A second boot applies a second migration.  Its own snapshot is
            # then removed -- exactly the state a pruned or hand-cleaned
            # backup tree leaves behind -- so the only snapshot left is the
            # STALE one, which still names the pin.
            later_still = self._migrations_plus(
                tmp,
                version=901,
                sql="CREATE TABLE lane_db_second_probe(id INTEGER PRIMARY KEY);\n",
                name="second",
            )
            for path in sorted(later.glob(persistence_backup.MIGRATION_GLOB)):
                (later_still / path.name).write_bytes(path.read_bytes())
            SQLiteStore(db, later_still).migrate()

            verdict = gate.evaluate(db, later_still, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED, verdict.reasons)
        self.assertTrue(
            any("that boot" in reason for reason in verdict.reasons), verdict.reasons
        )

    def test_a_newer_snapshot_that_does_not_carry_the_pin_stops_the_search(self):
        """The pin being more than one boot behind is itself the answer: what
        happened across those boots cannot be attributed to a migration."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            root = persistence_backup.default_backups_root(db)
            original = self._sole_snapshot(db)
            newer = root / ("2099%s" % original.name[4:])
            shutil.copytree(original, newer)
            manifest_path = newer / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            manifest["source_fingerprint"]["sha256"] = "c" * 64
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED, verdict.reasons)
        self.assertTrue(
            any("more than one boot behind" in reason for reason in verdict.reasons),
            verdict.reasons,
        )


class ASnapshotMustLiveInsideTheSnapshotTreeTests(CanonGateTestCase):
    """pf-adversary D10, measured: a symlinked snapshot directory pointing at
    the state directory, plus a `MANIFEST.json` beside the live database,
    made the gate offer THE LIVE DATABASE as its own backup -- and
    `persistence_backup._verify_snapshot`, following that link, unlinked the
    live `-wal` and destroyed 50 committed transactions.

    A name-based rule cannot see a link.  The candidate is resolved and
    required to be inside the snapshot tree and not to be the database under
    judgement.
    """

    def test_a_link_out_of_the_backup_tree_is_refused(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            root = persistence_backup.default_backups_root(db)
            escape = root / "2099_premigration_escape"
            escape.symlink_to(db.parent, target_is_directory=True)
            (db.parent / "MANIFEST.json").write_text(
                json.dumps(
                    {
                        "source_database": str(db.resolve()),
                        "source_fingerprint": {"sha256": before},
                        "snapshot_database": db.name,
                        "pending_versions": [],
                        "verification": {
                            "sha256": persistence_backup._sha256_file(db),
                            "bytes": db.stat().st_size,
                            "integrity_check": "ok",
                            "schema_migrations_in_snapshot": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            snapshot, reasons = gate.recoverable_snapshot(db, before)
            # RESOLVED, not as spelled.  Comparing the paths as given is the
            # tautology this test was written wrong the first time: the
            # candidate reads `db_backups/2099_.../pirateforce.sqlite3`,
            # which is textually unlike the live path and resolves to exactly
            # it.  Measured with the containment rule removed, the line below
            # is the one that fires.
            if snapshot is not None:
                self.assertNotEqual(
                    Path(snapshot).resolve(),
                    db.resolve(),
                    "the gate offered the live database as its own backup",
                )
            # The REAL snapshot is still there and still valid, so the
            # correct answer is that one -- what must never happen is the
            # link being taken instead.  (It sorts first: `2099...` beats the
            # real `2026...` under newest-first iteration, which is exactly
            # why the rule has to reject rather than merely deprioritise.)
            self.assertIsNotNone(snapshot, reasons)
            self.assertTrue(db.is_file(), "the live database is gone")


class TheRotationValueDescribesTheFileAsItIsNowTests(CanonGateTestCase):
    """pf-adversary D4, measured 40/40 under a concurrent writer: the sha was
    read once, three checks then re-opened the file, and the ORIGINAL digest
    was handed back as the value to write into `CANON_SHA.txt`.  Rotating a
    stale digest leaves every ps1 guard aborting forever against a database
    nobody touched."""

    def test_a_write_during_the_judgement_withdraws_the_rotation_value(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            real_integrity = gate.integrity_ok

            def write_then_check(path):
                # A writer that commits between the hash and the verdict --
                # the race, made deterministic.
                connection = sqlite3.connect(str(path))
                try:
                    connection.execute(
                        "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                        ("raced_in", "2026-09-01T00:00:00Z"),
                    )
                    connection.commit()
                    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                finally:
                    connection.close()
                return real_integrity(path)

            with mock.patch.object(gate, "integrity_ok", write_then_check):
                verdict = gate.evaluate(db, later, before)
        self.assertEqual(verdict.result, gate.RESULT_UNEXPLAINED, verdict.reasons)
        self.assertIsNone(verdict.new_sha)
        self.assertTrue(
            any("WHILE this gate was judging" in reason for reason in verdict.reasons),
            verdict.reasons,
        )


class NothingTheCallerSuppliesIsEverEchoedTests(CanonGateTestCase):
    """pf-adversary D3 and D7, both measured.

    D3: the reason line for an unreadable `--expect-sha` interpolated the
    caller's own string with `%r`, so `--expect-sha "NEW_SHA=DEADBEEF..."`
    put the token `NEW_SHA` into the output of an EXIT 13 run -- breaking
    this module's loudest invariant and enough to poison a caller that
    rotates by grepping for that token.

    D7: the same echo carried arbitrary non-ASCII into a `print` that, under
    the bridge's cp874 console, raised `UnicodeEncodeError` -- exit 1, empty
    stdout, no `RESULT=` line at all, on the one path whose whole job is to
    tell a human what is wrong.
    """

    def test_a_hostile_expectation_cannot_smuggle_the_rotation_token_out(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            for spelling in (
                "NEW_SHA=" + "D" * 56,
                "NEW_SHA=%s" % after.upper(),
                "\nNEW_SHA=%s\n" % after.upper(),
            ):
                verdict = gate.evaluate(db, later, spelling)
                rendered = gate.render(verdict, db)
                self.assertEqual(verdict.exit_code, 13, spelling)
                self.assertNotIn("NEW_SHA", rendered, rendered)

    def test_every_reason_line_survives_the_bridge_console_codec(self):
        """cp874 is the bridge's console codec.  Every byte this module can
        print must survive it, or the operator gets a traceback instead of
        the reason."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            for expectation in (
                before,                      # EXPLAINED
                after,                       # UNCHANGED
                "\u4e2d\u6587" * 20,         # not a sha, and not encodable
                b"bytes are not text",       # not even a string
            ):
                rendered = gate.render(gate.evaluate(db, later, expectation), db)
                rendered.encode("cp874")     # raises if this module ever echoes
                rendered.encode("ascii")


class NewShaIsPrintedOnlyWhenRotationIsAuthorisedTests(CanonGateTestCase):
    """The whole gate collapses if a caller can grep a rotation candidate out
    of a run that refused to authorise one.  `render` is the only place a sha
    reaches a caller, so the invariant is asserted there and again through the
    real command line below."""

    def test_only_the_explained_verdict_renders_a_new_sha_line(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            explained = gate.evaluate(db, later, before)
            unchanged = gate.evaluate(db, later, after)
            unexplained = gate.evaluate(db, MIGRATIONS, before)

            self.assertIn("NEW_SHA=", gate.render(explained, db))
            for verdict in (unchanged, unexplained):
                rendered = gate.render(verdict, db)
                self.assertNotIn("NEW_SHA", rendered, rendered)
                self.assertIn("RESULT=", rendered)

    def test_the_rendered_sha_is_uppercase_like_get_filehash(self):
        """`CANON_SHA.txt` is compared with `-cne` -- the CASE-SENSITIVE
        operator -- in `staged/175_round109_path_d_ci_status_gate_commit
        .ps1:123`.  A lowercase digest rotated into that file would abort the
        very next run against a database that had not changed."""
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)
            rendered = gate.render(gate.evaluate(db, later, before), db)
            self.assertIn("NEW_SHA=%s" % after.upper(), rendered)
            self.assertNotIn(after, rendered)


class CommandLineTests(CanonGateTestCase):
    """The exit code IS the answer, so it is graded through a real process,
    not through `main()` in-process: the caller is PowerShell reading
    `$LASTEXITCODE`."""

    def _run(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "pirateforce_foundation.persistence_canon_gate"]
            + [str(argument) for argument in arguments],
            cwd=str(ROOT),
            env=dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONIOENCODING="utf-8"),
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=300,
        )

    def test_the_three_documented_exit_codes_come_out_of_a_real_process(self):
        with self._workspace() as tmp:
            db, later, before, after = self._migrated(tmp)

            unchanged = self._run(
                "--db", db, "--migrations", later, "--expect-sha", after.upper()
            )
            self.assertEqual(unchanged.returncode, 0, unchanged.stderr)
            self.assertIn(b"RESULT=UNCHANGED", unchanged.stdout)
            self.assertNotIn(b"NEW_SHA", unchanged.stdout + unchanged.stderr)

            explained = self._run(
                "--db", db, "--migrations", later, "--expect-sha", before.upper()
            )
            self.assertEqual(explained.returncode, 20, explained.stderr)
            self.assertIn(b"RESULT=EXPLAINED_BY_MIGRATION", explained.stdout)
            self.assertIn(
                ("NEW_SHA=%s" % after.upper()).encode("ascii"), explained.stdout
            )

            unexplained = self._run(
                "--db", db, "--migrations", MIGRATIONS, "--expect-sha", before.upper()
            )
            self.assertEqual(unexplained.returncode, 13, unexplained.stderr)
            self.assertIn(b"RESULT=UNEXPLAINED", unexplained.stdout)
            self.assertNotIn(b"NEW_SHA", unexplained.stdout + unexplained.stderr)
            self.assertIn(b"REASON=", unexplained.stdout)

    def test_a_missing_argument_exits_with_something_a_caller_must_abort_on(self):
        result = self._run("--db", "nowhere")
        self.assertNotIn(
            result.returncode,
            (0, gate.EXIT_EXPLAINED),
            "argparse must not land on a code that means 'carry on' or 'rotate'",
        )

    def test_an_unexpected_failure_never_reports_as_unchanged(self):
        """The spec's last row: any other exit code means ABORT.  That is
        only safe if a module that breaks cannot land on 0 or 20."""
        with mock.patch.object(gate, "evaluate", side_effect=RuntimeError("boom")):
            code = gate.main(
                ["--db", "x", "--migrations", "y", "--expect-sha", "c" * 64]
            )
        self.assertEqual(code, gate.EXIT_MODULE_ERROR)
        self.assertNotIn(code, (0, gate.EXIT_EXPLAINED, gate.EXIT_UNEXPLAINED))


class ExitCodesMatchTheCallerContractTests(unittest.TestCase):
    def test_thirteen_is_still_the_number_the_ps1_jobs_already_abort_with(self):
        """`staged/175_round109_path_d_ci_status_gate_commit.ps1:123` exits
        13 today when the sha differs.  Keeping the number identical is what
        lets a job that has NOT been rewired yet behave correctly if it ever
        reaches this module."""
        self.assertEqual(gate.EXIT_UNEXPLAINED, 13)
        self.assertEqual(gate.EXIT_EXPLAINED, 20)
        self.assertEqual(gate.EXIT_UNCHANGED, 0)
        self.assertNotIn(
            gate.EXIT_MODULE_ERROR,
            (gate.EXIT_UNCHANGED, gate.EXIT_EXPLAINED, gate.EXIT_UNEXPLAINED),
        )


if __name__ == "__main__":
    unittest.main()
