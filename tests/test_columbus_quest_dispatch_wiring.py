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
refuses_with_both_reasons`` fail, not merely go quiet: the first asserts a
frame that would not exist, and the second asserts refusal EVENTS that would
not exist either (a reverted build produces no reply and no event at all for
that frame, which is a silent pass for a test that only checked "no crash").
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
from pirateforce_foundation import world_m2_crossing_handoff
from pirateforce_foundation import world_m2_return_leg
from pirateforce_foundation import world_population
from pirateforce_foundation import world_population_handoff
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

    def test_quest_operate_op1_quest3021_after_conversation_teleports_to_scene17_no_vehicle(self):
        """The mutation-proof half: BEFORE this round's wiring there was no
        Columbus branch at all, so this teleport action could never appear --
        revert the runtime.py Columbus branch and this fails.

        UPDATED PANYA-DECISION 2026-08-27T15:25+07:00
        (M2-accept-scene17-entry-without-vehicle-fix-later): the owner
        accepted M2 without a vehicle transform. This dispatch now SUCCEEDS
        end to end through the real dispatcher -- a real TeleportVital
        action is queued, no refusal event fires, and every token
        (WORLD_SCENE, the SCENE_ENTRY provisional-decree token, and the
        no-vehicle dispatch token) is still asserted so a future regression
        dropping any one of them is caught here.
        """
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
        labels = [action[0] for action in actions]
        self.assertIn(
            "CORE_REQUEST_014_COLUMBUS_Q3021_TELEPORT_SCENE17_ONCE", labels,
        )
        refusal_events = [
            event for event in state.events
            if event.startswith("columbus_quest3021_dispatch_refused_")
        ]
        self.assertEqual(refusal_events, [], state.events)
        self.assertIn(
            "core_request_014_columbus_scene17_teleport_sent", state.events,
        )
        self.assertTrue(any(
            event.startswith("WORLD_SCENE scene_id=17 ")
            for event in state.events
        ), state.events)
        self.assertIn(
            "SCENE_ENTRY scene=17 xyz=0.000,0.000,0.000 "
            "source=PROVISIONAL-OWNER-DECREE-20260827-1445",
            state.events,
        )
        self.assertIn(
            "COLUMBUS_QUEST3021_NO_VEHICLE_DISPATCH scene=17 source="
            + columbus_quest_dispatch.M2_NO_VEHICLE_TAG,
            state.events,
        )
        self.assertTrue(state.columbus_quest3021_dispatch_attempted)

    def test_the_scene_entry_and_no_vehicle_tokens_actually_reach_stdout(self):
        """PF-ADVERSARY FINDING, round e0daaa: emit=self.events.append alone
        (unlike the login resolve_entry call site, which defaults to
        emit=print) never reaches the real console unless the process was
        started with --export-events -- exactly the tokens PANYA-DECISION
        2026-08-27T14:45+07:00 and GT-106's own pass criteria require a
        human to read off the console. Proves the fix: these lines must
        appear on stdout, not merely in state.events, with no
        --export-events flag involved at all in this harness.
        """
        import io
        from contextlib import redirect_stdout

        state = self._real_state("tok-columbus-stdout")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_quest_operate_pc(
                    columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
                )
            ))
        printed = buffer.getvalue()
        self.assertIn(
            "SCENE_ENTRY scene=17 xyz=0.000,0.000,0.000 "
            "source=PROVISIONAL-OWNER-DECREE-20260827-1445",
            printed,
        )
        self.assertIn(
            "COLUMBUS_QUEST3021_NO_VEHICLE_DISPATCH scene=17 source="
            + columbus_quest_dispatch.M2_NO_VEHICLE_TAG,
            printed,
        )

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

    def test_choosing_columbus_sends_both_quest_options_now(self):
        """CORE-REQUEST-019 (Lane A, 2026-08-27T18:48+07:00): the composed
        conversation must carry BOTH quest 3021 and quest 3205 -- reverting
        the ``runtime.py`` call site back to the single-option
        ``make_columbus_conversation`` makes this fail (only 3021's tag
        would be present)."""
        state = self._real_state("tok-columbus-two-options")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        actions = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        conv_pc = [
            action[1] for action in actions
            if action[0].startswith("CORE_REQUEST_014")
        ][0]
        self.assertIn(
            self.legacy.u16tag(0x12, columbus_quest_dispatch.COLUMBUS_QUEST_ID),
            conv_pc,
        )
        self.assertIn(
            self.legacy.u16tag(
                0x12, columbus_quest_dispatch.COLUMBUS_QUEST_BORNAGAIN_ID,
            ),
            conv_pc,
        )
        self.assertIn(self.legacy.u16tag(0x0F, 2), conv_pc)

    def test_quest_operate_op1_quest3205_after_conversation_refuses_named_reason(self):
        """CORE-REQUEST-019: option 2 (quest 3205, Q_BORNAGAIN) has its own
        independent latch and always refuses today (no persisted
        home-marker column, no captured wire ack -- RE-112) -- mutation
        check: revert the new ``elif`` branch in ``runtime.py`` and this
        fails silently (no refusal event, no console token)."""
        state = self._real_state("tok-columbus-op1-3205")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        self.assertTrue(state.columbus_quest3021_conversation_sent)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(
                columbus_quest_dispatch.COLUMBUS_QUEST_BORNAGAIN_ID,
                1, 0, 0, 0, 0,
            )
        ))
        self.assertEqual(actions, [])
        self.assertIn(
            "columbus_quest3205_dispatch_refused_"
            + columbus_quest_dispatch.BORNAGAIN_MARKER_RESET_REFUSED_NO_PERSISTENCE_ROW,
            state.events,
        )
        self.assertTrue(state.columbus_quest3205_dispatch_attempted)
        # 3021's own latch must be untouched by a 3205 attempt.
        self.assertFalse(state.columbus_quest3021_dispatch_attempted)

    def test_quest_operate_op1_quest3021_still_works_after_two_option_wiring(self):
        """Regression guard: composing the two-option conversation must not
        break quest 3021's own dispatch/teleport path."""
        state = self._real_state("tok-columbus-3021-still-works")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(
                columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
            )
        ))
        labels = [action[0] for action in actions]
        self.assertIn(
            "CORE_REQUEST_014_COLUMBUS_Q3021_TELEPORT_SCENE17_ONCE", labels,
        )
        self.assertTrue(state.columbus_quest3021_dispatch_attempted)
        self.assertFalse(state.columbus_quest3205_dispatch_attempted)

    def test_quest_operate_op1_quest3021_then_3205_both_dispatch_independently(self):
        """A player who tries option 1 first, then goes back and tries
        option 2, must still get option 2's own refusal -- the outer gate
        must not stop checking once ONLY the 3021 latch is set."""
        state = self._real_state("tok-columbus-both-in-order")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(
                columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
            )
        ))
        self.assertTrue(state.columbus_quest3021_dispatch_attempted)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(
                columbus_quest_dispatch.COLUMBUS_QUEST_BORNAGAIN_ID,
                1, 0, 0, 0, 0,
            )
        ))
        self.assertIn(
            "columbus_quest3205_dispatch_refused_"
            + columbus_quest_dispatch.BORNAGAIN_MARKER_RESET_REFUSED_NO_PERSISTENCE_ROW,
            state.events,
        )
        self.assertTrue(state.columbus_quest3205_dispatch_attempted)

    def test_a_successful_crossing_reports_measured_stowaways(self):
        """CORE-REQUEST (LANE-A 20260829_1422): with ``legacy=`` and
        ``held_indices=`` passed at the runtime.py call site, a successful
        3021 crossing prints a MEASURED ``WORLD_POP_STOWAWAYS`` line built
        from this boot's own census indices -- names a GT tester can look
        for in their own console, not in a letter written from another
        boot's table.

        MUTATION-PROOF: revert the two kwargs and the exact same crossing
        still prints a WORLD_POP_STOWAWAYS line -- but the "unmeasured
        reason=call_site_passed_no_legacy" one, which this test forbids by
        word.  A mutation cannot go quiet either way: zero lines and two
        lines both fail the count assertion.
        """
        import io
        from contextlib import redirect_stdout

        state = self._real_state("tok-columbus-stowaways")
        # The harness's own TargetPos census armed this; the call site
        # hands exactly this attribute to the dispatch.
        self.assertIsNotNone(state.world_census_indices)
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_quest_operate_pc(
                    columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
                )
            ))
        printed = buffer.getvalue()
        stowaway_lines = [
            line for line in printed.splitlines()
            if line.startswith("WORLD_POP_STOWAWAYS")
        ]
        self.assertEqual(len(stowaway_lines), 1, printed)
        line = stowaway_lines[0]
        self.assertNotIn("unmeasured", line)
        self.assertNotIn("unreportable", line)
        self.assertIn(" held=", line)
        self.assertIn(" radius=", line)
        self.assertIn(" names=", line)
        # The call site's _emit records AND prints (the e0daaa finding's
        # convention): the same measured line must be in state.events too.
        self.assertIn(line, state.events)

    def test_a_successful_crossing_reports_the_departed_row_return_leg(self):
        """CORE-REQUEST (LANE-A 20260829_1546): the third keyword on the
        same runtime.py line -- ``departed_from`` is the in-memory scene-1
        position the character stands on at the moment of the crossing, so
        the WORLD_M2_RETURN_LEG line reports ``source=departed_row`` with a
        measured drift.

        MUTATION-PROOF: revert the kwarg and the same crossing still prints
        a WORLD_M2_RETURN_LEG line -- but the
        ``source=pinned_home_entry ... drift=unmeasured:
        call_site_passed_no_departure_row`` one, which this test forbids by
        word.  Zero lines and two lines both fail the count assertion, so a
        mutation cannot go quiet either way.
        """
        import io
        from contextlib import redirect_stdout

        state = self._real_state("tok-columbus-return-leg")
        # The harness's TargetPos frame checkpointed the in-memory row to
        # (10, 20, 30) in scene 1 -- the exact row the call site now hands
        # to the dispatch.
        departed = state.foundation.selected.position
        self.assertEqual(departed.scene_id, 1)
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_quest_operate_pc(
                    columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
                )
            ))
        printed = buffer.getvalue()
        leg_lines = [
            line for line in printed.splitlines()
            if line.startswith("WORLD_M2_RETURN_LEG")
        ]
        self.assertEqual(len(leg_lines), 1, printed)
        line = leg_lines[0]
        self.assertIn("owed=YES", line)
        self.assertIn("source=departed_row", line)
        self.assertNotIn("call_site_passed_no_departure_row", line)
        self.assertNotIn("unmeasured", line)
        # The drift the line reports is the module's own measurement over
        # the very row the harness checkpointed -- re-derived here through
        # the same public function, not re-asserted as a constant.
        expected_drift = world_m2_return_leg.drift_from_pinned_home(departed)
        self.assertIn(" drift={0:.1f}".format(expected_drift), line)
        # _emit records AND prints (the e0daaa convention).
        self.assertIn(line, state.events)

    def test_a_crossing_from_a_non_home_row_reports_the_named_absence(self):
        """pf-adversary (round roj9lp, D4): the conversation latch has no
        scene guard and survives a scene change, so the in-memory row can
        name another scene by the time the QuestOperate arrives.  A row
        from another scene is not a departure from home --
        ``return_ticket`` validates a passed row even when it would not
        use it, so handing it over degrades the whole line to a
        reason-only ``refused:ValueError`` stub with no ticket in it.
        The call site's scene guard passes None instead, which keeps the
        full pinned-home ticket on the console with the named absence --
        the exact line this state produced before the kwarg existed.

        MUTATION-PROOF: drop the ``scene_id == HOME_SCENE_ID`` conjunct
        from the guard and this crossing prints the "refused:" stub this
        test forbids by word.
        """
        import io
        from contextlib import redirect_stdout
        from dataclasses import replace

        state = self._real_state("tok-columbus-non-home-row")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        # A scene change between the conversation and the quest operate --
        # the in-memory shape a travel-gate crossing or GM warp leaves
        # behind (in-memory only, no durable write needed for this test).
        selected = state.foundation.selected
        state.foundation.selected = replace(
            selected, position=replace(selected.position, scene_id=2),
        )
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_quest_operate_pc(
                    columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
                )
            ))
        printed = buffer.getvalue()
        leg_lines = [
            line for line in printed.splitlines()
            if line.startswith("WORLD_M2_RETURN_LEG")
        ]
        self.assertEqual(len(leg_lines), 1, printed)
        line = leg_lines[0]
        self.assertNotIn("refused:", line)
        self.assertIn("owed=YES", line)
        self.assertIn("source=pinned_home_entry", line)
        self.assertIn("call_site_passed_no_departure_row", line)

    def test_a_successful_crossing_reports_the_return_population_owed(self):
        """The fourth report line on the same flagless call site: the
        population handoff the RETURN trip would need, named but not built
        (``world_m2_return_leg.return_population_owed`` -- see that
        function's own docstring for why it stays a source/count report
        rather than a composed frame).  Wired the same way the three report
        lines before it were: through ``columbus_quest_dispatch``'s own
        call, with no ``runtime.py`` edit.

        MUTATION-PROOF: drop the emit call and this test's line count goes to
        zero; swap in the eager ``handoff_on_crossing`` builder by mistake
        and ``kind=census``/``count=`` would still print but the module's own
        import-list tripwire (``test_world_m2_return_leg.py``) fails first.
        """
        import io
        from contextlib import redirect_stdout

        state = self._real_state("tok-columbus-return-population")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_quest_operate_pc(
                    columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
                )
            ))
        printed = buffer.getvalue()
        population_lines = [
            line for line in printed.splitlines()
            if line.startswith("WORLD_M2_RETURN_POPULATION")
        ]
        self.assertEqual(len(population_lines), 1, printed)
        line = population_lines[0]
        self.assertIn("owed=YES", line)
        self.assertIn(
            "source=" + world_scene_travel.CENSUS_SOURCE, line)
        self.assertIn("kind=census", line)
        self.assertIn("composed=NO", line)
        expected_count, expected_source = (
            world_population.census_count_for_dispatch()
        )
        self.assertIn("count={0}".format(expected_count), line)
        self.assertIn("count_source=" + expected_source, line)
        # _emit records AND prints (the e0daaa convention).
        self.assertIn(line, state.events)


class CrossingHandoffQueuedWiringTests(unittest.TestCase):
    """CORE-REQUEST (LANE-A round czoo9t) wired by chief round R250/65etwo:
    ``world_m2_crossing_handoff.crossing_handoff()`` is now actually QUEUED
    on the flagless Columbus 3021 path (``crossing_handoff_dispatched=True``
    at the ``runtime.py`` call site), not merely composed-and-printed the
    way round `czoo9t` shipped it.

    THIS CLASS IS THE GAP CHIEF NAMED IN ITS OWN ROUND REPORT.  R250's own
    text says it plainly: "ไม่มีเทสไหน assert บรรทัดคอนโซล/`dispatched=`
    ที่จุดรวมนี้โดยตรง ... นี่คือ 'false green' ที่แท้จริง" -- the wiring
    that actually sends bytes to the client landed with zero coverage of
    its own join, verified only by one hand-run probe during that round
    that left no trace on `main`.  Every test below is new this round and
    was RUN AGAINST THE PRE-EXISTING `runtime.py` code with no source edit
    of this round's own -- there was nothing to build, only something real
    already shipped to pin down before a future edit can regress it
    silently.

    MUTATION-PROOF, checked by hand against `runtime.py:5036` before
    writing this docstring: reverting ``crossing_handoff_dispatched=True``
    to the module's own default (``False``) at that one call site flips
    ``dispatched=NO`` back on -- caught by
    ``test_the_console_line_says_dispatched_yes_exactly_once`` below.
    Removing the ``handoff_actions`` splice (``runtime.py:5100-5111``)
    drops the clear frame out of the action list entirely -- caught by
    ``test_the_crossing_handoff_frame_is_queued_before_the_teleport_frame``.
    """

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
        state.dispatch(self.legacy.parse_outer(_target_pos_pc(self.legacy)))
        return state

    def _cross(self, token):
        state = self._real_state(token)
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        return state

    def test_the_crossing_handoff_frame_is_queued_before_the_teleport_frame(self):
        state = self._cross("tok-crossing-handoff-queued")
        # The SAME handoff the runtime call site reads, recomputed through
        # this lane's own public functions -- not a second, hand-guessed
        # encoder.
        expected_entry = columbus_quest_dispatch.resolve_columbus_arrival()
        expected_handoff = world_m2_crossing_handoff.crossing_handoff(
            self.legacy, expected_entry,
        )
        self.assertTrue(expected_handoff.sends_a_frame)
        self.assertEqual(
            expected_handoff.dispatch_slot,
            world_population_handoff.SLOT_BEFORE_TELEPORT,
        )

        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(
                columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
            )
        ))
        labels = [action[0] for action in actions]
        self.assertIn(expected_handoff.label, labels, actions)
        self.assertIn(
            "CORE_REQUEST_014_COLUMBUS_Q3021_TELEPORT_SCENE17_ONCE", labels,
        )
        self.assertLess(
            labels.index(expected_handoff.label),
            labels.index(
                "CORE_REQUEST_014_COLUMBUS_Q3021_TELEPORT_SCENE17_ONCE"
            ),
            "the clear frame's own dispatch_slot is before_teleport -- it "
            f"must be queued ahead of the teleport action: {actions!r}",
        )
        handoff_action = [
            action for action in actions if action[0] == expected_handoff.label
        ][0]
        self.assertEqual(handoff_action[1], expected_handoff.pc)
        self.assertEqual(handoff_action[2], expected_handoff.frame)

    def test_the_console_line_says_dispatched_yes_exactly_once(self):
        import io
        from contextlib import redirect_stdout

        state = self._real_state("tok-crossing-handoff-dispatched-yes")
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_quest_operate_pc(
                    columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
                )
            ))
        printed = buffer.getvalue()
        handoff_lines = [
            line for line in printed.splitlines()
            if line.startswith(world_m2_crossing_handoff.CONSOLE_TAG)
        ]
        self.assertEqual(len(handoff_lines), 1, printed)
        line = handoff_lines[0]
        self.assertIn(" dispatched=YES ", line)
        self.assertNotIn("dispatched=NO", line)
        self.assertIn(" composed=YES ", line)
        # e0daaa convention: emit records AND prints the same line.
        self.assertIn(line, state.events)
        self.assertIn(
            "world_m2_crossing_handoff_clear_scene_17", state.events,
        )

    def test_a_successful_crossing_clears_the_frozen_membership_fields(self):
        """A CLEAR handoff's own ``membership_reset.clears_everything`` is
        ``True`` (nothing replaces Port Royal's roster with a sea roster --
        the sea composer refuses to invent one, see
        ``world_population_handoff.SCENES_INTENTIONALLY_UNPOPULATED``), so
        the frozen state's own membership fields must go to ``None``, not
        be left holding Port Royal's placement indices after the boat
        sails.  Armed non-``None`` by the harness's own TargetPos frame
        before the crossing, checked ``None`` after."""
        state = self._real_state("tok-crossing-handoff-membership-reset")
        self.assertIsNotNone(state.population_indices)
        self.assertIsNotNone(state.world_census_indices)
        columbus_identity = columbus_quest_dispatch.columbus_actor_identity(
            self.legacy,
        )
        state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, columbus_identity)
        ))
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_quest_operate_pc(
                columbus_quest_dispatch.COLUMBUS_QUEST_ID, 1, 0, 0, 0, 0,
            )
        ))
        self.assertIsNone(state.population_indices)
        self.assertIsNone(state.world_census_indices)


if __name__ == "__main__":
    unittest.main()
