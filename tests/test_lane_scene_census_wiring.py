"""CORE-REQUEST (LANE-A 20260829_1845) -- the lane scene census point, on
the REAL dispatcher.

runtime.py's WORLD-CENSUS block used to be one dedicated branch per scene
(bg0001's else, bg0002's elif), so every finished population module waited
for a chief round to hand-splice a new elif -- the exact critical-path
shape lane_hooks exists to remove.  The new branch this file proves asks
``lane_hooks.scene_census_composer(scene_id)`` for every scene the
dedicated branches do not already claim, reads
``module_production_allowed()`` for the owning module (COO-DECISION
20260829_0041 option (b)), and consumes the ``SceneCensusResult`` contract
and nothing else.

Scene 278 (Bg1177, 'beach football field (TEST)') is used as the lane
scene because it is real in scene_entry_registry (login_entry_allowed) and
is BUILD-002's own named first target -- but the composer registered here
is a test double writing straight into lane_hooks' registry with cleanup,
never a file in the lane_hooks package directory.  No lane has shipped a
real composer as of this test's first commit; the day one ships, its own
wiring proof belongs to that lane's PR, not here.

Seeding a stored row at scene 278 uses the same direct
``store.save_position`` write into a throwaway per-test SQLite database as
tests/test_bg0002_census_wiring.py, for the same recorded reason: nothing
in this tree seeds a non-default scene on a real boot yet.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
LANE_SCENE_N_ID = 278
FAKE_MODULE = "pirateforce_foundation.lane_hooks._test_only_lane_census"
STEP_ANCHOR = (11.0, 22.0, 33.0)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class LaneSceneCensusWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        # Every test leaves the shared registry exactly as it found it --
        # same discipline as test_lane_hooks.py's private-point cleanup.
        self.addCleanup(
            lane_hooks._SCENE_CENSUS_COMPOSERS.pop, LANE_SCENE_N_ID, None,
        )
        self.addCleanup(
            lane_hooks._SCENE_CENSUS_COMPOSERS.pop,
            world_population.SCENE_ID, None,
        )
        self.addCleanup(
            lane_hooks._PRODUCTION_ALLOWED.pop, FAKE_MODULE, None,
        )

    # ----- harness (same shape as test_bg0002_census_wiring.py) --------

    def _target_pos_pc(self, xyz, heading=0.0, moving=0, derived=0):
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + b"".join(
                self.legacy.f32tag(value) for value in (*xyz, heading)
            )
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, derived)
        )

    def _step(self, state, xyz=STEP_ANCHOR, **kwargs):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(
                self.legacy.parse_outer(self._target_pos_pc(xyz, **kwargs))
            )
        return actions, buf.getvalue()

    def _state_at_scene(self, token, scene_id):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(
            self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC)
        )
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        if scene_id != world_population.SCENE_ID:
            destination = world_scene_travel.destination(scene_id)
            spawn = world_scene_travel.spawn_position(destination)
            self.store.select_character(
                state.foundation.session_id, character.selector,
            )
            self.store.save_position(
                state.foundation.session_id, character.id,
                Position(scene_id, 0, spawn[0], spawn[1], spawn[2], 0.0),
            )
        with contextlib.redirect_stdout(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    def _register(self, compose, scene_id=LANE_SCENE_N_ID, allowed=True):
        lane_hooks._SCENE_CENSUS_COMPOSERS[scene_id] = (
            lane_hooks.SceneCensusComposer(FAKE_MODULE, compose)
        )
        lane_hooks._PRODUCTION_ALLOWED[FAKE_MODULE] = allowed

    def _census(self, actions):
        return [
            action for action in actions
            if action[0].startswith("WORLD_CENSUS_")
        ]

    def _result(self, actor_count=5):
        return lane_hooks.SceneCensusResult(
            actor_count=actor_count,
            pc=b"\x01lane-census-pc",
            frame=b"\x02lane-census-frame",
            console_lines=(
                "LANE_CENSUS_TEST_LINE_ONE",
                "LANE_CENSUS_TEST_LINE_TWO",
            ),
            initial_reapply_ms=3000,
        )

    # ----- the point itself --------------------------------------------

    def test_a_registered_composer_owns_its_scenes_census(self):
        seen = {}

        def compose(**kwargs):
            seen.update(kwargs)
            return self._result()

        self._register(compose)
        state = self._state_at_scene("lane_census_owns", LANE_SCENE_N_ID)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            actions, out = self._step(state)
        census = self._census(actions)
        self.assertEqual(
            [action[0] for action in census],
            [
                f"WORLD_CENSUS_LANE_SCENE{LANE_SCENE_N_ID}_INITIAL_5",
                f"WORLD_CENSUS_LANE_SCENE{LANE_SCENE_N_ID}_REAPPLY_5",
            ],
        )
        self.assertEqual(
            [(action[1], action[2], action[3]) for action in census],
            [
                (b"\x01lane-census-pc", b"\x02lane-census-frame", 0.0),
                (b"\x01lane-census-pc", b"\x02lane-census-frame", 3.0),
            ],
        )
        # Console proof lines, in the lane's order, before the frame.
        self.assertIn(
            "LANE_CENSUS_TEST_LINE_ONE\nLANE_CENSUS_TEST_LINE_TWO\n", out,
        )
        # The call contract: keyword-only, these four names.
        self.assertEqual(seen["scene_id"], LANE_SCENE_N_ID)
        self.assertEqual(
            seen["anchor"], tuple(float(v) for v in STEP_ANCHOR),
        )
        self.assertIs(seen["legacy"], self.legacy)
        self.assertIn("scene_entry_registry", seen)
        # WIRED-v2 emission token on the production path (stderr).
        self.assertIn(
            f"LANE_HOOK_FIRED {FAKE_MODULE} "
            f"scene_census_composer:{LANE_SCENE_N_ID}",
            err.getvalue(),
        )
        self.assertIn(
            "world_census_lane_committed_actors_5_pc_15_frame_18",
            state.events,
        )

    def test_the_lane_census_sends_once_not_every_poll(self):
        self._register(lambda **kwargs: self._result())
        state = self._state_at_scene("lane_census_once", LANE_SCENE_N_ID)
        first, _out = self._step(state)
        second, _out = self._step(state)
        self.assertEqual(len(self._census(first)), 2)
        self.assertEqual(self._census(second), [])

    def test_a_declining_composer_latches_a_named_skip(self):
        self._register(lambda **kwargs: None)
        state = self._state_at_scene("lane_census_decline", LANE_SCENE_N_ID)
        actions, _out = self._step(state)
        self.assertEqual(self._census(actions), [])
        self.assertIn(
            f"world_census_lane_composer_declined_scene_{LANE_SCENE_N_ID}",
            state.events,
        )
        self.assertTrue(state.world_census_sent)

    def test_a_raising_composer_refuses_and_sends_no_frame(self):
        def compose(**kwargs):
            raise ValueError("lane composer bug")

        self._register(compose)
        state = self._state_at_scene("lane_census_raises", LANE_SCENE_N_ID)
        actions, _out = self._step(state)
        self.assertEqual(self._census(actions), [])
        self.assertIn(
            "world_census_lane_composer_refused_ValueError", state.events,
        )
        self.assertTrue(state.world_census_refused)

    def test_a_closed_module_stands_down_to_the_not_home_skip(self):
        # production_allowed = False: the option (b) flag read in the
        # branch condition itself -- the composer must never be called and
        # the scene falls through to the pre-existing skip latch,
        # byte-identical to a scene with no composer at all.
        calls = []
        self._register(
            lambda **kwargs: calls.append(1) or self._result(),
            allowed=False,
        )
        state = self._state_at_scene("lane_census_closed", LANE_SCENE_N_ID)
        actions, _out = self._step(state)
        self.assertEqual(self._census(actions), [])
        self.assertEqual(calls, [])
        self.assertIn(
            f"world_census_skipped_scene_{LANE_SCENE_N_ID}_not_home",
            state.events,
        )

    def test_a_malformed_but_typed_result_is_refused_not_escaped(self):
        # pf-adversary (round 73fhoc): a well-typed SceneCensusResult whose
        # field VALUES are garbage must land in the same fail-closed net
        # as a raise -- an earlier draft consumed the result outside the
        # try and unwound the listener thread after logging `committed`.
        self._register(lambda **kwargs: self._result()._replace(
            initial_reapply_ms="not-a-number",
        ))
        state = self._state_at_scene("lane_census_bad_field", LANE_SCENE_N_ID)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            actions, out = self._step(state)
        self.assertEqual(self._census(actions), [])
        self.assertIn(
            "world_census_lane_composer_refused_ValueError", state.events,
        )
        self.assertTrue(state.world_census_refused)
        # No console proof and no FIRED token for a census that never
        # shipped -- the token is emission evidence, not attempt evidence.
        self.assertNotIn("LANE_CENSUS_TEST_LINE_ONE", out)
        self.assertNotIn("LANE_HOOK_FIRED", err.getvalue())

    def test_a_wrong_shaped_return_is_refused_not_escaped(self):
        # The other measured escape: a truthy non-SceneCensusResult.
        self._register(lambda **kwargs: {"pc": b"x", "frame": b"y"})
        state = self._state_at_scene("lane_census_bad_shape", LANE_SCENE_N_ID)
        actions, _out = self._step(state)
        self.assertEqual(self._census(actions), [])
        self.assertIn(
            "world_census_lane_composer_refused_AttributeError",
            state.events,
        )
        self.assertTrue(state.world_census_refused)

    def test_a_non_ascii_console_line_cannot_kill_the_listener(self):
        # cp874 scar (rounds 86, 142): lane-authored console lines are the
        # one print in the block another lane composed.  console_safe must
        # have flattened them to ASCII before print is ever called.
        self._register(lambda **kwargs: self._result()._replace(
            console_lines=("LANE_LINE_THAI โท",),
        ))
        state = self._state_at_scene("lane_census_thai", LANE_SCENE_N_ID)
        actions, out = self._step(state)
        self.assertEqual(len(self._census(actions)), 2)
        self.assertIn("LANE_LINE_THAI", out)
        self.assertIn("\\u0e42", out)
        self.assertNotIn("โ", out)

    def test_scene_2_walks_the_bg0002_branch_even_with_a_composer(self):
        # Same no-regression property as the scene-1 test, for the OTHER
        # dedicated scene.  pf-adversary (round 73fhoc) measured the whole
        # suite staying green with the lane elif hoisted above the bg0002
        # elif; the guard is now a conjunct in the lane branch's own
        # condition, and this test is the one that dies if either the
        # conjunct or the ordering ever stops protecting scene 2.
        from pirateforce_foundation import world_population_bg0002

        calls = []
        scene2 = world_population_bg0002.SCENE2_N_ID
        self.addCleanup(
            lane_hooks._SCENE_CENSUS_COMPOSERS.pop, scene2, None,
        )
        self._register(
            lambda **kwargs: calls.append(1) or self._result(),
            scene_id=scene2,
        )
        state = self._state_at_scene("lane_census_scene2", scene2)
        actions, _out = self._step(state)
        census = self._census(actions)
        self.assertEqual(calls, [])
        self.assertTrue(census, "the bg0002 census must still send")
        for action in census:
            self.assertTrue(
                action[0].startswith("WORLD_CENSUS_BG0002_"), action[0],
            )

    def test_scene_1_walks_the_bg0001_branch_even_with_a_composer(self):
        # The no-regression-path property the lane's letter asked for by
        # name: a careless (or malicious) registration for the home scene
        # is never consulted -- the dedicated bg0001 branch keeps the
        # census it has always composed.
        calls = []
        self._register(
            lambda **kwargs: calls.append(1) or self._result(),
            scene_id=world_population.SCENE_ID,
        )
        state = self._state_at_scene(
            "lane_census_scene1", world_population.SCENE_ID,
        )
        actions, _out = self._step(state)
        census = self._census(actions)
        self.assertEqual(calls, [])
        self.assertTrue(census, "the bg0001 census must still send")
        for action in census:
            self.assertNotIn("LANE_SCENE", action[0])
            self.assertTrue(
                action[0].startswith("WORLD_CENSUS_INITIAL_")
                or action[0].startswith("WORLD_CENSUS_REAPPLY_"),
                action[0],
            )


if __name__ == "__main__":
    unittest.main()
