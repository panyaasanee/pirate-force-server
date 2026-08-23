"""GROUND-LOOT-DISPATCH (HYP-PF-032) -- the bit-0x08 pair on the dispatcher.

``tests/test_ground_loot_hypothesis.py`` proves the loader and the composer
offline.  This file drives the REAL ``make_state_class`` dispatch path behind
the opt-in ``scenarios/ground_loot_hypothesis_bit08_render.json`` and proves
the wire layer end to end, headless -- no server process, no socket, no
client:

  * at the house scene-load moment -- the first exact TargetPos after the
    runtime ack -- the dispatcher APPENDS exactly two actions, byte-identical
    to ``make_ground_loot_frames``'s own composition, AFTER the inherited
    actions of the trigger frame: NEAR at delay 0.0, then FAR at delay 0.10,
    each a single-element count=1 frame (the V43-proven-safe shape; a real
    client raised ErrorData=28317 on a combined multi-record derived-mask
    collection).  The frames ride alongside; the frozen population and the
    position checkpoint stay untouched;
  * the pair is one-shot: a second TargetPos adds neither action;
  * the pair writes no database row and takes no socket action;
  * the refusal ladder fails closed with no bytes: no selected character,
    not yet runtime-ack/teleport, malformed TargetPos (durable_target None),
    and the compose-drift path latches with its named refusal event;
  * containment: with the scenario absent nothing composes, the latch stays
    False and no lane event appears; the scenario modes stay mutually
    exclusive at construction; the other lane counters never move.

NOT proven here: whether a real client renders anything for a derived-bit-
0x08 list.  **No client has ever been shown a bit-0x08 frame** -- that is
GT-045, attended, not run.
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ground_loot_hypothesis as glh  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "ground_loot_hypothesis_bit08_render.json"
SCENE_LOAD_SCENARIO_PATH = (
    ROOT / "scenarios" / "scene2_fighting_fish_soldier.json"
)

PAIR_EVENT = "hyp_pf_032_ground_loot_bit08_pair_committed"
COMPOSE_REFUSED_EVENT = "ground_loot_compose_refused_no_reply"
NEAR_LABEL = "GROUND_LOOT_BIT08_RENDER_NEAR_ONCE"
FAR_LABEL = "GROUND_LOOT_BIT08_RENDER_FAR_ONCE"
LANE_LABELS = (NEAR_LABEL, FAR_LABEL)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class GroundLootDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
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
        self.scenario = glh.load_ground_loot_hypothesis_scenario(SCENARIO_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ----------------------------------------------------------

    def _state_type(self, *, pair=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            ground_loot_hypothesis_scenario=(
                self.scenario if pair else None
            ),
        )

    def _state(self, login, *, pair=True, ready=True, select=True):
        state = self._state_type(pair=pair)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(login)
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        if select:
            characters = self.store.list_characters(state.foundation.account_id)
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(characters[-1].selector)
            ))
            self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _target_pos_pc(self, x, y, z, heading=0.0, moving=1, derived=0):
        """The exact singleton shape parse_v141_refresh_target_pos accepts.

        ``derived`` held non-zero makes the same nested vital id parse to a
        None durable target -- the malformed-TargetPos rung below.
        """
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.f32tag(x) + self.legacy.f32tag(y)
            + self.legacy.f32tag(z) + self.legacy.f32tag(heading)
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, derived)
        )

    def _trigger(self, state, *, derived=0):
        position = state.foundation.selected.position
        return self.legacy.parse_outer(self._target_pos_pc(
            position.x, position.y, position.z, derived=derived,
        ))

    def _table_counts(self):
        db = sqlite3.connect(str(self.db_path))
        try:
            names = [row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {
                name: db.execute(
                    'SELECT COUNT(*) FROM "%s"' % name).fetchone()[0]
                for name in names
            }
        finally:
            db.close()

    def _lane_events(self, state):
        return [
            event for event in state.events
            if "ground_loot" in event
        ]

    def _ground_actions(self, actions):
        return [action for action in actions if action[0] in LANE_LABELS]

    # ----- the pair fires once, byte-exact, appended after ------------------

    def test_the_dispatcher_forwards_the_composers_bytes_exactly(self):
        state = self._state("gld01")
        expected = glh.make_ground_loot_frames(self.legacy, self.scenario)
        actions = state.dispatch(self._trigger(state))
        ground = self._ground_actions(actions)
        self.assertEqual(len(ground), 2)
        self.assertEqual(
            [(label, bytes(pc), bytes(frame), delay)
             for label, pc, frame, delay in ground],
            [
                (NEAR_LABEL, expected[0][0], expected[0][1], 0.0),
                (FAR_LABEL, expected[1][0], expected[1][1], 0.10),
            ],
        )
        for (_, pc, frame, _), (pc_sha, frame_sha) in zip(ground, (
            (glh.GROUND_LOOT_NEAR_PC_SHA256,
             glh.GROUND_LOOT_NEAR_FRAME_SHA256),
            (glh.GROUND_LOOT_FAR_PC_SHA256,
             glh.GROUND_LOOT_FAR_FRAME_SHA256),
        )):
            self.assertEqual(len(pc), glh.GROUND_LOOT_PC_SIZE)
            self.assertEqual(len(frame), glh.GROUND_LOOT_FRAME_SIZE)
            self.assertEqual(
                hashlib.sha256(bytes(pc)).hexdigest().upper(), pc_sha,
            )
            self.assertEqual(
                hashlib.sha256(bytes(frame)).hexdigest().upper(), frame_sha,
            )
            self.assertEqual(
                bytes(frame), self.legacy.frame_pc(bytes(pc)),
            )
        self.assertEqual(state.events.count(PAIR_EVENT), 1)
        self.assertIs(state.ground_loot_pair_sent, True)

    def test_the_pair_is_appended_after_the_inherited_actions(self):
        gated = self._state("gld02")
        ungated = self._state("gld02_control", pair=False)
        gated_actions = gated.dispatch(self._trigger(gated))
        ungated_actions = ungated.dispatch(self._trigger(ungated))
        # The two ground-loot actions are the LAST actions of the trigger
        # frame -- near then far -- and everything before them is the
        # inherited dispatch byte-for-byte: the frames ride alongside, they
        # displace nothing.
        self.assertEqual(
            [action[0] for action in gated_actions[-2:]],
            [NEAR_LABEL, FAR_LABEL],
        )
        self.assertEqual(
            [(label, bytes(pc), bytes(frame), delay)
             for label, pc, frame, delay in gated_actions[:-2]],
            [(label, bytes(pc), bytes(frame), delay)
             for label, pc, frame, delay in ungated_actions],
        )

    def test_the_pair_is_one_shot(self):
        state = self._state("gld03")
        first = state.dispatch(self._trigger(state))
        self.assertEqual(len(self._ground_actions(first)), 2)
        again = state.dispatch(self._trigger(state))
        self.assertEqual(self._ground_actions(again), [])
        self.assertEqual(state.events.count(PAIR_EVENT), 1)
        self.assertIs(state.ground_loot_pair_sent, True)

    def test_the_pair_writes_no_database_row(self):
        state = self._state("gld04")
        before = self._table_counts()
        state.dispatch(self._trigger(state))
        self.assertEqual(self._table_counts(), before)

    def test_the_checkpoint_of_the_trigger_frame_is_untouched(self):
        """The frames ride alongside: the frozen position checkpoint of the
        exact TargetPos still lands on the character row, unchanged."""
        gated = self._state("gld05")
        ungated = self._state("gld05_control", pair=False)
        gated.dispatch(self._trigger(gated))
        ungated.dispatch(self._trigger(ungated))
        gated_row = self.store.get_character(gated.foundation.selected.id)
        ungated_row = self.store.get_character(ungated.foundation.selected.id)
        self.assertEqual(
            (gated_row.position.x, gated_row.position.y,
             gated_row.position.z),
            (ungated_row.position.x, ungated_row.position.y,
             ungated_row.position.z),
        )

    # ----- the refusal ladder -----------------------------------------------

    def test_no_selected_character_fails_closed(self):
        state = self._state("gld06", select=False)
        origin = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        actions = state.dispatch(self.legacy.parse_outer(self._target_pos_pc(
            origin.x, origin.y, origin.z,
        )))
        self.assertEqual(self._ground_actions(actions), [])
        self.assertIs(state.ground_loot_pair_sent, False)
        self.assertEqual(self._lane_events(state), [])

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("gld07", ready=False)
        actions = state.dispatch(self._trigger(state))
        self.assertEqual(self._ground_actions(actions), [])
        self.assertIs(state.ground_loot_pair_sent, False)
        self.assertEqual(self._lane_events(state), [])
        # ... and the same session fires once the ack has been sent: the
        # refusal is sequencing, not poison.
        state.runtime_ack_sent = True
        actions = state.dispatch(self._trigger(state))
        self.assertEqual(len(self._ground_actions(actions)), 2)

    def test_a_malformed_target_pos_fails_closed(self):
        state = self._state("gld08")
        # Same nested vital id, non-zero trailing derived mask: the frozen
        # parser returns None and the branch must not consume the latch.
        actions = state.dispatch(self._trigger(state, derived=1))
        self.assertEqual(self._ground_actions(actions), [])
        self.assertIs(state.ground_loot_pair_sent, False)
        self.assertEqual(self._lane_events(state), [])
        # A later exact TargetPos still fires.
        actions = state.dispatch(self._trigger(state))
        self.assertEqual(len(self._ground_actions(actions)), 2)

    def test_a_drifted_composition_latches_by_name_and_emits_nothing(self):
        state = self._state("gld09")
        pinned = glh.GROUND_LOOT_NEAR_PC_SHA256
        glh.GROUND_LOOT_NEAR_PC_SHA256 = "00" * 32
        try:
            actions = state.dispatch(self._trigger(state))
        finally:
            glh.GROUND_LOOT_NEAR_PC_SHA256 = pinned
        self.assertEqual(self._ground_actions(actions), [])
        self.assertEqual(state.events.count(COMPOSE_REFUSED_EVENT), 1)
        self.assertNotIn(PAIR_EVENT, state.events)
        self.assertIs(state.ground_loot_pair_sent, True)
        # The refusal latched: with the pin restored the session still emits
        # nothing, so drift can never retry itself onto the wire.
        again = state.dispatch(self._trigger(state))
        self.assertEqual(self._ground_actions(again), [])
        self.assertEqual(state.events.count(COMPOSE_REFUSED_EVENT), 1)

    # ----- containment ------------------------------------------------------

    def test_with_the_scenario_absent_nothing_composes(self):
        state = self._state("gld10", pair=False)
        expected = glh.make_ground_loot_frames(self.legacy, self.scenario)
        actions = state.dispatch(self._trigger(state))
        labels = [row[0] for row in actions]
        self.assertNotIn(NEAR_LABEL, labels)
        self.assertNotIn(FAR_LABEL, labels)
        self.assertFalse(
            {bytes(row[1]) for row in actions}
            & {pc for pc, _ in expected},
        )
        self.assertIs(state.ground_loot_pair_sent, False)
        self.assertEqual(self._lane_events(state), [])

    def test_the_scenario_modes_stay_mutually_exclusive(self):
        from pirateforce_foundation.scene_load import load_scene_load_scenario
        other = load_scene_load_scenario(SCENE_LOAD_SCENARIO_PATH)
        with self.assertRaises(ValueError) as caught:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                scene_load_scenario=other,
                ground_loot_hypothesis_scenario=self.scenario,
            )
        self.assertIn("mutually exclusive", str(caught.exception))

    def test_a_lookalike_profile_cannot_reach_the_dispatcher(self):
        lookalike = glh.GroundLootScenario(
            self.scenario.scenario_id, self.scenario.hypothesis_id,
            self.scenario.elements,
        )
        with self.assertRaises(ValueError) as caught:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                ground_loot_hypothesis_scenario=lookalike,
            )
        self.assertIn("not_allowlisted", str(caught.exception))

    def test_the_other_lane_counters_never_move(self):
        state = self._state("gld11")
        state.dispatch(self._trigger(state))
        self.assertEqual(state.chat_input_echo_count, 0)
        self.assertEqual(state.channel_message_sweep_count, 0)
        self.assertEqual(state.stats_progression_sweep_count, 0)
        self.assertEqual(state.runtimeres_death_sweep_count, 0)
        self.assertEqual(state.damage_model_sweep_count, 0)
        self.assertEqual(state.npc_hostile_sweep_count, 0)
        self.assertEqual(state.logout_chat_push_count, 0)
        self.assertEqual(state.move_authority_accept_count, 0)

    def test_no_socket_action_rides_any_action(self):
        state = self._state("gld12")
        actions = state.dispatch(self._trigger(state))
        self.assertTrue(all(len(action) == 4 for action in actions))


if __name__ == "__main__":
    unittest.main()
