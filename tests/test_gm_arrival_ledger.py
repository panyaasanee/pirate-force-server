"""GT-279 / P-3: an empty capture folder must stop meaning four things at once.

The attended boot R322B pressed the real client's GM EXECUTE button three
times and afterwards ``capture/gm_command_capture/`` was empty -- which is
the same observation whether the client sent nothing, sent a different
vital id, never reached ``gm/dispatch.py``, or reached it and was refused
there.  ``gm/arrival_ledger.py`` splits the last of those four off from the
other three by writing one bounded line per arrival, whatever the outcome.

These tests pin the two halves that make that line trustworthy:

* the SHAPE (one line, ASCII, no payload bytes, every field capped), and
* the BOUNDS (the budget is per ACCOUNT, so a flooding peer cannot spend
  the budget the attended tester's own line needs -- denial of evidence by
  flooding is the obvious attack on a file whose whole value is that a line
  is present, and pf-adversary D1 measured that an authorized-vs-not split
  does NOT stop it: the tester's own frames are refused ones).

and the wiring in ``gm/dispatch.py``: every exit of the gate chain records
exactly one line, including the exits that raise, and the capture root
itself stays untouched for a non-GM connection.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import arrival_ledger  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402


class ArrivalLineShapeTests(unittest.TestCase):
    """The line itself, with no filesystem involved."""

    def test_known_id_renders_its_registry_name(self):
        line = arrival_ledger.format_arrival_line(
            0x51E9, "panya", 12, "captured", authorized=True, now_ts=0,
        )
        self.assertTrue(line.startswith(arrival_ledger.LEDGER_LINE_TOKEN + " "))
        self.assertIn("id=0x51E9", line)
        self.assertIn("name=GM_RunGMCommandVital", line)
        self.assertIn("account=panya", line)
        self.assertIn("len=12", line)
        self.assertIn("authorized=yes", line)
        self.assertIn("outcome=captured", line)

    def test_second_wired_opcode_is_named_too(self):
        line = arrival_ledger.format_arrival_line(
            0x6CEC, "gm1", 0, "captured", authorized=True, now_ts=0,
        )
        self.assertIn("name=Activity_CheatCodeVital", line)

    def test_unwired_id_is_recorded_but_not_named(self):
        # 0x162E CheatVital is client->server with no sink in this package:
        # an arrival for it must still be recorded, and must not be given a
        # name this module cannot back up.
        line = arrival_ledger.format_arrival_line(
            0x162E, "gm1", 4, "captured", authorized=True, now_ts=0,
        )
        self.assertIn("id=0x162E", line)
        self.assertIn(f"name={arrival_ledger.UNLISTED_VITAL_NAME}", line)

    def test_no_field_can_break_the_one_arrival_one_line_shape(self):
        line = arrival_ledger.format_arrival_line(
            0x51E9,
            "ev\nil\x00acct" + "A" * 500,
            7,
            "refused\nnot_gm" + "B" * 500,
            authorized=False,
            now_ts=0,
        )
        self.assertNotIn("\n", line)
        self.assertNotIn("\x00", line)
        self.assertLessEqual(len(line), arrival_ledger.MAX_LINE_LENGTH)
        self.assertTrue(line.isascii())

    def test_a_cut_field_says_it_was_cut(self):
        # pf-adversary D12: `refused_capture_write_failed_
        # CaptureFileNotVerifiedRemoved` is 58 characters.  Cut silently at
        # 48 it reads as a whole exception name that does not exist, and
        # two exception types sharing a prefix collapse into one token.
        line = arrival_ledger.format_arrival_line(
            0x51E9, "gm1", 1,
            "refused_capture_write_failed_CaptureFileNotVerifiedRemoved",
            authorized=True, now_ts=0,
        )
        outcome = line.split("outcome=")[1]
        self.assertTrue(outcome.endswith(arrival_ledger.TRUNCATION_MARK))
        self.assertEqual(len(outcome), arrival_ledger.MAX_OUTCOME_LENGTH)
        # ...and a field that fit is NOT marked.
        fits = arrival_ledger.format_arrival_line(
            0x51E9, "gm1", 1, "captured", authorized=True, now_ts=0,
        )
        self.assertTrue(fits.endswith("outcome=captured"))

    def test_non_str_fields_fall_back_and_are_never_str_coerced(self):
        class Hostile:
            def __str__(self):  # pragma: no cover - must never be called
                raise AssertionError("__str__ must not reach the ledger line")

        line = arrival_ledger.format_arrival_line(
            "not an int", Hostile(), "not an int", Hostile(),
            authorized=True, now_ts=0,
        )
        self.assertIn("id=unlisted", line)
        self.assertIn("account=unnamed", line)
        self.assertIn("len=-1", line)
        self.assertIn("outcome=unstated", line)

    def test_bool_is_not_accepted_as_a_vital_id(self):
        # `True == 1` in Python; an int subclass must not decide the name
        # this line carries (same `type(x) is` rule gm/dispatch.py applies
        # to account_name before the allowlist test).
        line = arrival_ledger.format_arrival_line(
            True, "gm1", 1, "captured", authorized=True, now_ts=0,
        )
        self.assertIn("id=unlisted", line)

    def test_unreadable_clock_still_produces_a_line(self):
        line = arrival_ledger.format_arrival_line(
            0x51E9, "gm1", 1, "captured", authorized=True, now_ts=float("nan"),
        )
        self.assertIn("ts=unreadable_clock", line)
        self.assertIn("outcome=captured", line)


class ArrivalLedgerFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.capture_root = Path(self.tmp.name) / "capture" / "gm_command_capture"
        arrival_ledger.reset_for_tests()
        self.addCleanup(arrival_ledger.reset_for_tests)

    @property
    def ledger_path(self):
        return (
            arrival_ledger.ledger_root_for_capture_root(self.capture_root)
            / arrival_ledger.LEDGER_FILENAME
        )

    def _all_lines(self):
        if not self.ledger_path.exists():
            return []
        return self.ledger_path.read_text("ascii").splitlines()

    def _lines(self):
        return [
            line for line in self._all_lines()
            if line.startswith(arrival_ledger.LEDGER_LINE_TOKEN + " ")
        ]

    def _record(self, account="gm1", authorized=True, outcome="captured"):
        return arrival_ledger.record_arrival(
            0x51E9, account, 3, outcome,
            authorized=authorized, capture_root=self.capture_root, now_ts=0,
        )

    def test_the_first_line_of_a_process_names_the_absolute_path_and_pid(self):
        # pf-adversary D3/D7: a relative capture root resolved against a
        # server cwd the reader is not looking under produces the same
        # "nothing is there" as a frame that never arrived, and an
        # append-only file with no per-process marker cannot separate this
        # boot's lines from a pytest run's.
        self._record()
        header = self._all_lines()[0]
        self.assertTrue(header.startswith(arrival_ledger.LEDGER_OPENED_TOKEN + " "))
        self.assertIn(f"pid={os.getpid()}", header)
        self.assertIn(f"path={self.ledger_path.parent.resolve()}", header)
        # ...once per process, not once per arrival.
        self._record()
        self.assertEqual(
            sum(1 for line in self._all_lines()
                if line.startswith(arrival_ledger.LEDGER_OPENED_TOKEN)),
            1,
        )

    def test_ledger_lands_beside_the_capture_root_not_inside_it(self):
        self._record()
        self.assertTrue(self.ledger_path.exists())
        # The capture root's contract -- "nothing written for a non-GM
        # connection" -- stays literally true because the ledger is not in
        # it.  Here the capture root was never even created.
        self.assertFalse(self.capture_root.exists())
        self.assertEqual(
            self.ledger_path.parent.name, arrival_ledger.LEDGER_DIR_NAME,
        )

    def test_lines_append_in_order_and_do_not_overwrite(self):
        self._record(account="one")
        self._record(account="two")
        lines = self._lines()
        self.assertEqual(len(lines), 2)
        self.assertIn("account=one", lines[0])
        self.assertIn("account=two", lines[1])

    def _mode_bits_are_enforced(self):
        """Does THIS filesystem keep the bits `chmod` was given?

        WHAT THE NEIGHBOURING FILE ACTUALLY DOES, stated correctly here
        after pf-adversary (round `6b1o1r`, finding 5) read the citation
        this docstring used to make: `tests/test_gm_command_capture.py`
        applies its "ASK THE FILESYSTEM, DO NOT ASK `os.name`" rule
        (`:1097-1105`, round `vxr32s`) to whether a NEWLINE IS A LEGAL
        FILENAME CHARACTER, and for the MODE-BIT property it deliberately
        keeps `if os.name == "posix"` (`:401`, `:425`, `:453`, `:461`)
        with a measured explanation above it.  So this probe is a
        DIFFERENT CHOICE from its neighbour, not the neighbour's rule
        being followed: it answers the same question by measurement
        instead of by host name, and it must be defended on its own.

        Why it is still the better one here: `os.name` cannot see a POSIX
        host whose TMPDIR is on a mount that drops mode bits (DrvFs, 9p,
        vfat), where the neighbour goes red for the filesystem rather than
        for the module.  The cost is that the weakening is computed, so
        the verdict is PRINTED (below) rather than left silent.

        Measured in the test's own temporary directory, which is the same
        filesystem as -- not the same directory as -- the ledger root two
        levels under it.
        """
        probe = Path(self.tmp.name) / "mode_probe"
        probe.write_bytes(b"")
        probe.chmod(0o600)
        enforced = stat.S_IMODE(probe.stat().st_mode) == 0o600
        probe.unlink()
        # Say it out loud.  A silently weakened assertion is the failure
        # mode this lane keeps paying for; `-s` or a red run shows which
        # half of the test the host actually ran.
        print(
            "GM_LEDGER_MODE_PROBE enforced=%s platform=%s"
            % ("yes" if enforced else "no", sys.platform)
        )
        return enforced

    def test_file_and_directory_are_owner_only(self):
        # TWO properties, because only one of them is portable and the
        # non-portable one is the one that matters on the server host.
        #
        # (a) WHAT THE MODULE ASKS FOR -- checkable on every OS: the open
        #     of the ledger passes 0o600 and the directory is chmod-ed to
        #     0o700 on every write.  A mutant that drops either call dies
        #     here on Windows as well as on Linux.
        # (b) WHAT THE FILESYSTEM THEN HOLDS -- asserted only where the
        #     probe says the bits survive.  windows-latest ignores them
        #     (measured: gate run 34125840418 read 0o666/0o777 back and
        #     took the whole gate red for it, closing PR #1066), so on a
        #     host like that this half asserts the weaker fact that is
        #     still true there: the file exists and the line landed.
        real_chmod, real_open = arrival_ledger.os.chmod, arrival_ledger.os.open
        with mock.patch.object(
            arrival_ledger.os, "chmod", wraps=real_chmod,
        ) as chmod_spy, mock.patch.object(
            arrival_ledger.os, "open", wraps=real_open,
        ) as open_spy:
            self._record()
        # One `_record()` writes twice (the once-per-process header line,
        # then the arrival line) and each write locks the directory down
        # again, so this pins EVERY call rather than a call count: no write
        # may ask for anything but 0o700 / 0o600, and at least one must
        # have happened (an empty list would otherwise pass vacuously).
        ledger_root = arrival_ledger.ledger_root_for_capture_root(
            self.capture_root,
        )
        self.assertEqual(
            {str(call.args[0]) for call in chmod_spy.call_args_list},
            {str(ledger_root)},
            "the chmod must be aimed at the ledger directory itself",
        )
        chmod_modes = [call.args[1] for call in chmod_spy.call_args_list]
        open_modes = [call.args[2] for call in open_spy.call_args_list]
        self.assertTrue(chmod_modes and open_modes)
        self.assertEqual(
            set(chmod_modes), {0o700},
            "the ledger directory must be chmod-ed 0o700 on every write",
        )
        self.assertEqual(
            set(open_modes), {0o600},
            "the ledger file must be created with mode 0o600",
        )
        if self._mode_bits_are_enforced():
            self.assertEqual(self.ledger_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                self.ledger_path.parent.stat().st_mode & 0o777, 0o700,
            )
        else:
            self.assertTrue(self.ledger_path.is_file())
            self.assertEqual(len(self._lines()), 1)

    def test_a_flood_cannot_spend_the_testers_budget(self):
        # The attack this budget shape exists for, in the form pf-adversary
        # D1 measured: an ORDINARY logged-in player -- not a GM, so its
        # arrivals are `authorized=False`, exactly like the attended
        # tester's own -- floods the ledger before the tester presses
        # EXECUTE.  Split by authorization state, the tester's line is the
        # one that does not fit.  Keyed per account, the flood spends only
        # its own budget.
        for _ in range(arrival_ledger.MAX_LINES_PER_ACCOUNT * 4):
            self._record(account="other_player", authorized=False,
                         outcome="refused_not_gm_account")
        before = len(self._lines())
        for _ in range(3):  # R322B pressed EXECUTE three times
            self.assertIsNotNone(
                self._record(account="panya", authorized=False,
                             outcome="refused_not_gm_account")
            )
        after = self._lines()
        self.assertEqual(len(after), before + 3)
        for line in after[-3:]:
            self.assertIn("account=panya", line)
            self.assertIn("outcome=refused_not_gm_account", line)

    def test_a_peer_inventing_a_new_name_per_frame_shares_one_bucket(self):
        # The other half of a per-account budget: unbounded distinct names
        # would be unbounded disk.  Past MAX_TRACKED_ACCOUNTS, every new
        # name spends from one shared overflow bucket.
        for i in range(arrival_ledger.MAX_TRACKED_ACCOUNTS * 4):
            self._record(account=f"throwaway{i}", authorized=False)
        ceiling = (
            arrival_ledger.MAX_TRACKED_ACCOUNTS * arrival_ledger.MAX_LINES_PER_ACCOUNT
            + arrival_ledger.MAX_OVERFLOW_LINES
        )
        self.assertLessEqual(len(self._lines()), ceiling)

    def test_a_spent_budget_says_so_once_and_then_goes_quiet(self):
        for _ in range(arrival_ledger.MAX_LINES_PER_ACCOUNT):
            self._record(account="attacker", authorized=False)
        full = self._record(account="attacker", authorized=False)
        self.assertIsNotNone(full)
        self.assertTrue(full.startswith(arrival_ledger.LEDGER_FULL_TOKEN))
        self.assertIn("account=attacker", full)
        # ...and exactly once, so the flood cannot turn the announcement
        # itself into the flood.
        self.assertIsNone(self._record(account="attacker", authorized=False))
        self.assertIsNone(self._record(account="attacker", authorized=False))
        self.assertEqual(
            sum(1 for line in self._all_lines()
                if line.startswith(arrival_ledger.LEDGER_FULL_TOKEN)),
            1,
        )

    def test_total_bytes_on_disk_are_bounded_by_the_budgets(self):
        for i in range(arrival_ledger.MAX_TRACKED_ACCOUNTS * 3):
            for _ in range(arrival_ledger.MAX_LINES_PER_ACCOUNT + 2):
                self._record(account=f"{i}" + "a" * 200, authorized=False,
                             outcome="x" * 200)
        buckets = arrival_ledger.MAX_TRACKED_ACCOUNTS + 1
        ceiling = (
            arrival_ledger.MAX_TRACKED_ACCOUNTS * arrival_ledger.MAX_LINES_PER_ACCOUNT
            + arrival_ledger.MAX_OVERFLOW_LINES
            + buckets  # one "budget spent" announcement per bucket
            + 1        # the opened header
        ) * (arrival_ledger.MAX_LINE_LENGTH + 1)
        self.assertLessEqual(self.ledger_path.stat().st_size, ceiling)

    def test_a_short_write_is_finished_not_reported_as_a_whole_line(self):
        # pf-adversary D2: `os.write` returning fewer bytes than asked is
        # not an error and does not raise.  Called once and trusted, it
        # puts half a line on disk, spends budget, and lets the NEXT line
        # run on from the middle of it -- one corrupt line where there
        # should be two good ones.  This lane has fixed this bug three
        # times before in this same package; here the write is looped, so
        # the line still lands whole.
        self._record(account="gm1")  # spend the once-per-process header
        real_write = arrival_ledger.os.write
        calls = []

        def short_first(fd, data):
            calls.append(data)
            if len(calls) == 1:
                return real_write(fd, data[:10])
            return real_write(fd, data)

        with mock.patch.object(arrival_ledger.os, "write", short_first):
            self.assertIsNotNone(self._record(account="gm1"))
        self.assertGreater(len(calls), 1)  # it really was a short write
        whole = [line for line in self._lines()
                 if line.endswith("outcome=captured")]
        self.assertEqual(len(whole), 2)
        for line in whole:
            self.assertTrue(line.startswith(arrival_ledger.LEDGER_LINE_TOKEN + " "))

    def test_a_write_that_stops_making_progress_spends_no_budget(self):
        # The half of D2 the loop cannot finish: a descriptor that accepts
        # nothing.  The caller must be told False (no budget spent) rather
        # than handed a line it can quote as written.
        self._record(account="gm1")
        with mock.patch.object(arrival_ledger.os, "write", return_value=0):
            self.assertIsNone(self._record(account="gm1"))
        self.assertEqual(len(self._lines()), 1)
        self.assertIsNotNone(self._record(account="gm1"))
        self.assertEqual(len(self._lines()), 2)

    def test_an_unusable_capture_root_costs_the_line_not_the_caller(self):
        # pf-adversary D5: before this module existed, the non-GM branch of
        # the gate chain never touched `capture_root` at all, so a caller
        # that passed a bad one still got a clean refusal.  Turning that
        # into a TypeError out of the lane hook would lose the refusal
        # event and the console line together.
        self.assertIsNone(
            arrival_ledger.record_arrival(
                0x51E9, "gm1", 1, "captured",
                authorized=False, capture_root=None, now_ts=0,
            )
        )

    def test_an_existing_world_writable_ledger_dir_is_locked_down(self):
        # pf-adversary D6: `makedirs(..., exist_ok=True)` never chmods a
        # directory that already exists, and an operator following a ticket
        # ("look in capture/gm_arrival_ledger") is exactly who creates it
        # by hand first.
        #
        # Same two-property split as `test_file_and_directory_are_owner_only`
        # above, and for the same measured reason: on windows-latest the
        # `chmod(0o777)` below does not take either, so the assertion that
        # the module locked it back down read 0o777 != 0o700 and took the
        # gate red.  What the module DOES (it chmods an existing directory
        # rather than trusting `makedirs(exist_ok=True)`) is checkable
        # everywhere; what the directory then HOLDS is only checkable
        # where the probe says the bits survive.
        root = arrival_ledger.ledger_root_for_capture_root(self.capture_root)
        root.mkdir(parents=True)
        root.chmod(0o777)
        real_chmod = arrival_ledger.os.chmod
        with mock.patch.object(
            arrival_ledger.os, "chmod", wraps=real_chmod,
        ) as chmod_spy:
            self._record()
        chmod_calls = [
            (str(call.args[0]), call.args[1])
            for call in chmod_spy.call_args_list
        ]
        self.assertTrue(chmod_calls)
        self.assertEqual(
            set(chmod_calls), {(str(root), 0o700)},
            "an existing ledger directory must still be locked down",
        )
        if self._mode_bits_are_enforced():
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
        else:
            self.assertTrue(self.ledger_path.is_file())

    def test_every_line_carries_the_pid_that_wrote_it(self):
        # pf-adversary (round `6b1o1r`) closed its report with the question
        # this answers: with the pid only on the header, attribution is
        # POSITIONAL, and this file is append-only and shared by every
        # process using the same relative capture root.  Boot the server,
        # run pytest in another terminal, then press EXECUTE: the real
        # arrival lands after pytest's header and the positional rule
        # blames pytest for the tester's own frame.
        self._record()
        with mock.patch.object(arrival_ledger.os, "getpid", return_value=4242):
            self._record(account="other")
        lines = self._lines()
        self.assertIn(f"pid={os.getpid()}", lines[0])
        self.assertIn("pid=4242", lines[1])
        # ...and the budget-exhaustion announcement too: it is the line a
        # reader meets when the evidence they wanted is missing.
        for _ in range(arrival_ledger.MAX_LINES_PER_ACCOUNT + 2):
            self._record(account="flood")
        full = [
            line for line in self._all_lines()
            if line.startswith(arrival_ledger.LEDGER_FULL_TOKEN)
        ]
        self.assertTrue(full)
        self.assertIn(f"pid={os.getpid()}", full[0])

    def test_each_ledger_root_this_process_touches_gets_its_own_header(self):
        # pf-adversary (round `6b1o1r`, finding 1): the announcement flag
        # was ONE process-global boolean while the header is per
        # DIRECTORY.  A process that wrote to a second root gave it no
        # header at all -- no pid, no absolute path -- and the single
        # console line named the FIRST root, pointing the reader at a
        # directory that does not hold the arrival.  That is D3/D7 (a
        # working directory the reader is not looking under) arriving
        # through the other door.
        second_capture = Path(self.tmp.name) / "second" / "gm_command_capture"
        arrival_ledger.record_arrival(
            0x51E9, "gm1", 1, "captured",
            authorized=True, capture_root=self.capture_root, now_ts=0,
        )
        arrival_ledger.record_arrival(
            0x51E9, "gm2", 1, "captured",
            authorized=True, capture_root=second_capture, now_ts=0,
        )
        second_path = (
            arrival_ledger.ledger_root_for_capture_root(second_capture)
            / arrival_ledger.LEDGER_FILENAME
        )
        second_lines = second_path.read_text("ascii").splitlines()
        self.assertTrue(
            second_lines[0].startswith(arrival_ledger.LEDGER_OPENED_TOKEN),
            second_lines,
        )
        self.assertIn(
            f"path={second_path.parent.resolve()}", second_lines[0],
        )
        # ...and still exactly one header per root, not one per arrival.
        arrival_ledger.record_arrival(
            0x51E9, "gm2", 1, "captured",
            authorized=True, capture_root=second_capture, now_ts=0,
        )
        self.assertEqual(
            sum(1 for line in second_path.read_text("ascii").splitlines()
                if line.startswith(arrival_ledger.LEDGER_OPENED_TOKEN)),
            1,
        )

    def test_a_console_that_raises_costs_the_console_line_not_the_arrival(self):
        # pf-adversary (round `6b1o1r`, finding 2): the `print` of the
        # header sits inside a `try/except OSError`, and neither way out
        # of a broken console is an OSError -- a closed stdout raises
        # ValueError, a cp874 console handed a path it cannot encode
        # raises UnicodeEncodeError.  Either one escaped into
        # `gm/dispatch.py`, losing the arrival line that had not been
        # written yet, and on the `except BaseException` arm REPLACING the
        # original exception with this one.
        for boom in (ValueError("I/O operation on closed file."),
                     UnicodeEncodeError("charmap", "x", 0, 1, "no mapping")):
            with self.subTest(boom=type(boom).__name__):
                arrival_ledger.reset_for_tests()
                with mock.patch("builtins.print", side_effect=boom):
                    line = self._record()
                self.assertIsNotNone(line)
                self.assertEqual(len(self._lines()), 1)
                self.ledger_path.unlink()

    def test_a_write_that_dies_after_partial_progress_spends_no_budget(self):
        # pf-adversary (round `6b1o1r`, finding 4): the repair arm for an
        # `os.write` that RAISES after partial progress had never
        # executed under this suite, and a mutant turning its `return
        # False` into `return True` -- i.e. reporting a half-written line
        # as landed, spending the budget for it -- survived every test.
        # The covered route was only the `count <= 0` one.
        real_write = arrival_ledger.os.write
        calls = []

        def _dies_after_one_chunk(fd, data):
            # The repair write of the bare newline is allowed through: it
            # is the module's documented way of ending the partial line so
            # the NEXT line does not get glued onto it.  (Measured while
            # writing this test: refusing it too produces exactly that
            # glued line, `GMGM_VITAL_ARRIVED ...`, which is the failure
            # the repair arm exists to avoid.)
            if data == b"\n":
                return real_write(fd, data)
            calls.append(data)
            if len(calls) == 1:
                return real_write(fd, data[:2])
            raise OSError("volume went away mid-line")

        self._record(account="gm1")
        with mock.patch.object(
            arrival_ledger.os, "write", side_effect=_dies_after_one_chunk,
        ):
            self.assertIsNone(self._record(account="gm1"))
        # The budget was not spent on the half-written line: the arrival
        # after the disk recovers still gets a full one.
        self.assertIsNotNone(self._record(account="gm1"))
        self.assertEqual(len(self._lines()), 2)

    def test_a_write_failure_costs_the_line_not_the_caller(self):
        with mock.patch.object(
            arrival_ledger.os, "open", side_effect=OSError("read-only volume"),
        ):
            self.assertIsNone(self._record())
        self.assertEqual(self._lines(), [])
        # ...and spends no budget, so the arrival after the disk recovers
        # is still recorded.
        self.assertIsNotNone(self._record())
        self.assertEqual(len(self._lines()), 1)

    def test_concurrent_arrivals_produce_whole_lines_and_an_exact_count(self):
        threads = [
            threading.Thread(target=self._record, kwargs={"account": "gm1"})
            for _ in range(arrival_ledger.MAX_LINES_PER_ACCOUNT)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        lines = self._lines()
        self.assertEqual(len(lines), arrival_ledger.MAX_LINES_PER_ACCOUNT)
        for line in lines:
            self.assertTrue(line.startswith(arrival_ledger.LEDGER_LINE_TOKEN + " "))
            self.assertIn("outcome=captured", line)


class DispatchRecordsEveryArrivalTests(unittest.TestCase):
    """The wiring: one line per arrival at gm/dispatch.py, every outcome."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.capture_root = Path(self.tmp.name) / "capture" / "gm_command_capture"
        self.config = Path(self.tmp.name) / "gm_accounts.json"
        self.config.write_text(json.dumps({"gm_accounts": ["gm1"]}), "utf-8")
        arrival_ledger.reset_for_tests()
        self.addCleanup(arrival_ledger.reset_for_tests)
        gm_dispatch.reset_rate_limit_state_for_tests()
        self.addCleanup(gm_dispatch.reset_rate_limit_state_for_tests)

    def _lines(self):
        path = (
            arrival_ledger.ledger_root_for_capture_root(self.capture_root)
            / arrival_ledger.LEDGER_FILENAME
        )
        if not path.exists():
            return []
        return [
            line for line in path.read_text("ascii").splitlines()
            if line.startswith(arrival_ledger.LEDGER_LINE_TOKEN + " ")
        ]

    def _capture_files(self):
        if not self.capture_root.exists():
            return []
        return sorted(p.name for p in self.capture_root.iterdir())

    def _run(self, account="gm1", payload=b"\x01\x02\x03"):
        return gm_dispatch.handle_gm_run_command_vital(
            account, payload,
            config_path=str(self.config),
            capture_root=self.capture_root,
            now_ts=0,
        )

    def test_refused_non_gm_arrival_is_recorded_and_capture_root_stays_empty(self):
        # THE WHOLE POINT.  This is the branch R322B could not tell apart
        # from "the client never sent anything".
        outcome = self._run(account="player1")
        self.assertFalse(outcome.authorized)
        self.assertEqual(outcome.refusal_reason, gm_dispatch.REFUSAL_NOT_GM)
        self.assertEqual(self._capture_files(), [])
        lines = self._lines()
        self.assertEqual(len(lines), 1)
        self.assertIn("id=0x51E9", lines[0])
        self.assertIn("account=player1", lines[0])
        self.assertIn("authorized=no", lines[0])
        self.assertIn(f"outcome=refused_{gm_dispatch.REFUSAL_NOT_GM}", lines[0])

    def test_authorized_capture_is_recorded_as_captured(self):
        outcome = self._run()
        self.assertIsNotNone(outcome.captured_path)
        lines = self._lines()
        self.assertEqual(len(lines), 1)
        self.assertIn("outcome=captured", lines[0])
        self.assertIn("authorized=yes", lines[0])
        self.assertEqual(len(self._capture_files()), 1)

    def test_rate_limited_arrival_is_recorded_with_its_own_reason(self):
        for _ in range(gm_dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW):
            self._run()
        self.assertEqual(
            self._run().refusal_reason, gm_dispatch.REFUSAL_RATE_LIMITED,
        )
        self.assertIn(
            f"outcome=refused_{gm_dispatch.REFUSAL_RATE_LIMITED}", self._lines()[-1],
        )

    def test_an_arrival_that_raises_is_still_recorded_and_still_raises(self):
        with self.assertRaises(ValueError):
            self._run(account="")
        lines = self._lines()
        self.assertEqual(len(lines), 1)
        self.assertIn("outcome=raised_ValueError", lines[0])
        self.assertIn("account=unnamed", lines[0])
        # pf-adversary D4: the chain raised, so whether this account is in
        # the allowlist is exactly what this call site does NOT know.
        self.assertIn("authorized=unknown", lines[0])

    def test_a_non_bytes_payload_records_a_length_it_cannot_measure(self):
        with self.assertRaises(TypeError):
            self._run(payload="not bytes")
        self.assertIn("outcome=raised_TypeError", self._lines()[0])
        self.assertIn("len=-1", self._lines()[0])

    def test_the_second_opcode_records_its_own_id(self):
        gm_dispatch.handle_activity_cheat_code_vital(
            "gm1", b"\x01",
            config_path=str(self.config),
            capture_root=self.capture_root,
            now_ts=0,
        )
        self.assertIn("id=0x6CEC", self._lines()[0])
        self.assertIn("name=Activity_CheatCodeVital", self._lines()[0])

    def test_no_payload_byte_ever_reaches_the_ledger(self):
        # A capture file holds the bytes; the ledger holds only their
        # count.  An unauthenticated peer must not be able to put a chosen
        # byte string on disk through this path.
        self._run(account="player1", payload=b"SECRETMARKER" * 8)
        text = "\n".join(self._lines())
        self.assertNotIn("SECRETMARKER", text)
        self.assertIn("len=96", text)

    def test_a_broken_ledger_does_not_break_dispatch(self):
        with mock.patch.object(
            arrival_ledger.os, "makedirs", side_effect=OSError("full disk"),
        ):
            outcome = self._run()
        self.assertIsNotNone(outcome.captured_path)
        self.assertEqual(self._lines(), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
