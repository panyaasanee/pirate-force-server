"""Shared fakes for the GM capture tests: one `os.close` failure mock,
one descriptor spy, and two streams that tell the truth about their encoding.

Not a test module (no `test_` prefix, nothing collected): a helper the three
GM capture test files import, the same way they share `pf_preconditions`.

Why it exists in one place instead of three copies: the three files each had
their own copy of this function for one round, and `pf-adversary` (round
`lkwmkp`, D3) showed the copies were unguarded -- deleting `real_close(fd)`
from the `test_gm_command_dispatch.py` copy left the whole suite green on
Linux and turned two tests red plus one error under a Windows emulation,
which is exactly the failure the guard test was written to make impossible.
One definition, one guard (`test_the_close_failure_helper_leaves_no_
descriptor_open` in `tests/test_gm_command_capture.py`), no copy that the
guard does not cover.
"""
from __future__ import annotations

import contextlib
import io
import os
from unittest import mock


def close_that_really_closes_then_fails(message: str):
    """`os.close` side effect that releases the descriptor, then reports failure.

    A `side_effect=OSError(...)` alone never closes the real descriptor. On
    Linux that leak is invisible -- an open handle blocks neither `unlink`
    nor a directory removal -- so the suite stayed green here while the
    Windows gate went RED twice on exactly these tests (`pirate-force-server`
    #926 run 34024390383 and #937 run 34029288153, both "6 failed ... 3
    errors"; six tests in that branch mocked `os.close`). Windows keeps a
    file locked while any handle on it is open and CPython's `os.open` does
    not pass `FILE_SHARE_DELETE`, so the leaked descriptor made
    `command_capture._best_effort_unlink` fail with a sharing violation:
    every one of those cases reported `CaptureFileNotVerifiedRemoved`
    instead of the failure the test asked for, and the still-open handle
    then broke the `TemporaryDirectory` cleanup registered in `setUp`.

    Closing for real first is also the more faithful model: `close()`
    consumes the descriptor even when it reports an error (which is exactly
    why `command_capture._capture_raw` never retries it), so a test that
    keeps the descriptor alive is testing a state the code under test can
    never be in.
    """
    real_close = os.close

    def _close(fd: int) -> None:
        real_close(fd)
        raise OSError(message)

    return _close


@contextlib.contextmanager
def descriptors_opened_by(module):
    """Record every descriptor ``module.os.open`` hands out, for one block.

    Extracted from `test_the_close_failure_helper_leaves_no_descriptor_open`
    so the three descriptor tests share ONE spy instead of three copies --
    the same reason `close_that_really_closes_then_fails` lives here (round
    `lkwmkp`, D3: the copy the guard did not cover was the copy that broke).

    Why a test needs this at all: `command_capture._capture_raw` closes its
    descriptor inside two guarded `try: os.close(fd) except OSError: pass`
    branches, and on POSIX an `unlink` succeeds while a descriptor is still
    open. So a cleanup test that asserts only `leftover == []` passes with
    the descriptor leaked -- measured, round `wxh2tw` (M37/M39): deleting
    either `os.close(fd)` left `tests/test_gm_command_capture.py` at 56
    passed. On Windows that leaked handle locks the capture file for the
    life of the process, which is the asymmetry that closed `#962`/`#970`
    in the other direction: the platform, not a test, was doing the work.

    Known limit (inherited from the test this came out of): asking
    `os.fstat` about an fd NUMBER is a negative about a number the OS may
    hand out again. Nothing opens a descriptor between the close and the
    assert in a single-threaded run, so this can produce a false RED, never
    a false green -- under `pytest-xdist` it would need real bookkeeping.
    """
    opened: list[int] = []
    real_open = os.open

    def spy_open(*args, **kwargs):
        fd = real_open(*args, **kwargs)
        opened.append(fd)
        return fd

    with mock.patch.object(module.os, "open", side_effect=spy_open):
        yield opened


class Cp874Stream(io.StringIO):
    """A stream that tells the TRUTH about what it can carry.

    `io.StringIO` has no `encoding` at all, so `console_safe` treats it as
    able to carry anything and every fold it performs goes unexercised --
    which is how three mutants survived their first review (pf-adversary,
    round `wxh2tw`, N5). A subclass that only SETS `encoding = "cp874"`
    without raising is the same trap one step further in: it exercises the
    fold but still accepts whatever the fold missed. A real operator
    console on this project is `cp874:strict`, and it raises.
    """

    encoding = "cp874"

    def write(self, text):
        text.encode(self.encoding)  # a real console raises here, so do we
        return super().write(text)


class Utf8Stream(io.StringIO):
    """A stream that announces `utf-8`, which production's really does.

    `runtime_console._Mirror.encoding` is a hardcoded `"utf-8"` property and
    `app.py` installs it as `sys.stderr`, so this -- not cp874 -- is what
    `console_safe` is asked about at runtime. It matters for the line-break
    fold: on a cp874 stream `console_safe` folds `U+0085` anyway, because
    cp874 cannot encode it, so a test written against cp874 alone passes
    with the fold deleted (round `wxh2tw`, mutant A06). Here the character
    is carryable, so only the fold can stop it.
    """

    encoding = "utf-8"

    def write(self, text):
        text.encode(self.encoding)
        return super().write(text)
