"""Watch the recovery half of session_lifecycle/abrupt_loss_recovery.

FND-009's primary claim is that a fresh server process "closed the stale open
lease before the new client login".  The entire server-side implementation of
that sentence is one call inside ``app.main()``.  Before this module no test
observed it: the only other mention of ``expire_open_sessions`` in the suite is
``test_session_row_persistence``, which calls the store method directly and so
proves the method works, not that starting a server uses it.

The distinction is not academic.  ``open_session`` already closes open rows for
the account that logs in, which masks the startup call whenever exactly one
account is involved -- every runtime pass so far.  It stops masking as soon as
the dead process held leases for more than one account: without the startup
call the other account's row stays open and its session id still authorises
``save_position``.  ``test_a_relogin_alone_would_leave_the_other_lease_open``
pins that masking so the recovery assertions cannot pass for free.

Nonclaim: no live process holds a stale session id after an abrupt loss, so the
open row is an invariant/oracle defect rather than a reachable write path today.
Concurrent multi-account runtime remains unproven (GT-003).
"""
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position
from pirateforce_foundation.store import SQLiteStore

APP_SOURCE = ROOT / "src" / "pirateforce_foundation" / "app.py"
SESSION_SOURCE = ROOT / "src" / "pirateforce_foundation" / "session.py"

SESSION_COLUMNS = (
    "id, account_id, lease_generation, selected_character_id, opened_at"
)


def start_one_server_process(db_path):
    """Run the real entry point through the one path that opens no listener."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [
            sys.executable, "-m", "pirateforce_foundation.app",
            "--db", str(db_path), "--self-test-only",
        ],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False,
    )


def build_wire(seed):
    """Deterministic opaque bytes; this module never claims wire semantics."""
    def build(selector):
        return (
            bytes([seed, selector]) + b"\x00" * 30,
            bytes([seed ^ 0xFF]) + b"\x11" * 15,
            0x10010001 + seed,
            0,
        )
    return build


def seed_two_accounts_lost_abruptly(store):
    """One dead process holding a selected lease for each of two accounts."""
    alpha = store.ensure_account("alpha")
    bravo = store.ensure_account("bravo")
    alpha_character = store.create_character(
        alpha, "Alpha01", "alpha01", "fp:alpha", build_wire(1),
        Position(1, 0, 11.5, -22.25, 186.0, 0.5),
    )
    bravo_character = store.create_character(
        bravo, "Bravo01", "bravo01", "fp:bravo", build_wire(2),
        Position(1, 0, 33.75, -44.5, 186.0, 1.25),
    )
    # One lease that already closed cleanly before the loss.
    closed_first = store.open_session(alpha)
    store.close_session(closed_first)
    alpha_lease = store.open_session(alpha)
    store.select_character(alpha_lease, alpha_character.selector)
    store.save_position(
        alpha_lease, alpha_character.id, Position(1, 0, 99.5, -88.25, 186.0, 2.0),
    )
    bravo_lease = store.open_session(bravo)
    store.select_character(bravo_lease, bravo_character.selector)
    return {
        "alpha": alpha,
        "bravo": bravo,
        "alpha_character": alpha_character,
        "bravo_character": bravo_character,
        "closed_first": closed_first,
        "alpha_lease": alpha_lease,
        "bravo_lease": bravo_lease,
    }


def rows(store, sql):
    with store.connect() as db:
        return [tuple(row) for row in db.execute(sql)]


def open_lease_ids(store):
    return {
        row[0] for row in rows(
            store, "SELECT id FROM sessions WHERE closed_at IS NULL",
        )
    }


def closed_at(store, session_id):
    with store.connect() as db:
        row = db.execute(
            "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
        ).fetchone()
    return None if row is None else row[0]


class StaleLeaseRecoveryThroughTheEntryPointTests(unittest.TestCase):
    """One abrupt loss, one real server start, then read the durable state."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "abrupt.sqlite3"
        cls.store = SQLiteStore(cls.db_path, ROOT / "migrations")
        cls.store.migrate()
        cls.seeded = seed_two_accounts_lost_abruptly(cls.store)
        cls.before_sessions = rows(
            cls.store, f"SELECT {SESSION_COLUMNS} FROM sessions ORDER BY id",
        )
        cls.before_characters = rows(
            cls.store, "SELECT * FROM characters ORDER BY id",
        )
        cls.before_positions = rows(
            cls.store, "SELECT * FROM character_positions ORDER BY character_id",
        )
        cls.before_closed_stamp = closed_at(cls.store, cls.seeded["closed_first"])
        cls.result = start_one_server_process(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_replacement_process_started_and_opened_no_listener(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)

    def test_one_start_closes_every_lease_the_dead_process_left_open(self):
        self.assertEqual(open_lease_ids(self.store), set())

    def test_one_start_closes_the_lease_of_an_account_that_never_returns(self):
        # Only this account exposes the startup call.  The account that logs
        # back in would have had its row closed by open_session regardless.
        self.assertIsNotNone(closed_at(self.store, self.seeded["bravo_lease"]))

    def test_a_relogin_alone_would_leave_the_other_lease_open(self):
        """Guard against the recovery assertions passing for the wrong reason."""
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "masked.sqlite3", ROOT / "migrations")
            store.migrate()
            seeded = seed_two_accounts_lost_abruptly(store)
            store.open_session(seeded["alpha"])
            self.assertIsNotNone(closed_at(store, seeded["alpha_lease"]))
            self.assertIsNone(closed_at(store, seeded["bravo_lease"]))

    def test_a_stale_lease_can_no_longer_write_a_position(self):
        with self.assertRaises(PermissionError):
            self.store.save_position(
                self.seeded["alpha_lease"],
                self.seeded["alpha_character"].id,
                Position(1, 0, 1.0, 2.0, 3.0, 0.0),
            )

    def test_a_stale_lease_can_no_longer_select_a_character(self):
        with self.assertRaises(KeyError):
            self.store.select_character(
                self.seeded["bravo_lease"],
                self.seeded["bravo_character"].selector,
            )

    def test_the_start_closes_leases_without_deleting_or_renumbering_history(self):
        after = rows(
            self.store, f"SELECT {SESSION_COLUMNS} FROM sessions ORDER BY id",
        )
        self.assertEqual(after, self.before_sessions)

    def test_the_start_leaves_an_already_closed_stamp_byte_identical(self):
        self.assertIsNotNone(self.before_closed_stamp)
        self.assertEqual(
            closed_at(self.store, self.seeded["closed_first"]),
            self.before_closed_stamp,
        )

    def test_the_start_leaves_every_character_row_and_position_untouched(self):
        self.assertEqual(
            rows(self.store, "SELECT * FROM characters ORDER BY id"),
            self.before_characters,
        )
        self.assertEqual(
            rows(
                self.store,
                "SELECT * FROM character_positions ORDER BY character_id",
            ),
            self.before_positions,
        )

    def test_the_recovered_database_is_usable_by_the_next_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "usable.sqlite3"
            store = SQLiteStore(db_path, ROOT / "migrations")
            store.migrate()
            seeded = seed_two_accounts_lost_abruptly(store)
            self.assertEqual(start_one_server_process(db_path).returncode, 0)
            fresh = store.open_session(seeded["bravo"])
            self.assertEqual(open_lease_ids(store), {fresh})
            character = store.select_character(
                fresh, seeded["bravo_character"].selector,
            )
            self.assertEqual(character.id, seeded["bravo_character"].id)
            with store.connect() as db:
                generation = db.execute(
                    "SELECT lease_generation FROM sessions WHERE id=?", (fresh,),
                ).fetchone()[0]
            self.assertEqual(int(generation), 2)


class StartupRecoveryOnANewDatabaseTests(unittest.TestCase):
    def test_a_start_on_a_new_database_migrates_before_it_recovers(self):
        # Recovering first would raise on a database with no sessions table,
        # so a zero exit here pins the order as well as the creation.
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "nested" / "created.sqlite3"
            result = start_one_server_process(db_path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(db_path.is_file())
            store = SQLiteStore(db_path, ROOT / "migrations")
            self.assertEqual(rows(store, "SELECT id FROM sessions"), [])


class StartupRecoveryWiringTests(unittest.TestCase):
    """Read app.main structurally so the call cannot move without notice."""

    @classmethod
    def setUpClass(cls):
        cls.source = APP_SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.main = next(
            node for node in cls.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )

    @staticmethod
    def _is_store_call(node, attribute):
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == attribute
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "store"
        )

    def _call_lines(self, attribute):
        return sorted(
            node.lineno for node in ast.walk(self.main)
            if self._is_store_call(node, attribute)
        )

    def _blocks(self):
        for node in ast.walk(self.main):
            for field in ("body", "orelse", "finalbody"):
                block = getattr(node, field, None)
                if isinstance(block, list) and block:
                    yield block

    def _direct_statement_calls(self, block, attribute):
        found = []
        for index, statement in enumerate(block):
            if isinstance(statement, ast.Expr) and self._is_store_call(
                statement.value, attribute,
            ):
                found.append(index)
        return found

    def test_recovery_is_wired_into_every_read_write_startup_branch(self):
        # One branch for the default/arena/population databases and one for the
        # item-move capture databases.  Scene-load is the documented exception.
        self.assertEqual(len(self._call_lines("expire_open_sessions")), 2)

    def test_every_recovery_call_follows_a_migration_in_its_own_block(self):
        blocks_with_recovery = 0
        for block in self._blocks():
            recovery = self._direct_statement_calls(block, "expire_open_sessions")
            if not recovery:
                continue
            blocks_with_recovery += 1
            migrations = self._direct_statement_calls(block, "migrate")
            self.assertTrue(migrations, ast.dump(block[0]))
            self.assertLess(min(migrations), min(recovery))
        self.assertEqual(blocks_with_recovery, 2)

    def test_recovery_runs_before_any_session_surface_is_built(self):
        built = sorted(
            node.lineno for node in ast.walk(self.main)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"CharacterLifecycle", "make_state_class"}
        )
        self.assertEqual(len(built), 2)
        self.assertLess(max(self._call_lines("expire_open_sessions")), min(built))

    def test_the_scene_load_branch_is_the_one_deliberate_exception(self):
        guards = []
        for node in ast.walk(self.main):
            if not isinstance(node, ast.If):
                continue
            test = ast.get_source_segment(self.source, node.test) or ""
            # The store-setup guard, not the later session_factory branch.
            if "scene_load is not None" in test and "item_move_capture" in test:
                guards.append(node)
        self.assertEqual(len(guards), 1)
        self.assertEqual(
            self._direct_statement_calls(guards[0].body, "expire_open_sessions"),
            [],
        )
        # The skip is coherent only because that mode never opens a lease.
        read_only = next(
            node for node in ast.parse(
                SESSION_SOURCE.read_text(encoding="utf-8"),
            ).body
            if isinstance(node, ast.ClassDef)
            and node.name == "ReadOnlyFoundationSession"
        )
        self.assertNotIn(
            "open_session",
            ast.dump(read_only),
        )


if __name__ == "__main__":
    unittest.main()
