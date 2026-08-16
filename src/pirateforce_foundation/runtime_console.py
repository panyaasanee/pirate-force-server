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
            self._console.write(value)
            self._retained.write(value)
        return len(value)

    def flush(self) -> None:
        with self._lock:
            self._console.flush()
            self._retained.flush()


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
        sys.stdout = _Mirror(console_out, self._retained_out)
        sys.stderr = _Mirror(console_err, self._retained_err)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            current_out, current_err = sys.stdout, sys.stderr
            try:
                current_out.flush()
                current_err.flush()
            finally:
                sys.stdout = self._previous_out
                sys.stderr = self._previous_err
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
