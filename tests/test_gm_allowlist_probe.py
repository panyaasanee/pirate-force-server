"""LANE-GM: the refusal that closed GT-279's attended boot must say why.

Round `wxh2tw`.  R322B (pf_bridge `notes_to_chief/20260907_0123_KA1A-R322B-
RESULTS-*`) put three real `GM_RunGMCommandVital` frames on the wire from
the real client's EXECUTE button and got a silent server and an empty disk,
and the letter had to close with an open question about where the frames
went.  They were refused, correctly, by an allowlist whose file is not in
the tree.  These tests pin the parts of that answer that can regress.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Same bootstrap every sibling test module in this directory carries. Without
# it this file passes only in a full-suite run, because another module happens
# to insert the path first -- `pytest tests/test_gm_allowlist_probe.py` alone
# gives `Interrupted: 1 error during collection`, which is how a documented
# single-file command in a GT ticket or a PR body dies on someone else's
# machine (LANE-CS measured exactly that on `tests/test_skill_learn_step_
# headless.py`, `pf_bridge#1629`).
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import accounts, allowlist_probe
from pirateforce_foundation.gm.allowlist_probe import (
    GM_ALLOWLIST_CONSOLE_TOKEN,
    announce_not_gm_once,
    describe_gm_allowlist,
    format_allowlist_refusal_line,
)


def _fields(line: str) -> dict:
    """The reading rule docs/GM_LANE.md gives operators, as code.

    Deliberately a second, independent copy of the parser in
    `tests/test_gm_command_capture.py` rather than an import of it: these two
    console lines are written by two modules, and a shared helper that drifted
    with one of them would hide exactly the divergence this asserts against.
    """
    fields: dict = {}
    i = 0
    while i < len(line):
        eq = line.find('="', i)
        if eq == -1:
            break
        key = line[line.rfind(" ", 0, eq) + 1:eq]
        i = eq + 2
        out = []
        while i < len(line):
            if line[i] == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    out.append('"')
                    i += 2
                    continue
                i += 1
                break
            out.append(line[i])
            i += 1
        fields.setdefault(key, "".join(out))
    return fields


class GmAllowlistProbeTests(unittest.TestCase):
    def setUp(self):
        allowlist_probe.reset_for_tests()
        self.addCleanup(allowlist_probe.reset_for_tests)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    # -- the pin that makes the line trustworthy at all --------------------

    def test_the_probe_resolves_the_same_file_gm_accounts_would_open(self):
        # If these two ever disagree, the line names a path the server never
        # opened -- which is worse than printing nothing, because it sends
        # the operator to edit the wrong file and then disbelieve the result.
        explicit = Path(self._tmp.name) / "explicit.json"
        with mock.patch.dict(os.environ, {accounts.ENV_OVERRIDE: "/env/path.json"}):
            for arg in (str(explicit), None):
                with self.subTest(config_path=arg):
                    self.assertEqual(
                        describe_gm_allowlist(arg).resolved_path,
                        accounts._resolve_path(arg),
                    )
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                describe_gm_allowlist(None).resolved_path,
                accounts._resolve_path(None),
            )

    def test_the_source_field_names_which_of_the_three_rules_chose_the_path(self):
        target = Path(self._tmp.name) / "a.json"
        self.assertEqual(describe_gm_allowlist(target).source, "argument")
        with mock.patch.dict(os.environ, {accounts.ENV_OVERRIDE: str(target)}):
            self.assertEqual(describe_gm_allowlist(None).source, "env")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(describe_gm_allowlist(None).source, "default")

    # -- the three states an operator has to be able to tell apart ---------

    def test_a_missing_allowlist_reads_as_missing_and_not_as_zero_accounts(self):
        # This is the state the shipped tree is in, and the state R322B was
        # in: `config/gm_accounts.json` does not exist. "missing" tells the
        # operator to create the file; "0" would tell them to edit a file
        # that is not there.
        status = describe_gm_allowlist(Path(self._tmp.name) / "nope.json")
        self.assertFalse(status.exists)
        line = format_allowlist_refusal_line(status, "admin", io.StringIO())
        self.assertIn("accounts=missing", line)

    def test_a_malformed_allowlist_reads_as_unreadable_and_not_as_zero(self):
        # `gm/accounts.py` raises on a malformed config on purpose, so a typo
        # does not silently resolve to "nobody is GM". That intent survives
        # only if this line keeps the two apart as well.
        bad = Path(self._tmp.name) / "bad.json"
        bad.write_text('{"gm_accounts": "panya"}', encoding="utf-8")
        status = describe_gm_allowlist(bad)
        self.assertTrue(status.exists)
        self.assertIsNone(status.account_count)
        self.assertIn("accounts=unreadable", format_allowlist_refusal_line(
            status, "admin", io.StringIO(),
        ))

    def test_a_populated_allowlist_reports_a_count_and_never_the_names(self):
        good = Path(self._tmp.name) / "good.json"
        good.write_text(
            json.dumps({"gm_accounts": ["panya", "thongchai"]}), encoding="utf-8",
        )
        line = format_allowlist_refusal_line(
            describe_gm_allowlist(good), "admin", io.StringIO(),
        )
        self.assertIn("accounts=2", line)
        # The console is not the place to enumerate who holds GM.
        self.assertNotIn("panya", line)
        self.assertNotIn("thongchai", line)

    # -- the hardening this line inherits rather than re-types -------------

    def test_a_hostile_account_name_cannot_forge_a_second_line_or_a_field(self):
        # The account name is matched verbatim against the allowlist and
        # nothing in this codebase restricts its characters, so it is exactly
        # as operator-controlled as the fields pf-adversary forged on the
        # capture line in rounds `nfbat1` and `vxr32s`. This line reuses those
        # functions; this test is what proves it still does.
        hostile = 'x" allowlist="/etc/passwd" accounts="99\x85GM_COMMAND_REFUSED_NOT_GM'
        line = format_allowlist_refusal_line(
            describe_gm_allowlist(Path(self._tmp.name) / "nope.json"),
            hostile, io.StringIO(),
        )
        self.assertEqual(len(line.splitlines()), 1, line)
        parsed = _fields(line)
        self.assertEqual(parsed["allowlist"], str(Path(self._tmp.name) / "nope.json"))
        self.assertIn("\\x85", parsed["account"])

    def test_the_console_token_is_pinned_to_its_literal_spelling(self):
        # Round `vxr32s` D4: the capture line's token was only ever compared
        # against its own constant, so renaming it left the suite green while
        # docs/GM_LANE.md told operators to grep a word that no longer
        # printed. Same defense, written down before the same bug.
        self.assertEqual(GM_ALLOWLIST_CONSOLE_TOKEN, "GM_COMMAND_REFUSED_NOT_GM")
        line = format_allowlist_refusal_line(
            describe_gm_allowlist(Path(self._tmp.name) / "nope.json"),
            "admin", io.StringIO(),
        )
        self.assertTrue(line.startswith("GM_COMMAND_REFUSED_NOT_GM "))

    # -- the latch ---------------------------------------------------------

    def test_the_line_prints_once_per_process(self):
        stream = io.StringIO()
        self.assertTrue(announce_not_gm_once("admin", stream=stream))
        for _ in range(5):
            self.assertFalse(announce_not_gm_once("admin", stream=stream))
        self.assertEqual(len(stream.getvalue().splitlines()), 1)

    def test_a_console_that_refuses_the_write_cannot_break_the_refusal_path(self):
        # A diagnostic on a refusal path must never turn a correctly-refused
        # GM command into an exception travelling back up through
        # `lane_hooks.fire()` into the connection handler.
        class Hostile(io.StringIO):
            def write(self, _):
                raise OSError("console gone")

        self.assertFalse(announce_not_gm_once("admin", stream=Hostile()))
        # And the latch must not have been spent on the line that never
        # arrived: a console briefly unwritable at the first refusal would
        # otherwise consume the only line this process ever prints.
        working = io.StringIO()
        self.assertTrue(announce_not_gm_once("admin", stream=working))
        self.assertEqual(len(working.getvalue().splitlines()), 1)

class GmRunCommandHookAnnouncesTests(unittest.TestCase):
    """End to end through the hook runtime.py actually fires."""

    def setUp(self):
        allowlist_probe.reset_for_tests()
        self.addCleanup(allowlist_probe.reset_for_tests)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    class _Session:
        def __init__(self, token):
            self.token = token
            self.events = []

    def _fire(self, token, payload=b""):
        from pirateforce_foundation.lane_hooks import lane_gm_run_command

        session = self._Session(token)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            returned = lane_gm_run_command._on_gm_run_command(session, payload)
        return session, stderr.getvalue(), returned

    def test_a_refused_command_prints_the_line_and_still_sends_no_frame(self):
        # The whole point of GT-279's negative result: from the client side
        # nothing changes -- no reply, no frame, no way to tell a GM-capable
        # server from any other one. The operator's console is the only thing
        # that gains a word.
        with mock.patch.dict(
            os.environ,
            {accounts.ENV_OVERRIDE: str(Path(self._tmp.name) / "nope.json")},
        ):
            session, printed, returned = self._fire("admin")
        self.assertIsNone(returned)
        self.assertEqual(session.events, ["gm_run_command_refused_not_gm_account"])
        self.assertEqual(len(printed.splitlines()), 1, printed)
        self.assertTrue(printed.startswith(GM_ALLOWLIST_CONSOLE_TOKEN))
        self.assertIn("accounts=missing", printed)

    def test_an_authorized_account_captures_and_prints_no_refusal_line(self):
        # The other side of the same latch: the line must be a symptom of the
        # refusal, not something the hook prints on its way past.
        allow = Path(self._tmp.name) / "gm.json"
        allow.write_text(json.dumps({"gm_accounts": ["panya"]}), encoding="utf-8")
        root = Path(self._tmp.name) / "capture"
        from pirateforce_foundation.gm import dispatch as gm_dispatch

        with mock.patch.dict(os.environ, {accounts.ENV_OVERRIDE: str(allow)}), \
                mock.patch.object(
                    gm_dispatch, "DEFAULT_CAPTURE_ROOT", str(root),
                ), mock.patch.object(
                    gm_dispatch.handle_gm_run_command_vital,
                    "__kwdefaults__",
                    {**(gm_dispatch.handle_gm_run_command_vital.__kwdefaults__ or {}),
                     "capture_root": str(root)},
                ):
            session, printed, _ = self._fire("panya", b"\x0b\x00")
        self.assertEqual(session.events, ["gm_run_command_authorized_capture"])
        self.assertNotIn(GM_ALLOWLIST_CONSOLE_TOKEN, printed)
        self.assertTrue(any(root.rglob("*.txt")), "no capture file was written")



if __name__ == "__main__":
    unittest.main()
