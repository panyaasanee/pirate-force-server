"""GM-002: raw GM_RunGMCommandVital capture sink writes bytes untouched."""
from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import struct

from pirateforce_foundation.gm.command_capture import (
    GM_RUN_GM_COMMAND_VITAL_ID,
    capture_raw_gm_command,
)


def _wstring(text: str) -> bytes:
    payload = text.encode("utf-16-le")
    return struct.pack("<I", len(payload)) + payload


def _nested_body(f10: int, f14: int, f18: int, s1: str, s2: str) -> bytes:
    return (
        bytes([0x0B, 1])
        + bytes([0x14]) + struct.pack("<I", f10)
        + bytes([0x14]) + struct.pack("<I", f14)
        + bytes([0x0B, f18])
        + _wstring(s1)
        + _wstring(s2)
    )


class GmCommandCaptureTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "capture"

    def test_writes_a_file_and_returns_its_path(self):
        out = capture_raw_gm_command(
            b"\x12\x34/warp 1", "panya", capture_root=self.root, now_ts=0
        )
        self.assertTrue(out.is_file())
        self.assertEqual(out.parent, self.root)

    def test_hex_dump_and_header_carry_the_raw_bytes_verbatim(self):
        raw = bytes(range(20))
        out = capture_raw_gm_command(raw, "panya", capture_root=self.root, now_ts=0)
        text = out.read_text(encoding="utf-8")
        self.assertIn(f"0x{GM_RUN_GM_COMMAND_VITAL_ID:04X}", text)
        self.assertIn("length=20", text)
        # every byte value must appear as a two-digit hex pair in the dump
        for b in raw:
            self.assertIn(f"{b:02x}", text)

    def test_two_captures_from_different_accounts_do_not_collide(self):
        out1 = capture_raw_gm_command(b"a", "panya", capture_root=self.root, now_ts=0)
        out2 = capture_raw_gm_command(b"b", "attended_test", capture_root=self.root, now_ts=0)
        self.assertNotEqual(out1, out2)

    def test_account_name_is_sanitized_in_the_filename(self):
        out = capture_raw_gm_command(
            b"x", "weird/../name", capture_root=self.root, now_ts=0
        )
        self.assertEqual(out.parent, self.root)
        self.assertNotIn("..", out.name)
        self.assertNotIn("/", out.name)

    def test_rejects_non_bytes_raw(self):
        with self.assertRaises(TypeError):
            capture_raw_gm_command("not bytes", "panya", capture_root=self.root)

    def test_rejects_empty_account_name(self):
        with self.assertRaises(ValueError):
            capture_raw_gm_command(b"x", "", capture_root=self.root)

    def test_same_account_same_second_captures_do_not_overwrite_each_other(self):
        # pf-adversary finding: two commands from one account landing in the
        # same wall-clock second must never silently overwrite each other.
        out1 = capture_raw_gm_command(
            b"first-command-bytes", "panya", capture_root=self.root, now_ts=1000.0
        )
        out2 = capture_raw_gm_command(
            b"second-command-bytes-DIFFERENT",
            "panya",
            capture_root=self.root,
            now_ts=1000.4,
        )
        self.assertNotEqual(out1, out2)
        text1 = out1.read_text(encoding="utf-8")
        text2 = out2.read_text(encoding="utf-8")
        self.assertNotEqual(text1, text2)
        self.assertIn("length=19", text1)  # len(b"first-command-bytes")
        self.assertIn("length=30", text2)  # len(b"second-command-bytes-DIFFERENT")

    def test_many_same_second_captures_from_one_account_all_survive(self):
        paths = [
            capture_raw_gm_command(
                bytes([i]), "panya", capture_root=self.root, now_ts=1000.0
            )
            for i in range(25)
        ]
        self.assertEqual(len(set(paths)), 25)
        for i, path in enumerate(paths):
            self.assertIn(f"length=1", path.read_text(encoding="utf-8"))
            self.assertIn(f"{i:02x}", path.read_text(encoding="utf-8"))

    def test_account_name_sanitizer_stays_pure_ascii_and_bounded(self):
        out = capture_raw_gm_command(
            b"x", "ปัญญา" + "a" * 100, capture_root=self.root, now_ts=0
        )
        self.assertTrue(out.name.isascii())
        self.assertLessEqual(len(out.name), 40 + len("_0x51E9.txt") + len("20000101T000000Z_"))

    def test_account_name_cannot_forge_extra_header_lines(self):
        # a newline in account_name must not let it inject a fake "account="
        # or "#" line into the capture file's header.
        out = capture_raw_gm_command(
            b"x",
            "evil\naccount=fake_injected\n# forged line",
            capture_root=self.root,
            now_ts=0,
        )
        text = out.read_text(encoding="utf-8")
        header_lines = text.split("\n\n", 1)[0].splitlines()
        account_lines = [line for line in header_lines if "account=" in line]
        self.assertEqual(len(account_lines), 1)
        forged_lines = [line for line in header_lines if line == "# forged line"]
        self.assertEqual(forged_lines, [])

    def test_account_name_all_non_ascii_falls_back_to_unnamed(self):
        out = capture_raw_gm_command(b"x", "账号测试", capture_root=self.root, now_ts=0)
        self.assertIn("unnamed", out.name)

    def test_decode_section_reports_a_well_formed_presence_zero_payload(self):
        out = capture_raw_gm_command(
            bytes([0x0B, 0]), "panya", capture_root=self.root, now_ts=0
        )
        text = out.read_text(encoding="utf-8")
        self.assertIn("decode: presence=0", text)

    def test_decode_section_reports_a_well_formed_nested_body(self):
        raw = _nested_body(11, 22, 3, "warp", "1 100 200")
        out = capture_raw_gm_command(raw, "panya", capture_root=self.root, now_ts=0)
        text = out.read_text(encoding="utf-8")
        self.assertIn("decode: presence=1", text)
        self.assertIn("field_0x10=11", text)
        self.assertIn("field_0x14=22", text)
        self.assertIn("field_0x18=3", text)
        self.assertIn('string_0x1c="warp"', text)
        self.assertIn('string_0x38="1 100 200"', text)

    def test_decode_section_reports_failure_without_losing_the_raw_bytes(self):
        raw = bytes([0xFF, 0xFF, 0xFF])
        out = capture_raw_gm_command(raw, "panya", capture_root=self.root, now_ts=0)
        text = out.read_text(encoding="utf-8")
        self.assertIn("decode: FAILED", text)
        for b in raw:
            self.assertIn(f"{b:02x}", text)

    def test_decoded_string_cannot_forge_extra_header_lines(self):
        # RE-088's two wide strings come straight from client-controlled
        # bytes -- a newline inside one must not inject a fake header line,
        # same guarantee already held for account_name.
        raw = _nested_body(1, 2, 3, "warp\n# forged line", "ok")
        out = capture_raw_gm_command(raw, "panya", capture_root=self.root, now_ts=0)
        text = out.read_text(encoding="utf-8")
        header_lines = text.split("\n\n", 1)[0].splitlines()
        forged_lines = [line for line in header_lines if line == "# forged line"]
        self.assertEqual(forged_lines, [])

    # ----- pf-adversary (round 50x5xt, verify-pass addendum): bounded ------
    # ----- collision-suffix loop, never an infinite spin -------------------

    def test_collision_loop_gives_up_after_the_bound_instead_of_spinning(self):
        from unittest import mock

        from pirateforce_foundation.gm import command_capture as capture_module

        with mock.patch.object(
            capture_module, "_MAX_FILENAME_COLLISION_ATTEMPTS", 3,
        ), mock.patch.object(
            capture_module.os, "open", side_effect=FileExistsError,
        ) as mock_open:
            with self.assertRaises(OSError):
                capture_raw_gm_command(
                    b"x", "panya", capture_root=self.root, now_ts=0,
                )
        # suffix 0, 1, 2, 3 -- exactly bound + 1 attempts, not unbounded.
        self.assertEqual(mock_open.call_count, 4)

    # ----- pf-adversary (this round): capture files must not be world- -----
    # ----- readable/executable regardless of the process umask -------------

    def test_capture_file_mode_is_owner_only_no_execute_regardless_of_umask(self):
        # `os.open` with no explicit `mode` argument defaults to 0o777
        # (masked by umask) -- reproduced live before this fix: under this
        # project's own default umask (0o022) that produced 0o755
        # (world-readable AND world-executable) for a file holding
        # forensic, client-controlled bytes (real account names, free-text
        # a GM typed). A permissive host umask (e.g. 0o000) would have made
        # it world-writable too. The fix passes an explicit mode=0o600, which
        # has no group/other bits for any umask to need to clear -- assert
        # that holds under a deliberately permissive umask (0o000) so this
        # test cannot pass by accident of the container's own umask.
        old_umask = os.umask(0o000)
        try:
            out = capture_raw_gm_command(
                b"x", "panya", capture_root=self.root, now_ts=0
            )
        finally:
            os.umask(old_umask)
        mode = stat.S_IMODE(out.stat().st_mode)
        self.assertEqual(mode, 0o600, oct(mode))

    def test_collision_loop_bound_does_not_affect_a_realistic_capture_count(self):
        # The real-world guard this bound exists next to (gm/dispatch.py's
        # own RATE_LIMIT_MAX_CALLS_PER_WINDOW) caps how often this loop can
        # even be entered per account per window -- this proves the default
        # bound leaves a generous, realistic same-second burst untouched.
        paths = [
            capture_raw_gm_command(
                bytes([i % 256]), "panya", capture_root=self.root, now_ts=1000.0,
            )
            for i in range(50)
        ]
        self.assertEqual(len(set(paths)), 50)


if __name__ == "__main__":
    unittest.main()
