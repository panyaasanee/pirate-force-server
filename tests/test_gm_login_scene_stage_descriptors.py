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

Why the fence matters even though POSIX hides it: `command_capture.py`'s own
docstring records the two Windows-gate closures (`#962`, `#970`) that a leaked
handle caused.  Here the consequence would be sharper still -- on Windows an
open handle on the temp file makes `os.replace(temp_path, path)` on the VERY
NEXT LINE raise `PermissionError`, so dropping line 736 would turn every GM
stage on the owner's own machine into a refusal, while every Linux round in
this project stayed green.

Two independent assertions per path, on purpose:

* the module ASKED for the close (recorded through a stand-in for the module's
  own `os` binding), which is a positive fact about this module;
* the descriptor is REALLY gone (`os.fstat` raises `EBADF`), which is a fact
  about the process and would still hold if the module were refactored to use
  `contextlib`, `os.closerange`, or a `finally`.

Known limit, inherited from `descriptors_opened_by` in `tests/pf_gm_capture_mocks.py`:
asking `os.fstat` about an fd NUMBER is a negative about a number the OS may
hand out again.  Nothing in these tests opens a descriptor between the close
and the assert in a single-threaded run, so the failure mode is a false RED,
never a false green.  A THREADED runner would need real bookkeeping; process
parallelism (`pytest-xdist`) is safe, because each worker has its own fd table.

The stand-ins here patch the MODULE ATTRIBUTE (`login_scene_stage.os`), not the
`os` module itself.  That is the difference from `descriptors_opened_by`, which
does `mock.patch.object(module.os, "open", ...)` -- and since `module.os is os`
for every module in this repository, its `module` parameter has no effect and
it patches the whole process (pf-adversary, round `i3evov`, D10).  Patching the
binding keeps the blast radius to the one module under test.
"""
from __future__ import annotations

import errno
import json
import os
import pathlib
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pirateforce_foundation.gm import login_scene_stage  # noqa: E402


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

    def assert_every_descriptor_released(self):
        self.assertEqual(
            len(self.opened),
            1,
            f"expected exactly one mkstemp descriptor, got {self.opened!r}",
        )
        fd = self.opened[0]
        # The process-level fact first, because it is the one that survives a
        # refactor of HOW the module closes; the recorder is the corroboration.
        with self.assertRaises(OSError) as raised:
            os.fstat(fd)
        self.assertEqual(
            raised.exception.errno,
            errno.EBADF,
            f"fd {fd} is still open after the call returned",
        )
        self.assertEqual(
            self.closed,
            [fd],
            "the module did not ask to close the descriptor it opened",
        )


class AtomicWriteReleasesItsDescriptorTests(_DescriptorCase):
    """Lines 733 and 736: the two closes in `_atomic_write_json`."""

    def test_the_success_path_closes_before_it_renames(self):
        path = self.tmp / "config" / "gm_login_scene.json"
        self.install()

        login_scene_stage._atomic_write_json(path, {"entries": {"GM_ONE": 1}})

        self.assertEqual(
            json.loads(path.read_text(encoding="ascii")), {"entries": {"GM_ONE": 1}}
        )
        self.assert_every_descriptor_released()

    def test_a_failure_before_the_rename_closes_and_leaves_no_temp_file(self):
        path = self.tmp / "config" / "gm_login_scene.json"
        self.install(fsync_error=OSError(errno.EIO, "injected fsync failure"))

        with self.assertRaises(OSError):
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

        login_scene_stage._restore_bytes(path, b'{"entries": {}}\n')

        self.assertEqual(path.read_bytes(), b'{"entries": {}}\n')
        self.assert_every_descriptor_released()

    def test_a_restore_that_fails_still_closes_and_still_does_not_raise(self):
        path = self.tmp / "gm_login_scene.json"
        path.write_bytes(b"replaced by a refusal\n")
        self.install(fsync_error=OSError(errno.EIO, "injected fsync failure"))

        # No `assertRaises`: this function must never raise over the top of the
        # refusal that called it.
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


class TheFenceCoversEverySiteTests(unittest.TestCase):
    """A fence that misses a site is worse than no fence: it reads as coverage.

    Counted from the module's own source rather than trusted, so a fifth
    `os.close(fd)` added later fails HERE -- with the count in the message --
    instead of landing unpinned the way these four did.
    """

    def test_the_module_has_exactly_the_four_close_sites_this_file_pins(self):
        source = pathlib.Path(login_scene_stage.__file__).read_text(encoding="utf-8")
        sites = [
            number
            for number, line in enumerate(source.splitlines(), start=1)
            if line.strip() == "os.close(fd)"
        ]
        self.assertEqual(
            len(sites),
            4,
            f"login_scene_stage.py has {len(sites)} `os.close(fd)` sites at lines "
            f"{sites}; this file pins four. Add a case for the new one.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
