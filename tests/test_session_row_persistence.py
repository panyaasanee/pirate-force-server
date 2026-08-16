"""Offline oracle for the `sessions` row-persistence claim.

The coverage row `session_lifecycle/session_row_persistence` is graded
`runtime_pass` on the strength of a read-only post-state oracle that observed
"one session row with both timestamps, integrity ok and an empty foreign-key
check" after a live client session.  Until now the only test cited by that row
was `tests/test_connection_lifecycle.py`, which exercises lease and socket
teardown error paths.  It queries `sessions.closed_at` twice, but only as a
side observation of a lease close; nothing in it watches the row *shape*, the
generation sequence, the accumulated history, or the integrity oracle that the
runtime report actually leans on.

This module reproduces that runtime oracle offline against the real
`SQLiteStore` and the real `CharacterLifecycle`, so the claim has a test that
fails when the claim stops being true.

Deliberately out of scope, because the runtime report does not claim them:
concurrent multi-client sessions, account isolation as a security property,
credential policy, and anything about what the client observed.

The module drives `CharacterLifecycle` rather than `FoundationSession` on
purpose: `FoundationSession.select_and_start` carries an opt-in gate that is
under active revision, and this claim is about the store, not that gate.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.store import SQLiteStore

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

SESSION_COLUMNS = (
    "id", "account_id", "selected_character_id", "opened_at", "closed_at",
)


class SessionRowPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.default = Position(
            1, 0,
            self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y,
            self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, self.default,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def tearDown(self):
        self.tmp.cleanup()

    # ---- helpers -------------------------------------------------------

    def preset(self, name):
        actor = self.legacy.get_preset_actor_wire()
        if name == "test01":
            return actor
        old = self.legacy.wstr_tag("test01")
        self.assertEqual(actor.count(old), 1)
        return actor.replace(old, self.legacy.wstr_tag(name), 1)

    def rows(self, account_id=None):
        """Read `sessions` through the same read-only oracle the report used."""
        with self.store.connect_read_only() as db:
            if account_id is None:
                cursor = db.execute(
                    "SELECT * FROM sessions ORDER BY lease_generation"
                )
            else:
                cursor = db.execute(
                    "SELECT * FROM sessions WHERE account_id=? "
                    "ORDER BY lease_generation",
                    (account_id,),
                )
            return [dict(row) for row in cursor.fetchall()]

    def oracle(self):
        """The exact post-state pair the runtime report quotes."""
        with self.store.connect_read_only() as db:
            integrity = db.execute("PRAGMA integrity_check").fetchall()
            foreign_keys = db.execute("PRAGMA foreign_key_check").fetchall()
        return [r[0] for r in integrity], [tuple(r) for r in foreign_keys]

    def one_full_session(self, login="oracle", name="oracle"):
        account_id, sid, _ = self.lifecycle.login(login)
        character = self.lifecycle.create(account_id, name, self.preset(name))
        selected = self.lifecycle.select(sid, character.selector)
        self.lifecycle.checkpoint(
            sid, selected, Position(1, 0, 11.0, 22.0, 33.0, 0.25),
        )
        self.lifecycle.exit(
            sid, selected, Position(1, 0, 44.0, 55.0, 66.0, 0.5),
        )
        return account_id, sid, selected

    # ---- the claim -----------------------------------------------------

    def test_login_writes_one_open_row_with_the_exact_column_shape(self):
        account_id, sid, _ = self.lifecycle.login("shape")
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        for column in SESSION_COLUMNS:
            self.assertIn(column, row)
        self.assertEqual(row["id"], sid)
        self.assertEqual(row["account_id"], account_id)
        self.assertIsNone(row["selected_character_id"])
        self.assertIsNone(row["closed_at"])
        self.assertTrue(row["opened_at"])
        self.assertEqual(row["lease_generation"], 1)

    def test_select_binds_the_character_and_exit_closes_the_same_row(self):
        account_id, sid, selected = self.one_full_session()
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["id"], sid)
        self.assertEqual(row["account_id"], account_id)
        self.assertEqual(row["selected_character_id"], selected.id)
        self.assertTrue(row["opened_at"])
        self.assertTrue(row["closed_at"])
        self.assertGreaterEqual(row["closed_at"], row["opened_at"])

    def test_post_state_oracle_is_ok_and_has_no_foreign_key_violation(self):
        self.one_full_session()
        integrity, foreign_keys = self.oracle()
        self.assertEqual(integrity, ["ok"])
        self.assertEqual(foreign_keys, [])

    def test_the_read_only_oracle_cannot_write_to_the_database(self):
        self.one_full_session()
        with self.store.connect_read_only() as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("UPDATE sessions SET closed_at=NULL")
        self.assertTrue(self.rows()[0]["closed_at"])

    def test_a_second_login_closes_the_first_row_and_bumps_the_generation(self):
        account_id, first, _ = self.lifecycle.login("relogin")
        _, second, _ = self.lifecycle.login("relogin")
        self.assertNotEqual(first, second)
        rows = self.rows(account_id)
        self.assertEqual([r["id"] for r in rows], [first, second])
        self.assertEqual([r["lease_generation"] for r in rows], [1, 2])
        self.assertTrue(rows[0]["closed_at"])
        self.assertIsNone(rows[1]["closed_at"])

    def test_history_accumulates_and_a_close_never_deletes_a_row(self):
        account_id, _, _ = self.lifecycle.login("history")
        for _ in range(3):
            self.lifecycle.login("history")
        rows = self.rows(account_id)
        self.assertEqual(len(rows), 4)
        self.assertEqual(
            [r["lease_generation"] for r in rows], [1, 2, 3, 4],
        )
        self.assertEqual(sum(1 for r in rows if r["closed_at"] is None), 1)
        self.store.close_session(rows[-1]["id"])
        self.assertEqual(len(self.rows(account_id)), 4)

    def test_close_session_is_idempotent_and_never_rewrites_the_stamp(self):
        _, sid, _ = self.lifecycle.login("idempotent")
        self.store.close_session(sid)
        first = self.rows()[0]["closed_at"]
        self.assertTrue(first)
        self.store.close_session(sid)
        self.store.close_session(sid)
        self.assertEqual(self.rows()[0]["closed_at"], first)

    def test_expire_closes_every_open_row_and_leaves_closed_stamps_alone(self):
        _, first, _ = self.lifecycle.login("expire-a")
        _, second, _ = self.lifecycle.login("expire-b")
        self.store.close_session(first)
        already = {r["id"]: r["closed_at"] for r in self.rows()}
        self.store.expire_open_sessions()
        after = {r["id"]: r["closed_at"] for r in self.rows()}
        self.assertEqual(after[first], already[first])
        self.assertTrue(after[second])
        self.assertTrue(all(value for value in after.values()))

    def test_a_login_on_another_account_never_closes_this_account_row(self):
        mine, my_sid, _ = self.lifecycle.login("account-one")
        self.lifecycle.login("account-two")
        rows = self.rows(mine)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], my_sid)
        self.assertIsNone(rows[0]["closed_at"])

    def test_a_closed_session_can_no_longer_select_or_write_a_position(self):
        account_id, sid, _ = self.lifecycle.login("revoked")
        character = self.lifecycle.create(
            account_id, "revoked", self.preset("revoked"),
        )
        selected = self.lifecycle.select(sid, character.selector)
        self.store.close_session(sid)
        with self.assertRaises(KeyError):
            self.lifecycle.select(sid, character.selector)
        with self.assertRaises(PermissionError):
            self.lifecycle.checkpoint(
                sid, selected, Position(1, 0, 1.0, 2.0, 3.0, 0.0),
            )

    # ---- guards, mutation-checked --------------------------------------

    def test_foreign_keys_are_enforced_so_an_orphan_row_is_refused(self):
        """Mutation check: prove the FK oracle above is not vacuous.

        `foreign_key_check` returning empty means nothing if the database would
        happily accept an orphan.  Writing one must fail at insert time.
        """
        self.one_full_session()
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.connect() as db:
                db.execute(
                    "INSERT INTO sessions(id,account_id,lease_generation,opened_at) "
                    "VALUES ('orphan',987654,1,'2026-01-01T00:00:00.000000+00:00')",
                )
        self.assertEqual(
            [r["id"] for r in self.rows() if r["id"] == "orphan"], [],
        )
        self.assertEqual(self.oracle()[1], [])

    def test_the_row_assertions_would_notice_a_session_left_open(self):
        """Mutation check: prove the closed_at assertion actually bites."""
        _, sid, _ = self.one_full_session()
        with self.store.connect() as db:
            db.execute(
                "UPDATE sessions SET closed_at=NULL WHERE id=?", (sid,),
            )
        row = self.rows()[0]
        self.assertIsNone(row["closed_at"])
        with self.assertRaises(AssertionError):
            self.assertTrue(row["closed_at"])

    def test_the_oracle_would_notice_a_foreign_key_violation(self):
        """Mutation check: prove `foreign_key_check` reports a real orphan.

        Foreign keys are enforced per connection, so an orphan can only be
        planted with enforcement off.  That is exactly why the post-state
        oracle is worth running: it catches rows the writer never inserted.
        """
        self.one_full_session()
        db = sqlite3.connect(self.db_path)
        try:
            db.execute("PRAGMA foreign_keys=OFF")
            db.execute(
                "INSERT INTO sessions(id,account_id,lease_generation,opened_at) "
                "VALUES ('planted',987654,99,'2026-01-01T00:00:00.000000+00:00')",
            )
            db.commit()
        finally:
            db.close()
        integrity, foreign_keys = self.oracle()
        self.assertEqual(integrity, ["ok"])
        self.assertEqual(len(foreign_keys), 1)
        self.assertEqual(foreign_keys[0][0], "sessions")


if __name__ == "__main__":
    unittest.main()
