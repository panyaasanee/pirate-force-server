"""LANE-DB-CANON-001: the second-storey gate that tells a legitimate migration
apart from an unexplained change to the owner's canonical database.

WHAT THIS FILE IS THE EVIDENCE FOR.  ``COO-DECISION 20260901_1241`` ruled that
``pf_bridge/CANON_SHA.txt`` must become rotatable, because
``COO-DECISION 20260901_1112`` point 1 had just made the canonical database the
DESTINATION of this lane's migrations -- so the two bridge jobs that compare
its sha256 against that file (``staged/175_round109_path_d_ci_status_gate_
commit.ps1:117-123``, ``staged/TEMPLATE_teardown_generic.ps1:414-436``) now
raise the same red for a correct boot as for damage.
``COO-DECISION 20260901_1447`` point 4 approved the design, and the calling
contract these tests pin is the one already sent to chief in
``pf_bridge/notes_to_chief/20260901_1515_LANE-DB-REQUEST-chief-staged-canon-
gate-spec-and-backuperror-wrapper.md`` section (b.1).  chief wires the ps1
side against THIS contract, so the exit codes below are not an implementation
detail: they are the interface, and are asserted through a real subprocess.

THE DATABASES HERE ARE REAL.  Every database is built by the real
``SQLiteStore`` running the repository's real ``migrations/`` directory inside
``tempfile.TemporaryDirectory()``, and every snapshot is produced by the real
snapshot code -- ``migrate_with_backup`` where a migration is the point, and
``persistence_backup.snapshot_database`` directly in the two fixtures that need
a snapshot of an ALREADY-migrated database (there ``should_snapshot`` correctly
declines, and an earlier draft of those two tests ran with no snapshot at all
and went red on the wrong condition).  Nothing here can reach
``state/pirateforce.sqlite3``.

THE ASYMMETRY THESE TESTS ARE BUILT AROUND.  A false red costs a human ten
minutes.  A false ``20`` rewrites ``CANON_SHA.txt``, which is the only record
of what the canonical database is supposed to be -- after that the gate is
pinned to whatever state the mistake left behind, permanently, and no later
round can tell.  So the bulk of this file is the negative direction: every one
of the five conditions is broken on its own, against a database that is otherwise perfectly explainable, and each
must drop the verdict to ``UNEXPLAINED``.  A test that only proved the happy
path would stay green against a ``classify`` whose body was
``return EXPLAINED_BY_MIGRATION``.

Nine of those refusals are pf-adversary findings against this module's FIRST
version, which had only four conditions and none of them anchored to the pin --
it answered ``EXPLAINED_BY_MIGRATION`` for a ``DELETE FROM accounts``.  They
live in ``AdversaryFoundTests`` and every one of them was measured red against
the code as it stood before the fix.

WHAT THIS FILE DOES NOT PROVE.  It does not touch ``staged/`` (not this lane's
to write, and not in this repository at all) and therefore proves nothing about
the ps1 jobs themselves; it does not run against the owner's canonical
database, which no cloud round can see; and the four limits named at the end of
``persistence_canon_gate``'s own docstring are limits of the DESIGN, so no test
here closes them either.

It also does not prove the gate is CORRECT about a real historical rotation --
only that it is correct about the conditions the gate was specified to check.

ASCII only: the bridge console is code page 874.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_backup  # noqa: E402
from pirateforce_foundation import persistence_canon_gate as gate  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"


class CanonGateTestBase(unittest.TestCase):
    """Builds the one situation the whole file varies: a database that HAS
    been migrated, whose pre-migration snapshot exists, and whose pin still
    names the pre-migration bytes.  That is the shape a real rotation has."""

    def _fresh_store(self, tmp, migrations=MIGRATIONS):
        store = SQLiteStore(Path(tmp) / "state" / "pirateforce.sqlite3", migrations)
        Path(store.path).parent.mkdir(parents=True, exist_ok=True)
        return store

    def _partial_migrations(self, tmp, upto):
        """A copy of ``migrations/`` holding only versions <= ``upto``, so a
        database can be brought to an OLDER schema with the real runner rather
        than by hand."""
        directory = Path(tmp) / ("migrations_upto_%03d" % upto)
        directory.mkdir(exist_ok=True)
        for path in sorted(MIGRATIONS.glob(gate.MIGRATION_GLOB)):
            if int(path.name[:3]) <= upto:
                shutil.copyfile(path, directory / path.name)
        return directory

    def _rotation_situation(self, tmp):
        """Returns ``(store, pinned_sha, backups_root)``.

        The database is migrated to the second-to-last version, hashed (that
        hash is the pin), then migrated the rest of the way through
        ``migrate_with_backup`` so a real snapshot of the pinned bytes lands in
        ``db_backups/``.  Nothing is faked: the snapshot is the one a boot
        would have taken.
        """
        versions = sorted(gate.migration_checksums(MIGRATIONS))
        older = self._partial_migrations(tmp, versions[-2])
        store = self._fresh_store(tmp, older)
        store.migrate()
        pinned = gate.sha256_file(store.path)

        full = SQLiteStore(store.path, MIGRATIONS)
        snapshot = full.migrate_with_backup()
        self.assertIsNotNone(snapshot, "the last migration should have earned a snapshot")
        self.assertNotEqual(
            gate.sha256_file(store.path), pinned,
            "the migration must actually have changed the file, or this fixture "
            "is not testing what it claims to",
        )
        return full, pinned, gate.default_backups_root(store.path)

    def _classify(self, store, pin, backups_root=None, migrations=MIGRATIONS):
        return gate.classify(store.path, migrations, pin, backups_root)

    def _write_into_the_main_file(self, path, statements):
        """Apply ``statements`` and leave them in the MAIN database file.

        The explicit ``close()`` is the whole point and was learned the hard
        way: these databases are WAL-mode, so a committed write lands in the
        ``-wal`` and the main file's sha256 does not move at all until the last
        connection closes and SQLite checkpoints.  Two tests here first
        "changed" the database and then asserted the sha had changed -- it had
        not, and they were measuring nothing.  It is also a real property of
        the pin the bridge keeps: ``Get-FileHash`` on the main file cannot see
        a write still living in a hot log.
        """
        db = sqlite3.connect(path)
        try:
            for statement, parameters in statements:
                db.execute(statement, parameters)
            db.commit()
        finally:
            db.close()


class VerdictTests(CanonGateTestBase):
    def test_an_untouched_database_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._fresh_store(tmp)
            store.migrate()
            result = self._classify(store, gate.sha256_file(store.path))
        self.assertEqual(gate.UNCHANGED, result.verdict)
        self.assertEqual(0, result.exit_code)
        self.assertIsNone(result.new_sha)

    def test_the_pin_is_matched_case_insensitively(self):
        """``CANON_SHA.txt`` is uppercase; ``sqlite3``/``hashlib`` produce
        lowercase.  A gate that made a real rotation out of letter case would
        rewrite the pin on a database nothing had touched."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._fresh_store(tmp)
            store.migrate()
            lower = gate.sha256_file(store.path).lower()
            result = self._classify(store, "  %s\n" % lower)
        self.assertEqual(gate.UNCHANGED, result.verdict)

    def test_a_real_migration_with_a_real_snapshot_is_explained(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, _root = self._rotation_situation(tmp)
            result = self._classify(store, pinned)
            actual = gate.sha256_file(store.path)
        self.assertEqual(gate.EXPLAINED_BY_MIGRATION, result.verdict, result.reasons)
        self.assertEqual(20, result.exit_code)
        self.assertEqual(actual, result.new_sha)
        self.assertIsNotNone(result.evidence["snapshot_of_pinned_bytes"])

    def test_the_new_sha_is_the_value_the_caller_would_pin(self):
        """The contract's whole point: what ``NEW_SHA=`` says must be what
        ``Get-FileHash`` on the same file says, or the rotation writes a value
        the next round's gate will immediately call UNEXPLAINED."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, _root = self._rotation_situation(tmp)
            result = self._classify(store, pinned)
            again = gate.classify(store.path, MIGRATIONS, result.new_sha)
        self.assertEqual(gate.UNCHANGED, again.verdict, again.reasons)


class RefusalTests(CanonGateTestBase):
    """Each test breaks exactly ONE of the four conditions on an otherwise
    explainable situation.  If any of these goes green the gate has become a
    machine for rotating the pin."""

    def test_a_changed_database_with_no_snapshot_of_the_pinned_bytes_is_unexplained(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            shutil.rmtree(root)
            result = self._classify(store, pinned)
        self.assertEqual(gate.UNEXPLAINED, result.verdict)
        self.assertEqual(13, result.exit_code)
        self.assertTrue(
            any("no completed, still-restorable snapshot" in reason
                for reason in result.reasons),
            result.reasons,
        )

    def test_a_snapshot_of_some_other_state_does_not_explain_this_pin(self):
        """The snapshot tree is full, and every snapshot in it is real -- but
        none of them holds the bytes the PIN names.  Rotating here would throw
        away the only description of a state nobody has a copy of."""
        with tempfile.TemporaryDirectory() as tmp:
            store, _pinned, _root = self._rotation_situation(tmp)
            unrelated = "A" * 64
            result = self._classify(store, unrelated)
        self.assertEqual(gate.UNEXPLAINED, result.verdict)

    def test_an_incomplete_snapshot_does_not_count(self):
        """``persistence_backup`` rule 2: a directory still named
        ``.INCOMPLETE`` is a boot that died mid-copy.  Reading it as a backup
        is the exact mistake that rule exists to forbid."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            [snapshot_dir] = [p for p in root.iterdir() if p.is_dir()]
            snapshot_dir.rename(
                snapshot_dir.with_name(snapshot_dir.name + gate.INCOMPLETE_SUFFIX)
            )
            result = self._classify(store, pinned)
        self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)

    def test_a_snapshot_that_no_longer_restores_does_not_count(self):
        """A backup nobody has re-opened is a claim, not a backup.  The
        manifest still says the snapshot is fine; the file behind it is not."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            [snapshot_dir] = [p for p in root.iterdir() if p.is_dir()]
            manifest = json.loads((snapshot_dir / "MANIFEST.json").read_text())
            copy = snapshot_dir / manifest["snapshot_database"]
            copy.write_bytes(b"")
            result = self._classify(store, pinned)
        self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)
        # Every reason this branch can produce contains the word "snapshot", so
        # an ``or "snapshot" in reason`` disjunct here would make the assertion
        # unfalsifiable.  The note the notes list is supposed to carry is named
        # exactly instead.
        self.assertTrue(
            any("no longer verifies" in note
                for note in result.evidence["snapshot_notes"]),
            result.evidence["snapshot_notes"],
        )

    def test_a_snapshot_naming_a_different_source_database_does_not_count(self):
        """A replay tool's scratch database sharing a backups tree must not be
        able to license a rotation of the CANONICAL pin -- the failure that
        would leave the real canonical un-pinned forever."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            [snapshot_dir] = [p for p in root.iterdir() if p.is_dir()]
            manifest_path = snapshot_dir / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["source_database"] = str(Path(tmp) / "state" / "somebody_elses.sqlite3")
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
            result = self._classify(store, pinned)
        self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)

    def test_a_pending_migration_means_the_change_is_not_a_finished_run(self):
        """The database was migrated, but this working tree has a migration it
        has never applied.  Whatever changed the file, it was not a completed
        run of the migrations this repository is holding."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, _root = self._rotation_situation(tmp)
            newer = Path(tmp) / "migrations_with_an_extra"
            newer.mkdir()
            for path in sorted(MIGRATIONS.glob(gate.MIGRATION_GLOB)):
                shutil.copyfile(path, newer / path.name)
            highest = sorted(gate.migration_checksums(MIGRATIONS))[-1]
            (newer / ("%03d_not_applied.sql" % (highest + 1))).write_text(
                "CREATE TABLE canon_gate_probe(id INTEGER PRIMARY KEY);\n"
            )
            result = self._classify(store, pinned, migrations=newer)
        self.assertEqual(gate.UNEXPLAINED, result.verdict)
        self.assertTrue(
            any("not applied" in reason for reason in result.reasons), result.reasons
        )

    def test_a_database_ahead_of_this_working_tree_is_unexplained(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, _root = self._rotation_situation(tmp)
            older = self._partial_migrations(tmp, sorted(gate.migration_checksums(MIGRATIONS))[-2])
            result = self._classify(store, pinned, migrations=older)
        self.assertEqual(gate.UNEXPLAINED, result.verdict)
        self.assertTrue(
            any("ahead of this working tree" in reason for reason in result.reasons),
            result.reasons,
        )

    def test_a_checksum_the_ledger_no_longer_matches_is_unexplained(self):
        """The ledger says version N ran, but N's bytes in this tree are not
        the bytes that ran.  The database is then describing a migration this
        repository does not contain, and cannot be said to explain anything."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, _root = self._rotation_situation(tmp)
            with sqlite3.connect(store.path) as db:
                db.execute(
                    "UPDATE schema_migrations SET checksum=? WHERE version=?",
                    ("0" * 64, sorted(gate.migration_checksums(MIGRATIONS))[-1]),
                )
            result = self._classify(store, pinned)
        self.assertEqual(gate.UNEXPLAINED, result.verdict)
        self.assertTrue(
            any("applied checksum differs" in reason for reason in result.reasons),
            result.reasons,
        )

    def test_a_ledger_with_no_checksum_column_is_unexplained(self):
        """A pre-checksum ledger is a database a boot is about to REWRITE
        (``store.migrate``'s ALTER/UPDATE branch).  Treating it as settled
        evidence of a finished migration is backwards."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, _root = self._rotation_situation(tmp)
            with sqlite3.connect(store.path) as db:
                rows = db.execute("SELECT version, applied_at FROM schema_migrations").fetchall()
                db.execute("DROP TABLE schema_migrations")
                db.execute(
                    "CREATE TABLE schema_migrations("
                    "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
                )
                db.executemany("INSERT INTO schema_migrations VALUES (?,?)", rows)
            result = self._classify(store, pinned)
        self.assertEqual(gate.UNEXPLAINED, result.verdict)
        self.assertTrue(
            any("checksum column" in reason for reason in result.reasons), result.reasons
        )

    def test_a_database_whose_every_page_is_destroyed_is_never_explained(self):
        """Kept, but no longer claiming to be the integrity_check test: pf-
        adversary measured that deleting condition 3 entirely left this green,
        because overwriting every page also destroys the LEDGER and condition 2
        reds it first.  ``AdversaryFoundTests.test_a_corrupt_data_page_with_an_
        intact_ledger_is_unexplained`` is the one that measures condition 3.
        What this still proves is narrower and still worth having: a file this
        broken produces a red rather than a crash."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, _root = self._rotation_situation(tmp)
            data = bytearray(Path(store.path).read_bytes())
            # Page 1 (the header) is left intact so the file still OPENS and
            # the refusal comes from integrity_check having something to say,
            # not from "file is not a database".  Every later page is
            # overwritten: an earlier version of this test flipped bytes in a
            # region that turned out to be free space, integrity_check
            # returned ``ok``, and the gate correctly called it EXPLAINED --
            # the test was measuring nothing.
            page_size = int.from_bytes(data[16:18], "big") or 4096
            for offset in range(page_size, len(data)):
                data[offset] = 0xFF
            Path(store.path).write_bytes(bytes(data))
            self.assertNotEqual(
                "ok", gate.integrity_check(store.path),
                "fixture must actually produce a database integrity_check rejects",
            )
            result = self._classify(store, pinned)
        self.assertEqual(gate.UNEXPLAINED, result.verdict)

    def test_a_missing_pin_can_never_rotate_the_pin(self):
        """An empty ``CANON_SHA.txt`` used to be the caller's problem.  Here it
        must be a red: a gate that says UNCHANGED when there is nothing to be
        unchanged from has unlocked itself forever."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._fresh_store(tmp)
            store.migrate()
            for empty in ("", "   \n", "not-a-sha", "A" * 63, "A" * 65, "G" * 64):
                with self.subTest(pin=empty):
                    result = self._classify(store, empty)
                    self.assertEqual(gate.UNEXPLAINED, result.verdict)
                    self.assertEqual(13, result.exit_code)

    def test_the_pin_is_not_repaired_by_stripping_characters_out_of_it(self):
        """The ps1 does ``-replace '[^0-9A-Fa-f]',''``.  This module must not:
        a truncated pin with punctuation in it would otherwise be rebuilt into
        a 64-character string no tool ever wrote."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._fresh_store(tmp)
            store.migrate()
            actual = gate.sha256_file(store.path)
            mangled = actual[:32] + "-" + actual[32:]
            result = self._classify(store, mangled)
        self.assertEqual(gate.UNEXPLAINED, result.verdict)

    def test_a_missing_database_is_unexplained_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = gate.classify(
                Path(tmp) / "state" / "nothing_here.sqlite3", MIGRATIONS, "A" * 64
            )
        self.assertEqual(gate.UNEXPLAINED, result.verdict)
        self.assertEqual(13, result.exit_code)


class GateWritesNothingTests(CanonGateTestBase):
    def test_classifying_leaves_the_database_and_the_snapshot_tree_alone(self):
        """The gate inspects the owner's only copy of the world.  If it can
        change it -- including SQLite's own checkpoint-on-close, which is how
        this lane already destroyed one hot WAL -- it is worse than nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)

            def census():
                files = {}
                for path in sorted(Path(tmp).rglob("*")):
                    if path.is_file():
                        files[str(path.relative_to(tmp))] = (
                            path.stat().st_size, gate.sha256_file(path)
                        )
                return files

            before = census()
            gate.classify(store.path, MIGRATIONS, pinned)
            after = census()

        # ``-shm`` is the ONE difference this test tolerates, and it is named
        # here rather than filtered out of the census, so that a future change
        # which starts writing something else cannot hide behind a broad
        # exclusion.  SQLite rebuilds the write-ahead-log INDEX whenever any
        # reader attaches -- including this gate's strictly read-only probes --
        # and that index holds no committed data (``persistence_backup``
        # excludes it from ``FINGERPRINT_SUFFIXES`` for the same reason:
        # deleting it loses nothing).  Every other file, the database and its
        # ``-wal`` included, must be byte-identical, and nothing may disappear.
        appeared = set(after) - set(before)
        for name in sorted(appeared):
            if name.endswith("-shm"):
                continue
            # A zero-byte ``-wal`` is the second tolerated artefact and is
            # allowed ONLY at zero bytes: SQLite creates the log file when a
            # reader attaches to a WAL-mode database that currently has none,
            # and an empty log holds no transaction.  A ``-wal`` with CONTENT
            # appearing here would mean this gate had written to the owner's
            # database, so the size is asserted rather than assumed.
            self.assertTrue(
                name.endswith("-wal") and after[name][0] == 0,
                "the gate created a file it has no business creating: %s (%d bytes)"
                % (name, after[name][0]),
            )
        self.assertEqual(set(), set(before) - set(after), "the gate deleted a file")
        for name, digest in before.items():
            if name.endswith("-shm"):
                continue
            self.assertEqual(digest, after[name], "the gate rewrote %s" % name)

    def test_classifying_a_hot_wal_database_does_not_lose_the_wal(self):
        """A stopped server normally leaves a hot ``-wal``.  A read-WRITE
        connect would checkpoint and delete it on close, and the transactions
        living only in that log would move into the main file -- changing the
        very sha256 this gate is reporting on."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, _root = self._rotation_situation(tmp)
            keep_open = sqlite3.connect(store.path)
            keep_open.execute("PRAGMA journal_mode=WAL")
            keep_open.execute("INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                              ("canon_gate_wal_probe", "2026-09-01T00:00:00Z"))
            keep_open.commit()
            wal = Path(str(store.path) + "-wal")
            self.assertTrue(wal.is_file() and wal.stat().st_size, "fixture needs a hot WAL")
            before = wal.read_bytes()
            main_before = Path(store.path).read_bytes()
            try:
                gate.classify(store.path, MIGRATIONS, pinned)
                self.assertEqual(before, wal.read_bytes())
                self.assertEqual(main_before, Path(store.path).read_bytes())
            finally:
                # In a ``finally`` because an assertion failure would otherwise
                # leave the handle open and, on a Windows runner,
                # ``TemporaryDirectory`` cleanup would raise PermissionError on
                # top of it -- masking the real failure with a teardown error.
                keep_open.close()


class CommandLineContractTests(CanonGateTestBase):
    """chief wires ``staged/`` against these exact numbers, through a real
    process boundary -- an in-process ``main()`` call would not catch a module
    that fails to import under ``-m``."""

    def _run(self, db, migrations, pin, backups_root=None):
        argv = [
            sys.executable, "-m", "pirateforce_foundation.persistence_canon_gate",
            "--db", str(db), "--migrations", str(migrations), "--expect-sha", str(pin),
        ]
        if backups_root is not None:
            argv += ["--backups-root", str(backups_root)]
        env = {"PYTHONPATH": str(ROOT / "src")}
        import os
        merged = dict(os.environ)
        merged.update(env)
        return subprocess.run(argv, capture_output=True, text=True, env=merged, cwd=str(ROOT))

    def test_exit_zero_for_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._fresh_store(tmp)
            store.migrate()
            done = self._run(store.path, MIGRATIONS, gate.sha256_file(store.path))
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertIn("VERDICT=UNCHANGED", done.stdout)
        self.assertNotIn("NEW_SHA=", done.stdout)

    def test_exit_twenty_and_a_parsable_new_sha_for_an_explained_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, _root = self._rotation_situation(tmp)
            done = self._run(store.path, MIGRATIONS, pinned)
            actual = gate.sha256_file(store.path)
        self.assertEqual(20, done.returncode, done.stdout + done.stderr)
        printed = [
            line.split("=", 1)[1].strip()
            for line in done.stdout.splitlines()
            if line.startswith("NEW_SHA=")
        ]
        self.assertEqual([actual], printed)

    def test_exit_thirteen_for_an_unexplained_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            shutil.rmtree(root)
            done = self._run(store.path, MIGRATIONS, pinned)
        self.assertEqual(13, done.returncode, done.stdout + done.stderr)
        self.assertIn("VERDICT=UNEXPLAINED", done.stdout)
        self.assertNotIn("NEW_SHA=", done.stdout)
        self.assertIn("ABORT", done.stdout)

    def test_the_three_exit_codes_stay_distinct_and_do_not_collide_with_faults(self):
        """A guard against renumbering, and nothing more.

        An earlier version of this test asserted ``13 == gate.EXIT_UNEXPLAINED``
        and claimed in its own docstring to be about
        ``staged/175_round109_path_d_ci_status_gate_commit.ps1:123``.  It was
        the module's own constant compared to a literal: ``staged/`` lives in
        the pf_bridge repository, is not present in this checkout, and nothing
        in this repository can measure it.  The reason 13 must not move is
        real -- a ps1 that has not been rewired yet still aborts on it -- but
        the evidence for that reason is not here, so the claim is made in
        writing to chief instead of pretended to in a test."""
        self.assertEqual(3, len(set(gate.EXIT_CODES.values())))
        self.assertNotIn(gate.EXIT_INTERNAL_ERROR, set(gate.EXIT_CODES.values()))
        self.assertEqual(0, gate.EXIT_CODES[gate.UNCHANGED])

    def test_an_internal_fault_does_not_borrow_a_verdict(self):
        """If the module itself breaks, the caller must not be able to read the
        result as ``UNCHANGED``.  Measured by making ``classify`` raise."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._fresh_store(tmp)
            store.migrate()
            argv = [
                sys.executable, "-c",
                "import sys; sys.path.insert(0, %r);\n"
                "from pirateforce_foundation import persistence_canon_gate as g\n"
                "def boom(*a, **k):\n"
                "    raise RuntimeError('deliberate')\n"
                "g.classify = boom\n"
                "sys.exit(g.main(['--db', %r, '--migrations', %r, '--expect-sha', %r]))"
                % (str(ROOT / "src"), str(store.path), str(MIGRATIONS), "A" * 64),
            ]
            done = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(gate.EXIT_INTERNAL_ERROR, done.returncode)
        self.assertNotIn(done.returncode, set(gate.EXIT_CODES.values()))
        self.assertIn("deliberate", done.stderr)



class AdversaryFoundTests(CanonGateTestBase):
    """Every test in this class is a pf-adversary finding from this module's
    first review, each measured against the module BEFORE it was fixed.  They
    are kept together because what they have in common matters more than what
    they each check: all of them are paths to a false ``20``, and a false ``20``
    makes the caller overwrite ``CANON_SHA.txt``."""

    # ---- D1: the verdict was not a function of the change at all ----------

    def test_a_delete_with_no_migration_since_the_pin_is_not_explained(self):
        """THE finding.  Fully migrated database, boot legitimately takes a
        snapshot (``should_snapshot`` also fires for a ledger/journal-mode
        rewrite with zero migrations pending), then someone deletes every
        account.  The old module answered EXPLAINED_BY_MIGRATION, exit 20, and
        the caller would have pinned the vandalised file."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._fresh_store(tmp)
            store.migrate()
            self._write_into_the_main_file(store.path, [
                ("INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                 ("victim_%d" % n, "2026-09-01T00:00:00Z"))
                for n in range(20)
            ])
            pinned = gate.sha256_file(store.path)
            root = gate.default_backups_root(store.path)
            # Taken through the real snapshot code, not through
            # ``migrate_with_backup``: on a database that is already fully
            # migrated ``should_snapshot`` correctly declines, and an earlier
            # version of this test therefore ran with NO snapshot at all -- it
            # went red on condition 4 and proved nothing about the finding it
            # is named for.
            persistence_backup.snapshot_database(store.path, root, reason="test fixture")
            self.assertIsNotNone(
                gate.find_snapshot_of_sha(store.path, pinned, root)[0],
                "fixture needs a snapshot the gate accepts, or this test reds for "
                "the wrong reason",
            )
            self._write_into_the_main_file(store.path, [("DELETE FROM accounts", ())])
            self.assertNotEqual(pinned, gate.sha256_file(store.path))

            result = self._classify(store, pinned, backups_root=root)
        self.assertNotIn(
            "snapshot", " ".join(result.reasons),
            "condition 4 must not be doing this test's work",
        )
        self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)
        self.assertEqual(13, result.exit_code)

    def test_gameplay_writes_after_a_real_migration_are_not_explained(self):
        """The same hole without any adversary: boot migrates, players play,
        the teardown job runs the gate.  A migration DID run, so the
        version-set check alone is not enough -- the derivation is what
        catches this.  ``NEW_SHA`` would otherwise have named a state no
        migration produced."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            after_migration = gate.sha256_file(store.path)
            self._write_into_the_main_file(store.path, [
                ("INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                 ("a_player_logged_in", "2026-09-01T00:00:00Z")),
            ])
            self.assertNotEqual(after_migration, gate.sha256_file(store.path))
            result = self._classify(store, pinned, backups_root=root)
        self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)
        self.assertTrue(
            any("does not reproduce" in reason for reason in result.reasons),
            result.reasons,
        )

    def test_one_insert_after_the_boot_is_enough_to_red_the_gate(self):
        """Named explicitly because it is the smallest input that separates the
        fixed module from the broken one: a single row."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            self.assertEqual(
                gate.EXPLAINED_BY_MIGRATION,
                self._classify(store, pinned, backups_root=root).verdict,
            )
            self._write_into_the_main_file(store.path, [
                ("INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                 ("one_row", "2026-09-01T00:00:00Z")),
            ])
            result = self._classify(store, pinned, backups_root=root)
        self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)

    def test_the_evidence_names_which_migrations_ran_since_the_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            result = self._classify(store, pinned, backups_root=root)
            expected_new = sorted(gate.migration_checksums(MIGRATIONS))[-1:]
        self.assertEqual(gate.EXPLAINED_BY_MIGRATION, result.verdict, result.reasons)
        self.assertEqual(expected_new, result.evidence["migrations_run_since_the_pin"])
        self.assertTrue(result.evidence["content_matches_derivation"])

    # ---- D2: the gate used to DELETE files while "verifying" them ---------

    def test_verifying_a_snapshot_does_not_delete_a_hot_wal_beside_it(self):
        """An operator inspects a backup and their process is killed, leaving a
        genuine hot ``-wal`` beside the snapshot database.  The old module
        borrowed ``persistence_backup._snapshot_is_still_good``, whose last
        step unlinks exactly those sidecars -- so running the GATE destroyed a
        committed transaction inside a BACKUP, in a module whose own rule 3 is
        that nothing is ever deleted."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            [snapshot_dir] = [p for p in root.iterdir() if p.is_dir()]
            manifest = json.loads((snapshot_dir / "MANIFEST.json").read_text())
            copy = snapshot_dir / manifest["snapshot_database"]

            operator = sqlite3.connect(copy)
            operator.execute("PRAGMA journal_mode=WAL")
            operator.execute(
                "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                ("operator_was_looking_at_this", "2026-09-01T00:00:00Z"),
            )
            operator.commit()
            wal = Path(str(copy) + "-wal")
            self.assertTrue(wal.is_file() and wal.stat().st_size, "fixture needs a hot WAL")
            wal_bytes = wal.read_bytes()

            def rows():
                probe = sqlite3.connect(copy)
                try:
                    return probe.execute(
                        "SELECT count(*) FROM accounts WHERE login_name=?",
                        ("operator_was_looking_at_this",),
                    ).fetchone()[0]
                finally:
                    probe.close()

            self.assertEqual(1, rows())
            try:
                gate.classify(store.path, MIGRATIONS, pinned, root)
                self.assertTrue(wal.is_file(), "the gate deleted a backup's write-ahead log")
                self.assertEqual(wal_bytes, wal.read_bytes())
                self.assertEqual(1, rows(), "the gate lost a committed transaction")
            finally:
                operator.close()

    # ---- D3: a manifest could point the gate at the live database ---------

    def test_a_manifest_cannot_name_a_file_outside_its_own_directory(self):
        """``persistence_backup._find_identical_snapshot`` guards this and says
        why in a comment; the first version of this module re-implemented that
        scan without the guard.  Measured then: the gate returned exit 20 while
        nominating the owner's LIVE canonical database as its own backup, and
        de-WAL'd that database in the act of verifying it."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            [snapshot_dir] = [p for p in root.iterdir() if p.is_dir()]
            manifest_path = snapshot_dir / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            for escape in (
                "../../%s" % Path(store.path).name,
                str(Path(store.path)),
                "..",
                "sub/dir.sqlite3",
            ):
                with self.subTest(escape=escape):
                    manifest["snapshot_database"] = escape
                    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
                    result = gate.classify(store.path, MIGRATIONS, pinned, root)
                    self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)

    def test_the_live_database_is_never_offered_as_its_own_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            [snapshot_dir] = [p for p in root.iterdir() if p.is_dir()]
            manifest_path = snapshot_dir / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["snapshot_database"] = "../../%s" % Path(store.path).name
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
            found, _notes = gate.find_snapshot_of_sha(store.path, pinned, root)
        self.assertIsNone(found)


    def test_a_vacuum_with_no_migration_since_the_pin_is_not_explained(self):
        """The case the derivation ALONE cannot catch, found by mutating the
        fix rather than the original code: ``VACUUM`` rewrites the file's page
        layout so the sha256 moves, while the CONTENT stays byte-for-byte the
        same -- so re-deriving from the snapshot reproduces it exactly and
        condition 5's comparison is happy.  Only the "has any migration run
        since the pin?" half separates this from a real rotation.  Without it
        the caller would pin a change no migration made, on nothing but a
        maintenance command."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._fresh_store(tmp)
            store.migrate()
            self._write_into_the_main_file(store.path, [
                ("INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                 ("before_the_vacuum_%d" % n, "2026-09-01T00:00:00Z"))
                for n in range(30)
            ])
            pinned = gate.sha256_file(store.path)
            root = gate.default_backups_root(store.path)
            persistence_backup.snapshot_database(store.path, root, reason="test fixture")
            self.assertIsNotNone(
                gate.find_snapshot_of_sha(store.path, pinned, root)[0],
                "fixture needs a snapshot the gate accepts",
            )
            db = sqlite3.connect(store.path)
            try:
                db.execute("VACUUM")
            finally:
                db.close()
            self.assertNotEqual(
                pinned, gate.sha256_file(store.path), "VACUUM must move the sha"
            )
            result = self._classify(store, pinned, backups_root=root)
        self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)
        self.assertTrue(
            any("no migration has been applied since the pin" in r for r in result.reasons),
            result.reasons,
        )
        self.assertEqual([], result.evidence["migrations_run_since_the_pin"])

    def test_a_fully_forged_manifest_cannot_nominate_the_live_database(self):
        """The traversal tests above are killed by the re-hash, not by the path
        guard -- measured by removing the guard and watching the suite stay
        green.  An attacker editing a manifest can equally forge the
        ``verification`` block, and then only the path guard is left.  With the
        guard removed and this manifest in place, the gate accepts the owner's
        LIVE canonical database as its own backup."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            [snapshot_dir] = [p for p in root.iterdir() if p.is_dir()]
            manifest_path = snapshot_dir / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            live = Path(store.path)
            manifest["snapshot_database"] = "../../%s" % live.name
            manifest["verification"] = {
                "bytes": live.stat().st_size,
                "sha256": gate.sha256_file(live).lower(),
                "integrity_check": "ok",
            }
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

            found, _notes = gate.find_snapshot_of_sha(store.path, pinned, root)
            self.assertIsNone(
                found, "the gate offered the live database as its own backup"
            )
            result = gate.classify(store.path, MIGRATIONS, pinned, root)
        self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)

    # ---- D4: integrity_check had no test of its own -----------------------

    def test_a_corrupt_data_page_with_an_intact_ledger_is_unexplained(self):
        """The old corruption test overwrote every page, which destroyed the
        LEDGER too -- so condition 2 alone redded it and deleting the
        integrity_check entirely left the suite green.  This one corrupts a
        single page and keeps searching until it finds one where the ledger
        still reads cleanly and only integrity_check objects."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            original = Path(store.path).read_bytes()
            page_size = int.from_bytes(original[16:18], "big") or 4096
            pages = len(original) // page_size

            found = None
            for page in range(2, pages + 1):
                data = bytearray(original)
                start = (page - 1) * page_size
                data[start:start + page_size] = b"\xa5" * page_size
                Path(store.path).write_bytes(bytes(data))
                if (
                    gate.ledger_rows(store.path) is not None
                    and gate.integrity_check(store.path) != "ok"
                ):
                    found = page
                    break
                Path(store.path).write_bytes(original)

            self.assertIsNotNone(
                found,
                "no single-page corruption produced a readable ledger with a "
                "failing integrity_check -- this test would be measuring nothing",
            )
            result = self._classify(store, pinned, backups_root=root)
            ledger_reasons = [r for r in result.reasons if "ledger" in r or "checksum" in r]
        self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)
        self.assertEqual([], ledger_reasons, "condition 2 must not be doing this test's work")
        self.assertTrue(
            any("integrity_check" in reason for reason in result.reasons), result.reasons
        )

    # ---- D5: an empty migrations/ made condition 2 vacuously true ---------

    def test_an_empty_or_missing_migrations_directory_can_never_explain(self):
        """Both sides of every set comparison were empty, so no reason was ever
        appended.  Measured on the old module with an emptied ledger and a
        ``--migrations`` path that did not exist: EXPLAINED_BY_MIGRATION."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            empty = Path(tmp) / "Pirate Force" / "migrations"
            empty.mkdir(parents=True)
            missing = Path(tmp) / "Pirate Force" / "not_here"
            with sqlite3.connect(store.path) as db:
                db.execute("DELETE FROM schema_migrations")
            for directory in (empty, missing):
                with self.subTest(migrations=directory.name):
                    result = gate.classify(store.path, directory, pinned, root)
                    self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)
                    self.assertTrue(
                        any("no migration files" in r for r in result.reasons),
                        result.reasons,
                    )

    # ---- D6: condition 1's guard was carried by condition 4 ---------------

    def test_an_invalid_pin_is_refused_for_being_an_invalid_pin(self):
        """Deleting condition 1 outright used to leave the suite green: the
        snapshot search redded those tests instead, and the caller was handed
        the wrong reason.  Asserting on the reason is what makes the guard
        independently load-bearing."""
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            for bad in ("", "   \n", "not-a-sha", pinned[:63], pinned + "A", "\ufeff" + pinned[:32]):
                with self.subTest(pin=bad):
                    result = gate.classify(store.path, MIGRATIONS, bad, root)
                    self.assertEqual(gate.UNEXPLAINED, result.verdict)
                    self.assertTrue(
                        any("64-character hex" in r for r in result.reasons), result.reasons
                    )
                    self.assertNotIn("expected_sha", result.evidence)

    def test_a_pin_wearing_a_byte_order_mark_still_matches(self):
        """PowerShell writes a BOM by default on several hosts, and the caller
        this contract asks to REWRITE ``CANON_SHA.txt`` is a PowerShell job --
        so the gate would have redded permanently on a pin it asked for
        itself.  ``str.strip()`` does not remove U+FEFF."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._fresh_store(tmp)
            store.migrate()
            result = self._classify(store, "\ufeff%s\r\n" % gate.sha256_file(store.path))
        self.assertEqual(gate.UNCHANGED, result.verdict, result.reasons)

    # ---- D7: tree content could forge a NEW_SHA= line onto a red run ------

    def test_a_snapshot_directory_name_cannot_forge_a_new_sha_line(self):
        """``NEW_SHA=`` is the one line the contract invites a caller to parse.
        A directory name containing a newline used to inject a whole extra line
        into the stdout of an exit-13 run."""
        if sys.platform.startswith("win"):
            self.skipTest("Windows file names cannot contain a newline")
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            [snapshot_dir] = [p for p in root.iterdir() if p.is_dir()]
            forged = "NEW_SHA=%s" % ("D" * 64)
            manifest_path = snapshot_dir / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["source_database"] = str(Path(tmp) / "somebody_else.sqlite3")
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
            snapshot_dir.rename(snapshot_dir.with_name("evil\n%s" % forged))
            result = gate.classify(store.path, MIGRATIONS, pinned, root)
            printed = gate.render(result)
        self.assertEqual(gate.UNEXPLAINED, result.verdict)
        self.assertEqual(
            [], [line for line in printed if line.startswith("NEW_SHA=")],
            "tree content forged the one line the contract says is machine-readable",
        )

    def test_multi_line_integrity_output_stays_on_one_line(self):
        """SQLite's integrity_check output is genuinely multi-line, so red
        stdout already carried lines with no ``reason:`` prefix even with no
        adversary present."""
        flattened = gate.render(
            gate.CanonGateResult(
                gate.UNEXPLAINED, "A" * 64, "B" * 64,
                reasons=["*** in database main ***\nTree 3 page 12 cell 55: bad\r\nNEW_SHA=" + "C" * 64],
            )
        )
        self.assertEqual([], [line for line in flattened if line.startswith("NEW_SHA=")])
        for line in flattened:
            self.assertNotIn("\n", line)

    # ---- D10: the missing-file branch was untested ------------------------

    def test_a_manifest_with_no_snapshot_database_key_is_a_red_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, pinned, root = self._rotation_situation(tmp)
            [snapshot_dir] = [p for p in root.iterdir() if p.is_dir()]
            manifest_path = snapshot_dir / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            for value in (None, 123, "", "does_not_exist.sqlite3"):
                with self.subTest(value=value):
                    broken = dict(manifest)
                    if value is None:
                        broken.pop("snapshot_database", None)
                    else:
                        broken["snapshot_database"] = value
                    manifest_path.write_text(json.dumps(broken, indent=2, sort_keys=True))
                    result = gate.classify(store.path, MIGRATIONS, pinned, root)
                    self.assertEqual(gate.UNEXPLAINED, result.verdict, result.reasons)

if __name__ == "__main__":
    unittest.main()
