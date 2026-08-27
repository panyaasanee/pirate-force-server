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
        # Rate-limit history is process-global (gm/dispatch.py's own
        # thread-safety/test-isolation tradeoff, see RATE_LIMIT_* comment) --
        # start every test from a known-empty state regardless of what ran
        # before it in this same process.
        gm_dispatch.reset_rate_limit_state_for_tests()

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

    # ----- pf-adversary (round 50x5xt): capture write failure refuses, ----
    # ----- never raises out of the handler -------------------------------

    def test_capture_os_error_is_refused_by_name_not_by_crashing(self):
        # This module's own docstring claims the "refuse by name, not by
        # crash" pattern covers this whole function -- before this round
        # that was only true for the account-lookup call, not for the disk
        # write. capture_root pointed at a path that already exists as a
        # FILE (not a directory) makes command_capture.py's own
        # `root.mkdir(parents=True, exist_ok=True)` raise a real FileExistsError,
        # the same OSError family an out-of-space or permission-denied disk
        # would raise.
        blocking_file = Path(self.tmp.name) / "capture_is_a_file"
        blocking_file.write_text("not a directory")
        config = self._config(["gm_listed"])
        outcome = gm_dispatch.handle_gm_run_command_vital(
            "gm_listed", _PRESENCE_ZERO_PAYLOAD,
            config_path=config, capture_root=blocking_file,
        )
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.captured_path)
        self.assertTrue(
            outcome.refusal_reason.startswith(
                gm_dispatch.REFUSAL_CAPTURE_WRITE_FAILED_PREFIX
            )
        )

    def test_capture_os_error_via_mock_does_not_propagate(self):
        config = self._config(["gm_listed"])
        with mock.patch.object(
            gm_dispatch, "capture_raw_gm_command",
            side_effect=OSError("simulated ENOSPC"),
        ):
            outcome = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
            )
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.captured_path)
        self.assertEqual(
            outcome.refusal_reason,
            f"{gm_dispatch.REFUSAL_CAPTURE_WRITE_FAILED_PREFIX}OSError",
        )

    # ----- pf-adversary (round 50x5xt, deferred): per-account rate limit --

    def test_calls_up_to_the_window_max_all_succeed(self):
        config = self._config(["gm_listed"])
        with mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 3,
        ):
            for i in range(3):
                outcome = gm_dispatch.handle_gm_run_command_vital(
                    "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                    config_path=config, capture_root=self.capture_root,
                    now_ts=1000.0 + i,
                )
                self.assertTrue(outcome.authorized)
                self.assertIsNotNone(outcome.captured_path)
                self.assertIsNone(outcome.refusal_reason)

    def test_the_call_past_the_window_max_is_refused_not_captured(self):
        config = self._config(["gm_listed"])
        with mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 2,
        ):
            for i in range(2):
                outcome = gm_dispatch.handle_gm_run_command_vital(
                    "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                    config_path=config, capture_root=self.capture_root,
                    now_ts=1000.0 + i,
                )
                self.assertIsNotNone(outcome.captured_path)
            before = list(self.capture_root.glob("*")) if self.capture_root.exists() else []
            outcome = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1002.0,
            )
            self.assertTrue(outcome.authorized)
            self.assertIsNone(outcome.captured_path)
            self.assertEqual(
                outcome.refusal_reason, gm_dispatch.REFUSAL_RATE_LIMITED,
            )
            after = list(self.capture_root.glob("*"))
            self.assertEqual(before, after)

    def test_the_window_slides_a_call_after_it_elapses_succeeds_again(self):
        config = self._config(["gm_listed"])
        with mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 1,
        ), mock.patch.object(
            gm_dispatch, "RATE_LIMIT_WINDOW_SECONDS", 5.0,
        ):
            first = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(first.captured_path)

            still_limited = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1004.9,
            )
            self.assertEqual(
                still_limited.refusal_reason, gm_dispatch.REFUSAL_RATE_LIMITED,
            )

            after_window = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1005.1,
            )
            self.assertIsNotNone(after_window.captured_path)
            self.assertIsNone(after_window.refusal_reason)

    def test_rate_limit_is_scoped_per_account_not_global(self):
        config = self._config(["gm_one", "gm_two"])
        with mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 1,
        ):
            first = gm_dispatch.handle_gm_run_command_vital(
                "gm_one", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(first.captured_path)
            # gm_one is now at its own cap -- gm_two must be unaffected.
            second = gm_dispatch.handle_gm_run_command_vital(
                "gm_two", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(second.captured_path)
            self.assertIsNone(second.refusal_reason)

    def test_refused_non_gm_calls_do_not_consume_a_gm_accounts_budget(self):
        config = self._config(["gm_listed"])
        with mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 1,
        ):
            for _ in range(5):
                outcome = gm_dispatch.handle_gm_run_command_vital(
                    "not_listed", _PRESENCE_ZERO_PAYLOAD,
                    config_path=config, capture_root=self.capture_root,
                    now_ts=1000.0,
                )
                self.assertEqual(
                    outcome.refusal_reason, gm_dispatch.REFUSAL_NOT_GM,
                )
            gm_outcome = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(gm_outcome.captured_path)

    def test_reset_rate_limit_state_for_tests_clears_history(self):
        config = self._config(["gm_listed"])
        with mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 1,
        ):
            capped = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(capped.captured_path)
            gm_dispatch.reset_rate_limit_state_for_tests()
            after_reset = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(after_reset.captured_path)
            self.assertIsNone(after_reset.refusal_reason)

    def test_default_window_and_limit_do_not_trip_on_a_handful_of_calls(self):
        # No mock.patch here -- proves the shipped defaults (not a
        # test-only override) stay out of the way of ordinary same-second
        # test/attended-use traffic for one account.
        config = self._config(["gm_listed"])
        for i in range(5):
            outcome = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(
                outcome.captured_path, f"call {i} was unexpectedly refused"
            )


if __name__ == "__main__":
    unittest.main()
