"""Governed designed echo-ack for the chat input frame ``UNKNOWN_0xAC52``.

The vital id 0xAC52 (44114) is absent from the v141 registry; the project
names table has since resolved it to ``Channel_LocalTalkMessageVital``
(``docs/PF_VITAL_NAMES.json``, RESOLVE-001).  This module keeps its
capture-era identifier ``UNKNOWN_0xAC52`` and stands on the proven UI action
behind it: GT-006 (grade B,
``reports/PF_GT006_CHAT_INPUT_UNKNOWN_FRAME_WIRE_CAPTURE_20260817.md``)
captured that typing an ASCII message into the client's chat box and pressing
Enter emits exactly one 34-byte payload vital id 0xAC52, version 0,
vital_count 1, inside the standard ``GSCN_RunTimeProtocolReq`` envelope
(pc_len 54); the server dispatched nothing and answered nothing, and the
client rendered no echo.  No lawful original-server response exists in the
corpus, so the response composed here is a *designed hypothesis*: the server
echoes the exact request vital back inside the accepted
``GSCN_RunTimeProtocolRes`` v4 collection envelope (56-byte PC / 66-byte
frame) and writes nothing anywhere -- chat has no table and this lane never
touches the store.  Both captured payloads share a fixed 10-byte prefix
``48 00 00 00 00 48 18 00 00 00`` followed by 12 (low, 0x00) byte pairs whose
low bytes are printable ASCII; byte index 6 (0x18 = 24) is a *candidate*
length field that only two equal-length samples support, so nothing here
claims or decodes it -- the prefix is compared as one opaque pinned blob.
This module is opt-in, test-only, and fails closed on every other payload:
wrong envelope, wrong length, wrong prefix, non-zero high bytes, and
non-printable low bytes all classify as rejection with no reply and no write.

CHAT-ECHO-002 (second tracked version, own opt-in scenario): attended GT-009
proved the byte-exact echo client-accepted and rendered with an *empty*
speaker slot, and the speaker-field research
(``reports/PF_CHAT_ECHO002_SPEAKER_FIELD_RESEARCH_20260818.md``) reads the
captured 10-byte prefix as two wstring headers -- tag ``0x48`` + u32 byte
length, the same convention grade-A proven for CreateActorDataEx/ActorAttr
names -- where wstring#1 (empty in every captured request) is the candidate
speaker-name field.  The designed variant behind
``scenarios/chat_input_hypothesis_speaker_echo.json`` keeps the identical
accepted request shape and every fail-closed guard and changes only the
composition: wstring#1 is filled with the selected character's canonical
name (UTF-16LE), everything from the second wstring header on is echoed
byte-exactly, and the composed PC is always ``56 + 2*len(name)`` bytes.  A
missing, empty, or non-two-byte-encodable name fails closed with no reply
and no write.  Whether the real client renders the name is not claimed here
(GT-012, attended big round #3).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


# UNKNOWN_0xAC52: the chat input frame (name from the GT-006 UI action only).
CHAT_INPUT_VITAL_ID = 0xAC52

# Shape pins measured in GT-006 (byte-counting only, no decode).
CHAT_INPUT_PAYLOAD_SIZE = 34
CHAT_INPUT_PREFIX = bytes.fromhex("48000000004818000000")
CHAT_INPUT_TEXT_PAIRS = 12
CHAT_INPUT_PRINTABLE_MIN = 0x20
CHAT_INPUT_PRINTABLE_MAX = 0x7E

# Captured original-client request payloads (34 bytes each, GT-006 seq 2-3):
# the fixed 10-byte prefix plus the typed characters interleaved with 0x00.
CHAT_INPUT_PROBE_PAYLOADS = {
    "probe1": bytes.fromhex(
        "48000000004818000000"
        "500046004300480041005400500052004F00420045003100"
    ),
    "probe2": bytes.fromhex(
        "48000000004818000000"
        "500046004300480041005400500052004F00420045003200"
    ),
}
CHAT_INPUT_PROBE_PAYLOAD_SHA256 = {
    "probe1": (
        "0DC90C60BB22C92FDFF3649125703546E9BE324C2D7C265023C00DACA1C584CF"
    ),
    "probe2": (
        "59ED7CD6071BC4D094098DFBAFA91ED6D190637A1AE07FC90B6937A6A9DCB208"
    ),
}

# Full request PCs (54 bytes, the GT-006 pc_len), pinned for tests and replay
# tooling: the one-vital GSCN_RunTimeProtocolReq envelope every captured
# client request uses, carrying the 34-byte payload.
CHAT_INPUT_PROBE_REQUEST_PCS = {
    "probe1": bytes.fromhex(
        "126F6E140000000008000B021201001252AC0B00"
        "48000000004818000000"
        "500046004300480041005400500052004F00420045003100"
    ),
    "probe2": bytes.fromhex(
        "126F6E140000000008000B021201001252AC0B00"
        "48000000004818000000"
        "500046004300480041005400500052004F00420045003200"
    ),
}
CHAT_INPUT_PROBE_REQUEST_PC_SHA256 = {
    "probe1": (
        "49C9BEA57F99246E19CF8DAB7A7D5A908DF7F230E71665762D6A6CAA0196154C"
    ),
    "probe2": (
        "33B905CDD41065A1DE58BCED9A92697F5FA2C77E7C397954BD4DEE84D89DA42C"
    ),
}

# Designed echo composition (GSCN_RunTimeProtocolRes v4, one vital, version 0,
# payload byte-equal to the request payload, proven trailing derived-class
# mask byte).  56-byte PC / 66-byte frame, deterministic per payload; the two
# captured probes are hash-pinned end to end.
CHAT_INPUT_ECHO_PC_SIZE = 56
CHAT_INPUT_ECHO_FRAME_SIZE = 66
CHAT_INPUT_ECHO_PC_SHA256 = {
    "probe1": (
        "B92C185ABB0C707EA6512409CAAF5ADC03D911E0399F0CC0DC60A2C49111FA06"
    ),
    "probe2": (
        "539B177F430B4391348F440932E119C1D58788BF15BFA061BF16F56E4DDDFC2C"
    ),
}
CHAT_INPUT_ECHO_FRAME_SHA256 = {
    "probe1": (
        "06C23375BE9A115C59AF410E1446393E2EE3B3294254BCDF6EB88FADFF7E2323"
    ),
    "probe2": (
        "E97A12256A0D61F8CBB8B433336F97D9EEA2A93CADA5934EAAEB5B7D4706EA10"
    ),
}

# CHAT-ECHO-002 speaker-name wstring composition (HYP-PF-014 version 2).
# The captured 10-byte prefix splits at the fixed offset 5: bytes 0-4 are the
# wstring#1 header (tag 0x48 + u32 length 0 = empty speaker slot) and bytes
# 5-9 are the wstring#2 header carrying the text length.  The variant
# replaces only the first 5 bytes with a real header + name and echoes
# everything from the second header on byte-exactly, so the composed PC is
# always 56 + 2*len(name) bytes.  (The frame grows by one extra byte over
# the naive +10 once the PC exceeds 60 bytes: the snappy literal header
# takes a second tag byte -- hence 68-byte PC / 79-byte frame below.)
CHAT_INPUT_SPEAKER_NAME_HEADER_SIZE = 5
CHAT_INPUT_SPEAKER_ECHO_PC_BASE_SIZE = 56
CHAT_INPUT_SPEAKER_ECHO_SCENARIO_ID = (
    "chat_input_hypothesis_speaker_echo_ascii12"
)

# Deterministic probe forms: both captured GT-006 payloads composed under the
# canonical smoke character name -- the persisted name the pinned V25 create
# wire commits ("test01", the same canonical `characters.name` NAME001/002
# proved the client accepts inside ActorAttr) -- hash-pinned end to end.
CHAT_INPUT_SPEAKER_PROBE_NAME = "test01"
CHAT_INPUT_SPEAKER_PROBE_PAYLOAD_SHA256 = {
    "probe1": (
        "D702CEE2B3BD83E7568EBAFC93B73D3B87D9AF643EE8155B36D827A6E24B4A02"
    ),
    "probe2": (
        "A9060FC24E676B8BB5752814A6404E8F95FB9438B9EA755727E480699A046921"
    ),
}
CHAT_INPUT_SPEAKER_ECHO_PC_SIZE = 68
CHAT_INPUT_SPEAKER_ECHO_FRAME_SIZE = 79
CHAT_INPUT_SPEAKER_ECHO_PC_SHA256 = {
    "probe1": (
        "5D80E83CE4C60A3927C9AFE020B0833358763BFE3CA1ECAB3EFB28E98BC9EE17"
    ),
    "probe2": (
        "8717FC3F5282269CF591FEFE24C2152E443C843A63B9927A0514D424D6EBA9F2"
    ),
}
CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256 = {
    "probe1": (
        "AA27B015AB9EA30537331408D5F262BC37EA489A0DB8E7B3BC7D4A1896D99D23"
    ),
    "probe2": (
        "79ABB34925D20793A0AC718246ACC717D8ECF8F41FB9DCDC0BD482E23FFE1FFA"
    ),
}


@dataclass(frozen=True)
class ChatInputHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    request_payload_sha256_probe1: str
    request_payload_sha256_probe2: str
    echo_pc_sha256_probe1: str
    echo_pc_sha256_probe2: str
    echo_frame_sha256_probe1: str
    echo_frame_sha256_probe2: str


_PROFILE_ECHO_ASCII12 = ChatInputHypothesisScenario(
    "chat_input_hypothesis_echo_ascii12",
    "HYP-PF-014",
    CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe1"],
    CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe2"],
    CHAT_INPUT_ECHO_PC_SHA256["probe1"],
    CHAT_INPUT_ECHO_PC_SHA256["probe2"],
    CHAT_INPUT_ECHO_FRAME_SHA256["probe1"],
    CHAT_INPUT_ECHO_FRAME_SHA256["probe2"],
)

_EXPECTED_ECHO_ASCII12 = {
    "schema": 1,
    "id": _PROFILE_ECHO_ASCII12.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_ECHO_ASCII12.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "response_policy": "echo_exact_request_vital_no_write_no_close",
    },
    "requests": {
        "shape": {
            "payload_size": CHAT_INPUT_PAYLOAD_SIZE,
            "prefix_hex": "48000000004818000000",
            "text_pairs": CHAT_INPUT_TEXT_PAIRS,
            "charset": "printable_ascii_0x20_0x7E",
        },
        "probe1": {
            "payload_size": CHAT_INPUT_PAYLOAD_SIZE,
            "payload_sha256": CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe1"],
            "pc_size": 54,
            "pc_sha256": CHAT_INPUT_PROBE_REQUEST_PC_SHA256["probe1"],
        },
        "probe2": {
            "payload_size": CHAT_INPUT_PAYLOAD_SIZE,
            "payload_sha256": CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe2"],
            "pc_size": 54,
            "pc_sha256": CHAT_INPUT_PROBE_REQUEST_PC_SHA256["probe2"],
        },
    },
    "composed_responses": {
        "policy": "echo_exact_request_vital_in_accepted_runtime_res_envelope",
        "pc_size": CHAT_INPUT_ECHO_PC_SIZE,
        "frame_size": CHAT_INPUT_ECHO_FRAME_SIZE,
        "probe1": {
            "pc_sha256": CHAT_INPUT_ECHO_PC_SHA256["probe1"],
            "frame_sha256": CHAT_INPUT_ECHO_FRAME_SHA256["probe1"],
        },
        "probe2": {
            "pc_sha256": CHAT_INPUT_ECHO_PC_SHA256["probe2"],
            "frame_sha256": CHAT_INPUT_ECHO_FRAME_SHA256["probe2"],
        },
    },
    "persisted_post_state": {
        "database_write": "none",
    },
    "capabilities": [
        "echo_acknowledge_exact_shape_pinned_chat_input_frames",
        "repeatable_echo_per_session_no_state_change",
    ],
    "nonclaims": [
        "prefix_byte_semantics_including_the_0x18_candidate_length_field",
        "text_lengths_other_than_12_characters",
        "non_ascii_or_thai_text",
        "channel_whisper_broadcast_semantics",
        "delivery_to_any_other_client",
        "message_persistence_or_database_write",
        "original_server_response_policy",
        "client_observable_chat_echo_or_rendering",
        "production_baseline_behavior",
    ],
}

_PROFILE_SPEAKER_ECHO_ASCII12 = ChatInputHypothesisScenario(
    CHAT_INPUT_SPEAKER_ECHO_SCENARIO_ID,
    "HYP-PF-014",
    CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe1"],
    CHAT_INPUT_PROBE_PAYLOAD_SHA256["probe2"],
    CHAT_INPUT_SPEAKER_ECHO_PC_SHA256["probe1"],
    CHAT_INPUT_SPEAKER_ECHO_PC_SHA256["probe2"],
    CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256["probe1"],
    CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256["probe2"],
)

_EXPECTED_SPEAKER_ECHO_ASCII12 = {
    "schema": 1,
    "id": _PROFILE_SPEAKER_ECHO_ASCII12.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_SPEAKER_ECHO_ASCII12.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "response_policy": "speaker_wstring_echo_no_write_no_close",
    },
    # The accepted request side is deliberately byte-identical to the plain
    # echo scenario: CHAT-ECHO-002 changes only the composition.
    "requests": _EXPECTED_ECHO_ASCII12["requests"],
    "composed_responses": {
        "policy": (
            "selected_character_name_fills_wstring1_"
            "in_accepted_runtime_res_envelope"
        ),
        "pc_size_rule": "56_plus_2_bytes_per_speaker_name_character",
        "probe_speaker_name": CHAT_INPUT_SPEAKER_PROBE_NAME,
        "pc_size": CHAT_INPUT_SPEAKER_ECHO_PC_SIZE,
        "frame_size": CHAT_INPUT_SPEAKER_ECHO_FRAME_SIZE,
        "probe1": {
            "pc_sha256": CHAT_INPUT_SPEAKER_ECHO_PC_SHA256["probe1"],
            "frame_sha256": CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256["probe1"],
        },
        "probe2": {
            "pc_sha256": CHAT_INPUT_SPEAKER_ECHO_PC_SHA256["probe2"],
            "frame_sha256": CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256["probe2"],
        },
    },
    "persisted_post_state": {
        "database_write": "none",
    },
    "capabilities": [
        "speaker_name_wstring_echo_of_exact_shape_pinned_chat_input_frames",
        "repeatable_echo_per_session_no_state_change",
    ],
    "nonclaims": [
        "prefix_byte_semantics_including_the_0x18_candidate_length_field",
        "wstring1_speaker_name_semantics_until_attended_gt012",
        "text_lengths_other_than_12_characters",
        "non_ascii_or_thai_text",
        "thai_or_non_bmp_speaker_names_on_the_wire",
        "channel_tag_selection_mechanism",
        "channel_whisper_broadcast_semantics",
        "delivery_to_any_other_client",
        "message_persistence_or_database_write",
        "original_server_response_policy",
        "client_observable_speaker_name_rendering",
        "production_baseline_behavior",
    ],
}

_EXPECTED_BY_ID = {
    _PROFILE_ECHO_ASCII12.scenario_id: (
        _EXPECTED_ECHO_ASCII12, _PROFILE_ECHO_ASCII12,
    ),
    _PROFILE_SPEAKER_ECHO_ASCII12.scenario_id: (
        _EXPECTED_SPEAKER_ECHO_ASCII12, _PROFILE_SPEAKER_ECHO_ASCII12,
    ),
}


def _exact_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(
            _exact_equal(actual[key], value) for key, value in expected.items()
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _exact_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def load_chat_input_hypothesis_scenario(
    path: str | Path,
) -> ChatInputHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid chat input hypothesis scenario") from exc
    if type(data) is not dict or data.get("id") not in _EXPECTED_BY_ID:
        raise ValueError(
            "chat input hypothesis scenario exceeds the exact allowlist"
        )
    expected, profile = _EXPECTED_BY_ID[data["id"]]
    if not _exact_equal(data, expected):
        raise ValueError(
            "chat input hypothesis scenario exceeds the exact allowlist"
        )
    return require_chat_input_hypothesis_scenario(profile)


def require_chat_input_hypothesis_scenario(
    value: Any,
) -> ChatInputHypothesisScenario:
    if type(value) is not ChatInputHypothesisScenario or value not in (
        _PROFILE_ECHO_ASCII12, _PROFILE_SPEAKER_ECHO_ASCII12,
    ):
        raise ValueError(
            "chat input hypothesis scenario object exceeds the allowlist"
        )
    for probe, payload in CHAT_INPUT_PROBE_PAYLOADS.items():
        digest = hashlib.sha256(payload).hexdigest().upper()
        if digest != CHAT_INPUT_PROBE_PAYLOAD_SHA256[probe]:
            raise RuntimeError("chat input hypothesis payload fixture drift")
        pc_digest = hashlib.sha256(
            CHAT_INPUT_PROBE_REQUEST_PCS[probe]
        ).hexdigest().upper()
        if pc_digest != CHAT_INPUT_PROBE_REQUEST_PC_SHA256[probe]:
            raise RuntimeError("chat input hypothesis request fixture drift")
        if classify_chat_input_payload(payload) != "ascii12":
            raise RuntimeError("chat input hypothesis fixture shape drift")
        speaker_payload = compose_chat_input_speaker_payload(
            CHAT_INPUT_SPEAKER_PROBE_NAME, payload,
        )
        speaker_digest = hashlib.sha256(speaker_payload).hexdigest().upper()
        if speaker_digest != CHAT_INPUT_SPEAKER_PROBE_PAYLOAD_SHA256[probe]:
            raise RuntimeError("chat input hypothesis speaker fixture drift")
    return value


def classify_chat_input_payload(payload: bytes) -> str:
    """Classify one nested payload against the exact GT-006 shape pins."""
    if len(payload) != CHAT_INPUT_PAYLOAD_SIZE:
        return "wrong_length"
    if payload[: len(CHAT_INPUT_PREFIX)] != CHAT_INPUT_PREFIX:
        return "wrong_prefix"
    text = payload[len(CHAT_INPUT_PREFIX):]
    for index in range(CHAT_INPUT_TEXT_PAIRS):
        low = text[2 * index]
        high = text[2 * index + 1]
        if high != 0x00 or not (
            CHAT_INPUT_PRINTABLE_MIN <= low <= CHAT_INPUT_PRINTABLE_MAX
        ):
            return "wrong_text"
    return "ascii12"


def classify_chat_input_attempt(legacy: Any, parsed: Any) -> str:
    """Classify one 0xAC52-bearing parse against the exact captured form.

    The accepted envelope is the same one-vital client request envelope the
    logout lane accepts: GSCN_RunTimeProtocolReq, outer version 0, outer mask
    0x02, vital_count 1, nested version 0.  Everything else fails closed.
    """
    if not (
        parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
        and parsed.outer_version == 0
        and parsed.outer_mask == 0x02
        and parsed.vital_count == 1
        and parsed.nested_id == CHAT_INPUT_VITAL_ID
        and parsed.nested_version == 0
    ):
        return "wrong_envelope"
    return classify_chat_input_payload(parsed.nested_payload)


# PF-HYPOTHESIS-LEDGER: HYP-PF-014 active
def make_chat_input_echo_response(legacy: Any, payload: bytes) -> tuple[bytes, bytes]:
    """Build and independently pin the designed echo for one accepted payload.

    Every payload must re-pass the exact shape classification; the composed
    PC must carry the request payload byte-exactly at the fixed offset of the
    one-vital RuntimeRes envelope.  The two captured GT-006 probes are
    additionally drift-checked against their pinned pc/frame hashes.
    """
    if classify_chat_input_payload(payload) != "ascii12":
        raise ValueError("chat input echo payload exceeds the accepted shape")
    pc, frame = legacy.make_runtime_vitals([
        (CHAT_INPUT_VITAL_ID, 0, payload),
    ])
    if len(pc) != CHAT_INPUT_ECHO_PC_SIZE or pc[20:54] != payload:
        raise RuntimeError("HYP-PF-014 echo is not the byte-exact request payload")
    if len(frame) != CHAT_INPUT_ECHO_FRAME_SIZE:
        raise RuntimeError("HYP-PF-014 response frame drift")
    payload_digest = hashlib.sha256(payload).hexdigest().upper()
    for probe, pinned in CHAT_INPUT_PROBE_PAYLOAD_SHA256.items():
        if payload_digest != pinned:
            continue
        if (
            hashlib.sha256(pc).hexdigest().upper()
            != CHAT_INPUT_ECHO_PC_SHA256[probe]
        ):
            raise RuntimeError("HYP-PF-014 response PC drift")
        if (
            hashlib.sha256(frame).hexdigest().upper()
            != CHAT_INPUT_ECHO_FRAME_SHA256[probe]
        ):
            raise RuntimeError("HYP-PF-014 response frame drift")
    return pc, frame


def compose_chat_input_speaker_payload(
    speaker_name: str, payload: bytes,
) -> bytes:
    """Fill wstring#1 of one accepted payload with the speaker name.

    Fail closed on every name the fixed-size reading cannot carry: only a
    non-empty ``str`` whose UTF-16LE encoding is exactly two bytes per
    character (no surrogate pairs, no unpaired surrogates) composes, so the
    resulting payload is always ``len(payload) + 2*len(speaker_name)`` bytes
    and the composed PC keeps the researched ``56 + 2*len(name)`` size.
    Everything from the second wstring header on is kept byte-exactly.
    """
    if classify_chat_input_payload(payload) != "ascii12":
        raise ValueError(
            "chat input speaker payload exceeds the accepted shape"
        )
    if type(speaker_name) is not str or not speaker_name:
        raise ValueError("chat input speaker name is unavailable")
    try:
        name_bytes = speaker_name.encode("utf-16-le")
    except UnicodeEncodeError as exc:
        raise ValueError(
            "chat input speaker name is not UTF-16LE encodable"
        ) from exc
    if len(name_bytes) != 2 * len(speaker_name):
        raise ValueError(
            "chat input speaker name exceeds the two-byte-per-character form"
        )
    return (
        payload[:1]
        + len(name_bytes).to_bytes(4, "little")
        + name_bytes
        + payload[CHAT_INPUT_SPEAKER_NAME_HEADER_SIZE:]
    )


def make_chat_input_speaker_echo_response(
    legacy: Any, payload: bytes, speaker_name: str,
) -> tuple[bytes, bytes]:
    """Build and independently pin the CHAT-ECHO-002 speaker-name variant.

    Same lane contract as the plain echo: the payload must re-pass the exact
    shape classification, nothing is written anywhere, and the composed PC
    must carry the variant payload byte-exactly at the fixed offset of the
    one-vital RuntimeRes envelope, at exactly the researched
    ``56 + 2*len(name)`` size.  The deterministic probe forms (both captured
    GT-006 payloads under the canonical smoke name) are additionally
    drift-checked against their pinned pc/frame hashes.
    """
    variant = compose_chat_input_speaker_payload(speaker_name, payload)
    pc, frame = legacy.make_runtime_vitals([
        (CHAT_INPUT_VITAL_ID, 0, variant),
    ])
    name_bytes_len = 2 * len(speaker_name)
    if len(pc) != CHAT_INPUT_SPEAKER_ECHO_PC_BASE_SIZE + name_bytes_len:
        raise RuntimeError("HYP-PF-014 speaker echo PC size drift")
    if pc[20:20 + len(variant)] != variant:
        raise RuntimeError(
            "HYP-PF-014 speaker echo is not the composed variant payload"
        )
    if variant[CHAT_INPUT_SPEAKER_NAME_HEADER_SIZE + name_bytes_len:] != (
        payload[CHAT_INPUT_SPEAKER_NAME_HEADER_SIZE:]
    ):
        raise RuntimeError(
            "HYP-PF-014 speaker echo text is not the byte-exact request text"
        )
    if speaker_name == CHAT_INPUT_SPEAKER_PROBE_NAME:
        payload_digest = hashlib.sha256(payload).hexdigest().upper()
        for probe, pinned in CHAT_INPUT_PROBE_PAYLOAD_SHA256.items():
            if payload_digest != pinned:
                continue
            if (
                hashlib.sha256(pc).hexdigest().upper()
                != CHAT_INPUT_SPEAKER_ECHO_PC_SHA256[probe]
            ):
                raise RuntimeError("HYP-PF-014 speaker echo PC drift")
            if (
                hashlib.sha256(frame).hexdigest().upper()
                != CHAT_INPUT_SPEAKER_ECHO_FRAME_SHA256[probe]
            ):
                raise RuntimeError("HYP-PF-014 speaker echo frame drift")
    return pc, frame
