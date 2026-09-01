"""LANE-DB: the second-storey gate that decides WHY the canonical database's
sha256 stopped matching ``pf_bridge/CANON_SHA.txt``.

WHY THIS FILE EXISTS.  Two PowerShell jobs on the bridge compare the canonical
database's sha256 against ``CANON_SHA.txt`` and treat ANY difference as bad:

* ``staged/175_round109_path_d_ci_status_gate_commit.ps1:117-123`` -- ``exit 13``
* ``staged/TEMPLATE_teardown_generic.ps1:414-436`` -- reports ``RED``

That comparison was correct while nothing was ever supposed to change the
owner's database.  ``COO-DECISION 20260901_1112`` point 1 changed the premise:
the canonical database is now the DESTINATION of this lane's work and is
upgraded to the standard schema by this server's own migrations at boot.  A
legitimate migration therefore now produces exactly the same red the gate was
built to raise for damage, and ``COO-DECISION 20260901_1241`` ruled that the
pin must be rotatable -- but only through a mechanism that can tell the two
apart.  ``COO-DECISION 20260901_1447`` point 4 approved this module's design;
the calling contract below is the one sent to chief in
``pf_bridge/notes_to_chief/20260901_1515_LANE-DB-REQUEST-chief-staged-canon-
gate-spec-and-backuperror-wrapper.md`` section (b.1), and the ps1 side is
chief's to wire, not this lane's.

## The contract, and why the exit code is the answer

``python -m pirateforce_foundation.persistence_canon_gate --db <canonical.db>
--migrations <migrations/> --expect-sha <value from CANON_SHA.txt>``

===== ============================ ==================================
exit   verdict                      what the caller must do
===== ============================ ==================================
0      ``UNCHANGED``                carry on, pin is still correct
20     ``EXPLAINED_BY_MIGRATION``   rotate the pin to the printed
                                    ``NEW_SHA=`` line, and log both
13     ``UNEXPLAINED``              ABORT, and do NOT rotate
other  the module itself broke      ABORT (never read as ``UNCHANGED``)
===== ============================ ==================================

``13`` is deliberately the number the un-modified ps1 already exits with, so a
job that has NOT yet been rewired still aborts correctly the day this module
appears.  ``20`` must be the ONLY path on which ``CANON_SHA.txt`` is ever
rewritten: a gate that can unlock itself in more than one way is worse than no
gate, because it still reads like protection.

## What ``EXPLAINED_BY_MIGRATION`` actually requires

The first version of this module asked only whether the database's PRESENT
state looked tidy: valid pin, self-consistent ledger, ``integrity_check`` ok,
some snapshot naming the pin.  pf-adversary measured what that let through and
the answer was: everything.  Not one of those four conditions is a function of
the DIFFERENCE between the pinned state and the current one, so a
``DELETE FROM accounts`` on a database whose boot had already taken its
snapshot came back ``EXPLAINED_BY_MIGRATION``, exit ``20``, and the caller
would have pinned the vandalised file.  So would an ordinary run: boot
migrates, players play, the teardown job runs the gate, and ``NEW_SHA`` names a
state no migration produced.  The verdict named a conclusion the gate had never
measured.

What it measures now is the question that was missing:

    is the file on disk today what THIS repository's migrations produce when
    they are applied to the state the pin names?

That is answered by doing it.  The snapshot of the pinned state is copied into
a scratch directory, the real ``SQLiteStore.migrate`` is run against the copy,
and the result is compared to the live database CONTENT-wise (a full
``iterdump`` of both, with the ledger's own rows set aside because their
``applied_at`` timestamps are wall-clock).  Equal means the only thing that
happened between the pin and now is this repository's own migrations.  Not
equal means something else did, and the pin must not move.

The five conditions, all required, every time:

1. **The pin is a real pin** -- exactly 64 hex characters after stripping
   surrounding whitespace and any byte-order mark.  A missing or malformed pin
   explains nothing and can never license a rotation.
2. **The ledger tells the same story as this repository's ``migrations/``** --
   every version on disk applied, no version applied that is not on disk, every
   applied checksum equal to the file's sha256 in this working tree, and the
   directory is not EMPTY (an empty ``migrations/`` made both sides of that
   comparison vacuously equal, which is how a wrong ``--migrations`` path used
   to pass).
3. **``PRAGMA integrity_check`` says ``ok``.**
4. **A snapshot of the pinned state exists and still verifies** -- a completed
   snapshot under the database's own ``db_backups/`` naming this database as
   its source and recording the pin as its source sha256, whose own file still
   hashes to what its manifest says and still opens as a database.
5. **At least one migration ran since the pin, and re-running it reproduces
   what is on disk** -- the derivation above.

## What condition 4 does and does not prove

It proves that some manifest claims the pinned sha as its source and that the
file it points at still matches that manifest's own recorded hash.  It does
NOT mean a byte copy of the pinned file is on disk: the snapshot is written
through SQLite's backup API and folds in a hot write-ahead log, so it holds the
pinned database's committed CONTENT while hashing to something else entirely.
Restoring it does not reproduce the pinned sha256, and once ``CANON_SHA.txt``
is rewritten the old value itself is gone.  Whoever rotates the pin should log
the old value, which is why the contract asks the caller to log both.

Condition 4 also refuses to be lenient about the snapshot's recorded source
PATH, and about the shape of its recorded FILE NAME.  The damaging failure here
is not a false red, it is a false ``20``: ``persistence_backup``'s own reuse
scan carries a guard against a manifest saying ``../../pirateforce.sqlite3``,
and the first version of this module re-implemented that scan without it --
measured, the gate then nominated the owner's LIVE database as its own backup,
returned ``20``, and destroyed that database's hot write-ahead log on the way.

## What this module never does

It never writes anything to the canonical database, to its snapshot tree, or to
``CANON_SHA.txt``.  Every connection it opens on either the live database or a
snapshot is a strict ``mode=ro`` URI, for the reason stated at length in
``persistence_backup``: a plain read-write connect on a WAL database
checkpoints and deletes the hot ``-wal`` when it closes.  For the same reason
this module verifies snapshots itself instead of borrowing
``persistence_backup._snapshot_is_still_good``: that helper ends in
``_verify_snapshot``, which UNLINKS the sidecars beside the file it checked --
correct for a snapshot that module has just created, destructive for one it
merely found.  Measured before it was fixed: a committed transaction sitting in
a hot ``-wal`` beside an operator's backup was deleted by this gate.

Condition 5 does write -- to a scratch copy inside
``tempfile.TemporaryDirectory()``, never to anything the caller named.  It
costs one full copy of the database and one migration run, which is why this
gate belongs in the once-per-upgrade job it was specified for and not in a
boot path.

## Four limits this module does NOT close, named so nobody assumes it did

1. **A write living only in a hot ``-wal`` moves nothing this gate is asked
   about.**  The pin is ``Get-FileHash`` of the MAIN file, so a committed
   transaction that has not been checkpointed leaves the sha untouched and the
   verdict is ``UNCHANGED`` without any of the five conditions running.  That is
   the caller's contract, not this module's to change; it is written down here
   because "the gate said UNCHANGED" is weaker than it reads.
2. **A migration whose SQL is not deterministic reds condition 5.**
   ``migrations/002_character_integrity.sql:10`` uses ``CURRENT_TIMESTAMP``, so
   if 002 is ever among the versions being re-derived the derivation will
   differ on the timestamp alone.  The direction is safe (a red, not a
   rotation), and every real rotation starts from a database that applied 002
   long ago -- but a human meeting that red should be told it is this, not
   damage.
3. **Condition 2's checksum half cannot fail on the FIRST real rotation.**  The
   owner's canonical database has a pre-checksum ledger, and the same boot that
   changes its sha backfills every checksum from the files in this working tree
   (``store.py``, the ``ALTER TABLE ... ADD COLUMN checksum`` branch).  The
   comparison then holds this tree against values copied out of this tree
   minutes earlier.  Condition 2's set-comparison halves still bite; the
   checksum half is asleep for that one run.
4. **``staged/`` and ``pf_bridge/`` are not in this repository.**  Every line
   number cited above for a ps1 or a letter is unverifiable from this checkout
   and is quoted from the other repository as of this round.  The in-repo
   citations are re-derivable and were re-derived.

ASCII only, like the rest of this repository's Python: the bridge console is
code page 874.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .persistence_backup import (
    INCOMPLETE_SUFFIX,
    MIGRATION_GLOB,
    _read_only_connection,
    default_backups_root,
)

#: The three answers, and the two failure shapes that are not answers.
UNCHANGED = "UNCHANGED"
EXPLAINED_BY_MIGRATION = "EXPLAINED_BY_MIGRATION"
UNEXPLAINED = "UNEXPLAINED"

EXIT_UNCHANGED = 0
EXIT_EXPLAINED = 20
EXIT_UNEXPLAINED = 13
#: Reserved for "this module raised something it did not plan for".  Distinct
#: from all three verdicts on purpose -- the caller's table says anything not
#: in {0, 20, 13} is an abort, and an internal fault must land there rather
#: than borrow a verdict it has not earned.
EXIT_INTERNAL_ERROR = 70

EXIT_CODES = {
    UNCHANGED: EXIT_UNCHANGED,
    EXPLAINED_BY_MIGRATION: EXIT_EXPLAINED,
    UNEXPLAINED: EXIT_UNEXPLAINED,
}

_HEX = set("0123456789abcdefABCDEF")


@dataclass
class CanonGateResult:
    """The whole answer, so a test can assert on the reasoning and not only on
    the number.  ``reasons`` is never empty for ``UNEXPLAINED``: a red that
    cannot say what it saw sends a human to guess at the owner's database."""

    verdict: str
    actual_sha: str | None
    expected_sha: str | None
    new_sha: str | None = None
    reasons: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.verdict]


def normalise_sha(value: str | None) -> str | None:
    """``value`` as 64 uppercase hex characters, or ``None`` when it is not a
    sha256 at all.

    Surrounding whitespace is stripped because ``CANON_SHA.txt`` is a text file
    a human edits and PowerShell's ``Get-Content -Raw`` keeps the trailing
    newline.  Nothing INSIDE the value is stripped, unlike the ps1's
    ``-replace '[^0-9A-Fa-f]',''``: that form would turn a truncated pin with a
    stray marker in it into a shorter string and, in the worst case, silently
    accept a value no tool ever wrote.  A pin this function rejects can only
    produce ``UNEXPLAINED``, never a rotation.
    """
    if value is None:
        return None
    # A byte-order mark is not whitespace and ``str.strip()`` leaves it in
    # place.  PowerShell's ``Set-Content``/``Out-File`` emit one by default on
    # several hosts, so a pin this gate itself asked the caller to rotate could
    # come back 65 characters long and red the gate permanently.  Stripped here
    # rather than in the caller because the caller is a ps1 nobody can test
    # from this repository.
    text = value.replace("\ufeff", "").strip()
    if len(text) != 64 or any(ch not in _HEX for ch in text):
        return None
    return text.upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def migration_checksums(migrations_dir: str | Path) -> dict[int, str]:
    """``{version: sha256 of the file's bytes}`` for this working tree.

    The glob, the "first three characters are the version" rule and the
    lowercase ``hexdigest`` all match ``SQLiteStore.migrate`` exactly, because
    what is being compared here is the value THAT runner wrote into the ledger.
    A divergence would make this gate answer a different question from the one
    the database was actually migrated by.
    """
    checksums: dict[int, str] = {}
    for path in sorted(Path(migrations_dir).glob(MIGRATION_GLOB)):
        checksums[int(path.name[:3])] = hashlib.sha256(path.read_bytes()).hexdigest()
    return checksums


def ledger_rows(db_path: str | Path) -> dict[int, str | None] | None:
    """``{version: checksum}`` from ``schema_migrations``, or ``None`` when the
    ledger cannot be read as one.

    ``None`` covers every shape of "this database cannot account for itself":
    no ledger table, no ``checksum`` column (a database from before the runner
    grew one -- which is a database a boot is about to REWRITE, so it is
    certainly not evidence that a past migration explains anything), a
    non-integer version, or a read that fails.  Every one of them is treated
    the same way downstream: no rotation.
    """
    path = Path(db_path)
    if not path.exists():
        return None
    try:
        db = _read_only_connection(path)
    except sqlite3.Error:
        return None
    try:
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(schema_migrations)")}
        if "version" not in columns or "checksum" not in columns:
            return None
        rows = db.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    except sqlite3.Error:
        return None
    finally:
        db.close()
    try:
        return {int(row[0]): (None if row[1] is None else str(row[1])) for row in rows}
    except (TypeError, ValueError):
        return None


def integrity_check(db_path: str | Path) -> str:
    """The first line SQLite returns, or a ``"cannot run"`` sentence.

    Never raises: a corrupt database is the case this exists to catch, so it
    must produce a reason string rather than a traceback out of the gate.
    """
    try:
        db = _read_only_connection(Path(db_path))
    except sqlite3.Error as error:
        return "cannot open read-only: %r" % (error,)
    try:
        rows = db.execute("PRAGMA integrity_check").fetchall()
    except sqlite3.Error as error:
        return "cannot run integrity_check: %r" % (error,)
    finally:
        db.close()
    if not rows:
        return "integrity_check returned nothing"
    return str(rows[0][0])


def _iter_snapshot_manifests(root: Path):
    """Every COMPLETED snapshot directory's ``(directory, manifest)``.

    A directory still carrying ``INCOMPLETE_SUFFIX``, or one with no readable
    ``MANIFEST.json``, is skipped in silence here and reported by the caller as
    "no snapshot found": ``persistence_backup`` rule 2 is that an unfinished
    snapshot must never be mistaken for a finished one, and this reader is
    exactly the place that rule would be broken.
    """
    if not root.is_dir():
        return
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name.endswith(INCOMPLETE_SUFFIX):
            continue
        manifest_path = directory / "MANIFEST.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(manifest, dict):
            yield directory, manifest


def _snapshot_file_inside(directory: Path, name) -> Path | None:
    """The snapshot database named by a manifest, but ONLY when that name is a
    plain file name resolving inside ``directory``.

    ``persistence_backup._find_identical_snapshot`` carries this guard with a
    comment naming the attack exactly -- "a manifest saying
    ``../../pirateforce.sqlite3`` must not be able to hand the LIVE database
    back as its own backup".  This module's first version re-implemented that
    scan and left the guard out.  Measured: with one hand-edited manifest the
    gate returned exit ``20`` while nominating the owner's live canonical
    database as its own backup, and destroyed that database's hot write-ahead
    log in the act of "verifying" it.  Both shapes are refused here -- a
    traversal (``..``) and an absolute path, which ``Path.__truediv__`` silently
    honours by discarding the left-hand side.
    """
    if not isinstance(name, str) or not name:
        return None
    if name != Path(name).name or name in (".", ".."):
        return None
    candidate = directory / name
    try:
        inside = candidate.resolve().parent == directory.resolve()
    except OSError:
        return None
    if not inside or not candidate.is_file():
        return None
    return candidate


def snapshot_still_verifies(candidate: Path, manifest: dict) -> bool:
    """Re-prove a snapshot READ-ONLY: it hashes to what its manifest recorded,
    and it still opens as a database whose integrity check passes.

    Deliberately NOT ``persistence_backup._snapshot_is_still_good``, whose last
    step is ``_verify_snapshot`` -- and ``_verify_snapshot`` ends by UNLINKING
    the ``-wal``/``-shm`` beside the file it checked.  That is correct for a
    snapshot that module has just written and knows the sidecars of; it is
    destructive for one this gate merely found.  Measured: an operator's
    interrupted inspection had left a genuine hot ``-wal`` beside a backup, and
    running the gate deleted it, taking a committed transaction with it -- in a
    module whose own rule 3 is that nothing is ever deleted or pruned.

    A backup nobody has re-opened is a claim, not a backup, so both halves are
    still done; only the deleting is dropped.
    """
    recorded = manifest.get("verification")
    if not isinstance(recorded, dict):
        return False
    try:
        if candidate.stat().st_size != recorded.get("bytes"):
            return False
        if sha256_file(candidate).lower() != str(recorded.get("sha256", "")).lower():
            return False
    except OSError:
        return False
    return integrity_check(candidate) == "ok"


def find_snapshot_of_sha(
    db_path: str | Path, expected_sha: str, backups_root: str | Path | None = None
) -> tuple[Path | None, list[str]]:
    """A snapshot holding the bytes ``expected_sha`` names, plus the notes on
    what was rejected and why.

    Returns the snapshot's DATABASE file (not its directory) so the caller can
    print a path a human can restore from without a second lookup.  Both the
    source-path match and the ``_snapshot_is_still_good`` re-proof are
    required; see this module's docstring, point 4, for why neither is relaxed.
    """
    source = Path(db_path).resolve()
    root = Path(backups_root) if backups_root is not None else default_backups_root(source)
    notes: list[str] = []
    seen = 0
    for directory, manifest in _iter_snapshot_manifests(root):
        seen += 1
        fingerprint = manifest.get("source_fingerprint")
        if not isinstance(fingerprint, dict):
            continue
        recorded = normalise_sha(fingerprint.get("sha256"))
        if recorded != expected_sha:
            continue
        recorded_source = manifest.get("source_database")
        if not isinstance(recorded_source, str) or Path(recorded_source) != source:
            notes.append(
                "%r holds the pinned state but names a different source database "
                "(%r, not %s)" % (directory.name, recorded_source, source)
            )
            continue
        candidate = _snapshot_file_inside(directory, manifest.get("snapshot_database"))
        if candidate is None:
            notes.append(
                "%r names the pinned state but its snapshot database file is missing "
                "or its manifest names a file outside its own directory"
                % directory.name
            )
            continue
        if not snapshot_still_verifies(candidate, manifest):
            notes.append(
                "%r names the pinned state but no longer verifies (re-hash or "
                "re-open failed) -- it cannot be restored from" % directory.name
            )
            continue
        return candidate, notes
    notes.append("checked %d completed snapshot(s) under %s" % (seen, root))
    return None, notes


def content_dump(db_path: str | Path) -> list[str]:
    """Everything the database HOLDS, as SQL, with the ledger's own rows left
    out -- read-only, and never raising for a database that will not open.

    ``schema_migrations`` is excluded because its ``applied_at`` is wall-clock:
    a re-derivation would differ from the live database on nothing but the
    minute it ran.  The ledger is not thereby unchecked -- conditions 2 and 5
    compare its VERSIONS directly, which is the part that carries meaning.

    ``iterdump`` and not a table-by-table walk on purpose: it covers tables this
    module has never heard of, including whatever a future migration adds, so
    the comparison does not quietly stop noticing new data.
    """
    try:
        db = _read_only_connection(Path(db_path))
    except sqlite3.Error as error:
        return ["UNREADABLE: %r" % (error,)]
    try:
        lines = [line for line in db.iterdump()]
    except (sqlite3.Error, TypeError) as error:
        return ["UNDUMPABLE: %r" % (error,)]
    finally:
        db.close()
    return [
        line for line in lines
        if "schema_migrations" not in line and line not in ("BEGIN TRANSACTION;", "COMMIT;")
    ]


def derive_from_snapshot(
    snapshot: Path, migrations_dir: str | Path
) -> tuple[list[str], set[int], str | None]:
    """Apply this repository's migrations to a COPY of ``snapshot`` and return
    ``(content dump of the result, versions applied before, error or None)``.

    This is condition 5, and it is the only condition that is a function of the
    difference between the pinned state and the current one.  The copy lives in
    ``tempfile.TemporaryDirectory()``; nothing the caller named is opened for
    writing at any point.

    The runner used is the repository's real ``SQLiteStore.migrate`` -- a
    re-implementation here would be answering a different question from the one
    the live database was actually migrated by, which is the whole failure this
    condition exists to detect.
    """
    from .store import SQLiteStore

    with tempfile.TemporaryDirectory(prefix="pf_canon_gate_") as scratch:
        work = Path(scratch) / "derived.sqlite3"
        try:
            shutil.copyfile(snapshot, work)
        except OSError as error:
            return [], set(), "could not copy the snapshot to derive from it: %r" % (error,)
        before = ledger_rows(work)
        if before is None:
            return [], set(), (
                "the snapshot's own ledger could not be read, so what was applied "
                "at the moment of the pin is unknown"
            )
        try:
            SQLiteStore(work, Path(migrations_dir)).migrate()
        except Exception as error:  # noqa: BLE001 -- reported, never raised out
            return [], set(before), (
                "this repository's migrations do not apply to the pinned state: %r"
                % (error,)
            )
        return content_dump(work), set(before), None


def classify(
    db_path: str | Path,
    migrations_dir: str | Path,
    expect_sha: str | None,
    backups_root: str | Path | None = None,
) -> CanonGateResult:
    """The whole decision, with no side effects of any kind."""
    database = Path(db_path)
    expected = normalise_sha(expect_sha)
    evidence: dict = {
        "database": str(database),
        "migrations": str(Path(migrations_dir)),
    }

    if not database.is_file():
        return CanonGateResult(
            UNEXPLAINED, None, expected,
            reasons=["canonical database is not a file: %s" % database],
            evidence=evidence,
        )
    try:
        actual = sha256_file(database)
    except OSError as error:
        return CanonGateResult(
            UNEXPLAINED, None, expected,
            reasons=["canonical database could not be read: %r" % (error,)],
            evidence=evidence,
        )
    evidence["actual_sha"] = actual

    if expected is None:
        # Deliberately NOT compared against ``actual`` first: with no valid pin
        # there is nothing to be unchanged FROM, and reporting UNCHANGED here
        # would let an empty CANON_SHA.txt pass the gate forever.
        return CanonGateResult(
            UNEXPLAINED, actual, None,
            reasons=[
                "expected sha is not a 64-character hex sha256: %r -- a missing or "
                "malformed pin explains nothing and must not be rotated" % (expect_sha,)
            ],
            evidence=evidence,
        )
    evidence["expected_sha"] = expected

    if actual == expected:
        return CanonGateResult(
            UNCHANGED, actual, expected,
            reasons=["canonical database still hashes to the pinned value"],
            evidence=evidence,
        )

    reasons: list[str] = []

    on_disk = migration_checksums(migrations_dir)
    ledger = ledger_rows(database)
    evidence["migrations_on_disk"] = sorted(on_disk)
    if not on_disk:
        # Both sides of every set comparison below are then empty, and an empty
        # set difference is not evidence of agreement -- it is evidence that
        # nothing was compared.  Measured: with ``--migrations`` pointing at a
        # path that did not exist and an emptied ledger, the first version of
        # this module returned EXPLAINED_BY_MIGRATION.
        reasons.append(
            "no migration files were found under %s -- a gate cannot say a "
            "migration explains anything when it has no migrations to compare "
            "against (check the --migrations path)" % Path(migrations_dir)
        )
    if ledger is None:
        evidence["ledger"] = None
        reasons.append(
            "schema_migrations could not be read as a versioned ledger with a "
            "checksum column -- this database cannot account for its own schema"
        )
    else:
        evidence["ledger"] = sorted(ledger)
        missing = sorted(set(on_disk) - set(ledger))
        extra = sorted(set(ledger) - set(on_disk))
        if missing:
            reasons.append(
                "migrations on disk that this database has not applied: %s -- the "
                "change cannot be the work of a completed migration run" % missing
            )
        if extra:
            reasons.append(
                "versions applied that this repository does not have files for: %s "
                "-- the database is ahead of this working tree" % extra
            )
        mismatched = [
            version
            for version in sorted(set(on_disk) & set(ledger))
            if ledger[version] != on_disk[version]
        ]
        if mismatched:
            reasons.append(
                "applied checksum differs from the file in this working tree for "
                "version(s) %s -- the ledger describes migration bytes this "
                "repository no longer contains" % mismatched
            )

    integrity = integrity_check(database)
    evidence["integrity_check"] = integrity
    if integrity != "ok":
        reasons.append("PRAGMA integrity_check did not return ok: %s" % integrity)

    snapshot, notes = find_snapshot_of_sha(database, expected, backups_root)
    evidence["snapshot_of_pinned_bytes"] = str(snapshot) if snapshot else None
    evidence["snapshot_notes"] = notes
    if snapshot is None:
        reasons.append(
            "no completed, still-restorable snapshot of the PINNED bytes (%s) was "
            "found for this database -- rotating the pin would discard the only "
            "record of what the database looked like before; %s"
            % (expected, "; ".join(notes))
        )

    if snapshot is not None:
        derived, applied_before, failure = derive_from_snapshot(snapshot, migrations_dir)
        evidence["versions_applied_at_the_pin"] = sorted(applied_before)
        if failure is not None:
            reasons.append(failure)
        else:
            applied_now = set(ledger or {})
            new_versions = sorted(applied_now - applied_before)
            evidence["migrations_run_since_the_pin"] = new_versions
            if not new_versions:
                # The condition the first version of this module was missing
                # entirely.  Every other check describes the database as it
                # stands; this one is anchored to the pin.  Without it a
                # ``DELETE FROM accounts`` on a database whose boot had already
                # snapshotted came back EXPLAINED, exit 20, and the caller
                # pinned the vandalised file.
                reasons.append(
                    "no migration has been applied since the pin was taken "
                    "(versions applied then and now are both %s) -- whatever "
                    "changed this file, it was not a migration"
                    % sorted(applied_now)
                )
            else:
                live = content_dump(database)
                if live != derived:
                    evidence["content_matches_derivation"] = False
                    reasons.append(
                        "applying migration(s) %s to the pinned state does not "
                        "reproduce what is on disk (%d dumped statement(s) here "
                        "vs %d derived) -- something other than this "
                        "repository's migrations changed the database, so the "
                        "new state is not a migration's to explain"
                        % (new_versions, len(live), len(derived))
                    )
                else:
                    evidence["content_matches_derivation"] = True

    if reasons:
        return CanonGateResult(
            UNEXPLAINED, actual, expected, reasons=reasons, evidence=evidence
        )

    # Condition 5's derivation read the live database AFTER its sha was taken.
    # Nothing in this contract makes the caller stop the server first, so a
    # checkpoint landing mid-run would have this gate report a NEW_SHA for a
    # file state that no longer exists.  Re-hashing costs one more read and
    # turns that into a red.
    settled = sha256_file(database)
    if settled != actual:
        return CanonGateResult(
            UNEXPLAINED, actual, expected,
            reasons=[
                "the database changed while the gate was reading it (%s -> %s) -- "
                "stop the server and run this again; pinning a value read from a "
                "moving file would pin a state that never existed as a whole"
                % (actual, settled)
            ],
            evidence=evidence,
        )

    return CanonGateResult(
        EXPLAINED_BY_MIGRATION, actual, expected, new_sha=actual,
        reasons=[
            "migration(s) %s ran since the pin, and re-applying them to the "
            "pinned state reproduces this database's content exactly; ledger "
            "matches migrations/, integrity_check is ok, and the pinned state "
            "is held by a snapshot that still verifies: %s"
            % (evidence.get("migrations_run_since_the_pin"), snapshot)
        ],
        evidence=evidence,
    )


def render(result: CanonGateResult) -> list[str]:
    """The stdout lines.

    Human-readable for a ps1 transcript ON PURPOSE, with one exception: the
    ``NEW_SHA=`` line is a machine contract and is the only line a caller is
    invited to parse.  Everything else may be reworded in a later round; the
    verdict itself travels in the exit code, so nothing important depends on
    this text surviving unchanged.
    """
    lines = ["VERDICT=%s" % result.verdict]
    if result.expected_sha:
        lines.append("EXPECTED_SHA=%s" % result.expected_sha)
    if result.actual_sha:
        lines.append("ACTUAL_SHA=%s" % result.actual_sha)
    if result.verdict == EXPLAINED_BY_MIGRATION:
        lines.append("NEW_SHA=%s" % result.new_sha)
    for reason in result.reasons:
        # Reasons interpolate values that come from the DATABASE TREE -- a
        # snapshot directory's name, SQLite's own multi-line integrity_check
        # output.  Measured: a directory named with an embedded newline printed
        # a forged ``NEW_SHA=`` line onto the stdout of an exit-13 run, which
        # is the one line this contract invites the caller to parse.  Folded
        # onto one line here so no reason can ever introduce a new one.
        flat = str(reason).replace("\r", " ").replace("\n", " | ")
        lines.append("  reason: %s" % flat)
    if result.verdict == EXPLAINED_BY_MIGRATION:
        lines.append(
            "  rotate CANON_SHA.txt to NEW_SHA and log both values; this is the "
            "only exit code on which that file may be rewritten."
        )
    elif result.verdict == UNEXPLAINED:
        lines.append("  ABORT: do NOT rotate CANON_SHA.txt.")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pirateforce_foundation.persistence_canon_gate",
        description=(
            "Decide whether the canonical database's sha256 differs from its pin "
            "because a migration explains it (exit 20, rotate the pin), because "
            "nothing changed (exit 0), or for a reason nobody has accounted for "
            "(exit 13, abort)."
        ),
    )
    parser.add_argument("--db", required=True, help="path to the canonical .db file")
    parser.add_argument(
        "--migrations", required=True, help="path to this repository's migrations/ directory"
    )
    parser.add_argument(
        "--expect-sha", required=True, help="the value currently in CANON_SHA.txt"
    )
    parser.add_argument(
        "--backups-root",
        default=None,
        help="snapshot tree to search; defaults to <database's directory>/db_backups",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = classify(args.db, args.migrations, args.expect_sha, args.backups_root)
    except Exception:  # noqa: BLE001 -- see EXIT_INTERNAL_ERROR
        # The traceback goes to stderr so the ps1 transcript keeps it, and the
        # code is one no verdict uses.  Swallowing this into 13 would be a
        # smaller lie than swallowing it into 0, but it would still report a
        # judgement about the owner's database that was never made.
        traceback.print_exc()
        print(
            "VERDICT=INTERNAL_ERROR\n  ABORT: the gate itself failed; no judgement "
            "was made about the database and CANON_SHA.txt must not be rotated.",
            file=sys.stderr,
        )
        return EXIT_INTERNAL_ERROR
    for line in render(result):
        print(line)
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover -- exercised via subprocess in tests
    raise SystemExit(main())
