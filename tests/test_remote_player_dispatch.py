"""REMOTE-PLAYER-DISPATCH-001 (HYP-PF-025) -- the visibility sweep on the
dispatcher.

``tests/test_remote_player_hypothesis.py`` proves the encoder offline.  This
file drives the REAL ``make_state_class`` dispatch path behind the opt-in
``scenarios/remote_player_hypothesis_visibility_probe.json`` and proves the
wire layer end to end, headless -- no server process, no socket, no client:

  * one accepted chat-input frame (the exact 34-byte ascii12 shape the
    HYP-PF-014 lane already classifies, reused because it is the only client
    action an attended tester can trigger on demand) produces exactly FIVE
    actions, in the scenario's order, spaced by ``spacing_seconds``;
  * the bytes the dispatcher emits are **identical** to the bytes
    ``build_remote_player_sweep`` composes from the selected character's own
    avatar wire and qword identity -- label, PC, frame and delay, compared
    with ``==`` on the bytes themselves.  The dispatcher is a forwarder, and
    if it ever becomes a second composer these tests go red;
  * every frame is ``GSCN_RunTimeProtocolRes`` 0x6E9D v4 with the inherited
    change mask ``0x00``, the derived change mask bit ``0x02``, and ONE
    ``actor_type 2`` entry;
  * the refusal ladder fires in its pinned order, each rung with its named
    no-reply event: a frame that is not the accepted ascii12 shape, then no
    selected character, then the sequence flags, then the one-shot latch;
  * a compose-time refusal (an invalid avatar wire) is turned into a named
    ``compose_refused`` event, returns nothing, and does NOT burn the
    one-shot: a later valid trigger still sends;
  * containment: with the scenario absent the same accepted frame produces
    no HYP_PF_025 label and no sweep byte; the other chat-keyed lanes are
    mutually exclusive at construction and their counters never move while
    this lane is active; the database gains no row in any table; and the
    lane takes no socket action.

NOT proven here, and this is the load-bearing limit: whether a real client
renders anything at all when it receives these bytes.  **No client has ever
been shown one byte of this profile.**  That is the attended test, not run.
"""
from __future__ import annotations

import dataclasses
import hashlib
import inspect
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.actor_wire import (  # noqa: E402
    bind_common_attr_identity,
)
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
from pirateforce_foundation import remote_player_hypothesis as rph  # noqa: E402
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "remote_player_hypothesis_visibility_probe.json"
)
HP_DEATH_SCENARIO_PATH = (
    ROOT / "scenarios" / "hp_death_hypothesis_death_sweep.json"
)
SWEEP_EVENT = "remote_player_hypothesis_visibility_probe_sent"
REPEAT_EVENT = "remote_player_hypothesis_already_sent_no_reply"
EVENT_PREFIX = "remote_player_hypothesis_"
COMPOSE_REFUSED_PREFIX = "remote_player_hypothesis_compose_refused_no_reply_"


class RemotePlayerDispatchTests(unittest.TestCase):
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
        self.scenario = rph.load_remote_player_hypothesis_scenario(
            SCENARIO_PATH
        )
        self.unlock = rph.remote_player_wire_unlock(self.scenario)
        self.probes = rph.resolve_probes(self.legacy)
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ---------------------------------------------------------

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            remote_player_hypothesis_scenario=(
                self.scenario if sweep else None
            ),
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
            self._select(state)
        state.runtime_ack_sent = ready
        return state

    def _select(self, state):
        characters = self.store.list_characters(state.foundation.account_id)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[-1].selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")

    def _trigger(self, probe="probe1"):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

    def _trigger_pc(self, payload, *, outer_version=0, nested_version=0):
        legacy = self.legacy
        return bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, outer_version)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, CHAT_INPUT_VITAL_ID)
            + legacy.u8tag(0x0B, nested_version)
            + payload
        )

    def _expected(self, state):
        """The encoder's composition, built without the dispatcher, from the
        very inputs the dispatcher must use: the selected character's own
        avatar wire and qword identity."""
        selected = state.foundation.selected
        self.assertIsNotNone(selected)
        return rph.build_remote_player_sweep(
            self.legacy, self.probes, self.unlock, self.scenario,
            avatar_wire=selected.avatar_wire,
            selected_identity=(
                (int(selected.identity_hi) << 32) | int(selected.identity_lo)
            ),
        )

    def _db_digest(self):
        return hashlib.sha256(self.db_path.read_bytes()).hexdigest()

    def _table_row_counts(self):
        connection = sqlite3.connect(str(self.db_path))
        try:
            tables = [
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "ORDER BY name"
                )
            ]
            return {
                table: connection.execute(
                    'SELECT COUNT(*) FROM "%s"' % table
                ).fetchone()[0]
                for table in tables
            }
        finally:
            connection.close()

    def _refused(self, state, parsed, event_fragment):
        before = self._db_digest()
        counts_before = self._table_row_counts()
        self.assertEqual(state.dispatch(parsed), [])
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertTrue(
            any(event_fragment in event for event in state.events),
            state.events,
        )
        self.assertEqual(state.remote_player_sweep_count, 0)
        self.assertEqual(self._db_digest(), before)
        self.assertEqual(self._table_row_counts(), counts_before)

    # ----- wiring ----------------------------------------------------------

    def test_make_state_class_accepts_the_remote_player_kwarg(self):
        parameters = inspect.signature(make_state_class).parameters
        self.assertEqual(
            rph.REMOTE_PLAYER_DISPATCH_KWARG,
            "remote_player_hypothesis_scenario",
        )
        self.assertIn(rph.REMOTE_PLAYER_DISPATCH_KWARG, parameters)
        self.assertIsNone(
            parameters[rph.REMOTE_PLAYER_DISPATCH_KWARG].default,
        )

    def test_the_mutual_exclusion_error_names_the_remote_player_lane(self):
        hp_death = sp.load_hp_death_hypothesis_scenario(HP_DEATH_SCENARIO_PATH)
        with self.assertRaises(ValueError) as ctx:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                remote_player_hypothesis_scenario=self.scenario,
                hp_death_hypothesis_scenario=hp_death,
            )
        self.assertIn("mutually exclusive", str(ctx.exception))
        self.assertIn("remote player hypothesis", str(ctx.exception))

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        for candidate in (
            object(),
            rph.REMOTE_PLAYER_SCENARIO_ID,
            rph.RemotePlayerHypothesisScenario(
                rph.REMOTE_PLAYER_SCENARIO_ID,
                rph.REMOTE_PLAYER_HYPOTHESIS_ID,
                ("NEGATIVE_CONTROL", "SPAWN_BARE"), 15.0, 0.0,
                rph.REMOTE_PLAYER_ACTION_LABEL_PREFIX,
            ),
        ):
            with self.subTest(candidate=type(candidate).__name__):
                with self.assertRaises(ValueError):
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        remote_player_hypothesis_scenario=candidate,
                    )

    # ----- happy path ------------------------------------------------------

    def test_one_request_sweeps_the_five_steps_in_the_pinned_order(self):
        state = self._state("rp01")
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 5)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            list(rph.REMOTE_PLAYER_ACTION_LABELS),
        )
        self.assertEqual(
            list(rph.REMOTE_PLAYER_STEP_ORDER),
            ["SPAWN_BARE", "SPAWN_AVATAR", "MOVE_A_1", "MOVE_A_2",
             "NEGATIVE_CONTROL"],
        )
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.remote_player_sweep_count, 1)

    def test_the_dispatched_bytes_are_the_encoders_bytes(self):
        """The dispatcher forwards; it does not compose a sweep of its own."""
        state = self._state("rp02")
        expected = self._expected(state)
        self.assertEqual(state.dispatch(self._trigger()), expected)

    def test_every_dispatched_frame_is_a_walkable_actor_type_2_frame(self):
        state = self._state("rp03")
        identities = set()
        for label, pc, frame, _delay in state.dispatch(self._trigger()):
            with self.subTest(step=label):
                read = rph.decode_remote_player_actor_entry_frame(pc)
                self.assertEqual(read["actor_type"], 2)
                self.assertEqual(pc[0], 0x12)
                self.assertEqual(int.from_bytes(pc[1:3], "little"), 0x6E9D)
                self.assertEqual(pc[9], rph.RUNTIME_PROTOCOL_RES_VERSION)
                self.assertEqual(
                    pc[rph.INHERITED_CHANGE_MASK_OFFSET],
                    rph.INHERITED_CHANGE_MASK_ABSENT,
                )
                self.assertEqual(
                    pc[rph.DERIVED_CHANGE_MASK_OFFSET],
                    rph.DERIVED_CHANGE_MASK_ACTOR_ENTRIES,
                )
                self.assertEqual(frame, self.legacy.frame_pc(pc))
                identities.add(read["identity"])
        self.assertEqual(identities, {
            rph.PROBE_IDENTITY_A, rph.PROBE_IDENTITY_B, rph.PROBE_IDENTITY_C,
        })

    def test_the_dispatched_frames_reproduce_the_pins(self):
        state = self._state("rp04")
        actions = state.dispatch(self._trigger())
        rows = rph.validate_remote_player_sweep(
            actions, self.scenario, self.probes,
        )
        for index, step in enumerate(rph.REMOTE_PLAYER_STEP_ORDER):
            pin = rph.REMOTE_PLAYER_PINS[step]
            with self.subTest(step=step):
                for key, expected in pin.items():
                    self.assertEqual(rows[index].get(key), expected, key)
                self.assertEqual(
                    self.pinned["probe"]["per_step"][step], pin,
                )

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("rp05")
        delays = [d for _l, _p, _f, d in state.dispatch(self._trigger())]
        self.assertEqual(delays, [0.0, 15.0, 15.0, 15.0, 15.0])
        self.assertEqual(delays[0], self.scenario.first_delay_seconds)
        self.assertTrue(
            all(d == self.scenario.spacing_seconds for d in delays[1:])
        )

    def test_the_avatar_step_replays_the_selected_characters_wire(self):
        """SPAWN_AVATAR's tail is the selected character's own opaque avatar
        wire, rebound to probe B, and it is the LAST attr of its entry."""
        state = self._state("rp06")
        selected = state.foundation.selected
        actions = state.dispatch(self._trigger())
        pc = actions[1][1]
        read = rph.decode_remote_player_actor_entry_frame(pc)
        self.assertEqual(read["attr_order"][-1], rph.AVATAR_ATTR_ID)
        avatar = read["attrs"][rph.AVATAR_ATTR_ID]
        self.assertEqual(avatar["identity"], rph.PROBE_IDENTITY_B)
        rebound = bind_common_attr_identity(
            selected.avatar_wire, rph.PROBE_IDENTITY_B & 0xFFFFFFFF,
            rph.PROBE_IDENTITY_B >> 32,
        )
        self.assertEqual(avatar["body_size"], len(rebound))
        self.assertEqual(pc[-len(rebound):], rebound)

    def test_the_request_payload_is_a_trigger_not_an_input(self):
        # Two fresh sessions, because the sweep is one-shot: the only thing
        # that differs between them is the request payload, and it must not
        # change one byte of the answer.
        first = self._state("rp07").dispatch(self._trigger("probe1"))
        second = self._state("rp08").dispatch(self._trigger("probe2"))
        self.assertEqual(
            [pc for _l, pc, _f, _d in first],
            [pc for _l, pc, _f, _d in second],
        )

    def test_the_sweep_takes_no_socket_action(self):
        state = self._state("rp09")
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 5)
        self.assertTrue(all(len(action) == 4 for action in actions))

    # ----- the refusal ladder ----------------------------------------------

    def test_a_wrong_length_frame_fails_closed_with_its_classification(self):
        state = self._state("rp10")
        payload = bytes(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])[-33:]
        self._refused(
            state, self.legacy.parse_outer(self._trigger_pc(payload)),
            "remote_player_hypothesis_wrong_length_no_reply",
        )

    def test_wrong_text_bytes_fail_closed_with_their_classification(self):
        state = self._state("rp11")
        pc = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        pc[-1] ^= 0xFF
        self._refused(
            state, self.legacy.parse_outer(bytes(pc)),
            "remote_player_hypothesis_wrong_text_no_reply",
        )

    def test_a_wrong_envelope_fails_closed_with_its_classification(self):
        state = self._state("rp12")
        payload = bytes(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])[-34:]
        self._refused(
            state,
            self.legacy.parse_outer(self._trigger_pc(payload, outer_version=1)),
            "remote_player_hypothesis_wrong_envelope_no_reply",
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state("rp13", select=False)
        self._refused(
            state, self._trigger(),
            "remote_player_hypothesis_no_selected_no_reply",
        )

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("rp14", ready=False)
        self._refused(
            state, self._trigger(),
            "remote_player_hypothesis_wrong_sequence_no_reply",
        )

    def test_the_ladder_fires_in_its_pinned_order_on_one_session(self):
        """One session, five rungs: classification, selection, sequence,
        the send, the one-shot latch -- each with its named event."""
        state = self._state("rp15", select=False, ready=False)
        bad = bytes(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])[-33:]
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(self._trigger_pc(bad))), [],
        )
        self.assertEqual(
            state.events[-1],
            "remote_player_hypothesis_wrong_length_no_reply",
        )
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(
            state.events[-1],
            "remote_player_hypothesis_no_selected_no_reply",
        )
        self._select(state)
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(
            state.events[-1],
            "remote_player_hypothesis_wrong_sequence_no_reply",
        )
        state.runtime_ack_sent = True
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 5)
        self.assertEqual(state.events[-1], SWEEP_EVENT)
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.events[-1], REPEAT_EVENT)
        self.assertEqual(state.remote_player_sweep_count, 1)

    def test_the_sweep_is_one_shot(self):
        """A second sweep would re-name identities the client now knows and
        turn the spawn steps into vtable +0x20 updates, so a repeat trigger
        must emit nothing at all, and must say so."""
        state = self._state("rp16")
        self.assertEqual(len(state.dispatch(self._trigger())), 5)
        before = self._db_digest()
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.dispatch(self._trigger("probe2")), [])
        self.assertEqual(state.remote_player_sweep_count, 1)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)
        self.assertEqual(state.events.count(REPEAT_EVENT), 2)
        self.assertEqual(self._db_digest(), before)

    def test_no_refusal_path_ever_composes_a_probe_frame(self):
        for login, kwargs in (
            ("rp17", {"ready": False}), ("rp18", {"select": False}),
        ):
            with self.subTest(**kwargs):
                state = self._state(login, **kwargs)
                self.assertEqual(state.dispatch(self._trigger()), [])
                self.assertEqual(state.remote_player_sweep_count, 0)

    # ----- the compose-refusal path ----------------------------------------

    def test_a_compose_refusal_names_itself_and_keeps_the_shot(self):
        """An invalid avatar wire refuses by name, returns nothing, and does
        NOT advance the one-shot counter: a later valid trigger still sends.
        """
        state = self._state("rp19")
        genuine = state.foundation.selected
        state.foundation.selected = dataclasses.replace(
            genuine, avatar_wire=b"junk",
        )
        counts_before = self._table_row_counts()
        self.assertEqual(state.dispatch(self._trigger()), [])
        refusals = [
            event for event in state.events
            if event.startswith(COMPOSE_REFUSED_PREFIX)
        ]
        self.assertEqual(len(refusals), 1)
        self.assertIn(
            "avatar_wire_absent_or_not_a_common_attr_body", refusals[0],
        )
        self.assertEqual(state.remote_player_sweep_count, 0)
        self.assertNotIn(SWEEP_EVENT, state.events)
        # A second broken trigger refuses again: the shot was not burned.
        self.assertEqual(state.dispatch(self._trigger("probe2")), [])
        self.assertEqual(state.remote_player_sweep_count, 0)
        self.assertEqual(len([
            event for event in state.events
            if event.startswith(COMPOSE_REFUSED_PREFIX)
        ]), 2)
        self.assertEqual(self._table_row_counts(), counts_before)
        # With the real character back, the third valid trigger still sends.
        state.foundation.selected = genuine
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 5)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            list(rph.REMOTE_PLAYER_ACTION_LABELS),
        )
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.remote_player_sweep_count, 1)

    # ----- containment -----------------------------------------------------

    def test_the_lane_composes_nothing_without_the_scenario(self):
        """Two independent locks.  (a) With no scenario the trigger keeps its
        frozen baseline answer: no HYP_PF_025 label, no sweep event, no byte
        of the sweep.  (b) Even a direct call into the dispatch method cannot
        emit anything, because the scenario and the unlock are closed over as
        None and the composer refuses -- the method fails closed with a named
        compose_refused event and an empty reply."""
        state = self._state("rp20", sweep=False)
        expected_pcs = {pc for _l, pc, _f, _d in self._expected(state)}
        actions = state.dispatch(self._trigger())
        self.assertFalse([
            label for label, _p, _f, _d in actions
            if label.startswith(rph.REMOTE_PLAYER_ACTION_LABEL_PREFIX)
        ])
        self.assertFalse(
            {pc for _l, pc, _f, _d in actions} & expected_pcs
        )
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.remote_player_sweep_count, 0)
        self.assertEqual(
            state._dispatch_remote_player_hypothesis(self._trigger()), [],
        )
        self.assertTrue(any(
            event.startswith(COMPOSE_REFUSED_PREFIX)
            for event in state.events
        ))
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.remote_player_sweep_count, 0)

    def test_no_other_chat_keyed_lane_is_reachable_while_this_one_runs(self):
        """The five other lanes keyed on vital 0xAC52 are refused at
        construction (mutual exclusion), so while this lane is active the
        accepted frame reaches ONLY the remote player dispatcher."""
        state = self._state("rp21")
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            list(rph.REMOTE_PLAYER_ACTION_LABELS),
        )
        for counter in (
            "chat_input_echo_count", "channel_message_sweep_count",
            "stats_progression_sweep_count", "hp_death_sweep_count",
            "runtimeres_death_sweep_count", "damage_model_sweep_count",
        ):
            with self.subTest(counter=counter):
                self.assertEqual(getattr(state, counter), 0)
        foreign = (
            "chat_input_hypothesis_", "channel_message_hypothesis_",
            "stats_progression_hypothesis_", "hp_death_hypothesis_",
            "runtimeres_death_hypothesis_", "damage_model_hypothesis_",
        )
        for event in state.events:
            self.assertFalse(event.startswith(foreign), event)

    def test_the_sweep_writes_no_row_to_any_table(self):
        state = self._state("rp22")
        counts_before = self._table_row_counts()
        digest_before = self._db_digest()
        # The comparison must have teeth: the session harness has already
        # written an account, a session and a character.
        self.assertTrue(any(count > 0 for count in counts_before.values()))
        self.assertEqual(len(state.dispatch(self._trigger())), 5)
        self.assertEqual(self._table_row_counts(), counts_before)
        self.assertEqual(self._db_digest(), digest_before)

    # ----- the wiring, read from the source --------------------------------

    def test_the_runtime_lane_sits_behind_the_scenario_gate(self):
        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "remote_player_hypothesis_scenario is not None", source,
        )
        # Exactly one call site, inside the branch: the dispatcher composes
        # nowhere else and nothing else composes for it.
        self.assertEqual(source.count("build_remote_player_sweep("), 1)
        self.assertEqual(
            source.count("def _dispatch_remote_player_hypothesis("), 1,
        )
        # One ledger annotation per file, on the dispatch method, exactly as
        # the HYP-PF-022/023/024 lanes carry theirs.
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-025 active"), 1,
        )

    def test_the_app_flag_is_live_and_still_demands_an_existing_database(self):
        source = (
            ROOT / "src" / "pirateforce_foundation" / "app.py"
        ).read_text(encoding="utf-8")
        self.assertIn("--remote-player-hypothesis-scenario", source)
        self.assertIn(
            "'--remote-player-hypothesis-scenario requires an explicit '",
            source,
        )
        self.assertIn(
            "remote_player_hypothesis_scenario=remote_player_hypothesis,",
            source,
        )
        self.assertIn(
            "'--remote-player-hypothesis-scenario are mutually exclusive'",
            source,
        )
        # Exactly one, for the same reason as the runtime.py assertion above.
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-025 active"), 1,
        )


if __name__ == "__main__":
    unittest.main()
