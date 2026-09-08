"""GM-003 v1: GM command grammar -- parse and log only, no gameplay effect."""
from __future__ import annotations

import contextlib
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import commands as commands_module
from pirateforce_foundation.gm import scene_catalog
from pirateforce_foundation.gm.commands import (
    MAX_SAY_MESSAGE_LENGTH,
    GmCommand,
    GmCommandArgsError,
    GmCommandParseError,
    describe_npc_target,
    describe_warp_target,
    log_gm_command,
    parse_gm_command,
)


@contextlib.contextmanager
def _o_binary_removed(module_os):
    """Make ``os.O_BINARY`` absent for the block, on EVERY platform.

    Twin of `tests/test_gm_command_capture.py`'s helper of the same name,
    for the same reason: the sibling "flags unchanged" test below used to
    assert `not hasattr(os, "O_BINARY")`, a statement about the HOST that
    is true on this Linux clone and false on the windows-latest gate. That
    pair of assertions was the whole of `pirate-force-server#962`'s
    `2 failed` (`AssertionError: True is not false`,
    `tests\\test_gm_commands.py:417`). The branch under test is the
    FALLBACK of `getattr(os, "O_BINARY", 0)`, so the absence is simulated
    and the pin keeps its teeth on both platforms. Restores in `finally`.
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


class _LyingTuple(tuple):
    """A tuple subclass that lies through __len__/__getitem__.

    Same threat model gm/warp_executor.py's and gm/say_wire.py's own
    `type(args) is not tuple` checks defend against -- an `isinstance`
    allowlist alone would not reject this.
    """

    def __len__(self):
        return 3

    def __getitem__(self, index):
        raise RuntimeError("lying tuple subclass")


class ParseGmCommandTests(unittest.TestCase):
    def test_warp_scene_only(self):
        cmd = parse_gm_command("warp 1")
        self.assertEqual(cmd.name, "warp")
        self.assertEqual(cmd.args, ("1",))

    def test_warp_scene_and_xy(self):
        cmd = parse_gm_command("warp 278 100 200")
        self.assertEqual(cmd.args, ("278", "100", "200"))

    def test_warp_rejects_wrong_arg_count(self):
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("warp 1 2")

    def test_warp_rejects_non_integer_scene_id(self):
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("warp abc")

    def test_warp_rejects_nan_and_infinite_coordinates(self):
        # pf-adversary finding: a position field must never silently accept
        # nan/inf -- whoever wires real warp execution against this parser
        # must not have to remember to add this check themselves.
        for bad in ("warp 1 nan 0", "warp 1 0 nan", "warp 1 inf 0", "warp 1 0 -inf",
                     "warp 1 1e400 0"):
            with self.assertRaises(GmCommandParseError):
                parse_gm_command(bad)

    def test_warp_accepts_ordinary_finite_coordinates(self):
        cmd = parse_gm_command("warp 1 -123.5 4200")
        self.assertEqual(cmd.args, ("1", "-123.5", "4200"))

    def test_npc_on_off(self):
        self.assertEqual(parse_gm_command("npc on 855").args, ("on", "855"))
        self.assertEqual(parse_gm_command("npc off 855").args, ("off", "855"))

    def test_npc_rejects_bad_switch(self):
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("npc maybe 855")

    def test_item(self):
        cmd = parse_gm_command("item 1001 5")
        self.assertEqual(cmd.args, ("1001", "5"))

    def test_lv(self):
        cmd = parse_gm_command("lv 30")
        self.assertEqual(cmd.args, ("30",))

    def test_spawn(self):
        cmd = parse_gm_command("spawn 35")
        self.assertEqual(cmd.args, ("35",))

    def test_say_keeps_whole_message(self):
        cmd = parse_gm_command("say hello there GM")
        self.assertEqual(cmd.args, ("hello there GM",))

    def test_say_requires_a_message(self):
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("say")

    def test_speed_accepts_a_finite_value(self):
        cmd = parse_gm_command("speed 5.0")
        self.assertEqual(cmd.name, "speed")
        self.assertEqual(cmd.args, ("5.0",))

    def test_speed_accepts_integer_looking_value(self):
        cmd = parse_gm_command("speed 400")
        self.assertEqual(cmd.args, ("400",))

    def test_speed_rejects_wrong_arg_count(self):
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("speed")
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("speed 1 2")

    def test_speed_rejects_non_numeric_value(self):
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("speed fast")

    def test_speed_rejects_nan_and_infinite(self):
        # Same rule warp's x/y already enforce (_require_number): a value
        # this lane cannot honestly encode as f32 must never reach a
        # composer as a string that merely happens to parse.
        for bad in ("speed nan", "speed inf", "speed -inf", "speed 1e400"):
            with self.assertRaises(GmCommandParseError):
                parse_gm_command(bad)

    def test_say_accepts_message_at_the_length_cap(self):
        cmd = parse_gm_command("say " + ("x" * MAX_SAY_MESSAGE_LENGTH))
        self.assertEqual(len(cmd.args[0]), MAX_SAY_MESSAGE_LENGTH)

    def test_say_rejects_message_over_the_length_cap(self):
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("say " + ("x" * (MAX_SAY_MESSAGE_LENGTH + 1)))

    def test_unknown_command_rejected(self):
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("flyaway 1")

    def test_empty_text_rejected(self):
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("   ")

    def test_command_name_is_case_insensitive(self):
        self.assertEqual(parse_gm_command("WARP 1").name, "warp")


class DescribeWarpTargetTests(unittest.TestCase):
    def test_known_scene_returns_gm_name(self):
        cmd = parse_gm_command("warp 1")
        self.assertEqual(describe_warp_target(cmd), "Port Royal")

    def test_unknown_scene_returns_none(self):
        cmd = parse_gm_command("warp 123456")
        self.assertIsNone(describe_warp_target(cmd))

    def test_rejects_non_warp_command(self):
        cmd = parse_gm_command("lv 1")
        with self.assertRaises(ValueError):
            describe_warp_target(cmd)

    def test_a_scene_id_the_client_itself_left_nameless_is_still_known_not_none(self):
        # scene_catalog id 13 has a row in the client's own committed table
        # (gm/data/gm_scene_name_tip.tsv) but that row's own two name
        # columns are both blank -- distinct from id 123456 above, which has
        # NO row at all. `describe_warp_target`'s docstring promises None
        # only for "the id has no row in the GM-004 catalog"; id 13 has one,
        # so the return here is "" (a hint, not a validity gate, per this
        # module's own docstring), and a caller must not read "" as "unknown
        # scene, warp refused" -- the warp itself is judged elsewhere
        # (login_scene_admission / world_scene_travel), never by this hint.
        cmd = parse_gm_command("warp 13")
        self.assertEqual(describe_warp_target(cmd), "")
        self.assertIsNotNone(describe_warp_target(cmd))


class DescribeNpcTargetTests(unittest.TestCase):
    def test_known_gm_switch_npc_returns_client_name(self):
        cmd = parse_gm_command("npc on 855")
        self.assertEqual(describe_npc_target(cmd), "傑克")

    def test_unknown_mob_id_returns_none(self):
        cmd = parse_gm_command("npc off 1")
        self.assertIsNone(describe_npc_target(cmd))

    def test_rejects_non_npc_command(self):
        cmd = parse_gm_command("lv 1")
        with self.assertRaises(ValueError):
            describe_npc_target(cmd)


class ArgsShapeGuardTests(unittest.TestCase):
    """pf-adversary (round 50x5xt): describe_warp_target/describe_npc_target/
    log_gm_command indexed or iterated `command.args` with no shape check --
    a hand-built GmCommand with a non-tuple args (dict, None, a lying tuple
    subclass) either crashed with a bare TypeError/RuntimeError instead of a
    module-specific error, or (for an integer-keyed dict) silently logged
    the dict's *keys* instead of its values. gm/warp_executor.py and
    gm/say_wire.py already closed this exact bug class for their own
    GmCommand inputs; this class proves it is now closed here too.
    """

    def test_describe_warp_target_rejects_non_tuple_args(self):
        cmd = GmCommand("warp", {0: "1", 1: "2", 2: "3"}, "warp 1 2 3")
        with self.assertRaises(GmCommandArgsError):
            describe_warp_target(cmd)

    def test_describe_warp_target_rejects_lying_tuple_subclass(self):
        cmd = GmCommand("warp", _LyingTuple(("1",)), "warp 1")
        with self.assertRaises(GmCommandArgsError):
            describe_warp_target(cmd)

    def test_describe_warp_target_rejects_short_args(self):
        cmd = GmCommand("warp", (), "warp")
        with self.assertRaises(GmCommandArgsError):
            describe_warp_target(cmd)

    def test_describe_warp_target_rejects_non_numeric_scene_id(self):
        # pf-adversary (round dnh0ai): shape-valid tuple, non-numeric content
        # -- int(args[0]) used to raise a bare ValueError instead of
        # GmCommandArgsError. A GmCommand "regardless of source" (this
        # module's own stated threat model) is not guaranteed to have gone
        # through parse_gm_command's _require_int first.
        cmd = GmCommand("warp", ("abc",), "warp abc")
        with self.assertRaises(GmCommandArgsError):
            describe_warp_target(cmd)

    def test_describe_npc_target_rejects_none_args(self):
        cmd = GmCommand("npc", None, "npc on 1")
        with self.assertRaises(GmCommandArgsError):
            describe_npc_target(cmd)

    def test_describe_npc_target_rejects_short_args(self):
        cmd = GmCommand("npc", ("on",), "npc on")
        with self.assertRaises(GmCommandArgsError):
            describe_npc_target(cmd)

    def test_describe_npc_target_rejects_non_numeric_mob_id(self):
        # pf-adversary (round dnh0ai): same gap as
        # test_describe_warp_target_rejects_non_numeric_scene_id, second call
        # site.
        cmd = GmCommand("npc", ("on", "not_an_int"), "npc on not_an_int")
        with self.assertRaises(GmCommandArgsError):
            describe_npc_target(cmd)

    def test_describe_warp_target_rejects_a_scene_id_whose_dunder_int_raises_a_non_value_error(self):
        # pf-adversary (round w8t8vi): _require_arg_int only caught
        # (TypeError, ValueError), same gap as warp_executor.py's identical
        # helper before this round -- a hand-built element whose __int__
        # raises something else leaked a bare exception past this function's
        # own promised GmCommandArgsError-only contract.
        class EvilInt:
            def __int__(self):
                raise AttributeError("boom")

        cmd = GmCommand("warp", (EvilInt(),), "warp x")
        with self.assertRaises(GmCommandArgsError):
            describe_warp_target(cmd)

    def test_describe_npc_target_rejects_a_mob_id_whose_dunder_int_raises_a_non_value_error(self):
        class EvilInt:
            def __int__(self):
                raise AttributeError("boom")

        cmd = GmCommand("npc", ("on", EvilInt()), "npc on x")
        with self.assertRaises(GmCommandArgsError):
            describe_npc_target(cmd)

    def test_log_gm_command_rejects_non_tuple_args_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "gm_command_log.ndjson"
            cmd = GmCommand("lv", {0: "1"}, "lv 1")
            with self.assertRaises(GmCommandArgsError):
                log_gm_command(cmd, "panya", log_path=log_path, now_ts=0)
            self.assertFalse(log_path.exists())

    def test_log_gm_command_records_real_values_not_dict_keys(self):
        # Regression for the exact bug pf-adversary found: list(some_dict)
        # yields the dict's KEYS, not its values -- a caller passing an
        # integer-keyed dict as args used to get a record whose "args" field
        # silently held [0, 1, 2] instead of the real string values.
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "gm_command_log.ndjson"
            cmd = parse_gm_command("warp 1 2 3")
            log_gm_command(cmd, "panya", log_path=log_path, now_ts=0)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["args"], ["1", "2", "3"])

    def test_log_gm_command_rejects_a_non_serializable_arg_and_writes_nothing(self):
        # pf-adversary (round w8t8vi): args is shape-valid (a real tuple) but
        # holds an element json.dumps cannot serialize. The old code built
        # path.parent.mkdir(...) and opened the file for append BEFORE calling
        # json.dumps -- so a rejected call still created the log directory
        # and an empty file, violating the sibling shape-rejection test's
        # "writes nothing on rejection" contract for this different failure
        # mode. json.dumps must now run before any filesystem mutation.
        class Weird:
            def __repr__(self):
                return "<Weird>"

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "sub" / "gm_command_log.ndjson"
            cmd = GmCommand("warp", (Weird(),), "warp x")
            with self.assertRaises(TypeError):
                log_gm_command(cmd, "panya", log_path=log_path, now_ts=0)
            self.assertFalse(log_path.exists())
            self.assertFalse(log_path.parent.exists())


class LogGmCommandTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.log_path = Path(self._tmp.name) / "gm_command_log.ndjson"

    def test_appends_one_ndjson_record_marked_not_executed(self):
        cmd = parse_gm_command("warp 1")
        out = log_gm_command(cmd, "panya", log_path=self.log_path, now_ts=0)
        self.assertEqual(out, self.log_path)
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["account"], "panya")
        self.assertEqual(record["command"], "warp")
        self.assertEqual(record["args"], ["1"])
        self.assertFalse(record["executed"])

    def test_two_calls_append_two_lines(self):
        log_gm_command(parse_gm_command("lv 1"), "panya", log_path=self.log_path, now_ts=0)
        log_gm_command(parse_gm_command("lv 2"), "panya", log_path=self.log_path, now_ts=0)
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)

    def test_rejects_empty_account_name(self):
        with self.assertRaises(ValueError):
            log_gm_command(parse_gm_command("lv 1"), "", log_path=self.log_path)

    def test_log_file_mode_is_owner_only_no_execute_regardless_of_umask(self):
        # Same bug class and same fix as
        # gm/command_capture.py's test_capture_file_mode_is_owner_only_no_execute_regardless_of_umask,
        # found by pf-adversary in a sibling file that fix did not touch:
        # the builtin open("a") this function used to call creates a new
        # file at the platform default (0o666 masked by umask, no execute
        # bit but still world-readable, world-writable under a permissive
        # umask) with no way to request an explicit mode -- for an ndjson
        # audit log of every GM command issued, including full `say
        # <message>` bodies. Assert under a deliberately permissive umask
        # (0o000) so this cannot pass by accident of the container's own
        # umask; 0o600 has no group/other bits for any umask to add back.
        old_umask = os.umask(0o000)
        try:
            out = log_gm_command(
                parse_gm_command("lv 1"), "panya", log_path=self.log_path, now_ts=0
            )
        finally:
            os.umask(old_umask)
        mode = stat.S_IMODE(out.stat().st_mode)
        if os.name == "posix":
            self.assertEqual(mode, 0o600, oct(mode))
        else:
            # No POSIX mode bits to check on this OS -- the call must still
            # succeed and produce a real file. Same Windows caveat as
            # command_capture.py: NTFS ignores this bit split, real access
            # control there is the containing directory's ACL.
            self.assertTrue(out.is_file())

    def test_log_open_passes_o_binary_flag_when_available(self):
        # Sibling of gm/command_capture.py's O_BINARY fix (pf-adversary D6,
        # round `lkwmkp`): this audit log is also written via a raw
        # os.open()+os.write() pair, one ndjson line per GM command. Without
        # os.O_BINARY, Windows' default text-mode translation on that
        # descriptor could turn an embedded `\n` inside the flag into extra
        # bytes on disk, corrupting the one-line-per-record contract. The
        # flag does not exist on this (POSIX) host, so it is monkeypatched
        # to a sentinel bit that cannot collide with any real O_* flag,
        # purely to prove this call site threads it through -- not to prove
        # anything about actual Windows CRLF behaviour.
        #
        # pf-adversary (this round, same fix as command_capture.py's sibling
        # test): delegate to the real os.open() with the sentinel bit
        # cleared first -- this bit has never been asked of the real
        # Windows CRT open call this fix targets, and an unrecognized oflag
        # bit is documented by Microsoft as unspecified, not guaranteed
        # ignored, so a real syscall must never see it.
        sentinel_bit = 1 << 30
        real_open = commands_module.os.open

        def _spy_then_real_open_without_sentinel(path, flags, *args, **kwargs):
            return real_open(path, flags & ~sentinel_bit, *args, **kwargs)

        with mock.patch.object(
            commands_module.os, "O_BINARY", sentinel_bit, create=True,
        ), mock.patch.object(
            commands_module.os,
            "open",
            side_effect=_spy_then_real_open_without_sentinel,
        ) as spy_open:
            log_gm_command(
                parse_gm_command("lv 1"), "panya", log_path=self.log_path, now_ts=0,
            )
        self.assertEqual(spy_open.call_count, 1)
        flags_arg = spy_open.call_args.args[1]
        self.assertTrue(
            flags_arg & sentinel_bit,
            f"os.open() flags {oct(flags_arg)} do not include the "
            f"O_BINARY sentinel bit {oct(sentinel_bit)} -- the getattr("
            f"os, 'O_BINARY', 0) fallback regressed or was removed",
        )

    def test_log_open_flags_unchanged_when_o_binary_absent(self):
        # Where os.O_BINARY does not exist, getattr(...) must fall back to
        # 0 -- the flags value passed to os.open() must be byte-for-byte
        # the same as before this fix.
        #
        # The absence is SIMULATED rather than assumed (see
        # `_o_binary_removed` at the top of this file): asserting
        # `not hasattr(os, "O_BINARY")` was a claim about the host, true
        # here and false on the windows-latest gate, and it is what turned
        # `#962` red. The fallback branch of `getattr(os, "O_BINARY", 0)`
        # is now exercised on every platform.
        with _o_binary_removed(commands_module.os):
            self.assertFalse(hasattr(commands_module.os, "O_BINARY"))
            with mock.patch.object(
                commands_module.os, "open", side_effect=commands_module.os.open,
            ) as spy_open:
                log_gm_command(
                    parse_gm_command("lv 1"), "panya", log_path=self.log_path,
                    now_ts=0,
                )
        self.assertEqual(spy_open.call_count, 1)
        flags_arg = spy_open.call_args.args[1]
        self.assertEqual(flags_arg, os.O_CREAT | os.O_APPEND | os.O_WRONLY)

    def test_log_directory_mode_is_owner_only_regardless_of_umask(self):
        # Sibling of gm/command_capture.py's directory-mode fix: a
        # world-writable containing directory would let another local user
        # delete or rename this audit log even though they cannot read it.
        nested_log_path = Path(self._tmp.name) / "nested" / "gm_command_log.ndjson"
        old_umask = os.umask(0o000)
        try:
            log_gm_command(
                parse_gm_command("lv 1"), "panya", log_path=nested_log_path, now_ts=0
            )
        finally:
            os.umask(old_umask)
        mode = stat.S_IMODE(nested_log_path.parent.stat().st_mode)
        if os.name == "posix":
            self.assertEqual(mode, 0o700, oct(mode))
        else:
            self.assertTrue(nested_log_path.parent.is_dir())

    def test_log_directory_mode_is_retightened_on_a_preexisting_loose_directory(self):
        # Sibling of gm/command_capture.py's identical fix (pf-adversary
        # verification pass, same round): `mkdir(..., exist_ok=True)` never
        # chmods a directory that already exists, and this function shares
        # its literal parent (`capture/`) with command_capture.py's own
        # default root -- whichever function runs first on a real host
        # locks that shared parent's mode in, forever, without this.
        # Simulate "some earlier call already created it loose."
        #
        # No POSIX mode bits to check on Windows (same caveat as the
        # sibling first-creation test above) -- runs assertions only on
        # POSIX; the call under test still runs and must still succeed on
        # every OS.
        nested_log_path = Path(self._tmp.name) / "preexisting" / "gm_command_log.ndjson"
        nested_log_path.parent.mkdir(mode=0o777)
        if os.name == "posix":
            os.chmod(nested_log_path.parent, 0o777)
            self.assertEqual(stat.S_IMODE(nested_log_path.parent.stat().st_mode), 0o777)
        old_umask = os.umask(0o022)
        try:
            log_gm_command(
                parse_gm_command("lv 1"), "panya", log_path=nested_log_path, now_ts=0
            )
        finally:
            os.umask(old_umask)
        if os.name == "posix":
            mode = stat.S_IMODE(nested_log_path.parent.stat().st_mode)
            self.assertEqual(mode, 0o700, oct(mode))
        else:
            self.assertTrue(nested_log_path.parent.is_dir())


class WarpByNameTests(unittest.TestCase):
    """`warp <scene name>` -- the form an operator at the client can type.

    The design claim under test is narrow: the name form resolves to the
    SAME `GmCommand` the id form produces, so nothing downstream learns a
    second shape, and it takes nothing away from the id form.
    """

    def test_a_name_produces_exactly_the_command_the_id_form_produces(self):
        by_name = parse_gm_command("warp Prison Exile Island")
        by_id = parse_gm_command("warp 2")
        self.assertEqual(by_name.name, by_id.name)
        self.assertEqual(by_name.args, by_id.args)
        self.assertEqual(by_name.args, ("2",))
        # `raw` is the one field that differs, and it must: the audit record
        # is what an operator's typed line is kept in.
        self.assertEqual(by_name.raw, "warp Prison Exile Island")

    def test_the_id_form_is_untouched_by_the_new_branch(self):
        # Every shape the numeric grammar accepted before the name branch
        # existed, including the ones `int()` accepts and a digit test would
        # not. A name form that narrowed these would be a regression paid
        # for with convenience.
        for text, expected in (
            ("warp 2", ("2",)),
            ("warp 2 10 20", ("2", "10", "20")),
            ("warp -1", ("-1",)),
            ("warp +7", ("+7",)),
            ("warp 007", ("007",)),
            ("warp 1_0", ("1_0",)),
            ("warp 999 1.5 -2.5", ("999", "1.5", "-2.5")),
        ):
            with self.subTest(text=text):
                self.assertEqual(parse_gm_command(text).args, expected)

    def test_an_unknown_scene_id_is_still_accepted_the_asymmetry_is_deliberate(self):
        # A number is a wire value and stands without the catalog; a name has
        # no meaning except through it. Pinned because the asymmetry looks
        # like an oversight until it is read as the rule.
        self.assertFalse(scene_catalog.is_known_scene_id(123456))
        self.assertEqual(parse_gm_command("warp 123456").args, ("123456",))
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("warp Definitely Not A Scene")

    def test_an_ambiguous_name_refuses_and_names_the_way_out(self):
        with self.assertRaises(GmCommandParseError) as caught:
            parse_gm_command("warp Hidden Island")
        message = str(caught.exception)
        self.assertIn("20 scenes", message)
        self.assertIn("warp <scene_id>", message)
        # Readable, not a dump of twenty numbers.
        self.assertIn("...", message)
        self.assertLessEqual(
            message.count(","), commands_module.MAX_AMBIGUOUS_SCENE_IDS_SHOWN + 1
        )

    def test_a_name_ending_in_digits_still_resolves_and_never_eats_coordinates(self):
        # 52 of the table's 330 names end in a digit, so "the last two tokens
        # are x/y" cannot be told from "the name ends in numbers". The name
        # form therefore takes NO coordinates, and the trailing-number line
        # is refused rather than silently warped without them.
        self.assertEqual(parse_gm_command("warp Navy Prison2").args, ("123",))
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("warp Navy Prison2 10 20")

    def test_no_message_this_branch_raises_echoes_what_the_operator_typed(self):
        # These lines reach a cp874 console. Echoing arbitrary client text is
        # one unlucky character from killing it, and the operator can already
        # see their own line. Both refusal paths are checked, with a query
        # that would be visible if it were echoed.
        marker = "ZZQQ_UNLIKELY_MARKER"
        for text in (f"warp {marker}", "warp Hidden Island"):
            with self.subTest(text=text):
                with self.assertRaises(GmCommandParseError) as caught:
                    parse_gm_command(text)
                message = str(caught.exception)
                self.assertNotIn(marker, message)
                self.assertNotIn("Hidden", message)
                message.encode("ascii")

    def test_the_bare_verb_still_shows_the_usage_line(self):
        with self.assertRaises(GmCommandParseError) as caught:
            parse_gm_command("warp")
        self.assertEqual(str(caught.exception), commands_module.COMMAND_USAGE["warp"])

    def test_the_usage_line_an_operator_reads_mentions_both_forms(self):
        # The grammar is spelled once (`COMMAND_USAGE`), so a form the parser
        # accepts but no usage sentence mentions is a form nobody finds.
        usage = commands_module.COMMAND_USAGE["warp"]
        self.assertIn("<scene_id>", usage)
        self.assertIn("<scene name>", usage)

    def test_the_resolved_id_is_what_the_audit_record_and_the_hint_read(self):
        command = parse_gm_command("warp Spice Paradise Island")
        self.assertEqual(describe_warp_target(command), "Spice Paradise Island")


class WarpNameNearMissTests(unittest.TestCase):
    """A mistyped island name names the island, instead of ending the line."""

    def _message(self, text):
        with self.assertRaises(GmCommandParseError) as caught:
            parse_gm_command(text)
        return str(caught.exception)

    def test_one_dropped_letter_gets_the_scene_id_it_meant(self):
        message = self._message("warp Prison Exile Iland")
        self.assertIn("did you mean 'Prison Exile Island' (scene 2)", message)
        # The way out is still there; the suggestion is added, not swapped in.
        self.assertIn("warp <scene_id>", message)

    def test_a_name_with_coordinates_now_names_the_id_that_carries_them(self):
        # This is the case the id-only rule used to leave at a dead end:
        # `Navy Prison2` really is a scene, and `warp Navy Prison2 10 20` is
        # refused because a trailing digit cannot be told from a coordinate.
        # Before this round the operator was told only to "use warp
        # <scene_id>" -- without being told which id that is.
        message = self._message("warp Navy Prisn2 10 20")
        self.assertIn("did you mean 'Navy Prison2' (scene 123)", message)

    def test_an_ambiguous_suggestion_prints_a_count_not_twenty_ids(self):
        message = self._message("warp hidden iland")
        self.assertIn("'Hidden Island' (on 20 scenes)", message)
        self.assertNotIn("308, 309", message)

    def test_nonsense_adds_no_suggestion_clause_at_all(self):
        message = self._message("warp qqqqqqqq")
        self.assertNotIn("did you mean", message)
        self.assertIn("no GM scene carries that name", message)

    def test_the_suggestion_never_echoes_what_the_operator_typed(self):
        # These lines reach a cp874 console. Every character printed has to
        # come out of the pinned table, which is measured cp874-safe; the
        # typed text carries no such guarantee. A marker that cannot appear
        # in any of the 330 shipped names is the witness.
        marker = "ZqxjvwZ"
        message = self._message("warp Prison Exile Iland %s" % marker)
        self.assertNotIn(marker, message)
        for candidate in ("warp %s" % marker, "warp Port Royl %s" % marker):
            with self.subTest(text=candidate):
                self.assertNotIn(marker, self._message(candidate))

    def test_every_suggestion_this_parser_prints_encodes_on_the_console(self):
        for text in (
            "warp Prison Exile Iland",
            "warp Navy Prisn2 10 20",
            "warp hidden iland",
            "warp Port Royl",
        ):
            with self.subTest(text=text):
                self._message(text).encode("cp874")

    def test_an_exact_name_still_parses_and_gains_no_suggestion_path(self):
        self.assertEqual(
            parse_gm_command("warp Prison Exile Island"),
            GmCommand("warp", ("2",), "warp Prison Exile Island"),
        )

    def test_the_numeric_form_is_untouched_by_the_suggestion_branch(self):
        for text, args in (
            ("warp 2", ("2",)),
            ("warp -1", ("-1",)),
            ("warp 007 5 6", ("007", "5", "6")),
            ("warp 1_0 5 6", ("1_0", "5", "6")),
        ):
            with self.subTest(text=text):
                self.assertEqual(parse_gm_command(text).args, args)

    def test_an_ambiguous_exact_name_keeps_its_own_rejection(self):
        # The ambiguous branch runs before this one and must not be reworded
        # by it: an exact ambiguous name lists ids, it does not "suggest".
        message = self._message("warp Hidden Island")
        self.assertIn("that name is on 20 scenes", message)
        self.assertNotIn("did you mean", message)


class WarpNameQueryIsHeldToTheConsoleCodecTests(unittest.TestCase):
    """pf-adversary round `nqgmam` D2: the query is the client-chosen side."""

    def _message(self, text):
        with self.assertRaises(GmCommandParseError) as caught:
            parse_gm_command(text)
        return str(caught.exception)

    def test_a_homoglyph_no_longer_resolves_to_a_real_scene(self):
        # `casefold()` is many-to-one: U+017F folds to 's', so this used to
        # come back as scene 2 and put a character with no cp874 byte into
        # the audit record's `raw`. Before the name form existed the same
        # line was a parse error and never reached the audit writer at all.
        self.assertIn("console can print", self._message("warp pri\u017fon exile i\u017fland"))

    def test_separators_and_controls_that_str_split_accepted_are_refused(self):
        # `str.split()` splits on every `str.isspace()` character, and none
        # of these is Unicode category Cf, so the chat layer's format filter
        # does not see them either.
        for text in (
            "warp Prison\u2028Exile\u2029Island",
            "warp \x0bPort\x0cRoyal",
            "warp Port\x1cRoyal",
            "warp Port\u3000Royal",
            "warp Port\x85Royal",
        ):
            with self.subTest(text=text):
                self.assertIn("console can print", self._message(text))

    def test_the_guard_excludes_no_shipped_name(self):
        # The bar is the one all 330 shipped names already meet, so closing
        # this must cost nothing that worked. Every name in the table still
        # parses (ambiguous ones raise the ambiguity error, never the codec
        # error -- which is the assertion that keeps this from passing by
        # refusing everything).
        for scene_id, name in scene_catalog.SCENE_ID_TO_GM_NAME.items():
            if not name.strip():
                continue
            with self.subTest(scene_id=scene_id):
                try:
                    resolved = parse_gm_command("warp %s" % name)
                except GmCommandParseError as error:
                    self.assertIn("that name is on", str(error))
                    continue
                self.assertEqual(resolved.name, "warp")
                self.assertIn(scene_id, scene_catalog.resolve_gm_scene_name(name))

    def test_ascii_space_and_tab_still_separate_a_name(self):
        self.assertEqual(parse_gm_command("warp Port\tRoyal").args, ("1",))
        self.assertEqual(parse_gm_command("warp  Port   Royal ").args, ("1",))

    def test_the_codec_refusal_echoes_nothing_typed_and_keeps_the_way_out(self):
        message = self._message("warp \u017fZqxjvwZ")
        self.assertNotIn("Zqxjvw", message)
        self.assertIn("warp <scene_id>", message)
        message.encode("cp874")

    def test_the_numeric_form_never_reaches_the_guard(self):
        # The guard sits inside the name branch only. A numeric first token
        # is decided before it, so the id form cannot be narrowed by this.
        for text, args in (("warp 2", ("2",)), ("warp -1", ("-1",)),
                           ("warp 007 5 6", ("007", "5", "6"))):
            with self.subTest(text=text):
                self.assertEqual(parse_gm_command(text).args, args)


class WarpUnknownNameMessageContentTests(unittest.TestCase):
    """pf-adversary round `nqgmam` D1: this branch's message had no witness."""

    def _message(self, text):
        with self.assertRaises(GmCommandParseError) as caught:
            parse_gm_command(text)
        return str(caught.exception)

    def test_the_two_counts_it_prints_are_the_two_it_means(self):
        # Mutant M21 swapped GM_NAME_COUNT for SCENE_COUNT and survived,
        # printing "330 names over 330 scenes" to an operator. The two
        # numbers differ, so pinning both catches the swap.
        message = self._message("warp qqqqqqqq")
        self.assertNotEqual(scene_catalog.GM_NAME_COUNT, scene_catalog.SCENE_COUNT)
        self.assertIn(
            "(%d names over %d scenes)"
            % (scene_catalog.GM_NAME_COUNT, scene_catalog.SCENE_COUNT),
            message,
        )

    def test_the_way_out_survives_on_the_unknown_branch_too(self):
        # Mutants M24 and M27 (drop the usage clause; replace the whole body
        # with "no") survived because only the AMBIGUOUS branch's way-out was
        # pinned.
        message = self._message("warp qqqqqqqq")
        self.assertIn("no GM scene carries that name", message)
        self.assertIn("warp <scene_id>", message)


class WarpNameQueryIsBoundedInLengthTests(unittest.TestCase):
    """The third of the three shapes pf-adversary asked the query to have.

    The codec card (round `nqgmam`) made the query cp874-encodable and
    single-line and left "bounded in length" open; letter `20260908_0017`
    recorded that gap.  `log_gm_command` writes `"raw": command.raw` into
    the ndjson audit file, so whatever this branch accepts becomes a log
    LINE -- these tests pin the bound, and pin that it is read first.
    """

    def _message(self, text):
        with self.assertRaises(GmCommandParseError) as caught:
            parse_gm_command(text)
        return str(caught.exception)

    def test_the_cap_matches_the_table_and_its_measured_value_is_written_down(self):
        """pf-adversary D2, MEASURED: the relationship alone pinned nothing.

        `assertEqual(MAX_WARP_NAME_QUERY_LENGTH, 2 * LONGEST_GM_NAME_LENGTH)`
        is a statement about two constants, and `108 == 2 * 54` satisfies it
        with BOTH of them hardcoded -- two mutants that typed the numbers in
        survived the whole suite.  The relationship is kept (it is what "one
        extra space per character of the longest matchable name" means) and
        the measured values are written down beside it, so a table
        re-derive turns this red instead of moving the cap silently.
        `test_gm_scene_catalog.py` holds the sha that makes the literals
        mean something.

        WHAT THIS STILL DOES NOT PIN, said plainly rather than left in the
        test's name: no assertion can tell `LONGEST_GM_NAME_LENGTH = 54`
        from `max(len(key) for key in ...)` while the table yields 54.  The
        guard against a typed constant is `SOURCE_SHA256`, which makes the
        table unable to change quietly; the literals here make the values a
        human has to re-approve when it does.  The test is named for that
        pair now, not for a derivation it cannot observe.
        """
        self.assertEqual(
            commands_module.MAX_WARP_NAME_QUERY_LENGTH,
            2 * scene_catalog.LONGEST_GM_NAME_LENGTH,
        )
        self.assertEqual(54, scene_catalog.LONGEST_GM_NAME_LENGTH)
        self.assertEqual(108, commands_module.MAX_WARP_NAME_QUERY_LENGTH)

    def test_the_line_that_used_to_write_a_200_kb_audit_row_is_refused(self):
        # `warp Port` + whitespace + `Royal` folds to `port royal` and
        # resolved to scene 1 before this cap, with every one of those bytes
        # landing in `raw`. Same line, both sides of the boundary.
        self.assertEqual(parse_gm_command("warp Port  Royal").args, ("1",))
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("warp Port" + " " * 200_000 + "Royal")

    def test_the_boundary_itself_is_pinned_on_both_sides(self):
        # The padding goes INSIDE the name: `parse_gm_command` strips the
        # whole line before splitting off the verb, so trailing spaces never
        # reach this branch and would have measured nothing.
        cap = commands_module.MAX_WARP_NAME_QUERY_LENGTH
        at_cap = "Port" + " " * (cap - len("PortRoyal")) + "Royal"
        self.assertEqual(len(at_cap), cap)
        self.assertEqual(parse_gm_command(f"warp {at_cap}").args, ("1",))
        over = "Port" + " " * (cap - len("PortRoyal") + 1) + "Royal"
        self.assertEqual(len(over), cap + 1)
        with self.assertRaises(GmCommandParseError) as caught:
            parse_gm_command(f"warp {over}")
        self.assertIn(str(cap), str(caught.exception))
        self.assertIn(str(len(over)), str(caught.exception))

    def test_the_cap_excludes_no_shipped_name(self):
        # The bound may only ever refuse a query no scene could answer. Walk
        # every shipped name, not a sample.
        cap = commands_module.MAX_WARP_NAME_QUERY_LENGTH
        for name in scene_catalog.SCENE_ID_TO_GM_NAME.values():
            self.assertLessEqual(len(name.strip()), cap)

    def test_the_length_is_read_before_anything_walks_the_string(self):
        # Every later check is at least O(len) and `_did_you_mean` is
        # difflib over the whole query, so a cap read after them bounds the
        # result and not the work. A query that is BOTH over-length and
        # un-encodable must come back with the length message: that can only
        # happen if the length is read first.
        cap = commands_module.MAX_WARP_NAME_QUERY_LENGTH
        both = "\u0142" * (cap + 1)
        self.assertFalse(commands_module._query_is_console_safe(both))
        message = self._message(f"warp {both}")
        self.assertIn("at most", message)
        self.assertNotIn(commands_module.QUERY_CONSOLE_CODEC, message.split(";")[0])

    def test_the_refusal_echoes_nothing_typed_and_stays_ascii(self):
        marker = "ZZQQ_UNLIKELY_MARKER"
        cap = commands_module.MAX_WARP_NAME_QUERY_LENGTH
        message = self._message("warp " + marker + "x" * cap)
        self.assertNotIn(marker, message)
        message.encode("ascii")


class WarpNameSelectorPicksAmongRepeatsTests(unittest.TestCase):
    """`warp <scene name> #n` -- the eleventh `Hidden Island`, reachable.

    Six names in the client's own table are on more than one scene id and
    the ambiguity refusal can only print the first
    `MAX_AMBIGUOUS_SCENE_IDS_SHOWN` of them, so before this an operator who
    wanted the eleventh had no way to name it from the client at all.
    """

    def _message(self, text):
        with self.assertRaises(GmCommandParseError) as caught:
            parse_gm_command(text)
        return str(caught.exception)

    def test_the_nth_repeat_is_the_nth_id_in_ascending_order(self):
        ids = scene_catalog.resolve_gm_scene_name("Hidden Island")
        self.assertEqual(len(ids), 20)
        self.assertEqual(list(ids), sorted(ids))
        for index, scene_id in enumerate(ids, start=1):
            with self.subTest(n=index):
                self.assertEqual(
                    parse_gm_command(f"warp Hidden Island #{index}").args,
                    (str(scene_id),),
                )

    def test_the_selector_resolves_at_parse_time_like_every_other_form(self):
        # Downstream must learn nothing new: `args` is the plain numeric
        # form `warp <scene_id>` already produces, and `raw` keeps the line.
        command = parse_gm_command("warp Hidden Island #11")
        self.assertEqual(command.name, "warp")
        self.assertEqual(len(command.args), 1)
        self.assertEqual(command.raw, "warp Hidden Island #11")

    def test_an_n_outside_the_range_is_refused_with_the_range_never_clamped(self):
        # A clamped selector sends a GM somewhere they did not ask for and
        # says nothing about it.
        for text in ("warp Hidden Island #0", "warp Hidden Island #21"):
            with self.subTest(text=text):
                message = self._message(text)
                self.assertIn("#1 to #20", message)
        self.assertEqual(parse_gm_command("warp Port Royal #1").args, ("1",))
        self.assertIn("on 1 scene,", self._message("warp Port Royal #2"))

    def test_only_ascii_digits_are_a_selector(self):
        # Thai digits are `isdigit()`, they encode in cp874 so the codec
        # card does not stop them, and `int()` takes them -- `#\u0e51\u0e51`
        # would have become 11. `int()` also takes `+11` and `1_1`.
        for tail in ("\u0e51\u0e51", "+11", "1_1", "0x11", ""):
            with self.subTest(tail=tail):
                with self.assertRaises(GmCommandParseError):
                    parse_gm_command(f"warp Hidden Island #{tail}")

    def test_a_hash_that_is_not_a_selector_stays_part_of_the_name(self):
        # No shipped name contains `#`, so these only ever refuse a typo --
        # but they must refuse it as a NAME, not silently drop characters.
        self.assertIn(
            "no GM scene carries that name",
            self._message("warp Hidden Island#3"),
        )
        self.assertIn(
            "no GM scene carries that name", self._message("warp Port#Royal")
        )

    def test_a_bare_selector_with_no_name_shows_the_usage_line(self):
        self.assertEqual(
            self._message("warp #3"), commands_module.COMMAND_USAGE["warp"]
        )

    def test_the_ambiguity_refusal_now_names_the_selector_as_the_way_out(self):
        # The way-out line is the only place an operator learns this form
        # exists at the moment they need it.
        message = self._message("warp Hidden Island")
        self.assertIn("#1 to #20", message)
        self.assertIn("warp <scene_id>", message)

    def test_no_selector_message_echoes_what_was_typed_and_all_stay_ascii(self):
        for text in (
            "warp Hidden Island #0",
            "warp Hidden Island #21",
            "warp Port Royal #2",
            "warp Hidden Island",
        ):
            with self.subTest(text=text):
                message = self._message(text)
                self.assertNotIn("Hidden", message)
                self.assertNotIn("Royal", message)
                message.encode("ascii")

    def test_the_selector_split_shows_the_codec_check_every_character(self):
        """pf-adversary D1, HIGH, MEASURED, reachable from the chat wire.

        `_split_scene_selector` runs BEFORE `_query_is_console_safe`, and it
        used to return `head.strip()` -- so every whitespace code point
        between the name and `#n` was deleted before the codec check could
        see it.  Twenty-seven of those are characters the check refuses,
        `\n`, `\x85`, `\xa0`, `\u2028` and `\u3000` among them; each one
        parsed, and each one landed in `command.raw`, which
        `log_gm_command` writes into the ndjson audit line.  `chat_command`
        does not stop them either (`has_format_characters` tests `Cf`; these
        are `Cc`/`Zl`/`Zs`), so a ordinary GM chat frame reached it.

        WALKS THE WHOLE CLASS, not a sample: the set is derived here from
        the codec check itself, so a change to what the console accepts
        cannot leave a hole this test does not look at.
        """
        refused_whitespace = [
            chr(code)
            for code in range(0x110000)
            if chr(code).isspace()
            and not commands_module._query_is_console_safe(chr(code))
        ]
        self.assertEqual(27, len(refused_whitespace))
        for ch in refused_whitespace:
            with self.subTest(ch=hex(ord(ch))):
                with self.assertRaises(GmCommandParseError) as raised:
                    parse_gm_command(f"warp Hidden Island{ch}#1")
                self.assertIn("cp874", str(raised.exception))

    def test_an_ordinary_extra_space_before_the_selector_still_resolves(self):
        # The other side of D1's fix: not stripping must not cost the
        # operator anything, because the catalog fold already collapses and
        # trims ordinary whitespace.
        self.assertEqual(parse_gm_command("warp Hidden Island #1").args, ("308",))
        self.assertEqual(parse_gm_command("warp Hidden Island  #1").args, ("308",))
        self.assertEqual(
            parse_gm_command("warp Hidden Island \t #1").args, ("308",),
        )

    def test_the_usage_line_mentions_the_selector(self):
        # A form the parser accepts but no usage sentence mentions is a form
        # nobody finds.
        self.assertIn("#n", commands_module.COMMAND_USAGE["warp"])

    def test_the_numeric_form_is_untouched_by_either_change(self):
        self.assertEqual(parse_gm_command("warp 2").args, ("2",))
        self.assertEqual(parse_gm_command("warp 2 10 20").args, ("2", "10", "20"))
        self.assertEqual(parse_gm_command("warp -1").args, ("-1",))
        self.assertEqual(parse_gm_command("warp 1_0").args, ("1_0",))


class _LoudStr(str):
    """A `str` that shouts if anything rewrites it.

    `isinstance(x, str)` is True for a subclass, so `parse_gm_command`
    accepts one -- and `len()` still works.  Any call to `strip` or `split`
    on the line means the length check is no longer the first thing that
    happens, which is precisely the defect this class exists to catch.
    """

    def strip(self, *args, **kwargs):  # noqa: D102 - see class docstring
        raise AssertionError("strip() ran before the length cap")

    def split(self, *args, **kwargs):  # noqa: D102 - see class docstring
        raise AssertionError("split() ran before the length cap")


class TheWholeLineCapTests(unittest.TestCase):
    """pf-adversary round `53rdv8` D5: one verb was capped, eight were not."""

    def test_a_verb_padded_with_a_whitespace_run_is_refused(self):
        # Every one of these parsed before, and `stripped` -- the whole
        # 200 KB -- became `command.raw`, which `log_gm_command` writes into
        # the ndjson audit as one line.
        padding = " " * 200_000
        for line in (
            f"speed{padding}1",
            f"npc{padding}on 5",
            f"item{padding}1 2",
            f"lv{padding}9",
            f"spawn{padding}7",
            f"warp{padding}2",
            f"gmprobe{padding}a",
            f"staged{padding}",
        ):
            with self.subTest(verb=line.split(" ")[0]):
                with self.assertRaises(GmCommandParseError) as raised:
                    parse_gm_command(line)
                self.assertIn("command line", str(raised.exception))

    def test_the_refusal_names_the_cap_and_echoes_nothing_typed(self):
        with self.assertRaises(GmCommandParseError) as raised:
            parse_gm_command("say " + "\u0e01" * commands_module.MAX_COMMAND_LINE_LENGTH)
        message = str(raised.exception)
        self.assertIn(str(commands_module.MAX_COMMAND_LINE_LENGTH), message)
        self.assertNotIn("\u0e01", message)
        message.encode("cp874")  # the console this line reaches

    def test_the_cap_is_read_before_strip_and_before_split(self):
        """The bound has to be on the WORK, not only on the result.

        `text.strip()` walks the line and `rest.split()` builds a list --
        so a cap placed after either bounds what is stored and not what is
        spent getting there.  `_LoudStr` fails the test if either runs.
        """
        with self.assertRaises(GmCommandParseError):
            parse_gm_command(_LoudStr("x" * (commands_module.MAX_COMMAND_LINE_LENGTH + 1)))

    def test_no_command_this_grammar_accepts_can_carry_a_longer_raw(self):
        # `raw` is what the audit writes. The cap is on the line, and
        # `stripped` is never longer than the line it came from.
        for line in ("warp 2", "say " + "a" * MAX_SAY_MESSAGE_LENGTH, "staged   "):
            with self.subTest(line=line[:12]):
                self.assertLessEqual(
                    len(parse_gm_command(line).raw),
                    commands_module.MAX_COMMAND_LINE_LENGTH,
                )

    def test_the_measured_numbers_the_cap_is_built_from(self):
        """Written down, not recomputed from the definition.

        Recomputing `longest verb + 1 + max(say, warp)` here would pass for
        any table at all -- that was D2/D3 last round.  These four literals
        are the measurement; changing any constant they come from makes a
        human re-read this test instead of watching a cap move on its own.
        """
        self.assertEqual(7, commands_module.LONGEST_COMMAND_NAME_LENGTH)  # `gmprobe`
        self.assertEqual(480, MAX_SAY_MESSAGE_LENGTH)
        self.assertEqual(108, commands_module.MAX_WARP_NAME_QUERY_LENGTH)
        self.assertEqual(488, commands_module.MAX_COMMAND_LINE_LENGTH)

    def test_the_longest_legitimate_line_still_parses_and_one_past_it_does_not(self):
        # 484 characters: `say ` plus a message at `say`'s own ceiling. The
        # cap leaves it four characters of the trailing space a chat client
        # adds; everything else in the grammar is 370+ characters shorter.
        longest_legitimate = "say " + "a" * MAX_SAY_MESSAGE_LENGTH
        self.assertEqual(484, len(longest_legitimate))
        self.assertEqual(
            ("a" * MAX_SAY_MESSAGE_LENGTH,), parse_gm_command(longest_legitimate).args
        )
        self.assertEqual(
            ("a" * MAX_SAY_MESSAGE_LENGTH,),
            parse_gm_command(longest_legitimate + "    ").args,
        )
        with self.assertRaises(GmCommandParseError):
            parse_gm_command("x" * (commands_module.MAX_COMMAND_LINE_LENGTH + 1))

    def test_a_line_at_the_cap_is_accepted_and_one_over_it_is_not(self):
        at_cap = "say " + "a" * (commands_module.MAX_COMMAND_LINE_LENGTH - 4)
        self.assertEqual(commands_module.MAX_COMMAND_LINE_LENGTH, len(at_cap))
        # Refused by `say`'s own cap, not by the line cap -- the two are
        # different sentences and the boundary must say which one it hit.
        with self.assertRaises(GmCommandParseError) as raised:
            parse_gm_command(at_cap)
        self.assertIn("say message", str(raised.exception))
        with self.assertRaises(GmCommandParseError) as raised:
            parse_gm_command(at_cap + "a")
        self.assertIn("command line", str(raised.exception))


class TheSceneSelectorSplitTests(unittest.TestCase):
    """The rightmost `#n` wins, and the digits come back as typed."""

    def test_the_selector_comes_back_as_the_digits_that_were_typed(self):
        self.assertEqual(
            ("Hidden Island ", "11"),
            commands_module._split_scene_selector("Hidden Island #11"),
        )
        self.assertEqual(
            ("Hidden Island ", "0000000000011"),
            commands_module._split_scene_selector("Hidden Island #0000000000011"),
        )

    def test_the_last_selector_wins_which_no_printed_message_reveals(self):
        """pf-adversary round `53rdv8` M9: `rpartition` -> `partition` survived.

        Both spellings REFUSE `Hidden Island #1 #2` -- one because
        `Hidden Island #1` is not in the catalog, the other because
        `1 #2` is not digits -- so no assertion on a parse result can tell
        them apart.  The rule lives on this function, so it is pinned on
        this function.
        """
        self.assertEqual(
            ("Hidden Island #1 ", "2"),
            commands_module._split_scene_selector("Hidden Island #1 #2"),
        )

    def test_a_line_with_no_selector_comes_back_unchanged(self):
        self.assertEqual(
            ("Hidden Island", None),
            commands_module._split_scene_selector("Hidden Island"),
        )
        self.assertEqual(
            ("Scene#3", None), commands_module._split_scene_selector("Scene#3")
        )


class TheOutOfRangeSelectorEchoTests(unittest.TestCase):
    """pf-adversary round `53rdv8` D9: it answered a question nobody asked."""

    def test_an_out_of_range_selector_is_printed_as_typed(self):
        with self.assertRaises(GmCommandParseError) as raised:
            parse_gm_command("warp Bear Island #0000000000011")
        message = str(raised.exception)
        self.assertIn("#0000000000011", message)
        # `#11` used to be what an operator who typed thirteen digits read
        # back, which is not a line you can check against your own screen.
        self.assertNotIn("#11 names", message)
        message.encode("cp874")

    def test_the_range_it_offers_is_still_the_table_s_own(self):
        with self.assertRaises(GmCommandParseError) as raised:
            parse_gm_command("warp Hidden Island #99")
        self.assertIn("#1 to #20", str(raised.exception))

    def test_a_selector_in_range_still_resolves_however_it_is_spelled(self):
        self.assertEqual(
            parse_gm_command("warp Hidden Island #0000000000011").args,
            parse_gm_command("warp Hidden Island #11").args,
        )


class TheLineCapDerivationHasTwoArmsTests(unittest.TestCase):
    """pf-adversary round `pdf3gh` D7: written inline, one arm was dead.

    `max(MAX_SAY_MESSAGE_LENGTH, MAX_WARP_NAME_QUERY_LENGTH)` is 480
    against 108, so the `warp` side of that `max()` could not be reached by
    any input, and three mutants of the expression survived the suite.
    These call the derivation directly, with the arms swapped, so the RULE
    is pinned rather than the number 488.
    """

    def test_the_widest_allowance_wins_when_it_is_the_warp_one(self):
        # `min` in place of `max` returns 118 here and 488 for the real
        # constants -- this is the case that can tell them apart.
        self.assertEqual(
            489,
            commands_module._derive_max_command_line_length(7, 10, 481),
        )

    def test_the_widest_allowance_wins_when_it_is_the_say_one(self):
        self.assertEqual(
            489,
            commands_module._derive_max_command_line_length(7, 481, 10),
        )

    def test_dropping_either_allowance_is_a_different_answer(self):
        both = commands_module._derive_max_command_line_length(7, 10, 481)
        self.assertNotEqual(
            both, commands_module._derive_max_command_line_length(7, 10)
        )
        self.assertEqual(
            both, commands_module._derive_max_command_line_length(7, 481)
        )

    def test_the_separator_is_counted_exactly_once(self):
        self.assertEqual(
            commands_module._derive_max_command_line_length(7, 480) + 1,
            commands_module._derive_max_command_line_length(8, 480),
        )

    def test_the_live_constant_is_that_rule_applied_to_the_live_caps(self):
        self.assertEqual(
            commands_module.MAX_COMMAND_LINE_LENGTH,
            commands_module._derive_max_command_line_length(
                commands_module.LONGEST_COMMAND_NAME_LENGTH,
                commands_module.MAX_SAY_MESSAGE_LENGTH,
                commands_module.MAX_WARP_NAME_QUERY_LENGTH,
            ),
        )


class TheAuditWriterChecksTheSizeItWasPromisedTests(unittest.TestCase):
    """pf-adversary round `pdf3gh` D2: the cap lived in the parser only.

    `log_gm_command` never read `command.raw`, so a hand-built `GmCommand`
    wrote whatever it carried into the ndjson audit as one line.
    """

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.log_path = Path(self._dir.name) / "gm.ndjson"

    def test_a_hand_built_raw_over_the_cap_is_refused_not_written(self):
        oversized = "say hi" + " " * commands_module.MAX_COMMAND_LINE_LENGTH
        with self.assertRaises(GmCommandArgsError):
            log_gm_command(
                GmCommand("say", ("hi",), oversized),
                "panya",
                log_path=self.log_path,
                now_ts=0,
            )
        # Refused BEFORE the append, not after: an audit file that already
        # holds the line is not defended by an exception.
        self.assertFalse(self.log_path.exists())

    def test_a_hand_built_arg_over_the_cap_is_refused_too(self):
        body = "x" * (commands_module.MAX_COMMAND_LINE_LENGTH + 1)
        with self.assertRaises(GmCommandArgsError):
            log_gm_command(
                GmCommand("say", (body,), "say hi"),
                "panya",
                log_path=self.log_path,
                now_ts=0,
            )
        self.assertFalse(self.log_path.exists())

    def test_a_non_str_arg_keeps_the_error_the_serializer_already_gave(self):
        # The size check must not take over a shape the audit writer
        # already answers: round `w8t8vi` pinned `TypeError` from
        # `json.dumps`, before any filesystem mutation.
        class Weird:
            def __repr__(self):
                return "<Weird>"

        with self.assertRaises(TypeError):
            log_gm_command(
                GmCommand("warp", (Weird(),), "warp x"),
                "panya",
                log_path=self.log_path,
                now_ts=0,
            )
        self.assertFalse(self.log_path.exists())

    def test_a_str_subclass_cannot_lie_its_way_past_the_length(self):
        class _ShortLiar(str):
            def __len__(self):  # noqa: D105 - the lie under test
                return 1

        with self.assertRaises(GmCommandArgsError):
            log_gm_command(
                GmCommand("say", ("hi",), _ShortLiar("z" * 200_000)),
                "panya",
                log_path=self.log_path,
                now_ts=0,
            )
        self.assertFalse(self.log_path.exists())

    def test_every_line_the_grammar_accepts_is_still_written(self):
        # The check re-asserts the parser's promise; it must not narrow it.
        # A `say` at its own ceiling is the longest line this grammar has.
        at_ceiling = "say " + "a" * MAX_SAY_MESSAGE_LENGTH
        command = parse_gm_command(at_ceiling)
        self.assertLessEqual(
            len(command.raw), commands_module.MAX_COMMAND_LINE_LENGTH
        )
        log_gm_command(command, "panya", log_path=self.log_path, now_ts=0)
        row = json.loads(self.log_path.read_text(encoding="utf-8").strip())
        self.assertEqual(at_ceiling, row["raw"])


class TheRefusedWarpNameSaysWhatItFoundTests(unittest.TestCase):
    """pf-adversary round `pdf3gh` D1: the catalog search had no reader.

    `suggest_gm_scene_names` computed real names and `chat_command.py` threw
    the sentence away, so the console line for `/warp Atlantic` was
    byte-identical before and after that search was written.
    """

    def test_a_near_miss_now_names_the_scenes_the_table_holds(self):
        hint = commands_module.refusal_hint_for("warp Atlantic")
        self.assertIn("did you mean", hint)
        self.assertIn("Atlantic Ocean1", hint)

    def test_the_usage_sentence_is_still_the_first_thing_it_says(self):
        hint = commands_module.refusal_hint_for("warp Atlantic")
        self.assertTrue(hint.startswith(commands_module.COMMAND_USAGE["warp"]))

    def test_nothing_typed_reaches_the_line(self):
        # A marker that appears in none of the 330 shipped names, so its
        # presence in the output could only have come from the query.
        marker = "ZZQX"
        hint = commands_module.refusal_hint_for(f"warp Atlantic{marker}")
        self.assertNotIn(marker, hint)

    def test_the_numeric_form_is_not_a_spelling_question(self):
        self.assertEqual(
            commands_module.usage_hint_for("warp 99999"),
            commands_module.refusal_hint_for("warp 99999"),
        )

    def test_no_other_verb_grows_a_clause(self):
        for body in ("lv abc", "spawn zzz", "say", "nonsense", ""):
            with self.subTest(body=body):
                self.assertEqual(
                    commands_module.usage_hint_for(body),
                    commands_module.refusal_hint_for(body),
                )

    def test_a_query_the_name_form_would_refuse_is_never_searched(self):
        over_cap = "q" * (commands_module.MAX_WARP_NAME_QUERY_LENGTH + 1)
        self.assertEqual(
            commands_module.usage_hint_for("warp " + over_cap),
            commands_module.refusal_hint_for("warp " + over_cap),
        )
        # A homoglyph the console codec has no byte for gets the same
        # treatment as it does one layer down, for the same reason.
        self.assertEqual(
            commands_module.usage_hint_for("warp \u0410tlantic"),
            commands_module.refusal_hint_for("warp \u0410tlantic"),
        )

    def test_every_line_it_can_print_survives_the_console_codec(self):
        for query in ("Atlantic", "Prison", "Island", "Sea", "Port"):
            with self.subTest(query=query):
                commands_module.refusal_hint_for(f"warp {query}").encode(
                    commands_module.QUERY_CONSOLE_CODEC
                )


if __name__ == "__main__":
    unittest.main()
