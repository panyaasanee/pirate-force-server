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


_forwarding = threading.local()


def _active_forwards() -> set[int]:
    """Mirrors this thread is already forwarding through, by id().

    Thread-local on purpose: two threads writing through the same dead
    mirror are not a cycle, and must not silence each other.
    """
    ids = getattr(_forwarding, "ids", None)
    if ids is None:
        ids = set()
        _forwarding.ids = ids
    return ids


def _reported_text_attr(stream: object, name: str, default: str) -> str:
    """Report a wrapped stream's ``encoding``/``errors``, never raise.

    COO ruling `20260907_1346`: a mirror has no right to declare an
    encoding of its own -- it reports the encoding of the console stream
    it is writing through, because that is the single question
    ``console_safe()`` exists to answer ("what can the stream that is
    being written to actually take?").  A property that raises would
    change dispatch, so every failure lands on the default instead.
    """
    try:
        value = getattr(stream, name, None)
    except Exception:
        return default
    return value if isinstance(value, str) else default


class _Mirror(TextIO):
    """One process-wide stdout/stderr writing to a console and a file.

    After ``stop_mirroring`` the retained file is gone but the operator's
    window is not, so a torn-down mirror FORWARDS to its fallback rather
    than dropping (COO ruling `20260907_1441`).

    NOTE: Evidence therefore splits across two places, and whoever reads
    the retained file must know it: lines written AFTER the owning
    ``RuntimeConsole.close()`` reach the console/fallback and are NOT in
    that run's ``server_console_live.*.txt``.  The retained file is not
    the whole of what the operator saw.
    """

    def __init__(self, console: TextIO, retained: TextIO) -> None:
        self._console = console
        self._retained = retained
        self._detached = False
        self._fallback: TextIO | None = None
        self._warned = False
        self._lock = threading.RLock()

    def _reported_sink(self) -> object:
        """The stream `encoding`/`errors` are answering FOR.

        Ruling `1346` names the question as "what can the stream that is
        being written to actually take?", so after teardown the honest
        answer is the fallback, not the console this mirror has stopped
        writing to (pf-adversary F1: reporting the dead console lets
        `console_safe()` skip a fold the fallback needed, and ruling
        `1441`'s swallow then eats the UnicodeEncodeError -- the line is
        recorded nowhere, which is the scar ruling `1346` exists for).
        """
        with self._lock:
            if self._detached and self._fallback is not None:
                return self._fallback
            return self._console

    @property
    def encoding(self) -> str:
        return _reported_text_attr(self._reported_sink(), "encoding", "utf-8")

    @property
    def errors(self) -> str:
        # "replace", not "strict": a diagnostic that makes console_safe()
        # fold wider than the real console needs is the mirror-image of
        # the damage this property exists to prevent.
        return _reported_text_attr(self._reported_sink(), "errors", "replace")

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return bool(getattr(self._console, "isatty", lambda: False)())

    def fileno(self) -> int:
        return self._console.fileno()

    def _detached_target(self) -> tuple[TextIO | None, bool]:
        """Pick the live stream to forward to, and whether to warn first.

        Snapshotting under the lock and doing the I/O outside it is
        load-bearing: forwarding writes into ANOTHER mirror's lock, and
        stdout's and stderr's fallbacks can cross.  Holding our own lock
        across that hop is a lock-order inversion between two threads.
        """
        with self._lock:
            if self._fallback is None:
                return None, False
            target = _live_stream(self._fallback)
            warn = not self._warned
            self._warned = True
            return target, warn

    def _warn_once(self, target: TextIO) -> None:
        # Written straight to the fallback: `warnings` and `logging` are
        # both unreliable at interpreter shutdown and `logging` can route
        # straight back into this sink (COO ruling `20260907_1441`).
        try:
            target.write(
                "[FOUNDATION] runtime console torn down; later lines go to"
                " the console only and are NOT in this run's retained log\n"
            )
        except Exception:
            pass

    def _forward(self, value: str | None) -> None:
        active = _active_forwards()
        if id(self) in active:
            # A fallback chain looped back to us.  Dropping here is the
            # only way out that does not recurse until the stack ends.
            return
        active.add(id(self))
        try:
            target, warn = self._detached_target()
            if target is None:
                return
            if warn:
                self._warn_once(target)
            try:
                if value is None:
                    target.flush()
                else:
                    target.write(value)
            except Exception:
                pass
        finally:
            active.discard(id(self))

    def write(self, value: str) -> int:
        if not isinstance(value, str):
            raise TypeError("runtime console accepts text only")
        with self._lock:
            if not self._detached:
                self._console.write(value)
                self._retained.write(value)
                return len(value)
        self._forward(value)
        return len(value)

    def flush(self) -> None:
        with self._lock:
            if not self._detached:
                self._console.flush()
                self._retained.flush()
                return
        self._forward(None)

    def stop_mirroring(self, fallback: TextIO) -> None:
        """Detach from both sinks and forward everything later, forever.

        Called by ``RuntimeConsole.close()`` immediately BEFORE the
        retained file (and possibly the console) is closed.  A mirror can
        outlive its owner: when two consoles are nested, closing them out
        of order leaves ``sys.stdout`` pointing at the older mirror, and a
        mirror over a closed file turns every later ``print()`` into a
        ValueError -- at interpreter shutdown that is exit code 120, with
        no traceback naming this module.

        Dropping the text was the first fix and it was the wrong one
        (COO ruling `20260907_1441`): a dead mirror holds a stream that
        is still writable and chooses not to use it, so the operator's
        window goes silent with nobody able to say why.  Forwarding keeps
        the line on the screen; the one-shot warning above says out loud
        that the retained file stops here.
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
    so stays green with `_fold_line_breaking_controls` deleted, while a
    mirror over a utf-8 console does not.

    NOTE: ``encoding`` is NOT a parameter here and is NOT the mirror's own
    answer either: a mirror has no right to declare an encoding of its
    own, it REPORTS the encoding of the console stream it wraps (COO
    ruling `20260907_1346`, correcting the contract this docstring
    published at `#1022`).  So a caller that wants a cp874 answer passes
    a cp874 ``console``; over a stream that declares nothing the mirror
    falls back to utf-8/replace.

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
