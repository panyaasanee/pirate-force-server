"""CORE-REQUEST-011: same-scene warp execution via ForcePos."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm.commands import GmCommand, parse_gm_command
from pirateforce_foundation.gm.teleport_wire import (
    FORCE_POS_VITAL_ID,
    decode_force_pos,
    make_force_pos_payload,
)
from pirateforce_foundation.gm.warp_executor import (
    WarpExecutorError,
    make_warp_force_pos_frame,
)


class WarpExecutorSameSceneTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_same_scene_warp_builds_a_force_pos_frame(self):
        command = parse_gm_command("warp 1 11865 6147")
        pc, frame = make_warp_force_pos_frame(self.legacy, 1, command, 1, -3.0)
        expected_pc, expected_frame = self.legacy.make_runtime_vital(
            FORCE_POS_VITAL_ID,
            1,
            make_force_pos_payload(self.legacy, 11865.0, 6147.0, -3.0),
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_round_trips_command_coordinates_through_decode(self):
        command = parse_gm_command("warp 3 100.5 200.25")
        _, frame = make_warp_force_pos_frame(self.legacy, 1, command, 3, 7.0)
        _, expected_frame = self.legacy.make_runtime_vital(
            FORCE_POS_VITAL_ID,
            1,
            make_force_pos_payload(self.legacy, 100.5, 200.25, 7.0),
        )
        self.assertEqual(frame, expected_frame)
        body = decode_force_pos(
            make_force_pos_payload(self.legacy, 100.5, 200.25, 7.0)
        )
        self.assertEqual((body.x, body.y, body.z), (100.5, 200.25, 7.0))


class WarpExecutorRefusalTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_refuses_a_non_warp_command(self):
        command = parse_gm_command("lv 60")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, command, 1, 0.0)

    def test_refuses_scene_only_warp_with_no_coordinates(self):
        command = parse_gm_command("warp 1")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, command, 1, 0.0)

    def test_refuses_when_command_scene_id_differs_from_current_scene(self):
        command = parse_gm_command("warp 2 100 200")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, command, 1, 0.0)

    def test_cross_scene_refusal_does_not_silently_send_an_in_scene_hop(self):
        # Regression guard: a naive implementation might ignore scene_id and
        # always build a ForcePos frame from whatever x/y the command carries.
        # That would misrepresent what ForcePos actually did (see module
        # docstring) -- this must raise, not return a frame.
        command = parse_gm_command("warp 999 0 0")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, command, 1, 0.0)
        self.assertIn("999", str(ctx.exception))
        self.assertIn("cannot cross scenes", str(ctx.exception))


class WarpExecutorAdversaryFindingsTests(unittest.TestCase):
    """pf-adversary (warp-executor round): z is not part of the `warp`
    grammar so it never passes through parse_gm_command's finiteness check,
    and docs/GM_LANE.md commits to accepting a GmCommand "regardless of
    source" -- so a caller can hand this module x/y that never went through
    _require_number either. These tests prove the module re-validates every
    numeric field itself rather than relying on the caller having used
    parse_gm_command.
    """

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_refuses_non_finite_z_on_an_otherwise_valid_parsed_command(self):
        command = parse_gm_command("warp 1 100 200")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, command, 1, float("nan"))
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, command, 1, float("inf"))

    def test_refuses_non_finite_x_or_y_from_a_command_not_built_by_parse_gm_command(self):
        bad = GmCommand("warp", ("1", "nan", "inf"), "warp 1 nan inf")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)

    def test_refuses_a_non_integer_scene_id_with_warp_executor_error_not_bare_value_error(self):
        bad = GmCommand("warp", ("not-a-scene", "1", "2"), "warp not-a-scene 1 2")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)

    def test_refuses_non_numeric_x_with_warp_executor_error_not_bare_value_error(self):
        bad = GmCommand("warp", ("1", "not-a-number", "2"), "warp 1 not-a-number 2")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)


if __name__ == "__main__":
    unittest.main()
