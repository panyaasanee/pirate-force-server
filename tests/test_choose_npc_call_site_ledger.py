"""LANE-E: the ChooseNPC call site hands the responder the SESSION's ledger.

WHAT THIS PINS AND WHY IT IS A SEPARATE FILE.  ``runtime.py``'s ChooseNPC
dispatch spent five rounds passing no ``mob_combat_ledger=`` at all, because
the scene-2 responder's dead branch used to refuse the WHOLE click and one
kill silenced the scene (chief's letter ``20260902_1918``).
``COO-DECISION 20260903_0251`` lifted that hold after ``#606`` narrowed the
refusal to the clicked identity, and this file is the guard that the keyword
is actually AT THE CALL SITE -- not merely accepted by a responder someone
calls by hand.

``tests/test_lane_a_click_after_a_kill.py`` (lane A's) proves the responder
behaves when a ledger is handed to it; it says so in its own docstring, and
it hands the ledger over by hand precisely because the call site did not.
This file removes that hand: every frame here goes through
``state.dispatch``, so if the keyword is deleted from ``runtime.py`` the
responder sees ``None``, composes at the table ceiling, and the
``dead_at_ceiling=1`` assertion below goes red.  Nothing else in the
repository would notice.

THE HARNESS SHAPE is reproduced from ``test_lane_a_click_after_a_kill.py``
rather than imported, for the reason that file gives for reproducing
LANE-B's: importing another lane's test class makes a production guarantee
die quietly the day that file is reorganised.
"""
from __future__ import annotations

import contextlib
import inspect
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
from pirateforce_foundation import lane_hooks                   # noqa: E402
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


class TheCallSiteHandsOverTheSessionLedgerTests(unittest.TestCase):

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

    # ---- harness ----------------------------------------------------

    def _clock(self):
        return self.clock_ms / 1000.0

    def _dispatch(self, state, pc):
        """Dispatch one frame, returning the actions AND the console."""
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            actions = state.dispatch(self.legacy.parse_outer(pc))
        return actions, out.getvalue() + err.getvalue()

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
        return spawn

    def _target_pos_pc(self, xyz):
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + b"".join(legacy.f32tag(value) for value in (*xyz, 0.0))
            + legacy.u8tag(0x0B, 0)
            + legacy.u8tag(0x0B, 0)
        )

    def _choose_npc_pc(self, actor_identity):
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.CHOOSE_NPC)
            + legacy.u8tag(0x0B, 0)
            + legacy.qwordtag(0x32, actor_identity)
        )

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

    def _killed_session_standing_in_scene_2(self):
        """A live session in scene 2, one monster really dead, and the
        player's position known -- the responder declines without it."""
        state = self._state("tok_call_site_ledger")
        spawn = self._warp(state, PRISON_EXILE)
        target = self.roster[0].actor_identity
        self._kill(state, target)
        self._dispatch(state, self._target_pos_pc(spawn))
        self.assertIsNotNone(
            state.last_target_pos,
            "the harness never gave the session a player position",
        )
        self.assertEqual(
            state.mob_combat_ledger.balance_of(target).current_hp, 0,
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
        return self._dispatch(
            state, self._choose_npc_pc(placement.actor_identity))

    def _answered_tokens(self, console):
        """The ANSWERED line as a set of whole tokens.

        NOT ``assertIn("dead_at_ceiling=1", console)``: pf-adversary D3
        measured that a responder miscounting the corpse debt by 12x prints
        ``dead_at_ceiling=12``, which CONTAINS that substring, and the whole
        lane stays green (38 passed).  A count is pinned by its whole token
        or it is not pinned.
        """
        line = next(
            (line for line in console.splitlines()
             if f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_ANSWERED" in line),
            None,
        )
        self.assertIsNotNone(line, console)
        return set(line.split())

    def _wound(self, state, target_identity, damage):
        """Take HP off a live monster in the session's own ledger."""
        state._sync_combat_scene_state()
        row = state.mob_combat_ledger.balance_of(target_identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(
                target_identity, max(0, row.max_hp - damage), 1)
        )
        return row.max_hp

    # ---- the pins ---------------------------------------------------

    def test_a_click_after_a_kill_still_puts_bytes_on_the_wire(self) -> None:
        state, _target = self._killed_session_standing_in_scene_2()
        index = self._civilian_index()
        actions, _console = self._click(state, index)
        answers = [
            action for action in actions
            if action[0] == (
                f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_FACE_P{index}")
        ]
        self.assertEqual(len(answers), 1, actions)
        self.assertTrue(answers[0][1], "the answer carried no pc bytes")
        self.assertTrue(answers[0][2], "the answer carried no frame bytes")

    def test_the_answer_proves_the_session_ledger_reached_the_responder(
        self,
    ) -> None:
        """``dead_at_ceiling=`` counts corpses the responder had to compose
        at the table ceiling, and it can only be non-zero if a ledger that
        KNOWS ABOUT THE KILL arrived.  Delete ``mob_combat_ledger=`` from
        the call site and this reads ``dead_at_ceiling=0``: the whole point
        of the round, in one token."""
        state, _target = self._killed_session_standing_in_scene_2()
        _actions, console = self._click(state, self._civilian_index())
        tokens = self._answered_tokens(console)
        self.assertIn("dead_at_ceiling=1", tokens)
        self.assertIn("hp=ledger", tokens)

    def test_the_corpse_is_refused_by_name_and_not_by_silence(self) -> None:
        """The behaviour ``COO-DECISION 20260903_0251`` accepted as the
        remaining cost: a click on the dead body itself still answers with
        no bytes -- but it is NAMED, and it is the only click that does.

        !! THIS TEST IS MEANT TO DIE, AND LANE A IS THE LANE THAT KILLS IT
        (AGENTS.md rule: a test pinning another lane's behaviour as a
        baseline has to be able to die on purpose).  The same COO note
        hands lane A the follow-up in which the corpse answers with a
        ``mob_death`` body instead of with silence; the commit that pays
        that debt REPLACES this assertion, and needs no letter to chief to
        do it.  What must survive is the half below it: the refusal is
        printed with the clicked placement's own number."""
        state, target = self._killed_session_standing_in_scene_2()
        dead_index = next(
            index for index, mob in self._hostile_indices().items()
            if mob.actor_identity == target
        )
        actions, console = self._click(state, dead_index)
        self.assertEqual(
            [action for action in actions
             if action[0].startswith(
                 f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_FACE_P")],
            [], actions,
        )
        self.assertIn(
            "_IDENTITY_REFUSED reason=clicked_body_is_dead_needs_a_mob_"
            f"death_body placement={dead_index} identity=0x", console)

    def test_a_click_before_any_kill_is_answered_at_the_ceiling(self) -> None:
        """The control: the same dispatch on a session with no combat in it
        answers with ``dead_at_ceiling=0``, so the assertion above is
        reading the kill and not merely the presence of a ledger."""
        state = self._state("tok_call_site_ledger_control")
        spawn = self._warp(state, PRISON_EXILE)
        self._dispatch(state, self._target_pos_pc(spawn))
        index = self._civilian_index()
        actions, console = self._click(state, index)
        self.assertTrue([
            action for action in actions
            if action[0] == (
                f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_FACE_P{index}")
        ], actions)
        self.assertIn("dead_at_ceiling=0", self._answered_tokens(console))

    def test_a_wounded_monster_reaches_the_wire_wounded(self) -> None:
        """The benefit the CORE-REQUEST was actually asking for, end to end.

        pf-adversary D7, measured: throwing every WOUND away inside
        ``lane_a_click_hp.current_hp_of`` (deaths still honoured) left this
        file green while the ceiling-heal the request exists to stop was
        fully back.  The dead path was pinned and the wounded path was not,
        so this drives a hurt-but-living monster through the dispatcher.
        """
        state = self._state("tok_call_site_ledger_wounded")
        spawn = self._warp(state, PRISON_EXILE)
        target = self.roster[0].actor_identity
        max_hp = self._wound(state, target, 1)
        self.assertGreater(
            state.mob_combat_ledger.balance_of(target).current_hp, 0,
            "the harness killed the monster instead of wounding it",
        )
        self.assertLess(
            state.mob_combat_ledger.balance_of(target).current_hp, max_hp,
            "the harness did not actually take any HP off",
        )
        self._dispatch(state, self._target_pos_pc(spawn))
        _actions, console = self._click(state, self._civilian_index())
        tokens = self._answered_tokens(console)
        self.assertIn("wounded=1", tokens)
        self.assertIn("dead_at_ceiling=0", tokens)

    def test_every_registered_responder_accepts_the_call_sites_keywords(
        self,
    ) -> None:
        """A responder that cannot take one keyword loses its WHOLE scene.

        pf-adversary D4, measured on a substituted old-signature responder:
        the click returns zero bytes and no action, the console still prints
        ``LANE_HOOK_FIRED`` (which reads as success), and the
        ``scene_choose_npc_responder_failed_TypeError`` event only reaches a
        console started with ``--export-events``.  ``lane_hooks``' own
        docstring ASKS responders to accept ``**kwargs``; nothing enforced
        it, and this round is the one that grew the call site from six
        keywords to seven.
        """
        call_site_keywords = {
            "legacy", "chosen_identities", "population_indices",
            "last_target_pos", "scene_id", "scene_entry_registry",
            "mob_combat_ledger",
        }
        registered = dict(lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS)
        self.assertTrue(registered, "no ChooseNPC responder is registered")
        for scene_id, entry in sorted(registered.items()):
            with self.subTest(scene=scene_id, module=entry.module):
                parameters = inspect.signature(entry.respond).parameters
                takes_var_keyword = any(
                    p.kind is inspect.Parameter.VAR_KEYWORD
                    for p in parameters.values()
                )
                missing = call_site_keywords - set(parameters)
                self.assertTrue(
                    takes_var_keyword or not missing,
                    f"{entry.module} would raise TypeError on "
                    f"{sorted(missing)} and lose scene {scene_id} entirely",
                )


if __name__ == "__main__":
    unittest.main()
