"""GM-002: raw 0x51E9 capture is log-only and computes its own GM gate."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pirateforce_foundation.gm import command_capture


class TestGmCommandCapture(unittest.TestCase):
    def test_non_gm_account_captures_nothing(self):
        with TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "capture.jsonl"
            result = command_capture.capture_raw_command(
                b"whatever", account_id=1, gm_accounts=frozenset(), out_path=out_path)
            self.assertIsNone(result)
            self.assertFalse(out_path.exists())

    def test_gm_account_appends_one_record(self):
        with TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "capture.jsonl"
            record = command_capture.capture_raw_command(
                b"\x01\x02\x03", account_id=7, gm_accounts=frozenset({7}), out_path=out_path)
            self.assertEqual(record["vital_id"], "0x51e9")
            self.assertEqual(record["account_id"], 7)
            self.assertEqual(record["length"], 3)
            self.assertEqual(record["hex"], "010203")
            lines = out_path.read_text(encoding="ascii").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), record)

    def test_account_not_in_the_allowlist_is_refused_even_if_other_accounts_are_gm(self):
        with TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "capture.jsonl"
            result = command_capture.capture_raw_command(
                b"x", account_id=8, gm_accounts=frozenset({7}), out_path=out_path)
            self.assertIsNone(result)
            self.assertFalse(out_path.exists())

    def test_capture_does_not_interpret_the_payload(self):
        with TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "capture.jsonl"
            record = command_capture.capture_raw_command(
                b"warp 17", account_id=7, gm_accounts=frozenset({7}), out_path=out_path)
            self.assertEqual(set(record), {"vital_id", "account_id", "length", "hex"})

    def test_appends_rather_than_overwrites(self):
        with TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "capture.jsonl"
            command_capture.capture_raw_command(
                b"a", account_id=7, gm_accounts=frozenset({7}), out_path=out_path)
            command_capture.capture_raw_command(
                b"bb", account_id=7, gm_accounts=frozenset({7}), out_path=out_path)
            lines = out_path.read_text(encoding="ascii").splitlines()
            self.assertEqual(len(lines), 2)

    def test_non_bytes_payload_is_rejected(self):
        with TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "capture.jsonl"
            with self.assertRaises(TypeError):
                command_capture.capture_raw_command(
                    "not-bytes", account_id=7, gm_accounts=frozenset({7}), out_path=out_path)

    def test_revoking_the_account_stops_capture_on_the_very_next_call(self):
        """The allowlist is recomputed per call, not cached by the caller."""
        with TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "capture.jsonl"
            allowlist = frozenset({7})
            command_capture.capture_raw_command(
                b"a", account_id=7, gm_accounts=allowlist, out_path=out_path)
            revoked = frozenset()
            result = command_capture.capture_raw_command(
                b"b", account_id=7, gm_accounts=revoked, out_path=out_path)
            self.assertIsNone(result)
            lines = out_path.read_text(encoding="ascii").splitlines()
            self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()
