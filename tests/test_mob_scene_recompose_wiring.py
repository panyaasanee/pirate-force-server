"""CORE-REQUEST (LANE-B 20260829_2055) -- the chief's wiring, proven.

LANE-B shipped ``mob_scene_recompose`` (round ``y9s0xo``): a SCENE-DISPATCHED
recompose composer that delegates scene 1 byte-identically to the live
``diag_multi_object_wiring.hostile_census_frames`` path and adds scene 2
(Bg0002).  This file proves the runtime.py half:

  * the arrival census commit STAMPS ``census_anchor_record`` with the scene
    it was measured in -- both the bg0001 branch and the bg0002 branch;
  * a hit in Bg0002 after its arrival census now sends the FULL recomposed
    census as its MOB_COMBAT_BAR frame, not the one-entry frame RE-092
    proved is replace-by-omission;
  * a kill in Bg0002 sends full-census MOB_DEATH_DYING / MOB_DEATH_DEAD
    frames the same way;
  * the module's own MOB_SCENE_RECOMPOSE console line prints on the compose
    path (the lane's wiring ask, point 3).

The scene-1 path is NOT re-proven here: tests/test_mob_combat_census_wiring
.py already pins its bytes and its fallback arms, and every event name that
file greps for is unchanged by this wiring.

Mutation kills this file was written against (each measured by reverting the
wiring by hand before the round's push):

  * drop the bg0002 arrival stamp -> the scene-2 bar test reddens on
    ``..._skipped_no_population_anchor``;
  * restore the old ``== world_population.SCENE_ID`` guard -> same red;
  * send ``step.bar_pc`` instead of the recomposed frame -> the byte
    comparison and the other-actor-still-present assertions redden.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import diag_multi_object_wiring  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_diag_multi_object  # noqa: E402
from pirateforce_foundation import mob_scene_recompose  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENE2_N_ID = world_population_bg0002.SCENE2_N_ID


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class MobSceneRecomposeWiringTests(unittest.TestCase):
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
        self.bg0002_roster = field_mobs.load_roster(field_mobs.BG0002_SCENE)
        self.bg0002_mob = self.bg0002_roster[0]

    # ----- harness (the shape test_scene_scoped_combat_wiring.py uses) ----

    def _login_and_create(self, token):
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

    def _state_scene1(self, token):
        state, character = self._login_and_create(token)
        self._start_game(state, character)
        return state

    def _state_at_scene2(self, token):
        """A real stored character row whose scene_id is 2 -- the same
        ``store.save_position`` route test_bg0002_census_wiring.py uses,
        because nothing in this tree seeds a scene-2 row on a real boot."""
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

    def _arrive(self, state):
        """The real arrival TargetPos, production order (login -> StartGame
        -> TargetPos -> census)."""
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
        with contextlib.redirect_stdout(io.StringIO()):
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
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(self.legacy.parse_outer(
                self._action_vital_pc(target_identity)
            ))
        return actions, buf.getvalue()

    def _set_balance(self, state, identity, current_hp):
        row = state.mob_combat_ledger.balance_of(identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, current_hp)
        )

    def _combat_labels(self, actions):
        return [
            label for label, _pc, _f, _d in actions
            if not label.startswith("WORLD_CENSUS_")
        ]

    # ----- the arrival stamp, both branches -------------------------------

    def test_the_scene1_arrival_census_stamps_its_own_scene(self):
        state = self._state_scene1("rw_stamp1")
        self.assertIsNone(getattr(state, "census_anchor_record", None))
        self._arrive(state)
        record = state.census_anchor_record
        self.assertIsInstance(record, mob_scene_recompose.CensusAnchor)
        self.assertEqual(world_population.SCENE_ID, record.scene_id)
        self.assertEqual(state.world_census_actor_count, record.actor_count)
        self.assertEqual(state.population_refresh_anchor, record.anchor)

    def test_the_scene2_arrival_census_stamps_its_own_scene(self):
        """THE POINT OF THE ROUND: before this wiring, a Bg0002 arrival
        deliberately left ``population_refresh_anchor`` unset (its comment
        reserves those attributes for bg0001 click-dispatch semantics), so
        the recompose sites had nothing to compose over and every hit fell
        to the one-entry frame.  The stamped record is bg0002's way in
        WITHOUT touching the bg0001-reserved attributes."""
        state = self._state_at_scene2("rw_stamp2")
        self.assertIsNone(getattr(state, "census_anchor_record", None))
        self._arrive(state)
        record = state.census_anchor_record
        self.assertIsInstance(record, mob_scene_recompose.CensusAnchor)
        self.assertEqual(SCENE2_N_ID, record.scene_id)
        # The bg0001-reserved attributes stay untouched, per the bg0002
        # branch's own standing comment.
        self.assertIsNone(getattr(state, "population_refresh_anchor", None))

    # ----- scene 2: the bar frame is the full recompose -------------------

    def test_scene2_bar_frame_after_arrival_is_the_full_recompose(self):
        state = self._state_at_scene2("rw_bar2")
        self._arrive(state)
        target = self.bg0002_mob.actor_identity
        actions, console = self._attack(state, target)
        labels = self._combat_labels(actions)
        self.assertEqual(labels, ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"])
        self.assertNotIn(
            "mob_combat_bar_census_compose_skipped_no_population_anchor",
            state.events,
        )
        bar = [a for a in actions if a[0] == "MOB_COMBAT_BAR"][0]
        bar_pc, bar_frame = bar[1], bar[2]
        # The same compose the call site ran, through the same public
        # function, over the same session state.
        expected = mob_scene_recompose.recompose_frames(
            self.legacy, state.census_anchor_record,
            state.mob_death_register,
            ledger=state.mob_combat_ledger,
            roster=self.bg0002_roster,
        )
        self.assertTrue(expected.composed, expected.state)
        self.assertEqual(expected.pc, bar_pc)
        self.assertEqual(expected.frame, bar_frame)
        self.assertEqual(bar_frame, self.legacy.frame_pc(bar_pc))
        # The whole POPULATION is on the wire (97 actors, the lane's own
        # measured number -- mobs and populace both), not the one hit
        # actor: the world-wipe RE-092 flagged would have shipped exactly
        # 1.  The count is read back off the composed bytes' own header
        # (``wire_actor_count``), not asserted from a roster.
        self.assertEqual(expected.actor_count, expected.wire_actor_count)
        self.assertGreater(expected.wire_actor_count, len(self.bg0002_roster))
        # The module's own console line printed on the compose path (the
        # lane's wiring ask, point 3).
        self.assertIn(mob_scene_recompose.CONSOLE_TOKEN, console)
        self.assertIn("state=composed", console)

    # ----- scene 2: the death frames are the full recompose ---------------

    def test_scene2_death_frames_after_arrival_are_the_full_recompose(self):
        state = self._state_at_scene2("rw_death2")
        self._arrive(state)
        target = self.bg0002_mob.actor_identity
        self._set_balance(state, target, 1)
        actions, console = self._attack(state, target)
        labels = self._combat_labels(actions)
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        self.assertNotIn(
            "mob_death_frames_census_compose_skipped_no_population_anchor",
            state.events,
        )
        dying = [a for a in actions if a[0] == "MOB_DEATH_DYING"][0]
        dead = [a for a in actions if a[0] == "MOB_DEATH_DEAD"][0]
        expected_dying = mob_scene_recompose.recompose_frames(
            self.legacy, state.census_anchor_record,
            state.mob_death_register,
            ledger=state.mob_combat_ledger,
            roster=self.bg0002_roster,
            dead_timer=mob_death.DYING_TIMER_SECONDS,
        )
        expected_dead = mob_scene_recompose.recompose_frames(
            self.legacy, state.census_anchor_record,
            state.mob_death_register,
            ledger=state.mob_combat_ledger,
            roster=self.bg0002_roster,
        )
        self.assertTrue(expected_dying.composed, expected_dying.state)
        self.assertTrue(expected_dead.composed, expected_dead.state)
        self.assertEqual(expected_dying.pc, dying[1])
        self.assertEqual(expected_dying.frame, dying[2])
        self.assertEqual(expected_dead.pc, dead[1])
        self.assertEqual(expected_dead.frame, dead[2])
        # Two separate composes, two console lines.
        self.assertGreaterEqual(
            console.count(mob_scene_recompose.CONSOLE_TOKEN), 2, console,
        )


    # ----- pf-adversary (round k882hm) D5: mutants the suite let live ----

    def test_scene1_bar_recompose_carries_the_diagnostic_objects(self):
        """M6: ``objects=(...)`` -> ``objects=()`` survived the whole suite.

        Nothing pinned the scene-1-with-diag-objects bytes, so deleting the
        five diagnostic bodies from the bar recompose stayed green while a
        diag session's bar frame silently lost them.  This is that pin: the
        frame the dispatch queues equals the compose done WITH the session's
        objects, and differs from the one done without.

        The session's ``diag_multi_objects`` is set directly rather than
        through a config file: this tree ships no
        ``config/diag_multi_object.json``, and what is under test is the
        call site's argument, not the activation path (which
        tests/test_diag_multi_object_wiring.py owns).
        """
        state = self._state_scene1("rw_objects")
        self._arrive(state)
        objects = mob_diag_multi_object.diagnostic_objects()
        state.diag_multi_objects = objects
        roster, ledger, _note = diag_multi_object_wiring.widen_for_combat(
            field_mobs.roster_for_scene_id(world_population.SCENE_ID),
            state.mob_combat_ledger, objects,
        )
        state.mob_combat_ledger = ledger
        target = objects[0].mob.actor_identity
        # RE-157 job 2: ``_arrive`` composed the real arrival census (and
        # its real announced-actor membership) BEFORE ``diag_multi_objects``
        # was assigned directly above, bypassing the activation path that
        # would normally widen that same census -- so the diag identity
        # this test attacks was never actually announced.  Widen the
        # membership by hand to match, the same union runtime.py's own
        # census-compose site performs when diag objects are active.
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                frozenset(state.mob_combat_announced_membership.actor_identities)
                | {target},
                state.mob_combat_announced_membership_generation,
            )
        )
        actions, _console = self._attack(state, target)
        bar = [a for a in actions if a[0] == "MOB_COMBAT_BAR"]
        self.assertEqual(1, len(bar), self._combat_labels(actions))
        with_objects = mob_scene_recompose.recompose_frames(
            self.legacy, state.census_anchor_record,
            state.mob_death_register,
            ledger=state.mob_combat_ledger, roster=roster,
            objects=objects,
        )
        without_objects = mob_scene_recompose.recompose_frames(
            self.legacy, state.census_anchor_record,
            state.mob_death_register,
            ledger=state.mob_combat_ledger, roster=roster,
        )
        self.assertTrue(with_objects.composed, with_objects.state)
        self.assertTrue(without_objects.composed, without_objects.state)
        # The two are genuinely different collections -- otherwise this
        # test would pass with the objects dropped.
        self.assertNotEqual(without_objects.pc, with_objects.pc)
        self.assertEqual(with_objects.pc, bar[0][1])
        self.assertEqual(with_objects.frame, bar[0][2])

    def test_a_death_where_only_one_compose_succeeds_degrades_both(self):
        """M8: the all-or-nothing guard (``and`` -> ``or``) survived.

        No test reached a state where one compose succeeds and the other
        refuses -- the existing refusal tests patch so BOTH fail -- so the
        invariant this file's call site argues for ("a dying frame from one
        collection and a dead frame from another must never interleave")
        was unproven.  With ``or`` in place of ``and``, the mutant assigns
        ``dying_pc = None`` into the action tuple on a mixed state.

        The mixed state is built the only way it can be: patch the module
        function the call site uses so the FIRST call composes and the
        SECOND refuses.
        """
        state = self._state_at_scene2("rw_mixed")
        self._arrive(state)
        target = self.bg0002_mob.actor_identity
        self._set_balance(state, target, 1)

        real = mob_scene_recompose.recompose_frames
        calls = {"n": 0}

        def _first_composes_then_refuses(*args, **kwargs):
            calls["n"] += 1
            record = real(*args, **kwargs)
            if calls["n"] == 1:
                return record
            return mob_scene_recompose.SceneRecompose(
                record.scene_id, record.scene,
                mob_scene_recompose.STATE_REFUSED_PREFIX + "ValueError",
                detail="test-induced second-compose refusal",
            )

        from pirateforce_foundation import runtime as runtime_module
        with mock.patch.object(
            runtime_module.mob_scene_recompose, "recompose_frames",
            side_effect=_first_composes_then_refuses,
        ):
            actions, _console = self._attack(state, target)

        labels = self._combat_labels(actions)
        self.assertEqual(
            labels[:3],
            ["MOB_COMBAT_ANNOUNCE", "MOB_DEATH_DYING", "MOB_DEATH_DEAD"],
        )
        dying = [a for a in actions if a[0] == "MOB_DEATH_DYING"][0]
        dead = [a for a in actions if a[0] == "MOB_DEATH_DEAD"][0]
        # Both pairs fall back together: real bytes, never a None pc, and
        # never one recomposed frame beside one one-entry frame.
        for pc, frame in ((dying[1], dying[2]), (dead[1], dead[2])):
            self.assertIsInstance(pc, bytes)
            self.assertIsInstance(frame, bytes)
            self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertIn(
            "mob_death_frames_census_compose_refused_ValueError",
            state.events,
        )

    def test_a_kill_outside_the_stamped_scene_falls_back_at_the_death_site(
        self,
    ):
        """M10: dropping the scene check in the DEATH guard survived.

        The bar site had a test for it (test_mob_combat_census_wiring.py);
        the death site did not, so the death guard could trust a stamp from
        another scene and recompose the previous map into this one.

        RE-157 job 2 ADDENDUM (MOB-COMBAT-001 announced-actor guard): the
        same scene-1-stamp-while-standing-in-scene-2 mismatch this test
        drives is now caught ONE GATE EARLIER, by
        ``mob_combat_membership.admits()``, before ``attack_from_observed_
        action`` ever runs -- see the identical addendum on
        ``test_mob_combat_census_wiring.py::
        test_bar_frame_outside_home_scene_falls_back_to_one_entry``.  No
        hit lands at all now, so there is no death frame (composed OR
        one-entry-fallback) to observe; the ledger is untouched.
        """
        state = self._state_scene1("rw_death_wrong_scene")
        self._arrive(state)
        self.assertEqual(
            world_population.SCENE_ID, state.census_anchor_record.scene_id,
        )
        # Stand the character in scene 2 while the stamp still describes
        # scene 1, then attempt to kill a scene-2 mob.
        state.foundation.selected = dataclasses.replace(
            state.foundation.selected,
            position=dataclasses.replace(
                state.foundation.selected.position, scene_id=SCENE2_N_ID,
            ),
        )
        target = self.bg0002_mob.actor_identity
        state._sync_combat_scene_state()
        self._set_balance(state, target, 1)
        before_ledger_generation = state.mob_combat_ledger.generation
        actions, _console = self._attack(state, target)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_announced_no_reply",
            state.events,
        )
        self.assertEqual(
            state.mob_combat_ledger.generation, before_ledger_generation,
        )

    def test_every_non_composed_state_keeps_a_greppable_prefix(self):
        """D6: an event outside ``_refused_``/``_skipped_`` is a false green.

        tests/test_mob_combat_dispatch.py asserts that no event starts with
        either prefix, so a bare ``no_composer_for_scene`` would pass that
        assertion while the one-entry world-wipe frame goes out.  This pins
        the mapping at the source.
        """
        from pirateforce_foundation import runtime as runtime_module
        cases = {
            mob_scene_recompose.STATE_NO_LEDGER: "refused_no_ledger",
            mob_scene_recompose.STATE_NO_COMPOSER:
                "skipped_no_composer_for_scene",
            mob_scene_recompose.STATE_REFUSED_PREFIX + "ValueError":
                "refused_ValueError",
            mob_scene_recompose.STATE_REFUSED_PREFIX
            + "objects_outside_scene_1":
                "refused_objects_outside_scene_1",
        }
        for state_name, expected in cases.items():
            record = mob_scene_recompose.SceneRecompose(
                1, "bg0001", state_name,
            )
            suffix = runtime_module._recompose_event_suffix(record)
            self.assertEqual(expected, suffix)
            self.assertTrue(
                suffix.startswith("refused_")
                or suffix.startswith("skipped_"),
                suffix,
            )


if __name__ == "__main__":
    unittest.main()
