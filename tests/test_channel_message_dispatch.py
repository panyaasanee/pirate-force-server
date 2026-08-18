"""CHAT-CHANNEL-003 (HYP-PF-019) -- runtime wire hookup for the channel sweep.

CHAT-CHANNEL-002 built the shared-serializer codec and deliberately left it
unreachable: nothing imported it, so no composed channel frame could ever
leave the process and GT-016 stayed BLOCKED.  This module drives the REAL
dispatch path behind the new opt-in
``scenarios/channel_message_hypothesis_channel_sweep.json`` and proves the
wire layer end to end, headless:

  * one accepted chat-input frame (the exact 34-byte ascii12 0xAC52 shape the
    HYP-PF-014 lane already classifies) produces exactly FIVE actions, in the
    scenario's channel order, spaced by ``spacing_seconds``;
  * the five nested payloads are identical BYTE FOR BYTE -- same 34 bytes,
    same sha256 -- because the speaker is empty on all five;
  * the five composed PCs differ in exactly TWO bytes, ``pc[16:18]``, the
    16-bit class id, which is CHAT-CHANNEL-001's "the channel id IS the
    selector" conclusion re-proven on bytes this server produced under
    dispatch rather than in a unit fixture;
  * all ten per-channel PC/frame hashes match the scenario pins;
  * the body is DECODED out of the request payload rather than spliced.

Fail-closed and containment are proven the same way: wrong length, wrong
prefix, wrong text bytes, wrong envelope, no selected character and
not-yet-runtime-ready all produce ``[]`` with a named no-reply event and no
frame; with no scenario at all the baseline is byte-identical (zero actions,
zero events); the database file is byte-identical across a whole sweep
window; a one-field-tampered scenario never loads; and the lane is not
one-shot -- two requests give ten frames with no accumulated state.

NOT proven here, and this is the load-bearing limit: whether the real client
renders any of the five lines.  That is GT-016, attended, not run.  This file
proves only that the bytes leave the server.
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

from pirateforce_foundation.channel_message_hypothesis import (  # noqa: E402
    CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET,
    CHANNEL_MESSAGE_PROBE1_FRAME_SHA256,
    CHANNEL_MESSAGE_PROBE1_PC_SHA256,
    CHANNEL_MESSAGE_PROBE_BODIES,
    CHANNEL_SWEEP_ACTION_LABEL_PREFIX,
    CHANNEL_SWEEP_FIRST_DELAY_SECONDS,
    CHANNEL_SWEEP_ORDER,
    CHANNEL_SWEEP_SPACING_SECONDS,
    SHARED_SERIALIZER_CHANNEL_IDS,
    channel_short_name,
    classify_channel_message_payload,
    decode_channel_message_payload,
    load_channel_message_hypothesis_scenario,
    make_channel_message_response,
)
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PREFIX,
    CHAT_INPUT_PROBE_PAYLOADS,
    CHAT_INPUT_PROBE_PAYLOAD_SHA256,
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
    classify_chat_input_payload,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SWEEP_SCENARIO_PATH = (
    ROOT / "scenarios" / "channel_message_hypothesis_channel_sweep.json"
)
CODEC_SCENARIO_PATH = (
    ROOT / "scenarios" / "channel_message_hypothesis_shared_serializer.json"
)
# The 16-bit channel id inside the one-vital collection envelope.
PC_CHANNEL_ID_SLICE = slice(16, 18)
SWEEP_EVENT = "channel_message_hypothesis_channel_sweep_sent"


class ChannelSweepRuntimeTests(unittest.TestCase):
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
        self.scenario = load_channel_message_hypothesis_scenario(
            SWEEP_SCENARIO_PATH
        )
        self.pinned = json.loads(
            SWEEP_SCENARIO_PATH.read_text(encoding="utf-8")
        )

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ---------------------------------------------------------

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            channel_message_hypothesis_scenario=(
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

    def _chat_pc(self, payload, *, outer_id=None, outer_version=0,
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

    def _chat_parsed(self, probe):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    # ----- happy path ------------------------------------------------------

    def test_one_request_sweeps_five_channels_in_the_pinned_order(self):
        state = self._state("sweep01")
        session_id = state.foundation.session_id
        actions = state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(len(actions), 5)
        self.assertEqual(
            [action[0] for action in actions],
            [
                CHANNEL_SWEEP_ACTION_LABEL_PREFIX + channel_short_name(name)
                for name in CHANNEL_SWEEP_ORDER
            ],
        )
        # ...which is the order the scenario file itself declares.
        self.assertEqual(
            [action[0] for action in actions],
            self.pinned["dispatch"]["action_labels"],
        )
        self.assertEqual(
            [action[0] for action in actions],
            [
                "HYP_PF_019_CHANNEL_SWEEP_LOCALTALK",
                "HYP_PF_019_CHANNEL_SWEEP_PARTY",
                "HYP_PF_019_CHANNEL_SWEEP_GUILD",
                "HYP_PF_019_CHANNEL_SWEEP_GMGLOBAL",
                "HYP_PF_019_CHANNEL_SWEEP_ACTORBOARDCAST",
            ],
        )
        self.assertEqual(state.channel_message_sweep_count, 1)
        self.assertIn(SWEEP_EVENT, state.events)
        # The lane never closes anything and never writes anything.
        self.assertIsNone(self._session_closed_at(session_id))

    def test_the_frames_carry_the_declared_channel_ids_in_order(self):
        state = self._state("sweep-ids")
        actions = state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(
            [action[1][PC_CHANNEL_ID_SLICE] for action in actions],
            [
                SHARED_SERIALIZER_CHANNEL_IDS[name].to_bytes(2, "little")
                for name in CHANNEL_SWEEP_ORDER
            ],
        )
        self.assertEqual(
            [
                int.from_bytes(action[1][PC_CHANNEL_ID_SLICE], "little")
                for action in actions
            ],
            self.pinned["dispatch"]["channel_id_order"],
        )

    def test_the_five_payloads_are_identical_byte_for_byte(self):
        # THE claim of this milestone: an empty speaker makes the five nested
        # payloads the same 34 bytes, so nothing but the class id distinguishes
        # the channels on the wire.
        state = self._state("sweep-payload")
        actions = state.dispatch(self._chat_parsed("probe1"))
        payloads = [
            action[1][
                CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET:
                CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET + 34
            ]
            for action in actions
        ]
        self.assertEqual(len(set(payloads)), 1)
        self.assertEqual(payloads[0], CHAT_INPUT_PROBE_PAYLOADS["probe1"])
        digests = {
            hashlib.sha256(payload).hexdigest().upper() for payload in payloads
        }
        self.assertEqual(
            digests, {CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe1"]},
        )
        self.assertEqual(
            digests.pop(),
            self.pinned["composed_responses"]["payload_sha256"],
        )
        # Empty speaker, decoded body, on every one of the five.
        for payload in payloads:
            self.assertEqual(
                decode_channel_message_payload(payload),
                ("", CHANNEL_MESSAGE_PROBE_BODIES["probe1"]),
            )

    def test_the_five_pcs_differ_in_exactly_two_bytes(self):
        state = self._state("sweep-twobytes")
        actions = state.dispatch(self._chat_parsed("probe1"))
        pcs = [action[1] for action in actions]
        self.assertEqual(len(set(pcs)), 5)
        self.assertEqual({len(pc) for pc in pcs}, {56})
        differing = set()
        for left in pcs:
            for right in pcs:
                differing |= {
                    index for index, (a, b) in enumerate(zip(left, right))
                    if a != b
                }
        self.assertEqual(sorted(differing), [16, 17])
        self.assertEqual(
            len(differing),
            self.pinned["composed_responses"][
                "pc_bytes_differing_across_channels"
            ],
        )
        self.assertEqual(
            min(differing),
            self.pinned["composed_responses"]["pc_channel_id_offset"],
        )
        # Blank those two bytes and all five collapse into one.
        blanked = {pc[:16] + b"\x00\x00" + pc[18:] for pc in pcs}
        self.assertEqual(len(blanked), 1)

    def test_every_dispatched_frame_matches_its_scenario_pin(self):
        state = self._state("sweep-pins")
        actions = state.dispatch(self._chat_parsed("probe1"))
        per_channel = self.pinned["composed_responses"]["per_channel"]
        for name, action in zip(CHANNEL_SWEEP_ORDER, actions):
            _label, pc, frame, _delay = action
            self.assertEqual(len(pc), 56, name)
            self.assertEqual(len(frame), 66, name)
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                per_channel[name]["pc_sha256"], name,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                per_channel[name]["frame_sha256"], name,
            )
            # ...and the same pins the module carries, independently.
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                CHANNEL_MESSAGE_PROBE1_PC_SHA256[name], name,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                CHANNEL_MESSAGE_PROBE1_FRAME_SHA256[name], name,
            )

    def test_the_dispatched_frames_are_the_documented_composer_output(self):
        # Nothing is assembled inside the dispatcher: every frame is what
        # make_channel_message_response returns for that channel.
        state = self._state("sweep-composer")
        actions = state.dispatch(self._chat_parsed("probe2"))
        for name, action in zip(CHANNEL_SWEEP_ORDER, actions):
            expected = make_channel_message_response(
                self.legacy, SHARED_SERIALIZER_CHANNEL_IDS[name], "",
                CHANNEL_MESSAGE_PROBE_BODIES["probe2"],
            )
            self.assertEqual((action[1], action[2]), expected, name)

    def test_the_spacing_matches_the_scenario(self):
        # The frozen V141 sender accumulates these onto one deadline, so the
        # first frame goes out immediately and each later frame is one full
        # spacing behind the previous one.
        state = self._state("sweep-spacing")
        actions = state.dispatch(self._chat_parsed("probe1"))
        delays = [action[3] for action in actions]
        self.assertEqual(
            delays,
            [CHANNEL_SWEEP_FIRST_DELAY_SECONDS]
            + [CHANNEL_SWEEP_SPACING_SECONDS] * 4,
        )
        self.assertEqual(delays[0], self.pinned["dispatch"][
            "first_frame_delay_seconds"
        ])
        self.assertEqual(
            set(delays[1:]), {self.pinned["dispatch"]["spacing_seconds"]},
        )
        # Total on-screen span of one sweep, on the cumulative timeline.
        self.assertEqual(sum(delays), 4 * CHANNEL_SWEEP_SPACING_SECONDS)

    def test_the_body_is_decoded_from_the_request_not_spliced(self):
        # A body the project never captured, at the same accepted shape: if the
        # dispatcher were echoing bytes it would still work, so the assertion
        # that matters is that the OUTGOING payload is the re-encoded decode of
        # what came in, on all five channels.
        state = self._state("sweep-decode")
        other = CHAT_INPUT_PREFIX + "HELLO WORLD!".encode("utf-16-le")
        self.assertEqual(classify_chat_input_payload(other), "ascii12")
        actions = state.dispatch(self.legacy.parse_outer(self._chat_pc(other)))
        self.assertEqual(len(actions), 5)
        for action in actions:
            payload = action[1][
                CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET:
                CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET + 34
            ]
            self.assertEqual(
                decode_channel_message_payload(payload),
                ("", "HELLO WORLD!"),
            )
        self.assertEqual(state.channel_message_sweep_count, 1)

    # ----- repeatability ---------------------------------------------------

    def test_two_requests_produce_ten_frames_with_no_accumulated_state(self):
        state = self._state("sweep-repeat")
        first = state.dispatch(self._chat_parsed("probe1"))
        second = state.dispatch(self._chat_parsed("probe2"))
        third = state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual([len(first), len(second), len(third)], [5, 5, 5])
        self.assertEqual(len(first) + len(second), 10)
        # Same request in, same ten bytes out: no counter leaks into the wire.
        self.assertEqual(first, third)
        self.assertNotEqual(first, second)
        self.assertEqual(state.channel_message_sweep_count, 3)
        self.assertEqual(state.events.count(SWEEP_EVENT), 3)

    def test_the_sweep_writes_nothing_to_the_database(self):
        state = self._state("sweep-nowrite")
        session_id = state.foundation.session_id
        before = self.db_path.read_bytes()
        state.dispatch(self._chat_parsed("probe1"))
        state.dispatch(self._chat_parsed("probe2"))
        state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(state.channel_message_sweep_count, 3)

    def test_a_refused_frame_also_writes_nothing(self):
        state = self._state("sweep-nowrite-refused")
        before = self.db_path.read_bytes()
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], bytes([base[0] ^ 0x01]) + base[1:]):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(self._chat_pc(payload))),
                [],
            )
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertEqual(state.channel_message_sweep_count, 0)

    # ----- fail closed -----------------------------------------------------

    def _assert_silent(self, state, parsed, event):
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn(event, state.events)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.channel_message_sweep_count, 0)

    def test_wrong_length_fails_closed(self):
        state = self._state("sweep-length")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], base + b"A\x00", b"", base[:5]):
            self._assert_silent(
                state, self.legacy.parse_outer(self._chat_pc(payload)),
                "channel_message_hypothesis_wrong_length_no_reply",
            )
        self.assertEqual(
            state.events.count(
                "channel_message_hypothesis_wrong_length_no_reply"
            ),
            4,
        )

    def test_wrong_prefix_fails_closed(self):
        state = self._state("sweep-prefix")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        tampered = bytes([base[0] ^ 0x01]) + base[1:]
        self.assertEqual(len(tampered), 34)
        self._assert_silent(
            state, self.legacy.parse_outer(self._chat_pc(tampered)),
            "channel_message_hypothesis_wrong_prefix_no_reply",
        )

    def test_wrong_text_bytes_fail_closed(self):
        state = self._state("sweep-text")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (
            base[:11] + b"\x01" + base[12:],   # high byte of pair 1 nonzero
            base[:10] + b"\x1f" + base[11:],   # below the printable range
            base[:10] + b"\x7f" + base[11:],   # above the printable range
        ):
            self.assertEqual(len(payload), 34)
            self._assert_silent(
                state, self.legacy.parse_outer(self._chat_pc(payload)),
                "channel_message_hypothesis_wrong_text_no_reply",
            )

    def test_wrong_envelope_fails_closed(self):
        state = self._state("sweep-envelope")
        payload = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for pc in (
            self._chat_pc(payload, nested_version=1),
            self._chat_pc(payload, outer_version=1),
            self._chat_pc(payload, outer_id=self.legacy.GSCN_LOGIN_PROTOCOL),
        ):
            self._assert_silent(
                state, self.legacy.parse_outer(pc),
                "channel_message_hypothesis_wrong_envelope_no_reply",
            )
        self.assertEqual(
            state.events.count(
                "channel_message_hypothesis_wrong_envelope_no_reply"
            ),
            3,
        )

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("sweep-seq", ready=False)
        self._assert_silent(
            state, self._chat_parsed("probe1"),
            "channel_message_hypothesis_wrong_sequence_no_reply",
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state_type()("sweep-noselect")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertIsNone(state.foundation.selected)
        self._assert_silent(
            state, self._chat_parsed("probe1"),
            "channel_message_hypothesis_no_selected_no_reply",
        )

    def test_no_refusal_path_ever_emits_a_sweep_event(self):
        # Guard the guard: every refusal above must be distinguishable from a
        # send, and none of them may leave a half-sweep behind.
        state = self._state("sweep-refusals")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (
            base[:-2],
            bytes([base[0] ^ 0x01]) + base[1:],
            base[:10] + b"\x1f" + base[11:],
        ):
            self.assertEqual(
                state.dispatch(self.legacy.parse_outer(self._chat_pc(payload))),
                [],
            )
        self.assertEqual(state.events.count(SWEEP_EVENT), 0)
        for event in state.events:
            self.assertNotIn("sweep", event)

    # ----- containment -----------------------------------------------------

    def test_without_a_scenario_the_baseline_does_not_move(self):
        # GT-006 baseline: the frozen dispatch counts the frame and answers
        # nothing.  Wiring the lane in must not have changed that by one byte.
        state = self._state("sweep-off", sweep=False)
        rx_before = state.rx_frames
        events_before = list(state.events)
        before = self.db_path.read_bytes()
        actions = state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(
            [a for a in actions if a[0].startswith("HYP_PF_019")], [],
        )
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(state.channel_message_sweep_count, 0)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(
            [e for e in state.events[len(events_before):]
             if "channel_message" in e],
            [],
        )
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_the_two_chat_lanes_are_mutually_exclusive(self):
        from pirateforce_foundation.chat_input_hypothesis import (
            load_chat_input_hypothesis_scenario,
        )
        chat = load_chat_input_hypothesis_scenario(
            ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
        )
        with self.assertRaises(ValueError) as raised:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                chat_input_hypothesis_scenario=chat,
                channel_message_hypothesis_scenario=self.scenario,
            )
        self.assertIn("mutually exclusive", str(raised.exception))

    def test_the_sweep_and_logout_scenarios_are_mutually_exclusive(self):
        from pirateforce_foundation.logout_hypothesis import (
            load_logout_hypothesis_scenario,
        )
        logout = load_logout_hypothesis_scenario(
            ROOT / "scenarios" / "logout_hypothesis_ack_echo.json"
        )
        with self.assertRaises(ValueError) as raised:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                logout_hypothesis_scenario=logout,
                channel_message_hypothesis_scenario=self.scenario,
            )
        self.assertIn("mutually exclusive", str(raised.exception))

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        from dataclasses import replace

        for bad in (
            object(),
            replace(self.scenario, spacing_seconds=0.25),
            replace(self.scenario, channel_order=CHANNEL_SWEEP_ORDER[:2]),
            replace(self.scenario, hypothesis_id="HYP-PF-014"),
        ):
            with self.assertRaises(ValueError):
                make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                    channel_message_hypothesis_scenario=bad,
                )

    def test_a_one_field_tampered_scenario_file_never_loads(self):
        data = json.loads(SWEEP_SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("test_only", False),
            lambda d: d.__setitem__("schema", 2),
            lambda d: d["entry"].__setitem__(
                "required_sequence", "selected_only",
            ),
            lambda d: d["dispatch"].__setitem__("spacing_seconds", 0.0),
            lambda d: d["dispatch"].__setitem__("one_shot", True),
            lambda d: d["dispatch"]["channel_order"].__setitem__(
                0, "Channel_WhisperVital",
            ),
            lambda d: d["dispatch"]["channel_id_order"].__setitem__(0, 21868),
            lambda d: d["dispatch"]["action_labels"].__setitem__(
                4, "HYP_PF_019_CHANNEL_SWEEP_WHISPER",
            ),
            lambda d: d["composed_responses"].__setitem__(
                "payload_sha256", "00" * 32,
            ),
            lambda d: d["composed_responses"]["per_channel"][
                "Channel_PartyMessageVital"
            ].__setitem__("frame_sha256", "00" * 32),
            lambda d: d["persisted_post_state"].__setitem__(
                "database_write", "chat_messages",
            ),
            lambda d: d["nonclaims"].pop(),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            self.assertNotEqual(tampered_data, data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_channel_message_hypothesis_scenario(tampered)

    def test_the_codec_only_profile_cannot_drive_the_sweep(self):
        # It loads (same module, same allowlist) but carries no channel order,
        # so handing it in would compose zero frames rather than a partial
        # sweep.  Loading it must not be mistaken for enabling CHAT-CHANNEL-003.
        codec_only = load_channel_message_hypothesis_scenario(
            CODEC_SCENARIO_PATH
        )
        self.assertEqual(codec_only.channel_order, ())
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            channel_message_hypothesis_scenario=codec_only,
        )
        state = state_type("sweep-codeconly")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        characters = self.store.list_characters(state.foundation.account_id)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        state.runtime_ack_sent = True
        self.assertEqual(state.dispatch(self._chat_parsed("probe1")), [])

    # ----- invariants behind the guards -----------------------------------

    def test_every_accepted_request_shape_is_decodable(self):
        # This is why the undecodable-payload backstop in the dispatcher never
        # fires today: the ascii12 shape is a strict subset of the 0x65AD40
        # schema.  If that ever stops being true the backstop starts earning
        # its keep, and this test says so.
        for payload in (
            CHAT_INPUT_PROBE_PAYLOADS["probe1"],
            CHAT_INPUT_PROBE_PAYLOADS["probe2"],
            CHAT_INPUT_PREFIX + "HELLO WORLD!".encode("utf-16-le"),
            CHAT_INPUT_PREFIX + b"\x20\x00" * 11 + b"\x7e\x00",
        ):
            self.assertEqual(classify_chat_input_payload(payload), "ascii12")
            self.assertEqual(
                classify_channel_message_payload(payload),
                "shared_serializer_message",
            )
            speaker, body = decode_channel_message_payload(payload)
            self.assertEqual(speaker, "")
            self.assertEqual(len(body), 12)


if __name__ == "__main__":
    unittest.main()
