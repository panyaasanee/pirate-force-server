"""STATS-PROG-002 (HYP-PF-020) -- runtime wire hookup for the progression sweep.

``tests/test_stats_progression_hypothesis.py`` proves the encoder offline.  This
module drives the REAL ``make_state_class`` dispatch path behind the opt-in
``scenarios/stats_progression_hypothesis_xp_sweep.json`` and proves the wire
layer end to end, headless -- no server process, no socket, no client:

  * one accepted chat-input frame (the exact 34-byte ascii12 shape the
    HYP-PF-014 lane already classifies, reused because it is the only client
    action an attended tester can trigger on demand) produces exactly NINE
    actions, in the scenario's step order, spaced by ``spacing_seconds``;
  * every dispatched frame carries vital id 0x309A with an ``ActorAttr``
    collection, and the Attr body at the fixed envelope offset re-decodes to
    the cumulative field set that step declares -- so the claim "the server can
    put level / experience / the five ability values on the wire" is checked on
    bytes this dispatcher produced, not on a unit fixture;
  * the baseline frame's body is byte-identical to the ``player_wire``
    projection the client has been accepting since NAME-002;
  * all twenty-seven per-step hashes (body, PC, frame) match the scenario pins,
    because the fresh-store harness reproduces the pinned probe identity
    exactly;
  * fail-closed and containment: wrong length, wrong prefix, wrong text bytes,
    wrong envelope, no selected character and not-yet-runtime-ready all give
    ``[]`` with a named no-reply event; with no scenario the baseline is
    byte-identical; the database file does not move one byte across accepted
    and refused windows; the lane is not one-shot; and it is mutually exclusive
    with every other scenario mode.

NOT proven here, and this is the load-bearing limit: whether the real client's
XP bar, level number or ability rows move.  That is GT-017, attended, not run.
This file proves only that the bytes leave the server.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PREFIX,
    CHAT_INPUT_PROBE_PAYLOADS,
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    make_actor_attr_with_name,
)
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.stats_progression_hypothesis import (  # noqa: E402
    ACTOR_ATTR_ID,
    STATS_PC_ATTR_BODY_OFFSET,
    STATS_PROBE_ACTOR,
    STATS_PROBE_ATTR_BODY_SHA256,
    STATS_PROBE_ATTR_BODY_SIZE,
    STATS_PROBE_FRAME_SHA256,
    STATS_PROBE_PC_SHA256,
    STATS_PROGRESSION_ACTION_LABEL_PREFIX,
    STATS_PROGRESSION_FIRST_DELAY_SECONDS,
    STATS_PROGRESSION_SPACING_SECONDS,
    STATS_PROGRESSION_STEP_ORDER,
    StatsProgressionActor,
    UPDATE_ATTR_VITAL_ID,
    decode_actor_attr,
    load_stats_progression_hypothesis_scenario,
    make_stats_progression_step_response,
    stats_progression_step_fields,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "stats_progression_hypothesis_xp_sweep.json"
)
SWEEP_EVENT = "stats_progression_hypothesis_xp_sweep_sent"
PC_VITAL_ID_SLICE = slice(16, 18)


class StatsProgressionRuntimeTests(unittest.TestCase):
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
        self.scenario = load_stats_progression_hypothesis_scenario(
            SCENARIO_PATH
        )
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ---------------------------------------------------------

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            stats_progression_hypothesis_scenario=(
                self.scenario if sweep else None
            ),
        )

    def _state(self, login, *, sweep=True, ready=True):
        state = self._state_type(sweep=sweep)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(state.foundation.account_id)
        self.assertEqual(len(characters), 1)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

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

    def _trigger(self, probe="probe1"):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

    def _body(self, pc, label):
        size = STATS_PROBE_ATTR_BODY_SIZE[label]
        return pc[STATS_PC_ATTR_BODY_OFFSET:STATS_PC_ATTR_BODY_OFFSET + size]

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    # ----- happy path ------------------------------------------------------

    def test_one_request_sweeps_the_nine_steps_in_the_pinned_order(self):
        state = self._state("stats01")
        session_id = state.foundation.session_id
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 9)
        self.assertEqual(
            [action[0] for action in actions],
            [
                STATS_PROGRESSION_ACTION_LABEL_PREFIX + label
                for label in STATS_PROGRESSION_STEP_ORDER
            ],
        )
        self.assertEqual(
            [action[0] for action in actions],
            self.pinned["dispatch"]["action_labels"],
        )
        self.assertEqual(
            [action[0] for action in actions],
            [
                "HYP_PF_020_STATS_PROG_BASELINE",
                "HYP_PF_020_STATS_PROG_EXPERIENCE_1",
                "HYP_PF_020_STATS_PROG_EXPERIENCE_2",
                "HYP_PF_020_STATS_PROG_LEVEL",
                "HYP_PF_020_STATS_PROG_ABILITY_STR",
                "HYP_PF_020_STATS_PROG_ABILITY_CON",
                "HYP_PF_020_STATS_PROG_ABILITY_DEX",
                "HYP_PF_020_STATS_PROG_ABILITY_INT",
                "HYP_PF_020_STATS_PROG_ABILITY_PER",
            ],
        )
        self.assertEqual(state.stats_progression_sweep_count, 1)
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertIsNone(self._session_closed_at(session_id))

    def test_every_dispatched_frame_is_an_update_attr_vital_actor_attr(self):
        state = self._state("stats-ids")
        actions = state.dispatch(self._trigger())
        for label, action in zip(STATS_PROGRESSION_STEP_ORDER, actions):
            pc = action[1]
            self.assertEqual(
                pc[PC_VITAL_ID_SLICE],
                UPDATE_ATTR_VITAL_ID.to_bytes(2, "little"), label,
            )
            self.assertIn(
                self.legacy.u16tag(0x12, ACTOR_ATTR_ID), pc[20:], label,
            )
        self.assertEqual(
            self.pinned["wire"]["vital_id"], UPDATE_ATTR_VITAL_ID,
        )

    def test_the_dispatched_bodies_decode_to_the_declared_field_sets(self):
        # THE claim of this milestone, checked on dispatched bytes: level,
        # experience and the five ability values are on the wire, with the
        # values the scenario declares, in mask-gated sparse form.
        state = self._state("stats-decode")
        actions = state.dispatch(self._trigger())
        actor = STATS_PROBE_ACTOR
        for index, (label, action) in enumerate(
            zip(STATS_PROGRESSION_STEP_ORDER, actions)
        ):
            expected = stats_progression_step_fields(self.legacy, actor, index)
            decoded = decode_actor_attr(self._body(action[1], label))
            self.assertEqual(
                decoded, (actor.identity_lo, actor.identity_hi, expected), label,
            )
        last = decode_actor_attr(self._body(actions[-1][1], "ABILITY_PER"))[2]
        self.assertEqual(last["level"], 7)
        self.assertEqual(last["experience"], 987654)
        self.assertEqual(
            [last[name] for name in (
                "ability_str", "ability_con", "ability_dex", "ability_int",
                "ability_per",
            )],
            [11, 22, 33, 44, 55],
        )

    def test_the_baseline_frame_is_the_proven_player_wire_projection(self):
        state = self._state("stats-baseline")
        actions = state.dispatch(self._trigger())
        body = self._body(actions[0][1], "BASELINE")
        characters = self.store.list_characters(state.foundation.account_id)
        character = characters[0]
        self.assertEqual(
            body,
            make_actor_attr_with_name(
                self.legacy, character.identity_lo, character.identity_hi,
                character.position.scene_id, character.position.scene_seq,
                character.name,
            ),
        )

    def test_every_dispatched_frame_matches_its_scenario_pin(self):
        state = self._state("stats-pins")
        actions = state.dispatch(self._trigger())
        per_step = self.pinned["probe"]["per_step"]
        for label, action in zip(STATS_PROGRESSION_STEP_ORDER, actions):
            _name, pc, frame, _delay = action
            self.assertEqual(len(pc), per_step[label]["pc_size"], label)
            self.assertEqual(len(frame), per_step[label]["frame_size"], label)
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                per_step[label]["pc_sha256"], label,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                per_step[label]["frame_sha256"], label,
            )
            self.assertEqual(
                hashlib.sha256(self._body(pc, label)).hexdigest().upper(),
                per_step[label]["attr_body_sha256"], label,
            )
            # ...and the same pins the module carries, independently.
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                STATS_PROBE_PC_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                STATS_PROBE_FRAME_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(self._body(pc, label)).hexdigest().upper(),
                STATS_PROBE_ATTR_BODY_SHA256[label], label,
            )

    def test_the_dispatched_frames_are_the_documented_composer_output(self):
        state = self._state("stats-composer")
        actions = state.dispatch(self._trigger("probe2"))
        for index, action in enumerate(actions):
            expected = make_stats_progression_step_response(
                self.legacy, STATS_PROBE_ACTOR, index,
            )
            self.assertEqual((action[1], action[2]), expected, index)

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("stats-spacing")
        actions = state.dispatch(self._trigger())
        delays = [action[3] for action in actions]
        self.assertEqual(
            delays,
            [STATS_PROGRESSION_FIRST_DELAY_SECONDS]
            + [STATS_PROGRESSION_SPACING_SECONDS] * 8,
        )
        self.assertEqual(
            delays[0], self.pinned["dispatch"]["first_frame_delay_seconds"],
        )
        self.assertEqual(
            set(delays[1:]), {self.pinned["dispatch"]["spacing_seconds"]},
        )
        self.assertEqual(sum(delays), 8 * STATS_PROGRESSION_SPACING_SECONDS)

    def test_the_request_payload_is_a_trigger_not_an_input(self):
        # Two different accepted chat payloads must produce byte-identical
        # sweeps: nothing from the request reaches the wire.
        state = self._state("stats-trigger")
        first = state.dispatch(self._trigger("probe1"))
        second = state.dispatch(self._trigger("probe2"))
        other = CHAT_INPUT_PREFIX + "HELLO WORLD!".encode("utf-16-le")
        third = state.dispatch(
            self.legacy.parse_outer(self._trigger_pc(other))
        )
        self.assertEqual(first, second)
        self.assertEqual(first, third)
        self.assertEqual(state.stats_progression_sweep_count, 3)

    # ----- repeatability ---------------------------------------------------

    def test_two_requests_give_eighteen_frames_with_no_accumulated_state(self):
        state = self._state("stats-repeat")
        first = state.dispatch(self._trigger("probe1"))
        second = state.dispatch(self._trigger("probe1"))
        self.assertEqual([len(first), len(second)], [9, 9])
        self.assertEqual(len(first) + len(second), 18)
        self.assertEqual(first, second)
        self.assertEqual(state.stats_progression_sweep_count, 2)
        self.assertEqual(state.events.count(SWEEP_EVENT), 2)

    def test_the_sweep_writes_nothing_to_the_database(self):
        state = self._state("stats-nowrite")
        session_id = state.foundation.session_id
        before = self.db_path.read_bytes()
        state.dispatch(self._trigger("probe1"))
        state.dispatch(self._trigger("probe2"))
        state.dispatch(self._trigger("probe1"))
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(state.stats_progression_sweep_count, 3)

    def test_a_refused_frame_also_writes_nothing(self):
        state = self._state("stats-nowrite-refused")
        before = self.db_path.read_bytes()
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], bytes([base[0] ^ 0x01]) + base[1:]):
            self.assertEqual(
                state.dispatch(
                    self.legacy.parse_outer(self._trigger_pc(payload))
                ),
                [],
            )
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertEqual(state.stats_progression_sweep_count, 0)

    # ----- fail closed -----------------------------------------------------

    def _assert_silent(self, state, parsed, event):
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn(event, state.events)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.stats_progression_sweep_count, 0)

    def test_wrong_length_fails_closed(self):
        state = self._state("stats-length")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], base + b"A\x00", b"", base[:5]):
            self._assert_silent(
                state, self.legacy.parse_outer(self._trigger_pc(payload)),
                "stats_progression_hypothesis_wrong_length_no_reply",
            )
        self.assertEqual(
            state.events.count(
                "stats_progression_hypothesis_wrong_length_no_reply"
            ),
            4,
        )

    def test_wrong_prefix_fails_closed(self):
        state = self._state("stats-prefix")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        tampered = bytes([base[0] ^ 0x01]) + base[1:]
        self.assertEqual(len(tampered), 34)
        self._assert_silent(
            state, self.legacy.parse_outer(self._trigger_pc(tampered)),
            "stats_progression_hypothesis_wrong_prefix_no_reply",
        )

    def test_wrong_text_bytes_fail_closed(self):
        state = self._state("stats-text")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (
            base[:11] + b"\x01" + base[12:],
            base[:10] + b"\x1f" + base[11:],
            base[:10] + b"\x7f" + base[11:],
        ):
            self.assertEqual(len(payload), 34)
            self._assert_silent(
                state, self.legacy.parse_outer(self._trigger_pc(payload)),
                "stats_progression_hypothesis_wrong_text_no_reply",
            )

    def test_wrong_envelope_fails_closed(self):
        state = self._state("stats-envelope")
        payload = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for pc in (
            self._trigger_pc(payload, nested_version=1),
            self._trigger_pc(payload, outer_version=1),
            self._trigger_pc(payload, outer_id=self.legacy.GSCN_LOGIN_PROTOCOL),
        ):
            self._assert_silent(
                state, self.legacy.parse_outer(pc),
                "stats_progression_hypothesis_wrong_envelope_no_reply",
            )
        self.assertEqual(
            state.events.count(
                "stats_progression_hypothesis_wrong_envelope_no_reply"
            ),
            3,
        )

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("stats-seq", ready=False)
        self._assert_silent(
            state, self._trigger(),
            "stats_progression_hypothesis_wrong_sequence_no_reply",
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state_type()("stats-noselect")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertIsNone(state.foundation.selected)
        self._assert_silent(
            state, self._trigger(),
            "stats_progression_hypothesis_no_selected_no_reply",
        )

    def test_no_refusal_path_ever_emits_a_sweep_event(self):
        state = self._state("stats-refusals")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (
            base[:-2],
            bytes([base[0] ^ 0x01]) + base[1:],
            base[:10] + b"\x1f" + base[11:],
        ):
            self.assertEqual(
                state.dispatch(
                    self.legacy.parse_outer(self._trigger_pc(payload))
                ),
                [],
            )
        self.assertEqual(state.events.count(SWEEP_EVENT), 0)
        for event in state.events:
            self.assertNotIn("sweep", event)

    # ----- containment -----------------------------------------------------

    def test_without_a_scenario_the_baseline_does_not_move(self):
        state = self._state("stats-off", sweep=False)
        rx_before = state.rx_frames
        events_before = list(state.events)
        before = self.db_path.read_bytes()
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [a for a in actions if a[0].startswith("HYP_PF_020")], [],
        )
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(state.stats_progression_sweep_count, 0)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(
            [e for e in state.events[len(events_before):]
             if "stats_progression" in e],
            [],
        )
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_the_lane_is_mutually_exclusive_with_every_other_mode(self):
        from pirateforce_foundation.channel_message_hypothesis import (
            load_channel_message_hypothesis_scenario,
        )
        from pirateforce_foundation.chat_input_hypothesis import (
            load_chat_input_hypothesis_scenario,
        )
        from pirateforce_foundation.logout_hypothesis import (
            load_logout_hypothesis_scenario,
        )
        others = {
            "chat_input_hypothesis_scenario": load_chat_input_hypothesis_scenario(
                ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
            ),
            "channel_message_hypothesis_scenario": (
                load_channel_message_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "channel_message_hypothesis_channel_sweep.json"
                )
            ),
            "logout_hypothesis_scenario": load_logout_hypothesis_scenario(
                ROOT / "scenarios" / "logout_hypothesis_ack_echo.json"
            ),
        }
        for name, other in others.items():
            with self.subTest(mode=name):
                with self.assertRaises(ValueError) as raised:
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        stats_progression_hypothesis_scenario=self.scenario,
                        **{name: other},
                    )
                self.assertIn("mutually exclusive", str(raised.exception))

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        from dataclasses import replace

        for bad in (
            object(),
            replace(self.scenario, spacing_seconds=0.25),
            replace(self.scenario, step_order=STATS_PROGRESSION_STEP_ORDER[:2]),
            replace(self.scenario, hypothesis_id="HYP-PF-019"),
        ):
            with self.assertRaises(ValueError):
                make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                    stats_progression_hypothesis_scenario=bad,
                )

    def test_the_probe_identity_the_pins_use_is_the_one_the_harness_makes(self):
        # The pins are only meaningful if the identity they were computed for
        # is the identity a fresh store actually hands out.
        state = self._state("stats-identity")
        character = self.store.list_characters(state.foundation.account_id)[0]
        self.assertEqual(
            StatsProgressionActor(
                character.identity_lo, character.identity_hi,
                character.position.scene_id, character.position.scene_seq,
                character.name,
            ),
            STATS_PROBE_ACTOR,
        )


if __name__ == "__main__":
    unittest.main()
