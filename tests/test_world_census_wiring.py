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

import dataclasses
import hashlib
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

# The wire, pinned as bytes, at ONE fixed anchor: (10.0, 20.0, 30.0).
#
# Why this exists.  Before it, the only stored byte check on this lane was
# rung 3, and every other assertion compared the dispatcher's output to
# build_world_population() -- the same producer, so a change inside the
# producer moved both sides together.  Measured: mutating one entry of
# HEADINGS, which mis-orients 28 of the 115 actors on the wire, left the whole
# suite green.  These digests cover 100% of the delivered bytes at every rung
# and that mutant turns them red.
#
# Rung 3's pc digest is the same value tests/golden/object_pop_002_baseline.json
# carries for the frozen V134 collection.  That is not a coincidence to be
# maintained by hand: it is the control rung being byte-identical to what
# shipped, and if it ever stops matching, the census stopped being a superset
# of the shipped wire.
CENSUS_WIRE_SHA256 = {
    3: ("3B77557DB6FDBAD9C5DA6338E1C31937004D4EAAD43FEFC956137C5B584B71CD",
        "5D032431D84C41E38F045AD126243FD6F67CE2669AAB8C45E7FA36B49025CDBD"),
    20: ("E1D2F7A0F69A74E9E5ECF490F666B75CA328A45EFDA33F99982CEE783F8FFC9F",
         "63E194F0275567CE30299274D98EC9F16E278DA12D2A35C2F7833A68D88A1528"),
    60: ("A554F55A23DB79006438BD9B2DD00F76767272874657F8E433699913049B808C",
         "B66173DD2A256C6D30C721C4A719D33524215898D1BDB1CA08EB210A5B8FBB73"),
    115: ("B972F4F4463DDBB28303BC1F694C7BA6DA1CDED76D656D0A79D12D636EC361A6",
          "AD80E280F4908759F066A85204403723D07408EF353491585247667D73074EFE"),
}
PIN_ANCHOR = (10.0, 20.0, 30.0)

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
        # model-ready reapply, not a single frame.  Compared against an
        # INDEPENDENT build rather than against each other -- the dispatcher
        # queues one object twice, so census[0] == census[1] cannot fail and
        # would be decoration.
        independent = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0), scene_id=1,
        )
        for action in census:
            self.assertEqual(action[1], independent.pc)
            self.assertEqual(action[2], independent.frame)
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
        # The inherited branch is disarmed at construction, not from inside
        # dispatch -- see the comment at that assignment for the two measured
        # reasons why.
        self.assertIs(state.npc_spawn_sent, True)
        self.assertIsNone(state.population_indices)
        self.assertIn("world_census_armed", state.events)
        actions = self._step(state)
        generation = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0), scene_id=1,
        )
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
        expected = world_population.build_world_population(
            self.legacy, far, scene_id=1,
        )
        self.assertEqual(census[0][1], expected.pc)
        self.assertEqual(state.population_refresh_anchor, far)
        # Not a tautology: a different anchor really does order the census
        # differently, so this test can fail.
        near = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0), scene_id=1,
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


    # ----- the wire itself, pinned as bytes at every rung -------------------

    def test_every_rung_matches_its_pinned_wire_digest(self):
        """The only assertion in this lane that a change to the BUILDER cannot
        move with it.  See CENSUS_WIRE_SHA256 for the mutant that motivated it.
        """
        for rung, (pc_sha, frame_sha) in sorted(CENSUS_WIRE_SHA256.items()):
            with self.subTest(rung=rung):
                state = self._state(
                    f"census_pin{rung}", world_census_actor_count=rung,
                )
                census = self._census(self._step(state, xyz=PIN_ANCHOR))
                self.assertEqual(len(census), 2)
                self.assertEqual(
                    hashlib.sha256(census[0][1]).hexdigest().upper(), pc_sha,
                )
                self.assertEqual(
                    hashlib.sha256(census[0][2]).hexdigest().upper(),
                    frame_sha,
                )

    # ----- the two ways the trigger used to be wrong ------------------------

    def test_the_census_fires_on_the_frame_that_sets_the_runtime_ack(self):
        """No test in this file may pre-set runtime_ack_sent, and this is why.

        v141 sets runtime_ack_sent INSIDE its dispatch (v141:3771) and only
        then reaches its population branch (v141:4292), so the flag is false
        on entry to the frame that arms it.  An earlier version of this wiring
        read the flag BEFORE super().dispatch and therefore lost that frame
        entirely: the frozen three-actor branch won the session, silently, with
        world_census_refused still False and no event saying so.  A client that
        reconnects mid-session sends TargetPos first, so that was not an exotic
        shape.
        """
        state = self._state("census_ack", ready=False)
        self.assertIs(state.runtime_ack_sent, False)
        actions = self._step(state)
        labels = [action[0] for action in actions]
        self.assertIn("RUNTIME_RES_ACK_FIRST_REQ", labels)
        self.assertIn(f"{INITIAL_PREFIX}115", labels)
        for frozen in FROZEN_LABELS:
            self.assertNotIn(frozen, labels)
        self.assertEqual(state.world_census_actor_count, 115)

    def test_a_target_pos_the_inherited_dispatcher_ignores_composes_nothing(self):
        """The invariant v141:4416 relies on, restated as a test.

        The frozen population branch sits under "outer_id is
        GSCN_RunTimeProtocolReq and teleport_sent" (v141:3680), and
        last_target_pos is assigned only inside that same block (v141:4259).
        So population_indices being set implies last_target_pos is set, and
        v141:4416 unpacks last_target_pos for any member of
        population_indices.  A trigger without those conjuncts could set the
        first without the second, and the next NPC click then raised TypeError
        out of the listener thread -- which has no except clause (v141:7440).
        """
        pc = self._target_pos_pc((-9999.0, 8888.0, 777.0))
        # Same body, different outer envelope: the inherited dispatcher does
        # not look at this frame at all.
        foreign = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_LOGIN_PROTOCOL)
            + pc[len(self.legacy.u16tag(0x12, 0)):]
        )
        state = self._state("census_foreign")
        actions = state.dispatch(self.legacy.parse_outer(foreign))
        self.assertEqual(self._census(actions), [])
        self.assertIsNone(state.population_indices)
        self.assertIsNone(state.last_target_pos)
        # And the click that used to kill the thread is now a no-op.
        self.assertEqual(
            state.dispatch(
                self.legacy.parse_outer(self._choose_npc_pc(0x2002))
            ),
            [],
        )
        # A real frame afterwards still gets the census: nothing was latched.
        self.assertEqual(len(self._census(self._step(state))), 2)

    # ----- containment, part two -------------------------------------------

    def test_the_second_password_lane_keeps_its_measured_population(self):
        """HYP-PF-009 is an opt-in lane that is not a scenario object.

        Its whole measurement is what this client does with an unsolicited
        frame, and it was characterized against the three-actor baseline.  It
        is contained by name because active_lanes cannot see it.
        """
        state = self._state("census_2pw", second_password_mode="bypass")
        labels = [action[0] for action in self._step(state)]
        self.assertEqual(self._census([(label,) for label in labels]), [])
        for frozen in FROZEN_LABELS:
            self.assertIn(frozen, labels)
        self.assertIsNone(state.world_census_actor_count)
        self.assertNotIn("world_census_armed", state.events)

    def test_export_events_is_not_contained_because_it_sends_nothing(self):
        """The other flag outside active_lanes, and the opposite ruling.

        --export-events changes what is printed, never what is sent, and
        GT-076 needs it on the staircase boots.  Containing it would make the
        measurement boots differ from the boot being measured.
        """
        state = self._state(
            "census_events",
            event_exporter=lambda event: None,
        )
        labels = [action[0] for action in self._step(state)]
        self.assertIn(f"{INITIAL_PREFIX}115", labels)

    # ----- the refusal is byte-identical to what shipped --------------------

    def test_a_refusal_queues_the_frozen_collection_byte_for_byte(self):
        """Fail closed means the shipped wire, not an empty town.

        The inherited branch is disarmed at construction, so a refusal cannot
        fall through to it -- the fallback has to rebuild it.  The catch is
        deliberately Exception, not a tuple: the builder reads two frozen
        constants by plain attribute access and calls frozen serializers, so
        drift arrives as AttributeError or struct.error as readily as
        ValueError, and an escape unwinds out of a listener thread that has no
        except clause.
        """
        original = world_population.build_world_population

        def explode(*args, **kwargs):
            raise AttributeError("V117_P30_EXACT_HP")

        state = self._state("census_refused_bytes")
        world_population.build_world_population = explode
        try:
            actions = self._step(state)
        finally:
            world_population.build_world_population = original
        frozen_pc, frozen_frame, frozen_rows = (
            self.legacy.make_v112_monster_shop_population_state()
        )
        self.assertEqual(
            [(label, bytes(pc), bytes(frame), delay)
             for label, pc, frame, delay in actions
             if label in FROZEN_LABELS],
            [
                (FROZEN_LABELS[0], frozen_pc, frozen_frame, 0.0),
                (FROZEN_LABELS[1], frozen_pc, frozen_frame, 3.00),
            ],
        )
        self.assertEqual(self._census(actions), [])
        self.assertIs(state.world_census_refused, True)
        self.assertIs(state.world_census_sent, True)
        self.assertEqual(
            state.population_indices, tuple(row[0] for row in frozen_rows),
        )
        self.assertIn(
            "world_census_compose_refused_AttributeError", state.events,
        )
        self.assertIn("world_census_fell_back_to_frozen_p0_p30_p91",
                      state.events)
        # Latched: the next step neither retries nor re-sends the fallback.
        self.assertEqual(
            [action[0] for action in self._step(state)
             if action[0] in FROZEN_LABELS or action[0].startswith(
                 "WORLD_CENSUS_")],
            [],
        )

    # ----- away from home ---------------------------------------------------

    def test_a_scene_that_is_not_home_gets_no_population_at_all(self):
        """The bg0001 census encodes scene 1 into every actor it builds.

        Delivering it into another map would put dock NPCs in a scene they do
        not belong to, so this refuses rather than degrading to the frozen
        three -- which carry scene 1 just the same.
        """
        state = self._state("census_away")
        selected = state.foundation.selected
        state.foundation.selected = dataclasses.replace(
            selected, position=dataclasses.replace(
                selected.position, scene_id=278,
            ),
        )
        actions = self._step(state)
        self.assertEqual(self._census(actions), [])
        for frozen in FROZEN_LABELS:
            self.assertNotIn(frozen, [action[0] for action in actions])
        self.assertIs(state.world_census_sent, True)
        self.assertIn("world_census_skipped_scene_278_not_home", state.events)


    # ----- BUILD-002 slice 1: the teleport that used to be a literal 1 ------

    def test_the_home_teleport_is_byte_identical_to_the_literal_it_replaced(self):
        """runtime.py:3675 was ``make_login_teleport(1, 0)``.

        It is now a table lookup, which is what lets a character whose row says
        another scene land there.  For a character whose row says scene 1 --
        every character that exists today -- the five arguments the table
        returns are (1, 0, 0.0, 0.0, 0.0), so the frame on the wire has to be
        the same bytes it has always been.  CHARTER-02's cumulative rule at the
        smallest scale there is: this is the assertion that says the change
        cannot cost a player anything.
        """
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type("travel_home")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc("travel_home")
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        teleport = [
            action for action in actions
            if action[0] == "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE"
        ]
        self.assertEqual(len(teleport), 1)
        expected_pc, expected_frame = self.legacy.make_login_teleport(1, 0)
        self.assertEqual(teleport[0][1], expected_pc)
        self.assertEqual(teleport[0][2], expected_frame)
        self.assertEqual(teleport[0][3], 0.70)


if __name__ == "__main__":
    unittest.main()
