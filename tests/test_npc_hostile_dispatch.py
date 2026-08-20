"""NPC-HOSTILE-DISPATCH (HYP-PF-027) -- the faction pairing on the dispatcher.

``tests/test_npc_hostile_hypothesis.py`` proves the encoder offline.  This
file drives the REAL ``make_state_class`` dispatch path behind the opt-in
``scenarios/npc_hostile_hypothesis_faction_pairing.json`` and proves the wire
layer end to end, headless -- no server process, no socket, no client:

  * THE ENTRY HALF: on a fresh database the first login + V25 create lands on
    the canonical smoke identity 0x10010001, and the StartGame response then
    CONTAINS the frozen faction-1 player ActorAttr bytes and NOT the
    production ones, with the named entry event; a second account's identity
    is not pinned, its StartGame stays production byte-for-byte, and its
    named fallback event fires;
  * THE SWEEP HALF: one accepted chat-input frame produces exactly ONE
    action, byte-identical to ``build_npc_hostile_sweep``'s own composition
    -- label, PC, frame and delay compared with ``==`` on the bytes.  The
    dispatcher is a forwarder, and if it ever becomes a second composer
    these tests go red;
  * the refusal ladder fires with its named no-reply events: wrong shape,
    no selected character, wrong sequence, non-pinned identity, an
    UNAPPLIED PAIRING (the entry half never sent the player faction), and
    the one-shot latch;
  * containment: with the scenario absent no HYP_PF_027 label and no lane
    event appears and the StartGame stays production; the chat-keyed lanes
    are mutually exclusive at construction; the database gains no row.

NOT proven here: whether a real client renders a hostile presentation.
**No client has ever been shown one byte of this profile** -- that is
GT-032, attended, not run.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation import npc_hostile_hypothesis as nhm  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as parent  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    make_actor_attr_with_basic_faction,
    make_actor_attr_with_name,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "npc_hostile_hypothesis_faction_pairing.json"
PARENT_SCENARIO_PATH = (
    ROOT / "scenarios" / "runtimeres_death_hypothesis_spawn_then_kill.json"
)

SWEEP_EVENT = "npc_hostile_hypothesis_faction_pairing_sent"
ENTRY_EVENT = "npc_hostile_hypothesis_player_faction1_start_game_sent"
ENTRY_NOT_PINNED_EVENT = (
    "npc_hostile_hypothesis_player_identity_not_pinned_production_start_game"
)
REPEAT_EVENT = "npc_hostile_hypothesis_already_sent_no_reply"
NO_SELECTED_EVENT = "npc_hostile_hypothesis_no_selected_no_reply"
WRONG_SEQUENCE_EVENT = "npc_hostile_hypothesis_wrong_sequence_no_reply"
IDENTITY_NOT_PINNED_EVENT = (
    "npc_hostile_hypothesis_player_identity_not_pinned_no_reply"
)
PAIRING_NOT_APPLIED_EVENT = (
    "npc_hostile_hypothesis_player_faction_not_applied_no_reply"
)
EVENT_PREFIX = "npc_hostile_hypothesis_"
ACTION_LABEL = "HYP_PF_027_NPC_HOSTILE_HOSTILE_SPAWN"
PINNED_LO = 0x10010001
PINNED_HI = 0


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class NpcHostileDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
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
        self.scenario = nhm.load_npc_hostile_hypothesis_scenario(SCENARIO_PATH)
        self.wire = nhm.npc_hostile_wire_unlock(self.scenario)
        self.probe = nhm.resolve_probe(self.legacy)

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ----------------------------------------------------------

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            npc_hostile_hypothesis_scenario=(
                self.scenario if sweep else None
            ),
        )

    def _state(self, login, *, sweep=True, ready=True, select=True):
        """The FIRST login+create on the fresh per-test database lands on
        account 1 selector 0, which IS the pinned smoke identity
        0x10010001."""
        state = self._state_type(sweep=sweep)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(login)
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        start_actions = None
        if select:
            start_actions = self._select(state)
        state.runtime_ack_sent = ready
        state.last_start_actions = start_actions
        return state

    def _select(self, state):
        characters = self.store.list_characters(state.foundation.account_id)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[-1].selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        return actions

    def _trigger(self):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])

    def _player_attrs(self, selected):
        p = selected.position
        plain = bytes(make_actor_attr_with_name(
            self.legacy, selected.identity_lo, selected.identity_hi,
            p.scene_id, p.scene_seq, selected.name,
        ))
        paired = bytes(make_actor_attr_with_basic_faction(
            self.legacy, selected.identity_lo, selected.identity_hi,
            p.scene_id, p.scene_seq, selected.name,
            nhm.NPC_HOSTILE_PLAYER_PAIR_FACTION,
        ))
        return plain, paired

    def _refused(self, state, parsed, event):
        before = state.npc_hostile_sweep_count
        out = state.dispatch(parsed)
        self.assertEqual(out, [])
        self.assertEqual(state.npc_hostile_sweep_count, before)
        self.assertTrue(
            any(e.startswith(event) for e in state.events),
            state.events[-3:],
        )

    # ----- the entry half ---------------------------------------------------

    def test_the_pinned_identity_gets_the_faction_start_game(self):
        state = self._state("nhd01")
        selected = state.foundation.selected
        self.assertEqual(
            (selected.identity_lo, selected.identity_hi),
            (PINNED_LO, PINNED_HI),
        )
        self.assertEqual(state.events.count(ENTRY_EVENT), 1)
        self.assertIs(state.npc_hostile_player_faction_start_sent, True)
        plain, paired = self._player_attrs(selected)
        sg_pc = bytes(state.last_start_actions[0][1])
        self.assertIn(paired, sg_pc)
        self.assertNotIn(plain, sg_pc)
        self.assertEqual(
            bytes(state.last_start_actions[0][2]),
            self.legacy.frame_pc(sg_pc),
        )

    def test_a_non_pinned_identity_falls_back_to_production_bytes(self):
        first = self._state("nhd02_first")
        self.assertEqual(first.foundation.selected.identity_lo, PINNED_LO)
        second = self._state("nhd02_second")
        selected = second.foundation.selected
        self.assertNotEqual(
            (selected.identity_lo, selected.identity_hi),
            (PINNED_LO, PINNED_HI),
        )
        self.assertEqual(second.events.count(ENTRY_NOT_PINNED_EVENT), 1)
        self.assertIs(second.npc_hostile_player_faction_start_sent, False)
        plain, paired = self._player_attrs(selected)
        sg_pc = bytes(second.last_start_actions[0][1])
        self.assertIn(plain, sg_pc)
        self.assertNotIn(paired, sg_pc)

    def test_with_the_scenario_absent_start_game_stays_production(self):
        state = self._state("nhd03", sweep=False)
        selected = state.foundation.selected
        plain, paired = self._player_attrs(selected)
        sg_pc = bytes(state.last_start_actions[0][1])
        self.assertIn(plain, sg_pc)
        self.assertNotIn(paired, sg_pc)
        self.assertFalse(
            any("npc_hostile" in event for event in state.events),
        )

    # ----- the sweep half ---------------------------------------------------

    def test_the_dispatcher_forwards_the_encoders_bytes_exactly(self):
        state = self._state("nhd04")
        expected = nhm.build_npc_hostile_sweep(
            self.legacy, self.probe, self.wire, self.scenario,
        )
        actions = state.dispatch(self._trigger())
        self.assertEqual(actions, expected)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][0], ACTION_LABEL)
        self.assertEqual(actions[0][3], 0.0)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)
        self.assertEqual(state.npc_hostile_sweep_count, 1)
        read = nhm.decode_npc_hostile_actor_entry_frame(actions[0][1])
        self.assertEqual(read["actor_type"], 4)
        self.assertEqual(read["identity"], 0x2001)
        self.assertEqual(
            read["attrs"][nhm.NPC_ATTR_ID]["fields"][nhm.BASIC_BIT_FACTION],
            6,
        )

    def test_one_shot(self):
        state = self._state("nhd05")
        first = state.dispatch(self._trigger())
        self.assertEqual(len(first), 1)
        again = state.dispatch(self._trigger())
        self.assertEqual(again, [])
        self.assertEqual(state.events.count(REPEAT_EVENT), 1)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)
        self.assertEqual(state.npc_hostile_sweep_count, 1)

    def test_the_sweep_writes_no_database_row(self):
        state = self._state("nhd06")
        import sqlite3
        def counts():
            db = sqlite3.connect(str(self.db_path))
            try:
                names = [row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
                return {
                    n: db.execute(
                        'SELECT COUNT(*) FROM "%s"' % n).fetchone()[0]
                    for n in names
                }
            finally:
                db.close()
        before = counts()
        state.dispatch(self._trigger())
        self.assertEqual(counts(), before)

    # ----- the refusal ladder -----------------------------------------------

    def test_wrong_text_bytes_fail_closed(self):
        state = self._state("nhd07")
        pc = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        pc[-1] ^= 0xFF
        self._refused(
            state, self.legacy.parse_outer(bytes(pc)), EVENT_PREFIX,
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state("nhd08", select=False)
        self._refused(state, self._trigger(), NO_SELECTED_EVENT)

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("nhd09", ready=False)
        self._refused(state, self._trigger(), WRONG_SEQUENCE_EVENT)

    def test_a_non_pinned_identity_is_refused_at_dispatch_too(self):
        self._state("nhd10_first")
        second = self._state("nhd10_second")
        self._refused(second, self._trigger(), IDENTITY_NOT_PINNED_EVENT)

    def test_an_unapplied_pairing_is_refused_by_name(self):
        state = self._state("nhd11")
        # Held wrong ON PURPOSE: simulate an entry half that fell back to
        # production (the flag's constructor value), with the identity still
        # pinned.  The dispatch must refuse: half a pairing re-runs the
        # arena-v2 proven negative and answers nothing.
        state.npc_hostile_player_faction_start_sent = False
        self._refused(state, self._trigger(), PAIRING_NOT_APPLIED_EVENT)

    # ----- containment ------------------------------------------------------

    def test_with_the_scenario_absent_nothing_composes(self):
        state = self._state("nhd12", sweep=False)
        expected = nhm.build_npc_hostile_sweep(
            self.legacy, self.probe, self.wire, self.scenario,
        )
        actions = state.dispatch(self._trigger())
        labels = [row[0] for row in actions]
        self.assertFalse(
            any(label.startswith("HYP_PF_027") for label in labels), labels,
        )
        self.assertFalse(
            {row[1] for row in actions} & {row[1] for row in expected},
        )
        self.assertNotIn(SWEEP_EVENT, state.events)

    def test_the_chat_keyed_lanes_are_mutually_exclusive(self):
        parent_scenario = parent.load_runtimeres_death_hypothesis_scenario(
            PARENT_SCENARIO_PATH,
        )
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                npc_hostile_hypothesis_scenario=self.scenario,
                runtimeres_death_hypothesis_scenario=parent_scenario,
            )

    def test_the_other_lane_counters_never_move(self):
        state = self._state("nhd13")
        state.dispatch(self._trigger())
        self.assertEqual(state.runtimeres_death_sweep_count, 0)
        self.assertEqual(state.damage_model_sweep_count, 0)
        self.assertEqual(state.damage_hp_link_sweep_count, 0)
        self.assertEqual(state.remote_player_sweep_count, 0)
        self.assertEqual(state.hp_death_sweep_count, 0)

    def test_no_socket_action_rides_any_action(self):
        state = self._state("nhd14")
        actions = state.dispatch(self._trigger())
        self.assertTrue(all(len(action) == 4 for action in actions))


if __name__ == "__main__":
    unittest.main()
