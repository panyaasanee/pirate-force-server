"""CORE-REQUEST-GM-010 -- the inbound 0x51E9 authorization gate.

``tests/test_gm_dispatch.py`` (an earlier, differently-scoped file despite
the similar name) proves CORE-REQUEST-006, the login-time GM state frame.
This file proves the new module, ``gm/dispatch.py``:
``handle_gm_run_command_vital`` must refuse -- and, critically, must never
write a capture file for -- any account that is not on the ``gm_accounts``
allowlist, including the default "nobody is GM" case and a malformed
config, before it ever authorizes a real capture.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm.command_wire import (  # noqa: E402
    GM_RUN_GM_COMMAND_VITAL_ID,
)


# A structurally valid GM_RunGMCommandVital payload (presence=0, the
# "empty" shape command_wire.py decodes cleanly) -- content does not matter
# for these tests, only that dispatch is given something byte-shaped.
_PRESENCE_ZERO_PAYLOAD = bytes([0x0B, 0x00])


class GmCommandDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.capture_root = Path(self.tmp.name) / "capture"

    def _config(self, gm_accounts_value):
        path = Path(self.tmp.name) / "gm_accounts.json"
        path.write_text(json.dumps({"gm_accounts": gm_accounts_value}))
        return str(path)

    # ----- default: no config file at all -> refused, nothing captured ----

    def test_default_no_config_refuses_and_writes_nothing(self):
        missing = str(Path(self.tmp.name) / "does_not_exist.json")
        outcome = gm_dispatch.handle_gm_run_command_vital(
            "some_player", _PRESENCE_ZERO_PAYLOAD,
            config_path=missing, capture_root=self.capture_root,
        )
        self.assertFalse(outcome.authorized)
        self.assertIsNone(outcome.captured_path)
        self.assertEqual(outcome.refusal_reason, gm_dispatch.REFUSAL_NOT_GM)
        self.assertFalse(self.capture_root.exists())

    # ----- an account NOT on the allowlist -> refused, nothing captured ---

    def test_non_gm_account_refuses_and_writes_nothing(self):
        config = self._config(["someone_else"])
        outcome = gm_dispatch.handle_gm_run_command_vital(
            "not_listed", _PRESENCE_ZERO_PAYLOAD,
            config_path=config, capture_root=self.capture_root,
        )
        self.assertFalse(outcome.authorized)
        self.assertIsNone(outcome.captured_path)
        self.assertEqual(outcome.refusal_reason, gm_dispatch.REFUSAL_NOT_GM)
        self.assertFalse(self.capture_root.exists())

    # ----- a malformed config -> refused BY NAME, never raises ------------

    def test_malformed_config_refuses_by_name_not_by_crashing(self):
        path = Path(self.tmp.name) / "gm_accounts.json"
        path.write_text(json.dumps({"gm_accounts": "not_a_list"}))
        outcome = gm_dispatch.handle_gm_run_command_vital(
            "any_player", _PRESENCE_ZERO_PAYLOAD,
            config_path=str(path), capture_root=self.capture_root,
        )
        self.assertFalse(outcome.authorized)
        self.assertIsNone(outcome.captured_path)
        self.assertTrue(
            outcome.refusal_reason.startswith(
                gm_dispatch.REFUSAL_LOOKUP_FAILED_PREFIX
            )
        )
        self.assertIn("ValueError", outcome.refusal_reason)
        self.assertFalse(self.capture_root.exists())

    # ----- an account ON the allowlist -> authorized, real capture --------

    def test_gm_account_is_authorized_and_captured(self):
        config = self._config(["gm_listed"])
        outcome = gm_dispatch.handle_gm_run_command_vital(
            "gm_listed", _PRESENCE_ZERO_PAYLOAD,
            config_path=config, capture_root=self.capture_root,
        )
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.refusal_reason)
        self.assertIsNotNone(outcome.captured_path)
        self.assertTrue(outcome.captured_path.is_file())
        contents = outcome.captured_path.read_text(encoding="utf-8")
        self.assertIn(f"0x{GM_RUN_GM_COMMAND_VITAL_ID:04X}", contents)
        self.assertIn("account=gm_listed", contents)
        self.assertIn("presence=0", contents)

    # ----- exactly one capture file per authorized call --------------------

    def test_two_authorized_calls_from_the_same_gm_write_two_files(self):
        config = self._config(["gm_listed"])
        first = gm_dispatch.handle_gm_run_command_vital(
            "gm_listed", _PRESENCE_ZERO_PAYLOAD,
            config_path=config, capture_root=self.capture_root, now_ts=1000.0,
        )
        second = gm_dispatch.handle_gm_run_command_vital(
            "gm_listed", _PRESENCE_ZERO_PAYLOAD,
            config_path=config, capture_root=self.capture_root, now_ts=1000.0,
        )
        self.assertNotEqual(first.captured_path, second.captured_path)
        self.assertTrue(first.captured_path.is_file())
        self.assertTrue(second.captured_path.is_file())

    # ----- caller misuse still raises (not client bytes) -------------------

    def test_empty_account_name_raises(self):
        with self.assertRaises(ValueError):
            gm_dispatch.handle_gm_run_command_vital(
                "", _PRESENCE_ZERO_PAYLOAD, capture_root=self.capture_root,
            )

    def test_non_bytes_payload_raises(self):
        config = self._config(["gm_listed"])
        with self.assertRaises(TypeError):
            gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", "not bytes",
                config_path=config, capture_root=self.capture_root,
            )

    # ----- pf-adversary: an oversized payload from a real GM is refused ---
    # ----- (still "authorized" -- it IS a GM account -- but not captured) -

    def test_oversized_payload_from_a_gm_account_is_refused_not_captured(self):
        config = self._config(["gm_listed"])
        oversized = bytes(gm_dispatch.MAX_RAW_PAYLOAD_LENGTH + 1)
        outcome = gm_dispatch.handle_gm_run_command_vital(
            "gm_listed", oversized,
            config_path=config, capture_root=self.capture_root,
        )
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.captured_path)
        self.assertEqual(
            outcome.refusal_reason, gm_dispatch.REFUSAL_PAYLOAD_TOO_LARGE,
        )
        self.assertFalse(self.capture_root.exists())

    def test_payload_at_exactly_the_size_cap_is_still_captured(self):
        config = self._config(["gm_listed"])
        at_cap = bytes(gm_dispatch.MAX_RAW_PAYLOAD_LENGTH)
        outcome = gm_dispatch.handle_gm_run_command_vital(
            "gm_listed", at_cap,
            config_path=config, capture_root=self.capture_root,
        )
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.refusal_reason)
        self.assertIsNotNone(outcome.captured_path)
        self.assertTrue(outcome.captured_path.is_file())

    def test_oversized_payload_from_a_non_gm_account_still_just_refuses_as_not_gm(self):
        # The size check runs AFTER authorization, so a non-GM sender's
        # refusal reason stays REFUSAL_NOT_GM regardless of payload size --
        # a non-GM account never learns the size cap exists.
        oversized = bytes(gm_dispatch.MAX_RAW_PAYLOAD_LENGTH + 1)
        outcome = gm_dispatch.handle_gm_run_command_vital(
            "not_listed", oversized, capture_root=self.capture_root,
        )
        self.assertFalse(outcome.authorized)
        self.assertEqual(outcome.refusal_reason, gm_dispatch.REFUSAL_NOT_GM)
        self.assertFalse(self.capture_root.exists())

    # ----- env-var override path still works (same as accounts.py) -------

    def test_env_override_path_is_honoured(self):
        config = self._config(["gm_listed"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: config},
        ):
            outcome = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                capture_root=self.capture_root,
            )
        self.assertTrue(outcome.authorized)


if __name__ == "__main__":
    unittest.main()
