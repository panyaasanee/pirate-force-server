"""LANE-E: the ChooseNPC call site hands the responder the SESSION's cell.

WHAT THIS PINS.  ``runtime.py``'s ChooseNPC dispatch composes its answer
through lane A's responders, and those responders route the frame through
``lane_hooks.lane_a_ground_preserve.compose_answer``.  That function reaches
the under-publication composer only when a real ``mob_loot.DropLedgerCell``
is handed to it; with ``None`` it falls back to v141's own bytes.  Lane A
asked for the keyword (``pf_bridge notes_to_chief/20260903_0325``) and lane
B's ``20260903_0152`` item 2 named the two things that had to be on ``main``
first -- ``caller_scene_fold`` and the under-publication composer.  Both are.

WHAT THE DIFFERENCE IS, STATED AT THE LAYER IT WAS MEASURED AT.  One row
standing in scene 2: the answer is 12,577 bytes with the keyword and 12,574
without it, which is the delta lane A predicted from its own measurement.
**Those three bytes are a MARKER, not the list** -- pf-adversary R314 (D1)
measured the same 12,577 for 1, 3 and 5 rows, matching what
``lane_a_ground_preserve``'s own docstring records for 1 vs 255.  That the
CLIENT then keeps its ground pool is ``RE-130``'s claim ABOUT THE CLIENT and
is proven nowhere in this repository.  So nothing in this file says a row
"survives" on the player's floor: that sentence belongs to the
client-observable layer, which has no result yet.  What is pinned is that
the marker reaches the wire at all, and that it is scene-local.

WHY IT IS A SEPARATE FILE FROM ``test_choose_npc_call_site_ledger.py``:
that one pins the COMBAT ledger keyword and would stay green with the loot
cell deleted.

THE HARNESS SHAPE is reproduced from ``test_choose_npc_call_site_ledger.py``
rather than imported, for the reason that file gives for reproducing lane
A's: importing another test class makes a production guarantee die quietly
the day that file is reorganised, and a subclass would silently re-run the
parent's whole suite here as well.

NO EXACT BYTE COUNT IS ASSERTED.  The frame's size is lane A's table data
and lane B's row shape; pinning 12,577 here would make this lane's file the
trap that kills their round (``COO-DECISION 20260903_0053`` rule b).  What
is pinned is the DIFFERENCE the seam exists to make, which no other lane
can change by editing a table.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
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
from pirateforce_foundation import mob_loot                        # noqa: E402
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
    lane_a_ground_preserve as ground_preserve,
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


class TheCallSiteHandsOverTheSessionLootCellTests(unittest.TestCase):

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


    def _row_count(self, state):
        return mob_loot.ground_rows_live_here(state.mob_loot_cell, "Bg0002")

    def _frame_of(self, state, placement_index):
        actions, console = self._click(state, placement_index)
        self.assertEqual(
            len(actions), 1,
            f"the click was not answered with one action: {console}",
        )
        return actions[0][2]

    # ---- the pins ---------------------------------------------------

    def test_a_row_on_this_floor_survives_an_answer_to_another_click(
        self,
    ) -> None:
        """The marker reaches the wire, measured through dispatch.

        A kill in scene 2 leaves loot on the ground.  The player then
        clicks a CIVILIAN -- nothing to do with the corpse -- and the
        answer to that click is composed under the cell's own publication
        instead of over it.  ``GT-204`` is written to watch this sequence
        at the layer where a player could see a difference; this test does
        not reach that layer and does not claim to.

        The mutant is applied in-process rather than by editing the file:
        withholding the cell from the same session, on the same click, is
        byte-for-byte what deleting ``mob_loot_cell=`` from the call site
        does, and it keeps the comparison free of table drift.
        """
        state, _target = self._killed_session_standing_in_scene_2()
        placement = self._civilian_index()
        self.assertEqual(
            self._row_count(state), 1,
            "the harness left no loot on the ground, so this test would "
            "pass for the wrong reason",
        )
        with_cell = self._frame_of(state, placement)

        held_back = state.mob_loot_cell
        state.mob_loot_cell = None
        try:
            without_cell = self._frame_of(state, placement)
        finally:
            state.mob_loot_cell = held_back

        # Lengths and digests in the message, never the frames: mutant (c)
        # produced 76 KB of unreadable output when this dumped both bodies
        # (pf-adversary R314 D6).
        self.assertNotEqual(
            with_cell, without_cell,
            "the standing ground row made no difference to the frame, so "
            "the call site is not reaching the under-publication composer "
            f"(len {len(with_cell)} vs {len(without_cell)}, "
            f"sha1 {hashlib.sha1(with_cell).hexdigest()[:12]} vs "
            f"{hashlib.sha1(without_cell).hexdigest()[:12]})",
        )
        self.assertGreater(
            len(with_cell), len(without_cell),
            "the answer that kept the ground list is not the longer frame",
        )

    def test_an_empty_floor_is_answered_with_the_bytes_of_the_day_before(
        self,
    ) -> None:
        """The common path must be untouched, byte for byte.

        Every boot before a kill, and every scene whose floor is clean,
        has to compose exactly what it composed yesterday -- otherwise the
        seam is a behaviour change on every click instead of on the one
        click it exists for.
        """
        state = self._state("tok_call_site_loot_cell_clean")
        spawn = self._warp(state, PRISON_EXILE)
        self._dispatch(state, self._target_pos_pc(spawn))
        placement = self._civilian_index()
        self.assertEqual(
            self._row_count(state), 0, "this scene's floor is not clean",
        )
        with_cell = self._frame_of(state, placement)

        held_back = state.mob_loot_cell
        state.mob_loot_cell = None
        try:
            without_cell = self._frame_of(state, placement)
        finally:
            state.mob_loot_cell = held_back

        self.assertEqual(
            len(with_cell), len(without_cell),
            "passing the cell changed the frame LENGTH on a clean floor",
        )
        self.assertEqual(
            hashlib.sha1(with_cell).hexdigest(),
            hashlib.sha1(without_cell).hexdigest(),
            "passing the cell changed the frame on a clean floor",
        )

    def test_no_other_scene_is_armed_with_this_scenes_ground_rows(
        self,
    ) -> None:
        """The cell now reaches EVERY registered responder, not just scene 2.

        pf-adversary R314 (D3): before this test, replacing the fold in
        ``compose_answer`` with a hard-coded ``"Bg0002"`` -- so that every
        scene's frame is armed with scene 2's rows -- left the whole file
        green.  The keyword was pinned, scene 2's behaviour was pinned, and
        the other twelve registered scenes were executed by nothing.

        Composed directly rather than through thirteen warps: driving each
        scene through ``dispatch`` costs minutes, and the defect this
        catches lives in the fold that ``compose_answer`` owns.  Scene 2
        keeps its dispatcher-driven pin above.

        This is the guard lane B's ``GROUND_LIVENESS_SCENE_MISMATCH`` and
        ``..._SCENE_ID_AMBIGUOUS`` exist for, seen from the call site's
        side.  It reads the live registry, so a scene registered tomorrow
        is covered the day it appears -- and it names lane A as the owner
        of ``compose_answer`` if it ever has to go red across a rename.
        """
        state, _target = self._killed_session_standing_in_scene_2()
        self.assertEqual(
            self._row_count(state), 1,
            "the harness left no loot on the ground, so a leak would be "
            "invisible to this test",
        )
        registered = sorted(lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS)
        self.assertIn(
            PRISON_EXILE, registered,
            "scene 2 is not registered, so this test proves nothing",
        )
        leaked = []
        for scene_id in registered:
            with self.subTest(scene=scene_id):
                with_cell = ground_preserve.compose_answer(
                    self.legacy, [], scene_id, state.mob_loot_cell)
                without_cell = ground_preserve.compose_answer(
                    self.legacy, [], scene_id, None)
                same = with_cell == without_cell
                if scene_id == PRISON_EXILE:
                    self.assertFalse(
                        same,
                        "the scene the rows actually stand in composed the "
                        "same bytes with and without the cell",
                    )
                elif not same:
                    leaked.append(scene_id)
        self.assertEqual(
            leaked, [],
            "these scenes were armed with scene 2's ground rows: "
            f"{leaked} -- the fold in lane_a_ground_preserve.compose_answer "
            "is not scene-local",
        )

    def test_the_call_site_reads_the_attribute_and_does_not_guess(
        self,
    ) -> None:
        """``mob_loot_cell=self.mob_loot_cell`` at the call site, by AST.

        Read as AST and not as text, for the reason lane B measured on its
        own baseline test (letter ``20260903_0355`` item three): a text
        pin goes red when the line is merely re-wrapped, and stays green
        when the name is changed with the old one left behind in a
        struck-through comment -- this house's own convention.

        ``getattr(self, "mob_loot_cell", None)`` is refused on purpose.
        The cell is opened in the same ``__init__`` ``try`` that re-raises
        (``runtime.py`` ~1401), so a session that reaches ``dispatch`` has
        one; a future rename must then fail loudly here instead of
        clearing the ground on every answer in silence.
        """
        tree = ast.parse(
            (ROOT / "src" / "pirateforce_foundation" / "runtime.py").read_text()
        )
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "respond"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "scene_choose_npc_responder"
        ]
        self.assertEqual(
            len(calls), 1,
            "expected exactly one scene_choose_npc_responder.respond() "
            f"call site, found {len(calls)}",
        )
        keywords = {kw.arg: kw.value for kw in calls[0].keywords}
        self.assertIn(
            "mob_loot_cell", keywords,
            "the call site passes no cell: every answer clears the ground",
        )
        value = keywords["mob_loot_cell"]
        self.assertIsInstance(
            value, ast.Attribute,
            "the cell must be read as self.mob_loot_cell, not guessed",
        )
        self.assertEqual(value.attr, "mob_loot_cell")
        self.assertIsInstance(value.value, ast.Name)
        self.assertEqual(value.value.id, "self")


if __name__ == "__main__":
    unittest.main()
