"""LANE-DB: an automatic snapshot of the real database taken BEFORE any
migration is applied to it.

WHY THIS FILE EXISTS.  The owner's standing rule, relayed as
``COO-DECISION 2026-09-01T11:12+07:00`` (``pf_bridge/notes_to_chief/
20260901_1112_COO-DECISION-amend-lane-db-canonical-db-via-migrations.md``,
point 3):

    migration that touches existing rows (backfill/UPDATE/rebuild) must have
    an automatic backup mechanism (a copy of the .db file before apply)
    landing before, or together with, that migration in the same PR -- the
    owner's ban on "cannot be undone, no backup" always applies to real data.

The same letter's point 1 makes the canonical database on the owner's machine
the DESTINATION of this lane's work: it is upgraded to the standard schema by
``SQLiteStore.migrate()`` automatically at server boot.  Those two facts
together are what this module is for.  Until it existed, no boot copied the
database at any point -- nine ``tools/*_headless_replay.py`` scripts copy a
database for their own scratch runs, and ``tests/pf_preconditions.py``
(``BACKUPS_TREE``) names a machine-local ``backups/`` tree of hand-made
snapshots, but nothing ran automatically at the one moment that matters, so
this lane's first schema change was blocked behind the gap on purpose.

## The three rules the copy itself obeys

1. **THE SOURCE IS NEVER TOUCHED.**  Every connection this module opens on the
   live database is opened through a strict ``mode=ro`` URI, including the one
   the copy itself reads from.  This is not decoration: a plain read-WRITE
   ``sqlite3.connect`` on a WAL database checkpoints and DELETES ``-wal`` and
   ``-shm`` when it closes as the last connection, so the naive version of
   this module performed the one irreversible act on the owner's file --
   destroying the very hot WAL it claimed to be preserving -- before anything
   had been verified.  Measured, then fixed; ``test_snapshot_leaves_the_source
   _database_byte_identical`` is the guard.
2. **AN UNFINISHED SNAPSHOT MUST NOT LOOK LIKE A FINISHED ONE.**  A snapshot is
   assembled in a directory whose name ends in ``.INCOMPLETE`` and is renamed
   to its real name only after the copy has been verified and the manifest
   written.  A boot that dies mid-copy (disk full, corrupt source) therefore
   leaves something a human cannot mistake for a good backup -- the failure
   mode that would otherwise put the owner one wrong ``copy`` command away
   from exactly the loss this rule exists to forbid.
3. **NOTHING IS EVER DELETED OR PRUNED.**  Throwing away an old snapshot is
   itself the irreversible act.  Repeated boots against the same unchanged
   database do not pile up copies either, but that is done by RECOGNISING an
   existing identical snapshot (``_find_identical_snapshot``), never by
   removing one.

FAIL-SAFE DIRECTION.  Every uncertainty resolves toward TAKING a snapshot,
never toward skipping one: an unreadable ledger, an unparseable version row, a
database this server cannot open read-only -- all report "pending unknown" and
get a snapshot.  The only two cases that legitimately skip are (a) there is no
database file yet (nothing to lose: a fresh install) and (b) the ledger is
readable AND proves every migration on disk is applied AND the ledger itself is
not about to be rewritten in place (``ledger_rewrite_pending``).

ASCII only, like the rest of this repository's Python: the bridge console is
code page 874.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATION_GLOB = "[0-9][0-9][0-9]_*.sql"

#: Directory name created beside the database file itself.  Deliberately NOT
#: derived from the repository root: the snapshot tree follows the database it
#: protects, whichever tree that database lives in, so a replay tool pointed at
#: a scratch database cannot write into the bridge's own backup history.  The
#: repository's ``.gitignore`` is deny-by-default at the root, so nothing under
#: here can be committed by accident.  Named ``db_backups`` rather than
#: ``backups`` on purpose -- ``backups/`` already exists on the bridge under
#: different governance (``tests/pf_preconditions.py``, ``BACKUPS_TREE``).
DEFAULT_BACKUP_DIRNAME = "db_backups"

#: Files SQLite may keep beside ``<name>.sqlite3``.  Their bytes are preserved
#: in the snapshot's ``raw_originals/`` subdirectory -- NOT beside the snapshot
#: database, where SQLite's own recovery would silently read them and make a
#: broken copy look whole (that is how this module's first WAL test passed
#: against an implementation that had no consistent copy at all).
SIDECAR_SUFFIXES = ("-wal", "-shm")

#: Subdirectory holding those raw bytes.
RAW_SUBDIR = "raw_originals"

#: Sidecars whose CONTENT is part of "what this database currently holds", and
#: therefore part of the fingerprint two snapshots are compared on.  ``-shm``
#: is deliberately excluded: it is a derived WAL index that SQLite rebuilds
#: whenever a reader attaches (including this module's own read-only probes),
#: so fingerprinting it would make every snapshot look different from the last
#: one and defeat the reuse that keeps a retried boot from copying the world
#: again and again.  It carries no committed data -- deleting it loses nothing.
FINGERPRINT_SUFFIXES = ("-wal",)

#: Suffix a snapshot directory carries while it is being assembled.
INCOMPLETE_SUFFIX = ".INCOMPLETE"

#: Seconds a read probe may block on a locked source before this module gives
#: up.  Mirrors ``SQLiteStore.connect``'s own ``PRAGMA busy_timeout=5000`` so a
#: database another process has locked EXCLUSIVE produces the same 5-second
#: diagnosable failure it produced before this module existed, instead of the
#: unbounded retry loop ``sqlite3.Connection.backup`` performs on its own.
BUSY_TIMEOUT_MS = 5000

#: Refuse to start a copy without at least this multiple of the source's size
#: free on the destination filesystem.  A snapshot that runs the disk out
#: halfway is worse than a boot that refuses to start and says why.
FREE_SPACE_FACTOR = 2.0


class BackupError(RuntimeError):
    """A pre-migration snapshot could not be produced or could not be proven
    readable afterwards.  Raised, never swallowed: a boot that cannot take a
    backup must not go on to migrate the owner's only copy of the world.

    Every failure this module can produce is wrapped in this type on purpose --
    ``SQLiteStore.migrate_with_backup`` documents that contract, and a boot
    wrapper written as ``except BackupError:`` must not be defeated by a raw
    ``OSError`` escaping from a ``mkdir``.
    """


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _read_only_connection(path: Path) -> sqlite3.Connection:
    """The ONLY way this module ever opens the live database.

    ``PRAGMA busy_timeout`` is set before any statement runs so that a probe
    against a database another process holds locked fails in bounded time.
    """
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.execute("PRAGMA busy_timeout=%d" % BUSY_TIMEOUT_MS)
    db.execute("PRAGMA query_only=ON")
    return db


def migration_versions(migrations_dir: str | Path) -> list[int]:
    """Every version number present on disk, ascending.

    Uses the same glob and the same "first three characters are the version"
    rule as ``SQLiteStore.migrate``; a divergence between the two would make
    this module's answer to "is anything pending?" a different question from
    the one the runner is about to act on, so the shape is copied on purpose.
    """
    paths = sorted(Path(migrations_dir).glob(MIGRATION_GLOB))
    return [int(path.name[:3]) for path in paths]


def applied_versions(db_path: str | Path) -> set[int] | None:
    """Versions the ledger says are already applied, or ``None`` for "the
    ledger could not be read".

    ``None`` is not an error here and must never be treated as an empty set by
    a caller: it is the fail-safe answer that makes ``pending_versions``
    report work-to-be-done and earns the database a snapshot.  Opened strictly
    read-only so that probing a database can never create one, never take a
    write lock and never upgrade a journal mode.  (It can still cause SQLite to
    rebuild the WAL index ``-shm`` beside a hot-WAL database -- that is
    SQLite's own recovery, not a write to the database, and it is the reason
    this docstring does not claim "touches nothing on disk".)
    """
    path = Path(db_path)
    if not path.exists():
        return None
    try:
        db = _read_only_connection(path)
    except sqlite3.Error:
        return None
    try:
        rows = db.execute("SELECT version FROM schema_migrations").fetchall()
    except sqlite3.Error:
        # No ledger table at all (a database from before 001, or one this
        # server has never touched), a hot WAL this read-only handle cannot
        # follow, corruption -- every one of them means "do not claim this
        # database is already up to date".
        return None
    finally:
        db.close()
    try:
        return {int(row[0]) for row in rows}
    except (TypeError, ValueError):
        return None


def pending_versions(
    db_path: str | Path, migrations_dir: str | Path
) -> list[int] | None:
    """Migrations on disk that this database has not recorded, ascending.

    ``None`` means "unknown, assume there is work" (see ``applied_versions``).
    An empty list means "proven up to date".  A database file that does not
    exist yet returns every version on disk -- a fresh database really does
    have all of them pending -- and it is ``should_snapshot`` below, not this
    function, that knows a nonexistent file has nothing worth copying.
    """
    versions = migration_versions(migrations_dir)
    path = Path(db_path)
    if not path.exists():
        return list(versions)
    applied = applied_versions(path)
    if applied is None:
        return None
    return [version for version in versions if version not in applied]


def ledger_rewrite_pending(db_path: str | Path) -> bool:
    """True when ``SQLiteStore.migrate`` will rewrite rows in the ledger table
    itself even though no migration FILE is pending.

    Found by measuring, not by reading: ``migrations/001_initial.sql:2``
    creates ``schema_migrations`` with only ``(version, applied_at)``, and the
    runner (``store.py``, the "checksum" branch of ``migrate``) upgrades any
    such ledger in place with ``ALTER TABLE ... ADD COLUMN checksum`` followed
    by one ``UPDATE`` per already-applied row.  A long-lived database created
    before the checksum column existed -- the owner's canonical database is
    exactly that shape of candidate -- therefore meets a boot that changes its
    rows while ``pending_versions`` correctly reports an empty list.  Without
    this check that boot would have been the one row-touching write in the
    whole system that got no snapshot, which is precisely the hole the owner's
    rule is about.

    Fail-safe like everything else here: anything that cannot be read reports
    True.
    """
    path = Path(db_path)
    if not path.exists():
        return False
    try:
        db = _read_only_connection(path)
    except sqlite3.Error:
        return True
    try:
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(schema_migrations)")}
    except sqlite3.Error:
        return True
    finally:
        db.close()
    if not columns:
        # No ledger table at all: migrate() is about to CREATE it and insert
        # every version into a database that already holds rows.
        return True
    return "checksum" not in columns


def journal_mode_rewrite_pending(db_path: str | Path) -> bool:
    """True when merely OPENING this database will rewrite it in place.

    pf-adversary, round 1, defect 2.  ``SQLiteStore.connect`` runs
    ``PRAGMA journal_mode=WAL`` unconditionally for every file database
    (``store.py:36``), and converting a rollback-journal database to WAL
    rewrites its header and creates ``-wal``/``-shm`` beside it.  So a
    database that arrives in ``journal_mode=delete`` -- a plain-file restore, a
    ``.dump``/``.restore`` round trip, a copy made by a third-party tool -- is
    modified by the very next statement after ``migrate_with_backup`` decides
    nothing is pending.  ``ledger_rewrite_pending`` models writes the MIGRATION
    performs; this models writes the CONNECTION performs, and both have to be
    asked before "nothing will be written" is a safe answer.

    Fail-safe: anything that cannot be read reports True.
    """
    path = Path(db_path)
    if not path.exists():
        return False
    try:
        db = _read_only_connection(path)
    except sqlite3.Error:
        return True
    try:
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]
    except (sqlite3.Error, TypeError, IndexError):
        return True
    finally:
        db.close()
    return str(mode).lower() != "wal"


def should_snapshot(
    db_path: str | Path, migrations_dir: str | Path
) -> tuple[bool, str]:
    """``(take_one, reason)`` -- the whole decision, in one testable place.

    The reason string is recorded in the snapshot manifest, so a later reader
    can see WHY a boot did or did not copy the database rather than inferring
    it from the absence of a folder.
    """
    path = Path(db_path)
    if str(db_path) == ":memory:":
        return False, "in-memory database: nothing on disk to copy"
    if not path.exists():
        return False, "no database file yet: a fresh database has nothing to lose"
    pending = pending_versions(path, migrations_dir)
    if pending is None:
        return True, "migration ledger unreadable: assuming migrations are pending"
    if not pending:
        if journal_mode_rewrite_pending(path):
            return True, (
                "no migration file is pending, but opening this database will "
                "rewrite its header in place (journal_mode is not WAL yet)"
            )
        if ledger_rewrite_pending(path):
            return True, (
                "no migration file is pending, but the ledger itself is about "
                "to be rewritten in place (checksum column upgrade)"
            )
        return False, "ledger proves every migration on disk is already applied"
    return True, "pending migrations: " + ",".join("%03d" % v for v in pending)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sidecar_paths(source: Path, suffixes=SIDECAR_SUFFIXES) -> list[Path]:
    return [
        source.with_name(source.name + suffix)
        for suffix in suffixes
        if source.with_name(source.name + suffix).exists()
    ]


def source_fingerprint(source: Path) -> dict:
    """Everything that has to be equal for two snapshots of this database to
    hold the same bytes -- the main file AND every sidecar, because a committed
    transaction can live entirely in ``-wal`` while the main file is untouched.

    Used only to recognise a snapshot that already exists (see
    ``_find_identical_snapshot``); it never decides whether to take one.
    """
    return {
        "path": str(source.resolve()),
        "bytes": source.stat().st_size,
        "sha256": _sha256_file(source),
        # A zero-byte ``-wal`` holds no transaction and is not part of what
        # this database contains.  It is skipped because attaching a reader to
        # a WAL database -- which this module's own read-only probes do -- can
        # leave an empty one behind where there was none, and counting that
        # would make every snapshot look different from the last and defeat
        # the reuse below.
        "sidecars": [
            {"name": p.name, "bytes": p.stat().st_size, "sha256": _sha256_file(p)}
            for p in _sidecar_paths(source, FINGERPRINT_SUFFIXES)
            if p.stat().st_size
        ],
    }


def _find_identical_snapshot(
    root: Path, fingerprint: dict, pending, source_name: str
) -> Path | None:
    """A completed snapshot of byte-identical source content, or ``None``.

    The case this exists for, measured: a migration of this lane's own that
    fails on its first statement.  ``pending_versions`` still reports it
    pending on every retry, so the owner re-running the bridge's ``.bat`` ten
    times to read the error would otherwise get ten full copies of the live
    world.  Recognising the existing one costs a re-read of the source; copying
    it again costs a re-read AND a full write, so this is never the slower
    path.  Directories still being assembled (``.INCOMPLETE``) and directories
    with no manifest are ignored -- only a snapshot that finished counts.
    """
    if not root.is_dir():
        return None
    for directory in sorted(root.iterdir(), reverse=True):
        if not directory.is_dir() or directory.name.endswith(INCOMPLETE_SUFFIX):
            continue
        manifest_path = directory / "MANIFEST.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if manifest.get("source_fingerprint") != fingerprint:
            continue
        if manifest.get("pending_versions") != pending:
            continue
        name = str(manifest.get("snapshot_database", ""))
        # The name comes off a file on disk; it is never joined as given.  A
        # manifest saying ``../../pirateforce.sqlite3`` must not be able to
        # hand the LIVE database back as its own backup.
        if name != source_name:
            continue
        candidate = directory / name
        if not candidate.is_file():
            continue
        if not _snapshot_is_still_good(candidate, manifest):
            # Left in place, never deleted (rule 3) -- it simply does not
            # count as a backup any more, and this boot takes a fresh one.
            continue
        return candidate
    return None


def _snapshot_is_still_good(candidate: Path, manifest: dict) -> bool:
    """Re-prove an OLD snapshot before a boot is allowed to rely on it.

    pf-adversary, round 1, defect 4 -- the worst one found in the second pass.
    Reuse used to be gated on ``candidate.is_file()`` alone: the manifest's own
    ``verification.sha256`` was written once and never compared to anything
    again.  A snapshot truncated in the meantime (a bad sector, an interrupted
    copy to a USB stick, a 0-byte artifact of a full disk) was handed straight
    back to the boot, which then migrated the owner's live rows believing it
    was protected, while the manifest beside the dead file still said
    ``"integrity_check": "ok"``.

    A backup nobody has opened is a claim, not a backup -- and that has to hold
    on the day the backup is NEEDED, not only on the day it was made.  So the
    file is re-hashed and re-opened here, every time, before it is allowed to
    stand in for a fresh copy.
    """
    recorded = manifest.get("verification")
    if not isinstance(recorded, dict):
        return False
    try:
        if candidate.stat().st_size != recorded.get("bytes"):
            return False
        if _sha256_file(candidate) != recorded.get("sha256"):
            return False
    except OSError:
        return False
    try:
        _verify_snapshot(candidate)
    except (BackupError, sqlite3.Error, OSError):
        return False
    return True


def _copy_consistent(source: Path, destination: Path) -> None:
    """A single self-contained ``.sqlite3`` holding everything committed to
    ``source``, including a WAL that has not been checkpointed yet.

    Uses SQLite's own online-backup API rather than ``shutil.copy`` because a
    plain file copy of a WAL database copies the database file WITHOUT the
    committed pages still sitting in ``-wal``: the copy opens clean and is
    silently missing the most recent transactions (measured -- the naive copy
    of a database whose only account was committed into a hot WAL reads back
    ``accounts == []``).

    The source handle is READ-ONLY (see rule 1 in the module docstring) and
    carries a busy timeout, and a bounded read runs first so that a database
    another process holds locked fails in about five seconds instead of
    disappearing into ``backup()``'s own unbounded ``SQLITE_BUSY`` retry loop.
    """
    src = _read_only_connection(source)
    try:
        src.execute("SELECT count(*) FROM sqlite_master").fetchone()
        dst = sqlite3.connect(str(destination))
        try:
            dst.execute("PRAGMA busy_timeout=%d" % BUSY_TIMEOUT_MS)
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _verify_snapshot(snapshot: Path) -> dict:
    """Prove the copy is a database that opens, passes SQLite's own integrity
    check, and still carries the ledger -- a backup nobody has ever opened is a
    claim, not a backup.

    Any ``-wal``/``-shm`` this verification connection creates beside the
    snapshot is removed afterwards: the snapshot database must be self-contained
    (that is what the manifest's ``restore_hint`` promises), and a stray sidecar
    beside it would let SQLite paper over a copy that is not.
    """
    try:
        db = _read_only_connection(snapshot)
    except sqlite3.Error as error:
        raise BackupError(
            "snapshot %s cannot be opened at all: %r" % (snapshot.name, error)
        ) from error
    try:
        try:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        except sqlite3.Error as error:
            # Damage bad enough that SQLite refuses to walk the file raises
            # here instead of returning a verdict.  Same outcome, one type:
            # this function's whole contract is that a snapshot it returns
            # from has been read.
            raise BackupError(
                "snapshot %s could not be integrity-checked: %r"
                % (snapshot.name, error)
            ) from error
        if str(integrity).lower() != "ok":
            raise BackupError(
                "snapshot %s failed integrity_check: %s" % (snapshot.name, integrity)
            )
        try:
            versions = sorted(
                int(row[0])
                for row in db.execute("SELECT version FROM schema_migrations")
            )
        except sqlite3.Error:
            versions = None
    finally:
        db.close()
    for suffix in SIDECAR_SUFFIXES:
        artifact = snapshot.with_name(snapshot.name + suffix)
        if artifact.exists():
            artifact.unlink()
    return {
        "integrity_check": "ok",
        "schema_migrations_in_snapshot": versions,
        "sha256": _sha256_file(snapshot),
        "bytes": snapshot.stat().st_size,
    }


def default_backups_root(db_path: str | Path) -> Path:
    return Path(db_path).resolve().parent / DEFAULT_BACKUP_DIRNAME


def _require_path_safe(what: str, value: str) -> None:
    if not value or any(ch.isspace() for ch in value) or any(
        ch in value for ch in '/\\:*?"<>|'
    ) or value in (".", "..") or value.startswith("."):
        raise BackupError("snapshot %s must be one path-safe word: %r" % (what, value))


def _require_free_space(root: Path, source: Path) -> None:
    probe = root
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        free = shutil.disk_usage(str(probe)).free
    except OSError as error:
        raise BackupError("cannot measure free space at %s: %r" % (probe, error)) from error
    needed = int(source.stat().st_size * FREE_SPACE_FACTOR)
    if free < needed:
        raise BackupError(
            "refusing to start a snapshot with %d bytes free at %s (want >= %d, "
            "%.1fx the %d-byte database): a copy that runs the disk out halfway "
            "is worse than a boot that refuses to start.%s"
            % (
                free, probe, needed, FREE_SPACE_FACTOR, source.stat().st_size,
                _unfinished_snapshot_advice(root),
            )
        )


def _unfinished_snapshot_advice(root: Path) -> str:
    """Name the dead weight, because this module will never remove it itself.

    pf-adversary, round 1, defect 3: unfinished snapshots are never pruned (by
    design -- deleting a backup is the irreversible act), so enough failed
    boots eventually push the free-space check below its threshold and the
    server refuses to start for good.  The refusal has to tell a human which
    directories are safe to delete, or it is a dead end rather than a warning.
    """
    if not root.is_dir():
        return ""
    dead = []
    for directory in sorted(root.iterdir()):
        if directory.is_dir() and directory.name.endswith(INCOMPLETE_SUFFIX):
            size = sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
            dead.append((directory.name, size))
    if not dead:
        return (
            " No unfinished snapshots are present; every directory under %s is a "
            "real backup and deleting one loses data." % root
        )
    total = sum(size for _, size in dead)
    return (
        " %d unfinished snapshot(s) under %s hold %d bytes and are SAFE TO DELETE "
        "(they are not backups -- each one is a copy that never completed): %s"
        % (len(dead), root, total, ", ".join(name for name, _ in dead))
    )


def snapshot_database(
    db_path: str | Path,
    backups_root: str | Path | None = None,
    *,
    label: str = "premigration",
    reason: str = "",
    pending: list[int] | None = None,
    stamp: str | None = None,
) -> Path:
    """Copy ``db_path`` into its own new directory under ``backups_root`` and
    return the path of the copied database.

    One directory per snapshot, never a shared folder of loose files: the
    manifest, the database and the raw ``-wal``/``-shm`` originals belong to
    each other and must not be mixed with a different boot's.  Nothing is ever
    overwritten and nothing is ever removed; an existing snapshot of
    byte-identical source content is RETURNED instead of duplicated.
    """
    source = Path(db_path)
    if not source.exists():
        raise BackupError("cannot snapshot a database that does not exist: %s" % source)
    root = Path(backups_root) if backups_root is not None else default_backups_root(source)
    _require_path_safe("label", label)
    stamp = _utc_stamp() if stamp is None else stamp
    _require_path_safe("stamp", stamp)

    fingerprint = source_fingerprint(source)
    existing = _find_identical_snapshot(root, fingerprint, pending, source.name)
    if existing is not None:
        return existing

    final = root / ("%s_%s_%s" % (stamp, label, source.stem))
    working = final.with_name(final.name + INCOMPLETE_SUFFIX)
    if final.exists() or working.exists():
        raise BackupError(
            "snapshot directory already exists, refusing to overwrite: %s" % final
        )
    _require_free_space(root, source)

    snapshot = working / source.name
    try:
        working.mkdir(parents=True)
        # The raw originals are copied BEFORE the database is opened at all, so
        # that what lands here is what the boot actually found.
        raw = working / RAW_SUBDIR
        raw.mkdir()
        sidecars = []
        for sidecar in _sidecar_paths(source):
            (raw / sidecar.name).write_bytes(sidecar.read_bytes())
            sidecars.append(sidecar.name)
        _copy_consistent(source, snapshot)
        verification = _verify_snapshot(snapshot)
        manifest = {
            "kind": "pf.lane_db.premigration_snapshot.v1",
            "taken_at_utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "source_database": str(source.resolve()),
            "source_bytes": source.stat().st_size,
            "source_fingerprint": fingerprint,
            "snapshot_database": snapshot.name,
            "raw_originals": sidecars,
            "label": label,
            "reason": reason,
            "pending_versions": pending,
            "verification": verification,
            "restore_hint": (
                "TO RESTORE, in this order, with the server STOPPED: "
                "(1) move the LIVE %s-wal and %s-shm out of the way -- renaming "
                "them is enough, do not delete them. THIS STEP IS NOT OPTIONAL: "
                "a stopped server normally leaves a hot write-ahead log beside "
                "the database, and SQLite replays it onto whatever file it finds "
                "there, so copying the snapshot in while the live log is still "
                "present silently re-applies the very transactions you are trying "
                "to undo and the result still passes PRAGMA integrity_check. "
                "(2) copy %s/%s over %s. That FILE is self-contained -- it already "
                "holds everything that was committed at snapshot time, including "
                "transactions that were then only in the write-ahead log. "
                "(3) start the server and check the data before deleting anything "
                "you moved aside in step 1. "
                "The originals from the moment of the snapshot are kept in %s/ for "
                "forensics only and are never copied back. A directory whose name "
                "ends in %s, or one with no MANIFEST.json in it, is an UNFINISHED "
                "snapshot and must never be restored from."
                % (source.name, source.name, final.name, snapshot.name,
                   source.name, RAW_SUBDIR, INCOMPLETE_SUFFIX)
            ),
        }
        (working / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except BackupError:
        raise
    except Exception as error:  # sqlite3.Error, OSError -- boot must stop
        raise BackupError(
            "pre-migration snapshot of %s failed: %r" % (source, error)
        ) from error
    # The rename is the commit: until it happens the directory is named
    # ``...INCOMPLETE`` and no reader may treat it as a backup.
    try:
        working.rename(final)
    except OSError as error:
        raise BackupError(
            "snapshot of %s was assembled but could not be published as %s: %r"
            % (source, final, error)
        ) from error
    return final / source.name
