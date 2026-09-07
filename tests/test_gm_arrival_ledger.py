"""GT-279 / P-3: an empty capture folder must stop meaning four things at once.

The attended boot R322B pressed the real client's GM EXECUTE button three
times and afterwards ``capture/gm_command_capture/`` was empty -- which is
the same observation whether the client sent nothing, sent a different
vital id, never reached ``gm/dispatch.py``, or reached it and was refused
there.  ``gm/arrival_ledger.py`` splits the last of those four off from the
other three by writing one bounded line per arrival, whatever the outcome.

These tests pin the two halves that make that line trustworthy:

* the SHAPE (one line, ASCII, no payload bytes, every field capped), and
* the BOUNDS (a flood from unauthenticated peers cannot spend the budget a
  real GM's line needs -- denial of evidence by flooding is the obvious
  attack on a file whose whole value is that a line is present).

and the wiring in ``gm/dispatch.py``: every exit of the gate chain records
exactly one line, including the exits that raise, and the capture root
itself stays untouched for a non-GM connection.
"""
from __future__ import annotations

import json
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

    def _lines(self):
        if not self.ledger_path.exists():
            return []
        return self.ledger_path.read_text("ascii").splitlines()

    def _record(self, account="gm1", authorized=True, outcome="captured"):
        return arrival_ledger.record_arrival(
            0x51E9, account, 3, outcome,
            authorized=authorized, capture_root=self.capture_root, now_ts=0,
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

    def test_file_and_directory_are_owner_only(self):
        self._record()
        self.assertEqual(self.ledger_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.ledger_path.parent.stat().st_mode & 0o777, 0o700)

    def test_unauthorized_flood_cannot_spend_the_authorized_budget(self):
        # The attack this budget split exists for: a peer that is not a GM
        # sends thousands of frames before the tester presses EXECUTE.  If
        # both kinds shared one budget, the ONE line the attended sheet
        # needs would be the line that does not fit.
        for _ in range(arrival_ledger.MAX_UNAUTHORIZED_LINES * 4):
            self._record(account="attacker", authorized=False,
                         outcome="refused_not_gm_account")
        before = len(self._lines())
        self.assertIsNotNone(self._record(account="gm1", authorized=True))
        after = self._lines()
        self.assertEqual(len(after), before + 1)
        self.assertIn("account=gm1", after[-1])
        self.assertIn("authorized=yes", after[-1])

    def test_a_spent_budget_says_so_once_and_then_goes_quiet(self):
        for _ in range(arrival_ledger.MAX_UNAUTHORIZED_LINES):
            self._record(account="attacker", authorized=False)
        full = self._record(account="attacker", authorized=False)
        self.assertIsNotNone(full)
        self.assertTrue(full.startswith(arrival_ledger.LEDGER_FULL_TOKEN))
        self.assertIn("authorized=no", full)
        # ...and exactly once, so the flood cannot turn the announcement
        # itself into the flood.
        self.assertIsNone(self._record(account="attacker", authorized=False))
        self.assertIsNone(self._record(account="attacker", authorized=False))
        self.assertEqual(
            sum(1 for line in self._lines()
                if line.startswith(arrival_ledger.LEDGER_FULL_TOKEN)),
            1,
        )

    def test_total_bytes_on_disk_are_bounded_by_the_budgets(self):
        for _ in range(arrival_ledger.MAX_UNAUTHORIZED_LINES * 2):
            self._record(account="a" * 200, authorized=False, outcome="x" * 200)
        for _ in range(arrival_ledger.MAX_AUTHORIZED_LINES * 2):
            self._record(account="b" * 200, authorized=True, outcome="y" * 200)
        ceiling = (
            arrival_ledger.MAX_AUTHORIZED_LINES
            + arrival_ledger.MAX_UNAUTHORIZED_LINES
            + 2  # the two "budget spent" announcements
        ) * (arrival_ledger.MAX_LINE_LENGTH + 1)
        self.assertLessEqual(self.ledger_path.stat().st_size, ceiling)

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
            threading.Thread(target=self._record, kwargs={"account": f"gm{i}"})
            for i in range(arrival_ledger.MAX_AUTHORIZED_LINES)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        lines = self._lines()
        self.assertEqual(len(lines), arrival_ledger.MAX_AUTHORIZED_LINES)
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
        return path.read_text("ascii").splitlines()

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
