"""Governed Grade-D acknowledged-logout composition for LogoutVital (0x1B40).

The client wire name (``LogoutVital``), its id, and both captured request
forms are the accepted R38/R40 decode results: subcode 01 is the in-game
"exit game" button and subcode 03 is "return to character select", each a
deterministic 34-byte PC / 44-byte frame across two independent sessions.
No lawful original-server response exists in the corpus, so the response
here is a *designed hypothesis*: the server echoes the exact request vital
back inside the accepted GSCN_RunTimeProtocolRes v4 collection envelope and
closes the session lease (``closed_at``) before any ack byte is queued.
After the ack the dispatch layer is silent (every inbound frame is counted
and ignored); the frozen v141 clock-driven transport heartbeat is unchanged
and continues until socket close, as it does in every accepted session.
This module is opt-in, test-only, and fails closed on every other payload.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


LOGOUT_VITAL_ID = 0x1B40
LOGOUT_SUBCODE_EXIT_GAME = 1
LOGOUT_SUBCODE_CHARACTER_SELECT = 3
LOGOUT_SUBCODES = (LOGOUT_SUBCODE_EXIT_GAME, LOGOUT_SUBCODE_CHARACTER_SELECT)

# Captured original-client request payloads (14 bytes each, byte-identical
# across capture_gt002 and capture_item_move_hyp001):
#   08 <subcode> 08 00 14 00000000 14 00000000
LOGOUT_REQUEST_PAYLOADS = {
    LOGOUT_SUBCODE_EXIT_GAME: bytes.fromhex(
        "0801080014000000001400000000"
    ),
    LOGOUT_SUBCODE_CHARACTER_SELECT: bytes.fromhex(
        "0803080014000000001400000000"
    ),
}

# Full captured request PCs (34 bytes), pinned for tests and replay tooling.
LOGOUT_REQUEST_PCS = {
    LOGOUT_SUBCODE_EXIT_GAME: bytes.fromhex(
        "126F6E140000000008000B0212010012401B0B00"
        "0801080014000000001400000000"
    ),
    LOGOUT_SUBCODE_CHARACTER_SELECT: bytes.fromhex(
        "126F6E140000000008000B0212010012401B0B00"
        "0803080014000000001400000000"
    ),
}
LOGOUT_REQUEST_PC_SHA256 = {
    LOGOUT_SUBCODE_EXIT_GAME: (
        "EF3B19F34A5FA55698617A16254BA5F722AC0BE44AF12170E1352CD206408973"
    ),
    LOGOUT_SUBCODE_CHARACTER_SELECT: (
        "EC5B53DCC49C034A9B716F893F4315104146B4220E9551C0101F1F699BB0FAA0"
    ),
}

# Designed echo-ack composition (GSCN_RunTimeProtocolRes v4, one vital,
# version 0, payload byte-equal to the request payload, proven trailing
# derived-class mask byte).  36-byte PC / 46-byte frame, deterministic.
LOGOUT_ACK_PC_SHA256 = {
    LOGOUT_SUBCODE_EXIT_GAME: (
        "9E4FA00E408910204C91DE264ED9274ECF7A3C7E8C37C75199F090AB7DE23C67"
    ),
    LOGOUT_SUBCODE_CHARACTER_SELECT: (
        "FC8B9E2CC2BD590458F1EAAFCE712D283538D525F136AD0F9838B108395F6DC6"
    ),
}
LOGOUT_ACK_FRAME_SHA256 = {
    LOGOUT_SUBCODE_EXIT_GAME: (
        "9B417B5F0EF05B1096FA000C7FC154DF952EF817232115DA077253BDC27A3D0A"
    ),
    LOGOUT_SUBCODE_CHARACTER_SELECT: (
        "AB172DFFCBC1195F086A848018FC4797D53945B6B2854D651D37B3740F4E6696"
    ),
}


# HYP-PF-013 (LOGOUT-CLOSE-001): after the byte-identical PF-012 ack, the
# server owns exactly one further lever it can pull without inventing payload
# bytes: a clean TCP shutdown+close of the accepted GAME socket.  The GT-007
# attended negative proved the echo-only shape leaves the real client parked
# on the never-closing socket (keepalive every ~2 s, no reconnect, no
# transition), and the corpus contains no 0x1B40 golden response, so the
# delayed server-initiated close is the next falsifiable hypothesis shape.
LOGOUT_POST_ACK_ACTION_NONE = "none"
LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET = "close_socket"
LOGOUT_CLOSE_DELAY_MS = 250


@dataclass(frozen=True)
class LogoutHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    request_pc_sha256_01: str
    request_pc_sha256_03: str
    ack_pc_sha256_01: str
    ack_pc_sha256_03: str
    ack_frame_sha256_01: str
    ack_frame_sha256_03: str
    post_ack_action: str
    close_delay_ms: int


_PROFILE_ECHO = LogoutHypothesisScenario(
    "logout_hypothesis_ack_echo_subcode01_03",
    "HYP-PF-012",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_NONE,
    0,
)

# PF-HYPOTHESIS-LEDGER: HYP-PF-013 active
_PROFILE_ACK_CLOSE = LogoutHypothesisScenario(
    "logout_hypothesis_ack_close_subcode01_03",
    "HYP-PF-013",
    LOGOUT_REQUEST_PC_SHA256[1],
    LOGOUT_REQUEST_PC_SHA256[3],
    LOGOUT_ACK_PC_SHA256[1],
    LOGOUT_ACK_PC_SHA256[3],
    LOGOUT_ACK_FRAME_SHA256[1],
    LOGOUT_ACK_FRAME_SHA256[3],
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_CLOSE_DELAY_MS,
)

_EXPECTED_ECHO = {
    "schema": 1,
    "id": _PROFILE_ECHO.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_ECHO.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "post_ack_policy": "dispatch_silent_until_socket_close",
    },
    "requests": {
        "subcode01": {
            "pc_size": 34,
            "pc_sha256": LOGOUT_REQUEST_PC_SHA256[1],
        },
        "subcode03": {
            "pc_size": 34,
            "pc_sha256": LOGOUT_REQUEST_PC_SHA256[3],
        },
    },
    "composed_responses": {
        "subcode01": {
            "pc_size": 36,
            "pc_sha256": LOGOUT_ACK_PC_SHA256[1],
            "frame_size": 46,
            "frame_sha256": LOGOUT_ACK_FRAME_SHA256[1],
        },
        "subcode03": {
            "pc_size": 36,
            "pc_sha256": LOGOUT_ACK_PC_SHA256[3],
            "frame_size": 46,
            "frame_sha256": LOGOUT_ACK_FRAME_SHA256[3],
        },
    },
    "persisted_post_state": {
        "sessions_closed_at": "written_before_ack_bytes_are_queued",
        "position_rewrite": "none",
    },
    "capabilities": [
        "acknowledge_exact_captured_logout_requests_after_clean_close",
        "silence_connection_after_acknowledged_logout",
    ],
    "nonclaims": [
        "original_server_response_policy",
        "client_observable_exit_or_character_select_return",
        "logout_outside_runtime_ready_sequence",
        "subcodes_other_than_01_and_03",
        "production_baseline_behavior",
    ],
}

# HYP-PF-013 exact allowlist: identical pins and identical fail-closed
# envelope to the echo scenario, plus the single new post-ack lever.  The
# ack bytes themselves are the unchanged hash-pinned PF-012 composition;
# no byte is invented under this scenario either.
_EXPECTED_ACK_CLOSE = {
    "schema": 1,
    "id": _PROFILE_ACK_CLOSE.scenario_id,
    "test_only": True,
    "production_allowed": False,
    "hypothesis_id": _PROFILE_ACK_CLOSE.hypothesis_id,
    "entry": {
        "flow": "full_writable_character",
        "required_sequence": "selected_and_runtime_ready",
        "post_ack_policy": "dispatch_silent_then_server_clean_socket_close",
        "post_ack_action": LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
        "close_delay_ms": LOGOUT_CLOSE_DELAY_MS,
    },
    "requests": {
        "subcode01": {
            "pc_size": 34,
            "pc_sha256": LOGOUT_REQUEST_PC_SHA256[1],
        },
        "subcode03": {
            "pc_size": 34,
            "pc_sha256": LOGOUT_REQUEST_PC_SHA256[3],
        },
    },
    "composed_responses": {
        "subcode01": {
            "pc_size": 36,
            "pc_sha256": LOGOUT_ACK_PC_SHA256[1],
            "frame_size": 46,
            "frame_sha256": LOGOUT_ACK_FRAME_SHA256[1],
        },
        "subcode03": {
            "pc_size": 36,
            "pc_sha256": LOGOUT_ACK_PC_SHA256[3],
            "frame_size": 46,
            "frame_sha256": LOGOUT_ACK_FRAME_SHA256[3],
        },
    },
    "persisted_post_state": {
        "sessions_closed_at": "written_before_ack_bytes_are_queued",
        "position_rewrite": "none",
    },
    "capabilities": [
        "acknowledge_exact_captured_logout_requests_after_clean_close",
        "silence_connection_after_acknowledged_logout",
        "server_initiated_clean_socket_close_after_acknowledged_logout",
    ],
    "nonclaims": [
        "original_server_response_policy",
        "client_observable_exit_or_character_select_return",
        "logout_outside_runtime_ready_sequence",
        "subcodes_other_than_01_and_03",
        "production_baseline_behavior",
    ],
}

_EXPECTED_BY_ID = {
    _PROFILE_ECHO.scenario_id: (_EXPECTED_ECHO, _PROFILE_ECHO),
    _PROFILE_ACK_CLOSE.scenario_id: (_EXPECTED_ACK_CLOSE, _PROFILE_ACK_CLOSE),
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


def load_logout_hypothesis_scenario(path: str | Path) -> LogoutHypothesisScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid logout hypothesis scenario") from exc
    if type(data) is not dict or data.get("id") not in _EXPECTED_BY_ID:
        raise ValueError("logout hypothesis scenario exceeds the exact allowlist")
    expected, profile = _EXPECTED_BY_ID[data["id"]]
    if not _exact_equal(data, expected):
        raise ValueError("logout hypothesis scenario exceeds the exact allowlist")
    return require_logout_hypothesis_scenario(profile)


def require_logout_hypothesis_scenario(value: Any) -> LogoutHypothesisScenario:
    if type(value) is not LogoutHypothesisScenario or value not in (
        _PROFILE_ECHO, _PROFILE_ACK_CLOSE,
    ):
        raise ValueError("logout hypothesis scenario object exceeds the allowlist")
    for subcode in LOGOUT_SUBCODES:
        digest = hashlib.sha256(LOGOUT_REQUEST_PCS[subcode]).hexdigest().upper()
        if digest != LOGOUT_REQUEST_PC_SHA256[subcode]:
            raise RuntimeError("logout hypothesis request fixture drift")
    return value


def classify_logout_attempt(legacy: Any, parsed: Any) -> str:
    """Classify one 0x1B40-bearing parse against the exact captured forms."""
    if not (
        parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
        and parsed.outer_version == 0
        and parsed.outer_mask == 0x02
        and parsed.vital_count == 1
        and parsed.nested_id == LOGOUT_VITAL_ID
        and parsed.nested_version == 0
    ):
        return "wrong_envelope"
    for subcode in LOGOUT_SUBCODES:
        if parsed.nested_payload == LOGOUT_REQUEST_PAYLOADS[subcode]:
            return f"exact_{subcode:02d}"
    return "wrong_payload"


# PF-HYPOTHESIS-LEDGER: HYP-PF-012 active
def make_logout_ack_response(legacy: Any, subcode: int) -> tuple[bytes, bytes]:
    """Build and independently pin the designed echo ack for one subcode."""
    if subcode not in LOGOUT_SUBCODES:
        raise ValueError("logout ack subcode exceeds the accepted captures")
    pc, frame = legacy.make_runtime_vitals([
        (LOGOUT_VITAL_ID, 0, LOGOUT_REQUEST_PAYLOADS[subcode]),
    ])
    if (
        len(pc) != 36
        or hashlib.sha256(pc).hexdigest().upper() != LOGOUT_ACK_PC_SHA256[subcode]
    ):
        raise RuntimeError("HYP-PF-012 response PC drift")
    if (
        len(frame) != 46
        or hashlib.sha256(frame).hexdigest().upper()
        != LOGOUT_ACK_FRAME_SHA256[subcode]
    ):
        raise RuntimeError("HYP-PF-012 response frame drift")
    return pc, frame
