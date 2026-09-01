"""LANE-DB: the second-tier gate that decides whether a canonical database
whose sha no longer matches ``CANON_SHA.txt`` is EXPLAINED by this
repository's own migrations having been applied to it -- or is a difference
nobody can account for, in which case the job that called this module must
abort exactly as it aborts today.

WHY THIS FILE EXISTS.  ``CANON_SHA.txt`` pins the SHA-256 of the owner's
canonical ``state/pirateforce.sqlite3``.  It lives in the SIBLING repository
``pf_bridge`` -- not in this one -- so none of the paths named below can be
re-derived from a fresh clone of this repository, and every one of them was
read at ``../pf_bridge`` on a machine that has both.

**16** scripts under ``pf_bridge/staged/`` compare that pin, in three shapes
(counted by reading them, after an earlier letter of this lane's claimed
"two, measured" and was wrong):

* pin-vs-file, ``exit 13`` -- ``175_...ps1:122`` (``-cne``, CASE-SENSITIVE),
  ``168``, ``169``, ``178``, ``179``; and ``143``, ``145``, ``146``, ``147``
  with the case-insensitive ``-ne``.
* pin-vs-file at BOOT, ``exit 13`` -- ``072``, ``087``, ``090``, ``097``,
  ``126``.  These are the ones an attended round runs, so the first correct
  upgrade of the canonical database stops the owner's next test session from
  starting at all.  ``0949_gt027_stalepad_canonical_guard.ps1:63`` is a
  sixteenth, and exits **23**, not 13.
* ``TEMPLATE_teardown_generic.ps1`` reports ``RED`` at ``:424`` and again at
  ``:826``.

!! A ROTATION DOES NOT SATISFY ALL OF THEM.  ``175_...ps1:245`` (and the same
shape in 143, 145, 146, 147, ``168:283``, ``169:318``, ``178:490``,
``179:396``) compares the file to ITSELF before and after the run
(``$shaAfter -cne $shaBefore``) and reports ``RED: CANONICAL DB MOVED``.  A
boot-time migration during such a round trips that guard no matter what
``CANON_SHA.txt`` says.  This module cannot help there; only the job's owner
can decide what that guard should do about a migration, and this is written
down here so nobody plans an upgrade believing the rotation covers it.

That direct comparison and this lane's charter contradict each other.
``pf_bridge/notes_to_chief/20260901_1112_COO-DECISION-amend-lane-db-canonical
-db-via-migrations.md`` point 1 makes the canonical database the DESTINATION
of this lane's work: it is upgraded to the standard schema by
``SQLiteStore.migrate`` at server boot.  Every such boot changes the file's
bytes, so under the direct comparison the FIRST correct migration of the
canonical database looks identical to corruption, and the owner's gate fires
on the very act it was amended to allow.

The answer approved in ``20260901_1447_COO-DECISION-lane-db-m4-unblocked-
canon-sha-mechanism-approved-backuperror-handling.md`` point 4 is NOT to
weaken the gate and NOT to pre-compute the next sha (nobody can know it: two
migrations of the same files produce different bytes, because the ledger
records a timestamp).  It is to answer a narrower question, from evidence
present on the machine at the moment of the check:

    the sha changed -- is the database now exactly what this repository's
    ``migrations/`` say it should be, does SQLite still consider it intact,
    and are the bytes it had BEFORE the change still recoverable?

Only all three together earn a rotation of ``CANON_SHA.txt``.

## THE THREE ANSWERS AND THEIR EXIT CODES

The exit code is the answer; stdout is for the log.  The caller's contract is
in ``pf_bridge/notes_to_chief/20260901_1515_LANE-DB-REQUEST-chief-staged-
canon-gate-spec-and-backuperror-wrapper.md`` section (b.1).

===== ==================================== ===================================
exit  result                               what the caller must do
===== ==================================== ===================================
0     ``UNCHANGED``                        carry on, as today
75    ``EXPLAINED_BY_MIGRATION``           rotate ``CANON_SHA.txt`` to the
                                           ``NEW_SHA=`` line, log before/after
13    ``UNEXPLAINED``                      ABORT, exactly as today.  NEVER
                                           rotate.
other this module itself broke             ABORT.  Never read as ``UNCHANGED``
===== ==================================== ===================================

``13`` is deliberately the number those ps1 jobs already exit with when the
sha does not match, so a job that has NOT been rewired yet keeps its current
behaviour if it ever calls this module by accident.

!! ``NEW_SHA=`` IS PRINTED ON EXIT 75 AND ON NO OTHER PATH.  The whole gate
collapses if a caller can grep a rotation candidate out of a run that refused
to authorise one, so the other results print ``ACTUAL_SHA=`` instead and the
string ``NEW_SHA`` never appears in their output.

!! SHA VALUES ARE PRINTED IN UPPERCASE, because that is what
``Get-FileHash`` produces and what ``CANON_SHA.txt`` holds today, and because
``175_round109_path_d_ci_status_gate_commit.ps1:122`` compares with ``-cne``
-- the CASE-SENSITIVE operator.  A lowercase digest written into that file by
a rotation would make the very next run of a job that still does its own
comparison abort against a database that had not changed at all.  Comparison
INSIDE this module is case-insensitive, so a file already holding either case
is read correctly.

## FAIL-SAFE DIRECTION

Every uncertainty resolves toward ``UNEXPLAINED``: an unreadable ledger, an
unparseable manifest, a missing migrations directory, a snapshot that no
longer re-verifies, a garbage ``--expect-sha``.  ``EXPLAINED_BY_MIGRATION``
is only ever reached by proving three positive facts, never by failing to
find a problem.

## WHAT THIS MODULE NEVER DOES

It never writes to the canonical database itself, never migrates, never
rotates ``CANON_SHA.txt`` (the caller does that, and only on 75), and never
deletes a snapshot.  Every connection it opens is a strict ``mode=ro`` URI
borrowed from ``persistence_backup._read_only_connection``.

!! IT IS NOT TRUE THAT IT LEAVES THE DATABASE'S DIRECTORY UNTOUCHED, and an
earlier version of this docstring said so.  Measured (pf-adversary D5) on a
quiescent migrated database: after one ``evaluate`` the directory has gained
``<name>-shm`` and a zero-byte ``<name>-wal``, and they are still there
afterwards.  That is SQLite's own recovery -- attaching any reader to a WAL
database rebuilds the index -- and ``persistence_backup.applied_versions``
says the same thing about itself in its own docstring, which the first draft
of this file did not finish reading.  The sidecars are deliberately LEFT
where they are: removing a ``-wal`` beside a live database is the one
irreversible act ``persistence_backup``'s rule 1 exists to forbid, and doing
it here to keep a tidier claim would spend the owner's committed data on a
tidier sentence.  What IS true: no byte of the database file changes, and the gate
takes no write lock on it.

ASCII only, like the rest of this repository's Python: the bridge console is
code page 874.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from .persistence_backup import (
    INCOMPLETE_SUFFIX,
    applied_versions,
    MIGRATION_GLOB,
    BackupError,
    _read_only_connection,
    _require_path_safe,
    _sha256_file,
    _snapshot_is_still_good,
    default_backups_root,
)

RESULT_UNCHANGED = "UNCHANGED"
RESULT_EXPLAINED = "EXPLAINED_BY_MIGRATION"
RESULT_UNEXPLAINED = "UNEXPLAINED"

EXIT_UNCHANGED = 0

#: !! CHANGED FROM 20, and the change is a correction, not a preference.
#: 20 is ALREADY TAKEN in the bridge, with the opposite meaning, and a caller
#: that branches on it would read "rotate the pin and go on" out of a script
#: saying the round is ruined.  Measured on `pf_bridge/staged/*.ps1`
#: (36 files) this round:
#:   `TEMPLATE_teardown_generic.ps1:520-521` -- "THIS ROUND IS DEGRADED, NOT
#:       GREEN (exit 20)"
#:   `072_gt001_boot.ps1:72` -- "ABORT: no server PID", exit 20
#: 75 was then measured free across every spelling those scripts use
#: (`exit N`, `-Code N`, `::Exit(N)`, `SetShouldExit(N)`): zero hits.
#: Nothing calls this module yet in either repository, so the value can still
#: be corrected without breaking a caller; once `staged/` is wired it cannot.
EXIT_EXPLAINED = 75
EXIT_UNEXPLAINED = 13

#: Returned when this module raises something it did not plan for.  Distinct
#: from all three verdicts on purpose: the spec's last row says a caller must
#: treat an unknown code as ABORT rather than as ``UNCHANGED``, and that is
#: only possible if a broken run cannot land on 0.
EXIT_MODULE_ERROR = 70

@dataclass(frozen=True)
class Verdict:
    """The whole answer.  ``new_sha`` is set on ``EXPLAINED_BY_MIGRATION``
    and on nothing else -- see the module docstring."""

    result: str
    exit_code: int
    actual_sha: str | None
    new_sha: str | None
    snapshot: Path | None
    reasons: tuple[str, ...]


def _unexplained(*reasons: str, actual_sha: str | None = None) -> Verdict:
    return Verdict(
        result=RESULT_UNEXPLAINED,
        exit_code=EXIT_UNEXPLAINED,
        actual_sha=actual_sha,
        new_sha=None,
        snapshot=None,
        reasons=tuple(reasons),
    )


def normalise_sha(value: object) -> str | None:
    """Lowercase 64-hex form of ``value``, or ``None`` when it is not a
    SHA-256 at all.

    ``None`` is what makes a corrupt or empty ``CANON_SHA.txt`` an
    ``UNEXPLAINED`` rather than an accident: an expectation nobody can read
    must never be able to match, and must never be able to be "explained".
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if len(text) != 64:
        return None
    # NOT `int(text, 16)`: that accepts `+aaa...`, `0xaa...` and `aa_aa...`
    # as "hexadecimal" (measured by pf-adversary, D11).  A digest is exactly
    # 64 characters drawn from one alphabet, and nothing else is one.
    if any(character not in "0123456789abcdefABCDEF" for character in text):
        return None
    return text.lower()


def _bad_expectation(value: object) -> str:
    """The reason line for an unreadable ``--expect-sha``, describing the
    value WITHOUT quoting it back.

    pf-adversary D3/D7, both measured.  The first version interpolated the
    caller's own string with ``%r``, so ``--expect-sha "NEW_SHA=DEADBEEF..."``
    put the token ``NEW_SHA`` into the output of an EXIT 13 run -- breaking
    this module's loudest invariant, and enough to poison a caller that
    rotates by grepping for that token.  The same echo carried arbitrary
    non-ASCII into a ``print`` that, under the bridge's cp874 console, raised
    ``UnicodeEncodeError`` and produced exit 1 with NO ``RESULT=`` line at
    all.  Describing the value closes both: nothing the caller supplies is
    ever reproduced.
    """
    if not isinstance(value, str):
        return (
            "the expected sha is not text at all (it is a %s), so no database "
            "can match it" % type(value).__name__
        )
    stripped = value.strip()
    return (
        "the expected sha is not 64 hexadecimal characters (it is %d "
        "character(s)%s), so no database can match it -- check CANON_SHA.txt"
        % (
            len(stripped),
            "" if len(stripped) != 64 else " and carries a non-hexadecimal one",
        )
    )


def ledger_matches_migrations(
    db_path: str | Path, migrations_dir: str | Path
) -> tuple[bool, tuple[str, ...]]:
    """True only when the ledger in the database records EXACTLY the
    migrations this repository ships, each with the checksum of the file's
    current bytes.

    This is the check that makes "explained by migration" mean something
    narrow.  ``SQLiteStore.migrate`` (``store.py``) writes
    ``schema_migrations(version, applied_at, checksum)`` where ``checksum`` is
    the SHA-256 of the migration file it applied, so a database that has been
    brought up to this repository's schema -- and to no other -- produces an
    exact set equality plus an exact checksum match.  Three things it
    therefore refuses, each of which the direct sha comparison could not tell
    apart from a legitimate migration:

    * a ledger row for a version this repository does not have (the database
      is NEWER than the server, the same condition ``store.migrate`` raises
      "database schema is newer than this server" for),
    * a migration file present on disk that the database has not applied (the
      boot did not finish, or migrated a different database),
    * a checksum that differs from the file's bytes today (the migration file
      was edited after it was applied -- the exact thing
      ``migrations/`` numbering rules forbid, and what ``store.migrate``
      raises "migration checksum mismatch" for).
    """
    reasons: list[str] = []
    directory = Path(migrations_dir)
    if not directory.is_dir():
        return False, ("no migrations directory at %s" % directory,)
    files = sorted(directory.glob(MIGRATION_GLOB))
    if not files:
        return False, ("no migration files under %s" % directory,)
    versions = [int(path.name[:3]) for path in files]
    if len(versions) != len(set(versions)):
        # `store.migrate` raises on this; a gate that shrugged would authorise
        # a rotation against a migrations directory the server cannot run.
        return False, ("duplicate migration version under %s" % directory,)
    on_disk = {
        version: hashlib.sha256(path.read_bytes()).hexdigest()
        for path, version in zip(files, versions)
    }

    path = Path(db_path)
    try:
        db = _read_only_connection(path)
    except sqlite3.Error as error:
        return False, ("cannot open %s read-only: %r" % (path, error),)
    try:
        rows = db.execute("SELECT version,checksum FROM schema_migrations").fetchall()
    except sqlite3.Error as error:
        # No ledger table, a hot WAL this read-only handle cannot follow,
        # corruption.  None of them is "explained".
        return False, ("cannot read schema_migrations from %s: %r" % (path, error),)
    finally:
        db.close()

    ledger: dict[int, str] = {}
    for row in rows:
        try:
            version = int(row[0])
        except (TypeError, ValueError):
            return False, ("schema_migrations holds a non-integer version: %r" % (row[0],),)
        if not isinstance(row[1], str):
            # A NULL checksum is a ledger the checksum upgrade in
            # `store.migrate` has not finished with.  Unprovable, so refused.
            return False, ("schema_migrations version %d has no checksum" % version,)
        ledger[version] = row[1].strip().lower()

    unknown = sorted(set(ledger) - set(on_disk))
    if unknown:
        reasons.append(
            "the database records migration(s) this repository does not ship: %s"
            % ", ".join(str(version) for version in unknown)
        )
    missing = sorted(set(on_disk) - set(ledger))
    if missing:
        reasons.append(
            "migration(s) on disk that the database has not applied: %s"
            % ", ".join(str(version) for version in missing)
        )
    for version in sorted(set(on_disk) & set(ledger)):
        if ledger[version] != on_disk[version]:
            reasons.append(
                "migration %03d checksum in the ledger does not match the file "
                "on disk" % version
            )
    if reasons:
        return False, tuple(reasons)
    return True, ()


def integrity_ok(db_path: str | Path) -> tuple[bool, tuple[str, ...]]:
    """SQLite's own verdict on the file, read strictly read-only."""
    path = Path(db_path)
    try:
        db = _read_only_connection(path)
    except sqlite3.Error as error:
        return False, ("cannot open %s read-only: %r" % (path, error),)
    try:
        row = db.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as error:
        return False, ("integrity_check on %s failed to run: %r" % (path, error),)
    finally:
        db.close()
    verdict = "" if row is None else str(row[0])
    if verdict.lower() != "ok":
        return False, ("integrity_check on %s says: %s" % (path, verdict),)
    return True, ()


def _names_this_database(manifest: dict, db: Path) -> bool:
    """True when the manifest says it was taken from ``db`` (already
    resolved).  A snapshot of a DIFFERENT database that happened to hold the
    same bytes is not a backup of this one."""
    source = manifest.get("source_database")
    if not isinstance(source, str):
        return False
    try:
        return Path(source).resolve() == db
    except OSError:
        return False


def _is_within(path: Path, root: Path) -> bool:
    """True when ``path`` is the same as, or under, ``root`` -- both already
    resolved by the caller, so a symlink cannot smuggle a path past this."""
    try:
        settled_root = root.resolve()
    except OSError:
        return False
    return path == settled_root or settled_root in path.parents


def recoverable_snapshot(
    db_path: str | Path, expect_sha: str, backups_root: str | Path | None = None
) -> tuple[Path | None, tuple[str, ...]]:
    """The snapshot that still holds the bytes ``expect_sha`` names, or
    ``None``.

    THIS IS THE CHECK THE OWNER'S RULE IS ABOUT.  A rotation of
    ``CANON_SHA.txt`` throws away the last written record of what the database
    used to be; the owner's standing ban on "cannot be undone, no backup"
    (``20260901_1112`` point 3) means the gate may only authorise that when
    the old bytes are still on disk and still readable.  The link is exact
    is recorded rather than recomputed: ``persistence_backup`` writes the
    SHA-256 of the source file it copied into ``MANIFEST.json`` under
    ``source_fingerprint.sha256``, so a snapshot whose manifest names
    ``expect_sha`` was taken from the database ``CANON_SHA.txt`` still
    describes.

    !! TWO THINGS THAT CLAIM IS NOT, both measured (pf-adversary D8).  First,
    the snapshot is NOT a byte copy: ``_copy_consistent`` uses SQLite's
    online-backup API, so the snapshot file is a rebuild with the same
    contents and a different digest.  Restoring it therefore does NOT give
    back a file whose ``Get-FileHash`` equals the old pin -- what is
    recoverable is the DATA, not the bytes, and any recovery still ends with
    a rotation.  Second, the link is only as good as a JSON string this
    module cannot authenticate: ``_snapshot_is_still_good`` re-proves the
    snapshot against its OWN ``verification`` block, which is self-consistent
    by construction, so a manifest whose ``source_fingerprint.sha256`` was
    edited names a moment that never existed and the gate believes it.  That
    is the residual this module cannot close from disk; it is stated in the
    round file and was put to COO in writing.

    The candidate is then re-proved with ``persistence_backup``'s own
    ``_snapshot_is_still_good`` -- re-hashed against its manifest and
    re-opened -- because a backup nobody has opened is a claim, not a backup,
    and this is the one moment where believing a stale claim costs the only
    copy of the original bytes.
    """
    # `CANON_SHA.txt` holds the UPPERCASE form `Get-FileHash` writes, and this
    # function is public: the one-off canonical-upgrade job
    # (`20260901_1515` section b.2) is expected to call it with that value
    # verbatim.  Normalising here rather than trusting the caller was found by
    # measurement, not by reading -- handed the uppercase digest, the version
    # that only normalised the MANIFEST side answered "no backup exists" for a
    # snapshot sitting right there.  The failure direction was safe (a false
    # UNEXPLAINED, never a false EXPLAINED) but the answer was still wrong.
    wanted = normalise_sha(expect_sha)
    if wanted is None:
        return None, (_bad_expectation(expect_sha),)
    db = Path(db_path).resolve()
    root = Path(backups_root) if backups_root is not None else default_backups_root(db)
    if not root.is_dir():
        return None, ("no snapshot directory at %s" % root,)

    rejected: list[str] = []
    seen_newer = False
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
        if not isinstance(manifest, dict):
            continue
        fingerprint = manifest.get("source_fingerprint")
        if not isinstance(fingerprint, dict):
            continue
        # D1, pf-adversary, CRITICAL.  Until this rule existed the loop
        # accepted ANY completed snapshot naming the pin, from any boot, any
        # date -- so a database that had been migrated correctly last week and
        # then had `DELETE FROM accounts` run on it today still came back
        # EXPLAINED, because a snapshot naming the stale pin was still on
        # disk.  Measured: 200 rows deleted, verdict `EXPLAINED_BY_MIGRATION`
        # (exit 20 at the time; the code is 75 now).  The letter this module
        # implements says the copy must be
        # "of that boot" (`20260901_1515` section b.1); a snapshot with a
        # newer sibling is by definition not the copy of the most recent one.
        # Snapshot directory names begin with a UTC timestamp
        # (`persistence_backup._utc_stamp`), so newest-first iteration makes
        # the FIRST snapshot of this database the only admissible candidate.
        if normalise_sha(fingerprint.get("sha256")) != wanted:
            if _names_this_database(manifest, db):
                seen_newer = True
                rejected.append(
                    "%s is a NEWER snapshot of this database and it does not "
                    "carry the sha CANON_SHA.txt names -- the pin is more "
                    "than one boot behind, so what changed since cannot be "
                    "attributed to a migration" % directory.name
                )
                break
            continue
        if seen_newer:
            break
        # A snapshot of a DIFFERENT database that happens to have held the
        # same bytes is not a backup of this one.
        if not _names_this_database(manifest, db):
            rejected.append(
                "%s carries the expected sha but was taken from another "
                "database" % directory.name
            )
            continue
        name = manifest.get("snapshot_database")
        # The name comes off a file on disk and is never joined as given: a
        # manifest saying `../../pirateforce.sqlite3` must not be able to
        # offer the LIVE database as its own backup.  The rule is
        # `persistence_backup._require_path_safe`, REUSED rather than
        # re-spelled -- pf-adversary D6 measured that the hand-written
        # separator test this replaced was incomplete on the only platform
        # the gate runs on: `D:evil.sqlite3` contains neither `/` nor `\`
        # and still leaves the snapshot tree, and `x.sqlite3:ads` names an
        # NTFS alternate data stream.  That function forbids `:` and every
        # other reserved character, and it is the same rule the snapshot
        # WRITER validates against, so the two cannot drift apart.
        if not isinstance(name, str):
            rejected.append("%s names no snapshot file at all" % directory.name)
            continue
        try:
            _require_path_safe("database name", name)
        except BackupError as error:
            rejected.append("%s: %s" % (directory.name, error))
            continue
        candidate = directory / name
        if not candidate.is_file():
            rejected.append("%s has no %s in it any more" % (directory.name, name))
            continue
        # Containment, checked on the RESOLVED path rather than on the name.
        # pf-adversary D10: a junction inside `db_backups/` pointing at the
        # state directory made the gate offer the LIVE database as its own
        # backup -- and `_verify_snapshot`, following that link, unlinked the
        # live `-wal` and destroyed 50 committed transactions.  A name-based
        # rule cannot see a link; this does.
        try:
            settled = candidate.resolve()
        except OSError as error:
            rejected.append("%s cannot be resolved: %r" % (directory.name, error))
            continue
        if settled == db or not _is_within(settled, root):
            rejected.append(
                "%s points at %s, which is not inside the snapshot tree -- "
                "refusing to treat it as a backup" % (directory.name, settled)
            )
            continue
        try:
            still_good = _snapshot_is_still_good(candidate, manifest)
        except (BackupError, sqlite3.Error, OSError) as error:
            rejected.append("%s could not be re-verified: %r" % (directory.name, error))
            continue
        if not still_good:
            rejected.append(
                "%s no longer matches its own manifest -- it is not a backup "
                "any more" % directory.name
            )
            continue
        return candidate, ()

    if rejected:
        return None, tuple(
            ["no usable snapshot holds the pre-change bytes:"] + rejected
        )
    return None, (
        "no snapshot under %s was taken from %s while it held the sha "
        "CANON_SHA.txt names, so the pre-change bytes are not recoverable"
        % (root, db),
    )


def evaluate(
    db_path: str | Path,
    migrations_dir: str | Path,
    expect_sha: str,
    backups_root: str | Path | None = None,
) -> Verdict:
    """The whole decision, with no side effect on the canonical database."""
    expected = normalise_sha(expect_sha)
    if expected is None:
        return _unexplained(_bad_expectation(expect_sha))
    db = Path(db_path)
    if not db.is_file():
        return _unexplained("there is no database file at %s" % db)
    try:
        actual = _sha256_file(db)
    except OSError as error:
        return _unexplained("cannot read %s: %r" % (db, error))

    if actual == expected:
        reasons = ["the database is byte-identical to the sha CANON_SHA.txt names"]
        # `CANON_SHA.txt` fingerprints the MAIN FILE only -- that is what
        # `Get-FileHash` hashes, and this gate answers the same question so
        # that a job which has not been rewired keeps its behaviour exactly.
        # But a committed transaction can live entirely in `-wal` with the
        # main file untouched, so "the file matches" and "the database holds
        # what it held" are not the same sentence.  The verdict is NOT
        # changed by this (that would make the gate stricter than the jobs it
        # replaces, on a state a killed server leaves behind routinely); the
        # difference is simply not left unsaid.
        hot = db.with_name(db.name + "-wal")
        try:
            pending = hot.is_file() and hot.stat().st_size > 0
        except OSError:
            pending = False
        if pending:
            reasons.append(
                "NOTE: a non-empty %s sits beside it, so committed data may "
                "exist that this sha does not cover -- CANON_SHA.txt "
                "fingerprints the main file only" % hot.name
            )
        return Verdict(
            result=RESULT_UNCHANGED,
            exit_code=EXIT_UNCHANGED,
            actual_sha=actual,
            new_sha=None,
            snapshot=None,
            reasons=tuple(reasons),
        )

    reasons: list[str] = []
    ledger_ok, ledger_reasons = ledger_matches_migrations(db, migrations_dir)
    reasons.extend(ledger_reasons)
    intact, integrity_reasons = integrity_ok(db)
    reasons.extend(integrity_reasons)
    snapshot, snapshot_reasons = recoverable_snapshot(db, expected, backups_root)
    reasons.extend(snapshot_reasons)

    if ledger_ok and intact and snapshot is not None:
        bound, binding_reasons = _schema_came_from_that_boot(db, snapshot)
        reasons.extend(binding_reasons)
        if bound:
            # D4, pf-adversary, measured 40/40 under a concurrent writer: the
            # sha was taken BEFORE three checks that each re-open the file, and
            # handed back as the value to write into `CANON_SHA.txt`.  A
            # rotation to a stale digest leaves every ps1 guard aborting
            # forever against a database nobody touched.  Re-hash and refuse
            # if anything moved underneath: the whole verdict was computed
            # about a file that no longer exists as it was.
            try:
                settled = _sha256_file(db)
            except OSError as error:
                return _unexplained(
                    "cannot re-read %s to confirm the rotation value: %r"
                    % (db, error),
                    actual_sha=actual,
                )
            if settled != actual:
                return _unexplained(
                    "the database changed WHILE this gate was judging it "
                    "(%s -> %s) -- nothing here describes the file as it is "
                    "now, so no rotation value is offered"
                    % (actual.upper(), settled.upper()),
                    actual_sha=settled,
                )
            return Verdict(
                result=RESULT_EXPLAINED,
                exit_code=EXIT_EXPLAINED,
                actual_sha=actual,
                new_sha=actual,
                snapshot=snapshot,
                reasons=(
                    "the ledger records exactly this repository's migrations, "
                    "it is exactly the ledger the boot that took the snapshot "
                    "above set out to produce, integrity_check says ok, and "
                    "the pre-change bytes are still recoverable",
                ),
            )
    return _unexplained(*reasons, actual_sha=actual)


def _schema_came_from_that_boot(
    db: Path, snapshot: Path
) -> tuple[bool, tuple[str, ...]]:
    """True when the ledger the database carries NOW is exactly the ledger the
    boot that took ``snapshot`` set out to produce.

    pf-adversary D1 (CRITICAL) is the reason this exists.  Without it the
    only question asked was "does a snapshot naming the pin exist", which any
    old snapshot answers -- so a database migrated correctly last week and
    then emptied today still came back ``EXPLAINED``.  The letter this module
    implements says the copy must be the pre-migrate copy OF THAT BOOT
    (``20260901_1515`` section b.1), and ``persistence_backup`` records
    exactly what that boot was about to do: ``pending_versions`` in the
    manifest, and ``verification.schema_migrations_in_snapshot`` -- the
    ledger as it stood inside the copy.  Their union is the ledger that boot
    would produce if it succeeded; anything else means this database's schema
    was not made by the boot this snapshot belongs to.

    !! WHAT THIS STILL DOES NOT PROVE, and no evidence on disk can:
    that ONLY a migration changed the bytes.  Rows written in the same boot,
    after the migration, leave the ledger untouched and are invisible here.
    ``EXPLAINED`` therefore means "the schema is exactly this repository's,
    made by the boot whose snapshot is still on disk, and the pre-change
    bytes are recoverable" -- it does NOT mean "nothing else happened".  The
    caller closes that gap, not this module: the upgrade job runs with the
    server stopped and calls the gate immediately (``20260901_1515`` section
    b.2, steps 1 and 5).  Raised with COO in writing rather than left here.
    """
    manifest_path = snapshot.parent / "MANIFEST.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return False, ("cannot re-read %s: %r" % (manifest_path, error),)
    if not isinstance(manifest, dict):
        return False, ("%s is not a manifest object" % manifest_path,)
    verification = manifest.get("verification")
    inside = verification.get("schema_migrations_in_snapshot") if isinstance(
        verification, dict
    ) else None
    pending = manifest.get("pending_versions")
    if not isinstance(inside, list) or not isinstance(pending, list):
        return False, (
            "%s does not record what its boot was about to apply, so this "
            "database's schema cannot be attributed to it" % snapshot.parent.name,
        )
    try:
        expected_ledger = {int(version) for version in inside} | {
            int(version) for version in pending
        }
    except (TypeError, ValueError):
        return False, ("%s records unreadable version numbers" % snapshot.parent.name,)
    now = applied_versions(db)
    if now is None:
        return False, ("the ledger in %s cannot be read" % db,)
    if now != expected_ledger:
        return False, (
            "the ledger is %s but the boot that took %s set out to produce "
            "%s -- this schema was not made by that boot"
            % (
                sorted(now),
                snapshot.parent.name,
                sorted(expected_ledger),
            ),
        )
    return True, ()


def render(verdict: Verdict, db_path: str | Path) -> str:
    """The log lines.  ``NEW_SHA=`` appears on exit 75 and nowhere else."""
    lines = [
        "RESULT=%s" % verdict.result,
        "DB=%s" % Path(db_path).resolve(),
    ]
    if verdict.actual_sha is not None:
        if verdict.new_sha is not None:
            lines.append("NEW_SHA=%s" % verdict.new_sha.upper())
        else:
            lines.append("ACTUAL_SHA=%s" % verdict.actual_sha.upper())
    if verdict.snapshot is not None:
        lines.append("SNAPSHOT=%s" % verdict.snapshot)
    lines.extend("REASON=%s" % reason for reason in verdict.reasons)
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pirateforce_foundation.persistence_canon_gate",
        description=(
            "Decide whether a canonical database whose sha differs from "
            "CANON_SHA.txt is explained by this repository's migrations. "
            "Exit 0 UNCHANGED, 75 EXPLAINED_BY_MIGRATION (rotate "
            "CANON_SHA.txt to NEW_SHA), 13 UNEXPLAINED (abort), anything "
            "else means this module broke (abort)."
        ),
    )
    parser.add_argument("--db", required=True, help="the canonical .db file")
    parser.add_argument(
        "--migrations", required=True, help="this repository's migrations/ directory"
    )
    parser.add_argument(
        "--expect-sha", required=True, help="the value in CANON_SHA.txt"
    )
    parser.add_argument(
        "--backups-root",
        default=None,
        help=(
            "where pre-migration snapshots live; defaults to the db_backups/ "
            "directory persistence_backup writes beside the database"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        verdict = evaluate(
            arguments.db,
            arguments.migrations,
            arguments.expect_sha,
            arguments.backups_root,
        )
    except Exception as error:  # the spec's "anything else means ABORT" row
        print(
            "RESULT=MODULE_ERROR\nREASON=%r" % (error,),
            file=sys.stderr,
        )
        return EXIT_MODULE_ERROR
    # One stream for every verdict.  A caller that captures only stdout must
    # get the REASON lines on the abort path too -- that is the path where a
    # human has to find out what is wrong with the owner's database.
    print(render(verdict, arguments.db))
    return verdict.exit_code


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    sys.exit(main())
