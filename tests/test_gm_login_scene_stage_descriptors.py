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

WHERE THE FENCE STANDS, and why it moved (pf-adversary, round `fx4p76`, D1).
The first two versions of this file watched the fd table around the two
PRIVATE helpers that already had an `os.close(fd)` in them -- the two places a
leak was least likely to be.  Everything an operator actually calls
(`stage_login_scene`, `restore_login_scene`, `claim_login_scene`, and the
`_write_entry` / `_write_entry_locked` / `_load_document` chain underneath
them) was covered by a source scan alone, and pf-adversary walked a probe that
holds a handle open across `os.replace` straight through it: inserted into
`_write_entry_locked` it left this file at `8 passed` while the process went
from 4 open descriptors to 9 over five stages.  So the window now goes around
the PUBLIC calls as well -- `TheOperatorFacingCallsLeakNothingTests` -- and
that class is the fence.  The helper classes stay because they say WHICH
statement broke; they are no longer the only thing watching.

WHAT EACH ASSERTION IS FOR, spelled out because the first version of this file
got it wrong in both directions (pf-adversary, round `s03veu`, D1 and D3).
Exactly ONE of the three enforces the property in the first line of this
docstring; the other two pin the MECHANISM this module happens to use today:

* PROPERTY -- the fd table of this process is unchanged across the call
  (`/proc/self/fd`, whole-table delta).  This is the only assertion here that
  is about descriptors at all rather than about statements: it survives a
  refactor of HOW the module closes -- measured on the `with os.fdopen(fd,
  "wb") as handle:` rewrite, where it stays GREEN while the two mechanism pins
  below go red -- and it is the one that sees a descriptor opened by any call
  other than the module's own `mkstemp`.  The earlier version had no such assertion, so an inserted
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

WHO WATCHES THE PROPERTY ASSERTION ITSELF (pf-adversary, round `fx4p76`, D2).
`TheLeakDetectorItselfWorksTests` used to read `self.leaked` directly, which
watched the READER and not the ASSERTION: a bare `return` at the top of
`assert_no_descriptor_leaked` left this file at `8 passed`, and so did that
`return` together with a real leak injected into the module.  Every case in
that class now calls `assert_no_descriptor_leaked()` itself and asserts what it
does -- raises on a leak, passes on a clean window, raises when a case forgot
the window at all.  A `return` at the top of it now fails the file.

THE SOURCE SCAN IS A TRIPWIRE, NOT THE FENCE.  `opening_call_sites()` parses
the module with `ast`, so it cannot be fooled by a comment or a docstring that
happens to spell `tempfile.mkstemp(` (pf-adversary, round `fx4p76`, D4: the
regex it replaces scanned those too, and a comment could turn this file red for
free).  It follows `from tempfile import mkstemp as _x`, `import io` /
`io.open`, a bare `open(...)`, and `_x = os.open` rebindings, because the regex
it replaces knew `os.open(` and `tempfile.mkstemp(` and nothing else -- four of
the five spellings pf-adversary tried walked past it.  It still cannot see a
descriptor opened through a name this file has never heard of, which is exactly
why the fd-table window around the public calls is the fence and this is the
tripwire that says "a new opening site landed, go look".

Known limit of the two mechanism assertions, inherited from
`descriptors_opened_by` in `tests/pf_gm_capture_mocks.py`: asking `os.fstat`
about an fd NUMBER is a negative about a number the OS may hand out again.
Nothing in these tests opens a descriptor between the close and the assert in a
single-threaded run, and the fd-table snapshot is taken around the module call
alone, so the failure mode is a false RED, never a false green.  Both rest on
CPython refcounting closing the descriptors the test body itself opens
(`read_text`, `read_bytes`, `iterdir`) at the end of their expression.  Named
here because it is an assumption and not a guarantee (pf-adversary, round
`s03veu`, D6); this file as it stands was run 25 times and was green 25/25.  A THREADED runner would need
real bookkeeping; `[PROPOSED]` process parallelism (`pytest-xdist`) is safe,
because each worker is a separate PROCESS with its own fd table -- REASONING,
not a measurement: `pytest-xdist` is not installed on this host, so nobody here
has run this file under it (pf-adversary, round `fx4p76`, D4's correction).

The fd-table read is POSIX-only.  On a host without `/proc/self/fd` the
property assertion cannot run, and rather than pass quietly this file FAILS if
that happens on Linux -- a fence going silent must never look like a green.
`test_a_table_that_could_not_be_read_fails_the_assertion_on_linux` is what
makes that sentence a measurement instead of a promise.

ON WINDOWS THE PROPERTY IS NOT MEASURED AT ALL, and this file will not pretend
otherwise (pf-adversary, round `da16dj`, D-2).  `read_fd_table` returns None
there, `assert_no_descriptor_leaked` takes its early return, and all of its
call sites become no-ops -- on `gate-windows.yml`, which is the gate this
project treats as authoritative and the only platform where the bug this file
exists for is fatal.  What IS covered on Windows is the CONSEQUENCE rather than
the descriptor: `test_a_rename_that_fails_removes_the_temp_file_and_raises`,
`test_a_rename_that_fails_while_restoring_leaves_the_file_as_it_was` and
`test_a_stage_whose_rename_fails_restores_and_leaks_nothing` inject the
`PermissionError` that an open handle causes there and assert the module
refuses cleanly, removes its temp file and leaves the operator's file alone.
That is a real property and it runs on every platform; it is NOT the same as
counting descriptors, and nobody should read it as such.  That sentence is
permanent: it is not to be deleted in a later round on the grounds that
everything here is green (COO `20260907_1245` section 4).

The question it used to leave open -- what measures the descriptor property
itself on Windows -- was put to COO in
`notes_to_chief/20260907_1211_LANE-GM-ASK-COO-what-measures-descriptors-on-windows.md`
and RULED ON in `notes_to_chief/20260907_1245_COO-DECISION-gm1211-windows-`
`measures-the-effect-LANE-GM.md`: NOTHING measures it there, and that is
accepted, because counting handles through the Windows API is a new tool built
for one test file.  What is measured there is the CONSEQUENCE, above.  The one
condition attached to accepting it is `UNMEASURED_ASSERTIONS`: on a host where
the table cannot be read, `assert_no_descriptor_leaked` appends the calling
case's id and returns, so "nobody looked" is an event in the run and not an
absence -- a no-op and a pass are otherwise the same colour in a test report,
which is how a tree with a real leak injected reached `27 passed`.
`TheUnmeasuredArmIsRecordedTests` pins all three directions of that: the row
appears when the reader returns None off Linux, it does NOT appear for a case
that merely forgot to open the window, and it does not appear on a window that
really was measured.  The ledger says nothing about descriptors; it says only
whether anyone looked.

The stand-ins here patch the MODULE ATTRIBUTE (`login_scene_stage.os`), not the
`os` module itself.  That is the difference from `descriptors_opened_by`, which
does `mock.patch.object(module.os, "open", ...)` -- and since `module.os is os`
for every module in this repository, its `module` parameter has no effect and
it patches the whole process (pf-adversary, round `i3evov`, D10).  Patching the
binding keeps the blast radius to the one module under test.
"""
from __future__ import annotations

import ast
import contextlib
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

FD_TABLE = "/proc/self/fd"

# Every time `assert_no_descriptor_leaked` returns WITHOUT having measured
# anything, it appends the id of the case that called it here.  The list exists
# so that "the fd table could not be read" is a recorded event and not an
# absence: on a host where the table is unreadable the assertion is a no-op,
# and a no-op and a pass are the same colour in a test report.  Read by
# `TheUnmeasuredArmIsRecordedTests`, which is the only thing in this file that
# can tell those two apart (COO ruling `20260907_1245`, answering LANE-GM's
# letter `20260907_1211`; raised by pf-adversary, round `da16dj`, D-2).
#
# NOT a substitute for the property.  Nothing in this list says a descriptor
# was or was not leaked; it says only that nobody looked.
UNMEASURED_ASSERTIONS: list[str] = []

# Attribute spellings that hand back a descriptor.  `mkdtemp` is deliberately
# absent: it makes a directory and returns a name, never an fd.
OPENING_ATTRIBUTES = {
    ("os", "open"),
    ("io", "open"),
    ("tempfile", "mkstemp"),
    ("tempfile", "NamedTemporaryFile"),
    ("tempfile", "TemporaryFile"),
}
# The same functions reached by a bare name.  `open` is here because it is a
# builtin nobody has to import.
OPENING_BARE_NAMES = {"open"}
OPENING_MODULES = {"os", "io", "tempfile"}
CLOSING_SITE = "os.close(fd)"

# Scenes the committed catalog knows, matching `test_gm_login_scene_stage.py`.
# Literals on purpose: a catalog that lost them should fail loudly here.
GM_ACCOUNT = "GM_ONE"
TEST_STAGE = 278
PORT_ROYAL = 1


def opening_call_sites(source: str):
    """Line numbers where `source` calls something that returns a descriptor.

    Parsed, not grepped, for two reasons pf-adversary measured on the regex
    this replaces (round `fx4p76`): a comment or docstring spelling
    `tempfile.mkstemp(` made the site count red for free (D4), and four of five
    real spellings walked past it (D1).

    WHAT IT FOLLOWS, and what it does not.  It follows `from os import open as
    _x`, `import os as _o`, `_o = os` and `_x = os.open`.  It is measured BLIND
    to `getattr(os, "open")`, `os.pipe`, `os.dup`, `os.dup2`, `os.memfd_create`,
    `select.epoll`, `socket.socket`, `pathlib.Path(p).open`, `path.open`,
    `codecs.open`, `dbm.open`, `io.FileIO`, `io.open_code`, `builtins.open`,
    `subprocess.Popen(stdout=PIPE)`, and any call through a class or instance
    attribute (pf-adversary, round `da16dj`, D-4: 25 of 30 spellings tried).
    `TheFenceCoversEverySiteTests` pins that blindness as a list, so widening
    this function is a deliberate edit rather than a silent one.  This is the
    reason the file calls it a TRIPWIRE: the fence is the fd-table window.

    Returns `[(line, spelling)]` sorted by line.
    """
    tree = ast.parse(source)
    aliased: dict[str, str] = {}
    modules: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in OPENING_MODULES:
                    modules[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module in OPENING_MODULES:
            for alias in node.names:
                if (node.module, alias.name) in OPENING_ATTRIBUTES:
                    aliased[alias.asname or alias.name] = (
                        f"{node.module}.{alias.name}"
                    )
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute):
            value = node.value
            if isinstance(value.value, ast.Name):
                module = modules.get(value.value.id, value.value.id)
                if (module, value.attr) in OPENING_ATTRIBUTES:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            aliased[target.id] = f"{module}.{value.attr}"
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
            if node.value.id in OPENING_MODULES:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        modules[target.id] = node.value.id
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            module = modules.get(func.value.id, func.value.id)
            if (module, func.attr) in OPENING_ATTRIBUTES:
                sites.append((node.lineno, f"{module}.{func.attr}"))
        elif isinstance(func, ast.Name):
            if func.id in OPENING_BARE_NAMES:
                sites.append((node.lineno, func.id))
            elif func.id in aliased:
                sites.append((node.lineno, aliased[func.id]))
    return sorted(sites)


def read_fd_table():
    """Every descriptor this process holds, as `{fd: target}`, or None off POSIX.

    The descriptor `os.listdir` itself uses to read the directory appears in
    its OWN listing.  An earlier version of this function dropped it by target
    (`/proc/<pid>/fd`), and pf-adversary (round `fx4p76`, D3) measured that
    deleting those two lines changed nothing.  Measured here rather than
    defended: `os.listdir` closes that descriptor before it returns, so by the
    time `readlink` asks about the number it is already gone -- three trials,
    every one of them `ENOENT` for exactly one name and no `/proc/<pid>/fd`
    target resolved at all.  The `OSError` arm below is therefore what drops
    it, the filter was dead code, and dead code in a fence reads as protection
    that is not there.  `TheReaderItselfTests` pins the arm that really does
    the work.
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
        table[number] = target
    return table


class _NeverWatched:
    """Sentinel: this case called the module without watching the fd table."""


class _OsStandIn:
    """`login_scene_stage.os`, with `close` recorded and faults injectable.

    Everything not named here delegates to the real `os`, so the module under
    test behaves normally -- this is a recorder with injectable faults, not a
    fake filesystem.  The three faults are the three ways the shipped module
    can fail after it already holds a descriptor: `fsync` raising, `write`
    coming back short without raising, and `replace` refusing (which is what
    Windows does when a handle is still open on the temp file).
    """

    def __init__(
        self,
        closed: list[int],
        fsync_error: BaseException | None = None,
        short_write: bool = False,
        replace_error: BaseException | None = None,
    ):
        self._closed = closed
        self._fsync_error = fsync_error
        self._short_write = short_write
        self._replace_error = replace_error

    def __getattr__(self, name):
        return getattr(os, name)

    def close(self, fd: int) -> None:
        self._closed.append(fd)
        os.close(fd)

    def fsync(self, fd: int) -> None:
        if self._fsync_error is not None:
            raise self._fsync_error
        os.fsync(fd)

    def write(self, fd: int, data):
        if self._short_write:
            return 0
        return os.write(fd, data)

    def replace(self, src, dst):
        if self._replace_error is not None:
            raise self._replace_error
        return os.replace(src, dst)


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

    def install(self, **faults):
        """Point the module at the stand-ins for the duration of one test."""
        real_os = login_scene_stage.os
        real_tempfile = login_scene_stage.tempfile
        login_scene_stage.os = _OsStandIn(self.closed, **faults)
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
            # Off Linux this method has just decided nothing.  Say so out loud
            # instead of returning into a green: the entry below is the only
            # difference between "measured, clean" and "did not look".  The
            # sentinel arm above returns by RAISING, so a case that forgot the
            # window can never land here and be filed as a platform limit.
            UNMEASURED_ASSERTIONS.append(self.id())
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

    def test_a_short_write_refuses_and_takes_the_temp_file_with_it(self):
        """The `count <= 0` arm: a full disk, the case the loop was copied for.

        Never executed by any test before round `da16dj` (pf-adversary, round
        `s03veu`, D5), so the branch that turns a half-written config into a
        refusal was itself unmeasured.
        """
        path = self.tmp / "config" / "gm_login_scene.json"
        self.install(short_write=True)

        with self.watching_the_fd_table(), self.assertRaises(OSError) as raised:
            login_scene_stage._atomic_write_json(path, {"entries": {"GM_ONE": 1}})

        self.assertIn("short write", str(raised.exception))
        self.assertFalse(path.exists(), "a short write must not create the file")
        self.assertEqual(
            sorted(p.name for p in (self.tmp / "config").iterdir()),
            [],
            "the temp file outlived the short write it was created for",
        )
        self.assert_every_descriptor_released()

    def test_a_rename_that_fails_removes_the_temp_file_and_raises(self):
        """The arm after the close: `os.replace` refusing.

        This is the Windows failure this whole file is about -- an open handle
        makes `os.replace` raise `PermissionError` -- and it too had never been
        executed.  The descriptor is already closed by the time it runs, so
        what is measured here is that the temp file does not survive.
        """
        path = self.tmp / "config" / "gm_login_scene.json"
        self.install(replace_error=PermissionError(errno.EACCES, "injected replace"))

        with self.watching_the_fd_table(), self.assertRaises(PermissionError):
            login_scene_stage._atomic_write_json(path, {"entries": {"GM_ONE": 1}})

        self.assertFalse(path.exists(), "a failed rename must not create the file")
        self.assertEqual(
            sorted(p.name for p in (self.tmp / "config").iterdir()),
            [],
            "the temp file outlived the rename that failed",
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

    def test_a_short_write_while_restoring_is_swallowed_and_changes_nothing(self):
        """The short-write arm of `_restore_bytes` -- never executed before.

        The raise is caught by this function's own `except OSError: return`,
        which is the design: a restore must not raise over the refusal that
        called it.  So its MESSAGE is unobservable here and this case does not
        pin it -- pf-adversary (round `da16dj`, D-8) measured that rewording it
        keeps this file green, and that is a consequence of the swallow, not a
        gap to paper over with a source-text pin.  What must NOT happen is the
        operator's file being left half-written, and that is what this measures.
        """
        path = self.tmp / "gm_login_scene.json"
        path.write_bytes(b"replaced by a refusal\n")
        self.install(short_write=True)

        with self.watching_the_fd_table():
            login_scene_stage._restore_bytes(path, b'{"entries": {}}\n')

        self.assertEqual(
            path.read_bytes(),
            b"replaced by a refusal\n",
            "a short write while restoring must not half-write the file",
        )
        self.assertEqual(
            sorted(p.name for p in self.tmp.iterdir()),
            ["gm_login_scene.json"],
            "the temp file outlived the short write",
        )
        self.assert_every_descriptor_released()

    def test_a_rename_that_fails_while_restoring_leaves_the_file_as_it_was(self):
        """The `os.replace` arm of `_restore_bytes` -- never executed before."""
        path = self.tmp / "gm_login_scene.json"
        path.write_bytes(b"replaced by a refusal\n")
        self.install(replace_error=PermissionError(errno.EACCES, "injected replace"))

        with self.watching_the_fd_table():
            login_scene_stage._restore_bytes(path, b'{"entries": {}}\n')

        self.assertEqual(
            path.read_bytes(),
            b"replaced by a refusal\n",
            "a failed rename while restoring must not touch the file",
        )
        self.assertEqual(
            sorted(p.name for p in self.tmp.iterdir()),
            ["gm_login_scene.json"],
            "the temp file outlived the rename that failed",
        )
        self.assert_every_descriptor_released()

    def test_restoring_an_absence_removes_the_file_and_opens_nothing(self):
        """`original_bytes is None` -- the "there was no entry" arm.

        Never executed before round `da16dj`.  It is the one path through
        `_restore_bytes` that must NOT open a descriptor at all, so
        `assert_every_descriptor_released` (which demands exactly one) is the
        wrong assertion here and the property assertion is the right one.
        """
        path = self.tmp / "gm_login_scene.json"
        path.write_bytes(b"a file that should not survive\n")
        self.install()

        with self.watching_the_fd_table():
            login_scene_stage._restore_bytes(path, None)

        self.assertFalse(path.exists(), "restoring an absence must remove the file")
        self.assert_no_descriptor_leaked()
        self.assertEqual(
            self.opened, [], "the absence path must not open a descriptor at all"
        )
        self.assertEqual(
            self.closed, [], "nothing was opened, so nothing may be closed"
        )


class TheOperatorFacingCallsLeakNothingTests(_DescriptorCase):
    """THE FENCE. The fd table around the calls an operator actually makes.

    pf-adversary (round `fx4p76`, D1): the helper classes above watch two
    private functions that already close their descriptor.  A probe holding a
    handle open across `os.replace` inside `_write_entry_locked` -- which is
    neither of them -- left this file at `8 passed` while the process grew from
    4 open descriptors to 9 over five stages.  These cases watch the public
    entry points end to end, with the REAL `os` and `tempfile` (no stand-ins),
    so every descriptor any part of the chain opens is inside the window.
    """

    def setUp(self):
        super().setUp()
        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [GM_ACCOUNT]}), encoding="utf-8"
        )
        self.config_path = self.tmp / "config" / "gm_login_scene.json"
        # One call before the window, so `claim` and `restore` have an entry
        # to work on.
        # KNOWN HOLE, measured, not argued away (pf-adversary, round
        # `da16dj`, D-1): a descriptor opened ONCE PER PROCESS -- the realistic
        # shape, an `lru_cache`d reader that keeps its handle -- is in `before`
        # for every window here and cancels out. A leak guarded by
        # `if not _held:` inserted into `_write_entry_locked` keeps this file
        # at green; the same leak on every call turns four of these cases red.
        # An earlier version of this comment claimed the five-stage case below
        # covered it. It does not: its window wraps the loop, not this line.
        self.stage(TEST_STAGE)

    def stage(self, scene_id):
        return login_scene_stage.stage_login_scene(
            GM_ACCOUNT,
            scene_id,
            gm_accounts_config_path=str(self.accounts_path),
            config_path=str(self.config_path),
        )

    def test_a_successful_stage_leaks_nothing(self):
        with self.watching_the_fd_table():
            result = self.stage(PORT_ROYAL)

        self.assertTrue(result.staged, f"the fixture stopped staging: {result!r}")
        self.assert_no_descriptor_leaked()

    def test_a_refused_stage_leaks_nothing(self):
        with self.watching_the_fd_table():
            result = login_scene_stage.stage_login_scene(
                "DECKHAND",
                PORT_ROYAL,
                gm_accounts_config_path=str(self.accounts_path),
                config_path=str(self.config_path),
            )

        self.assertFalse(result.staged, "a non-GM account must not stage")
        self.assert_no_descriptor_leaked()

    def test_a_restore_leaks_nothing(self):
        with self.watching_the_fd_table():
            restored = login_scene_stage.restore_login_scene(
                GM_ACCOUNT,
                None,
                gm_accounts_config_path=str(self.accounts_path),
                config_path=str(self.config_path),
            )

        self.assertTrue(restored, "the fixture stopped restoring")
        self.assert_no_descriptor_leaked()

    def test_a_claim_leaks_nothing(self):
        with self.watching_the_fd_table():
            claimed = login_scene_stage.claim_login_scene(
                GM_ACCOUNT, config_path=str(self.config_path)
            )

        self.assertEqual(claimed, TEST_STAGE, "the fixture stopped claiming")
        self.assert_no_descriptor_leaked()

    def test_a_stage_whose_rename_fails_restores_and_leaks_nothing(self):
        """The only case here that reaches `_restore_bytes` from a public call.

        pf-adversary (round `da16dj`, D-3): every other case in this class
        walks the success path, so `restore_login_scene(account, None)` reaches
        `_atomic_write_json` and NEVER `_restore_bytes` -- the class docstring's
        "end to end" was true of one path only.  This one injects the Windows
        failure the whole file is about (`os.replace` refusing) into the public
        call, which sends `_write_entry_locked` down its `REASON_WRITE_FAILED`
        arm and through `_restore_bytes` on the way out.

        It is the one case here that installs the stand-ins; two temp files are
        opened on this path, so only the PROPERTY assertion applies.
        """
        self.install(replace_error=PermissionError(errno.EACCES, "injected"))

        with self.watching_the_fd_table():
            result = self.stage(PORT_ROYAL)

        self.assertFalse(result.staged, "a failed rename must not report staged")
        self.assert_no_descriptor_leaked()
        self.assertGreaterEqual(
            len(self.opened),
            2,
            "this case is meant to walk BOTH _atomic_write_json and "
            f"_restore_bytes; it opened {self.opened!r}",
        )
        self.assertEqual(
            sorted(self.closed),
            sorted(self.opened),
            "every descriptor opened on the refusal path must be closed",
        )

    def test_five_stages_in_one_window_do_not_grow_the_fd_table(self):
        """The shape pf-adversary's probe was measured in: five stages, one window.

        A leak of one descriptor per call is arithmetic here, so an fd number
        the OS happens to reuse cannot hide it.
        """
        with self.watching_the_fd_table():
            for _ in range(5):
                self.stage(PORT_ROYAL)

        self.assert_no_descriptor_leaked()


class TheLeakDetectorItselfWorksTests(_DescriptorCase):
    """The property ASSERTION, pointed at a leak on purpose.

    pf-adversary (round `fx4p76`, D2): the earlier version of this class read
    `self.leaked` directly and never called `assert_no_descriptor_leaked`, so
    it watched the reader and left the assertion itself unguarded -- a bare
    `return` at the top of that method kept this file at `8 passed`, and so did
    that `return` plus a real leak injected into the module.  Every case here
    now goes through the assertion, which is the path all four per-path cases
    above take.
    """

    def test_a_descriptor_left_open_inside_the_window_fails_the_assertion(self):
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
        with self.assertRaises(AssertionError) as raised:
            self.assert_no_descriptor_leaked()
        self.assertIn(
            str(leaked_fd),
            str(raised.exception),
            "the assertion failed without naming the descriptor that leaked",
        )

    def test_a_window_that_leaks_nothing_passes_the_assertion(self):
        with self.watching_the_fd_table():
            handle, name = tempfile.mkstemp(dir=str(self.tmp), prefix=".probe.")
            os.close(handle)
            os.unlink(name)

        # No `assertRaises`: a clean window must not be reported as a leak, or
        # the fence would be a false red on every path.
        self.assert_no_descriptor_leaked()

    def test_a_table_that_could_not_be_read_fails_the_assertion_on_linux(self):
        """The `None` arm's Linux guard, which nothing pinned until `da16dj`.

        pf-adversary (round `da16dj`, D-5): deleting the `assertFalse(...)`
        from that arm and leaving a bare `return` kept this file at
        `24 passed`, so the docstring sentence "a fence going silent must never
        look like a green" was itself an unmeasured claim.
        """
        if not sys.platform.startswith("linux"):
            return
        self.leaked = None
        with self.assertRaises(AssertionError) as raised:
            self.assert_no_descriptor_leaked()
        self.assertIn("unreadable on a Linux host", str(raised.exception))

    def test_a_case_that_forgot_the_window_fails_the_assertion(self):
        """The sentinel arm: never watching must not read as never leaking."""
        self.assertIs(self.leaked, _NeverWatched, "setUp stopped arming the sentinel")
        with self.assertRaises(AssertionError) as raised:
            self.assert_no_descriptor_leaked()
        self.assertIn("outside `watching_the_fd_table()`", str(raised.exception))


class TheUnmeasuredArmIsRecordedTests(_DescriptorCase):
    """A host that could not look must not report the same colour as a host that did.

    COO ruling `20260907_1245`, answering this lane's letter `20260907_1211`,
    which pf-adversary forced in round `da16dj` (D-2).  The ruling accepts that
    nothing on Windows can count this process's descriptors and sets one price
    for accepting it: the RUN has to say so, not just the docstring.  The
    finding being paid was `27 passed` on a tree with a real descriptor leak
    injected -- green, on the one platform where that leak is fatal.

    These three cases are about the LEDGER, not about descriptors.  Nothing
    here can tell you whether anything leaked.
    """

    @contextlib.contextmanager
    def a_host_that_cannot_read_its_fd_table(self):
        """`read_fd_table()` returning None the way a non-POSIX host makes it.

        The table path is moved to a name that does not exist, so the None
        comes back out of the reader's own `except OSError` arm -- the line a
        Windows host takes -- instead of being assigned to `self.leaked` by
        hand.  `sys.platform` moves with it because the two are not
        independent here: a LINUX host that cannot read the table is a broken
        reader and has to stay red, which is what
        `test_a_table_that_could_not_be_read_fails_the_assertion_on_linux`
        pins.  Both are restored on the way out, including on a failure.

        HALF OF THIS IS REASONING, NOT MEASUREMENT, and that half is named on
        purpose.  What is measured: when the reader returns None and the host
        is not Linux, the early return is reached and recorded.  What is NOT
        measured: what a real Windows host does.  No Windows host has run this
        -- there is none in this project's reach -- and there the None comes
        from `/proc/self/fd` not existing rather than from a path this test
        invented.  Do not upgrade this sentence later because the case is
        green; green here is not a Windows measurement (COO `1245` section 4).
        """
        global FD_TABLE
        real_table, real_platform = FD_TABLE, sys.platform
        FD_TABLE = str(self.tmp / "there-is-no-fd-table-on-this-host")
        sys.platform = "win32"
        try:
            yield
        finally:
            FD_TABLE = real_table
            sys.platform = real_platform

    def test_a_host_that_cannot_read_the_table_records_that_nothing_was_measured(self):
        """The case COO asked for: a real leak, a green assertion, a ledger row.

        The descriptor opened inside the window is deliberately still open when
        the assertion runs.  On this host the assertion would catch it; with
        the table unreadable it does not, and passes.  That pass is exactly the
        `27 passed` pf-adversary reported, reproduced on purpose -- so the row
        this leaves behind is the whole point of the case.
        """
        before = len(UNMEASURED_ASSERTIONS)
        with self.a_host_that_cannot_read_its_fd_table():
            with self.watching_the_fd_table():
                handle, name = tempfile.mkstemp(dir=str(self.tmp), prefix=".probe.")
            self.addCleanup(os.unlink, name)
            self.addCleanup(os.close, handle)
            self.assertIsNone(
                self.leaked,
                "the reader read a table it was told does not exist, so this "
                "case is no longer simulating the platform it claims to",
            )
            # Passes, with a descriptor left open. That is the defect, staged.
            self.assert_no_descriptor_leaked()
        self.assertEqual(
            UNMEASURED_ASSERTIONS[before:],
            [self.id()],
            "the assertion decided nothing and left no trace of deciding "
            "nothing, so a reader of this run cannot tell it from a pass",
        )

    def test_a_case_that_forgot_the_window_is_not_filed_as_a_platform_limit(self):
        """The two ways of not measuring must not be laundered into each other.

        A case that never opened the window is a BUG IN THE CASE and stays a
        failure; only the platform arm is allowed to record and return.  If the
        ledger row were appended before the sentinel check, this file would
        start excusing its own broken cases on every non-Linux runner.
        """
        before = len(UNMEASURED_ASSERTIONS)
        with self.a_host_that_cannot_read_its_fd_table():
            self.assertIs(self.leaked, _NeverWatched, "setUp stopped arming the sentinel")
            with self.assertRaises(AssertionError) as raised:
                self.assert_no_descriptor_leaked()
        self.assertIn("outside `watching_the_fd_table()`", str(raised.exception))
        self.assertEqual(
            UNMEASURED_ASSERTIONS[before:],
            [],
            "a case that forgot the window was filed as a platform limit",
        )

    def test_the_ledger_grows_exactly_when_the_table_could_not_be_read(self):
        """Both directions, on whatever host is running, with no early return.

        Deliberately not guarded by platform: on a POSIX host this is the case
        that kills an unconditional append (a ledger that grows on every call
        records nothing), and on a host without the table it is the case that
        kills a missing one.  Whichever host runs it, one of the two mutants
        dies here.
        """
        before = len(UNMEASURED_ASSERTIONS)
        with self.watching_the_fd_table():
            handle, name = tempfile.mkstemp(dir=str(self.tmp), prefix=".probe.")
            os.close(handle)
            os.unlink(name)
        expected = [self.id()] if self.leaked is None else []
        self.assert_no_descriptor_leaked()
        self.assertEqual(
            UNMEASURED_ASSERTIONS[before:],
            expected,
            "the ledger and the reader disagree about whether this window was "
            "measured at all",
        )


class TheReaderItselfTests(unittest.TestCase):
    """`read_fd_table` reads what it claims to and drops what it claims to.

    pf-adversary (round `fx4p76`, D3): deleting the two lines that dropped the
    reader's own directory descriptor by target left this file at `8 passed`.
    The answer is not a cleverer pin for those lines -- it is that they were
    dead.  `os.listdir` has already closed that descriptor when `readlink` runs
    (measured: one name per read, always `ENOENT`), so the `OSError` arm drops
    it and the filter never fired.  The lines are gone; these cases pin what
    replaced them.
    """

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = pathlib.Path(holder.name)

    def off_posix(self):
        """True where `/proc/self/fd` cannot exist. Per-method, never in setUp.

        Not `skipTest`: a new skip marker is a red preflight row in this
        project (`[skips]`), and more to the point every other case in this
        file passes trivially off-POSIX rather than skipping -- see
        `assert_no_descriptor_leaked`.  These three follow the same rule so the
        Windows gate reads one story, not two.
        """
        return not sys.platform.startswith("linux")

    def test_the_listing_names_a_descriptor_that_is_gone_before_it_is_resolved(self):
        """The reader's own dirfd, and the arm that actually drops it.

        Without the `try`/`except OSError` around `readlink`, this is not a
        silent mis-count: every call raises and the whole file errors out.
        """
        if self.off_posix():
            return
        names = os.listdir(FD_TABLE)
        vanished = []
        for name in names:
            try:
                os.readlink(f"{FD_TABLE}/{name}")
            except OSError as exc:
                vanished.append((name, exc.errno))
        self.assertEqual(
            len(vanished),
            1,
            "exactly one name in the listing -- the descriptor `os.listdir` "
            f"used to read it -- should be gone by `readlink`; got {vanished!r}",
        )
        self.assertEqual(vanished[0][1], errno.ENOENT)

    def test_the_reader_reports_no_descriptor_pointing_at_the_fd_directory(self):
        """CHARACTERISATION, not a pin: nothing here can make this red.

        Said plainly because the version of this file that round `fx4p76`
        shipped presented an assertion of exactly this shape as if it guarded
        the filter it was written for.  It does not: the entry never reaches
        the table on any code path, with or without a filter.  It is kept to
        record the fact the docstring above rests on.
        """
        if self.off_posix():
            return
        table = read_fd_table()
        self.assertIsNotNone(table, f"{FD_TABLE} is unreadable on a Linux host")
        self.assertEqual(
            {
                number: target
                for number, target in table.items()
                if target.startswith("/proc/") and target.endswith("/fd")
            },
            {},
        )

    def test_the_reader_resolves_a_descriptor_that_is_actually_open(self):
        """A reader that returns a constant must not look like a clean table."""
        if self.off_posix():
            return
        handle, name = tempfile.mkstemp(dir=str(self.tmp), prefix=".probe.")
        self.addCleanup(os.unlink, name)
        self.addCleanup(os.close, handle)
        table = read_fd_table()
        self.assertIsNotNone(table)
        self.assertEqual(
            table.get(handle),
            name,
            "the reader did not report an open descriptor, so an empty table "
            "would be indistinguishable from a clean one",
        )


class TheFenceCoversEverySiteTests(unittest.TestCase):
    """A fence that misses a site is worse than no fence: it reads as coverage.

    Counted from the module's own source rather than trusted, and parsed rather
    than grepped (see the docstring's tripwire paragraph). The count that
    matters is of OPENING sites, because an opening site is the only way a leak
    can enter and it is the one thing the per-path assertions structurally
    cannot see (pf-adversary, round `s03veu`, D1: a fifth site that opened and
    never closed kept the earlier version of this file at `5 passed`).
    """

    def source(self):
        return pathlib.Path(login_scene_stage.__file__).read_text(encoding="utf-8")

    def test_the_module_has_exactly_the_two_opening_sites_this_file_pins(self):
        sites = opening_call_sites(self.source())
        self.assertEqual(
            [spelling for _, spelling in sites],
            ["tempfile.mkstemp", "tempfile.mkstemp"],
            f"login_scene_stage.py opens descriptors at {len(sites)} sites "
            f"({sites}); this file pins two, both `tempfile.mkstemp`. A new one "
            "is a new leak surface: add a case to "
            "`TheOperatorFacingCallsLeakNothingTests` if a public call reaches "
            "it, and update this list on purpose.",
        )

    def test_the_scanner_is_not_a_spelling_and_ignores_comments(self):
        """The five spellings that walked past the regex, plus the free red.

        pf-adversary (round `fx4p76`, D1 and D4) measured these against the
        regex this replaces: four of the six CALLS opened a descriptor it never
        saw, and the comment and the docstring -- neither of them a call --
        made the file red for nothing.
        """
        source = (
            "import io\n"
            "import os\n"
            "import tempfile\n"
            "from tempfile import mkstemp as _mkstemp\n"
            "_lowlevel_open = os.open\n"
            "# a comment that spells tempfile.mkstemp( and os.open(\n"
            "def f(path):\n"
            '    """A docstring spelling tempfile.mkstemp( too."""\n'
            "    a = _mkstemp(dir=path)\n"
            "    b = open(path)\n"
            "    c = io.open(path)\n"
            "    d = _lowlevel_open(path, os.O_RDONLY)\n"
            "    e = os.open(path, os.O_RDONLY)\n"
            "    g = tempfile.mkstemp(dir=path)\n"
            "    return a, b, c, d, e, g\n"
        )
        self.assertEqual(
            [spelling for _, spelling in opening_call_sites(source)],
            [
                "tempfile.mkstemp",
                "open",
                "io.open",
                "os.open",
                "os.open",
                "tempfile.mkstemp",
            ],
        )

    def test_the_scanner_does_not_count_mkdtemp_which_opens_nothing(self):
        """`mkdtemp` returns a name, not a descriptor. `os.fdopen` wraps one."""
        source = (
            "import os\n"
            "import tempfile\n"
            "def f(path, fd):\n"
            "    a = tempfile.mkdtemp(dir=path)\n"
            "    b = os.fdopen(fd, 'wb')\n"
            "    return a, b\n"
        )
        self.assertEqual(opening_call_sites(source), [])

    def test_the_spellings_this_scanner_is_measured_blind_to(self):
        """Recorded as a list, not defended (pf-adversary, round `da16dj`, D-4).

        An earlier version of the case above said `path.open()` "opens
        nothing".  That was false -- `pathlib.Path.open` hands back a real
        descriptor; the scanner simply cannot see it.  Every spelling here
        opens one and is missed.  If you widen `opening_call_sites`, this list
        goes red and you shorten it on purpose, which is the only way a known
        hole stops being a forgotten one.
        """
        blind = (
            "getattr(os, 'open')(p, 0)",
            "os.pipe()",
            "os.dup(3)",
            "os.dup2(3, 4)",
            "select.epoll()",
            "socket.socket()",
            "pathlib.Path(p).open()",
            "p.open()",
            "codecs.open(p)",
            "io.FileIO(p)",
        )
        for spelling in blind:
            source = (
                "import codecs\n"
                "import io\n"
                "import os\n"
                "import pathlib\n"
                "import select\n"
                "import socket\n"
                "def f(p):\n"
                f"    return {spelling}\n"
            )
            with self.subTest(spelling=spelling):
                self.assertEqual(opening_call_sites(source), [])

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
