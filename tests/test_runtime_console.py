from __future__ import annotations

import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.runtime_console import (  # noqa: E402
    RuntimeConsole,
    install_runtime_console,
)


class RuntimeConsoleTests(unittest.TestCase):
    def test_summary_output_is_mirrored_and_streams_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, err = io.StringIO(), io.StringIO()
            previous_out, previous_err = sys.stdout, sys.stderr
            runtime = RuntimeConsole(
                Path(tmp), out, err, close_console_streams=False,
            )
            try:
                print("visible summary")
                print("visible error", file=sys.stderr)
                sys.stdout.flush(); sys.stderr.flush()
            finally:
                runtime.close()
            self.assertIs(sys.stdout, previous_out)
            self.assertIs(sys.stderr, previous_err)
            self.assertEqual(out.getvalue(), "visible summary\n")
            self.assertEqual(err.getvalue(), "visible error\n")
            self.assertEqual(
                (Path(tmp) / "server_console_live.out.txt").read_bytes(),
                b"visible summary\n",
            )
            self.assertEqual(
                (Path(tmp) / "server_console_live.err.txt").read_bytes(),
                b"visible error\n",
            )

    def test_install_uses_capture_root_and_visible_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = []
            out, err = io.StringIO(), io.StringIO()

            def streams(title):
                captured.append(title)
                return out, err, False

            runtime = install_runtime_console(
                ROOT, tmp, ROOT / "state" / "runtime.sqlite3", "test-mode",
                console_streams=streams,
            )
            runtime.close()
            self.assertEqual(len(captured), 1)
            self.assertIn("Pirate Force Foundation Server", captured[0])
            self.assertIn("test-mode", captured[0])
            retained = (
                Path(tmp) / "server_console_live.out.txt"
            ).read_text(encoding="utf-8")
            self.assertIn("[FOUNDATION] visible console:", retained)
            self.assertIn("[FOUNDATION] summary logs:", retained)

    def test_existing_log_pair_fails_closed_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "server_console_live.out.txt").write_text(
                "preserve", encoding="utf-8",
            )
            with self.assertRaises(FileExistsError):
                RuntimeConsole(
                    root, io.StringIO(), io.StringIO(),
                    close_console_streams=False,
                )
            self.assertEqual(
                (root / "server_console_live.out.txt").read_text(encoding="utf-8"),
                "preserve",
            )

    def test_self_test_only_is_the_console_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture = Path(tmp) / "self-test-capture"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable, "-m", "pirateforce_foundation.app",
                    "--capture-root", str(capture), "--self-test-only",
                ],
                cwd=ROOT, env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(capture.exists())

    def test_all_server_launchers_request_normal_windows(self):
        for name in (
            "run_foundation_visible.ps1",
            "run_test_arena.ps1",
            "run_scene2_load_only.ps1",
        ):
            source = (ROOT / "tools" / name).read_text(encoding="utf-8")
            self.assertIn("-WindowStyle Normal", source, name)
        # The scene guard is a helper, not a server. Its hidden window remains
        # allowed while the actual Foundation Start-Process is explicitly normal.


if __name__ == "__main__":
    unittest.main()
