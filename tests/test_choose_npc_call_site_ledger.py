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
``hp=ledger``/``from_ledger=`` assertions below go red.  Nothing else in
the repository would notice.

R316 CORRECTED THIS PARAGRAPH.  It used to name a ``dead_at_ceiling=1``
assertion, and R316 deleted that assertion when the call site also began
handing over ``mob_death_register=`` -- the one dead body in this scene now
comes back as a corpse, so the ceiling count is legitimately 0.  A module
docstring that names a pin the file no longer holds is the first thing the
next round reads to learn what this file guards (pf-adversary R316 D7).

THE HARNESS SHAPE is reproduced from ``test_lane_a_click_after_a_kill.py``
rather than imported, for the reason that file gives for reproducing
LANE-B's: importing another lane's test class makes a production guarantee
die quietly the day that file is reorganised.
"""
from __future__ import annotations

import ast
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
from pirateforce_foundation import runtime                         # noqa: E402
from pirateforce_foundation import scene2_prison_exile_tables as tables  # noqa: E402
from pirateforce_foundation import world_population                # noqa: E402
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
        """``hp=ledger`` with a COUNT of bodies that took their HP from it
        is the token that can only be printed if a ledger which KNOWS ABOUT
        THE KILL arrived.  Delete ``mob_combat_ledger=`` from the call site
        and it reads ``hp=ceiling from_ledger=0`` (measured this round):
        the whole point of R313, in one token.

        WHY THIS ASSERTION MOVED (R316).  Until this round the pin was
        ``dead_at_ceiling=1``, and that token was honest THEN: with no
        register at the call site, the one dead body in this scene had to
        be composed at the table ceiling, and only a ledger that had seen
        the kill could count it.  R316 hands the responder
        ``mob_death_register=`` as well, so the same body now comes back as
        a corpse and the ceiling count is legitimately 0.  Reading
        ``dead_as_corpse=1`` INSTEAD would have been a silent downgrade of
        this test: that count comes from the REGISTER, and measured, it
        stays 1 with ``mob_combat_ledger=`` deleted from the call site (the
        mutant above, measured) -- this file would then have kept a green
        pin on a keyword that was gone.  ``from_ledger=`` is the count that
        dies with the ledger, so it is the one that carries the pin."""
        state, _target = self._killed_session_standing_in_scene_2()
        _actions, console = self._click(state, self._civilian_index())
        tokens = self._answered_tokens(console)
        self.assertIn("hp=ledger", tokens)
        # DERIVED, not typed: every hostile placement except the one this
        # harness buried is a live body whose HP came out of the ledger.
        # The literal `11` was a hardcode of `12 - 1` that would have
        # survived the next owner ruling on placements (pf-adversary R316
        # D8).
        live_hostiles = len(self._hostile_indices()) - 1
        self.assertIn(f"from_ledger={live_hostiles}", tokens)
        self.assertIn("dead_as_corpse=1", tokens)

    def test_the_corpse_answers_with_a_body_instead_of_with_silence(
        self,
    ) -> None:
        """The debt ``COO-DECISION 20260903_0252`` opened and R316 pays: a
        click on the dead body itself used to answer with NOTHING, refused
        by name.  It now answers.

        THIS TEST REPLACES ``test_the_corpse_is_refused_by_name_and_not_by
        _silence``, which said in its own docstring that it was meant to
        die the day lane A's corpse answer reached the call site.  It died
        here, on purpose, and the assertions below pin what took its place
        rather than deleting a pin and moving on.

        WHAT THIS FILE PINS, AND WHAT IT DELIBERATELY DOES NOT.  What is
        pinned here is what a CALL-SITE guard can honestly pin: that the
        click is no longer silent, that the answer carries the whole
        island rather than the clicked row alone, and that the line names
        the placement the player really clicked.

        NOT PINNED HERE, AND NAMED SO NOBODY READS THIS FILE AS COVER FOR
        IT (pf-adversary R316 D3, two mutants measured): that the corpse
        entry carries no MovementAttr, and that its HP is 0 rather than
        full.  Both derive from the responder's own composition, both stay
        green in THIS file when broken, and both are pinned in lane A's
        ``tests/test_lane_a_click_after_a_kill.py``
        (``test_the_corpse_answer_sends_no_movement_for_the_clicked_body``).
        The label ``CORPSE_P`` is a name the SERVER chose; it is evidence
        that the corpse branch ran, and evidence of nothing else.

        NOT CLAIMED AT ALL: that the player sees a body lying on the floor.
        These are wire bytes; the client-observable layer is GT-214's."""
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
        answers = [
            action for action in actions
            if action[0] == (
                f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_CORPSE_P{dead_index}")
        ]
        self.assertEqual(len(answers), 1, actions)
        self.assertTrue(answers[0][1], "the corpse answer carried no pc bytes")
        self.assertTrue(
            answers[0][2], "the corpse answer carried no frame bytes")
        self.assertIn(
            "_CLICKED_BODY_IS_A_CORPSE reason=answered_with_a_corpse_body_"
            f"not_a_facing placement={dead_index} identity=0x", console)
        self.assertIn("dead_as_corpse=1", self._answered_tokens(console))

    def test_the_corpse_answer_still_carries_the_whole_island(self) -> None:
        """"There ARE bytes" is not the same claim as "the world is still
        in them", and RE-092 is the reason the difference matters.

        pf-adversary R316 D2, measured: composing the corpse answer from
        ``entries[:1]`` takes the frame from 12,546 bytes / 97 actors to
        164 bytes / 1 actor -- the replace-by-omission world wipe RE-092
        named -- and the console still prints ``visible=97``, because that
        count is computed BEFORE composition.  The whole suite stayed green
        at 8389 passed.  Lane A's own guard for this reads that console
        string, so it is a console-layer statement standing in for a
        frame-layer fact.

        This pin is frame-layer: the corpse answer is compared against a
        civilian answer from the SAME session, which is known to carry the
        island.  A frame that dropped the world would be a fraction of it.

        NOT CLAIMED: that the two frames are byte-identical.  They are not,
        and they should not be -- one row is composed as a corpse."""
        state, target = self._killed_session_standing_in_scene_2()
        dead_index = next(
            index for index, mob in self._hostile_indices().items()
            if mob.actor_identity == target
        )
        corpse_actions, _console = self._click(state, dead_index)
        corpse_frame = next(
            action[2] for action in corpse_actions
            if action[0] == (
                f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_CORPSE_P{dead_index}")
        )
        civilian_index = self._civilian_index()
        civilian_actions, _console2 = self._click(state, civilian_index)
        civilian_frame = next(
            action[2] for action in civilian_actions
            if action[0] == (
                f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_FACE_P"
                f"{civilian_index}")
        )
        self.assertGreater(len(civilian_frame), 10_000, "the control frame "
                           "is not island-sized; the harness changed")
        # A corpse row is composed differently from a facing row, so a
        # small delta is expected and healthy.  A world wipe is not small.
        self.assertGreater(
            len(corpse_frame), len(civilian_frame) * 0.9,
            f"the corpse answer is {len(corpse_frame)} bytes against the "
            f"civilian answer's {len(civilian_frame)}: the island is gone",
        )

    def test_the_corpse_line_names_the_clicked_body_not_the_first_one(
        self,
    ) -> None:
        """With one corpse in the scene, "the placement clicked" and "the
        first dead placement" are the same number, so the assertion above
        cannot tell them apart.  This is the defect chief's own letter
        ``20260902_1918`` item 4.1 named -- the refusal used to print the
        first dead hostile in sorted order, sending a tester to look at a
        placement that had nothing wrong with it -- and it is the half of
        the deleted test that had to survive (pf-adversary R316 D9,
        measured: printing the first corpse's index instead of the clicked
        one leaves this file green without this test).

        So: kill two, click the SECOND."""
        state, first = self._killed_session_standing_in_scene_2()
        hostiles = self._hostile_indices()
        second = next(
            mob.actor_identity for _index, mob in sorted(hostiles.items())
            if mob.actor_identity != first
        )
        self._kill(state, second)
        second_index = next(
            index for index, mob in hostiles.items()
            if mob.actor_identity == second
        )
        first_index = next(
            index for index, mob in hostiles.items()
            if mob.actor_identity == first
        )
        self.assertNotEqual(
            first_index, second_index, "the harness killed one body twice")
        self.assertGreater(
            second_index, first_index,
            "this test needs the clicked corpse to sort AFTER the other "
            "one, or it cannot tell the two readings apart",
        )
        actions, console = self._click(state, second_index)
        self.assertIn(
            "_CLICKED_BODY_IS_A_CORPSE reason=answered_with_a_corpse_body_"
            f"not_a_facing placement={second_index} identity=0x", console)
        self.assertNotIn(
            f"not_a_facing placement={first_index} ", console)
        self.assertEqual(
            len([action for action in actions
                 if action[0] == (
                     f"LANE_A_CHOOSE_NPC_SCENE{PRISON_EXILE}_CORPSE_P"
                     f"{second_index}")]),
            1, actions,
        )
        self.assertIn("dead_as_corpse=2", self._answered_tokens(console))

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

    @staticmethod
    def _keywords_the_call_site_passes() -> set:
        """Every keyword ``runtime.py`` actually hands the responder.

        Read from the source with ``ast``, not retyped here: a name that
        only exists in this file's own head is a name that goes stale in
        the commit that adds the next keyword, which is what happened three
        rounds running (pf-adversary R316 D1).
        """
        source = Path(runtime.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        found: set = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "respond":
                continue
            owner = func.value
            if (
                not isinstance(owner, ast.Name)
                or owner.id != "scene_choose_npc_responder"
            ):
                continue
            found |= {kw.arg for kw in node.keywords if kw.arg is not None}
        return found

    def test_a_malformed_extra_actions_does_not_kill_the_dispatch_thread(
        self,
    ) -> None:
        """CORE-REQUEST 20260904_0137's pair, pf-adversary (round `t0funk`),
        reproduced: a responder handing back ``extra_actions=None`` instead
        of the documented ``()`` default used to raise ``TypeError:
        'NoneType' object is not iterable`` OUT OF ``state.dispatch()``
        entirely -- uncaught, because ``actions.extend(response.
        extra_actions)`` sat outside every try/except at this call site.
        This project's own scar tissue (``pose_trial.py``'s interlock X07)
        is that the frozen ``game_listener`` around ``dispatch()`` has NO
        except handler at all, so that exception kills the connection's
        listener thread.

        No REGISTERED responder can trigger this today (only
        ``lane_a_choose_npc_scene1`` ever returns non-default
        ``extra_actions``/``latches_spent``, and it is
        ``production_allowed = False``), which is why this test reaches
        past the registry with a fake entry rather than a real click on a
        real scene -- the same shape
        ``test_every_registered_responder_accepts_the_call_sites_keywords``
        above already uses to test a call-site guard no CURRENT responder
        happens to trip.
        """
        module_name = "pirateforce_foundation.lane_hooks.fake_malformed_responder"

        def _malformed_respond(**_ignored):
            return lane_hooks.ChooseNpcResponse(
                console_lines=(),
                label="FAKE_MALFORMED_P0",
                pc=b"",
                frame=b"",
                delay=0.0,
                extra_actions=None,  # the shape under test: not a tuple
            )

        original_entry = lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.get(1)
        original_allowed = lane_hooks._PRODUCTION_ALLOWED.get(module_name)

        def _restore():
            if original_entry is None:
                lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.pop(1, None)
            else:
                lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS[1] = original_entry
            if original_allowed is None:
                lane_hooks._PRODUCTION_ALLOWED.pop(module_name, None)
            else:
                lane_hooks._PRODUCTION_ALLOWED[module_name] = original_allowed

        self.addCleanup(_restore)
        lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS[1] = lane_hooks.ChooseNpcResponder(
            module_name, _malformed_respond,
        )
        lane_hooks._PRODUCTION_ALLOWED[module_name] = True

        state = self._state("tok_malformed_extra_actions")
        self.assertEqual(
            state.foundation.selected.position.scene_id, 1,
            "a fresh session must start in scene 1 for this fake to fire",
        )
        placement = next(iter(
            world_population.load_port_royal_placements(self.legacy)
        ))
        actions, console = self._dispatch(
            state, self._choose_npc_pc(placement.actor_identity),
        )
        # If the guard regresses, `state.dispatch` above raises before this
        # line is ever reached -- pytest reports that as an ERROR, which is
        # the real assertion this test makes; everything below just proves
        # the fail-CLOSED direction chosen is the one that shipped.
        self.assertTrue(
            actions, "the face frame the responder DID compose must still "
            "ship even though the collection half was malformed",
        )
        self.assertIn(
            "scene_choose_npc_responder_extra_actions_malformed_TypeError",
            state.events,
        )
        self.assertFalse(
            state.shop_store5_open_sent,
            "the latch write-back must not run on the same malformed path "
            "as the extend() that raised",
        )

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
        it, and the round that opened this guard grew the call site from
        six keywords to seven.

        R316: THE KEYWORD SET IS NOW READ OUT OF ``runtime.py`` ITSELF, and
        the retyped list it replaces is why.  pf-adversary, measured: on
        the R316 tree the retyped set still held EIGHT names while the call
        site passed NINE, so a responder given an explicit eight-keyword
        signature and no ``**_ignored`` PASSED this guard while losing all
        eleven of its production scenes (3-11, 126, 130) to exactly the
        silent ``TypeError`` above.  The guard went stale in the very
        commit that made it stale -- three rounds running, because a human
        has to remember to retype the name in two files.  An AST read of
        the real call site cannot forget.
        """
        call_site_keywords = self._keywords_the_call_site_passes()
        # A floor, so an AST read that silently finds nothing (the call
        # moves, is renamed, is wrapped) cannot turn this guard green.
        self.assertGreaterEqual(len(call_site_keywords), 9, call_site_keywords)
        self.assertIn("mob_death_register", call_site_keywords)
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
