"""CHAT-CHANNEL-002 (HYP-PF-019) -- decoder/emitter for the five channels that
share the client serializer 0x65AD40.

Pure offline pytest: no network, no database, no GameClient, no UI.  The only
external artefacts are read-only Python source (the frozen v141 module, loaded
solely for its proven ``make_runtime_vitals`` envelope helper) and two scenario
JSON files.

What these tests are actually proving
-------------------------------------
CHAT-ECHO-001/002 could only ever answer a request it had already received:
the first ten payload bytes were an opaque pinned blob.  CHAT-CHANNEL-001
disassembled the base ``Channel_MessageVtial`` Serialize 0x65AD40 and read
those ten bytes as two tag-0x48 wstring headers -- speaker @+0x34 then body
@+0x18.  This lane implements that schema server-side and then proves the
reading is real rather than plausible, by three independent byte-level
cross-checks against pins produced by the *older, non-decoding* code path:

  1. ``decode`` of each captured GT-006 payload yields ``("", "PFCHATPROBEn")``
     and ``encode`` of that pair reproduces the captured payload byte-exactly.
  2. Composing the generated LocalTalk payload through the same v141
     ``make_runtime_vitals`` envelope reproduces the response PC and frame
     hashes pinned in ``scenarios/chat_input_hypothesis_echo.json`` -- the
     hashes CHAT-ECHO-001 put on the wire without decoding anything.
  3. Encoding ``("test01", "PFCHATPROBEn")`` reproduces the CHAT-ECHO-002
     speaker-variant payload/PC/frame pins.

A wrong field order, tag, length width or endianness cannot survive any of
those.

NOT tested here, because it is not claimed: whether the client renders any of
the five channels (GT-016, attended, not run), anything about the original
server's routing or fan-out, and any wire behaviour of the four non-LocalTalk
channels, which this project has never observed in either direction.
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
    CHANNEL_MESSAGE_ACCEPTED,
    CHANNEL_SWEEP_ORDER,
    CHANNEL_SWEEP_SCENARIO_ID,
    CHANNEL_SWEEP_SPACING_SECONDS,
    CHANNEL_MESSAGE_FIELD_ORDER,
    CHANNEL_MESSAGE_PC_OVERHEAD,
    CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET,
    CHANNEL_MESSAGE_PROBE1_FRAME_SHA256,
    CHANNEL_MESSAGE_PROBE1_PC_SHA256,
    CHANNEL_MESSAGE_PROBE_BODIES,
    CHANNEL_MESSAGE_PROBE_SPEAKER,
    CHANNEL_MESSAGE_SERIALIZER_VA,
    CHANNEL_NAME_BY_ID,
    CHANNEL_WHISPER_NAME,
    CHANNEL_WHISPER_SERIALIZER_VA,
    CHANNEL_WHISPER_VITAL_ID,
    CHANNEL_WSTRING_HEADER_SIZE,
    CHANNEL_WSTRING_TAG,
    ChannelMessage,
    SHARED_SERIALIZER_CHANNELS,
    SHARED_SERIALIZER_CHANNEL_IDS,
    channel_name_id,
    classify_channel_id,
    classify_channel_message_frame,
    classify_channel_message_payload,
    decode_channel_message,
    decode_channel_message_payload,
    encode_channel_message,
    encode_channel_message_payload,
    load_channel_message_hypothesis_scenario,
    make_channel_message_response,
)
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_PAYLOADS,
    CHAT_INPUT_PROBE_PAYLOAD_SHA256,
    CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256,
    CHAT_INPUT_SPEAKER_ECHO_PC_SHA256,
    CHAT_INPUT_SPEAKER_PROBE_NAME,
    CHAT_INPUT_SPEAKER_PROBE_PAYLOAD_SHA256,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "channel_message_hypothesis_shared_serializer.json"
)
SWEEP_SCENARIO_PATH = (
    ROOT / "scenarios" / "channel_message_hypothesis_channel_sweep.json"
)
ECHO_SCENARIO_PATH = ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
SPEAKER_SCENARIO_PATH = (
    ROOT / "scenarios" / "chat_input_hypothesis_speaker_echo.json"
)
# CHAT-ECHO-001/002 own those two files; this lane must leave them byte-identical.
ECHO_SCENARIO_FILE_SHA256 = (
    "1350C98A0DE99B4690191BB998F66A0DFE7B8A7A41F15F33DBAD135DE0C75ABB"
)
# CHAT-CHANNEL-002 owns the codec-only profile; CHAT-CHANNEL-003 must add a
# second file rather than widen that one.
SHARED_SERIALIZER_SCENARIO_FILE_SHA256 = (
    "31D1E45A7D3D52BEA909478C916533E2D4542F1AC35C22671BA8B06316C5E6B2"
)
# The 16-bit channel id sits at PC bytes 16:18 of the one-vital collection
# envelope (u16tag 3 + u32tag 5 + u8tag 2 + u8tag 2 + u16tag 3 = 15, +1 tag).
PC_CHANNEL_ID_SLICE = slice(16, 18)


def _wstring(text: str) -> bytes:
    raw = text.encode("utf-16-le")
    return bytes([CHANNEL_WSTRING_TAG]) + len(raw).to_bytes(4, "little") + raw


class ChannelTableTests(unittest.TestCase):
    """The five ids are derived from the in-image literals, not asserted."""

    def test_every_channel_id_is_the_nameid_hash_of_its_class_literal(self):
        for name, pinned in SHARED_SERIALIZER_CHANNEL_IDS.items():
            self.assertEqual(channel_name_id(name), pinned, name)
        self.assertEqual(len(set(SHARED_SERIALIZER_CHANNEL_IDS.values())), 5)
        self.assertEqual(
            sorted(SHARED_SERIALIZER_CHANNELS),
            sorted(SHARED_SERIALIZER_CHANNEL_IDS),
        )

    def test_localtalk_is_the_gt006_anchor(self):
        # The single wire-captured id in the whole family.
        self.assertEqual(
            channel_name_id("Channel_LocalTalkMessageVital"), 0xAC52,
        )
        self.assertEqual(
            SHARED_SERIALIZER_CHANNEL_IDS["Channel_LocalTalkMessageVital"],
            CHAT_INPUT_VITAL_ID,
        )

    def test_whisper_is_derived_too_but_is_not_in_the_shared_family(self):
        # Same hash, different serializer -> deliberately out of scope.
        self.assertEqual(channel_name_id(CHANNEL_WHISPER_NAME), 0x556C)
        self.assertEqual(channel_name_id(CHANNEL_WHISPER_NAME),
                         CHANNEL_WHISPER_VITAL_ID)
        self.assertNotIn(
            CHANNEL_WHISPER_VITAL_ID, SHARED_SERIALIZER_CHANNEL_IDS.values(),
        )
        self.assertNotEqual(
            CHANNEL_MESSAGE_SERIALIZER_VA, CHANNEL_WHISPER_SERIALIZER_VA,
        )

    def test_the_binary_spelling_of_the_class_name_is_load_bearing(self):
        # CHAT-CHANNEL-001: four classes in this family are spelled "Vtial";
        # the hash is over the literal, so any respelling shifts the id.
        self.assertNotEqual(
            channel_name_id("Channel_LocalTalkMessageVtial"),
            channel_name_id("Channel_LocalTalkMessageVital"),
        )


class DecoderTests(unittest.TestCase):
    def test_captured_payloads_decode_to_empty_speaker_and_the_typed_body(self):
        for probe, payload in CHAT_INPUT_PROBE_PAYLOADS.items():
            self.assertEqual(
                hashlib.sha256(payload).hexdigest().upper(),
                CHAT_INPUT_PROBE_PAYLOAD_SHA256[probe],
            )
            speaker, body = decode_channel_message_payload(payload)
            self.assertEqual(speaker, CHANNEL_MESSAGE_PROBE_SPEAKER)
            self.assertEqual(body, CHANNEL_MESSAGE_PROBE_BODIES[probe])

    def test_round_trip_of_both_captured_payloads_is_byte_exact(self):
        # The headline proof: decode -> encode reproduces the wire bytes.
        for probe, payload in CHAT_INPUT_PROBE_PAYLOADS.items():
            speaker, body = decode_channel_message_payload(payload)
            self.assertEqual(
                encode_channel_message_payload(speaker, body), payload, probe,
            )

    def test_decode_channel_message_names_the_channel(self):
        payload = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for name, channel_id in SHARED_SERIALIZER_CHANNEL_IDS.items():
            self.assertEqual(
                decode_channel_message(channel_id, payload),
                ChannelMessage(channel_id, name, "", "PFCHATPROBE1"),
            )

    def test_the_ten_byte_prefix_is_two_headers_not_one_blob(self):
        payload = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        self.assertEqual(payload[0], CHANNEL_WSTRING_TAG)
        self.assertEqual(int.from_bytes(payload[1:5], "little"), 0)
        self.assertEqual(payload[5], CHANNEL_WSTRING_TAG)
        self.assertEqual(int.from_bytes(payload[6:10], "little"), 0x18)
        self.assertEqual(len(payload), 2 * CHANNEL_WSTRING_HEADER_SIZE + 0x18)
        self.assertEqual(CHANNEL_MESSAGE_FIELD_ORDER, ("speaker", "body"))

    def test_speaker_first_then_body_is_not_interchangeable(self):
        # Swapping the two fields produces different bytes, so the pinned
        # round trip really does discriminate the field order.
        self.assertNotEqual(
            encode_channel_message_payload("alpha", "beta"),
            encode_channel_message_payload("beta", "alpha"),
        )

    def test_arbitrary_bmp_text_round_trips(self):
        # Any BMP text is exactly two bytes per character, so the schema
        # carries it; whether the client DISPLAYS it is not claimed (GT-016).
        for speaker, body in (
            ("", "x"),
            ("test01", "PFCHATPROBE1"),
            ("\u0e1c\u0e39\u0e49\u0e40\u0e25\u0e48\u0e19", "\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35"),
            ("\u4e2d\u6587", "\u65e5\u672c\u8a9e"),
            ("A" * 200, "B" * 400),
            (" ", " leading space"),
        ):
            payload = encode_channel_message_payload(speaker, body)
            self.assertEqual(
                decode_channel_message_payload(payload), (speaker, body),
            )
            self.assertEqual(
                len(payload),
                2 * CHANNEL_WSTRING_HEADER_SIZE + 2 * len(speaker)
                + 2 * len(body),
            )


class FailClosedTests(unittest.TestCase):
    """Every rejection means: no reply, no write, no partial result."""

    def test_channel_ids_outside_the_shared_five_are_refused(self):
        for channel_id in (
            CHANNEL_WHISPER_VITAL_ID,   # 0x556C -- different serializer
            0xBA58,                     # JoinCustomChannel (Command)
            0xE064,                     # CustomChannelMessage (extra fields)
            0xFDF2,                     # ForbidTalkNotification
            0x0000, 0xFFFF, -1, 0x1AC52,
            None, "0xAC52", True, 44114.0,
        ):
            self.assertEqual(
                classify_channel_id(channel_id),
                "channel_outside_shared_serializer",
                repr(channel_id),
            )
            with self.assertRaises(ValueError):
                decode_channel_message(
                    channel_id, CHAT_INPUT_PROBE_PAYLOADS["probe1"],
                )
            with self.assertRaises(ValueError):
                encode_channel_message(channel_id, "", "PFCHATPROBE1")

    def test_whisper_is_refused_even_with_a_well_formed_two_wstring_payload(self):
        # Whisper's schema has a third wstring plus a u8 result byte, so a
        # payload this lane can build is NOT a valid whisper frame.  Refusing
        # it is the correct behaviour, not a limitation.
        payload = encode_channel_message_payload("test01", "hello")
        self.assertEqual(
            classify_channel_message_frame(CHANNEL_WHISPER_VITAL_ID, payload),
            "channel_outside_shared_serializer",
        )
        whisper_shaped = payload + _wstring("recipient") + b"\x00"
        self.assertEqual(
            classify_channel_message_frame(
                CHAT_INPUT_VITAL_ID, whisper_shaped,
            ),
            "trailing_bytes_after_body",
        )

    def test_wrong_tag_is_refused(self):
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for index in (0, 5):
            bad = bytearray(base)
            bad[index] = 0x0B
            self.assertEqual(
                classify_channel_message_payload(bytes(bad)),
                "wrong_wstring_tag",
            )
            with self.assertRaises(ValueError):
                decode_channel_message_payload(bytes(bad))

    def test_odd_byte_length_is_refused(self):
        odd_speaker = b"\x48\x01\x00\x00\x00\x41" + _wstring("hi")
        odd_body = _wstring("") + b"\x48\x03\x00\x00\x00\x41\x00\x42"
        for payload in (odd_speaker, odd_body):
            self.assertEqual(
                classify_channel_message_payload(payload),
                "odd_wstring_byte_length",
            )
            with self.assertRaises(ValueError):
                decode_channel_message_payload(payload)

    def test_length_longer_than_the_payload_is_refused(self):
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        overlong_body = bytearray(base)
        overlong_body[6:10] = (0x1A).to_bytes(4, "little")
        overlong_speaker = bytearray(base)
        overlong_speaker[1:5] = (0x40).to_bytes(4, "little")
        huge = bytearray(base)
        huge[6:10] = (0xFFFFFFFE).to_bytes(4, "little")
        for payload in (overlong_body, overlong_speaker, huge):
            self.assertEqual(
                classify_channel_message_payload(bytes(payload)),
                "wstring_length_exceeds_payload",
            )

    def test_truncated_headers_are_refused(self):
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (b"", b"\x48", b"\x48\x00\x00\x00", base[:9]):
            self.assertEqual(
                classify_channel_message_payload(payload),
                "truncated_wstring_header",
            )

    def test_trailing_bytes_are_refused(self):
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for extra in (b"\x00", b"\x0b\x00", _wstring("third")):
            self.assertEqual(
                classify_channel_message_payload(base + extra),
                "trailing_bytes_after_body",
            )
            with self.assertRaises(ValueError):
                decode_channel_message(CHAT_INPUT_VITAL_ID, base + extra)

    def test_non_bmp_and_surrogates_are_refused_on_decode(self):
        pair = _wstring("") + b"\x48\x04\x00\x00\x00\x00\xd8\x00\xdc"
        lone_high = _wstring("") + b"\x48\x04\x00\x00\x00\x00\xd8\x41\x00"
        lone_low = _wstring("") + b"\x48\x02\x00\x00\x00\x00\xdc"
        for payload in (pair, lone_high, lone_low):
            self.assertEqual(
                classify_channel_message_payload(payload),
                "text_not_two_bytes_per_character",
            )
            with self.assertRaises(ValueError):
                decode_channel_message_payload(payload)

    def test_non_bmp_and_surrogates_are_refused_on_encode(self):
        for speaker, body in (
            ("\U0001F600", "ok"),
            ("ok", "\U0001F600"),
            ("\ud800", "ok"),
            ("ok", "\udfff"),
        ):
            with self.assertRaises(ValueError):
                encode_channel_message_payload(speaker, body)

    def test_empty_body_is_refused_both_ways(self):
        payload = _wstring("test01") + _wstring("")
        self.assertEqual(
            classify_channel_message_payload(payload), "empty_body",
        )
        with self.assertRaises(ValueError):
            decode_channel_message_payload(payload)
        with self.assertRaises(ValueError):
            encode_channel_message_payload("test01", "")
        # An empty SPEAKER stays legal: that is what the client actually sends.
        self.assertEqual(
            classify_channel_message_payload(_wstring("") + _wstring("x")),
            CHANNEL_MESSAGE_ACCEPTED,
        )

    def test_non_string_and_non_bytes_inputs_are_refused(self):
        for payload in (None, "48000000", 34, ["\x48"]):
            self.assertNotEqual(
                classify_channel_message_payload(payload),
                CHANNEL_MESSAGE_ACCEPTED,
            )
        for speaker, body in ((None, "ok"), (42, "ok"), ("ok", None), ("ok", 42)):
            with self.assertRaises(ValueError):
                encode_channel_message_payload(speaker, body)

    def test_no_rejection_path_ever_returns_a_partial_message(self):
        # Every classify result is either the accepted token or a declared
        # rejection reason; decode raises rather than returning half a pair.
        from pirateforce_foundation.channel_message_hypothesis import (
            CHANNEL_MESSAGE_REJECTIONS,
        )
        samples = (
            b"", b"\x48", CHAT_INPUT_PROBE_PAYLOADS["probe1"] + b"\x00",
            _wstring("a") + _wstring(""), b"\x0b" * 34,
        )
        for payload in samples:
            reason = classify_channel_message_payload(payload)
            self.assertIn(reason, CHANNEL_MESSAGE_REJECTIONS)
            with self.assertRaises(ValueError) as raised:
                decode_channel_message_payload(payload)
            self.assertIn(reason, str(raised.exception))


class ComposedResponseTests(unittest.TestCase):
    """The emitter side, cross-checked against the older lane's pins."""

    @classmethod
    def setUpClass(cls):
        # Source import only: no server is started, no socket is opened, no
        # database is touched.
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_generated_localtalk_response_equals_the_chat_echo_001_pins(self):
        # THE cross-check.  These hashes were produced by the opaque-splice
        # echo path, which never parsed the payload; reproducing them from a
        # payload built out of (speaker, body) is what proves the decode.
        pinned = json.loads(ECHO_SCENARIO_PATH.read_text(encoding="utf-8"))
        composed = pinned["composed_responses"]
        for probe in ("probe1", "probe2"):
            pc, frame = make_channel_message_response(
                self.legacy, CHAT_INPUT_VITAL_ID,
                CHANNEL_MESSAGE_PROBE_SPEAKER,
                CHANNEL_MESSAGE_PROBE_BODIES[probe],
            )
            self.assertEqual(len(pc), composed["pc_size"])
            self.assertEqual(len(frame), composed["frame_size"])
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                composed[probe]["pc_sha256"], probe,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                composed[probe]["frame_sha256"], probe,
            )
            # ...and the request side the echo lane pinned is the same bytes.
            self.assertEqual(
                hashlib.sha256(
                    pc[CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET:
                       CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET + 34],
                ).hexdigest().upper(),
                pinned["requests"][probe]["payload_sha256"],
            )

    def test_generated_speaker_variant_equals_the_chat_echo_002_pins(self):
        for probe in ("probe1", "probe2"):
            payload = encode_channel_message_payload(
                CHAT_INPUT_SPEAKER_PROBE_NAME,
                CHANNEL_MESSAGE_PROBE_BODIES[probe],
            )
            self.assertEqual(
                hashlib.sha256(payload).hexdigest().upper(),
                CHAT_INPUT_SPEAKER_PROBE_PAYLOAD_SHA256[probe],
            )
            pc, frame = make_channel_message_response(
                self.legacy, CHAT_INPUT_VITAL_ID,
                CHAT_INPUT_SPEAKER_PROBE_NAME,
                CHANNEL_MESSAGE_PROBE_BODIES[probe],
            )
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                CHAT_INPUT_SPEAKER_ECHO_PC_SHA256[probe],
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256[probe],
            )

    def test_all_five_channels_are_pinned_and_wire_identical(self):
        pcs = {}
        for name, channel_id in SHARED_SERIALIZER_CHANNEL_IDS.items():
            pc, frame = make_channel_message_response(
                self.legacy, channel_id,
                CHANNEL_MESSAGE_PROBE_SPEAKER,
                CHANNEL_MESSAGE_PROBE_BODIES["probe1"],
            )
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                CHANNEL_MESSAGE_PROBE1_PC_SHA256[name], name,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                CHANNEL_MESSAGE_PROBE1_FRAME_SHA256[name], name,
            )
            self.assertEqual(
                pc[PC_CHANNEL_ID_SLICE], channel_id.to_bytes(2, "little"),
            )
            pcs[name] = pc
        # CHAT-CHANNEL-001's central finding, reproduced on composed bytes:
        # the five differ ONLY in the 16-bit class id.
        self.assertEqual(len(set(pcs.values())), 5)
        blanked = {
            pc[:PC_CHANNEL_ID_SLICE.start] + b"\x00\x00"
            + pc[PC_CHANNEL_ID_SLICE.stop:]
            for pc in pcs.values()
        }
        self.assertEqual(len(blanked), 1)
        payloads = {
            pc[CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET:
               CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET + 34]
            for pc in pcs.values()
        }
        self.assertEqual(payloads, {CHAT_INPUT_PROBE_PAYLOADS["probe1"]})

    def test_composition_needs_no_request_template(self):
        # A message this project has never captured, on a channel this project
        # has never seen, composes deterministically from (speaker, body).
        pc, frame = make_channel_message_response(
            self.legacy,
            SHARED_SERIALIZER_CHANNEL_IDS["Channel_GuildMessageVital"],
            "test01", "guild hello",
        )
        payload = encode_channel_message_payload("test01", "guild hello")
        self.assertEqual(len(pc), len(payload) + CHANNEL_MESSAGE_PC_OVERHEAD)
        self.assertEqual(
            pc[CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET:
               CHANNEL_MESSAGE_PC_PAYLOAD_OFFSET + len(payload)], payload,
        )
        self.assertEqual(
            decode_channel_message(
                SHARED_SERIALIZER_CHANNEL_IDS["Channel_GuildMessageVital"],
                payload,
            ),
            ChannelMessage(
                0x8189, "Channel_GuildMessageVital", "test01", "guild hello",
            ),
        )
        self.assertEqual(
            (pc, frame),
            self.legacy.make_runtime_vitals([(0x8189, 0, payload)]),
        )

    def test_composition_is_deterministic_and_repeatable(self):
        first = make_channel_message_response(
            self.legacy, CHAT_INPUT_VITAL_ID, "test01", "PFCHATPROBE1",
        )
        second = make_channel_message_response(
            self.legacy, CHAT_INPUT_VITAL_ID, "test01", "PFCHATPROBE1",
        )
        self.assertEqual(first, second)

    def test_the_envelope_is_the_reused_v141_helper_not_a_new_one(self):
        payload = encode_channel_message_payload("", "PFCHATPROBE1")
        self.assertEqual(
            make_channel_message_response(
                self.legacy, CHAT_INPUT_VITAL_ID, "", "PFCHATPROBE1",
            ),
            self.legacy.make_runtime_vitals([
                (CHAT_INPUT_VITAL_ID, 0, payload),
            ]),
        )

    def test_composition_refuses_every_rejected_input(self):
        for channel_id, speaker, body in (
            (CHANNEL_WHISPER_VITAL_ID, "", "PFCHATPROBE1"),
            (0xBA58, "", "PFCHATPROBE1"),
            (CHAT_INPUT_VITAL_ID, "", ""),
            (CHAT_INPUT_VITAL_ID, None, "PFCHATPROBE1"),
            (CHAT_INPUT_VITAL_ID, "\U0001F600", "PFCHATPROBE1"),
            (CHAT_INPUT_VITAL_ID, "", "\ud800"),
        ):
            with self.assertRaises(ValueError):
                make_channel_message_response(
                    self.legacy, channel_id, speaker, body,
                )


class ScenarioGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_scenario_loads_and_is_opt_in_test_only(self):
        scenario = load_channel_message_hypothesis_scenario(SCENARIO_PATH)
        self.assertEqual(scenario.hypothesis_id, "HYP-PF-019")
        self.assertEqual(
            scenario.scenario_id, "channel_message_hypothesis_shared_serializer",
        )
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertIs(data["test_only"], True)
        self.assertIs(data["production_allowed"], False)
        self.assertEqual(data["persisted_post_state"]["database_write"], "none")
        self.assertEqual(
            data["requests"]["shape"]["rejected_channel_ids"],
            [CHANNEL_WHISPER_VITAL_ID],
        )
        self.assertEqual(
            sorted(data["requests"]["shape"]["accepted_channel_ids"]),
            sorted(CHANNEL_NAME_BY_ID),
        )

    def test_scenario_allowlist_is_exact(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("test_only", False),
            lambda d: d.__setitem__("hypothesis_id", "HYP-PF-014"),
            lambda d: d.__setitem__("id", "channel_message_hypothesis_v2"),
            lambda d: d.__setitem__("extra_field", 1),
            lambda d: d.pop("nonclaims"),
            lambda d: d["persisted_post_state"].__setitem__(
                "database_write", "chat_messages",
            ),
            lambda d: d["requests"]["shape"]["accepted_channel_ids"].append(
                CHANNEL_WHISPER_VITAL_ID,
            ),
            lambda d: d["composed_responses"]["per_channel"][
                "Channel_GuildMessageVital"
            ].__setitem__("frame_sha256", "00" * 32),
            lambda d: d["composed_responses"]["crosscheck"].__setitem__(
                "chat_echo_001_probe1_pc_sha256", "00" * 32,
            ),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_channel_message_hypothesis_scenario(tampered)

    def test_unrelated_scenario_files_never_load_through_this_gate(self):
        for path in (ECHO_SCENARIO_PATH, SPEAKER_SCENARIO_PATH):
            with self.assertRaises(ValueError):
                load_channel_message_hypothesis_scenario(path)
        missing = Path(self.tmp.name) / "nope.json"
        with self.assertRaises(ValueError):
            load_channel_message_hypothesis_scenario(missing)

    def test_the_chat_echo_scenario_files_are_untouched(self):
        self.assertEqual(
            hashlib.sha256(ECHO_SCENARIO_PATH.read_bytes()).hexdigest().upper(),
            ECHO_SCENARIO_FILE_SHA256,
        )

    def test_this_lane_is_reachable_only_through_the_opt_in_scenario(self):
        """CHAT-CHANNEL-003 deliberately changed what this guard can assert.

        Until 2026-08-18 this test asserted the strongest possible containment:
        the string ``channel_message_hypothesis`` appeared in NO runtime module
        at all, so the lane was unreachable by construction rather than by
        flag.  That was the honest statement of CHAT-CHANNEL-002, whose whole
        point was a codec with no way to reach the wire -- which is also why
        GT-016 stayed BLOCKED.  CHAT-CHANNEL-003 is the milestone that hooks it
        up, so ``runtime.py`` and ``app.py`` now import it on purpose and this
        assertion had to move rather than be worked around.  (It was NOT worked
        around: no indirection, no lazy import, no derived module name -- the
        two importers are named below and the list is exact, so a third one
        shows up here as a failure.)

        What is still true, and is what this guard now pins:

          * ``connection.py`` and ``scenario.py`` still never mention it.
          * Nothing reaches the lane without an explicit opt-in scenario
            object: every mention in ``runtime.py`` is inside the
            ``channel_message_hypothesis_scenario is not None`` gate, and
            ``app.py`` only builds one from an explicit CLI flag.
          * Both scenario profiles keep ``production_allowed: false`` and
            ``database_write: none``.
          * The frozen v141 module still knows nothing about any of it.

        The runtime-behaviour half of this contract (no scenario => zero
        actions, zero events, byte-identical database) is proven against the
        real dispatch path in tests/test_channel_message_dispatch.py.
        """
        module = "channel_message_hypothesis"
        src = ROOT / "src" / "pirateforce_foundation"
        importers = sorted(
            path.name for path in src.glob("*.py")
            if module in path.read_text(encoding="utf-8")
            and path.name != f"{module}.py"
        )
        self.assertEqual(importers, ["app.py", "runtime.py"])
        for name in ("connection.py", "scenario.py"):
            self.assertNotIn(
                module, (src / name).read_text(encoding="utf-8"), name,
            )
        legacy_source = LEGACY_PATH.read_text(encoding="utf-8")
        self.assertNotIn(module, legacy_source)
        self.assertNotIn("Channel_", legacy_source)

    def test_every_runtime_mention_sits_behind_the_opt_in_gate(self):
        # The lane may be imported, but it must be impossible to enter it
        # without an opt-in scenario object.  Both call sites and the branch
        # that guards them are named here so that adding an ungated one fails.
        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "if channel_message_hypothesis_scenario is not None:", source,
        )
        self.assertIn(
            "channel_message_hypothesis_scenario is not None\n"
            "                and nested_id == CHAT_INPUT_VITAL_ID",
            source,
        )
        # The composer is reached from exactly one call site (the import line
        # is the other mention).
        self.assertEqual(source.count("make_channel_message_response"), 2)
        self.assertEqual(source.count("make_channel_message_response("), 1)
        self.assertEqual(
            source.count("_dispatch_channel_message_hypothesis"), 2,
        )

    def test_both_profiles_stay_test_only_with_no_database_write(self):
        for path in (SCENARIO_PATH, SWEEP_SCENARIO_PATH):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIs(data["test_only"], True, path.name)
            self.assertIs(data["production_allowed"], False, path.name)
            self.assertEqual(
                data["persisted_post_state"]["database_write"], "none",
                path.name,
            )
            self.assertEqual(data["hypothesis_id"], "HYP-PF-019", path.name)

    def test_the_cli_flag_requires_an_explicit_database(self):
        source = (
            ROOT / "src" / "pirateforce_foundation" / "app.py"
        ).read_text(encoding="utf-8")
        self.assertIn("--channel-message-hypothesis-scenario", source)
        self.assertIn(
            "'--channel-message-hypothesis-scenario requires an explicit "
            "existing --db'",
            source,
        )

    def test_the_sweep_profile_loads_and_pins_the_dispatch_policy(self):
        scenario = load_channel_message_hypothesis_scenario(SWEEP_SCENARIO_PATH)
        self.assertEqual(scenario.scenario_id, CHANNEL_SWEEP_SCENARIO_ID)
        self.assertEqual(scenario.channel_order, CHANNEL_SWEEP_ORDER)
        self.assertEqual(scenario.spacing_seconds, CHANNEL_SWEEP_SPACING_SECONDS)
        # The codec-only profile carries no dispatch policy at all: it cannot
        # be handed to the sweep branch and accidentally emit one frame.
        codec_only = load_channel_message_hypothesis_scenario(SCENARIO_PATH)
        self.assertEqual(codec_only.channel_order, ())
        self.assertEqual(codec_only.spacing_seconds, 0.0)

    def test_the_sweep_profile_allowlist_is_exact(self):
        data = json.loads(SWEEP_SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("test_only", False),
            lambda d: d.__setitem__("id", "channel_message_hypothesis_sweep_v2"),
            lambda d: d.__setitem__("extra_field", 1),
            lambda d: d.pop("nonclaims"),
            lambda d: d["dispatch"].__setitem__("spacing_seconds", 0.0),
            lambda d: d["dispatch"]["channel_order"].reverse(),
            lambda d: d["dispatch"]["channel_order"].pop(),
            lambda d: d["dispatch"].__setitem__(
                "speaker_policy", "selected_character_name",
            ),
            lambda d: d["persisted_post_state"].__setitem__(
                "database_write", "chat_messages",
            ),
            lambda d: d["composed_responses"]["per_channel"][
                "Channel_GMGlobalMessageVital"
            ].__setitem__("pc_sha256", "00" * 32),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered_sweep.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_channel_message_hypothesis_scenario(tampered)

    def test_the_shared_serializer_profile_file_is_untouched(self):
        # CHAT-CHANNEL-002 pinned that file end to end; CHAT-CHANNEL-003 adds a
        # second file rather than editing it.
        self.assertEqual(
            hashlib.sha256(SCENARIO_PATH.read_bytes()).hexdigest().upper(),
            SHARED_SERIALIZER_SCENARIO_FILE_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
