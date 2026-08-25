"""WORLD-CENSUS-001 -- the census on the REAL dispatcher, default boot.

``tests/test_world_population.py`` proves the builder offline: memberships,
nesting, byte counts, refusals.  It cannot say whether anything reaches a
client, because until this wiring landed nothing imported the module at all.
This file drives ``make_state_class`` headless -- no server process, no socket,
no client -- and proves the part that was missing:

  * a DEFAULT boot, constructed with no flag and no scenario of any kind, now
    queues the whole bg0001 census where it used to queue three actors, on the
    same trigger (first TargetPos after the runtime ack), with the same
    initial-plus-reapply schedule (0.0s then 3.0s);
  * the count is IN THE LABEL, because v141 prints one console line per queued
    action at send time and four staircase boots have to be distinguishable
    from that line alone;
  * at rung 3 the wire is byte-identical to the frozen
    ``make_v112_monster_shop_population_state()`` collection, so the control
    rung is a control on the dispatch path and not only in the builder;
  * CONTAINMENT: a boot that opted into any lane keeps the frozen three-actor
    population it was measured against.  This is the whole reason the wiring
    is keyed on "no lane is active" rather than on nothing at all;
  * the census is one-shot per session, and a compose refusal fails CLOSED to
    the shipped three-actor branch on the same frame and latches;
  * the anchor is THIS frame's TargetPos, not the previous one.

NOT proven here, and not provable without a person at a screen: whether the
client accepts a 115-actor RuntimeRes collection at all, and whether any of
those actors becomes a model on screen.  The highest count with a recorded
result anywhere in this project is 20.  That is GT-078, attended, not run.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation.ground_loot_hypothesis import (  # noqa: E402
    load_ground_loot_hypothesis_scenario,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
GROUND_LOOT_SCENARIO = (
    ROOT / "scenarios" / "ground_loot_hypothesis_bit08_render.json"
)

INITIAL_PREFIX = "WORLD_CENSUS_INITIAL_"
REAPPLY_PREFIX = "WORLD_CENSUS_REAPPLY_"
FROZEN_LABELS = (
    "V134_P0_P30_P91_ISOLATED_INITIAL_READY",
    "V134_P0_P30_P91_ISOLATED_REAPPLY_READY",
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class WorldCensusWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
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

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ----------------------------------------------------------

    def _state(self, token, *, ready=True, **kwargs):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector, **kwargs,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.runtime_ack_sent = ready
        state.welcome_message_sent = ready
        state.current_scene_music_sent = ready
        return state

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

    def _step(self, state, xyz=(10.0, 20.0, 30.0), **kwargs):
        return state.dispatch(
            self.legacy.parse_outer(self._target_pos_pc(xyz, **kwargs))
        )

    def _census(self, actions):
        return [
            action for action in actions
            if action[0].startswith("WORLD_CENSUS_")
        ]

    def _choose_npc_pc(self, identity):
        vitals = [
            self.legacy.u16tag(0x12, self.legacy.TARGET_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.qwordtag(0x32, identity)
            + self.legacy.u8tag(0x08, 2),
            self.legacy.u16tag(0x12, self.legacy.CHOOSE_NPC)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.qwordtag(0x32, identity),
        ]
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, len(vitals))
            + b"".join(vitals)
        )

    # ----- the default boot is the census -----------------------------------

    def test_the_default_boot_queues_the_whole_census_twice(self):
        state = self._state("census_default")
        actions = self._step(state)
        census = self._census(actions)
        self.assertEqual(
            [action[0] for action in census],
            [f"{INITIAL_PREFIX}115", f"{REAPPLY_PREFIX}115"],
        )
        self.assertEqual([action[3] for action in census], [0.0, 3.0])
        # The same collection twice, exactly as the frozen branch does it: the
        # V138 nearest-20 runtime pass that was accepted was an initial plus a
        # model-ready reapply, not a single frame.
        self.assertEqual(census[0][1], census[1][1])
        self.assertEqual(census[0][2], census[1][2])
        self.assertEqual(
            census[1][3], world_population.INITIAL_REAPPLY_MS / 1000.0,
        )
        self.assertEqual(state.world_census_actor_count, 115)
        self.assertEqual(len(state.world_census_indices), 115)
        self.assertIs(state.world_census_refused, False)

    def test_the_frozen_three_actor_labels_are_gone_from_the_default_boot(self):
        """The point of the build order, stated as a negative."""
        state = self._state("census_replaces")
        labels = [action[0] for action in self._step(state)]
        for frozen in FROZEN_LABELS:
            self.assertNotIn(frozen, labels)

    def test_the_bookkeeping_the_frozen_branch_commits_is_committed(self):
        """Downstream frozen paths read this state; it has to match the wire."""
        state = self._state("census_books")
        self.assertIs(state.npc_spawn_sent, False)
        actions = self._step(state)
        generation = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0),
        )
        self.assertIs(state.npc_spawn_sent, True)
        self.assertIs(state.npc_idle_action_sent, False)
        self.assertEqual(state.population_indices, generation.indices)
        self.assertEqual(state.population_refresh_anchor, (10.0, 20.0, 30.0))
        self.assertEqual(self._census(actions)[0][1], generation.pc)
        self.assertEqual(self._census(actions)[0][2], generation.frame)

    def test_the_label_carries_the_count_that_actually_went_out(self):
        """v141 prints '[G>] <label> (N bytes)' per queued action at SEND time
        (v141:7762).  The rung has to be readable from that one line, or four
        attended boots of the GT-078 staircase are indistinguishable in the
        console the tester is actually watching.
        """
        for rung in world_population.STAIRCASE_RUNGS:
            with self.subTest(rung=rung):
                state = self._state(
                    f"census_rung{rung}", world_census_actor_count=rung,
                )
                census = self._census(self._step(state))
                self.assertEqual(
                    [action[0] for action in census],
                    [f"{INITIAL_PREFIX}{rung}", f"{REAPPLY_PREFIX}{rung}"],
                )
                self.assertEqual(state.world_census_actor_count, rung)
                self.assertEqual(len(state.population_indices), rung)

    def test_rung_three_is_byte_identical_to_the_frozen_collection(self):
        """The control rung, checked against the frozen encoder itself.

        ``make_v112_monster_shop_population_state`` is what the shipped branch
        sends today.  If rung 3 ever stops matching it byte for byte, the
        staircase has no control and every rung above it is uninterpretable.
        """
        state = self._state("census_control", world_census_actor_count=3)
        census = self._census(self._step(state))
        frozen_pc, frozen_frame, frozen_rows = (
            self.legacy.make_v112_monster_shop_population_state()
        )
        self.assertEqual(census[0][1], frozen_pc)
        self.assertEqual(census[0][2], frozen_frame)
        self.assertEqual(len(frozen_pc), 504)
        self.assertEqual(len(frozen_frame), 517)
        self.assertEqual(
            state.population_indices, tuple(row[0] for row in frozen_rows),
        )

    def test_the_census_is_one_shot_per_session(self):
        state = self._state("census_once")
        self.assertEqual(len(self._census(self._step(state))), 2)
        self.assertEqual(self._census(self._step(state)), [])
        self.assertEqual(
            [event for event in state.events
             if event.startswith("world_census_committed_")],
            [f"world_census_committed_actors_115_pc_{17928}_frame_{17942}"],
        )

    # ----- the anchor -------------------------------------------------------

    def test_the_census_is_anchored_on_this_frame_not_the_previous_one(self):
        """v141 sets last_target_pos from the CURRENT frame (v141:4259) before
        its population branch reads it (v141:4292).  This wiring runs BEFORE
        the inherited dispatch, so reading last_target_pos alone would anchor
        the census one step behind the player and silently order the census
        around a position they have already left.
        """
        far = (30000.0, 25000.0, 1000.0)
        state = self._state("census_anchor")
        census = self._census(self._step(state, xyz=far))
        expected = world_population.build_world_population(self.legacy, far)
        self.assertEqual(census[0][1], expected.pc)
        self.assertEqual(state.population_refresh_anchor, far)
        # Not a tautology: a different anchor really does order the census
        # differently, so this test can fail.
        near = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0),
        )
        self.assertNotEqual(expected.indices, near.indices)

    # ----- containment ------------------------------------------------------

    def test_an_opt_in_lane_keeps_the_population_it_was_measured_against(self):
        """Several lanes pin actor identities inside the band the census
        occupies (115 identities spread over a 149-wide index space, 34 gaps).
        Widening the population underneath a lane that is measuring something
        else would change that lane's control without anyone noticing.
        """
        state = self._state(
            "census_contained",
            ground_loot_hypothesis_scenario=(
                load_ground_loot_hypothesis_scenario(GROUND_LOOT_SCENARIO)
            ),
        )
        labels = [action[0] for action in self._step(
            state, xyz=(
                state.foundation.selected.position.x,
                state.foundation.selected.position.y,
                state.foundation.selected.position.z,
            ),
        )]
        self.assertEqual(self._census([(label,) for label in labels]), [])
        for frozen in FROZEN_LABELS:
            self.assertIn(frozen, labels)
        self.assertIsNone(state.world_census_actor_count)

    # ----- refusals ---------------------------------------------------------

    def test_an_impossible_rung_is_refused_at_construction(self):
        for bad in (0, -1, 116, 3.0, "3", True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        world_census_actor_count=bad,
                    )

    def test_a_compose_refusal_falls_back_to_the_shipped_branch_and_latches(self):
        """Fail closed means the player still gets what they got yesterday.

        A raise inside the builder must not kill the connection and must not
        leave the session with no population at all: npc_spawn_sent is left
        alone so the frozen three-actor branch runs on this very frame, and the
        refusal latches so it cannot retry itself onto the wire on every step.
        """
        original = world_population.build_world_population

        def explode(*args, **kwargs):
            raise ValueError("frozen placement source count drift")

        state = self._state("census_refused")
        world_population.build_world_population = explode
        try:
            labels = [action[0] for action in self._step(state)]
        finally:
            world_population.build_world_population = original
        self.assertEqual(self._census([(label,) for label in labels]), [])
        for frozen in FROZEN_LABELS:
            self.assertIn(frozen, labels)
        self.assertIs(state.world_census_refused, True)
        self.assertIsNone(state.world_census_actor_count)
        self.assertIn(
            "world_census_compose_refused_ValueError", state.events,
        )
        # Latched: a later step neither retries nor emits a second refusal.
        self.assertEqual(self._census(self._step(state)), [])
        self.assertEqual(
            state.events.count("world_census_compose_refused_ValueError"), 1,
        )

    # ----- what the wider membership changes downstream ---------------------

    def test_the_v138_destination_population_still_replaces_the_census(self):
        """A regression that was proposed and does not exist.

        The V139 P86 interaction gates compare population_indices against
        V138_MARKER1_NEAREST_INDICES (v141:4267, v141:4495), so a wider boot
        population looks like it must break them.  It does not: the V138
        marker branch REASSIGNS population_indices when it fires (v141:3742),
        and it does not read the boot population at all.  Pinned here because
        the argument is easy to make and wrong.
        """
        state = self._state("census_v138")
        self._step(state)
        self.assertEqual(len(state.population_indices), 115)
        state.v137_marker1_transport_sent = True
        state.dispatch(self.legacy.parse_outer(
            self.legacy.V138_MARKER1_READY_PC
        ))
        self.assertIs(state.v138_marker1_population_sent, True)
        self.assertEqual(
            state.population_indices,
            self.legacy.V138_MARKER1_NEAREST_INDICES,
        )

    def test_the_wider_membership_widens_who_answers_a_click(self):
        """Declared, not hidden: this is a real behavioural change.

        The frozen ChooseNPC path answers only for actors in
        population_indices (v141:4409).  With three members, 112 placements
        were silently ignored; with the census they are members, so clicking
        one now composes the V98 face/conversation response -- and that
        response rebuilds the WHOLE population snapshot, so a click now costs
        a census-sized frame instead of a 504-byte one.  Nothing here says a
        client does anything useful with either; that is attended work.
        """
        state = self._state("census_click")
        self._step(state)
        outsider = 0x2000 + 1 + 1  # placement 1, not one of P0/P30/P91
        self.assertNotIn(1, world_population.SHIPPED_ISOLATED_INDICES)
        actions = state.dispatch(
            self.legacy.parse_outer(self._choose_npc_pc(outsider))
        )
        self.assertEqual(
            [action[0] for action in actions],
            [
                "V98_NPC_FACE_PLAYER_POSITION_HEADING_P1",
                "V98_NPC_CONVERSATION_DEFAULT_P1",
            ],
        )
        self.assertGreater(len(actions[0][1]), 504)


if __name__ == "__main__":
    unittest.main()
