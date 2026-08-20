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
        keys off it.  Do not reformat it.
        """
        return "[precondition:%s] %s is not in a fresh clone - %s" % (
            self.key, self.what, self.why,
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

REGISTRY = {
    p.key: p
    for p in (
        CANONICAL_DB,
        CLIENT_IMAGE,
        CAPTURE_V141,
        BACKUPS_TREE,
        LOGIN_REQ_CAPTURE,
        BRIDGE_SIBLING,
        GAME_INSTALL_TREE,
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
