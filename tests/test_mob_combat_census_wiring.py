"""CORE-REQUEST-008 -- combat/death frames compose the FULL census, not one entry.

``tests/test_mob_combat_dispatch.py`` proves the combat/death wiring in
isolation: every test there attacks BEFORE any arrival census has run, so
``population_refresh_anchor``/``world_census_actor_count`` are unset and the
three call sites this file exercises take the fallback branch (the old
one-entry ``step.bar_pc``/``death_step.dying_pc``/``death_step.dead_pc``
frames).  ``tests/test_world_census_wiring.py`` proves the arrival census
itself reflects a wound or a kill on its NEXT compose -- it never inspects
the hit/death frames combat sends in the SAME response.

Neither file drives the sequence a real session actually produces (arrival
census, THEN combat) through the three sites CORE-REQUEST-008 wires, so
neither would have caught the bug this round closes: on that sequence, the
combat/death frames used to carry a bare one-entry ``RuntimeRes`` collection
that RE-092 proved the client's remote-actor consumer treats as
replace-by-omission -- every OTHER actor already on the client's registry
would vanish on the first hit or kill, not just refresh one monster's bar.

This file drives arrival-census-then-combat through the real dispatcher and
proves the three sites (``MOB_COMBAT_BAR``, ``MOB_DEATH_DYING``,
``MOB_DEATH_DEAD``) now carry the full recomposed census (matching an
independent ``mob_death.hostile_census_frames`` call byte for byte) instead
of the one-entry frame, AND that the one-entry fallback still fires -- named
by its own event, not silently -- on the pre-arrival sequence the other two
files already cover.

Also proves the two gaps pf-adversary found in the first version of this
wiring (round keen-pasteur-ahn7zb), both fixed in the same round these tests
ship in:

  * a ``hostile_census_frames`` call that raises (roster/ledger/register
    disagreement, or anything else) degrades to the one-entry frame and
    names itself with a ``*_compose_refused_<ExceptionType>`` event, instead
    of propagating out of ``dispatch()`` and killing the listener thread the
    way the arrival census's own equivalent failure is already guarded
    against 90 lines above this wiring;
  * a hit/kill that lands while the player is away from the home scene
    (``population_refresh_anchor``/``world_census_actor_count`` describing a
    DIFFERENT scene than the one combat is happening in -- these two
    attributes are never invalidated together) takes the same one-entry
    fallback instead of shipping a mismatched-scene census.

NOT proven here: whether a real client renders any of this.  Same
client-observable gap GT-084/RIDER-084-A already track for the arrival
census fix -- this is wire/DB evidence only.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# ~~CONTROL_TARGET = mob_death.SANCTIONED_FIRST_TARGET_IDENTITY  # 0x201F,
# P30~~  ROUND 8ftmbx: that placement is withdrawn from what this lane ships
# (COO-DECISION 2026-08-29T00:41+07:00, RE-128 crosswalk: it is a townsman).
# The identity these wiring tests drive is the roster's own control row.
CONTROL_TARGET = 0x2000 + field_mobs.CONTROL_PLACEMENT_INDEX + 1
CENSUS_ANCHOR = (10.0, 20.0, 30.0)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class MobCombatCensusWiringTests(unittest.TestCase):
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
        self.roster = field_mobs.load_roster()
        self.control_mob = next(
            m for m in self.roster if m.actor_identity == CONTROL_TARGET
        )

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness -----------------------------------------------------

    def _state(self, token, **kwargs):
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

    def _drive_arrival_census(self, state, xyz=CENSUS_ANCHOR):
        """Send the same TargetPos frame test_world_census_wiring.py uses to
        arm the arrival census, so this state's population_refresh_anchor /
        world_census_actor_count are set exactly the way a real session sets
        them before combat can ever reach a field mob.
        """
        state.dispatch(self.legacy.parse_outer(self._target_pos_pc(xyz)))
        self.assertIsNotNone(state.population_refresh_anchor)
        self.assertIsNotNone(state.world_census_actor_count)

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

    def _attack(self, state, target_identity, **kwargs):
        return state.dispatch(self.legacy.parse_outer(
            self._action_vital_pc(target_identity, **kwargs)
        ))

    def _set_balance(self, state, identity, current_hp):
        row = state.mob_combat_ledger.balance_of(identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, current_hp)
        )

    # ----- MOB_COMBAT_BAR carries the full census after arrival ------------

    def test_bar_frame_after_arrival_census_is_the_full_recompose_not_one_entry(
        self,
    ):
        state = self._state("cw_bar")
        self._drive_arrival_census(state)
        actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        bar_pc, bar_frame, _delay = (
            actions[1][1], actions[1][2], actions[1][3],
        )
        self.assertNotIn(
            "mob_combat_bar_census_compose_skipped_no_population_anchor",
            state.events,
        )
        expected_pc, expected_frame = mob_death.hostile_census_frames(
            self.legacy, state.population_refresh_anchor,
            state.world_census_actor_count, self.roster,
            state.mob_death_register, ledger=state.mob_combat_ledger,
        )
        self.assertEqual(bar_pc, expected_pc)
        self.assertEqual(bar_frame, expected_frame)
        self.assertEqual(bar_frame, self.legacy.frame_pc(bar_pc))
        # The one-entry frame this used to send is a strict PREFIX of neither
        # -- proves the compose actually changed shape, not just that the two
        # happen to line up by coincidence.
        self.assertNotEqual(bar_pc, actions[0][1])  # not reusing announce_pc
        # Another roster member's identity that never took part in this hit
        # is still present on the wire -- the world-wipe RE-092 flagged would
        # have dropped it.
        other = next(
            m for m in self.roster if m.actor_identity != CONTROL_TARGET
        )
        other_entry = field_mobs.hostile_actor_entry(
            self.legacy, other, current_hp=other.max_hp,
        )
        self.assertIn(other_entry, bar_pc)

    # ----- MOB_DEATH_DYING / MOB_DEATH_DEAD carry the full census too ------

    def test_death_frames_after_arrival_census_are_the_full_recompose(self):
        state = self._state("cw_death")
        self._drive_arrival_census(state)
        self._set_balance(state, CONTROL_TARGET, 500)
        actions = self._attack(state, CONTROL_TARGET)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        self.assertTrue(all(label == "MOB_LOOT_DROP" for label in labels[3:]))
        self.assertNotIn(
            "mob_death_frames_census_compose_skipped_no_population_anchor",
            state.events,
        )
        dying_pc, dying_frame = actions[1][1], actions[1][2]
        dead_pc, dead_frame = actions[2][1], actions[2][2]
        expected_dying_pc, expected_dying_frame = mob_death.hostile_census_frames(
            self.legacy, state.population_refresh_anchor,
            state.world_census_actor_count, self.roster,
            state.mob_death_register, ledger=state.mob_combat_ledger,
            dead_timer=mob_death.DYING_TIMER_SECONDS,
        )
        expected_dead_pc, expected_dead_frame = mob_death.hostile_census_frames(
            self.legacy, state.population_refresh_anchor,
            state.world_census_actor_count, self.roster,
            state.mob_death_register, ledger=state.mob_combat_ledger,
        )
        self.assertEqual(dying_pc, expected_dying_pc)
        self.assertEqual(dying_frame, expected_dying_frame)
        self.assertEqual(dead_pc, expected_dead_pc)
        self.assertEqual(dead_frame, expected_dead_frame)
        self.assertNotEqual(dying_pc, dead_pc)
        # A living roster member (not the sanctioned target) is still on the
        # wire in both frames -- the world-wipe risk RE-092 flagged would
        # have removed it.
        other = next(
            m for m in self.roster if m.actor_identity != CONTROL_TARGET
        )
        other_entry = field_mobs.hostile_actor_entry(
            self.legacy, other, current_hp=other.max_hp,
        )
        self.assertIn(other_entry, dying_pc)
        self.assertIn(other_entry, dead_pc)

    # ----- pre-arrival: the one-entry fallback still fires, and is named ---

    def test_bar_frame_before_any_census_falls_back_to_the_one_entry_frame(
        self,
    ):
        """Same sequence tests/test_mob_combat_dispatch.py's tests use
        (attack with no arrival census ever driven) -- proves the fallback
        this round adds is not merely inert but actually taken, and named by
        its own event rather than silently degrading.
        """
        state = self._state("cw_bar_fallback")
        self.assertIsNone(getattr(state, "population_refresh_anchor", None))
        actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertIn(
            "mob_combat_bar_census_compose_skipped_no_population_anchor",
            state.events,
        )

    def test_death_frames_before_any_census_fall_back_to_one_entry_frames(
        self,
    ):
        state = self._state("cw_death_fallback")
        self.assertIsNone(getattr(state, "population_refresh_anchor", None))
        self._set_balance(state, CONTROL_TARGET, 500)
        actions = self._attack(state, CONTROL_TARGET)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        self.assertIn(
            "mob_death_frames_census_compose_skipped_no_population_anchor",
            state.events,
        )

    # ----- pf-adversary finding 1: a compose failure is fail-closed, not fatal

    def test_bar_frame_compose_failure_falls_back_and_is_named(self):
        """pf-adversary (round keen-pasteur-ahn7zb): the first version of
        this wiring called ``hostile_census_frames`` with no guard at all --
        any exception (roster/ledger/register disagreement, or anything
        else the builder can raise) would propagate out of ``dispatch()``
        and, per the arrival census's own documented reasoning for the
        SAME kind of call, kill the listener thread. This proves the fix:
        a raising compose degrades to the one-entry frame instead.
        """
        state = self._state("cw_bar_refused")
        self._drive_arrival_census(state)
        with mock.patch.object(
            mob_death, "hostile_census_frames",
            side_effect=ValueError("test-induced compose failure"),
        ):
            actions = self._attack(state, CONTROL_TARGET)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        bar_pc, bar_frame = actions[1][1], actions[1][2]
        self.assertEqual(bar_frame, self.legacy.frame_pc(bar_pc))
        self.assertIn(
            "mob_combat_bar_census_compose_refused_ValueError",
            state.events,
        )

    def test_death_frames_compose_failure_falls_back_and_is_named(self):
        state = self._state("cw_death_refused")
        self._drive_arrival_census(state)
        self._set_balance(state, CONTROL_TARGET, 500)
        with mock.patch.object(
            mob_death, "hostile_census_frames",
            side_effect=ValueError("test-induced compose failure"),
        ):
            actions = self._attack(state, CONTROL_TARGET)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        self.assertIn(
            "mob_death_frames_census_compose_refused_ValueError",
            state.events,
        )

    # ----- pf-adversary finding 2: an away-from-home-scene anchor is not trusted

    def test_bar_frame_outside_home_scene_falls_back_to_one_entry(self):
        """pf-adversary (round keen-pasteur-ahn7zb): population_refresh_
        anchor/world_census_actor_count are set once at arrival and never
        invalidated on scene departure, so nothing stopped a stale
        home-scene anchor from being recomposed and sent to a client that
        has since left that scene. This proves the added scene guard: once
        ``foundation.selected.position.scene_id`` no longer matches the
        scene the anchor/count describe, the wiring falls back to the
        one-entry frame instead of trusting a mismatched pair.

        UPDATED round ytkgdh (COO-DECISION 2026-08-29T08:48+07:00 item 3):
        the first version stood the character in scene 999 and still hit a
        bg0001 mob, because the combat roster ignored the scene entirely --
        the exact wall that decision closed.  An unaddressed scene now
        refuses combat by name before any frame composes (pinned in
        tests/test_scene_scoped_combat_wiring.py), so the ONLY way a hit
        can land away from the home scene is in a scene with its own live
        roster.  Same guard, proven where it is still reachable: the
        scene-1 arrival anchor must not be recomposed into a Bg0002 hit's
        bar frame.
        """
        state = self._state("cw_bar_wrong_scene")
        self._drive_arrival_census(state)
        state.foundation.selected = replace(
            state.foundation.selected,
            position=replace(
                state.foundation.selected.position, scene_id=2,
            ),
        )
        bg0002_target = field_mobs.load_roster(
            field_mobs.BG0002_SCENE
        )[0].actor_identity
        actions = self._attack(state, bg0002_target)
        self.assertEqual(
            [
                label for label, _pc, _f, _d in actions
                if not label.startswith("WORLD_CENSUS_")
            ],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        self.assertIn(
            "mob_combat_bar_census_compose_skipped_no_population_anchor",
            state.events,
        )
        self.assertNotIn(
            "mob_combat_bar_census_compose_refused_ValueError",
            state.events,
        )


if __name__ == "__main__":
    unittest.main()
