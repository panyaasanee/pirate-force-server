"""GM-003 v1: GM command grammar -- parse and log only, no gameplay effect."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.commands import (
    MAX_SAY_MESSAGE_LENGTH,
    GmCommandParseError,
    describe_npc_target,
    describe_warp_target,
    log_gm_command,
    parse_gm_command,
)


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


if __name__ == "__main__":
    unittest.main()
