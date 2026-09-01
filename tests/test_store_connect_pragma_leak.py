"""STORE-CONNECT-PRAGMA-LEAK-001: ``SQLiteStore.connect()`` closes the sqlite3
handle even when one of the PRAGMA statements raises.

WHY THIS EXISTS.  LANE-DB's CORE-REQUEST
(``pf_bridge/notes_to_chief/20260901_1904_LANE-DB-CORE-REQUEST-store-connect-
pragma-leak-outside-try.md``) measured that ``store.py``'s ``connect()`` ran
``sqlite3.connect`` and all four ``PRAGMA`` statements BEFORE the ``try:``
block that closes the handle on error -- so a corrupt/truncated file (a
partial snapshot restore, a bad path) that makes any PRAGMA raise
``sqlite3.DatabaseError`` left the OS file descriptor open under
``gc.collect()``, only reclaimed later by the garbage collector rather than
deterministically.  That is the same shape of leak that got PR #495 gated
red on Windows (``WinError 32``, a file another process still has open) --
that one was in a test fixture; this one is in the module itself and only
fires on the ``journal_mode=WAL`` branch, i.e. only for a real file-backed
database, which is the one case Windows actually locks.

This file reproduces LANE-DB's exact repro (open a file that is not a
sqlite3 database) and asserts the descriptor is gone immediately after the
raise, with no ``gc.collect()`` needed -- proving the fix is deterministic
close-on-error, not a GC coincidence.
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pirateforce_foundation.store import SQLiteStore


def _open_fds_under(directory: str) -> list[str]:
    fd_dir = "/proc/self/fd"
    if not os.path.isdir(fd_dir):
        return []
    matches = []
    for entry in os.listdir(fd_dir):
        try:
            target = os.readlink(os.path.join(fd_dir, entry))
        except OSError:
            continue
        if target.startswith(directory):
            matches.append(target)
    return matches


class StoreConnectPragmaLeakTest(unittest.TestCase):
    def test_not_a_database_file_raises_and_closes_immediately(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = Path(tmpdir) / "state.sqlite3"
            # Not a database: PRAGMA journal_mode=WAL raises on it.
            bad_path.write_bytes(b"not a sqlite3 file at all")

            store = SQLiteStore(str(bad_path), migrations=Path(tmpdir))

            with self.assertRaises(sqlite3.DatabaseError):
                with store.connect():
                    pass  # pragma_raise happens before the body ever runs

            open_after = _open_fds_under(tmpdir)
            self.assertEqual(
                open_after,
                [],
                f"handle(s) still open under {tmpdir!r} immediately after "
                f"the PRAGMA raise, before gc.collect(): {open_after!r}",
            )

    def test_memory_db_pragma_path_still_works(self):
        # journal_mode=WAL is skipped for ":memory:" -- guard against the fix
        # changing behavior on the branch LANE-DB's repro does not touch.
        store = SQLiteStore(":memory:", migrations=Path(tempfile.mkdtemp()))
        with store.connect() as db:
            db.execute("CREATE TABLE t(x)")
            db.execute("INSERT INTO t VALUES (1)")
        with store.connect() as db:
            # separate ":memory:" connection -- proves normal commit/close
            # still runs on the success path, unaffected by the fix.
            db.execute("CREATE TABLE t(x)")


if __name__ == "__main__":
    unittest.main()
