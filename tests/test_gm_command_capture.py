"""GM-002: raw GM_RunGMCommandVital capture sink writes bytes untouched."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.command_capture import (
    GM_RUN_GM_COMMAND_VITAL_ID,
    capture_raw_gm_command,
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

    def test_account_name_all_non_ascii_falls_back_to_unnamed(self):
        out = capture_raw_gm_command(b"x", "账号测试", capture_root=self.root, now_ts=0)
        self.assertIn("unnamed", out.name)


if __name__ == "__main__":
    unittest.main()
