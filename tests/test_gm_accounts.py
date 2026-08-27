"""GM-001: gm_accounts allowlist -- default empty, exact match only, no self-elevation path."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.accounts import is_gm_account, load_gm_accounts


class GmAccountsDefaultTests(unittest.TestCase):
    def test_missing_config_file_means_nobody_is_gm(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does_not_exist.json"
            self.assertEqual(load_gm_accounts(missing), frozenset())
            self.assertFalse(is_gm_account("panya", missing))
            self.assertFalse(is_gm_account("", missing))

    def test_empty_gm_accounts_list_means_nobody_is_gm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_accounts.json"
            path.write_text(json.dumps({"gm_accounts": []}), encoding="utf-8")
            self.assertEqual(load_gm_accounts(path), frozenset())
            self.assertFalse(is_gm_account("panya", path))


class GmAccountsAllowlistTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "gm_accounts.json"
        self.path.write_text(
            json.dumps({"gm_accounts": ["panya", "attended_test"]}), encoding="utf-8"
        )

    def test_listed_account_is_gm(self):
        self.assertTrue(is_gm_account("panya", self.path))
        self.assertTrue(is_gm_account("attended_test", self.path))

    def test_unlisted_account_is_not_gm(self):
        self.assertFalse(is_gm_account("some_player", self.path))

    def test_matching_is_exact_and_case_sensitive(self):
        self.assertFalse(is_gm_account("Panya", self.path))
        self.assertFalse(is_gm_account(" panya", self.path))
        self.assertFalse(is_gm_account("panya ", self.path))

    def test_load_gm_accounts_returns_frozenset(self):
        accounts = load_gm_accounts(self.path)
        self.assertIsInstance(accounts, frozenset)
        self.assertEqual(accounts, frozenset({"panya", "attended_test"}))


class GmAccountsMalformedConfigTests(unittest.TestCase):
    def test_non_list_gm_accounts_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_accounts.json"
            path.write_text(json.dumps({"gm_accounts": "panya"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_gm_accounts(path)

    def test_non_string_entry_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_accounts.json"
            path.write_text(json.dumps({"gm_accounts": ["panya", 5]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_gm_accounts(path)

    def test_is_gm_account_rejects_non_str_account_name(self):
        with self.assertRaises(TypeError):
            is_gm_account(12345)

    def test_non_object_top_level_json_raises_value_error(self):
        # A JSON list/string/null at the top level must fail loud with
        # ValueError like every other malformed shape here, not fall through
        # to an unhandled AttributeError from a bare dict.get() call.
        for bad_top_level in ([1, 2, 3], "not an object", None):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "gm_accounts.json"
                path.write_text(json.dumps(bad_top_level), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_gm_accounts(path)


if __name__ == "__main__":
    unittest.main()
