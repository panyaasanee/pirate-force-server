"""CORE-REQUEST-011: same-scene warp execution via ForcePos."""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm.commands import GmCommand, parse_gm_command
from pirateforce_foundation.gm.teleport_wire import (
    FORCE_POS_VITAL_ID,
    decode_force_pos,
    make_force_pos_payload,
)
from pirateforce_foundation.gm.warp_executor import (
    WarpExecutorError,
    WarpTarget,
    make_warp_force_pos_frame,
    make_warp_teleport_frame_no_coords_with_target,
    make_warp_teleport_frame_with_target,
    warp_no_coords_live_target,
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

    def test_refuses_a_scene_id_element_whose_dunder_int_raises_a_non_value_error(self):
        # pf-adversary (round w8t8vi): _require_int only caught
        # (TypeError, ValueError). A hand-built args element whose __int__
        # raises anything else (AttributeError here) is still a shape-valid
        # 3-tuple, so it never touched the args-container guard above -- it
        # leaked a bare AttributeError past this module's own promised
        # WarpExecutorError-only contract.
        class EvilInt:
            def __int__(self):
                raise AttributeError("boom int")

        bad = GmCommand("warp", (EvilInt(), "1", "2"), "warp x 1 2")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame(self.legacy, 1, bad, 0, 0.0)

    def test_refuses_an_x_element_whose_dunder_float_raises_a_non_value_error(self):
        class EvilFloat:
            def __float__(self):
                raise KeyError("boom float")

        bad = GmCommand("warp", ("1", EvilFloat(), "2"), "warp 1 x 2")
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

    def test_refuses_a_tuple_subclass_whose_len_lies_with_an_uncaught_exception(self):
        # pf-adversary (second pass, same round): isinstance(args, tuple)
        # admits any subclass, including one that overrides __len__ to
        # raise something other than WarpExecutorError. GmCommand is a
        # plain frozen dataclass (gm/commands.py) with no validation, so
        # nothing stops a hand-built GmCommand from carrying one -- exactly
        # the "regardless of source" threat model this module's docstring
        # claims to defend against. type(args) is not tuple rejects every
        # subclass outright, so this must never reach the lying __len__.
        class EvilTuple(tuple):
            def __len__(self):
                raise RuntimeError("boom-len")

        bad = GmCommand("warp", EvilTuple((1, 2.0, 3.0)), "warp 1 2 3")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)
        self.assertNotIsInstance(ctx.exception, RuntimeError)

    def test_refuses_a_tuple_subclass_whose_getitem_lies_with_an_uncaught_exception(self):
        class EvilTuple(tuple):
            def __getitem__(self, i):
                raise KeyError("boom-getitem")

        bad = GmCommand("warp", EvilTuple((1, 2.0, 3.0)), "warp 1 2 3")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, bad, 1, 0.0)
        self.assertNotIsInstance(ctx.exception, KeyError)


class WarpTeleportCrossSceneTests(unittest.TestCase):
    """CORE-REQUEST: cross-scene warp via legacy.make_login_teleport.

    COO-DECISION 2026-08-31T14:41+07:00 (pf_bridge/notes_to_chief/
    20260831_1441_COO-DECISION-warp-cross-scene-opens-gt106r2-passed.md)
    authorizes this. Scene 17 is the one destination GT-106-R2 measured a
    real client rendering; scene 278 is used elsewhere in this codebase's
    own gm/login_scene_stage tests as a plain, catalog-known, non-
    sanctioned scene, so it doubles as a second known-good id here without
    inventing a new fixture value.
    """

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_builds_the_exact_bytes_make_login_teleport_would(self):
        # (-13270, 22794) replaces this test's original (100, 200) fixture
        # (round `<ground-gate round>`): 278's own ground_extent (opened by
        # LANE-A, `20260901_2252_LANE-A-REPLY-...`) makes (100, 200) a real
        # off-map point now, and `_refuse_if_outside_ground` refuses it --
        # this test is about exact byte-encoding, not about the ground gate
        # (see WarpExecutorGroundGateTests for that), so it moves to a point
        # this project's own registry proves is on 278's ground (near its
        # spawn) rather than asserting around the new refusal.
        command = parse_gm_command("warp 278 -13270 22794")
        pc, frame, _target = make_warp_teleport_frame_with_target(
            self.legacy, command, 30.0
        )
        expected_pc, expected_frame = self.legacy.make_login_teleport(
            278, 0, -13270.0, 22794.0, 30.0
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_scene_seq_is_always_the_shared_scene_sequence_constant(self):
        # population.SCENE_SEQUENCE is 0 -- "the only value ever measured, at
        # scene 1 and at scene 2 alike" per that module's own docstring.
        # Reused here rather than re-derived so a future correction fixes
        # this module for free.
        from pirateforce_foundation.population import SCENE_SEQUENCE

        self.assertEqual(SCENE_SEQUENCE, 0)
        command = parse_gm_command("warp 17 834 -598")
        pc, _frame, target = make_warp_teleport_frame_with_target(
            self.legacy, command, 0.0
        )
        expected_pc, _ = self.legacy.make_login_teleport(
            17, SCENE_SEQUENCE, 834.0, -598.0, 0.0
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(target.scene_id, 17)

    def test_the_target_carries_the_wire_binary32_values_not_the_python_floats(self):
        # (-13270.7, 22794) replaces this test's original (11865.7, 6147)
        # fixture, same reason and same round as
        # test_builds_the_exact_bytes_make_login_teleport_would above: 278's
        # real ground_extent makes the old point off-map, and this test is
        # about binary32 rounding, not about the ground gate. -13270.7 keeps
        # the decimal (the whole point -- it must round differently in f32
        # than in Python's float64) while staying inside 278's ground.
        command = parse_gm_command("warp 278 -13270.7 22794")
        _, _, target = make_warp_teleport_frame_with_target(
            self.legacy, command, -3.25
        )
        self.assertIsInstance(target, WarpTarget)
        expected_x = struct.unpack("<f", struct.pack("<f", -13270.7))[0]
        self.assertEqual(target.x, expected_x)
        self.assertNotEqual(target.x, -13270.7)  # the whole point of the test
        self.assertEqual(target.y, 22794.0)
        self.assertEqual(target.z, -3.25)
        self.assertEqual(target.scene_id, 278)

    def test_refuses_a_non_warp_command(self):
        command = parse_gm_command("lv 60")
        with self.assertRaises(WarpExecutorError):
            make_warp_teleport_frame_with_target(self.legacy, command, 0.0)

    def test_refuses_the_coordinate_less_form(self):
        # There is still no position for TeleportVital to carry either --
        # this shape stays gm/login_scene_stage.py's job.
        command = parse_gm_command("warp 278")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_teleport_frame_with_target(self.legacy, command, 0.0)
        self.assertIn("stages", str(ctx.exception))

    def test_refuses_an_unknown_scene_id_rather_than_composing_blind(self):
        command = parse_gm_command("warp 999999 0 0")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_teleport_frame_with_target(self.legacy, command, 0.0)
        self.assertIn("999999", str(ctx.exception))

    def test_refuses_non_finite_coordinates(self):
        command = parse_gm_command("warp 278 100 200")
        with self.assertRaises(WarpExecutorError):
            make_warp_teleport_frame_with_target(
                self.legacy, command, float("nan")
            )
        bad = GmCommand("warp", ("278", "nan", "1"), "warp 278 nan 1")
        with self.assertRaises(WarpExecutorError):
            make_warp_teleport_frame_with_target(self.legacy, bad, 0.0)

    def test_refuses_a_non_tuple_args_container_same_as_the_force_pos_path(self):
        # Both composers share `_require_args_tuple`; one regression test
        # here is enough to prove the sharing, not a second full sweep of
        # every shape WarpExecutorArgsShapeTests already covers.
        bad = GmCommand("warp", {0: 278, 1: 100.0, 2: 200.0}, "warp 278 100 200")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_teleport_frame_with_target(self.legacy, bad, 0.0)
        self.assertNotIsInstance(ctx.exception, KeyError)


class WarpNoCoordsLiveTargetTests(unittest.TestCase):
    """GM-A (`R278`, round jd4jqp): `warp_no_coords_live_target`'s own gate."""

    def test_a_marker_backed_scene_returns_its_destination(self):
        target = warp_no_coords_live_target(4)
        self.assertIsNotNone(target)
        self.assertEqual(target.n_id, 4)
        self.assertTrue(target.has_authored_entry)

    def test_scenes_gt182_names_as_examples_all_qualify(self):
        # GT-182's own objective text: "pick one already opened by LANE-A,
        # e.g. scene 4/5/6/8/10". One assertion per id, not a loop that
        # hides which one broke.
        for scene_id in (4, 5, 6, 8, 10):
            with self.subTest(scene_id=scene_id):
                self.assertIsNotNone(warp_no_coords_live_target(scene_id))

    def test_a_markerless_scene_with_a_pinned_spawn_still_returns_none(self):
        # Scene 278: n_MARKER == 0, but world_scene_travel DOES carry a
        # pinned (native-placement, "authored" evidence tier) spawn for it.
        # GT-182 nonclaim 4 says this scene keeps the OLD stage-only rule --
        # the point of this test is that "has a spawn" alone would get this
        # wrong; the gate has to be `has_authored_entry`, not `spawn is not
        # None`.
        target = world_scene_travel.destination(278)
        self.assertIsNotNone(target.spawn)
        self.assertFalse(target.has_authored_entry)
        self.assertIsNone(warp_no_coords_live_target(278))

    def test_a_scene_id_not_in_the_registry_at_all_returns_none(self):
        self.assertIsNone(warp_no_coords_live_target(999999))

    def test_a_malformed_scene_id_still_raises(self):
        with self.assertRaises(WarpExecutorError):
            warp_no_coords_live_target("not-an-int")


class WarpTeleportFrameNoCoordsTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_builds_a_live_teleport_at_the_pinned_marker_spawn(self):
        target = world_scene_travel.destination(4)
        x, y, z = world_scene_travel.spawn_position(target)
        pc, frame, wire_target = make_warp_teleport_frame_no_coords_with_target(
            self.legacy, 4
        )
        expected_pc, expected_frame = self.legacy.make_login_teleport(
            4, 0, x, y, z
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))
        self.assertEqual(wire_target.scene_id, 4)
        self.assertEqual((wire_target.x, wire_target.y, wire_target.z), (x, y, z))

    def test_the_z_comes_from_the_marker_not_from_a_caller_argument(self):
        # This function takes no z parameter at all -- GT-172's F-2 (old
        # scene's z carried over) cannot reproduce here because there is no
        # caller-supplied z to carry.
        import inspect

        params = inspect.signature(
            make_warp_teleport_frame_no_coords_with_target
        ).parameters
        self.assertEqual(set(params), {"legacy", "scene_id"})

    def test_refuses_a_markerless_destination(self):
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_teleport_frame_no_coords_with_target(self.legacy, 278)
        self.assertIn("278", str(ctx.exception))

    def test_refuses_an_unknown_scene_id(self):
        with self.assertRaises(WarpExecutorError):
            make_warp_teleport_frame_no_coords_with_target(self.legacy, 999999)


class WarpExecutorGroundGateTests(unittest.TestCase):
    """LANE-A-REPLY `20260901_2252` opened `world_scene_entry.
    is_position_within_scene_ground` for this lane to import; these tests
    prove `warp_executor._refuse_if_outside_ground` uses it correctly on
    both frame builders, without regressing the one cross-scene destination
    (scene 17) COO-DECISION 2026-08-31T14:41+07:00 already authorized.

    Bounds used below (`world_scene_travel.destination(278)`, measured, not
    invented): spawn (-13270.0576171875, 22794.2734375), ground_extent
    (6195.029296875, 2209.421875) -- so x in [-19465.09, -7075.03], y in
    [20584.85, 25003.70] is inside, and (0, 0) is far outside either axis.
    """

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_refuses_a_same_scene_warp_outside_scene_278s_ground_extent(self):
        command = parse_gm_command("warp 278 0 0")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_force_pos_frame(self.legacy, 1, command, 278, 0.0)
        self.assertIn("outside scene 278", str(ctx.exception))

    def test_accepts_a_same_scene_warp_inside_scene_278s_ground_extent(self):
        command = parse_gm_command("warp 278 -13270.0576171875 22794.2734375")
        # Must not raise -- this is the same call shape the refusal test
        # above uses, at a point this project's own registry proves is on
        # the ground (278's spawn itself).
        make_warp_force_pos_frame(self.legacy, 1, command, 278, 0.0)

    def test_refuses_a_cross_scene_warp_outside_scene_278s_ground_extent(self):
        command = parse_gm_command("warp 278 0 0")
        with self.assertRaises(WarpExecutorError) as ctx:
            make_warp_teleport_frame_with_target(self.legacy, command, 0.0)
        self.assertIn("outside scene 278", str(ctx.exception))

    def test_does_not_refuse_the_proven_scene_17_cross_scene_warp(self):
        # Regression guard: scene 17's ONLY spawn evidence is a
        # PROVISIONAL-OWNER-DECREE, so is_position_within_scene_ground(17,
        # *, *) is False for every point, including this exact one --
        # GT-106-R2 measured a real client receiving and rendering it, and
        # WarpTeleportCrossSceneTests.
        # test_scene_seq_is_always_the_shared_scene_sequence_constant above
        # already pins the call succeeding. A hard ground gate must not
        # start refusing it.
        command = parse_gm_command("warp 17 834 -598")
        # Must not raise.
        make_warp_teleport_frame_with_target(self.legacy, command, 0.0)

    def test_still_does_not_check_a_scene_with_no_ground_evidence_at_all(self):
        # Scene 2 has ground_extent=None in today's registry -- the exact
        # scene named in the original bug report (`/warp 2 100000 200`,
        # pf_bridge/notes_to_chief/20260901_2028_LANE-GM-TO-LANE-A-...).
        # This module still cannot protect against that specific report
        # until scene 2 gains ground evidence -- documented as a STILL OPEN
        # gap in gm/chat_command_action.py's docstring, not silently
        # narrowed here.
        command = parse_gm_command("warp 2 100000 200")
        # Must not raise (scene_id == current_scene_id keeps the existing
        # same-scene check happy; only the new ground gate is under test).
        make_warp_force_pos_frame(self.legacy, 1, command, 2, 0.0)


if __name__ == "__main__":
    unittest.main()
