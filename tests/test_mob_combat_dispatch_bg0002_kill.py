"""LANE-B: a kill that ACTUALLY DROPS, driven end to end on the real
dispatcher, in the scene whose roster can drop at all.

WHY THIS FILE EXISTS (COO-DECISION 2026-09-02T14:47+07:00, pf_bridge
notes_to_chief/20260902_1447_COO-DECISION-lane-b-next-round-bg0002-kill-
harness-*.md, answering chief's open item four 1 of 20260902_1345):

    "no test in the repo composes a NON-EMPTY scene-boundary generation
     through a real scene crossing, because the bg0001 roster cannot drop
     anything at all (4 rows x 30 seeds = 0) -- so the four order pins in
     tests/test_mob_combat_dispatch.py are HOLLOW today"

``tests/test_mob_combat_dispatch.py`` says the same thing about itself, in
its own words, at ``test_the_kill_burst_frame_by_frame_and_the_frame_that_
ends_it``: "forty consecutive kills in this exact harness composed ZERO
MOB_LOOT_DROP frames ... the ordering claim stays [PROPOSED] until a kill
that drops is driven end to end."  This file is that drive.

WHAT IS MEASURED HERE, on a flagless boot with no scenario of any kind:

  * a killing blow on a Bg0002 roster row composes FOUR actions, and the
    last one is a real ``MOB_LOOT_DROP`` carrying a real row -- the item id
    the roll produced, standing at the identity that fell, tagged with the
    scene it fell in;
  * the kill's generation is the WHOLE live floor (MOB_LOOT_WIRING shape
    4b): a second kill over a floor that already holds one row publishes a
    generation of THREE rows, not of the two the second kill rolled;
  * and therefore -- this is the whole point -- a scene-boundary generation
    behind it would roll the client's floor back to before the newest kill.
    ``test_the_boundary_generation_lands_before_the_kill_across_a_real_
    crossing`` drives a real leave-and-return, gets a NON-EMPTY boundary
    generation out of it (frames_1, the row left by the first kill), and
    pins that it lands ahead of the kill's, which is ``MOB_LOOT_WIRING``
    step 6's rule.  chief's PR #572 shipped that order INVERTED for one
    commit (his own letter 20260902_1345 item one); #575 fixed it; nothing
    in the repo could catch it going backwards again through a real
    crossing, because no crossing ever had a row to carry.  Now one does.

WHAT IS NOT MEASURED HERE, and no line of this file may be read as it:
NOBODY HAS SEEN ANY OF THIS ON A SCREEN.  Whether a client draws a ground
generation at all, whether it draws one delivered at a scene boundary, and
what a re-announcement does to an already-drawn label (NONCLAIM 12) are all
open.  ``GT-204`` is the measurement point on the screen and this file does
not stand in for it.  Wire/DB layer only.

MUTATION-PROOF ON PURPOSE.  Move the boundary flush back to the end of the
dispatch sum and ``test_the_boundary_generation_lands_before_the_kill_
across_a_real_crossing`` fails on the index order.  Drop the drop frame from
the kill burst and ``test_a_bg0002_kill_composes_a_real_drop_frame_last``
fails on a three-action burst.  Make the kill publish only its own rows
instead of the live floor and ``test_the_kills_generation_carries_the_whole_
floor_not_just_this_kills_rows`` fails on ``live_2``.
"""
from __future__ import annotations

import contextlib
import io
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mob_tables                # noqa: E402
from pirateforce_foundation import field_mobs                      # noqa: E402
from pirateforce_foundation import mob_combat                      # noqa: E402
from pirateforce_foundation import mob_combat_membership           # noqa: E402
from pirateforce_foundation import mob_drop_presence               # noqa: E402
from pirateforce_foundation import mob_loot                        # noqa: E402
from pirateforce_foundation import world_scene_travel              # noqa: E402
from pirateforce_foundation.gm.chat_command_action import (        # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.gm.warp_executor import WarpTarget     # noqa: E402
from pirateforce_foundation.gm.warp_target_record import (         # noqa: E402
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

#: The scene the drop table can actually pay out in.  ``Bg0002`` is
#: addressed by scene id 2 (``world_scene_folder``), and every one of its
#: twelve rows rolls an item on ~77% of seeds -- re-derived, not assumed, by
#: :meth:`RosterDropRatesTests.test_bg0001_cannot_drop_and_bg0002_can`.
DESTINATION_SCENE_ID = 2
DESTINATION_FOLDER = "Bg0002"

#: A seed measured to pay out on both of the two rows this file kills.  If a
#: table edit ever moves the roll, the drop assertions fail loudly rather
#: than quietly measuring nothing -- which is exactly the failure mode that
#: made the pins in ``test_mob_combat_dispatch.py`` hollow for four days.
DROP_SEED = 1

#: How many seeds the roster-rate re-derivation spends per row.  chief's
#: measurement used 30 for bg0001; kept identical so the two numbers are
#: comparable.
SEEDS_PER_ROW = 30


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class RosterDropRatesTests(unittest.TestCase):
    """The fact this whole file rests on, re-derived here rather than cited.

    Pure table work: no dispatcher, no store, no legacy image.
    """

    def test_bg0001_cannot_drop_and_bg0002_can(self):
        bg0001_hits = sum(
            1
            for mob in field_mobs.load_roster(field_mob_tables.SCENE)
            for seed in range(SEEDS_PER_ROW)
            if _rolls_something(mob, seed)
        )
        self.assertEqual(
            bg0001_hits, 0,
            "bg0001 now drops something -- the pins in "
            "tests/test_mob_combat_dispatch.py are no longer hollow and the "
            "reason this file exists has changed; say so in a round file "
            "before editing this number",
        )
        bg0002 = field_mobs.load_roster(DESTINATION_FOLDER)
        self.assertTrue(bg0002, "the Bg0002 roster is empty")
        for mob in bg0002:
            with self.subTest(placement=mob.placement_index):
                self.assertTrue(
                    _rolls_something(mob, DROP_SEED),
                    "placement %d stopped dropping on the seed this file "
                    "kills with" % mob.placement_index,
                )


def _rolls_something(mob, seed):
    roll = mob_loot.roll_drops(mob, random.Random(seed))
    return bool(roll.items or roll.money)


class Bg0002KillDispatchTests(unittest.TestCase):

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
        self.roster = field_mobs.load_roster(DESTINATION_FOLDER)
        self.first_target = self.roster[0].actor_identity
        self.second_target = self.roster[1].actor_identity
        # An injected clock, for one reason only: two kills in one test are
        # 600 ms apart in ATTACK_CADENCE_MS_PROVISIONAL terms and a test
        # must not sleep.  It gates nothing (production passes the real
        # monotonic clock through the same argument).
        self.clock_ms = 0

    # ----- harness -------------------------------------------------------

    def _clock(self):
        return self.clock_ms / 1000.0

    def _dispatch(self, state, pc):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return state.dispatch(self.legacy.parse_outer(pc))

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            monotonic_clock=self._clock,
        )
        state = state_type(token)
        self._dispatch(state, self.legacy._synthetic_client_login_pc(token))
        self._dispatch(state, self.legacy._V25_REAL_CREATE_PC)
        character = self.store.list_characters(state.foundation.account_id)[-1]
        self._dispatch(
            state, self.legacy._synthetic_start_game_pc(character.selector),
        )
        # Same pre-arming as tests/test_mob_combat_dispatch.py: the one-time
        # bootstrap frames are not what this file measures and every one of
        # them is unconditional.
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        # The roll is the one thing in this loop that is random in
        # production.  Seeded here so a drop is a fact of the test rather
        # than a coin toss; the rate itself is re-derived by
        # RosterDropRatesTests above.
        state.mob_loot_rng = random.Random(DROP_SEED)
        return state

    def _warp(self, state, scene_id):
        """One cross-scene GM warp through the production arming path.

        The same seam ``tests/test_mob_loot_scene_boundary_wiring.py`` uses:
        park a ``WarpTarget``, then let dispatch's own
        ``_gm_warp_note_position_pending`` -> ``_gm_warp_resync_selected_
        scene`` run, which is what calls ``_mob_loot_cross_scene_boundary``.
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
        actions = self._dispatch(
            state, self.legacy._synthetic_client_login_pc(state.token),
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, scene_id,
            "the warp did not move the session's scene",
        )
        self.clock_ms += 1000
        return actions

    def _action_vital_pc(self, target_identity):
        legacy = self.legacy
        body = (
            legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, target_identity)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, 0)
            + legacy.u32tag(0x19, 0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.u8tag(0x0B, 0)
            + legacy.u16tag(0x12, 0)
            + legacy.u8tag(0x0B, 0)
        )
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.ACTION_VITAL)
            + legacy.u8tag(0x0B, 0)
            + body
        )

    def _kill(self, state, target_identity):
        """Put ``target_identity`` on 1 HP and land one blow on it.

        ``_sync_combat_scene_state`` is called here for the same reason
        ``_dispatch_mob_combat`` calls it as its own first step: after a
        crossing the ledger still belongs to the scene the session left, and
        a balance written into that ledger would be thrown away by the
        rebuild.  Calling it changes nothing else -- it is idempotent once
        the folder matches, which is exactly the state the dispatch below
        finds it in.
        """
        state._sync_combat_scene_state()
        row = state.mob_combat_ledger.balance_of(target_identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(target_identity, row.max_hp, 1)
        )
        # The announced-census membership guard, seeded directly (same note
        # as tests/test_mob_combat_dispatch.py: this file isolates the kill
        # from census composition, which test_mob_combat_census_wiring.py
        # owns).
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (target_identity,),
                state.mob_combat_announced_membership_generation,
            )
        )
        actions = self._dispatch(state, self._action_vital_pc(target_identity))
        self.clock_ms += 1000
        return actions

    @staticmethod
    def _labels(actions):
        return [label for label, *_rest in actions]

    @staticmethod
    def _ground(actions):
        return [a for a in actions if a[0] == mob_drop_presence.ACTION_LABEL]

    # ----- the kill that drops -------------------------------------------

    def test_a_bg0002_kill_composes_a_real_drop_frame_last(self):
        """The pin ``test_mob_combat_dispatch.py`` could not make.

        [MEASURED HERE] the burst of a killing blow in Bg0002 is FOUR
        actions -- announce (0.0), dying (0.0), dead (0.7), drop (0.0) --
        and the drop frame really is the last of them, with a row behind it.
        The adjacency the other file could only read off a queue delay is a
        fact of the returned list here.
        """
        state = self._state("bg2-kill-drops")
        self._warp(state, DESTINATION_SCENE_ID)
        actions = self._kill(state, self.first_target)

        self.assertEqual(
            self._labels(actions)[-4:],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD",
             mob_drop_presence.ACTION_LABEL],
            "the kill burst is not [announce, dying, dead, drop]: %r"
            % (self._labels(actions),),
        )
        self.assertEqual([delay for *_r, delay in actions][-4:],
                         [0.0, 0.0, 0.7, 0.0])
        drop = self._ground(actions)
        self.assertEqual(len(drop), 1, self._labels(actions))
        self.assertTrue(drop[0][1], "the drop frame carries no bytes")

        # And the row behind it is this kill's, in the scene it fell in.
        rows = state.mob_loot_cell.ledger.drops
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0].mob_identity, self.first_target)
        self.assertEqual(rows[0].scene, DESTINATION_FOLDER)
        self.assertIn("mob_drop_presence_sustained_live_1", state.events)

    def test_the_kills_generation_carries_the_whole_floor_not_just_this_kills_rows(self):
        """MOB_LOOT_WIRING shape 4b, measured instead of quoted -- and the
        reason step 6's ordering rule is not a preference.

        [MEASURED HERE] the second kill rolls TWO rows onto a floor that
        already holds ONE, and the generation it publishes says live=3.  A
        generation that carries the whole floor is a generation that
        OVERWRITES the whole floor on the client, which is why anything
        published behind it erases the player's newest drop.
        """
        state = self._state("bg2-whole-floor")
        self._warp(state, DESTINATION_SCENE_ID)
        self._kill(state, self.first_target)
        self.assertIn("mob_drop_presence_sustained_live_1", state.events)

        second = self._kill(state, self.second_target)
        self.assertEqual(
            [row.mob_identity for row in state.mob_loot_cell.ledger.drops],
            [self.first_target, self.second_target, self.second_target],
        )
        self.assertIn("mob_drop_presence_sustained_live_3", state.events)
        self.assertNotIn(
            "mob_drop_presence_sustained_live_2", state.events,
            "the second kill published only its own rows -- the floor the "
            "player already earned is not in the generation",
        )
        self.assertEqual(len(self._ground(second)), 1)

    # ----- step 6, across a real crossing ---------------------------------

    def test_the_boundary_generation_lands_before_the_kill_across_a_real_crossing(self):
        """chief's open item four 1, closed by measurement.

        Kill in Bg0002 -> warp out to bg0001 -> warp back.  The return
        crossing now composes a NON-EMPTY boundary generation (the row the
        first kill left standing), and the first dispatch after arrival both
        flushes it and kills again.

        [MEASURED HERE] the order of that dispatch is
        ``[... census, MOB_LOOT_DROP(boundary), MOB_COMBAT_ANNOUNCE,
        MOB_DEATH_DYING, MOB_DEATH_DEAD, MOB_LOOT_DROP(the kill)]``.  The
        boundary bytes are the ones stashed at the crossing, byte for byte,
        and they land AHEAD of the kill -- MOB_LOOT_WIRING step 6.  Inverted
        (the shape #572 shipped for one commit), the older, smaller
        generation would be the last word on the floor and the two rows this
        kill just paid out would vanish from the client.
        """
        state = self._state("bg2-boundary-before-kill")
        self._warp(state, DESTINATION_SCENE_ID)
        self._kill(state, self.first_target)

        self._warp(state, 1)
        self._warp(state, DESTINATION_SCENE_ID)
        # The crossing really did compose something this time -- this is the
        # sentence that was untrue of every other test in the repo.
        self.assertIn(
            "mob_loot_boundary_entered_%s_frames_1" % DESTINATION_FOLDER,
            state.events,
            "the return crossing composed an EMPTY generation, so this test "
            "measures nothing: %r"
            % ([e for e in state.events if "mob_loot_boundary" in e],),
        )
        stashed = state.mob_loot_boundary_frames_pending
        self.assertEqual(len(stashed), 1)
        self.assertEqual(
            state.mob_loot_boundary_frames_scene,
            mob_loot.scene_key(DESTINATION_FOLDER),
        )

        actions = self._kill(state, self.second_target)
        labels = self._labels(actions)
        ground_at = [
            index for index, label in enumerate(labels)
            if label == mob_drop_presence.ACTION_LABEL
        ]
        self.assertEqual(
            len(ground_at), 2,
            "expected the boundary generation and the kill's: %r" % (labels,),
        )
        boundary_index, kill_index = ground_at
        self.assertLess(
            boundary_index, labels.index("MOB_DEATH_DEAD"),
            "the boundary generation landed behind the kill -- step 6 "
            "inverted, and the player's newest drop is the one it erases: %r"
            % (labels,),
        )
        self.assertEqual(kill_index, len(labels) - 1, labels)
        self.assertIn("mob_loot_boundary_flushed_frames_1", state.events)

        # The frame that landed IS the stash, not a recomposition of it.
        self.assertEqual(actions[boundary_index][1], stashed[0][0])
        self.assertEqual(actions[boundary_index][2], stashed[0][1])
        # And it is the smaller, older word about the floor: one row against
        # the three the kill behind it publishes.  (Byte length, stated as
        # what it is -- neither generation is decoded here.)
        self.assertLess(
            len(actions[boundary_index][1]), len(actions[kill_index][1]),
        )
        self.assertIn("mob_drop_presence_sustained_live_3", state.events)


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
