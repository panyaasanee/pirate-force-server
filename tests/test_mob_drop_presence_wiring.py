"""CORE-REQUEST 2246 (LANE-B m0vp7m, COO-DECISION 2026-08-29T23:42): the
runtime wiring of ``mob_drop_presence.sustain_a_kill``.

``tests/test_mob_drop_presence.py`` proves the module against a bare cell;
nothing in it touches ``runtime.py``.  Before this round the MOB_LOOT block
had NO test pinning its own behaviour at all (lane B's letter measured it:
the announce-then-prune loop shipped with zero coverage, which is how a
dispatch that deleted every row it had just announced stayed green for
rounds).  This file drives the REAL dispatcher through a kill and pins the
three properties the CORE-REQUEST bought:

  1. the call is UNCONDITIONAL -- a kill whose roll dropped nothing still
     reaches ``sustain_a_kill`` (the old ``if drops:`` guard is gone), so
     rows already on the ground are re-announced instead of silently
     omitted (RE-130: an omitted live key is an erased live key);
  2. announcing does NOT consume -- the rows are still in the cell after
     the dispatch that announced them (the old per-key ``take`` loop is
     gone);
  3. both console line and session event fire on the production path
     (WIRED v2: an import alone is not wiring).

The ground is pre-seeded through ``cell.loot_a_kill`` with a Bg0002 mob --
the same fixture shape lane B's module tests use -- because the bg0001
roster's drop tables are genuinely empty (R221: the Port Royal dummies have
``n_DROPS_*=0``), so no scene-1 kill can produce rows.  The KILL that is
driven through the dispatcher is a real scene-1 control-target kill; only
the pre-existing ground is planted.

NOT proven here: any client behaviour.  Wire/headless evidence only (G5).
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

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_drop_presence  # noqa: E402
from pirateforce_foundation import mob_loot  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.mob_death import DeathRecord  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
CONTROL_TARGET = 0x2000 + field_mobs.CONTROL_PLACEMENT_INDEX + 1
CENSUS_ANCHOR = (10.0, 20.0, 30.0)
KILLER = 0x750059


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class DropPresenceWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # One dropping (mob, seed) pair from the scene whose tables actually
        # drop, found by scan rather than hard-coded: a seed pinned to a
        # drop-table edit is a test that goes red for the wrong reason.
        cls.bg0002_roster = field_mobs.load_roster(
            scene=field_mobs.BG0002_SCENE,
        )
        cls.dropping = None
        for mob in cls.bg0002_roster:
            for seed in range(60):
                roll = mob_loot.roll_drops(mob, random.Random(seed))
                if roll.placeable_count:
                    cls.dropping = (mob, seed)
                    break
            if cls.dropping is not None:
                break
        if cls.dropping is None:
            raise unittest.SkipTest("no scene's tables drop anything")

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

    # ----- harness (same frames test_mob_combat_census_wiring.py drives) ----

    def _state(self, token):
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

    def _action_vital_pc(
        self, target_identity, *, action_code=0,
        heading=0.0, x=0.0, y=0.0, z=0.0,
    ):
        legacy = self.legacy
        body = (
            legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, target_identity)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, action_code)
            + legacy.u32tag(0x19, 0)
            + legacy.f32tag(heading) + legacy.f32tag(x)
            + legacy.f32tag(y) + legacy.f32tag(z)
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

    def _drive_arrival_census(self, state, xyz=CENSUS_ANCHOR):
        state.dispatch(self.legacy.parse_outer(self._target_pos_pc(xyz)))
        self.assertIsNotNone(state.population_refresh_anchor)

    def _kill(self, state, target_identity):
        """Drop the target to lethal range and attack it, capturing stdout."""
        row = state.mob_combat_ledger.balance_of(target_identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            type(row)(target_identity, row.max_hp, 500)
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(self.legacy.parse_outer(
                self._action_vital_pc(target_identity)
            ))
        return actions, buf.getvalue()

    def _donor_roll(self, mob):
        """A real Bg0002 roll's ITEMS, re-addressed to ``mob``.

        The bg0001 tables drop nothing (R221), so the only way to get real
        rows standing in the scene this file kills in is to borrow a scene
        that does drop and re-address the roll -- the same substitution
        ``test_the_kills_own_rows_survive_their_own_announcement`` already
        makes, and ``loot_a_kill`` validates the re-addressing itself.
        """
        donor_mob, seed = self.dropping
        donor = mob_loot.roll_drops(donor_mob, random.Random(seed))
        return mob_loot.DropRoll(
            mob.template_id, mob.actor_identity,
            donor.items, donor.money, donor.draws, donor.refusals,
        )

    def _plant_ground(self, state, mob=None):
        """One kill's rows folded into the SESSION's own cell.

        ROUND 4e9r7g: THE PLANTING MOB IS NOW A SCENE-1 MOB, and that is the
        whole edit.  A ``GroundDrop`` owns the scene it fell in (COO-DECISION
        2026-09-02T02:52+07:00 way 1) and a publication carries only the rows
        of the scene it is published in, so a row planted with a Bg0002 mob
        is CORRECTLY absent from a bg0001 kill's generation -- which is what
        this fixture used to do, and what made these tests read as if the
        ground had been lost.  It has not: see
        ``test_a_drop_from_another_scene_neither_travels_nor_disappears``,
        which plants exactly that way ON PURPOSE and proves both halves.
        """
        if mob is None:
            mob = self._planting_mob()
        drops = state.mob_loot_cell.loot_a_kill(
            mob, DeathRecord(mob.actor_identity, KILLER, mob.max_hp),
            self._donor_roll(mob),
            kill_token=999,
        )
        self.assertTrue(drops, "the planted kill must leave rows")
        return drops

    def _planting_mob(self):
        """A scene-1 roster mob that is NOT the control target.

        Not the control target because the looted register keeps one row per
        identity: planting with it would make the driven kill of the same
        identity refuse as a replay, which is a real guard doing its job and
        not something a fixture should have to fight.
        """
        return next(
            mob for mob in field_mobs.load_roster()
            if mob.actor_identity not in (CONTROL_TARGET, KILLER)
        )

    # ----- the three pinned properties --------------------------------------

    def test_a_no_drop_kill_still_reannounces_the_ground(self):
        """Kills the ``if drops:`` guard mutation: the control target's own
        tables are empty, so under the old wiring this dispatch would have
        sent NOTHING about loot -- and the client, on receiving a later
        generation, would have lost the planted rows (RE-130)."""
        state = self._state("dpw_reannounce")
        self._drive_arrival_census(state)
        planted = self._plant_ground(state)
        actions, console = self._kill(state, CONTROL_TARGET)
        loot = [a for a in actions if a[0] == mob_drop_presence.ACTION_LABEL]
        self.assertEqual(
            len(loot), 1,
            "a kill that dropped nothing must still carry the live ground",
        )
        self.assertIn(mob_drop_presence.CONSOLE_TOKEN + " ", console)
        self.assertIn("carried=%d" % len(planted), console)
        self.assertIn("announced=0", console)
        self.assertTrue(any(
            event.startswith("mob_drop_presence_")
            for event in state.events
        ), state.events)

    def test_announcing_does_not_consume_the_rows(self):
        """Kills the prune-loop mutation: after the announcing dispatch the
        planted rows are still in the cell, still inside their lifetime,
        and a pickup can still find them."""
        state = self._state("dpw_rows_survive")
        self._drive_arrival_census(state)
        planted = self._plant_ground(state)
        keys = {drop.drop_key for drop in planted}
        self._kill(state, CONTROL_TARGET)
        live_keys = {
            drop.drop_key for drop in state.mob_loot_cell.ledger.drops
        }
        self.assertEqual(
            keys & live_keys, keys,
            "announcing a row must not remove it from the ledger",
        )

    def test_the_kills_own_rows_survive_their_own_announcement(self):
        """Kills the take-loop mutation the first two tests cannot reach: a
        dispatcher-driven kill whose roll DID drop rows.  No scene-1 table
        drops anything, so the roll is substituted -- the control target's
        own identities over the dropping scene's item rows, which is
        exactly what ``loot_a_kill`` validates -- while everything else
        (dispatch, death schedule, cell, announcement) is the real path.
        Under the old wiring these rows were removed from the ledger in the
        same dispatch that announced them; they must now still be live."""
        from unittest import mock

        state = self._state("dpw_own_rows")
        self._drive_arrival_census(state)
        mob, seed = self.dropping
        donor = mob_loot.roll_drops(mob, random.Random(seed))
        synthetic = mob_loot.DropRoll(
            self._control_template_id(state), CONTROL_TARGET,
            donor.items, donor.money, donor.draws, donor.refusals,
        )
        with mock.patch.object(
            mob_loot, "roll_drops", return_value=synthetic,
        ):
            actions, console = self._kill(state, CONTROL_TARGET)
        loot = [a for a in actions if a[0] == mob_drop_presence.ACTION_LABEL]
        self.assertEqual(len(loot), 1)
        self.assertIn("announced=%d" % len(donor.items), console)
        live = tuple(state.mob_loot_cell.ledger.drops)
        self.assertEqual(
            len(live), len(donor.items),
            "the rows this kill announced must still be in the ledger",
        )

    def _control_template_id(self, state):
        roster = field_mobs.load_roster()
        return next(
            m for m in roster if m.actor_identity == CONTROL_TARGET
        ).template_id

    def test_a_drop_from_another_scene_neither_travels_nor_disappears(self):
        """COO-DECISION 2026-09-02T02:52+07:00 way 1, on the PRODUCTION path.

        The row is planted with a Bg0002 mob -- so it owns Bg0002 -- and the
        kill driven through the dispatcher is a scene-1 kill.  Both halves of
        the decision are measured here, on the real dispatch and not on a
        bare cell:

          1. scene 1's publication carries no key of it (the leak, closed);
          2. it is STILL IN THE LEDGER afterwards, standing where it fell
             (COO-DECISION 2026-09-02T02:53+07:00 -- no row may be removed
             until a removal publisher exists).  The superseded
             ``reconcile_scene_transition`` would have failed half 2.
        """
        state = self._state("dpw_cross_scene")
        self._drive_arrival_census(state)
        elsewhere_mob, _seed = self.dropping
        planted = self._plant_ground(state, mob=elsewhere_mob)
        planted_keys = {drop.drop_key for drop in planted}
        for drop in planted:
            self.assertEqual(drop.scene, field_mobs.BG0002_SCENE)

        actions, console = self._kill(state, CONTROL_TARGET)

        # 1. nothing about that ground travels in this scene's publication.
        loot = [a for a in actions if a[0] == mob_drop_presence.ACTION_LABEL]
        self.assertEqual(loot, [], "a Bg0002 row must not ride a bg0001 kill")
        self.assertIn("live=0", console)
        self.assertIn("elsewhere=%d" % len(planted), console)

        # 2. and it is still on the ground, whole.
        live = {drop.drop_key for drop in state.mob_loot_cell.ledger.drops}
        self.assertEqual(planted_keys & live, planted_keys)
        self.assertEqual(
            {drop.scene for drop in state.mob_loot_cell.ledger.drops},
            {field_mobs.BG0002_SCENE})

    def test_an_empty_ground_stays_quiet_but_the_call_still_fires(self):
        """No planted rows, a no-drop kill: no MOB_LOOT_DROP action goes out
        (an empty generation has nothing to protect), but the presence line
        and event still record that the path ran -- the WIRED-v2 emission."""
        state = self._state("dpw_empty")
        self._drive_arrival_census(state)
        actions, console = self._kill(state, CONTROL_TARGET)
        loot = [a for a in actions if a[0] == mob_drop_presence.ACTION_LABEL]
        self.assertEqual(loot, [])
        self.assertIn(mob_drop_presence.CONSOLE_TOKEN + " ", console)
        self.assertTrue(any(
            event.startswith("mob_drop_presence_")
            for event in state.events
        ), state.events)


if __name__ == "__main__":
    unittest.main()
