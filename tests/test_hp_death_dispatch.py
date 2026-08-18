"""HP-DEATH-002 (HYP-PF-022) -- the death sweep on the real dispatcher.

``tests/test_hp_death_encoder.py`` proves the encoder offline.  This file drives
the REAL ``make_state_class`` dispatch path behind the opt-in
``scenarios/hp_death_hypothesis_death_sweep.json`` and proves the wire layer end
to end, headless -- no server process, no socket, no client:

  * one accepted chat-input frame (the exact 34-byte ascii12 shape the
    HYP-PF-014 lane already classifies, reused because it is the only client
    action an attended tester can trigger on demand) produces exactly FOUR
    actions, in the scenario's order, spaced by ``spacing_seconds``;
  * every dispatched frame carries vital id 0x309A with an ``ActorAttr``
    collection, and the Attr body at the fixed envelope offset re-decodes to
    the cumulative field set that step declares;
  * the frame the client should read as DEATH carries mask bit 0x0004 with the
    value 0 AND mask bit 0x0080 with a positive float -- checked on the bytes
    this dispatcher produced, at the byte level, not on a unit fixture -- and
    the frames before and after it do not;
  * the sweep ends with the character alive, on the wire;
  * fail-closed and containment: wrong length, wrong prefix, wrong text bytes,
    wrong envelope, no selected character and not-yet-runtime-ready all give
    ``[]`` with a named no-reply event; with no scenario the same trigger
    produces nothing and no frame in the process can carry bit 0x0080; the
    database file does not move one byte across accepted and refused windows;
    and the lane is mutually exclusive with every other scenario mode.

NOT proven here, and this is the load-bearing limit: whether a real client
opens L"Main_Dead", or does anything at all, when it receives these bytes.
That is GT-019, attended, not run.  This file proves only that the bytes leave
the server, and that they are the exact pair the client's own ``IsDead``
predicate reads.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "hp_death_hypothesis_death_sweep.json"
STATS_SCENARIO_PATH = (
    ROOT / "scenarios" / "stats_progression_hypothesis_xp_sweep.json"
)
SWEEP_EVENT = "hp_death_hypothesis_death_sweep_sent"
PC_VITAL_ID_SLICE = slice(16, 18)
BASIC_MASK_OFFSET = 12


class HpDeathRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = sp.load_hp_death_hypothesis_scenario(SCENARIO_PATH)
        self.unlock = sp.hp_death_lethal_unlock(self.scenario)
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ---------------------------------------------------------

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            hp_death_hypothesis_scenario=(self.scenario if sweep else None),
        )

    def _state(self, login, *, sweep=True, ready=True, select=True):
        state = self._state_type(sweep=sweep)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        if select:
            characters = self.store.list_characters(state.foundation.account_id)
            self.assertEqual(len(characters), 1)
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(characters[0].selector)
            ))
            self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _trigger(self, probe="probe1"):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

    def _trigger_pc(self, payload, *, outer_id=None, outer_version=0,
                    nested_version=0):
        legacy = self.legacy
        outer = legacy.GSCN_RUNTIME_PROTOCOL_REQ if outer_id is None else outer_id
        return bytes(
            legacy.u16tag(0x12, outer)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, outer_version)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, CHAT_INPUT_VITAL_ID)
            + legacy.u8tag(0x0B, nested_version)
            + payload
        )

    def _db_digest(self):
        return hashlib.sha256(self.db_path.read_bytes()).hexdigest()

    # ----- happy path ------------------------------------------------------

    def test_one_request_sweeps_the_four_steps_in_the_pinned_order(self):
        state = self._state("death01")
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), len(sp.HP_DEATH_STEP_ORDER))
        self.assertEqual(
            [label for label, _pc, _frame, _delay in actions],
            [
                sp.HP_DEATH_ACTION_LABEL_PREFIX + label
                for label in sp.HP_DEATH_STEP_ORDER
            ],
        )
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.hp_death_sweep_count, 1)

    def test_every_dispatched_frame_is_an_update_attr_vital_actor_attr(self):
        state = self._state("death02")
        for _label, pc, _frame, _delay in state.dispatch(self._trigger()):
            self.assertEqual(
                pc[PC_VITAL_ID_SLICE],
                sp.UPDATE_ATTR_VITAL_ID.to_bytes(2, "little"),
            )
            self.assertEqual(
                pc[sp.STATS_PC_PAYLOAD_OFFSET + 3:
                   sp.STATS_PC_PAYLOAD_OFFSET + 6],
                self.legacy.u16tag(0x12, sp.ACTOR_ATTR_ID),
            )

    def test_the_dispatched_bodies_decode_to_the_declared_field_sets(self):
        state = self._state("death03")
        selected = state.foundation.selected
        actor = sp.StatsProgressionActor(
            selected.identity_lo, selected.identity_hi,
            selected.position.scene_id, selected.position.scene_seq,
            selected.name,
        )
        actions = state.dispatch(self._trigger())
        for index, (_label, pc, _frame, _delay) in enumerate(actions):
            expected = sp.hp_death_step_fields(self.legacy, actor, index)
            self.assertEqual(
                sp.decode_actor_attr(sp.hp_death_attr_body(pc), self.unlock),
                (actor.identity_lo, actor.identity_hi, expected),
            )

    def test_exactly_one_dispatched_frame_satisfies_the_client_predicate(self):
        """The whole milestone, checked on the wire.

        The client's ``IsDead`` (0x454AC0) is ``f32[attr+0x58] > 0.0f`` AND
        ``u32[attr+0x44] == 0``.  Read both out of the composed bytes -- mask
        bit, tag and value -- and assert that exactly the HP_ZERO frame
        satisfies it.
        """
        state = self._state("death04")
        actions = state.dispatch(self._trigger())
        lethal = []
        for index, (_label, pc, _frame, _delay) in enumerate(actions):
            body = sp.hp_death_attr_body(pc)
            mask = int.from_bytes(
                body[BASIC_MASK_OFFSET:BASIC_MASK_OFFSET + 2], "little",
            )
            label = sp.HP_DEATH_STEP_ORDER[index]
            self.assertEqual(mask, sp.HP_DEATH_PROBE_BASIC_MASK[label], label)
            _lo, _hi, fields = sp.decode_actor_attr(body, self.unlock)
            has_timer = bool(mask & sp.HP_DEATH_TIMER_MASK_BIT)
            self.assertEqual(has_timer, "hp_death_timer" in fields)
            hp_zero = (
                bool(mask & sp.PROGRESSION_FIELDS["hp_current"].mask_bit)
                and fields["hp_current"] == 0
            )
            if has_timer and hp_zero and fields["hp_death_timer"] > 0.0:
                lethal.append(label)
        self.assertEqual(lethal, list(sp.HP_DEATH_LETHAL_STEP_LABELS))

    def test_the_death_timer_is_on_the_wire_as_tag_0x2a_and_60_seconds(self):
        state = self._state("death05")
        actions = state.dispatch(self._trigger())
        armed = sp.HP_DEATH_STEP_ORDER.index("TIMER_ARMED")
        body = sp.hp_death_attr_body(actions[armed][1])
        self.assertIn(sp.HP_DEATH_TIMER_WIRE_BYTES, body)
        index = body.index(sp.HP_DEATH_TIMER_WIRE_BYTES)
        self.assertEqual(body[index], sp.HP_DEATH_TIMER_TAG)
        self.assertEqual(
            struct.unpack("<f", body[index + 1:index + 5])[0],
            sp.HP_DEATH_TIMER_SECONDS,
        )
        self.assertGreaterEqual(
            sp.HP_DEATH_TIMER_SECONDS,
            sp.DURATION_DYING_IMAGE_DEFAULT - sp.DURATION_DYING_WINDOW_MARGIN,
        )

    def test_the_baseline_frame_carries_no_new_bit(self):
        state = self._state("death06")
        actions = state.dispatch(self._trigger())
        body = sp.hp_death_attr_body(actions[0][1])
        mask = int.from_bytes(
            body[BASIC_MASK_OFFSET:BASIC_MASK_OFFSET + 2], "little",
        )
        self.assertFalse(mask & sp.HP_DEATH_TIMER_MASK_BIT)
        self.assertNotIn(sp.HP_DEATH_TIMER_WIRE_BYTES, body)

    def test_the_sweep_ends_alive_on_the_wire(self):
        state = self._state("death07")
        actions = state.dispatch(self._trigger())
        _lo, _hi, fields = sp.decode_actor_attr(
            sp.hp_death_attr_body(actions[-1][1]), self.unlock,
        )
        self.assertGreater(fields["hp_current"], 0)

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("death08")
        delays = [delay for _l, _p, _f, delay in state.dispatch(self._trigger())]
        self.assertEqual(delays[0], sp.HP_DEATH_FIRST_DELAY_SECONDS)
        self.assertTrue(
            all(delay == self.scenario.spacing_seconds for delay in delays[1:])
        )
        self.assertEqual(
            self.scenario.spacing_seconds, sp.HP_DEATH_SPACING_SECONDS,
        )

    def test_the_request_payload_is_a_trigger_not_an_input(self):
        # Same session, so the only thing that could differ is the request
        # payload -- and it must not, because nothing in it is read.
        state = self._state("death09")
        first = state.dispatch(self._trigger("probe1"))
        second = state.dispatch(self._trigger("probe2"))
        self.assertEqual(
            [pc for _l, pc, _f, _d in first],
            [pc for _l, pc, _f, _d in second],
        )

    def test_two_requests_give_eight_frames_with_no_accumulated_state(self):
        state = self._state("death11")
        first = state.dispatch(self._trigger())
        second = state.dispatch(self._trigger())
        self.assertEqual(len(first) + len(second), 8)
        self.assertEqual(
            [pc for _l, pc, _f, _d in first], [pc for _l, pc, _f, _d in second],
        )
        self.assertEqual(state.hp_death_sweep_count, 2)

    def test_the_sweep_writes_nothing_to_the_database(self):
        state = self._state("death12")
        before = self._db_digest()
        state.dispatch(self._trigger())
        self.assertEqual(self._db_digest(), before)

    # ----- fail closed -----------------------------------------------------

    def _refused(self, state, parsed, event_fragment):
        before = self._db_digest()
        self.assertEqual(state.dispatch(parsed), [])
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertTrue(
            any(event_fragment in event for event in state.events),
            state.events,
        )
        self.assertEqual(self._db_digest(), before)

    def test_wrong_length_fails_closed(self):
        state = self._state("death13")
        payload = bytes(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])[-33:]
        self._refused(
            state, self.legacy.parse_outer(self._trigger_pc(payload)),
            "hp_death_hypothesis_",
        )

    def test_wrong_text_bytes_fail_closed(self):
        state = self._state("death14")
        pc = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        pc[-1] ^= 0xFF
        self._refused(
            state, self.legacy.parse_outer(bytes(pc)), "hp_death_hypothesis_",
        )

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("death15", ready=False)
        self._refused(
            state, self._trigger(),
            "hp_death_hypothesis_wrong_sequence_no_reply",
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state("death16", select=False)
        self._refused(
            state, self._trigger(),
            "hp_death_hypothesis_no_selected_no_reply",
        )

    def test_no_refusal_path_ever_emits_a_lethal_frame(self):
        for login, kwargs in (
            ("death17", {"ready": False}), ("death18", {"select": False}),
        ):
            state = self._state(login, **kwargs)
            self.assertEqual(state.dispatch(self._trigger()), [])
            self.assertEqual(state.hp_death_sweep_count, 0)

    # ----- containment -----------------------------------------------------

    def test_without_a_scenario_the_trigger_produces_no_death_frame(self):
        state = self._state("death19", sweep=False)
        actions = state.dispatch(self._trigger())
        for _label, pc, _frame, _delay in actions:
            self.assertNotIn(sp.HP_DEATH_TIMER_WIRE_BYTES, pc)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.hp_death_sweep_count, 0)

    def test_the_lane_is_mutually_exclusive_with_every_other_mode(self):
        stats = sp.load_stats_progression_hypothesis_scenario(
            STATS_SCENARIO_PATH
        )
        with self.assertRaises(ValueError):
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                hp_death_hypothesis_scenario=self.scenario,
                stats_progression_hypothesis_scenario=stats,
            )

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        for candidate in (
            object(), "hp_death_hypothesis_death_sweep",
            sp.HpDeathHypothesisScenario(
                sp.HP_DEATH_SCENARIO_ID, sp.HP_DEATH_HYPOTHESIS_ID,
                sp.HP_DEATH_STEP_ORDER, 6.0, 60.0,
            ),
        ):
            with self.assertRaises(ValueError):
                make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                    hp_death_hypothesis_scenario=candidate,
                )

    def test_the_runtime_lane_sits_behind_the_scenario_gate(self):
        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn("if hp_death_hypothesis_scenario is not None:", source)
        self.assertEqual(source.count("make_hp_death_step_response("), 1)
        self.assertEqual(
            source.count("# PF-HYPOTHESIS-LEDGER: HYP-PF-022 active"), 1,
        )

    def test_the_cli_flag_demands_an_explicit_existing_database(self):
        source = (
            ROOT / "src" / "pirateforce_foundation" / "app.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "'--hp-death-hypothesis-scenario requires an explicit existing "
            "--db'",
            source,
        )
        self.assertIn("--hp-death-hypothesis-scenario", source)


if __name__ == "__main__":
    unittest.main()
