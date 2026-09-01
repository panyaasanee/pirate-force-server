"""LANE-DB-CANON-001: a canonical database whose sha CHANGED is only ever
called "explained" when a recorded migration run says so.

WHAT THIS FILE IS THE EVIDENCE FOR.  ``COO-DECISION 20260901_1447`` point 4
(``pf_bridge/notes_to_chief/20260901_1447_COO-DECISION-lane-db-m4-unblocked-
canon-sha-mechanism-approved-backuperror-handling.md``) approved
``persistence_canon_gate`` with exactly three outcomes -- ``UNCHANGED`` /
``EXPLAINED_BY_MIGRATION`` / ``UNEXPLAINED`` -- as the second layer under the
one-line sha gate that exists today in PowerShell
(``pf_bridge/staged/175_round109_path_d_ci_status_gate_commit.ps1``, the
``CANON_SHA`` branch, ``exit 13``).  ``COO-DECISION 20260901_2149`` then set
this round as the round it had to land in.

THE DANGER THIS FILE IS AIMED AT.  The easy version of this module reasons
from the sha itself -- "a migration was added lately, so the difference is
probably that" -- and unlocks itself in every case, including the one case the
gate exists for: somebody edited the owner's only copy of the world by hand.
So the tests that matter most here are the NEGATIVE ones.
``test_a_hand_edited_database_with_a_tidy_ledger_is_unexplained`` builds a
database whose ledger is perfect, writes a row into it the way a human with a
sqlite3 prompt would, and proves the gate still says ``UNEXPLAINED``;
``test_a_snapshot_of_a_different_starting_sha_is_not_evidence`` and
``test_a_truncated_snapshot_is_not_evidence`` remove one leg of the evidence at
a time from an otherwise-passing case.

THE DATABASES HERE ARE REAL.  Every database is built by the real
``SQLiteStore`` over the repository's real ``migrations/`` directory inside
``tempfile.TemporaryDirectory()``; every snapshot is produced by the real
``SQLiteStore.migrate_with_backup``.  No manifest is hand-written except in
the tests that deliberately corrupt one, and nothing here can reach
``state/pirateforce.sqlite3``.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable: no player
and no attended tester can see any of it.  Nothing here runs the PowerShell
gate -- ``staged/`` is outside this lane's write scope, and wiring the ps1 to
call this module is chief's (``COO-ORDER 20260901_1447`` point 3), so the
end-to-end "red gate turns amber" path is unproven by this file.  And no test
here runs against the owner's real canonical database; every path is a
temporary one.
"""
import json
import os
import re
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

PROBE_SQL = "CREATE TABLE lane_db_canon_probe(id INTEGER PRIMARY KEY, note TEXT);\n"


class CanonGateTest(unittest.TestCase):
    # ---- helpers ----------------------------------------------------------

    def _migrated_store(self, tmp):
        """A real database at the state the repo's migrations produce."""
        store = SQLiteStore(Path(tmp) / "state" / "pirateforce.sqlite3", MIGRATIONS)
        Path(store.path).parent.mkdir(parents=True, exist_ok=True)
        store.migrate()
        store.ensure_account("owner")
        return store

    def _migrations_plus(self, tmp, version=900, sql=PROBE_SQL):
        """The real migrations directory plus one more file -- the only honest
        way to give a real database something genuinely pending."""
        later = Path(tmp) / "migrations_plus"
        later.mkdir()
        for path in sorted(MIGRATIONS.glob(persistence_backup.MIGRATION_GLOB)):
            (later / path.name).write_bytes(path.read_bytes())
        (later / ("%03d_lane_db_canon_probe.sql" % version)).write_text(
            sql, encoding="utf-8"
        )
        return later

    def _explained_case(self, tmp):
        """The one case that is SUPPOSED to come out EXPLAINED_BY_MIGRATION:
        a canonical database, snapshotted by the real backup path, then
        migrated by the real runner.

        Returns ``(store, canon_sha, migrations_dir, backups_root)``.
        """
        store = self._migrated_store(tmp)
        canon = gate.database_sha256(store.path)
        later = self._migrations_plus(tmp)
        store.migrations = later
        backups = Path(tmp) / "db_backups"
        snapshot = store.migrate_with_backup(backups_root=backups)
        self.assertIsNotNone(snapshot, "the fixture must really take a snapshot")
        return store, canon, later, backups

    def _verdict(self, store, canon, migrations, backups):
        return gate.classify(store.path, migrations, canon, backups)

    def _poststate_path(self, backups, sha256):
        return self._manifest_path(backups).parent / (
            persistence_backup.poststate_filename(sha256)
        )

    @staticmethod
    def _manifest_path(backups):
        directories = [d for d in sorted(Path(backups).iterdir()) if d.is_dir()]
        assert len(directories) == 1, directories
        return directories[0] / "MANIFEST.json"

    def _rewrite_manifest(self, backups, **changes):
        path = self._manifest_path(backups)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest.update(changes)
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return manifest

    # ---- UNCHANGED --------------------------------------------------------

    def test_a_database_that_still_hashes_to_canon_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            verdict = gate.classify(store.path, MIGRATIONS, canon)
            self.assertEqual(gate.UNCHANGED, verdict.outcome)
            self.assertEqual(0, verdict.exit_code)
            self.assertIsNone(verdict.new_canon_sha)

    def test_unchanged_is_decided_before_any_snapshot_or_ledger_is_looked_at(self):
        """The cheap answer must not depend on evidence it does not need.

        A canonical database sitting on a machine with no ``db_backups/`` at
        all -- the normal state between upgrades -- must still pass, or the
        gate turns red for every boot that did nothing.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            missing = Path(tmp) / "no_such_backups_root"
            verdict = gate.classify(store.path, MIGRATIONS, canon, missing)
            self.assertEqual(gate.UNCHANGED, verdict.outcome)
            self.assertFalse(missing.exists())

    def test_the_recorded_sha_is_compared_case_insensitively(self):
        """``CANON_SHA.txt`` holds upper-case hex; ``hashlib`` produces lower.

        Without one normalisation point every single run would report a
        change, and the second layer would be exercised on every boot.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            verdict = gate.classify(store.path, MIGRATIONS, canon.upper())
            self.assertEqual(gate.UNCHANGED, verdict.outcome)

    # ---- EXPLAINED_BY_MIGRATION ------------------------------------------

    def test_a_real_migration_run_over_a_canonical_database_is_explained(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.EXPLAINED_BY_MIGRATION, verdict.outcome)
            self.assertEqual(75, verdict.exit_code)
            self.assertNotEqual(canon, verdict.observed_sha)
            # The value to rotate is the sha this run MEASURED, never one a
            # human typed into the PR ahead of time (`LANE-DB REPLY 1332`).
            self.assertEqual(gate.database_sha256(store.path), verdict.new_canon_sha)
            self.assertEqual([900], verdict.evidence["migrations_applied_since_canon"])

    def test_the_explained_verdict_names_the_snapshot_it_relied_on(self):
        """An "explained" verdict a human cannot audit is not evidence."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            verdict = self._verdict(store, canon, later, backups)
            named = Path(verdict.evidence["snapshot_database"])
            self.assertTrue(named.is_file())
            self.assertTrue(str(named).startswith(str(backups)))
            with sqlite3.connect(str(named)) as copy:
                # The named file is the PRE-migration state: the probe table
                # the migration created must NOT be in it.
                tables = {
                    row[0]
                    for row in copy.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            self.assertIn("schema_migrations", tables)
            self.assertNotIn("lane_db_canon_probe", tables)

    # ---- UNEXPLAINED: the negatives that give the gate its value ----------

    def test_a_hand_edited_database_with_a_tidy_ledger_is_unexplained(self):
        """The scenario the whole module exists for.

        Nothing about this database's LEDGER is wrong -- it matches the repo
        exactly -- and it passes ``integrity_check``.  Only the absence of a
        snapshot recording the canonical state entering a migration separates
        it from the explained case, and that has to be enough.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            hand = sqlite3.connect(store.path)
            hand.execute(
                "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                ("edited_by_hand", "2026-09-01T22:00:00Z"),
            )
            hand.commit()
            hand.close()
            self.assertNotEqual(canon, gate.database_sha256(store.path))
            verdict = gate.classify(store.path, MIGRATIONS, canon)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertEqual(13, verdict.exit_code)
            self.assertIn("not evidence", verdict.reason)
            self.assertIsNone(verdict.new_canon_sha)

    def test_a_snapshot_of_a_different_starting_sha_is_not_evidence(self):
        """A snapshot proves a migration ran; it proves it ran FROM the
        canonical state only if the state it copied hashed to that sha."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            wrong = "a" * 64
            verdict = gate.classify(store.path, later, wrong, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("not the expected", json.dumps(verdict.evidence))

    def test_a_snapshot_of_another_database_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            self._rewrite_manifest(
                backups,
                source_fingerprint=dict(
                    json.loads(self._manifest_path(backups).read_text())[
                        "source_fingerprint"
                    ],
                    path=str(Path(tmp) / "some_other.sqlite3"),
                ),
            )
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("not of the database being judged", json.dumps(verdict.evidence))

    def test_a_truncated_snapshot_is_not_evidence(self):
        """A backup nobody has opened is a claim, not a backup -- and the day
        the gate quotes it is the day it has to be re-proved."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            manifest = json.loads(self._manifest_path(backups).read_text())
            copy = self._manifest_path(backups).parent / manifest["snapshot_database"]
            with copy.open("r+b") as handle:
                handle.truncate(copy.stat().st_size // 3)
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("no longer the size", json.dumps(verdict.evidence))

    def test_a_snapshot_corrupted_without_changing_size_is_not_evidence(self):
        """The size check is the cheap one; the hash is the one that catches a
        bad sector that kept the file length."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            manifest = json.loads(self._manifest_path(backups).read_text())
            copy = self._manifest_path(backups).parent / manifest["snapshot_database"]
            blob = bytearray(copy.read_bytes())
            middle = len(blob) // 2
            # XOR rather than zero: a fresh SQLite file has zero-filled
            # padding, so writing zeros into it can leave the bytes -- and the
            # hash -- unchanged, which is how this test first passed for the
            # wrong reason.
            blob[middle : middle + 64] = bytes(
                b ^ 0xFF for b in blob[middle : middle + 64]
            )
            copy.write_bytes(bytes(blob))
            self.assertEqual(len(blob), manifest["verification"]["bytes"])
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("no longer hashes", json.dumps(verdict.evidence))

    def test_a_snapshot_taken_for_a_reason_other_than_a_pending_migration_is_not_evidence(self):
        """``persistence_backup`` also snapshots when the ledger cannot be read
        or the journal mode is about to be rewritten.  Those copies say
        "something was about to happen", not "a migration ran"."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            for pending, expected_reason in (
                # An empty list is only evidence when the manifest ALSO says
                # the boot was about to rewrite the database in place; this
                # snapshot's reason says a migration was pending, so an empty
                # list contradicts it.
                ([], "not an in-place rewrite"),
                (None, "not a list of versions"),
                ("900", "not a list of versions"),
                ([True], "not a list of versions"),
            ):
                with self.subTest(pending_versions=pending):
                    self._rewrite_manifest(backups, pending_versions=pending)
                    verdict = self._verdict(store, canon, later, backups)
                    self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
                    self.assertIn(expected_reason, json.dumps(verdict.evidence))

    def test_an_unfinished_snapshot_directory_is_never_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            directory = self._manifest_path(backups).parent
            directory.rename(
                directory.with_name(directory.name + persistence_backup.INCOMPLETE_SUFFIX)
            )
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)

    def test_a_manifest_cannot_offer_the_live_database_as_its_own_backup(self):
        """A manifest is a file on disk; its ``snapshot_database`` name is
        attacker-shaped input and is never joined as given."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            directory = self._manifest_path(backups).parent
            relative = os.path.relpath(Path(store.path).resolve(), directory)
            self._rewrite_manifest(backups, snapshot_database=relative)
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("unsafe snapshot name", json.dumps(verdict.evidence))

    def test_a_manifest_of_an_unknown_kind_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            self._rewrite_manifest(backups, kind="pf.something.else.v9")
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("manifest kind", json.dumps(verdict.evidence))

    def test_a_migration_in_the_repo_that_was_never_applied_is_unexplained(self):
        """The sha moved AND the boot did not finish its migrations: whatever
        changed the file, it was not a completed migration run."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            # ``later`` already holds 900, which IS applied; add one more that
            # the database has never seen.
            further = later
            (further / "901_lane_db_canon_probe_two.sql").write_text(
                "CREATE TABLE lane_db_canon_probe_two(id INTEGER PRIMARY KEY);\n",
                encoding="utf-8",
            )
            verdict = gate.classify(store.path, further, canon, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertEqual([901], verdict.evidence["ledger"]["not_applied"])

    def test_a_database_newer_than_this_server_is_unexplained(self):
        """The same refusal ``SQLiteStore.migrate`` raises, as a verdict."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            # Judge the migrated database against the repo's own (shorter)
            # migration set: version 900 is now applied but unknown to it.
            verdict = gate.classify(store.path, MIGRATIONS, canon, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertEqual([900], verdict.evidence["ledger"]["unknown_to_repo"])

    def test_a_migration_file_edited_after_it_was_applied_is_unexplained(self):
        """The lane charter forbids editing an applied migration; a gate that
        waved this through would let the file that produced the schema and the
        schema itself drift apart silently."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            edited = later / "900_lane_db_canon_probe.sql"
            edited.write_text(PROBE_SQL + "-- edited after apply\n", encoding="utf-8")
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertEqual([900], verdict.evidence["ledger"]["checksum_mismatch"])

    def test_an_unreadable_ledger_is_unexplained_and_never_read_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            Path(store.path).write_bytes(b"this is not a database at all")
            self.assertIsNone(gate.read_ledger(store.path))
            verdict = gate.classify(store.path, MIGRATIONS, canon)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("could not be read", verdict.reason)

    def test_a_database_that_fails_integrity_check_is_never_explained(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            with mock.patch.object(
                gate, "integrity_check", return_value="*** in database main ***"
            ):
                verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("integrity_check", verdict.reason)

    def test_a_snapshot_whose_pending_migration_never_landed_is_unexplained(self):
        """A snapshot says a migration was ABOUT to run.  If the ledger does
        not show it applied, the run died in the middle and the file moved for
        some other reason."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            # 902 was never a file in the repo, so the LEDGER check passes
            # cleanly and the snapshot-specific branch is the one that fires.
            self._rewrite_manifest(backups, pending_versions=[900, 902])
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("did not finish", verdict.reason)

    # ---- the gate must not touch what it judges ---------------------------

    def test_judging_a_database_with_a_hot_wal_changes_nothing_it_judges(self):
        """``persistence_backup._verify_snapshot`` DELETES the sidecars beside
        the file it verifies -- correct for a copy that must be
        self-contained, catastrophic if it were ever pointed at the live
        database.  This gate opens the live file read-only and unlinks
        nothing.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            live = Path(store.path)
            holder = sqlite3.connect(str(live))
            holder.execute("PRAGMA journal_mode=WAL")
            holder.execute(
                "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                ("committed_into_the_wal", "2026-09-01T22:30:00Z"),
            )
            holder.commit()
            try:
                wal = live.with_name(live.name + "-wal")
                shm = live.with_name(live.name + "-shm")
                self.assertTrue(wal.is_file() and wal.stat().st_size)
                self.assertTrue(
                    shm.is_file(),
                    "a live connection is holding the WAL index open, which is "
                    "the state this test needs",
                )
                before = (live.read_bytes(), wal.read_bytes())
                names_before = sorted(p.name for p in live.parent.iterdir())
                gate.classify(live, later, canon, backups)
                # Byte comparison AND a directory listing: the first draft of
                # this test compared only bytes, and three separate mutants
                # that DELETED files beside the database passed it unnoticed
                # (pf-adversary, round `gfkvro`, defect 5).
                self.assertEqual(
                    names_before, sorted(p.name for p in live.parent.iterdir()),
                    "a gate run must not remove a file beside the live database",
                )
                self.assertTrue(wal.is_file(), "the live -wal must still exist")
                self.assertTrue(shm.is_file(), "the live -shm must still exist")
                self.assertEqual(before, (live.read_bytes(), wal.read_bytes()))
            finally:
                holder.close()

    def test_the_database_is_hashed_before_this_module_opens_anything(self):
        """The docstring's ordering claim, proved rather than asserted.

        A read-only probe of a WAL database makes SQLite rebuild the ``-shm``
        index beside it, so "we opened it first" would not show up in the sha
        -- which is exactly why an unproved ordering claim in a docstring is
        worthless here.  The order is therefore measured directly.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            order = []
            real_hash, real_open = gate._sha256_file, gate._read_only_connection

            def hashing(path):
                order.append(("hash", str(path)))
                return real_hash(path)

            def opening(path):
                order.append(("open", str(path)))
                return real_open(path)

            with mock.patch.object(gate, "_sha256_file", hashing), \
                    mock.patch.object(gate, "_read_only_connection", opening):
                gate.classify(store.path, later, canon, backups)
            live = str(Path(store.path))
            touching_live = [step for step in order if step[1] == live]
            self.assertTrue(touching_live, order)
            self.assertEqual(("hash", live), touching_live[0])

    def test_the_verdict_is_about_the_bytes_that_were_on_disk(self):
        """The database is hashed before this module opens anything, so the
        observed sha is the one a caller hashing the same file would get."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(
                gate.database_sha256(store.path), verdict.observed_sha
            )

    # ---- reading the expected sha ----------------------------------------

    def test_the_real_canon_sha_file_of_the_bridge_is_readable_as_written(self):
        """The format this gate has to accept is not hypothetical: it is the
        upper-case single line the bridge keeps today.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "CANON_SHA.txt"
            path.write_text(
                "4FF37060D3A2E876A41A479A348E062557D6C2FA2FF355548FAF81830A548454\n",
                encoding="utf-8",
            )
            self.assertEqual(
                "4ff37060d3a2e876a41a479a348e062557d6c2fa2ff355548faf81830a548454",
                gate.read_expected_sha(path),
            )

    def test_an_expected_sha_file_with_two_digests_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "CANON_SHA.txt"
            path.write_text("%s\n%s\n" % ("a" * 64, "b" * 64), encoding="utf-8")
            with self.assertRaises(gate.CanonGateError):
                gate.read_expected_sha(path)

    def test_a_garbage_expected_sha_is_refused_rather_than_compared(self):
        for value in ("", "not a sha", "a" * 63, "g" * 64):
            with self.subTest(value=value):
                with self.assertRaises(gate.CanonGateError):
                    gate.normalise_sha(value)

    def test_a_missing_database_is_a_gate_error_not_an_outcome(self):
        """"I could not look" is not "I looked and it was fine"."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(gate.CanonGateError):
                gate.classify(Path(tmp) / "nothing.sqlite3", MIGRATIONS, "a" * 64)

    def test_a_missing_migrations_directory_is_a_gate_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            with self.assertRaises(gate.CanonGateError):
                gate.classify(store.path, Path(tmp) / "nope", "a" * 64)

    # ---- the CLI contract the ps1 caller will depend on -------------------

    def _run_cli(self, *argv):
        import io

        out, err = io.StringIO(), io.StringIO()
        code = gate.main([str(a) for a in argv], stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def test_cli_exit_codes_are_the_three_the_coo_decision_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            now = gate.database_sha256(store.path)

            code, out, _ = self._run_cli(
                "--db", store.path, "--migrations", later,
                "--expect-sha", now, "--backups-root", backups,
            )
            self.assertEqual(0, code)
            self.assertIn("CANON_GATE UNCHANGED", out)

            code, out, _ = self._run_cli(
                "--db", store.path, "--migrations", later,
                "--expect-sha", canon, "--backups-root", backups,
            )
            self.assertEqual(gate.EXIT_CODE[gate.EXPLAINED_BY_MIGRATION], code)
            self.assertIn(gate.NEW_SHA_TOKEN + now.upper(), out)

            code, out, _ = self._run_cli(
                "--db", store.path, "--migrations", later,
                "--expect-sha", "a" * 64, "--backups-root", backups,
            )
            self.assertEqual(13, code)
            self.assertIn("CANON_GATE UNEXPLAINED", out)
            self.assertNotIn(gate.NEW_SHA_TOKEN, out)

    def test_cli_reads_the_expected_sha_from_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            path = Path(tmp) / "CANON_SHA.txt"
            path.write_text(canon.upper() + "\n", encoding="utf-8")
            code, out, _ = self._run_cli(
                "--db", store.path, "--migrations", later,
                "--expect-sha-file", path, "--backups-root", backups,
            )
            self.assertEqual(75, code)

    def test_cli_json_output_carries_the_whole_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            code, out, _ = self._run_cli(
                "--db", store.path, "--migrations", later,
                "--expect-sha", canon, "--backups-root", backups, "--json",
            )
            payload = json.loads(out)
            self.assertEqual(75, code)
            self.assertEqual(gate.EXPLAINED_BY_MIGRATION, payload["outcome"])
            self.assertEqual(75, payload["exit_code"])
            self.assertEqual(gate.database_sha256(store.path), payload["new_canon_sha"])

    def test_cli_usage_failures_are_never_one_of_the_three_outcomes(self):
        """A caller must not be able to read "the gate crashed" as "pass"."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            code, _, err = self._run_cli(
                "--db", Path(tmp) / "nothing.sqlite3",
                "--migrations", MIGRATIONS, "--expect-sha", "a" * 64,
            )
            self.assertEqual(gate.EXIT_USAGE, code)
            self.assertNotIn(code, (0, 20))
            self.assertIn("COULD NOT RUN", err)

            code, _, _ = self._run_cli("--db", store.path)
            self.assertEqual(2, code)

    def test_cli_refuses_both_expected_sha_forms_at_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            code, _, _ = self._run_cli(
                "--db", store.path, "--migrations", MIGRATIONS,
                "--expect-sha", "a" * 64, "--expected-sha-file", "x",
            )
            self.assertEqual(2, code)

    def test_the_module_runs_as_a_module_from_a_shell(self):
        """The ps1 caller will invoke it exactly this way, so the entry point
        is proved through a real subprocess, not only through ``main()``."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
            done = subprocess.run(
                [sys.executable, "-m",
                 "pirateforce_foundation.persistence_canon_gate",
                 "--db", str(store.path), "--migrations", str(later),
                 "--expect-sha", canon, "--backups-root", str(backups)],
                capture_output=True, text=True, env=env, timeout=120,
            )
            self.assertEqual(75, done.returncode, done.stderr)
            self.assertIn(gate.NEW_SHA_TOKEN, done.stdout)

    # ---- the exit codes themselves ---------------------------------------

    def test_the_three_outcomes_map_to_0_75_13_and_nothing_else(self):
        """75 rather than the 20 this lane first proposed to chief.

        pf-adversary (round `gfkvro`, defect 11) measured the collision: 20 is
        already `THIS ROUND IS DEGRADED, NOT GREEN` in
        `staged/TEMPLATE_teardown_generic.ps1` and `ABORT: no server PID` in
        `staged/072_gt001_boot.ps1`.  Re-derived here rather than trusted: the
        codes are asserted against the dict, and the letter to chief carries
        the ps1 measurement.
        """
        self.assertEqual(
            {gate.UNCHANGED: 0, gate.EXPLAINED_BY_MIGRATION: 75, gate.UNEXPLAINED: 13},
            gate.EXIT_CODE,
        )
        self.assertEqual(3, len(gate.EXIT_CODE))
        self.assertNotIn(gate.EXIT_USAGE, gate.EXIT_CODE.values())


if __name__ == "__main__":
    unittest.main()


class AdversaryFindingsTest(CanonGateTest):
    """Every defect pf-adversary measured against this module's first draft
    (round `gfkvro`), turned into a test that fails on the old behaviour.

    The review is in this round's file,
    ``pf_bridge/rounds/DB_20260901_2213_gfkvro_canon-gate-lands.md``.  These
    are kept apart from the tests above because they are not statements about
    what the gate is FOR -- they are the receipts for defects that were real,
    reproduced, and are the reason the module has the shape it has.
    """

    # ---- D1: laundering a hand-edited database with a written manifest ----

    def _plant_forged_snapshot(self, tmp, live, claimed_pre_sha, **overrides):
        """The reviewer's attack, verbatim: a directory, a copy of the live
        database, and a hand-written manifest naming the published canon sha.
        """
        root = Path(tmp) / "db_backups"
        directory = root / "29991231T235959000000Z_premigration_pirateforce"
        directory.mkdir(parents=True)
        copy = directory / Path(live).name
        copy.write_bytes(Path(live).read_bytes())
        manifest = {
            "kind": "pf.lane_db.premigration_snapshot.v1",
            "snapshot_database": copy.name,
            "pending_versions": [1],
            "source_fingerprint": {
                "path": str(Path(live).resolve()),
                "sha256": claimed_pre_sha,
                "bytes": Path(live).stat().st_size,
                "sidecars": [],
            },
            "verification": {
                "integrity_check": "ok",
                "sha256": gate.database_sha256(copy),
                "bytes": copy.stat().st_size,
            },
        }
        manifest.update(overrides)
        (directory / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        return root, directory

    def test_d1_a_forged_manifest_over_a_hand_edited_database_is_refused(self):
        """pf-adversary D1, MEASURED against the first draft: this exact
        recipe returned EXPLAINED_BY_MIGRATION and printed the hand-edited
        database's sha as the value to rotate to.

        What refuses it now is the one condition whose evidence is not a
        number in a JSON file: the copy claims migration 1 was pending, and
        its own ``schema_migrations`` already contains 1.  (The forgery also
        has no POSTSTATE, which is checked first -- both are asserted below,
        so removing either check alone fails this test.)
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            hand = sqlite3.connect(store.path)
            hand.execute(
                "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                ("i_gave_myself_everything", "2026-09-01T22:00:00Z"),
            )
            hand.commit()
            hand.close()
            root, directory = self._plant_forged_snapshot(tmp, store.path, canon)

            verdict = gate.classify(store.path, MIGRATIONS, canon, root)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertEqual(13, verdict.exit_code)
            self.assertIsNone(verdict.new_canon_sha)
            self.assertIn("POSTSTATE.", json.dumps(verdict.evidence))

            # ... and with a POSTSTATE forged too, the ledger inside the copy
            # is what still refuses it.
            (directory / persistence_backup.poststate_filename(
                gate.database_sha256(store.path)
            )).write_text(
                json.dumps(
                    {
                        "kind": "pf.lane_db.post_migration_state.v1",
                        "source_database": str(Path(store.path).resolve()),
                        "post_migration_sha256": gate.database_sha256(store.path),
                    }
                ),
                encoding="utf-8",
            )
            verdict = gate.classify(store.path, MIGRATIONS, canon, root)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("not a pre-migration copy", json.dumps(verdict.evidence))

    # ---- D2: the blessing window that never closed -------------------------

    def test_d2_one_real_migration_does_not_bless_every_later_edit(self):
        """pf-adversary D2, MEASURED against the first draft with NO forged
        input at all: after one legitimate migration, a hand INSERT and then a
        hand DELETE of every account both still came out
        ``EXPLAINED_BY_MIGRATION`` -- the world wiped and the gate saying
        "rotate".  ``POSTSTATE.json`` is what closes it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            self.assertEqual(
                gate.EXPLAINED_BY_MIGRATION,
                self._verdict(store, canon, later, backups).outcome,
                "the legitimate migration must still be explained",
            )
            for name, sql in (
                ("a hand INSERT", "INSERT INTO accounts(login_name,created_at) "
                                  "VALUES ('helped_myself','2026-09-01T23:00:00Z')"),
                ("a hand DELETE of every account", "DELETE FROM accounts"),
            ):
                with self.subTest(edit=name):
                    hand = sqlite3.connect(store.path)
                    hand.execute(sql)
                    hand.commit()
                    hand.close()
                    verdict = self._verdict(store, canon, later, backups)
                    self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
                    # No boot ever recorded producing THESE bytes, so no
                    # note with this sha in its name exists.
                    self.assertIn(
                        "no boot recorded producing",
                        json.dumps(verdict.evidence),
                    )

    def test_the_post_state_note_records_the_sha_the_migration_produced(self):
        """The mechanism D2's fix rests on, proved on its own."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            note = json.loads(
                self._poststate_path(
                    backups, gate.database_sha256(store.path)
                ).read_text()
            )
            self.assertEqual(
                persistence_backup.POSTSTATE_KIND, note["kind"]
            )
            self.assertEqual(
                gate.database_sha256(store.path), note["post_migration_sha256"]
            )
            self.assertNotEqual(canon, note["post_migration_sha256"])
            self.assertEqual([900], note["versions_applied_by_this_run"])

    def test_a_post_state_note_is_never_overwritten(self):
        """``persistence_backup`` rule 3, on the newest file it writes: a
        second boot must not be able to re-bless a file the first never saw.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            note = self._poststate_path(backups, gate.database_sha256(store.path))
            before = note.read_bytes()
            self.assertIsNone(
                persistence_backup.record_post_migration_state(
                    self._manifest_path(backups).parent / "pirateforce.sqlite3",
                    store.path,
                    [1],
                )
            )
            self.assertEqual(before, note.read_bytes())

    def test_a_failure_to_write_the_post_state_note_never_breaks_a_boot(self):
        """The migration has already happened when the note is written, so a
        note that cannot be written must not raise -- the gate then answers
        UNEXPLAINED, which is the fail-closed direction."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            later = self._migrations_plus(tmp)
            store.migrations = later
            backups = Path(tmp) / "db_backups"
            real_open = os.open

            def only_the_note_fails(path, *args, **kwargs):
                if persistence_backup.POSTSTATE_PREFIX in str(path):
                    raise OSError("disk full")
                return real_open(path, *args, **kwargs)

            with mock.patch.object(os, "open", side_effect=only_the_note_fails):
                snapshot = store.migrate_with_backup(backups_root=backups)
            self.assertIsNotNone(snapshot, "the boot must still return its snapshot")
            self.assertEqual(
                [1, 2, 3, 4, 5, 6, 900],
                sorted(gate.read_ledger(store.path)),
                "the migration must have run even though the note could not be written",
            )
            self.assertFalse(
                any(
                    Path(snapshot).parent.glob(
                        persistence_backup.POSTSTATE_PREFIX + "*"
                    )
                )
            )
            # ... and the gate then falls back to UNEXPLAINED, the fail-closed
            # direction: no note, no evidence.
            self.assertEqual(
                gate.UNEXPLAINED,
                gate.classify(store.path, later, canon, backups).outcome,
            )

    def test_a_post_state_note_about_another_database_is_not_evidence(self):
        """The note names the database it is about, and that is checked: a
        POSTSTATE copied in from another machine's backups explains nothing
        about this file."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            note = self._poststate_path(backups, gate.database_sha256(store.path))
            payload = json.loads(note.read_text())
            payload["source_database"] = str(Path(tmp) / "someone_elses.sqlite3")
            note.write_text(json.dumps(payload), encoding="utf-8")
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("about another database", json.dumps(verdict.evidence))

    def test_a_snapshot_that_hashes_right_but_fails_integrity_is_not_evidence(self):
        """The hash proves the file did not change since the manifest was
        written; only opening it proves it is still a database.  Both are
        needed -- a damaged backup that somebody re-hashed passes the first
        and must still be refused.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            directory = self._manifest_path(backups).parent
            manifest = json.loads(self._manifest_path(backups).read_text())
            copy = directory / manifest["snapshot_database"]
            blob = bytearray(copy.read_bytes())
            # Damage the first page after the header.  Measured: SQLite then
            # refuses the read outright rather than returning a verdict, which
            # is the branch this exercises; the "SQLite walks it and reports
            # damage" branch is covered by the stub test below, because
            # producing that on demand is not reproducible.
            blob[4096:4396] = bytes(b ^ 0x5A for b in blob[4096:4396])
            copy.write_bytes(bytes(blob))
            manifest["verification"]["sha256"] = gate.database_sha256(copy)
            manifest["verification"]["bytes"] = copy.stat().st_size
            self._manifest_path(backups).write_text(
                json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
            )
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("the snapshot cannot be", json.dumps(verdict.evidence))

    def test_a_snapshot_sqlite_itself_calls_damaged_is_not_evidence(self):
        """The other half of the check above: SQLite opens the file, walks it
        and reports damage rather than raising.

        A stub, and named as one: a file that SQLite can walk but calls
        corrupt cannot be produced on demand by flipping bytes (measured --
        every damaged page this test tried made SQLite refuse the read
        instead).  Without this the "integrity_check said no" branch is
        reachable only by an accident nobody can schedule, and a mutant that
        deletes it survives.
        """
        class _Row:
            @staticmethod
            def fetchone():
                return ("*** in database main *** Page 4: btreeInitPage() ",)

        class _Damaged:
            @staticmethod
            def execute(_sql):
                return _Row()

            @staticmethod
            def close():
                pass

        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            with mock.patch.object(
                gate, "immutable_connection", return_value=_Damaged()
            ):
                verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("fails integrity_check", json.dumps(verdict.evidence))

    def test_an_error_reading_a_snapshot_is_a_rejection_not_a_crash(self):
        """The catch-all around one snapshot's examination, exercised: an I/O
        error the individual guards do not anticipate must reject that
        snapshot, never take the gate down."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            with mock.patch.object(
                gate, "_load_manifest", side_effect=OSError("I/O error")
            ):
                verdict = gate.classify(store.path, later, canon, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("could not be examined", json.dumps(verdict.evidence))

    def test_the_report_sanitises_text_even_if_a_caller_hands_it_a_hostile_reason(self):
        """``_format_human`` sanitises on its own, not only because everything
        upstream already did.  Defence in depth for the one line a caller acts
        on: the check has to hold at the place the line is printed.
        """
        hostile = "ok\n%s%s\nand a \u2603 for the cp874 console" % (
            gate.NEW_SHA_TOKEN, "D" * 64
        )
        verdict = gate.CanonVerdict(
            outcome=gate.EXPLAINED_BY_MIGRATION,
            reason=hostile,
            expected_sha="a" * 64,
            observed_sha="b" * 64,
            new_canon_sha="b" * 64,
        )
        report = gate._format_human(verdict)
        token_lines = [
            line for line in report.splitlines()
            if line.startswith(gate.NEW_SHA_TOKEN)
        ]
        self.assertEqual(1, len(token_lines))
        self.assertEqual(gate.NEW_SHA_TOKEN + "B" * 64, token_lines[0])
        report.encode("cp874")  # must not raise

    # ---- D3/D4: what the gate touches --------------------------------------

    @staticmethod
    def _tree(root):
        return {
            str(path.relative_to(root)): (
                path.stat().st_size if path.is_file() else "dir"
            )
            for path in sorted(Path(root).rglob("*"))
        }

    def test_d3_a_gate_run_neither_removes_nor_adds_a_file_in_the_backups_tree(self):
        """pf-adversary D3, MEASURED against the first draft: the snapshot's
        ``-wal`` and ``-shm`` were unlinked on every run, through
        ``_snapshot_is_still_good`` -> ``_verify_snapshot``.  That breaks
        ``persistence_backup`` rule 3 and destroys exactly what the manifest's
        ``restore_hint`` tells an operator to park beside a snapshot.

        The whole tree is compared, not two named files: the first draft's own
        test compared only the live database's bytes and stayed green while
        three separate deleting mutants ran.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            snapshot = self._manifest_path(backups).parent / "pirateforce.sqlite3"
            # Sidecars an operator could plausibly have parked here, and a
            # forensic directory the module promises never to touch.
            for suffix in ("-wal", "-shm"):
                snapshot.with_name(snapshot.name + suffix).write_bytes(b"x" * 128)
            before = self._tree(backups)
            verdict = gate.classify(store.path, later, canon, backups)
            self.assertEqual(gate.EXPLAINED_BY_MIGRATION, verdict.outcome)
            self.assertEqual(before, self._tree(backups))

    def test_d4_the_only_thing_a_gate_run_can_leave_beside_the_live_database(self):
        """pf-adversary D4, MEASURED: read-only opens of a hot-WAL database
        make SQLite build a ``-shm`` index beside it.  The first draft's
        docstring said the module "writes nothing", which was false; the claim
        is now narrow and this test is what keeps it honest -- the main file
        and the ``-wal`` are byte-identical, and ``-shm`` is the ONLY name that
        may appear.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            live = Path(store.path)
            holder = sqlite3.connect(str(live))
            holder.execute("PRAGMA journal_mode=WAL")
            holder.execute(
                "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
                ("committed_into_the_wal", "2026-09-01T23:30:00Z"),
            )
            holder.commit()
            holder.close()
            shm = live.with_name(live.name + "-shm")
            if shm.exists():
                shm.unlink()
            before = self._tree(live.parent)
            frozen = {
                name: (live.parent / name).read_bytes()
                for name in before
                if not name.endswith("-shm")
            }
            gate.classify(live, later, canon, backups)
            # Run it a second time: the first run is what creates the -shm, so
            # only a second run can show whether an EXISTING one survives.  A
            # gate that unlinked it after every integrity check passed the
            # single-run version of this test unnoticed.
            middle = self._tree(live.parent)
            gate.classify(live, later, canon, backups)
            after = self._tree(live.parent)
            self.assertEqual(
                sorted(middle), sorted(after),
                "a second gate run must neither create nor remove anything",
            )
            appeared = set(after) - set(before)
            self.assertEqual([], sorted(set(before) - set(after)), "nothing removed")
            # A database whose header says WAL gets both index files rebuilt
            # by a read-only attach.  Both are derived, and the -wal that
            # appears must be EMPTY: an empty write-ahead log holds no
            # transaction, so nothing about the database's content moved.
            self.assertTrue(
                appeared <= {live.name + "-shm", live.name + "-wal"},
                "a gate run may only ever leave SQLite's own index files "
                "beside the live database, found: %s" % sorted(appeared),
            )
            for name in appeared:
                if name.endswith("-wal"):
                    self.assertEqual(
                        0, after[name], "a gate run must not leave a NON-EMPTY -wal"
                    )
            for name, blob in frozen.items():
                self.assertEqual(blob, (live.parent / name).read_bytes(), name)

    # ---- D6: the rotation the design mandates ------------------------------

    def test_d6_the_expected_sha_file_is_read_in_the_encodings_powershell_writes(self):
        """pf-adversary D6, MEASURED against the first draft: PowerShell 5.1's
        ``>`` and ``Out-File`` write UTF-16LE, which raised
        ``UnicodeDecodeError`` -- a ``ValueError``, caught by nothing -- so the
        FIRST successful rotation would have bricked the gate with a traceback
        and exit 1.
        """
        digest = "4FF37060D3A2E876A41A479A348E062557D6C2FA2FF355548FAF81830A548454"
        cases = {
            "ascii + CRLF (what the bridge has today)": digest.encode("ascii") + b"\r\n",
            "utf-8 with BOM": b"\xef\xbb\xbf" + digest.encode("ascii") + b"\r\n",
            "utf-16le with BOM (PowerShell 5.1 '>')": (digest + "\r\n").encode("utf-16-le"),
            "utf-16le without BOM": (digest + "\r\n").encode("utf-16-le"),
            "utf-16be with BOM": b"\xfe\xff" + (digest + "\r\n").encode("utf-16-be"),
        }
        cases["utf-16le with BOM (PowerShell 5.1 '>')"] = (
            b"\xff\xfe" + (digest + "\r\n").encode("utf-16-le")
        )
        with tempfile.TemporaryDirectory() as tmp:
            for name, blob in cases.items():
                with self.subTest(encoding=name):
                    path = Path(tmp) / "CANON_SHA.txt"
                    path.write_bytes(blob)
                    self.assertEqual(digest.lower(), gate.read_expected_sha(path))

    def test_an_undecodable_expected_sha_file_is_a_named_refusal_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "CANON_SHA.txt"
            path.write_bytes(b"\xff\xfe\x00")
            with self.assertRaises(gate.CanonGateError):
                gate.read_expected_sha(path)

    # ---- D7: nothing escapes as exit 1 -------------------------------------

    def test_d7_attacker_shaped_manifests_never_crash_the_gate(self):
        """pf-adversary D7, MEASURED: a NUL byte in a manifest's path raised
        ``ValueError`` out of ``Path().resolve()`` and the process exited 1 --
        which every ps1 guard branching on 13 reads as "not 13"."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            good_manifest = self._manifest_path(backups).read_text()
            for name, change in (
                ("a NUL byte in the source path",
                 {"source_fingerprint": {"path": "/tmp/a\x00b", "sha256": canon,
                                         "bytes": 1, "sidecars": []}}),
                ("a manifest that is a list, not an object", None),
                ("pending_versions of an unusable type", {"pending_versions": {"a": 1}}),
                ("a source fingerprint that is a string", {"source_fingerprint": "no"}),
            ):
                with self.subTest(manifest=name):
                    path = self._manifest_path(backups)
                    # Restore the real manifest first: a previous subtest may
                    # have replaced it with something that is not an object.
                    path.write_text(good_manifest, encoding="utf-8")
                    if change is None:
                        path.write_text("[1,2,3]", encoding="utf-8")
                    else:
                        self._rewrite_manifest(backups, **change)
                    verdict = gate.classify(store.path, later, canon, backups)
                    self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
                    self.assertEqual(13, verdict.exit_code)

    def test_d7_an_unlistable_backups_directory_is_a_verdict_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            with mock.patch.object(
                Path, "iterdir", side_effect=PermissionError("denied")
            ):
                code, _, err = self._run_cli(
                    "--db", store.path, "--migrations", later,
                    "--expect-sha", canon, "--backups-root", backups,
                )
            self.assertEqual(13, code)

    def test_an_unexpected_exception_is_never_read_as_a_pass(self):
        """A gate that dies must not be able to exit 0 or the explained code."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            with mock.patch.object(
                gate, "classify", side_effect=RuntimeError("something unforeseen")
            ):
                code, _, err = self._run_cli(
                    "--db", store.path, "--migrations", MIGRATIONS,
                    "--expect-sha", "a" * 64,
                )
            self.assertEqual(gate.EXIT_USAGE, code)
            self.assertNotIn(code, gate.EXIT_CODE.values())
            self.assertIn("CRASHED", err)

    def test_every_gate_error_message_maps_to_the_same_non_passing_code(self):
        """pf-adversary D5 mutant 11: the first draft's only error-path test
        used one message, so a branch returning 0 for an error whose text
        contained a particular word survived undetected."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            for message in ("migration", "unchanged", "ok", "", "explained"):
                with self.subTest(message=message):
                    with mock.patch.object(
                        gate, "classify",
                        side_effect=gate.CanonGateError(message),
                    ):
                        code, _, _ = self._run_cli(
                            "--db", store.path, "--migrations", MIGRATIONS,
                            "--expect-sha", "a" * 64,
                        )
                    self.assertEqual(gate.EXIT_USAGE, code)

    # ---- D8/D9: the line the caller acts on --------------------------------

    def test_d8_a_snapshot_name_cannot_forge_the_machine_readable_line(self):
        """pf-adversary D8, MEASURED on Linux: a snapshot directory named with
        an embedded newline and a ``NEW_SHA=`` payload put an attacker-chosen
        line AHEAD of the real one, and a caller taking the first match would
        have rotated ``CANON_SHA.txt`` to it."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            directory = self._manifest_path(backups).parent
            payload = "zz\n%s%s\n_x" % (gate.NEW_SHA_TOKEN, "D" * 64)
            directory.rename(directory.with_name(payload))
            code, out, _ = self._run_cli(
                "--db", store.path, "--migrations", later,
                "--expect-sha", canon, "--backups-root", backups,
            )
            token_lines = [
                line for line in out.splitlines()
                if line.startswith(gate.NEW_SHA_TOKEN)
            ]
            self.assertEqual(1, len(token_lines), out)
            self.assertNotIn("D" * 64, token_lines[0])
            self.assertEqual(
                gate.NEW_SHA_TOKEN + gate.database_sha256(store.path).upper(),
                token_lines[0],
            )
            self.assertEqual(75, code)

    def test_d9_a_console_that_cannot_encode_a_path_still_gets_the_verdict(self):
        """pf-adversary D9, MEASURED: one character with no cp874 mapping in a
        snapshot name killed ``print()`` AFTER the verdict was computed, so a
        decided UNEXPLAINED exited 1."""
        import io

        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            directory = self._manifest_path(backups).parent
            directory.rename(directory.with_name("snapshot_\u2603_x"))
            narrow = io.TextIOWrapper(io.BytesIO(), encoding="cp874", errors="strict")
            code = gate.main(
                ["--db", str(store.path), "--migrations", str(later),
                 "--expect-sha", canon, "--backups-root", str(backups)],
                stdout=narrow, stderr=narrow,
            )
            self.assertIn(code, (13, 75))

    # ---- D10: --help is not a pass ----------------------------------------

    def test_d10_help_does_not_exit_like_a_gate_that_passed(self):
        """pf-adversary D10: ``--help`` returned argparse's 0, which is
        UNCHANGED's code.  An invocation that checked nothing must not be
        indistinguishable from one that checked and passed."""
        for argv in (["--help"], ["-h"]):
            with self.subTest(argv=argv):
                code, _, _ = self._run_cli(*argv)
                self.assertEqual(gate.EXIT_USAGE, code)
                self.assertNotEqual(0, code)

    # ---- D11: the exit code itself -----------------------------------------

    #: Exit codes measured in `pf_bridge/staged/*.ps1` on 2026-09-01 by
    #: LANE-DB round `gfkvro`, across every spelling those scripts use
    #: (`exit N`, `-Code N`, `[Environment]::Exit(N)`, `SetShouldExit(N)`).
    #: Pinned here because `pf_bridge` is NOT part of this repository -- it is
    #: a separate working tree on the owner's machine -- so a CI checkout
    #: cannot re-derive them.  The test below re-derives them anyway when the
    #: bridge IS beside this repo, and goes red if the two disagree.
    MEASURED_BRIDGE_EXIT_CODES = {
        0, 1, 2, 10, 11, 12, 13, 14, 15, 16, 17, 20, 21, 30, 31, 32, 33, 34,
        35, 36, 37, 39, 40, 41, 42, 43, 44, 45, 46, 50, 51, 61, 62, 63, 128,
    }

    def test_d11_the_explained_code_is_not_one_the_bridge_already_uses(self):
        """pf-adversary D11: 20 -- the code this lane first proposed to chief
        -- is already `THIS ROUND IS DEGRADED, NOT GREEN` in
        `staged/TEMPLATE_teardown_generic.ps1` and `ABORT: no server PID` in
        `staged/072_gt001_boot.ps1`.

        DELIBERATELY NOT A `skipTest`.  Second pass, R9: a skip here would be
        silent in exactly the environment where a reviewer reads the commit,
        and this repository's Windows gate counts skips
        (`docs/PYTEST_SKIP_PINS.json` and the `skip_census` step of
        `.github/workflows/gate-windows.yml`) -- a new one is itself a red.
        So the pin above is asserted always, and the live re-derivation is an
        extra check that only runs where it can.
        """
        self.assertNotIn(
            gate.EXIT_CODE[gate.EXPLAINED_BY_MIGRATION],
            self.MEASURED_BRIDGE_EXIT_CODES,
            "the explained code collides with one the bridge already uses",
        )
        self.assertIn(13, self.MEASURED_BRIDGE_EXIT_CODES)
        self.assertIn(20, self.MEASURED_BRIDGE_EXIT_CODES)

        staged = ROOT.parent / "pf_bridge" / "staged"
        if not staged.is_dir():
            return  # not a skip: the pin above has already been asserted
        used = set()
        # Every spelling those scripts use.  Second pass, R9 measured that a
        # bare `exit N` regex misses `Finish178 -Code 13` and about thirty
        # other `-Code <N>` sites, so the pin had a fuse in it.
        pattern = re.compile(
            r"(?:exit|-Code|::Exit\(|SetShouldExit\()\s*(\d+)", re.IGNORECASE
        )
        for script in staged.glob("*.ps1"):
            for match in pattern.finditer(
                script.read_text(encoding="utf-8", errors="replace")
            ):
                used.add(int(match.group(1)))
        self.assertNotIn(
            gate.EXIT_CODE[gate.EXPLAINED_BY_MIGRATION],
            used,
            "a staged script has claimed the explained code since it was "
            "measured; pick another and tell chief",
        )
        unpinned = used - self.MEASURED_BRIDGE_EXIT_CODES
        self.assertEqual(
            set(),
            unpinned,
            "the bridge uses exit codes this pin has never seen (%s); "
            "re-measure and update MEASURED_BRIDGE_EXIT_CODES" % sorted(unpinned),
        )


class SecondAdversaryPassTest(CanonGateTest):
    """The second pass's findings (R1-R11), each as a test that fails on the
    behaviour it measured.

    The first pass made the gate refuse forged EVIDENCE.  The second pass
    asked a better question -- *what is the gate hashing, a file or a
    database?* -- and answered it with two measured inversions: a wiped world
    that came out ``EXPLAINED_BY_MIGRATION`` with a rotate instruction, and a
    real migration that came out ``UNCHANGED``.  Both are one root cause: a
    committed SQLite transaction can live entirely in ``-wal`` and never touch
    the file being hashed.
    """

    def _wal_holder(self, live, name="in_the_wal"):
        """A connection with a committed row SQLite cannot checkpoint away
        while it lives -- the state a running server is in."""
        holder = sqlite3.connect(str(live))
        holder.execute("PRAGMA journal_mode=WAL")
        holder.execute(
            "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
            (name, "2026-09-01T23:45:00Z"),
        )
        holder.commit()
        return holder

    # ---- R1: a wiped world must never be "explained" ----------------------

    def test_r1_a_world_wiped_into_the_wal_is_never_explained(self):
        """pf-adversary R1, MEASURED against the rebuild's first draft: an
        ordinary process deleted every account, committed, and was killed; the
        delete stayed in the ``-wal``, the main file still hashed to what the
        migration had produced, and the gate answered
        ``EXPLAINED_BY_MIGRATION``, exit 75, "rotate to this sha" -- over a
        database with zero accounts in it.

        The precondition is weaker than the documented backups-tree limit:
        this needs only the ability to write the database, which every
        player-facing path already has.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            self.assertEqual(
                gate.EXPLAINED_BY_MIGRATION,
                self._verdict(store, canon, later, backups).outcome,
            )
            before = Path(store.path).read_bytes()
            killer = sqlite3.connect(store.path)
            killer.execute("PRAGMA journal_mode=WAL")
            killer.execute("DELETE FROM accounts")
            killer.commit()
            try:
                # The main file is untouched -- that is the whole trap.
                self.assertEqual(before, Path(store.path).read_bytes())
                verdict = self._verdict(store, canon, later, backups)
                self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
                self.assertEqual(13, verdict.exit_code)
                self.assertIsNone(verdict.new_canon_sha)
                self.assertIn("write-ahead log", verdict.reason)
                self.assertGreater(verdict.evidence["hot_wal_bytes"], 0)
            finally:
                killer.close()

    def test_r1_a_hot_wal_also_blocks_the_unchanged_answer(self):
        """UNCHANGED is the outcome that exits 0, so it is the one that must
        not be reachable over a database whose contents are partly outside the
        file being hashed."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            self.assertEqual(
                gate.UNCHANGED, gate.classify(store.path, MIGRATIONS, canon).outcome
            )
            holder = self._wal_holder(store.path)
            try:
                self.assertEqual(canon, gate.database_sha256(store.path))
                verdict = gate.classify(store.path, MIGRATIONS, canon)
                self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
                self.assertNotEqual(0, verdict.exit_code)
            finally:
                holder.close()

    def test_r1_the_hot_wal_test_of_the_first_pass_now_checks_its_verdict(self):
        """pf-adversary R1: the first pass's own hot-WAL test built exactly
        this state, called ``classify`` and threw the return value away.  What
        it discarded was ``EXPLAINED_BY_MIGRATION``."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            holder = self._wal_holder(Path(store.path))
            try:
                verdict = gate.classify(store.path, later, canon, backups)
                self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            finally:
                holder.close()

    # ---- R2: a real migration must not read as UNCHANGED ------------------

    def test_r2_a_migration_that_is_still_in_the_wal_is_not_unchanged(self):
        """pf-adversary R2, MEASURED: with one extra connection open across
        ``migrate()`` -- a monitoring tool, a lingering server, a concurrent
        boot -- the migration never reached the main file, so the gate said
        UNCHANGED (exit 0) about a database that had just been migrated, and
        then UNEXPLAINED forever once anything checkpointed.

        Both halves are fixed here: the gate refuses while the log is hot, and
        no misleading note is written for a file the migration is not in.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            later = self._migrations_plus(tmp)
            store.migrations = later
            backups = Path(tmp) / "db_backups"
            reader = sqlite3.connect(store.path)
            reader.execute("PRAGMA journal_mode=WAL")
            reader.execute("SELECT count(*) FROM accounts").fetchone()
            try:
                snapshot = store.migrate_with_backup(backups_root=backups)
                self.assertGreater(
                    persistence_backup.hot_wal_bytes(store.path), 0,
                    "the fixture must really leave the migration in the WAL",
                )
                self.assertEqual(canon, gate.database_sha256(store.path))
                verdict = gate.classify(store.path, later, canon, backups)
                self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
                self.assertNotEqual(0, verdict.exit_code)
                # ... and no note was written, so nothing wrong is recorded.
                self.assertEqual(
                    [],
                    sorted(
                        Path(snapshot).parent.glob(
                            persistence_backup.POSTSTATE_PREFIX + "*"
                        )
                    ),
                )
            finally:
                reader.close()

    def test_r2_the_note_is_written_once_the_database_is_quiescent(self):
        """The other side of the refusal above: the supported flow (the server
        stopped, which is step 1 of the canonical upgrade job) does produce a
        note and does come out explained."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            self.assertEqual(0, persistence_backup.hot_wal_bytes(store.path))
            self.assertTrue(
                self._poststate_path(
                    backups, gate.database_sha256(store.path)
                ).is_file()
            )
            self.assertEqual(
                gate.EXPLAINED_BY_MIGRATION,
                self._verdict(store, canon, later, backups).outcome,
            )

    def test_a_note_whose_contents_contradict_its_own_name_is_refused(self):
        """The lookup is by filename, so the sha INSIDE the note is a second,
        independent statement -- and a hand-written note is the only way the
        two can disagree.  Checking it costs one comparison and closes the
        gap where a note's name is the only thing anybody reads.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            observed = gate.database_sha256(store.path)
            note = self._poststate_path(backups, observed)
            payload = json.loads(note.read_text())
            payload["post_migration_sha256"] = "c" * 64
            note.write_text(json.dumps(payload), encoding="utf-8")
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("its name claims", json.dumps(verdict.evidence))

    def test_a_gate_run_that_reaches_a_verdict_still_removes_no_sidecar(self):
        """The deleting-verifier mutants of the first pass could hide inside
        the integrity check, which the hot-WAL refusal now short-circuits in
        the other sidecar tests.  A read-only holder keeps the -shm alive
        WITHOUT putting bytes in the -wal, so the gate runs all the way to a
        verdict with a sidecar present that must survive it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            live = Path(store.path)
            holder = persistence_backup._read_only_connection(live)
            holder.execute("SELECT count(*) FROM accounts").fetchone()
            try:
                shm = live.with_name(live.name + "-shm")
                self.assertTrue(shm.is_file(), "the fixture needs a live -shm")
                self.assertEqual(0, persistence_backup.hot_wal_bytes(live))
                names_before = sorted(p.name for p in live.parent.iterdir())
                verdict = gate.classify(live, later, canon, backups)
                self.assertEqual(gate.EXPLAINED_BY_MIGRATION, verdict.outcome)
                self.assertTrue(shm.is_file(), "the live -shm must survive")
                self.assertEqual(
                    names_before, sorted(p.name for p in live.parent.iterdir())
                )
            finally:
                holder.close()

    # ---- R3: the two shapes the owner's own database is in ----------------

    def test_r3_a_ledger_checksum_upgrade_is_explained_not_refused(self):
        """pf-adversary R3, MEASURED: ``ledger_rewrite_pending``'s own
        docstring says the owner's canonical database is exactly the shape
        that hits it -- a ledger from before the checksum column.  Such a boot
        snapshots with ``pending_versions == []``, which the first rebuild
        rejected outright, so the FIRST boot of the real canonical database
        would have produced an unrecoverable 13 at all twelve bridge guards.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            # Reproduce a pre-checksum ledger exactly as 001_initial.sql made
            # it, then let the runner upgrade it in place.
            strip = sqlite3.connect(store.path)
            strip.executescript(
                "BEGIN;"
                "CREATE TABLE _old(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);"
                "INSERT INTO _old SELECT version, applied_at FROM schema_migrations;"
                "DROP TABLE schema_migrations;"
                "ALTER TABLE _old RENAME TO schema_migrations;"
                "COMMIT;"
            )
            strip.close()
            canon = gate.database_sha256(store.path)
            self.assertTrue(persistence_backup.ledger_rewrite_pending(store.path))
            backups = Path(tmp) / "db_backups"
            snapshot = store.migrate_with_backup(backups_root=backups)
            self.assertIsNotNone(snapshot)
            manifest = json.loads(
                (Path(snapshot).parent / "MANIFEST.json").read_text()
            )
            self.assertEqual([], manifest["pending_versions"])
            self.assertEqual(
                persistence_backup.REASON_LEDGER_REWRITE,
                persistence_backup.reason_code_for(manifest["reason"]),
            )
            verdict = gate.classify(store.path, MIGRATIONS, canon, backups)
            self.assertEqual(gate.EXPLAINED_BY_MIGRATION, verdict.outcome)
            self.assertEqual(75, verdict.exit_code)

    def test_r3_an_empty_pending_list_alone_is_still_not_evidence(self):
        """The relaxation above must not become a hole: a manifest that simply
        omits its pending versions, with a reason that is not an in-place
        rewrite, is still refused."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            self._rewrite_manifest(backups, pending_versions=[], reason="whatever")
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("not an in-place rewrite", json.dumps(verdict.evidence))

    def test_r3_an_in_place_rewrite_claim_is_cross_checked_against_the_copy(self):
        """A hand-written manifest cannot buy the relaxation by claiming the
        rewrite reason: the copy it points at must hold exactly the versions
        the live database holds, which a real pre-migration copy of a
        migrating database does not."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            self._rewrite_manifest(
                backups,
                pending_versions=[],
                reason="no migration file is pending, but the ledger itself is "
                       "about to be rewritten in place (checksum column upgrade)",
            )
            verdict = self._verdict(store, canon, later, backups)
            self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
            self.assertIn("its copy holds versions", json.dumps(verdict.evidence))

    def test_the_reason_codes_cover_every_branch_should_snapshot_can_take(self):
        """The mapping from prose to code is pinned against the real function,
        so improving a sentence in ``should_snapshot`` without updating
        ``reason_code_for`` goes red instead of silently reclassifying every
        snapshot as UNKNOWN."""
        seen = set()
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            later = self._migrations_plus(tmp)
            _, reason = persistence_backup.should_snapshot(store.path, later)
            seen.add(persistence_backup.reason_code_for(reason))

            broken = Path(tmp) / "broken.sqlite3"
            broken.write_bytes(b"not a database")
            _, reason = persistence_backup.should_snapshot(broken, MIGRATIONS)
            seen.add(persistence_backup.reason_code_for(reason))

            plain = Path(tmp) / "plain.sqlite3"
            db = sqlite3.connect(str(plain))
            db.execute("PRAGMA journal_mode=delete")
            db.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,"
                       " applied_at TEXT NOT NULL, checksum TEXT)")
            for version in persistence_backup.migration_versions(MIGRATIONS):
                db.execute(
                    "INSERT INTO schema_migrations VALUES (?,?,?)",
                    (version, "2026-09-01T00:00:00Z", "x"),
                )
            db.commit()
            db.close()
            _, reason = persistence_backup.should_snapshot(plain, MIGRATIONS)
            seen.add(persistence_backup.reason_code_for(reason))
        self.assertNotIn(persistence_backup.REASON_UNKNOWN, seen)
        self.assertEqual(
            {
                persistence_backup.REASON_PENDING_MIGRATIONS,
                persistence_backup.REASON_LEDGER_UNREADABLE,
                persistence_backup.REASON_JOURNAL_MODE_REWRITE,
            },
            seen,
        )

    # ---- R4: a reused snapshot directory ----------------------------------

    def test_r4_a_reused_snapshot_directory_does_not_accuse_the_operator(self):
        """pf-adversary R4, MEASURED: ``_find_identical_snapshot`` hands one
        directory to many runs, and a single fixed note name meant the second
        run read the first run's note.  The gate then said "something changed
        it afterwards" to an operator who had restored the pristine file and
        re-run the boot -- permanently, because reuse also suppresses a new
        snapshot.  One note per outcome, named for its own sha, is the fix.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            pristine = Path(store.path).read_bytes()
            later = self._migrations_plus(tmp)
            store.migrations = later
            backups = Path(tmp) / "db_backups"

            first = store.migrate_with_backup(backups_root=backups)
            self.assertEqual(
                gate.EXPLAINED_BY_MIGRATION,
                gate.classify(store.path, later, canon, backups).outcome,
            )
            # The operator puts the canonical file back and boots again.
            Path(store.path).write_bytes(pristine)
            for suffix in ("-wal", "-shm"):
                sidecar = Path(store.path).with_name(Path(store.path).name + suffix)
                if sidecar.exists():
                    sidecar.unlink()
            second = store.migrate_with_backup(backups_root=backups)
            self.assertEqual(
                Path(first).parent, Path(second).parent, "the fixture needs reuse"
            )
            self.assertNotEqual(
                gate.database_sha256(store.path), canon, "the second run re-migrated"
            )
            verdict = gate.classify(store.path, later, canon, backups)
            self.assertEqual(gate.EXPLAINED_BY_MIGRATION, verdict.outcome)
            self.assertEqual(
                2,
                len(list(
                    Path(first).parent.glob(
                        persistence_backup.POSTSTATE_PREFIX + "*"
                    )
                )),
                "one reused directory must be able to carry a note per run",
            )

    # ---- R5: never-overwrite must be a lock, not a check ------------------

    def test_r5_two_boots_racing_on_one_note_cannot_overwrite_each_other(self):
        """pf-adversary R5, MEASURED: check-then-rename let both racers
        believe they had written, through one shared temporary name, and the
        loser's note was silently replaced.  ``O_CREAT|O_EXCL`` makes the
        loser lose."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            directory = self._manifest_path(backups).parent
            snapshot = directory / "pirateforce.sqlite3"
            note = self._poststate_path(backups, gate.database_sha256(store.path))
            before = note.read_bytes()
            self.assertIsNone(
                persistence_backup.record_post_migration_state(
                    snapshot, store.path, [111]
                ),
                "a second writer for the same outcome must lose",
            )
            self.assertEqual(before, note.read_bytes())
            self.assertEqual(
                [],
                sorted(directory.glob("*" + persistence_backup.INCOMPLETE_SUFFIX)),
                "no temporary file may be left inside a published snapshot",
            )

    # ---- R6: the manifest that is used is the manifest that was checked ----

    def test_r6_a_manifest_that_changes_mid_run_is_a_verdict_not_a_crash(self):
        """pf-adversary R6, MEASURED: the manifest was read twice, and the
        second read was outside every handler, so a file that became
        unreadable between the two turned a decided verdict into a
        ``TypeError`` out of ``classify()``."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            real = gate._load_manifest
            state = {"calls": 0}

            def vanishing(directory, name="MANIFEST.json"):
                state["calls"] += 1
                if state["calls"] > 1 and name == "MANIFEST.json":
                    return None
                return real(directory, name)

            with mock.patch.object(gate, "_load_manifest", vanishing):
                verdict = gate.classify(store.path, later, canon, backups)
            self.assertIn(verdict.outcome, (gate.EXPLAINED_BY_MIGRATION, gate.UNEXPLAINED))

    # ---- R8: the boundary the first mutant set never touched --------------

    def test_r8_a_canon_sha_differing_in_one_character_is_not_unchanged(self):
        """pf-adversary R8: every fixture used shas that were either identical
        or wholly different, so nothing distinguished a full sha256 comparison
        from a four-character prefix on the path that exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._migrated_store(tmp)
            canon = gate.database_sha256(store.path)
            for index in (0, 3, 4, 31, 63):
                with self.subTest(differing_character=index):
                    digits = list(canon)
                    digits[index] = "0" if digits[index] != "0" else "1"
                    verdict = gate.classify(store.path, MIGRATIONS, "".join(digits))
                    self.assertEqual(gate.UNEXPLAINED, verdict.outcome)
                    self.assertNotEqual(0, verdict.exit_code)

    def test_r8_a_live_database_that_cannot_be_opened_fails_the_integrity_check(self):
        """The ``cannot open`` branch of ``integrity_check``, which no test
        reached: it must report a problem, never the string ``ok``."""
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "not_here.sqlite3"
            self.assertNotEqual("ok", gate.integrity_check(missing).lower())
            broken = Path(tmp) / "broken.sqlite3"
            broken.write_bytes(b"this is not a database at all")
            self.assertNotEqual("ok", gate.integrity_check(broken).lower())

    def test_r8_the_note_records_the_size_of_the_file_it_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            note = json.loads(
                self._poststate_path(
                    backups, gate.database_sha256(store.path)
                ).read_text()
            )
            self.assertEqual(
                Path(store.path).stat().st_size, note["post_migration_bytes"]
            )

    def test_r8_safe_text_is_bounded(self):
        """The bound is what keeps one absurd path from burying the verdict
        line; without a test, removing it changes nothing visible."""
        long_name = "n" * 5000
        self.assertLessEqual(len(gate._safe_text(long_name)), 120)
        self.assertLessEqual(len(gate._safe_text(long_name, limit=200)), 200)

    # ---- R10/R11: what the report actually tells a caller ------------------

    def test_r10_json_and_human_output_carry_the_same_value_to_rotate_to(self):
        """pf-adversary R10: ``--json`` emits no ``NEW_SHA=`` token at all, and
        the outcome table promised one without qualification.  The table now
        names the field; this pins that the two agree."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            args = ["--db", str(store.path), "--migrations", str(later),
                    "--expect-sha", canon, "--backups-root", str(backups)]
            human_code, human, _ = self._run_cli(*args)
            json_code, payload, _ = self._run_cli(*args, "--json")
            self.assertEqual(human_code, json_code)
            token = [
                line for line in human.splitlines()
                if line.startswith(gate.NEW_SHA_TOKEN)
            ][0]
            self.assertEqual(
                token[len(gate.NEW_SHA_TOKEN):].lower(),
                json.loads(payload)["new_canon_sha"],
            )
            self.assertNotIn(gate.NEW_SHA_TOKEN, payload)

    def test_r11_the_human_report_says_why_each_snapshot_was_rejected(self):
        """pf-adversary R11: the one line the report printed was, in two real
        flows, misleading -- and the truthful diagnosis existed but was
        reachable only under ``--json``."""
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            self._rewrite_manifest(backups, kind="pf.something.else.v9")
            code, out, _ = self._run_cli(
                "--db", store.path, "--migrations", later,
                "--expect-sha", canon, "--backups-root", backups,
            )
            self.assertEqual(13, code)
            self.assertIn("manifest kind", out)

    def test_r11_a_crowded_backups_tree_cannot_bury_the_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, canon, later, backups = self._explained_case(tmp)
            self._rewrite_manifest(backups, kind="pf.something.else.v9")
            for index in range(12):
                (Path(backups) / ("2026090%02dT000000000000Z_x_y" % index)).mkdir()
            code, out, _ = self._run_cli(
                "--db", store.path, "--migrations", later,
                "--expect-sha", canon, "--backups-root", backups,
            )
            self.assertEqual(13, code)
            self.assertLessEqual(len(out.splitlines()), 4 + gate.REPORTED_REJECTIONS + 1)
            self.assertIn("more snapshot(s) examined", out)


class LaneDbCp874TripwireTest(unittest.TestCase):
    """A local mirror of the Windows-only cp874 tripwire, scoped to this lane.

    WHY THIS EXISTS, and why it is narrow.  Three of this lane's rounds were
    lost to gates that no local ``pytest`` run can see: the whole check lives
    in ``.github/workflows/gate-windows.yml`` and only ever speaks after a PR
    is open.  The "cp874 static tripwire" step there scans every tracked
    ``.py`` under ``tools/``, ``src/`` and ``current/`` and goes RED on one
    character that code page 874 cannot encode -- and this very file's module
    was written with a U+1F534 marker in its docstring, which would have been
    the fourth different gate channel to close a LANE-DB PR.

    Scoped to this lane's own modules on purpose: a repo-wide assertion here
    would turn red in this lane's test file for another lane's commit, which
    is not this file's business.  The workflow remains the authority for the
    whole tree.
    """

    LANE_FILES = sorted(
        [*(ROOT / "src" / "pirateforce_foundation").glob("persistence_*.py")]
    ) + [Path(__file__).resolve()]

    def test_this_lanes_modules_survive_a_cp874_console(self):
        self.assertTrue(self.LANE_FILES, "the lane's own modules must be found")
        offenders = []
        for path in self.LANE_FILES:
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                for char in line:
                    try:
                        char.encode("cp874")
                    except UnicodeEncodeError:
                        offenders.append(
                            "%s:%d codepoint %s" % (path.name, number, hex(ord(char)))
                        )
        self.assertEqual(
            [],
            offenders,
            "a character with no cp874 mapping does not degrade into '?' on the "
            "bridge console -- it raises UnicodeEncodeError inside print(). Use "
            "the house ASCII marker '!!' instead. See the cp874 step in "
            ".github/workflows/gate-windows.yml.",
        )
