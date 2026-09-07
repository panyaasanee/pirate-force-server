"""The GM stuck-capture console line, read back off the RETAINED FILE ON DISK.

WHAT THIS FILE IS FOR, AND WHY IT IS NOT A FOURTH COPY OF AN EXISTING TEST.
`tests/test_gm_command_capture.py` already pins that `_best_effort_unlink`
prints ONE line when the capture path carries a newline or a `U+0085` (NEL),
and `test_every_character_str_splitlines_breaks_on_is_folded` generalises it.
All of those read the line out of an `io.StringIO`.  `io.StringIO` performs no
newline translation and stores `str`, so it cannot answer the question an
operator actually asks, which is about the file they open in an editor:

    what is in `server_console_live.err.txt`, as BYTES, after the process that
    wrote it has exited?

chief said this in the letter that shipped the seam this file uses
(`pf_bridge/notes_to_chief/20260907_1109_FROM_CHIEF-to-LANE-GM-core-request-`
`gm-064-wired.md`, item 2): his own `U+0085` test uses `io.StringIO`, so it
proves the mirror does not fold, and it does NOT prove the newline behaviour of
the real file.  He declined to claim that half on this lane's behalf.  This
lane accepted the debt in `20260907_1156_LANE-GM-TO-CHIEF-gm-064-seam-received-`
`and-not-used-yet.md` and left it unpaid for a round.  This file pays it.

WHAT IS ACTUALLY DIFFERENT HERE.  Nothing between the producer and the disk is
stood in for.  The console is a real `RuntimeConsole`, so `sys.stderr` is the
real `build_console_mirror` object over the real retained handle, opened the
way the shipped runtime opens it (`"x"`, `encoding="utf-8"`, `newline="\\n"`,
`buffering=1`).  The line is composed by the shipped `_best_effort_unlink`.
The assertions then read the closed file twice: once as `bytes`, which is the
only view that can see a newline translation, and once as text, which is the
view a grep tool has.  The one thing simulated is the failure that makes the
producer print at all -- `os.unlink` raising, the Windows sharing violation the
whole stuck-capture path exists for -- because a host that unlinks happily
cannot be argued into that state (`tests/test_gm_command_capture.py:960` makes
the same choice, for the same reason, and round `vxr32s` records the Windows
gate closing `#970` when an earlier test tried to build the hostile name on the
filesystem instead).

THE HALF THIS FILE DOES NOT MEASURE, NAMED SO NOBODY UPGRADES IT LATER.  The
reason `newline="\\n"` matters at all is Windows, where the default would turn
each `\\n` into `\\r\\n` on the way to disk.  No Windows host has run this: the
byte assertions below are taken on whatever host runs the suite, and on Linux a
translating open and a non-translating open produce the same bytes.  So
`test_the_newline_argument_is_what_decides_the_bytes_on_disk` measures the
MECHANISM (that the argument, not the platform, chooses) and
`test_the_runtime_still_opens_the_retained_file_without_translation` is a
tripwire on the shipped value.  Neither is a Windows measurement, and a green
run here is not evidence about a Windows host.  Same rule this lane wrote into
`test_gm_login_scene_stage_descriptors.py` under COO ruling `20260907_1245`:
where a platform cannot be measured, say so in the file rather than let the
colour of the run say something else.
"""

from __future__ import annotations

import io
import os
import pathlib
import re
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pirateforce_foundation import runtime_console  # noqa: E402
from pirateforce_foundation.gm import command_capture  # noqa: E402

# The runtime's own names for the two retained files, spelled here on purpose:
# if `RuntimeConsole` renames them, an operator's runbook breaks and this file
# should say so rather than follow along quietly.
RETAINED_ERR = "server_console_live.err.txt"

LF = 0x0A
CR = 0x0D
NEL_UTF8 = b"\xc2\x85"


class RetainedTailTests(unittest.TestCase):
    """One GM stuck line, written by the shipped producer, read off disk."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = pathlib.Path(holder.name)

    def stuck_line_into_a_real_retained_file(self, path):
        """Drive the shipped printer into a real `RuntimeConsole` and close it.

        Returns the retained stderr file's bytes.  The console streams are
        `io.StringIO` because a test process has no console to write to -- that
        is the CONSOLE half of the mirror, and it is not what this file is
        about.  The RETAINED half, which is the half being measured, is a real
        file the runtime opened itself.
        """
        log_root = self.tmp / "logs"
        console_out, console_err = io.StringIO(), io.StringIO()
        console = runtime_console.RuntimeConsole(
            log_root, console_out, console_err, close_console_streams=False,
        )
        try:
            with mock.patch.object(
                command_capture.os, "unlink",
                side_effect=OSError("simulated Windows sharing violation"),
            ), mock.patch.object(command_capture.time, "sleep"):
                removed = command_capture._best_effort_unlink(
                    path, account_name="panya", attempted_bytes=1,
                )
        finally:
            # Restores sys.stdout/sys.stderr and closes the retained handles;
            # the file is only complete once this has run.
            console.close()
        self.assertFalse(removed, "the unlink stand-in did not refuse")
        return (log_root / RETAINED_ERR).read_bytes()

    def test_a_nel_in_the_capture_path_is_one_line_in_the_file_on_disk(self):
        """The debt chief declined to claim: the real file, not a `StringIO`.

        The hostile path carries a NEL followed by a complete forged copy of
        the console token.  If the producer's fold were gone, this file would
        hold two lines to `str.splitlines()` -- the reader every grep-the-
        console tool in this project uses -- and the second would open with
        the real token, which is the whole attack.
        """
        forged = "\x85GM_CAPTURE_UNLINK_STUCK path=C:\\clean account=admin"
        hostile = self.tmp / f"cap{forged}" / "capture" / "x.bin"

        raw = self.stuck_line_into_a_real_retained_file(hostile)

        self.assertEqual(
            raw.count(bytes([LF])), 1,
            f"the retained file holds more than one line terminator: {raw!r}",
        )
        self.assertNotIn(
            NEL_UTF8, raw,
            "U+0085 reached the retained file as itself; the producer's fold "
            "is what keeps a NEL from becoming a line break for `splitlines()`",
        )
        text = raw.decode("utf-8")
        self.assertEqual(
            len(text.splitlines()), 1,
            f"`splitlines()` sees more than one line in the file: {text!r}",
        )
        self.assertTrue(
            text.startswith(command_capture._UNLINK_STUCK_CONSOLE_TOKEN),
            f"the retained file does not open with the real token: {text!r}",
        )
        self.assertIn(
            "\\x85", text,
            "the NEL is not visible as an escape, so an operator reading this "
            "file cannot see that one was sent",
        )

    def test_a_newline_in_the_capture_path_is_one_line_in_the_file_on_disk(self):
        """The same question for `\\n`, which is the character that would
        actually be translated on the way to disk if the open said so.

        Kept separate from the NEL case rather than parametrised: NEL is about
        the PRODUCER's fold and `\\n` is about the FILE's newline handling, and
        a single case covering both would go red for either reason.
        """
        forged = "\nGM_CAPTURE_UNLINK_STUCK path=C:\\clean account=admin"
        hostile = self.tmp / f"cap{forged}" / "capture" / "x.bin"

        raw = self.stuck_line_into_a_real_retained_file(hostile)

        self.assertEqual(
            raw.count(bytes([LF])), 1,
            f"the retained file holds more than one line terminator: {raw!r}",
        )
        self.assertEqual(
            raw.count(bytes([CR])), 0,
            "the retained file carries a CR: the runtime's `newline` argument "
            f"stopped deciding and the platform started: {raw!r}",
        )
        text = raw.decode("utf-8")
        self.assertEqual(len(text.splitlines()), 1, repr(text))
        self.assertIn("\\x0a", text)

    def test_the_console_half_and_the_retained_half_hold_the_same_line(self):
        """The mirror's promise, checked where the two halves are different
        KINDS of object -- one an in-memory buffer, the other a file that has
        been encoded, written, flushed and closed.

        chief's `test_a_line_breaking_control_stays_on_one_line_through_the_
        mirror` asserts this equality with two `StringIO`s, where it is nearly
        free.  Here the right-hand side made a round trip through utf-8 and the
        filesystem, so an encoding or a translation that changed the text would
        show up as an inequality rather than as a passing test somewhere else.
        """
        log_root = self.tmp / "logs"
        console_out, console_err = io.StringIO(), io.StringIO()
        console = runtime_console.RuntimeConsole(
            log_root, console_out, console_err, close_console_streams=False,
        )
        try:
            with mock.patch.object(
                command_capture.os, "unlink",
                side_effect=OSError("simulated Windows sharing violation"),
            ), mock.patch.object(command_capture.time, "sleep"):
                command_capture._best_effort_unlink(
                    self.tmp / "cap\x85x" / "capture" / "x.bin",
                    account_name="\u0e17\u0e14\u0e2a\u0e2d\u0e1a",
                    attempted_bytes=1,
                )
        finally:
            console.close()

        on_disk = (log_root / RETAINED_ERR).read_bytes().decode("utf-8")
        self.assertEqual(console_err.getvalue(), on_disk)
        self.assertIn(
            "\u0e17\u0e14\u0e2a\u0e2d\u0e1a", on_disk,
            "a Thai GM account name did not survive to the retained file; an "
            "operator grepping this file for their own name would find "
            "nothing (`gm/login_scene_override.py`'s `console_safe` scar)",
        )

    def test_the_newline_argument_is_what_decides_the_bytes_on_disk(self):
        """MECHANISM, not a Windows measurement.

        Two files, same text, same host, different `newline` argument: the
        bytes differ.  That is the whole content of the claim "`newline=\\n`
        is what stops the retained file becoming CRLF" -- the argument, and not
        the platform, chooses.  What a real Windows host does with the DEFAULT
        is not measured here and is not measurable here.
        """
        as_shipped = self.tmp / "as_shipped.txt"
        translating = self.tmp / "translating.txt"
        with as_shipped.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write("one\ntwo\n")
        with translating.open("w", encoding="utf-8", newline="\r\n") as handle:
            handle.write("one\ntwo\n")

        self.assertEqual(as_shipped.read_bytes(), b"one\ntwo\n")
        self.assertEqual(translating.read_bytes(), b"one\r\ntwo\r\n")
        self.assertEqual(
            len(as_shipped.read_bytes()) + 2, len(translating.read_bytes()),
            "the two opens produced the same bytes, so this case is no longer "
            "measuring that the argument decides anything",
        )

    def test_the_runtime_still_opens_the_retained_file_without_translation(self):
        """TRIPWIRE on chief's file, which this lane does not write to.

        `runtime_console.py` is chief's territory.  This does not assert what
        it should say; it asserts that what it DOES say has not moved out from
        under the byte assertions above.  If this goes red, the right response
        is to re-measure this file's claims against the new open, not to edit
        the number here.
        """
        source = pathlib.Path(runtime_console.__file__).read_text(
            encoding="utf-8",
        )
        opens = re.findall(
            r'\.open\(\s*"x",\s*encoding="utf-8",\s*newline="\\n",'
            r'\s*buffering=1,\s*\)',
            source,
        )
        self.assertEqual(
            len(opens), 2,
            "the two retained-file opens in `runtime_console.py` no longer "
            "read `newline=\"\\\\n\"`; the on-disk byte counts in this file "
            "were measured against that argument",
        )
        console = runtime_console.RuntimeConsole(
            self.tmp / "probe", io.StringIO(), io.StringIO(),
            close_console_streams=False,
        )
        try:
            # Closed in `finally` rather than left to the garbage collector:
            # this lane spent round `da16dj` on a descriptor fence for exactly
            # this module, and a test that leaks two handles while asserting a
            # name would be arguing against its own work.
            self.assertEqual(
                console.stderr_path.name, RETAINED_ERR,
                "the retained stderr file was renamed",
            )
        finally:
            console.close()


class TheHarnessItselfWorksTests(unittest.TestCase):
    """The producer really is the thing being driven, not a lookalike.

    Without this, every assertion above could be satisfied by a retained file
    that never received the GM line at all -- `raw.count(b"\\n") == 1` is also
    true of a file holding one unrelated line, and `assertNotIn(NEL)` is true
    of an empty one.  pf-adversary round `fx4p76` D2 was exactly this shape in
    another file: a class that watched the reader instead of the subject.
    """

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = pathlib.Path(holder.name)

    def test_the_retained_file_is_empty_when_the_producer_does_not_print(self):
        log_root = self.tmp / "logs"
        console = runtime_console.RuntimeConsole(
            log_root, io.StringIO(), io.StringIO(), close_console_streams=False,
        )
        try:
            pass
        finally:
            console.close()
        self.assertEqual((log_root / RETAINED_ERR).read_bytes(), b"")

    def test_the_producer_prints_nothing_when_the_unlink_succeeds(self):
        """The stuck line is conditional, and the condition is real.

        If `_best_effort_unlink` printed unconditionally, the cases above would
        pass while measuring a line nobody in production ever sees.
        """
        log_root = self.tmp / "logs"
        target = self.tmp / "capture" / "x.bin"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"\x00")
        console = runtime_console.RuntimeConsole(
            log_root, io.StringIO(), io.StringIO(), close_console_streams=False,
        )
        try:
            removed = command_capture._best_effort_unlink(
                target, account_name="panya", attempted_bytes=1,
            )
        finally:
            console.close()
        self.assertTrue(removed, "the real unlink refused; this host is not "
                        "the one this case was written for")
        self.assertEqual((log_root / RETAINED_ERR).read_bytes(), b"")
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
