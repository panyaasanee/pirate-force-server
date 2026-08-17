"""Runtime wire hookup for the HYP-PF-014 chat input echo (UNKNOWN_0xAC52).

Every test drives the real dispatch path behind the chat input opt-in
scenario.  The two captured GT-006 chat input frames (34-byte payload vital
id 0xAC52 inside the standard one-vital GSCN_RunTimeProtocolReq envelope)
are acknowledged with a designed echo composition; the accepted shape is
pinned fail-closed (exact 34-byte length, exact 10-byte prefix, 12 printable
ASCII (low, 0x00) pairs) and everything else -- wrong lengths, wrong
prefixes, non-zero high bytes, non-printable low bytes, wrong envelopes,
wrong sequences, and every frame without the opt-in scenario -- produces no
reply and no write.  The lane touches no database table (chat has none), it
never closes the socket, and it is deliberately not one-shot: every accepted
frame on a session is echoed.  ``production_allowed`` stays false.
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
    CHAT_INPUT_ECHO_FRAME_SHA256,
    CHAT_INPUT_ECHO_PC_SHA256,
    CHAT_INPUT_PREFIX,
    CHAT_INPUT_PROBE_PAYLOADS,
    CHAT_INPUT_PROBE_PAYLOAD_SHA256,
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_PROBE_REQUEST_PC_SHA256,
    CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256,
    CHAT_INPUT_SPEAKER_ECHO_FRAME_SIZE,
    CHAT_INPUT_SPEAKER_ECHO_PC_SHA256,
    CHAT_INPUT_SPEAKER_ECHO_PC_SIZE,
    CHAT_INPUT_SPEAKER_NAME_HEADER_SIZE,
    CHAT_INPUT_SPEAKER_PROBE_NAME,
    CHAT_INPUT_SPEAKER_PROBE_PAYLOAD_SHA256,
    CHAT_INPUT_VITAL_ID,
    compose_chat_input_speaker_payload,
    load_chat_input_hypothesis_scenario,
    make_chat_input_echo_response,
    make_chat_input_speaker_echo_response,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
SPEAKER_SCENARIO_PATH = (
    ROOT / "scenarios" / "chat_input_hypothesis_speaker_echo.json"
)
# CHAT-ECHO-001 pinned the plain echo scenario file end to end; CHAT-ECHO-002
# must leave it byte-identical (its own policy lives in a separate file).
ECHO_SCENARIO_FILE_SHA256 = (
    "1350C98A0DE99B4690191BB998F66A0DFE7B8A7A41F15F33DBAD135DE0C75ABB"
)


class ChatInputEchoRuntimeTests(unittest.TestCase):
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
        self.scenario = load_chat_input_hypothesis_scenario(SCENARIO_PATH)
        self.speaker_scenario = load_chat_input_hypothesis_scenario(
            SPEAKER_SCENARIO_PATH
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _state_type(self, *, chat=True, speaker=False):
        scenario = self.speaker_scenario if speaker else self.scenario
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            chat_input_hypothesis_scenario=scenario if chat else None,
        )

    def _state(self, login, *, chat=True, ready=True, speaker=False):
        state = self._state_type(chat=chat, speaker=speaker)(login)
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

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

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

    def test_request_fixtures_match_the_gt006_capture(self):
        for probe in ("probe1", "probe2"):
            payload = CHAT_INPUT_PROBE_PAYLOADS[probe]
            self.assertEqual(len(payload), 34)
            self.assertEqual(payload[:10], CHAT_INPUT_PREFIX)
            self.assertEqual(
                hashlib.sha256(payload).hexdigest().upper(),
                CHAT_INPUT_PROBE_PAYLOAD_SHA256[probe],
            )
            pc = CHAT_INPUT_PROBE_REQUEST_PCS[probe]
            self.assertEqual(len(pc), 54)
            self.assertEqual(pc, self._chat_pc(payload))
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                CHAT_INPUT_PROBE_REQUEST_PC_SHA256[probe],
            )
            parsed = self.legacy.parse_outer(pc)
            self.assertEqual(parsed.nested_id, CHAT_INPUT_VITAL_ID)
            self.assertEqual(parsed.nested_payload, payload)
        # The two captured payloads differ only in the final typed character.
        first = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        second = CHAT_INPUT_PROBE_PAYLOADS["probe2"]
        self.assertEqual(first[:-2], second[:-2])

    def test_probe1_echo_is_byte_exact_and_pinned(self):
        state = self._state("chat01")
        session_id = state.foundation.session_id
        expected_pc, expected_frame = make_chat_input_echo_response(
            self.legacy, CHAT_INPUT_PROBE_PAYLOADS["probe1"],
        )
        actions = state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(actions, [(
            "HYP_PF_014_CHAT_INPUT_ECHO_ASCII12",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertEqual(len(expected_pc), 56)
        self.assertEqual(len(expected_frame), 66)
        self.assertEqual(
            expected_pc[20:54], CHAT_INPUT_PROBE_PAYLOADS["probe1"],
        )
        self.assertEqual(
            hashlib.sha256(expected_pc).hexdigest().upper(),
            CHAT_INPUT_ECHO_PC_SHA256["probe1"],
        )
        self.assertEqual(
            hashlib.sha256(expected_frame).hexdigest().upper(),
            CHAT_INPUT_ECHO_FRAME_SHA256["probe1"],
        )
        self.assertEqual(state.chat_input_echo_count, 1)
        self.assertIn("chat_input_hypothesis_echo_ack_ascii12", state.events)
        # The session lease stays open: the echo lane never closes anything.
        self.assertIsNone(self._session_closed_at(session_id))

    def test_probe2_echo_is_byte_exact_and_pinned(self):
        state = self._state("chat02")
        expected_pc, expected_frame = make_chat_input_echo_response(
            self.legacy, CHAT_INPUT_PROBE_PAYLOADS["probe2"],
        )
        actions = state.dispatch(self._chat_parsed("probe2"))
        self.assertEqual(actions, [(
            "HYP_PF_014_CHAT_INPUT_ECHO_ASCII12",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertEqual(
            hashlib.sha256(expected_frame).hexdigest().upper(),
            CHAT_INPUT_ECHO_FRAME_SHA256["probe2"],
        )

    def test_consecutive_messages_are_each_echoed(self):
        # Deliberately not one-shot: chat can repeat within one session.
        state = self._state("chat-repeat")
        first = state.dispatch(self._chat_parsed("probe1"))
        second = state.dispatch(self._chat_parsed("probe2"))
        third = state.dispatch(self._chat_parsed("probe1"))
        for actions in (first, second, third):
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0][0], "HYP_PF_014_CHAT_INPUT_ECHO_ASCII12")
        self.assertEqual(first[0][1:], third[0][1:])
        self.assertNotEqual(first[0][1], second[0][1])
        self.assertEqual(state.chat_input_echo_count, 3)
        self.assertEqual(
            state.events.count("chat_input_hypothesis_echo_ack_ascii12"), 3,
        )

    def test_echo_writes_nothing_to_the_database(self):
        state = self._state("chat-nowrite")
        session_id = state.foundation.session_id
        before = self.db_path.read_bytes()
        state.dispatch(self._chat_parsed("probe1"))
        state.dispatch(self._chat_parsed("probe2"))
        state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(state.chat_input_echo_count, 3)

    def test_wrong_length_fails_closed(self):
        state = self._state("chat-length")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], base + b"A\x00"):
            parsed = self.legacy.parse_outer(self._chat_pc(payload))
            self.assertEqual(state.dispatch(parsed), [])
        self.assertEqual(
            state.events.count("chat_input_hypothesis_wrong_length_no_reply"),
            2,
        )
        self.assertEqual(state.chat_input_echo_count, 0)

    def test_wrong_prefix_fails_closed(self):
        state = self._state("chat-prefix")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        tampered = bytes([base[0] ^ 0x01]) + base[1:]
        self.assertEqual(len(tampered), 34)
        parsed = self.legacy.parse_outer(self._chat_pc(tampered))
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn(
            "chat_input_hypothesis_wrong_prefix_no_reply", state.events,
        )
        self.assertEqual(state.chat_input_echo_count, 0)

    def test_wrong_text_bytes_fail_closed(self):
        state = self._state("chat-text")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        mutations = (
            base[:11] + b"\x01" + base[12:],   # high byte of pair 1 nonzero
            base[:10] + b"\x1f" + base[11:],   # low byte below printable range
            base[:10] + b"\x7f" + base[11:],   # low byte above printable range
        )
        for payload in mutations:
            self.assertEqual(len(payload), 34)
            parsed = self.legacy.parse_outer(self._chat_pc(payload))
            self.assertEqual(state.dispatch(parsed), [])
        self.assertEqual(
            state.events.count("chat_input_hypothesis_wrong_text_no_reply"),
            3,
        )
        self.assertEqual(state.chat_input_echo_count, 0)

    def test_wrong_envelope_fails_closed(self):
        state = self._state("chat-envelope")
        payload = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for pc in (
            self._chat_pc(payload, nested_version=1),
            self._chat_pc(payload, outer_version=1),
            self._chat_pc(payload, outer_id=self.legacy.GSCN_LOGIN_PROTOCOL),
        ):
            self.assertEqual(state.dispatch(self.legacy.parse_outer(pc)), [])
        self.assertEqual(
            state.events.count("chat_input_hypothesis_wrong_envelope_no_reply"),
            3,
        )
        self.assertEqual(state.chat_input_echo_count, 0)

    def test_wrong_sequence_fails_closed(self):
        state = self._state("chat-seq", ready=False)
        self.assertEqual(state.dispatch(self._chat_parsed("probe1")), [])
        self.assertIn(
            "chat_input_hypothesis_wrong_sequence_no_reply", state.events,
        )
        self.assertEqual(state.chat_input_echo_count, 0)

    def test_no_selected_character_fails_closed(self):
        state = self._state_type()("chat-noselect")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertIsNone(state.foundation.selected)
        self.assertEqual(state.dispatch(self._chat_parsed("probe1")), [])
        self.assertIn(
            "chat_input_hypothesis_no_selected_no_reply", state.events,
        )
        self.assertEqual(state.chat_input_echo_count, 0)

    def test_without_scenario_nothing_changes(self):
        # GT-006 baseline: the frozen dispatch neither answers nor echoes.
        state = self._state("chat-off", chat=False)
        rx_before = state.rx_frames
        actions = state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(
            [a for a in actions if a[0].startswith("HYP_PF_014")], [],
        )
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(state.chat_input_echo_count, 0)
        self.assertNotIn("chat_input_hypothesis_echo_ack_ascii12", state.events)

    def test_response_maker_pins_and_rejects_nonconforming_payloads(self):
        for probe in ("probe1", "probe2"):
            pc, frame = make_chat_input_echo_response(
                self.legacy, CHAT_INPUT_PROBE_PAYLOADS[probe],
            )
            self.assertEqual(len(pc), 56)
            self.assertEqual(len(frame), 66)
            expected_pc, expected_frame = self.legacy.make_runtime_vitals([
                (CHAT_INPUT_VITAL_ID, 0, CHAT_INPUT_PROBE_PAYLOADS[probe]),
            ])
            self.assertEqual(pc, expected_pc)
            self.assertEqual(frame, expected_frame)
        # Any 12-pair printable payload composes structurally (no pinned
        # hash exists for it, so only the structural pins apply)...
        other = CHAT_INPUT_PREFIX + "HELLO WORLD!".encode("utf-16-le")
        pc, frame = make_chat_input_echo_response(self.legacy, other)
        self.assertEqual((len(pc), len(frame)), (56, 66))
        self.assertEqual(pc[20:54], other)
        # ...while every non-conforming payload is refused outright.
        for bad in (
            CHAT_INPUT_PROBE_PAYLOADS["probe1"][:-2],
            b"\x00" * 34,
            CHAT_INPUT_PREFIX + b"\x19\x00" * 12,
        ):
            with self.assertRaises(ValueError):
                make_chat_input_echo_response(self.legacy, bad)

    def test_scenario_allowlist_is_exact(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("id", "chat_input_hypothesis_echo_v2"),
            lambda d: d.__setitem__("extra_field", 1),
            lambda d: d.pop("nonclaims"),
            lambda d: d["requests"]["shape"].__setitem__("payload_size", 36),
            lambda d: d["composed_responses"]["probe1"].__setitem__(
                "frame_sha256", "00" * 32,
            ),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_chat_input_hypothesis_scenario(tampered)

    def test_chat_and_logout_scenarios_are_mutually_exclusive(self):
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
                chat_input_hypothesis_scenario=self.scenario,
            )
        self.assertIn("mutually exclusive", str(raised.exception))

    # ----- CHAT-ECHO-002: speaker-name wstring variant ---------------------

    def _speaker_variant_payload(self, probe):
        payload = CHAT_INPUT_PROBE_PAYLOADS[probe]
        name_bytes = CHAT_INPUT_SPEAKER_PROBE_NAME.encode("utf-16-le")
        return (
            payload[:1]
            + len(name_bytes).to_bytes(4, "little")
            + name_bytes
            + payload[CHAT_INPUT_SPEAKER_NAME_HEADER_SIZE:]
        )

    def test_speaker_variant_payload_fixtures_match_the_research_reading(self):
        # wstring#1 header replaced, name inserted, wstring#2 + text kept
        # byte-exactly -- the CHAT-ECHO-002 research composition, pinned.
        for probe in ("probe1", "probe2"):
            payload = CHAT_INPUT_PROBE_PAYLOADS[probe]
            variant = compose_chat_input_speaker_payload(
                CHAT_INPUT_SPEAKER_PROBE_NAME, payload,
            )
            self.assertEqual(variant, self._speaker_variant_payload(probe))
            self.assertEqual(len(variant), 34 + 12)
            self.assertEqual(variant[0], 0x48)
            self.assertEqual(
                int.from_bytes(variant[1:5], "little"),
                2 * len(CHAT_INPUT_SPEAKER_PROBE_NAME),
            )
            self.assertEqual(
                variant[5:17].decode("utf-16-le"),
                CHAT_INPUT_SPEAKER_PROBE_NAME,
            )
            self.assertEqual(
                variant[17:],
                payload[CHAT_INPUT_SPEAKER_NAME_HEADER_SIZE:],
            )
            self.assertEqual(
                hashlib.sha256(variant).hexdigest().upper(),
                CHAT_INPUT_SPEAKER_PROBE_PAYLOAD_SHA256[probe],
            )

    def test_the_plain_echo_scenario_file_is_untouched(self):
        self.assertEqual(
            hashlib.sha256(SCENARIO_PATH.read_bytes()).hexdigest().upper(),
            ECHO_SCENARIO_FILE_SHA256,
        )

    def test_speaker_probe1_echo_is_byte_exact_and_pinned(self):
        state = self._state("speak01", speaker=True)
        session_id = state.foundation.session_id
        # The fixture create commits the canonical V25 name, binding the
        # runtime name source to the pinned probe form.
        self.assertEqual(
            state.foundation.selected.name, CHAT_INPUT_SPEAKER_PROBE_NAME,
        )
        expected_pc, expected_frame = make_chat_input_speaker_echo_response(
            self.legacy, CHAT_INPUT_PROBE_PAYLOADS["probe1"],
            CHAT_INPUT_SPEAKER_PROBE_NAME,
        )
        actions = state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(actions, [(
            "HYP_PF_014_CHAT_INPUT_SPEAKER_ECHO_ASCII12",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertEqual(len(expected_pc), CHAT_INPUT_SPEAKER_ECHO_PC_SIZE)
        self.assertEqual(
            len(expected_frame), CHAT_INPUT_SPEAKER_ECHO_FRAME_SIZE,
        )
        self.assertEqual(
            expected_pc[20:66], self._speaker_variant_payload("probe1"),
        )
        self.assertEqual(
            hashlib.sha256(expected_pc).hexdigest().upper(),
            CHAT_INPUT_SPEAKER_ECHO_PC_SHA256["probe1"],
        )
        self.assertEqual(
            hashlib.sha256(expected_frame).hexdigest().upper(),
            CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256["probe1"],
        )
        self.assertEqual(state.chat_input_echo_count, 1)
        self.assertIn(
            "chat_input_hypothesis_speaker_echo_ack_ascii12", state.events,
        )
        self.assertNotIn("chat_input_hypothesis_echo_ack_ascii12", state.events)
        # The session lease stays open: the speaker lane never closes anything.
        self.assertIsNone(self._session_closed_at(session_id))

    def test_speaker_probe2_echo_is_byte_exact_and_pinned(self):
        state = self._state("speak02", speaker=True)
        expected_pc, expected_frame = make_chat_input_speaker_echo_response(
            self.legacy, CHAT_INPUT_PROBE_PAYLOADS["probe2"],
            CHAT_INPUT_SPEAKER_PROBE_NAME,
        )
        actions = state.dispatch(self._chat_parsed("probe2"))
        self.assertEqual(actions, [(
            "HYP_PF_014_CHAT_INPUT_SPEAKER_ECHO_ASCII12",
            expected_pc, expected_frame, 0.0,
        )])
        self.assertEqual(
            hashlib.sha256(expected_frame).hexdigest().upper(),
            CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256["probe2"],
        )

    def test_speaker_consecutive_messages_are_each_echoed(self):
        # The variant keeps the deliberate not-one-shot contract.
        state = self._state("speak-repeat", speaker=True)
        first = state.dispatch(self._chat_parsed("probe1"))
        second = state.dispatch(self._chat_parsed("probe2"))
        third = state.dispatch(self._chat_parsed("probe1"))
        for actions in (first, second, third):
            self.assertEqual(len(actions), 1)
            self.assertEqual(
                actions[0][0], "HYP_PF_014_CHAT_INPUT_SPEAKER_ECHO_ASCII12",
            )
        self.assertEqual(first[0][1:], third[0][1:])
        self.assertNotEqual(first[0][1], second[0][1])
        self.assertEqual(state.chat_input_echo_count, 3)
        self.assertEqual(
            state.events.count("chat_input_hypothesis_speaker_echo_ack_ascii12"),
            3,
        )

    def test_speaker_echo_writes_nothing_to_the_database(self):
        state = self._state("speak-nowrite", speaker=True)
        session_id = state.foundation.session_id
        before = self.db_path.read_bytes()
        state.dispatch(self._chat_parsed("probe1"))
        state.dispatch(self._chat_parsed("probe2"))
        state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(state.chat_input_echo_count, 3)

    def test_speaker_short_and_toolong_fail_closed(self):
        # The GT-009-observed off-shape lengths (5- and 18-character texts)
        # stay silent under the variant: classification is unchanged.
        state = self._state("speak-length", speaker=True)
        short = (
            b"\x48" + (0).to_bytes(4, "little")
            + b"\x48" + (10).to_bytes(4, "little")
            + "SHORT".encode("utf-16-le")
        )
        toolong = (
            b"\x48" + (0).to_bytes(4, "little")
            + b"\x48" + (36).to_bytes(4, "little")
            + "PFCHATPROBETOOLONG".encode("utf-16-le")
        )
        self.assertEqual((len(short), len(toolong)), (20, 46))
        for payload in (short, toolong):
            parsed = self.legacy.parse_outer(self._chat_pc(payload))
            self.assertEqual(state.dispatch(parsed), [])
        self.assertEqual(
            state.events.count("chat_input_hypothesis_wrong_length_no_reply"),
            2,
        )
        self.assertEqual(state.chat_input_echo_count, 0)

    def test_speaker_wrong_scenario_id_variants_fail_closed(self):
        # A scenario file outside the two-entry exact allowlist never loads.
        data = json.loads(SPEAKER_SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("id", "chat_input_hypothesis_speaker_v2"),
            lambda d: d.__setitem__("extra_field", 1),
            lambda d: d.pop("nonclaims"),
            lambda d: d["entry"].__setitem__(
                "response_policy",
                "echo_exact_request_vital_no_write_no_close",
            ),
            lambda d: d["composed_responses"].__setitem__(
                "probe_speaker_name", "test02",
            ),
            lambda d: d["composed_responses"].__setitem__("pc_size", 56),
            lambda d: d["composed_responses"]["probe1"].__setitem__(
                "frame_sha256", "00" * 32,
            ),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered_speaker.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_chat_input_hypothesis_scenario(tampered)

    def test_speaker_no_selected_character_fails_closed(self):
        state = self._state_type(speaker=True)("speak-noselect")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertIsNone(state.foundation.selected)
        self.assertEqual(state.dispatch(self._chat_parsed("probe1")), [])
        self.assertIn(
            "chat_input_hypothesis_no_selected_no_reply", state.events,
        )
        self.assertEqual(state.chat_input_echo_count, 0)

    def test_speaker_unavailable_name_fails_closed(self):
        # A selected character whose name the fixed-size composition cannot
        # carry produces no reply and no write (the name source is the
        # canonical `characters.name`, so this is a guard, not a flow).
        from dataclasses import replace

        state = self._state("speak-noname", speaker=True)
        state.foundation.selected = replace(
            state.foundation.selected, name="",
        )
        before = self.db_path.read_bytes()
        self.assertEqual(state.dispatch(self._chat_parsed("probe1")), [])
        self.assertIn(
            "chat_input_hypothesis_speaker_name_unavailable_no_reply",
            state.events,
        )
        self.assertEqual(state.chat_input_echo_count, 0)
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_speaker_response_maker_pins_and_rejects_nonconforming_input(self):
        for probe in ("probe1", "probe2"):
            pc, frame = make_chat_input_speaker_echo_response(
                self.legacy, CHAT_INPUT_PROBE_PAYLOADS[probe],
                CHAT_INPUT_SPEAKER_PROBE_NAME,
            )
            self.assertEqual(len(pc), CHAT_INPUT_SPEAKER_ECHO_PC_SIZE)
            self.assertEqual(len(frame), CHAT_INPUT_SPEAKER_ECHO_FRAME_SIZE)
            expected_pc, expected_frame = self.legacy.make_runtime_vitals([
                (CHAT_INPUT_VITAL_ID, 0, self._speaker_variant_payload(probe)),
            ])
            self.assertEqual(pc, expected_pc)
            self.assertEqual(frame, expected_frame)
        # Any accepted payload under any two-byte-encodable name composes
        # structurally at exactly 56 + 2*len(name) PC bytes...
        other = CHAT_INPUT_PREFIX + "HELLO WORLD!".encode("utf-16-le")
        pc, frame = make_chat_input_speaker_echo_response(
            self.legacy, other, "Ab9",
        )
        self.assertEqual(len(pc), 56 + 6)
        self.assertEqual(pc[20:60], b"\x48\x06\x00\x00\x00" + "Ab9".encode(
            "utf-16-le") + other[CHAT_INPUT_SPEAKER_NAME_HEADER_SIZE:])
        # ...while unavailable names and non-conforming payloads are refused.
        probe1 = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for bad_name in ("", None, 42, "\U0001F600", "\ud800"):
            with self.assertRaises(ValueError):
                make_chat_input_speaker_echo_response(
                    self.legacy, probe1, bad_name,
                )
        for bad_payload in (
            probe1[:-2],
            b"\x00" * 34,
            CHAT_INPUT_PREFIX + b"\x19\x00" * 12,
        ):
            with self.assertRaises(ValueError):
                make_chat_input_speaker_echo_response(
                    self.legacy, bad_payload, CHAT_INPUT_SPEAKER_PROBE_NAME,
                )

    def test_plain_echo_scenario_still_uses_the_plain_composition(self):
        # Loading the speaker scenario must not leak into the plain lane.
        state = self._state("speak-crosscheck", speaker=False)
        actions = state.dispatch(self._chat_parsed("probe1"))
        self.assertEqual(actions[0][0], "HYP_PF_014_CHAT_INPUT_ECHO_ASCII12")
        self.assertEqual(
            hashlib.sha256(actions[0][2]).hexdigest().upper(),
            CHAT_INPUT_ECHO_FRAME_SHA256["probe1"],
        )
        self.assertNotIn(
            "chat_input_hypothesis_speaker_echo_ack_ascii12", state.events,
        )


if __name__ == "__main__":
    unittest.main()
