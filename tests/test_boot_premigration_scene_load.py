"""COO-DECISION 20260905_0250: `app.py`'s only call site for the boot-time
`class_id` backfill sits after an if/else that does NOT call
`store.migrate_with_backup()` on every boot path -- a `--scene-load-scenario`
boot in particular.  On a database that predates migration 006 (no
`class_id` column yet) this used to raise `sqlite3.OperationalError: no such
column: class_id` and take the whole boot down (`KA1A-R314-RESULTS`,
`pf_bridge/notes_to_chief/20260905_0233_...boot-crash-class-id-backfill.md`).

`store.list_character_ids_missing_class_id`'s own `PRAGMA table_info`
guard (LANE-DB round qinqve) is exercised in isolation by
`tests/test_persistence_class_id_backfill.py`'s
`test_a_database_that_predates_migration_006_does_not_crash_the_boot` --
that test calls the backfill function directly, in-process, never through
`app.main()`.  COO's decision named a stronger bar than that: a real
`--scene-load-scenario` boot, against a real on-disk pre-006 database, must
come up LISTENING on a port -- not merely "the one function under test
didn't raise".  This is that test: a real `app.py` subprocess, a real
socket file, boots from an outside process the same way an attended round
does.
"""
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.store import SQLiteStore

MIGRATIONS = ROOT / "migrations"
SCENARIO = ROOT / "scenarios" / "scene2_load_only.json"
BOOT_TIMEOUT_SECONDS = 20


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _port_is_accepting(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        try:
            probe.connect((host, port))
        except OSError:
            return False
    return True


class BootWithPremigrationDatabaseTests(unittest.TestCase):
    def _make_premigration_database(self, db_path: Path) -> None:
        # A real migrate first (so every OTHER column/table this boot needs
        # exists), then drop only `class_id` back off -- the same
        # simulation `test_persistence_class_id_backfill.py`'s
        # `test_a_database_that_predates_migration_006_does_not_crash_the_
        # boot` uses, since this store has no "stop at migration N" entry
        # point to halt short of 006 with instead.
        store = SQLiteStore(str(db_path), MIGRATIONS)
        store.migrate_with_backup()
        with store.connect() as db:
            db.execute("ALTER TABLE characters DROP COLUMN class_id")

    def test_scene_load_scenario_boot_against_a_premigration_database_still_listens(
        self,
    ):
        self.assertTrue(
            SCENARIO.is_file(), f"fixture scenario missing: {SCENARIO}"
        )
        run_dir = Path(self.enterContext(
            __import__("tempfile").TemporaryDirectory()
        ))
        db_path = run_dir / "premigration.db"
        self._make_premigration_database(db_path)
        # `--capture-root` (app.py:942-947) chdir()s the child into this
        # directory before the listeners come up.  Without it, v141's own
        # relative-path writes (its default LOGIN_... capture directory) and
        # runtime_console.install_runtime_console's default log_root
        # (ROOT/logs/server_<stamp>) land inside the real repository working
        # tree -- a real regression an earlier version of this test caused:
        # the stray default capture directory it left behind satisfied
        # `pf_preconditions`'s "is the corpus present" check (directory
        # exists) for every OTHER test in the same `pytest tests/` run,
        # turning `test_capture_corpus.py`'s clean skip-on-a-fresh-clone
        # into nine false failures against a corpus that was never really
        # there.  (Deliberately not spelling that directory's literal name
        # in this comment: the Windows gate's own exclusion step greps
        # tests/*.py for it and would silently drop this whole module from
        # the gate -- AGENTS.md section 7's documented trap, the same one
        # this module exists to guard against.)
        capture_root = run_dir / "capture"
        game_port = _free_tcp_port()
        process = subprocess.Popen(
            [
                sys.executable, "-m", "src.pirateforce_foundation.app",
                "--db", str(db_path),
                "--scene-load-scenario", str(SCENARIO),
                "--game-port", str(game_port),
                "--capture-root", str(capture_root),
            ],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
        )
        try:
            deadline = time.monotonic() + BOOT_TIMEOUT_SECONDS
            listening = False
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                if _port_is_accepting("127.0.0.1", game_port):
                    listening = True
                    break
                time.sleep(0.1)

            if not listening:
                exit_code = process.poll()
                if exit_code is None:
                    process.terminate()
                    try:
                        output = process.communicate(timeout=5)[0]
                    except subprocess.TimeoutExpired:
                        process.kill()
                        output = process.communicate(timeout=5)[0]
                    self.fail(
                        "GAME listener on port %d never accepted a "
                        "connection within %ds; process was still running "
                        "(no crash, but never came up).  Output:\n%s"
                        % (game_port, BOOT_TIMEOUT_SECONDS, output[-4000:])
                    )
                output = process.communicate(timeout=5)[0]
                self.fail(
                    "boot crashed before the GAME listener ever came up "
                    "(exit code %r).  This is the exact regression "
                    "COO-DECISION 20260905_0250 named -- "
                    "app.py:802's class_id backfill running on a database "
                    "that never ran migration 006.  Output:\n%s"
                    % (exit_code, output[-4000:])
                )

            self.assertTrue(
                listening,
                "GAME listener must accept a connection -- this line "
                "should be unreachable given the loop above",
            )
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            process.stdout and process.stdout.close()


if __name__ == "__main__":
    unittest.main()
