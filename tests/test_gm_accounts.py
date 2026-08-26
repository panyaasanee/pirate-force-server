"""GM-001: the allowlist every other GM-lane module trusts."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pirateforce_foundation.gm import accounts


class TestGmAccounts(unittest.TestCase):
    def test_default_is_empty(self):
        self.assertEqual(accounts.load_gm_accounts(None), frozenset())

    def test_missing_env_var_is_empty(self):
        self.assertEqual(accounts.load_gm_accounts(""), frozenset())

    def test_missing_file_is_empty_not_an_error(self):
        self.assertEqual(
            accounts.load_gm_accounts("/nonexistent/path/gm_accounts.json"),
            frozenset(),
        )

    def test_malformed_json_is_empty_not_an_error(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_accounts.json"
            path.write_text("{ not json", encoding="utf-8")
            self.assertEqual(accounts.load_gm_accounts(path), frozenset())

    def test_non_list_json_is_empty(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_accounts.json"
            path.write_text(json.dumps({"1": True}), encoding="utf-8")
            self.assertEqual(accounts.load_gm_accounts(path), frozenset())

    def test_loads_listed_account_ids(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_accounts.json"
            path.write_text(json.dumps([7, 42]), encoding="utf-8")
            self.assertEqual(accounts.load_gm_accounts(path), frozenset({7, 42}))

    def test_non_int_entries_are_dropped_not_fatal(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_accounts.json"
            path.write_text(json.dumps([7, "not-an-id", None, True]), encoding="utf-8")
            self.assertEqual(accounts.load_gm_accounts(path), frozenset({7}))

    def test_is_gm_true_only_for_listed_account(self):
        allowlist = frozenset({7})
        self.assertTrue(accounts.is_gm(7, allowlist))
        self.assertFalse(accounts.is_gm(8, allowlist))

    def test_is_gm_false_on_empty_allowlist_for_every_account(self):
        for account_id in (0, 1, -1, 7, 999999):
            self.assertFalse(accounts.is_gm(account_id, frozenset()))


if __name__ == "__main__":
    unittest.main()
