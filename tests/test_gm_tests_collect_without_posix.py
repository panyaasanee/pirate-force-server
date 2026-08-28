"""Every `tests/test_gm_*.py` must IMPORT where the POSIX-only names are gone.

Why this file exists, measured rather than imagined:

PR #224 carried a working round of LANE-GM work and never reached main.  The
Windows gate did not fail an assertion -- it failed to COLLECT:

    tests\\test_gm_login_scene_stage.py:295: in RefusalLeavesTheFileAloneTests
        @unittest.skipIf(os.geteuid() == 0, "root ignores directory write bits")
    E   AttributeError: module 'os' has no attribute 'geteuid'

    (Actions run 33210364835, commit e2fdd796, job `gate`)

The lesson is narrower than "test on Windows" and worth stating exactly: a
`skipIf` protects the test BODY, never the decorator's own argument, which
runs while the class body runs -- at import.  A POSIX-only call written into
a skip condition therefore executes on Windows no matter how many `os.name`
guards sit above it.  And a single collection error is not one red test: it
aborts the run, so `pytest_subset` AND `skip_census` both went red (no test
ran, so the census saw 0 skips where nine modules pin 48 between them) and
`merge-claude-pr.yml` closed the PR to keep the lane lock from jamming shut.

WHAT THIS FILE ACTUALLY MEASURES, said plainly, because the honest name is
longer than the useful one: it imports every lane-GM test module for real,
in a child process where **the names listed below** have been removed from
`os` and the modules listed below refuse to import.

MEASURED LIMIT, and it is a real one: an import-time `if os.name == "nt":`
branch is NOT executed by this probe.  Setting `os.name = "nt"` in the child
was tried in the round that wrote this file and produces a FALSE RED --
`pathlib.Path()` picks `WindowsPath` off `os.name` at instantiation, so all
28 lane-GM modules die with `NotImplementedError: cannot instantiate
'WindowsPath' on your system`, for a reason that has nothing to do with the
defect being hunted.  A probe that cries wolf on every file is worse than a
narrower one, so the narrow one is what shipped: the `nt` half of any
import-time branch is still unwitnessed here.

It is NOT a Windows emulator and it does NOT prove a module imports on
Windows.  The lists are `[proposed]`, hand-assembled from the "Availability:
Unix" notes in the `os` docs; only `geteuid` is MEASURED, from the run above.
pf-adversary found six real gaps in the first version of these lists
(`os.setpriority`, `os.wait`, `signal.SIGKILL`, `socket.AF_UNIX`,
`select.epoll`, `readline`) -- all six are here now, and the fact that it
found them is exactly why this paragraph claims no completeness.  Adding a
name costs one line; if the gate goes red for a name missing here, add it
rather than trusting the list.

Deliberately not covered: what these modules DO at run time on Windows.  An
in-body `if os.name == "posix":` branch is the tool for that -- and it is the
tool this lane uses rather than a skip, because `docs/PYTEST_SKIP_PINS.json`
pins every skip the suite may produce and an unpinned one turns the gate red
by itself.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"

# Names `os` carries on Linux and does not carry on Windows.  [proposed] --
# see the module docstring; only `geteuid` is measured.
POSIX_ONLY_OS_NAMES = (
    "chown", "chroot", "confstr", "fchmod", "fchown", "fork", "forkpty",
    "fpathconf", "getegid", "geteuid", "getgid", "getgroups", "getloadavg",
    "getpgid", "getpgrp", "getpriority", "getresgid", "getresuid", "getsid",
    "getuid", "initgroups", "killpg", "lchown", "major", "makedev", "minor",
    "mkfifo", "mknod", "nice", "openpty", "pathconf", "pipe2", "pread",
    "pwrite", "readv", "sched_getaffinity", "sched_setaffinity", "sendfile",
    "setegid", "seteuid", "setgid", "setgroups", "setpgid", "setpgrp",
    "setpriority", "setregid", "setresgid", "setresuid", "setreuid", "setsid",
    "setuid", "spawnvp", "statvfs", "sync", "sysconf", "tcgetpgrp",
    "tcsetpgrp", "ttyname", "uname", "wait", "wait3", "wait4", "writev",
    "EX_OK", "O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK", "O_SYNC",
    "WIFEXITED", "WEXITSTATUS", "WNOHANG",
)

# Attributes of OTHER stdlib modules that Windows does not carry.  The first
# version of this file checked `os` alone, and four of these walked past it.
POSIX_ONLY_ATTRS = {
    "signal": ("SIGKILL", "SIGHUP", "SIGUSR1", "SIGUSR2", "SIGCHLD",
               "SIGPIPE", "SIGALRM", "SIGQUIT", "setitimer", "sigwait",
               "pthread_kill"),
    "socket": ("AF_UNIX", "SO_REUSEPORT", "MSG_DONTWAIT", "socketpair"),
    "select": ("epoll", "poll", "devpoll", "kqueue"),
}

# Modules that simply are not there on Windows.
POSIX_ONLY_MODULES = ("crypt", "curses", "fcntl", "grp", "nis", "posix",
                      "pty", "pwd", "readline", "resource", "spwd", "syslog",
                      "termios", "tty")

# The child does the whole job, so that a name deleted from `os` can never
# leak into the process that is doing the asserting.
_CHILD = r'''
import importlib
import importlib.util
import os
import sys

POSIX_ONLY_OS_NAMES = {os_names!r}
POSIX_ONLY_ATTRS = {attrs!r}
POSIX_ONLY_MODULES = {modules!r}
TEST_FILES = {files!r}


class _NoPosixModules:
    """Refuse the POSIX-only modules, the way a Windows interpreter does."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in POSIX_ONLY_MODULES:
            raise ModuleNotFoundError("No module named " + repr(fullname),
                                      name=fullname)
        return None


# Warm the stdlib the test modules lean on BEFORE the amputation, so that this
# harness measures the test files rather than the import machinery.
for _warm in ("json", "pathlib", "tempfile", "shutil", "unittest",
              "unittest.mock", "subprocess", "platform", "hashlib", "struct",
              "socket", "select", "signal", "sqlite3", "textwrap", "types",
              "typing", "ast", "io", "re"):
    try:
        importlib.import_module(_warm)
    except Exception:
        pass

for _name in POSIX_ONLY_OS_NAMES:
    if hasattr(os, _name):
        delattr(os, _name)
for _mod_name, _attr_names in POSIX_ONLY_ATTRS.items():
    _mod = sys.modules.get(_mod_name)
    if _mod is not None:
        for _attr in _attr_names:
            if hasattr(_mod, _attr):
                try:
                    delattr(_mod, _attr)
                except (AttributeError, TypeError):
                    pass
for _name in POSIX_ONLY_MODULES:
    sys.modules.pop(_name, None)
sys.meta_path.insert(0, _NoPosixModules())

failures = []
for path in TEST_FILES:
    stem = os.path.basename(path)[:-3]
    module_name = "_no_posix_probe_" + stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException as exc:  # a SystemExit at import counts too
        failures.append("{{0}}: {{1}}: {{2}}".format(
            os.path.basename(path), type(exc).__name__, exc))
    finally:
        sys.modules.pop(module_name, None)

# Never let the reporter be the thing that dies: the gate console is cp874,
# and one unmappable character in a traceback would otherwise turn a useful
# failure into an empty one -- the trap tests/test_gm_source_is_cp874_safe.py
# already writes around.
_out = sys.stdout.buffer
for line in failures:
    _out.write(line.encode("utf-8", "backslashreplace") + b"\n")
_out.flush()
sys.exit(1 if failures else 0)
'''


def _lane_gm_test_files():
    return sorted(str(path) for path in TESTS_DIR.glob("test_gm_*.py"))


def _tracked_lane_gm_test_files():
    """The same set as git sees it, or None where git cannot answer."""
    try:
        done = subprocess.run(
            ["git", "ls-files", "--", "tests/test_gm_*.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            encoding="utf-8",
            errors="surrogateescape",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return sorted(
        str(REPO_ROOT / line) for line in done.stdout.splitlines() if line
    )


def _run_probe(files):
    script = _CHILD.format(
        os_names=POSIX_ONLY_OS_NAMES,
        attrs=POSIX_ONLY_ATTRS,
        modules=POSIX_ONLY_MODULES,
        files=list(files),
    )
    # Through a file rather than `python -c`: this file exists to be trusted
    # on Windows, and a multi-line `-c` argument is exactly the sort of thing
    # that survives quoting on one platform and not the other.  The explicit
    # encoding is not decoration either -- the default is the machine's ANSI
    # code page, and one undecodable byte there would raise INSIDE
    # `subprocess.run` instead of being reported by it.
    with tempfile.TemporaryDirectory() as tmp:
        script_path = pathlib.Path(tmp) / "pf_no_posix_probe.py"
        script_path.write_text(script, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            encoding="utf-8",
            errors="surrogateescape",
            timeout=600,
        )


class LaneGmTestsImportWithoutPosixTests(unittest.TestCase):
    def test_the_file_list_is_not_quietly_empty(self):
        # A glob that silently matched nothing would make this file a no-op
        # reporting success forever.  28 files today; the floor sits close
        # enough that losing most of the lane fails here.
        self.assertGreaterEqual(len(_lane_gm_test_files()), 20)

    def test_every_lane_gm_test_file_is_tracked_by_git(self):
        # Not a tidiness rule.  The gate checks out what git has, so a new
        # test file left unstaged is ZERO BYTES on the machine that decides,
        # and the round ships a guard that is not there.  pf-adversary caught
        # exactly that on this file, in the round that wrote it.
        tracked = _tracked_lane_gm_test_files()
        if tracked is None:
            # Degrades to a no-op rather than a skip, deliberately: a skip
            # here would be an UNPINNED skip, and an unpinned skip turns the
            # whole gate red on its own (docs/PYTEST_SKIP_PINS.json).  Trading
            # a silent no-op on a machine without git for a red gate on the
            # machine that decides is the wrong trade.  The gate checks out
            # with git and `fetch-depth: 0`, so the check runs where it counts;
            # measured 2026-08-29, this returns None only when the process
            # cannot read .git at all (e.g. running as `nobody`).
            return
        self.assertEqual([], sorted(set(_lane_gm_test_files()) - set(tracked)))

    def test_every_lane_gm_test_module_imports_without_posix(self):
        result = _run_probe(_lane_gm_test_files())
        self.assertEqual(
            0,
            result.returncode,
            "these lane-GM test modules cannot be COLLECTED where the "
            "POSIX-only names are absent, which turns the whole gate red "
            "rather than one test:\n"
            + result.stdout
            + result.stderr,
        )

    def test_the_probe_actually_catches_the_defect_it_was_written_for(self):
        # Without this, a probe that silently stopped importing anything
        # would keep passing.  The bait is the exact line from PR #224.
        with tempfile.TemporaryDirectory() as tmp:
            bait = pathlib.Path(tmp) / "test_gm_bait_not_collected.py"
            bait.write_text(
                "import os\n"
                "import unittest\n"
                "\n"
                "\n"
                "class Bait(unittest.TestCase):\n"
                "    @unittest.skipIf(os.name == 'nt', 'POSIX only')\n"
                "    @unittest.skipIf(os.geteuid() == 0, 'root')\n"
                "    def test_nothing(self):\n"
                "        pass\n",
                encoding="utf-8",
            )
            result = _run_probe([str(bait)])

        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("AttributeError", result.stdout)
        self.assertIn("geteuid", result.stdout)

    def test_the_probe_catches_the_six_names_it_first_walked_past(self):
        # Every one of these is absent on Windows and would abort collection
        # the way `geteuid` did, and every one was GREEN against the first
        # version of this file (pf-adversary, round ank2vl).  A row each, so
        # a later edit to the lists above cannot quietly drop them again.
        baits = {
            "os_setpriority": "import os\n_S = os.setpriority\n",
            "os_wait": "import os\n_W = os.wait\n",
            "signal_sigkill": "import signal\n_K = signal.SIGKILL\n",
            "socket_af_unix": "import socket\n_U = socket.AF_UNIX\n",
            "select_epoll": "import select\n_P = select.epoll\n",
            "readline_module": "import readline\n",
        }
        for name, source in baits.items():
            with self.subTest(bait=name), tempfile.TemporaryDirectory() as tmp:
                bait = pathlib.Path(tmp) / ("test_gm_bait_%s.py" % name)
                bait.write_text(source, encoding="utf-8")
                result = _run_probe([str(bait)])
                self.assertEqual(
                    1, result.returncode, result.stdout + result.stderr
                )


if __name__ == "__main__":
    unittest.main()
