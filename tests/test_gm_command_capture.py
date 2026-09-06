"""GM-002: raw GM_RunGMCommandVital capture sink writes bytes untouched."""
from __future__ import annotations

import contextlib
import io
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import struct

from pirateforce_foundation.gm import command_capture
from pirateforce_foundation.gm.command_capture import (
    GM_RUN_GM_COMMAND_VITAL_ID,
    CaptureFileNotVerifiedRemoved,
    capture_raw_gm_command,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_gm_capture_mocks import close_that_really_closes_then_fails  # noqa: E402


@contextlib.contextmanager
def _o_binary_removed(module_os):
    """Make ``os.O_BINARY`` absent for the block, on EVERY platform.

    The "flags unchanged when O_BINARY is absent" test below used to open
    with ``assertFalse(hasattr(os, "O_BINARY"))`` -- a statement about the
    HOST rather than about the code under test. It holds on this Linux
    cloud clone and is false on windows-latest, which is where this
    project's trusted gate runs: `pirate-force-server#962` was closed by
    the gate with exactly that assertion red (`AssertionError: True is not
    false`, `tests\\test_gm_command_capture.py:269` and
    `tests\\test_gm_commands.py:417` -- the whole of that run's `2 failed`).

    Simulating the absence instead keeps the pin's teeth on both platforms:
    the branch under test is `getattr(os, "O_BINARY", 0)`'s FALLBACK, and
    the only honest way to reach it on a machine that has the flag is to
    take the flag away for the duration. `command_capture.os` IS the stdlib
    `os` module, so this deletes and restores a module attribute -- safe
    here because unittest runs these serially, and restored in `finally`
    even if the body raises.
    """
    had = hasattr(module_os, "O_BINARY")
    saved = getattr(module_os, "O_BINARY", None)
    if had:
        delattr(module_os, "O_BINARY")
    try:
        yield
    finally:
        if had:
            setattr(module_os, "O_BINARY", saved)


def _wstring(text: str) -> bytes:
    # 0x48 tag + uint32le byte count + payload (corrected 2026-09-02;
    # PF_A2_STRING_WIRE_TAG_DELTA.tsv rows 6266/6267/6279/6280).
    payload = text.encode("utf-16-le")
    return bytes((0x48,)) + struct.pack("<I", len(payload)) + payload


def _nested_body(f10: int, f14: int, f18: int, s1: str, s2: str) -> bytes:
    return (
        bytes([0x0B, 1])
        + bytes([0x14]) + struct.pack("<I", f10)
        + bytes([0x14]) + struct.pack("<I", f14)
        + bytes([0x0B, f18])
        + _wstring(s1)
        + _wstring(s2)
    )


class GmCommandCaptureTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "capture"

    def test_writes_a_file_and_returns_its_path(self):
        out = capture_raw_gm_command(
            b"\x12\x34/warp 1", "panya", capture_root=self.root, now_ts=0
        )
        self.assertTrue(out.is_file())
        self.assertEqual(out.parent, self.root)

    def test_hex_dump_and_header_carry_the_raw_bytes_verbatim(self):
        raw = bytes(range(20))
        out = capture_raw_gm_command(raw, "panya", capture_root=self.root, now_ts=0)
        text = out.read_text(encoding="utf-8")
        self.assertIn(f"0x{GM_RUN_GM_COMMAND_VITAL_ID:04X}", text)
        self.assertIn("length=20", text)
        # every byte value must appear as a two-digit hex pair in the dump
        for b in raw:
            self.assertIn(f"{b:02x}", text)

    def test_two_captures_from_different_accounts_do_not_collide(self):
        out1 = capture_raw_gm_command(b"a", "panya", capture_root=self.root, now_ts=0)
        out2 = capture_raw_gm_command(b"b", "attended_test", capture_root=self.root, now_ts=0)
        self.assertNotEqual(out1, out2)

    def test_account_name_is_sanitized_in_the_filename(self):
        out = capture_raw_gm_command(
            b"x", "weird/../name", capture_root=self.root, now_ts=0
        )
        self.assertEqual(out.parent, self.root)
        self.assertNotIn("..", out.name)
        self.assertNotIn("/", out.name)

    def test_rejects_non_bytes_raw(self):
        with self.assertRaises(TypeError):
            capture_raw_gm_command("not bytes", "panya", capture_root=self.root)

    def test_rejects_empty_account_name(self):
        with self.assertRaises(ValueError):
            capture_raw_gm_command(b"x", "", capture_root=self.root)

    def test_same_account_same_second_captures_do_not_overwrite_each_other(self):
        # pf-adversary finding: two commands from one account landing in the
        # same wall-clock second must never silently overwrite each other.
        out1 = capture_raw_gm_command(
            b"first-command-bytes", "panya", capture_root=self.root, now_ts=1000.0
        )
        out2 = capture_raw_gm_command(
            b"second-command-bytes-DIFFERENT",
            "panya",
            capture_root=self.root,
            now_ts=1000.4,
        )
        self.assertNotEqual(out1, out2)
        text1 = out1.read_text(encoding="utf-8")
        text2 = out2.read_text(encoding="utf-8")
        self.assertNotEqual(text1, text2)
        self.assertIn("length=19", text1)  # len(b"first-command-bytes")
        self.assertIn("length=30", text2)  # len(b"second-command-bytes-DIFFERENT")

    def test_many_same_second_captures_from_one_account_all_survive(self):
        paths = [
            capture_raw_gm_command(
                bytes([i]), "panya", capture_root=self.root, now_ts=1000.0
            )
            for i in range(25)
        ]
        self.assertEqual(len(set(paths)), 25)
        for i, path in enumerate(paths):
            self.assertIn(f"length=1", path.read_text(encoding="utf-8"))
            self.assertIn(f"{i:02x}", path.read_text(encoding="utf-8"))

    def test_account_name_sanitizer_stays_pure_ascii_and_bounded(self):
        out = capture_raw_gm_command(
            b"x", "ปัญญา" + "a" * 100, capture_root=self.root, now_ts=0
        )
        self.assertTrue(out.name.isascii())
        self.assertLessEqual(len(out.name), 40 + len("_0x51E9.txt") + len("20000101T000000Z_"))

    def test_account_name_cannot_forge_extra_header_lines(self):
        # a newline in account_name must not let it inject a fake "account="
        # or "#" line into the capture file's header.
        out = capture_raw_gm_command(
            b"x",
            "evil\naccount=fake_injected\n# forged line",
            capture_root=self.root,
            now_ts=0,
        )
        text = out.read_text(encoding="utf-8")
        header_lines = text.split("\n\n", 1)[0].splitlines()
        account_lines = [line for line in header_lines if "account=" in line]
        self.assertEqual(len(account_lines), 1)
        forged_lines = [line for line in header_lines if line == "# forged line"]
        self.assertEqual(forged_lines, [])

    def test_account_name_all_non_ascii_falls_back_to_unnamed(self):
        out = capture_raw_gm_command(b"x", "账号测试", capture_root=self.root, now_ts=0)
        self.assertIn("unnamed", out.name)

    def test_decode_section_reports_a_well_formed_presence_zero_payload(self):
        out = capture_raw_gm_command(
            bytes([0x0B, 0]), "panya", capture_root=self.root, now_ts=0
        )
        text = out.read_text(encoding="utf-8")
        self.assertIn("decode: presence=0", text)

    def test_decode_section_reports_a_well_formed_nested_body(self):
        raw = _nested_body(11, 22, 3, "warp", "1 100 200")
        out = capture_raw_gm_command(raw, "panya", capture_root=self.root, now_ts=0)
        text = out.read_text(encoding="utf-8")
        self.assertIn("decode: presence=1", text)
        self.assertIn("field_0x10=11", text)
        self.assertIn("field_0x14=22", text)
        self.assertIn("field_0x18=3", text)
        self.assertIn('string_0x1c="warp"', text)
        self.assertIn('string_0x38="1 100 200"', text)

    def test_decode_section_reports_failure_without_losing_the_raw_bytes(self):
        raw = bytes([0xFF, 0xFF, 0xFF])
        out = capture_raw_gm_command(raw, "panya", capture_root=self.root, now_ts=0)
        text = out.read_text(encoding="utf-8")
        self.assertIn("decode: FAILED", text)
        for b in raw:
            self.assertIn(f"{b:02x}", text)

    def test_decoded_string_cannot_forge_extra_header_lines(self):
        # RE-088's two wide strings come straight from client-controlled
        # bytes -- a newline inside one must not inject a fake header line,
        # same guarantee already held for account_name.
        raw = _nested_body(1, 2, 3, "warp\n# forged line", "ok")
        out = capture_raw_gm_command(raw, "panya", capture_root=self.root, now_ts=0)
        text = out.read_text(encoding="utf-8")
        header_lines = text.split("\n\n", 1)[0].splitlines()
        forged_lines = [line for line in header_lines if line == "# forged line"]
        self.assertEqual(forged_lines, [])

    # ----- pf-adversary (round 50x5xt, verify-pass addendum): bounded ------
    # ----- collision-suffix loop, never an infinite spin -------------------

    def test_collision_loop_gives_up_after_the_bound_instead_of_spinning(self):
        from unittest import mock

        from pirateforce_foundation.gm import command_capture as capture_module

        with mock.patch.object(
            capture_module, "_MAX_FILENAME_COLLISION_ATTEMPTS", 3,
        ), mock.patch.object(
            capture_module.os, "open", side_effect=FileExistsError,
        ) as mock_open:
            with self.assertRaises(OSError):
                capture_raw_gm_command(
                    b"x", "panya", capture_root=self.root, now_ts=0,
                )
        # suffix 0, 1, 2, 3 -- exactly bound + 1 attempts, not unbounded.
        self.assertEqual(mock_open.call_count, 4)

    # ----- pf-adversary D6, round `lkwmkp`: capture bytes must not be -----
    # ----- silently CRLF-translated by Windows' os.open() text mode --------

    def test_capture_file_open_passes_o_binary_flag_when_available(self):
        # This project never opens a raw-write descriptor with os.O_BINARY
        # anywhere (grepped across src/, tests/, tools/ before this fix),
        # and its trusted gate runs on windows-latest. Without the flag,
        # CPython's os.open() on Windows leaves the descriptor in the
        # C-runtime's default text mode, so the raw os.write() calls in
        # `capture_raw_gm_command` would be subject to \n -> \r\n
        # translation -- silently breaking this module's own "lossless
        # copy" promise. os.O_BINARY does not exist on this (Linux) host,
        # so it is monkeypatched to a sentinel bit that cannot collide with
        # any real O_* flag CPython defines, purely to prove this call site
        # threads the flag through when the platform provides it -- this
        # does NOT prove anything about actual Windows CRLF behaviour,
        # which no machine in this cloud environment can measure.
        #
        # pf-adversary (this round): the spy used to delegate to the real
        # os.open() with the sentinel bit still set in the flags it forwarded
        # -- harmless on Linux (an unrecognized oflag bit is ignored), but
        # this bit has never been asked of the real Windows CRT open call
        # this fix targets, and Microsoft documents an unrecognized oflag
        # as unspecified rather than ignored. A red Windows gate from that
        # would look like this fix broke Windows, when the real cause would
        # be a test sending a syscall a value nothing asked it to accept.
        # The wrapper below records the flags actually requested, then
        # clears the sentinel bit before handing off to the real os.open --
        # proving the call site threads the flag through without ever
        # letting the untested bit reach a real syscall.
        sentinel_bit = 1 << 30
        real_open = command_capture.os.open

        def _spy_then_real_open_without_sentinel(path, flags, *args, **kwargs):
            return real_open(path, flags & ~sentinel_bit, *args, **kwargs)

        with mock.patch.object(
            command_capture.os, "O_BINARY", sentinel_bit, create=True,
        ), mock.patch.object(
            command_capture.os,
            "open",
            side_effect=_spy_then_real_open_without_sentinel,
        ) as spy_open:
            capture_raw_gm_command(
                b"x", "panya", capture_root=self.root, now_ts=0,
            )
        self.assertEqual(spy_open.call_count, 1)
        flags_arg = spy_open.call_args.args[1]
        self.assertTrue(
            flags_arg & sentinel_bit,
            f"os.open() flags {oct(flags_arg)} do not include the "
            f"O_BINARY sentinel bit {oct(sentinel_bit)} -- the getattr("
            f"os, 'O_BINARY', 0) fallback regressed or was removed",
        )

    def test_capture_file_open_flags_unchanged_when_o_binary_absent(self):
        # Where os.O_BINARY does not exist, getattr(...) must fall back to
        # 0 -- the flags value passed to os.open() must be byte-for-byte
        # the same as before this fix. This pins that the fix is a true
        # no-op there, not a behaviour change riding along with it.
        #
        # The absence is SIMULATED rather than assumed (see
        # `_o_binary_removed` above): the previous version of this test
        # asserted `not hasattr(os, "O_BINARY")` about the host, which is
        # true on this Linux clone and false on the windows-latest gate --
        # it is what turned `#962` red. What this test is actually about is
        # the fallback branch of `getattr(os, "O_BINARY", 0)`, and that
        # branch is now exercised on every platform.
        with _o_binary_removed(command_capture.os):
            self.assertFalse(hasattr(command_capture.os, "O_BINARY"))
            with mock.patch.object(
                command_capture.os, "open", side_effect=command_capture.os.open,
            ) as spy_open:
                capture_raw_gm_command(
                    b"z", "panya", capture_root=self.root, now_ts=2,
                )
        self.assertEqual(spy_open.call_count, 1)
        flags_arg = spy_open.call_args.args[1]
        self.assertEqual(flags_arg, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    # ----- pf-adversary (this round): capture files must not be world- -----
    # ----- readable/executable regardless of the process umask -------------

    def test_capture_file_mode_is_owner_only_no_execute_regardless_of_umask(self):
        # `os.open` with no explicit `mode` argument defaults to 0o777
        # (masked by umask) -- reproduced live before this fix: under this
        # project's own default umask (0o022) that produced 0o755
        # (world-readable AND world-executable) for a file holding
        # forensic, client-controlled bytes (real account names, free-text
        # a GM typed). A permissive host umask (e.g. 0o000) would have made
        # it world-writable too. The fix passes an explicit mode=0o600, which
        # has no group/other bits for any umask to need to clear -- assert
        # that holds under a deliberately permissive umask (0o000) so this
        # test cannot pass by accident of the container's own umask.
        #
        # gate RED, round vb3ktn (this lane, self-caught after the fact):
        # this assertion is POSIX-only. NTFS has no POSIX permission bits --
        # CPython's os.open() on Windows only ever inspects the `mode`
        # argument for a single bit (stat.S_IWRITE, i.e. "not read-only");
        # any owner/group/other split, including the 0o600 this fix passes,
        # is accepted and then silently ignored. Measured on this project's
        # own real gate (windows-latest, run 33132956815): the identical fix
        # and test produced mode 0o666 there, not 0o600 -- proving this is
        # not a container-umask fluke, it is what Windows actually does.
        # The gate this project trusts runs on Windows on purpose (see
        # .github/workflows/gate-windows.yml's own docstring) because that
        # is the real deployment target, so the exact-mode assertion below
        # is only meaningful -- and only run -- on a POSIX os.stat(). On
        # Windows this test still proves the call does not raise and the
        # file is written, but the owner-only *enforcement* this fix's
        # commit message claims is a POSIX-only guarantee: on the real
        # Windows bridge, `capture/gm_command_capture/*.txt` is only as
        # private as the containing directory's NTFS ACL, which this lane's
        # write zone (a plain file write, no `pywin32`/ACL API available)
        # cannot set. Flagged to COO in a companion pf_bridge letter this
        # round rather than silently narrowing what this test proves.
        old_umask = os.umask(0o000)
        try:
            out = capture_raw_gm_command(
                b"x", "panya", capture_root=self.root, now_ts=0
            )
        finally:
            os.umask(old_umask)
        mode = stat.S_IMODE(out.stat().st_mode)
        if os.name == "posix":
            self.assertEqual(mode, 0o600, oct(mode))
        else:
            # No POSIX mode bits to check on this OS -- the call must still
            # succeed and produce a real file; see the comment above.
            self.assertTrue(out.is_file())

    def test_capture_directory_mode_is_owner_only_regardless_of_umask(self):
        # `Path.mkdir` with no explicit `mode` is masked by the process
        # umask the same way `os.open` is -- a permissive host umask (e.g.
        # 0o000) leaves this directory world-writable, which lets another
        # local user delete or rename the 0o600 capture files inside even
        # though they cannot read their contents, partially defeating this
        # module's own "nothing captured is ever lost" guarantee. Uses a
        # fresh subdirectory (not self.root, created in setUp before this
        # test could set the umask) so the mkdir call under test is the one
        # that actually creates it.
        nested_root = Path(self.root) / "nested"
        old_umask = os.umask(0o000)
        try:
            capture_raw_gm_command(b"x", "panya", capture_root=nested_root, now_ts=0)
        finally:
            os.umask(old_umask)
        mode = stat.S_IMODE(nested_root.stat().st_mode)
        if os.name == "posix":
            self.assertEqual(mode, 0o700, oct(mode))
        else:
            self.assertTrue(nested_root.is_dir())

    def test_capture_directory_mode_is_retightened_on_a_preexisting_loose_directory(self):
        # pf-adversary (verification pass, same round): `mkdir(...,
        # exist_ok=True)` is a silent no-op when the directory already
        # exists -- it never chmods it. `DEFAULT_CAPTURE_ROOT` shares its
        # literal parent (`capture/`) with gm/commands.py's
        # `DEFAULT_LOG_PATH`, and `.gitignore` documents that parent as
        # never cleaned up, so on a real host whichever function runs first
        # locks in whatever mode the umask in effect at that one moment
        # produced -- every later call, even under a strict umask, would
        # otherwise leave a once-loose directory stuck wide open forever.
        # Simulate that: create the directory loose *before* calling the
        # function under test (standing in for "some earlier call, or the
        # other function, created it under a permissive umask"), then call
        # with a strict umask and assert the mode is retightened anyway.
        #
        # No POSIX mode bits to check on Windows (same caveat as the
        # sibling first-creation test above) -- this test's own precondition
        # (a directory already sitting at a loose mode) cannot be
        # constructed there either, so it only runs its assertions on
        # POSIX; the call under test still runs and must still succeed on
        # every OS.
        nested_root = Path(self.root) / "preexisting"
        nested_root.mkdir(mode=0o777, parents=True)
        if os.name == "posix":
            os.chmod(nested_root, 0o777)
            self.assertEqual(stat.S_IMODE(nested_root.stat().st_mode), 0o777)
        old_umask = os.umask(0o022)
        try:
            capture_raw_gm_command(b"x", "panya", capture_root=nested_root, now_ts=0)
        finally:
            os.umask(old_umask)
        if os.name == "posix":
            mode = stat.S_IMODE(nested_root.stat().st_mode)
            self.assertEqual(mode, 0o700, oct(mode))
        else:
            self.assertTrue(nested_root.is_dir())

    def test_collision_loop_bound_does_not_affect_a_realistic_capture_count(self):
        # The real-world guard this bound exists next to (gm/dispatch.py's
        # own RATE_LIMIT_MAX_CALLS_PER_WINDOW) caps how often this loop can
        # even be entered per account per window -- this proves the default
        # bound leaves a generous, realistic same-second burst untouched.
        paths = [
            capture_raw_gm_command(
                bytes([i % 256]), "panya", capture_root=self.root, now_ts=1000.0,
            )
            for i in range(50)
        ]
        self.assertEqual(len(set(paths)), 50)


    # ----- pf-adversary (round `40bjg7`, follow-up `gn7gk5`): a write -----
    # ----- failure must not leave an unaccounted file on disk -------------

    def test_a_write_failure_leaves_no_file_behind_when_cleanup_succeeds(self):
        # Reproduces the adversary's own repro: only os.write is faked (the
        # real os.open runs, so a real empty file exists at the moment the
        # write fails) -- before this round, that file was left on disk with
        # nothing accounting for it. It must be gone once this call returns.
        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ):
            with self.assertRaises(OSError) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertNotIsInstance(
            ctx.exception, CaptureFileNotVerifiedRemoved,
            "cleanup succeeded (nothing else in this test touches os.unlink) "
            "-- the caller must see a plain OSError, not the unverified-removal "
            "subclass, or gm/dispatch.py would wrongly refuse to refund a call "
            "that really did leave zero bytes on disk",
        )
        leftover = list(Path(self.root).glob("*")) if Path(self.root).exists() else []
        self.assertEqual(
            leftover, [],
            "a write failure left a file on disk that nothing will ever "
            "account for -- the exact gap this test guards",
        )

    def test_a_write_failure_raises_the_unverified_subclass_when_cleanup_also_fails(self):
        # Both os.write and the cleanup os.unlink fail: the caller cannot
        # prove the partial file is gone, so it must see a DISTINCT
        # exception type rather than the plain OSError it would otherwise
        # read as "zero bytes on disk, safe to refund".
        # pf-adversary (round `0op9bt` ADDENDUM, D6): an unmocked `unlink`
        # failure now retries for real (`_UNLINK_ATTEMPTS`) and prints a
        # real stderr line -- mock `time.sleep` and swallow the print so
        # this test stays fast and quiet, the same as the tests that were
        # written FOR that retry behaviour further down this file.
        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            command_capture.os, "unlink", side_effect=OSError("simulated EACCES"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(CaptureFileNotVerifiedRemoved) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertIsInstance(
            ctx.exception.__cause__, OSError,
            "the original write failure must still be chained, not swallowed",
        )
        # The real (unmocked-at-the-syscall-level) file genuinely still
        # exists -- this test's own os.unlink mock is what prevented its
        # removal, so the file is really there, not merely unasserted.
        leftover = list(Path(self.root).glob("*"))
        self.assertEqual(len(leftover), 1, leftover)

    def test_best_effort_unlink_treats_already_gone_as_success(self):
        missing = Path(self.root) / "does_not_exist.txt"
        self.assertTrue(command_capture._best_effort_unlink(missing))

    def test_the_retry_delay_has_a_literal_floor_above_zero(self):
        # pf-adversary (round `0op9bt` ADDENDUM, D5): the tests that pin the
        # sleep CALLS all compare against
        # ``command_capture._UNLINK_RETRY_DELAY_SECONDS`` -- the constant's
        # OWN live value -- so a mutant that sets it to ``0.0`` (deleting
        # the only property this round adds: waiting out a transient
        # Windows sharing violation) passed the whole suite. This compares
        # against a LITERAL floor instead, which no such mutant can dodge
        # by changing the constant it is compared against.
        self.assertGreater(command_capture._UNLINK_RETRY_DELAY_SECONDS, 0.0)

    def test_the_unlink_attempt_count_has_a_literal_floor_of_one(self):
        # pf-adversary (round `0op9bt` ADDENDUM, D7): nothing pinned
        # ``_UNLINK_ATTEMPTS >= 1`` as a literal -- at 0 the retry loop's
        # body never runs and the function reports "could not remove"
        # without ever calling ``os.unlink``, which the module's own
        # "unreachable final iteration" comment assumes cannot happen. The
        # module-level ``assert`` next to the constant is the enforcement;
        # this is the regression pin for it.
        self.assertGreaterEqual(command_capture._UNLINK_ATTEMPTS, 1)

    # ----- COO-DECISION `2047` (round `0op9bt`): the cleanup unlink gets a --
    # ----- BOUNDED retry (Windows sharing violations are transient), the ---
    # ----- exhausted case keeps the old contract, POSIX sees no change -----

    def test_a_cleanup_unlink_that_succeeds_on_the_third_try_is_a_clean_removal(self):
        # COO's first required test: fail twice, succeed on the third
        # attempt. The caller must read the SAME plain OSError it reads when
        # the very first unlink succeeds -- i.e. gm/dispatch.py refunds the
        # quota -- because the partial file really is gone by the time this
        # returns.
        real_unlink = command_capture.os.unlink
        attempts = []

        def _unlink(path):
            attempts.append(path)
            if len(attempts) < 3:
                raise OSError("simulated Windows sharing violation")
            real_unlink(path)

        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            command_capture.os, "unlink", side_effect=_unlink,
        ), mock.patch.object(command_capture.time, "sleep") as sleep_spy:
            with self.assertRaises(OSError) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)

        self.assertEqual(len(attempts), 3, attempts)
        self.assertNotIsInstance(
            ctx.exception, CaptureFileNotVerifiedRemoved,
            "the third attempt removed the file, so the caller must see the "
            "plain OSError that means 'zero bytes on disk, safe to refund' -- "
            "reporting the unverified subclass here would strand the quota "
            "for a call that really did clean up after itself",
        )
        self.assertEqual(
            sleep_spy.call_count, 2,
            "three attempts means exactly two gaps between them",
        )
        self.assertEqual(
            [c.args[0] for c in sleep_spy.call_args_list],
            [command_capture._UNLINK_RETRY_DELAY_SECONDS] * 2,
        )
        self.assertLessEqual(
            command_capture._UNLINK_RETRY_DELAY_SECONDS
            * (command_capture._UNLINK_ATTEMPTS - 1),
            0.3,
            "COO capped the total added delay at ~300 ms for the whole "
            "retry sequence",
        )
        self.assertEqual(
            list(Path(self.root).glob("*")), [],
            "the file the third attempt removed must really be gone",
        )

    def test_a_cleanup_unlink_that_fails_every_attempt_still_refuses_the_refund(self):
        # COO's second required test: all three attempts fail. Nothing about
        # the pre-retry contract changes -- CaptureFileNotVerifiedRemoved,
        # the original write error still chained, the file still on disk,
        # no refund -- and the operator gets exactly one stderr line naming
        # the file that stayed behind (there is no janitor: that quota is
        # only cleared by restarting the process).
        attempts = []

        def _unlink(path):
            attempts.append(path)
            raise OSError("simulated Windows sharing violation")

        stderr = io.StringIO()
        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            command_capture.os, "unlink", side_effect=_unlink,
        ), mock.patch.object(
            command_capture.time, "sleep",
        ) as sleep_spy, contextlib.redirect_stderr(stderr):
            with self.assertRaises(CaptureFileNotVerifiedRemoved) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)

        self.assertEqual(
            len(attempts), 3, attempts,
        )
        self.assertEqual(
            command_capture._UNLINK_ATTEMPTS, 3,
            "COO-DECISION `2047` fixed the bound at three attempts -- "
            "changing it is a decision, not a tuning knob",
        )
        self.assertEqual(
            sleep_spy.call_count, 2,
            "the last failure must not sleep before giving up",
        )
        self.assertIsInstance(
            ctx.exception.__cause__, OSError,
            "the original write failure must still be chained, not swallowed",
        )
        leftover = list(Path(self.root).glob("*"))
        self.assertEqual(len(leftover), 1, leftover)
        printed = stderr.getvalue().splitlines()
        self.assertEqual(
            len(printed), 1,
            f"exactly one stuck-file line, got {printed!r}",
        )
        self.assertIn(command_capture._UNLINK_STUCK_CONSOLE_TOKEN, printed[0])
        self.assertIn(str(leftover[0]), printed[0])
        self.assertTrue(
            printed[0].isascii(),
            "the bridge console is cp874 -- a non-ASCII log line kills the "
            "tool reading it",
        )

    def test_a_dead_stderr_cannot_turn_the_stuck_file_line_into_the_raised_error(self):
        # This drives the ORDINARY `except OSError` write-failure path (a
        # plain `OSError` from `os.write`), NOT `_capture_raw`'s
        # `except BaseException` shutdown path -- pf-adversary (round
        # `0op9bt` ADDENDUM, D8) found this comment claimed the latter while
        # the test exercised the former, which is exactly how D1/D2 (the
        # real shutdown-path bugs) went unnoticed. See
        # `test_a_dead_stderr_during_the_shutdown_reraise_path_still_reraises_the_original_exception`
        # below for the path this comment used to claim to cover. What this
        # test actually pins: a dead `sys.stderr` while classifying an
        # ordinary write failure must not turn the raised exception into a
        # `ValueError` from the failed log line.
        closed = io.StringIO()
        closed.close()

        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            command_capture.os, "unlink",
            side_effect=OSError("simulated Windows sharing violation"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), mock.patch.object(command_capture.sys, "stderr", closed):
            with self.assertRaises(CaptureFileNotVerifiedRemoved) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)

        self.assertIsInstance(
            ctx.exception.__cause__, OSError,
            "the original write failure must still be the chained cause -- "
            "not a ValueError from writing to a closed stream",
        )

    def test_a_non_oserror_escaping_the_write_loop_never_sleeps_during_cleanup(self):
        # pf-adversary (round `0op9bt` ADDENDUM, D1): `_capture_raw`'s
        # `except BaseException` branch calls `_best_effort_unlink` with
        # `retry=False` for exactly this reason -- that branch's job is
        # re-raising an in-flight `SystemExit`/`KeyboardInterrupt`
        # unchanged, and `time.sleep` between retries would open a window,
        # during interpreter shutdown, where a second signal could replace
        # it. A failing unlink here must therefore make exactly ONE attempt
        # and sleep ZERO times, even though `_UNLINK_ATTEMPTS` is 3.
        with mock.patch.object(
            command_capture.os, "write", side_effect=SystemExit(3),
        ), mock.patch.object(
            command_capture.os, "unlink",
            side_effect=OSError("simulated Windows sharing violation"),
        ) as unlink_spy, mock.patch.object(
            command_capture.time, "sleep",
        ) as sleep_spy, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertEqual(
            ctx.exception.code, 3,
            "the shutdown path must re-raise the ORIGINAL exception "
            "unchanged, not translate it into anything else",
        )
        self.assertEqual(unlink_spy.call_count, 1, "retry=False means one try")
        self.assertEqual(sleep_spy.call_count, 0)

    def test_the_shutdown_call_site_also_names_the_account_and_bytes(self):
        # pf-adversary (round `smztdu`, finding 3): the third call site
        # (BaseException/shutdown) -- same content pin as the write-failure
        # and close-failure sites above, for the same reason: nothing
        # caught `account_name=""`/`attempted_bytes=0` being passed here
        # instead of the real values before this test existed.
        stderr = io.StringIO()
        with mock.patch.object(
            command_capture.os, "write", side_effect=SystemExit(3),
        ), mock.patch.object(
            command_capture.os, "unlink",
            side_effect=OSError("simulated Windows sharing violation"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit):
                capture_raw_gm_command(
                    b"x", "thongchai", capture_root=self.root, now_ts=0,
                )
        printed = stderr.getvalue().splitlines()
        self.assertEqual(len(printed), 1, printed)
        self.assertIn("account=thongchai", printed[0])
        self.assertNotIn("attempted_bytes=0", printed[0])

    def test_a_dead_stderr_during_the_shutdown_reraise_path_still_reraises_the_original_exception(self):
        # pf-adversary (round `0op9bt` ADDENDUM, D2): the log-line guard
        # around the shutdown-path unlink used to be `except Exception`,
        # which does NOT catch `KeyboardInterrupt` or `SystemExit` -- the
        # exact two exceptions this whole branch exists to protect. A CLOSED
        # `io.StringIO` only raises `ValueError` (an `Exception`), which the
        # old guard already caught -- that mutant survives against a closed
        # stream, so this uses a fake stream whose `write` raises
        # `KeyboardInterrupt` itself, the real failure mode `except
        # Exception` cannot catch, to prove the guard actually needs
        # `BaseException`.
        class _StreamThatInterrupts:
            encoding = "utf-8"

            def write(self, _text):
                raise KeyboardInterrupt()

        with mock.patch.object(
            command_capture.os, "write", side_effect=SystemExit(3),
        ), mock.patch.object(
            command_capture.os, "unlink",
            side_effect=OSError("simulated Windows sharing violation"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), mock.patch.object(
            command_capture.sys, "stderr", _StreamThatInterrupts(),
        ):
            with self.assertRaises(SystemExit) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertEqual(
            ctx.exception.code, 3,
            "a KeyboardInterrupt raised by the failed print must not "
            "replace the SystemExit this path is re-raising",
        )

    def test_the_stuck_file_line_names_the_account_and_the_attempted_bytes(self):
        # pf-adversary (round `0op9bt` ADDENDUM, D3): the line used to say
        # only "its capture quota stays charged" -- no account, no byte
        # count -- although the file on disk can be empty while the charge
        # is the ~4 KB disk-block floor or larger. Two accounts stuck at the
        # same second used to print IDENTICAL lines.
        stderr = io.StringIO()
        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            command_capture.os, "unlink",
            side_effect=OSError("simulated Windows sharing violation"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), contextlib.redirect_stderr(stderr):
            with self.assertRaises(CaptureFileNotVerifiedRemoved):
                capture_raw_gm_command(
                    b"hello", "thongchai", capture_root=self.root, now_ts=0,
                )
        printed = stderr.getvalue().splitlines()
        self.assertEqual(len(printed), 1, printed)
        self.assertIn("account=thongchai", printed[0])
        self.assertIn("attempted_bytes=", printed[0])
        self.assertNotIn(
            "attempted_bytes=0", printed[0],
            "the real capture header+payload is never zero bytes",
        )

    def test_an_account_name_with_a_newline_cannot_forge_a_second_stuck_file_line(self):
        # pf-adversary (round `smztdu`, finding 1): `console_safe` only
        # folds characters the STREAM cannot encode -- a literal `\n` is
        # representable in every encoding this project uses, so it used to
        # pass straight through unescaped, and `account_name` here is the
        # account's real login name (`gm/accounts.py`'s `gm_accounts` match
        # it verbatim; nothing restricts its characters). This exact field
        # already needed the same defense once before, for the on-disk
        # header line (`header_account = _escape_for_header(account_name)`
        # a few lines above in the source, "an account_name containing a
        # newline must not be able to forge extra header lines") -- this
        # pins that the stderr line gets the same escape.
        # Punctuation (":", "/") is deliberate: `_sanitize_account` (used
        # for the FILENAME only, a separate field from the one this test
        # targets) drops anything outside ASCII alnum/-/_, so a payload
        # built only from those characters would also show up sanitized
        # into `path=`, confounding a plain substring/count check on the
        # stderr line with an unrelated, pre-existing property of the
        # filename. Non-alnum punctuation here is dropped from the
        # filename but preserved (escaped) in the field this test guards.
        hostile_account = (
            "normal_gm\n"
            "FORGED: path=/etc/passwd attempted_bytes=999999999 attempts=3"
        )
        stderr = io.StringIO()
        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            command_capture.os, "unlink",
            side_effect=OSError("simulated Windows sharing violation"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), contextlib.redirect_stderr(stderr):
            with self.assertRaises(CaptureFileNotVerifiedRemoved):
                capture_raw_gm_command(
                    b"x", hostile_account, capture_root=self.root, now_ts=0,
                )
        raw_output = stderr.getvalue()
        printed = raw_output.splitlines()
        self.assertEqual(
            len(printed), 1,
            f"{printed!r}: a newline in the account name must not split "
            "this into two lines -- the second one forged, "
            "attacker-controlled",
        )
        self.assertIn("\\n", printed[0], "the newline must be VISIBLE, escaped")
        self.assertIn(
            "FORGED", printed[0],
            "the rest of the account name must still be readable, just "
            "folded onto the one real line, not dropped",
        )

    def test_the_stuck_file_line_still_prints_when_capture_root_is_not_ascii(self):
        # pf-adversary (round `0op9bt` ADDENDUM, D4): every existing test for
        # this line used `self.root`, which comes from
        # `tempfile.TemporaryDirectory` and is therefore always plain ASCII
        # -- so `printed[0].isascii()` pinned nothing about non-ASCII input,
        # only the literal token text. `path` is built from `capture_root`
        # (a config value here, not a test-only fixture); before
        # `console_safe` folded it, a character `io.StringIO`'s ASCII
        # fallback cannot carry raised `UnicodeEncodeError` straight out of
        # this function's own `print`, which the guard above swallowed --
        # the operator got NO line at all, for the one case (an unencodable
        # path) this token exists to report.
        non_ascii_root = Path(self._tmp.name) / "José" / "capture"
        stderr = io.StringIO()
        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            command_capture.os, "unlink",
            side_effect=OSError("simulated Windows sharing violation"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), contextlib.redirect_stderr(stderr):
            with self.assertRaises(CaptureFileNotVerifiedRemoved):
                capture_raw_gm_command(
                    b"x", "panya", capture_root=non_ascii_root, now_ts=0,
                )
        printed = stderr.getvalue().splitlines()
        self.assertEqual(
            len(printed), 1,
            "the line must still be written, folded to what the stream "
            "can carry, not dropped",
        )
        self.assertTrue(printed[0].isascii())
        self.assertIn("Jos", printed[0])

    def test_a_cleanup_unlink_that_works_first_try_never_sleeps(self):
        # COO's explicit condition on accepting the retry at all: "Linux must
        # not be able to tell the difference". The retry path is entered only
        # by a FAILING unlink, so the ordinary POSIX cleanup -- the only one
        # this project's own gate and dev machines ever run -- still does
        # exactly one syscall and no sleeping.
        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(command_capture.time, "sleep") as sleep_spy:
            with self.assertRaises(OSError):
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertEqual(
            sleep_spy.call_count, 0,
            "an unlink that succeeds on the first attempt must not sleep",
        )
        self.assertEqual(list(Path(self.root).glob("*")), [])

    # ----- pf-adversary (round `gn7gk5`, follow-up `79ahzl`): os.close() ---
    # ----- failing must not bypass the cleanup-then-classify contract -----
    # ----- the write-failure branch above already holds ------------------

    def test_a_close_failure_right_after_a_write_failure_is_swallowed_and_still_cleans_up(self):
        # Before this round, this exact combination (os.write raises, THEN
        # the os.close(fd) in the except block also raises) propagated the
        # close() error immediately, before _best_effort_unlink ever ran --
        # skipping the whole classify contract. os.unlink is real here
        # (only write and close are faked), so cleanup must still succeed
        # and the ORIGINAL write error must be what the caller sees.
        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            command_capture.os, "close",
            side_effect=close_that_really_closes_then_fails("simulated close EIO"),
        ):
            with self.assertRaises(OSError) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertNotIsInstance(ctx.exception, CaptureFileNotVerifiedRemoved)
        self.assertIn("simulated ENOSPC", str(ctx.exception))
        leftover = list(Path(self.root).glob("*")) if Path(self.root).exists() else []
        self.assertEqual(leftover, [])

    def test_a_close_failure_after_a_successful_write_is_not_silently_refunded(self):
        # THE MORE SEVERE CASE (pf-adversary): os.write fully SUCCEEDS
        # (every byte accepted) and only the terminal os.close(fd) then
        # fails -- a real, documented POSIX behavior (deferred write-back
        # error surfacing at close, not exclusive to NFS). Before this
        # round nothing caught this at all: it propagated a bare OSError
        # past this function untouched. os.unlink is real here, so cleanup
        # must succeed and this must be classified exactly like a write
        # failure, not silently ignored.
        with mock.patch.object(
            command_capture.os, "close",
            side_effect=close_that_really_closes_then_fails(
                "simulated close ENOSPC",
            ),
        ):
            with self.assertRaises(OSError) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertNotIsInstance(ctx.exception, CaptureFileNotVerifiedRemoved)
        self.assertIn("simulated close ENOSPC", str(ctx.exception))
        leftover = list(Path(self.root).glob("*")) if Path(self.root).exists() else []
        self.assertEqual(
            leftover, [],
            "a write that fully succeeded, then failed only at close(), "
            "left a COMPLETE real capture on disk with no cleanup attempt",
        )

    def test_a_close_failure_after_a_successful_write_raises_unverified_when_cleanup_also_fails(self):
        # Both the write-succeeded-close-failed case above AND the cleanup
        # unlink fail: real, complete content may still be on disk, so the
        # caller must see the distinct subclass, not a plain OSError.
        with mock.patch.object(
            command_capture.os, "close",
            side_effect=close_that_really_closes_then_fails(
                "simulated close ENOSPC",
            ),
        ), mock.patch.object(
            command_capture.os, "unlink", side_effect=OSError("simulated EACCES"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(CaptureFileNotVerifiedRemoved) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertIsInstance(ctx.exception.__cause__, OSError)
        leftover = list(Path(self.root).glob("*"))
        self.assertEqual(len(leftover), 1, leftover)
        # The write really did complete -- this is a full, real capture
        # file, not an empty one, unlike the write-failure scenarios above.
        self.assertGreater(leftover[0].stat().st_size, 0)

    def test_the_close_failure_call_site_also_names_the_account_and_bytes(self):
        # pf-adversary (round `smztdu`, finding 3): D3's own test above
        # exercises only the WRITE-failure call site. Mutating
        # `account_name=account_name, attempted_bytes=len(file_body)` to
        # `account_name="", attempted_bytes=0` at the OTHER two call sites
        # (this close-failure one, and the BaseException/shutdown one) left
        # the whole three-file suite green -- confirmed by hand before this
        # test existed. This is the close-failure site's own content pin --
        # the file's own docs call this the MORE severe case (a complete
        # real capture, not an empty one, left unaccounted for).
        stderr = io.StringIO()
        with mock.patch.object(
            command_capture.os, "close",
            side_effect=close_that_really_closes_then_fails(
                "simulated close ENOSPC",
            ),
        ), mock.patch.object(
            command_capture.os, "unlink", side_effect=OSError("simulated EACCES"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), contextlib.redirect_stderr(stderr):
            with self.assertRaises(CaptureFileNotVerifiedRemoved):
                capture_raw_gm_command(
                    b"x", "thongchai", capture_root=self.root, now_ts=0,
                )
        printed = stderr.getvalue().splitlines()
        self.assertEqual(len(printed), 1, printed)
        self.assertIn("account=thongchai", printed[0])
        self.assertNotIn(
            "attempted_bytes=0", printed[0],
            "a successful write followed by a failed close is the MORE "
            "severe case -- a real, non-empty capture -- and must not "
            "report zero attempted bytes",
        )

    def test_the_close_failure_helper_leaves_no_descriptor_open(self):
        # The guard that makes every close-failure test in this package mean
        # the same thing on Windows as on Linux. A `side_effect` that only
        # raises leaks the descriptor; on Linux nothing notices, on Windows
        # the open handle locks the file and every one of those tests
        # reports the wrong exception class and then breaks its own temp-dir
        # cleanup -- the RED gate on #926 and #937. This test fails on ANY
        # platform the moment the helper stops closing for real, so the
        # Windows-only failure cannot come back invisibly.
        #
        # It guards ONE definition on purpose: pf-adversary (round `lkwmkp`,
        # D3) broke the first version of this fix by deleting `real_close`
        # from the copy of the helper that lived in
        # `test_gm_command_dispatch.py` -- Linux stayed 93 passed and the
        # Windows emulation went red, i.e. the guard proved the state of the
        # copy next to it and nothing else. There is now a single definition
        # in `tests/pf_gm_capture_mocks.py` that all three files import.
        #
        # Known limit (same review): `os.fstat` below asserts a negative
        # about an fd NUMBER, which the OS may hand out again. Nothing opens
        # a descriptor between the close and the assert in a single-threaded
        # run, so today this can only produce a false RED, never a false
        # green -- but under `pytest-xdist` it would need the helper's own
        # bookkeeping instead.
        opened = []
        real_open = os.open

        def spy_open(*args, **kwargs):
            fd = real_open(*args, **kwargs)
            opened.append(fd)
            return fd

        with mock.patch.object(
            command_capture.os, "open", side_effect=spy_open,
        ), mock.patch.object(
            command_capture.os, "close",
            side_effect=close_that_really_closes_then_fails("simulated close EIO"),
        ):
            with self.assertRaises(OSError):
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertEqual(len(opened), 1, opened)
        with self.assertRaises(OSError):
            # EBADF: the descriptor the capture opened is gone, so nothing
            # holds the capture file open once the failure has propagated.
            os.fstat(opened[0])

    def test_a_non_oserror_from_the_write_loop_still_closes_and_cleans_up(self):
        # pf-adversary (round `lkwmkp`, D5): rounds `gn7gk5`/`79ahzl`
        # replaced this function's `try/finally` with `except OSError`, so
        # any non-OSError escaping the write loop (`MemoryError` on the
        # `file_body[written:]` slice, `KeyboardInterrupt` at shutdown) left
        # both the descriptor and the `O_CREAT|O_EXCL` file behind -- on
        # Windows locked for the life of the process. The exception itself
        # must still propagate unchanged: an interpreter shutdown is not a
        # quota event and must not be dressed up as one.
        with mock.patch.object(
            command_capture.os, "write", side_effect=MemoryError("simulated"),
        ):
            with self.assertRaises(MemoryError):
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        leftover = list(Path(self.root).glob("*")) if Path(self.root).exists() else []
        self.assertEqual(
            leftover, [],
            "a non-OSError during the write left the partial capture file "
            "on disk, in the one function that promises it never does",
        )

    # ----- pf-adversary (follow-up review of round `79ahzl`): os.write's ---
    # ----- return value was never checked -- the SAME bug this package ----
    # ----- already found and fixed twice (gm/commands.py round `hs9m2r`, --
    # ----- gm/login_scene_stage.py's copy of it) and never ported here ----

    def test_a_resumed_short_write_still_produces_a_complete_untruncated_file(self):
        # Same shape as gm/commands.py's own
        # test_a_short_write_to_the_audit_log_is_not_reported_as_success
        # (round hs9m2r): one os.write call reports fewer bytes than asked,
        # with no exception -- the write LOOP must resume and finish the
        # file rather than silently accepting the short count as done.
        #
        # pf-adversary (follow-up review of round w87k4s): the original
        # version of this test asserted only `endswith(b"\n")` and
        # `b"hello world" in content` -- both still pass against a real
        # regression (dropping the loop's `file_body[written:]` slice on
        # retry, so the resumed call re-sends the WHOLE buffer instead of
        # only what's left, duplicating the leading bytes into the file
        # header). Reproduced live: 525 bytes starting `##...` instead of
        # 524 bytes starting `#...`, and the weak assertions above both
        # still passed on that corrupted file. Compare byte-for-byte
        # against an independently-captured clean run instead -- the one
        # property this module's own docstring actually promises ("a
        # lossless copy of every raw send lands on disk").
        payload = b"hello world, this is more than one byte long"
        clean_path = capture_raw_gm_command(
            payload, "panya", capture_root=self.root, now_ts=0,
        )
        expected = clean_path.read_bytes()
        clean_path.unlink()

        real_write = command_capture.os.write
        state = {"first": True}

        def short_once(fd, data):
            if state["first"] and len(data) > 1:
                state["first"] = False
                return real_write(fd, data[:1])
            return real_write(fd, data)

        with mock.patch.object(command_capture.os, "write", side_effect=short_once):
            out = capture_raw_gm_command(
                payload, "panya", capture_root=self.root, now_ts=0,
            )
        self.assertEqual(out.read_bytes(), expected)

    def test_a_write_making_no_progress_fails_closed_and_cleans_up(self):
        # Same shape as gm/commands.py's own
        # test_a_write_making_no_progress_fails_closed (round hs9m2r): a
        # write reporting 0 bytes with no exception must not be reported as
        # success -- before this fix it fell straight through to
        # `return out_path`, no exception, no refusal, quota charged
        # normally, for a file this module's own docstring promises is
        # never truncated.
        with mock.patch.object(command_capture.os, "write", return_value=0):
            with self.assertRaises(OSError) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertNotIsInstance(ctx.exception, CaptureFileNotVerifiedRemoved)
        self.assertIn("short write", str(ctx.exception))
        leftover = list(Path(self.root).glob("*")) if Path(self.root).exists() else []
        self.assertEqual(
            leftover, [],
            "a write making zero progress left a (empty) file on disk "
            "that the cleanup path failed to remove",
        )

    def test_a_write_making_no_progress_raises_unverified_when_cleanup_also_fails(self):
        with mock.patch.object(
            command_capture.os, "write", return_value=0,
        ), mock.patch.object(
            command_capture.os, "unlink", side_effect=OSError("simulated EACCES"),
        ), mock.patch.object(
            command_capture.time, "sleep",
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(CaptureFileNotVerifiedRemoved):
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        leftover = list(Path(self.root).glob("*"))
        self.assertEqual(len(leftover), 1, leftover)


if __name__ == "__main__":
    unittest.main()
