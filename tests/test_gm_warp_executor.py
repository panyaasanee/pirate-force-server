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


class WarpExecutorArgsShapeTests(unittest.TestCase):
    """gm/say_wire.py's own docstring (pf-adversary, say-wire round) named
    this module's identical, at-the-time-unfixed gap: command.args was
    measured/indexed with plain len()/[0]/[1]/[2], which raises a bare
    TypeError/KeyError/IndexError -- never WarpExecutorError -- for an args
    container of the wrong shape (None, a set, a dict), not just the wrong
    value. These tests prove that gap is closed here too.
    """

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_refuses_none_args_with_warp_executor_error_not_bare_type_error(self):
        bad = GmCommand("warp", None, "warp 1 100 200")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)
        self.assertNotIsInstance(ctx.exception, TypeError)

    def test_refuses_a_set_args_container_with_warp_executor_error_not_bare_type_error(self):
        bad = GmCommand("warp", {1, 100, 200}, "warp 1 100 200")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)
        self.assertNotIsInstance(ctx.exception, TypeError)

    def test_refuses_a_dict_args_container_with_warp_executor_error_not_bare_key_error(self):
        bad = GmCommand(
            "warp", {"scene_id": 1, "x": 100, "y": 200}, "warp 1 100 200"
        )
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)
        self.assertNotIsInstance(ctx.exception, KeyError)

    def test_refuses_a_str_args_scalar_instead_of_silently_reading_its_characters(self):
        # pf-adversary (this round): "123" passes len()==3 and is positionally
        # indexable, so without an explicit str/bytes guard this would have
        # silently built a real ForcePos frame from scene_id='1', x='2', y='3'
        # instead of refusing a container that was never the intended
        # (scene_id, x, y) sequence.
        bad = GmCommand("warp", "123", "warp 123")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)

    def test_refuses_a_bytes_args_scalar_instead_of_silently_reading_its_bytes(self):
        bad = GmCommand("warp", b"123", "warp b123")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)

    def test_refuses_an_args_object_whose_len_raises_outside_the_original_three_types(self):
        # pf-adversary (this round): the first draft of this fix only caught
        # TypeError/KeyError/IndexError, so a custom __len__ raising anything
        # else (e.g. ValueError) still leaked past WarpExecutorError.
        class WeirdLen:
            def __len__(self):
                raise ValueError("boom")

            def __getitem__(self, i):
                return 1

        bad = GmCommand("warp", WeirdLen(), "warp weird")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)
        # WarpExecutorError subclasses ValueError, so a bare ValueError leak
        # would still pass assertRaises(WarpExecutorError) above -- the real
        # assertion is that it is exactly this module's own error type.
        self.assertIsInstance(ctx.exception, WarpExecutorError)
        self.assertIs(type(ctx.exception), WarpExecutorError)

    def test_refuses_an_args_object_whose_getitem_raises_outside_the_original_three_types(self):
        class WeirdGetitem:
            def __len__(self):
                return 3

            def __getitem__(self, i):
                raise AttributeError("nope")

        bad = GmCommand("warp", WeirdGetitem(), "warp weird")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)
        self.assertNotIsInstance(ctx.exception, AttributeError)

    def test_refuses_an_integer_keyed_dict_instead_of_silently_reading_it_positionally(self):
        # pf-adversary (say-wire args-shape follow-up round): a dict keyed
        # 0/1/2 passes len()==3 and is indexable at [0]/[1]/[2] without ever
        # raising, so the previous blacklist (str/bytes guard + broad except)
        # never caught it -- it silently built a real ForcePos frame from a
        # dict that was never the intended (scene_id, x, y) tuple. The
        # isinstance(args, tuple) allowlist closes this without needing to
        # special-case dicts at all.
        bad = GmCommand("warp", {0: 1, 1: 100.0, 2: 200.0}, "warp 1 100 200")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)
        self.assertNotIsInstance(ctx.exception, KeyError)

    def test_refuses_a_list_args_container(self):
        # GmCommand.args is typed tuple[str, ...]; a list is a plausible
        # caller mistake (JSON deserializes arrays as lists) that behaves
        # identically to a tuple under len()/indexing, so it was never
        # caught by any of the previous guards either.
        bad = GmCommand("warp", ["1", "100", "200"], "warp 1 100 200")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)

    def test_refuses_a_bytearray_args_scalar(self):
        bad = GmCommand("warp", bytearray(b"123"), "warp 123")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)


if __name__ == "__main__":
    unittest.main()
