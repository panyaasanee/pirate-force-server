"""D8 item 1, MEASURED: does the durable warp write of `#745` leave the
census anchored on the DEPARTURE scene's coordinates?

`COO-DECISION 20260904_1744` item 4 handed this to LANE-GM and asked for a
measurement with a REAL MUTANT on `FoundationSession`, not an opinion:

    "วาปครั้งแรกของล็อกอินใน dispatch เดียวกัน: บล็อก census รันทีหลังใน
     เฟรมเดียวกัน อาจประกอบให้ฉากปลายทาง ขณะที่ `last_target_pos` ยังเป็น
     พิกัดต้นทาง"

(the first warp of a login, in the same dispatch: the census block runs
later in the same frame and may compose the DESTINATION scene's roster
while `last_target_pos` still holds the DEPARTURE scene's coordinates --
GT-172 F-1 arriving through a third door.)

WHY THIS FILE EXISTS SEPARATELY FROM THE TWO IT SITS BETWEEN.  Both halves
were already pinned, and neither half can answer D8 item 1:

  * `tests/test_gm_warp_scene_persist.py` drives the real store and the
    real `FoundationSession`, and pins that `persist_warp_scene` puts
    `foundation.selected` back.  It never runs `runtime.py`'s dispatch, so
    it cannot see what the census anchor does afterwards.
  * `tests/test_gm_warp_position_confirmed.py::GmWarpCensusLatchClearTests`
    drives the real dispatch and pins that a cross-scene resync clears
    `last_target_pos`.  It arms the warp by calling `record_warp_target`
    directly -- no durable write ever happens in it -- so it cannot see
    what `#745`'s write does to the row the resync reads.

D8 item 1 is exactly the seam between them: the write happens FIRST (inside
`chat_command_action._warp_teleport_action_no_coords`, before the action
list is returned), and the resync happens SECOND (in `dispatch`, on the
label of that action).  This file runs both, in that order, on one real
connection.

THE ANSWER THIS FILE MEASURES.  With `#745` on `main` the D1 restore is
what keeps the two halves honest: the durable row moves to the destination,
the IN-MEMORY row stays in the departure scene, so
`_gm_warp_resync_selected_scene` still sees a CROSS-scene warp, relabels,
and clears `last_target_pos` before any census can read it.  D8 item 1 does
NOT occur.

THE MUTANT THAT PROVES IT IS THE FIX DOING THE WORK, not an accident of the
fixture: defeat the restore only (`_restore_selected` -> a no-op that
reports success, i.e. exactly the shape of the first draft pf-adversary
caught), leave everything else real, and the departure scene's coordinates
survive into the destination's census -- D8 item 1 reproduced on demand.

NONCLAIM.  This is a headless measurement of server state.  It is not
evidence that any scene renders, that a census reaches a screen, or that
`GT-172` F-1 is closed; those need the attended pass their own tickets
already name.  No GM step is skipped by it -- no account gains or loses GM
status here, and the fixture logs in through the ordinary flagless boot.
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation.gm import (  # noqa: E402
    accounts as gm_accounts,
    chat_command_action,
    login_scene_override,
    warp_scene_persist,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: Prison Exile.  Marker-backed, `login_entry_allowed` true, and the scene
#: the owner actually typed in R309 -- the same destination
#: `test_gm_warp_scene_persist.py` uses, for the same reason.
DESTINATION_SCENE = 2

NO_COORDS_LABEL = (
    chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class WarpPersistCensusAnchorTests(unittest.TestCase):
    """Real store, real lifecycle, real session, real dispatch."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # The pin both sibling files document: an unpinned login-scene
        # override resolves to the gitignored repo-relative config, which
        # would make "this account has no staged login scene" a fact about
        # the machine rather than about this fixture.
        env_pin = mock.patch.dict(gm_accounts.os.environ, {
            login_scene_override.ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_gm_login_scene.json"),
            login_scene_override.STANDALONE_ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_standalone_map.json"),
        })
        env_pin.start()
        self.addCleanup(env_pin.stop)
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

    # ----- harness -------------------------------------------------------

    def _login_and_start(self, token):
        """The flagless boot: no scenario arguments of any kind."""
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
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
        return state

    def _walked_in_the_departure_scene(self, state):
        """The state a player who moved before warping leaves behind.

        Set on the runtime state rather than replayed through a
        TargetPosVital because what D8 item 1 is about is the VALUE the
        census would anchor on, and this is the field it reads (see
        WORLD-CENSUS-001's own comment in `runtime.py`).  The coordinates
        are the character's own current row, so a stale anchor here is
        indistinguishable from the real thing -- which is the point.
        """
        position = state.foundation.selected.position
        anchor = (position.x, position.y, position.z, 0.0)
        state.last_target_pos = anchor
        # The census already fired once this connection, in the departure
        # scene: the latch KA1A-ROOTCAUSE measured, set exactly as a real
        # first-scene census would leave it.
        state.world_census_sent = True
        return anchor

    def _warp_then_dispatch(self, state):
        """The real send path, then the real dispatch that labels it.

        Order copied from production, not invented here: the durable write
        happens inside `_warp_teleport_action_no_coords` while the action is
        being composed, and `_gm_warp_note_position_pending` runs later, in
        `dispatch`, on the label of the action that came back.
        """
        captured = io.StringIO()
        with redirect_stderr(captured):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                state, DESTINATION_SCENE, self.legacy,
            )
        self.assertIsNotNone(verdict.action)
        self.assertEqual(verdict.action[0], NO_COORDS_LABEL)

        real = state._dispatch_with_lanes

        def _one_warp_action(parsed):
            state._dispatch_with_lanes = real
            return [(NO_COORDS_LABEL, b"", b"", 0.0)]

        state._dispatch_with_lanes = _one_warp_action
        with redirect_stderr(captured):
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc(state.token)
            ))
        self.assertEqual([action[0] for action in actions], [NO_COORDS_LABEL])
        return captured.getvalue()

    def _row_scene(self, state):
        """The scene as the DATABASE holds it, not the in-memory copy."""
        return self.store.get_character(
            state.foundation.selected.id
        ).position.scene_id

    # ----- D8 item 1, measured on the shipped code -----------------------

    def test_the_durable_warp_write_does_not_leave_a_stale_census_anchor(
        self,
    ):
        """The headline: D8 item 1 does not occur with `#745` on `main`."""
        state = self._login_and_start("d8anchor01")
        anchor = self._walked_in_the_departure_scene(state)
        self.assertEqual(state.foundation.selected.position.scene_id, 1)

        self._warp_then_dispatch(state)

        # The durable row moved -- this is `#745`'s own deliverable, asserted
        # here so a regression that silently stops writing cannot make the
        # anchor assertion below pass for the wrong reason.
        self.assertEqual(self._row_scene(state), DESTINATION_SCENE)
        # The in-memory row was relabelled by the resync, which is proof the
        # resync ran at all rather than early-returning.
        self.assertEqual(
            state.foundation.selected.position.scene_id, DESTINATION_SCENE,
        )
        # And the departure scene's coordinates are gone before any census
        # in this dispatch could read them.
        self.assertIsNone(state.last_target_pos)
        self.assertNotEqual(state.last_target_pos, anchor)
        self.assertFalse(state.world_census_sent)

    def test_the_resync_event_names_the_destination_scene(self):
        """A second, independent reading of the same frame.

        `last_target_pos` being None could in principle mean "cleared" or
        "never set"; the event trail distinguishes them, and this test would
        stay green only if the relabel really happened for THIS scene.
        """
        state = self._login_and_start("d8anchor02")
        self._walked_in_the_departure_scene(state)

        self._warp_then_dispatch(state)

        self.assertIn(
            f"gm_warp_selected_scene_resynced_{DESTINATION_SCENE}",
            state.events,
        )
        self.assertTrue(state.scene_label_is_server_guess)

    def test_the_persist_outcome_on_this_path_is_persisted(self):
        """The write door really ran; the anchor result is not a by-product
        of a warp whose durable write was refused before it started."""
        state = self._login_and_start("d8anchor03")
        self._walked_in_the_departure_scene(state)

        self._warp_then_dispatch(state)

        self.assertIn(
            chat_command_action.EVENT_WARP_SCENE_PERSIST_PREFIX
            + warp_scene_persist.OUTCOME_PERSISTED,
            state.events,
        )

    # ----- the mutant: defeat ONLY the D1 restore ------------------------

    def test_without_the_d1_restore_the_departure_anchor_survives(self):
        """MUTANT, and the whole reason this file can claim a measurement.

        `_restore_selected` is replaced by a no-op that REPORTS SUCCESS --
        the exact shape of the first draft pf-adversary caught in round
        `q3cde9` (the durable write landed and the in-memory row was left
        pointing at the destination).  Nothing else is patched: the same
        store, the same session, the same router, the same dispatch.

        What the mutant produces is D8 item 1 in full: the in-memory row now
        names the destination, so `_gm_warp_resync_selected_scene` sees
        `target.scene_id == selected.position.scene_id`, early-returns as a
        same-scene warp, and never clears the anchor -- the census that runs
        later in this dispatch would compose the DESTINATION scene's roster
        around the DEPARTURE scene's coordinates.

        So the answer to `COO 1744` item 4 is "measured, and it does not
        occur" ONLY because the restore is there.  This test goes red the
        day someone removes it, which is what makes the headline test above
        worth reading.
        """
        state = self._login_and_start("d8anchor04")
        anchor = self._walked_in_the_departure_scene(state)

        with mock.patch.object(
            warp_scene_persist, "_restore_selected",
            lambda _foundation, _snapshot: True,
        ):
            self._warp_then_dispatch(state)

        # The mutant does not break the durable write -- it breaks only the
        # in-memory row, which is precisely why the defect was silent.
        self.assertEqual(self._row_scene(state), DESTINATION_SCENE)
        self.assertEqual(
            state.foundation.selected.position.scene_id, DESTINATION_SCENE,
        )
        # D8 item 1, reproduced: the departure scene's coordinates are still
        # the anchor, and the census latch was never unlatched.
        self.assertEqual(state.last_target_pos, anchor)
        self.assertTrue(state.world_census_sent)
        self.assertNotIn(
            f"gm_warp_selected_scene_resynced_{DESTINATION_SCENE}",
            state.events,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
