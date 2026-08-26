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


if __name__ == "__main__":
    unittest.main()
