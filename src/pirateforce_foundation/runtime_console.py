"""Visible runtime console with deterministic UTF-8 file mirrors.

Actual server invocations always show a Windows console.  Human-readable
stdout/stderr are mirrored to bounded per-run files while raw protocol logs
remain in the existing capture_v141 files.
"""
from __future__ import annotations

import atexit
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO


class _Mirror(TextIO):
    def __init__(self, console: TextIO, retained: TextIO) -> None:
        self._console = console
        self._retained = retained
        self._detached = False
        self._fallback: TextIO | None = None
        self._lock = threading.RLock()

    @property
    def encoding(self) -> str:
        return "utf-8"

    @property
    def errors(self) -> str:
        return "strict"

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return bool(getattr(self._console, "isatty", lambda: False)())

    def fileno(self) -> int:
        return self._console.fileno()

    def write(self, value: str) -> int:
        if not isinstance(value, str):
            raise TypeError("runtime console accepts text only")
        with self._lock:
            if self._detached:
                return len(value)
            self._console.write(value)
            self._retained.write(value)
        return len(value)

    def flush(self) -> None:
        with self._lock:
            if self._detached:
                return
            self._console.flush()
            self._retained.flush()

    def stop_mirroring(self, fallback: TextIO) -> None:
        """Stop writing to both sinks, without raising, forever.

        Called by ``RuntimeConsole.close()`` immediately BEFORE the
        retained file (and possibly the console) is closed.  A mirror can
        outlive its owner: when two consoles are nested, closing them out
        of order leaves ``sys.stdout`` pointing at the older mirror, and a
        mirror over a closed file turns every later ``print()`` into a
        ValueError -- at interpreter shutdown that is exit code 120, with
        no traceback naming this module.  Dropping the text is the lesser
        of the two harms: the process is already tearing its console down.
        """
        with self._lock:
            self._detached = True
            self._fallback = fallback


def _live_stream(stream: TextIO) -> TextIO:
    """Skip past mirrors that a nested owner already tore down.

    Restoring is a chain, not a single hop: with two consoles alive at
    once the inner one remembers the outer one's mirror as "previous".
    Closing them in either order must land on a stream that is still
    writable, so follow the fallback each dead mirror left behind.
    """
    seen: set[int] = set()
    while (
        isinstance(stream, _Mirror)
        and stream._detached
        and stream._fallback is not None
        and id(stream) not in seen
    ):
        seen.add(id(stream))
        stream = stream._fallback
    return stream


def build_console_mirror(console: TextIO, retained: TextIO) -> TextIO:
    """Return the object ``RuntimeConsole`` installs as stdout/stderr.

    Built over caller-owned streams: this opens no file, creates no
    directory and never touches ``sys``, so a test can drive the real
    mirror -- the one an operator reads through -- instead of a stand-in
    of its own making.  CORE-REQUEST-GM-064 (LANE-GM round `fx4p76`,
    chief queue item (4)) asked for exactly this door, because a test
    stream that encodes cp874 folds line-breaking controls for free and
    so stays green with `_fold_line_breaking_controls` deleted, while
    this mirror declares utf-8 and does not.

    The declared ``encoding`` is deliberately NOT a parameter here: it is
    `_Mirror`'s own decision, so the day it changes, every test built on
    this factory moves with it instead of pinning a copy of the old
    answer.

    ``RuntimeConsole.__init__`` is required to build its two mirrors
    through this function; `test_runtime_console.py` fails if it stops.
    """
    return _Mirror(console, retained)


class RuntimeConsole:
    """Own mirrored stdout/stderr for one actual server process."""

    def __init__(
        self, log_root: Path, console_out: TextIO, console_err: TextIO, *,
        close_console_streams: bool,
    ) -> None:
        log_root.mkdir(parents=True, exist_ok=True)
        self.log_root = log_root
        self.stdout_path = log_root / "server_console_live.out.txt"
        self.stderr_path = log_root / "server_console_live.err.txt"
        self._retained_out = self.stdout_path.open(
            "x", encoding="utf-8", newline="\n", buffering=1,
        )
        try:
            self._retained_err = self.stderr_path.open(
                "x", encoding="utf-8", newline="\n", buffering=1,
            )
        except BaseException:
            self._retained_out.close()
            self.stdout_path.unlink(missing_ok=True)
            raise
        self._console_out = console_out
        self._console_err = console_err
        self._close_console_streams = close_console_streams
        self._previous_out = sys.stdout
        self._previous_err = sys.stderr
        self._closed = False
        self._lock = threading.RLock()
        self._installed_out = build_console_mirror(
            console_out, self._retained_out,
        )
        self._installed_err = build_console_mirror(
            console_err, self._retained_err,
        )
        sys.stdout = self._installed_out
        sys.stderr = self._installed_err

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                self._installed_out.flush()
                self._installed_err.flush()
            finally:
                # Restore per stream, and only when the stream this
                # instance installed is still the one in place.  Handing
                # `_previous_out` back unconditionally hands a LATER
                # owner's stdout to an EARLIER owner's dead mirror.
                if sys.stdout is self._installed_out:
                    sys.stdout = _live_stream(self._previous_out)
                if sys.stderr is self._installed_err:
                    sys.stderr = _live_stream(self._previous_err)
                try:
                    # A substituted factory may return a plain stream:
                    # tearing the mirror down must never be the reason
                    # the retained files stay open forever, because
                    # `_closed` is already True and no retry can help.
                    for installed, previous in (
                        (self._installed_out, self._previous_out),
                        (self._installed_err, self._previous_err),
                    ):
                        stop = getattr(installed, "stop_mirroring", None)
                        if stop is not None:
                            stop(previous)
                finally:
                    self._retained_out.close()
                    self._retained_err.close()
                if self._close_console_streams:
                    self._console_out.close()
                    self._console_err.close()


def _windows_console_streams(title: str) -> tuple[TextIO, TextIO, bool]:
    """Show the inherited console or allocate one when launched headlessly."""
    if os.name != "nt":
        return sys.stdout, sys.stderr, False
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32.GetConsoleWindow.restype = ctypes.c_void_p
    window = kernel32.GetConsoleWindow()
    if not window:
        if not kernel32.AllocConsole():
            raise OSError(ctypes.get_last_error(), "AllocConsole failed")
        window = kernel32.GetConsoleWindow()
    if not window:
        raise RuntimeError("Windows console window is unavailable")
    kernel32.SetConsoleOutputCP(65001)
    kernel32.SetConsoleTitleW(str(title))
    # SW_SHOW=5.  This also reverses a legacy Start-Process -WindowStyle Hidden.
    user32.ShowWindow(window, 5)
    console_out = open(
        "CONOUT$", "w", encoding="utf-8", errors="replace",
        newline="\n", buffering=1,
    )
    console_err = open(
        "CONOUT$", "w", encoding="utf-8", errors="replace",
        newline="\n", buffering=1,
    )
    return console_out, console_err, True


def install_runtime_console(
    project_root: str | Path, capture_root: str | Path | None,
    db_path: str | Path, mode: str, *,
    console_streams=None,
) -> RuntimeConsole:
    """Install one visible console and one deterministic summary-log pair."""
    root = Path(project_root).resolve()
    if capture_root is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%fZ")
        log_root = root / "logs" / f"server_{stamp}_{os.getpid()}"
    else:
        log_root = Path(capture_root).resolve()
    title = f"Pirate Force Foundation Server | {mode} | {Path(db_path).name}"
    factory = console_streams or _windows_console_streams
    console_out, console_err, owned = factory(title)
    runtime = RuntimeConsole(
        log_root, console_out, console_err,
        close_console_streams=owned,
    )
    atexit.register(runtime.close)
    print(f"[FOUNDATION] visible console: {title}")
    print(f"[FOUNDATION] summary logs: {runtime.stdout_path} | {runtime.stderr_path}")
    return runtime
