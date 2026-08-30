"""scene_admission_gate.py -- COO-DECISION 2026-08-29T09:41+07:00 item 2.

Three layers.

``SceneAdmissionGateUnitTests`` proves the gate itself with no runtime state
at all: COO-DECISION 0941's third acceptance criterion is that "this scene
has no population" must be provable by calling the gate, not by grepping
which modules a call site imports.

``FrozenLabelDriftTests`` pins the three independent copies of the frozen
branch's two label strings against each other (pf-adversary D7): the gate
matches by literal, so a drift in any copy would make it withhold nothing,
silently.

``FrozenLegacyPopulationSceneGateWiringTests`` drives the real dispatcher
headless and proves the WITHHOLD, not just the strip: the frames are gone
AND the four fields the branch latches are back to their pre-dispatch
values, so nothing downstream believes in actors the client never got
(pf-adversary D2) and the branch is still armed for a later home-scene
frame (pf-adversary D9).

WHAT NO TEST HERE CAN PROVE, and why: the gate's verdict is
``selected.position.scene_id``, a row the server wrote.
``world_travel_gate.py`` states that this project cannot distinguish that
row from a client that never applied the teleport, so "the client is in
scene N" is not observable here. Every test below asserts about the ROW.
"""
from __future__ import annotations

import dataclasses
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import scene_admission_gate  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    load_chat_input_hypothesis_scenario,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
RUNTIME_PATH = ROOT / "src" / "pirateforce_foundation" / "runtime.py"
CHAT_SCENARIO_PATH = ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
FROZEN_LABELS = scene_admission_gate.FROZEN_LEGACY_POPULATION_LABELS

# A scene id that is NOT the home scene. Deliberately an id this project
# treats as addressed-but-not-live: the gate's question is only "is this the
# home scene", so an id with no population of its own is the cleanest probe
# and cannot accidentally pass by way of some other scene's census.
# (pf-adversary D7 caught an earlier comment here calling 278 "live", which
# runtime.py's own bg0002 branch contradicts.)
NON_HOME_SCENE_ID = 278


class SceneAdmissionGateUnitTests(unittest.TestCase):
    """No server, no legacy binary, no dispatch -- the gate proves itself."""

    def test_admits_the_home_scene(self):
        self.assertTrue(
            scene_admission_gate.admits_frozen_legacy_population(
                world_population.SCENE_ID,
            )
        )

    def test_refuses_a_non_home_scene(self):
        self.assertFalse(
            scene_admission_gate.admits_frozen_legacy_population(
                NON_HOME_SCENE_ID,
            )
        )

    def test_refuses_no_scene_selected_yet(self):
        self.assertFalse(
            scene_admission_gate.admits_frozen_legacy_population(None)
        )

    def test_refuses_a_non_int_scene_id(self):
        self.assertFalse(
            scene_admission_gate.admits_frozen_legacy_population("1")
        )
        self.assertFalse(
            scene_admission_gate.admits_frozen_legacy_population(1.0)
        )

    def test_contains_is_exact_not_a_prefix_match(self):
        """The frozen branch's neighbours share the V134_P0 prefix."""
        self.assertFalse(
            scene_admission_gate.contains_frozen_legacy_population(
                [("V134_P0_Q3020_NPC_CONVERSATION_ONCE", b"", b"", 0.0)]
            )
        )
        self.assertTrue(
            scene_admission_gate.contains_frozen_legacy_population(
                [(FROZEN_LABELS[0], b"", b"", 0.0)]
            )
        )

    def test_without_keeps_the_prefix_sharing_neighbour(self):
        keep = ("V134_P0_Q3020_NPC_CONVERSATION_ONCE", b"pc", b"frame", 0.0)
        actions = [(FROZEN_LABELS[0], b"a", b"b", 0.0), keep,
                   (FROZEN_LABELS[1], b"c", b"d", 3.0)]
        self.assertEqual(
            scene_admission_gate.without_frozen_legacy_population(actions),
            [keep],
        )

    def test_without_does_not_mutate_its_input(self):
        actions = [(FROZEN_LABELS[0], b"pc", b"frame", 0.0)]
        original = list(actions)
        scene_admission_gate.without_frozen_legacy_population(actions)
        self.assertEqual(actions, original)


class FrozenLabelDriftTests(unittest.TestCase):
    """Three independent copies of two strings; pin them to each other.

    pf-adversary D7: the gate matches these labels as literals, and there is
    no shared symbol between the frozen builder (v141), runtime.py's own
    rebuild of it, and this module. If one drifts, the gate silently stops
    withholding. Nothing else in the tree notices, so this does.
    """

    def test_v141_still_spells_the_labels_the_gate_matches(self):
        text = LEGACY_PATH.read_text(encoding="utf-8", errors="strict")
        for label in FROZEN_LABELS:
            self.assertIn(
                f"'{label}'", text,
                f"v141 no longer emits {label}; the gate would withhold "
                f"nothing and say nothing",
            )

    def test_the_runtime_fallback_rebuild_uses_the_same_two_labels(self):
        text = RUNTIME_PATH.read_text(encoding="utf-8", errors="strict")
        for label in FROZEN_LABELS:
            self.assertIn(
                f'"{label}"', text,
                f"runtime.py's frozen fallback no longer emits {label}",
            )

    def test_no_fourth_spelling_of_the_isolated_labels_exists(self):
        pattern = re.compile(r"V134_P0_P30_P91_ISOLATED_[A-Z_]+")
        found = set()
        for path in (LEGACY_PATH, RUNTIME_PATH):
            found |= set(
                pattern.findall(path.read_text(encoding="utf-8"))
            )
        self.assertEqual(
            found, set(FROZEN_LABELS),
            "a V134_P0_P30_P91_ISOLATED_* label exists that the gate does "
            "not know about",
        )


class FrozenLegacyPopulationSceneGateWiringTests(unittest.TestCase):
    """The real dispatcher, headless -- no socket, no client."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_chat_input_hypothesis_scenario(CHAT_SCENARIO_PATH)

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, token):
        # chat_input_hypothesis_scenario is deliberately NOT
        # population_scenario or scene_load_scenario -- the two lanes
        # runtime.py disarms the frozen branch for at construction. This
        # boot leaves it armed for the whole session, exactly like every
        # other opt-in lane the containment rule names.
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            chat_input_hypothesis_scenario=self.scenario,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.runtime_ack_sent = True
        return state

    def _move_row_to(self, state, scene_id):
        selected = state.foundation.selected
        state.foundation.selected = dataclasses.replace(
            selected, position=dataclasses.replace(
                selected.position, scene_id=scene_id,
            ),
        )

    def _target_pos_pc(self, xyz=(10.0, 20.0, 30.0), heading=0.0):
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + b"".join(legacy.f32tag(value) for value in (*xyz, heading))
            + legacy.u8tag(0x0B, 0)
            + legacy.u8tag(0x0B, 0)
        )

    def _step(self, state):
        return state.dispatch(self.legacy.parse_outer(self._target_pos_pc()))

    def _labels(self, actions):
        return [action[0] for action in actions]

    def test_opt_in_lane_on_the_home_scene_keeps_its_measured_control(self):
        """CONTROL: unchanged from before this round's patch.

        A session that opted into a lane the disarm block does not cover,
        and whose row never leaves scene 1, still gets the frozen
        three-actor population it was always measured against -- the
        containment rule test_world_census_wiring.py documents. If this
        regresses, the gate is refusing scenes it must admit.
        """
        state = self._state("scene_gate_home")
        self.assertEqual(
            state.foundation.selected.position.scene_id,
            world_population.SCENE_ID,
        )
        labels = self._labels(self._step(state))
        for frozen in FROZEN_LABELS:
            self.assertIn(frozen, labels)
        self.assertIs(state.npc_spawn_sent, True)
        self.assertEqual(state.population_indices, (0, 30, 91))

    def test_a_withheld_frame_ships_nothing_and_latches_nothing(self):
        """THE FIX, both halves (pf-adversary D2).

        The frames are gone AND every field the branch latched is back to
        its pre-dispatch value -- so population_indices does not attest to
        actors the client was never sent, and the ChooseNPC answerer that
        reads it as evidence of rendering finds nothing to answer for.
        """
        state = self._state("scene_gate_away")
        self._move_row_to(state, NON_HOME_SCENE_ID)
        before = (
            state.npc_spawn_sent, state.npc_idle_action_sent,
            state.population_indices, state.population_refresh_anchor,
        )
        labels = self._labels(self._step(state))
        for frozen in FROZEN_LABELS:
            self.assertNotIn(frozen, labels)
        self.assertEqual(
            (state.npc_spawn_sent, state.npc_idle_action_sent,
             state.population_indices, state.population_refresh_anchor),
            before,
            "the branch latched state for a population it did not ship",
        )
        self.assertIn(
            f"frozen_legacy_population_withheld_scene_{NON_HOME_SCENE_ID}",
            state.events,
        )

    def test_withholding_away_does_not_empty_the_home_scene_later(self):
        """pf-adversary D9: the branch is one-shot, so a strip would be fatal.

        v141:4308 latches npc_spawn_sent permanently. If a withheld frame
        left that latch set, a session withheld once while its row was away
        could never populate its home scene for the rest of its life. This
        drives exactly that sequence: away (withheld), then home.
        """
        state = self._state("scene_gate_round_trip")
        self._move_row_to(state, NON_HOME_SCENE_ID)
        away = self._labels(self._step(state))
        for frozen in FROZEN_LABELS:
            self.assertNotIn(frozen, away)

        self._move_row_to(state, world_population.SCENE_ID)
        home = self._labels(self._step(state))
        for frozen in FROZEN_LABELS:
            self.assertIn(
                frozen, home,
                "the withheld frame left the one-shot branch latched off; "
                "this session's home scene is empty for good",
            )
        self.assertEqual(state.population_indices, (0, 30, 91))

    def test_the_gate_is_what_refuses_not_a_side_effect(self):
        """Direct proof, per COO-DECISION 0941 item 4's third criterion.

        The assertion calls the gate itself against the scene the row ends
        up naming, rather than re-deriving "not home" independently -- the
        "provable from the gate, not from grepping module names" shape.
        """
        state = self._state("scene_gate_direct")
        self._move_row_to(state, NON_HOME_SCENE_ID)
        self.assertFalse(
            scene_admission_gate.admits_frozen_legacy_population(
                state.foundation.selected.position.scene_id,
            )
        )


if __name__ == "__main__":
    unittest.main()
