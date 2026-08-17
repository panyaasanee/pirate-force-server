"""Pins for the recorded single-session known limitation (HYP-PF-011).

Owner decision 2026-08-17 (item 14, option B): single-session service is a
``known_limitation``, not ``by_design``.  These tests pin both enforcement
layers exactly as the report records them, so the limitation cannot drift or
be "fixed" quietly without tripping the ledger's preconditions:

1. the legacy v141 accept layer is structurally serial (both listeners), and
2. the Foundation store's ``open_session`` closes every open lease of the
   same account before the new lease exists, failing the old lease closed.

Evidence report:
``reports/PF_SESSION_LIMIT001_SINGLE_SESSION_SERIAL_ACCEPT_KNOWN_LIMITATION_20260817.md``
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
LEDGER_PATH = ROOT / "docs" / "HYPOTHESIS_LEDGER.json"
COVERAGE_PATH = ROOT / "docs" / "FUNCTIONAL_COVERAGE.json"


class SerialAcceptStructureTests(unittest.TestCase):
    """The wire-layer wall: accept-and-handle in one loop, both listeners."""

    @classmethod
    def setUpClass(cls):
        cls.source = LEGACY_PATH.read_text(encoding="utf-8")

    def test_both_listeners_use_backlog_four_and_inline_accept(self):
        self.assertEqual(self.source.count("s.listen(4)"), 2)
        self.assertEqual(self.source.count(".accept()"), 2)

    def test_no_per_connection_service_machinery_exists(self):
        # The round-18 measurement (second client queued 42.1 s / 22.1 s in
        # the TCP backlog, accepted ~30 ms after the first closed) is only
        # structurally possible while nothing services connections in
        # parallel.  Pin the absence of every stdlib mechanism for it.
        for marker in (
            "ThreadingTCPServer", "ThreadingMixIn", "socketserver",
            "selectors.", "import selectors", "asyncio",
        ):
            self.assertNotIn(marker, self.source, marker)
        # Threads exist for the listeners themselves; none is started with a
        # per-connection handler argument taking an accepted socket.
        for match in re.finditer(r"Thread\(target=([A-Za-z_][A-Za-z_0-9]*)", self.source):
            self.assertNotIn("conn", match.group(1))


class LeaseTakeoverTests(unittest.TestCase):
    """The Foundation-layer wall: one open lease per account, old one dies."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.account_id = self.store.ensure_account("limitation")

    def tearDown(self):
        self.tmp.cleanup()

    def _open_rows(self):
        with self.store.connect() as db:
            return db.execute(
                "SELECT id, lease_generation FROM sessions "
                "WHERE account_id=? AND closed_at IS NULL ORDER BY lease_generation",
                (self.account_id,),
            ).fetchall()

    def test_open_session_closes_every_prior_open_lease_of_the_account(self):
        first = self.store.open_session(self.account_id)
        second = self.store.open_session(self.account_id)
        rows = self._open_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], second)
        self.assertEqual(rows[0]["lease_generation"], 2)
        self.assertNotEqual(first, second)
        with self.store.connect() as db:
            closed = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (first,),
            ).fetchone()
        self.assertIsNotNone(closed["closed_at"])

    def test_taken_over_lease_fails_closed_for_selected_session_work(self):
        first = self.store.open_session(self.account_id)
        self.store.open_session(self.account_id)
        with self.assertRaisesRegex(PermissionError, "stale or non-owning"):
            self.store.get_backpack(first, character_id=1)

    def test_other_accounts_are_untouched_by_a_takeover(self):
        other_account = self.store.ensure_account("bystander")
        other = self.store.open_session(other_account)
        self.store.open_session(self.account_id)
        self.store.open_session(self.account_id)
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (other,),
            ).fetchone()
        self.assertIsNone(row["closed_at"])


class KnownLimitationRecordTests(unittest.TestCase):
    """The decision record itself must stay exactly what the owner approved."""

    def test_ledger_entry_is_active_pending_and_production_false(self):
        raw = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        entry = {e["id"]: e for e in raw["entries"]}["HYP-PF-011"]
        self.assertEqual(entry["kind"], "protocol_hypothesis")
        self.assertEqual(entry["introduced_checkpoint"], "MULTI-CLIENT-001")
        self.assertEqual(entry["status"], "active")
        self.assertIs(entry["production_allowed"], False)
        self.assertIn("known_limitation rather than by_design", entry["provenance"])
        self.assertIn("exception boundary", entry["exact_value_or_transform"])
        self.assertIn("lease policy", entry["exact_value_or_transform"])

    def test_matrix_row_is_blocked_with_this_evidence_and_never_by_design(self):
        raw = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
        row = next(
            cap
            for domain in raw["domains"] if domain["id"] == "session_lifecycle"
            for cap in domain["capabilities"]
            if cap["id"] == "concurrent_multi_client"
        )
        self.assertEqual(row["status"], "blocked")
        self.assertTrue(row["required"])
        self.assertIn(
            "reports/PF_SESSION_LIMIT001_SINGLE_SESSION_SERIAL_ACCEPT_"
            "KNOWN_LIMITATION_20260817.md",
            row["evidence_refs"],
        )
        self.assertIn("not by_design", row["notes"])


if __name__ == "__main__":
    unittest.main()
