"""GT-DIAG-MULTI-OBJECT-001: the diagnostic-boot allowlist.

Deliberately the same file as ``tests/test_gm_accounts.py`` with one name
changed throughout, because the module under test is deliberately the same
module as ``gm/accounts.py`` with one name changed throughout: default empty,
exact match only, malformed config refused out loud, no path by which a
client can put itself on the list.  A second config loader that drifted from
the first in even one of those four properties is the failure this file
exists to catch.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.diag_multi_object_config import (  # noqa: E402
    CONFIG_KEY,
    DEFAULT_CONFIG_PATH,
    ENV_OVERRIDE,
    is_diag_multi_object_account,
    load_diag_multi_object_accounts,
)


class DiagConfigDefaultTests(unittest.TestCase):
    def test_missing_config_file_means_nobody_gets_the_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does_not_exist.json"
            self.assertEqual(load_diag_multi_object_accounts(missing), frozenset())
            self.assertFalse(is_diag_multi_object_account("panya", missing))
            self.assertFalse(is_diag_multi_object_account("", missing))

    def test_empty_account_list_means_nobody_gets_the_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diag_multi_object.json"
            path.write_text(json.dumps({CONFIG_KEY: []}), encoding="utf-8")
            self.assertEqual(load_diag_multi_object_accounts(path), frozenset())
            self.assertFalse(is_diag_multi_object_account("panya", path))

    def test_this_repository_ships_no_allowlist_file(self):
        # The absence of this file IS the off switch, and a future commit that
        # adds one would turn the diagnostic on for whoever it names on every
        # boot from the repository root.  Named here so that would be a failing
        # test rather than a surprise on someone's screen.
        self.assertFalse((ROOT / DEFAULT_CONFIG_PATH).exists())

    def test_env_override_name_and_default_path_are_the_documented_ones(self):
        # The wiring text asks for "an env var, same shape as
        # PF_GM_ACCOUNTS_CONFIG"; an operator following the handback types
        # these two strings, so they are pinned rather than left to drift.
        self.assertEqual(ENV_OVERRIDE, "PF_DIAG_MULTI_OBJECT_CONFIG")
        self.assertEqual(DEFAULT_CONFIG_PATH, "config/diag_multi_object.json")
        self.assertNotIn(ENV_OVERRIDE, os.environ)


class DiagConfigAllowlistTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "diag_multi_object.json"
        self.path.write_text(
            json.dumps({CONFIG_KEY: ["panya", "attended_test"]}), encoding="utf-8"
        )

    def test_listed_account_gets_the_diagnostic(self):
        self.assertTrue(is_diag_multi_object_account("panya", self.path))
        self.assertTrue(is_diag_multi_object_account("attended_test", self.path))

    def test_unlisted_account_does_not(self):
        self.assertFalse(is_diag_multi_object_account("some_player", self.path))

    def test_matching_is_exact_and_case_sensitive(self):
        self.assertFalse(is_diag_multi_object_account("Panya", self.path))
        self.assertFalse(is_diag_multi_object_account(" panya", self.path))
        self.assertFalse(is_diag_multi_object_account("panya ", self.path))

    def test_load_returns_frozenset(self):
        accounts = load_diag_multi_object_accounts(self.path)
        self.assertIsInstance(accounts, frozenset)
        self.assertEqual(accounts, frozenset({"panya", "attended_test"}))

    def test_env_override_is_read_when_no_path_is_passed(self):
        os.environ[ENV_OVERRIDE] = str(self.path)
        self.addCleanup(os.environ.pop, ENV_OVERRIDE, None)
        self.assertTrue(is_diag_multi_object_account("panya"))
        self.assertFalse(is_diag_multi_object_account("nobody"))


class DiagConfigMalformedTests(unittest.TestCase):
    def test_non_list_accounts_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diag_multi_object.json"
            path.write_text(json.dumps({CONFIG_KEY: "panya"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_diag_multi_object_accounts(path)

    def test_non_string_entry_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diag_multi_object.json"
            path.write_text(json.dumps({CONFIG_KEY: ["panya", 5]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_diag_multi_object_accounts(path)

    def test_rejects_non_str_account_name(self):
        with self.assertRaises(TypeError):
            is_diag_multi_object_account(12345)

    def test_non_object_top_level_json_raises_value_error(self):
        for bad_top_level in ([1, 2, 3], "not an object", None):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "diag_multi_object.json"
                path.write_text(json.dumps(bad_top_level), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_diag_multi_object_accounts(path)

    def test_a_gm_allowlist_file_does_not_grant_the_diagnostic(self):
        # The two loaders read DIFFERENT keys out of DIFFERENT files on
        # purpose: being GM must not silently also mean "put five extra
        # monsters in my town", and one operator's copy-paste of the other
        # file must resolve to empty rather than to everyone in it.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_accounts.json"
            path.write_text(
                json.dumps({"gm_accounts": ["panya"]}), encoding="utf-8")
            self.assertEqual(load_diag_multi_object_accounts(path), frozenset())
            self.assertFalse(is_diag_multi_object_account("panya", path))


if __name__ == "__main__":
    unittest.main()
