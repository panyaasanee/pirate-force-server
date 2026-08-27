"""CORE-REQUEST-014 wiring: Columbus (MOBS n_ID 156, bg0001 placement index 1)
-> quest 3021 -> scene 17, driven through the REAL dispatcher.

Drives ``runtime.make_state_class`` headless -- no server process, no socket,
no client -- through a full login/create/start-game sequence and then two
real inbound frames (``ChooseNPC`` naming Columbus, then ``QuestOperateVital``
op1/quest 3021), the same harness convention
``tests/test_world_scene_liveness_wiring.py`` already uses for CORE-REQUEST-
003/004.

MUTATION-PROOF ON PURPOSE.  Before this round's wiring there was no Columbus
branch in ``runtime.py`` at all -- ``_dispatch_columbus_quest3021`` did not
exist, and neither did ``columbus_quest_dispatch.py``.  Reverting either one
makes ``test_choosing_columbus_sends_one_nonempty_npc_conversation_for_
quest_3021`` and ``test_quest_operate_op1_quest3021_after_conversation_
refuses_with_the_vehicle_reason`` fail, not merely go quiet: the first
asserts a frame that would not exist, and the second asserts a refusal EVENT
that would not exist either (a reverted build produces no reply and no event
at all for that frame, which is a silent pass for a test that only checked
"no crash").

CORRECTION round 0z3kjx: the second test used to name TWO refusal events
(scene-17 arrival plus vehicle bind).  It now names one -- scene 17 gained an
owner-decreed placeholder spawn this round (see
``pirateforce_foundation.columbus_quest_dispatch`` module docstring), so only
the vehicle-bind gap (RE-096) still refuses.  The test was updated, not
weakened: it still pins the exact refusal reason string, and still fails if
runtime.py's Columbus branch is reverted.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch
from pirateforce_foundation import world_scene_travel
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _choose_npc_pc(legacy, *actor_ids: int) -> bytes:
    """Same shape as v141's own self-test ``choose_request`` helper
    (``current/pf_login_game_server_v141.py:6242-6250``) -- that helper is
    local to the ``__main__`` self-test scope and not exported, so this
    rebuilds the identical tag sequence from the frozen primitives rather
    than duplicating a guessed one.
    """
    body = b"".join(
        legacy.u16tag(0x12, legacy.CHOOSE_NPC)
        + legacy.u8tag(0x0B, 0)
        + legacy.qwordtag(0x32, actor_id)
        for actor_id in actor_ids
    )
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, len(actor_ids))
        + body
    )


def _target_pos_pc(legacy, xyz=(10.0, 20.0, 30.0), heading=0.0, moving=0,
                    derived=0) -> bytes:
    """Arms ``population_indices`` the same way ``tests/test_world_census_
    wiring.py``'s own ``_step`` helper does (same frame, rebuilt here rather
    than imported so this file has no test-to-test coupling).  Columbus's
    ChooseNPC branch is deliberately gated on ``population_indices`` already
    containing placement index 1 -- see ``runtime.py``'s
    ``_dispatch_columbus_quest3021`` docstring for why -- so every test here
    that expects a conversation has to arm the census first, the same way a
    real client's own TargetPos frame would.
    """
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
        + legacy.u8tag(0x0B, 0)
        + b"".join(legacy.f32tag(value) for value in (*xyz, heading))
        + legacy.u8tag(0x0B, moving)
        + legacy.u8tag(0x0B, derived)
    )


class ColumbusQuest3021WiringTests(unittest.TestCase):
    """Boots through ``runtime.make_state_class`` itself, not a double."""

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

    def _real_state(self, token):
        state_type = make_state_class(self.legacy, self.lifecycle, self.projector)
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        # Arm the arrival census (see _target_pos_pc's docstring) so
        # population_indices contains Columbus's placement index before any
        # test sends a ChooseNPC -- a flagless real boot does this on the
        # player's first TargetPos frame, not on start-game alone.
        state.dispatch(self.legacy.parse_outer(_target_pos_pc(self.legacy)))
        return state

    def test_choosing_columbus_sends_one_nonempty_npc_conversation_for_quest_3021(self):
        state = self._real_state("tok-columbus-conv")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        actions = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        labels = [action[0] for action in actions]
        self.assertIn(
            "CORE_REQUEST_014_COLUMBUS_Q3021_NPC_CONVERSATION_ONCE", labels,
        )
        self.assertIn(
            "core_request_014_columbus_npc_conversation_sent_once",
            state.events,
        )
        self.assertTrue(state.columbus_quest3021_conversation_sent)
        # Genuinely quest 3021 on the wire, not merely labelled so.
        conv_pc = [
            action[1] for action in actions
            if action[0].startswith("CORE_REQUEST_014")
        ][0]
        self.assertIn(
            self.legacy.u16tag(0x12, columbus_quest_dispatch.COLUMBUS_QUEST_ID),
            conv_pc,
        )
        self.assertNotIn(
            self.legacy.u16tag(0x12, 3023), conv_pc,
        )

    def test_a_second_choose_npc_does_not_send_a_duplicate_conversation(self):
        state = self._real_state("tok-columbus-once")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        first = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        second = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))

        def columbus_labels(actions):
            return [
                action[0] for action in actions
                if action[0].startswith("CORE_REQUEST_014")
            ]

        self.assertEqual(
            columbus_labels(first),
            ["CORE_REQUEST_014_COLUMBUS_Q3021_NPC_CONVERSATION_ONCE"],
        )
        self.assertEqual(columbus_labels(second), [])

    def test_choosing_a_different_npc_sends_nothing(self):
        """Mutation check for the identity gate: some OTHER actor identity
        must not trip Columbus's conversation."""
        state = self._real_state("tok-columbus-other")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        other_identity = columbus_identity + 1
        actions = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, other_identity)
        ))
        labels = [action[0] for action in actions]
        self.assertNotIn(
            "CORE_REQUEST_014_COLUMBUS_Q3021_NPC_CONVERSATION_ONCE", labels,
        )
        self.assertFalse(state.columbus_quest3021_conversation_sent)

    def test_quest_operate_op1_quest3021_after_conversation_refuses_with_the_vehicle_reason(self):
        """The mutation-proof half: BEFORE this round's wiring there was no
        Columbus branch at all, so this refused event could never appear --
        revert the runtime.py Columbus branch and this fails.

        UPDATED round 0z3kjx: the scene-17 arrival half of the refusal is
        gone -- scenarios/world_scene_registry_001.json's scene-17 entry now
        carries an owner-decreed placeholder spawn (PANYA-DECISION
        2026-08-27T14:45+07:00), so ``resolve_columbus_arrival`` no longer
        raises ``SceneEntryRefused`` for scene 17.  runtime.py's own
        ``_dispatch_columbus_quest3021`` (untouched by this lane) formats
        one event per entry in ``error.reasons`` generically, so this test
        changing from 2 events to 1 is that loop observing a real change in
        ``columbus_quest_dispatch.py``, not a runtime.py edit."""
        state = self._real_state("tok-columbus-op1")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        self.assertTrue(state.columbus_quest3021_conversation_sent)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(
                columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
            )
        ))
        self.assertEqual(actions, [])
        refusal_events = [
            event for event in state.events
            if event.startswith("columbus_quest3021_dispatch_refused_")
        ]
        self.assertEqual(len(refusal_events), 1, state.events)
        self.assertEqual(
            refusal_events,
            [
                "columbus_quest3021_dispatch_refused_"
                + columbus_quest_dispatch.VEHICLE_BIND_REFUSED_NO_VEHICLE_ROW,
            ],
        )
        self.assertNotIn(
            "columbus_quest3021_dispatch_refused_scene17_teleport_refused_"
            "scene_has_no_pinned_spawn",
            [event for event in state.events],
        )
        self.assertTrue(state.columbus_quest3021_dispatch_attempted)

    def test_columbus_dispatch_reuses_the_boot_loaded_registry_not_a_fresh_disk_read(self):
        """PF-ADVERSARY FINDING, round 4txjyg (R192): the first draft of
        ``_dispatch_columbus_quest3021`` called
        ``dispatch_columbus_quest3021`` without ``registry=``, so
        ``resolve_entry`` fell back to re-reading
        ``scenarios/world_scene_registry_001.json`` from disk on every
        dispatch attempt instead of reusing the SAME boot-loaded
        ``scene_entry_registry`` the login path already threads through --
        a live fault in that file (e.g. a concurrent round editing it, or a
        transient read error) would then propagate an uncaught exception all
        the way up through ``dispatch()`` and kill that player's connection,
        instead of surfacing as the ``SceneEntryRefused`` this module is
        built to expect and catch.  Regression: what must be exactly ZERO is
        the INCREASE in real ``load_scene_registry()`` calls caused
        specifically by the Columbus ChooseNPC+QuestOperateVital step, on
        top of whatever boot/login/target-pos already legitimately caused
        (other subsystems -- travel-gate observation, scene liveness -- may
        call ``load_scene_registry()`` of their own accord during boot, out
        of this test's scope).  Reverting the
        ``registry=scene_entry_registry`` fix in ``runtime.py`` makes this
        fail with extra calls recorded during the Columbus step."""
        real_load = world_scene_travel.load_scene_registry
        calls = []

        def counting_load(*args, **kwargs):
            calls.append(1)
            return real_load(*args, **kwargs)

        with mock.patch.object(
            world_scene_travel, "load_scene_registry", counting_load,
        ):
            state = self._real_state("tok-columbus-registry-reuse")
            calls_after_boot = len(calls)
            columbus_identity = (
                columbus_quest_dispatch.columbus_actor_identity(self.legacy)
            )
            state.dispatch(self.legacy.parse_outer(
                _choose_npc_pc(self.legacy, columbus_identity)
            ))
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_quest_operate_pc(
                    columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
                )
            ))
        self.assertEqual(
            len(calls), calls_after_boot,
            "Columbus dispatch must reuse the boot-loaded registry, not "
            "re-read scenarios/world_scene_registry_001.json from disk "
            f"(boot caused {calls_after_boot} call(s), Columbus dispatch "
            f"added {len(calls) - calls_after_boot} more)",
        )

    def test_quest_operate_without_a_prior_conversation_is_ignored(self):
        """The op1/3021 frame arriving with no NPCConversation sent first
        (no ChooseNPC ever happened this session) must not dispatch -- RE-094
        is explicit that ``QuestOperateVital`` itself carries no actor field,
        so the conversation having been sent IS the only actor-context this
        tree has for "this player is mid-Columbus"."""
        state = self._real_state("tok-columbus-no-conv")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(
                columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
            )
        ))
        self.assertFalse(state.columbus_quest3021_dispatch_attempted)
        self.assertFalse(any(
            event.startswith("columbus_quest3021_dispatch_refused_")
            for event in state.events
        ))

    def test_quest_operate_wrong_quest_id_is_ignored(self):
        """Mutation check for the quest-id gate: op1 for a DIFFERENT quest
        (3020, the pre-existing frozen P0 lane) must not trip Columbus's
        dispatch."""
        state = self._real_state("tok-columbus-wrong-quest")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(3020, 1, 0, 0, 0, 0)
        ))
        self.assertEqual(actions, [])
        self.assertFalse(state.columbus_quest3021_dispatch_attempted)

    def test_quest_operate_wrong_operation_is_ignored(self):
        """Mutation check for the operation gate: op2/quest 3021 (a
        different UI action on the same quest record) must not trip this
        dispatch either."""
        state = self._real_state("tok-columbus-wrong-op")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(
                columbus_quest_dispatch.COLUMBUS_QUEST_ID, 2, 0, 0, 0, 0,
            )
        ))
        self.assertEqual(actions, [])
        self.assertFalse(state.columbus_quest3021_dispatch_attempted)


if __name__ == "__main__":
    unittest.main()
