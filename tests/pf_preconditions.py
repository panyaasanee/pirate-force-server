"""One place that knows what this repository does NOT contain.

WHY THIS FILE EXISTS.  On 2026-08-20 the Windows gate ran on a second machine
for the first time in this project's history - GitHub Actions run #3, a fresh
clone on windows-latest - and the pytest step went red with four failures.  All
four were the same shape: a test reached for evidence that lives outside git
and can never be inside it (the canonical database, the read-only client image,
the untracked capture corpus, the machine-local ``backups/`` tree).  FINDINGS
R12 predicted exactly this on 2026-08-17 ("the gate passes because of THIS
MACHINE, not because of the repository"); run #3 is the first time anybody
measured it.  Panya's ruling, 2026-08-20 ~15:45:

    Fix it at the test, with skipUnless, not with an --ignore list on the CI
    side.  A test must know its own preconditions and must SAY that it skipped,
    on EVERY machine.  An --ignore list makes the test vanish silently on the
    runner while the suite still reports a number that looks the same.

    A skipped check is not a passed check.  Every skip must be counted, named
    and given a reason, and the count must be PINNED so that it goes red when
    it moves - in either direction.  Otherwise a real test drifts into the skip
    pile one day and nobody notices.

HOW TO USE IT.  Never write a bare ``skipUnless(path.exists(), "...")`` again.
Ask this module instead::

    from pf_preconditions import CANONICAL_DB, CLIENT_IMAGE

    @CANONICAL_DB.skip_unless_present()
    def test_something_that_needs_the_database(self):
        ...

The reason string that reaches pytest always starts with the machine-readable
token ``[precondition:<key>]``.  ``tools/pf_pytest_precondition_census.py``
parses those tokens out of ``pytest -rs`` output, groups them by key, and
compares each group against the pin in ``docs/PYTEST_SKIP_PINS.json``:

  * artifact PRESENT  -> that key must produce EXACTLY ZERO skips;
  * artifact ABSENT   -> that key must produce exactly its pinned count.

Both directions are red, so neither "a test quietly joined the skip pile" nor
"a guarded test quietly disappeared" can happen without the gate saying so.

A skip that carries no ``[precondition:...]`` token is NOT an error - some
skips are design decisions, not missing evidence - but the census lists them
separately by name and pins their count too, so they cannot multiply in the
dark either.

WHAT THIS MODULE IS NOT.  It is not a way to make a test weaker.  On a machine
that HAS the artifact every guard here is a no-op and every assertion runs at
full strength.  Nothing in this file may ever be used to relax an assertion.

This module is pure standard library and imports nothing from ``src`` or
``tools``; it opens no file at import time beyond ``Path.exists`` probes.
ASCII only, on purpose: the bridge console is code page 874.
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The install tree the repository is cloned beside on the bridge.  Everything
# under it is proprietary and is never committed.
SIBLING = ROOT.parent


class Precondition:
    """A named piece of evidence that a fresh clone does not have.

    ``paths`` is every filesystem path that must exist for the guarded tests to
    be able to run.  ``present`` is recomputed on every access, never cached at
    import time, so a test that creates its own fixture is not fooled by an
    answer from module-load time.
    """

    __slots__ = ("key", "paths", "what", "why")

    def __init__(self, key: str, paths, what: str, why: str) -> None:
        if not key or any(ch.isspace() for ch in key):
            raise ValueError("precondition key must be a single word: %r" % key)
        self.key = key
        self.paths = tuple(Path(p) for p in paths)
        if not self.paths:
            raise ValueError("precondition %r names no path" % key)
        self.what = what
        self.why = why

    @property
    def present(self) -> bool:
        return all(p.exists() for p in self.paths)

    @property
    def missing(self):
        return tuple(p for p in self.paths if not p.exists())

    @property
    def reason(self) -> str:
        """The exact string a skipped test reports.

        The ``[precondition:<key>]`` prefix is load-bearing: the census tool
        keys off it.  Do not reformat it.  The missing filenames are named at
        the end so a partially-present clone (e.g. a bridge with five of the
        eight external tables) says WHICH files it lacks instead of an
        undifferentiated "not in a fresh clone" (R145 adversary, defect 8).
        """
        missing = self.missing
        tail = ""
        if missing and len(missing) != len(self.paths):
            tail = " [missing %d/%d: %s]" % (
                len(missing), len(self.paths),
                ", ".join(p.name for p in missing),
            )
        return "[precondition:%s] %s is not in a fresh clone - %s%s" % (
            self.key, self.what, self.why, tail,
        )

    def skip_unless_present(self):
        """Decorator for a test method or a TestCase class."""
        return unittest.skipUnless(self.present, self.reason)

    def require(self, case: unittest.TestCase) -> None:
        """Imperative form, for a precondition only known inside the test."""
        if not self.present:
            case.skipTest(self.reason)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<Precondition %s present=%s>" % (self.key, self.present)


class HistoricalGitObject:
    """A named piece of git HISTORY, and a verdict on WHY this clone lacks it.

    WHY THIS CLASS EXISTS, MEASURED 2026-08-21 (round 118).  Everything above
    asks ``Path.exists``, because everything above is a file that lives outside
    git.  This one is the opposite shape: the artifact is INSIDE git, and what a
    machine can be missing is not the file but the DEPTH OF HISTORY that holds
    it.  A cloud round clones shallow (``--depth 53`` produced 56 commits on
    2026-08-21, against a full history of 184), so
    ``git show 5c200e2:migrations/001_initial.sql`` exits 128 there and the one
    test that reads it died with a raw ``CalledProcessError``.  Read at face
    value that says the suite is RED ON MAIN, on a tree nobody has touched.  It
    is not: the same commit ran 1206 passed / 4 skipped the moment
    ``git fetch --unshallow`` finished.

    WHY IT IS A STATE MACHINE AND NOT A BOOLEAN.  The first draft asked one
    question - does ``git cat-file -e`` exit zero - and called every "no" a
    shallow clone.  An adversarial pass took that apart: with ``.git`` deleted
    the whole suite went GREEN, because the guarded tests skipped and the skip
    census asked this same object the same broken question and agreed with
    itself.  A guard whose oracle is also its own grader has no witness.  So
    ``state()`` separates the reasons, and only two of them may become a skip:

      * ``PRESENT``  - the objects are here.  The test runs at full strength.
      * ``SHALLOW``  - git works, this IS a repository, the repository says it
        is shallow, and the objects are outside the graft.  A declared skip.
      * ``PARTIAL``  - the same, for a blobless/treeless partial clone that
        cannot produce the object without its promisor remote.  A declared skip.
      * ``BROKEN``   - anything else: no git on the machine, not a work tree,
        git timed out, or the objects are missing from a clone that is NEITHER
        shallow NOR partial.  That last case means the revision is wrong or
        history was rewritten, and it is exactly what a typo in a SHA looks
        like.  **A BROKEN state never skips.**  ``require`` fails the test with
        the measured reason, so a wrong SHA cannot quietly disable a test on
        every machine and still be graded PASS.

    THIS IS NOT A WAY TO MAKE A TEST WEAKER.  The Windows gate checks out with
    ``fetch-depth: 0`` (verified at ``.github/workflows/gate-windows.yml``), and
    the bridge holds the whole history, so on both machines that decide anything
    the state is ``PRESENT`` and every assertion runs.  A skip can only appear on
    a clone that provably cannot produce the bytes.

    NAME THE OBJECTS THE CONSUMER ACTUALLY READS, not just their commit.  A
    partial clone has the commit and not the blob - measured, exit 0 for
    ``<sha>^{commit}`` and 128 for ``<sha>:<path>`` in the same clone - so a
    commit-only probe would report PRESENT and leave the test to die anyway.

    Nothing is cached: every property recomputes, so a run that unshallows its
    own clone is not answered from an earlier moment.  ``git`` is given a
    timeout, because a partial clone's probe can try to fetch from a promisor
    remote that is not there.

    There is deliberately no ``skip_unless_present()`` on this class.  A
    decorator is evaluated at IMPORT time, which would shell out to git before
    a single test ran, and would freeze the answer for the whole session.
    """

    PRESENT = "present"
    SHALLOW = "shallow"
    PARTIAL = "partial"
    BROKEN = "broken"
    SKIPPABLE = (SHALLOW, PARTIAL)

    __slots__ = ("key", "revisions", "what", "why", "root", "timeout")

    def __init__(self, key: str, revisions, what: str, why: str,
                 root=None, timeout: int = 60) -> None:
        if not key or any(ch.isspace() for ch in key):
            raise ValueError("precondition key must be a single word: %r" % key)
        self.key = key
        self.revisions = tuple(str(r) for r in revisions)
        if not self.revisions:
            raise ValueError("precondition %r names no revision" % key)
        if not all(self.revisions):
            raise ValueError("precondition %r names an empty revision" % key)
        self.what = what
        self.why = why
        self.root = Path(root) if root is not None else ROOT
        self.timeout = timeout

    # -- talking to git -----------------------------------------------------

    def _git(self, args):
        """``(returncode, stdout, unanswerable)``.

        ``unanswerable`` is None unless git ITSELF could not answer - it is not
        the same fact as "git answered no", and collapsing the two is the defect
        this class was rewritten to remove.
        """
        try:
            done = subprocess.run(
                ["git", "--no-optional-locks"] + list(args),
                cwd=str(self.root),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
            )
        except OSError as error:
            return None, "", "git is not runnable on this machine (%s)" % (error,)
        except subprocess.TimeoutExpired:
            return None, "", (
                "git did not answer within %d seconds - a partial clone "
                "probing an unreachable promisor remote looks like this"
                % self.timeout
            )
        return done.returncode, done.stdout.decode("utf-8", "replace"), None

    def _is_partial_clone(self) -> bool:
        code, out, unanswerable = self._git(
            ["config", "--get-regexp", r"^(extensions\.partialclone|remote\..*\.promisor)$"])
        if unanswerable is not None:
            return False
        return code == 0 and bool(out.strip())

    # -- the verdict --------------------------------------------------------

    def state(self):
        """``(state, detail)`` - measured now, never cached."""
        code, out, unanswerable = self._git(["rev-parse", "--is-shallow-repository"])
        if unanswerable is not None:
            return self.BROKEN, unanswerable
        if code != 0:
            return self.BROKEN, "%s is not a git work tree" % self.root
        shallow = out.strip() == "true"

        missing = []
        for revision in self.revisions:
            code, _out, unanswerable = self._git(["cat-file", "-e", revision])
            if unanswerable is not None:
                return self.BROKEN, unanswerable
            if code != 0:
                missing.append(revision)
        if not missing:
            return self.PRESENT, ""

        listed = ", ".join(missing)
        if shallow:
            return self.SHALLOW, (
                "this clone is shallow and its graft cuts off %s" % listed)
        if self._is_partial_clone():
            return self.PARTIAL, (
                "this is a partial clone and it cannot produce %s without its "
                "promisor remote" % listed)
        return self.BROKEN, (
            "this clone is complete - neither shallow nor partial - and still "
            "cannot produce %s, so the revision is wrong or history was "
            "rewritten.  This is what a typo in a pinned SHA looks like, and it "
            "must not become a skip" % listed)

    @property
    def present(self) -> bool:
        return self.state()[0] == self.PRESENT

    @property
    def missing(self):
        code, _out, unanswerable = self._git(["rev-parse", "--git-dir"])
        if unanswerable is not None or code != 0:
            return self.revisions
        found = []
        for revision in self.revisions:
            code, _out, unanswerable = self._git(["cat-file", "-e", revision])
            if unanswerable is not None or code != 0:
                found.append(revision)
        return tuple(found)

    @property
    def reason(self) -> str:
        """The generic form, and the one the census keys off.

        The ``[precondition:<key>]`` prefix is load-bearing.  ``require`` sends
        a longer version of this with the MEASURED cause appended; both carry
        the token, so the census counts them the same way.
        """
        return "[precondition:%s] %s is not in this clone - %s" % (
            self.key, self.what, self.why,
        )

    def skip_reason(self, detail: str) -> str:
        return "%s [measured: %s]" % (self.reason, detail)

    def require(self, case: unittest.TestCase) -> None:
        """Skip only for a cause that was measured; otherwise fail loudly."""
        state, detail = self.state()
        if state == self.PRESENT:
            return
        if state in self.SKIPPABLE:
            case.skipTest(self.skip_reason(detail))
        case.fail(
            "%s cannot be read here, and NOT because of clone depth: %s"
            % (self.what, detail))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<HistoricalGitObject %s state=%s>" % (self.key, self.state()[0])


# ---------------------------------------------------------------------------
# The registry.  Adding an entry here is a deliberate act: it also needs a pin
# in docs/PYTEST_SKIP_PINS.json, or the census goes red on an unknown key.
# ---------------------------------------------------------------------------

CANONICAL_DB = Precondition(
    "canonical_db",
    [ROOT / "state" / ("pirateforce" + ".sqlite3")],
    "the canonical database state/pirateforce.sqlite3",
    "it is the live server's own state, .gitignore keeps it out on purpose, "
    "and round 41 forbade the suite from writing to it at all",
)

CLIENT_IMAGE = Precondition(
    "client_image",
    [SIBLING / "GameClient" / "GameClient.local.bin"],
    "the read-only client image ../GameClient/GameClient.local.bin",
    "it is a 14.7 MB proprietary binary that must never be uploaded anywhere",
)

CAPTURE_V141 = Precondition(
    "capture_v141",
    [ROOT / "capture_v141"],
    "the v141 capture corpus capture_v141/",
    "the corpus is untracked working evidence, produced by running the real "
    "client against our server",
)

BACKUPS_TREE = Precondition(
    "backups_tree",
    [ROOT / "backups"],
    "the machine-local backups/ tree",
    "it holds pre-migration runtime snapshots that only exist on the bridge",
)

EVIDENCE_TREE = Precondition(
    "evidence_tree",
    [ROOT / "evidence"],
    "the machine-local evidence/ capture tree",
    "it holds the live-session capture transcripts (v74-v83) that "
    "tools/pf_structural_corpus_audit_config.json pins as sources; the "
    "allowlist .gitignore keeps the whole tree out on purpose",
)

# Kept in step with tools/pf_multiplayer_readiness_audit.LOGIN_REQ_CAPTURE by
# test_pytest_precondition_census.py, which compares the two strings and goes
# red if either side moves alone.
LOGIN_REQ_CAPTURE_RELPATH = (
    "analysis/lost_eden_leisure_runtime/capture_v110/"
    "LOGIN_20260814_152723_188831_59376.txt"
)

LOGIN_REQ_CAPTURE = Precondition(
    "login_req_capture",
    [ROOT / LOGIN_REQ_CAPTURE_RELPATH],
    "the LoginVitalReq capture " + LOGIN_REQ_CAPTURE_RELPATH,
    "it is one file in the untracked analysis/ corpus, and the audit tool "
    "already answers 'skipped (untracked capture absent)' without it",
)

BRIDGE_SIBLING = Precondition(
    "bridge_sibling",
    [SIBLING / "pf_bridge"],
    "the pf_bridge working directory beside this clone",
    "it is a separate repository holding the ledger, the flags and the "
    "evidence, and tools/pf_vital_name_thunk_static.py resolves it as "
    "ROOT.parent / 'pf_bridge'",
)

GAME_INSTALL_TREE = Precondition(
    "game_install_tree",
    [SIBLING / "GameClient"],
    "the game install tree ../GameClient/",
    "it is the shipped client's data directory, proprietary and never "
    "committed",
)

# The Codex RE deliverable tables, committed to pf_bridge main on 2026-08-23
# (Panya ruling 20:39 +07:00).  They are tracked files - but in the SIBLING
# repository, so a machine that clones only this repository (the Windows gate
# checks out exactly one repo) cannot have them.  The cloud clone and the
# bridge both hold pf_bridge beside this clone, so the guarded tests run at
# full strength on both machines that matter.
EXTERNAL_RE_TABLES = Precondition(
    "external_re_tables",
    [SIBLING / "pf_bridge" / "external" / name for name in (
        "PF_PROTOCOL_REGISTRY.tsv",
        "PF_SERIALIZER_FIELDS.tsv",
        "PF_RUNTIME_CLASSMAP.tsv",
        "PF_FIELD_VALIDATION.tsv",
        "PF_INPUT_INVENTORY.tsv",
        # The last three of the eight, on the remote since 2026-08-24
        # (pf_bridge 579b468).  They are listed here, not only in the tool's
        # PINS, because a clone that has five tables and not eight must skip
        # rather than half-run: the R145 cross-checks join across all three.
        "PF_PROTOCOL_PRIORITY.tsv",
        "PF_DATA_EVIDENCE.tsv",
        "PF_TAG_CENSUS.tsv",
    )],
    "the Codex RE deliverable tables ../pf_bridge/external/PF_*.tsv",
    "they live in the pf_bridge sibling repository, which the single-repo "
    "gate checkout does not have; tools/pf_external_registry.py is their "
    "only consumer and pins their sha256s",
)

# The pre-Foundation schema commit.  tests/test_foundation.py reads
# migrations/001_initial.sql out of it to prove that a database created by the
# original schema still upgrades, so the test cannot invent the bytes: they
# only exist in history.
ORIGINAL_SCHEMA_COMMIT = "5c200e2"

#: The exact object tests/test_foundation.py reads, named as the consumer names
#: it.  The commit alone would not do: a partial clone has the commit and not
#: the blob.
ORIGINAL_SCHEMA_BLOB = ORIGINAL_SCHEMA_COMMIT + ":migrations/001_initial.sql"

ORIGINAL_SCHEMA_HISTORY = HistoricalGitObject(
    "original_schema_history",
    [ORIGINAL_SCHEMA_COMMIT + "^{commit}", ORIGINAL_SCHEMA_BLOB],
    "the original schema at " + ORIGINAL_SCHEMA_BLOB,
    "it exists only in history, and a shallow clone is cut off from it - "
    "measured 2026-08-21, a cloud round's clone carried 56 of 184 commits and "
    "not that one; the Windows gate checks out with fetch-depth: 0 and the "
    "bridge holds the whole history, so this guard is a no-op on both machines "
    "that decide anything",
)

# The commit the multiplayer-readiness report was measured at.  Kept in step
# with tools/pf_multiplayer_readiness_audit.HEAD_COMMIT by
# test_pytest_precondition_census.py, exactly as LOGIN_REQ_CAPTURE_RELPATH is:
# neither side may move alone.  Separate key from the schema commit above ON
# PURPOSE, because a clone can hold one and not the other and a shared key
# would skip tests that could have run: measured 2026-08-21, a clone of the
# cloud round's own shape held 5cc0eda and not 5c200e2 (1 failure), while a
# depth-1 clone held neither (4 failures).
#
# THAT MEASUREMENT HAS A SHELF LIFE and the split does not depend on it.  Where
# the graft of a fixed --depth falls moves with every commit on main, so the
# day 5cc0eda drops out of a cloud clone too, these three tests skip for a
# measured reason instead of running - which is the designed behaviour, not a
# surprise.  Do not re-derive "how far apart" from this comment; ask git.
AUDIT_HEAD_COMMIT = "5cc0eda"

#: The tool reads the tests/ tree AND every tests/*.py blob at that commit
#: (ls-tree plus a batched cat-file).  One representative blob is named here so
#: that a partial clone, which has the commit and not the blobs, is classified
#: as PARTIAL rather than reported PRESENT and left to fail.
AUDIT_HEAD_SAMPLE_BLOB = AUDIT_HEAD_COMMIT + ":tests/test_foundation.py"

AUDIT_HEAD_HISTORY = HistoricalGitObject(
    "audit_head_history",
    [AUDIT_HEAD_COMMIT + "^{commit}", AUDIT_HEAD_SAMPLE_BLOB],
    "the suite as it stood at " + AUDIT_HEAD_COMMIT
    + ", which tools/pf_multiplayer_readiness_audit.py re-derives its published "
    "size from",
    "the tool answers HistoryUnavailable without it and then fails its own "
    "historical pin, which is the right answer for the tool and the wrong one "
    "for a test that never got to run; the gate and the bridge both hold the "
    "commit, so the re-derivation happens there for real",
)

REGISTRY = {
    p.key: p
    for p in (
        CANONICAL_DB,
        CLIENT_IMAGE,
        CAPTURE_V141,
        BACKUPS_TREE,
        EVIDENCE_TREE,
        LOGIN_REQ_CAPTURE,
        BRIDGE_SIBLING,
        GAME_INSTALL_TREE,
        EXTERNAL_RE_TABLES,
        ORIGINAL_SCHEMA_HISTORY,
        AUDIT_HEAD_HISTORY,
    )
}

TOKEN_PREFIX = "[precondition:"


def key_of(reason: str):
    """Return the precondition key inside a skip reason, or None.

    The census tool uses this, and so does its test, so the parser and the
    producer can never drift apart.
    """
    at = reason.find(TOKEN_PREFIX)
    if at < 0:
        return None
    end = reason.find("]", at)
    if end < 0:
        return None
    return reason[at + len(TOKEN_PREFIX):end]
