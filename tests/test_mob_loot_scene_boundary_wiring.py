"""CORE-REQUEST (LANE-B v2, pf_bridge notes_to_chief 20260902_1052): the drop
cell learns about a scene crossing, and the generation it composes there is
HELD until the arrival census has committed.

Drives ``runtime.make_state_class`` headless -- no server process, no socket,
no client.  The warp seam is the same one
``tests/test_gm_warp_chain_census_shipped.py`` uses (park a ``WarpTarget``,
then let dispatch's own ``_gm_warp_note_position_pending`` ->
``_gm_warp_resync_selected_scene`` run), rebuilt here rather than imported so
this file has no test-to-test coupling.

MUTATION-PROOF ON PURPOSE.  Delete the ``_mob_loot_cross_scene_boundary``
call from ``_gm_warp_resync_selected_scene`` and
``test_a_cross_scene_warp_tells_the_drop_cell_it_crossed`` fails on a missing
event.  Delete the census gate from ``_mob_loot_boundary_flush`` and
``test_the_boundary_generation_is_held_until_the_census_commits`` fails on a
frame that arrives one poll too early.  Delete the ``except`` in
``_mob_loot_cross_scene_boundary`` and
``test_a_composer_refusal_is_an_event_not_an_exception`` fails with the
exception it is asserting cannot escape.

WHAT NONE OF THIS PROVES: that a client draws a ground generation delivered at
a scene boundary.  Nobody has watched one.  ``mob_loot.enter_scene_frames``
labels it an assumption of LANE B and NONCLAIM 12 is open.  These tests are
the wire/DB layer only.
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

from pirateforce_foundation import mob_loot                       # noqa: E402
from pirateforce_foundation import world_scene_travel             # noqa: E402
from pirateforce_foundation.gm.chat_command_action import (       # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.gm.warp_executor import (             # noqa: E402
    WarpTarget,
)
from pirateforce_foundation.gm.warp_target_record import (        # noqa: E402
    current_character_id, record_warp_target,
)
from pirateforce_foundation.legacy_bridge import (                 # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle    # noqa: E402
from pirateforce_foundation.model import Position                  # noqa: E402
from pirateforce_foundation.runtime import make_state_class        # noqa: E402
from pirateforce_foundation.store import SQLiteStore               # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

DESTINATION_SCENE_ID = 2


def _legacy():
    return load_legacy(LEGACY_PATH)


class SceneBoundaryWiringTests(unittest.TestCase):

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
        self.empty_poll_pc = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 0)
        )

    # ----- harness -------------------------------------------------------

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        self._dispatch(state, self.legacy._synthetic_client_login_pc(token))
        self._dispatch(state, self.legacy._V25_REAL_CREATE_PC)
        character = self.store.list_characters(state.foundation.account_id)[-1]
        self._dispatch(
            state, self.legacy._synthetic_start_game_pc(character.selector),
        )
        return state

    def _dispatch(self, state, pc):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            actions = state.dispatch(self.legacy.parse_outer(pc))
        return actions

    def _warp(self, state, scene_id):
        """One cross-scene GM warp through the production arming path."""
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
        actions = self._dispatch(
            state, self.legacy._synthetic_client_login_pc(state.token),
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, scene_id,
            "the warp did not move the session's scene",
        )
        return actions

    @staticmethod
    def _ground(actions):
        return [a for a in actions if a[0] == "MOB_LOOT_DROP"]

    # ----- the tests -----------------------------------------------------

    def test_a_cross_scene_warp_tells_the_drop_cell_it_crossed(self):
        state = self._state("tok-boundary-crossed")
        self._warp(state, DESTINATION_SCENE_ID)
        entered = [
            event for event in state.events
            if event.startswith("mob_loot_boundary_entered_")
        ]
        self.assertEqual(
            len(entered), 1,
            "the warp did not reach _mob_loot_cross_scene_boundary: %r"
            % ([e for e in state.events if "mob_loot_boundary" in e],),
        )
        # The scene is named by FOLDER, never by scene id -- the cell's own
        # contract (mob_loot._require_scene refuses a non-str).
        self.assertTrue(
            entered[0].startswith("mob_loot_boundary_entered_Bg0002_"),
            entered[0],
        )

    def test_an_empty_scene_publishes_nothing_and_says_so(self):
        state = self._state("tok-boundary-empty")
        actions = self._warp(state, DESTINATION_SCENE_ID)
        self.assertEqual(self._ground(actions), [])
        self.assertIn(
            "mob_loot_boundary_entered_Bg0002_frames_0", state.events,
        )
        # Nothing is owed, so no later poll invents one either.
        for _ in range(3):
            self.assertEqual(self._ground(self._dispatch(
                state, self.empty_poll_pc)), [])

    def test_the_boundary_generation_is_held_until_the_census_commits(self):
        state = self._state("tok-boundary-held")
        state.mob_loot_boundary_frames_pending = ((b"pc", b"frame"),)
        state.world_census_sent = False
        state.world_census_refused = False
        self.assertEqual(state._mob_loot_boundary_flush(), [])
        self.assertEqual(
            state.mob_loot_boundary_frames_pending, ((b"pc", b"frame"),),
            "a held generation must still be owed after a refused flush",
        )
        state.world_census_sent = True
        released = state._mob_loot_boundary_flush()
        self.assertEqual(released, [("MOB_LOOT_DROP", b"pc", b"frame", 0.0)])
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())
        self.assertIn("mob_loot_boundary_flushed_frames_1", state.events)
        # Flushed once, never twice.
        self.assertEqual(state._mob_loot_boundary_flush(), [])

    def test_a_refused_census_also_releases_the_held_generation(self):
        """A census that refused by name is never coming.  Holding the ground
        hostage to it would lose the ground forever on that map."""
        state = self._state("tok-boundary-refused-census")
        state.mob_loot_boundary_frames_pending = ((b"pc", b"frame"),)
        state.world_census_sent = False
        state.world_census_refused = True
        self.assertEqual(
            state._mob_loot_boundary_flush(),
            [("MOB_LOOT_DROP", b"pc", b"frame", 0.0)],
        )

    def test_the_held_generation_rides_last_in_the_dispatch(self):
        state = self._state("tok-boundary-last")
        state.mob_loot_boundary_frames_pending = ((b"pc", b"frame"),)
        state.world_census_sent = True
        actions = self._dispatch(state, self.empty_poll_pc)
        self.assertTrue(actions, "expected at least the boundary action")
        self.assertEqual(actions[-1], ("MOB_LOOT_DROP", b"pc", b"frame", 0.0))
        self.assertEqual(len(self._ground(actions)), 1)

    def test_an_unaddressed_scene_id_is_refused_by_name_with_no_frames(self):
        state = self._state("tok-boundary-unaddressed")
        state._mob_loot_cross_scene_boundary(9999)
        self.assertIn(
            "mob_loot_boundary_scene_9999_unaddressed_no_frames", state.events,
        )
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())

    def test_a_composer_refusal_is_an_event_not_an_exception(self):
        """The listener thread has no ``except`` above this call.  A refusal
        the composer is entitled to raise (an unmined item id in a standing
        row, a duplicate key, a serializer handle that is not the frozen one)
        must not travel."""
        state = self._state("tok-boundary-refusal")

        def _boom(_legacy, _scene):
            raise mob_loot.MobLootContractError(
                mob_loot.REFUSE_TYPE_NOT_TYPED_RECORD, "measured refusal",
            )

        state.mob_loot_cell.enter_scene_frames = _boom
        state._mob_loot_cross_scene_boundary(DESTINATION_SCENE_ID)
        self.assertIn(
            "mob_loot_boundary_compose_refused_MobLootContractError",
            state.events,
        )
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())

    def test_a_kill_refused_for_being_in_another_scene_is_handled_not_raised(self):
        """SOURCE-LEVEL PIN, and it is labelled as one.

        Declaring the cell's scene (which this round's boundary call now
        does) arms ``mob_loot.REFUSE_KILL_IN_ANOTHER_SCENE`` in
        ``loot_a_kill``.  The dispatch site catches only two refusal names
        and re-raises the rest, into a listener thread with no ``except``.
        This asserts the third name is handled in the same block.  It is NOT
        a driven kill: no attended or headless round has produced this
        refusal yet, and pretending otherwise would be the kind of claim
        this project strikes.
        """
        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn("mob_loot.REFUSE_KILL_IN_ANOTHER_SCENE", source)
        self.assertIn('"mob_loot_refused_kill_in_another_scene_"', source)


if __name__ == "__main__":
    unittest.main()
