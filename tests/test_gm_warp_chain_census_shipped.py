"""GM-A's real acceptance criterion, one layer deeper than the latch.

NOW.md (2026-09-02 03:48+07:00) records the owner's own wording for GM-A:
warping across SEVERAL maps in a row must find the NPCs on EVERY map, not
just on the first warp of a login.  ``tests/test_gm_warp_position_confirmed
.py``'s KA1A class already pins the fix that made that possible -- every
cross-scene hop clears the once-per-login census latch
(``gm_warp_cross_scene_census_latch_cleared_<scene>``) -- but it stops
there, on purpose: it asserts FLAGS and EVENT TOKENS and never dispatches
another frame afterwards, so nothing in this repository has ever measured
the thing the owner will actually look at, which is whether a census with
actors in it is really composed and queued for hop two, hop three and hop
eight.

Clearing a latch is a precondition, not the census.  Between the latch and
the frame sit five more gates that the KA1A class cannot see, every one of
which fails CLOSED and silently (``runtime.py:7893-7906`` and the arms
below it):

* the anchor.  A hop clears ``last_target_pos``, so the anchor now comes
  from ``world_scene_travel.spawn_position(destination(scene_id))`` -- a
  scene the registry does not pin raises, latches ``world_census_refused``
  and ships nothing (``runtime.py:7945-7967``).  The KA1A chain hops to
  ``departure_scene + 1 .. + 7``, i.e. scene ids picked for arithmetic
  rather than from the registry, and never notices because it never asks
  for a frame;
* the composer.  ``lane_hooks.scene_census_composer(scene_id)`` must exist
  AND its module must be production-allowed (``runtime.py:8184-8194``);
* the composer's own admission check -- ``login_entry_allowed`` for that
  scene -- which answers ``None`` and takes the DECLINED arm, latching
  ``world_census_sent = True`` with no frame at all (``runtime.py:8339``);
* composition itself, which latches ``world_census_refused`` on any raise
  (``runtime.py:8326``);
* and, for scene 1 only, the walk-before-census disjunct still held shut on
  purpose (KA1A-AMENDMENT 20260901_1120) -- covered by its own test at the
  bottom of this file, which is a statement about what the tester WILL see,
  not a bug report.

So this file drives the REAL dispatcher, headless, with no scenario objects
at all, and for a chain of eight hops across REGISTRY-PINNED scenes asserts
the thing the owner asks for: a ``WORLD_CENSUS_*`` action, naming that
destination scene, carrying a non-zero actor count, on the very first
ordinary runtime poll after each hop.

The two halves of the harness are borrowed, not invented, so this file
cannot drift away from what the other two prove:

* the warp is armed through the same seam ``tests/test_gm_warp_position_
  confirmed.py`` uses (``_dispatch_with_lanes`` replaced for exactly one
  frame with one returning a single ``WARP_ACTION_LABEL`` action, plus
  ``record_warp_target``) -- so the production path
  ``_gm_warp_note_position_pending`` -> ``_gm_warp_resync_selected_scene``
  is the one that moves the scene and clears the latch;
* the poll and the census filter are ``tests/test_world_census_arrival_
  trigger.py``'s (``EMPTY_RUNTIME_PC``, the frame a player who has not
  touched the keyboard sends, and labels starting ``WORLD_CENSUS_``).

NOT PROVEN HERE, and no line of this file may be quoted as if it were: that
a client draws anybody.  This is the wire/server layer only -- the actions
are composed and queued, and that is where this file stops.  GT-192
(attended) remains the only thing that can say the tester SAW NPCs on every
map, and GM ``/warp`` is the tool that got the session to those maps in the
first place, never the evidence that the maps work.
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

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import scene_catalog  # noqa: E402
from pirateforce_foundation.gm.chat_command_action import (  # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.gm.warp_executor import (  # noqa: E402
    WarpTarget, warp_no_coords_live_target,
)
from pirateforce_foundation.gm.warp_target_record import (  # noqa: E402
    current_character_id,
    record_warp_target,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# tests/test_world_census_arrival_trigger.py's own bytes: an outer
# RuntimeProtocolReq with vital_count == 0 -- the frame a player who has not
# touched the keyboard produces, and the one the census gate reads.
EMPTY_RUNTIME_PC = bytes.fromhex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 00"
)

LATCH_CLEARED_PREFIX = "gm_warp_cross_scene_census_latch_cleared_"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _lane_census_scenes() -> tuple[int, ...]:
    """Every non-home scene a registered, production-allowed composer claims.

    Read from the live registry for the reason
    ``test_world_census_arrival_trigger.py`` gives for the same helper: a
    scene a lane adds tomorrow is covered the day it registers, and a scene
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


def _bare_warp_destinations() -> tuple[int, ...]:
    """Every scene id GM-A's bare ``/warp <scene>`` can actually reach today.

    Asked of the PRODUCTION gate (``warp_executor.warp_no_coords_live_target``,
    which is what ``make_warp_teleport_frame_no_coords_with_target`` re-checks
    before it builds a frame), not listed here: the day LANE-A opens another
    marker-backed scene, this file covers it without an edit, and the day one
    closes, no assertion here is left describing a map nobody can reach.

    ``gm/scene_catalog.py`` names 330 scenes; this set is much smaller, and
    the difference is not a defect -- a ``/warp`` to a scene outside it is
    REFUSED by name (``WarpExecutorError``), never a silent empty map.
    """
    return tuple(
        scene_id for scene_id in sorted(scene_catalog.SCENE_ID_TO_GM_NAME)
        if warp_no_coords_live_target(scene_id) is not None
    )


class _WarpChainHarness(unittest.TestCase):
    """Flagless boot -> arm a real warp -> ask for the next ordinary poll."""

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
        field_mobs.load_roster()

    # ----- boot ----------------------------------------------------------

    def _login_and_start(self, token):
        """No scenario arguments of any kind -- the boot GT-192 will use.

        ``world_census_enabled`` is ``not active_lanes and
        second_password_mode == "required"`` (``runtime.py:991-993``), so
        passing any scenario object here would turn the census off and make
        every assertion below vacuous.  Asserted, not assumed, in
        ``test_the_boot_this_file_uses_really_has_the_census_armed``.
        """
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc(token)
            ))
            state.dispatch(
                self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC)
            )
            character = self.store.list_characters(
                state.foundation.account_id
            )[-1]
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    # ----- frames --------------------------------------------------------

    def _dispatch(self, state, pc):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            actions = state.dispatch(self.legacy.parse_outer(pc))
        return actions, out.getvalue(), err.getvalue()

    def _poll(self, state):
        return self._dispatch(state, EMPTY_RUNTIME_PC)

    def _target_pos_pc(self, xyz, heading=0.0, moving=1):
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
            + self.legacy.u8tag(0x0B, 0)
        )

    def _step(self, state, xyz):
        return self._dispatch(state, self._target_pos_pc(xyz))

    # ----- the warp ------------------------------------------------------

    def _warp(self, state, scene_id):
        """One cross-scene GM warp, through the production arming path.

        Same seam as ``test_gm_warp_position_confirmed.py``: dispatch's own
        ``_dispatch_with_lanes`` is replaced for exactly ONE frame with one
        that returns a single ``WARP_ACTION_LABEL`` action, so the branch
        under test (dispatch reading the label an action carries, then
        ``_gm_warp_note_position_pending`` ->
        ``_gm_warp_resync_selected_scene``) is the production one.  The
        destination is parked first, exactly as ``chat_command_action``'s
        warp verdict parks it before queueing the action.
        """
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        target = WarpTarget(scene_id, spawn[0], spawn[1], spawn[2])
        self.assertTrue(
            record_warp_target(state, target, current_character_id(state))
        )
        real = state._dispatch_with_lanes

        def _one_warp_action(parsed):
            state._dispatch_with_lanes = real
            return [(WARP_ACTION_LABEL, b"", b"", 0.0)]

        state._dispatch_with_lanes = _one_warp_action
        actions, _out, _err = self._dispatch(
            state, self.legacy._synthetic_client_login_pc(state.token)
        )
        self.assertEqual([action[0] for action in actions], [WARP_ACTION_LABEL])
        self.assertEqual(
            state.foundation.selected.position.scene_id, scene_id,
            "the warp did not move the session's scene -- everything this "
            "test measures afterwards would be about the wrong map",
        )
        return spawn

    # ----- reading the answer --------------------------------------------

    @staticmethod
    def _census(actions):
        return [
            action for action in actions
            if action[0].startswith("WORLD_CENSUS_")
        ]

    @staticmethod
    def _actor_count(label):
        """The trailing ``_<count>`` every census label carries.

        ``WORLD_CENSUS_LANE_SCENE7_INITIAL_62`` -> 62.  Returns None when the
        label does not end in a number, which is itself a failure worth
        naming rather than swallowing.
        """
        tail = label.rsplit("_", 1)[-1]
        return int(tail) if tail.isdigit() else None


class TheChainShipsACensusOnEveryHopTests(_WarpChainHarness):
    """PANYA (NOW.md, GM-A): several maps in a row, NPCs on every one.

    The chain below is the shape of the GT-182 session the owner ran and
    rejected GM-A over -- many hops in ONE login, ending with a hop back to
    a scene already visited -- but with the destinations taken from the live
    composer registry instead of arithmetic, because a hop to a scene no
    composer claims can only ever prove the not-home skip.
    """

    def test_every_hop_of_a_long_chain_queues_a_census_for_that_scene(self):
        scenes = _lane_census_scenes()
        self.assertGreaterEqual(
            len(scenes), 4,
            "a chain shorter than four hops is not the scenario GM-A was "
            "rejected over",
        )
        chain = list(scenes)
        chain.append(scenes[0])  # the "back to a map already seen" leg
        state = self._login_and_start("gmwarpchain01")

        seen = []
        for hop_index, scene_id in enumerate(chain):
            self._warp(state, scene_id)
            self.assertFalse(
                state.world_census_sent,
                f"hop {hop_index} to scene {scene_id}: the latch was not "
                "cleared, so no census can be composed for this map",
            )
            actions, _out, _err = self._poll(state)
            census = self._census(actions)
            self.assertTrue(
                census,
                f"hop {hop_index} to scene {scene_id}: the first ordinary "
                "poll after the warp queued NO census action at all -- this "
                "is the empty map the owner reported, measured",
            )
            labels = [action[0] for action in census]
            for label in labels:
                self.assertIn(
                    f"SCENE{scene_id}_", label,
                    f"hop {hop_index}: a census went out, but it is not this "
                    f"destination's ({labels})",
                )
            initial = [
                label for label in labels if "_INITIAL_" in label
            ]
            self.assertEqual(
                len(initial), 1,
                f"hop {hop_index} to scene {scene_id}: expected exactly one "
                f"INITIAL census action, got {labels}",
            )
            count = self._actor_count(initial[0])
            self.assertIsNotNone(
                count, f"hop {hop_index}: unreadable label {initial[0]}",
            )
            self.assertGreater(
                count, 0,
                f"hop {hop_index} to scene {scene_id}: the census shipped "
                "with ZERO actors -- an empty map that reports success",
            )
            seen.append((scene_id, count))

        self.assertEqual([scene for scene, _count in seen], chain)

    def test_every_map_a_bare_warp_can_reach_ships_one_on_arrival(self):
        """The whole reachable world, in one login, in one test.

        The three tests above prove the CHAIN for the lane-composed scenes.
        This one closes the set: it asks the production gate which scenes
        ``/warp <scene>`` can reach at all and requires a census from every
        single one of them -- including scene 2, whose census comes from the
        runtime's own bg0002 arm and not from ``lane_hooks`` at all, so a
        chain built only from the lane registry would never have touched it.

        Scene 1 is the one documented exception and is asserted as an
        exception, not skipped: see ``TheOneMapThatIsStillSilentTests``.
        If the walk-before-census disjunct opens, THIS test starts failing
        too (it will find a census where it expects none), which is the
        reminder to come back and rewrite both.
        """
        destinations = _bare_warp_destinations()
        self.assertIn(world_population.SCENE_ID, destinations)
        state = self._login_and_start("gmwarpchain09")

        shipped = {}
        for scene_id in destinations:
            self._warp(state, scene_id)
            actions, _out, _err = self._poll(state)
            initial = [
                action[0] for action in self._census(actions)
                if "_INITIAL_" in action[0]
            ]
            if scene_id == world_population.SCENE_ID:
                self.assertEqual(
                    initial, [],
                    "scene 1 shipped on arrival -- the walk-before-census "
                    "disjunct opened and this file is now stale",
                )
                continue
            self.assertEqual(
                len(initial), 1,
                f"scene {scene_id} is reachable by a bare /warp but did not "
                f"ship exactly one arrival census: {initial}",
            )
            count = self._actor_count(initial[0])
            self.assertIsNotNone(count, initial[0])
            self.assertGreater(
                count, 0, f"scene {scene_id} shipped an empty census",
            )
            shipped[scene_id] = count

        self.assertEqual(
            sorted(list(shipped) + [world_population.SCENE_ID]),
            sorted(destinations),
            "some reachable map was neither measured nor named as the "
            "exception",
        )

    def test_the_second_hop_is_not_a_replay_of_the_first_maps_roster(self):
        """Two different maps must not ship the same actor count by accident.

        The bug shape this kills is a census composed from the DEPARTURE
        scene's roster after the scene id was relabelled -- it would ship a
        frame (so the test above stays green) that shows the previous map's
        NPCs.  Two scenes whose rosters differ in size make that visible
        without needing to decode the frame.
        """
        scenes = _lane_census_scenes()
        state = self._login_and_start("gmwarpchain02")
        counts = {}
        for scene_id in scenes:
            self._warp(state, scene_id)
            actions, _out, _err = self._poll(state)
            initial = [
                action[0] for action in self._census(actions)
                if "_INITIAL_" in action[0]
            ]
            self.assertEqual(len(initial), 1, f"scene {scene_id}: {initial}")
            counts[scene_id] = self._actor_count(initial[0])

        self.assertGreater(
            len(set(counts.values())), 1,
            "every scene in the chain shipped the same actor count "
            f"({counts}) -- either the rosters really are identical or one "
            "roster is being replayed for every map",
        )

    def test_a_hop_after_the_player_walked_anchors_on_the_destination(self):
        """The chain, run the way a tester runs it: walk, then warp again.

        Every other test in this file warps from a standing start, so
        ``last_target_pos`` is None on arrival and the anchor can only come
        from the destination's own pinned spawn.  A real GT-192 session does
        not look like that: the tester lands, walks around looking for NPCs,
        and only then types the next ``/warp``.  That leaves the DEPARTURE
        map's coordinates in ``last_target_pos``, and the arrival census
        reads that field before it falls back to the spawn
        (``runtime.py:7908-7910``) -- so a hop that forgot to clear it
        composes the new map around a point on the old one.  That is F-1
        from GT-172 arriving through a different door, and it is invisible
        to a label check: the frame ships, names the right scene, carries
        the right count, and puts the bodies where the player is not.

        Measured, not assumed: with ``last_target_pos = None`` removed from
        the resync (``runtime.py:5683``), every other test in this file
        still passes and this one fails.
        """
        scenes = _lane_census_scenes()[:5]
        state = self._login_and_start("gmwarpchain08")
        for hop_index, scene_id in enumerate(scenes):
            spawn = self._warp(state, scene_id)
            actions, _out, _err = self._poll(state)
            self.assertTrue(
                self._census(actions), f"hop {hop_index}: no census at all",
            )
            record = state.census_anchor_record
            self.assertIsNotNone(
                record,
                f"hop {hop_index} to scene {scene_id}: the census committed "
                "without stamping the anchor it used, so nothing downstream "
                "can tell which map it was composed around",
            )
            self.assertEqual(record.scene_id, scene_id)
            self.assertEqual(
                tuple(record.anchor), tuple(float(axis) for axis in spawn),
                f"hop {hop_index} to scene {scene_id}: this map's census was "
                "composed around a point that is not its own spawn -- on the "
                "walking chain that means the PREVIOUS map's coordinates",
            )
            # What the tester does before typing the next /warp.
            self._step(
                state, (spawn[0] + 250.0, spawn[1] - 125.0, spawn[2]),
            )
            self.assertIsNotNone(
                state.last_target_pos,
                "the walk did not register, so the next hop is not the "
                "scenario this test exists to cover",
            )

    def test_each_hop_names_its_own_latch_clear_and_no_other(self):
        """The event trail must be readable hop by hop, in order.

        Without this, a chain that cleared the latch twice for one scene and
        never for another could still satisfy the count-based assertions
        above.
        """
        scenes = _lane_census_scenes()[:4]
        state = self._login_and_start("gmwarpchain03")
        for scene_id in scenes:
            self._warp(state, scene_id)
            self._poll(state)

        cleared = [
            event[len(LATCH_CLEARED_PREFIX):]
            for event in state.events
            if event.startswith(LATCH_CLEARED_PREFIX)
        ]
        self.assertEqual(cleared, [str(scene_id) for scene_id in scenes])


class TheHarnessMeasuresWhatItClaimsTests(_WarpChainHarness):
    """Controls.  A green suite above means nothing without these."""

    def test_the_boot_this_file_uses_really_has_the_census_armed(self):
        state = self._login_and_start("gmwarpchain04")
        self.assertIn("world_census_armed", state.events)

    def test_a_scene_with_no_composer_ships_nothing_and_says_so(self):
        """The negative control, and a true statement about the game.

        Scene 278 is pinned in the registry (so the anchor resolves) but no
        lane composes for it, so the runtime takes its not-home skip.  If
        this ever starts shipping a census, the assertions above are no
        longer measuring composer coverage.
        """
        state = self._login_and_start("gmwarpchain05")
        self._warp(state, 278)
        actions, _out, _err = self._poll(state)

        self.assertEqual(self._census(actions), [])
        self.assertIn("world_census_skipped_scene_278_not_home", state.events)

    def test_without_the_latch_clear_the_second_hop_ships_nothing(self):
        """The mutation this whole file exists to catch, run as a test.

        Re-latching ``world_census_sent`` by hand right after a hop is
        exactly what the pre-``67fe6fe`` runtime did on its own, and it is
        the state GT-182 measured: the map is silent and NOTHING says so.
        """
        scenes = _lane_census_scenes()
        state = self._login_and_start("gmwarpchain06")
        self._warp(state, scenes[0])
        self._poll(state)

        self._warp(state, scenes[1])
        state.world_census_sent = True  # the bug, reintroduced on purpose
        actions, _out, _err = self._poll(state)

        self.assertEqual(
            self._census(actions), [],
            "the second hop shipped a census even with the latch held shut "
            "-- then this file's chain assertions prove nothing",
        )


class TheOneMapThatIsStillSilentTests(_WarpChainHarness):
    """Scene 1 after a warp: what the tester WILL see, written down.

    KA1A-AMENDMENT 20260901_1120 held the scene-1 walk-before-census
    disjunct shut ON PURPOSE (the ChooseNPC/``population_indices`` hazard
    named at ``runtime.py:7880-7891``), and NOW.md's census-latch entry
    records that item 4 stays that way.  The consequence has never been
    written down anywhere the tester reads: warping BACK to Port Royal mid
    session lands on a map that stays empty until the character moves one
    step.  That is not a defect of this chain and this file does not report
    it as one -- it is the boundary of GM-A, pinned so nobody claims "every
    map" without an asterisk, and so the day the disjunct opens, this test
    goes red and somebody has to come back and say so.
    """

    def test_a_warp_back_to_scene_one_stays_empty_until_the_player_moves(self):
        scenes = _lane_census_scenes()
        state = self._login_and_start("gmwarpchain07")
        self._warp(state, scenes[0])
        self._poll(state)

        spawn = self._warp(state, world_population.SCENE_ID)
        actions, _out, _err = self._poll(state)
        self.assertEqual(
            self._census(actions), [],
            "scene 1 shipped a census on arrival -- if the disjunct opened, "
            "this file's docstring and the letters that cite it are stale",
        )

        moved = (spawn[0] + 10.0, spawn[1] + 10.0, spawn[2])
        actions, _out, _err = self._step(state, moved)
        self.assertTrue(
            self._census(actions),
            "one step did not produce the home census either -- then scene 1 "
            "is empty for the whole rest of the session, which is a bigger "
            "statement than this test was written to make",
        )


if __name__ == "__main__":
    unittest.main()
