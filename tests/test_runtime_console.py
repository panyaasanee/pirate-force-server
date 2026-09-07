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

    def test_factory_writes_both_ends_and_reports_the_console_encoding(self):
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
        # COO ruling `20260907_1346` flipped this pin: the mirror does
        # not declare utf-8/strict, it REPORTS what the console it wraps
        # declares.  io.StringIO declares neither, so both answers here
        # are the documented fallbacks -- and `errors` is "replace", not
        # "strict", so a diagnostic can never raise out of dispatch.
        self.assertEqual(mirror.encoding, "utf-8")
        self.assertEqual(mirror.errors, "replace")
        self.assertTrue(mirror.writable())

    def test_a_line_breaking_control_stays_on_one_line_through_the_mirror(self):
        # This is the property LANE-GM's own test depends on, and the reason
        # a cp874 stand-in cannot stand in: cp874 cannot encode U+0085 at
        # all, so a stand-in folds it for free and stays green even with the
        # producer's own folding deleted.  A mirror over a stream that
        # takes utf-8 reports utf-8 and carries the character through
        # untouched -- so a test built on this factory sees the second
        # line a deleted fold would create.
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
            # RuntimeConsole tears down what it installed, so a stand-in
            # for the factory's product has to be tear-downable too.
            def stop_mirroring(self, fallback):
                torn_down.append((self, fallback))

        torn_down = []
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
        self.assertEqual([pair[0] for pair in torn_down], list(installed))



class RuntimeConsoleLifetimeTest(unittest.TestCase):
    """Two consoles alive at once, and the argument order of the factory.

    Both cases come from the adversary pass on `#1022` (findings D1 and
    the second half of D5).  Neither had a test that could go red.
    """

    def test_factory_writes_the_console_before_the_retained_file(self):
        # D1: the previous test wrote the same text to two look-alike
        # sinks, so `_Mirror(retained, console)` stayed green.  Order is
        # load-bearing, and DISPUTED: `test_gm_login_scene_admission.py`
        # reads the same console-first order as the hazard (a cp874
        # console raised and the refusal was then recorded nowhere).
        # This pins the order the code ships with TODAY so it cannot
        # drift silently; which order is right is open, and turns on
        # `write()` not being atomic across its two sinks.
        # D2 is decided (COO `20260907_1346`); encoding/errors are
        # pinned by the two tests below, not here.
        order: list[str] = []

        class _Recorder(io.StringIO):
            def __init__(self, name: str) -> None:
                super().__init__()
                self._name = name

            def write(self, value: str) -> int:
                order.append(self._name)
                return super().write(value)

        console, retained = _Recorder("console"), _Recorder("retained")
        build_console_mirror(console, retained).write("summary\n")
        self.assertEqual(order, ["console", "retained"])

    def test_a_dying_console_never_hands_stdout_a_dead_mirror(self):
        # D5: `close()` used to restore `_previous_out` unconditionally.
        # With two consoles alive, that hands the LATER owner's stdout to
        # the EARLIER owner's mirror, whose retained file is closed --
        # every later print() raises ValueError, and the interpreter
        # exits 120 while flushing at shutdown.  Both close orders.
        for order in ("outer-first", "inner-first"):
            with self.subTest(order=order):
                with tempfile.TemporaryDirectory() as tmp:
                    previous_out, previous_err = sys.stdout, sys.stderr
                    outer = RuntimeConsole(
                        Path(tmp) / "outer", io.StringIO(), io.StringIO(),
                        close_console_streams=False,
                    )
                    inner = RuntimeConsole(
                        Path(tmp) / "inner", io.StringIO(), io.StringIO(),
                        close_console_streams=False,
                    )
                    try:
                        first, second = (
                            (outer, inner) if order == "outer-first"
                            else (inner, outer)
                        )
                        first.close()
                        # The guard itself: closing one console must not
                        # take stdout away from the one still running.
                        self.assertIs(sys.stdout, second._installed_out)
                        self.assertIs(sys.stderr, second._installed_err)
                        second.close()
                    finally:
                        outer.close()
                        inner.close()
                        restored_out, restored_err = sys.stdout, sys.stderr
                        sys.stdout, sys.stderr = previous_out, previous_err
                    self.assertIs(restored_out, previous_out)
                    self.assertIs(restored_err, previous_err)

    def test_a_mirror_that_outlived_its_files_forwards_instead_of_raising(
        self,
    ):
        # The same failure seen from the object's side: whatever still
        # holds a closed console's mirror must not turn print() into an
        # exception at interpreter shutdown.  COO ruling `20260907_1441`
        # then chose FORWARD over drop -- the operator's window is a
        # person, the retained file is not -- so the line has to land on
        # the fallback and NOT in the closed retained file.
        with tempfile.TemporaryDirectory() as tmp:
            fallback = io.StringIO()
            previous_out, previous_err = sys.stdout, sys.stderr
            sys.stdout = fallback
            try:
                runtime = RuntimeConsole(
                    Path(tmp), io.StringIO(), io.StringIO(),
                    close_console_streams=False,
                )
                leaked = sys.stdout
                runtime.close()
            finally:
                sys.stdout, sys.stderr = previous_out, previous_err
            self.assertEqual(leaked.write("after close\n"), len("after close\n"))
            leaked.flush()
            self.assertIn("after close\n", fallback.getvalue())
            # The evidence really does split in two, which is why
            # `_Mirror.__doc__` says so: the retained file stops at close.
            self.assertEqual(
                (Path(tmp) / "server_console_live.out.txt").read_bytes(), b"",
            )

    def test_the_teardown_warning_is_emitted_once_not_once_per_line(self):
        # COO ruling `20260907_1441` item 3: one bool per mirror, not a
        # counter per line.  Ten lines after teardown must still leave
        # exactly one warning on the fallback, or a torn-down console
        # turns into ten lines of noise for every real line.
        fallback = io.StringIO()
        mirror = build_console_mirror(io.StringIO(), io.StringIO())
        mirror.stop_mirroring(fallback)
        for index in range(10):
            mirror.write(f"line {index}\n")
        text = fallback.getvalue()
        self.assertEqual(text.count("runtime console torn down"), 1)
        for index in range(10):
            self.assertIn(f"line {index}\n", text)

    def test_forwarding_never_raises_and_never_recurses_through_a_cycle(self):
        # Two dead mirrors pointing at each other: `_live_stream` alone
        # only bounds ITS walk, so without the per-thread re-entry guard
        # a.write() -> b.write() -> a.write() recurses until the stack
        # ends.  A raising fallback must be swallowed too: after teardown
        # a diagnostic may never change dispatch.
        first = build_console_mirror(io.StringIO(), io.StringIO())
        second = build_console_mirror(io.StringIO(), io.StringIO())
        first.stop_mirroring(second)
        second.stop_mirroring(first)
        # Counting the hops, not just "it returned": a RecursionError is
        # an Exception and the swallow above catches it, so a version
        # with the guard deleted still returns normally after burning a
        # thousand frames.  This is the assertion that goes red for it.
        hops = []
        original = runtime_console._live_stream

        def counting(stream):
            hops.append(stream)
            return original(stream)

        runtime_console._live_stream = counting
        try:
            self.assertEqual(first.write("cycle\n"), len("cycle\n"))
            first.flush()
        finally:
            runtime_console._live_stream = original
        # Measured 5 with the guard in place (write: resolve, warn, value;
        # flush: resolve, forward) -- bounded.  Without it, unbounded.
        self.assertLessEqual(len(hops), 8)

        class _Hostile(io.StringIO):
            def write(self, value: str) -> int:
                raise OSError("the operator's window is gone too")

            def flush(self) -> None:
                raise OSError("and so is its flush")

        hostile = build_console_mirror(io.StringIO(), io.StringIO())
        hostile.stop_mirroring(_Hostile())
        self.assertEqual(hostile.write("swallowed\n"), len("swallowed\n"))
        hostile.flush()

    def test_flush_forwards_after_teardown_too_not_only_write(self):
        # pf-adversary T3: ruling `20260907_1441` names write() AND
        # flush(); only write() was pinned, so `flush()` could go back to
        # a bare `return` with the suite still green.
        flushed = []

        class _Counting(io.StringIO):
            def flush(self) -> None:
                flushed.append(True)
                super().flush()

        fallback = _Counting()
        mirror = build_console_mirror(io.StringIO(), io.StringIO())
        mirror.stop_mirroring(fallback)
        mirror.flush()
        self.assertTrue(flushed)

    def test_a_torn_down_mirror_reports_the_stream_it_now_writes_to(self):
        # pf-adversary F1: `console_safe()` asks what the stream being
        # written to can take.  After teardown that is the fallback; a
        # mirror still answering for its dead console lets a cp874 screen
        # take a utf-8 line, raise, and have ruling `1441`'s swallow eat
        # the evidence.
        class _Narrow(io.StringIO):
            encoding = "cp874"
            errors = "strict"

        class _Wide(io.StringIO):
            encoding = "utf-8"
            errors = "replace"

        mirror = build_console_mirror(_Wide(), io.StringIO())
        self.assertEqual(mirror.encoding, "utf-8")
        mirror.stop_mirroring(_Narrow())
        self.assertEqual(mirror.encoding, "cp874")
        self.assertEqual(mirror.errors, "strict")

    def test_a_mirror_reports_the_encoding_of_the_console_it_wraps(self):
        # COO ruling `20260907_1346`: `console_safe()` asks one question
        # -- what can the stream being written to actually take -- and a
        # constant cannot answer it.  A cp874 console must report cp874,
        # or the fold is computed for a screen that does not exist.
        class _Cp874Stream(io.StringIO):
            encoding = "cp874"
            errors = "backslashreplace"

        mirror = build_console_mirror(_Cp874Stream(), io.StringIO())
        self.assertEqual(mirror.encoding, "cp874")
        self.assertEqual(mirror.errors, "backslashreplace")

        class _Raising(io.StringIO):
            @property
            def encoding(self):
                raise ValueError("closed")

        # A property that raises would change dispatch on every print().
        falling_back = build_console_mirror(_Raising(), io.StringIO())
        self.assertEqual(falling_back.encoding, "utf-8")

    def test_nested_consoles_leave_the_process_exiting_zero(self):
        # The whole point, measured the only way that counts: a real
        # interpreter that opened two consoles, closed them out of order
        # and printed afterwards must exit 0.  Measured across three
        # commits: 120 before this PR's first commit, 0 from it on --
        # so this pins THAT commit, which reaches main only here,
        # because the gate closed `#1039` before it could land.
        script = (
            "import io, sys\n"
            "sys.path.insert(0, {src!r})\n"
            "from pathlib import Path\n"
            "from pirateforce_foundation.runtime_console import RuntimeConsole\n"
            "outer = RuntimeConsole(Path({tmp!r}) / 'outer', io.StringIO(),"
            " io.StringIO(), close_console_streams=False)\n"
            "inner = RuntimeConsole(Path({tmp!r}) / 'inner', io.StringIO(),"
            " io.StringIO(), close_console_streams=False)\n"
            "outer.close()\n"
            "inner.close()\n"
            "print('after both closes')\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable, "-c",
                    script.format(src=str(ROOT / "src"), tmp=tmp),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("after both closes", result.stdout)

if __name__ == "__main__":
    unittest.main()
