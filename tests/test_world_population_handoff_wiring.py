"""COO-DECISION 20260829_2254: runtime.py calls the crossing handoff.

``tests/test_world_population_handoff.py`` proves the seam against bare
inputs; ``tests/test_world_travel_gate_wiring.py`` proves the crossing
commit order against a DOUBLE that mirrors the letter's patch.  Neither
executes the block in ``runtime.py`` that this round wired, so neither can
see the four things the wiring owns:

  1. the handoff frame is queued in the slot the handoff itself names --
     a clear BEFORE the teleport (it belongs to the scene the client still
     renders), a census AFTER it (it belongs to the scene being loaded);
  2. a census is queued twice (initial + reapply), at the handoff's own
     reapply_ms -- NOT "the login cadence": the login census composes only
     after the client reports in-scene, so its reapply is redundancy,
     while here the initial goes out 0.0s after the teleport (mid-load,
     the state the seam's docstring says may be dropped) and the reapply
     is the only copy with a chance to land in-scene (pf-adversary R235,
     D4).  Scene-load-time vs reapply_ms is UNMEASURED; the module names
     TravelGateSet._settle() as the composition point the day it grows a
     callback;
  3. the membership fields are rewritten together on every crossing, and
     ONLY a home-scene census writes real values -- every other crossing
     (clear, unavailable, and a roster census alike) clears them, because
     the frozen state may neither keep naming actors the client no longer
     holds (the one-ChooseNPC-recomposes-the-old-town failure) nor be
     handed roster indices the frozen ChooseNPC composer cannot answer
     (pf-adversary R235, D2: connection-fatal KeyError);
  4. identity resolution survives only a census crossing back into the
     home scene -- the face-frame gate must not correct clicks against a
     membership that no longer describes the client.

This file drives the REAL dispatcher -- login, arrival census, then a
scripted walk into the departure gate and back -- with
``travel_gate_debug_enabled=True``, which is the one boot configuration
where a gate crossing can happen at all (production gates are inert; see
DebugDefaultOffTests).  Same justification as
``test_world_scene_liveness_wiring.py``'s real-crossing test.

NOT proven here: that any client renders the recomposed population.
Wire/headless evidence only (G5); GT-081 remains the observable half.
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

from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation import world_population_handoff  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation import world_travel_gate  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.world_travel_gate import (  # noqa: E402
    forget_preload, load_travel_gates, preload,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
DEPARTURE_GATE = "port_royal_columbus_departure"
ATTENDED_SPAWN = (-8553.947265625, -2579.68896484375, 186.0)
STAGE_LANDING = (-13200.0, 22800.0, -2492.0)
CENSUS_ANCHOR = (10.0, 20.0, 30.0)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class CrossingHandoffWiringTests(unittest.TestCase):
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
        forget_preload()
        preload()
        self.addCleanup(forget_preload)
        self.settings = load_travel_gates()[1]
        gates = load_travel_gates()[0]
        self.centre = {g.name: g for g in gates}[DEPARTURE_GATE].centre

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ----------------------------------------------------------

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            travel_gate_debug_enabled=True,
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
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
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

    def _report(self, state, xyz):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(
                self.legacy.parse_outer(self._target_pos_pc(xyz))
            )
        return actions, buf.getvalue()

    def _walk_until_crossing(self, state, xyz):
        """Stand on a spot until the dwell rule opens the gate."""
        for _ in range(self.settings.dwell_reports + 2):
            actions, console = self._report(state, xyz)
            if any("TELEPORT" in a[0] for a in actions):
                return actions, console
        self.fail("the walk never produced a crossing")

    def _cross_out(self, state):
        """Login anchor, arrival census, then into the departure gate."""
        self._report(state, CENSUS_ANCHOR)
        self.assertIsNotNone(state.population_indices)
        self.assertTrue(state.world_census_identity_resolved)
        return self._walk_until_crossing(state, self.centre)

    # ----- the four pinned properties ---------------------------------------

    def test_a_clear_crossing_queues_the_clear_before_the_teleport(self):
        state = self._state("chw_clear")
        actions, console = self._cross_out(state)
        labels = [a[0] for a in actions]
        clear_label = "WORLD_POP_HANDOFF_CLEAR_SCENE_278"
        teleport = next(i for i, l in enumerate(labels) if "TELEPORT" in l)
        self.assertIn(clear_label, labels)
        self.assertLess(
            labels.index(clear_label), teleport,
            "a clear belongs to the scene the client still renders: %r"
            % labels,
        )
        self.assertIn("WORLD_POP_HANDOFF ", console)
        self.assertIn("kind=clear", console)
        self.assertIn(
            "world_pop_handoff_clear_scene_278", state.events,
        )
        # THE BYTES, not just the label (pf-adversary R235, D1: swapping
        # pc/frame in the hand-typed action tuple survived the whole
        # suite; the sender ships element [2], so the swap would put the
        # unframed pc on the wire for every crossing).  The clear frame is
        # deterministic, so it is pinned against an independent compose,
        # and the frame slot is pinned as the FRAMED pc.
        clear = actions[labels.index(clear_label)]
        independent = world_population_handoff.handoff_on_crossing(
            self.legacy, 278, tuple(self.centre),
        )
        self.assertEqual(clear[1], independent.pc)
        self.assertEqual(clear[2], independent.frame)
        self.assertEqual(clear[2], self.legacy.frame_pc(clear[1]))

    def test_a_clear_crossing_drops_the_membership_it_cannot_answer_for(self):
        state = self._state("chw_membership")
        self._cross_out(state)
        self.assertIsNone(state.population_indices)
        self.assertIsNone(state.population_refresh_anchor)
        self.assertFalse(
            state.world_census_identity_resolved,
            "the face-frame gate may not correct clicks against a "
            "membership the client no longer holds",
        )

    def test_a_crossing_clears_mob_combat_announced_membership_too(self):
        """RE-157 job 2 / LANE-B letter 1838 (CORE-REQUEST): an ordinary
        travel-gate crossing never used to touch
        ``mob_combat_announced_membership`` at all -- only login, GM /warp,
        and the bg0001/bg0002/lane-composer census points did -- so a
        player who walked into a new scene through this gate (not a GM
        /warp) could keep the OLD scene's combat membership, matching
        ``_gm_warp_resync_selected_scene``'s own drop+bump reasoning for
        exactly the same reason: a membership nobody can answer for is a
        membership to drop.
        """
        state = self._state("chw_combat_membership")
        departure_scene = 1
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                departure_scene, (0x2058,),
                state.mob_combat_announced_membership_generation,
            )
        )
        generation_before = state.mob_combat_announced_membership_generation

        self._cross_out(state)

        self.assertIsNone(state.mob_combat_announced_membership)
        self.assertGreater(
            state.mob_combat_announced_membership_generation,
            generation_before,
        )
        self.assertTrue(
            any(
                event.startswith(
                    "world_travel_gate_crossing_mob_combat_membership_"
                    "cleared_"
                )
                for event in state.events
            ),
            state.events,
        )

    def test_the_return_census_queues_after_the_teleport_and_reapplies(self):
        state = self._state("chw_return")
        self._cross_out(state)
        # The client lands, walks out of the landing zone, and comes back.
        self._report(state, STAGE_LANDING)
        self._report(state, (-11500.0, 22800.0, -2492.0))
        actions, console = self._walk_until_crossing(
            state, (-13100.0, 22800.0, -2492.0),
        )
        labels = [a[0] for a in actions]
        census_label = "WORLD_POP_HANDOFF_CENSUS_SCENE_1"
        teleport = next(i for i, l in enumerate(labels) if "TELEPORT" in l)
        self.assertIn(census_label, labels)
        self.assertIn(census_label + "_REAPPLY", labels)
        self.assertGreater(
            labels.index(census_label), teleport,
            "a census belongs to the scene being loaded: %r" % labels,
        )
        self.assertGreater(
            labels.index(census_label + "_REAPPLY"),
            labels.index(census_label),
        )
        # The cadence is the handoff's own reapply_ms in SECONDS -- the same
        # ms-to-s conversion every sibling census branch does.  Pinned to the
        # module constant, not a literal, so a deliberate cadence change
        # shows up here as a test edit, never as a silent drift
        # (pf-adversary R235 M2: reapply_ms/100.0 survived the first
        # version of this file).
        initial = actions[labels.index(census_label)]
        reapply = actions[labels.index(census_label + "_REAPPLY")]
        self.assertEqual(initial[3], 0.0)
        self.assertEqual(
            reapply[3],
            world_population_handoff.INITIAL_REAPPLY_MS / 1000.0,
        )
        self.assertIn("kind=census", console)
        # The membership now names what the return frame put on the client,
        # and the anchor is the census's own -- both from one MembershipReset.
        self.assertIsNotNone(state.population_indices)
        self.assertTrue(len(state.population_indices) > 0)
        self.assertIsNotNone(state.population_refresh_anchor)
        self.assertTrue(state.world_census_identity_resolved)
        # And the bytes queued are the handoff's own, byte for byte
        # (pf-adversary R235, D1): an independently composed handoff at
        # the recorded anchor must match the queued pc AND frame exactly,
        # and the frame slot must be the FRAMED pc -- the swap mutant dies
        # on either line.
        independent = world_population_handoff.handoff_on_crossing(
            self.legacy, world_scene_travel.HOME_SCENE_ID,
            tuple(state.population_refresh_anchor),
        )
        self.assertEqual(initial[1], independent.pc)
        self.assertEqual(initial[2], independent.frame)
        self.assertEqual(initial[2], self.legacy.frame_pc(initial[1]))
        self.assertEqual(
            len(state.population_indices), len(independent.membership),
        )
        # world_census_indices and the recompose stamp travel with the
        # return census (pf-adversary R235, D6 -- the partial-commit
        # shape): both must describe the census now in force.
        self.assertEqual(
            state.world_census_indices, state.population_indices,
        )
        self.assertEqual(
            tuple(state.census_anchor_record.anchor),
            tuple(state.population_refresh_anchor),
        )

    def test_a_roster_census_crossing_withholds_the_membership(self):
        """pf-adversary R235 D2 (MEASURED, latent behind the inert gates):
        the frozen ChooseNPC composer (v141:4395) speaks the bg0001 table
        unconditionally, so roster indices written into
        ``population_indices`` are one click from a connection-fatal
        KeyError.  The wiring therefore ships a non-home census's frame
        but withholds its membership, with a named event.  The gate table
        only crosses 1<->278, so the roster census is substituted at the
        seam boundary -- a REAL scene-14 handoff (81 actors), composed by
        the seam itself, returned where the crossing would receive it.
        This also pins the home-scene conjunct the identity flag stands
        on, which no gate-reachable walk can distinguish (D5)."""
        from unittest import mock

        roster = world_population_handoff.handoff_for_arrival(
            self.legacy, 14, (0.0, 0.0, 0.0),
        )
        self.assertEqual(
            roster.kind, world_population_handoff.KIND_CENSUS,
        )
        self.assertGreater(len(roster.membership), 0)
        state = self._state("chw_roster_withheld")
        self._report(state, CENSUS_ANCHOR)
        with mock.patch.object(
            world_population_handoff, "handoff_on_crossing",
            return_value=roster,
        ):
            actions, console = self._walk_until_crossing(
                state, self.centre,
            )
        labels = [a[0] for a in actions]
        census_label = "WORLD_POP_HANDOFF_CENSUS_SCENE_14"
        teleport = next(i for i, l in enumerate(labels) if "TELEPORT" in l)
        # The frame still ships (the scene is not left empty)...
        self.assertIn(census_label, labels)
        self.assertGreater(labels.index(census_label), teleport)
        # ...but the membership does not reach the frozen state.
        self.assertIsNone(state.population_indices)
        self.assertIsNone(state.population_refresh_anchor)
        self.assertIsNone(state.world_census_indices)
        self.assertFalse(state.world_census_identity_resolved)
        self.assertIn(
            "world_pop_handoff_membership_withheld_scene_14",
            state.events,
        )

    def test_the_crossing_still_departs_when_the_handoff_cannot_compose(self):
        """The handoff's fail-closed contract reaches the wiring: a broken
        composition must not cost the player the crossing itself."""
        from unittest import mock

        state = self._state("chw_unavailable")
        self._report(state, CENSUS_ANCHOR)
        with mock.patch.object(
            world_population_handoff, "handoff_for_arrival",
            side_effect=RuntimeError("composer exploded"),
        ):
            actions, console = self._walk_until_crossing(state, self.centre)
        labels = [a[0] for a in actions]
        self.assertTrue(any("TELEPORT" in l for l in labels), labels)
        self.assertFalse(
            any(l.startswith("WORLD_POP_HANDOFF_") for l in labels), labels,
        )
        self.assertIn("kind=unavailable", console)
        # An unavailable handoff still drops the membership: nobody can
        # answer for it (the seam's own contract).
        self.assertIsNone(state.population_indices)
        self.assertIsNone(state.population_refresh_anchor)


if __name__ == "__main__":
    unittest.main()
