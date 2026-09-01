"""LANE-B's two library fixes, wired into runtime.py and driven end to end.

CORE-REQUEST (LANE-B letter 20260901_2255), approved by COO-DECISION
2026-09-01T21:48+07:00, answering CODEX_URGENT 2026-09-01T20:40+07:00 P0-5.
The library halves already shipped and are pinned by their own modules' tests;
what nothing pinned until this file is the CALL SITE, which lives in
``runtime.py`` and which no lane but the chief may write:

  (1) ``transitioning=(scene, actor_identity)`` on BOTH census recomposes of
      the death path.  Without it, ``dead_timer`` is one scalar applied to
      every dead row the census carries -- so composing THIS kill's DYING
      frame (20s) re-armed every OTHER already-dead corpse's timer and stood
      its death animation back up.  The one-corpse limit was never a client
      limit; it was this argument being absent.

  (2) ``mob_loot.DropLedgerCell.reconcile_scene_transition()`` at the scene
      boundary in ``_sync_combat_scene_state``.  ``DropLedger`` has no scene
      term and every kill re-announces the whole live ledger, so a drop left
      standing in the scene the player just left rode along into the next
      scene's first kill publication.

Everything below is driven through the REAL dispatcher (login -> StartGame ->
TargetPos -> ActionVital), not by asserting that a keyword was passed: the
timers are read out of the composed census bytes, and the ground is read out
of the session's own live drop cell.

NOT PROVEN HERE, unchanged from every other file in this family: whether a
real attack input produces this exact ActionVital shape, and whether a real
client draws anything for these frames.  Scene arrival is synthesized the same
two ways ``tests/test_scene_scoped_combat_wiring.py`` synthesizes it, and for
the same reason -- what is under test is the DISPATCH's answer, not any travel
lane.

NONCLAIM carried forward from ``mob_loot.reconcile_scene_transition``: clearing
the WHOLE ledger at a boundary is the conservative side of an authenticity
question CODEX_URGENT itself leaves OPEN, not a claim about what the original
server did with a drop when a player walked away from it.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_loot  # noqa: E402
from pirateforce_foundation import mob_scene_recompose  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENE2_N_ID = world_population_bg0002.SCENE2_N_ID
CONTROL_TARGET = 0x2000 + field_mobs.CONTROL_PLACEMENT_INDEX + 1
RECONCILE_EVENT_PREFIX = "mob_loot_scene_reconcile_cleared_"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _seed_that_drops(mob):
    """The first ``random.Random`` seed whose FIRST roll drops something.

    The runtime calls ``mob_loot.roll_drops(mob, self.mob_loot_rng)`` exactly
    once per kill, so seeding the session's own generator with this value
    reproduces this roll byte for byte.  Searched rather than hardcoded: a
    literal seed is a number this file would be asserting about the drop
    tables, and the tables are the client's, not ours.
    """
    for seed in range(500):
        roll = mob_loot.roll_drops(mob, random.Random(seed))
        if roll.items or roll.money:
            return seed
    raise AssertionError(
        "no seed in 500 makes mob 0x%X drop anything: the fixture this file "
        "needs (a drop actually standing on the ground) cannot be built"
        % mob.actor_identity
    )


class CorpseRearmAndDropSceneReconcileTests(unittest.TestCase):
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
        self.bg0001_roster = field_mobs.load_roster()
        self.bg0002_roster = field_mobs.load_roster(field_mobs.BG0002_SCENE)

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness (same shape as test_scene_scoped_combat_wiring.py) -----

    def _login_and_create(self, token):
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
        return state, character

    def _start_game(self, state, character):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return buf.getvalue()

    def _state(self, token):
        state, character = self._login_and_create(token)
        self._start_game(state, character)
        return state

    def _state_at_scene2(self, token):
        state, character = self._login_and_create(token)
        destination = world_scene_travel.destination(SCENE2_N_ID)
        spawn = world_scene_travel.spawn_position(destination)
        self.store.select_character(
            state.foundation.session_id, character.selector,
        )
        self.store.save_position(
            state.foundation.session_id, character.id,
            Position(SCENE2_N_ID, 0, spawn[0], spawn[1], spawn[2], 0.0),
        )
        self._start_game(state, character)
        return state

    def _move_to_scene(self, state, scene_id):
        selected = state.foundation.selected
        state.foundation.selected = dataclasses.replace(
            selected,
            position=dataclasses.replace(
                selected.position, scene_id=scene_id,
            ),
        )

    def _arrive(self, state):
        """The real arrival TargetPos, which is what commits the census
        anchor the death recompose reads.  Without it the death path takes
        its no_population_anchor fallback and composes nothing."""
        anchor = (
            state.foundation.selected.position.x,
            state.foundation.selected.position.y,
            state.foundation.selected.position.z,
        )
        legacy = self.legacy
        pc = (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + b"".join(legacy.f32tag(v) for v in (*anchor, 0.0))
            + legacy.u8tag(0x0B, 0)
            + legacy.u8tag(0x0B, 0)
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(legacy.parse_outer(pc))
        return anchor

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

    def _attack(self, state, target_identity):
        # RE-157 job 2 harness note, copied from tests/test_mob_combat_
        # dispatch.py: seed the announced-actor membership the mob_combat_
        # membership guard requires for whatever scene the character
        # CURRENTLY stands in.  Read fresh on every call so a mid-test scene
        # move is followed.
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (target_identity,),
                state.mob_combat_announced_membership_generation,
            )
        )
        # Two swings in one test run faster than the real attack cadence
        # allows; the timing gate is owned by
        # tests/test_mob_combat_cadence_wiring.py and is not what this file
        # measures.
        state.mob_combat_cadence = mob_combat.open_cadence_ledger()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(self.legacy.parse_outer(
                self._action_vital_pc(target_identity)
            ))
        return actions

    def _set_balance(self, state, identity, current_hp):
        row = state.mob_combat_ledger.balance_of(identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, current_hp)
        )

    def _kill(self, state, identity):
        """One killing blow, driven through dispatch.  Returns the actions."""
        self._set_balance(state, identity, 1)
        actions = self._attack(state, identity)
        labels = [label for label, *_rest in actions]
        self.assertIn(
            "MOB_DEATH_DEAD", labels,
            "fixture failure: identity 0x%X did not die (%r)" % (
                identity, labels),
        )
        return actions

    @staticmethod
    def _pc_for(actions, label):
        return next(pc for lbl, pc, *_rest in actions if lbl == label)

    def _reconcile_events(self, state):
        return [
            event for event in state.events
            if event.startswith(RECONCILE_EVENT_PREFIX)
        ]

    # ----- (1) the corpse re-arm ------------------------------------------

    def test_a_second_death_does_not_rearm_the_first_corpses_timer(self):
        """Two corpses, one scene, one composed census -- driven for real.

        Kill mob A, then kill mob B.  B's DYING recompose composes the WHOLE
        census at ``dead_timer=DYING_TIMER_SECONDS`` (20s).  Before the
        ``transitioning=`` wiring, A's corpse entry in those very bytes
        carried that 20s timer too: the client re-entered A's dying state and
        played its death animation again, which is the "only one corpse at a
        time" behaviour CODEX_URGENT P0-5 reported.  A must now be at
        ``DEAD_TIMER_SECONDS`` -- its steady state -- while B, the row this
        transition is actually about, still gets the 20s.

        Read out of the composed bytes, not out of a call record.

        MUTATION-PROOF (measured): drop ``transitioning=`` from the
        ``recompose_dying`` call in runtime.py and the "A holds the floor"
        assertion goes red on the re-armed entry.
        """
        state = self._state("rearm_two_corpses")
        self._arrive(state)
        first, second = self.bg0001_roster[0], self.bg0001_roster[1]
        self.assertNotEqual(first.actor_identity, second.actor_identity)

        self._kill(state, first.actor_identity)
        actions = self._kill(state, second.actor_identity)

        self.assertTrue(
            state.mob_death_register.is_dead(first.actor_identity),
            "fixture failure: the first corpse left the register",
        )
        self.assertFalse(
            [e for e in state.events if "census_compose" in e],
            "fixture failure: the death path fell back to the one-entry "
            "frames, so no full census was composed to read timers out of: "
            "%r" % (state.events,),
        )

        dying_pc = self._pc_for(actions, "MOB_DEATH_DYING")
        dead_pc = self._pc_for(actions, "MOB_DEATH_DEAD")
        first_at_floor = mob_death.death_actor_entry(
            self.legacy, first, death_timer=mob_death.DEAD_TIMER_SECONDS,
        )
        first_rearmed = mob_death.death_actor_entry(
            self.legacy, first, death_timer=mob_death.DYING_TIMER_SECONDS,
        )
        second_dying = mob_death.death_actor_entry(
            self.legacy, second, death_timer=mob_death.DYING_TIMER_SECONDS,
        )
        second_dead = mob_death.death_actor_entry(
            self.legacy, second, death_timer=mob_death.DEAD_TIMER_SECONDS,
        )

        # THE FIX: the already-dead corpse holds its floor in BOTH frames.
        self.assertIn(first_at_floor, dying_pc)
        self.assertNotIn(first_rearmed, dying_pc)
        self.assertIn(first_at_floor, dead_pc)
        self.assertNotIn(first_rearmed, dead_pc)
        # AND the row this transition IS about still moves, or the "fix"
        # would just be a census that never animates anything.
        self.assertIn(second_dying, dying_pc)
        self.assertIn(second_dead, dead_pc)

    def test_a_lone_death_is_unchanged_by_the_transitioning_argument(self):
        """The single-corpse path, byte for byte as it shipped.

        ``transitioning`` is documented as a no-op when at most one row is
        dead ("apply to everyone" and "apply to the one row named" already
        agree), and this is the regression that would catch it if the wiring
        had named the wrong row: the FIRST kill of a session must still put
        its own dying body, at the 20s timer, in its own dying census.
        """
        state = self._state("rearm_one_corpse")
        self._arrive(state)
        only = self.bg0001_roster[0]
        actions = self._kill(state, only.actor_identity)
        dying_pc = self._pc_for(actions, "MOB_DEATH_DYING")
        dead_pc = self._pc_for(actions, "MOB_DEATH_DEAD")
        self.assertIn(
            mob_death.death_actor_entry(
                self.legacy, only,
                death_timer=mob_death.DYING_TIMER_SECONDS,
            ),
            dying_pc,
        )
        self.assertIn(
            mob_death.death_actor_entry(
                self.legacy, only, death_timer=mob_death.DEAD_TIMER_SECONDS,
            ),
            dead_pc,
        )
        self.assertFalse(
            [e for e in state.events if "census_compose" in e], state.events,
        )

    def test_the_death_path_never_refuses_on_the_transitioning_row(self):
        """``REFUSE_TRANSITIONING_NOT_A_DEAD_ROW`` cannot fire from here.

        ``mob_death`` refuses a ``transitioning`` value that is not BOTH dead
        in the register AND a member of the roster the call received.  At this
        call site the pair is taken from ``death_step.record``, which
        ``mob_death.kill`` built out of the roster row the dispatch resolved
        and which ``commit_death`` has already accepted -- so the refusal is
        structurally unreachable on the normal path.  Proven rather than
        argued: a full kill sequence in each of the two composable scenes,
        with no refusal of any kind in the event log.
        """
        home = self._state("transitioning_home")
        self._arrive(home)
        self._kill(home, self.bg0001_roster[0].actor_identity)
        self._kill(home, self.bg0001_roster[1].actor_identity)

        away = self._state_at_scene2("transitioning_away")
        self._arrive(away)
        self._kill(away, self.bg0002_roster[0].actor_identity)
        self._kill(away, self.bg0002_roster[1].actor_identity)

        for state in (home, away):
            self.assertFalse(
                [
                    event for event in state.events
                    if mob_death.REFUSE_TRANSITIONING_NOT_A_DEAD_ROW in event
                    or "census_compose" in event
                ],
                state.events,
            )

    def test_both_recomposes_name_the_row_not_only_the_dying_one(self):
        """The one assertion in this file that is NOT byte-observable, and
        it is here for a reason that is written down rather than hidden.

        The DEAD recompose composes at ``dead_timer=DEAD_TIMER_SECONDS``,
        which is exactly the floor every OTHER corpse is held at -- so
        "apply the scalar to everyone" and "apply it to the one row named"
        produce byte-identical census frames on that call today, and
        deleting ``transitioning=`` from it alone changes nothing a test can
        read off the wire (measured: the whole file stays green).  It is
        still wrong to leave off: the moment ``dead_timer`` on that call ever
        stops being the floor, the re-arm bug is back on the DEAD frame with
        no test to catch it.  So this pins the ARGUMENT, at the real dispatch,
        and says plainly that it is a structural pin and not evidence about
        bytes.
        """
        state = self._state("rearm_both_calls")
        self._arrive(state)
        self._kill(state, self.bg0001_roster[0].actor_identity)

        seen = []
        real = mob_scene_recompose.recompose_frames

        def recording(*args, **kwargs):
            seen.append(kwargs.get("transitioning"))
            return real(*args, **kwargs)

        second = self.bg0001_roster[1]
        with mock.patch.object(
            mob_scene_recompose, "recompose_frames", recording,
        ):
            self._kill(state, second.actor_identity)

        self.assertEqual(
            seen, [(second.scene, second.actor_identity)] * 2,
            "both the dying and the dead recompose must name the row this "
            "transition is about",
        )

    # ----- (2) the ground at a scene boundary ------------------------------

    def _kill_with_a_drop(self, state, mob):
        """Kill ``mob`` through dispatch with the session's own RNG seeded so
        the roll actually drops something.  Returns the live ground rows."""
        state.mob_loot_rng = random.Random(_seed_that_drops(mob))
        self._kill(state, mob.actor_identity)
        drops = state.mob_loot_cell.ledger.drops
        self.assertTrue(
            drops,
            "fixture failure: the seeded roll left nothing on the ground, so "
            "there is no drop for a scene change to clear",
        )
        return drops

    def test_a_drop_left_in_one_scene_is_gone_after_a_scene_change(self):
        """P-1's half of this round: the ground does not follow the player.

        Kill a Bg0002 mob so a real drop stands on the ground there, then walk
        to bg0001 and swing.  The scene sync clears the cell ONCE, says how
        many rows it took, and the next kill in the new scene publishes an
        empty ground instead of re-announcing the other scene's loot.

        MUTATION-PROOF (measured): remove the
        ``reconcile_scene_transition()`` call from
        ``_sync_combat_scene_state`` and the emptied-ledger assertion goes
        red with the Bg0002 drop still standing.
        """
        state = self._state_at_scene2("drop_scene_change")
        self._arrive(state)
        victim = self.bg0002_roster[0]
        drops = self._kill_with_a_drop(state, victim)
        before = len(self._reconcile_events(state))

        self._move_to_scene(state, 1)
        self._attack(state, CONTROL_TARGET)

        self.assertEqual(state.mob_combat_scene_folder, "bg0001")
        self.assertEqual(
            state.mob_loot_cell.ledger.drops, (),
            "a drop from the scene the player left is still on the ground",
        )
        new_events = self._reconcile_events(state)[before:]
        self.assertEqual(
            new_events, [RECONCILE_EVENT_PREFIX + str(len(drops))],
            "the boundary must reconcile exactly once and say how many rows "
            "it cleared: %r" % (state.events,),
        )

    def test_the_cleared_ground_does_not_reappear_in_the_new_scenes_kill(
        self,
    ):
        """The player-visible half: what the NEXT kill actually publishes.

        Every kill re-announces the whole live ledger (shape 4b), which is
        exactly why an un-reconciled cell leaked: the first kill in the new
        scene would have re-sent the old scene's drop keys.  bg0001's mobs
        carry no drop tables, so the first kill after the walk home publishes
        an empty ground -- and that is the observable difference.
        """
        state = self._state_at_scene2("drop_no_reappear")
        self._arrive(state)
        stale = self._kill_with_a_drop(state, self.bg0002_roster[0])
        stale_keys = tuple(drop.drop_key for drop in stale)

        self._move_to_scene(state, 1)
        # The combat ledger is re-opened lazily, at attack time: this first
        # ordinary swing is what crosses the boundary and syncs bg0001's rows
        # in.  The kill that publishes the ground comes after it.
        self._attack(state, CONTROL_TARGET)
        actions = self._kill(state, CONTROL_TARGET)

        self.assertEqual(state.mob_loot_cell.ledger.drops, ())
        for _label, pc, *_rest in actions:
            for key in stale_keys:
                self.assertNotIn(
                    self.legacy.u32tag(mob_loot.ELEMENT_KEY_TAG, key), pc,
                    "the new scene's kill re-announced drop key 0x%X from "
                    "the scene the player left" % key,
                )

    def test_an_in_scene_dispatch_does_not_reconcile_the_ground(self):
        """The other half, and the one a careless wiring gets wrong: a swing
        in the SAME scene must leave the ground alone.

        The reconcile lives inside ``if folder != self.mob_combat_scene_
        folder:``.  Hoisted one level out, it would fire on every ActionVital
        and delete a drop the player was walking towards -- so this drives a
        second, in-scene attack and pins BOTH the untouched ground and the
        absent event.
        """
        state = self._state_at_scene2("drop_same_scene")
        self._arrive(state)
        drops = self._kill_with_a_drop(state, self.bg0002_roster[0])
        before = len(self._reconcile_events(state))
        folder_before = state.mob_combat_scene_folder

        # A second, ordinary swing in the same scene at a different mob.
        self._attack(state, self.bg0002_roster[1].actor_identity)

        self.assertEqual(state.mob_combat_scene_folder, folder_before)
        self.assertEqual(len(self._reconcile_events(state)), before)
        self.assertEqual(state.mob_loot_cell.ledger.drops, drops)


if __name__ == "__main__":
    unittest.main()
