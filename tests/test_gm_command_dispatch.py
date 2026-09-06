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

import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import command_capture as gm_command_capture  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm.command_wire import (  # noqa: E402
    GM_RUN_GM_COMMAND_VITAL_ID,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_gm_capture_mocks import close_that_really_closes_then_fails  # noqa: E402


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
        # Capture-quota usage is process-global too (same tradeoff, see
        # MAX_CAPTURED_BYTES_PER_ACCOUNT comment) -- same reasoning.
        gm_dispatch.reset_capture_quota_state_for_tests()

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

    def test_non_str_account_name_raises(self):
        with self.assertRaises(ValueError):
            gm_dispatch.handle_gm_run_command_vital(
                12345, _PRESENCE_ZERO_PAYLOAD, capture_root=self.capture_root,
            )

    def test_a_str_subclass_account_name_is_rejected_not_authorized(self):
        # pf-adversary (gm/ package sweep): this entry point is the one
        # place a real client's authenticated login token flows in as
        # account_name -- if it accepted a str subclass here, the same
        # __eq__/__hash__-lying bypass accounts.is_gm_account now rejects
        # for itself could still be reintroduced one call earlier.
        class EvilStr(str):
            def __eq__(self, other):
                return True

            def __hash__(self):
                return hash("gm_listed")

        config = self._config(["gm_listed"])
        with self.assertRaises(ValueError):
            gm_dispatch.handle_gm_run_command_vital(
                EvilStr("totally_not_a_gm"), _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
            )
        self.assertFalse(self.capture_root.exists())

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

    # ----- pf-adversary (gm/ package sweep): total-volume capture quota ---
    # ----- (distinct from the per-call size cap and the burst rate limit) -

    def test_capture_quota_refuses_once_the_estimated_total_exceeds_the_cap(self):
        config = self._config(["gm_listed"])
        payload = bytes(1000)
        per_call_estimate = gm_dispatch._estimate_capture_file_bytes(1000, len("gm_listed"))
        with mock.patch.object(
            gm_dispatch, "MAX_CAPTURED_BYTES_PER_ACCOUNT", per_call_estimate * 2,
        ), mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 100,
        ):
            first = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(first.captured_path)
            second = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.1,
            )
            self.assertIsNotNone(second.captured_path)
            before = list(self.capture_root.glob("*"))
            third = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.2,
            )
            # Still a real GM account -- the quota refusal never says
            # otherwise, same shape as the payload-size and rate-limit
            # refusals above.
            self.assertTrue(third.authorized)
            self.assertIsNone(third.captured_path)
            self.assertEqual(
                third.refusal_reason, gm_dispatch.REFUSAL_CAPTURE_QUOTA_EXCEEDED,
            )
            after = list(self.capture_root.glob("*"))
            self.assertEqual(before, after)

    def test_capture_quota_is_scoped_per_account_not_global(self):
        config = self._config(["gm_one", "gm_two"])
        payload = bytes(1000)
        with mock.patch.object(
            gm_dispatch, "MAX_CAPTURED_BYTES_PER_ACCOUNT",
            gm_dispatch._estimate_capture_file_bytes(1000, len("gm_one")),
        ):
            first = gm_dispatch.handle_gm_run_command_vital(
                "gm_one", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(first.captured_path)
            # gm_one is now at its own cap -- gm_two must be unaffected.
            second = gm_dispatch.handle_gm_run_command_vital(
                "gm_two", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            self.assertIsNotNone(second.captured_path)
            self.assertIsNone(second.refusal_reason)

    def test_refused_non_gm_calls_do_not_consume_a_gm_accounts_capture_quota(self):
        config = self._config(["gm_listed"])
        payload = bytes(1000)
        with mock.patch.object(
            gm_dispatch, "MAX_CAPTURED_BYTES_PER_ACCOUNT",
            gm_dispatch._estimate_capture_file_bytes(1000, len("gm_listed")),
        ):
            for _ in range(5):
                outcome = gm_dispatch.handle_gm_run_command_vital(
                    "not_listed", payload, config_path=config,
                    capture_root=self.capture_root, now_ts=1000.0,
                )
                self.assertEqual(outcome.refusal_reason, gm_dispatch.REFUSAL_NOT_GM)
            gm_outcome = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload, config_path=config,
                capture_root=self.capture_root, now_ts=1000.0,
            )
            self.assertIsNotNone(gm_outcome.captured_path)

    def test_reset_capture_quota_state_for_tests_clears_usage(self):
        config = self._config(["gm_listed"])
        payload = bytes(1000)
        with mock.patch.object(
            gm_dispatch, "MAX_CAPTURED_BYTES_PER_ACCOUNT",
            gm_dispatch._estimate_capture_file_bytes(1000, len("gm_listed")),
        ):
            capped = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload, config_path=config,
                capture_root=self.capture_root, now_ts=1000.0,
            )
            self.assertIsNotNone(capped.captured_path)
            gm_dispatch.reset_capture_quota_state_for_tests()
            after_reset = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload, config_path=config,
                capture_root=self.capture_root, now_ts=1000.0,
            )
            self.assertIsNotNone(after_reset.captured_path)
            self.assertIsNone(after_reset.refusal_reason)

    def test_default_quota_does_not_trip_on_a_handful_of_small_calls(self):
        # No mock.patch here -- proves the shipped default (50 MiB) stays
        # out of the way of ordinary same-second test/attended-use traffic.
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

    # ----- pf-adversary (round `whoaop`): decode-section re-print was not --
    # ----- charged against the capture-quota estimate at all -------------

    @staticmethod
    def _nested_body_payload(str1: str, str2: str) -> bytes:
        # A structurally valid GM_RunGMCommandVital nested body (RE-088
        # pin): presence(u8 tag, nonzero) + field_0x10(u32 tag) +
        # field_0x14(u32 tag) + field_0x18(u8 tag) + two 0x48-tagged,
        # length-prefixed UTF-16LE strings (5+N each since the 2026-09-02
        # tag correction -- with the old 4+N shape here the decode section
        # raises, the strings are never re-printed, and this whole guard
        # passes while testing nothing). Content of the scalar fields
        # does not matter for this test, only that command_capture.py's
        # decode section succeeds and re-prints str1/str2.
        def wstr(s: str) -> bytes:
            raw = s.encode("utf-16-le")
            return bytes((0x48,)) + struct.pack("<I", len(raw)) + raw

        body = bytes([0x0B, 0x01])
        body += bytes([0x14]) + struct.pack("<I", 0)
        body += bytes([0x14]) + struct.pack("<I", 0)
        body += bytes([0x0B, 0x00])
        body += wstr(str1)
        body += wstr(str2)
        return body

    def test_capture_quota_estimate_covers_non_ascii_decode_section_reprint(self):
        # Regression for the exact defect pf-adversary reproduced: the old
        # `raw_payload_length * 5 + 1024` formula only charged for
        # command_capture._hex_dump's ~4.75x expansion and ignored that
        # _decode_section re-prints string_0x1c/string_0x38 a SECOND time
        # via unicode_escape (up to 3x more per raw byte for any BMP
        # non-Latin1 codepoint, Thai included) once the payload decodes as
        # a nonzero-presence nested body. A Thai-heavy payload at the size
        # cap used to charge 328,694 bytes against an actual write of
        # 508,235 -- a 1.546x overrun of the guard's own stated invariant.
        thai_char = "ก"  # ก -- BMP, non-ASCII, non-Latin1
        fixed_header = 2 + 5 + 5 + 2 + 5 + 5  # tags/scalars + 2 tagged length prefixes
        budget_chars = (gm_dispatch.MAX_RAW_PAYLOAD_LENGTH - fixed_header) // 2
        str1 = thai_char * (budget_chars // 2)
        str2 = thai_char * (budget_chars - len(str1))
        payload = self._nested_body_payload(str1, str2)
        self.assertLessEqual(len(payload), gm_dispatch.MAX_RAW_PAYLOAD_LENGTH)

        estimate = gm_dispatch._estimate_capture_file_bytes(
            len(payload), len("gm_listed"),
        )

        config = self._config(["gm_listed"])
        outcome = gm_dispatch.handle_gm_run_command_vital(
            "gm_listed", payload,
            config_path=config, capture_root=self.capture_root,
            now_ts=1000.0,
        )
        self.assertIsNotNone(outcome.captured_path)
        actual_bytes_written = outcome.captured_path.stat().st_size

        self.assertGreaterEqual(
            estimate, actual_bytes_written,
            "capture-quota estimate undercounts a real write -- the "
            "MAX_CAPTURED_BYTES_PER_ACCOUNT guard no longer bounds what "
            "actually lands on disk",
        )

    def test_capture_quota_estimate_covers_a_long_or_non_ascii_account_name(self):
        # Regression for the OLD debt named but not fixed in round
        # `eu2g1d-b` (that round's own D8 nonclaim: "the quota hole that
        # does not count account_name -- old, not this round's -- still
        # unfixed, next round's job"). `_sanitize_account`'s 40-char
        # truncation (command_capture.py) only bounds the FILENAME -- the
        # header line's `account=` value is
        # `_escape_for_header(account_name)`, the FULL, untruncated,
        # unsanitized account_name run through `unicode_escape`, and
        # nothing upstream of this call (``accounts.is_gm_account`` above)
        # caps how long an allowlisted account_name string may be. A
        # non-BMP account_name character costs 10 escaped bytes
        # (``\Uxxxxxxxx``) per source character -- verified directly
        # against Python's own ``unicode_escape`` codec, not assumed:
        # ``"\U00020000".encode("unicode_escape")`` is ``b'\\U00020000'``,
        # 10 bytes for len-1 input.
        astral_char = "\U00020000"  # non-BMP -- 10 escaped bytes/character
        account_name = astral_char * 200
        config = self._config([account_name])
        payload = _PRESENCE_ZERO_PAYLOAD

        estimate = gm_dispatch._estimate_capture_file_bytes(
            len(payload), len(account_name),
        )

        outcome = gm_dispatch.handle_gm_run_command_vital(
            account_name, payload,
            config_path=config, capture_root=self.capture_root,
            now_ts=1000.0,
        )
        self.assertIsNotNone(outcome.captured_path)
        actual_bytes_written = outcome.captured_path.stat().st_size

        self.assertGreaterEqual(
            estimate, actual_bytes_written,
            "capture-quota estimate undercounts a real write for a long/"
            "non-ASCII account_name -- the MAX_CAPTURED_BYTES_PER_ACCOUNT "
            "guard no longer bounds what actually lands on disk",
        )

    def test_the_account_name_term_is_pinned_at_ten_bytes_a_character(self):
        # The card above pins that the TERM EXISTS; pf-adversary (round
        # `vq07el`) showed it does not pin the term's VALUE. Re-running that
        # card with a coefficient of 2, 3, 4 or 5 passes all four, because
        # the flat 2 KiB header allowance absorbs the difference at the 200
        # characters it happens to use. A coefficient of 2 under-estimates
        # for real from 220 characters up (est 2504 vs actual 2535), so the
        # card was firing on "something changed", not on "the number is
        # right" -- the shape of house wound 12.
        #
        # 10 is not a taste: a full sweep of Python's own unicode_escape over
        # all 0x110000 codepoints puts the maximum escaped length at exactly
        # 10 bytes (`\Uxxxxxxxx`, first reached at U+10000). Pin the
        # derivative directly, where no header allowance can hide it.
        per_character = (
            gm_dispatch._estimate_capture_file_bytes(0, 1)
            - gm_dispatch._estimate_capture_file_bytes(0, 0)
        )
        self.assertEqual(
            per_character, 10,
            "one account_name character must be charged the 10 bytes "
            "unicode_escape can actually cost it",
        )
        self.assertEqual(
            len("\U00020000".encode("unicode_escape")), per_character,
            "the coefficient and the codec must agree, measured not assumed",
        )

    # ----- pf-adversary (round `vq07el`, D9): the quota charges CONTENT ---
    # ----- bytes but is a cap on DISK bytes, and a small file still ------
    # ----- consumes a whole filesystem block ------------------------------

    def test_charged_capture_bytes_floors_a_small_call_at_one_disk_block(self):
        # A tiny call's own content estimate (2048 header + a few bytes)
        # is well under one filesystem block -- charging exactly that would
        # let a scripted account's many small/empty commands consume far
        # more real disk than the quota's running total ever shows.
        small_content_estimate = gm_dispatch._estimate_capture_file_bytes(0, 0)
        self.assertLess(
            small_content_estimate, gm_dispatch.MIN_CAPTURE_FILE_DISK_BYTES,
            "this test is only meaningful while the content estimate for a "
            "trivial call is smaller than one disk block",
        )
        self.assertEqual(
            gm_dispatch._charged_capture_bytes(0, 0),
            gm_dispatch.MIN_CAPTURE_FILE_DISK_BYTES,
        )

    def test_charged_capture_bytes_does_not_floor_a_large_call(self):
        # The floor must not LOWER a charge that already exceeds one disk
        # block -- that would undercharge every real-sized command instead
        # of only fixing the small-call gap it exists for.
        large_content_estimate = gm_dispatch._estimate_capture_file_bytes(
            1000, len("gm_listed"),
        )
        self.assertGreater(
            large_content_estimate, gm_dispatch.MIN_CAPTURE_FILE_DISK_BYTES,
        )
        self.assertEqual(
            gm_dispatch._charged_capture_bytes(1000, len("gm_listed")),
            large_content_estimate,
        )

    def test_capture_quota_is_charged_at_the_disk_block_floor_not_the_smaller_content_estimate(self):
        # End-to-end: a real GM account sending the smallest possible
        # payload repeatedly must be refused after MIN_CAPTURE_FILE_DISK_BYTES
        # bytes' worth of calls, not after the (larger) number of calls the
        # unfloored content estimate would have allowed under the same cap.
        config = self._config(["gm_listed"])
        cap = gm_dispatch.MIN_CAPTURE_FILE_DISK_BYTES * 2
        # Sanity: if this test's own arithmetic assumption stops holding
        # (a future change makes the content estimate exceed the floor for
        # this payload/account-name length), the test would pass for the
        # wrong reason -- fail loudly instead.
        content_estimate = gm_dispatch._estimate_capture_file_bytes(
            len(_PRESENCE_ZERO_PAYLOAD), len("gm_listed"),
        )
        self.assertLess(content_estimate, gm_dispatch.MIN_CAPTURE_FILE_DISK_BYTES)
        with mock.patch.object(
            gm_dispatch, "MAX_CAPTURED_BYTES_PER_ACCOUNT", cap,
        ), mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 100,
        ):
            first = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            second = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.1,
            )
            third = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.2,
            )
        self.assertIsNotNone(first.captured_path)
        self.assertIsNotNone(second.captured_path)
        self.assertIsNone(
            third.captured_path,
            "two calls already charged a full MIN_CAPTURE_FILE_DISK_BYTES "
            "each against a two-block cap -- a third call using the "
            "smaller, unfloored content estimate would wrongly still fit",
        )
        self.assertEqual(
            third.refusal_reason, gm_dispatch.REFUSAL_CAPTURE_QUOTA_EXCEEDED,
        )

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

    # ----- pf-adversary (round `vq07el`, D10): a failed write must not ----
    # ----- permanently spend the quota it never actually used ------------

    def test_a_failed_write_refunds_its_charge_so_a_later_call_still_fits(self):
        # Cap set to exactly one call's charge: before this round's fix,
        # the first (failing) call would have consumed the whole cap and
        # the second (real) call -- same account, same payload size, no
        # mock -- would have been wrongly refused as over-quota despite
        # zero bytes ever landing on disk for the first call.
        config = self._config(["gm_listed"])
        payload = bytes(1000)
        one_call_charge = gm_dispatch._charged_capture_bytes(
            len(payload), len("gm_listed"),
        )
        with mock.patch.object(
            gm_dispatch, "MAX_CAPTURED_BYTES_PER_ACCOUNT", one_call_charge,
        ), mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 100,
        ):
            with mock.patch.object(
                gm_dispatch, "capture_raw_gm_command",
                side_effect=OSError("simulated ENOSPC"),
            ):
                failed = gm_dispatch.handle_gm_run_command_vital(
                    "gm_listed", payload,
                    config_path=config, capture_root=self.capture_root,
                    now_ts=1000.0,
                )
            self.assertIsNone(failed.captured_path)
            self.assertEqual(
                failed.refusal_reason,
                f"{gm_dispatch.REFUSAL_CAPTURE_WRITE_FAILED_PREFIX}OSError",
            )

            retried = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.1,
            )
        self.assertIsNotNone(
            retried.captured_path,
            "the failed call's charge was not refunded -- a real write "
            "for the same account/size was wrongly refused as over-quota",
        )

    def test_a_failed_write_refund_never_pushes_the_running_total_negative(self):
        # Two failures in a row for an account that never had a successful
        # charge must not build a negative balance -- a negative running
        # total would grant more budget than any call actually consumed
        # once a real write later succeeds.
        config = self._config(["gm_listed"])
        with mock.patch.object(
            gm_dispatch, "capture_raw_gm_command",
            side_effect=OSError("simulated ENOSPC"),
        ):
            gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
            gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.1,
            )
        self.assertEqual(
            gm_dispatch._capture_quota_bytes_by_account.get("gm_listed", 0), 0,
        )

    # ----- pf-adversary (round `40bjg7`, follow-up `gn7gk5`): the refund ---
    # ----- above must not fire for a write failure it cannot prove left ---
    # ----- zero bytes on disk ----------------------------------------------

    def test_a_real_write_failure_still_refunds_once_the_partial_file_is_confirmed_gone(self):
        # Through the REAL command_capture path this time (only the
        # syscall fails, not the whole function) -- the exact scenario
        # pf-adversary reproduced against round `40bjg7`'s own D10 fix.
        # os.unlink is not mocked, so command_capture's own cleanup runs
        # for real and this must behave exactly like the mocked-function
        # tests above: refunded, and nothing left on disk.
        config = self._config(["gm_listed"])
        payload = bytes(1000)
        one_call_charge = gm_dispatch._charged_capture_bytes(
            len(payload), len("gm_listed"),
        )
        with mock.patch.object(
            gm_dispatch, "MAX_CAPTURED_BYTES_PER_ACCOUNT", one_call_charge,
        ), mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 100,
        ):
            with mock.patch.object(
                gm_command_capture.os, "write",
                side_effect=OSError("simulated ENOSPC"),
            ):
                failed = gm_dispatch.handle_gm_run_command_vital(
                    "gm_listed", payload,
                    config_path=config, capture_root=self.capture_root,
                    now_ts=1000.0,
                )
            self.assertEqual(
                failed.refusal_reason,
                f"{gm_dispatch.REFUSAL_CAPTURE_WRITE_FAILED_PREFIX}OSError",
            )
            retried = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.1,
            )
        self.assertIsNotNone(retried.captured_path)
        leftover = list(self.capture_root.glob("*"))
        self.assertEqual(
            len(leftover), 1, "exactly the retried call's own file, nothing "
            "left over from the failed one",
        )

    def test_a_write_failure_that_cannot_be_cleaned_up_is_not_refunded(self):
        # Both the write AND command_capture's own cleanup unlink fail --
        # real bytes may still be on disk for this call, so refunding here
        # would silently recreate D9 (quota reads less than real disk use).
        config = self._config(["gm_listed"])
        payload = bytes(1000)
        # pf-adversary (round `0op9bt` ADDENDUM, D6): an unmocked `unlink`
        # failure now retries for real and prints a real stderr line --
        # mock `time.sleep` and swallow the print so this test stays fast
        # and quiet.
        with mock.patch.object(
            gm_command_capture.os, "write",
            side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            gm_command_capture.os, "unlink",
            side_effect=OSError("simulated EACCES"),
        ), mock.patch.object(
            gm_command_capture.time, "sleep",
        ), contextlib.redirect_stderr(io.StringIO()):
            outcome = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.captured_path)
        self.assertEqual(
            outcome.refusal_reason,
            f"{gm_dispatch.REFUSAL_CAPTURE_WRITE_FAILED_PREFIX}"
            f"CaptureFileNotVerifiedRemoved",
        )
        charged = gm_dispatch._charged_capture_bytes(len(payload), len("gm_listed"))
        self.assertEqual(
            gm_dispatch._capture_quota_bytes_by_account.get("gm_listed", 0),
            charged,
            "the charge must still stand -- nothing proved the bytes never "
            "reached disk",
        )

    # ----- pf-adversary (round `gn7gk5`, follow-up `79ahzl`): a write that -
    # ----- fully SUCCEEDED, then failed only at close(), is the more ------
    # ----- severe case -- a COMPLETE real capture, not an empty one -------

    def test_a_close_only_failure_after_a_successful_write_is_not_refunded_when_unrecoverable(self):
        config = self._config(["gm_listed"])
        payload = bytes(1000)
        with mock.patch.object(
            gm_command_capture.os, "close",
            side_effect=close_that_really_closes_then_fails(
                "simulated close ENOSPC",
            ),
        ), mock.patch.object(
            gm_command_capture.os, "unlink",
            side_effect=OSError("simulated EACCES"),
        ), mock.patch.object(
            gm_command_capture.time, "sleep",
        ), contextlib.redirect_stderr(io.StringIO()):
            outcome = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.0,
            )
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.captured_path)
        self.assertEqual(
            outcome.refusal_reason,
            f"{gm_dispatch.REFUSAL_CAPTURE_WRITE_FAILED_PREFIX}"
            f"CaptureFileNotVerifiedRemoved",
        )
        charged = gm_dispatch._charged_capture_bytes(len(payload), len("gm_listed"))
        self.assertEqual(
            gm_dispatch._capture_quota_bytes_by_account.get("gm_listed", 0),
            charged,
            "a full, real capture may be sitting on disk uncleaned -- "
            "refunding here would charge nothing for real disk usage",
        )

    def test_a_close_only_failure_still_refunds_once_cleanup_confirms_removal(self):
        # Same trigger, but os.unlink is real this time -- cleanup succeeds,
        # so this must behave exactly like an ordinary write failure: safe
        # to refund, and a later real call for the same account still fits.
        config = self._config(["gm_listed"])
        payload = bytes(1000)
        one_call_charge = gm_dispatch._charged_capture_bytes(
            len(payload), len("gm_listed"),
        )
        with mock.patch.object(
            gm_dispatch, "MAX_CAPTURED_BYTES_PER_ACCOUNT", one_call_charge,
        ), mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 100,
        ):
            with mock.patch.object(
                gm_command_capture.os, "close",
                side_effect=close_that_really_closes_then_fails(
                    "simulated close ENOSPC",
                ),
            ):
                failed = gm_dispatch.handle_gm_run_command_vital(
                    "gm_listed", payload,
                    config_path=config, capture_root=self.capture_root,
                    now_ts=1000.0,
                )
            self.assertEqual(
                failed.refusal_reason,
                f"{gm_dispatch.REFUSAL_CAPTURE_WRITE_FAILED_PREFIX}OSError",
            )
            retried = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", payload,
                config_path=config, capture_root=self.capture_root,
                now_ts=1000.1,
            )
        self.assertIsNotNone(retried.captured_path)
        leftover = list(self.capture_root.glob("*"))
        self.assertEqual(len(leftover), 1, leftover)

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

    # ----- pf-adversary (verify pass, same round): out-of-order now_ts ----
    # ----- must not let a stale timestamp hide behind a newer one --------

    def test_an_out_of_order_now_ts_is_still_pruned_correctly(self):
        # Reproduces, without real threads, the ordering gap pf-adversary
        # found live: two calls for the same account whose *insertion*
        # order does not match their *timestamp* order (the exact shape a
        # clock-read-before-the-lock race could produce). bisect.insort
        # keeps gm/dispatch.py's internal history sorted regardless of
        # insertion order, so the front-pop prune loop's ascending-order
        # assumption holds even here.
        config = self._config(["gm_listed"])
        with mock.patch.object(
            gm_dispatch, "RATE_LIMIT_MAX_CALLS_PER_WINDOW", 2,
        ), mock.patch.object(
            gm_dispatch, "RATE_LIMIT_WINDOW_SECONDS", 5.0,
        ):
            # Later timestamp recorded first...
            later = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1010.0,
            )
            self.assertIsNotNone(later.captured_path)
            # ...then an earlier timestamp arrives second (out of order).
            earlier = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1006.0,
            )
            self.assertIsNotNone(earlier.captured_path)
            # Window is now at its cap (2): a third call still inside both
            # timestamps' windows is refused.
            third = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1010.5,
            )
            self.assertEqual(
                third.refusal_reason, gm_dispatch.REFUSAL_RATE_LIMITED,
            )
            # Once real (wall-clock-ordered) time passes 1006.0's own
            # window (cutoff 1006.0 + 5.0 = 1011.0), the OUT-OF-ORDER
            # earlier entry must still be pruned correctly (sorted by
            # value, not by insertion order) -- proving the fix is by
            # construction, not by luck: if pruning were still assuming
            # insertion order, the 1010.0 entry (inserted first, but
            # numerically LATER) would incorrectly block this from ever
            # being pruned by a front-pop.
            after_earlier_window = gm_dispatch.handle_gm_run_command_vital(
                "gm_listed", _PRESENCE_ZERO_PAYLOAD,
                config_path=config, capture_root=self.capture_root,
                now_ts=1011.1,
            )
            self.assertIsNotNone(after_earlier_window.captured_path)
            self.assertIsNone(after_earlier_window.refusal_reason)

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
