"""GM-002: raw GM_RunGMCommandVital capture sink writes bytes untouched."""
from __future__ import annotations

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


def close_that_really_closes_then_fails(message: str):
    """`os.close` side effect that releases the descriptor, then reports failure.

    A `side_effect=OSError(...)` alone never closes the real descriptor. On
    Linux that leak is invisible -- an open handle blocks neither `unlink`
    nor a directory removal -- so the whole suite stayed green here while
    the Windows gate went RED twice on exactly these tests
    (`pirate-force-server` #926 run 34024390383, #937 run 34029288153,
    both "6 failed, 3 errors" with six close-mocking tests in the round).
    Windows keeps a file locked while any handle on it is open, so the
    leaked descriptor made `_best_effort_unlink` inside the code under test
    fail with a sharing violation: every one of these cases reported
    `CaptureFileNotVerifiedRemoved` instead of the failure the test asked
    for, and the still-open handle then broke the `TemporaryDirectory`
    cleanup registered in `setUp`.

    Closing for real first is also the more faithful model: POSIX `close()`
    consumes the descriptor even when it reports an error (which is exactly
    why `command_capture._capture_raw` does not retry it), so a test that
    keeps the descriptor alive is testing a state the code under test can
    never be in.
    """
    real_close = os.close

    def _close(fd: int) -> None:
        real_close(fd)
        raise OSError(message)

    return _close


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
        with mock.patch.object(
            command_capture.os, "write", side_effect=OSError("simulated ENOSPC"),
        ), mock.patch.object(
            command_capture.os, "unlink", side_effect=OSError("simulated EACCES"),
        ):
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
        ):
            with self.assertRaises(CaptureFileNotVerifiedRemoved) as ctx:
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        self.assertIsInstance(ctx.exception.__cause__, OSError)
        leftover = list(Path(self.root).glob("*"))
        self.assertEqual(len(leftover), 1, leftover)
        # The write really did complete -- this is a full, real capture
        # file, not an empty one, unlike the write-failure scenarios above.
        self.assertGreater(leftover[0].stat().st_size, 0)

    def test_the_close_failure_helper_leaves_no_descriptor_open(self):
        # The guard that makes the three close-failure tests above mean the
        # same thing on Windows as on Linux. A `side_effect` that only
        # raises leaks the descriptor; on Linux nothing notices, on Windows
        # the open handle locks the file and every one of those tests
        # reports the wrong exception class and then breaks its own temp-dir
        # cleanup -- the RED gate on #926 and #937. This test fails on ANY
        # platform the moment the helper stops closing for real, so the
        # Windows-only failure cannot come back invisibly.
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
        ):
            with self.assertRaises(CaptureFileNotVerifiedRemoved):
                capture_raw_gm_command(b"x", "panya", capture_root=self.root, now_ts=0)
        leftover = list(Path(self.root).glob("*"))
        self.assertEqual(len(leftover), 1, leftover)


if __name__ == "__main__":
    unittest.main()
