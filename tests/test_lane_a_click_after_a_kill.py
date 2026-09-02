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
END TO END.  The ChooseNPC call site in ``runtime.py`` does NOT pass
``mob_combat_ledger`` today - chief withheld that line until this guard
narrowed, which is the whole reason this round exists.  So a pure frame
round trip would exercise the ``ledger=None`` path and prove nothing about
the guard.  The ledger this file hands the responder is the SESSION's own,
after a real ``ACTION_VITAL`` killed a real monster in a real scene-2
arrival; only the one argument chief will add is supplied by hand.
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

    def _click(self, state, placement_index):
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
            )
        return response, err.getvalue()

    def test_a_civilian_still_answers_after_a_real_kill(self) -> None:
        state, _target = self._killed_session()
        response, stderr = self._click(state, self._civilian_index())
        self.assertIsNotNone(
            response,
            "a kill in this scene silenced a click on a civilian - the "
            "state chief measured as indistinguishable from a dead server",
        )
        self.assertIn("dead_at_ceiling=1", response.console_lines[0])
        self.assertIn("_DEAD_BODY_AT_CEILING placement=", stderr)

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
        state, target = self._killed_session()
        dead_index = next(
            index for index, mob in self._hostile_indices().items()
            if mob.actor_identity == target
        )
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


if __name__ == "__main__":
    unittest.main()
