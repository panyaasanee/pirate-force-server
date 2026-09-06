"""One shared `os.close` failure mock for the GM capture tests.

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

import os


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
