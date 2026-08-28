"""GM-003 v1: GM command grammar -- parse and log only, no gameplay effect."""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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

    @unittest.skipUnless(os.name == "posix", "POSIX mode bits only")
    def test_log_directory_mode_is_retightened_on_a_preexisting_loose_directory(self):
        # Sibling of gm/command_capture.py's identical fix (pf-adversary
        # verification pass, same round): `mkdir(..., exist_ok=True)` never
        # chmods a directory that already exists, and this function shares
        # its literal parent (`capture/`) with command_capture.py's own
        # default root -- whichever function runs first on a real host
        # locks that shared parent's mode in, forever, without this.
        # Simulate "some earlier call already created it loose."
        nested_log_path = Path(self._tmp.name) / "preexisting" / "gm_command_log.ndjson"
        nested_log_path.parent.mkdir(mode=0o777)
        os.chmod(nested_log_path.parent, 0o777)
        self.assertEqual(stat.S_IMODE(nested_log_path.parent.stat().st_mode), 0o777)
        old_umask = os.umask(0o022)
        try:
            log_gm_command(
                parse_gm_command("lv 1"), "panya", log_path=nested_log_path, now_ts=0
            )
        finally:
            os.umask(old_umask)
        mode = stat.S_IMODE(nested_log_path.parent.stat().st_mode)
        self.assertEqual(mode, 0o700, oct(mode))


if __name__ == "__main__":
    unittest.main()
