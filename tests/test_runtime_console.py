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

from pirateforce_foundation import runtime_console  # noqa: E402
from pirateforce_foundation.runtime_console import (  # noqa: E402
    RuntimeConsole,
    build_console_mirror,
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
        # An explicit --db is mandatory here.  Without it the app resolves the
        # default foundation path state/pirateforce.sqlite3 -- the CANONICAL
        # database -- and the foundation branch runs store.migrate() plus
        # expire_open_sessions() against it on every pytest run.  That exact
        # latent hole applied migration 004 to the canonical DB at
        # 2026-08-18 01:22:31 during the round-51 Windows gate (job 096); it
        # had been invisible before only because migrations 001-003 were
        # already applied, making migrate() a no-op.  See
        # pf_bridge/FINDINGS_R41_PYTEST_TOUCHED_CANONICAL_DB.md.
        with tempfile.TemporaryDirectory() as tmp:
            capture = Path(tmp) / "self-test-capture"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable, "-m", "pirateforce_foundation.app",
                    "--db", str(Path(tmp) / "selftest_scratch.sqlite3"),
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



class ConsoleMirrorFactoryTests(unittest.TestCase):
    """CORE-REQUEST-GM-064: the door that lets a test drive the real mirror.

    Every assertion here is about the object an operator actually reads
    through.  None of them build a stand-in stream.
    """

    def test_factory_writes_both_ends_and_declares_the_module_encoding(self):
        console, retained = io.StringIO(), io.StringIO()
        previous_out, previous_err = sys.stdout, sys.stderr
        with tempfile.TemporaryDirectory() as tmp:
            mirror = build_console_mirror(console, retained)
            # No file, no directory: the whole point of the door is that a
            # test can hold the mirror without RuntimeConsole's own I/O.
            self.assertEqual(os.listdir(tmp), [])
        self.assertIs(sys.stdout, previous_out)
        self.assertIs(sys.stderr, previous_err)
        self.assertEqual(mirror.write("summary\n"), len("summary\n"))
        self.assertEqual(console.getvalue(), "summary\n")
        self.assertEqual(retained.getvalue(), "summary\n")
        self.assertEqual(mirror.encoding, "utf-8")
        self.assertEqual(mirror.errors, "strict")
        self.assertTrue(mirror.writable())

    def test_a_line_breaking_control_stays_on_one_line_through_the_mirror(self):
        # This is the property LANE-GM's own test depends on, and the reason
        # a cp874 stand-in cannot stand in: cp874 cannot encode U+0085 at
        # all, so a stand-in folds it for free and stays green even with the
        # producer's own folding deleted.  The real mirror declares utf-8
        # and carries the character through untouched -- so a test built on
        # this factory sees the second line a deleted fold would create.
        console, retained = io.StringIO(), io.StringIO()
        mirror = build_console_mirror(console, retained)
        mirror.write("TOKEN a=1\u0085b=2\n")
        self.assertEqual(retained.getvalue(), "TOKEN a=1\u0085b=2\n")
        self.assertEqual(console.getvalue(), retained.getvalue())
        self.assertEqual(retained.getvalue().count("\n"), 1)
        with self.assertRaises(UnicodeEncodeError):
            "\u0085".encode("cp874")

    def test_runtime_console_installs_what_the_factory_returns(self):
        # The anti-drift pin: the factory is worthless if RuntimeConsole
        # goes back to constructing _Mirror directly, because then GM's
        # test holds one object and the operator reads another.
        class Sentinel(io.StringIO):
            pass

        built = []

        def factory(console, retained):
            mirror = Sentinel()
            built.append((console, retained, mirror))
            return mirror

        with tempfile.TemporaryDirectory() as tmp:
            out, err = io.StringIO(), io.StringIO()
            original = runtime_console.build_console_mirror
            runtime_console.build_console_mirror = factory
            try:
                console = RuntimeConsole(
                    Path(tmp), out, err, close_console_streams=False,
                )
                installed = (sys.stdout, sys.stderr)
                console.close()
            finally:
                runtime_console.build_console_mirror = original
        self.assertEqual(len(built), 2)
        self.assertIs(installed[0], built[0][2])
        self.assertIs(installed[1], built[1][2])
        self.assertIs(built[0][0], out)
        self.assertIs(built[1][0], err)

if __name__ == "__main__":
    unittest.main()
