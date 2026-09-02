"""LANE-A: a kill in scene 2 must not silence the island's clicks.

THE TEST THAT DID NOT EXIST, AND ITS ABSENCE IS THE WHOLE POINT.  On
2026-09-02 this lane shipped a ChooseNPC responder that read a combat
ledger and, on a body the ledger said was dead, refused THE WHOLE CLICK.
Four related test files were green (109 passed) and one of them asserted
that refusal AS DESIRED BEHAVIOUR, because no test in this repository ever
killed a monster in scene 2 and then clicked anybody.  chief did, on the
real dispatcher, and measured that one kill silences every click in the
scene until the player reconnects - ``_sync_combat_scene_state`` pulls the
death back out of ``mob_death_register`` on every re-entry, so leaving the
scene does not clear it (letter ``20260902_1918``).

``COO-DECISION 20260902_1945``: the dead guard judges the CLICKED body
only.  This file drives that with a REAL kill through the REAL dispatcher
rather than a hand-built ledger, and it is deliberately in a file of its
own so the property survives a rewrite of either responder's own suite.

WHY IT CALLS ``respond`` DIRECTLY AFTER THE KILL, AND WHY THAT IS STILL
END TO END.  ~~The ChooseNPC call site in ``runtime.py`` does NOT pass
``mob_combat_ledger`` today - chief withheld that line until this guard
narrowed, which is the whole reason this round exists.~~ CORRECTED ROUND
``qa86im``: chief landed ``mob_combat_ledger=`` at ``runtime.py:8800`` in
``server#619`` (R313, ``COO-DECISION 20260903_0251``), so that half is
production now.  The sentence still holds for the OTHER keyword: the call
site passes no ``mob_death_register=`` yet, so a pure frame round trip
would exercise the ``register=None`` path and prove nothing about the
corpse answer this round added.  The ledger and the register this file
hands the responder are the SESSION's own, after a real ``ACTION_VITAL``
killed a real monster in a real scene-2 arrival; only the arguments chief
has yet to add are supplied by hand.

WHAT ROUND ``qa86im`` ADDED HERE, AND WHY IT IS THE SAME FILE.  ``COO-
DECISION 20260903_0252``: "a corpse must answer with a body instead of
silence".  The refusal this file pinned in round ``4uztfj`` is still the
right answer when nothing can compose a corpse, so both halves are pinned
side by side -- with a register, the click on the dead body is ANSWERED
and carries the corpse; without one, it is refused by name, exactly as
before.
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

from pirateforce_foundation import field_mobs                      # noqa: E402
from pirateforce_foundation import mob_combat                      # noqa: E402
from pirateforce_foundation import mob_combat_membership           # noqa: E402
from pirateforce_foundation import mob_death                       # noqa: E402
from pirateforce_foundation import scene2_prison_exile_tables as tables  # noqa: E402
from pirateforce_foundation import world_scene_travel              # noqa: E402
from pirateforce_foundation.gm.chat_command_action import (        # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.gm.warp_executor import WarpTarget     # noqa: E402
from pirateforce_foundation.gm.warp_target_record import (         # noqa: E402
    current_character_id,
    record_warp_target,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_scene2 as responder_mod,
)
from pirateforce_foundation.legacy_bridge import (                 # noqa: E402
    LegacyProjector,
    load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle    # noqa: E402
from pirateforce_foundation.model import Position                  # noqa: E402
from pirateforce_foundation.runtime import make_state_class        # noqa: E402
from pirateforce_foundation.store import SQLiteStore               # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
PRISON_EXILE = 2
DESTINATION_FOLDER = "Bg0002"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class AKillDoesNotSilenceTheIslandTests(unittest.TestCase):
    """The harness shape is ``tests/test_mob_combat_dispatch_bg0002_kill.py``'s
    (LANE-B's file), reproduced rather than imported: importing another
    lane's test class would make this property die quietly the day that
    file is reorganised, and this one is a production guarantee."""

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
        self.clock_ms = 0

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
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        state.mob_loot_rng = random.Random(1)
        return state

    def _warp(self, state, scene_id):
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
        self._dispatch(
            state, self.legacy._synthetic_client_login_pc(state.token),
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, scene_id,
            "the warp did not move the session's scene",
        )
        self.clock_ms += 1000

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
        state._sync_combat_scene_state()
        row = state.mob_combat_ledger.balance_of(target_identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(target_identity, row.max_hp, 1)
        )
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (target_identity,),
                state.mob_combat_announced_membership_generation,
            )
        )
        self._dispatch(state, self._action_vital_pc(target_identity))
        self.clock_ms += 1000

    def _killed_session(self):
        """A live session standing in scene 2 with one monster really dead."""
        state = self._state("tok_lane_a_click_after_kill")
        self._warp(state, PRISON_EXILE)
        target = self.roster[0].actor_identity
        self._kill(state, target)
        balance = state.mob_combat_ledger.balance_of(target)
        self.assertEqual(
            balance.current_hp, 0,
            "the harness did not actually kill the monster",
        )
        return state, target

    def _hostile_indices(self):
        return responder_mod._hostile_mobs_by_placement_index()

    def _civilian_index(self):
        hostile = self._hostile_indices()
        return next(
            index for index in sorted(
                p.placement_index for p in tables.load_known_placements())
            if index not in hostile
        )

    def _click(self, state, placement_index, with_register=False):
        placement = next(
            p for p in tables.load_known_placements()
            if p.placement_index == placement_index
        )
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=self.legacy,
                chosen_identities=(placement.actor_identity,),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=state.mob_combat_ledger,
                # THE SESSION'S OWN REGISTER, not a hand-built one: the
                # kill above went through the real dispatcher, so this is
                # the object ``runtime.py`` would hand over the day chief
                # adds the keyword -- including the scene tag it wrote
                # itself.
                mob_death_register=(
                    state.mob_death_register if with_register else None),
            )
        return response, err.getvalue()

    def _dead_index(self, target):
        return next(
            index for index, mob in self._hostile_indices().items()
            if mob.actor_identity == target
        )

    def test_a_civilian_still_answers_after_a_real_kill(self) -> None:
        state, _target = self._killed_session()
        response, stderr = self._click(state, self._civilian_index())
        self.assertIsNotNone(
            response,
            "a kill in this scene silenced a click on a civilian - the "
            "state chief measured as indistinguishable from a dead server",
        )
        self.assertIn("dead_at_ceiling=1", response.console_lines[0])
        self.assertIn("dead_as_corpse=0", response.console_lines[0])
        self.assertIn(
            "_DEAD_BODY_AT_CEILING count=1 placements=", stderr)
        self.assertIn("identities=0x", stderr)

    def test_the_whole_island_is_still_in_that_answer(self) -> None:
        state, _target = self._killed_session()
        response, _stderr = self._click(state, self._civilian_index())
        self.assertIn(
            f"visible={len(tables.load_known_placements())}",
            response.console_lines[0],
        )

    def test_clicking_the_dead_body_is_refused_by_its_own_placement(
        self,
    ) -> None:
        """STILL THE ANSWER WITHOUT A REGISTER, and that is the point of
        keeping this test beside the corpse ones below: every boot until
        chief adds the second keyword takes exactly this path."""
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        response, stderr = self._click(state, dead_index)
        self.assertIsNone(response)
        self.assertIn(
            "_IDENTITY_REFUSED reason=clicked_body_is_dead_needs_a_mob_"
            f"death_body placement={dead_index} identity=0x", stderr)

    def test_a_second_click_on_a_civilian_still_answers(self) -> None:
        """The failure chief measured was STICKY: it survived leaving and
        re-entering the scene.  One answer is not enough evidence that it
        is gone; the same session clicking twice is."""
        state, _target = self._killed_session()
        first, _ = self._click(state, self._civilian_index())
        second, _ = self._click(state, self._civilian_index())
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.frame, second.frame)

    # ------------------------------------------------------------------
    # ROUND ``qa86im``: the corpse answers instead of the silence
    # (``COO-DECISION 20260903_0252``).  Same session, same real kill; the
    # only difference is that the register the session already holds is
    # handed over the way chief's next line will hand it.
    # ------------------------------------------------------------------

    def test_the_session_register_really_holds_the_kill(self) -> None:
        """The premise of every test below it, measured not assumed."""
        state, target = self._killed_session()
        mob = self._hostile_indices()[self._dead_index(target)]
        self.assertEqual(mob.scene, DESTINATION_FOLDER)
        self.assertTrue(
            state.mob_death_register.is_dead(target, mob.scene),
            "the real dispatcher did not write this kill to the register",
        )

    def test_clicking_the_dead_body_answers_with_a_corpse(self) -> None:
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        response, stderr = self._click(state, dead_index, with_register=True)
        self.assertIsNotNone(
            response,
            "a click on a corpse is still answered with silence - the "
            "state COO-DECISION 20260903_0252 sent this round to close",
        )
        self.assertEqual(
            response.label,
            f"LANE_A_CHOOSE_NPC_SCENE2_CORPSE_P{dead_index}",
            "a corpse cannot turn to face the player, so the label must "
            "not claim a facing",
        )
        self.assertIn("dead_as_corpse=1", response.console_lines[0])
        self.assertIn("dead_at_ceiling=0", response.console_lines[0])
        self.assertIn("_CLICKED_BODY_IS_A_CORPSE", stderr)
        self.assertNotIn("_IDENTITY_REFUSED", stderr)

    def test_that_frame_carries_the_composers_corpse_and_not_a_ceiling(
        self,
    ) -> None:
        state, target = self._killed_session()
        mob = self._hostile_indices()[self._dead_index(target)]
        response, _stderr = self._click(
            state, self._civilian_index(), with_register=True)
        self.assertIn(
            mob_death.corpse_npc_attr(
                self.legacy, mob,
                death_timer=mob_death.DEAD_TIMER_SECONDS,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE),
            response.frame,
            "the body in the frame is not mob_death's own corpse",
        )
        self.assertNotIn(
            field_mobs.hostile_npc_attr(
                self.legacy, mob, current_hp=mob.max_hp,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE),
            response.frame,
            "the dead monster stood back up at its ceiling in this frame",
        )
        self.assertIn("dead_at_ceiling=0", response.console_lines[0])
        self.assertIn("dead_as_corpse=1", response.console_lines[0])

    def test_the_whole_island_is_still_in_the_corpse_answer(self) -> None:
        """``RE-092``: an omitted row is a DELETED actor.  A corpse answer
        that shipped 96 of 97 would clear somebody off the screen."""
        state, target = self._killed_session()
        response, _stderr = self._click(
            state, self._dead_index(target), with_register=True)
        self.assertIn(
            f"visible={len(tables.load_known_placements())}",
            response.console_lines[0],
        )

    def test_the_corpse_answer_sends_no_movement_for_the_clicked_body(
        self,
    ) -> None:
        """A MovementAttr on a fallen body snaps it back to its roster row
        -- the reason ``mob_death.death_actor_entry`` defaults
        ``with_movement=False``."""
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        placement = next(
            p for p in tables.load_known_placements()
            if p.placement_index == dead_index
        )
        response, _stderr = self._click(
            state, dead_index, with_register=True)
        heading = self.legacy._heading_to_player(
            placement.x, placement.y, 1.0, 2.0)
        self.assertNotIn(
            self.legacy.make_remote_movement_attr(
                placement.actor_identity,
                placement.x, placement.y, placement.z, heading, mask=0x03),
            response.frame,
        )

    def test_a_grave_dug_in_another_scene_cannot_bury_this_body(
        self,
    ) -> None:
        """The register is keyed by ``(scene, identity)`` and this is what
        that key BUYS: scene 2 and scene 14 really do share identities."""
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        mob = self._hostile_indices()[dead_index]
        foreign = mob_death.DeathRegister((
            mob_death.DeathRecord(
                actor_identity=mob.actor_identity,
                killer_identity=mob_death.SANCTIONED_FIRST_TARGET_IDENTITY,
                max_hp=mob.max_hp,
                scene="Bg0015",
            ),
        ), 1)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=self.legacy,
                chosen_identities=(mob.actor_identity,),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=state.mob_combat_ledger,
                mob_death_register=foreign,
            )
        self.assertIsNone(response)
        self.assertIn(
            "clicked_body_is_dead_needs_a_mob_death_body", err.getvalue())

    def test_a_register_that_is_not_a_register_composes_nothing(
        self,
    ) -> None:
        """Fail CLOSED on the type: an object that merely answers
        ``is_dead`` is not a grave this lane may compose a body out of."""
        class _NotARegister:
            def is_dead(self, identity, scene=None):
                return True

        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        mob = self._hostile_indices()[dead_index]
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=self.legacy,
                chosen_identities=(mob.actor_identity,),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=state.mob_combat_ledger,
                mob_death_register=_NotARegister(),
            )
        self.assertIsNone(response)
        self.assertIn(
            "clicked_body_is_dead_needs_a_mob_death_body", err.getvalue())

    def test_a_live_click_is_unchanged_when_a_register_is_passed(
        self,
    ) -> None:
        """The frame a player sees on every OTHER click must not move
        because this keyword arrived."""
        state, _target = self._killed_session()
        without, _ = self._click(state, self._civilian_index())
        with_register, _ = self._click(
            state, self._civilian_index(), with_register=True)
        self.assertNotEqual(
            without.frame, with_register.frame,
            "the corpse changed no byte - the register was not read",
        )
        self.assertEqual(without.label, with_register.label)
        self.assertIn("dead_at_ceiling=1", without.console_lines[0])
        self.assertIn("dead_at_ceiling=0", with_register.console_lines[0])


if __name__ == "__main__":
    unittest.main()
