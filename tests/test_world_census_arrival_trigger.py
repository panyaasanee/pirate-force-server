"""PANYA-ORDER 20260901_0215 section 4, chief round ``4w5j25`` -- the world
census fires on ARRIVAL for every scene but home, on the REAL dispatcher.

    "the server must send NPCs itself before I have to start walking ... no
    round should ever again require me to walk just to make spawn call up
    NPCs."

WHAT CHANGED, IN ONE LINE.  runtime.py's WORLD-CENSUS-001 guard used to read
``last_target_pos is not None or scene_id == SCENE2_N_ID``; it now reads
``last_target_pos is not None or scene_id != world_population.SCENE_ID``.
Nothing else in the block moved: the arrival-anchor fallback underneath it was
already scene-agnostic (it asks ``scene_entry_registry`` for whatever scene
the session is in) and already fails closed for a scene with no pinned spawn.

WHY THIS FILE EXISTS BESIDE test_bg0002_census_wiring.py.  That file proves
the bg0002 carve-out CORE-REQUEST-026 added and still owns it; this file
proves the carve-out became the rule, over scenes that file never touches --
and, just as importantly, proves the ONE scene deliberately left out (home /
bg0001) is still movement-gated AND says, by driving it, exactly what would
break if a later round widened it without doing the other half of the work.

Seeding a stored row at a non-default scene uses the same direct
``store.save_position`` write into a throwaway per-test SQLite database as
tests/test_bg0002_census_wiring.py and tests/test_lane_scene_census_wiring.py,
for the same recorded reason: nothing in this tree seeds a non-default scene
on a real boot yet.  Never the canonical DB, never a committed fixture.
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
from pirateforce_foundation import world_population_handoff  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# bg0003 (Spice Paradise).  Chosen as the worked example because it is one of
# LANE-A's already-built world scenes: pinned spawn in the registry,
# ``login_entry_allowed``, a registered production-allowed census composer,
# and NO ChooseNPC responder -- i.e. the ordinary shape of the nine scenes
# this change opens, not a special case.
WORLD_SCENE_N_ID = 3
STEP_ANCHOR = (11.0, 22.0, 33.0)

# Same bytes tests/test_bg0002_census_wiring.py uses: an outer
# RuntimeProtocolReq with vital_count == 0 -- an ordinary runtime poll
# carrying no TargetPosVital at all, which is every frame a player who has
# not touched the keyboard yet produces.
EMPTY_RUNTIME_PC = bytes.fromhex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 00"
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _scenes_with_a_composer() -> tuple[int, ...]:
    """Every non-home scene a registered, production-allowed composer claims.

    Read from the live registry rather than listed here, so a scene a lane
    adds tomorrow is covered by this file the day it registers -- and a scene
    a lane REMOVES cannot leave a green test asserting nothing.
    """
    scenes = []
    for scene_id in sorted(world_scene_travel.CENSUS_SOURCES):
        if scene_id == world_population.SCENE_ID:
            continue
        composer = lane_hooks.scene_census_composer(scene_id)
        if composer is None:
            continue
        if not lane_hooks.module_production_allowed(composer.module):
            continue
        scenes.append(scene_id)
    return tuple(scenes)


class _ArrivalHarness(unittest.TestCase):
    """Login/create/start-game against a throwaway DB, stopping at the poll."""

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

    # ----- harness (same shape as the two sibling wiring files) --------

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

    def _choose_npc_pc(self, *actor_ids):
        body = b"".join(
            self.legacy.u16tag(0x12, self.legacy.CHOOSE_NPC)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.qwordtag(0x32, actor_id)
            for actor_id in actor_ids
        )
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, len(actor_ids))
            + body
        )

    def _dispatch(self, state, pc):
        """One frame, with the console captured (a census prints a lot)."""
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            actions = state.dispatch(self.legacy.parse_outer(pc))
        return actions, out.getvalue(), err.getvalue()

    def _poll(self, state):
        """The frame a player who has NOT moved sends."""
        return self._dispatch(state, EMPTY_RUNTIME_PC)

    def _step(self, state, xyz=STEP_ANCHOR):
        """The frame a player who HAS moved sends."""
        return self._dispatch(state, self._target_pos_pc(xyz))

    def _state_at_scene(self, token, scene_id):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        with contextlib.redirect_stdout(io.StringIO()):
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
            spawn = world_scene_travel.spawn_position(
                world_scene_travel.destination(scene_id)
            )
            # save_position needs an open session that already selected this
            # character (store.py's stale-session detection); start_game
            # re-selects the same row a moment later, a harmless no-op.
            self.store.select_character(
                state.foundation.session_id, character.selector,
            )
            self.store.save_position(
                state.foundation.session_id, character.id,
                Position(scene_id, 0, spawn[0], spawn[1], spawn[2], 0.0),
            )
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        self.assertEqual(
            state.foundation.selected.position.scene_id, scene_id,
            "the seeded row did not survive login -- the rest of this test "
            "would be measuring the wrong scene",
        )
        return state

    def _census(self, actions):
        return [
            action for action in actions
            if action[0].startswith("WORLD_CENSUS_")
        ]


class ArrivalTriggerFiresForEveryOpenWorldSceneTests(_ArrivalHarness):
    """(a) A scene WITH a pinned spawn composes its census on arrival."""

    def test_bg0003_ships_its_whole_roster_before_any_target_pos_vital(self):
        """The worked example, byte for byte.

        No TargetPosVital has ever been dispatched on this connection, so
        ``last_target_pos`` is still None -- the exact state that sent NOTHING
        for this scene before round ``4w5j25``.  The bytes are re-composed
        here through the seam's own public entry point at the scene's pinned
        spawn, so a call site that quietly used some other anchor (or some
        other roster) fails this, not merely a label check.
        """
        state = self._state_at_scene("arrival_bg0003", WORLD_SCENE_N_ID)
        self.assertIsNone(state.last_target_pos)
        actions, out, _err = self._poll(state)
        census = self._census(actions)

        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(WORLD_SCENE_N_ID)
        )
        expected = world_population_handoff.handoff_for_arrival(
            self.legacy, WORLD_SCENE_N_ID, spawn,
        )
        self.assertEqual(
            [action[0] for action in census],
            [
                f"WORLD_CENSUS_LANE_SCENE{WORLD_SCENE_N_ID}"
                f"_INITIAL_{expected.actor_count}",
                f"WORLD_CENSUS_LANE_SCENE{WORLD_SCENE_N_ID}"
                f"_REAPPLY_{expected.actor_count}",
            ],
        )
        for action in census:
            self.assertEqual(action[1], expected.pc)
            self.assertEqual(action[2], expected.frame)
        self.assertEqual(census[0][3], 0.0)
        self.assertGreater(census[1][3], 0.0)
        # Still no player report on this connection: the census was composed
        # from the scene's pin, not from anything the player did.
        self.assertIsNone(state.last_target_pos)
        self.assertIs(state.world_census_sent, True)
        self.assertIs(state.world_census_refused, False)
        self.assertIn(
            "world_census_lane_committed_actors_"
            f"{expected.actor_count}_pc_{len(expected.pc)}"
            f"_frame_{len(expected.frame)}",
            state.events,
        )
        # Console proof reached the operator BEFORE the frame was queued.
        self.assertIn("WORLD_CENSUS", out)

    def test_every_open_world_scene_with_a_composer_fires_on_arrival(self):
        """The count, not one example: every scene this change opens.

        Driven off the live registry (see ``_scenes_with_a_composer``), so
        the number this test covers is the number that actually exists.
        """
        scenes = _scenes_with_a_composer()
        # If this ever becomes empty the file above still passes vacuously.
        self.assertGreaterEqual(len(scenes), 9, scenes)
        composed = {}
        for scene_id in scenes:
            with self.subTest(scene=scene_id):
                state = self._state_at_scene(
                    f"arrival_scene_{scene_id}", scene_id,
                )
                actions, _out, _err = self._poll(state)
                census = self._census(actions)
                self.assertEqual(len(census), 2, census)
                self.assertIsNone(state.last_target_pos)
                self.assertIs(state.world_census_sent, True)
                self.assertIs(state.world_census_refused, False)
                composed[scene_id] = census[0][0]
        self.assertEqual(sorted(composed), list(scenes))

    def test_a_player_who_does_move_first_still_anchors_on_the_real_report(
        self,
    ):
        """The arrival anchor is a fallback, never an override.

        Same guarantee test_bg0002_census_wiring.py pins for scene 2; pinned
        here for a lane scene because the widened disjunct now reaches this
        branch by two routes instead of one.
        """
        state = self._state_at_scene("arrival_late_move", WORLD_SCENE_N_ID)
        actions, _out, _err = self._step(state)
        census = self._census(actions)
        self.assertEqual(len(census), 2, census)
        expected = world_population_handoff.handoff_for_arrival(
            self.legacy, WORLD_SCENE_N_ID,
            tuple(float(value) for value in STEP_ANCHOR),
        )
        self.assertEqual(census[0][1], expected.pc)
        self.assertEqual(census[0][2], expected.frame)

    def test_the_arrival_census_is_still_one_shot_per_session(self):
        state = self._state_at_scene("arrival_once", WORLD_SCENE_N_ID)
        first, _out, _err = self._poll(state)
        self.assertEqual(len(self._census(first)), 2)
        second, _out, _err = self._poll(state)
        self.assertEqual(self._census(second), [])
        third, _out, _err = self._step(state)
        self.assertEqual(self._census(third), [])


class ArrivalAnchorFailsClosedTests(_ArrivalHarness):
    """(b) A scene with NO pinned spawn refuses -- it does not crash."""

    def test_an_unresolvable_arrival_anchor_latches_a_refusal_and_no_frame(
        self,
    ):
        """Every scene in the registry today HAS a pinned spawn, so the
        failure is driven the same way tests/test_bg0002_census_wiring.py
        drives it for scene 2: by breaking the lookup itself, which is
        exactly what an unpinned/corrupt row does to this call.

        The refusal must latch: ``scene_entry_registry`` is loaded once at
        boot and never reloaded, so retrying it would re-log the identical
        failure on every poll for the whole session.  And it must be a
        refusal rather than an escape -- the enclosing frame path has no
        ``except`` (v141:7440), so a raise here ends the connection.
        """
        state = self._state_at_scene("arrival_unpinned", WORLD_SCENE_N_ID)
        original = world_scene_travel.spawn_position

        def explode(*args, **kwargs):
            raise ValueError("synthetic: spawn position unreadable")

        world_scene_travel.spawn_position = explode
        try:
            actions, _out, _err = self._poll(state)
        finally:
            world_scene_travel.spawn_position = original
        self.assertEqual(self._census(actions), [])
        self.assertIs(state.world_census_sent, False)
        self.assertIs(state.world_census_refused, True)
        # Scene-named, not bg0002-named: the string has to be able to name
        # scene 3 as honestly as scene 2 now that both can reach it.
        self.assertIn(
            "world_census_arrival_anchor_refused_scene_"
            f"{WORLD_SCENE_N_ID}_ValueError",
            state.events,
        )
        # Latched: a later poll, with the real function restored, neither
        # retries nor re-logs.
        actions, _out, _err = self._poll(state)
        self.assertEqual(self._census(actions), [])
        self.assertEqual(
            state.events.count(
                "world_census_arrival_anchor_refused_scene_"
                f"{WORLD_SCENE_N_ID}_ValueError"
            ),
            1,
        )

    def test_a_scene_no_composer_claims_still_sends_nothing_on_arrival(self):
        """Scene 278 is pinned and login-allowed but has no census source.

        Before this round it reached the not-home skip on the player's first
        step; now it reaches the same skip on the first poll.  Same outcome,
        zero frames -- what changed is only WHEN the branch answers, and this
        pins that the answer did not become a frame.
        """
        no_composer = 278
        self.assertIsNone(lane_hooks.scene_census_composer(no_composer))
        state = self._state_at_scene("arrival_no_composer", no_composer)
        actions, _out, _err = self._poll(state)
        self.assertEqual(self._census(actions), [])
        self.assertIs(state.world_census_sent, True)
        self.assertIn(
            f"world_census_skipped_scene_{no_composer}_not_home",
            state.events,
        )


class HomeSceneIsDeliberatelyNotWidenedTests(_ArrivalHarness):
    """(c) The one scene left on the movement gate, and the reason, driven.

    bg0001 is excluded because it is the only census arm that arms
    ``population_indices`` with no lane_hooks ChooseNPC responder in front of
    it, and v141:4395-4416 unpacks ``last_target_pos`` for any chosen
    identity found in that tuple with NO None check.  The second test below
    is that unpack, driven, so the exclusion cannot be deleted by a later
    round as "an oversight from the round that widened the others".
    """

    def test_home_still_sends_nothing_until_the_player_moves(self):
        state = self._state_at_scene("home_control", world_population.SCENE_ID)
        actions, _out, _err = self._poll(state)
        self.assertEqual(self._census(actions), [])
        self.assertIs(state.world_census_sent, False)
        self.assertIs(state.world_census_refused, False)
        self.assertIsNone(state.population_indices)

    def test_home_composes_the_same_census_it_always_did_on_the_first_step(
        self,
    ):
        state = self._state_at_scene("home_step", world_population.SCENE_ID)
        actions, _out, _err = self._step(state)
        census = self._census(actions)
        # The count in the label is the census's own SHIPPED count (108 of a
        # requested 115 today -- seven placements resolve to no identity and
        # are dropped, RE-128), so it is rebuilt here rather than read off
        # ``census_count_for_dispatch()``, which answers the REQUEST.
        count, source = world_population.census_count_for_dispatch()
        generation = world_population.build_world_population(
            self.legacy, tuple(float(v) for v in STEP_ANCHOR), count,
            scene_id=world_population.SCENE_ID, count_source=source,
        )
        self.assertEqual(
            [action[0] for action in census],
            [
                f"WORLD_CENSUS_INITIAL_{generation.actor_count}",
                f"WORLD_CENSUS_REAPPLY_{generation.actor_count}",
            ],
        )
        self.assertIs(state.world_census_sent, True)
        # The invariant the exclusion buys: home never arms population_indices
        # while last_target_pos is None.
        self.assertIsNotNone(state.population_indices)
        self.assertIsNotNone(state.last_target_pos)

    def test_the_frozen_choose_npc_loop_is_why_home_waits(self):
        """THE MEASUREMENT BEHIND THE EXCLUSION, not an argument for it.

        Same connection, same click, one field different: with the real
        ``last_target_pos`` the frozen branch answers the click; with it None
        -- the state a home arrival census would leave a player in until the
        first WASD press -- the same click raises ``TypeError`` out of
        ``dispatch``, which in production is the GAME listener thread dying
        for the whole session (v141:7440 has no except).  A dead connection
        is a worse answer to PANYA-ORDER 20260901_0215 than the walk it
        removes, so home keeps the movement gate until one of the two fixes
        named at the call site lands.
        """
        state = self._state_at_scene("home_click", world_population.SCENE_ID)
        self._step(state)
        self.assertTrue(state.population_indices)
        # Any member EXCEPT the frozen V112 monster index: that one index is
        # ``continue``d before the unpack (v141:4411), so clicking it would
        # measure the one placement in the census that cannot show this.
        placement_index = next(
            index for index in state.population_indices
            if index != self.legacy.V112_MONSTER_INDEX
        )
        actor_identity = placement_index + 0x2000 + 1
        # Control: the click is answered while the player HAS reported.
        answered, _out, _err = self._dispatch(
            state, self._choose_npc_pc(actor_identity),
        )
        self.assertTrue(answered, "the control click sent nothing")
        # Counterfactual: the identical click, in the state an unguarded
        # widening to home would have produced.
        state.last_target_pos = None
        with self.assertRaises(TypeError):
            self._dispatch(state, self._choose_npc_pc(actor_identity))


if __name__ == "__main__":  # pragma: no cover - parity with sibling files
    unittest.main()
