"""The second layer of the canonical-database sha gate: is a CHANGED sha
explained by a migration this lane's own backup path recorded, or not?

Why this module exists
----------------------
The gate that exists today is a sha comparison in PowerShell: read
``pf_bridge/CANON_SHA.txt``, hash the canonical database, ``exit 13`` when the
two differ.  It is not one script -- measured this round, ``CANON_SHA.txt`` is
named in 19 files under ``pf_bridge/staged/``, twelve of which abort on a
mismatch (``175_round109_path_d_ci_status_gate_commit.ps1`` is the one this
lane cited first, and 143/145/146/147/168/169/178/179 plus the boot scripts
072/087/090/097/126 carry their own variants).  That matters for whoever wires
this module in: the integration is many sites wide, and every site not wired
keeps exiting 13 on a legitimately migrated database.

That gate is correct and must stay, but it has one outcome for two very
different worlds:

* the file changed because a migration of this lane ran, which is the whole
  point of `COO-DECISION 20260901_1112` (the canonical database becomes the
  standard schema THROUGH these migrations), and
* the file changed for a reason nobody can name, which is the thing the gate
  is there to stop.

`COO-DECISION 20260901_1447` point 4 approved this module with exactly three
outcomes and told this lane not to change the shape:

===========================  =========  =========================================
outcome                      exit code  meaning for the caller
===========================  =========  =========================================
``UNCHANGED``                0          the database hashes to the recorded canon
``EXPLAINED_BY_MIGRATION``   75         changed, and the change is evidenced;
                                        rotate ``CANON_SHA.txt`` to the printed
                                        ``NEW_SHA=`` value -- AS ASCII (see the
                                        rotation warning below).  Under
                                        ``--json`` there is NO ``NEW_SHA=``
                                        line: the value is the
                                        ``new_canon_sha`` field, because a
                                        stream that has to parse as JSON
                                        cannot also carry a bare token line
``UNEXPLAINED``              13         stop.  13 is deliberately the code the
                                        existing ps1 guards already exit with,
                                        so a caller that has not been taught
                                        about this module still fails closed
===========================  =========  =========================================

Anything else -- including 2, which covers bad arguments, ``--help`` and any
unexpected exception -- means the gate did not pass.  A caller must never treat
"the gate crashed" as "the gate was happy"; this module has no outcome that
means "probably fine", and it never exits 1 with a traceback if it can help it,
because a ps1 branching on 13 reads exit 1 as "not 13".

!! The sha cannot explain itself
-------------------------------
The dangerous way to build this layer is to look at the new sha, notice a
migration file was added to the repo lately, and call the difference explained.
That is a gate that unlocks itself in every case, which is worse than no gate:
the one scenario it would wave through is the one where somebody edited the
owner's only copy of the world by hand, exactly what
`COO-DECISION 20260901_1112` forbids.

So this module never reasons from the sha alone.  It reasons from evidence a
boot leaves behind:

1. the ledger inside the live database (``schema_migrations``: version AND
   checksum) compared against the migration files in the repo;
2. a COMPLETED pre-migration snapshot taken by
   ``persistence_backup.snapshot_database`` whose manifest records that the
   database it copied hashed to the sha we are being asked about, that
   migrations were pending at that moment, and whose OWN COPY does not already
   contain them;
3. the ``POSTSTATE.json`` that ``SQLiteStore.migrate_with_backup`` writes after
   that migration ran, recording the sha the migration PRODUCED -- which must
   equal the sha the database has right now.

!! THE HONEST LIMIT OF ALL THIS, and it is not small
-----------------------------------------------------
Every piece of evidence above lives in the backups directory.  ANYONE WHO CAN
WRITE THERE CAN WRITE ALL OF IT, and the one number a forgery needs -- the
canonical sha -- is published in ``pf_bridge/CANON_SHA.txt``.  pf-adversary
demonstrated this against an earlier draft of this module (round `gfkvro`,
defect 1): a hand-edited database plus a hand-written six-line manifest came
out ``EXPLAINED_BY_MIGRATION``, exit code and all.  Point 3 and the ledger
check in point 2 were added because of that review and they make a forgery
considerably harder -- a forger must now also produce a database that
genuinely lacks the migration and keep three separate shas consistent -- but
they do not make it impossible, and no arrangement of files inside a directory
the attacker controls ever could.

READ THIS AS: the gate separates HONEST DRIFT from A RECORDED MIGRATION.  It is
NOT an authentication boundary, it does not defend against a person with write
access to the machine, and no report may quote it as if it did.  Making it one
needs something outside this module -- a backups tree the server can write and
nobody else can, or a signature -- and that is a decision for the owner and the
COO, not for this lane.  It is on the record in
``pf_bridge/notes_to_chief/20260901_2213_LANE-DB-ASK-COO-canon-gate-is-not-an-
authentication-boundary.md``.

What this module does NOT claim (read before quoting a green result)
--------------------------------------------------------------------
* ``EXPLAINED_BY_MIGRATION`` says "this file went into a recorded migration
  from the canonical state and came back out as exactly these bytes".  Because
  point 3 pins the post-migration sha, ordinary gameplay writes AFTER that
  migration no longer ride along inside the verdict -- they make it
  ``UNEXPLAINED``, which is the fail-closed direction.  On a canonical database
  being upgraded with the server stopped that is what is wanted; on a database
  the server is actively writing, expect ``UNEXPLAINED`` and do not read it as
  tampering.
* ``UNCHANGED`` is a statement about the bytes of the main database file.  A
  database with a hot ``-wal`` beside it can hold committed transactions that
  are not in those bytes yet, and this module does not checkpoint anything to
  find out (checkpointing the owner's database to answer a question is exactly
  the kind of write this lane must not do).
* This module writes nothing, deletes nothing and rotates nothing.  ONE
  EXCEPTION, stated because an earlier draft claimed "writes nothing" and was
  measurably wrong: opening the LIVE database read-only makes SQLite rebuild
  its ``-shm`` WAL index beside it if none is there, so a ``-shm`` can appear.
  The main database file and its ``-wal`` are byte-identical afterwards
  (measured, and pinned by a test).  Files under the backups directory are
  opened ``immutable=1``, which creates nothing at all.
* Rotating ``CANON_SHA.txt`` is the caller's action, and that file lives in
  ``pf_bridge/``, outside this lane's write scope.  !! WRITE IT AS ASCII.
  Windows PowerShell 5.1's ``>`` and ``Out-File`` produce UTF-16LE by default;
  this module now decodes those too, but the file the whole bridge shares
  should stay the plain ASCII line it is today (``Set-Content -Encoding
  ascii``).

This module hashes the database BEFORE it opens anything, so the verdict is
about the bytes the gate actually saw.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .persistence_backup import (
    DEFAULT_BACKUP_DIRNAME,
    INCOMPLETE_SUFFIX,
    MIGRATION_GLOB,
    POSTSTATE_KIND,
    REASON_JOURNAL_MODE_REWRITE,
    REASON_LEDGER_REWRITE,
    _read_only_connection,
    _sha256_file,
    default_backups_root,
    hot_wal_bytes,
    immutable_connection,
    poststate_filename,
    reason_code_for,
    snapshot_ledger,
)

#: The two reasons a snapshot can carry that mean "a boot was about to rewrite
#: this database in place without any migration FILE being pending".
#: ``persistence_backup.ledger_rewrite_pending`` says in so many words that the
#: owner's canonical database is exactly the shape that hits the first of them,
#: so refusing these would have made the FIRST boot of the real canonical
#: database an unrecoverable 13 (pf-adversary, round `gfkvro`, second pass, R3
#: -- measured, both shapes).
IN_PLACE_REWRITE_REASONS = (REASON_LEDGER_REWRITE, REASON_JOURNAL_MODE_REWRITE)

# The three outcomes of `COO-DECISION 20260901_1447` point 4, verbatim.
UNCHANGED = "UNCHANGED"
EXPLAINED_BY_MIGRATION = "EXPLAINED_BY_MIGRATION"
UNEXPLAINED = "UNEXPLAINED"

#: 13 is the code all twelve canonical guards in ``pf_bridge/staged/*.ps1``
#: already exit with, so a caller that has never been taught about this module
#: still fails closed on UNEXPLAINED.
#:
#: 75 is deliberately NOT the 20 this lane proposed to chief in
#: ``20260901_1515_LANE-DB-REQUEST-chief-staged-canon-gate-spec-and-
#: backuperror-wrapper.md``.  pf-adversary (round `gfkvro`, defect 11) found
#: that 20 is already spoken for with the OPPOSITE polarity -- measured:
#: ``staged/TEMPLATE_teardown_generic.ps1:520-521`` exits 20 for "THIS ROUND IS
#: DEGRADED, NOT GREEN" and ``staged/072_gt001_boot.ps1:72`` exits 20 for
#: "ABORT: no server PID".  75 is unused by every ``exit`` in every staged
#: script (measured this round) and sits outside all of their number clusters.
EXIT_CODE = {UNCHANGED: 0, EXPLAINED_BY_MIGRATION: 75, UNEXPLAINED: 13}

#: Everything that is not a verdict: bad arguments, an unreadable expected-sha
#: file, ``--help``, and any unexpected exception.  NOT one of the three
#: outcomes -- a caller that could not be told what to check has not checked
#: anything, and must never be able to read that as a pass.
EXIT_USAGE = 2

#: The only manifest shape this gate accepts as evidence.  A future snapshot
#: format has to teach this module about itself rather than be assumed
#: compatible.
SNAPSHOT_MANIFEST_KIND = "pf.lane_db.premigration_snapshot.v1"


class CanonGateError(RuntimeError):
    """The gate could not be run at all (bad expected-sha file, missing
    database, unreadable migrations directory).

    Deliberately NOT an outcome: "I could not look" is not "I looked and it was
    fine", and it is not "I looked and it was wrong" either.
    """


@dataclass(frozen=True)
class CanonVerdict:
    outcome: str
    reason: str
    expected_sha: str | None = None
    observed_sha: str | None = None
    #: Set only for EXPLAINED_BY_MIGRATION -- the value the caller should write
    #: into CANON_SHA.txt.  It is always the sha this run measured, never a
    #: value computed ahead of time (the reason the mechanism, not the number,
    #: travels in the migration PR -- `LANE-DB REPLY 20260901_1332`).
    new_canon_sha: str | None = None
    evidence: dict = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        return EXIT_CODE[self.outcome]

    def as_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "reason": self.reason,
            "expected_sha": self.expected_sha,
            "observed_sha": self.observed_sha,
            "new_canon_sha": self.new_canon_sha,
            "exit_code": self.exit_code,
            "evidence": self.evidence,
        }


def normalise_sha(value: str) -> str:
    """A sha256 in the one form this module compares.

    ``CANON_SHA.txt`` holds upper-case hex; ``hashlib`` produces lower-case.
    Comparing the two as written would make every single run report a change,
    so normalisation happens in one function and both sides go through it.
    """
    text = "".join(str(value).split()).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise CanonGateError("not a sha256 hex digest: %r" % (value,))
    return text


#: Byte-order marks, longest first, mapped to the encoding they announce.
#: pf-adversary (round `gfkvro`, defect 6) measured what Windows PowerShell 5.1
#: actually writes when a caller rotates this file the way the design says to:
#: ``>`` redirection and ``Out-File`` both produce UTF-16LE, and a UTF-16 file
#: read as UTF-8 raises ``UnicodeDecodeError`` -- a ``ValueError``, which the
#: OSError handler below never caught, so the FIRST successful rotation would
#: have bricked the gate with a traceback and exit 1.  Decoding by BOM costs
#: four lines and removes that entirely.
_BOMS = (
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xfe\xff", "utf-16-be"),
    (b"\xff\xfe", "utf-16-le"),
)


def _decode_sha_file(blob: bytes, where: Path) -> str:
    """Text out of a file some other tool wrote, or a named refusal.

    A BOM decides; with no BOM, UTF-8 is tried and then UTF-16LE, because a
    BOM-less UTF-16LE file (``Set-Content -Encoding Unicode`` on some hosts)
    decodes as UTF-8 into NUL-separated characters rather than failing, and
    those would reach ``normalise_sha`` as an unhelpful "not a sha256".
    """
    for bom, encoding in _BOMS:
        if blob.startswith(bom):
            try:
                # The BOM itself decodes to U+FEFF; it is a marker, not part
                # of the digest, and leaving it in would reach normalise_sha
                # as an unhelpful "not a sha256".
                return blob.decode(encoding).lstrip("\ufeff")
            except UnicodeDecodeError as error:
                raise CanonGateError(
                    "the expected-sha file %s starts with a %s byte-order mark "
                    "but does not decode as %s: %r" % (where, encoding, encoding, error)
                ) from error
    for encoding in ("utf-8", "utf-16-le"):
        try:
            text = blob.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" not in text:
            return text
    raise CanonGateError(
        "the expected-sha file %s is not text this gate can read (tried the "
        "byte-order marks, UTF-8 and UTF-16LE)" % where
    )


def read_expected_sha(path: str | Path) -> str:
    """The recorded canonical sha, from ``CANON_SHA.txt`` or an equivalent."""
    file = Path(path)
    try:
        blob = file.read_bytes()
    except OSError as error:
        raise CanonGateError(
            "cannot read the expected-sha file %s: %r" % (file, error)
        ) from error
    raw = _decode_sha_file(blob, file)
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(lines) != 1:
        # A file with two digests in it has no single answer, and picking the
        # first would silently prefer whichever line an editor happened to
        # leave on top.
        raise CanonGateError(
            "the expected-sha file %s must hold exactly one digest, found %d "
            "non-empty line(s)" % (file, len(lines))
        )
    return normalise_sha(lines[0])


def database_sha256(db_path: str | Path) -> str:
    """Hash the main database file, opening nothing."""
    file = Path(db_path)
    if not file.is_file():
        raise CanonGateError("no database file to hash at %s" % file)
    try:
        return _sha256_file(file)
    except OSError as error:
        raise CanonGateError("cannot hash %s: %r" % (file, error)) from error


def repo_migration_checksums(migrations_dir: str | Path) -> dict[int, str]:
    """``{version: sha256 of the file}`` for the migrations in the repo.

    Same glob and same "first three characters are the version" rule as
    ``SQLiteStore.migrate`` and ``persistence_backup.migration_versions``; a
    divergence would make this gate judge a different set of files from the one
    the runner applies.
    """
    directory = Path(migrations_dir)
    if not directory.is_dir():
        raise CanonGateError("no migrations directory at %s" % directory)
    checksums: dict[int, str] = {}
    for path in sorted(directory.glob(MIGRATION_GLOB)):
        version = int(path.name[:3])
        if version in checksums:
            raise CanonGateError("duplicate migration version %03d" % version)
        try:
            checksums[version] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise CanonGateError(
                "cannot read migration %s: %r" % (path.name, error)
            ) from error
    if not checksums:
        raise CanonGateError("no migration files under %s" % directory)
    return checksums


def read_ledger(db_path: str | Path) -> dict[int, str | None] | None:
    """``{version: checksum}`` from the live ledger, or ``None`` when it cannot
    be read.

    ``None`` is never an "empty ledger": the caller must treat it as "no
    evidence", the same fail-safe direction ``persistence_backup`` takes.
    Opened strictly read-only -- probing the owner's database must never be
    able to create it, lock it for writing or upgrade its journal mode.
    """
    path = Path(db_path)
    if not path.is_file():
        return None
    try:
        db = _read_only_connection(path)
    except sqlite3.Error:
        return None
    try:
        rows = db.execute("SELECT version,checksum FROM schema_migrations").fetchall()
    except sqlite3.Error:
        return None
    finally:
        db.close()
    ledger: dict[int, str | None] = {}
    for row in rows:
        try:
            version = int(row[0])
        except (TypeError, ValueError):
            return None
        checksum = row[1]
        ledger[version] = None if checksum is None else str(checksum)
    return ledger


def integrity_check(db_path: str | Path) -> str:
    """SQLite's own verdict on the live database, or a reason it could not be
    asked.

    Unlike ``persistence_backup._verify_snapshot`` this NEVER unlinks the
    ``-wal``/``-shm`` beside the file it opened.  That function may do so
    because it is looking at a copy that is supposed to be self-contained;
    doing it here would delete committed transactions out of the owner's live
    database to answer a read-only question.
    """
    path = Path(db_path)
    try:
        db = _read_only_connection(path)
    except sqlite3.Error as error:
        return "cannot open: %r" % (error,)
    try:
        return str(db.execute("PRAGMA integrity_check").fetchone()[0])
    except (sqlite3.Error, IndexError, TypeError) as error:
        return "cannot check: %r" % (error,)
    finally:
        db.close()


def ledger_agrees_with_repo(
    ledger: dict[int, str | None] | None, repo: dict[int, str]
) -> tuple[bool, str, dict]:
    """Does the live ledger describe exactly the migrations in this repo?

    Three ways to fail, and they are reported apart because they mean different
    things to a human reading the gate output:

    * a version applied that this repo has never heard of => the database is
      newer than the server, the same refusal ``SQLiteStore.migrate`` raises;
    * a version in the repo that the database has not applied => the boot did
      not finish, so whatever changed the file was not a completed migration
      run;
    * a checksum mismatch => the FILE for an applied version has been edited
      since it was applied, which the lane charter forbids outright.
    """
    if ledger is None:
        return False, "the ledger of the live database could not be read", {}
    unknown = sorted(set(ledger) - set(repo))
    missing = sorted(set(repo) - set(ledger))
    mismatched = sorted(
        version
        for version, checksum in ledger.items()
        if version in repo and checksum != repo[version]
    )
    detail = {
        "ledger_versions": sorted(ledger),
        "repo_versions": sorted(repo),
        "unknown_to_repo": unknown,
        "not_applied": missing,
        "checksum_mismatch": mismatched,
    }
    if unknown:
        return False, (
            "the database records migration(s) %s that do not exist in this "
            "repo: it is newer than this server" % unknown
        ), detail
    if missing:
        return False, (
            "migration(s) %s in the repo are not recorded as applied: no "
            "completed migration run explains this database" % missing
        ), detail
    if mismatched:
        return False, (
            "migration file(s) %s were edited after being applied (ledger "
            "checksum differs from the file on disk)" % mismatched
        ), detail
    return True, "the ledger matches the repo migrations exactly", detail


def _safe_text(value, limit: int = 120) -> str:
    """Text that came off disk, rendered so it cannot forge a line of output.

    pf-adversary (round `gfkvro`, defect 8) measured the injection: a snapshot
    DIRECTORY NAME containing a newline and ``NEW_CANON_SHA=<attacker value>``
    was interpolated into the human report, ahead of the real token line, and a
    caller taking the first match would have written the attacker's value into
    ``CANON_SHA.txt``.  Defect 9 measured the other half: one character with no
    code page 874 mapping in such a name kills ``print()`` on the bridge
    console AFTER the verdict was computed, turning a decided UNEXPLAINED into
    exit 1.  Both are closed here rather than at each call site: everything
    that came from the filesystem goes through this function, and what comes
    out is single-line, bounded and pure ASCII.
    """
    text = repr(value) if not isinstance(value, str) else value
    text = text.encode("ascii", "backslashreplace").decode("ascii")
    text = "".join(
        ch if ch.isprintable() else "\\x%02x" % ord(ch) for ch in text
    )
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _load_manifest(directory: Path, name: str = "MANIFEST.json") -> dict | None:
    path = directory / name
    try:
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _snapshot_still_readable(candidate: Path, manifest: dict) -> tuple[bool, str]:
    """Re-prove an existing snapshot WITHOUT touching one byte of the backups
    tree.

    This replaces a call to ``persistence_backup._snapshot_is_still_good``.
    pf-adversary (round `gfkvro`, defect 3) measured what that call did from
    here: it reaches ``_verify_snapshot``, which unconditionally ``unlink()``s
    the ``-wal`` and ``-shm`` beside the file it verified -- correct for the
    module that MAKES a self-contained copy, forbidden for a gate that only
    reads (``persistence_backup`` rule 3: nothing is ever deleted or pruned).
    Two files disappeared from ``db_backups/`` on every gate run, one of them
    exactly what the manifest's own ``restore_hint`` tells an operator to park
    beside the snapshot during a restore.  It also raced: two gate runs
    unlinking the same sidecar flipped the loser's verdict from EXPLAINED to
    UNEXPLAINED for no reason in the data.

    It also hashed the candidate twice per run (defect 13, measured at 3x the
    database size in reads).  Here it is hashed once, and the snapshot is
    opened ``immutable=1`` so SQLite creates no index file beside it either.
    """
    recorded = manifest.get("verification")
    if not isinstance(recorded, dict):
        return False, "the manifest carries no verification block"
    try:
        if candidate.stat().st_size != recorded.get("bytes"):
            return False, "the snapshot is no longer the size its manifest records"
        if _sha256_file(candidate) != recorded.get("sha256"):
            return False, "the snapshot no longer hashes to what its manifest records"
    except OSError as error:
        return False, "the snapshot cannot be read: %s" % _safe_text(repr(error))
    try:
        db = immutable_connection(candidate)
    except sqlite3.Error as error:
        return False, "the snapshot cannot be opened: %s" % _safe_text(repr(error))
    try:
        integrity = str(db.execute("PRAGMA integrity_check").fetchone()[0])
    except (sqlite3.Error, IndexError, TypeError) as error:
        return False, "the snapshot cannot be integrity-checked: %s" % _safe_text(
            repr(error)
        )
    finally:
        db.close()
    if integrity.lower() != "ok":
        return False, "the snapshot fails integrity_check: %s" % _safe_text(integrity)
    return True, "ok"


def read_post_migration_state(directory: Path, sha256: str) -> dict | None:
    """The note saying a migration in this snapshot's directory produced
    ``sha256``, or ``None``.

    See ``persistence_backup.record_post_migration_state`` for why it exists:
    a snapshot records the state going INTO a migration, and pre-state evidence
    alone blesses every later content of the file forever (pf-adversary, round
    `gfkvro`, first pass, D2 -- measured, including a run where every account
    row had been deleted and the gate still answered "explained, rotate").

    Looked up BY NAME rather than found by scanning: the file is called
    ``POSTSTATE.<sha>.json``, so one snapshot directory that several boots
    reused carries one note per outcome and this lookup cannot pick up a
    previous run's (second pass, R4).
    """
    payload = _load_manifest(directory, poststate_filename(sha256))
    if payload is None or payload.get("kind") != POSTSTATE_KIND:
        return None
    return payload


def find_premigration_evidence(
    db_path: str | Path,
    expected_sha: str,
    observed_sha: str,
    backups_root: str | Path | None = None,
    live_ledger: set[int] | None = None,
) -> tuple[Path | None, dict | None, str, dict]:
    """The snapshot that records this exact database coming OUT of a migration
    that went IN at the expected sha, or ``None`` plus why nothing qualifies.

    A qualifying snapshot has ALL of:

    1. a finished directory (not ``.INCOMPLETE``) with a manifest of the one
       kind this gate knows;
    2. ``source_fingerprint.path`` resolving to the database being judged;
    3. ``source_fingerprint.sha256`` equal to the EXPECTED sha -- the file that
       was copied was the canonical one;
    4. ``pending_versions`` a non-empty list of ints -- a snapshot taken
       because a ledger could not be read, or because a journal mode was about
       to be rewritten, is not evidence that a migration ran;
    5. a ``POSTSTATE.json`` whose ``post_migration_sha256`` equals the OBSERVED
       sha -- the database in front of us is the one that migration produced,
       and nothing has touched it since;
    6. the snapshot's own ``schema_migrations`` NOT containing the versions it
       says were pending -- a copy taken before a migration cannot already
       contain it;
    7. the snapshot database still on disk, still hashing to its manifest and
       still opening clean.

    !! WHAT THIS STILL CANNOT DO, stated where it is implemented and not only
    in the module header: conditions 1-5 and 7 are all files under
    ``backups_root``.  Anyone who can WRITE there can write all of them, and
    the one number such a forgery needs -- the canonical sha -- is published in
    ``pf_bridge/CANON_SHA.txt``.  pf-adversary demonstrated exactly that
    forgery against the pre-state-only version of this function (round
    `gfkvro`, defect 1): a hand-edited database plus a six-line hand-written
    manifest came out EXPLAINED.  Conditions 5 and 6 make that much harder -- the
    forger must now also produce a database that genuinely lacks the migration
    and keep three shas consistent -- but they do not make it impossible, and
    no arrangement of files inside a directory the attacker controls ever
    could.  THIS GATE SEPARATES HONEST DRIFT FROM A RECORDED MIGRATION.  It is
    not an authentication boundary and must not be quoted as one.
    """
    live = _resolved_or_none(db_path)
    if live is None:
        return None, None, "the database path cannot be resolved", {}
    live_ledger = set() if live_ledger is None else set(live_ledger)
    root = Path(backups_root) if backups_root is not None else default_backups_root(live)
    looked_at: list[str] = []
    rejected: list[dict] = []
    if not root.is_dir():
        return None, None, (
            "no snapshot directory at %s, so nothing records this database "
            "entering a migration" % _safe_text(str(root))
        ), {"backups_root": _safe_text(str(root)), "directories_examined": []}

    try:
        directories = sorted(root.iterdir(), reverse=True)
    except OSError as error:
        # An unreadable backups directory is "no evidence", never a crash: a
        # gate that dies with exit 1 is read as "not 13" by every ps1 caller
        # in the bridge (pf-adversary, round `gfkvro`, defect 7).
        return None, None, (
            "the snapshot directory %s cannot be listed: %s"
            % (_safe_text(str(root)), _safe_text(repr(error)))
        ), {"backups_root": _safe_text(str(root)), "directories_examined": []}

    for directory in directories:
        try:
            if not directory.is_dir() or directory.name.endswith(INCOMPLETE_SUFFIX):
                continue
        except OSError:
            continue
        looked_at.append(_safe_text(directory.name))
        # The manifest comes back FROM the check, never read a second time.
        # pf-adversary (round `gfkvro`, second pass, R6) measured the seam: the
        # second read sat outside every handler, so a manifest that became
        # unreadable between the two turned a decided verdict into a TypeError
        # out of `classify` -- and none of the safe-name and int-list checks
        # applied to the first read applied to the values actually used.
        reason, manifest = _why_not_evidence(
            directory, live, expected_sha, observed_sha, live_ledger
        )
        if reason is not None or manifest is None:
            rejected.append({
                "snapshot": _safe_text(directory.name),
                "why": reason or "the manifest could not be re-read",
            })
            continue
        candidate = directory / str(manifest["snapshot_database"])
        pending = sorted(int(v) for v in manifest["pending_versions"])
        return candidate, manifest, (
            "snapshot %s copied this database at sha %s with %s, and its %s "
            "records a boot producing exactly the database being judged"
            % (
                _safe_text(directory.name),
                expected_sha,
                ("migration(s) %s pending" % pending) if pending
                else ("an in-place rewrite pending (%s)"
                      % reason_code_for(manifest.get("reason", ""))),
                poststate_filename(observed_sha),
            )
        ), {
            "backups_root": _safe_text(str(root)),
            "directories_examined": looked_at,
            "rejected": rejected,
            "accepted": _safe_text(directory.name),
        }

    return None, None, (
        "no snapshot under %s records this database being copied at the expected "
        "sha with a migration pending AND coming back out at the sha it has now "
        "(%d finished snapshot directory/ies examined)"
        % (_safe_text(str(root)), len(looked_at))
    ), {
        "backups_root": _safe_text(str(root)),
        "directories_examined": looked_at,
        "rejected": rejected,
    }


def _why_not_evidence(
    directory: Path, live: Path, expected_sha: str, observed_sha: str,
    live_ledger: set[int],
) -> tuple[str | None, dict | None]:
    """``(None, manifest)`` when this directory qualifies, else
    ``(reason, None)``.

    The manifest travels OUT of this function so that the caller acts on the
    same object that was validated here (pf-adversary, round `gfkvro`, second
    pass, R6).

    One function, so that every rejection reason is reachable from a test and
    no branch can be added without a name a human can read in the output.
    Every filesystem error inside becomes a rejection, never an exception:
    the files here are attacker-shaped input, and a crash is worse than a
    refusal (first pass, D7 -- a NUL byte in a manifest's path turned a
    verdict of 13 into exit 1, which every ps1 guard in the bridge reads as
    "not 13").
    """
    def no(reason: str) -> tuple[str, None]:
        return reason, None

    try:
        manifest = _load_manifest(directory)
        if manifest is None:
            return no("no readable manifest")
        if manifest.get("kind") != SNAPSHOT_MANIFEST_KIND:
            return no("manifest kind %s is not %r" % (
                _safe_text(manifest.get("kind")), SNAPSHOT_MANIFEST_KIND
            ))
        fingerprint = manifest.get("source_fingerprint")
        if not isinstance(fingerprint, dict):
            return no("no source fingerprint")
        if _resolved_or_none(fingerprint.get("path")) != live:
            return no(
                "it is a snapshot of %s, not of the database being judged"
                % _safe_text(fingerprint.get("path"))
            )
        try:
            recorded_sha = normalise_sha(str(fingerprint.get("sha256")))
        except CanonGateError:
            return no("unusable source sha")
        if recorded_sha != expected_sha:
            return no(
                "it copied a database hashing to %s, not the expected %s"
                % (recorded_sha, expected_sha)
            )

        pending = manifest.get("pending_versions")
        if not isinstance(pending, list) or not all(
            isinstance(v, int) and not isinstance(v, bool) for v in pending
        ):
            return no(
                "it records pending_versions=%s, which is not a list of versions"
                % _safe_text(pending)
            )
        code = reason_code_for(manifest.get("reason", ""))
        if not pending and code not in IN_PLACE_REWRITE_REASONS:
            return no(
                "it records no pending migration and its reason (%s) is not an "
                "in-place rewrite, so it is not evidence that a boot was about "
                "to change this database" % code
            )

        name = str(manifest.get("snapshot_database", ""))
        # The name comes off a file on disk and is never joined as given: a
        # manifest naming ``../../pirateforce.sqlite3`` must not be able to
        # offer the LIVE database as its own evidence.
        if not name or name != Path(name).name or name in (".", ".."):
            return no("unsafe snapshot name")
        candidate = directory / name
        if not candidate.is_file() or _resolved_or_none(candidate) == live:
            return no("the snapshot database is gone")

        note_name = poststate_filename(observed_sha)
        post = read_post_migration_state(directory, observed_sha)
        if post is None:
            return no(
                "it has no %s, so no boot recorded producing the database that "
                "is here now" % note_name
            )
        if _resolved_or_none(post.get("source_database")) != live:
            return no("its %s is about another database" % note_name)
        try:
            post_sha = normalise_sha(str(post.get("post_migration_sha256")))
        except CanonGateError:
            return no("its %s carries no usable sha" % note_name)
        if post_sha != observed_sha:
            # Only reachable if the note's CONTENT disagrees with its own
            # filename, i.e. somebody wrote it by hand.
            return no(
                "its %s records sha %s, which is not the %s its name claims"
                % (note_name, post_sha, observed_sha)
            )

        # Prove the copy is intact BEFORE reading anything out of it: a
        # truncated snapshot should be reported as a damaged backup, not as a
        # database with a strange ledger.
        good, why = _snapshot_still_readable(candidate, manifest)
        if not good:
            return no(why)

        inside = snapshot_ledger(candidate)
        if inside is None:
            return no("the snapshot's own ledger cannot be read")
        if not pending and inside != set(live_ledger):
            # An in-place rewrite applies no migration, so the copy taken
            # before it must carry exactly the versions the database carries
            # now.  Without this the relaxed rule above would accept a
            # hand-written manifest that simply omits pending_versions.
            return no(
                "it records an in-place rewrite, but its copy holds versions "
                "%s while the database holds %s"
                % (sorted(inside), sorted(live_ledger))
            )
        already = sorted(set(pending) & inside)
        if already:
            # A copy taken BEFORE a migration cannot already contain it.  This
            # is the one condition whose evidence is bytes inside the copied
            # database rather than a number in a JSON file its writer chose
            # (first pass, D1).
            return no(
                "it claims migration(s) %s were pending, but its own copy "
                "already contains %s: it is not a pre-migration copy"
                % (sorted(pending), already)
            )
    except (OSError, ValueError, TypeError) as error:
        return no("this snapshot could not be examined: %s" % _safe_text(repr(error)))
    return None, manifest


def _resolved_or_none(value) -> Path | None:
    """``Path(value).resolve()`` that answers ``None`` instead of raising.

    ``Path("a\x00b").resolve()`` raises ``ValueError``, which no ``except
    OSError`` catches, and a manifest on disk can contain exactly that.
    """
    try:
        return Path(str(value)).resolve()
    except (OSError, ValueError, TypeError):
        return None


def classify(
    db_path: str | Path,
    migrations_dir: str | Path,
    expected_sha: str,
    backups_root: str | Path | None = None,
) -> CanonVerdict:
    """The whole gate in one function, so that a test can reach every branch.

    Order matters and is deliberate: the database is HASHED FIRST, before this
    module opens anything at all, so the verdict is about the bytes that were
    on disk when the gate looked -- not about a file that a read-only probe of
    our own had already caused SQLite to touch a sidecar of.
    """
    expected = normalise_sha(expected_sha)
    observed = database_sha256(db_path)

    # !! BEFORE ANY COMPARISON.  A database with bytes in its write-ahead log
    # is not the file this gate just hashed, and neither verdict below means
    # anything about it (`persistence_backup.hot_wal_bytes` carries what
    # pf-adversary measured in both directions).  Refusing is the only honest
    # answer, and it is the fail-closed one: the caller's remedy is the first
    # step of the canonical upgrade job anyway -- stop the server, let SQLite
    # checkpoint, run the gate again.
    wal = hot_wal_bytes(db_path)
    if wal != 0:
        return CanonVerdict(
            outcome=UNEXPLAINED,
            reason=(
                "this database has %s in its write-ahead log, so its file and "
                "its contents are different things right now and no sha of the "
                "file means anything: stop whatever is writing it, let SQLite "
                "checkpoint, and run the gate again"
                % ("an unreadable -wal" if wal < 0 else "%d uncheckpointed bytes" % wal)
            ),
            expected_sha=expected,
            observed_sha=observed,
            evidence={"hot_wal_bytes": wal},
        )

    if observed == expected:
        return CanonVerdict(
            outcome=UNCHANGED,
            reason="the database hashes to the recorded canonical sha",
            expected_sha=expected,
            observed_sha=observed,
        )

    repo = repo_migration_checksums(migrations_dir)
    agrees, ledger_reason, ledger_detail = ledger_agrees_with_repo(
        read_ledger(db_path), repo
    )
    if not agrees:
        return CanonVerdict(
            outcome=UNEXPLAINED,
            reason="the sha changed and %s" % ledger_reason,
            expected_sha=expected,
            observed_sha=observed,
            evidence={"ledger": ledger_detail},
        )

    snapshot, manifest, snapshot_reason, snapshot_detail = find_premigration_evidence(
        db_path, expected, observed, backups_root,
        live_ledger=set(ledger_detail["ledger_versions"]),
    )
    if snapshot is None:
        return CanonVerdict(
            outcome=UNEXPLAINED,
            reason=(
                "the sha changed, the ledger is tidy, but %s. A tidy ledger on "
                "its own is not evidence: a database edited by hand has one "
                "too." % snapshot_reason
            ),
            expected_sha=expected,
            observed_sha=observed,
            evidence={"ledger": ledger_detail, "snapshots": snapshot_detail},
        )

    # The migrations that snapshot was taken for have to be recorded applied
    # now, or the run it protected never finished and something else moved the
    # file.
    pending_then = sorted(int(v) for v in manifest.get("pending_versions", []))
    unapplied = [v for v in pending_then if v not in ledger_detail["ledger_versions"]]
    if unapplied:
        return CanonVerdict(
            outcome=UNEXPLAINED,
            reason=(
                "the sha changed and a snapshot records migration(s) %s pending, "
                "but %s are still not recorded as applied: that migration run "
                "did not finish" % (pending_then, unapplied)
            ),
            expected_sha=expected,
            observed_sha=observed,
            evidence={"ledger": ledger_detail, "snapshots": snapshot_detail},
        )

    integrity = integrity_check(db_path)
    if integrity.lower() != "ok":
        return CanonVerdict(
            outcome=UNEXPLAINED,
            reason=(
                "the sha changed with a migration recorded, but the database "
                "does not pass integrity_check: %s" % integrity
            ),
            expected_sha=expected,
            observed_sha=observed,
            evidence={
                "ledger": ledger_detail,
                "snapshots": snapshot_detail,
                "integrity_check": integrity,
            },
        )

    return CanonVerdict(
        outcome=EXPLAINED_BY_MIGRATION,
        reason=(
            "the sha changed because this database went into a recorded "
            "migration run: %s; the ledger now matches the repo exactly and "
            "the database passes integrity_check" % snapshot_reason
        ),
        expected_sha=expected,
        observed_sha=observed,
        new_canon_sha=observed,
        evidence={
            "ledger": ledger_detail,
            "snapshots": snapshot_detail,
            "integrity_check": integrity,
            "snapshot_database": str(snapshot),
            "migrations_applied_since_canon": pending_then,
        },
    )


#: How many rejected snapshots the human report explains before pointing at
#: ``--json``.  Bounded so that a backups tree with hundreds of directories
#: cannot bury the verdict line at the top.
REPORTED_REJECTIONS = 5

#: The one machine-readable line of the human report.  A caller reads the
#: EXIT CODE for the verdict and this line only for the value to write.
NEW_SHA_TOKEN = "NEW_SHA="


def _format_human(verdict: CanonVerdict) -> str:
    """The report, built so that no text off the filesystem can forge a line.

    Every prose line is indented by two spaces and every piece of text that
    came from disk has been through ``_safe_text`` (single line, ASCII,
    bounded), so the only line that can ever start at column 0 with
    ``NEW_SHA=`` is the one this function appends.  pf-adversary (round
    `gfkvro`, defect 8) measured the alternative: a snapshot directory named
    with an embedded newline put a second, attacker-chosen ``NEW_SHA=`` line
    AHEAD of the real one, and a caller taking the first match would have
    rotated ``CANON_SHA.txt`` to it.

    The token is also asserted to occur exactly once before the report is
    returned -- a belt-and-braces check that costs nothing and would have
    caught that defect on its own.
    """
    lines = [
        "CANON_GATE %s (exit %d)" % (verdict.outcome, verdict.exit_code),
        "  expected %s" % (verdict.expected_sha or "-"),
        "  observed %s" % (verdict.observed_sha or "-"),
        "  %s" % _safe_text(verdict.reason, limit=400),
    ]
    # The actual diagnosis, which used to be reachable only under --json.
    # pf-adversary (round `gfkvro`, second pass, R11) measured two real flows
    # where the single summary line above is misleading -- and one where it
    # accuses an operator of changing the database when a snapshot was merely
    # reused -- while `evidence["snapshots"]["rejected"]` said exactly what
    # happened.  A gate whose diagnosis a human cannot see is a gate they will
    # work around.
    rejected = (verdict.evidence.get("snapshots") or {}).get("rejected") or []
    for entry in rejected[:REPORTED_REJECTIONS]:
        if isinstance(entry, dict):
            lines.append(
                "  snapshot %s: %s"
                % (_safe_text(entry.get("snapshot")), _safe_text(entry.get("why"), 200))
            )
    if len(rejected) > REPORTED_REJECTIONS:
        lines.append(
            "  (%d more snapshot(s) examined; run with --json for all of them)"
            % (len(rejected) - REPORTED_REJECTIONS)
        )
    if verdict.new_canon_sha is not None:
        lines.append("%s%s" % (NEW_SHA_TOKEN, verdict.new_canon_sha.upper()))
    report = "\n".join(lines)
    appearances = sum(
        1 for line in report.splitlines() if line.startswith(NEW_SHA_TOKEN)
    )
    expected_appearances = 0 if verdict.new_canon_sha is None else 1
    if appearances != expected_appearances:
        # Unreachable by construction; if it ever fires, refusing to print is
        # the safe move, because the caller acts on this line.
        raise CanonGateError(
            "the report carries %d %s lines, expected %d"
            % (appearances, NEW_SHA_TOKEN, expected_appearances)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pirateforce_foundation.persistence_canon_gate",
        description=(
            "Second-layer canonical database gate. Exit 0 = UNCHANGED, "
            "%d = EXPLAINED_BY_MIGRATION (rotate CANON_SHA.txt to the printed "
            "%s value -- or, under --json, to the new_canon_sha field -- and "
            "write it as ASCII), 13 = UNEXPLAINED, %d = the gate did not run. "
            "ONLY 0 and %d mean the gate passed."
            % (
                EXIT_CODE[EXPLAINED_BY_MIGRATION], NEW_SHA_TOKEN, EXIT_USAGE,
                EXIT_CODE[EXPLAINED_BY_MIGRATION],
            )
        ),
    )
    parser.add_argument("--db", required=True, help="the database to judge")
    parser.add_argument(
        "--migrations", required=True, help="the repo's migrations/ directory"
    )
    expected = parser.add_mutually_exclusive_group(required=True)
    # `--expect-sha` is the spelling this lane promised chief in
    # `20260901_1515_LANE-DB-REQUEST-chief-staged-canon-gate-spec-and-
    # backuperror-wrapper.md`; `--expected-sha` is accepted as well so that a
    # caller written against either letter works.  Neither is preferred and
    # both are the same option.
    expected.add_argument(
        "--expect-sha", "--expected-sha", dest="expect_sha",
        help="the recorded canonical sha256",
    )
    expected.add_argument(
        "--expect-sha-file", "--expected-sha-file", dest="expect_sha_file",
        help="a file holding it, e.g. pf_bridge/CANON_SHA.txt",
    )
    parser.add_argument(
        "--backups-root",
        default=None,
        help="where pre-migration snapshots live (default: %s/ beside the database)"
        % DEFAULT_BACKUP_DIRNAME,
    )
    parser.add_argument(
        "--json", action="store_true", help="print the verdict as one JSON object"
    )
    return parser


def main(argv: list[str] | None = None, stdout=None, stderr=None) -> int:
    out = sys.stdout if stdout is None else stdout
    err = sys.stderr if stderr is None else stderr
    parser = build_parser()
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit:
        # EVERY argparse exit becomes EXIT_USAGE, including `--help`'s 0.
        # pf-adversary (round `gfkvro`, defect 10) named the false green: a
        # `--help` invocation checked nothing, and returning argparse's 0 made
        # it indistinguishable by exit code from a gate that checked and
        # passed.  A gate has no "pass" that did not look at a database.
        return EXIT_USAGE
    try:
        expected = (
            normalise_sha(args.expect_sha)
            if args.expect_sha is not None
            else read_expected_sha(args.expect_sha_file)
        )
        verdict = classify(args.db, args.migrations, expected, args.backups_root)
        report = (
            json.dumps(verdict.as_dict(), indent=2, sort_keys=True)
            if args.json
            else _format_human(verdict)
        )
    except CanonGateError as error:
        _write(err, "CANON_GATE COULD NOT RUN: %s" % _safe_text(str(error), 400))
        return EXIT_USAGE
    except Exception as error:  # noqa: BLE001 - a gate must not die undecided
        # Anything unforeseen is EXIT_USAGE, never a traceback and exit 1:
        # every canonical guard in `pf_bridge/staged/*.ps1` branches on 13, so
        # an uncaught crash used to read as "not 13" to all twelve of them
        # (pf-adversary, round `gfkvro`, defect 7 -- reached from a manifest
        # holding a NUL byte, and from an unreadable backups directory).
        _write(err, "CANON_GATE CRASHED: %s" % _safe_text(repr(error), 400))
        return EXIT_USAGE
    if not _write(out, report):
        # The verdict was decided; only the printing failed.  Returning the
        # verdict anyway is the point (pf-adversary, round `gfkvro`, defect 9:
        # an unencodable character in a path killed print() AFTER the work was
        # done, turning a decided UNEXPLAINED into exit 1 on the cp874 bridge
        # console).  `_write` already retried in ASCII; if even that failed the
        # exit code still carries the answer.
        pass
    return verdict.exit_code


def _write(stream, text: str) -> bool:
    """Print one block of text, surviving a console that cannot encode it.

    The bridge console is code page 874 (`persistence_backup`'s own header
    says so).  Everything this module composes is ASCII already; this is the
    last line of defence for a stream whose encoding is narrower still.
    """
    try:
        print(text, file=stream)
        return True
    except (UnicodeEncodeError, ValueError):
        try:
            print(text.encode("ascii", "backslashreplace").decode("ascii"),
                  file=stream)
            return True
        except Exception:  # noqa: BLE001 - nothing left to try
            return False


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
