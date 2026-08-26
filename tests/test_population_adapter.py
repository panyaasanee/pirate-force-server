import copy
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.population import (
    AUTHORITATIVE_COUNT,
    build_port_royal_initial_population,
    build_port_royal_membership_transition,
)
from pirateforce_foundation.population_scenario import (
    PopulationScenario,
    load_population_scenario,
)
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore


INITIAL = (-6.3993670664785895e-06, -146.40045166015625, 931.0)
REFRESH = (271.29193115234375, -1748.8984375, 931.0)


class PopulationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.scenario = load_population_scenario(
            ROOT / "scenarios/object_population_v94.json"
        )
        self.store = SQLiteStore(
            Path(self.tmp.name) / "population.sqlite3", ROOT / "migrations"
        )
        self.store.migrate()
        default = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default, self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.projector = LegacyProjector(self.legacy)

    def tearDown(self):
        self.tmp.cleanup()

    def target_pc(self, xyz=INITIAL, heading=0.0, moving=0):
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + b"".join(self.legacy.f32tag(value) for value in (*xyz, heading))
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, 0)
        )

    def state(self, *, scenario=True, ready=True, token="population",
              world_census_actor_count=None):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            population_scenario=self.scenario if scenario else None,
            world_census_actor_count=world_census_actor_count,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[0]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.runtime_ack_sent = ready
        state.welcome_message_sent = ready
        state.current_scene_music_sent = ready
        return state, character

    def test_config_is_an_exact_geometry_free_allowlist(self):
        source = ROOT / "scenarios/object_population_v94.json"
        original = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(self.scenario.authoritative_count, 20)
        self.assertEqual(self.scenario.refresh_distance, 1000.0)
        self.assertEqual(self.scenario.initial_reapply_ms, 3000)
        serialized = json.dumps(original, sort_keys=True)
        for forbidden in ("\"x\"", "\"y\"", "\"z\"", "heading"):
            self.assertNotIn(forbidden, serialized)

        bad = Path(self.tmp.name) / "bad.json"
        mutations = (
            lambda data: data.update(extra=True),
            lambda data: data.update(schema=True),
            lambda data: data["entry"].update(scene_id=2),
            lambda data: data["population"].update(source_count=114),
            lambda data: data["population"].update(refresh_distance=999),
            lambda data: data["population"].update(initial_reapply_ms=2999),
            lambda data: data["population"].update(x=0),
            lambda data: data["capabilities"].append("combat"),
            lambda data: data["nonclaims"].reverse(),
        )
        for mutate in mutations:
            candidate = copy.deepcopy(original)
            mutate(candidate)
            bad.write_text(json.dumps(candidate), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_population_scenario(bad)
        bad.write_text("[]", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_population_scenario(bad)

    def test_first_ready_target_commits_checkpoint_then_initial_and_reapply(self):
        state, character = self.state()
        actions = state.dispatch(self.legacy.parse_outer(self.target_pc()))
        expected = build_port_royal_initial_population(self.legacy, INITIAL)
        self.assertEqual([action[0] for action in actions], [
            "OBJECT_POP_V94_INITIAL_NEAREST20",
            "OBJECT_POP_V94_INITIAL_MODEL_READY_REAPPLY",
        ])
        self.assertEqual([action[1:3] for action in actions], [
            (expected.pc, expected.frame), (expected.pc, expected.frame),
        ])
        self.assertEqual([action[3] for action in actions], [0.0, 3.0])
        self.assertEqual(state.object_population_membership, expected.current_indices)
        self.assertEqual(state.object_population_anchor, INITIAL)
        self.assertEqual(state.object_population_generation, 1)
        self.assertEqual(len(expected.entrant_indices), AUTHORITATIVE_COUNT)
        self.assertEqual(expected.retained_indices, ())
        persisted = self.store.get_character(character.id)
        self.assertEqual(
            persisted.position,
            Position(1, 0, *INITIAL, 0.0),
        )
        self.assertNotIn(
            "V134_P0_P30_P91_ISOLATED_INITIAL_READY",
            [action[0] for action in actions],
        )

    def test_super_succeeds_before_commit_and_action_order_is_preserved(self):
        state, character = self.state(token="super-order")
        state.welcome_message_sent = False
        state.current_scene_music_sent = False
        original = self.legacy.GameSessionState.dispatch
        observations = []

        def checking_dispatch(instance, parsed):
            observations.append((
                instance.object_population_membership,
                instance.object_population_anchor,
                self.store.get_character(character.id).position,
            ))
            return original(instance, parsed)

        self.legacy.GameSessionState.dispatch = checking_dispatch
        try:
            actions = state.dispatch(self.legacy.parse_outer(self.target_pc()))
        finally:
            self.legacy.GameSessionState.dispatch = original
        self.assertEqual(len(observations), 1)
        self.assertIsNone(observations[0][0])
        self.assertIsNone(observations[0][1])
        self.assertEqual(observations[0][2], Position(1, 0, *INITIAL, 0.0))
        self.assertEqual(len(state.object_population_membership), AUTHORITATIVE_COUNT)
        self.assertEqual(state.object_population_anchor, INITIAL)
        self.assertEqual([action[0] for action in actions], [
            "V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE",
            "V100_MUSIC_CONTROL_CURRENT_SCENE",
            "OBJECT_POP_V94_INITIAL_NEAREST20",
            "OBJECT_POP_V94_INITIAL_MODEL_READY_REAPPLY",
        ])

    def test_super_failure_preserves_checkpoint_but_rolls_back_population(self):
        state, character = self.state(token="super-failure")
        original = self.legacy.GameSessionState.dispatch

        def fail_dispatch(_instance, _parsed):
            raise RuntimeError("injected inherited dispatch failure")

        self.legacy.GameSessionState.dispatch = fail_dispatch
        try:
            with self.assertRaisesRegex(RuntimeError, "injected inherited"):
                state.dispatch(self.legacy.parse_outer(self.target_pc()))
        finally:
            self.legacy.GameSessionState.dispatch = original
        self.assertEqual(
            self.store.get_character(character.id).position,
            Position(1, 0, *INITIAL, 0.0),
        )
        self.assertIsNone(state.object_population_membership)
        self.assertIsNone(state.object_population_anchor)
        self.assertEqual(state.object_population_generation, 0)
        self.assertTrue(state.npc_spawn_sent)
        self.assertIsNone(state.population_indices)
        self.assertNotIn(
            "object_population_v94_initial_membership_committed", state.events,
        )

        changed, changed_character = self.state(token="changed-super-failure")
        changed.dispatch(self.legacy.parse_outer(self.target_pc()))
        prior_membership = changed.object_population_membership
        prior_anchor = changed.object_population_anchor
        prior_generation = changed.object_population_generation
        self.legacy.GameSessionState.dispatch = fail_dispatch
        try:
            with self.assertRaisesRegex(RuntimeError, "injected inherited"):
                changed.dispatch(self.legacy.parse_outer(self.target_pc(REFRESH)))
        finally:
            self.legacy.GameSessionState.dispatch = original
        self.assertEqual(
            self.store.get_character(changed_character.id).position,
            Position(1, 0, *REFRESH, 0.0),
        )
        self.assertEqual(changed.object_population_membership, prior_membership)
        self.assertEqual(changed.object_population_anchor, prior_anchor)
        self.assertEqual(changed.object_population_generation, prior_generation)

    def test_readiness_shape_scene_and_checkpoint_fail_closed(self):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            population_scenario=self.scenario,
        )
        unselected = state_type("unselected")
        self.assertEqual(
            unselected.dispatch(self.legacy.parse_outer(self.target_pc())), []
        )
        self.assertIsNone(unselected.object_population_membership)

        state, character = self.state(ready=False, token="not-ready")
        not_ready_actions = state.dispatch(
            self.legacy.parse_outer(self.target_pc())
        )
        self.assertFalse(any(
            action[0].startswith("OBJECT_POP_") for action in not_ready_actions
        ))
        self.assertIsNone(state.object_population_membership)
        self.assertEqual(self.store.get_character(character.id).position.x, INITIAL[0])
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        replay_actions = state.dispatch(self.legacy.parse_outer(self.target_pc()))
        self.assertEqual(
            len([a for a in replay_actions if a[0].startswith("OBJECT_POP_")]), 2
        )

        malformed, _ = self.state(token="malformed")
        parsed = self.legacy.parse_outer(self.target_pc())
        parsed.vital_count = 2
        self.assertEqual(malformed.dispatch(parsed), [])
        self.assertIsNone(malformed.object_population_membership)
        nonfinite = self.target_pc((math.nan, INITIAL[1], INITIAL[2]))
        self.assertEqual(malformed.dispatch(self.legacy.parse_outer(nonfinite)), [])
        self.assertIsNone(malformed.object_population_membership)

        wrong_scene, _ = self.state(token="wrong-scene")
        wrong_scene.foundation.selected = replace(
            wrong_scene.foundation.selected,
            position=Position(2, 0, *INITIAL, 0.0),
        )
        self.assertEqual(
            wrong_scene.dispatch(self.legacy.parse_outer(self.target_pc())), []
        )
        self.assertIsNone(wrong_scene.object_population_membership)

        failed, _ = self.state(token="checkpoint-failure")
        failed.foundation.checkpoint = lambda _position: (_ for _ in ()).throw(
            PermissionError("stale lease")
        )
        with self.assertRaises(PermissionError):
            failed.dispatch(self.legacy.parse_outer(self.target_pc()))
        self.assertIsNone(failed.object_population_membership)
        self.assertIsNone(failed.object_population_anchor)

    def test_threshold_suppression_transition_and_natural_reentry(self):
        state, character = self.state()
        state.dispatch(self.legacy.parse_outer(self.target_pc()))
        initial_membership = state.object_population_membership

        near = (INITIAL[0] + 100.0, INITIAL[1], INITIAL[2])
        self.assertEqual(state.dispatch(self.legacy.parse_outer(self.target_pc(near))), [])
        self.assertEqual(state.object_population_anchor, INITIAL)
        self.assertEqual(state.object_population_membership, initial_membership)
        parsed_near = self.legacy.parse_v141_refresh_target_pos(
            self.legacy.parse_outer(self.target_pc(near))
        )
        self.assertEqual(
            self.store.get_character(character.id).position.x, parsed_near[0]
        )

        expected = build_port_royal_membership_transition(
            self.legacy, initial_membership, REFRESH,
        )
        actions = state.dispatch(self.legacy.parse_outer(self.target_pc(REFRESH)))
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][0], "OBJECT_POP_V94_REFRESH_ENTER[91]_LEAVE[70]")
        self.assertEqual(actions[0][1:3], (expected.pc, expected.frame))
        self.assertEqual(state.object_population_membership, expected.current_indices)
        self.assertEqual(state.object_population_anchor, REFRESH)
        self.assertEqual(state.object_population_generation, 2)

        reverse = build_port_royal_membership_transition(
            self.legacy, expected.current_indices, INITIAL,
        )
        actions = state.dispatch(self.legacy.parse_outer(self.target_pc(INITIAL)))
        self.assertEqual(actions[0][0], "OBJECT_POP_V94_REFRESH_ENTER[70]_LEAVE[91]")
        self.assertEqual(actions[0][1:3], (reverse.pc, reverse.frame))
        self.assertEqual(state.object_population_membership, reverse.current_indices)
        self.assertEqual(state.object_population_generation, 3)

    def test_threshold_advances_anchor_but_suppresses_unchanged_set(self):
        state, _ = self.state()
        state.dispatch(self.legacy.parse_outer(self.target_pc()))
        membership = state.object_population_membership
        generation = state.object_population_generation
        state.object_population_anchor = (INITIAL[0] - 1000.0, INITIAL[1], INITIAL[2])
        self.assertEqual(state.dispatch(self.legacy.parse_outer(self.target_pc())), [])
        self.assertEqual(state.object_population_anchor, INITIAL)
        self.assertEqual(state.object_population_membership, membership)
        self.assertEqual(state.object_population_generation, generation)
        self.assertIn("object_population_unchanged_set_suppressed", state.events)

    def test_modes_are_mutually_exclusive(self):
        for kwargs in (
            {"scenario": object(), "population_scenario": self.scenario},
            {"scene_load_scenario": object(), "population_scenario": self.scenario},
            {"scenario": object(), "scene_load_scenario": object(),
             "population_scenario": self.scenario},
        ):
            with self.assertRaises(ValueError):
                make_state_class(
                    self.legacy, self.lifecycle, self.projector, **kwargs,
                )
        with self.assertRaises(ValueError):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                population_scenario=PopulationScenario(
                    self.scenario.scenario_id, 1, 20, 999.0, 3000,
                ),
            )
        with self.assertRaises(ValueError):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                population_scenario=PopulationScenario(
                    self.scenario.scenario_id, True, 20, 1000.0, 3000,
                ),
            )

    def test_no_scenario_baseline_actions_remain_golden(self):
        """WORLD-CENSUS-001 changed the LABEL of the no-scenario boot, and the
        golden proves the ONLY other thing that changed is the two name tags
        GT-078's fix added.

        Before BUILD-001 was wired this boot emitted the frozen
        ``V134_P0_P30_P91_ISOLATED_*`` pair, and the golden below is still
        those exact bytes - captured from ``make_v112_monster_shop_
        population_state()``, which this project does not edit and which is
        still nameless for P0/P91 today.  This boot now emits the census
        instead, whose rung 3 is pinned to the same three placements in the
        same frozen order, so set/order equality still holds.  Byte equality
        does NOT any more:

        AMENDMENT 2026-08-26 (post-GT-078 OWNER-REJECTED name fix, this
        lane).  ``_entry()`` in world_population.py stopped discarding
        ``SceneActorPlacement.source_name`` for every non-P30 member, so
        rung 3 now carries P0's and P91's own frozen names while the golden
        (the frozen fallback) still does not.  The golden bytes stay exactly
        as captured - they are still correct for what they represent - and
        the invariant this test proves is narrower: the wire is the golden
        bytes plus exactly those two name tags, nothing else moved.  See
        tests/test_world_population.py's
        ``test_rung_three_differs_from_the_shipped_default_by_exactly_the_
        two_added_names`` for the same invariant proven directly against the
        two encoders.
        """
        from pirateforce_foundation.population import load_port_royal_placements
        from pirateforce_foundation.world_population import SHIPPED_MONSTER_INDEX

        state, _ = self.state(
            scenario=False, token="baseline", world_census_actor_count=3,
        )
        self.assertNotIn("object_population_membership", state.__dict__)
        actions = state.dispatch(self.legacy.parse_outer(self.target_pc()))
        golden = json.loads((
            ROOT / "tests/golden/object_pop_002_baseline.json"
        ).read_text(encoding="utf-8"))
        self.assertEqual(
            [action[0] for action in actions],
            ["WORLD_CENSUS_INITIAL_3", "WORLD_CENSUS_REAPPLY_3"],
        )
        # The golden's own labels are still what the frozen branch emits, and
        # are still what a refusing session falls back to, so the key stays
        # live rather than rotting into unread data.
        self.assertEqual(golden["labels"], [
            "V134_P0_P30_P91_ISOLATED_INITIAL_READY",
            "V134_P0_P30_P91_ISOLATED_REAPPLY_READY",
        ])
        self.assertEqual([action[3] for action in actions], golden["delays"])

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        added_bytes = sum(
            len(self.legacy.wstr_tag(placements[index].source_name))
            for index in (0, 30, 91)
            if index != SHIPPED_MONSTER_INDEX
        )
        for action, golden_action in zip(actions, golden["actions"]):
            self.assertEqual(
                len(action[1]) - golden_action["pc_length"], added_bytes,
            )
            self.assertEqual(
                len(action[2]) - golden_action["frame_length"], added_bytes,
            )
        # And both actions of the pair (initial + reapply) are the identical
        # generation replayed, exactly as the golden's own identical pair is.
        self.assertEqual(actions[0][1], actions[1][1])
        self.assertEqual(actions[0][2], actions[1][2])

    def test_no_scenario_boot_sends_the_whole_census_by_default(self):
        """The default boot - no flag of any kind - is the census now.

        This is the assertion the build order exists for.  It is deliberately
        stated on the DEFAULT construction, with no ``world_census_actor_count``
        handed in, because a lane that only works when a test passes an
        argument is exactly the opt-in shape BUILD-001 was written to end.
        """
        state, _ = self.state(scenario=False, token="census")
        actions = state.dispatch(self.legacy.parse_outer(self.target_pc()))
        self.assertEqual(
            [action[0] for action in actions],
            ["WORLD_CENSUS_INITIAL_115", "WORLD_CENSUS_REAPPLY_115"],
        )
        self.assertEqual([action[3] for action in actions], [0.0, 3.0])
        self.assertEqual(state.world_census_actor_count, 115)
        self.assertEqual(len(state.population_indices), 115)
        self.assertIs(state.npc_spawn_sent, True)

    def test_the_population_scenario_boot_keeps_its_own_population(self):
        """Containment: an opt-in lane is not silently repopulated.

        Every hypothesis lane in this tree was measured against the frozen
        three-actor baseline, and several pin actor identities inside the band
        the census occupies.  A boot that opted into one of them must see the
        population it has always seen.
        """
        state, _ = self.state(scenario=True, token="contained")
        actions = state.dispatch(self.legacy.parse_outer(self.target_pc()))
        self.assertEqual(
            [action[0] for action in actions
             if action[0].startswith("WORLD_CENSUS_")],
            [],
        )
        self.assertIsNone(state.world_census_actor_count)


if __name__ == "__main__":
    unittest.main()
