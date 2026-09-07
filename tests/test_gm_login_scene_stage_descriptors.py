"""`gm/login_scene_stage.py`: every descriptor it opens is closed on every path.

Why this file exists, and why it is separate from `test_gm_login_scene_stage.py`:

`pf-adversary` (round `i3evov`, D6) measured that
`sed '736s/os.close(fd)/pass/' src/pirateforce_foundation/gm/login_scene_stage.py`
left `pytest -k "login_scene or stage"` at **391 passed**.  All four
`os.close(fd)` sites in that module -- 733 and 736 in `_atomic_write_json`, 770
and 773 in `_restore_bytes` -- were unpinned, so a refactor could drop any of
them and this project's whole test suite would agree.

CORRECTION, measured here rather than repeated: round `i3evov`'s round file
wrote that line 736 leaks one descriptor on every successful GM stage.  That
is FALSE.  The shipped module closes the descriptor on all four paths; what
was missing was the FENCE, not the close.  This file adds the fence and says
so, instead of quietly landing a "fix" for a bug that was never there.

Why the fence matters even though POSIX hides it: `tests/pf_gm_capture_mocks.py`
(line 72) records the two Windows-gate closures (`#962`, `#970`) that a leaked
handle caused.  Here the consequence would be sharper still -- on Windows an
open handle on the temp file makes `os.replace(temp_path, path)` on the VERY
NEXT LINE raise `PermissionError`, so dropping line 736 would turn every GM
stage on the owner's own machine into a refusal, while every Linux round in
this project stayed green.

WHAT EACH ASSERTION IS FOR, spelled out because the first version of this file
got it wrong in both directions (pf-adversary, round `s03veu`, D1 and D3).
Exactly ONE of the three enforces the property in the first line of this
docstring; the other two pin the MECHANISM this module happens to use today:

* PROPERTY -- the fd table of this process is unchanged across the call
  (`/proc/self/fd`, whole-table delta).  This is the only assertion here that
  is about descriptors at all rather than about statements: it survives a
  refactor to `contextlib`, `os.fdopen`, `os.closerange` or a `finally`, and it
  is the one that sees a descriptor opened by any call other than the module's
  own `mkstemp`.  The earlier version had no such assertion, so an inserted
  `os.dup(fd)` -- a live handle carried into `os.replace` on the next line,
  verbatim the disaster the paragraph above describes -- kept the file at
  `5 passed`.
* MECHANISM -- `os.fstat(fd)` raises `EBADF` for the ONE fd `mkstemp` returned.
  A negative about a number the OS may hand out again, and blind to every
  other descriptor.
* MECHANISM -- the module ASKED for the close, recorded through a stand-in for
  its own `os` binding: `self.closed == [fd]`.  This pins the LITERAL
  `os.close(fd)` statement.  Rewriting the module as
  `with os.fdopen(fd, "wb") as handle:` -- correct, and measured leak-free --
  turns this red, together with the site count below.  That is a deliberate,
  documented cost, NOT a bug report about your refactor: if you meet these red
  and the fd-table assertion GREEN, you changed how this module closes and the
  right response is to update this file on purpose, never to delete the
  property assertion that is still green.

Known limit of the two mechanism assertions, inherited from
`descriptors_opened_by` in `tests/pf_gm_capture_mocks.py`: asking `os.fstat`
about an fd NUMBER is a negative about a number the OS may hand out again.
Nothing in these tests opens a descriptor between the close and the assert in a
single-threaded run, and the fd-table snapshot is taken around the module call
alone, so the failure mode is a false RED, never a false green.  Both rest on
CPython refcounting closing the descriptors the test body itself opens
(`read_text`, `read_bytes`, `iterdir`) at the end of their expression --
measured, 25/25 green, but named here because it is an assumption and not a
guarantee (pf-adversary, round `s03veu`, D6).  A THREADED runner would need
real bookkeeping; process parallelism (`pytest-xdist`) is safe, because each
worker is a separate PROCESS with its own fd table.

The fd-table read is POSIX-only.  On a host without `/proc/self/fd` the
property assertion cannot run, and rather than pass quietly this file FAILS if
that happens on Linux -- a fence going silent must never look like a green.

The stand-ins here patch the MODULE ATTRIBUTE (`login_scene_stage.os`), not the
`os` module itself.  That is the difference from `descriptors_opened_by`, which
does `mock.patch.object(module.os, "open", ...)` -- and since `module.os is os`
for every module in this repository, its `module` parameter has no effect and
it patches the whole process (pf-adversary, round `i3evov`, D10).  Patching the
binding keeps the blast radius to the one module under test.
"""
from __future__ import annotations

import contextlib
import errno
import json
import os
import pathlib
import re
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pirateforce_foundation.gm import login_scene_stage  # noqa: E402

FD_TABLE = "/proc/self/fd"

# The module opens descriptors ONLY through these two spellings today. The site
# count below reads the source for them, so a third opening site -- the only way
# a leak can enter -- fails loudly instead of landing invisible to this file.
OPENING_SITE = re.compile(r"tempfile\.mkstemp\(|(?<!\w)os\.open\(")
CLOSING_SITE = "os.close(fd)"


def read_fd_table():
    """Every descriptor this process holds, as `{fd: target}`, or None off POSIX.

    The descriptor `os.listdir` itself uses to read the directory appears in
    its own listing; it points at `/proc/<pid>/fd` and is dropped here, so two
    reads taken around a call cancel it out. An fd that vanishes between the
    listing and the `readlink` is that same descriptor being closed under us.
    """
    try:
        names = os.listdir(FD_TABLE)
    except OSError:
        return None
    table = {}
    for name in names:
        try:
            number = int(name)
        except ValueError:
            continue
        try:
            target = os.readlink(f"{FD_TABLE}/{name}")
        except OSError:
            continue
        if target.startswith("/proc/") and target.endswith("/fd"):
            continue
        table[number] = target
    return table


class _NeverWatched:
    """Sentinel: this case called the module without watching the fd table."""


class _OsStandIn:
    """`login_scene_stage.os`, with `close` recorded and `fsync` optionally broken.

    Everything not named here delegates to the real `os`, so the module under
    test behaves normally -- this is a recorder with one injectable fault, not
    a fake filesystem.
    """

    def __init__(self, closed: list[int], fsync_error: BaseException | None = None):
        self._closed = closed
        self._fsync_error = fsync_error

    def __getattr__(self, name):
        return getattr(os, name)

    def close(self, fd: int) -> None:
        self._closed.append(fd)
        os.close(fd)

    def fsync(self, fd: int) -> None:
        if self._fsync_error is not None:
            raise self._fsync_error
        os.fsync(fd)


class _TempfileStandIn:
    """`login_scene_stage.tempfile`, recording every descriptor `mkstemp` hands out.

    The module opens its descriptors through `tempfile.mkstemp`, never through
    `os.open`, which is why `descriptors_opened_by` (built for
    `command_capture.py`) cannot see them at all.
    """

    def __init__(self, opened: list[int]):
        self._opened = opened

    def __getattr__(self, name):
        return getattr(tempfile, name)

    def mkstemp(self, *args, **kwargs):
        fd, name = tempfile.mkstemp(*args, **kwargs)
        self._opened.append(fd)
        return fd, name


class _DescriptorCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name)
        self.opened: list[int] = []
        self.closed: list[int] = []
        self.leaked = _NeverWatched

    def install(self, fsync_error: BaseException | None = None):
        """Point the module at the stand-ins for the duration of one test."""
        real_os = login_scene_stage.os
        real_tempfile = login_scene_stage.tempfile
        login_scene_stage.os = _OsStandIn(self.closed, fsync_error)
        login_scene_stage.tempfile = _TempfileStandIn(self.opened)

        def restore():
            login_scene_stage.os = real_os
            login_scene_stage.tempfile = real_tempfile

        self.addCleanup(restore)

    @contextlib.contextmanager
    def watching_the_fd_table(self):
        """Snapshot every descriptor this process holds around ONE module call.

        Wrapped around the call and nothing else, so descriptors the test body
        opens to check its own results are outside the window.
        """
        before = read_fd_table()
        try:
            yield
        finally:
            after = read_fd_table()
            if before is None or after is None:
                self.leaked = None
            else:
                self.leaked = {
                    number: target
                    for number, target in after.items()
                    if before.get(number) != target
                }

    def assert_no_descriptor_leaked(self):
        """THE PROPERTY. Everything else in this file pins a statement."""
        self.assertIsNot(
            self.leaked,
            _NeverWatched,
            "this case called the module outside `watching_the_fd_table()`, so "
            "the only leak-detecting assertion in this file never ran",
        )
        if self.leaked is None:
            self.assertFalse(
                sys.platform.startswith("linux"),
                f"{FD_TABLE} is unreadable on a Linux host: the one assertion "
                "here that can see a leaked descriptor just went silent. Fix "
                "the reader; do not weaken the fence.",
            )
            return
        self.assertEqual(
            self.leaked,
            {},
            "the call left descriptors open that it did not hold before: "
            f"{self.leaked!r}",
        )

    def assert_every_descriptor_released(self):
        # Property first: it is the only one of the three that sees a leak the
        # module did not open through its own `mkstemp`.
        self.assert_no_descriptor_leaked()
        self.assertEqual(
            len(self.opened),
            1,
            f"expected exactly one mkstemp descriptor, got {self.opened!r}",
        )
        fd = self.opened[0]
        with self.assertRaises(OSError) as raised:
            os.fstat(fd)
        self.assertEqual(
            raised.exception.errno,
            errno.EBADF,
            f"fd {fd} is still open after the call returned",
        )
        # MECHANISM PIN, see this file's docstring: a correct rewrite to
        # `os.fdopen`/`finally` turns this red with the fd table green.
        self.assertEqual(
            self.closed,
            [fd],
            "the module did not ask to close the descriptor it opened with a "
            "literal `os.close(fd)`; if the fd-table assertion above is green "
            "you refactored HOW it closes -- update this file deliberately",
        )


class AtomicWriteReleasesItsDescriptorTests(_DescriptorCase):
    """Lines 733 and 736: the two closes in `_atomic_write_json`."""

    def test_the_success_path_closes_before_it_renames(self):
        path = self.tmp / "config" / "gm_login_scene.json"
        self.install()

        with self.watching_the_fd_table():
            login_scene_stage._atomic_write_json(path, {"entries": {"GM_ONE": 1}})

        self.assertEqual(
            json.loads(path.read_text(encoding="ascii")), {"entries": {"GM_ONE": 1}}
        )
        self.assert_every_descriptor_released()

    def test_a_failure_before_the_rename_closes_and_leaves_no_temp_file(self):
        path = self.tmp / "config" / "gm_login_scene.json"
        self.install(fsync_error=OSError(errno.EIO, "injected fsync failure"))

        with self.watching_the_fd_table(), self.assertRaises(OSError):
            login_scene_stage._atomic_write_json(path, {"entries": {}})

        self.assertFalse(path.exists(), "a failed write must not create the file")
        self.assertEqual(
            sorted(p.name for p in (self.tmp / "config").iterdir()),
            [],
            "the temp file outlived the failure it was created for",
        )
        self.assert_every_descriptor_released()


class RestoreReleasesItsDescriptorTests(_DescriptorCase):
    """Lines 770 and 773: the two closes in `_restore_bytes`.

    `_restore_bytes` runs where something has ALREADY failed and swallows
    `OSError` by design, so a leak here is doubly invisible: no exception
    reaches a caller and no test that only reads the file can see it.
    """

    def test_restoring_a_file_closes_its_descriptor(self):
        path = self.tmp / "gm_login_scene.json"
        path.write_bytes(b"replaced by a refusal\n")
        self.install()

        with self.watching_the_fd_table():
            login_scene_stage._restore_bytes(path, b'{"entries": {}}\n')

        self.assertEqual(path.read_bytes(), b'{"entries": {}}\n')
        self.assert_every_descriptor_released()

    def test_a_restore_that_fails_still_closes_and_still_does_not_raise(self):
        path = self.tmp / "gm_login_scene.json"
        path.write_bytes(b"replaced by a refusal\n")
        self.install(fsync_error=OSError(errno.EIO, "injected fsync failure"))

        # No `assertRaises`: this function must never raise over the top of the
        # refusal that called it.
        with self.watching_the_fd_table():
            login_scene_stage._restore_bytes(path, b'{"entries": {}}\n')

        self.assertEqual(
            path.read_bytes(),
            b"replaced by a refusal\n",
            "a failed restore must not half-write the operator's file",
        )
        self.assertEqual(
            sorted(p.name for p in self.tmp.iterdir()),
            ["gm_login_scene.json"],
            "the temp file outlived the failed restore",
        )
        self.assert_every_descriptor_released()


class TheLeakDetectorItselfWorksTests(_DescriptorCase):
    """The fence's one property assertion, pointed at a leak on purpose.

    Without this, `read_fd_table` returning a constant -- an empty dict, the
    same dict twice, `None` -- leaves every test in this file green while
    detecting nothing, which is the exact failure mode round `s03veu` shipped.
    """

    def test_a_descriptor_left_open_inside_the_window_is_reported(self):
        handle, name = tempfile.mkstemp(dir=str(self.tmp), prefix=".probe.")
        self.addCleanup(os.unlink, name)
        with self.watching_the_fd_table():
            leaked_fd = os.dup(handle)
        os.close(handle)
        self.addCleanup(os.close, leaked_fd)

        if self.leaked is None:
            self.assertFalse(
                sys.platform.startswith("linux"),
                f"{FD_TABLE} is unreadable on a Linux host",
            )
            return
        self.assertIn(
            leaked_fd,
            self.leaked,
            "a descriptor opened inside the window and still open at the end "
            "of it was not reported: this file cannot see a leak",
        )

    def test_a_window_that_leaks_nothing_reports_nothing(self):
        with self.watching_the_fd_table():
            handle, name = tempfile.mkstemp(dir=str(self.tmp), prefix=".probe.")
            os.close(handle)
            os.unlink(name)

        if self.leaked is None:
            self.assertFalse(
                sys.platform.startswith("linux"),
                f"{FD_TABLE} is unreadable on a Linux host",
            )
            return
        self.assertEqual(
            self.leaked,
            {},
            f"the reader invented a leak that is not there: {self.leaked!r}",
        )


class TheFenceCoversEverySiteTests(unittest.TestCase):
    """A fence that misses a site is worse than no fence: it reads as coverage.

    Counted from the module's own source rather than trusted. The count that
    matters is of OPENING sites, because an opening site is the only way a leak
    can enter and it is the one thing the per-path assertions structurally
    cannot see (pf-adversary, round `s03veu`, D1: a fifth site that opened and
    never closed kept the earlier version of this file at `5 passed`).
    """

    def source(self):
        return pathlib.Path(login_scene_stage.__file__).read_text(encoding="utf-8")

    def test_the_module_has_exactly_the_two_opening_sites_this_file_pins(self):
        sites = [
            number
            for number, line in enumerate(self.source().splitlines(), start=1)
            if OPENING_SITE.search(line)
        ]
        self.assertEqual(
            len(sites),
            2,
            f"login_scene_stage.py opens descriptors at {len(sites)} sites "
            f"(lines {sites}); this file pins two, both `tempfile.mkstemp`. A "
            "new one is a new leak surface no test here covers: add a case.",
        )

    def test_the_four_literal_close_statements_are_still_there(self):
        """MECHANISM PIN. A correct refactor may legitimately change this.

        See this file's docstring: if this is red while every fd-table
        assertion is green, nothing leaked -- the module stopped closing with a
        literal `os.close(fd)`, and this number is to be updated on purpose.
        """
        sites = [
            number
            for number, line in enumerate(self.source().splitlines(), start=1)
            if line.strip() == CLOSING_SITE
        ]
        self.assertEqual(
            len(sites),
            4,
            f"login_scene_stage.py has {len(sites)} `{CLOSING_SITE}` sites at "
            f"lines {sites}; this file pins four.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
