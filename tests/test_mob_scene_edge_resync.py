"""The combat roster follows the player across a scene edge, measured.

COO-DECISION 2026-09-03T19:43+07:00 item 1, on chief's finding
``pf_bridge/notes_to_chief/20260903_1855_CHIEF-FINDING-COO-the-mob-register-
belongs-to-another-scene-after-a-warp.md``.

WHAT THIS FILE IS ABOUT, in the words of the console line that lied::

    standing in scene 278 -> MOB_AI_TICK_LIVE scene=278 mobs=4
    standing in scene  14 -> MOB_AI_TICK_LIVE scene=14  mobs=4

Neither scene has a mined mob table (``field_mobs.live_scenes()`` is
bg0001/Bg0002 and nothing else), so their truthful roster is empty.  The
four rows are bg0001's, held since ``__init__`` because
``_sync_combat_scene_state`` had three callers -- an attack and the scene-1
and scene-2 census branches -- and a player who warps anywhere else and does
not attack never reaches one of them.  R306 and R307 both printed it off the
owner's own screen.

WHAT EACH CARD REFUSES TO BE.  None of these assert that a call exists:
they boot the real dispatcher and read the structures the tick decides
aggro from.  Delete the call at the top of ``dispatch`` and the first two
go red; delete the call in ``_gm_warp_resync_selected_scene`` and the third
does; the last four hold the conditions the same ruling attached to the fix
(ground rows survive, an unaddressed scene is a refusal and not an empty
roster, a same-scene frame does not silently reset a wound, and a refusal
inside the sync cannot unwind the frame).

NOT PROVEN HERE: that a real client walking in scene 14 sees anything
different.  These are wire/DB-layer measurements on a headless boot; the
client-observable half belongs to GT-224, which the ruling deliberately did
NOT wait for.
"""
from __future__ import annotations

import contextlib
import io
import random
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import mob_loot  # noqa: E402
from pirateforce_foundation import world_scene_folder  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_b_mob_ai_tick,
)
from pirateforce_foundation.gm.warp_executor import WarpTarget  # noqa: E402
from pirateforce_foundation.gm.warp_target_record import (  # noqa: E402
    SESSION_ATTRIBUTE as GM_WARP_TARGET_SESSION_ATTRIBUTE,
    WarpTargetRecord,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.mob_death import DeathRecord  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
LIVE_TOKEN = "MOB_AI_TICK_LIVE"
STEP_ANCHOR = (11.0, 22.0, 33.0)
# The beach football field: real in scene_entry_registry (so a character can
# be seeded standing in it), addressed by world_scene_folder, and NOT in
# field_mobs.live_scenes() -- which is what makes "mobs=4" there a lie about
# another scene rather than a count of its own.
AWAY_SCENE_ID = 278
AWAY_FOLDER = "Bg1177"
KILLER = 0x1234
# The real resolver captured at import, so a test can patch
# scene_folder_for_scene_id to return None for ONE unaddressed id while
# every other scene still resolves truthfully.
_REAL_FOLDER = world_scene_folder.scene_folder_for_scene_id


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class SceneEdgeResyncTests(unittest.TestCase):
    """Same boot shape as tests/test_mob_ai_tick_gate_wiring.py: the real
    state class, a throwaway SQLite database, real frames through the real
    parser.  Nothing here registers a double for the code under test."""

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
        # The premise every card below rests on, asserted instead of
        # assumed: the away scene is ADDRESSED (so it is not a refusal) and
        # has no table of its own (so its honest roster is empty).
        self.assertEqual(
            world_scene_folder.scene_folder_for_scene_id(AWAY_SCENE_ID),
            AWAY_FOLDER,
        )
        self.assertNotIn(AWAY_FOLDER, field_mobs.live_scenes())

    # ----- harness ------------------------------------------------------

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

    def _booted(self, token, scene_id=None):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(
            self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC)
        )
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        if scene_id is not None:
            destination = world_scene_travel.destination(scene_id)
            spawn = world_scene_travel.spawn_position(destination)
            self.store.select_character(
                state.foundation.session_id, character.selector,
            )
            self.store.save_position(
                state.foundation.session_id, character.id,
                Position(scene_id, 0, spawn[0], spawn[1], spawn[2], 0.0),
            )
        with contextlib.redirect_stdout(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    def _step(self, state, xyz=STEP_ANCHOR):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            state.dispatch(
                self.legacy.parse_outer(self._target_pos_pc(xyz))
            )
        return out.getvalue(), err.getvalue()

    def _seed_one_ground_row(self, state):
        """One dropped item standing on the floor, through the cell's own
        kill path -- the same route ``_dispatch_mob_combat`` uses.  The seed
        is SEARCHED for, not typed, so a change to the drop tables makes
        this fixture fail loudly instead of silently seeding nothing."""
        roster = field_mobs.load_roster(field_mobs.BG0002_SCENE)
        state.mob_loot_cell.enter_scene(field_mobs.BG0002_SCENE)
        for mob in roster:
            for seed in range(64):
                drops = state.mob_loot_cell.loot_a_kill(
                    mob,
                    DeathRecord(mob.actor_identity, KILLER, mob.max_hp),
                    mob_loot.roll_drops(mob, random.Random(seed)),
                    kill_token=seed + 1,
                )
                if drops:
                    return drops
        self.fail("no (mob, seed) pair in Bg0002 dropped anything")

    # ----- the edge itself ----------------------------------------------

    def test_a_frame_from_another_scene_reopens_the_roster(self):
        # THE ONE THAT DIES WHEN THE CALL AT THE TOP OF dispatch() GOES.
        # The character is seeded standing in the away scene BEFORE
        # StartGame, which is a door no lane syncs: no attack, no scene-1
        # or scene-2 census.  Before this fix the register and the ledger
        # stayed on the boot roster for the whole session.
        state = self._booted("edge_other_scene", scene_id=AWAY_SCENE_ID)
        self.assertEqual(
            state.foundation.selected.position.scene_id, AWAY_SCENE_ID)
        self._step(state)
        self.assertEqual(
            state.mob_combat_scene_folder, AWAY_FOLDER,
            "the session is standing in %s and the combat structures are "
            "still opened on %r" % (
                AWAY_FOLDER, state.mob_combat_scene_folder,
            ),
        )
        self.assertEqual(state.mob_ai_register.rows, ())
        self.assertEqual(state.mob_combat_ledger.identities(), ())
        self.assertEqual(state.mob_combat_ledger.scene, AWAY_FOLDER)

    def test_the_live_line_stops_naming_another_scenes_mobs(self):
        # The exact line R306/R307 printed off the owner's screen, which is
        # how this defect was found in the first place.  ``mobs=`` is read
        # from the register the tick is about to run on, so a register that
        # still holds bg0001 prints 4 under a scene that has no mobs at all.
        state = self._booted("edge_live_line", scene_id=AWAY_SCENE_ID)
        out, _err = self._step(state)
        lines = [
            line for line in out.splitlines()
            if line.startswith(LIVE_TOKEN)
        ]
        self.assertEqual(
            lines, ["%s scene=%d mobs=0" % (LIVE_TOKEN, AWAY_SCENE_ID)],
            "the tick's own console line still reports another scene's "
            "mob count while the player stands in a scene with no table",
        )

    def test_a_warp_reconciles_on_the_next_frame_not_its_own(self):
        # The warp resync relabels the scene at the END of its own dispatch
        # and does NOT re-open the roster there (pf-adversary round pk14rf,
        # finding 5: nothing between that relabel and the next dispatch reads
        # the register or ledger, so a same-frame call was dead weight).
        # This pins BOTH halves: after the resync the folder is still the
        # departure scene (the one-frame lag is real and intended), and the
        # detector at the top of the next frame reconciles it.
        state = self._booted("edge_warp_lag")
        self.assertEqual(state.mob_combat_scene_folder, "bg0001")
        target = WarpTarget(AWAY_SCENE_ID, 1.0, 2.0, 3.0)
        setattr(
            state, GM_WARP_TARGET_SESSION_ATTRIBUTE,
            WarpTargetRecord(target, getattr(
                state.foundation.selected, "id", None)),
        )
        state._gm_warp_resync_selected_scene(state.foundation.selected)
        self.assertEqual(
            state.foundation.selected.position.scene_id, AWAY_SCENE_ID)
        # The relabel happened; the roster has NOT been re-opened yet.
        self.assertEqual(
            state.mob_combat_scene_folder, "bg0001",
            "the warp resync re-opened the roster inside its own frame -- "
            "the removed same-frame call is back",
        )
        # Next frame: the top-of-dispatch detector reconciles it.
        self._step(state)
        self.assertEqual(state.mob_combat_scene_folder, AWAY_FOLDER)
        self.assertEqual(state.mob_ai_register.rows, ())

    # ----- the conditions the ruling attached to the fix -----------------

    def test_ground_rows_survive_the_edge(self):
        # COO-DECISION 2026-09-02T02:53+07:00, carried into item 1 of the
        # ruling this change implements: re-opening the combat ledger MUST
        # NOT delete ground rows.  A dropped item lives in mob_loot_cell,
        # which this path does not touch -- pinned, not stated, because the
        # withdrawn reconcile_scene_transition() call would have deleted
        # exactly these rows from exactly this boundary.
        state = self._booted("edge_ground_rows")
        drops = self._seed_one_ground_row(state)
        before = state.mob_loot_cell.scene_ledger()
        self.assertTrue(drops)
        cell = state.mob_loot_cell
        # Cross the edge the same way the dispatcher learns about one: the
        # scene label changes, then a frame arrives.
        state.foundation.selected = replace(
            state.foundation.selected,
            position=replace(
                state.foundation.selected.position,
                scene_id=AWAY_SCENE_ID,
            ),
        )
        self._step(state)
        self.assertEqual(state.mob_combat_scene_folder, AWAY_FOLDER)
        self.assertIs(state.mob_loot_cell, cell)
        self.assertEqual(
            state.mob_loot_cell.scene_ledger(), before,
            "crossing a scene edge deleted the rows standing on the "
            "floor of the scene the player left",
        )

    def test_an_unaddressed_scene_leaves_the_combat_state_untouched(self):
        # RECONCILED WITH LANE-B (pf-adversary round pk14rf finding 2 vs
        # test_scene_scoped_combat_wiring).  An unaddressed scene is a
        # refusal, not an arrival: the combat folder, ledger and register
        # must stay on the departed scene here.  The tick lie is killed at
        # the tick (next card), not by swapping the scene on a refusal.
        state = self._booted("edge_unaddressed_untouched")
        folder_before = state.mob_combat_scene_folder
        ids_before = state.mob_combat_ledger.identities()
        rows_before = state.mob_ai_register.rows
        state.foundation.selected = replace(
            state.foundation.selected,
            position=replace(
                state.foundation.selected.position, scene_id=12,
            ),
        )
        with mock.patch.object(
            world_scene_folder, "scene_folder_for_scene_id",
            return_value=None,
        ):
            state._sync_combat_scene_at_edge()
        self.assertEqual(state.mob_combat_scene_folder, folder_before)
        self.assertEqual(state.mob_combat_ledger.identities(), ids_before)
        self.assertEqual(state.mob_ai_register.rows, rows_before)

    def test_the_tick_does_not_fire_in_a_scene_the_register_is_not_for(self):
        # THE #2 FIX, at the tick.  313 of the 330 GM-warpable scene ids are
        # unaddressed; standing in one leaves the register on the departed
        # scene (card above), so the tick and its MOB_AI_TICK_LIVE line must
        # NOT run off it -- that is the exact scene=N mobs=4 lie.  The gate
        # compares the current scene's folder to the register's; they
        # disagree here, so nothing fires and nothing prints.
        state = self._booted("edge_tick_guard")
        # Force production_allowed so the ONLY thing standing the tick down
        # is the folder-agreement guard, not the lane switch.
        previous = lane_hooks._PRODUCTION_ALLOWED.get(
            lane_b_mob_ai_tick.MODULE_NAME)
        lane_hooks._PRODUCTION_ALLOWED[
            lane_b_mob_ai_tick.MODULE_NAME] = True
        self.addCleanup(
            lane_hooks._PRODUCTION_ALLOWED.__setitem__,
            lane_b_mob_ai_tick.MODULE_NAME, previous)
        state.foundation.selected = replace(
            state.foundation.selected,
            position=replace(
                state.foundation.selected.position, scene_id=12,
            ),
        )
        with mock.patch.object(
            world_scene_folder, "scene_folder_for_scene_id",
            side_effect=lambda sid: (
                None if sid == 12
                else _REAL_FOLDER(sid)
            ),
        ):
            out, err = self._step(state)
        self.assertEqual(
            [l for l in out.splitlines() if l.startswith(LIVE_TOKEN)], [],
            "MOB_AI_TICK_LIVE printed off a register that is not this "
            "scene's -- the scene=N mobs=4 lie",
        )
        self.assertNotIn(lane_b_mob_ai_tick.MODULE_NAME, err)

    def test_an_unaddressed_scene_still_refuses_an_attack_by_name(self):
        # Leaving the combat state alone (above) must NOT change the attack
        # path's own answer: _dispatch_mob_combat calls _sync_combat_scene_
        # state itself, which re-resolves the folder and returns None for an
        # unaddressed scene, so an attack there still refuses by name.
        state = self._booted("edge_unaddressed_attack")
        state.foundation.selected = replace(
            state.foundation.selected,
            position=replace(
                state.foundation.selected.position, scene_id=12,
            ),
        )
        with mock.patch.object(
            world_scene_folder, "scene_folder_for_scene_id",
            return_value=None,
        ):
            self.assertIsNone(state._sync_combat_scene_state())

    def test_a_persistent_refusal_is_logged_once_not_every_frame(self):
        # runtime.py:1269's rule: an events list appended to per frame may
        # not grow without a bound the client controls.  combat_scene_edge_
        # scene_id is advanced BEFORE the work, so a scene that keeps failing
        # (or an unaddressed one the player stands still in) is evaluated
        # once per arrival, not once per movement frame.  An early draft
        # left the folder marker unchanged on refusal and re-logged forever.
        state = self._booted("edge_refusal_once")
        state.foundation.selected = replace(
            state.foundation.selected,
            position=replace(
                state.foundation.selected.position, scene_id=AWAY_SCENE_ID,
            ),
        )

        def boom():
            raise RuntimeError("scene edge refusal under test")

        state._sync_combat_scene_state = boom
        for step in range(6):
            self._step(state, xyz=(11.0 + step, 22.0, 33.0))
        refused = [
            e for e in state.events
            if e == "combat_scene_edge_resync_refused_RuntimeError"
        ]
        self.assertEqual(
            len(refused), 1,
            "a persistent refusal logged once per frame: %d lines" % (
                len(refused),
            ),
        )

    def test_the_success_edge_event_names_both_scenes(self):
        # The greppable token this change ships. Asserted here so its
        # spelling, its <from>, and the fact that it fires at all are pinned
        # -- an early draft shipped it with zero cards, and a mutant that
        # deleted the event or the folder-None guard passed every other
        # card.  Booted on the home scene, then crossed to scene 2 (Bg0002,
        # a live roster), so the event is the resynced form, not the
        # unaddressed one.
        state = self._booted("edge_success_event")
        state.foundation.selected = replace(
            state.foundation.selected,
            position=replace(
                state.foundation.selected.position, scene_id=2,
            ),
        )
        self._step(state)
        self.assertIn(
            "combat_scene_edge_resynced_bg0001_to_Bg0002", state.events,
            "the edge either did not fire or did not name the scene it "
            "left and the scene it entered",
        )
        self.assertEqual(state.mob_combat_scene_folder, "Bg0002")

    def test_a_same_scene_frame_does_not_reopen_anything(self):
        # Re-opening resets WOUNDS at epoch 0 by design (the method's own
        # docstring, COO-DECISION 20260829_0848 item 3).  That is correct
        # ACROSS an edge and silent data loss WITHIN one: a detector that
        # re-opened on every frame would heal every monster a walking
        # player had already hit.
        state = self._booted("edge_same_scene")
        identity = state.mob_combat_ledger.identities()[0]
        wounded = state.mob_combat_ledger.balance_of(identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            wounded.__class__(identity, wounded.max_hp, 1)
        )
        ledger = state.mob_combat_ledger
        register = state.mob_ai_register
        for step in range(3):
            self._step(state, xyz=(11.0 + step, 22.0, 33.0))
        self.assertIs(state.mob_combat_ledger, ledger)
        self.assertIs(state.mob_ai_register, register)
        self.assertEqual(
            state.mob_combat_ledger.balance_of(identity).current_hp, 1,
            "a frame that did not change scene re-opened the ledger and "
            "healed a monster the player had already wounded",
        )

    def test_a_refusal_inside_the_sync_does_not_unwind_the_frame(self):
        # v141:7440 has no except: an exception out of dispatch kills the
        # listener thread.  This path now runs on ordinary movement frames,
        # so a refusal here would cost the whole session rather than one
        # attack.  Booted on the home scene, then crossed so the refusing
        # sync is actually reached (a boot at the away scene would have
        # already advanced the edge marker past it).
        state = self._booted("edge_refusal")
        state.foundation.selected = replace(
            state.foundation.selected,
            position=replace(
                state.foundation.selected.position, scene_id=AWAY_SCENE_ID,
            ),
        )

        def boom():
            raise RuntimeError("scene edge refusal under test")

        state._sync_combat_scene_state = boom
        self._step(state)
        self.assertIn(
            "combat_scene_edge_resync_refused_RuntimeError", state.events,
            "the refusal was swallowed without a word in the trail",
        )

    def test_a_register_refusal_leaves_no_torn_pair(self):
        # pf-adversary round pk14rf, finding 1 -- the highest-severity one.
        # _sync_combat_scene_state assigns ledger, register and folder in
        # sequence, and mob_ai_control.open_register can raise by design.
        # An early draft assigned the ledger FIRST, so a raise left the
        # ledger on the NEW scene and the register on the OLD one -- a pair
        # mob_combat.balance_of then rejects as target_not_in_ledger deeper
        # in the same dispatch, OUTSIDE this method's catch and through
        # v141:7558's except-less loop.  The fix builds the register into a
        # local before touching any field.  Booted on bg0001, crossed to
        # Bg0002 (a live roster, so open_register is actually called), with
        # open_register forced to raise.
        state = self._booted("edge_atomic")
        ledger_before = state.mob_combat_ledger
        register_before = state.mob_ai_register
        folder_before = state.mob_combat_scene_folder
        self.assertEqual(folder_before, "bg0001")
        state.foundation.selected = replace(
            state.foundation.selected,
            position=replace(
                state.foundation.selected.position, scene_id=2,
            ),
        )
        import pirateforce_foundation.mob_ai_control as mob_ai_control_mod
        with mock.patch.object(
            mob_ai_control_mod, "open_register",
            side_effect=RuntimeError("register refuses this roster"),
        ):
            self._step(state)  # must NOT raise out of dispatch
        # All three fields are still the departed scene's -- never a ledger
        # from Bg0002 paired with a register from bg0001.
        self.assertIs(state.mob_combat_ledger, ledger_before)
        self.assertIs(state.mob_ai_register, register_before)
        self.assertEqual(state.mob_combat_scene_folder, folder_before)
        self.assertEqual(state.mob_combat_ledger.scene, "bg0001")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
